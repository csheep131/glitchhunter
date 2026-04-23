"""
Model-Monitoring API Router für GlitchHunter Web-UI.

Bietet REST-API für Model-Management:
- Modell-Übersicht
- Status-Checks
- Load/Unload
- Health-Checks
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ui.web.backend.models import get_model_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/models", tags=["Models"])


# ============== Models ==============

class ModelResponse(BaseModel):
    """Modell-Response."""
    id: str
    name: str
    type: str
    provider: Optional[str] = None
    loaded: bool
    vram_usage_mb: float
    size_mb: float
    quantization: str
    last_used: Optional[str] = None
    load_count: int = 0
    avg_inference_time_ms: float = 0.0


class RemoteModelResponse(ModelResponse):
    """Remote-Modell-Response."""
    api_url: str
    rate_limit_per_minute: int
    requests_today: int
    avg_latency_ms: float
    availability: float


class LoadModelRequest(BaseModel):
    """Load-Request."""
    model_id: str = Field(..., description="Modell-ID")


class LoadModelResponse(BaseModel):
    """Load-Response."""
    success: bool
    message: str
    model_id: str


class HealthCheckResponse(BaseModel):
    """Health-Check-Response."""
    model_id: str
    status: str
    message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class ModelStatisticsResponse(BaseModel):
    """Modell-Statistiken-Response."""
    total_local: int
    total_remote: int
    local_loaded: int
    remote_available: int
    total_vram_usage_mb: float
    total_load_count: int


# ============== Endpoints ==============

@router.get("", response_model=List[ModelResponse])
async def get_all_models():
    """Alle Modelle abrufen."""
    try:
        manager = get_model_manager()
        models = manager.get_all_models()
        
        return [
            ModelResponse(
                id=m.id,
                name=m.name,
                type=m.type,
                provider=m.provider,
                loaded=m.loaded,
                vram_usage_mb=m.vram_usage_mb,
                size_mb=m.size_mb,
                quantization=m.quantization,
                last_used=m.last_used.isoformat() if m.last_used else None,
                load_count=m.load_count,
                avg_inference_time_ms=m.avg_inference_time_ms,
            )
            for m in models
        ]
    except Exception as e:
        logger.error(f"Fehler beim Laden der Modelle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/local", response_model=List[ModelResponse])
async def get_local_models():
    """Lokale Modelle abrufen."""
    try:
        manager = get_model_manager()
        models = manager.get_local_models()
        
        return [
            ModelResponse(
                id=m.id,
                name=m.name,
                type=m.type,
                provider=m.provider,
                loaded=m.loaded,
                vram_usage_mb=m.vram_usage_mb,
                size_mb=m.size_mb,
                quantization=m.quantization,
                last_used=m.last_used.isoformat() if m.last_used else None,
                load_count=m.load_count,
                avg_inference_time_ms=m.avg_inference_time_ms,
            )
            for m in models
        ]
    except Exception as e:
        logger.error(f"Fehler beim Laden der lokalen Modelle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/remote", response_model=List[RemoteModelResponse])
async def get_remote_models():
    """Remote-Modelle abrufen."""
    try:
        manager = get_model_manager()
        models = manager.get_remote_models()
        
        return [
            RemoteModelResponse(
                id=m.id,
                name=m.name,
                type=m.type,
                provider=m.provider,
                loaded=m.loaded,
                vram_usage_mb=m.vram_usage_mb,
                size_mb=m.size_mb,
                quantization=m.quantization,
                last_used=m.last_used.isoformat() if m.last_used else None,
                load_count=m.load_count,
                avg_inference_time_ms=m.avg_inference_time_ms,
                api_url=m.api_url,
                rate_limit_per_minute=m.rate_limit_per_minute,
                requests_today=m.requests_today,
                avg_latency_ms=m.avg_latency_ms,
                availability=m.availability,
            )
            for m in models
        ]
    except Exception as e:
        logger.error(f"Fehler beim Laden der Remote-Modelle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(model_id: str):
    """Modell-Details abrufen."""
    try:
        manager = get_model_manager()
        model = manager.get_model(model_id)
        
        if not model:
            raise HTTPException(status_code=404, detail="Modell nicht gefunden")
        
        return ModelResponse(
            id=model.id,
            name=model.name,
            type=model.type,
            provider=model.provider,
            loaded=model.loaded,
            vram_usage_mb=model.vram_usage_mb,
            size_mb=model.size_mb,
            quantization=model.quantization,
            last_used=model.last_used.isoformat() if model.last_used else None,
            load_count=model.load_count,
            avg_inference_time_ms=model.avg_inference_time_ms,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Laden des Modells: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/load", response_model=LoadModelResponse)
async def load_model(request: LoadModelRequest):
    """Modell laden."""
    try:
        manager = get_model_manager()
        success = await manager.load_model(request.model_id)
        
        return LoadModelResponse(
            success=success,
            message=f"Modell {request.model_id} {'erfolgreich geladen' if success else 'konnte nicht geladen werden'}",
            model_id=request.model_id,
        )
    except Exception as e:
        logger.error(f"Fehler beim Laden des Modells: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unload", response_model=LoadModelResponse)
async def unload_model(request: LoadModelRequest):
    """Modell entladen."""
    try:
        manager = get_model_manager()
        success = await manager.unload_model(request.model_id)

        return LoadModelResponse(
            success=success,
            message=f"Modell {request.model_id} {'erfolgreich entladen' if success else 'konnte nicht entladen werden'}",
            model_id=request.model_id,
        )
    except Exception as e:
        logger.error(f"Fehler beim Entladen des Modells: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=ModelStatisticsResponse)
async def get_model_statistics():
    """Modell-Statistiken abrufen."""
    try:
        manager = get_model_manager()
        stats = manager.get_model_statistics()
        
        return ModelStatisticsResponse(**stats)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Statistiken: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{model_id}/health", response_model=HealthCheckResponse)
async def check_model_health(model_id: str):
    """Modell-Gesundheit prüfen."""
    try:
        manager = get_model_manager()
        result = await manager.check_model_health(model_id)
        
        return HealthCheckResponse(
            model_id=model_id,
            status=result.get("status", "unknown"),
            message=result.get("message"),
            details={k: v for k, v in result.items() if k not in ["status", "message"]},
        )
    except Exception as e:
        logger.error(f"Fehler beim Health-Check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=ModelStatisticsResponse)
async def get_model_statistics():
    """Modell-Statistiken abrufen."""
    try:
        manager = get_model_manager()
        stats = manager.get_model_statistics()
        
        return ModelStatisticsResponse(
            total_local=stats["total_local"],
            total_remote=stats["total_remote"],
            local_loaded=stats["local_loaded"],
            remote_available=stats["remote_available"],
            total_vram_usage_mb=stats["total_vram_usage_mb"],
            total_load_count=stats["total_load_count"],
        )
    except Exception as e:
        logger.error(f"Fehler beim Laden der Statistiken: {e}")
        raise HTTPException(status_code=500, detail=str(e))
