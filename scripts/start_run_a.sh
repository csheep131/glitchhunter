#!/bin/bash
#
# start_run_a.sh - GlitchHunter Automated Scan & Fix (Stack A)
#
# Usage: ./scripts/start_run_a.sh [project_path]
#

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

REPO_PATH="${1:-.}"

echo "===================================================="
echo "  GlitchHunter: Automated Scan & Fix (Stack A)      "
echo "===================================================="
echo "Project Path: $REPO_PATH"
echo ""

# Phase 1: Scan
echo ">>> PHASE 1: VULNERABILITY SCAN"
"$SCRIPT_DIR/run_stack_a.sh" scan "$REPO_PATH"

echo ""
echo ">>> PHASE 1 COMPLETE."
echo ""

# Phase 2: Fix
echo ">>> PHASE 2: AUTONOMOUS FIX RUN"
"$SCRIPT_DIR/run_stack_a.sh" fix "$REPO_PATH"

echo ""
echo "===================================================="
echo "  ALL OPERATIONS COMPLETE!"
echo "===================================================="
