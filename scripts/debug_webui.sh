#!/usr/bin/env bash
#
# GlitchHunter Web-UI Debug-Start-Skript
#
# Startet das Backend mit maximalem Logging für Debugging:
# - DEBUG Log-Level
# - Request-Logging
# - WebSocket-Logging
# - JSON-Pretty-Print für Responses
#
# Usage:
#   ./scripts/debug_webui.sh
#
# Options (Environment Variables):
#   LOG_LEVEL      - Log-Level (default: DEBUG)
#   LOG_FILE       - Log-Datei (default: logs/glitchhunter_webui_debug.log)
#   PORT           - Port (default: 6262)
#   REPO_PATH      - Test-Repo-Pfad für curl-Test (default: /home/schaf/projects/glitchhunter)
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
LOG_LEVEL="${LOG_LEVEL:-DEBUG}"
LOG_FILE="${LOG_FILE:-logs/glitchhunter_webui_debug.log}"
PORT="${PORT:-6262}"
REPO_PATH="${REPO_PATH:-/home/schaf/projects/glitchhunter}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${CYAN}[DEBUG]${NC} $1"
}

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_info "Prüfe Voraussetzungen..."
    
    # Check Python
    if ! command -v python &> /dev/null; then
        log_error "Python nicht gefunden. Bitte Python 3.11+ installieren."
        exit 1
    fi
    
    PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
    log_debug "Python-Version: $PYTHON_VERSION"
    
    # Check uvicorn
    if ! python -c "import uvicorn" &> /dev/null; then
        log_error "uvicorn nicht installiert. Bitte installieren: pip install uvicorn"
        exit 1
    fi
    log_debug "uvicorn: installiert"
    
    # Check fastapi
    if ! python -c "import fastapi" &> /dev/null; then
        log_error "FastAPI nicht installiert. Bitte installieren: pip install fastapi"
        exit 1
    fi
    log_debug "fastapi: installiert"
    
    # Check project structure
    if [[ ! -f "${PROJECT_ROOT}/ui/web/backend/app.py" ]]; then
        log_error "app.py nicht gefunden unter: ${PROJECT_ROOT}/ui/web/backend/app.py"
        exit 1
    fi
    log_debug "app.py: gefunden"
    
    # Create log directory
    mkdir -p "$(dirname "${PROJECT_ROOT}/${LOG_FILE}")"
    log_debug "Log-Verzeichnis: $(dirname "${PROJECT_ROOT}/${LOG_FILE}")"
    
    log_info "Alle Voraussetzungen erfüllt ✓"
}

# Start backend server
start_backend() {
    print_header "Starte GlitchHunter Web-UI Backend (Debug-Modus)"
    
    log_info "Konfiguration:"
    echo "  LOG_LEVEL:  ${LOG_LEVEL}"
    echo "  LOG_FILE:   ${LOG_FILE}"
    echo "  PORT:       ${PORT}"
    echo "  REPO_PATH:  ${REPO_PATH}"
    echo ""
    
    log_info "Starte uvicorn Server..."
    log_warn "Drücke STRG+C zum Stoppen"
    echo ""
    
    # Export environment variables for Python
    export GLITCHHUNTER_LOG_LEVEL="${LOG_LEVEL}"
    export GLITCHHUNTER_LOG_FILE="${PROJECT_ROOT}/${LOG_FILE}"
    
    # Start uvicorn with debug logging
    cd "${PROJECT_ROOT}"
    python -m uvicorn ui.web.backend.app:app \
        --host 0.0.0.0 \
        --port "${PORT}" \
        --reload \
        --log-level "${LOG_LEVEL,,}" \
        2>&1 | tee -a "${PROJECT_ROOT}/${LOG_FILE}"
}

# Test API endpoint
test_api_endpoint() {
    print_header "Teste API-Endpoint"
    
    log_info "Sende POST /api/v1/analyze..."
    
    RESPONSE=$(curl -s -X POST "http://localhost:${PORT}/api/v1/analyze" \
        -H "Content-Type: application/json" \
        -d "{
            \"repo_path\": \"${REPO_PATH}\",
            \"use_parallel\": true,
            \"enable_ml_prediction\": false,
            \"enable_auto_refactor\": false,
            \"max_workers\": 2
        }" \
        -w "\n%{http_code}")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n-1)
    
    if [[ "$HTTP_CODE" == "200" ]]; then
        log_info "HTTP Status: ${GREEN}${HTTP_CODE} OK${NC}"
    else
        log_error "HTTP Status: ${RED}${HTTP_CODE}${NC}"
    fi
    
    log_info "Response:"
    echo "$BODY" | python -m json.tool 2>/dev/null || echo "$BODY"
    
    # Extract job_id for further tests
    JOB_ID=$(echo "$BODY" | python -c "import sys, json; print(json.load(sys.stdin).get('job_id', ''))" 2>/dev/null || echo "")
    
    if [[ -n "$JOB_ID" ]]; then
        log_info "Job-ID extrahiert: ${CYAN}${JOB_ID}${NC}"
        echo "$JOB_ID"
    else
        log_warn "Keine Job-ID extrahiert"
        echo ""
    fi
}

# Test WebSocket connection
test_websocket() {
    local JOB_ID="$1"
    
    if [[ -z "$JOB_ID" ]]; then
        log_warn "Keine Job-ID für WebSocket-Test"
        return
    fi
    
    print_header "Teste WebSocket-Verbindung"
    
    # Check if websocat is available
    if command -v websocat &> /dev/null; then
        log_info "Verbinde mit WebSocket: ws://localhost:${PORT}/ws/results/${JOB_ID}"
        log_warn "Timeout nach 5 Sekunden..."
        
        timeout 5 websocat "ws://localhost:${PORT}/ws/results/${JOB_ID}" 2>&1 || true
    else
        log_warn "websocat nicht installiert. Installieren mit:"
        echo "  sudo apt install websocat"
        echo "  oder: cargo install websocat"
        echo ""
        log_info "Alternativ im Browser testen:"
        echo "  http://localhost:${PORT}"
    fi
}

# Test job status
test_job_status() {
    local JOB_ID="$1"
    
    if [[ -z "$JOB_ID" ]]; then
        log_warn "Keine Job-ID für Status-Test"
        return
    fi
    
    print_header "Teste Job-Status"
    
    log_info "Frage Job-Status ab..."
    
    RESPONSE=$(curl -s "http://localhost:${PORT}/api/v1/jobs/${JOB_ID}")
    
    echo "$RESPONSE" | python -m json.tool 2>/dev/null || echo "$RESPONSE"
}

# Show log tail
show_logs() {
    print_header "Live-Logs (letzte 50 Zeilen)"
    
    if [[ -f "${PROJECT_ROOT}/${LOG_FILE}" ]]; then
        log_info "Verfolge Log-Datei: ${LOG_FILE}"
        log_warn "Drücke STRG+C zum Beenden"
        echo ""
        tail -f "${PROJECT_ROOT}/${LOG_FILE}" | grep --color=auto -E "(Job|WebSocket|Analyse|ERROR|DEBUG|INFO)"
    else
        log_error "Log-Datei nicht gefunden: ${PROJECT_ROOT}/${LOG_FILE}"
    fi
}

# Health check
health_check() {
    print_header "Health Check"
    
    log_info "Prüfe Server-Status..."
    
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${PORT}/api/v1/status" || echo "000")
    
    if [[ "$RESPONSE" == "200" ]]; then
        log_info "Server-Status: ${GREEN}healthy${NC}"
        return 0
    else
        log_error "Server-Status: ${RED}unreachable (HTTP ${RESPONSE})${NC}"
        return 1
    fi
}

# Cleanup
cleanup() {
    echo ""
    log_info "Cleanup..."
    # Add cleanup tasks here if needed
}

# Main
main() {
    trap cleanup EXIT
    
    print_header "GlitchHunter Web-UI Debug-Start"
    
    check_prerequisites
    
    echo ""
    log_info "Starte Backend-Server..."
    echo ""
    log_info "Öffne Browser: http://localhost:${PORT}"
    log_info "API-Dokumentation: http://localhost:${PORT}/docs"
    echo ""
    log_info "Drücke STRG+C zum Stoppen"
    echo ""
    
    # Start backend (this will block)
    start_backend
}

# Parse command line arguments
case "${1:-start}" in
    start)
        main
        ;;
    test)
        check_prerequisites
        # Wait for server to be ready
        sleep 2
        JOB_ID=$(test_api_endpoint)
        test_websocket "$JOB_ID"
        test_job_status "$JOB_ID"
        ;;
    logs)
        show_logs
        ;;
    health)
        health_check
        ;;
    *)
        echo "Usage: $0 {start|test|logs|health}"
        echo ""
        echo "Commands:"
        echo "  start  - Start backend server with debug logging (default)"
        echo "  test   - Run API and WebSocket tests"
        echo "  logs   - Show live logs"
        echo "  health - Check server health"
        echo ""
        exit 1
        ;;
esac
