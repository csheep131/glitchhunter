"""
Remote-Server Manager für GlitchHunter Web-UI.

Verwaltet LLM-Server im lokalen Netzwerk:
- Server hinzufügen/entfernen
- Server-Status prüfen
- Verfügbare Modelle laden
- API-Endpunkte konfigurieren

Beispiel-Server:
- asgard (lokaler Host)
- Ollama-Server
- vLLM-Server
- Custom-API-Server
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class RemoteServer:
    """Remote-LLM-Server."""
    id: str
    name: str
    host: str  # IP oder Hostname
    port: int
    api_type: str  # ollama, vllm, openai, custom
    api_key: Optional[str] = None
    enabled: bool = True
    available_models: List[str] = field(default_factory=list)
    last_checked: Optional[datetime] = None
    status: str = "unknown"  # online, offline, error
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class RemoteServerManager:
    """
    Manager für Remote-LLM-Server.
    
    Features:
    - Server verwalten (CRUD)
    - Server-Status prüfen
    - Verfügbare Modelle laden
    - API-Typen unterstützen (Ollama, vLLM, OpenAI)
    
    Usage:
        manager = RemoteServerManager()
        manager.initialize()
        servers = manager.get_all_servers()
    """
    
    def __init__(self):
        """Initialisiert Server-Manager."""
        self._servers: Dict[str, RemoteServer] = {}
        
        logger.info("RemoteServerManager initialisiert")
    
    def initialize(self):
        """Initialisiert Server mit Defaults."""
        logger.info("Initialisiere Remote-Server...")
        
        # Default: OpenWebUI auf Asgard (bereits installiert!)
        self._servers["openwebui_asgard"] = RemoteServer(
            id="openwebui_asgard",
            name="💬 OpenWebUI (Asgard)",
            host="asgard",
            port=3000,
            api_type="openwebui",
            enabled=True,
            metadata={
                "web_url": "http://asgard:3000",
                "backend_url": "http://asgard-llm:8081/v1",
                "description": "OpenWebUI Chat-Interface auf Asgard",
            },
        )
        
        # Ollama auf Asgard (für Model-Management)
        self._servers["ollama_asgard"] = RemoteServer(
            id="ollama_asgard",
            name="🦙 Ollama (Asgard)",
            host="asgard",
            port=11434,
            api_type="ollama",
            enabled=True,
        )
        
        logger.info(f"{len(self._servers)} Server initialisiert")
    
    def get_all_servers(self) -> List[RemoteServer]:
        """
        Returns alle Server.
        
        Returns:
            Liste von RemoteServer
        """
        return list(self._servers.values())
    
    def get_server(self, server_id: str) -> Optional[RemoteServer]:
        """
        Returns Server nach ID.
        
        Args:
            server_id: Server-ID
            
        Returns:
            RemoteServer oder None
        """
        return self._servers.get(server_id)
    
    def add_server(self, server: RemoteServer) -> bool:
        """
        Fügt Server hinzu.
        
        Args:
            server: RemoteServer
            
        Returns:
            True wenn erfolgreich
        """
        if server.id in self._servers:
            return False
        
        self._servers[server.id] = server
        logger.info(f"Server hinzugefügt: {server.name}")
        return True
    
    def update_server(self, server_id: str, updates: Dict[str, Any]) -> bool:
        """
        Aktualisiert Server.
        
        Args:
            server_id: Server-ID
            updates: Updates-Dict
            
        Returns:
            True wenn erfolgreich
        """
        if server_id not in self._servers:
            # Server existiert nicht - vielleicht ist es eine ID-Änderung?
            # Versuchen wir den Server zu finden und zu aktualisieren
            logger.warning(f"Server {server_id} nicht gefunden, versuche Update trotzdem")
            return False
        
        server = self._servers[server_id]
        
        for key, value in updates.items():
            if hasattr(server, key):
                setattr(server, key, value)
        
        # Wenn sich die ID geändert hat
        if 'id' in updates and updates['id'] != server_id:
            self._servers[updates['id']] = server
            del self._servers[server_id]
        
        logger.info(f"Server aktualisiert: {server.name} ({server_id})")
        return True
    
    def delete_server(self, server_id: str) -> bool:
        """
        Löscht Server.
        
        Args:
            server_id: Server-ID
            
        Returns:
            True wenn erfolgreich
        """
        if server_id not in self._servers:
            return False
        
        del self._servers[server_id]
        logger.info(f"Server gelöscht: {server_id}")
        return True
    
    async def check_server_status(self, server_id: str) -> str:
        """
        Prüft Server-Status.
        
        Args:
            server_id: Server-ID
            
        Returns:
            Status (online, offline, error)
        """
        server = self._servers.get(server_id)
        if not server:
            return "error"
        
        try:
            api_url = f"http://{server.host}:{server.port}"
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                if server.api_type == "ollama":
                    # Ollama API prüfen
                    response = await client.get(f"{api_url}/api/tags")
                    if response.status_code == 200:
                        server.status = "online"
                        server.error_message = None
                        
                        # Verfügbare Modelle laden
                        data = response.json()
                        server.available_models = [
                            model["name"] for model in data.get("models", [])
                        ]
                    else:
                        server.status = "offline"
                        server.error_message = f"HTTP {response.status_code}"
                
                elif server.api_type == "openwebui":
                    # OpenWebUI - Web-UI prüfen
                    response = await client.get(f"{api_url}")
                    if response.status_code == 200:
                        server.status = "online"
                        server.available_models = ["Chat verfügbar"]
                        server.error_message = None
                    else:
                        server.status = "offline"
                        server.error_message = f"HTTP {response.status_code}"
                
                elif server.api_type == "vllm":
                    # vLLM API prüfen
                    response = await client.get(f"{api_url}/v1/models")
                    if response.status_code == 200:
                        server.status = "online"
                        data = response.json()
                        server.available_models = [
                            model["id"] for model in data.get("data", [])
                        ]
                    else:
                        server.status = "offline"
                
                elif server.api_type == "openai":
                    # OpenAI API prüfen
                    headers = {}
                    if server.api_key:
                        headers["Authorization"] = f"Bearer {server.api_key}"
                    
                    response = await client.get(
                        f"{api_url}/v1/models",
                        headers=headers,
                    )
                    if response.status_code == 200:
                        server.status = "online"
                    else:
                        server.status = "offline"
                        server.error_message = f"HTTP {response.status_code}"
                
                else:
                    # Custom API - einfacher Health-Check
                    response = await client.get(f"{api_url}/health")
                    server.status = "online" if response.status_code == 200 else "offline"
            
            server.last_checked = datetime.now()
            
        except Exception as e:
            server.status = "error"
            server.error_message = str(e)
            logger.error(f"Status-Check für {server.name} fehlgeschlagen: {e}")
        
        return server.status
    
    async def check_all_servers(self):
        """
        Prüft alle Server parallel.
        """
        tasks = [
            self.check_server_status(server_id)
            for server_id in self._servers
        ]
        
        await asyncio.gather(*tasks)
    
    def get_available_models(self, server_id: str) -> List[str]:
        """
        Returns verfügbare Modelle eines Servers.
        
        Args:
            server_id: Server-ID
            
        Returns:
            Liste von Modell-Namen
        """
        server = self._servers.get(server_id)
        if not server:
            return []
        
        return server.available_models
    
    def get_server_statistics(self) -> Dict[str, Any]:
        """
        Returns Server-Statistiken.
        
        Returns:
            Statistik-Dict
        """
        servers = list(self._servers.values())
        
        return {
            "total_servers": len(servers),
            "online_servers": sum(1 for s in servers if s.status == "online"),
            "offline_servers": sum(1 for s in servers if s.status == "offline"),
            "error_servers": sum(1 for s in servers if s.status == "error"),
            "total_models": sum(len(s.available_models) for s in servers),
        }


# ============== Globale Instanz ==============

_remote_server_manager: Optional[RemoteServerManager] = None


def get_remote_server_manager() -> RemoteServerManager:
    """
    Returns globale RemoteServerManager-Instanz.
    
    Returns:
        RemoteServerManager
    """
    global _remote_server_manager
    if _remote_server_manager is None:
        _remote_server_manager = RemoteServerManager()
        _remote_server_manager.initialize()
    return _remote_server_manager
