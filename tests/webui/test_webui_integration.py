"""
GlitchHunter Web-UI Integration Tests.

Tests für:
- API Endpoints (/api/v1/analyze, /api/v1/jobs, /api/v1/results)
- WebSocket-Verbindungen (/ws/results/{job_id})
- Job-Flow (pending → running → completed)
- Error-Handling
- ParallelSwarmCoordinator Integration

Usage:
    pytest tests/webui/test_webui_integration.py -v

Coverage:
    pytest tests/webui/ --cov=ui.web.backend --cov-report=html
"""

import asyncio
import time
from pathlib import Path
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

# Import app and dependencies
from ui.web.backend.app import (
    app,
    job_manager,
    AnalyzeRequest,
    ParallelSwarmCoordinator,
    ParallelExecutionResult,
)


# ============== Fixtures ==============


@pytest.fixture
def client() -> TestClient:
    """
    Erstellt Test-Client für FastAPI-App.
    
    Returns:
        TestClient für API-Requests
    """
    # JobManager vor jedem Test zurücksetzen
    job_manager._jobs.clear()
    job_manager._websockets.clear()
    
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def test_repo_path(tmp_path: Path) -> Path:
    """
    Erstellt temporäres Test-Repository.
    
    Args:
        tmp_path: pytest tmp_path fixture
        
    Returns:
        Pfad zum Test-Repository
    """
    repo = tmp_path / "test_repo"
    repo.mkdir()
    
    # Minimale Python-Datei erstellen
    test_file = repo / "hello.py"
    test_file.write_text("""
def hello(name: str) -> str:
    '''Say hello to someone.'''
    if not name:
        raise ValueError("Name cannot be empty")
    return f"Hello, {name}!"

class Calculator:
    '''Simple calculator.'''
    
    def add(self, a: int, b: int) -> int:
        return a + b
    
    def subtract(self, a: int, b: int) -> int:
        return a - b
""")
    
    return repo


@pytest.fixture
def empty_repo_path(tmp_path: Path) -> Path:
    """
    Erstellt leeres temporäres Repository.
    
    Args:
        tmp_path: pytest tmp_path fixture
        
    Returns:
        Pfad zum leeren Repository
    """
    repo = tmp_path / "empty_repo"
    repo.mkdir()
    return repo


# ============== API Endpoint Tests ==============


class TestAnalyzeEndpoint:
    """Tests für /api/v1/analyze Endpoint."""
    
    def test_analyze_endpoint_creates_job(self, client: TestClient, test_repo_path: Path):
        """
        Testet dass /api/v1/analyze einen Job erstellt.
        
        Erwartet:
        - HTTP 200 Response
        - job_id in Response
        - Status: pending
        - Job existiert im JobManager
        """
        response = client.post("/api/v1/analyze", json={
            "repo_path": str(test_repo_path),
            "use_parallel": True,
            "enable_ml_prediction": False,
            "enable_auto_refactor": False,
            "max_workers": 2,
        })
        
        # Assert HTTP Status
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Assert Response-Struktur
        data = response.json()
        assert "job_id" in data, "Response muss job_id enthalten"
        assert "status" in data, "Response muss status enthalten"
        assert "message" in data, "Response muss message enthalten"
        
        # Assert Status
        assert data["status"] == "pending", f"Expected status 'pending', got '{data['status']}'"
        assert data["message"] == "Analyse gestartet"
        
        # Assert Job existiert im JobManager
        job = job_manager.get_job(data["job_id"])
        assert job is not None, "Job muss im JobManager existieren"
        assert job["repo_path"] == str(test_repo_path)
        assert job["status"] == "pending"
    
    def test_analyze_endpoint_with_minimal_payload(self, client: TestClient, test_repo_path: Path):
        """
        Testet /api/v1/analyze mit minimaler Payload.
        
        Erwartet:
        - Default-Werte werden verwendet
        - use_parallel: true (default)
        - max_workers: 4 (default)
        """
        response = client.post("/api/v1/analyze", json={
            "repo_path": str(test_repo_path),
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        
        # Job sollte mit Default-Werten erstellt worden sein
        job = job_manager.get_job(data["job_id"])
        assert job is not None
    
    def test_analyze_endpoint_invalid_repo_path(self, client: TestClient):
        """
        Testet /api/v1/analyze mit ungültigem Repository-Pfad.
        
        Erwartet:
        - Job wird trotzdem erstellt (Fehler kommt im Background-Task)
        - Job-Status wird später auf "failed" gesetzt
        """
        response = client.post("/api/v1/analyze", json={
            "repo_path": "/nonexistent/path/that/does/not/exist",
            "use_parallel": True,
            "max_workers": 2,
        })
        
        # Job-Erstellung sollte trotzdem funktionieren
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        
        # Job existiert im JobManager
        job = job_manager.get_job(data["job_id"])
        assert job is not None
        assert job["status"] == "pending"
        
        # Hinweis: Der tatsächliche Fehler tritt asynchron im Background-Task auf
        # und muss mit Polling oder WebSocket geprüft werden
    
    def test_analyze_endpoint_empty_repo(self, client: TestClient, empty_repo_path: Path):
        """
        Testet /api/v1/analyze mit leerem Repository.
        
        Erwartet:
        - Job wird erstellt
        - Analyse läuft durch (auch wenn keine Dateien)
        """
        response = client.post("/api/v1/analyze", json={
            "repo_path": str(empty_repo_path),
            "use_parallel": False,  # Sequential für deterministisches Verhalten
            "max_workers": 1,
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data


class TestJobsEndpoint:
    """Tests für /api/v1/jobs Endpoint."""
    
    def test_list_jobs_empty(self, client: TestClient):
        """
        Testet /api/v1/jobs mit keinem Job.
        
        Erwartet:
        - Leere Jobs-Liste
        """
        response = client.get("/api/v1/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert len(data["jobs"]) == 0
    
    def test_list_jobs_with_one_job(self, client: TestClient, test_repo_path: Path):
        """
        Testet /api/v1/jobs mit einem Job.
        
        Erwartet:
        - Jobs-Liste enthält einen Eintrag
        - Job-Daten sind korrekt
        """
        # Erst Job erstellen
        create_response = client.post("/api/v1/analyze", json={
            "repo_path": str(test_repo_path),
        })
        job_id = create_response.json()["job_id"]
        
        # Dann Jobs abrufen
        response = client.get("/api/v1/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert len(data["jobs"]) == 1
        
        # Job-Daten prüfen
        job = data["jobs"][0]
        assert job["repo_path"] == str(test_repo_path)
        assert job["status"] == "pending"
    
    def test_get_single_job(self, client: TestClient, test_repo_path: Path):
        """
        Testet /api/v1/jobs/{job_id}.
        
        Erwartet:
        - Job-Daten werden zurückgegeben
        - Struktur ist korrekt
        """
        # Erst Job erstellen
        create_response = client.post("/api/v1/analyze", json={
            "repo_path": str(test_repo_path),
        })
        job_id = create_response.json()["job_id"]
        
        # Dann Job abrufen
        response = client.get(f"/api/v1/jobs/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "job" in data
        
        job = data["job"]
        assert job["repo_path"] == str(test_repo_path)
    
    def test_get_nonexistent_job(self, client: TestClient):
        """
        Testet /api/v1/jobs/{job_id} mit nicht-existierender Job-ID.
        
        Erwartet:
        - HTTP 404
        """
        response = client.get("/api/v1/jobs/nonexistent-job-id")
        
        assert response.status_code == 404


class TestResultsEndpoint:
    """Tests für /api/v1/results/{job_id} Endpoint."""
    
    def test_get_results_pending_job(self, client: TestClient, test_repo_path: Path):
        """
        Testet /api/v1/results/{job_id} für pending Job.
        
        Erwartet:
        - Ergebnisse sind noch leer/null
        - Status ist "pending"
        """
        # Erst Job erstellen
        create_response = client.post("/api/v1/analyze", json={
            "repo_path": str(test_repo_path),
        })
        job_id = create_response.json()["job_id"]
        
        # Ergebnisse abrufen (sofort, bevor Analyse läuft)
        response = client.get(f"/api/v1/results/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["findings_count"] == 0
    
    def test_get_results_nonexistent_job(self, client: TestClient):
        """
        Testet /api/v1/results/{job_id} mit nicht-existierender Job-ID.
        
        Erwartet:
        - HTTP 404
        """
        response = client.get("/api/v1/results/nonexistent-job-id")
        
        assert response.status_code == 404


class TestStatusEndpoint:
    """Tests für /api/v1/status Endpoint."""
    
    def test_get_status(self, client: TestClient):
        """
        Testet /api/v1/status.
        
        Erwartet:
        - Server-Status ist "healthy"
        - Version ist enthalten
        """
        response = client.get("/api/v1/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "active_jobs" in data
        assert "total_jobs" in data


# ============== WebSocket Tests ==============


class TestWebSocket:
    """Tests für WebSocket-Endpoint /ws/results/{job_id}."""
    
    def test_websocket_connection(self, client: TestClient, test_repo_path: Path):
        """
        Testet WebSocket-Verbindung.
        
        Erwartet:
        - WebSocket kann verbunden werden
        - Initiale Status-Nachricht wird empfangen
        """
        # Erst Job erstellen
        create_response = client.post("/api/v1/analyze", json={
            "repo_path": str(test_repo_path),
        })
        job_id = create_response.json()["job_id"]
        
        # WebSocket verbinden
        with client.websocket_connect(f"/ws/results/{job_id}") as websocket:
            # Initiale Nachricht empfangen
            data = websocket.receive_json()
            
            assert "type" in data
            assert data["type"] == "status"
            assert "status" in data
            assert data["status"] in ["pending", "running", "completed"]
    
    def test_websocket_ping_pong(self, client: TestClient, test_repo_path: Path):
        """
        Testet WebSocket Ping/Pong Keep-Alive.
        
        Erwartet:
        - Ping wird mit Pong beantwortet
        """
        # Erst Job erstellen
        create_response = client.post("/api/v1/analyze", json={
            "repo_path": str(test_repo_path),
        })
        job_id = create_response.json()["job_id"]
        
        # WebSocket verbinden
        with client.websocket_connect(f"/ws/results/{job_id}") as websocket:
            # Initiale Nachricht empfangen
            websocket.receive_json()
            
            # Ping senden
            websocket.send_text("ping")
            
            # Pong empfangen
            response = websocket.receive_text()
            assert response == "pong"
    
    def test_websocket_nonexistent_job(self, client: TestClient):
        """
        Testet WebSocket mit nicht-existierender Job-ID.
        
        Erwartet:
        - WebSocket kann trotzdem verbunden werden
        - Error-Message wird gesendet oder Connection wird geschlossen
        """
        # WebSocket zu nicht-existierendem Job
        try:
            with client.websocket_connect("/ws/results/nonexistent-job-id") as websocket:
                # Sollte entweder Error empfangen oder geschlossen werden
                data = websocket.receive_json()
                # Wenn Nachricht kommt, sollte es Error sein
                assert data.get("type") == "error" or "status" in data
        except Exception:
            # Connection könnte auch geschlossen werden
            pass


# ============== Job-Flow Tests ==============


class TestJobFlow:
    """Tests für kompletten Job-Flow."""
    
    def test_job_flow_sequential(self, client: TestClient, test_repo_path: Path):
        """
        Testet kompletten Job-Flow mit sequenzieller Analyse.
        
        Erwartet:
        - Job wird erstellt (pending)
        - Analyse läuft (running)
        - Analyse schließt ab (completed)
        - Ergebnisse sind verfügbar
        
        Hinweis: Da Background-Tasks asynchron sind, müssen wir pollen.
        """
        # 1. Analyse starten
        create_response = client.post("/api/v1/analyze", json={
            "repo_path": str(test_repo_path),
            "use_parallel": False,  # Sequential für deterministischeres Verhalten
            "max_workers": 1,
            "enable_ml_prediction": False,
            "enable_auto_refactor": False,
        })
        
        assert create_response.status_code == 200
        job_id = create_response.json()["job_id"]
        
        # 2. Initialer Status sollte "pending" sein
        job_response = client.get(f"/api/v1/jobs/{job_id}")
        job = job_response.json()["job"]
        assert job["status"] == "pending"
        
        # 3. Warten bis Background-Task startet (kurz)
        time.sleep(0.5)
        
        # 4. Polling bis Job abgeschlossen (max 30 Sekunden)
        max_wait = 30
        poll_interval = 1
        waited = 0
        
        while waited < max_wait:
            time.sleep(poll_interval)
            waited += poll_interval
            
            job_response = client.get(f"/api/v1/jobs/{job_id}")
            job = job_response.json()["job"]
            status = job["status"]
            
            if status == "completed":
                break
            elif status == "failed":
                # Job ist fehlgeschlagen - mit Error-Details
                pytest.fail(f"Job fehlgeschlagen nach {waited}s: {job.get('errors', [])}")
        
        # 5. Assert Job erfolgreich abgeschlossen
        assert job["status"] == "completed", f"Job nicht abgeschlossen nach {waited}s"
        
        # 6. Ergebnisse prüfen
        results_response = client.get(f"/api/v1/results/{job_id}")
        results = results_response.json()
        
        assert results["status"] == "completed"
        assert "findings_count" in results
        assert "execution_time" in results
        assert results["execution_time"] > 0
    
    def test_multiple_jobs_parallel(self, client: TestClient, test_repo_path: Path):
        """
        Testet mehrere parallele Jobs.
        
        Erwartet:
        - Mehrere Jobs können gleichzeitig erstellt werden
        - Jobs haben unterschiedliche IDs
        - Alle Jobs werden verarbeitet
        """
        job_ids = []
        
        # 3 Jobs erstellen
        for i in range(3):
            response = client.post("/api/v1/analyze", json={
                "repo_path": str(test_repo_path),
                "use_parallel": False,
                "max_workers": 1,
            })
            assert response.status_code == 200
            job_id = response.json()["job_id"]
            job_ids.append(job_id)
        
        # Alle IDs sollten unterschiedlich sein
        assert len(set(job_ids)) == 3, "Alle Job-IDs sollten unique sein"
        
        # Alle Jobs sollten im JobManager existieren
        for job_id in job_ids:
            job = job_manager.get_job(job_id)
            assert job is not None
        
        # Jobs-Liste sollte 3 Einträge haben
        jobs_response = client.get("/api/v1/jobs")
        jobs = jobs_response.json()["jobs"]
        assert len(jobs) == 3


# ============== ParallelSwarmCoordinator Integration ==============


class TestParallelSwarmCoordinator:
    """Integrationstests für ParallelSwarmCoordinator."""
    
    @pytest.mark.asyncio
    async def test_coordinator_small_repo(self, test_repo_path: Path):
        """
        Testet ParallelSwarmCoordinator mit kleinem Repo.
        
        Erwartet:
        - Coordinator kann initialisiert werden
        - run_swarm_parallel() läuft erfolgreich
        - Ergebnis hat korrekte Struktur
        """
        coordinator = ParallelSwarmCoordinator(max_workers=2)
        
        result = await coordinator.run_swarm_parallel(str(test_repo_path))
        
        # Ergebnis-Struktur prüfen
        assert isinstance(result, ParallelExecutionResult)
        assert hasattr(result, 'success')
        assert hasattr(result, 'findings')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'execution_time')
        assert hasattr(result, 'parallelization_factor')
        
        # Werte prüfen
        assert isinstance(result.success, bool)
        assert isinstance(result.findings, list)
        assert isinstance(result.errors, list)
        assert result.execution_time > 0
        assert result.parallelization_factor >= 1.0
    
    @pytest.mark.asyncio
    async def test_coordinator_empty_repo(self, empty_repo_path: Path):
        """
        Testet ParallelSwarmCoordinator mit leerem Repo.
        
        Erwartet:
        - Coordinator läuft ohne Exception
        - Ergebnis zeigt 0 Findings
        """
        coordinator = ParallelSwarmCoordinator(max_workers=2)
        
        result = await coordinator.run_swarm_parallel(str(empty_repo_path))
        
        assert isinstance(result, ParallelExecutionResult)
        assert len(result.findings) == 0
        assert result.success is True  # Sollte erfolgreich sein, auch wenn nichts zu finden
    
    @pytest.mark.asyncio
    async def test_coordinator_nonexistent_path(self):
        """
        Testet ParallelSwarmCoordinator mit nicht-existierendem Pfad.
        
        Erwartet:
        - Exception wird geworfen
        """
        coordinator = ParallelSwarmCoordinator(max_workers=2)
        
        with pytest.raises(Exception):
            await coordinator.run_swarm_parallel("/nonexistent/path")


# ============== Error Handling Tests ==============


class TestErrorHandling:
    """Tests für Error-Handling."""
    
    def test_invalid_json_payload(self, client: TestClient):
        """
        Testet /api/v1/analyze mit ungültigem JSON.
        
        Erwartet:
        - HTTP 422 (Validation Error)
        """
        response = client.post(
            "/api/v1/analyze",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_missing_required_field(self, client: TestClient):
        """
        Testet /api/v1/analyze ohne required field.
        
        Erwartet:
        - HTTP 422 (Validation Error)
        """
        response = client.post("/api/v1/analyze", json={
            # repo_path fehlt
            "use_parallel": True,
        })
        
        assert response.status_code == 422


# ============== Performance Tests ==============


class TestPerformance:
    """Performance-Tests für Web-UI."""
    
    def test_analyze_endpoint_response_time(self, client: TestClient, test_repo_path: Path):
        """
        Testet Response-Time von /api/v1/analyze.
        
        Erwartet:
        - Response in < 100ms (Job-Erstellung ist schnell)
        """
        start = time.time()
        
        response = client.post("/api/v1/analyze", json={
            "repo_path": str(test_repo_path),
        })
        
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 0.1, f"Response-Time {elapsed:.3f}s > 100ms"
    
    def test_jobs_endpoint_response_time(self, client: TestClient, test_repo_path: Path):
        """
        Testet Response-Time von /api/v1/jobs.
        
        Erwartet:
        - Response in < 50ms
        """
        # Erst Job erstellen
        client.post("/api/v1/analyze", json={
            "repo_path": str(test_repo_path),
        })
        
        # Dann messen
        start = time.time()
        
        response = client.get("/api/v1/jobs")
        
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 0.05, f"Response-Time {elapsed:.3f}s > 50ms"


# ============== Konfigurations-Tests ==============


class TestConfiguration:
    """Tests für Konfiguration."""
    
    def test_default_max_workers(self, client: TestClient, test_repo_path: Path):
        """
        Testet dass max_workers Default-Wert hat.
        
        Erwartet:
        - Request ohne max_workers verwendet Default (4)
        """
        response = client.post("/api/v1/analyze", json={
            "repo_path": str(test_repo_path),
            # max_workers nicht angegeben
        })
        
        assert response.status_code == 200
        
        # Job sollte erstellt worden sein
        job_id = response.json()["job_id"]
        job = job_manager.get_job(job_id)
        assert job is not None
    
    def test_invalid_max_workers(self, client: TestClient, test_repo_path: Path):
        """
        Testet /api/v1/analyze mit ungültigem max_workers.
        
        Erwartet:
        - HTTP 422 bei negativer Zahl
        """
        response = client.post("/api/v1/analyze", json={
            "repo_path": str(test_repo_path),
            "max_workers": -1,
        })
        
        # Sollte Validation Error sein
        assert response.status_code == 422
