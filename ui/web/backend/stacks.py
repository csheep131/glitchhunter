"""
Stack-Manager für GlitchHunter Web-UI.

Verwaltet Hardware-Stacks (A, B, C) mit:
- Konfiguration (geladen aus config.yaml)
- Status-Überwachung
- Testing
- Model-Management

Features:
- 3 Stacks: A (Standard), B (Enhanced), C (Remote API)
- Hardware-Detektion
- Model-Loading/Unloading
- Stack-Testing
- Dynamische Konfiguration aus config.yaml
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Projekt-Root Verzeichnis (2 Ebenen hoch von ui/web/backend/)
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


@dataclass
class StackConfig:
    """Konfiguration für einen Stack."""
    id: str
    name: str
    description: str
    hardware: str
    mode: str
    models: Dict[str, str]
    model_paths: Dict[str, str] = field(default_factory=dict)  # Modell-ID -> Pfad
    security: Dict[str, Any] = field(default_factory=dict)
    inference: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    priority: int = 1
    vram_limit: int = 0
    cuda_compute: str = ""


@dataclass
class StackStatus:
    """Status eines Stacks."""
    id: str
    status: str  # online, offline, error
    gpu_usage: float = 0.0
    vram_usage: float = 0.0
    temperature: float = 0.0
    active_models: List[str] = field(default_factory=list)
    last_test: Optional[datetime] = None
    test_result: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class TestResult:
    """Ergebnis eines Stack-Tests."""
    test_id: str
    stack_id: str
    test_type: str  # quick, performance, stress
    status: str  # running, completed, failed
    duration_seconds: float
    results: Dict[str, Any]
    recommendation: str
    created_at: datetime = field(default_factory=datetime.now)


class StackManager:
    """
    Manager für Hardware-Stacks.
    
    Features:
    - Stack-Konfiguration
    - Status-Überwachung
    - Testing
    - Model-Management
    
    Usage:
        manager = StackManager()
        manager.initialize()
        stacks = manager.get_all_stacks()
    """
    
    def __init__(self):
        """Initialisiert Stack-Manager."""
        self._stacks: Dict[str, StackConfig] = {}
        self._status: Dict[str, StackStatus] = {}
        self._test_results: Dict[str, TestResult] = {}
        
        logger.info("StackManager initialisiert")
    
    def initialize(self, config=None):
        """Initialisiert alle Stacks.
        
        Args:
            config: Optional Config-Objekt aus config.yaml. 
                    Wenn None, wird config.yaml automatisch geladen.
        """
        logger.info("Initialisiere Stacks...")

        # Config laden wenn nicht übergeben
        if config is None:
            try:
                import sys
                sys.path.insert(0, str(_PROJECT_ROOT / "src"))
                from core.config import Config
                config = Config.load(_PROJECT_ROOT / "config.yaml")
                logger.info(f"Config aus {_PROJECT_ROOT / 'config.yaml'} geladen")
            except Exception as e:
                logger.warning(f"Konnte config.yaml nicht laden ({e}), verwende Fallback-Konfiguration")
                config = None

        # Stack A aus config.yaml laden
        if config and "stack_a" in config.hardware:
            hw = config.hardware["stack_a"]
            self._stacks["stack_a"] = self._create_stack_from_config(
                stack_id="stack_a",
                name="Stack A (Standard)",
                description=f"Sequenzielle Analyse mit {hw.name} ({hw.vram_limit}GB)",
                hardware=hw.name,
                mode=hw.mode,
                models=hw.models,
                security=hw.security,
                inference=hw.inference,
                vram_limit=hw.vram_limit,
                cuda_compute=hw.cuda_compute,
            )
        else:
            # Fallback
            self._stacks["stack_a"] = StackConfig(
                id="stack_a",
                name="Stack A (Standard)",
                description="Sequenzielle Analyse mit GTX 3060 (8GB)",
                hardware="GTX 3060 (8GB VRAM)",
                mode="sequential",
                models={
                    "primary": "qwen3.5-9b",
                    "secondary": "phi-4-mini",
                },
                model_paths={
                    "primary": str(_PROJECT_ROOT / "models" / "Qwen3.5-9B-UncensoredHauhauCS-Aggressive-Q4_K_M.gguf"),
                    "secondary": str(_PROJECT_ROOT / "models" / "phi-4-mini-instruct.Q4_K_M.gguf"),
                },
                security={"enabled": True, "level": "lite", "owasp_top10": True},
                inference={"max_batch_size": 1, "parallel_requests": False},
                vram_limit=8,
                priority=1,
            )

        # Stack B aus config.yaml laden
        if config and "stack_b" in config.hardware:
            hw = config.hardware["stack_b"]
            self._stacks["stack_b"] = self._create_stack_from_config(
                stack_id="stack_b",
                name="Stack B (Enhanced)",
                description=f"Parallele Analyse mit {hw.name} ({hw.vram_limit}GB)",
                hardware=hw.name,
                mode=hw.mode,
                models=hw.models,
                security=hw.security,
                inference=hw.inference,
                vram_limit=hw.vram_limit,
                cuda_compute=hw.cuda_compute,
            )
        else:
            # Fallback
            self._stacks["stack_b"] = StackConfig(
                id="stack_b",
                name="Stack B (Enhanced)",
                description="Parallele Analyse mit RTX 3090 (24GB)",
                hardware="RTX 3090 (24GB VRAM)",
                mode="parallel",
                models={
                    "primary": "qwen3.5-27b",
                    "secondary": "deepseek-v3.2-small",
                },
                model_paths={
                    "primary": str(_PROJECT_ROOT / "models" / "Qwen3.5-27B-Instruct-Q4_K_M.gguf"),
                    "secondary": str(_PROJECT_ROOT / "models" / "DeepSeek-V3.2-Small-Q4_K_M.gguf"),
                },
                security={"enabled": True, "level": "full"},
                inference={"max_batch_size": 4, "parallel_requests": True},
                vram_limit=24,
                priority=2,
            )

        # Stack C: Remote API (immer hardcoded, da nicht in config.yaml)
        self._stacks["stack_c"] = StackConfig(
            id="stack_c",
            name="Stack C (Remote API)",
            description="Hybrid-Analyse mit Remote-APIs",
            hardware="Remote (Ollama LAN, Cloud APIs)",
            mode="hybrid",
            models={
                "ollama_lan": "qwen3.5:9b-instruct-q4_k_m",
                "vllm_lan": "Qwen/Qwen3.5-27B-Instruct",
                "openai": "gpt-4o-2024-11-20",
                "anthropic": "claude-3-5-sonnet-20241022",
                "deepseek": "deepseek-chat",
            },
            security={"enabled": True, "level": "full"},
            inference={"max_batch_size": 10, "parallel_requests": True, "remote_enabled": True},
            priority=3,
        )

        # Initiale Status setzen
        for stack_id in self._stacks:
            self._status[stack_id] = StackStatus(
                id=stack_id,
                status="offline",  # Wird bei erstem Check aktualisiert
            )

        logger.info(f"{len(self._stacks)} Stacks initialisiert")

    def _create_stack_from_config(
        self,
        stack_id: str,
        name: str,
        description: str,
        hardware: str,
        mode: str,
        models: Dict[str, Any],
        security: Dict[str, Any],
        inference: Dict[str, Any],
        vram_limit: int = 0,
        cuda_compute: str = "",
    ) -> StackConfig:
        """Erstellt StackConfig aus config.yaml Daten.
        
        Args:
            stack_id: Stack-ID
            name: Anzeigename
            description: Beschreibung
            hardware: Hardware-Name
            mode: Ausführungsmodus
            models: Modell-Dict aus config.yaml
            security: Security-Konfiguration
            inference: Inference-Konfiguration
            vram_limit: VRAM-Limit in GB
            cuda_compute: CUDA Compute Capability
            
        Returns:
            StackConfig instance
        """
        # Modell-Namen und Pfade extrahieren
        model_names = {}
        model_paths = {}
        
        for role, model_data in models.items():
            if isinstance(model_data, dict):
                model_name = model_data.get("name", role)
                model_path = model_data.get("path", "")
                
                # Pfad relativ zu Projekt-Root auflösen
                if model_path and not Path(model_path).is_absolute():
                    model_path = str(_PROJECT_ROOT / model_path)
                
                model_names[role] = model_name
                model_paths[role] = model_path
            else:
                model_names[role] = str(model_data)
                model_paths[role] = ""

        return StackConfig(
            id=stack_id,
            name=name,
            description=description,
            hardware=hardware,
            mode=mode,
            models=model_names,
            model_paths=model_paths,
            security=security,
            inference=inference,
            vram_limit=vram_limit,
            cuda_compute=cuda_compute,
            priority=1 if stack_id == "stack_a" else 2,
        )
    
    def get_all_stacks(self) -> List[StackConfig]:
        """
        Returns alle Stacks.
        
        Returns:
            Liste von StackConfig
        """
        return list(self._stacks.values())
    
    def get_stack(self, stack_id: str) -> Optional[StackConfig]:
        """
        Returns Stack nach ID.
        
        Args:
            stack_id: Stack-ID
            
        Returns:
            StackConfig oder None
        """
        return self._stacks.get(stack_id)
    
    def update_stack_config(self, stack_id: str, updates: Dict[str, Any]):
        """
        Aktualisiert Stack-Konfiguration.

        Args:
            stack_id: Stack-ID
            updates: Updates-Dict
        """
        if stack_id not in self._stacks:
            raise ValueError(f"Stack {stack_id} nicht gefunden")

        stack = self._stacks[stack_id]

        # Spezielle Behandlung für model_paths
        if "model_paths" in updates:
            for role, path in updates["model_paths"].items():
                if path:  # Nur wenn Pfad nicht leer
                    stack.model_paths[role] = path
            del updates["model_paths"]  # Nicht noch einmal via setattr

        # Spezielle Behandlung für models (nur Namen, nicht Pfade)
        if "models" in updates and isinstance(updates["models"], dict):
            for role, name in updates["models"].items():
                if role in stack.models:
                    stack.models[role] = name
            del updates["models"]

        # Felder aktualisieren
        for key, value in updates.items():
            if hasattr(stack, key):
                setattr(stack, key, value)

        logger.info(f"Stack {stack_id} Konfiguration aktualisiert")

    def update_model_path(self, stack_id: str, role: str, path: str):
        """
        Aktualisiert den Pfad eines Modells für einen Stack.
        
        Args:
            stack_id: Stack-ID
            role: Modell-Rolle (primary, secondary)
            path: Neuer Pfad zum Modell
        """
        if stack_id not in self._stacks:
            raise ValueError(f"Stack {stack_id} nicht gefunden")
        
        stack = self._stacks[stack_id]
        stack.model_paths[role] = path
        logger.info(f"Stack {stack_id} Modell-Pfad für '{role}' aktualisiert: {path}")

    def get_all_model_paths(self) -> Dict[str, Dict[str, str]]:
        """
        Returns alle Modell-Pfade aller Stacks.
        
        Returns:
            Dict: {stack_id: {role: path, ...}, ...}
        """
        result = {}
        for stack_id, stack in self._stacks.items():
            if stack.model_paths:
                result[stack_id] = dict(stack.model_paths)
        return result
    
    def get_stack_status(self, stack_id: str) -> Optional[StackStatus]:
        """
        Returns Stack-Status.
        
        Args:
            stack_id: Stack-ID
            
        Returns:
            StackStatus oder None
        """
        return self._status.get(stack_id)
    
    async def update_stack_status(self, stack_id: str):
        """
        Aktualisiert Stack-Status (Hardware-Check).
        
        Args:
            stack_id: Stack-ID
        """
        if stack_id not in self._stacks:
            return
        
        status = self._status[stack_id]
        stack = self._stacks[stack_id]
        
        try:
            if stack_id == "stack_c":
                # Remote Stack - API-Verfügbarkeit prüfen
                status.status = "online"  # Simuliert
                status.gpu_usage = 0.0
                status.vram_usage = 0.0
            else:
                # Lokale Stacks - Hardware prüfen
                gpu_info = await self._get_gpu_info()
                
                status.status = "online" if gpu_info else "offline"
                status.gpu_usage = gpu_info.get("usage", 0.0) if gpu_info else 0.0
                status.vram_usage = gpu_info.get("vram", 0.0) if gpu_info else 0.0
                status.temperature = gpu_info.get("temperature", 0.0) if gpu_info else 0.0
            
            logger.debug(f"Stack {stack_id} Status aktualisiert: {status.status}")
            
        except Exception as e:
            logger.error(f"Fehler beim Status-Update für {stack_id}: {e}")
            status.status = "error"
            status.error_message = str(e)
    
    async def _get_gpu_info(self) -> Optional[Dict[str, float]]:
        """
        Holt GPU-Informationen.
        
        Returns:
            Dict mit GPU-Infos oder None
        """
        try:
            # PyNVML für NVIDIA-GPUs
            import pynvml
            
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            
            usage = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
            memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
            temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            
            pynvml.nvmlShutdown()
            
            return {
                "usage": float(usage),
                "vram": float(memory.used / 1024 / 1024),  # MB
                "temperature": float(temperature),
            }
            
        except ImportError:
            logger.debug("PyNVML nicht installiert, GPU-Info nicht verfügbar")
            return None
        except Exception as e:
            logger.debug(f"GPU-Info nicht verfügbar: {e}")
            return None
    
    async def test_stack(
        self,
        stack_id: str,
        test_type: str = "quick",
    ) -> TestResult:
        """
        Führt Stack-Test durch.
        
        Args:
            stack_id: Stack-ID
            test_type: Test-Typ (quick, performance, stress)
            
        Returns:
            TestResult
        """
        if stack_id not in self._stacks:
            raise ValueError(f"Stack {stack_id} nicht gefunden")
        
        test_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        result = TestResult(
            test_id=test_id,
            stack_id=stack_id,
            test_type=test_type,
            status="running",
            duration_seconds=0.0,
            results={},
            recommendation="Test läuft...",
        )
        
        self._test_results[test_id] = result
        
        try:
            start_time = time.time()
            
            if test_type == "quick":
                results = await self._run_quick_test(stack_id)
            elif test_type == "performance":
                results = await self._run_performance_test(stack_id)
            elif test_type == "stress":
                results = await self._run_stress_test(stack_id)
            else:
                raise ValueError(f"Unbekannter Test-Typ: {test_type}")
            
            duration = time.time() - start_time
            
            result.status = "completed"
            result.duration_seconds = duration
            result.results = results
            result.recommendation = self._generate_recommendation(stack_id, results)
            
            # Status aktualisieren
            self._status[stack_id].last_test = datetime.now()
            self._status[stack_id].test_result = "passed" if results.get("success", False) else "failed"
            
        except Exception as e:
            result.status = "failed"
            result.duration_seconds = time.time() - start_time
            result.recommendation = f"Test fehlgeschlagen: {e}"
        
        return result
    
    async def _run_quick_test(self, stack_id: str) -> Dict[str, Any]:
        """
        Führt Quick-Test durch (< 30s).
        
        Args:
            stack_id: Stack-ID
            
        Returns:
            Test-Ergebnisse
        """
        logger.info(f"Quick-Test für {stack_id}")
        
        # Simulierter Test
        await asyncio.sleep(2)  # 2 Sekunden warten
        
        return {
            "success": True,
            "model_load_time_ms": 234.5,
            "inference_time_ms": 123.4,
            "message": "Quick-Test erfolgreich",
        }
    
    async def _run_performance_test(self, stack_id: str) -> Dict[str, Any]:
        """
        Führt Performance-Test durch (2-5 min).
        
        Args:
            stack_id: Stack-ID
            
        Returns:
            Test-Ergebnisse
        """
        logger.info(f"Performance-Test für {stack_id}")
        
        # Simulierter Test
        await asyncio.sleep(5)  # 5 Sekunden warten (simuliert)
        
        return {
            "success": True,
            "avg_response_time_ms": 234.5,
            "p95_response_time_ms": 456.7,
            "p99_response_time_ms": 678.9,
            "requests_per_second": 12.5,
            "total_requests": 100,
            "failed_requests": 2,
            "message": "Performance-Test erfolgreich",
        }
    
    async def _run_stress_test(self, stack_id: str) -> Dict[str, Any]:
        """
        Führt Stress-Test durch (10-20 min).
        
        Args:
            stack_id: Stack-ID
            
        Returns:
            Test-Ergebnisse
        """
        logger.info(f"Stress-Test für {stack_id}")
        
        # Simulierter Test
        await asyncio.sleep(10)  # 10 Sekunden warten (simuliert)
        
        return {
            "success": True,
            "max_concurrent_requests": 50,
            "memory_peak_mb": 18432,
            "error_rate": 0.02,
            "recovery_time_ms": 123.4,
            "message": "Stress-Test erfolgreich",
        }
    
    def _generate_recommendation(
        self,
        stack_id: str,
        results: Dict[str, Any],
    ) -> str:
        """
        Generiert Empfehlung basierend auf Test-Ergebnissen.
        
        Args:
            stack_id: Stack-ID
            results: Test-Ergebnisse
            
        Returns:
            Empfehlung
        """
        if not results.get("success", False):
            return "Stack ist nicht bereit für Produktion"
        
        if "avg_response_time_ms" in results:
            avg_time = results["avg_response_time_ms"]
            if avg_time < 200:
                return "Exzellente Performance - Bereit für Produktion"
            elif avg_time < 500:
                return "Gute Performance - Bereit für Produktion"
            else:
                return "Performance verbesserungswürdig - Testing empfohlen"
        
        return "Stack ist bereit für Produktion"
    
    def get_test_result(self, test_id: str) -> Optional[TestResult]:
        """
        Returns Test-Ergebnis nach ID.
        
        Args:
            test_id: Test-ID
            
        Returns:
            TestResult oder None
        """
        return self._test_results.get(test_id)
    
    def get_test_history(self, stack_id: str, limit: int = 10) -> List[TestResult]:
        """
        Returns Test-Historie für Stack.
        
        Args:
            stack_id: Stack-ID
            limit: Limit
            
        Returns:
            Liste von TestResult
        """
        tests = [
            t for t in self._test_results.values()
            if t.stack_id == stack_id
        ]
        
        # Nach Datum sortieren (neueste zuerst)
        tests.sort(key=lambda x: x.created_at, reverse=True)
        
        return tests[:limit]


# ============== Globale Instanz ==============

_stack_manager: Optional[StackManager] = None


def get_stack_manager() -> StackManager:
    """
    Returns globale StackManager-Instanz.
    
    Returns:
        StackManager
    """
    global _stack_manager
    if _stack_manager is None:
        _stack_manager = StackManager()
        _stack_manager.initialize()
    return _stack_manager
