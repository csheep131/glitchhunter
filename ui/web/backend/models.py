"""
Model-Monitoring Manager für GlitchHunter Web-UI.

Überwacht lokale und Remote-Modelle mit:
- Modell-Status (geladen, entladen, verfügbar)
- VRAM-Verbrauch
- Response-Zeiten
- Verfügbarkeit

Features:
- Lokale Modelle (Pfad, Größe, VRAM)
- Remote Modelle (API, Latenz, Rate-Limit)
- Auto-Loading bei Bedarf
- Health-Checks
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Informationen über ein Modell."""
    id: str
    name: str
    type: str  # local, remote
    provider: Optional[str] = None
    path: Optional[str] = None
    size_mb: float = 0.0
    quantization: str = "full"
    loaded: bool = False
    vram_usage_mb: float = 0.0
    last_used: Optional[datetime] = None
    load_count: int = 0
    avg_inference_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RemoteModelInfo(ModelInfo):
    """Informationen über ein Remote-Modell."""
    api_url: str = ""
    api_key_env: Optional[str] = None
    rate_limit_per_minute: int = 60
    requests_today: int = 0
    last_request: Optional[datetime] = None
    avg_latency_ms: float = 0.0
    availability: float = 100.0


class ModelManager:
    """
    Manager für KI-Modelle.
    
    Features:
    - Lokale Modelle verwalten
    - Remote-Modelle verwalten
    - Status-Überwachung
    - Load/Unload
    - Health-Checks
    
    Usage:
        manager = ModelManager()
        manager.initialize()
        models = manager.get_all_models()
    """
    
    def __init__(self):
        """Initialisiert Model-Manager."""
        self._local_models: Dict[str, ModelInfo] = {}
        self._remote_models: Dict[str, RemoteModelInfo] = {}
        self._model_cache: Dict[str, Any] = {}
        
        logger.info("ModelManager initialisiert")
    
    def initialize(self):
        """Initialisiert alle Modelle."""
        logger.info("Initialisiere Modelle...")
        
        # Lokale Modelle (Beispiele)
        self._local_models["qwen3.5-9b-q4_k_m"] = ModelInfo(
            id="qwen3.5-9b-q4_k_m",
            name="Qwen3.5-9B (4-bit)",
            type="local",
            path="/models/qwen3.5-9b-q4_k_m.gguf",
            size_mb=5400.0,
            quantization="q4_k_m",
            loaded=False,
            metadata={
                "context_length": 8192,
                "n_layers": 32,
                "n_embd": 4096,
            },
        )
        
        self._local_models["qwen3.5-27b-q4_k_m"] = ModelInfo(
            id="qwen3.5-27b-q4_k_m",
            name="Qwen3.5-27B (4-bit)",
            type="local",
            path="/models/qwen3.5-27b-q4_k_m.gguf",
            size_mb=16800.0,
            quantization="q4_k_m",
            loaded=False,
            metadata={
                "context_length": 16384,
                "n_layers": 48,
                "n_embd": 5120,
            },
        )
        
        self._local_models["phi-4-mini-q8"] = ModelInfo(
            id="phi-4-mini-q8",
            name="Phi-4-mini (8-bit)",
            type="local",
            path="/models/phi-4-mini-q8.gguf",
            size_mb=3200.0,
            quantization="q8",
            loaded=False,
            metadata={
                "context_length": 4096,
                "n_layers": 24,
            },
        )
        
        # Remote-Modelle
        self._remote_models["ollama-qwen3.5-9b"] = RemoteModelInfo(
            id="ollama-qwen3.5-9b",
            name="Qwen3.5-9B (Ollama)",
            type="remote",
            provider="ollama",
            api_url="http://localhost:11434",
            api_key_env=None,
            rate_limit_per_minute=120,
            loaded=True,  # Ollama ist immer "geladen"
            metadata={
                "context_length": 8192,
            },
        )
        
        self._remote_models["openai-gpt-4o"] = RemoteModelInfo(
            id="openai-gpt-4o",
            name="GPT-4o (OpenAI)",
            type="remote",
            provider="openai",
            api_url="https://api.openai.com/v1",
            api_key_env="OPENAI_API_KEY",
            rate_limit_per_minute=10,
            loaded=True,
            metadata={
                "context_length": 128000,
                "cost_per_1k_tokens": 0.005,
            },
        )
        
        self._remote_models["anthropic-claude-3-5-sonnet"] = RemoteModelInfo(
            id="anthropic-claude-3-5-sonnet",
            name="Claude 3.5 Sonnet (Anthropic)",
            type="remote",
            provider="anthropic",
            api_url="https://api.anthropic.com/v1",
            api_key_env="ANTHROPIC_API_KEY",
            rate_limit_per_minute=5,
            loaded=True,
            metadata={
                "context_length": 200000,
                "cost_per_1k_tokens": 0.003,
            },
        )
        
        logger.info(f"{len(self._local_models)} lokale, {len(self._remote_models)} Remote-Modelle initialisiert")
    
    def get_all_models(self) -> List[ModelInfo]:
        """
        Returns alle Modelle.
        
        Returns:
            Liste von ModelInfo
        """
        all_models = list(self._local_models.values()) + list(self._remote_models.values())
        return all_models
    
    def get_local_models(self) -> List[ModelInfo]:
        """
        Returns lokale Modelle.
        
        Returns:
            Liste von ModelInfo
        """
        return list(self._local_models.values())
    
    def get_remote_models(self) -> List[RemoteModelInfo]:
        """
        Returns Remote-Modelle.
        
        Returns:
            Liste von RemoteModelInfo
        """
        return list(self._remote_models.values())
    
    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """
        Returns Modell nach ID.
        
        Args:
            model_id: Modell-ID
            
        Returns:
            ModelInfo oder None
        """
        return self._local_models.get(model_id) or self._remote_models.get(model_id)
    
    async def load_model(self, model_id: str) -> bool:
        """
        Lädt ein Modell.
        
        Args:
            model_id: Modell-ID
            
        Returns:
            True wenn erfolgreich
        """
        model = self._local_models.get(model_id)
        if not model:
            logger.warning(f"Modell {model_id} nicht gefunden")
            return False
        
        if model.loaded:
            logger.info(f"Modell {model_id} ist bereits geladen")
            return True
        
        try:
            # Prüfen ob Modell-Datei existiert
            if model.path and not Path(model.path).exists():
                logger.error(f"Modell-Datei nicht gefunden: {model.path}")
                return False
            
            # Modell laden (simuliert - hier würde echtes Loading passieren)
            logger.info(f"Lade Modell {model_id}...")
            await asyncio.sleep(2)  # Simuliertes Laden
            
            model.loaded = True
            model.load_count += 1
            model.last_used = datetime.now()
            
            # VRAM-Verbrauch schätzen
            model.vram_usage_mb = model.size_mb * 1.2  # 20% Overhead
            
            logger.info(f"Modell {model_id} erfolgreich geladen")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Laden von {model_id}: {e}")
            return False
    
    async def unload_model(self, model_id: str) -> bool:
        """
        Entlädt ein Modell.
        
        Args:
            model_id: Modell-ID
            
        Returns:
            True wenn erfolgreich
        """
        model = self._local_models.get(model_id)
        if not model:
            return False
        
        if not model.loaded:
            return True
        
        try:
            logger.info(f"Entlade Modell {model_id}...")
            
            # Modell entladen (simuliert)
            await asyncio.sleep(1)
            
            model.loaded = False
            model.vram_usage_mb = 0.0
            
            logger.info(f"Modell {model_id} erfolgreich entladen")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Entladen von {model_id}: {e}")
            return False
    
    async def check_model_health(self, model_id: str) -> Dict[str, Any]:
        """
        Prüft Modell-Gesundheit.
        
        Args:
            model_id: Modell-ID
            
        Returns:
            Health-Check-Ergebnis
        """
        model = self.get_model(model_id)
        if not model:
            return {"status": "error", "message": "Modell nicht gefunden"}
        
        try:
            if model.type == "local":
                # Lokales Modell prüfen
                if model.path and not Path(model.path).exists():
                    return {
                        "status": "error",
                        "message": "Modell-Datei nicht gefunden",
                        "path": model.path,
                    }
                
                return {
                    "status": "ok" if model.loaded else "unloaded",
                    "loaded": model.loaded,
                    "vram_usage_mb": model.vram_usage_mb,
                    "path": model.path,
                }
                
            else:
                # Remote-Modell prüfen
                remote = model if isinstance(model, RemoteModelInfo) else None
                if not remote:
                    return {"status": "error", "message": "Kein Remote-Modell"}
                
                # API-Verfügbarkeit prüfen
                start_time = time.time()
                available = await self._check_remote_availability(remote)
                latency = (time.time() - start_time) * 1000
                
                remote.avg_latency_ms = latency
                remote.availability = 100.0 if available else 0.0
                
                return {
                    "status": "ok" if available else "error",
                    "available": available,
                    "latency_ms": latency,
                    "rate_limit": remote.rate_limit_per_minute,
                    "requests_today": remote.requests_today,
                }
                
        except Exception as e:
            logger.error(f"Health-Check für {model_id} fehlgeschlagen: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _check_remote_availability(self, model: RemoteModelInfo) -> bool:
        """
        Prüft Verfügbarkeit eines Remote-Modells.
        
        Args:
            model: Remote-Modell
            
        Returns:
            True wenn verfügbar
        """
        try:
            import httpx
            
            api_key = None
            if model.api_key_env:
                api_key = os.getenv(model.api_key_env)
            
            headers = {}
            if model.provider == "openai":
                headers["Authorization"] = f"Bearer {api_key}"
            elif model.provider == "anthropic":
                headers["x-api-key"] = api_key
                headers["anthropic-version"] = "2023-06-01"
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{model.api_url}/models",
                    headers=headers,
                )
                return response.status_code == 200
                
        except Exception as e:
            logger.debug(f"Remote-Verfügbarkeit fehlgeschlagen: {e}")
            return False
    
    def get_model_statistics(self) -> Dict[str, Any]:
        """
        Returns Modell-Statistiken.
        
        Returns:
            Statistik-Dict
        """
        local_loaded = [m for m in self._local_models.values() if m.loaded]
        remote_available = [m for m in self._remote_models.values() if m.loaded]
        
        return {
            "total_local": len(self._local_models),
            "total_remote": len(self._remote_models),
            "local_loaded": len(local_loaded),
            "remote_available": len(remote_available),
            "total_vram_usage_mb": sum(m.vram_usage_mb for m in local_loaded),
            "total_load_count": sum(m.load_count for m in self._local_models.values()),
        }
    
    async def update_model_usage(self, model_id: str, inference_time_ms: float):
        """
        Aktualisiert Modell-Nutzung.
        
        Args:
            model_id: Modell-ID
            inference_time_ms: Inferenz-Zeit in ms
        """
        model = self.get_model(model_id)
        if not model:
            return
        
        model.last_used = datetime.now()
        
        # Durchschnittliche Inferenz-Zeit aktualisieren (exponential moving average)
        alpha = 0.1
        model.avg_inference_time_ms = (
            alpha * inference_time_ms +
            (1 - alpha) * model.avg_inference_time_ms
        )
        
        # Remote-Modell Requests zählen
        if isinstance(model, RemoteModelInfo):
            model.requests_today += 1
            model.last_request = datetime.now()


# ============== Globale Instanz ==============

_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """
    Returns globale ModelManager-Instanz.
    
    Returns:
        ModelManager
    """
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
        _model_manager.initialize()
    return _model_manager
