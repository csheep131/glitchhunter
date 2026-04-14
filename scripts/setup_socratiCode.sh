#!/bin/bash
#
# Setup SocratiCode MCP Server for GlitchHunter
#
# This script sets up the SocratiCode MCP server with Docker Compose,
# including Qdrant vector database and Ollama for embeddings.
#
# Usage: ./setup_socratiCode.sh [install|start|stop|status]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SOCRATICODE_DIR="$PROJECT_DIR/.socratiCode"

echo "========================================"
echo "  SocratiCode MCP Setup                "
echo "========================================"
echo ""

# Create SocratiCode directory
mkdir -p "$SOCRATICODE_DIR"

# Create docker-compose.yml
create_docker_compose() {
    cat > "$SOCRATICODE_DIR/docker-compose.yml" << 'EOF'
version: '3.8'

services:
  # Qdrant Vector Database
  qdrant:
    image: qdrant/qdrant:latest
    container_name: glitchhunter-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./qdrant_storage:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Ollama for Embeddings
  ollama:
    image: ollama/ollama:latest
    container_name: glitchhunter-ollama
    ports:
      - "11434:11434"
    volumes:
      - ./ollama_models:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 5

  # SocratiCode MCP Server
  socratiCode:
    image: ghcr.io/socraticode/socratiCode:latest
    container_name: glitchhunter-socratiCode
    ports:
      - "8934:8934"
    volumes:
      - ${PROJECT_DIR}:/codebase:ro
      - ./socratiCode_config:/app/config
    environment:
      - QDRANT_URL=http://qdrant:6333
      - OLLAMA_URL=http://ollama:11434
      - EMBEDDING_MODEL=nomic-embed-text
      - CODEBASE_PATH=/codebase
    depends_on:
      qdrant:
        condition: service_healthy
      ollama:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8934/health"]
      interval: 10s
      timeout: 5s
      retries: 5

networks:
  default:
    name: glitchhunter-network
EOF

    echo "Created docker-compose.yml"
}

# Create SocratiCode config
create_config() {
    mkdir -p "$SOCRATICODE_DIR/socratiCode_config"
    
    cat > "$SOCRATICODE_DIR/socratiCode_config/config.yaml" << 'EOF'
# SocratiCode Configuration

server:
  host: "0.0.0.0"
  port: 8934

qdrant:
  url: "http://qdrant:6333"
  collection_name: "codebase"

ollama:
  url: "http://ollama:11434"
  embedding_model: "nomic-embed-text"

indexing:
  chunk_size: 512
  chunk_overlap: 50
  max_file_size_mb: 10
  exclude_patterns:
    - "*.min.js"
    - "*.map"
    - "node_modules/**"
    - "__pycache__/**"
    - ".git/**"
    - "*.pyc"
    - "dist/**"
    - "build/**"

logging:
  level: "INFO"
  format: "json"
EOF

    echo "Created SocratiCode config"
}

# Install command
do_install() {
    echo "Installing SocratiCode MCP..."
    echo ""

    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo "ERROR: Docker not found. Please install Docker."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo "ERROR: Docker Compose not found. Please install Docker Compose."
        exit 1
    fi

    echo "Docker found: $(docker --version)"
    echo ""

    # Create configuration
    create_docker_compose
    create_config

    echo ""
    echo "Installation complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Start services: ./setup_socratiCode.sh start"
    echo "  2. Check status:   ./setup_socratiCode.sh status"
}

# Start command
do_start() {
    echo "Starting SocratiCode MCP services..."
    echo ""

    if [ ! -f "$SOCRATICODE_DIR/docker-compose.yml" ]; then
        echo "SocratiCode not installed. Run: ./setup_socratiCode.sh install"
        exit 1
    fi

    cd "$SOCRATICODE_DIR"

    # Pull images
    echo "Pulling Docker images..."
    docker compose pull

    # Start services
    echo "Starting services..."
    docker compose up -d

    echo ""
    echo "Waiting for services to be healthy..."
    sleep 10

    # Check status
    docker compose ps

    echo ""
    echo "Services started!"
    echo ""
    echo "Endpoints:"
    echo "  Qdrant:      http://localhost:6333"
    echo "  Ollama:      http://localhost:11434"
    echo "  SocratiCode: http://localhost:8934"
}

# Stop command
do_stop() {
    echo "Stopping SocratiCode MCP services..."
    echo ""

    if [ ! -f "$SOCRATICODE_DIR/docker-compose.yml" ]; then
        echo "SocratiCode not installed."
        exit 1
    fi

    cd "$SOCRATICODE_DIR"
    docker compose down

    echo "Services stopped."
}

# Status command
do_status() {
    echo "SocratiCode MCP Status:"
    echo ""

    if [ ! -f "$SOCRATICODE_DIR/docker-compose.yml" ]; then
        echo "Not installed."
        return
    fi

    cd "$SOCRATICODE_DIR"

    echo "Docker Compose services:"
    docker compose ps

    echo ""
    echo "Service health:"
    
    # Check Qdrant
    if curl -s http://localhost:6333/ > /dev/null 2>&1; then
        echo "  ✓ Qdrant: healthy"
    else
        echo "  ✗ Qdrant: not responding"
    fi

    # Check Ollama
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "  ✓ Ollama: healthy"
    else
        echo "  ✗ Ollama: not responding"
    fi

    # Check SocratiCode
    if curl -s http://localhost:8934/health > /dev/null 2>&1; then
        echo "  ✓ SocratiCode: healthy"
    else
        echo "  ✗ SocratiCode: not responding"
    fi
}

# Pull embedding model
pull_embedding_model() {
    echo "Pulling embedding model..."
    echo ""

    # Check if Ollama is running
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Ollama not running. Start services first."
        return 1
    fi

    # Pull model
    echo "Downloading nomic-embed-text model..."
    ollama run nomic-embed-text exit

    echo "Embedding model ready!"
}

# Main
COMMAND="${1:-help}"

case "$COMMAND" in
    install)
        do_install
        ;;
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    status)
        do_status
        ;;
    pull-model)
        pull_embedding_model
        ;;
    help|*)
        echo "Usage: $0 {install|start|stop|status|pull-model}"
        echo ""
        echo "Commands:"
        echo "  install     Install SocratiCode MCP (create config)"
        echo "  start       Start all services"
        echo "  stop        Stop all services"
        echo "  status      Check service status"
        echo "  pull-model  Download embedding model"
        ;;
esac

echo ""
echo "Done!"
