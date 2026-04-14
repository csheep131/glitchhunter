"""
Tests for HardwareDetector.

Unit tests for hardware detection functionality with mocked pynvml.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hardware.detector import HardwareDetector
from hardware.profiles import StackType


class MockNvmlDevice:
    """Mock NVML device handle."""

    def __init__(self, vram_gb: float, name: str = "NVIDIA GeForce RTX 3090") -> None:
        self.vram_gb = vram_gb
        self.name = name

    def get_memory_info(self) -> MagicMock:
        """Mock memory info."""
        info = MagicMock()
        info.total = int(self.vram_gb * 1024**3)
        return info

    def get_name(self) -> bytes:
        """Mock device name."""
        return self.name.encode("utf-8")

    def get_cuda_compute_capability(self) -> tuple:
        """Mock CUDA compute capability."""
        return (8, 6)


class TestHardwareDetector:
    """Test cases for HardwareDetector."""

    def test_detect_with_nvml(self) -> None:
        """Test detection when pynvml is available."""
        mock_device = MockNvmlDevice(vram_gb=24.0)

        with patch("src.hardware.detector.pynvml") as mock_pynvml:
            mock_pynvml.nvmlInit = MagicMock()
            mock_pynvml.nvmlDeviceGetCount = MagicMock(return_value=1)
            mock_pynvml.nvmlDeviceGetHandleByIndex = MagicMock(return_value=mock_device)
            mock_pynvml.nvmlDeviceGetMemoryInfo = MagicMock(
                side_effect=lambda h: mock_device.get_memory_info()
            )
            mock_pynvml.nvmlDeviceGetName = MagicMock(
                side_effect=lambda h: mock_device.get_name()
            )
            mock_pynvml.nvmlDeviceGetCudaComputeCapability = MagicMock(
                side_effect=lambda h: mock_device.get_cuda_compute_capability()
            )

            detector = HardwareDetector()
            profile = detector.detect()

            assert profile.stack_type == StackType.STACK_B
            assert profile.vram_limit == 24
            detector.shutdown()

    def test_detect_insufficient_vram(self) -> None:
        """Test detection with insufficient VRAM for Stack B."""
        mock_device = MockNvmlDevice(vram_gb=8.0, name="NVIDIA GeForce GTX 3060")

        with patch("src.hardware.detector.pynvml") as mock_pynvml:
            mock_pynvml.nvmlInit = MagicMock()
            mock_pynvml.nvmlDeviceGetCount = MagicMock(return_value=1)
            mock_pynvml.nvmlDeviceGetHandleByIndex = MagicMock(return_value=mock_device)
            mock_pynvml.nvmlDeviceGetMemoryInfo = MagicMock(
                side_effect=lambda h: mock_device.get_memory_info()
            )

            detector = HardwareDetector()
            profile = detector.detect()

            assert profile.stack_type == StackType.STACK_A
            assert profile.vram_limit == 8
            detector.shutdown()

    def test_detect_without_nvml(self) -> None:
        """Test detection when pynvml is not available."""
        with patch.dict(sys.modules, {"pynvml": None}):
            detector = HardwareDetector()
            profile = detector.detect()

            # Should fallback to Stack A
            assert profile.stack_type == StackType.STACK_A
            detector.shutdown()

    def test_detect_pynvml_import_error(self) -> None:
        """Test detection when pynvml import fails."""
        with patch("src.hardware.detector.pynvml", side_effect=ImportError):
            detector = HardwareDetector()
            profile = detector.detect()

            assert profile.stack_type == StackType.STACK_A

    def test_detect_pynvml_init_error(self) -> None:
        """Test detection when pynvml initialization fails."""
        with patch("src.hardware.detector.pynvml") as mock_pynvml:
            mock_pynvml.nvmlInit = MagicMock(side_effect=Exception("Init failed"))

            detector = HardwareDetector()
            profile = detector.detect()

            assert profile.stack_type == StackType.STACK_A

    def test_get_gpu_name(self) -> None:
        """Test GPU name retrieval."""
        mock_device = MockNvmlDevice(vram_gb=24.0)

        with patch("src.hardware.detector.pynvml") as mock_pynvml:
            mock_pynvml.nvmlInit = MagicMock()
            mock_pynvml.nvmlDeviceGetCount = MagicMock(return_value=1)
            mock_pynvml.nvmlDeviceGetHandleByIndex = MagicMock(return_value=mock_device)
            mock_pynvml.nvmlDeviceGetName = MagicMock(
                return_value=mock_device.get_name()
            )

            detector = HardwareDetector()
            detector.detect()

            gpu_name = detector.get_gpu_name(0)
            assert gpu_name == "NVIDIA GeForce RTX 3090"
            detector.shutdown()

    def test_get_gpu_name_invalid_index(self) -> None:
        """Test GPU name retrieval with invalid index."""
        with patch("src.hardware.detector.pynvml") as mock_pynvml:
            mock_pynvml.nvmlInit = MagicMock()
            mock_pynvml.nvmlDeviceGetCount = MagicMock(return_value=1)

            detector = HardwareDetector()
            detector.detect()

            gpu_name = detector.get_gpu_name(5)  # Invalid index
            assert gpu_name is None
            detector.shutdown()

    def test_get_cuda_compute_capability(self) -> None:
        """Test CUDA compute capability retrieval."""
        mock_device = MockNvmlDevice(vram_gb=24.0)

        with patch("src.hardware.detector.pynvml") as mock_pynvml:
            mock_pynvml.nvmlInit = MagicMock()
            mock_pynvml.nvmlDeviceGetCount = MagicMock(return_value=1)
            mock_pynvml.nvmlDeviceGetHandleByIndex = MagicMock(return_value=mock_device)
            mock_pynvml.nvmlDeviceGetCudaComputeCapability = MagicMock(
                return_value=(8, 6)
            )

            detector = HardwareDetector()
            detector.detect()

            cuda = detector.get_cuda_compute_capability(0)
            assert cuda == "8.6"
            detector.shutdown()

    def test_context_manager(self) -> None:
        """Test context manager usage."""
        with patch("src.hardware.detector.pynvml") as mock_pynvml:
            mock_pynvml.nvmlInit = MagicMock()
            mock_pynvml.nvmlShutdown = MagicMock()
            mock_pynvml.nvmlDeviceGetCount = MagicMock(return_value=0)

            with HardwareDetector() as detector:
                profile = detector.detect()
                assert profile.stack_type == StackType.STACK_A

            mock_pynvml.nvmlShutdown.assert_called_once()

    def test_multiple_gpus(self) -> None:
        """Test detection with multiple GPUs."""
        device1 = MockNvmlDevice(vram_gb=8.0, name="GTX 3060")
        device2 = MockNvmlDevice(vram_gb=24.0, name="RTX 3090")

        with patch("src.hardware.detector.pynvml") as mock_pynvml:
            mock_pynvml.nvmlInit = MagicMock()
            mock_pynvml.nvmlDeviceGetCount = MagicMock(return_value=2)
            mock_pynvml.nvmlDeviceGetHandleByIndex = MagicMock(
                side_effect=lambda i: [device1, device2][i]
            )
            mock_pynvml.nvmlDeviceGetMemoryInfo = MagicMock(
                side_effect=lambda h: h.get_memory_info()
            )

            detector = HardwareDetector()
            profile = detector.detect()

            # Should select Stack B due to combined VRAM (32GB)
            assert profile.stack_type == StackType.STACK_B
            detector.shutdown()
