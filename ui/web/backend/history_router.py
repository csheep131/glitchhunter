"""
History API Router für GlitchHunter Web-UI.

Bietet REST-API für History/Verlauf:
- Analyse-History
- Problem-History
- Report-History
- Statistiken
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ui.web.backend.history import get_history_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/history", tags=["History"])


# ============== Models ==============

class HistoryEntry(BaseModel):
    """Basis-Eintrag für History."""
    id: int
    created_at: str
    status: str


class AnalysisHistoryEntry(HistoryEntry):
    """Analyse-History-Eintrag."""
    job_id: str
    repo_path: str
    stack: str
    findings_count: int
    duration_seconds: float
    completed_at: Optional[str] = None


class ProblemHistoryEntry(HistoryEntry):
    """Problem-History-Eintrag."""
    problem_id: str
    prompt: str
    classification: Optional[str] = None
    duration_seconds: float


class ReportHistoryEntry(HistoryEntry):
    """Report-History-Eintrag."""
    report_id: str
    format: str
    job_id: Optional[str] = None
    problem_id: Optional[str] = None


class StatisticsResponse(BaseModel):
    """Statistik-Response."""
    period_days: int
    analysis: Dict[str, Any]
    problems: Dict[str, Any]
    reports: Dict[str, int]


class DailyStatsEntry(BaseModel):
    """Täglicher Statistik-Eintrag."""
    date: str
    total_analyses: int
    total_findings: int
    avg_duration: float
    completed_count: int
    failed_count: int


# ============== Endpoints ==============

@router.get("/analysis", response_model=List[AnalysisHistoryEntry])
async def get_analysis_history(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(None),
    repo: Optional[str] = Query(None),
):
    """Analyse-History abrufen."""
    try:
        manager = get_history_manager()
        history = manager.get_analysis_history(
            limit=limit,
            offset=offset,
            status_filter=status,
            repo_filter=repo,
        )
        return history
    except Exception as e:
        logger.error(f"Fehler beim Laden der Analyse-History: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/{job_id}", response_model=AnalysisHistoryEntry)
async def get_analysis_entry(job_id: str):
    """Einzelnen Analyse-Eintrag abrufen."""
    try:
        manager = get_history_manager()
        entry = manager.get_analysis_entry(job_id)
        
        if not entry:
            raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")
        
        return entry
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Laden des Analyse-Eintrags: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/analysis/{job_id}")
async def delete_analysis_entry(job_id: str):
    """Analyse-Eintrag löschen."""
    try:
        manager = get_history_manager()
        manager.delete_analysis_entry(job_id)
        
        return {"status": "success", "message": "Eintrag gelöscht"}
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Analyse-Eintrags: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/problems", response_model=List[ProblemHistoryEntry])
async def get_problem_history(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Problem-History abrufen."""
    try:
        manager = get_history_manager()
        history = manager.get_problem_history(limit=limit, offset=offset)
        return history
    except Exception as e:
        logger.error(f"Fehler beim Laden der Problem-History: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports", response_model=List[ReportHistoryEntry])
async def get_report_history(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Report-History abrufen."""
    try:
        manager = get_history_manager()
        history = manager.get_report_history(limit=limit, offset=offset)
        return history
    except Exception as e:
        logger.error(f"Fehler beim Laden der Report-History: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    days: int = Query(default=30, ge=1, le=365),
):
    """Statistiken für letzte X Tage abrufen."""
    try:
        manager = get_history_manager()
        stats = manager.get_statistics(days=days)
        return stats
    except Exception as e:
        logger.error(f"Fehler beim Laden der Statistiken: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily-stats", response_model=List[DailyStatsEntry])
async def get_daily_stats(
    days: int = Query(default=7, ge=1, le=90),
):
    """Tägliche Statistiken abrufen."""
    try:
        manager = get_history_manager()
        stats = manager.get_daily_stats(days=days)
        return stats
    except Exception as e:
        logger.error(f"Fehler beim Laden der täglichen Statistiken: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/all")
async def clear_all_history():
    """Gesamte History löschen."""
    try:
        manager = get_history_manager()
        manager.clear_all()
        
        return {"status": "success", "message": "Alle History-Einträge gelöscht"}
    except Exception as e:
        logger.error(f"Fehler beim Löschen der History: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_history(
    older_than_days: int = Query(default=90, ge=1, le=365),
):
    """Alte Einträge bereinigen."""
    try:
        manager = get_history_manager()
        manager.cleanup(older_than_days=older_than_days)
        
        return {
            "status": "success",
            "message": f"Einträge älter als {older_than_days} Tage gelöscht",
        }
    except Exception as e:
        logger.error(f"Fehler beim Bereinigen der History: {e}")
        raise HTTPException(status_code=500, detail=str(e))
