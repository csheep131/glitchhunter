#!/bin/bash
#
# GlitchHunter v2.0 Auto-Detection Runner
#
# Automatisch Hardware erkennen und besten Stack wählen
# Usage: ./run_auto.sh [scan|fix] [--cpu-only] [--incremental] [--full] <path>
#

set -e

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Skript-Verzeichnis
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Aktiviere venv falls vorhanden
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
fi

# Parse Argumente
COMMAND=""
TARGET_PATH=""
CPU_ONLY=""
INCREMENTAL=""
FORCE_FULL=""

while [[ $# -gt 0 ]]; do
    case $1 in
        scan|fix)
            COMMAND="$1"
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
    scan        Security scan only
    fix         Scan and auto-fix vulnerabilities

Options:
    --cpu-only      Force CPU-only mode (no GPU required)
    --incremental   Only scan changed files (fast!)
    --full          Force full scan (ignore cache)
    --clear-cache   Clear all caches before scan
    -h, --help      Show this help

Examples:
    ./run_auto.sh scan /path/to/project
    ./run_auto.sh fix --cpu-only /path/to/project
    ./run_auto.sh scan --incremental /path/to/project
    ./run_auto.sh fix --full --clear-cache /path/to/project

EOF
}

function detect_hardware() {
    echo -e "${BLUE}🔍 Detecting hardware...${NC}"
    
    # Prüfe CUDA
    if command -v nvidia-smi &> /dev/null; then
        GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1)
        if [ -n "$GPU_MEM" ]; then
            GPU_GB=$((GPU_MEM / 1024))
            echo -e "${GREEN}✓ GPU detected: ${GPU_GB}GB VRAM${NC}"
            
            if [ "$GPU_GB" -ge 20 ]; then
                echo -e "${GREEN}  → Stack B (RTX 3090/4090)${NC}"
                STACK="b"
            elif [ "$GPU_GB" -ge 8 ]; then
                echo -e "${GREEN}  → Stack A (RTX 3060/4060)${NC}"
                STACK="a"
            else
                echo -e "${YELLOW}  → Low VRAM, using CPU fallback${NC}"
                STACK="cpu"
            fi
            return
        fi
    fi
    
    # Prüfe ROCm
    if command -v rocminfo &> /dev/null; then
        echo -e "${GREEN}✓ AMD GPU detected (ROCm)${NC}"
        STACK="rocm"
        return
    fi
    
    # Keine GPU
    echo -e "${YELLOW}⚠ No GPU detected, using CPU-only mode${NC}"
    STACK="cpu"
}

function check_llama_cpp() {
    if ! command -v llama-cli &> /dev/null; then
        echo -e "${YELLOW}⚠ llama.cpp not found${NC}"
        echo -e "${YELLOW}  For CPU-only mode, install llama.cpp:${NC}"
        echo -e "${YELLOW}  git clone https://github.com/ggerganov/llama.cpp${NC}"
        echo -e "${YELLOW}  cd llama.cpp && cmake -B build && cmake --build build${NC}"
        
        if [ "$STACK" == "cpu" ]; then
            echo -e "${RED}✗ llama.cpp required for CPU mode${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✓ llama.cpp available${NC}"
    fi
}

function download_model_if_needed() {
    MODEL_DIR="$HOME/.glitchhunter/models"
    MODEL_FILE="qwen2.5-coder-7b-instruct-q4_k_m.gguf"
    
    if [ ! -f "$MODEL_DIR/$MODEL_FILE" ]; then
        echo -e "${YELLOW}⚠ Model not found: $MODEL_FILE${NC}"
        echo -e "${YELLOW}  Downloading... (4.5GB)${NC}"
        
        mkdir -p "$MODEL_DIR"
        
        # Versuche huggingface-cli
        if command -v huggingface-cli &> /dev/null; then
            huggingface-cli download Qwen/Qwen2.5-Coder-7B-Instruct-GGUF \
                "$MODEL_FILE" \
                --local-dir "$MODEL_DIR"
        else
            echo -e "${YELLOW}  Please install huggingface-cli:${NC}"
            echo -e "${YELLOW}  pip install huggingface-hub${NC}"
            exit 1
        fi
    fi
}

function run_scan() {
    local target="$1"
    
    echo -e "${BLUE}🚀 Starting GlitchHunter v2.0...${NC}"
    echo -e "${BLUE}   Command: $COMMAND${NC}"
    echo -e "${BLUE}   Target: $target${NC}"
    echo -e "${BLUE}   Stack: $STACK${NC}"
    
    # Baue Python-Kommando
    PYTHON_CMD="python -m src.main $COMMAND"
    
    if [ -n "$CPU_ONLY" ] || [ "$STACK" == "cpu" ]; then
        PYTHON_CMD="$PYTHON_CMD --cpu-only"
    fi
    
    if [ -n "$INCREMENTAL" ]; then
        PYTHON_CMD="$PYTHON_CMD --incremental"
    fi
    
    if [ -n "$FORCE_FULL" ]; then
        PYTHON_CMD="$PYTHON_CMD --full-scan"
    fi
    
    if [ -n "$CLEAR_CACHE" ]; then
        PYTHON_CMD="$PYTHON_CMD --clear-cache"
    fi
    
    PYTHON_CMD="$PYTHON_CMD \"$target\""
    
    echo -e "${BLUE}   Running: $PYTHON_CMD${NC}"
    echo ""
    
    # Führe aus
    cd "$PROJECT_DIR"
    eval "$PYTHON_CMD"
}

# Hauptlogik
function main() {
    echo -e "${GREEN}════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}     GlitchHunter v2.0 Auto-Runner${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════${NC}"
    echo ""
    
    # Validierung
    if [ -z "$COMMAND" ]; then
        echo -e "${RED}✗ Error: No command specified${NC}"
        show_help
        exit 1
    fi
    
    if [ -z "$TARGET_PATH" ]; then
        echo -e "${RED}✗ Error: No target path specified${NC}"
        show_help
        exit 1
    fi
    
    if [ ! -d "$TARGET_PATH" ]; then
        echo -e "${RED}✗ Error: Directory not found: $TARGET_PATH${NC}"
        exit 1
    fi
    
    # Hardware-Erkennung (außer bei --cpu-only)
    if [ -z "$CPU_ONLY" ]; then
        detect_hardware
    else
        echo -e "${BLUE}🔧 CPU-only mode forced${NC}"
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
    echo -e "${GREEN}════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}     GlitchHunter v2.0 Complete${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════${NC}"
}

main