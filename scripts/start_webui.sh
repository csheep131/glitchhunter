#!/bin/bash
# Start-Skript für GlitchHunter Web-UI

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# In Projekt-Root wechseln
cd "$PROJECT_ROOT"

# Python aus venv verwenden (fallback zu Projekt-venv)
if [ -n "$VIRTUAL_ENV" ]; then
    PYTHON="$VIRTUAL_ENV/bin/python3"
    echo "✅ Verwende Python aus venv: $PYTHON"
elif [ -f "$PROJECT_ROOT/venv/bin/python3" ]; then
    PYTHON="$PROJECT_ROOT/venv/bin/python3"
    echo "✅ Verwende Python aus Projekt-venv: $PYTHON"
else
    PYTHON="python3"
    echo "⚠️  Keine venv gefunden, verwende System-Python: $PYTHON"
fi

# PYTHONPATH setzen damit Imports funktionieren
# src/ muss zuerst kommen damit src.agent.* Imports funktionieren
export PYTHONPATH="$PROJECT_ROOT/src:$PROJECT_ROOT:$PYTHONPATH"
echo "📁 PYTHONPATH: $PROJECT_ROOT/src:$PROJECT_ROOT"

# Standard-Port
PORT=${1:-6262}

echo "🚀 Starte GlitchHunter Web-UI..."
echo "📡 Dashboard: http://localhost:$PORT"
echo "📚 API Docs: http://localhost:$PORT/docs"
echo ""

# Server starten
exec "$PYTHON" -m ui.web.backend.app
