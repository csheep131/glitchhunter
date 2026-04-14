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


def _make_mock_pynvml(devices=None, init_side_effect=None):
    """Create a mock pynvml module with configured devices."""
    mock = MagicMock()
    if init_side_effect:
        mock.nvmlInit = MagicMock(side_effect=init_side_effect)
    else:
        mock.nvmlInit = MagicMock()

    if devices is None:
        devices = []

    mock.nvmlDeviceGetCount = MagicMock(return_value=len(devices))
    mock.nvmlDeviceGetHandleByIndex = MagicMock(
        side_effect=lambda i: devices[i] if i < len(devices) else MagicMock()
    )
    mock.nvmlDeviceGetMemoryInfo = MagicMock(
        side_effect=lambda h: h.get_memory_info()
    )
    mock.nvmlDeviceGetName = MagicMock(
        side_effect=lambda h: h.get_name()
    )
    mock.nvmlDeviceGetCudaComputeCapability = MagicMock(
        side_effect=lambda h: h.get_cuda_compute_capability()
    )
    mock.nvmlShutdown = MagicMock()
    return mock


class TestHardwareDetector:
    """Test cases for HardwareDetector."""

    def test_detect_with_nvml(self) -> None:
        """Test detection when pynvml is available."""
        mock_device = MockNvmlDevice(vram_gb=24.0)
        mock_pynvml = _make_mock_pynvml(devices=[mock_device])

        with patch.dict(sys.modules, {"pynvml": mock_pynvml}):
            detector = HardwareDetector()
            profile = detector.detect()
            assert profile.stack_type == StackType.STACK_B
            assert profile.vram_limit == 24
            detector.shutdown()

    def test_detect_insufficient_vram(self) -> None:
        """Test detection with insufficient VRAM for Stack B."""
        mock_device = MockNvmlDevice(vram_gb=8.0, name="NVIDIA GeForce GTX 3060")
        mock_pynvml = _make_mock_pynvml(devices=[mock_device])

        with patch.dict(sys.modules, {"pynvml": mock_pynvml}):
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
            assert profile.stack_type == StackType.STACK_A
            detector.shutdown()

    def test_detect_pynvml_import_error(self) -> None:
        """Test detection when pynvml import fails."""
        with patch.dict(sys.modules, {"pynvml": None}):
            detector = HardwareDetector()
            profile = detector.detect()
            assert profile.stack_type == StackType.STACK_A

    def test_detect_pynvml_init_error(self) -> None:
        """Test detection when pynvml initialization fails."""
        mock_pynvml = _make_mock_pynvml(init_side_effect=Exception("Init failed"))

        with patch.dict(sys.modules, {"pynvml": mock_pynvml}):
            detector = HardwareDetector()
            profile = detector.detect()
            assert profile.stack_type == StackType.STACK_A

    def test_get_gpu_name(self) -> None:
        """Test GPU name retrieval."""
        mock_device = MockNvmlDevice(vram_gb=24.0)
        mock_pynvml = _make_mock_pynvml(devices=[mock_device])

        with patch.dict(sys.modules, {"pynvml": mock_pynvml}):
            detector = HardwareDetector()
            detector.detect()
            gpu_name = detector.get_gpu_name(0)
            assert gpu_name == "NVIDIA GeForce RTX 3090"
            detector.shutdown()

    def test_get_gpu_name_invalid_index(self) -> None:
        """Test GPU name retrieval with invalid index."""
        mock_device = MockNvmlDevice(vram_gb=24.0)
        mock_pynvml = _make_mock_pynvml(devices=[mock_device])

        with patch.dict(sys.modules, {"pynvml": mock_pynvml}):
            detector = HardwareDetector()
            detector.detect()
            gpu_name = detector.get_gpu_name(5)  # Invalid index
            assert gpu_name is None
            detector.shutdown()

    def test_get_cuda_compute_capability(self) -> None:
        """Test CUDA compute capability retrieval."""
        mock_device = MockNvmlDevice(vram_gb=24.0)
        mock_pynvml = _make_mock_pynvml(devices=[mock_device])

        with patch.dict(sys.modules, {"pynvml": mock_pynvml}):
            detector = HardwareDetector()
            detector.detect()
            cuda = detector.get_cuda_compute_capability(0)
            assert cuda == "8.6"
            detector.shutdown()

    def test_context_manager(self) -> None:
        """Test context manager usage."""
        mock_pynvml = _make_mock_pynvml(devices=[])

        with patch.dict(sys.modules, {"pynvml": mock_pynvml}):
            with HardwareDetector() as detector:
                profile = detector.detect()
                assert profile.stack_type == StackType.STACK_A

            mock_pynvml.nvmlShutdown.assert_called_once()

    def test_multiple_gpus(self) -> None:
        """Test detection with multiple GPUs."""
        device1 = MockNvmlDevice(vram_gb=8.0, name="GTX 3060")
        device2 = MockNvmlDevice(vram_gb=24.0, name="RTX 3090")
        mock_pynvml = _make_mock_pynvml(devices=[device1, device2])

        with patch.dict(sys.modules, {"pynvml": mock_pynvml}):
            detector = HardwareDetector()
            profile = detector.detect()
            # Should select Stack B due to combined VRAM (32GB)
            assert profile.stack_type == StackType.STACK_B
            detector.shutdown()
