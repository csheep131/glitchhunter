# GlitchHunter Web-UI Audit-Plan

**Erstellt:** 2026-04-21  
**Status:** Draft  
**Priorität:** Hoch  

---

## 1. Problem-Analyse

### Beobachtetes Symptom
- Web-UI startet erfolgreich (Server läuft auf Port 6262)
- Bei Klick auf "Analyse starten" wird Request an `/api/v1/analyze` gesendet
- UI zeigt **sofort "completed"** an, ohne dass eine tatsächliche Analyse stattfindet
- Keine echten Analyse-Ergebnisse sichtbar

### Erwartetes Verhalten
1. User klickt "Analyse starten"
2. Request wird an Backend gesendet
3. Job wird erstellt (Status: `pending`)
4. Background-Task startet Analyse (Status: `running`)
5. Live-Updates via WebSocket (Fortschritt, Findings)
6. Analyse abgeschlossen (Status: `completed`)
7. Ergebnisse werden angezeigt

### Kritische Hypothesen (priorisiert)

#### **Hypothese 1: WebSocket-Verbindung wird nicht korrekt hergestellt** ⭐⭐⭐
**Warum plausibel:**
- Frontend-Code erstellt WebSocket erst NACH成功 des `/api/v1/analyze` Requests
- Wenn WebSocket-Verbindung scheitert, empfängt Frontend keine Status-Updates
- UI bleibt im Anfangszustand oder zeigt fälschlich "completed" an

**Prüfung:**
- Browser-Konsole auf WebSocket-Fehler prüfen
- Network Tab: WebSocket-Connection zu `/ws/results/{job_id}`
- Backend-Logs: Wird `websocket_results()` aufgerufen?

**Bestätigung wenn:**
- WebSocket-Fehler in Browser-Konsole
- Connection wird sofort getrennt
- Backend loggt WebSocket-Disconnect ohne vorherige Messages

---

#### **Hypothese 2: Background-Task wird nicht ausgeführt** ⭐⭐⭐
**Warum plausibel:**
- `run_analysis()` wird via `background_tasks.add_task()` registriert
- Wenn Task sofort exceptiont, wird Job auf "failed" gesetzt
- Frontend erhält möglicherweise nur "complete" ohne Details

**Prüfung:**
- Backend-Logs auf Exceptions in `run_analysis()` prüfen
- Log-Level auf DEBUG setzen
- `ParallelSwarmCoordinator.run_swarm_parallel()` Aufruf prüfen

**Bestätigung wenn:**
- Log-Eintrag: "Analyse {job_id} fehlgeschlagen: ..."
- Job-Status ist "failed" statt "completed"
- `ParallelSwarmCoordinator` wirft Exception

---

#### **Hypothese 3: Job-Status wird falsch initialisiert** ⭐⭐
**Warum plausibel:**
- `JobManager.create_job()` setzt Status auf "pending"
- `run_analysis()` setzt Status auf "running" via `update_job_status()`
- Wenn `broadcast()` vor WebSocket-Connect aufgerufen wird, geht Update verloren

**Prüfung:**
- Log-Reihenfolge prüfen: Job-Erstellung → WebSocket-Connect → Broadcast
- `job_manager._jobs` Inspektion während Analyse

**Bestätigung wenn:**
- Broadcast wird ausgeführt bevor WebSocket verbunden ist
- Job-Status bleibt auf "pending" stehen

---

#### **Hypothese 4: Frontend-Logik zeigt Status nicht korrekt an** ⭐⭐
**Warum plausibel:**
- `updateStatus()` Funktion wird nur bei WebSocket `onmessage` aufgerufen
- Wenn WebSocket-Nachrichten nicht korrekt geparst werden, UI aktualisiert nicht
- Button wird bei `complete` wieder enabled → sieht aus wie "sofort fertig"

**Prüfung:**
- Browser-Konsole: `console.log()` der WebSocket-Nachrichten
- `websocket.onmessage` Handler prüfen
- Status-Badge im DOM inspizieren

**Bestätigung wenn:**
- WebSocket-Nachrichten kommen an, werden aber nicht verarbeitet
- `data.type` entspricht nicht erwarteten Werten

---

#### **Hypothese 5: ParallelSwarmCoordinator initialisiert falsch** ⭐
**Warum plausibel:**
- `ParallelSwarmCoordinator(max_workers=max_workers)` wird in `run_analysis()` erstellt
- Wenn Import fehlt oder Initialisierung exceptiont, schlägt Analyse fehl

**Prüfung:**
- Backend-Logs auf Import-Fehler prüfen
- `ParallelSwarmCoordinator` direkt testen

**Bestätigung wenn:**
- Log: "ImportError" oder "AttributeError"
- Test mit minimalem Repo schlägt fehl

---

## 2. Debugging-Schritte

### Schritt 1: Logging-Konfiguration aktivieren

**Ziel:** Maximale Sichtbarkeit in Backend-Logs

```bash
# Backend mit erhöhtem Log-Level starten
cd /home/schaf/projects/glitchhunter
python -m uvicorn ui.web.backend.app:app \
  --host 0.0.0.0 \
  --port 6262 \
  --reload \
  --log-level debug
```

**Alternativ via Environment:**
```bash
export LOG_LEVEL=DEBUG
python -c "from ui.web.backend.app import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=6262, log_level='debug')"
```

**Erwartete Logs:**
```
[DEBUG]  Job {job_id[:8]} erstellt für {repo_path}
[DEBUG]  WebSocket zu Job {job_id[:8]} hinzugefügt
[DEBUG]  Job {job_id[:8]} Status: running
[INFO]   Analyse {job_id[:8]} abgeschlossen: {n} findings
```

---

### Schritt 2: Browser Developer Tools

**Console Tab:**
```javascript
// Manuelles Logging aktivieren (vor Analyse starten)
window.DEBUG_WEBSOCKET = true;
```

**Network Tab Filter:**
- `/api/v1/analyze` → Request/Response inspizieren
- `/ws/results/*` → WebSocket Frames ansehen
- Auf Status-Codes achten (200, 400, 500?)

**Application Tab:**
- WebSocket Connections prüfen
- Gibt es aktive WebSocket-Verbindungen?

---

### Schritt 3: API-Endpoints manuell testen

**Mit curl:**
```bash
# 1. Analyse starten
curl -X POST http://localhost:6262/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "/home/schaf/projects/glitchhunter",
    "use_parallel": true,
    "enable_ml_prediction": false,
    "enable_auto_refactor": false,
    "max_workers": 2
  }' | jq

# Erwartete Response:
# {
#   "job_id": "...",
#   "status": "pending",
#   "message": "Analyse gestartet"
# }
```

**Job-Status abfragen:**
```bash
# 2. Job-Status prüfen
curl http://localhost:6262/api/v1/jobs/{JOB_ID} | jq

# 3. Alle Jobs ansehen
curl http://localhost:6262/api/v1/jobs | jq
```

**WebSocket testen (mit websocat):**
```bash
# WebSocket-Client installieren
sudo apt install websocat  # oder: cargo install websocat

# WebSocket verbinden (JOB_ID ersetzen)
websocat ws://localhost:6262/ws/results/{JOB_ID}

# Sollte JSON empfangen:
# {"type": "status", "status": "pending"}
```

---

### Schritt 4: Backend-Code instrumentieren

**Temporäre Debug-Logs in `app.py` einfügen:**

```python
# In run_analysis() VOR Coordinator-Aufruf
logger.error(f"DEBUG: run_analysis gestartet für Job {job_id[:8]}")
logger.error(f"DEBUG: repo_path={repo_path}, use_parallel={use_parallel}")

# NACH Coordinator-Aufruf
logger.error(f"DEBUG: Coordinator zurück, result.findings={len(result.findings)}")

# In websocket_results()
logger.error(f"DEBUG: WebSocket verbunden für Job {job_id[:8]}")
logger.error(f"DEBUG: Job exists: {job_id in job_manager._jobs}")
```

**Warum `logger.error()`:** Damit Logs sicher in der Konsole erscheinen, auch wenn Log-Level falsch konfiguriert ist.

---

### Schritt 5: Minimalen Test-Case erstellen

**Test-Skript `scripts/test_webui_minimal.py`:**
```python
#!/usr/bin/env python3
"""
Minimaler Test für Web-UI Backend.
"""
import asyncio
import sys
from pathlib import Path

# src/ zu sys.path hinzufügen
SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from agent.parallel_swarm import ParallelSwarmCoordinator

async def test_coordinator():
    """Testet ParallelSwarmCoordinator direkt."""
    repo_path = Path("/home/schaf/projects/glitchhunter")
    
    print(f"Teste Coordinator mit Repo: {repo_path}")
    print(f"Repo exists: {repo_path.exists()}")
    
    coordinator = ParallelSwarmCoordinator(max_workers=2)
    
    try:
        result = await coordinator.run_swarm_parallel(str(repo_path))
        print(f"✓ Analyse erfolgreich")
        print(f"  Findings: {len(result.findings)}")
        print(f"  Errors: {result.errors}")
        print(f"  Execution Time: {result.execution_time:.2f}s")
        return True
    except Exception as e:
        print(f"✗ Analyse fehlgeschlagen: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_coordinator())
    sys.exit(0 if success else 1)
```

---

### Schritt 6: Job-Manager State inspizieren

**Interaktiver Python-Check:**
```python
from ui.web.backend.app import job_manager

# Alle Jobs ansehen
for job_id, job in job_manager._jobs.items():
    print(f"Job {job_id[:8]}:")
    print(f"  Status: {job['status']}")
    print(f"  Repo: {job['repo_path']}")
    print(f"  Result: {job.get('result')}")
    print(f"  WebSockets: {len(job_manager._websockets.get(job_id, []))}")
```

---

## 3. Logging-Konfiguration

### Empfohlene Logging-Konfiguration für Debugging

**In `config.yaml` temporär ändern:**
```yaml
logging:
  level: "DEBUG"  # Von INFO auf DEBUG
  file: "logs/glitchhunter_webui.log"
  
  # Stack-spezifisch
  stack_a:
    level: "DEBUG"
  stack_b:
    level: "DEBUG"
```

**Logging-Datei einsehen:**
```bash
# Live-Mitlesen
tail -f logs/glitchhunter_webui.log | grep -E "(Job|WebSocket|Analyse|ERROR)"

# Letzte 100 Zeilen
tail -100 logs/glitchhunter_webui.log
```

### Request-Logging aktivieren

**Middleware in `app.py` hinzufügen (temporär):**
```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response
```

### WebSocket-Logging erweitern

**In `websocket_results()` einfügen:**
```python
async def websocket_results(websocket: WebSocket, job_id: str):
    logger.info(f"WebSocket-Verbindung angefordert für Job {job_id[:8]}")
    
    await job_manager.add_websocket(job_id, websocket)
    logger.info(f"WebSocket hinzugefügt, aktive Connections: {len(job_manager._websockets[job_id])}")
    
    try:
        job = job_manager.get_job(job_id)
        if job:
            logger.info(f"Sende initialen Status: {job['status']}")
            await websocket.send_json({
                "type": "status",
                "status": job["status"],
            })
        
        while True:
            data = await websocket.receive_text()
            logger.debug(f"WebSocket-Nachricht empfangen: {data}")
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect as e:
        logger.warning(f"WebSocket-Verbindung getrennt: {e}")
    except Exception as e:
        logger.error(f"WebSocket-Fehler: {e}", exc_info=True)
    finally:
        job_manager.remove_websocket(job_id, websocket)
        logger.info(f"WebSocket entfernt")
```

---

## 4. Test-Plan

### Test 1: API Endpoint `/api/v1/analyze`

**Zu testende Datei:** `tests/webui/test_webui_integration.py`

```python
import pytest
from fastapi.testclient import TestClient
from ui.web.backend.app import app, job_manager

client = TestClient(app)

def test_analyze_endpoint_creates_job():
    """Testet dass /api/v1/analyze einen Job erstellt."""
    response = client.post("/api/v1/analyze", json={
        "repo_path": "/tmp/test_repo",
        "use_parallel": True,
        "enable_ml_prediction": False,
        "enable_auto_refactor": False,
        "max_workers": 2,
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"
    
    # Job muss im JobManager existieren
    job = job_manager.get_job(data["job_id"])
    assert job is not None
    assert job["repo_path"] == "/tmp/test_repo"
```

---

### Test 2: WebSocket Verbindung

```python
from starlette.testclient import TestClient as WebSocketTestClient
from starlette.websockets import WebSocketDisconnect

def test_websocket_connection():
    """Testet WebSocket-Verbindung."""
    # Erst Job erstellen
    response = client.post("/api/v1/analyze", json={
        "repo_path": "/tmp/test_repo",
        "use_parallel": False,
        "max_workers": 1,
    })
    job_id = response.json()["job_id"]
    
    # WebSocket verbinden
    with WebSocketTestClient(app) as websocket_client:
        websocket_client.send_json({"type": "connect"})
        
        # Initiale Status-Nachricht sollte kommen
        data = websocket_client.receive_json()
        assert data["type"] == "status"
        assert data["status"] in ["pending", "running", "completed"]
```

---

### Test 3: Job-Flow (End-to-End)

```python
import time

def test_complete_job_flow():
    """Testet kompletten Job-Flow von Erstellung bis Abschluss."""
    # 1. Analyse starten
    response = client.post("/api/v1/analyze", json={
        "repo_path": "/home/schaf/projects/glitchhunter",
        "use_parallel": False,  # Sequential für schnelleren Test
        "max_workers": 1,
    })
    job_id = response.json()["job_id"]
    
    # 2. Status polling (da Background-Task asynchron)
    for _ in range(30):  # Max 30 Sekunden warten
        time.sleep(1)
        
        job_response = client.get(f"/api/v1/jobs/{job_id}")
        job = job_response.json()["job"]
        
        if job["status"] == "completed":
            break
        elif job["status"] == "failed":
            pytest.fail(f"Job fehlgeschlagen: {job.get('errors', [])}")
    
    # 3. Ergebnis prüfen
    assert job["status"] == "completed"
    assert job.get("result") is not None
    assert "findings" in job["result"]
```

---

### Test 4: ParallelSwarmCoordinator Integration

```python
import asyncio
import pytest
from pathlib import Path
from agent.parallel_swarm import ParallelSwarmCoordinator

@pytest.mark.asyncio
async def test_parallel_coordinator_small_repo():
    """Testet ParallelSwarmCoordinator mit kleinem Repo."""
    coordinator = ParallelSwarmCoordinator(max_workers=2)
    
    # Kleines Test-Repo verwenden
    test_repo = Path("/tmp/test_small_repo")
    test_repo.mkdir(parents=True, exist_ok=True)
    (test_repo / "test.py").write_text("def hello(): pass\n")
    
    result = await coordinator.run_swarm_parallel(str(test_repo))
    
    assert result.success is True
    assert isinstance(result.findings, list)
    assert result.execution_time > 0
```

---

### Test 5: Error Handling

```python
def test_analyze_nonexistent_repo():
    """Testet Error-Handling bei nicht-existierendem Repo."""
    response = client.post("/api/v1/analyze", json={
        "repo_path": "/nonexistent/path",
        "use_parallel": True,
        "max_workers": 2,
    })
    
    # Sollte trotzdem Job erstellen (Fehler kommt im Background)
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    
    # Warten bis Background-Task fertig
    time.sleep(5)
    
    # Job sollte "failed" sein
    job_response = client.get(f"/api/v1/jobs/{job_id}")
    job = job_response.json()["job"]
    assert job["status"] == "failed"
    assert len(job["errors"]) > 0
```

---

## 5. Fix-Plan

### Fix 1: WebSocket-Initialisierung reparieren

**Problem:** WebSocket wird möglicherweise nicht korrekt initialisiert oder getrennt bevor Status-Updates kommen.

**Lösung in `app.py`:**
```python
async def websocket_results(websocket: WebSocket, job_id: str):
    """WebSocket für Live-Ergebnisse."""
    logger.info(f"WebSocket-Request für Job {job_id[:8]}")
    
    # WebSocket akzeptieren VOR add_websocket
    await websocket.accept()
    logger.info(f"WebSocket akzeptiert für Job {job_id[:8]}")
    
    # Erst dann zur Job-Liste hinzufügen
    if job_id in job_manager._websockets:
        job_manager._websockets[job_id].append(websocket)
        logger.info(f"WebSocket zu Job {job_id[:8]} hinzugefügt")
    else:
        logger.warning(f"Job {job_id[:8]} existiert nicht in _websockets")
        await websocket.close()
        return
    
    try:
        # Initialen Status senden
        job = job_manager.get_job(job_id)
        if job:
            logger.info(f"Sende initialen Status: {job['status']}")
            await websocket.send_json({
                "type": "status",
                "status": job["status"],
                "job_id": job_id,
            })
        else:
            logger.error(f"Job {job_id[:8]} nicht gefunden")
            await websocket.send_json({
                "type": "error",
                "error": f"Job {job_id[:8]} nicht gefunden",
            })
            return
        
        # Keep-Alive Loop
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0  # 60s Timeout für Keep-Alive
                )
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Keep-Alive Timeout - Connection prüfen
                continue
    
    except WebSocketDisconnect as e:
        logger.info(f"WebSocket {job_id[:8]} disconnected: {e}")
    except Exception as e:
        logger.error(f"WebSocket-Fehler {job_id[:8]}: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "error": str(e),
            })
        except Exception:
            pass
    finally:
        job_manager.remove_websocket(job_id, websocket)
        logger.info(f"WebSocket {job_id[:8]} entfernt")
```

---

### Fix 2: Background-Task Exception-Handling verbessern

**Problem:** Exceptions in `run_analysis()` werden nicht korrekt geloggt oder an Frontend kommuniziert.

**Lösung in `app.py`:**
```python
async def run_analysis(
    job_id: str,
    repo_path: str,
    use_parallel: bool,
    enable_ml: bool,
    enable_refactor: bool,
    max_workers: int,
):
    """Führt Analyse im Hintergrund aus."""
    logger.info(f"run_analysis gestartet für Job {job_id[:8]}")
    logger.info(f"  repo_path: {repo_path}")
    logger.info(f"  use_parallel: {use_parallel}")
    logger.info(f"  max_workers: {max_workers}")
    
    try:
        # Status: running
        logger.info(f"Setze Job {job_id[:8]} auf 'running'")
        job_manager.update_job_status(job_id, "running")
        
        # Broadcast nur wenn WebSocket verbunden
        try:
            await job_manager.broadcast(job_id, {"type": "status", "status": "running"})
            logger.debug(f"Broadcast 'running' gesendet")
        except Exception as broadcast_error:
            logger.warning(f"Broadcast fehlgeschlagen (kein WebSocket?): {broadcast_error}")
        
        # Coordinator auswählen und ausführen
        logger.info(f"Starte Coordinator (use_parallel={use_parallel})")
        
        if use_parallel:
            logger.info(f"Erstelle ParallelSwarmCoordinator(max_workers={max_workers})")
            coordinator = ParallelSwarmCoordinator(max_workers=max_workers)
            logger.info(f"Rufe run_swarm_parallel('{repo_path}') auf")
            result = await coordinator.run_swarm_parallel(repo_path)
            logger.info(f"run_swarm_parallel abgeschlossen: {len(result.findings)} findings")
        else:
            logger.info(f"Erstelle SwarmCoordinator()")
            coordinator = SwarmCoordinator()
            swarm_result = await coordinator.run_swarm(repo_path)
            
            result = ParallelExecutionResult(
                success=swarm_result.get("success", False),
                findings=[],  # TODO: Konvertierung implementieren
                errors=swarm_result.get("errors", []),
                execution_time=swarm_result.get("execution_time", 0),
            )
        
        # Ergebnis speichern
        logger.info(f"Speichere Ergebnis für Job {job_id[:8]}")
        job_manager.update_job_status(
            job_id,
            "completed",
            result=result,
            completed_at=datetime.now(),
        )
        
        # WebSocket Broadcast
        await job_manager.broadcast(job_id, {
            "type": "complete",
            "status": "completed",
            "findings_count": len(result.findings),
            "execution_time": result.execution_time,
            "success": result.success,
        })
        
        logger.info(f"Analyse {job_id[:8]} abgeschlossen: {len(result.findings)} findings in {result.execution_time:.2f}s")
        
    except FileNotFoundError as e:
        logger.error(f"Datei nicht gefunden: {e}")
        job_manager.update_job_status(job_id, "failed", errors=[f"File not found: {e}"])
        await job_manager.broadcast(job_id, {
            "type": "error",
            "status": "failed",
            "error": f"Datei nicht gefunden: {e}",
        })
        
    except PermissionError as e:
        logger.error(f"Keine Berechtigung: {e}")
        job_manager.update_job_status(job_id, "failed", errors=[f"Permission denied: {e}"])
        await job_manager.broadcast(job_id, {
            "type": "error",
            "status": "failed",
            "error": f"Keine Berechtigung: {e}",
        })
        
    except Exception as e:
        logger.error(f"Analyse {job_id[:8]} fehlgeschlagen: {e}", exc_info=True)
        import traceback
        error_details = f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}"
        job_manager.update_job_status(job_id, "failed", errors=[error_details])
        await job_manager.broadcast(job_id, {
            "type": "error",
            "status": "failed",
            "error": error_details,
        })
```

---

### Fix 3: Frontend WebSocket-Logik verbessern

**Problem:** Frontend-WebSocket-Handler verarbeitet möglicherweise nicht alle Nachrichtentypen korrekt.

**Lösung in `index.html`:**
```javascript
function connectWebSocket(jobId) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/results/${jobId}`;
    
    console.log('Verbinde WebSocket:', wsUrl);
    websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
        console.log('✓ WebSocket verbunden');
        updateStatus('connecting');
    };

    websocket.onmessage = (event) => {
        console.log('WebSocket-Nachricht empfangen:', event.data);
        
        let data;
        try {
            data = JSON.parse(event.data);
        } catch (e) {
            console.error('Fehler beim Parsen der WebSocket-Nachricht:', e);
            return;
        }
        
        console.log('Geparste Nachricht:', data);

        if (data.type === 'status') {
            console.log('Status-Update:', data.status);
            updateStatus(data.status);
            if (data.status === 'running') {
                document.getElementById('progressFill').style.width = '50%';
            }
        } else if (data.type === 'complete') {
            console.log('Analyse abgeschlossen:', data);
            updateStatus('completed');
            document.getElementById('progressFill').style.width = '100%';
            document.getElementById('stat-findings').textContent = data.findings_count || '0';
            
            const btn = document.getElementById('analyzeBtn');
            btn.disabled = false;
            btn.textContent = '🚀 Analyse starten';
            
            // Ergebnisse laden
            loadResults(jobId);
        } else if (data.type === 'error') {
            console.error('Analyse fehlgeschlagen:', data);
            updateStatus('failed');
            alert('Analyse fehlgeschlagen: ' + (data.error || 'Unbekannter Fehler'));
            
            const btn = document.getElementById('analyzeBtn');
            btn.disabled = false;
            btn.textContent = '🚀 Analyse starten';
        } else {
            console.log('Unbekannter Nachrichtentyp:', data.type);
        }
    };

    websocket.onerror = (error) => {
        console.error('✗ WebSocket-Fehler:', error);
    };

    websocket.onclose = (event) => {
        console.log('WebSocket getrennt:', event.code, event.reason);
        if (event.code !== 1000) {
            // Nicht-normaler Disconnect
            updateStatus('disconnected');
        }
    };

    // Keep-Alive
    setInterval(() => {
        if (websocket.readyState === WebSocket.OPEN) {
            websocket.send('ping');
        }
    }, 30000);
}
```

---

### Fix 4: Job-Manager Thread-Safety

**Problem:** `JobManager` wird von Background-Task und WebSocket-Handler gleichzeitig verwendet.

**Lösung:** Async-Locks hinzufügen (optional, für robuste Lösung):

```python
import asyncio

class JobManager:
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._websockets: Dict[str, List[WebSocket]] = {}
        self._lock = asyncio.Lock()  # NEW
    
    async def update_job_status(self, job_id: str, status: str, **kwargs):
        """Aktualisiert Job-Status (thread-safe)."""
        async with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = status
                self._jobs[job_id].update(kwargs)
                logger.debug(f"Job {job_id[:8]} Status: {status}")
    
    async def broadcast(self, job_id: str, message: Dict[str, Any]):
        """Sendet Nachricht an alle WebSocket-Clients."""
        async with self._lock:
            if job_id not in self._websockets:
                return
            websockets_copy = self._websockets[job_id].copy()
        
        disconnected = []
        for ws in websockets_copy:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)

        async with self._lock:
            for ws in disconnected:
                if ws in self._websockets.get(job_id, []):
                    self._websockets[job_id].remove(ws)
```

---

## 6. Validierung

### Checkliste für erfolgreiche Reparatur

- [ ] **API Endpoint funktioniert**
  - `POST /api/v1/analyze`返回 200 mit Job-ID
  - Job wird im JobManager erstellt
  - Response enthält korrekte Daten

- [ ] **Background-Task läuft**
  - `run_analysis()` wird ausgeführt
  - Job-Status wechselt von `pending` → `running` → `completed`
  - Logs zeigen Coordinator-Aufruf

- [ ] **WebSocket-Verbindung steht**
  - Browser-Konsole: "WebSocket verbunden"
  - Network Tab: WebSocket-Connection mit Status 101
  - Initiale Status-Nachricht wird empfangen

- [ ] **Live-Updates funktionieren**
  - Status-Änderungen werden via Broadcast gesendet
  - Frontend empfängt und verarbeitet Updates
  - Progress-Bar bewegt sich

- [ ] **Ergebnisse werden angezeigt**
  - Nach "completed" werden Findings geladen
  - `/api/v1/results/{job_id}`返回 korrekte Daten
  - UI zeigt Findings-Liste an

- [ ] **Error-Handling funktioniert**
  - Bei Fehlern wird Status `failed` gesetzt
  - Error-Message wird via WebSocket gesendet
  - Frontend zeigt Fehler an

---

### Manuelle Testschritte

**1. Backend starten:**
```bash
cd /home/schaf/projects/glitchhunter
python -m uvicorn ui.web.backend.app:app --host 0.0.0.0 --port 6262 --reload --log-level debug
```

**2. Browser öffnen:**
```
http://localhost:6262
```

**3. Analyse starten:**
- Repository-Pfad eingeben: `/home/schaf/projects/glitchhunter`
- Optionen: Parallele Analyse ✓, ML Prediction ✗
- "Analyse starten" klicken

**4. Browser-Konsole prüfen:**
```
✓ WebSocket verbunden
WebSocket-Nachricht empfangen: {"type":"status","status":"pending"}
WebSocket-Nachricht empfangen: {"type":"status","status":"running"}
WebSocket-Nachricht empfangen: {"type":"complete","status":"completed",...}
```

**5. Backend-Logs prüfen:**
```
[INFO] Job {id} erstellt für /home/schaf/projects/glitchhunter
[INFO] WebSocket-Request für Job {id}
[INFO] WebSocket akzeptiert für Job {id}
[INFO] Setze Job {id} auf 'running'
[INFO] Erstelle ParallelSwarmCoordinator(max_workers=4)
[INFO] Rufe run_swarm_parallel(...) auf
[INFO] run_swarm_parallel abgeschlossen: N findings
[INFO] Analyse {id} abgeschlossen: N findings in X.XXs
```

**6. Ergebnisse prüfen:**
- Progress-Bar geht auf 100%
- Status-Badge zeigt "completed" (grün)
- "Gefundene Issues" Zähler aktualisiert

---

### Automatisierte Tests ausführen

**Nach Implementierung der Fixes:**
```bash
cd /home/schaf/projects/glitchhunter

# Neue Web-UI-Tests ausführen
pytest tests/webui/test_webui_integration.py -v

# Mit Coverage
pytest tests/webui/ --cov=ui.web.backend --cov-report=html

# Einzelne Tests
pytest tests/webui/test_webui_integration.py::test_analyze_endpoint_creates_job -v
pytest tests/webui/test_webui_integration.py::test_websocket_connection -v
pytest tests/webui/test_webui_integration.py::test_complete_job_flow -v
```

---

## Anhang: Häufige Fehlerbilder

### Fehler 1: "WebSocket closed immediately"
**Ursache:** WebSocket wird nicht korrekt akzeptiert oder Job existiert nicht.

**Lösung:**
- `await websocket.accept()` VOR `add_websocket()` aufrufen
- Prüfen ob Job in `job_manager._websockets` existiert

---

### Fehler 2: "Job not found" im WebSocket
**Ursache:** Job wurde gelöscht oder WebSocket-Handler hat falsche Job-ID.

**Lösung:**
- Job-ID in Frontend korrekt speichern
- Job nicht vorzeitig aufräumen

---

### Fehler 3: "run_analysis never called"
**Ursache:** `background_tasks.add_task()` wird nicht ausgeführt.

**Lösung:**
- FastAPI `BackgroundTasks` korrekt injizieren
- Funktionssignatur prüfen: `async def analyze_repository(..., background_tasks: BackgroundTasks)`

---

### Fehler 4: "ParallelSwarmCoordinator throws exception"
**Ursache:** Import-Fehler, falsche Initialisierung, oder Repo-Pfad ungültig.

**Lösung:**
- Import prüfen: `from agent.parallel_swarm import ParallelSwarmCoordinator`
- Repo-Pfad validieren bevor Coordinator erstellt wird
- Exception-Logging mit `exc_info=True`

---

### Fehler 5: "Frontend shows completed immediately"
**Ursache:** WebSocket-Nachricht vom Typ "complete" wird sofort gesendet, oder Frontend-Logik ist falsch.

**Lösung:**
- Backend: Broadcast nur NACH tatsächlicher Analyse senden
- Frontend: `updateStatus()` nur bei korrekten Nachrichtentypen aufrufen
- Console-Logging im Frontend aktivieren

---

## Nächste Schritte

1. **Debug-Modus aktivieren** (Logging auf DEBUG)
2. **Manuelle Tests durchführen** (curl, Browser-Konsole)
3. **Root-Cause identifizieren** (Logs analysieren)
4. **Fix implementieren** (siehe Fix-Plan)
5. **Tests schreiben** (siehe Test-Plan)
6. **Validierung** (Checkliste abarbeiten)

---

**Dokument aktualisiert:** 2026-04-21  
**Autor:** GlitchHunter Debug-System
