#!/bin/bash
#
# Download recommended models for GlitchHunter
#
# This script downloads the officially recommended GGUF models
# for optimal performance with GlitchHunter v2.0
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Model directory
MODEL_DIR="${HOME}/.glitchhunter/models"
mkdir -p "$MODEL_DIR"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  GlitchHunter Model Downloader${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Check for huggingface-cli
if ! command -v huggingface-cli &> /dev/null; then
    echo -e "${RED}Error: huggingface-cli not found${NC}"
    echo "Install with: pip install huggingface-hub"
    exit 1
fi

# Function to download model
download_model() {
    local repo=$1
    local file=$2
    local desc=$3
    
    echo -e "${YELLOW}Downloading: $desc${NC}"
    echo "  Repository: $repo"
    echo "  File: $file"
    
    if [ -f "$MODEL_DIR/$file" ]; then
        echo -e "${GREEN}  Already exists, skipping${NC}"
        return 0
    fi
    
    huggingface-cli download "$repo" "$file" \
        --local-dir "$MODEL_DIR" \
        --local-dir-use-symlinks False
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  Download complete${NC}"
    else
        echo -e "${RED}  Download failed${NC}"
        return 1
    fi
}

# Parse arguments
DOWNLOAD_ALL=false
SPECIFIC_MODEL=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            DOWNLOAD_ALL=true
            shift
            ;;
        --qwen-7b)
            SPECIFIC_MODEL="qwen-7b"
            shift
            ;;
        --qwen-14b)
            SPECIFIC_MODEL="qwen-14b"
            shift
            ;;
        --deepseek)
            SPECIFIC_MODEL="deepseek"
            shift
            ;;
        --phi)
            SPECIFIC_MODEL="phi"
            shift
            ;;
        --list)
            echo "Available models:"
            echo "  --qwen-7b     Qwen2.5-Coder-7B (Recommended, ~4.5GB)"
            echo "  --qwen-14b    Qwen2.5-Coder-14B (Better quality, ~8.5GB)"
            echo "  --deepseek    DeepSeek-Coder-V2-Lite (Security focus, ~9GB)"
            echo "  --phi         Phi-4 (Fast inference, ~8GB)"
            echo "  --all         Download all recommended models"
            exit 0
            ;;
        -h|--help)
            echo "Usage: $0 [OPTION]"
            echo ""
            echo "Options:"
            echo "  --all         Download all recommended models"
            echo "  --qwen-7b     Download Qwen2.5-Coder-7B only"
            echo "  --qwen-14b    Download Qwen2.5-Coder-14B only"
            echo "  --deepseek    Download DeepSeek-Coder-V2-Lite only"
            echo "  --phi         Download Phi-4 only"
            echo "  --list        List available models"
            echo "  -h, --help    Show this help"
            echo ""
            echo "Default (no args): Downloads Qwen2.5-Coder-7B (recommended)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "Target directory: $MODEL_DIR"
echo ""

# Download based on selection
if [ "$DOWNLOAD_ALL" = true ]; then
    echo -e "${BLUE}Downloading ALL recommended models...${NC}"
    echo "This will use approximately 30GB of disk space."
    echo ""
    
    download_model \
        "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF" \
        "qwen2.5-coder-7b-instruct-q4_k_m.gguf" \
        "Qwen2.5-Coder-7B (Primary Recommendation)"
    
    download_model \
        "Qwen/Qwen2.5-Coder-14B-Instruct-GGUF" \
        "qwen2.5-coder-14b-instruct-q4_k_m.gguf" \
        "Qwen2.5-Coder-14B (Enhanced Quality)"
    
    download_model \
        "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct-GGUF" \
        "deepseek-coder-v2-lite-instruct-q4_k_m.gguf" \
        "DeepSeek-Coder-V2-Lite (Security Specialist)"
    
    download_model \
        "microsoft/Phi-4-instruct-GGUF" \
        "phi-4-instruct-q4_k_m.gguf" \
        "Phi-4 (Fast Inference)"

elif [ "$SPECIFIC_MODEL" = "qwen-7b" ]; then
    download_model \
        "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF" \
        "qwen2.5-coder-7b-instruct-q4_k_m.gguf" \
        "Qwen2.5-Coder-7B"

elif [ "$SPECIFIC_MODEL" = "qwen-14b" ]; then
    download_model \
        "Qwen/Qwen2.5-Coder-14B-Instruct-GGUF" \
        "qwen2.5-coder-14b-instruct-q4_k_m.gguf" \
        "Qwen2.5-Coder-14B"

elif [ "$SPECIFIC_MODEL" = "deepseek" ]; then
    download_model \
        "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct-GGUF" \
        "deepseek-coder-v2-lite-instruct-q4_k_m.gguf" \
        "DeepSeek-Coder-V2-Lite"

elif [ "$SPECIFIC_MODEL" = "phi" ]; then
    download_model \
        "microsoft/Phi-4-instruct-GGUF" \
        "phi-4-instruct-q4_k_m.gguf" \
        "Phi-4"

else
    # Default: Download recommended model
    echo -e "${BLUE}Downloading recommended model...${NC}"
    echo "Use --all to download all models, or --list to see options."
    echo ""
    
    download_model \
        "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF" \
        "qwen2.5-coder-7b-instruct-q4_k_m.gguf" \
        "Qwen2.5-Coder-7B (Recommended)"
fi

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Download Complete${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Models are stored in: $MODEL_DIR"
echo ""
echo "To use these models with GlitchHunter:"
echo "  1. Update config.yaml with the model path"
echo "  2. Or run: ./scripts/run_auto.sh scan /path/to/repo"
echo ""
ls -lh "$MODEL_DIR"
