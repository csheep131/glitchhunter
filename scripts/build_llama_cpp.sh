#!/bin/bash
#
# Build llama-cpp-python with GPU support for GlitchHunter
#
# This script builds llama-cpp-python from source with CUDA acceleration
# optimized for NVIDIA GPUs (Compute Capability 8.6 for RTX 3060/3090)
#
# Usage: ./build_llama_cpp.sh
#

set -e

echo "========================================"
echo "  Building llama-cpp-python with CUDA  "
echo "========================================"

# Configuration
export CMAKE_ARGS="-DGGML_CUDA=on \
    -DCUDA_ARCHITECTURES=86 \
    -DGGML_CUDA_FA=on \
    -DGGML_CUDA_F16=on \
    -DGGML_CUDA_GRAPH_OPT=on \
    -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc"

export FORCE_CMAKE=1

# Check for CUDA
if ! command -v nvcc &> /dev/null; then
    echo "ERROR: CUDA not found. Please install CUDA Toolkit."
    echo "Download from: https://developer.nvidia.com/cuda-downloads"
    exit 1
fi

echo "CUDA found: $(nvcc --version | head -n1)"

# Check for CUDA compute capability
echo ""
echo "Target CUDA Architecture: 86 (RTX 3060/3090)"
echo ""

# Uninstall existing installation
echo "Removing existing llama-cpp-python installation..."
pip uninstall -y llama-cpp-python 2>/dev/null || true

# Install build dependencies
echo ""
echo "Installing build dependencies..."
pip install --upgrade pip setuptools wheel cmake ninja

# Install llama-cpp-python with CUDA support
echo ""
echo "Building llama-cpp-python with CUDA support..."
echo "This may take 10-30 minutes depending on your system..."
echo ""

CMAKE_ARGS="$CMAKE_ARGS" pip install --no-cache-dir llama-cpp-python

# Verify installation
echo ""
echo "Verifying installation..."
python -c "import llama_cpp; print(f'llama-cpp-python version: {llama_cpp.__version__}')"

echo ""
echo "========================================"
echo "  Build complete!                       "
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Download models using: python scripts/download_models.py"
echo "2. Start the API server: python -m src.api.server"
echo ""
