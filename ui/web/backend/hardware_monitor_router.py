"""
Hardware-Monitoring API Router für GlitchHunter Web-UI.

Bietet REST-API für Hardware-Überwachung:
- GPU-Status
- CPU-Status
- RAM-Status
- Historie
- Alarme
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ui.web.backend.hardware_monitor import get_hardware_monitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/hardware", tags=["Hardware"])


# ============== Models ==============

class GPUInfoResponse(BaseModel):
    """GPU-Info Response."""
    name: str
    available: bool
    usage: float
    vram_used: int
    vram_total: int
    temperature: float
    power_draw: float
    fan_speed: int
    error: str = None


class CPUInfoResponse(BaseModel):
    """CPU-Info Response."""
    model: str
    cores: int
    usage: float
    frequency_mhz: float
    temperature: float
    per_core_usage: List[float] = Field(default_factory=list)


class MemoryInfoResponse(BaseModel):
    """RAM-Info Response."""
    total: int
    used: int
    free: int
    percent: float
    swap_total: int
    swap_used: int
    swap_percent: float


class HardwareSummaryResponse(BaseModel):
    """Hardware-Zusammenfassung Response."""
    gpu: Dict[str, Any]
    cpu: Dict[str, Any]
    memory: Dict[str, Any]


class HistoryEntryResponse(BaseModel):
    """Historie-Eintrag Response."""
    timestamp: str
    gpu_usage: float
    gpu_vram: int
    gpu_temp: float
    cpu_usage: float
    memory_percent: float


class AlertResponse(BaseModel):
    """Alarm Response."""
    level: str
    component: str
    message: str


# ============== Endpoints ==============

@router.get("", response_model=HardwareSummaryResponse)
async def get_hardware_summary():
    """Hardware-Zusammenfassung abrufen."""
    try:
        monitor = get_hardware_monitor()
        summary = monitor.get_hardware_summary()
        
        return HardwareSummaryResponse(**summary)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Hardware-Zusammenfassung: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gpu", response_model=GPUInfoResponse)
async def get_gpu_info():
    """GPU-Informationen abrufen."""
    try:
        monitor = get_hardware_monitor()
        gpu = monitor.get_gpu_info()
        
        return GPUInfoResponse(
            name=gpu.name,
            available=gpu.available,
            usage=gpu.usage,
            vram_used=gpu.vram_used,
            vram_total=gpu.vram_total,
            temperature=gpu.temperature,
            power_draw=gpu.power_draw,
            fan_speed=gpu.fan_speed,
            error=gpu.error,
        )
    except Exception as e:
        logger.error(f"Fehler beim Laden der GPU-Infos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cpu", response_model=CPUInfoResponse)
async def get_cpu_info():
    """CPU-Informationen abrufen."""
    try:
        monitor = get_hardware_monitor()
        cpu = monitor.get_cpu_info()
        
        return CPUInfoResponse(
            model=str(cpu.model) if cpu.model else "Unknown",
            cores=cpu.cores_logical,
            usage=cpu.usage,
            frequency_mhz=cpu.frequency_mhz,
            temperature=cpu.temperature,
            per_core_usage=cpu.per_core_usage,
        )
    except Exception as e:
        logger.error(f"Fehler beim Laden der CPU-Infos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory", response_model=MemoryInfoResponse)
async def get_memory_info():
    """RAM-Informationen abrufen."""
    try:
        monitor = get_hardware_monitor()
        memory = monitor.get_memory_info()
        
        return MemoryInfoResponse(
            total=memory.total,
            used=memory.used,
            free=memory.free,
            percent=memory.percent,
            swap_total=memory.swap_total,
            swap_used=memory.swap_used,
            swap_percent=memory.swap_percent,
        )
    except Exception as e:
        logger.error(f"Fehler beim Laden der RAM-Infos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=List[HistoryEntryResponse])
async def get_history(minutes: int = 5):
    """Historie abrufen."""
    try:
        monitor = get_hardware_monitor()
        history = monitor.get_history(minutes=minutes)
        
        return [HistoryEntryResponse(**h) for h in history]
    except Exception as e:
        logger.error(f"Fehler beim Laden der Historie: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts():
    """Hardware-Alarme abrufen."""
    try:
        monitor = get_hardware_monitor()
        alerts = monitor.get_alerts()
        
        return [AlertResponse(**a) for a in alerts]
    except Exception as e:
        logger.error(f"Fehler beim Laden der Alarme: {e}")
        raise HTTPException(status_code=500, detail=str(e))
