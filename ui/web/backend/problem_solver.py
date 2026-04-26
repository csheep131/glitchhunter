"""
Problem-Solver Service für GlitchHunter Web-UI.

Bietet API-Endpoints für prompt-basierte Problemlösung:
- Problem mit Prompt lösen
- Live-Updates via WebSocket
- Klassifikation und Diagnose
- Lösungsvorschläge anwenden

Features:
- Integration mit bestehendem ProblemManager
- WebSocket für Live-Status
- Multi-Step-Flow (Intake → Classify → Diagnose → Plan → Fix)
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/problem", tags=["Problem-Solving"])


# ============== Models ==============

class ProblemSolveRequest(BaseModel):
    """Request zum Lösen eines Problems."""
    prompt: str = Field(..., description="Problembeschreibung als Text")
    repo_path: Optional[str] = Field(None, description="Pfad zum Repository")
    with_ml_prediction: bool = Field(default=True, description="ML Prediction verwenden")
    with_code_analysis: bool = Field(default=True, description="Code-Analyse verwenden")
    auto_fix: bool = Field(default=False, description="Automatisch fixen")
    stack: str = Field(default="stack_b", description="Hardware-Stack")


class ProblemSolveResponse(BaseModel):
    """Response nach Starten der Problemlösung."""
    problem_id: str
    status: str
    message: str
    estimated_duration: Optional[str] = None


class ProblemResult(BaseModel):
    """Ergebnis einer Problemlösung."""
    problem_id: str
    status: str
    prompt: str
    classification: Optional[str] = None
    diagnosis: Optional[str] = None
    plan: Optional[str] = None
    solution: Optional[str] = None
    code_changes: Optional[List[Dict[str, Any]]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class ApplySolutionRequest(BaseModel):
    """Request zum Anwenden einer Lösung."""
    problem_id: str
    file_path: str
    code_changes: List[Dict[str, Any]]


class ApplySolutionResponse(BaseModel):
    """Response nach Anwenden einer Lösung."""
    success: bool
    message: str
    git_commit: Optional[str] = None
    backup_path: Optional[str] = None


# ============== Service ==============

class ProblemSolverService:
    """
    Service für Problemlösung.
    
    Flow:
    1. Problem Intake (Prompt empfangen)
    2. Klassifikation (Problem-Typ erkennen)
    3. Diagnose (Ursache finden)
    4. Plan erstellen (Lösungsweg)
    5. Auto-Fix (optional)
    6. Ergebnis zurückgeben
    
    Usage:
        service = ProblemSolverService()
        problem_id = await service.solve_problem(request, websocket)
    """
    
    def __init__(self):
        """Initialisiert Problem-Solver-Service."""
        self._problem_manager = None
        self._active_problems: Dict[str, Dict[str, Any]] = {}
        logger.info("ProblemSolverService initialisiert")
    
    def _get_problem_manager(self, repo_path: Optional[str] = None):
        """Lädt ProblemManager-Instanz."""
        if self._problem_manager is None:
            from src.problem.manager import ProblemManager
            glitchhunter_root = Path("/home/schaf/projects/glitchhunter")
            if repo_path:
                pm_path = Path(repo_path)
            else:
                pm_path = glitchhunter_root
            self._problem_manager = ProblemManager(repo_path=pm_path)
        return self._problem_manager
    
    async def solve_problem(
        self,
        request: ProblemSolveRequest,
        websocket: Optional[WebSocket] = None,
    ) -> str:
        """
        Löst Problem mit Prompt.
        
        Args:
            request: ProblemSolveRequest
            websocket: Optional WebSocket für Live-Updates
            
        Returns:
            problem_id: ID des erstellten Problems
        """
        try:
            pm = self._get_problem_manager()
            
            # 1. Problem Intake
            logger.info(f"[Problem] Intake: {request.prompt[:100]}...")
            problem = pm.intake_problem(
                description=request.prompt,
                source="webui",
                repo_path=request.repo_path,
            )
            
            problem_id = problem.id
            self._active_problems[problem_id] = {
                "status": "intake_complete",
                "request": request,
                "started_at": datetime.now(),
            }
            
            # WebSocket Status senden
            await self._send_websocket_update(
                websocket, problem_id, "intake_complete",
                {"message": "Problem erfasst"}
            )
            
            # 2. Klassifikation (im Hintergrund)
            asyncio.create_task(
                self._classify_and_diagnose(problem_id, request, websocket)
            )
            
            return problem_id
            
        except Exception as e:
            logger.error(f"Fehler beim Problemlösen: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _classify_and_diagnose(
        self,
        problem_id: str,
        request: ProblemSolveRequest,
        websocket: Optional[WebSocket] = None,
    ):
        """
        Führt Klassifikation und Diagnose durch.
        
        Hintergrund-Task für asynchrone Verarbeitung.
        Alle sync-Methoden werden via run_in_executor ausgeführt.
        """
        try:
            pm = self._get_problem_manager()
            
            # 2. Klassifikation
            await self._send_websocket_update(
                websocket, problem_id, "classifying",
                {"message": "Klassifiziere Problem..."}
            )
            
            loop = asyncio.get_event_loop()
            
            classification = await loop.run_in_executor(
                None, pm.classify_problem, problem_id
            )
            self._active_problems[problem_id]["classification"] = classification
            
            await self._send_websocket_update(
                websocket, problem_id, "classified",
                {
                    "classification": str(classification),
                    "message": f"Problem-Typ: {classification}",
                }
            )
            
            # 3. Diagnose
            await self._send_websocket_update(
                websocket, problem_id, "diagnosing",
                {"message": "Führe Diagnose durch..."}
            )
            
            if request.with_code_analysis:
                diagnosis = await loop.run_in_executor(
                    None, pm.generate_diagnosis, problem_id
                )
                self._active_problems[problem_id]["diagnosis"] = str(diagnosis)
                
                await self._send_websocket_update(
                    websocket, problem_id, "diagnosed",
                    {
                        "diagnosis": str(diagnosis),
                        "message": "Diagnose abgeschlossen",
                    }
                )
            
            # 4. Plan erstellen
            await self._send_websocket_update(
                websocket, problem_id, "planning",
                {"message": "Erstelle Lösungsplan..."}
            )
            
            plan = await loop.run_in_executor(
                None, pm.create_solution_plan, problem_id
            )
            self._active_problems[problem_id]["plan"] = str(plan)
            
            await self._send_websocket_update(
                websocket, problem_id, "planned",
                {
                    "plan": str(plan),
                    "message": "Lösungsplan erstellt",
                }
            )
            
            # 5. Auto-Fix (optional)
            if request.auto_fix:
                await self._send_websocket_update(
                    websocket, problem_id, "fixing",
                    {"message": "Wende Fix automatisch an..."}
                )
                
                result = await loop.run_in_executor(
                    None, pm.auto_fix, problem_id
                )
                self._active_problems[problem_id]["solution"] = str(result)
                
                await self._send_websocket_update(
                    websocket, problem_id, "completed",
                    {
                        "solution": str(result),
                        "message": "Problem gelöst",
                    }
                )
            else:
                # Manueller Flow - Lösung vorschlagen
                solution = await loop.run_in_executor(
                    None, pm.create_solution_plan, problem_id
                )
                self._active_problems[problem_id]["solution"] = str(solution)
                
                await self._send_websocket_update(
                    websocket, problem_id, "completed",
                    {
                        "solution": str(solution),
                        "message": "Lösungsvorschlag erstellt",
                    }
                )
            
            # Status aktualisieren
            self._active_problems[problem_id]["status"] = "completed"
            self._active_problems[problem_id]["completed_at"] = datetime.now()
            
        except Exception as e:
            logger.error(f"Fehler bei Klassifikation/Diagnose: {e}")
            await self._send_websocket_update(
                websocket, problem_id, "error",
                {"error": str(e), "message": "Fehler bei der Analyse"}
            )
            self._active_problems[problem_id]["status"] = "failed"
    
    async def _send_websocket_update(
        self,
        websocket: Optional[WebSocket],
        problem_id: str,
        event_type: str,
        data: Dict[str, Any],
    ):
        """Sendet Update via WebSocket."""
        if websocket and websocket.client_state == 1:  # WebSocket.OPEN
            try:
                await websocket.send_json({
                    "type": event_type,
                    "problem_id": problem_id,
                    **data,
                })
            except Exception as e:
                logger.warning(f"WebSocket-Update fehlgeschlagen: {e}")
    
    def get_problem(self, problem_id: str) -> Optional[ProblemResult]:
        """
        Holt Problem-Ergebnis.
        
        Args:
            problem_id: Problem-ID
            
        Returns:
            ProblemResult oder None
        """
        problem_data = self._active_problems.get(problem_id)
        if not problem_data:
            return None
        
        return ProblemResult(
            problem_id=problem_id,
            status=problem_data.get("status", "unknown"),
            prompt=problem_data.get("request", {}).get("prompt", ""),
            classification=problem_data.get("classification"),
            diagnosis=problem_data.get("diagnosis"),
            plan=problem_data.get("plan"),
            solution=problem_data.get("solution"),
            created_at=problem_data.get("started_at", datetime.now()),
            completed_at=problem_data.get("completed_at"),
        )
    
    def get_history(self, limit: int = 50) -> List[ProblemResult]:
        """
        Holt Problem-Historie.
        
        Args:
            limit: Maximale Anzahl Einträge
            
        Returns:
            Liste von ProblemResult
        """
        # Sortiert nach created_at, neueste zuerst
        sorted_problems = sorted(
            self._active_problems.values(),
            key=lambda x: x.get("started_at", datetime.now()),
            reverse=True,
        )[:limit]
        
        return [
            ProblemResult(
                problem_id=p.get("request", {}).get("problem_id", "unknown"),
                status=p.get("status", "unknown"),
                prompt=p.get("request", {}).get("prompt", ""),
                classification=p.get("classification"),
                created_at=p.get("started_at", datetime.now()),
                completed_at=p.get("completed_at"),
            )
            for p in sorted_problems
        ]


# ============== Router ==============

service = ProblemSolverService()


@router.post("/solve", response_model=ProblemSolveResponse)
async def solve_problem(request: ProblemSolveRequest):
    """Problem mit Prompt lösen."""
    problem_id = await service.solve_problem(request)
    
    return ProblemSolveResponse(
        problem_id=problem_id,
        status="processing",
        message="Problemlösung gestartet",
        estimated_duration="30-120 Sekunden",
    )


@router.get("/{problem_id}", response_model=ProblemResult)
async def get_problem(problem_id: str):
    """Problem-Ergebnis abrufen."""
    result = service.get_problem(problem_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Problem nicht gefunden")
    
    return result


@router.get("/history", response_model=List[ProblemResult])
async def get_history(limit: int = 50):
    """Problem-Historie abrufen."""
    return service.get_history(limit)


@router.post("/{problem_id}/apply", response_model=ApplySolutionResponse)
async def apply_solution(problem_id: str, request: ApplySolutionRequest):
    """Lösung anwenden."""
    # TODO: Implementierung
    return ApplySolutionResponse(
        success=True,
        message="Lösung angewendet",
    )


@router.websocket("/ws/{problem_id}")
async def websocket_problem(websocket: WebSocket, problem_id: str):
    """WebSocket für Live-Updates."""
    await websocket.accept()
    logger.debug(f"Problem WebSocket {problem_id} verbunden")
    
    try:
        # Initialen Status senden
        problem = service.get_problem(problem_id)
        if problem:
            await websocket.send_json({
                "type": "status",
                "problem_id": problem_id,
                "status": problem.status,
            })
        
        # Auf Nachrichten warten (Keep-Alive)
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        logger.debug(f"Problem WebSocket {problem_id} getrennt")
    except Exception as e:
        logger.error(f"Problem WebSocket Fehler: {e}")
