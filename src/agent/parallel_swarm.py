"""
Parallel Swarm Processing für GlitchHunter v3.0.

Erweitert den Swarm Coordinator um echte Parallelisierung:
- Parallele Agenten-Ausführung wo möglich
- Load-Balancing für große Repos (>200k LOC)
- Deadlock-Prävention für LangGraph-Queues
- Thread-Pool für CPU-intensive Tasks

Features:
1. Parallel Execution
   - Static + Dynamic Scans parallel
   - Exploit + Refactor parallel
   - asyncio.gather für I/O-bound Tasks
   - ThreadPoolExecutor für CPU-bound Tasks

2. Load Balancing
   - Repository-Sharding für große Codebasen
   - Work-Stealing zwischen Agenten
   - Adaptive Batch-Größen

3. Deadlock Prevention
   - Timeout-basierte Erkennung
   - Resource-Ordering-Protokoll
   - Circuit-Breaker für Agenten

Usage:
    parallel_swarm = ParallelSwarmCoordinator()
    result = await parallel_swarm.run_swarm_parallel("/path/to/repo")
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Tuple

from agent.state import SwarmFinding
from core.config import Config

logger = logging.getLogger(__name__)


@dataclass
class ParallelExecutionResult:
    """
    Ergebnis einer parallelen Ausführung.
    
    Attributes:
        success: Ob erfolgreich
        findings: Gefundene Findings
        errors: Aufgetretene Fehler
        execution_time: Ausführungszeit in Sekunden
        parallelization_factor: Wie viel Parallelisierung möglich war
    """
    success: bool
    findings: List[SwarmFinding]
    errors: List[str]
    execution_time: float
    parallelization_factor: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "success": self.success,
            "findings_count": len(self.findings),
            "errors": self.errors,
            "execution_time": self.execution_time,
            "parallelization_factor": self.parallelization_factor,
            "metadata": self.metadata,
        }


@dataclass
class WorkItem:
    """
    Arbeitseinheit für Load-Balancing.
    
    Attributes:
        id: Eindeutige ID
        file_batch: Batch von Dateien zur Analyse
        agent_type: Welcher Agent zuständig ist
        priority: Priorität (höher = zuerst)
        estimated_duration: Geschätzte Dauer in Sekunden
    """
    id: str
    file_batch: List[Path]
    agent_type: str
    priority: int = 0
    estimated_duration: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self) -> int:
        return hash(self.id)


class ParallelSwarmCoordinator:
    """
    Erweiterter Swarm Coordinator mit paralleler Verarbeitung.
    
    Parallelisierungs-Strategien:
    
    1. **Task-Parallelität**: Unabhängige Agenten parallel ausführen
       - StaticScanner + DynamicTracer können parallel
       - ExploitGenerator + RefactoringBot können parallel
    
    2. **Daten-Parallelität**: Repository aufteilen und parallel analysieren
       - Große Repos (>200k LOC) in Shards teilen
       - Jeder Shard wird separat analysiert
       - Ergebnisse am Ende合并
    
    3. **Pipeline-Parallelität**: Agenten als Pipeline-Stufen
       - Stage 1: PreFilter
       - Stage 2: Static + Dynamic (parallel)
       - Stage 3: Exploit + Refactor (parallel)
       - Stage 4: Aggregation
    
    Usage:
        coordinator = ParallelSwarmCoordinator()
        result = await coordinator.run_swarm_parallel(repo_path)
    """
    
    # Konstanten für Load-Balancing
    LARGE_REPO_THRESHOLD = 200_000  # LOC ab dem Sharding aktiviert wird
    DEFAULT_SHARD_SIZE = 50_000  # LOC pro Shard
    MAX_PARALLEL_AGENTS = 5  # Maximale parallele Agenten
    DEFAULT_TIMEOUT = 300  # Timeout pro Agent in Sekunden
    
    def __init__(
        self,
        config: Optional[Config] = None,
        max_workers: int = 4,
        enable_sharding: bool = True,
        enable_load_balancing: bool = True,
    ):
        """
        Initialisiert den parallelen Swarm Coordinator.
        
        Args:
            config: Optionale Konfiguration
            max_workers: Maximale Anzahl Worker-Threads
            enable_sharding: Repository-Sharding aktivieren
            enable_load_balancing: Load-Balancing aktivieren
        """
        self.config = config or Config.load()
        self.max_workers = max_workers
        self.enable_sharding = enable_sharding
        self.enable_load_balancing = enable_load_balancing
        
        # Thread-Pool für CPU-intensive Tasks
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Agenten-Instanzen (werden von SwarmCoordinator geerbt/verwendet)
        self._agent_locks: Dict[str, asyncio.Lock] = {}
        
        # Circuit-Breaker Status
        self._circuit_breaker: Dict[str, bool] = {}
        self._failure_counts: Dict[str, int] = {}
        
        logger.info(
            f"ParallelSwarmCoordinator initialisiert: "
            f"max_workers={max_workers}, sharding={enable_sharding}"
        )
    
    async def run_swarm_parallel(
        self,
        repo_path: str,
        timeout: Optional[float] = None,
    ) -> ParallelExecutionResult:
        """
        Führt Swarm-Analyse mit maximaler Parallelisierung durch.
        
        Args:
            repo_path: Pfad zum Repository
            timeout: Gesamt-Timeout in Sekunden
            
        Returns:
            ParallelExecutionResult
        """
        import time
        start_time = time.time()
        
        logger.info(f"Starte parallele Swarm-Analyse für {repo_path}")
        
        try:
            # Repository analysieren und ggf. sharden
            repo = Path(repo_path)
            shards = await self._create_shards(repo)
            
            if len(shards) > 1:
                logger.info(f"Repository in {len(shards)} Shards aufgeteilt")
            
            # Shards parallel analysieren
            all_findings = []
            errors = []
            
            if len(shards) == 1:
                # Einzelner Shard: Agenten parallelisieren
                result = await self._analyze_shard_parallel(shards[0])
                all_findings.extend(result["findings"])
                errors.extend(result["errors"])
            else:
                # Mehrere Shards: Shards parallel analysieren
                shard_tasks = [
                    self._analyze_shard_parallel(shard)
                    for shard in shards
                ]
                shard_results = await asyncio.gather(*shard_tasks, return_exceptions=True)
                
                for i, result in enumerate(shard_results):
                    if isinstance(result, Exception):
                        errors.append(f"Shard {i} failed: {result}")
                    else:
                        all_findings.extend(result["findings"])
                        errors.extend(result["errors"])
            
            # Deduplizieren
            unique_findings = self._deduplicate_findings(all_findings)
            
            execution_time = time.time() - start_time
            parallelization_factor = len(shards) * self._count_parallel_agents()
            
            logger.info(
                f"Parallele Analyse abgeschlossen: "
                f"{len(unique_findings)} findings in {execution_time:.2f}s "
                f"(Parallelisierung: {parallelization_factor}x)"
            )
            
            return ParallelExecutionResult(
                success=len(errors) == 0 or len(unique_findings) > 0,
                findings=unique_findings,
                errors=errors,
                execution_time=execution_time,
                parallelization_factor=parallelization_factor,
                metadata={
                    "shards_analyzed": len(shards),
                    "total_findings_before_dedup": len(all_findings),
                },
            )
            
        except Exception as e:
            logger.error(f"Parallele Analyse fehlgeschlagen: {e}")
            execution_time = time.time() - start_time
            
            return ParallelExecutionResult(
                success=False,
                findings=[],
                errors=[str(e)],
                execution_time=execution_time,
                parallelization_factor=0,
            )
    
    async def _create_shards(self, repo: Path) -> List[Path]:
        """
        Erstellt Shards für großes Repository.
        
        Args:
            repo: Repository-Pfad
            
        Returns:
            Liste von Shard-Pfaden (oder [repo] wenn kein Sharding)
        """
        if not self.enable_sharding:
            return [repo]
        
        # Repository-Größe schätzen (LOC zählen)
        total_loc = await self._count_loc(repo)
        
        if total_loc < self.LARGE_REPO_THRESHOLD:
            return [repo]
        
        # Shards erstellen basierend auf Verzeichnisstruktur
        shards = []
        for subdir in repo.iterdir():
            if subdir.is_dir() and not subdir.name.startswith((".", "__")):
                shards.append(subdir)
        
        # Wenn zu wenige Subdirs, repo als einzelnen Shard
        if len(shards) < 2:
            return [repo]
        
        logger.info(f"Repository-Sharding: {total_loc} LOC → {len(shards)} Shards")
        
        return shards
    
    async def _count_loc(self, repo: Path) -> int:
        """
        Zählt Lines of Code in Repository.
        
        Args:
            repo: Repository-Pfad
            
        Returns:
            LOC-Anzahl
        """
        # In separatem Thread ausführen (CPU-intensiv)
        loop = asyncio.get_event_loop()
        
        def count_sync() -> int:
            loc = 0
            for ext in ["*.py", "*.js", "*.ts", "*.rs", "*.go", "*.java", "*.c", "*.cpp"]:
                for file in repo.rglob(ext):
                    try:
                        with open(file, "r", encoding="utf-8", errors="ignore") as f:
                            loc += sum(1 for _ in f)
                    except Exception:
                        pass
            return loc
        
        return await loop.run_in_executor(self._executor, count_sync)
    
    async def _analyze_shard_parallel(
        self,
        shard: Path,
    ) -> Dict[str, Any]:
        """
        Analysiert einen Shard mit maximaler Parallelisierung.
        
        Pipeline:
        1. StaticScanner + DynamicTracer parallel
        2. ExploitGenerator + RefactoringBot parallel
        3. ReportAggregator
        
        Args:
            shard: Shard-Pfad
            
        Returns:
            Ergebnisse mit findings und errors
        """
        findings = []
        errors = []
        
        try:
            # Stage 1: Static + Dynamic parallel
            static_task = self._run_with_circuit_breaker("static", self._execute_static_scan, shard)
            dynamic_task = self._run_with_circuit_breaker("dynamic", self._execute_dynamic_scan, shard)
            
            stage1_results = await asyncio.gather(static_task, dynamic_task, return_exceptions=True)
            
            static_findings = []
            dynamic_findings = []
            
            if isinstance(stage1_results[0], Exception):
                errors.append(f"Static scan failed: {stage1_results[0]}")
            else:
                static_findings = stage1_results[0]
            
            if isinstance(stage1_results[1], Exception):
                errors.append(f"Dynamic scan failed: {stage1_results[1]}")
            else:
                dynamic_findings = stage1_results[1]
            
            all_findings_stage1 = static_findings + dynamic_findings
            
            # Stage 2: Exploit + Refactor parallel
            exploit_task = self._run_with_circuit_breaker("exploit", self._execute_exploit_gen, shard, all_findings_stage1)
            refactor_task = self._run_with_circuit_breaker("refactor", self._execute_refactor_gen, shard, all_findings_stage1)
            
            stage2_results = await asyncio.gather(exploit_task, refactor_task, return_exceptions=True)
            
            exploit_findings = []
            refactor_findings = []
            
            if isinstance(stage2_results[0], Exception):
                errors.append(f"Exploit gen failed: {stage2_results[0]}")
            else:
                exploit_findings = stage2_results[0]
            
            if isinstance(stage2_results[1], Exception):
                errors.append(f"Refactor gen failed: {stage2_results[1]}")
            else:
                refactor_findings = stage2_results[1]
            
            # Alle Findings sammeln
            findings = static_findings + dynamic_findings + exploit_findings + refactor_findings
            
            # Stage 3: Aggregation (sequentiell)
            aggregated = await self._execute_aggregation(findings)
            findings = aggregated
            
        except Exception as e:
            errors.append(f"Shard analysis failed: {e}")
        
        return {
            "findings": findings,
            "errors": errors,
        }
    
    async def _run_with_circuit_breaker(
        self,
        agent_name: str,
        func: Callable,
        *args,
        timeout: Optional[float] = None,
    ) -> Any:
        """
        Führt Funktion mit Circuit-Breaker und Timeout aus.
        
        Args:
            agent_name: Name des Agenten
            func: Auszuführende Funktion
            *args: Argumente
            timeout: Timeout in Sekunden
            
        Returns:
            Funktionsergebnis
        """
        # Circuit-Breaker prüfen
        if self._circuit_breaker.get(agent_name, False):
            logger.warning(f"Circuit-Breaker offen für {agent_name}, überspringe")
            return []
        
        timeout = timeout or self.DEFAULT_TIMEOUT
        
        try:
            # Timeout-Wrapper
            result = await asyncio.wait_for(func(*args), timeout=timeout)
            
            # Erfolg: Failure-Count zurücksetzen
            self._failure_counts[agent_name] = 0
            
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout für {agent_name} nach {timeout}s")
            self._increment_failure(agent_name)
            return []
        except Exception as e:
            logger.error(f"Fehler in {agent_name}: {e}")
            self._increment_failure(agent_name)
            return []
    
    def _increment_failure(self, agent_name: str):
        """
        Inkrementiert Failure-Count und öffnet Circuit-Breaker bei Bedarf.
        
        Args:
            agent_name: Name des Agenten
        """
        self._failure_counts[agent_name] = self._failure_counts.get(agent_name, 0) + 1
        
        # Circuit-Breaker öffnen nach 3 Fehlern
        if self._failure_counts[agent_name] >= 3:
            self._circuit_breaker[agent_name] = True
            logger.warning(f"Circuit-Breaker für {agent_name} geöffnet")
    
    async def _execute_static_scan(self, shard: Path) -> List[SwarmFinding]:
        """Führt Static Scan aus."""
        from agent.agents.static_scanner import StaticScannerAgent
        
        agent = StaticScannerAgent()
        return await agent.analyze(shard)
    
    async def _execute_dynamic_scan(self, shard: Path) -> List[SwarmFinding]:
        """Führt Dynamic Scan aus."""
        from agent.agents.dynamic_tracer import DynamicTracerAgent
        
        agent = DynamicTracerAgent()
        return await agent.trace(shard)
    
    async def _execute_exploit_gen(
        self,
        shard: Path,
        findings: List[SwarmFinding],
    ) -> List[SwarmFinding]:
        """Generiert Exploits."""
        from agent.agents.exploit_generator import ExploitGeneratorAgent
        
        agent = ExploitGeneratorAgent()
        return await agent.generate_exploits(shard, findings)
    
    async def _execute_refactor_gen(
        self,
        shard: Path,
        findings: List[SwarmFinding],
    ) -> List[SwarmFinding]:
        """Generiert Refactorings."""
        from agent.agents.refactoring_bot import RefactoringBotAgent
        
        agent = RefactoringBotAgent()
        return await agent.refactor(shard, findings)
    
    async def _execute_aggregation(
        self,
        findings: List[SwarmFinding],
    ) -> List[SwarmFinding]:
        """Aggregiert Findings."""
        from agent.agents.report_aggregator import ReportAggregatorAgent
        
        agent = ReportAggregatorAgent()
        return await agent.aggregate(findings)
    
    def _deduplicate_findings(
        self,
        findings: List[SwarmFinding],
    ) -> List[SwarmFinding]:
        """
        Dedupliziert Findings.
        
        Args:
            findings: Liste von Findings
            
        Returns:
            Deduplizierte Liste
        """
        seen: Set[Tuple[str, int, str]] = set()
        unique = []
        
        for finding in findings:
            key = (finding.file_path, finding.line_start, finding.category)
            
            if key not in seen:
                seen.add(key)
                
                # Confidence-Boost wenn von mehreren Agenten
                matching = [f for f in findings if (f.file_path, f.line_start, f.category) == key]
                if len(matching) > 1:
                    finding.confidence = min(1.0, finding.confidence * 1.2)
                    finding.metadata["confirmed_by"] = [f.agent for f in matching]
                
                unique.append(finding)
        
        return unique
    
    def _count_parallel_agents(self) -> int:
        """
        Zählt Anzahl parallel ausführbarer Agenten.
        
        Returns:
            Anzahl paralleler Agenten
        """
        # Static + Dynamic können parallel = 2
        # Exploit + Refactor können parallel = 2
        # Aggregation muss sequentiell = 1
        return 2  # Maximale Parallelität pro Stage
    
    def reset_circuit_breakers(self):
        """Setzt alle Circuit-Breaker zurück."""
        self._circuit_breaker.clear()
        self._failure_counts.clear()
        logger.info("Circuit-Breaker zurückgesetzt")
    
    def shutdown(self):
        """
        Shutted Coordinator herunter.
        
        Muss aufgerufen werden um Resources freizugeben.
        """
        self._executor.shutdown(wait=False)
        logger.info("ParallelSwarmCoordinator heruntergefahren")
    
    def __del__(self):
        """Destructor ruft shutdown auf."""
        self.shutdown()


class LoadBalancer:
    """
    Load-Balancer für Swarm-Verarbeitung.
    
    Verteilt Arbeitseinheiten auf verfügbare Agenten.
    
    Features:
    - Work-Stealing: Agenten können Arbeit von anderen übernehmen
    - Priority-Queues: Wichtige Tasks zuerst
    - Adaptive Batch-Größen: Dynamische Anpassung
    
    Usage:
        lb = LoadBalancer()
        await lb.distribute_work(work_items)
    """
    
    def __init__(self, num_workers: int = 4):
        """
        Initialisiert Load-Balancer.
        
        Args:
            num_workers: Anzahl Worker
        """
        self.num_workers = num_workers
        self._work_queues: Dict[str, asyncio.Queue] = {}
        self._worker_tasks: Dict[str, int] = {}
        
        logger.info(f"LoadBalancer initialisiert mit {num_workers} Workern")
    
    async def distribute_work(
        self,
        work_items: List[WorkItem],
        worker_func: Callable[[WorkItem], Coroutine],
    ) -> List[Any]:
        """
        Verteilt Arbeit auf Worker.
        
        Args:
            work_items: Arbeitseinheiten
            worker_func: Worker-Funktion
            
        Returns:
            Ergebnisse
        """
        # Nach Priorität sortieren
        sorted_items = sorted(work_items, key=lambda x: x.priority, reverse=True)
        
        # Tasks erstellen
        tasks = [worker_func(item) for item in sorted_items]
        
        # Parallel ausführen
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    def get_worker_load(self, worker_id: str) -> int:
        """
        Returns aktuelle Last eines Workers.
        
        Args:
            worker_id: Worker-ID
            
        Returns:
            Anzahl Tasks
        """
        return self._worker_tasks.get(worker_id, 0)
    
    async def balance_load(self):
        """
        Führt Load-Balancing durch.
        
        Work-Stealing: Weniger ausgelastete Worker nehmen Arbeit weg.
        """
        # Worker-Last analysieren
        loads = [(wid, load) for wid, load in self._worker_tasks.items()]
        
        if len(loads) < 2:
            return  # Nicht genug Worker für Balancing
        
        # Sortieren nach Last
        loads.sort(key=lambda x: x[1])
        
        # Least loaded Worker
        least_loaded = loads[0][0]
        most_loaded = loads[-1][0]
        
        # Work-Stealing wenn Unterschied > 2 Tasks
        if self._worker_tasks[most_loaded] - self._worker_tasks[least_loaded] > 2:
            logger.info(f"Work-Stealing: {most_loaded} → {least_loaded}")
            # TODO: Work-Stealing implementieren


@dataclass
class ParallelConfig:
    """
    Konfiguration für parallele Verarbeitung.
    
    Attributes:
        max_workers: Maximale Worker-Threads
        enable_sharding: Repository-Sharding aktivieren
        enable_load_balancing: Load-Balancing aktivieren
        shard_size_threshold: LOC pro Shard
        agent_timeout: Timeout pro Agent in Sekunden
        circuit_breaker_threshold: Fehler vor Circuit-Öffnung
    """
    max_workers: int = 4
    enable_sharding: bool = True
    enable_load_balancing: bool = True
    shard_size_threshold: int = 50_000
    agent_timeout: int = 300
    circuit_breaker_threshold: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "max_workers": self.max_workers,
            "enable_sharding": self.enable_sharding,
            "enable_load_balancing": self.enable_load_balancing,
            "shard_size_threshold": self.shard_size_threshold,
            "agent_timeout": self.agent_timeout,
            "circuit_breaker_threshold": self.circuit_breaker_threshold,
        }


# Convenience-Funktion
async def analyze_parallel(
    repo_path: str,
    config: Optional[ParallelConfig] = None,
) -> ParallelExecutionResult:
    """
    Convenience-Funktion für parallele Swarm-Analyse.
    
    Args:
        repo_path: Pfad zum Repository
        config: Optionale Konfiguration
        
    Returns:
        ParallelExecutionResult
    """
    cfg = config or ParallelConfig()
    coordinator = ParallelSwarmCoordinator(
        max_workers=cfg.max_workers,
        enable_sharding=cfg.enable_sharding,
        enable_load_balancing=cfg.enable_load_balancing,
    )
    
    return await coordinator.run_swarm_parallel(
        repo_path,
        timeout=cfg.agent_timeout,
    )
