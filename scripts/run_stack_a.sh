#!/bin/bash
#
# Start GlitchHunter for Stack A (GTX 3060, 8GB VRAM)
#
# This script configures and starts GlitchHunter with settings
# optimized for NVIDIA GTX 3060 with 8GB VRAM.
#
# Features:
# - Sequential execution mode
# - Security-Lite scanning
# - Qwen3.5-9B + Phi-4-mini models
# - Conservative VRAM usage
#
# Usage: ./run_stack_a.sh [options]
#

set -e

# Get script directory (zsh compatible)
if [ -n "${ZSH_VERSION:-}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${(%):-%x}")" && pwd)"
elif [ -n "${BASH_SOURCE:-}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
fi
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Activate virtual environment if it exists (sh compatible)
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    . "$PROJECT_DIR/venv/bin/activate"
elif [ -f "$PROJECT_DIR/.venv/bin/activate" ]; then
    . "$PROJECT_DIR/.venv/bin/activate"
fi

# Set PYTHONPATH for src imports
export PYTHONPATH="${PROJECT_DIR}/src:${PYTHONPATH:+:$PYTHONPATH}"

echo "========================================"
echo "  GlitchHunter - Stack A (GTX 3060)    "
echo "========================================"
echo ""

# Set hardware profile
export GLITCHHUNTER_STACK="stack_a"
export GLITCHHUNTER_MODE="sequential"

# Model paths (local)
export MODEL_ANALYZER="$HOME/stuff/offline_llm/models/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf"
export MODEL_VERIFIER="$HOME/stuff/offline_llm/models/microsoft_Phi-4-mini-instruct-Q4_K_M.gguf"

# Remote LLM server (optional)
# Set MODEL_API_URL to use a remote OpenAI-compatible server (e.g., Ollama, llama.cpp server)
# For Stack A with TurboQuant, we default to localhost:8080
export MODEL_API_URL="${MODEL_API_URL:-http://localhost:8080/v1}"

# Check models exist if NOT using remote API (or if we want to be sure they are there for the server)
if [ ! -f "$MODEL_ANALYZER" ]; then
    echo "ERROR: Analyzer model not found: $MODEL_ANALYZER"
    echo "Run: python scripts/download_models.py qwen3.5-9b-uncensored-hauCS"
    exit 1
fi

if [ ! -f "$MODEL_VERIFIER" ]; then
    echo "ERROR: Verifier model not found: $MODEL_VERIFIER"
    echo "Run: python scripts/download_models.py --stack-a"
    exit 1
fi

echo "Using LLM API: $MODEL_API_URL"

echo "Hardware Profile: Stack A (GTX 3060, 8GB)"
echo "Execution Mode: Sequential"
echo ""
echo "Models:"
echo "  Analyzer: Qwen3.5-9B Uncensored (hauCS Aggressive)"
echo "  Verifier: Phi-4-mini"
echo ""

# Set CUDA options for 8GB VRAM
export CUDA_VISIBLE_DEVICES="0"
export GGML_CUDA_ENABLE="1"
export GGML_CUDA_MAIN_DEVICE="0"

# Conservative memory settings for 8GB
export LLAMA_CPP_N_CTX="8192"
export LLAMA_CPP_N_GPU_LAYERS="35"
export LLAMA_CPP_N_THREADS="8"

# Disable features that require more VRAM
export GLITCHHUNTER_PARALLEL_INFERENCE="false"
export GLITCHHUNTER_DEEP_SECURITY_SCAN="false"
export GLITCHHUNTER_MULTI_MODEL_CONSENSUS="false"

# Enable basic features
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

# Set PATH to include current directory for scripts
export PATH="$SCRIPT_DIR:$PATH"

# --- Automation Helpers ---

SERVER_PID=""

cleanup() {
    if [ -n "$SERVER_PID" ]; then
        echo ""
        echo "Stopping LLM Server (PID: $SERVER_PID)..."
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
        echo "Server stopped."
    fi
}

# Trap exit/interrupt to ensure cleanup
trap cleanup EXIT INT TERM

ensure_server_built() {
    # Get build path from config
    LLAMA_TOOLS_PATH=$(grep "llama_tools_path:" "$PROJECT_DIR/config.yaml" | awk '{print $2}' | tr -d '"')
    LLAMA_TOOLS_PATH=${LLAMA_TOOLS_PATH:-"/home/schaf/tools/llama-cpp-turboquant-cuda"}
    
    if [ ! -f "$LLAMA_TOOLS_PATH/build/bin/llama-server" ]; then
        echo "LLM Server not found. Building now..."
        BATCH_MODE=1 "$SCRIPT_DIR/build_llama_cpp.sh"
    fi
}

wait_for_server() {
    local max_retries=60
    local count=0
    echo -n "Waiting for LLM Server to be ready..."
    while ! curl -s http://localhost:8080/health > /dev/null; do
        sleep 1
        echo -n "."
        count=$((count + 1))
        if [ $count -ge $max_retries ]; then
            echo ""
            echo "ERROR: Server timed out after $max_retries seconds."
            exit 1
        fi
    done
    echo " Ready!"
}

start_server_bg() {
    if curl -s http://localhost:8080/health > /dev/null; then
        echo "LLM Server is already running on port 8080."
        echo "Attempting to kill existing server to ensure clean VRAM..."
        pkill -f llama-server || true
        sleep 2
    fi

    ensure_server_built

    # Get paths from config
    LLAMA_TOOLS_PATH=$(grep "llama_tools_path:" "$PROJECT_DIR/config.yaml" | awk '{print $2}' | tr -d '"')
    LLAMA_TOOLS_PATH=${LLAMA_TOOLS_PATH:-"/home/schaf/tools/llama-cpp-turboquant-cuda"}
    CHAT_TEMPLATE="$PROJECT_DIR/src/inference/templates/qwen_de.jinja"
    
    echo "Starting LLM Server in background..."
    
    cd "$LLAMA_TOOLS_PATH/build"
    # Start server with TurboQuant parameters
    TURBO_LAYER_ADAPTIVE=1 ./bin/llama-server \
        -m "$MODEL_ANALYZER" \
        -ctk turbo3 \
        -ctv turbo3 \
        -c 131072 \
        -ngl 50 \
        -fa on \
        -t 8 \
        -b 512 \
        --host 0.0.0.0 \
        --port 8080 \
        --temp 0.3 \
        --top-p 0.9 \
        --min-p 0.1 \
        --repeat-penalty 1.2 \
        --reasoning off \
        --reasoning-format none \
        --chat-template-file "$CHAT_TEMPLATE" \
        > "$PROJECT_DIR/logs/llama_server.log" 2>&1 &
    
    SERVER_PID=$!
    echo "Server started with PID: $SERVER_PID (Logs: logs/llama_server.log)"
    
    cd "$PROJECT_DIR"
    wait_for_server
}

# Parse command line arguments
COMMAND="${1:-api}"

case "$COMMAND" in
    api)
        echo "Starting API server..."
        echo ""
        cd "$PROJECT_DIR/src"
        python3 -m api.server
        ;;
    
    analyze)
        REPO_PATH="${2:-.}"
        start_server_bg
        echo "Starting analysis for: $REPO_PATH"
        echo ""
        cd "$PROJECT_DIR"
        python3 -c "
from core.config import Config
from core.logging_config import setup_logging
from agent.state_machine import build_workflow
config = Config.load()
setup_logging(config.logging, log_level=config.logging.get_level_for_stack('stack_a'))
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
        cd "$PROJECT_DIR/src"
        python3 -c "
from hardware.detector import HardwareDetector
detector = HardwareDetector()
profile = detector.detect()
print(f'Detected Stack: {profile.stack_type.value}')
print(f'GPU Name: {detector.get_gpu_name() or \"Unknown\"}')
print(f'VRAM: {profile.vram_limit} GB')
print(f'Mode: {profile.mode.value}')
detector.shutdown()
"
        ;;

    scan)
        REPO_PATH="${2:-.}"
        start_server_bg
        echo "Starting AI-augmented SCAN for: $REPO_PATH"
        echo "This will perform ingestion, security scanning, and AI verification."
        echo ""
        cd "$PROJECT_DIR"
        export MODEL_API_URL="http://localhost:8080"
        python3 -c "
from core.config import Config
from core.logging_config import setup_logging
from agent.state_machine import build_workflow
config = Config.load()
setup_logging(config.logging, log_level=config.logging.get_level_for_stack('stack_a'))
workflow = build_workflow()
result = workflow.run('$REPO_PATH', stop_after='llift_prioritizer')
print('Scan complete!')
print(f'Findings: {result.get(\"prefilter_result\", {}).get(\"security_findings\", 0)} security, {result.get(\"prefilter_result\", {}).get(\"correctness_findings\", 0)} correctness')
"
        cleanup
        ;;

    fix)
        REPO_PATH="${2:-.}"
        start_server_bg
        echo "Starting FIX RUN for: $REPO_PATH"
        echo "This will scan and then attempt to generate/verify patches."
        echo ""
        cd "$PROJECT_DIR"
        export MODEL_API_URL="http://localhost:8080"
        python3 -c "
from core.config import Config
from core.logging_config import setup_logging
from agent.state_machine import build_workflow
config = Config.load()
setup_logging(config.logging, log_level=config.logging.get_level_for_stack('stack_a'))
workflow = build_workflow()
result = workflow.run('$REPO_PATH')
print('Fix run complete!')
print(f'Patches generated: {len(result.get(\"patches\", []))}')
print(f'Patches verified: {len(result.get(\"verified_patches\", []))}')
"
        cleanup
        ;;
    
    download)
        echo "Downloading Stack A models..."
        echo ""
        python3 "$SCRIPT_DIR/download_models.py" --stack-a
        ;;
    
    llm-server)
        echo "Starting TurboQuant LLM Server..."
        
        # Get paths from config
        LLAMA_TOOLS_PATH=$(grep "llama_tools_path:" "$PROJECT_DIR/config.yaml" | awk '{print $2}' | tr -d '"')
        LLAMA_TOOLS_PATH=${LLAMA_TOOLS_PATH:-"/home/schaf/tools/llama-cpp-turboquant-cuda"}
        CHAT_TEMPLATE="$PROJECT_DIR/src/inference/templates/qwen_de.jinja"
        
        if [ ! -f "$LLAMA_TOOLS_PATH/build/bin/llama-server" ]; then
            echo "ERROR: llama-server not found at $LLAMA_TOOLS_PATH/build/bin/llama-server"
            echo "Please run: ./scripts/build_llama_cpp.sh first."
            exit 1
        fi

        echo "Model: $MODEL_ANALYZER"
        echo "Port: 8080"
        echo ""

        cd "$LLAMA_TOOLS_PATH/build"
        
        # Start server with TurboQuant parameters
        TURBO_LAYER_ADAPTIVE=1 ./bin/llama-server \
            -m "$MODEL_ANALYZER" \
            -ctk turbo3 \
            -ctv turbo3 \
            -c 131072 \
            -ngl 50 \
            -fa on \
            -t 8 \
            -b 512 \
            --host 0.0.0.0 \
            --port 8080 \
            --temp 0.3 \
            --top-p 0.9 \
            --min-p 0.1 \
            --repeat-penalty 1.2 \
            --reasoning off \
            --reasoning-format none \
            --chat-template-file "$CHAT_TEMPLATE"
        ;;

    *)
        echo "Usage: $0 {scan [path]|fix [path]}"
        echo ""
        echo "Commands:"
        echo "  scan [path]      Vulnerability scan only (Automatic build & server management)"
        echo "  fix [path]       Full autonomous fixing cycle (Automatic build & server management)"
        echo ""
        echo "Advanced Commands:"
        echo "  api              Start the GlitchHunter API server"
        echo "  llm-server       Start the TurboQuant LLM server manually"
        echo "  check            Check hardware detection"
        echo "  download         Download required models"
        exit 1
        ;;
esac

echo ""
echo "Done!"
