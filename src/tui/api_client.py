"""API Client for TUI to communicate with GlitchHunter API."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)


class TUIApiClient:
    """HTTP client for TUI to fetch real data from API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=5.0)
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
    
    async def _get(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Make GET request to API."""
        try:
            url = urljoin(self.base_url, f"/api/{endpoint}")
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return None
    
    async def get_status(self) -> Optional[Dict[str, Any]]:
        """Get complete system status."""
        return await self._get("v1/status")
    
    async def get_stack(self) -> Optional[Dict[str, Any]]:
        """Get current stack info."""
        return await self._get("v1/stack")
    
    async def get_models(self) -> Optional[List[Dict[str, Any]]]:
        """Get available models."""
        result = await self._get("v1/models")
        return result if isinstance(result, list) else None
    
    async def get_system(self) -> Optional[Dict[str, Any]]:
        """Get system resources."""
        return await self._get("v1/system")
    
    async def get_health(self) -> Optional[Dict[str, Any]]:
        """Get health check."""
        return await self._get("health")
    
    async def get_socraticode(self) -> Optional[Dict[str, Any]]:
        """Get SocratiCode MCP status."""
        return await self._get("v1/socraticode")
    
    async def start_analysis(
        self, 
        repo_path: str, 
        security: bool = True, 
        correctness: bool = True, 
        patches: bool = True,
        index_mcp: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Start analysis job."""
        try:
            url = urljoin(self.base_url, "/api/analyze")
            response = await self.client.post(
                url,
                json={
                    "repo_path": repo_path, 
                    "scan_security": security, 
                    "scan_correctness": correctness,
                    "generate_patches": patches,
                    "index_mcp": index_mcp
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to start analysis: {e}")
            return None
    
    def is_api_online(self) -> bool:
        """Check if API is online (sync for startup)."""
        try:
            response = httpx.get(urljoin(self.base_url, "/api/health"), timeout=2.0)
            return response.status_code == 200
        except Exception:
            return False
