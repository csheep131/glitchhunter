"""
Hardware Auto-Detection für GlitchHunter v2.0

Erkennt verfügbare Hardware und wählt das beste Backend.
"""

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, Optional
import os
import subprocess

from .detector import HardwareDetector, HardwareProfile
from ..inference.llama_cpp_backend import LlamaCppBackend

logger = logging.getLogger(__name__)


class BackendType(Enum):
    """Verfügbare Inference-Backends."""
    CUDA = auto()
    ROCM = auto()
    CPU_LLAMA_CPP = auto()
    OPENAI_API = auto()
    VLLM = auto()


@dataclass
class BackendRecommendation:
    """Empfohlene Backend-Konfiguration."""
    backend_type: BackendType
    backend_name: str
    confidence: float
    reason: str
    config: Dict[str, Any]
    fallback_chain: list  # Liste von BackendTypes


class AutoDetector:
    """
    Automatische Hardware-Erkennung und Backend-Auswahl.
    
    Features:
    - Erkennt GPU (CUDA/ROCm)
    - Fallback auf llama.cpp CPU
    - API-Key Detection für Cloud-Backends
    - Performance-basierte Empfehlung
    """
    
    def __init__(self):
        self.detector = HardwareDetector()
        self.profile: Optional[HardwareProfile] = None
        self._available_backends: Dict[BackendType, bool] = {}
    
    def detect(self) -> BackendRecommendation:
        """
        Führt vollständige Hardware-Erkennung durch.
        
        Returns:
            BackendRecommendation mit bester Konfiguration
        """
        logger.info("Starte Hardware-Auto-Detection...")
        
        # 1. Hardware-Profil ermitteln
        self.profile = self.detector.detect()
        
        # 2. Verfügbare Backends prüfen
        self._scan_backends()
        
        # 3. Beste Option wählen
        recommendation = self._select_backend()
        
        logger.info(f"Empfohlenes Backend: {recommendation.backend_name}")
        logger.info(f"Grund: {recommendation.reason}")
        
        return recommendation
    
    def _scan_backends(self) -> None:
        """Prüft welche Backends verfügbar sind."""
        # CUDA
        self._available_backends[BackendType.CUDA] = self._check_cuda()
        
        # ROCm
        self._available_backends[BackendType.ROCM] = self._check_rocm()
        
        # llama.cpp
        self._available_backends[BackendType.CPU_LLAMA_CPP] = LlamaCppBackend.is_available()
        
        # OpenAI API
        self._available_backends[BackendType.OPENAI_API] = bool(
            os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
        )
        
        # vLLM
        self._available_backends[BackendType.VLLM] = self._check_vllm()
        
        logger.debug(f"Verfügbare Backends: {self._available_backends}")
    
    def _check_cuda(self) -> bool:
        """Prüft ob CUDA verfügbar ist."""
        try:
            result = subprocess.run(
                ["nvidia-smi"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except:
            # Prüfe über Python
            try:
                import torch
                return torch.cuda.is_available()
            except:
                return False
    
    def _check_rocm(self) -> bool:
        """Prüft ob ROCm verfügbar ist."""
        try:
            result = subprocess.run(
                ["rocminfo"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except:
            try:
                import torch
                return hasattr(torch, 'version') and torch.version.hip is not None
            except:
                return False
    
    def _check_vllm(self) -> bool:
        """Prüft ob vLLM verfügbar ist."""
        try:
            import vllm
            return True
        except:
            return False
    
    def _select_backend(self) -> BackendRecommendation:
        """Wählt das beste verfügbare Backend."""
        # Prioritätsreihenfolge
        priority = [
            (BackendType.CUDA, "NVIDIA CUDA", "Lokale GPU-Beschleunigung"),
            (BackendType.ROCM, "AMD ROCm", "AMD GPU-Beschleunigung"),
            (BackendType.VLLM, "vLLM Server", "Optimierte Server-Inference"),
            (BackendType.OPENAI_API, "OpenAI API", "Cloud-basierte Inference"),
            (BackendType.CPU_LLAMA_CPP, "llama.cpp CPU", "CPU-only Fallback"),
        ]
        
        fallback_chain = []
        
        for backend_type, name, reason in priority:
            if self._available_backends.get(backend_type, False):
                config = self._get_backend_config(backend_type)
                
                # Baue Fallback-Chain
                for bt, _, _ in priority:
                    if bt != backend_type and self._available_backends.get(bt, False):
                        fallback_chain.append(bt)
                
                return BackendRecommendation(
                    backend_type=backend_type,
                    backend_name=name,
                    confidence=0.95 if backend_type in [BackendType.CUDA, BackendType.ROCM] else 0.8,
                    reason=reason,
                    config=config,
                    fallback_chain=fallback_chain,
                )
        
        # Kein Backend verfügbar
        return BackendRecommendation(
            backend_type=BackendType.CPU_LLAMA_CPP,
            backend_name="llama.cpp CPU (nicht installiert)",
            confidence=0.0,
            reason="Kein Backend verfügbar. Bitte llama.cpp installieren oder API-Key setzen.",
            config={},
            fallback_chain=[],
        )
    
    def _get_backend_config(self, backend_type: BackendType) -> Dict[str, Any]:
        """Erstellt Backend-spezifische Konfiguration."""
        if backend_type == BackendType.CUDA:
            return {
                "device": "cuda",
                "gpu_layers": -1,  # Alle Layers auf GPU
                "batch_size": self._optimal_batch_size(),
            }
        
        elif backend_type == BackendType.ROCM:
            return {
                "device": "rocm",
                "gpu_layers": -1,
                "batch_size": self._optimal_batch_size(),
            }
        
        elif backend_type == BackendType.CPU_LLAMA_CPP:
            import multiprocessing
            return {
                "threads": multiprocessing.cpu_count(),
                "context_size": 4096,  # Konservativer für CPU
                "gpu_layers": 0,
            }
        
        elif backend_type == BackendType.OPENAI_API:
            return {
                "api_key": os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY"),
                "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                "model": os.getenv("GLITCHHUNTER_MODEL", "gpt-4"),
            }
        
        elif backend_type == BackendType.VLLM:
            return {
                "url": os.getenv("VLLM_URL", "http://localhost:8000"),
                "model": os.getenv("VLLM_MODEL", ""),
            }
        
        return {}
    
    def _optimal_batch_size(self) -> int:
        """Berechnet optimale Batch-Größe basierend auf VRAM."""
        if not self.profile or not self.profile.vram_gb:
            return 1
        
        # Heuristik: Je mehr VRAM, desto größere Batches
        vram = self.profile.vram_gb
        if vram >= 24:
            return 8
        elif vram >= 16:
            return 4
        elif vram >= 8:
            return 2
        else:
            return 1
    
    def get_system_report(self) -> Dict[str, Any]:
        """Generiert einen detaillierten System-Report."""
        if not self.profile:
            self.detect()
        
        return {
            "hardware": {
                "cpu_cores": self.profile.cpu_cores if self.profile else None,
                "ram_gb": self.profile.ram_gb if self.profile else None,
                "vram_gb": self.profile.vram_gb if self.profile else None,
                "gpus": self.profile.gpus if self.profile else [],
            },
            "backends": {
                backend.name: available
                for backend, available in self._available_backends.items()
            },
            "recommendation": self._select_backend().__dict__ if self.profile else None,
        }


def detect_hardware() -> BackendRecommendation:
    """
    Convenience-Funktion für Hardware-Detection.
    
    Returns:
        BackendRecommendation
    """
    detector = AutoDetector()
    return detector.detect()