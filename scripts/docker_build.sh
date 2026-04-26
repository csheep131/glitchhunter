#!/bin/bash
# GlitchHunter Docker Build Script
# Erstellt das Docker-Image für Deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  🐛  GlitchHunter v3.0 Docker Build                     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Version aus pyproject.toml lesen
VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
IMAGE_NAME="glitchhunter"
IMAGE_TAG="${VERSION:-latest}"

echo "📦 Build: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "📁 Projekt: ${PROJECT_ROOT}"
echo ""

# Build
echo "🔨 Starte Docker Build..."
docker build \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    --progress=plain \
    -t "${IMAGE_NAME}:${IMAGE_TAG}" \
    -t "${IMAGE_NAME}:latest" \
    -f Dockerfile.slim \
    .

echo ""
echo "✅ Build abgeschlossen!"
echo ""
echo "📊 Image-Info:"
docker images "${IMAGE_NAME}:${IMAGE_TAG}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
echo ""
echo "🚀 Starten mit:"
echo "   docker compose up -d"
echo ""
echo "   Oder:"
echo "   docker run -d -p 6262:6262 \\"
echo "     -v \$(pwd)/config.yaml:/app/config.yaml:ro \\"
echo "     -v gh-data:/app/data \\"
echo "     --name glitchhunter \\"
echo "     ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""
