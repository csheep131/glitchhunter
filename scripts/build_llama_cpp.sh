#!/bin/bash
#
# Build llama-cpp-turboquant-cuda for GlitchHunter
#
# This script builds the standalone llama-server with TurboQuant support
# optimized for NVIDIA GPUs (Compute Capability 8.6 for RTX 3060/3090).
#
# Repository: https://github.com/spiritbuun/llama-cpp-turboquant-cuda.git
# Branch: feature/turboquant-kv-cache
#

set -e

# Get project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "===================================================="
echo "  Building llama-cpp-turboquant-cuda with FA/Turbo  "
echo "===================================================="

# Get build path from config.yaml or use default
LLAMA_TOOLS_PATH=$(grep "llama_tools_path:" "$PROJECT_DIR/config.yaml" | awk '{print $2}' | tr -d '"')
LLAMA_TOOLS_PATH=${LLAMA_TOOLS_PATH:-"/home/schaf/tools/llama-cpp-turboquant-cuda"}

echo "Target directory: $LLAMA_TOOLS_PATH"

# Check dependencies
if ! command -v nvcc &> /dev/null; then
    echo "ERROR: CUDA (nvcc) not found. Please install CUDA Toolkit."
    exit 1
fi

if ! command -v cmake &> /dev/null; then
    echo "ERROR: cmake not found. Please install cmake."
    exit 1
fi

# Clone repository if needed
if [ ! -d "$LLAMA_TOOLS_PATH" ]; then
    echo "Cloning repository..."
    git clone https://github.com/spiritbuun/llama-cpp-turboquant-cuda.git "$LLAMA_TOOLS_PATH"
else
    echo "Directory exists. Updating..."
fi

cd "$LLAMA_TOOLS_PATH"

# Checkout branch
echo "Checking out feature/turboquant-kv-cache..."
git checkout feature/turboquant-kv-cache

# Check if build already exists and binary is present
if [ -f "build/bin/llama-server" ]; then
    echo "Build already exists and llama-server found."
    
    if [ "$BATCH_MODE" = "1" ]; then
        echo "BATCH_MODE enabled: Skipping re-build."
        exit 0
    fi

    read -p "Do you want to re-build? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping build."
        exit 0
    fi
fi

# Build
echo "Preparing build directory..."
rm -rf build
mkdir build
cd build

echo "Configuring with CMake..."
cmake .. \
  -DGGML_CUDA=ON \
  -DGGML_NATIVE=ON \
  -DGGML_CUDA_FA=ON \
  -DGGML_CUDA_FA_ALL_QUANTS=ON \
  -DCMAKE_BUILD_TYPE=Release

echo "Compiling (using all available cores)..."
cmake --build . -j$(nproc)

echo ""
echo "========================================"
echo "  Build complete!                       "
echo "  Binary: $LLAMA_TOOLS_PATH/build/bin/llama-server"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Run: ./scripts/run_stack_a.sh fix"
echo ""
