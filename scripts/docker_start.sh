#!/bin/bash
# GlitchHunter Docker Start Script
# Startet die Web-UI in Docker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  🐛  GlitchHunter v3.0 Docker Start                     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Prüfe ob Docker läuft
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker läuft nicht!"
    echo "   Bitte starte Docker Desktop oder Docker Daemon."
    exit 1
fi

# Prüfe ob Image existiert
if ! docker image inspect glitchhunter:latest > /dev/null 2>&1; then
    echo "⚠️  Image nicht gefunden. Baue zuerst..."
    bash "$SCRIPT_DIR/docker_build.sh"
fi

echo "🚀 Starte GlitchHunter..."
echo ""

# docker-compose verwenden wenn vorhanden
if [ -f "docker-compose.yml" ]; then
    docker compose up -d
    echo ""
    echo "✅ GlitchHunter gestartet!"
    echo ""
    echo "📡 Dashboard: http://localhost:6262"
    echo "📚 API Docs:  http://localhost:6262/docs"
    echo "💓 Health:    http://localhost:6262/api/v1/status"
    echo ""
    echo "📋 Logs:      docker compose logs -f"
    echo "🛑 Stoppen:   docker compose down"
    echo ""
else
    # Fallback: docker run
    docker run -d \
        --name glitchhunter \
        -p 6262:6262 \
        -v "$(pwd)/config.yaml:/app/config.yaml:ro" \
        -v gh-data:/app/data \
        -v gh-logs:/app/logs \
        -v gh-cache:/app/cache \
        -v gh-reports:/app/reports \
        --restart unless-stopped \
        glitchhunter:latest
    
    echo ""
    echo "✅ GlitchHunter gestartet!"
    echo ""
    echo "📡 Dashboard: http://localhost:6262"
    echo "📚 API Docs:  http://localhost:6262/docs"
    echo "💓 Health:    http://localhost:6262/api/v1/status"
    echo ""
    echo "📋 Logs:      docker logs -f glitchhunter"
    echo "🛑 Stoppen:   docker stop glitchhunter"
    echo ""
fi
