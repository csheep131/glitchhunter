"""
Stack-API Router für GlitchHunter Web-UI.

Bietet REST-API für Stack-Management:
- Stack-Übersicht
- Konfiguration
- Testing
- Status
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ui.web.backend.stacks import get_stack_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stacks", tags=["Stacks"])


# ============== Models ==============

class StackConfigResponse(BaseModel):
    """Stack-Konfiguration Response."""
    id: str
    name: str
    description: str
    hardware: str
    mode: str
    models: Dict[str, str]
    security: Dict[str, Any]
    inference: Dict[str, Any]
    enabled: bool
    priority: int


class StackStatusResponse(BaseModel):
    """Stack-Status Response."""
    id: str
    status: str
    gpu_usage: float
    vram_usage: float
    temperature: float
    active_models: List[str]
    last_test: Optional[str]
    test_result: Optional[str]
    error_message: Optional[str]


class TestRequest(BaseModel):
    """Test-Request."""
    test_type: str = Field(default="quick", description="Test-Typ (quick, performance, stress)")


class TestResultResponse(BaseModel):
    """Test-Ergebnis Response."""
    test_id: str
    stack_id: str
    test_type: str
    status: str
    duration_seconds: float
    results: Dict[str, Any]
    recommendation: str
    created_at: str


# ============== Endpoints ==============

@router.get("", response_model=List[StackConfigResponse])
async def get_all_stacks():
    """Alle Stacks abrufen."""
    try:
        manager = get_stack_manager()
        stacks = manager.get_all_stacks()
        
        return [
            StackConfigResponse(
                id=s.id,
                name=s.name,
                description=s.description,
                hardware=s.hardware,
                mode=s.mode,
                models=s.models,
                security=s.security,
                inference=s.inference,
                enabled=s.enabled,
                priority=s.priority,
            )
            for s in stacks
        ]
    except Exception as e:
        logger.error(f"Fehler beim Laden der Stacks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{stack_id}", response_model=StackConfigResponse)
async def get_stack(stack_id: str):
    """Stack-Details abrufen."""
    try:
        manager = get_stack_manager()
        stack = manager.get_stack(stack_id)
        
        if not stack:
            raise HTTPException(status_code=404, detail="Stack nicht gefunden")
        
        return StackConfigResponse(
            id=stack.id,
            name=stack.name,
            description=stack.description,
            hardware=stack.hardware,
            mode=stack.mode,
            models=stack.models,
            security=stack.security,
            inference=stack.inference,
            enabled=stack.enabled,
            priority=stack.priority,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Laden des Stacks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{stack_id}")
async def update_stack(stack_id: str, updates: Dict[str, Any]):
    """Stack-Konfiguration aktualisieren."""
    try:
        manager = get_stack_manager()
        manager.update_stack_config(stack_id, updates)
        
        return {"status": "success", "message": f"Stack {stack_id} aktualisiert"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Stacks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{stack_id}/status", response_model=StackStatusResponse)
async def get_stack_status(stack_id: str):
    """Stack-Status abrufen."""
    try:
        manager = get_stack_manager()
        
        # Status aktualisieren
        await manager.update_stack_status(stack_id)
        
        status = manager.get_stack_status(stack_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Stack nicht gefunden")
        
        return StackStatusResponse(
            id=status.id,
            status=status.status,
            gpu_usage=status.gpu_usage,
            vram_usage=status.vram_usage,
            temperature=status.temperature,
            active_models=status.active_models,
            last_test=status.last_test.isoformat() if status.last_test else None,
            test_result=status.test_result,
            error_message=status.error_message,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Laden des Stack-Status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{stack_id}/test", response_model=TestResultResponse)
async def test_stack(stack_id: str, request: TestRequest):
    """Stack testen."""
    try:
        manager = get_stack_manager()
        
        result = await manager.test_stack(
            stack_id=stack_id,
            test_type=request.test_type,
        )
        
        return TestResultResponse(
            test_id=result.test_id,
            stack_id=result.stack_id,
            test_type=result.test_type,
            status=result.status,
            duration_seconds=result.duration_seconds,
            results=result.results,
            recommendation=result.recommendation,
            created_at=result.created_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Fehler beim Testen des Stacks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{stack_id}/tests", response_model=List[TestResultResponse])
async def get_test_history(stack_id: str, limit: int = 10):
    """Test-Historie für Stack abrufen."""
    try:
        manager = get_stack_manager()
        tests = manager.get_test_history(stack_id, limit=limit)
        
        return [
            TestResultResponse(
                test_id=t.test_id,
                stack_id=t.stack_id,
                test_type=t.test_type,
                status=t.status,
                duration_seconds=t.duration_seconds,
                results=t.results,
                recommendation=t.recommendation,
                created_at=t.created_at.isoformat(),
            )
            for t in tests
        ]
    except Exception as e:
        logger.error(f"Fehler beim Laden der Test-Historie: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{stack_id}/tests/{test_id}", response_model=TestResultResponse)
async def get_test_result(stack_id: str, test_id: str):
    """Test-Ergebnis abrufen."""
    try:
        manager = get_stack_manager()
        result = manager.get_test_result(test_id)
        
        if not result or result.stack_id != stack_id:
            raise HTTPException(status_code=404, detail="Test nicht gefunden")
        
        return TestResultResponse(
            test_id=result.test_id,
            stack_id=result.stack_id,
            test_type=result.test_type,
            status=result.status,
            duration_seconds=result.duration_seconds,
            results=result.results,
            recommendation=result.recommendation,
            created_at=result.created_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Laden des Test-Ergebnisses: {e}")
        raise HTTPException(status_code=500, detail=str(e))
