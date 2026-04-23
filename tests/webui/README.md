# GlitchHunter Web-UI Tests

Integrationstests für die GlitchHunter Web-UI.

## Test-Dateien

- `test_webui_integration.py` - Umfassende Integrationstests für API, WebSocket und Job-Flow

## Voraussetzungen

```bash
# pytest installieren
pip install pytest pytest-asyncio

# Coverage (optional)
pip install pytest-cov
```

## Tests ausführen

### Alle Tests
```bash
pytest tests/webui/ -v
```

### Mit Coverage
```bash
pytest tests/webui/ --cov=ui.web.backend --cov-report=html
```

### Einzelne Test-Klassen
```bash
# API Endpoint Tests
pytest tests/webui/test_webui_integration.py::TestAnalyzeEndpoint -v

# WebSocket Tests
pytest tests/webui/test_webui_integration.py::TestWebSocket -v

# Job-Flow Tests
pytest tests/webui/test_webui_integration.py::TestJobFlow -v

# Coordinator Integration
pytest tests/webui/test_webui_integration.py::TestParallelSwarmCoordinator -v
```

### Einzelne Tests
```bash
pytest tests/webui/test_webui_integration.py::TestAnalyzeEndpoint::test_analyze_endpoint_creates_job -v
```

## Test-Abdeckung

### API Endpoints
- [x] `POST /api/v1/analyze` - Job-Erstellung
- [x] `GET /api/v1/jobs` - Job-Liste
- [x] `GET /api/v1/jobs/{job_id}` - Einzelner Job
- [x] `GET /api/v1/results/{job_id}` - Ergebnisse
- [x] `GET /api/v1/status` - Server-Status

### WebSocket
- [x] Verbindungsaufbau
- [x] Initiale Status-Nachricht
- [x] Ping/Pong Keep-Alive
- [x] Error-Handling

### Job-Flow
- [x] Job-Erstellung (pending)
- [x] Status-Übergänge
- [x] Abschluss (completed)
- [x] Multiple parallele Jobs

### Error-Handling
- [x] Ungültige Payloads
- [x] Fehlende Felder
- [x] Nicht-existierende Jobs

### Performance
- [x] Response-Time Tests

## Debugging

### Test mit Logging
```bash
pytest tests/webui/ -v -s --log-cli-level=DEBUG
```

### Test mit pdb
```bash
pytest tests/webui/test_webui_integration.py::TestAnalyzeEndpoint::test_analyze_endpoint_creates_job --pdb
```

## Bekannte Einschränkungen

1. **Background-Tasks**: Da Analyse-Jobs asynchron laufen, müssen Tests pollen oder warten.
   - Lösung: `time.sleep()` mit Timeout-Logik
   
2. **WebSocket im TestClient**: Starlette TestClient hat Limitationen bei WebSockets.
   - Lösung: Echte Browser-Tests mit Playwright für vollständige E2E-Tests

3. **Externe Dependencies**: ParallelSwarmCoordinator benötigt ggf. externe Tools.
   - Lösung: Mocking für Unit-Tests, echte Tests nur in CI/CD

## Nächste Schritte

- [ ] E2E-Tests mit Playwright
- [ ] Performance-Tests mit Last-Simulation
- [ ] Visual Regression Tests für Frontend
