"""
API routes for GlitchHunter.

Defines all REST API endpoints for analysis, status, hardware info, and escalation.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status

from core.exceptions import GlitchHunterException
from hardware.detector import HardwareDetector
from api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalysisResult,
    EscalationRequest,
    HardwareInfo,
    HealthResponse,
    StatusResponse,
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
async def start_analysis(request: AnalyzeRequest) -> AnalyzeResponse:
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

    # TODO: Start background analysis task
    # For now, just return the analysis ID

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
