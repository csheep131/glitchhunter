#!/bin/bash
#
# Start GlitchHunter TUI (Terminal User Interface)
#
# Usage: ./run_tui.sh [api_url]
#

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Default API URL
API_URL="${1:-http://localhost:8000}"

echo "==================================="
echo "  GlitchHunter TUI"
echo "==================================="
echo ""

# Check if we're in the right directory
if [ ! -f "$PROJECT_DIR/src/tui/app.py" ]; then
    echo "ERROR: TUI not found. Are you in the glitchhunter directory?"
    exit 1
fi

# Activate virtual environment
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
elif [ -f "$PROJECT_DIR/.venv/bin/activate" ]; then
    source "$PROJECT_DIR/.venv/bin/activate"
else
    echo "WARNING: No virtual environment found"
fi

# Check if textual is installed
if ! python3 -c "import textual" 2>/dev/null; then
    echo "Installing Textual..."
    pip install textual httpx
fi

echo "API URL: $API_URL"
echo ""

# Check if API is running
echo "Checking API connection..."
if curl -s "$API_URL/api/health" > /dev/null 2>&1; then
    echo "✅ API is online"
else
    echo "⚠️  API not available at $API_URL"
    echo "   Start API first: ./scripts/run_stack_a.sh api"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "Starting TUI..."
echo "Press Q or Escape to exit"
echo ""

# Set PYTHONPATH and run TUI
cd "$PROJECT_DIR/src"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:$PYTHONPATH}"
export GLITCHHUNTER_API_URL="$API_URL"

python3 -m tui.app "$@"

echo ""
echo "TUI closed."
