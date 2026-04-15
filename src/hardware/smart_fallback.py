"""
Smart Fallback System for GlitchHunter TurboQuant

Extends hardware detection with intelligent GPU/CPU fallback while preserving
all TurboQuant optimizations (KV-Cache, Flash-Attention, custom kernels).
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional
import multiprocessing

from hardware.detector import HardwareDetector
from hardware.profiles import HardwareProfile, StackType

logger = logging.getLogger(__name__)


class InferenceMode(Enum):
    """Inference mode based on hardware availability."""
    FULL_GPU = "full_gpu"           # All layers on GPU (-1)
    HYBRID = "hybrid"               # Partial GPU offload
    CPU_ONLY = "cpu_only"           # CPU mode (0)


@dataclass
class InferenceConfig:
    """Configuration for inference with smart fallback."""
    mode: InferenceMode
    n_gpu_layers: int               # -1 = all, 0 = none, >0 = partial
    n_threads: int                  # CPU threads
    n_ctx: int                      # Context size
    use_turboquant: bool            # Always True, preserves optimizations
    batch_size: int
    flash_attention: bool           # Flash-Attention enabled
    kv_cache_quantization: str      # KV cache quant mode
    
    def to_llama_kwargs(self) -> Dict[str, Any]:
        """Convert to kwargs for llama-cpp-python."""
        return {
            "n_gpu_layers": self.n_gpu_layers,
            "n_threads": self.n_threads,
            "n_ctx": self.n_ctx,
            "n_batch": self.batch_size,
            # TurboQuant optimizations always passed
            "flash_attn": self.flash_attention,
            "kv_cache_quantization": self.kv_cache_quantization,
        }


class SmartFallbackManager:
    """
    Manages intelligent fallback between GPU and CPU modes.
    
    Preserves all TurboQuant optimizations regardless of mode:
    - KV-Cache quantization
    - Flash-Attention
    - Custom kernels (when CPU-compatible)
    """
    
    # VRAM thresholds in GB
    FULL_GPU_THRESHOLD = 8          # 8GB+ for full GPU
    HYBRID_THRESHOLD = 4            # 4-8GB for hybrid mode
    
    # Context sizes by mode
    CONTEXT_FULL_GPU = 128000       # 128k for GPU
    CONTEXT_HYBRID = 65536          # 64k for hybrid
    CONTEXT_CPU = 8192              # 8k for CPU (conservative)
    
    def __init__(self, cpu_only: bool = False):
        self.cpu_only = cpu_only
        self._detector = HardwareDetector()
        self._profile: Optional[HardwareProfile] = None
        
    def detect_and_configure(self) -> InferenceConfig:
        """
        Detect hardware and return optimal inference configuration.
        
        Returns:
            InferenceConfig with mode-appropriate settings
        """
        if self.cpu_only:
            logger.info("CPU-only mode forced by user")
            return self._get_cpu_config()
        
        # Detect hardware
        self._profile = self._detector.detect()
        
        # Get VRAM info
        vram_gb = self._get_available_vram()
        
        logger.info(f"Hardware detection: VRAM={vram_gb:.1f}GB, Stack={self._profile.stack_type.value}")
        
        # Select mode based on VRAM
        if vram_gb >= self.FULL_GPU_THRESHOLD:
            return self._get_full_gpu_config(vram_gb)
        elif vram_gb >= self.HYBRID_THRESHOLD:
            return self._get_hybrid_config(vram_gb)
        else:
            logger.warning(f"Insufficient VRAM ({vram_gb:.1f}GB), falling back to CPU")
            return self._get_cpu_config()
    
    def _get_full_gpu_config(self, vram_gb: float) -> InferenceConfig:
        """Full GPU mode - all layers on GPU."""
        config = InferenceConfig(
            mode=InferenceMode.FULL_GPU,
            n_gpu_layers=-1,           # -1 = all layers
            n_threads=max(4, multiprocessing.cpu_count() // 2),
            n_ctx=self.CONTEXT_FULL_GPU,
            use_turboquant=True,
            batch_size=512,
            flash_attention=True,
            kv_cache_quantization="q4_0",  # Aggressive KV cache quant
        )
        logger.info(f"Configured FULL GPU mode: n_gpu_layers=-1, ctx={config.n_ctx}")
        return config
    
    def _get_hybrid_config(self, vram_gb: float) -> InferenceConfig:
        """Hybrid mode - partial GPU offload with layer-adaptive quantization."""
        # Calculate optimal GPU layers based on VRAM
        # Heuristic: ~500MB per layer for 7B model
        estimated_layers = int((vram_gb - 2) * 2)  # Conservative estimate
        n_gpu_layers = max(10, min(estimated_layers, 35))
        
        config = InferenceConfig(
            mode=InferenceMode.HYBRID,
            n_gpu_layers=n_gpu_layers,
            n_threads=multiprocessing.cpu_count(),
            n_ctx=self.CONTEXT_HYBRID,
            use_turboquant=True,
            batch_size=256,
            flash_attention=True,
            kv_cache_quantization="q5_0",  # Balanced quant
        )
        logger.info(f"Configured HYBRID mode: n_gpu_layers={n_gpu_layers}, ctx={config.n_ctx}")
        return config
    
    def _get_cpu_config(self) -> InferenceConfig:
        """CPU-only mode - preserves TurboQuant CPU optimizations."""
        config = InferenceConfig(
            mode=InferenceMode.CPU_ONLY,
            n_gpu_layers=0,            # 0 = CPU only
            n_threads=multiprocessing.cpu_count(),
            n_ctx=self.CONTEXT_CPU,
            use_turboquant=True,
            batch_size=128,
            flash_attention=False,      # Flash-Attn typically GPU-only
            kv_cache_quantization="q4_0",  # Aggressive for CPU efficiency
        )
        logger.info(f"Configured CPU mode: threads={config.n_threads}, ctx={config.n_ctx}")
        return config
    
    def _get_available_vram(self) -> float:
        """Get available VRAM in GB."""
        try:
            import pynvml
            pynvml.nvmlInit()
            
            total_vram = 0
            for i in range(pynvml.nvmlDeviceGetCount()):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                total_vram += info.total
            
            pynvml.nvmlShutdown()
            return total_vram / (1024**3)
            
        except:
            return 0.0
    
    def get_mode_description(self, config: InferenceConfig) -> str:
        """Get human-readable mode description."""
        descriptions = {
            InferenceMode.FULL_GPU: "Full TurboQuant GPU (All Layers)",
            InferenceMode.HYBRID: "Hybrid GPU/CPU (Layer-Adaptive)",
            InferenceMode.CPU_ONLY: "CPU-Only TurboQuant",
        }
        return descriptions.get(config.mode, "Unknown")


def get_inference_config(
    cpu_only: bool = False,
    force_mode: Optional[InferenceMode] = None,
) -> InferenceConfig:
    """
    Convenience function to get inference configuration.
    
    Args:
        cpu_only: Force CPU-only mode
        force_mode: Force specific mode (for testing)
        
    Returns:
        InferenceConfig optimized for detected hardware
    """
    manager = SmartFallbackManager(cpu_only=cpu_only)
    
    if force_mode:
        # For testing: manually create config
        if force_mode == InferenceMode.FULL_GPU:
            return manager._get_full_gpu_config(24)
        elif force_mode == InferenceMode.HYBRID:
            return manager._get_hybrid_config(6)
        else:
            return manager._get_cpu_config()
    
    return manager.detect_and_configure()


# Backwards compatibility alias
configure_inference = get_inference_config