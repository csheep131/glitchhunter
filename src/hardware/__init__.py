"""
Hardware detection and management module for GlitchHunter.

Provides automatic detection of GPU hardware and selection of appropriate
hardware profiles (Stack A or Stack B) based on available VRAM.

Exports:
    - HardwareDetector: Main class for hardware detection
    - HardwareProfile: Dataclass representing hardware configuration
    - VRAMManager: Manages VRAM allocation for models
    - SmartFallbackManager: Intelligent GPU/CPU fallback with TurboQuant
"""

from hardware.detector import HardwareDetector
from hardware.profiles import HardwareProfile, StackType
from hardware.vram_manager import VRAMManager
from hardware.smart_fallback import (
    SmartFallbackManager,
    InferenceMode,
    InferenceConfig,
    get_inference_config,
)

__all__ = [
    "HardwareDetector",
    "HardwareProfile",
    "StackType",
    "VRAMManager",
    "SmartFallbackManager",
    "InferenceMode",
    "InferenceConfig",
    "get_inference_config",
]