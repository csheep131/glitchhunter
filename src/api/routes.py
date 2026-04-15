"""
API routes for GlitchHunter.

Defines all REST API endpoints for analysis, status, hardware info, and escalation.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status, Request

from core.exceptions import GlitchHunterException
from core.config import Config
from hardware.detector import HardwareDetector
from api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalysisResult,
    EscalationRequest,
    HardwareInfo,
    HealthResponse,
    StatusResponse,
    StackInfo,
    ModelInfo,
    LlamaStatus,
    SystemResources,
    SocratiCodeStatus,
    CompleteStatus,
    # Problem-Solver Schemas
    ProblemIntakeRequest,
    ProblemUpdateRequest,
    ProblemResponse,
    ProblemListResponse,
    ClassificationResultResponse,
    ProblemStatisticsResponse,
    ProblemDeleteResponse,
)

logger = logging.getLogger(__name__)

# Router for all API routes
router = APIRouter()

# In-memory storage for analysis jobs (replace with database in production)
_analysis_jobs: Dict[str, Dict[str, Any]] = {}


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns the health status of the API and its components.
    """
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.utcnow(),
        components={
            "api": "healthy",
            "inference": "unknown",
            "mcp": "unknown",
            "database": "healthy",
        },
    )


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Analysis"],
)
async def start_analysis(request: AnalyzeRequest, fastapi_request: Request) -> AnalyzeResponse:
    """
    Start code analysis for a repository.

    Initiates an asynchronous analysis job that:
    1. Parses and maps the repository
    2. Runs security and correctness scans
    3. Generates bug hypotheses
    4. Creates and verifies patches
    5. Produces a final report

    Args:
        request: Analysis request with repository path and options

    Returns:
        AnalyzeResponse with analysis ID and initial status
    """
    analysis_id = f"analysis-{uuid.uuid4().hex[:12]}"

    logger.info(f"Starting analysis {analysis_id} for {request.repo_path}")

    # Store job info
    _analysis_jobs[analysis_id] = {
        "repo_path": request.repo_path,
        "status": "queued",
        "current_state": "init",
        "request": request.model_dump(),
        "started_at": datetime.utcnow(),
        "completed_at": None,
        "progress_percent": 0.0,
        "findings_count": 0,
        "patches_generated": 0,
        "patches_verified": 0,
        "errors": [],
        "result": None,
    }

    # Initialize analysis with options
    state_machine = fastapi_request.app.state.state_machine
    analysis_id = await state_machine.start_analysis(
        repo_path=request.repo_path,
        scan_security=request.scan_security,
        scan_correctness=request.scan_correctness,
        generate_patches=request.generate_patches,
        index_mcp=request.index_mcp
    )

    return AnalyzeResponse(
        analysis_id=analysis_id,
        status="queued",
        repo_path=request.repo_path,
        started_at=datetime.utcnow(),
        estimated_duration_seconds=600,
        message="Analysis job queued successfully",
    )


@router.get(
    "/analyze/{analysis_id}/status",
    response_model=StatusResponse,
    tags=["Analysis"],
)
async def get_analysis_status(analysis_id: str) -> StatusResponse:
    """
    Get status of an analysis job.

    Args:
        analysis_id: ID of the analysis job

    Returns:
        StatusResponse with current progress and statistics

    Raises:
        HTTPException: If analysis not found
    """
    if analysis_id not in _analysis_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' not found",
        )

    job = _analysis_jobs[analysis_id]

    return StatusResponse(
        analysis_id=analysis_id,
        status=job["status"],
        current_state=job.get("current_state"),
        progress_percent=job["progress_percent"],
        findings_count=job["findings_count"],
        patches_generated=job["patches_generated"],
        patches_verified=job["patches_verified"],
        errors=job["errors"],
        started_at=job["started_at"],
        completed_at=job["completed_at"],
        result_url=f"/api/analyze/{analysis_id}/result"
        if job["status"] == "completed"
        else None,
    )


@router.get(
    "/analyze/{analysis_id}/result",
    response_model=AnalysisResult,
    tags=["Analysis"],
)
async def get_analysis_result(analysis_id: str) -> AnalysisResult:
    """
    Get complete analysis result.

    Args:
        analysis_id: ID of the analysis job

    Returns:
        AnalysisResult with all findings and patches

    Raises:
        HTTPException: If analysis not found or not completed
    """
    if analysis_id not in _analysis_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' not found",
        )

    job = _analysis_jobs[analysis_id]

    if job["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Analysis not completed (status: {job['status']})",
        )

    # TODO: Return actual result
    return AnalysisResult(
        analysis_id=analysis_id,
        repo_path=job["repo_path"],
        status="completed",
        findings=[],
        patches=[],
        statistics={"files_analyzed": 0, "lines_analyzed": 0},
        started_at=job["started_at"],
        completed_at=job["completed_at"] or datetime.utcnow(),
        duration_seconds=(
            (job["completed_at"] or datetime.utcnow()) - job["started_at"]
        ).total_seconds(),
    )


@router.get("/hardware", response_model=HardwareInfo, tags=["System"])
async def get_hardware_info() -> HardwareInfo:
    """
    Get detected hardware information.

    Returns information about the detected GPU hardware stack
    (Stack A: GTX 3060 or Stack B: RTX 3090).
    """
    detector = HardwareDetector()

    try:
        profile = detector.detect()
        gpu_name = detector.get_gpu_name()
        cuda_compute = detector.get_cuda_compute_capability()

        return HardwareInfo(
            detected_stack=profile.stack_type.value,
            gpu_name=gpu_name,
            vram_total_gb=profile.vram_limit,
            vram_available_gb=profile.available_vram_gb,
            cuda_compute=cuda_compute,
            execution_mode=profile.mode.value,
            features=profile.features,
        )

    finally:
        detector.shutdown()


@router.post("/escalate", tags=["Escalation"])
async def escalate_issue(request: EscalationRequest) -> Dict[str, Any]:
    """
    Escalate an issue to a higher level.

    Escalation levels:
    - Level 1: Context Explosion (provide more context)
    - Level 2: Bug Decomposition (break into smaller issues)
    - Level 3: Multi-Model Ensemble (use multiple models)
    - Level 4: Human-in-the-Loop (request human review)

    Args:
        request: Escalation request with issue ID and level

    Returns:
        Escalation result with new status
    """
    logger.info(
        f"Escalating issue {request.issue_id} to level {request.level}: {request.reason}"
    )

    # TODO: Implement escalation logic
    # For now, return placeholder response

    return {
        "issue_id": request.issue_id,
        "escalation_level": request.level,
        "status": "escalated",
        "message": f"Issue escalated to level {request.level}",
        "next_action": "pending_review",
    }


@router.get("/status", tags=["System"])
async def get_system_status() -> Dict[str, Any]:
    """
    Get overall system status.

    Returns status of all components and active jobs.
    """
    active_jobs = sum(
        1 for job in _analysis_jobs.values() if job["status"] in ("queued", "running")
    )
    completed_jobs = sum(
        1 for job in _analysis_jobs.values() if job["status"] == "completed"
    )

    return {
        "status": "operational",
        "version": "0.1.0",
        "timestamp": datetime.utcnow(),
        "jobs": {
            "active": active_jobs,
            "completed": completed_jobs,
            "total": len(_analysis_jobs),
        },
        "components": {
            "api": "healthy",
            "worker": "healthy",
            "inference": "unknown",
            "mcp": "unknown",
        },
    }


@router.delete(
    "/analyze/{analysis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Analysis"],
)
async def cancel_analysis(analysis_id: str) -> None:
    """
    Cancel an analysis job.

    Args:
        analysis_id: ID of the analysis job to cancel

    Raises:
        HTTPException: If analysis not found or already completed
    """
    if analysis_id not in _analysis_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' not found",
        )

    job = _analysis_jobs[analysis_id]

    if job["status"] == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel completed analysis",
        )

    # Update status
    job["status"] = "cancelled"
    job["completed_at"] = datetime.utcnow()

    logger.info(f"Analysis {analysis_id} cancelled")


# =============================================================================
# TUI Endpoints (Real Data)
# =============================================================================

import os
import time
from pathlib import Path

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Track API start time for uptime
_API_START_TIME = time.time()


def _get_gpu_info() -> tuple[str, int]:
    """Get GPU name and VRAM."""
    try:
        detector = HardwareDetector()
        profile = detector.detect()
        name = detector.get_gpu_name() or "Unknown"
        vram = int(profile.vram_limit)
        detector.shutdown()
        return name, vram
    except Exception as e:
        logger.warning(f"Could not detect GPU: {e}")
        return "Unknown", 8


def _get_model_size_gb(path: str) -> Optional[float]:
    """Get model file size in GB."""
    try:
        size_bytes = Path(path).stat().st_size
        return round(size_bytes / (1024**3), 2)
    except Exception:
        return None


def _get_system_resources() -> Dict[str, Any]:
    """Get real system resource usage."""
    resources = {
        "cpu_percent": 0.0,
        "ram_used_gb": 0.0,
        "ram_total_gb": 32.0,
        "gpu_temp_c": None,
        "vram_used_gb": None,
        "vram_total_gb": None,
    }
    
    if PSUTIL_AVAILABLE:
        try:
            resources["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            resources["ram_used_gb"] = round(mem.used / (1024**3), 1)
            resources["ram_total_gb"] = round(mem.total / (1024**3), 1)
        except Exception as e:
            logger.warning(f"Could not get system resources: {e}")
    
    # Try to get GPU info
    try:
        detector = HardwareDetector()
        profile = detector.detect()
        resources["vram_total_gb"] = profile.vram_limit
        # TODO: Get actual VRAM usage
        detector.shutdown()
    except Exception:
        pass
    
    return resources


@router.get("/v1/status", response_model=CompleteStatus, tags=["TUI"])
async def get_complete_status() -> CompleteStatus:
    """
    Get complete system status for TUI display.
    
    Returns real-time data about:
    - Current stack configuration
    - Available models
    - Llama server status
    - System resources
    """
    # Detect current stack
    gpu_name, vram_gb = _get_gpu_info()
    current_stack_type = "stack_a" if vram_gb <= 12 else "stack_b"
    
    # Stack configurations
    stacks = [
        StackInfo(
            stack_type="stack_a",
            gpu_name="GTX 3060",
            vram_gb=8,
            mode="sequential",
            available=current_stack_type == "stack_a"
        ),
        StackInfo(
            stack_type="stack_b",
            gpu_name="RTX 3090",
            vram_gb=24,
            mode="parallel",
            available=current_stack_type == "stack_b"
        ),
    ]
    
    current_stack = next(s for s in stacks if s.stack_type == current_stack_type)
    current_stack.gpu_name = gpu_name  # Use detected name
    current_stack.vram_gb = vram_gb
    
    # Model configuration based on stack
    if current_stack_type == "stack_a":
        models = [
            ModelInfo(
                name="Qwen3.5-9B-Uncensored",
                role="analyzer",
                path=os.environ.get("MODEL_ANALYZER", "models/qwen3.5-9b.gguf"),
                available=os.path.exists(os.environ.get("MODEL_ANALYZER", "")),
                size_gb=None,
            ),
            ModelInfo(
                name="Phi-4-mini",
                role="verifier",
                path=os.environ.get("MODEL_VERIFIER", "models/phi-4-mini.gguf"),
                available=os.path.exists(os.environ.get("MODEL_VERIFIER", "")),
                size_gb=None,
            ),
        ]
    else:
        models = [
            ModelInfo(
                name="Qwen3.5-27B",
                role="analyzer",
                path="models/qwen3.5-27b.gguf",
                available=os.path.exists("models/qwen3.5-27b.gguf"),
                size_gb=None,
            ),
            ModelInfo(
                name="DeepSeek-V3.2-Small",
                role="verifier",
                path="models/deepseek-v3.2-small.gguf",
                available=os.path.exists("models/deepseek-v3.2-small.gguf"),
                size_gb=None,
            ),
        ]
    
    # Get actual model sizes
    for model in models:
        model.size_gb = _get_model_size_gb(model.path)
    
    # System resources
    sys_resources = _get_system_resources()
    
    # Get SocratiCode status
    socraticode_status = _get_socraticode_status()
    
    return CompleteStatus(
        api_online=True,
        current_stack=current_stack,
        available_stacks=stacks,
        models=models,
        llama=LlamaStatus(
            running=True,  # TODO: Actually check
            response_time_ms=None,
            load_percent=None,
            port=8000,
        ),
        socraticode=SocratiCodeStatus(**socraticode_status),
        system=SystemResources(**sys_resources),
        uptime_seconds=int(time.time() - _API_START_TIME),
    )


@router.get("/v1/stack", response_model=StackInfo, tags=["TUI"])
async def get_current_stack() -> StackInfo:
    """Get current hardware stack information."""
    gpu_name, vram_gb = _get_gpu_info()
    stack_type = "stack_a" if vram_gb <= 12 else "stack_b"
    
    return StackInfo(
        stack_type=stack_type,
        gpu_name=gpu_name,
        vram_gb=vram_gb,
        mode="sequential" if stack_type == "stack_a" else "parallel",
        available=True,
    )


@router.get("/v1/models", response_model=List[ModelInfo], tags=["TUI"])
async def get_available_models() -> List[ModelInfo]:
    """Get list of available AI models."""
    stack = await get_current_stack()
    
    if stack.stack_type == "stack_a":
        return [
            ModelInfo(
                name="Qwen3.5-9B-Uncensored",
                role="analyzer",
                path=os.environ.get("MODEL_ANALYZER", ""),
                available=os.path.exists(os.environ.get("MODEL_ANALYZER", "")),
            ),
            ModelInfo(
                name="Phi-4-mini",
                role="verifier",
                path=os.environ.get("MODEL_VERIFIER", ""),
                available=os.path.exists(os.environ.get("MODEL_VERIFIER", "")),
            ),
        ]
    else:
        return [
            ModelInfo(
                name="Qwen3.5-27B",
                role="analyzer",
                path="models/qwen3.5-27b.gguf",
                available=os.path.exists("models/qwen3.5-27b.gguf"),
            ),
            ModelInfo(
                name="DeepSeek-V3.2-Small",
                role="verifier",
                path="models/deepseek-v3.2-small.gguf",
                available=os.path.exists("models/deepseek-v3.2-small.gguf"),
            ),
        ]


@router.get("/v1/system", response_model=SystemResources, tags=["TUI"])
async def get_system_resources() -> SystemResources:
    """Get current system resource usage."""
    resources = _get_system_resources()
    return SystemResources(**resources)


def _get_socraticode_status() -> Dict[str, Any]:
    """Check SocratiCode MCP server status with targeted auto-start."""
    try:
        from core.config import Config
        config = Config.load()
        mcp_cfg = config.mcp_integration
        
        if not mcp_cfg.enabled:
            return {
                "enabled": False,
                "connected": False,
                "server_url": "Disabled",
                "indexed_projects": 0,
                "features": [],
            }

        from mcp_gw.socratiCode_client import SocratiCodeMCP
        
        server_cfg = mcp_cfg.server
        host = server_cfg.get("host", "localhost")
        port = server_cfg.get("port", 8934)
        url = f"http://{host}:{port}"
        
        mcp = SocratiCodeMCP(server_url=url)
        connected = mcp.connect_sync()
        
        # Detect if missing installation
        script_path = Path(__file__).parent.parent.parent / "scripts" / "setup_socratiCode.sh"
        compose_file = Path(__file__).parent.parent.parent / ".socratiCode" / "docker-compose.yml"
        
        # Auto-start/install logic if enabled and not connected
        if not connected and mcp_cfg.auto_start:
            logger.info("SocratiCode offline, checking infrastructure...")
            try:
                import subprocess
                if script_path.exists():
                    if not compose_file.exists():
                        logger.info("SocratiCode not installed, running targeted install...")
                        subprocess.Popen(
                            [str(script_path), "install"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True
                        ).wait(timeout=30) # Install is quick (just creating files)
                    
                    logger.info("Triggering SocratiCode start operation...")
                    subprocess.Popen(
                        [str(script_path), "start"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True
                    )
            except Exception as e:
                logger.warning(f"Failed to handle SocratiCode autonomous setup: {e}")

        # Try to get list of indexed projects
        indexed_projects = 0
        if connected:
            try:
                import httpx
                response = httpx.get(f"{url}/codebase/projects", timeout=2.0)
                if response.status_code == 200:
                    data = response.json()
                    indexed_projects = len(data.get("projects", []))
            except Exception:
                pass
        
        features = []
        if connected:
            features = ["semantic_search", "dependency_graph", "context_artifacts", "circular_deps"]
        
        return {
            "enabled": True,
            "connected": connected,
            "server_url": url,
            "indexed_projects": indexed_projects,
            "features": features,
        }
    except Exception as e:
        logger.warning(f"Could not check SocratiCode status: {e}")
        return {
            "enabled": False,
            "connected": False,
            "server_url": "Unknown",
            "indexed_projects": 0,
            "features": [],
        }


@router.get("/v1/socraticode", response_model=SocratiCodeStatus, tags=["TUI"])
async def get_socraticode_status() -> SocratiCodeStatus:
    """Get SocratiCode MCP integration status."""
    status = _get_socraticode_status()
    return SocratiCodeStatus(**status)


# =============================================================================
# Problem-Solver Endpoints
# =============================================================================

# In-memory storage für Problem-Solver (wird durch ProblemManager verwaltet)
_problem_managers: Dict[str, Any] = {}


def _get_problem_manager(repo_path: Optional[str] = None) -> Any:
    """
    Holt oder erstellt ProblemManager für Repository.
    
    Args:
        repo_path: Optionaler Repository-Pfad (default: config.repository.path)
    
    Returns:
        ProblemManager Instanz
    """
    from core.config import Config
    from problem.manager import ProblemManager
    
    if not repo_path:
        config = Config.load()
        repo_path = config.repository.path
    
    # Manager im Cache suchen
    if repo_path in _problem_managers:
        return _problem_managers[repo_path]
    
    # Neuen Manager erstellen
    manager = ProblemManager(repo_path=Path(repo_path))
    _problem_managers[repo_path] = manager
    
    return manager


@router.post(
    "/problems",
    response_model=ProblemResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Problem-Solver"],
)
async def create_problem(
    request: ProblemIntakeRequest,
) -> ProblemResponse:
    """
    Neues Problem aufnehmen.
    
    Erstellt ein neues ProblemCase aus einer rohen Problembeschreibung.
    Führt automatische initiale Klassifikation durch.
    
    Args:
        request: ProblemIntakeRequest mit Beschreibung und optionalen Metadaten
    
    Returns:
        ProblemResponse mit erstelltem Problem
    """
    manager = _get_problem_manager()
    
    # Problem aufnehmen
    problem = manager.intake_problem(
        description=request.description,
        title=request.title,
        source=request.source,
    )
    
    return ProblemResponse(
        id=problem.id,
        title=problem.title,
        raw_description=problem.raw_description,
        problem_type=problem.problem_type.value,
        severity=problem.severity.value,
        status=problem.status.value,
        goal_state=problem.goal_state,
        constraints=problem.constraints,
        affected_components=problem.affected_components,
        success_criteria=problem.success_criteria,
        risk_level=problem.risk_level,
        risk_factors=problem.risk_factors,
        created_at=problem.created_at,
        updated_at=problem.updated_at,
        source=problem.source,
    )


@router.get(
    "/problems",
    response_model=ProblemListResponse,
    tags=["Problem-Solver"],
)
async def list_problems(
    status_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
) -> ProblemListResponse:
    """
    Alle Probleme auflisten.
    
    Unterstützt optionale Filter nach Status und Typ.
    
    Args:
        status_filter: Filter nach Status (intake, diagnosis, planning, etc.)
        type_filter: Filter nach Typ (bug, performance, security, etc.)
    
    Returns:
        ProblemListResponse mit Liste von Problemen
    """
    manager = _get_problem_manager()
    
    # Filter konvertieren
    status_enum = None
    type_enum = None
    
    if status_filter:
        try:
            from problem.models import ProblemStatus
            status_enum = ProblemStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}",
            )
    
    if type_filter:
        try:
            from problem.models import ProblemType
            type_enum = ProblemType(type_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid type: {type_filter}",
            )
    
    # Probleme laden
    problems = manager.list_problems(
        status_filter=status_enum,
        type_filter=type_enum,
    )
    
    # In Response konvertieren
    problem_responses = [
        ProblemResponse(
            id=p.id,
            title=p.title,
            raw_description=p.raw_description,
            problem_type=p.problem_type.value,
            severity=p.severity.value,
            status=p.status.value,
            goal_state=p.goal_state,
            constraints=p.constraints,
            affected_components=p.affected_components,
            success_criteria=p.success_criteria,
            risk_level=p.risk_level,
            risk_factors=p.risk_factors,
            created_at=p.created_at,
            updated_at=p.updated_at,
            source=p.source,
        )
        for p in problems
    ]
    
    return ProblemListResponse(
        problems=problem_responses,
        total=len(problems),
    )


@router.get(
    "/problems/{problem_id}",
    response_model=ProblemResponse,
    tags=["Problem-Solver"],
)
async def get_problem(problem_id: str) -> ProblemResponse:
    """
    Problem-Details abrufen.
    
    Args:
        problem_id: ID des Problems
    
    Returns:
        ProblemResponse mit Problem-Details
    
    Raises:
        HTTPException: Wenn Problem nicht gefunden
    """
    manager = _get_problem_manager()
    
    problem = manager.get_problem(problem_id)
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem '{problem_id}' not found",
        )
    
    return ProblemResponse(
        id=problem.id,
        title=problem.title,
        raw_description=problem.raw_description,
        problem_type=problem.problem_type.value,
        severity=problem.severity.value,
        status=problem.status.value,
        goal_state=problem.goal_state,
        constraints=problem.constraints,
        affected_components=problem.affected_components,
        success_criteria=problem.success_criteria,
        risk_level=problem.risk_level,
        risk_factors=problem.risk_factors,
        created_at=problem.created_at,
        updated_at=problem.updated_at,
        source=problem.source,
    )


@router.post(
    "/problems/{problem_id}/classify",
    response_model=ClassificationResultResponse,
    tags=["Problem-Solver"],
)
async def classify_problem(problem_id: str) -> ClassificationResultResponse:
    """
    Problem klassifizieren.
    
    Führt detaillierte Klassifikation des Problems durch und
    aktualisiert das Problem mit den Ergebnissen.
    
    Args:
        problem_id: ID des zu klassifizierenden Problems
    
    Returns:
        ClassificationResultResponse mit Klassifikations-Ergebnis
    
    Raises:
        HTTPException: Wenn Problem nicht gefunden
    """
    manager = _get_problem_manager()
    
    try:
        result = manager.classify_problem(problem_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    # Alternative Klassifikationen formatieren
    alternatives = [
        {
            "problem_type": alt["problem_type"],
            "confidence": alt["confidence"],
        }
        for alt in result.alternatives
    ]
    
    return ClassificationResultResponse(
        problem_id=problem_id,
        problem_type=result.problem_type.value,
        confidence=result.confidence,
        keywords_found=result.keywords_found,
        affected_components=result.affected_components,
        recommended_actions=result.recommended_actions,
        alternatives=alternatives,
    )


@router.patch(
    "/problems/{problem_id}",
    response_model=ProblemResponse,
    tags=["Problem-Solver"],
)
async def update_problem(
    problem_id: str,
    request: ProblemUpdateRequest,
) -> ProblemResponse:
    """
    Problem aktualisieren.
    
    Aktualisiert einzelne Felder eines Problems.
    
    Args:
        problem_id: ID des Problems
        request: ProblemUpdateRequest mit zu aktualisierenden Feldern
    
    Returns:
        ProblemResponse mit aktualisiertem Problem
    
    Raises:
        HTTPException: Wenn Problem nicht gefunden
    """
    manager = _get_problem_manager()
    
    # Updates vorbereiten
    updates = request.model_dump(exclude_unset=True)
    
    try:
        problem = manager.update_problem(problem_id, updates)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem '{problem_id}' not found",
        )
    
    return ProblemResponse(
        id=problem.id,
        title=problem.title,
        raw_description=problem.raw_description,
        problem_type=problem.problem_type.value,
        severity=problem.severity.value,
        status=problem.status.value,
        goal_state=problem.goal_state,
        constraints=problem.constraints,
        affected_components=problem.affected_components,
        success_criteria=problem.success_criteria,
        risk_level=problem.risk_level,
        risk_factors=problem.risk_factors,
        created_at=problem.created_at,
        updated_at=problem.updated_at,
        source=problem.source,
    )


@router.delete(
    "/problems/{problem_id}",
    response_model=ProblemDeleteResponse,
    status_code=status.HTTP_200_OK,
    tags=["Problem-Solver"],
)
async def delete_problem(problem_id: str) -> ProblemDeleteResponse:
    """
    Problem löschen.
    
    Löscht ein ProblemCase permanent.
    
    Args:
        problem_id: ID des zu löschenden Problems
    
    Returns:
        ProblemDeleteResponse mit Status
    
    Raises:
        HTTPException: Wenn Problem nicht gefunden
    """
    manager = _get_problem_manager()
    
    if manager.delete_problem(problem_id):
        return ProblemDeleteResponse(
            success=True,
            problem_id=problem_id,
            message="Problem deleted successfully",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem '{problem_id}' not found",
        )


@router.get(
    "/problems/stats",
    response_model=ProblemStatisticsResponse,
    tags=["Problem-Solver"],
)
async def get_problem_statistics() -> ProblemStatisticsResponse:
    """
    Problem-Statistiken abrufen.
    
    Returns aggregierte Statistiken über alle Probleme.
    
    Returns:
        ProblemStatisticsResponse mit Statistiken
    """
    manager = _get_problem_manager()
    stats = manager.get_statistics()
    
    return ProblemStatisticsResponse(
        total_problems=stats["total_problems"],
        by_type=stats["by_type"],
        by_status=stats["by_status"],
        oldest_problem=stats["oldest_problem"],
        newest_problem=stats["newest_problem"],
    )


# Error handler for GlitchHunter exceptions (registered on app in server.py)
async def glitchhunter_exception_handler(
    request, exc: GlitchHunterException
) -> Dict[str, Any]:
    """Handle GlitchHunter exceptions."""
    logger.error(f"GlitchHunter error: {exc.message}", extra=exc.details)

    return {
        "error": exc.__class__.__name__,
        "message": exc.message,
        "code": exc.code,
        "details": exc.details,
    }
