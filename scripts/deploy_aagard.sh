#!/bin/bash
# GlitchHunter Deployment Skript für aagard
# Verwendet lokale Modelle unter /home/schaf/modelle

set -euo pipefail

SERVER="aagard"
REMOTE_DIR="/home/schaf/glitchhunter"
BUILD_DIR="/tmp/glitchhunter-build"

echo "=== GlitchHunter aagard Deployment ==="

# 1. Build-Ordner vorbereiten
echo "[1/5] Build-Verzeichnis vorbereiten..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# 2. Nur relevante Dateien kopieren
echo "[2/5] Dateien für Build kopieren..."
cp Dockerfile.webui "$BUILD_DIR/Dockerfile"
cp docker-compose.aagard.yml "$BUILD_DIR/docker-compose.yml"
cp config.aagard.yaml "$BUILD_DIR/config.aagard.yaml"
cp -r ui/web/ "$BUILD_DIR/ui/web/"
cp -r src/ "$BUILD_DIR/src/"
cp config.yaml "$BUILD_DIR/config.yaml"

# 3. Auf aagard übertragen
echo "[3/5] Auf $SERVER übertragen..."
ssh "$SERVER" "mkdir -p $REMOTE_DIR"
rsync -avz --delete \
    "$BUILD_DIR/" \
    "$SERVER:$REMOTE_DIR/"

# 4. Docker Image auf aagard bauen
echo "[4/5] Docker Image auf $SERVER bauen..."
ssh "$SERVER" "cd $REMOTE_DIR && docker build -t glitchhunter:aagard ."

# 5. Docker Compose starten
echo "[5/5] Container auf $SERVER starten..."
ssh "$SERVER" "cd $REMOTE_DIR && docker compose -f docker-compose.yml down 2>/dev/null; docker compose -f docker-compose.yml up -d"

echo ""
echo "=== Deployment abgeschlossen ==="
echo "Dashboard: http://aagard:6262"
echo "API Docs:  http://aagard:6262/docs"
echo ""
echo "Logs: ssh $SERVER 'docker compose -f $REMOTE_DIR/docker-compose.yml logs -f'"
