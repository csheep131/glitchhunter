"""
FastAPI Backend für GlitchHunter Web-UI.

Bietet REST-API und WebSocket für:
- Repository-Analyse starten
- Live-Ergebnisse streamen
- Team-Collaboration
- Auto-Refactoring triggern

Endpoints:
- POST /api/v1/analyze - Analyse starten
- GET /api/v1/results/{id} - Ergebnisse abrufen
- WS /ws/results/{id} - Live-Ergebnisse streamen
- POST /api/v1/refactor - Refactoring anwenden
- GET /api/v1/status - Server-Status
"""

import asyncio
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ============== Logging-Konfiguration ==============
# Logging AM ANFANG konfigurieren damit alle Logs sichtbar sind
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# src/ zu sys.path hinzufügen für Imports ohne src.-Prefix
# Dies ermöglicht Imports wie "from agent.parallel_swarm import ..."
SRC_PATH = Path(__file__).resolve().parent.parent.parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent.parallel_swarm import ParallelSwarmCoordinator, ParallelExecutionResult
from agent.swarm_coordinator import SwarmCoordinator


# ============== Models ==============

class AnalyzeRequest(BaseModel):
    """Request für Repository-Analyse."""
    repo_path: str = Field(..., description="Pfad zum Repository")
    use_parallel: bool = Field(default=True, description="Parallele Analyse aktivieren")
    enable_ml_prediction: bool = Field(default=True, description="ML Prediction aktivieren")
    enable_auto_refactor: bool = Field(default=False, description="Auto-Refactoring aktivieren")
    max_workers: int = Field(default=4, description="Maximale Worker für parallele Analyse")
    stack: str = Field(default="stack_b", description="Hardware Stack (stack_a, stack_b, stack_c)")


class AnalyzeResponse(BaseModel):
    """Response für gestartete Analyse."""
    job_id: str
    status: str
    message: str
    estimated_duration: Optional[str] = None


class AnalysisResult(BaseModel):
    """Ergebnis einer Analyse."""
    job_id: str
    status: str
    findings_count: int
    execution_time: float
    parallelization_factor: float
    findings: Optional[List[Dict[str, Any]]] = None
    errors: Optional[List[str]] = None
    created_at: datetime


class RefactorRequest(BaseModel):
    """Request für Auto-Refactoring."""
    finding_id: str = Field(..., description="ID des Findings zum Refactoren")
    file_path: str = Field(..., description="Pfad zur Datei")
    apply: bool = Field(default=False, description="Refactoring direkt anwenden")


# ============== Job Manager ==============

class JobManager:
    """
    Verwaltet Analyse-Jobs.
    
    Features:
    - Job-Tracking mit Status
    - Ergebnisse cachen
    - WebSocket Connections verwalten
    """
    
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._websockets: Dict[str, List[WebSocket]] = {}
    
    def create_job(self, repo_path: str) -> str:
        """Erstellt neuen Job."""
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {
            "status": "pending",
            "repo_path": repo_path,
            "created_at": datetime.now(),
            "result": None,
            "errors": [],
        }
        self._websockets[job_id] = []
        logger.info(f"Job {job_id[:8]} erstellt für {repo_path}")
        return job_id
    
    def update_job_status(self, job_id: str, status: str, **kwargs):
        """Aktualisiert Job-Status."""
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = status
            self._jobs[job_id].update(kwargs)
            logger.debug(f"Job {job_id[:8]} Status: {status}")
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Returns Job-Informationen."""
        return self._jobs.get(job_id)
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Returns alle Jobs."""
        return list(self._jobs.values())
    
    async def add_websocket(self, job_id: str, websocket: WebSocket):
        """Fügt WebSocket zu Job hinzu."""
        if job_id in self._websockets:
            await websocket.accept()
            self._websockets[job_id].append(websocket)
            logger.debug(f"WebSocket zu Job {job_id[:8]} hinzugefügt")
    
    def remove_websocket(self, job_id: str, websocket: WebSocket):
        """Entfernt WebSocket von Job."""
        if job_id in self._websockets:
            self._websockets[job_id] = [
                ws for ws in self._websockets[job_id] if ws != websocket
            ]
    
    async def broadcast(self, job_id: str, message: Dict[str, Any]):
        """Sendet Nachricht an alle WebSocket-Clients."""
        if job_id in self._websockets:
            disconnected = []
            for ws in self._websockets[job_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    disconnected.append(ws)
            
            # Disconnected entfernen
            for ws in disconnected:
                self._websockets[job_id].remove(ws)


# Globale Instanz
job_manager = JobManager()


# ============== FastAPI App ==============

def create_app() -> FastAPI:
    """
    Erstellt FastAPI App.
    
    Returns:
        FastAPI application
    """
    app = FastAPI(
        title="GlitchHunter Web-UI",
        description="Web-Interface für GlitchHunter Code-Analyse",
        version="3.0.0",
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In Produktion einschränken!
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.add_api_route("/api/v1/analyze", analyze_repository, methods=["POST"])
    app.add_api_route("/api/v1/jobs", list_jobs, methods=["GET"])
    app.add_api_route("/api/v1/jobs/{job_id}", get_job, methods=["GET"])
    app.add_api_route("/api/v1/results/{job_id}", get_results, methods=["GET"])
    app.add_api_route("/api/v1/refactor", apply_refactor, methods=["POST"])
    app.add_api_route("/api/v1/status", get_status, methods=["GET"])
    app.add_api_websocket_route("/ws/results/{job_id}", websocket_results)
    
    # Settings Routes (neu in Phase 1)
    from ui.web.backend.settings import router as settings_router
    app.include_router(settings_router)
    
    # Refactoring Routes (neu in Phase 1.4)
    from ui.web.backend.refactor import router as refactor_router
    app.include_router(refactor_router)
    
    # Problem-Solving Routes (neu in Phase 2.1)
    from ui.web.backend.problem_solver import router as problem_router
    app.include_router(problem_router)
    
    # Report-Generator Routes (neu in Phase 2.3)
    from ui.web.backend.reports import router as reports_router
    app.include_router(reports_router)
    
    # History Routes (neu in Phase 2.5)
    from ui.web.backend.history_router import router as history_router
    app.include_router(history_router)
    
    # Stack-Management Routes (neu in Phase 3.1)
    from ui.web.backend.stacks_router import router as stacks_router
    app.include_router(stacks_router)
    
    # Model-Monitoring Routes (neu in Phase 3.3)
    from ui.web.backend.models_router import router as models_router
    app.include_router(models_router)
    
    # Hardware-Monitoring Routes (neu in Phase 3.6)
    from ui.web.backend.hardware_monitor_router import router as hardware_router
    app.include_router(hardware_router)
    
    # Remote-Server Routes (neu für Model-Config)
    from ui.web.backend.remote_servers_router import router as servers_router
    app.include_router(servers_router)

    # Frontend Routes (HTML Dashboard + alle anderen Seiten)
    @app.get("/")
    async def serve_frontend():
        """Serviert das Frontend Dashboard."""
        from pathlib import Path
        frontend_html = Path(__file__).parent.parent / "frontend" / "index.html"

        if frontend_html.exists():
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=frontend_html.read_text(encoding="utf-8"))

        return HTMLResponse(content="<h1>Frontend not found</h1>", status_code=404)
    
    @app.get("/problem.html")
    async def serve_problem():
        """Serviert Problemlöser-Seite."""
        from pathlib import Path
        from fastapi.responses import HTMLResponse
        html_file = Path(__file__).parent.parent / "frontend" / "problem.html"
        return HTMLResponse(content=html_file.read_text(encoding="utf-8")) if html_file.exists() else HTMLResponse("<h1>404</h1>", status_code=404)
    
    @app.get("/refactor.html")
    async def serve_refactor():
        """Serviert Refactoring-Seite."""
        from pathlib import Path
        from fastapi.responses import HTMLResponse
        html_file = Path(__file__).parent.parent / "frontend" / "refactor.html"
        return HTMLResponse(content=html_file.read_text(encoding="utf-8")) if html_file.exists() else HTMLResponse("<h1>404</h1>", status_code=404)
    
    @app.get("/reports.html")
    async def serve_reports():
        """Serviert Reports-Seite."""
        from pathlib import Path
        from fastapi.responses import HTMLResponse
        html_file = Path(__file__).parent.parent / "frontend" / "reports.html"
        return HTMLResponse(content=html_file.read_text(encoding="utf-8")) if html_file.exists() else HTMLResponse("<h1>404</h1>", status_code=404)
    
    @app.get("/history.html")
    async def serve_history():
        """Serviert History-Seite."""
        from pathlib import Path
        from fastapi.responses import HTMLResponse
        html_file = Path(__file__).parent.parent / "frontend" / "history.html"
        return HTMLResponse(content=html_file.read_text(encoding="utf-8")) if html_file.exists() else HTMLResponse("<h1>404</h1>", status_code=404)
    
    @app.get("/stacks.html")
    async def serve_stacks():
        """Serviert Stack-Management-Seite."""
        from pathlib import Path
        from fastapi.responses import HTMLResponse
        html_file = Path(__file__).parent.parent / "frontend" / "stacks.html"
        return HTMLResponse(content=html_file.read_text(encoding="utf-8")) if html_file.exists() else HTMLResponse("<h1>404</h1>", status_code=404)
    
    @app.get("/stack-config.html")
    async def serve_stack_config():
        """Serviert Stack-Konfigurations-Seite."""
        from pathlib import Path
        from fastapi.responses import HTMLResponse
        html_file = Path(__file__).parent.parent / "frontend" / "stack-config.html"
        return HTMLResponse(content=html_file.read_text(encoding="utf-8")) if html_file.exists() else HTMLResponse("<h1>404</h1>", status_code=404)

    @app.get("/models.html")
    async def serve_models():
        """Serviert Model-Monitoring-Seite."""
        from pathlib import Path
        from fastapi.responses import HTMLResponse
        html_file = Path(__file__).parent.parent / "frontend" / "models.html"
        return HTMLResponse(content=html_file.read_text(encoding="utf-8")) if html_file.exists() else HTMLResponse("<h1>404</h1>", status_code=404)
    
    @app.get("/testing.html")
    async def serve_testing():
        """Serviert Stack-Testing-Seite."""
        from pathlib import Path
        from fastapi.responses import HTMLResponse
        html_file = Path(__file__).parent.parent / "frontend" / "testing.html"
        return HTMLResponse(content=html_file.read_text(encoding="utf-8")) if html_file.exists() else HTMLResponse("<h1>404</h1>", status_code=404)
    
    @app.get("/hardware.html")
    async def serve_hardware():
        """Serviert Hardware-Monitoring-Seite."""
        from pathlib import Path
        from fastapi.responses import HTMLResponse
        html_file = Path(__file__).parent.parent / "frontend" / "hardware.html"
        return HTMLResponse(content=html_file.read_text(encoding="utf-8")) if html_file.exists() else HTMLResponse("<h1>404</h1>", status_code=404)
    
    @app.get("/settings.html")
    async def serve_settings():
        """Serviert Settings-Seite."""
        from pathlib import Path
        from fastapi.responses import HTMLResponse
        html_file = Path(__file__).parent.parent / "frontend" / "settings.html"
        return HTMLResponse(content=html_file.read_text(encoding="utf-8")) if html_file.exists() else HTMLResponse("<h1>404</h1>", status_code=404)

    # Static Files (für CSS, JS, Images)
    try:
        from pathlib import Path
        static_dir = Path(__file__).parent.parent / "frontend"
        if static_dir.exists():
            app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    except Exception as e:
        logger.debug(f"Static files mount skipped: {e}")

    return app


# ============== Endpoints ==============

async def analyze_repository(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
) -> AnalyzeResponse:
    """
    Startet Repository-Analyse.
    
    Args:
        request: AnalyzeRequest
        background_tasks: FastAPI BackgroundTasks
        
    Returns:
        AnalyzeResponse mit Job-ID
    """
    # Job erstellen
    job_id = job_manager.create_job(request.repo_path)
    
    # Analyse im Hintergrund starten
    background_tasks.add_task(
        run_analysis,
        job_id,
        request.repo_path,
        request.use_parallel,
        request.enable_ml_prediction,
        request.enable_auto_refactor,
        request.max_workers,
        request.stack,  # Stack-Parameter übergeben
    )
    
    return AnalyzeResponse(
        job_id=job_id,
        status="pending",
        message="Analyse gestartet",
        estimated_duration="30-300 Sekunden (abhängig von Repository-Größe)",
    )


async def run_analysis(
    job_id: str,
    repo_path: str,
    use_parallel: bool,
    enable_ml: bool,
    enable_refactor: bool,
    max_workers: int,
    stack: str = "stack_b",
):
    """
    Führt Analyse im Hintergrund aus.

    Args:
        job_id: Job-ID
        repo_path: Repository-Pfad
        use_parallel: Parallele Analyse
        enable_ml: ML Prediction
        enable_refactor: Auto-Refactoring
        max_workers: Maximale Worker
        stack: Hardware Stack (stack_a, stack_b, stack_c)
    """
    start_time = datetime.now()
    logger.info(f"=" * 60)
    logger.info(f"Analyse gestartet für Job {job_id[:8]}")
    logger.info(f"  Repository: {repo_path}")
    logger.info(f"  Parallel: {use_parallel}, ML: {enable_ml}, Refactor: {enable_refactor}")
    logger.info(f"  Max Workers: {max_workers}")
    logger.info(f"=" * 60)

    try:
        # Validiere Repository-Pfad
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            raise ValueError(f"Repository-Pfad existiert nicht: {repo_path}")
        if not repo_path_obj.is_dir():
            raise ValueError(f"Repository-Pfad ist kein Verzeichnis: {repo_path}")

        logger.debug(f"Repository-Pfad validiert: {repo_path}")

        # Status: running
        logger.info(f"Job {job_id[:8]} Status: pending -> running")
        job_manager.update_job_status(job_id, "running")
        await job_manager.broadcast(job_id, {"type": "status", "status": "running"})

        # Coordinator auswählen und initialisieren
        coordinator = None
        result = None

        if use_parallel:
            logger.info(f"Initialisiere ParallelSwarmCoordinator mit {max_workers} Workern...")
            try:
                coordinator = ParallelSwarmCoordinator(max_workers=max_workers)
                logger.debug(f"ParallelSwarmCoordinator erfolgreich initialisiert")
            except Exception as coord_init_error:
                logger.error(
                    f"ParallelSwarmCoordinator Initialisierung fehlgeschlagen: {coord_init_error}",
                    exc_info=True,
                )
                logger.warning(f"Falle zurück auf SwarmCoordinator (sequenziell)")

                # Fallback auf SwarmCoordinator
                coordinator = SwarmCoordinator()
                logger.info(f"SwarmCoordinator (Fallback) initialisiert")

                # SwarmCoordinator ausführen
                logger.info(f"Starte sequenzielle Swarm-Analyse...")
                swarm_result = await coordinator.run_swarm(repo_path)
                logger.info(f"Swarm-Analyse abgeschlossen")

                # In ParallelExecutionResult konvertieren
                result = ParallelExecutionResult(
                    success=swarm_result.get("success", False),
                    findings=swarm_result.get("findings", []),
                    errors=swarm_result.get("errors", []),
                    execution_time=swarm_result.get("execution_time", 0),
                    parallelization_factor=1.0,
                )
            else:
                # ParallelSwarmCoordinator erfolgreich, jetzt ausführen
                logger.info(f"Starte parallele Swarm-Analyse mit {max_workers} Workern...")
                result = await coordinator.run_swarm_parallel(repo_path)
                logger.info(f"Parallele Swarm-Analyse abgeschlossen")

        else:
            # Sequenzielle Analyse
            logger.info(f"Initialisiere SwarmCoordinator (sequenziell)...")
            try:
                coordinator = SwarmCoordinator()
                logger.debug(f"SwarmCoordinator erfolgreich initialisiert")
            except Exception as coord_init_error:
                logger.error(
                    f"SwarmCoordinator Initialisierung fehlgeschlagen: {coord_init_error}",
                    exc_info=True,
                )
                raise RuntimeError(f"Coordinator Initialisierung fehlgeschlagen: {coord_init_error}")

            logger.info(f"Starte sequenzielle Swarm-Analyse...")
            swarm_result = await coordinator.run_swarm(repo_path)
            logger.info(f"Swarm-Analyse abgeschlossen")

            # In ParallelExecutionResult konvertieren
            result = ParallelExecutionResult(
                success=swarm_result.get("success", False),
                findings=swarm_result.get("findings", []),
                errors=swarm_result.get("errors", []),
                execution_time=swarm_result.get("execution_time", 0),
                parallelization_factor=1.0,
            )

        # Ergebnis validieren
        if result is None:
            raise RuntimeError("Coordinator returned None as result")

        logger.info(f"Ergebnis validiert: {len(result.findings)} findings, {len(result.errors)} errors")

        # Ergebnis speichern
        end_time = datetime.now()
        execution_duration = (end_time - start_time).total_seconds()

        logger.info(f"Speichere Ergebnis für Job {job_id[:8]}...")
        job_manager.update_job_status(
            job_id,
            "completed",
            result=result,
            completed_at=end_time,
        )
        logger.debug(f"Job-Status aktualisiert: completed")

        # WebSocket Broadcast
        logger.info(f"Sende 'complete' Broadcast an {len(job_manager._websockets.get(job_id, []))} WebSocket-Clients")
        await job_manager.broadcast(job_id, {
            "type": "complete",
            "status": "completed",
            "findings_count": len(result.findings),
            "execution_time": result.execution_time,
            "errors": result.errors,
        })

        logger.info(f"=" * 60)
        logger.info(f"Analyse {job_id[:8]} ERFOLGREICH ABGESCHLOSSEN")
        logger.info(f"  Dauer: {execution_duration:.2f}s")
        logger.info(f"  Findings: {len(result.findings)}")
        logger.info(f"  Errors: {len(result.errors)}")
        logger.info(f"=" * 60)

    except Exception as e:
        # Umfassendes Exception-Handling
        error_message = f"Analyse {job_id[:8]} FEHLGESCHLAGEN: {type(e).__name__}: {e}"
        logger.error(error_message, exc_info=True)

        # Job-Status auf failed setzen
        job_manager.update_job_status(
            job_id,
            "failed",
            errors=[f"{type(e).__name__}: {e}"],
            failed_at=datetime.now(),
        )
        logger.debug(f"Job-Status aktualisiert: failed")

        # WebSocket Broadcast mit Error
        try:
            await job_manager.broadcast(job_id, {
                "type": "error",
                "status": "failed",
                "error": str(e),
                "error_type": type(e).__name__,
            })
            logger.debug(f"Error-Broadcast an WebSocket-Clients gesendet")
        except Exception as broadcast_error:
            logger.error(f"Konnte Error-Broadcast nicht senden: {broadcast_error}")

        logger.info(f"=" * 60)
        logger.info(f"Analyse {job_id[:8]} FEHLGESCHLAGEN nach {(datetime.now() - start_time).total_seconds():.2f}s")
        logger.info(f"=" * 60)


def _serialize_datetime(obj: Any) -> Any:
    """
    Serialisiert datetime-Objekte für JSON-Response.
    
    Args:
        obj: Beliebiges Objekt
        
    Returns:
        Serialisierbare Version des Objekts
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


async def list_jobs() -> JSONResponse:
    """Returns alle Analyse-Jobs."""
    jobs = job_manager.get_all_jobs()
    
    # Datetime-Objekte serialisieren
    serialized_jobs = []
    for job in jobs:
        serialized_job = job.copy()
        if "created_at" in serialized_job and isinstance(serialized_job["created_at"], datetime):
            serialized_job["created_at"] = serialized_job["created_at"].isoformat()
        if "completed_at" in serialized_job and isinstance(serialized_job["completed_at"], datetime):
            serialized_job["completed_at"] = serialized_job["completed_at"].isoformat()
        if "failed_at" in serialized_job and isinstance(serialized_job["failed_at"], datetime):
            serialized_job["failed_at"] = serialized_job["failed_at"].isoformat()
        serialized_jobs.append(serialized_job)
    
    return JSONResponse(content={"jobs": serialized_jobs})


async def get_job(job_id: str) -> JSONResponse:
    """Returns Job-Informationen."""
    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    
    # Kopie erstellen und datetime-Objekte serialisieren
    serialized_job = job.copy()
    if "created_at" in serialized_job and isinstance(serialized_job["created_at"], datetime):
        serialized_job["created_at"] = serialized_job["created_at"].isoformat()
    if "completed_at" in serialized_job and isinstance(serialized_job["completed_at"], datetime):
        serialized_job["completed_at"] = serialized_job["completed_at"].isoformat()
    if "failed_at" in serialized_job and isinstance(serialized_job["failed_at"], datetime):
        serialized_job["failed_at"] = serialized_job["failed_at"].isoformat()

    return JSONResponse(content={"job": serialized_job})


async def get_results(job_id: str) -> AnalysisResult:
    """Returns Analyse-Ergebnisse."""
    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")

    result = job.get("result")

    return AnalysisResult(
        job_id=job_id,
        status=job["status"],
        findings_count=len(result.findings) if result else 0,
        execution_time=result.execution_time if result else 0,
        parallelization_factor=result.parallelization_factor if result else 1.0,
        findings=[f.to_dict() for f in result.findings] if result else None,
        errors=result.errors if result else None,
        created_at=job["created_at"].isoformat() if isinstance(job["created_at"], datetime) else job["created_at"],
    )


async def apply_refactor(request: RefactorRequest) -> JSONResponse:
    """
    Wendet Auto-Refactoring an.
    
    Args:
        request: RefactorRequest
        
    Returns:
        JSONResponse mit Ergebnis
    """
    # TODO: Auto-Refactoring implementieren
    # from fixing.auto_refactor import AutoRefactor
    
    return JSONResponse(content={
        "success": True,
        "message": "Refactoring angewendet",
        "finding_id": request.finding_id,
    })


async def get_status() -> JSONResponse:
    """Returns Server-Status."""
    return JSONResponse(content={
        "status": "healthy",
        "version": "3.0.0",
        "active_jobs": len([j for j in job_manager.get_all_jobs() if j["status"] == "running"]),
        "total_jobs": len(job_manager.get_all_jobs()),
    })


async def websocket_results(websocket: WebSocket, job_id: str):
    """
    WebSocket für Live-Ergebnisse.

    Args:
        websocket: WebSocket Connection
        job_id: Job-ID
    """
    # WebSocket akzeptieren
    await websocket.accept()
    logger.debug(f"WebSocket für Job {job_id[:8]} akzeptiert")
    
    # WebSocket zum Job Manager hinzufügen
    await job_manager.add_websocket(job_id, websocket)

    try:
        # Job-Status senden
        job = job_manager.get_job(job_id)
        if job:
            logger.debug(f"Sende initialen Status an {job_id[:8]}: {job['status']}")
            await websocket.send_json({
                "type": "status",
                "status": job["status"],
            })

        # Auf Nachrichten warten (Keep-Alive)
        while True:
            data = await websocket.receive_text()
            # Ping/Pong für Keep-Alive
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        logger.debug(f"WebSocket {job_id[:8]} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        job_manager.remove_websocket(job_id, websocket)
        logger.debug(f"WebSocket für Job {job_id[:8]} entfernt")


# ============== App Instance ==============

# App-Instanz für uvicorn und direkte Imports
app: FastAPI = create_app()


# ============== Main ==============

def main():
    """Startet FastAPI Server."""
    uvicorn.run(
        "ui.web.backend.app:app",
        host="0.0.0.0",
        port=6262,
        reload=True,
    )


if __name__ == "__main__":
    main()
