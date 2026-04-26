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


class UpdateModelPathResponse(BaseModel):
    """Response für Pfad-Aktualisierung."""
    success: bool
    message: str
    model_id: str
    path: str


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

# WICHTIG: Statische Pfade VOR /{model_id} definieren,
# sonst greift FastAPIs Route-Matching fälschlicherweise auf {model_id} zu!

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


@router.get("/by_stack", response_model=Dict[str, List[Dict[str, Any]]])
async def get_models_by_stack():
    """Alle lokalen Modelle nach Stack gruppiert abrufen."""
    try:
        manager = get_model_manager()
        return manager.get_available_models_by_stack()
    except Exception as e:
        logger.error(f"Fehler beim Laden der Modelle nach Stack: {e}")
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


@router.get("/llama_status")
async def get_llama_status():
    """Prüft ob llama.cpp Server läuft und gibt VRAM-Status."""
    try:
        import subprocess
        import os
        
        result = {
            "llama_running": False,
            "llama_pid": None,
            "vram_total_mb": 0,
            "vram_used_mb": 0,
            "vram_free_mb": 0,
            "vram_usage_pct": 0,
            "gpu_name": "",
            "loaded_model": None,
        }
        
        # Prüfe ob llama.cpp Prozess läuft
        try:
            ps = subprocess.run(
                ["pgrep", "-a", "llama"],
                capture_output=True, text=True, timeout=5
            )
            if ps.returncode == 0:
                lines = ps.stdout.strip().split('\n')
                for line in lines:
                    if 'llama' in line.lower() and ('server' in line.lower() or 'main' in line.lower()):
                        parts = line.split()
                        result["llama_running"] = True
                        result["llama_pid"] = int(parts[0]) if parts else None
                        # Versuche Modellnamen aus Kommandozeile zu extrahieren
                        for i, p in enumerate(parts):
                            if p in ['-m', '--model'] and i + 1 < len(parts):
                                result["loaded_model"] = parts[i + 1].split('/')[-1]
                        break
        except Exception as e:
            logger.debug(f"pgrep llama fehlgeschlagen: {e}")
        
        # nvidia-smi für VRAM
        try:
            smi = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10
            )
            if smi.returncode == 0:
                line = smi.stdout.strip().split('\n')[0]
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 4:
                    result["gpu_name"] = parts[0]
                    result["vram_total_mb"] = float(parts[1])
                    result["vram_used_mb"] = float(parts[2])
                    result["vram_free_mb"] = float(parts[3])
                    result["vram_usage_pct"] = round(float(parts[2]) / float(parts[1]) * 100, 1) if float(parts[1]) > 0 else 0
        except Exception as e:
            logger.debug(f"nvidia-smi fehlgeschlagen: {e}")
        
        return result
    except Exception as e:
        logger.error(f"Fehler beim LLaMA-Status: {e}")
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


class UpdateModelPathRequest(BaseModel):
    """Request zum Aktualisieren eines Modell-Pfads."""
    model_id: str = Field(..., description="Modell-ID")
    path: str = Field(..., description="Neuer Pfad zum Modell")


@router.put("/{model_id}/path", response_model=UpdateModelPathResponse)
async def update_model_path(model_id: str, request: UpdateModelPathRequest):
    """Modell-Pfad aktualisieren."""
    try:
        manager = get_model_manager()
        success = manager.update_model_path(model_id, request.path)

        return UpdateModelPathResponse(
            success=success,
            message=f"Modell-Pfad für {model_id} {'aktualisiert' if success else 'konnte nicht aktualisiert werden'}",
            model_id=model_id,
            path=request.path,
        )
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Modell-Pfads: {e}")
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


