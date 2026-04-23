"""
Stack-Manager für GlitchHunter Web-UI.

Verwaltet Hardware-Stacks (A, B, C) mit:
- Konfiguration
- Status-Überwachung
- Testing
- Model-Management

Features:
- 3 Stacks: A (Standard), B (Enhanced), C (Remote API)
- Hardware-Detektion
- Model-Loading/Unloading
- Stack-Testing
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StackConfig:
    """Konfiguration für einen Stack."""
    id: str
    name: str
    description: str
    hardware: str
    mode: str
    models: Dict[str, str]
    security: Dict[str, Any]
    inference: Dict[str, Any]
    enabled: bool = True
    priority: int = 1


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
    
    def initialize(self):
        """Initialisiert alle Stacks."""
        logger.info("Initialisiere Stacks...")
        
        # Stack A: Standard (GTX 3060)
        self._stacks["stack_a"] = StackConfig(
            id="stack_a",
            name="Stack A (Standard)",
            description="Sequenzielle Analyse mit GTX 3060 (8GB)",
            hardware="GTX 3060 (8GB VRAM)",
            mode="sequential",
            models={
                "primary": "qwen3.5-9b-q4_k_m",
                "secondary": "phi-4-mini-q8",
            },
            security={
                "enabled": True,
                "level": "full",
                "owasp_top10": True,
            },
            inference={
                "max_batch_size": 4,
                "parallel_requests": False,
            },
            priority=1,
        )
        
        # Stack B: Enhanced (RTX 3090)
        self._stacks["stack_b"] = StackConfig(
            id="stack_b",
            name="Stack B (Enhanced)",
            description="Parallele Analyse mit RTX 3090 (24GB)",
            hardware="RTX 3090 (24GB VRAM)",
            mode="parallel",
            models={
                "primary": "qwen3.5-27b-q4_k_m",
                "secondary": "deepseek-v3.2-q8",
            },
            security={
                "enabled": True,
                "level": "full",
            },
            inference={
                "max_batch_size": 10,
                "parallel_requests": True,
            },
            priority=2,
        )
        
        # Stack C: Remote API
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
            security={
                "enabled": True,
                "level": "full",
            },
            inference={
                "max_batch_size": 10,
                "parallel_requests": True,
                "remote_enabled": True,
            },
            priority=3,
        )
        
        # Initiale Status setzen
        for stack_id in self._stacks:
            self._status[stack_id] = StackStatus(
                id=stack_id,
                status="offline",  # Wird bei erstem Check aktualisiert
            )
        
        logger.info(f"{len(self._stacks)} Stacks initialisiert")
    
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
        
        # Felder aktualisieren
        for key, value in updates.items():
            if hasattr(stack, key):
                setattr(stack, key, value)
        
        logger.info(f"Stack {stack_id} Konfiguration aktualisiert")
    
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
