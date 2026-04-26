#!/bin/bash
# GlitchHunter Docker Stop Script
# Stoppt und entfernt den Container

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "🛑 Stoppe GlitchHunter..."

# docker-compose verwenden wenn möglich
if docker compose ps > /dev/null 2>&1; then
    docker compose down
    echo "✅ GlitchHunter gestoppt (docker compose down)"
elif docker ps -q -f name=glitchhunter > /dev/null 2>&1; then
    docker stop glitchhunter
    docker rm glitchhunter
    echo "✅ GlitchHunter gestoppt (docker stop/rm)"
else
    echo "⚠️  GlitchHunter läuft nicht"
fi

echo ""
echo "💡 Volumes bleiben erhalten (Daten, Logs, Cache, Reports)"
echo "   Zum Löschen: docker volume rm gh-data gh-logs gh-cache gh-reports"
