"""
Model Router für GlitchHunter v2.0

Routet Anfragen an verschiedene Modelle (API, lokal, CPU-fallback).
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union
from datetime import datetime
import time

from ..hardware.auto_detect import AutoDetector, BackendType, BackendRecommendation
from ..inference.llama_cpp_backend import LlamaCppBackend, LlamaConfig
from ..inference.engine import InferenceEngine
from .voting_engine import ModelVote

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Konfiguration für ein Modell im Ensemble."""
    model_id: str
    model_name: str
    backend_type: BackendType
    weight: float = 1.0
    timeout_seconds: float = 60.0
    priority: int = 0  # Höher = wichtiger
    config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}


class ModelRouter:
    """
    Routet Inferenz-Anfragen an verschiedene Modelle.
    
    Features:
    - Automatische Backend-Auswahl
    - Parallele Anfragen an mehrere Modelle
    - Fallback bei Fehlern
    - Load-Balancing
    """
    
    # Default Ensemble-Konfiguration
    DEFAULT_ENSEMBLE = [
        ModelConfig(
            model_id="primary",
            model_name="Qwen2.5-Coder-32B",
            backend_type=BackendType.OPENAI_API,
            weight=1.2,
            priority=10,
        ),
        ModelConfig(
            model_id="secondary",
            model_name="DeepSeek-Coder-V2",
            backend_type=BackendType.OPENAI_API,
            weight=1.0,
            priority=9,
        ),
        ModelConfig(
            model_id="local",
            model_name="Qwen2.5-Coder-7B-GGUF",
            backend_type=BackendType.CPU_LLAMA_CPP,
            weight=0.8,
            priority=5,
        ),
    ]
    
    def __init__(
        self,
        models: Optional[List[ModelConfig]] = None,
        auto_detect: bool = True,
    ):
        self.models = models or self.DEFAULT_ENSEMBLE
        self.auto_detect = auto_detect
        self._backends: Dict[BackendType, Any] = {}
        self._initialized = False
        self._detector: Optional[AutoDetector] = None
        
    async def initialize(self) -> bool:
        """Initialisiert alle konfigurierten Backends."""
        if self._initialized:
            return True
        
        logger.info("Initialisiere ModelRouter...")
        
        if self.auto_detect:
            self._detector = AutoDetector()
            recommendation = self._detector.detect()
            logger.info(f"Hardware-Detection: {recommendation.backend_name}")
        
        # Initialisiere jedes Modell
        initialized_models = []
        for model in self.models:
            if await self._init_model(model):
                initialized_models.append(model)
        
        self.models = initialized_models
        self._initialized = len(self.models) > 0
        
        if self._initialized:
            logger.info(f"ModelRouter bereit mit {len(self.models)} Modellen")
        else:
            logger.error("Keine Modelle konnten initialisiert werden!")
        
        return self._initialized
    
    async def _init_model(self, model: ModelConfig) -> bool:
        """Initialisiert ein einzelnes Modell."""
        try:
            if model.backend_type == BackendType.CPU_LLAMA_CPP:
                backend = LlamaCppBackend()
                if not backend.setup():
                    logger.warning(f"Konnte llama.cpp nicht initialisieren für {model.model_id}")
                    return False
                self._backends[model.model_id] = backend
                logger.info(f"Modell initialisiert: {model.model_id}")
                return True
            
            elif model.backend_type == BackendType.OPENAI_API:
                # Prüfe API-Key
                import os
                if not (os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")):
                    logger.warning(f"Kein API-Key für {model.model_id}")
                    return False
                self._backends[model.model_id] = InferenceEngine()
                logger.info(f"API-Modell initialisiert: {model.model_id}")
                return True
            
            else:
                logger.warning(f"Nicht unterstütztes Backend: {model.backend_type}")
                return False
                
        except Exception as e:
            logger.error(f"Fehler bei Initialisierung von {model.model_id}: {e}")
            return False
    
    async def generate_single(
        self,
        model_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> ModelVote:
        """
        Generiert mit einem einzelnen Modell.
        
        Args:
            model_id: ID des Modells
            prompt: User-Prompt
            system_prompt: Optionaler System-Prompt
            
        Returns:
            ModelVote mit Ergebnis
        """
        model = next((m for m in self.models if m.model_id == model_id), None)
        if not model:
            raise ValueError(f"Unbekanntes Modell: {model_id}")
        
        backend = self._backends.get(model_id)
        if not backend:
            raise RuntimeError(f"Modell {model_id} nicht initialisiert")
        
        start_time = time.time()
        
        try:
            if model.backend_type == BackendType.CPU_LLAMA_CPP:
                # llama.cpp Backend
                full_prompt = self._build_llama_prompt(prompt, system_prompt)
                response = await asyncio.to_thread(
                    backend.generate,
                    full_prompt,
                    max_tokens=2048,
                )
            
            elif model.backend_type == BackendType.OPENAI_API:
                # API Backend
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                response = await backend.generate_async(messages)
            
            else:
                response = ""
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Extrahiere Fix und Confidence aus Response
            fix, confidence, reasoning = self._parse_response(response)
            
            return ModelVote(
                model_id=model_id,
                model_name=model.model_name,
                fix_proposal=fix,
                confidence=confidence,
                reasoning=reasoning,
                response_time_ms=duration_ms,
                metadata={"raw_response": response[:500]},
            )
            
        except Exception as e:
            logger.error(f"Fehler bei {model_id}: {e}")
            return ModelVote(
                model_id=model_id,
                model_name=model.model_name,
                fix_proposal="",
                confidence=0.0,
                reasoning=f"Fehler: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
                metadata={"error": str(e)},
            )
    
    async def generate_ensemble(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_ids: Optional[List[str]] = None,
    ) -> List[ModelVote]:
        """
        Generiert mit mehreren Modellen parallel.
        
        Args:
            prompt: User-Prompt
            system_prompt: Optionaler System-Prompt
            model_ids: Optional Liste von Modell-IDs (default: alle)
            
        Returns:
            Liste von ModelVotes
        """
        if not self._initialized:
            await self.initialize()
        
        models_to_use = self.models
        if model_ids:
            models_to_use = [m for m in self.models if m.model_id in model_ids]
        
        if not models_to_use:
            logger.error("Keine Modelle für Ensemble verfügbar")
            return []
        
        logger.info(f"Ensemble-Generierung mit {len(models_to_use)} Modellen...")
        
        # Parallele Generierung
        tasks = [
            self.generate_single(m.model_id, prompt, system_prompt)
            for m in models_to_use
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        votes = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Modell-Fehler: {result}")
            elif isinstance(result, ModelVote):
                votes.append(result)
        
        logger.info(f"Ensemble abgeschlossen: {len(votes)}/{len(models_to_use)} erfolgreich")
        return votes
    
    def _build_llama_prompt(self, prompt: str, system_prompt: Optional[str]) -> str:
        """Baut Prompt für llama.cpp."""
        if system_prompt:
            return f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
        else:
            return f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
    
    def _parse_response(self, response: str) -> tuple:
        """Parst Fix, Confidence und Reasoning aus Response."""
        # Default-Werte
        fix = response.strip()
        confidence = 0.7  # Default
        reasoning = ""
        
        # Versuche Confidence zu extrahieren
        import re
        confidence_match = re.search(r'Confidence:\s*(\d+(?:\.\d+)?)%?', response, re.IGNORECASE)
        if confidence_match:
            try:
                confidence = float(confidence_match.group(1)) / 100
            except:
                pass
        
        # Extrahiere Reasoning falls vorhanden
        reasoning_match = re.search(r'Reasoning:\s*(.+?)(?=\n\n|\Z)', response, re.IGNORECASE | re.DOTALL)
        if reasoning_match:
            reasoning = reasoning_match.group(1).strip()
        
        return fix, min(confidence, 1.0), reasoning
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Gibt Liste der verfügbaren Modelle zurück."""
        return [
            {
                "id": m.model_id,
                "name": m.model_name,
                "backend": m.backend_type.name,
                "weight": m.weight,
                "priority": m.priority,
                "initialized": m.model_id in self._backends,
            }
            for m in self.models
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Gibt Router-Statistiken zurück."""
        return {
            "initialized": self._initialized,
            "models_configured": len(self.models),
            "models_initialized": len(self._backends),
            "hardware": self._detector.get_system_report() if self._detector else None,
        }