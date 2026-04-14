#!/bin/bash
#
# Start GlitchHunter for Stack B (RTX 3090, 24GB VRAM)
#
# This script configures and starts GlitchHunter with settings
# optimized for NVIDIA RTX 3090 with 24GB VRAM.
#
# Features:
# - Parallel execution mode
# - Full security scanning
# - Qwen3.5-27B + DeepSeek-V3.2-Small models
# - Maximum VRAM utilization
#
# Usage: ./run_stack_b.sh [options]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "  GlitchHunter - Stack B (RTX 3090)    "
echo "========================================"
echo ""

# Set hardware profile
export GLITCHHUNTER_STACK="stack_b"
export GLITCHHUNTER_MODE="parallel"

# Model paths
export MODEL_ANALYZER="$PROJECT_DIR/models/qwen3.5-27b-instruct-q4_k_m.gguf"
export MODEL_VERIFIER="$PROJECT_DIR/models/deepseek-v3.2-small-q4_k_m.gguf"

# Check models exist
if [ ! -f "$MODEL_ANALYZER" ]; then
    echo "ERROR: Analyzer model not found: $MODEL_ANALYZER"
    echo "Run: python scripts/download_models.py --stack-b"
    exit 1
fi

if [ ! -f "$MODEL_VERIFIER" ]; then
    echo "ERROR: Verifier model not found: $MODEL_VERIFIER"
    echo "Run: python scripts/download_models.py --stack-b"
    exit 1
fi

echo "Hardware Profile: Stack B (RTX 3090, 24GB)"
echo "Execution Mode: Parallel"
echo ""
echo "Models:"
echo "  Analyzer: Qwen3.5-27B"
echo "  Verifier: DeepSeek-V3.2-Small"
echo ""

# Set CUDA options for 24GB VRAM
export CUDA_VISIBLE_DEVICES="0"
export GGML_CUDA_ENABLE="1"
export GGML_CUDA_MAIN_DEVICE="0"

# Aggressive memory settings for 24GB
export LLAMA_CPP_N_CTX="16384"
export LLAMA_CPP_N_GPU_LAYERS="50"
export LLAMA_CPP_N_THREADS="12"

# Enable all features for Stack B
export GLITCHHUNTER_PARALLEL_INFERENCE="true"
export GLITCHHUNTER_DEEP_SECURITY_SCAN="true"
export GLITCHHUNTER_MULTI_MODEL_CONSENSUS="true"
export GLITCHHUNTER_AST_ANALYSIS="true"
export GLITCHHUNTER_COMPLEXITY_CHECK="true"
export GLITCHHUNTER_BASIC_SECURITY="true"
export GLITCHHUNTER_PATCH_GENERATION="true"
export GLITCHHUNTER_SANDBOX_EXECUTION="true"

echo "Configuration:"
echo "  Context Length: $LLAMA_CPP_N_CTX"
echo "  GPU Layers: $LLAMA_CPP_N_GPU_LAYERS"
echo "  CPU Threads: $LLAMA_CPP_N_THREADS"
echo ""

# Parse command line arguments
COMMAND="${1:-api}"

case "$COMMAND" in
    api)
        echo "Starting API server..."
        echo ""
        cd "$PROJECT_DIR"
        python -m src.api.server
        ;;
    
    analyze)
        REPO_PATH="${2:-.}"
        echo "Starting analysis for: $REPO_PATH"
        echo ""
        cd "$PROJECT_DIR"
        python -c "
from src.agent.state_machine import build_workflow
workflow = build_workflow()
result = workflow.run('$REPO_PATH')
print('Analysis complete!')
print(f'State: {result.get(\"current_state\", \"unknown\")}')
print(f'Errors: {result.get(\"errors\", [])}')
"
        ;;
    
    check)
        echo "Running hardware check..."
        echo ""
        cd "$PROJECT_DIR"
        python -c "
from src.hardware.detector import HardwareDetector
detector = HardwareDetector()
profile = detector.detect()
print(f'Detected Stack: {profile.stack_type.value}')
print(f'GPU Name: {detector.get_gpu_name() or \"Unknown\"}')
print(f'VRAM: {profile.vram_limit} GB')
print(f'Mode: {profile.mode.value}')
detector.shutdown()
"
        ;;
    
    download)
        echo "Downloading Stack B models..."
        echo ""
        python "$SCRIPT_DIR/download_models.py" --stack-b
        ;;
    
    *)
        echo "Usage: $0 {api|analyze [repo_path]|check|download}"
        echo ""
        echo "Commands:"
        echo "  api              Start the API server"
        echo "  analyze [path]   Analyze a repository"
        echo "  check            Check hardware detection"
        echo "  download         Download required models"
        exit 1
        ;;
esac

echo ""
echo "Done!"
