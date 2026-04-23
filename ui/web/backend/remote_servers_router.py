"""
Remote-Server API Router für GlitchHunter Web-UI.

Bietet REST-API für Remote-Server-Management:
- Server CRUD
- Status-Checks
- Verfügbare Modelle
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ui.web.backend.remote_servers import get_remote_server_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/servers", tags=["Remote-Servers"])


# ============== Models ==============

class ServerRequest(BaseModel):
    """Server-Request."""
    name: str
    host: str
    port: int
    api_type: str  # ollama, vllm, openai, custom
    api_key: Optional[str] = None
    enabled: bool = True


class ServerResponse(BaseModel):
    """Server-Response."""
    id: str
    name: str
    host: str
    port: int
    api_type: str
    enabled: bool
    status: str
    available_models: List[str]
    last_checked: Optional[str] = None
    error_message: Optional[str] = None


class ServerStatisticsResponse(BaseModel):
    """Server-Statistiken-Response."""
    total_servers: int
    online_servers: int
    offline_servers: int
    error_servers: int
    total_models: int


# ============== Endpoints ==============

@router.get("", response_model=List[ServerResponse])
async def get_all_servers():
    """Alle Remote-Server abrufen."""
    try:
        manager = get_remote_server_manager()
        
        # Status aller Server prüfen
        await manager.check_all_servers()
        
        servers = manager.get_all_servers()
        
        return [
            ServerResponse(
                id=s.id,
                name=s.name,
                host=s.host,
                port=s.port,
                api_type=s.api_type,
                enabled=s.enabled,
                status=s.status,
                available_models=s.available_models,
                last_checked=s.last_checked.isoformat() if s.last_checked else None,
                error_message=s.error_message,
            )
            for s in servers
        ]
    except Exception as e:
        logger.error(f"Fehler beim Laden der Server: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{server_id}", response_model=ServerResponse)
async def get_server(server_id: str):
    """Server-Details abrufen."""
    try:
        manager = get_remote_server_manager()
        server = manager.get_server(server_id)
        
        if not server:
            raise HTTPException(status_code=404, detail="Server nicht gefunden")
        
        # Status prüfen
        await manager.check_server_status(server_id)
        
        return ServerResponse(
            id=server.id,
            name=server.name,
            host=server.host,
            port=server.port,
            api_type=server.api_type,
            enabled=server.enabled,
            status=server.status,
            available_models=server.available_models,
            last_checked=server.last_checked.isoformat() if server.last_checked else None,
            error_message=server.error_message,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Laden des Servers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=ServerResponse)
async def add_server(request: ServerRequest):
    """Server hinzufügen."""
    try:
        manager = get_remote_server_manager()
        
        # ID generieren
        server_id = request.name.lower().replace(" ", "_")
        
        from ui.web.backend.remote_servers import RemoteServer
        server = RemoteServer(
            id=server_id,
            name=request.name,
            host=request.host,
            port=request.port,
            api_type=request.api_type,
            api_key=request.api_key,
            enabled=request.enabled,
        )
        
        if not manager.add_server(server):
            raise HTTPException(status_code=400, detail="Server existiert bereits")
        
        # Status prüfen
        await manager.check_server_status(server_id)
        
        return ServerResponse(
            id=server.id,
            name=server.name,
            host=server.host,
            port=server.port,
            api_type=server.api_type,
            enabled=server.enabled,
            status=server.status,
            available_models=server.available_models,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen des Servers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{server_id}", response_model=ServerResponse)
async def update_server(server_id: str, request: ServerRequest):
    """Server aktualisieren."""
    try:
        manager = get_remote_server_manager()
        
        updates = {
            "name": request.name,
            "host": request.host,
            "port": request.port,
            "api_type": request.api_type,
            "api_key": request.api_key,
            "enabled": request.enabled,
        }
        
        if not manager.update_server(server_id, updates):
            raise HTTPException(status_code=404, detail="Server nicht gefunden")
        
        # Status prüfen
        await manager.check_server_status(server_id)
        
        server = manager.get_server(server_id)
        
        return ServerResponse(
            id=server.id,
            name=server.name,
            host=server.host,
            port=server.port,
            api_type=server.api_type,
            enabled=server.enabled,
            status=server.status,
            available_models=server.available_models,
            last_checked=server.last_checked.isoformat() if server.last_checked else None,
            error_message=server.error_message,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Servers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{server_id}")
async def delete_server(server_id: str):
    """Server löschen."""
    try:
        manager = get_remote_server_manager()
        
        if not manager.delete_server(server_id):
            raise HTTPException(status_code=404, detail="Server nicht gefunden")
        
        return {"status": "success", "message": f"Server {server_id} gelöscht"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Servers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{server_id}/check")
async def check_server(server_id: str):
    """Server-Status prüfen."""
    try:
        manager = get_remote_server_manager()
        status = await manager.check_server_status(server_id)
        
        server = manager.get_server(server_id)
        
        return {
            "server_id": server_id,
            "status": status,
            "available_models": server.available_models if server else [],
            "error_message": server.error_message if server else None,
        }
    except Exception as e:
        logger.error(f"Fehler beim Status-Check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{server_id}/models", response_model=List[str])
async def get_server_models(server_id: str):
    """Verfügbare Modelle eines Servers abrufen."""
    try:
        manager = get_remote_server_manager()
        
        # Status prüfen um Modelle zu laden
        await manager.check_server_status(server_id)
        
        models = manager.get_available_models(server_id)
        
        return models
    except Exception as e:
        logger.error(f"Fehler beim Laden der Modelle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=ServerStatisticsResponse)
async def get_server_statistics():
    """Server-Statistiken abrufen."""
    try:
        manager = get_remote_server_manager()
        stats = manager.get_server_statistics()
        
        return ServerStatisticsResponse(**stats)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Statistiken: {e}")
        raise HTTPException(status_code=500, detail=str(e))
