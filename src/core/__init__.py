"""
Core module for GlitchHunter.

Provides fundamental configuration, logging, and exception handling
used across all modules.

Exports:
    - Config: Main configuration class
    - LoggingConfig: Logging configuration (from config module)
    - GlitchHunterException: Base exception class
"""

from .config import Config, LoggingConfig
from .logging_config import setup_logging
from .exceptions import (
    GlitchHunterException,
    HardwareDetectionError,
    ModelLoadError,
    PatchApplyError,
    EscalationError,
    MCPConnectionError,
)

__all__ = [
    "Config",
    "LoggingConfig",
    "setup_logging",
    "GlitchHunterException",
    "HardwareDetectionError",
    "ModelLoadError",
    "PatchApplyError",
    "EscalationError",
    "MCPConnectionError",
]
