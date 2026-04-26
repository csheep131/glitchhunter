"""
Model-Monitoring Manager für GlitchHunter Web-UI.

Überwacht lokale und Remote-Modelle mit:
- Modell-Status (geladen, entladen, verfügbar)
- VRAM-Verbrauch
- Response-Zeiten
- Verfügbarkeit
- Dynamische Modell-Liste aus config.yaml

Features:
- Lokale Modelle (Pfad, Größe, VRAM)
- Remote Modelle (API, Latenz, Rate-Limit)
- Auto-Loading bei Bedarf
- Health-Checks
- Konfiguration aus config.yaml
"""

import asyncio
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Projekt-Root Verzeichnis (2 Ebenen hoch von ui/web/backend/)
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


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
    
    def initialize(self, config=None):
        """Initialisiert alle Modelle.
        
        Args:
            config: Optional Config-Objekt aus config.yaml.
                    Wenn None, wird config.yaml automatisch geladen.
        """
        logger.info("Initialisiere Modelle...")

        # Config laden wenn nicht übergeben
        if config is None:
            try:
                import sys
                sys.path.insert(0, str(_PROJECT_ROOT / "src"))
                from core.config import Config
                config = Config.load(_PROJECT_ROOT / "config.yaml")
                logger.info(f"Config aus {_PROJECT_ROOT / 'config.yaml'} geladen")
            except Exception as e:
                logger.warning(f"Konnte config.yaml nicht laden ({e}), verwende Fallback-Modelle")
                config = None

        # Lokale Modelle aus config.yaml laden
        if config:
            self._load_models_from_config(config)
        else:
            # Fallback: Hardcoded Modelle
            self._load_fallback_models()

        # GGUF-Dateien scannen als Ergänzung (findet auch nicht-in-config-Modelle)
        self._scan_gguf_files()
        
        # Remote-Modelle (immer hinzufügen)
        self._load_remote_models()

        logger.info(f"{len(self._local_models)} lokale, {len(self._remote_models)} Remote-Modelle initialisiert")

    def _load_models_from_config(self, config):
        """Lädt Modelle aus config.yaml.
        
        Args:
            config: Config-Objekt
        """
        # Modelle aus hardware.{stack}.models extrahieren
        for stack_name, hw in config.hardware.items():
            if stack_name == "stack_c":
                continue  # Stack C ist Remote, wird separat behandelt

            models = hw.models if hasattr(hw, 'models') else {}
            for role, model_data in models.items():
                if not isinstance(model_data, dict):
                    continue

                model_name = model_data.get("name", role)
                model_path = model_data.get("path", "")
                context_length = model_data.get("context_length", 4096)
                n_gpu_layers = model_data.get("n_gpu_layers", 0)
                n_threads = model_data.get("n_threads", 8)

                # Pfad relativ zu Projekt-Root auflösen
                if model_path and not Path(model_path).is_absolute():
                    full_path = str(_PROJECT_ROOT / model_path)
                else:
                    full_path = model_path

                # Modell-ID generieren
                model_id = f"{model_name}-{stack_name}"

                # Dateigröße schätzen (falls Datei existiert)
                size_mb = 0.0
                if full_path and Path(full_path).exists():
                    size_mb = Path(full_path).stat().st_size / (1024 * 1024)

                # Quantisierung aus Dateiname erraten
                quant = "unknown"
                if full_path:
                    fname = Path(full_path).name.lower()
                    if "q4_k_m" in fname:
                        quant = "q4_k_m"
                    elif "q8" in fname:
                        quant = "q8"
                    elif "q5" in fname:
                        quant = "q5"
                    elif "f16" in fname:
                        quant = "f16"
                    elif "f32" in fname:
                        quant = "f32"

                self._local_models[model_id] = ModelInfo(
                    id=model_id,
                    name=f"{model_name} ({stack_name.upper()})",
                    type="local",
                    path=full_path,
                    size_mb=size_mb,
                    quantization=quant,
                    loaded=False,
                    metadata={
                        "context_length": context_length,
                        "n_gpu_layers": n_gpu_layers,
                        "n_threads": n_threads,
                        "role": role,
                        "stack": stack_name,
                    },
                )

        # Auch model_downloads aus config.yaml verwenden für verfügbare Modelle
        if hasattr(config, 'model_downloads') and config.model_downloads.models:
            for model_key, dl_config in config.model_downloads.models.items():
                model_id = f"{dl_config.name if hasattr(dl_config, 'name') else model_key}"
                # Nur hinzufügen wenn nicht bereits vorhanden
                if model_id not in self._local_models:
                    self._local_models[model_id] = ModelInfo(
                        id=model_id,
                        name=dl_config.description if hasattr(dl_config, 'description') else model_key,
                        type="local",
                        path="",  # Pfad unbekannt - muss heruntergeladen werden
                        size_mb=dl_config.size_gb * 1024 if hasattr(dl_config, 'size_gb') else 0,
                        quantization="q4_k_m",  # Default
                        loaded=False,
                        metadata={
                            "stack": dl_config.stack if hasattr(dl_config, 'stack') else "unknown",
                            "repo_id": dl_config.repo_id if hasattr(dl_config, 'repo_id') else "",
                            "filename": dl_config.filename if hasattr(dl_config, 'filename') else "",
                            "downloadable": True,
                        },
                    )

    def _load_fallback_models(self):
        """Lädt Fallback-Modelle: Scannt GGUF-Dateien aus Modell-Verzeichnissen."""
        # Mögliche Modell-Verzeichnisse (Docker-Container + lokal)
        model_dirs = [
            Path("/home/schaf/modelle"),       # asgard: Haupt-Modellverzeichnis
            Path("/home/schaf/models"),         # Alternativer Pfad
            Path("/app/models"),                # Docker-Container
            _PROJECT_ROOT / "models",           # Projekt-Root/models
        ]
        
        gguf_files = []
        for model_dir in model_dirs:
            if model_dir.exists():
                logger.info(f"Scanne Modell-Verzeichnis: {model_dir}")
                for gguf in sorted(model_dir.rglob("*.gguf")):
                    size_mb = gguf.stat().st_size / (1024 * 1024)
                    gguf_files.append((gguf, size_mb))
                    logger.debug(f"  Gefunden: {gguf.name} ({size_mb:.0f} MB)")
        
        if not gguf_files:
            logger.warning("Keine GGUF-Modelle gefunden!")
            return
        
        # GGUFs nach Stack zuordnen basierend auf Größe und Name
        for gguf_path, size_mb in gguf_files:
            name = gguf_path.stem
            fname = gguf_path.name.lower()
            
            # Quantisierung erkennen
            quant = "unknown"
            for q in ["q4_k_m", "q8_0", "q5_k_m", "q6_k", "q4_0", "q5_0", "f16", "f32", "bf16"]:
                if q in fname:
                    quant = q
                    break
            
            # Stack basierend auf Größe zuordnen
            if size_mb > 12000:  # >12GB → Stack B (RTX 3090, 24GB)
                stack = "stack_b"
            elif size_mb > 6000:  # 6-12GB → Stack B secondary oder Stack A
                stack = "stack_b"
            else:  # <6GB → Stack A (GTX 3060, 12GB)
                stack = "stack_a"
            
            model_id = f"{name}-{stack}"
            
            self._local_models[model_id] = ModelInfo(
                id=model_id,
                name=f"{name} ({stack.upper()})",
                type="local",
                path=str(gguf_path),
                size_mb=size_mb,
                quantization=quant,
                loaded=False,
                metadata={
                    "role": "primary",
                    "stack": stack,
                    "filename": gguf_path.name,
                },
            )
        
        logger.info(f"{len(self._local_models)} GGUF-Modelle aus Verzeichnissen geladen")

    def _is_multi_part(self, filename: str) -> bool:
        """Prüft ob eine GGUF-Datei Teil eines Multi-Part-Splits ist.
        
        Erkennt Muster wie: model-00001-of-00004.gguf, model.gguf.split.001, etc.
        """
        fname = filename.lower()
        # Muster: "00001-of-00004" oder ".split." oder ".part1."
        if re.search(r'\d{5}-of-\d{5}', fname):
            return True
        if '.split.' in fname or '.part' in fname:
            return True
        return False

    def _scan_gguf_files(self):
        """Scannt GGUF-Dateien als Ergänzung zu config.yaml-Modellen."""
        model_dirs = [
            Path("/home/schaf/modelle"),       # asgard: Haupt-Modellverzeichnis
            Path("/home/schaf/models"),         # Alternativer Pfad
            Path("/app/models"),                # Docker-Container
            _PROJECT_ROOT / "models",           # Projekt-Root/models
        ]
        
        for model_dir in model_dirs:
            if not model_dir.exists():
                continue
            logger.info(f"Scanne Modell-Verzeichnis: {model_dir}")
            for gguf in sorted(model_dir.rglob("*.gguf")):
                # Skip mmproj (vision encoder)
                if "mmproj" in gguf.name.lower():
                    continue
                # Skip multi-part files (00001-of-00004 etc.)
                if self._is_multi_part(gguf.name):
                    logger.debug(f"  Überspringe Multi-Part: {gguf.name}")
                    continue
                    
                size_mb = gguf.stat().st_size / (1024 * 1024)
                name = gguf.stem
                fname = gguf.name.lower()
                
                # Quantisierung erkennen
                quant = "unknown"
                for q in ["q4_k_m", "q8_0", "q5_k_m", "q6_k", "q4_0", "q5_0", "iq3_xxs", "f16", "f32", "bf16", "q4_k_s"]:
                    if q in fname:
                        quant = q
                        break
                
                # Stack basierend auf Größe
                if size_mb > 12000:
                    stack = "stack_b"
                elif size_mb > 6000:
                    stack = "stack_b"
                else:
                    stack = "stack_a"
                
                model_id = f"{name}-{stack}"
                
                # Nur hinzufügen wenn nicht bereits via config geladen
                if model_id not in self._local_models:
                    self._local_models[model_id] = ModelInfo(
                        id=model_id,
                        name=f"{name} ({stack.upper()})",
                        type="local",
                        path=str(gguf),
                        size_mb=size_mb,
                        quantization=quant,
                        loaded=False,
                        metadata={
                            "role": "discovered",
                            "stack": stack,
                            "filename": gguf.name,
                        },
                    )
                    logger.debug(f"  GGUF entdeckt: {gguf.name} ({size_mb:.0f} MB) → {stack}")
        
        logger.info(f"Nach GGUF-Scan: {len(self._local_models)} lokale Modelle")

    def _load_remote_models(self):
        """Lädt Remote-Modelle."""
        
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

    def update_model_path(self, model_id: str, new_path: str) -> bool:
        """
        Aktualisiert den Pfad eines lokalen Modells.
        
        Args:
            model_id: Modell-ID
            new_path: Neuer Pfad
            
        Returns:
            True wenn erfolgreich
        """
        model = self._local_models.get(model_id)
        if not model:
            logger.warning(f"Modell {model_id} nicht gefunden")
            return False

        model.path = new_path
        
        # Dateigröße aktualisieren falls Datei existiert
        if Path(new_path).exists():
            model.size_mb = Path(new_path).stat().st_size / (1024 * 1024)
        
        logger.info(f"Modell-Pfad für {model_id} aktualisiert: {new_path}")
        return True

    def get_available_models_by_stack(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Returns alle lokalen Modelle gruppiert nach Stack.
        
        Returns:
            Dict: {stack_id: [{id, name, path, size_mb, ...}, ...], ...}
        """
        result = {}
        for model in self._local_models.values():
            stack = model.metadata.get("stack", "unknown")
            if stack not in result:
                result[stack] = []
            
            result[stack].append({
                "id": model.id,
                "name": model.name,
                "path": model.path,
                "size_mb": model.size_mb,
                "quantization": model.quantization,
                "role": model.metadata.get("role", "unknown"),
                "context_length": model.metadata.get("context_length", 0),
                "exists": Path(model.path).exists() if model.path else False,
            })
        
        return result
    
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
