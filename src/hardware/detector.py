"""
Hardware detection module for GlitchHunter.

Automatically detects GPU hardware and selects the appropriate hardware profile
(Stack A or Stack B) based on available VRAM.
"""

import logging
from typing import Optional

from hardware.profiles import HardwareProfile, StackType, get_profile

logger = logging.getLogger(__name__)

# VRAM thresholds for stack selection (in GB)
STACK_A_MIN_VRAM = 6  # Minimum for Stack A (GTX 3060)
STACK_B_MIN_VRAM = 20  # Minimum for Stack B (RTX 3090)


class HardwareDetector:
    """
    Detects available GPU hardware and selects appropriate hardware profile.

    Uses pynvml (NVIDIA Management Library) to query GPU information including
    VRAM size, compute capability, and GPU name.

    Attributes:
        _initialized: Whether pynvml has been initialized
        _gpu_count: Number of detected GPUs
        _total_vram: Total VRAM across all GPUs in GB
    """

    def __init__(self) -> None:
        """Initialize the hardware detector."""
        self._initialized: bool = False
        self._gpu_count: int = 0
        self._total_vram: float = 0.0
        self._nvml_available: bool = False

    def detect(self) -> HardwareProfile:
        """
        Detect hardware and return the appropriate hardware profile.

        Returns:
            HardwareProfile for the detected hardware (Stack A or Stack B)

        Raises:
            HardwareDetectionError: If detection fails
        """
        try:
            self._initialize_nvml()
            vram_gb = self._get_total_vram_gb()

            logger.info(f"Detected {self._gpu_count} GPU(s) with {vram_gb:.1f}GB total VRAM")

            profile = self._select_profile(vram_gb)
            logger.info(f"Selected hardware profile: {profile.name} ({profile.stack_type.value})")

            return profile

        except Exception as e:
            logger.error(f"Hardware detection failed: {e}")
            # Fallback to Stack A (conservative)
            logger.warning("Falling back to Stack A (sequential mode)")
            return get_profile(StackType.STACK_A)

    def _initialize_nvml(self) -> None:
        """Initialize NVIDIA Management Library (pynvml)."""
        if self._initialized:
            return

        try:
            import pynvml

            pynvml.nvmlInit()
            self._gpu_count = pynvml.nvmlDeviceGetCount()
            self._initialized = True
            self._nvml_available = True
            logger.debug(f"pynvml initialized successfully, {self._gpu_count} GPU(s) found")

        except ImportError:
            logger.warning("pynvml not available, using CPU-only detection")
            self._nvml_available = False
            self._gpu_count = 0

        except Exception as e:
            logger.warning(f"pynvml initialization failed: {e}")
            self._nvml_available = False
            self._gpu_count = 0

    def _get_total_vram_gb(self) -> float:
        """
        Get total VRAM across all GPUs in GB.

        Returns:
            Total VRAM in GB
        """
        if not self._initialized or not self._nvml_available:
            # Fallback: assume no GPU
            return 0.0

        try:
            import pynvml

            total_vram_bytes = 0
            for i in range(self._gpu_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                total_vram_bytes += info.total

            # Convert bytes to GB
            return total_vram_bytes / (1024**3)

        except Exception as e:
            logger.error(f"Failed to get VRAM info: {e}")
            return 0.0

    def _select_profile(self, vram_gb: float) -> HardwareProfile:
        """
        Select hardware profile based on available VRAM.

        Args:
            vram_gb: Available VRAM in GB

        Returns:
            Appropriate HardwareProfile
        """
        if vram_gb >= STACK_B_MIN_VRAM:
            logger.info(f"VRAM {vram_gb:.1f}GB >= {STACK_B_MIN_VRAM}GB threshold → Stack B")
            return get_profile(StackType.STACK_B)

        if vram_gb >= STACK_A_MIN_VRAM:
            logger.info(f"VRAM {vram_gb:.1f}GB >= {STACK_A_MIN_VRAM}GB threshold → Stack A")
            return get_profile(StackType.STACK_A)

        # Not enough VRAM for any stack
        logger.warning(
            f"Insufficient VRAM: {vram_gb:.1f}GB < {STACK_A_MIN_VRAM}GB minimum. "
            "Using Stack A in CPU mode."
        )
        return get_profile(StackType.STACK_A)

    def get_gpu_name(self, index: int = 0) -> Optional[str]:
        """
        Get the name of a specific GPU.

        Args:
            index: GPU index (default: 0)

        Returns:
            GPU name or None if not available
        """
        if not self._initialized or not self._nvml_available:
            return None

        try:
            import pynvml

            if index >= self._gpu_count:
                return None

            handle = pynvml.nvmlDeviceGetHandleByIndex(index)
            return pynvml.nvmlDeviceGetName(handle).decode("utf-8")

        except Exception as e:
            logger.error(f"Failed to get GPU name: {e}")
            return None

    def get_cuda_compute_capability(self, index: int = 0) -> Optional[str]:
        """
        Get CUDA compute capability of a specific GPU.

        Args:
            index: GPU index (default: 0)

        Returns:
            CUDA compute capability string (e.g., "8.6") or None
        """
        if not self._initialized or not self._nvml_available:
            return None

        try:
            import pynvml

            if index >= self._gpu_count:
                return None

            handle = pynvml.nvmlDeviceGetHandleByIndex(index)
            major = pynvml.nvmlDeviceGetCudaComputeCapability(handle)[0]
            minor = pynvml.nvmlDeviceGetCudaComputeCapability(handle)[1]
            return f"{major}.{minor}"

        except Exception as e:
            logger.error(f"Failed to get CUDA compute capability: {e}")
            return None

    def shutdown(self) -> None:
        """Shutdown pynvml and release resources."""
        if self._initialized and self._nvml_available:
            try:
                import pynvml

                pynvml.nvmlShutdown()
                self._initialized = False
                logger.debug("pynvml shutdown complete")

            except Exception as e:
                logger.error(f"Error during pynvml shutdown: {e}")

    def __enter__(self) -> "HardwareDetector":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - ensure cleanup."""
        self.shutdown()
