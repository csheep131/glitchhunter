"""
VRAM management module for GlitchHunter.

Manages VRAM allocation for models, tracking usage and ensuring models
fit within available VRAM limits.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

from .profiles import HardwareProfile, ExecutionMode

logger = logging.getLogger(__name__)

# VRAM reservation for system overhead (in GB)
SYSTEM_VRAM_RESERVATION = 1.0

# VRAM safety margin (percentage)
VRAM_SAFETY_MARGIN = 0.1  # 10%


@dataclass
class VRAMAllocation:
    """Represents a VRAM allocation for a model."""

    model_name: str
    allocated_vram_gb: float
    context_length: int
    batch_size: int


class VRAMManager:
    """
    Manages VRAM allocation and tracking for model inference.

    Tracks allocated VRAM, ensures models fit within limits, and provides
    methods for sequential vs. parallel execution modes.

    Attributes:
        profile: Hardware profile with VRAM limits
        total_vram_gb: Total available VRAM in GB
        allocated_vram_gb: Currently allocated VRAM in GB
        allocations: Dictionary of active VRAM allocations
    """

    def __init__(self, profile: HardwareProfile) -> None:
        """
        Initialize VRAM manager with a hardware profile.

        Args:
            profile: Hardware profile containing VRAM limits
        """
        self._profile = profile
        self._total_vram_gb = profile.available_vram_gb
        self._allocated_vram_gb = 0.0
        self._allocations: Dict[str, VRAMAllocation] = {}
        self._lock = False  # Simple lock for thread safety

        logger.debug(
            f"VRAMManager initialized for {profile.name} "
            f"({self._total_vram_gb:.1f}GB available)"
        )

    @property
    def profile(self) -> HardwareProfile:
        """Get the hardware profile."""
        return self._profile

    @property
    def total_vram_gb(self) -> float:
        """Get total available VRAM in GB."""
        return self._total_vram_gb

    @property
    def allocated_vram_gb(self) -> float:
        """Get currently allocated VRAM in GB."""
        return self._allocated_vram_gb

    @property
    def available_vram_gb(self) -> float:
        """Get currently available (unallocated) VRAM in GB."""
        return max(0.0, self._total_vram_gb - self._allocated_vram_gb)

    @property
    def utilization_percent(self) -> float:
        """Get current VRAM utilization as percentage."""
        if self._total_vram_gb == 0:
            return 0.0
        return (self._allocated_vram_gb / self._total_vram_gb) * 100

    def is_sequential_mode(self) -> bool:
        """
        Check if running in sequential mode.

        Returns:
            True if sequential mode (Stack A), False if parallel (Stack B)
        """
        return self._profile.mode == ExecutionMode.SEQUENTIAL

    def allocate_for_model(
        self,
        model_name: str,
        required_vram_gb: float,
        context_length: int,
        batch_size: int = 1,
    ) -> bool:
        """
        Allocate VRAM for a model.

        Args:
            model_name: Unique name for the model
            required_vram_gb: Required VRAM in GB
            context_length: Context length for the model
            batch_size: Batch size for inference

        Returns:
            True if allocation successful, False if insufficient VRAM

        Raises:
            ValueError: If model_name is already allocated
        """
        if self._lock:
            logger.warning("VRAMManager is locked, allocation delayed")
            return False

        if model_name in self._allocations:
            raise ValueError(f"Model '{model_name}' is already allocated")

        # Apply safety margin
        required_with_margin = required_vram_gb * (1 + VRAM_SAFETY_MARGIN)

        if required_with_margin > self.available_vram_gb:
            logger.warning(
                f"Insufficient VRAM for '{model_name}': "
                f"requires {required_with_margin:.2f}GB, "
                f"only {self.available_vram_gb:.2f}GB available"
            )
            return False

        # Allocate
        allocation = VRAMAllocation(
            model_name=model_name,
            allocated_vram_gb=required_with_margin,
            context_length=context_length,
            batch_size=batch_size,
        )
        self._allocations[model_name] = allocation
        self._allocated_vram_gb += required_with_margin

        logger.info(
            f"Allocated {required_with_margin:.2f}GB VRAM for '{model_name}' "
            f"({self.utilization_percent:.1f}% utilization)"
        )

        return True

    def release_for_model(self, model_name: str) -> bool:
        """
        Release VRAM allocated for a model.

        Args:
            model_name: Name of the model to release

        Returns:
            True if released successfully, False if model not found
        """
        if model_name not in self._allocations:
            logger.warning(f"Cannot release '{model_name}': not allocated")
            return False

        allocation = self._allocations[model_name]
        self._allocated_vram_gb -= allocation.allocated_vram_gb
        del self._allocations[model_name]

        logger.info(
            f"Released {allocation.allocated_vram_gb:.2f}GB VRAM from '{model_name}' "
            f"({self.utilization_percent:.1f}% utilization)"
        )

        return True

    def is_allocated(self, model_name: str) -> bool:
        """
        Check if a model has allocated VRAM.

        Args:
            model_name: Name of the model

        Returns:
            True if model has allocated VRAM
        """
        return model_name in self._allocations

    def get_allocation(self, model_name: str) -> Optional[VRAMAllocation]:
        """
        Get VRAM allocation details for a model.

        Args:
            model_name: Name of the model

        Returns:
            VRAMAllocation or None if not allocated
        """
        return self._allocations.get(model_name)

    def can_load_both_models(self) -> bool:
        """
        Check if both primary and secondary models can be loaded simultaneously.

        Returns:
            True if both models fit in VRAM
        """
        primary = self._profile.primary_model
        secondary = self._profile.secondary_model

        # Estimate VRAM requirements (rough approximation)
        # Actual calculation depends on model size and quantization
        primary_vram = self._estimate_model_vram(primary.context_length)
        secondary_vram = self._estimate_model_vram(secondary.context_length)

        total_required = primary_vram + secondary_vram
        return total_required <= self._total_vram_gb

    def _estimate_model_vram(self, context_length: int) -> float:
        """
        Estimate VRAM requirement for a model.

        Args:
            context_length: Context length for the model

        Returns:
            Estimated VRAM in GB
        """
        # Rough estimation based on context length
        # Actual calculation depends on model architecture and quantization
        base_vram = 2.0  # Base model weights (quantized)
        context_vram = (context_length / 1024) * 0.5  # 0.5GB per 1K context

        return base_vram + context_vram

    def get_available_vram(self) -> float:
        """
        Get currently available VRAM in GB.

        Returns:
            Available VRAM in GB
        """
        return self.available_vram_gb

    def clear_all_allocations(self) -> None:
        """Clear all VRAM allocations (use with caution)."""
        if self._allocations:
            logger.warning(f"Clearing {len(self._allocations)} VRAM allocations")
            self._allocations.clear()
            self._allocated_vram_gb = 0.0

    def get_status(self) -> dict:
        """
        Get VRAM manager status as dictionary.

        Returns:
            Dictionary with VRAM status information
        """
        return {
            "profile": self._profile.name,
            "total_vram_gb": self._total_vram_gb,
            "allocated_vram_gb": self._allocated_vram_gb,
            "available_vram_gb": self.available_vram_gb,
            "utilization_percent": self.utilization_percent,
            "mode": self._profile.mode.value,
            "active_allocations": len(self._allocations),
            "allocations": {
                name: {
                    "vram_gb": alloc.allocated_vram_gb,
                    "context_length": alloc.context_length,
                    "batch_size": alloc.batch_size,
                }
                for name, alloc in self._allocations.items()
            },
        }

    def __str__(self) -> str:
        """String representation of VRAM manager status."""
        status = self.get_status()
        return (
            f"VRAMManager({status['profile']}, "
            f"{status['allocated_vram_gb']:.1f}/{status['total_vram_gb']:.1f}GB "
            f"[{status['utilization_percent']:.1f}%])"
        )
