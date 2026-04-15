#!/bin/bash
#
# GlitchHunter v2.0 Auto-Detection Runner
#
# Automatisch Hardware erkennen und besten Stack wählen
# Usage: ./run_auto.sh [scan|fix] [--cpu-only] [--incremental] [--full] <path>
#

set -e

# Skript-Verzeichnis
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Aktiviere venv falls vorhanden
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
fi

# Set PYTHONPATH fuer src imports (wichtig!)
export PYTHONPATH="${PROJECT_DIR}/src:${PYTHONPATH:+:$PYTHONPATH}"

# Parse Argumente
COMMAND=""
TARGET_PATH=""
CPU_ONLY=""
INCREMENTAL=""
FORCE_FULL=""

while [[ $# -gt 0 ]]; do
    case $1 in
        scan|analyze)
            COMMAND="analyze"
            shift
            ;;
        fix)
            COMMAND="analyze"  # fix = analyze + auto-apply
            shift
            ;;
        --cpu-only)
            CPU_ONLY="--cpu-only"
            shift
            ;;
        --incremental)
            INCREMENTAL="--incremental"
            shift
            ;;
        --full)
            FORCE_FULL="--full-scan"
            shift
            ;;
        --clear-cache)
            CLEAR_CACHE="--clear-cache"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            if [ -z "$TARGET_PATH" ]; then
                TARGET_PATH="$1"
            fi
            shift
            ;;
    esac
done

function show_help() {
    cat << EOF
GlitchHunter v2.0 Auto-Runner

Usage: ./run_auto.sh [COMMAND] [OPTIONS] <path>

Commands:
    scan, analyze   Security scan only
    fix             Scan and auto-fix vulnerabilities

Options:
    --cpu-only      Force CPU-only mode (no GPU required)
    --incremental   Only scan changed files (fast!)
    --full          Force full scan (ignore cache)
    --clear-cache   Clear all caches before scan
    -h, --help      Show this help

Examples:
    ./run_auto.sh scan /path/to/project
    ./run_auto.sh analyze /path/to/project
    ./run_auto.sh fix --cpu-only /path/to/project
    ./run_auto.sh scan --incremental /path/to/project
    ./run_auto.sh fix --full --clear-cache /path/to/project

EOF
}

function detect_hardware() {
    echo "Detecting hardware..."
    
    # Prüfe CUDA
    if command -v nvidia-smi &> /dev/null; then
        GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1)
        if [ -n "$GPU_MEM" ]; then
            GPU_GB=$((GPU_MEM / 1024))
            echo "[OK] GPU detected: ${GPU_GB}GB VRAM"
            
            if [ "$GPU_GB" -ge 20 ]; then
                echo "     Stack B (RTX 3090/4090)"
                STACK="b"
            elif [ "$GPU_GB" -ge 8 ]; then
                echo "     Stack A (RTX 3060/4060)"
                STACK="a"
            else
                echo "     Low VRAM, using CPU fallback"
                STACK="cpu"
            fi
            return
        fi
    fi
    
    # Prüfe ROCm
    if command -v rocminfo &> /dev/null; then
        echo "[OK] AMD GPU detected (ROCm)"
        STACK="rocm"
        return
    fi
    
    # Keine GPU
    echo "[WARN] No GPU detected, using CPU-only mode"
    STACK="cpu"
}

function check_llama_cpp() {
    if ! command -v llama-cli &> /dev/null; then
        echo "[WARN] llama.cpp not found"
        echo "       For CPU-only mode, install llama.cpp:"
        echo "       git clone https://github.com/ggerganov/llama.cpp"
        echo "       cd llama.cpp && cmake -B build && cmake --build build"
        
        if [ "$STACK" == "cpu" ]; then
            echo "[ERR] llama.cpp required for CPU mode"
            exit 1
        fi
    else
        echo "[OK] llama.cpp available"
    fi
}

function download_model_if_needed() {
    MODEL_DIR="$HOME/.glitchhunter/models"
    MODEL_FILE="qwen2.5-coder-7b-instruct-q4_k_m.gguf"
    
    if [ ! -f "$MODEL_DIR/$MODEL_FILE" ]; then
        echo "[WARN] Model not found: $MODEL_FILE"
        echo "       Downloading... (4.5GB)"
        
        mkdir -p "$MODEL_DIR"
        
        # Versuche huggingface-cli
        if command -v huggingface-cli &> /dev/null; then
            huggingface-cli download Qwen/Qwen2.5-Coder-7B-Instruct-GGUF \
                "$MODEL_FILE" \
                --local-dir "$MODEL_DIR"
        else
            echo "       Please install huggingface-cli:"
            echo "       pip install huggingface-hub"
            exit 1
        fi
    fi
}

function run_scan() {
    local target="$1"
    
    echo "Starting GlitchHunter v2.0..."
    echo "   Command: $COMMAND"
    echo "   Target: $target"
    echo "   Stack: $STACK"
    echo ""
    
    # Wichtig: Ins src-Verzeichnis wechseln!
    cd "$PROJECT_DIR/src"
    
    # Führe Analyse direkt aus (wie run_stack_a.sh)
    python3 -c "
from core.config import Config
from core.logging_config import setup_logging
from agent.state_machine import build_workflow
config = Config.load()
setup_logging(config.logging, log_level='INFO')
workflow = build_workflow()
result = workflow.run('$target')
print('Analysis complete!')
print(f'State: {result.get(\"current_state\", \"unknown\")}')
print(f'Errors: {result.get(\"errors\", [])}')
"
}

# Hauptlogik
function main() {
    echo "================================================"
    echo "     GlitchHunter v2.0 Auto-Runner"
    echo "================================================"
    echo ""
    
    # Validierung
    if [ -z "$COMMAND" ]; then
        echo "[ERR] Error: No command specified"
        show_help
        exit 1
    fi
    
    if [ -z "$TARGET_PATH" ]; then
        echo "[ERR] Error: No target path specified"
        show_help
        exit 1
    fi
    
    if [ ! -d "$TARGET_PATH" ]; then
        echo "[ERR] Error: Directory not found: $TARGET_PATH"
        exit 1
    fi
    
    # Hardware-Erkennung (außer bei --cpu-only)
    if [ -z "$CPU_ONLY" ]; then
        detect_hardware
    else
        echo "[INFO] CPU-only mode forced"
        STACK="cpu"
    fi
    
    echo ""
    
    # Prüfe llama.cpp für CPU-Modus
    if [ "$STACK" == "cpu" ]; then
        check_llama_cpp
        download_model_if_needed
    fi
    
    echo ""
    
    # Führe Scan aus
    run_scan "$TARGET_PATH"
    
    echo ""
    echo "================================================"
    echo "     GlitchHunter v2.0 Complete"
    echo "================================================"
}

main