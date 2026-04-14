"""
Hardware detection and management module for GlitchHunter.

Provides automatic detection of GPU hardware and selection of appropriate
hardware profiles (Stack A or Stack B) based on available VRAM.

Exports:
    - HardwareDetector: Main class for hardware detection
    - HardwareProfile: Dataclass representing hardware configuration
    - VRAMManager: Manages VRAM allocation for models
"""

from hardware.detector import HardwareDetector
from hardware.profiles import HardwareProfile, StackType
from hardware.vram_manager import VRAMManager

__all__ = [
    "HardwareDetector",
    "HardwareProfile",
    "StackType",
    "VRAMManager",
]
