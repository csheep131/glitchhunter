"""
Hardware profile definitions for GlitchHunter.

Defines dataclasses and enums for representing different hardware configurations
(Stack A: GTX 3060 8GB, Stack B: RTX 3090 24GB).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class StackType(str, Enum):
    """Hardware stack type enumeration."""

    STACK_A = "stack_a"
    STACK_B = "stack_b"


class ExecutionMode(str, Enum):
    """Execution mode for inference."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


@dataclass(frozen=True)
class ModelConfig:
    """Configuration for a single model."""

    name: str
    path: str
    context_length: int
    n_gpu_layers: int
    n_threads: int
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40

    def __post_init__(self) -> None:
        """Validate model configuration."""
        if self.n_gpu_layers < 0:
            raise ValueError("n_gpu_layers must be non-negative")
        if self.n_threads < 1:
            raise ValueError("n_threads must be at least 1")
        if self.context_length < 1024:
            raise ValueError("context_length must be at least 1024")


@dataclass(frozen=True)
class SecurityConfig:
    """Security scan configuration."""

    enabled: bool
    level: str  # "lite" or "full"
    owasp_top10: bool
    api_security: bool
    attack_scenarios: bool

    def __post_init__(self) -> None:
        """Validate security configuration."""
        if self.level not in ("lite", "full"):
            raise ValueError("Security level must be 'lite' or 'full'")


@dataclass(frozen=True)
class InferenceConfig:
    """Inference engine configuration."""

    max_batch_size: int
    parallel_requests: bool
    turbo_quant: bool

    def __post_init__(self) -> None:
        """Validate inference configuration."""
        if self.max_batch_size < 1:
            raise ValueError("max_batch_size must be at least 1")


@dataclass(frozen=True)
class HardwareProfile:
    """
    Represents a complete hardware configuration profile.

    Attributes:
        stack_type: Type of hardware stack (A or B)
        name: Human-readable name (e.g., "GTX 3060")
        vram_limit: Total VRAM in GB
        cuda_compute: CUDA compute capability (e.g., "8.6")
        mode: Execution mode (sequential or parallel)
        primary_model: Main analyzer model configuration
        secondary_model: Verifier/helper model configuration
        security: Security scan configuration
        inference: Inference engine configuration
        features: Dictionary of enabled features
    """

    stack_type: StackType
    name: str
    vram_limit: int
    cuda_compute: str
    mode: ExecutionMode
    primary_model: ModelConfig
    secondary_model: ModelConfig
    security: SecurityConfig
    inference: InferenceConfig
    features: Dict[str, bool] = field(default_factory=dict)

    @property
    def is_parallel(self) -> bool:
        """Check if profile supports parallel execution."""
        return self.mode == ExecutionMode.PARALLEL

    @property
    def available_vram_gb(self) -> int:
        """Return available VRAM after reserving 1GB for system."""
        return max(0, self.vram_limit - 1)

    def has_feature(self, feature_name: str) -> bool:
        """Check if a specific feature is enabled."""
        return self.features.get(feature_name, False)


# Predefined hardware profiles

STACK_A_PROFILE = HardwareProfile(
    stack_type=StackType.STACK_A,
    name="GTX 3060",
    vram_limit=8,
    cuda_compute="8.6",
    mode=ExecutionMode.SEQUENTIAL,
    primary_model=ModelConfig(
        name="qwen3.5-9b",
        path="models/Qwen3.5-9B-Instruct-Q4_K_M.gguf",
        context_length=8192,
        n_gpu_layers=35,
        n_threads=8,
    ),
    secondary_model=ModelConfig(
        name="phi-4-mini",
        path="models/phi-4-mini-instruct.Q4_K_M.gguf",
        context_length=4096,
        n_gpu_layers=25,
        n_threads=6,
    ),
    security=SecurityConfig(
        enabled=True,
        level="lite",
        owasp_top10=True,
        api_security=False,
        attack_scenarios=False,
    ),
    inference=InferenceConfig(
        max_batch_size=1,
        parallel_requests=False,
        turbo_quant=True,
    ),
    features={
        "ast_analysis": True,
        "complexity_check": True,
        "basic_security": True,
        "patch_generation": True,
        "sandbox_execution": True,
        "parallel_inference": False,
        "deep_security_scan": False,
        "multi_model_consensus": False,
    },
)

STACK_B_PROFILE = HardwareProfile(
    stack_type=StackType.STACK_B,
    name="RTX 3090",
    vram_limit=24,
    cuda_compute="8.6",
    mode=ExecutionMode.PARALLEL,
    primary_model=ModelConfig(
        name="qwen3.5-27b",
        path="models/Qwen3.5-27B-Instruct-Q4_K_M.gguf",
        context_length=16384,
        n_gpu_layers=50,
        n_threads=12,
    ),
    secondary_model=ModelConfig(
        name="deepseek-v3.2-small",
        path="models/DeepSeek-V3.2-Small-Q4_K_M.gguf",
        context_length=8192,
        n_gpu_layers=40,
        n_threads=10,
    ),
    security=SecurityConfig(
        enabled=True,
        level="full",
        owasp_top10=True,
        api_security=True,
        attack_scenarios=True,
    ),
    inference=InferenceConfig(
        max_batch_size=4,
        parallel_requests=True,
        turbo_quant=True,
    ),
    features={
        "ast_analysis": True,
        "complexity_check": True,
        "basic_security": True,
        "patch_generation": True,
        "sandbox_execution": True,
        "parallel_inference": True,
        "deep_security_scan": True,
        "multi_model_consensus": True,
    },
)

# Profile lookup table
HARDWARE_PROFILES: Dict[StackType, HardwareProfile] = {
    StackType.STACK_A: STACK_A_PROFILE,
    StackType.STACK_B: STACK_B_PROFILE,
}


def get_profile(stack_type: StackType) -> HardwareProfile:
    """
    Get a hardware profile by stack type.

    Args:
        stack_type: The stack type to retrieve

    Returns:
        The corresponding HardwareProfile

    Raises:
        ValueError: If stack_type is not recognized
    """
    if stack_type not in HARDWARE_PROFILES:
        raise ValueError(f"Unknown stack type: {stack_type}")
    return HARDWARE_PROFILES[stack_type]
