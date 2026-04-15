"""
Ensemble Coordinator für GlitchHunter Escalation Level 3.

Koordiniert parallele Analysen mit mehreren Modellen und Ensemble-Voting.
Echte llama-cpp Integration mit Singleton ModelLoader.
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from llama_cpp import Llama

logger = logging.getLogger(__name__)


# Timeout für Modell-Analysen (60 Sekunden)
MODEL_ANALYSIS_TIMEOUT = 60.0


@dataclass
class ModelConfig:
    """Konfiguration für ein einzelnes Modell."""

    name: str
    path: str
    context_length: int
    n_gpu_layers: int
    n_threads: int
    n_batch: int = 512

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelConfig":
        """Erstellt ModelConfig aus Dictionary."""
        return cls(
            name=data.get("name", "unknown"),
            path=data.get("path", ""),
            context_length=data.get("context_length", 4096),
            n_gpu_layers=data.get("n_gpu_layers", 0),
            n_threads=data.get("n_threads", 4),
            n_batch=data.get("n_batch", 512),
        )


@dataclass
class ModelResponse:
    """
    Antwort eines Modells.

    Attributes:
        model_id: Modell-ID
        hypothesis: Hypothese
        confidence: Konfidenz
        reasoning: Begründung
        patch_suggestion: Patch-Vorschlag
        response_time_ms: Antwortzeit
    """

    model_id: str
    hypothesis: str
    confidence: float
    reasoning: str = ""
    patch_suggestion: str = ""
    response_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "model_id": self.model_id,
            "hypothesis": self.hypothesis,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "patch_suggestion": self.patch_suggestion,
            "response_time_ms": self.response_time_ms,
            "metadata": self.metadata,
        }


@dataclass
class EnsembleResult:
    """
    Ergebnis des Ensemble-Votings.

    Attributes:
        winning_hypothesis: Gewinnende Hypothese
        votes: Stimmen
        agreement_level: Übereinstimmungs-Level
        models_used: Verwendete Modelle
        total_models: Anzahl Modelle
    """

    winning_hypothesis: str = ""
    votes: Dict[str, int] = field(default_factory=dict)
    agreement_level: str = "none"
    models_used: List[str] = field(default_factory=list)
    total_models: int = 0
    all_responses: List[ModelResponse] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "winning_hypothesis": self.winning_hypothesis,
            "votes": self.votes,
            "agreement_level": self.agreement_level,
            "models_used": self.models_used,
            "total_models": self.total_models,
            "all_responses": [r.to_dict() for r in self.all_responses],
            "metadata": self.metadata,
        }


class ModelLoader:
    """
    Singleton für llama-cpp Modell-Instanzen.

    Verwaltet das Lazy Loading und Caching von Modell-Instanzen.
    Thread-safe durch Lock-Mechanismus.

    Features:
    - Singleton Pattern für globale Instanz
    - Lazy Loading (Modelle nur bei Bedarf)
    - Thread-safe Zugriff
    - Memory Management (VRAM-Überwachung)
    """

    _instance: Optional["ModelLoader"] = None
    _lock = threading.Lock()
    _models: Dict[str, Llama] = {}
    _model_metadata: Dict[str, Dict[str, Any]] = {}

    def __new__(cls) -> "ModelLoader":
        """Singleton-Instanz erstellen."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_model(
        cls,
        model_path: str,
        n_gpu_layers: int = 0,
        n_threads: int = 4,
        n_batch: int = 512,
        n_ctx: int = 4096,
        verbose: bool = False,
    ) -> Llama:
        """
        Lädt oder cached ein Modell.

        Args:
            model_path: Pfad zur GGUF-Datei
            n_gpu_layers: Anzahl der GPU-Layers (0 für CPU-only)
            n_threads: Anzahl CPU-Threads
            n_batch: Batch-Größe für Inferenz
            n_ctx: Context-Fenster-Größe
            verbose: Ausführliches Logging

        Returns:
            Geladene Llama-Instanz

        Raises:
            FileNotFoundError: Wenn Modell-Datei nicht existiert
            RuntimeError: Wenn Modell nicht geladen werden kann
        """
        with cls._lock:
            if model_path not in cls._models:
                logger.info(f"Loading model: {model_path}")

                # Validiere Pfad
                model_file = Path(model_path)
                if not model_file.exists():
                    raise FileNotFoundError(f"Model file not found: {model_path}")

                try:
                    # Lade Modell mit llama-cpp
                    model = Llama(
                        model_path=str(model_file),
                        n_gpu_layers=n_gpu_layers,
                        n_threads=n_threads,
                        n_batch=n_batch,
                        n_ctx=n_ctx,
                        verbose=verbose,
                    )

                    cls._models[model_path] = model
                    cls._model_metadata[model_path] = {
                        "n_gpu_layers": n_gpu_layers,
                        "n_threads": n_threads,
                        "n_batch": n_batch,
                        "n_ctx": n_ctx,
                        "loaded_at": time.time(),
                    }

                    logger.info(
                        f"Model loaded successfully: {model_path} "
                        f"(GPU layers: {n_gpu_layers}, Threads: {n_threads})"
                    )

                except Exception as e:
                    logger.error(f"Failed to load model {model_path}: {e}")
                    raise RuntimeError(f"Failed to load model: {e}") from e

            return cls._models[model_path]

    @classmethod
    def unload_model(cls, model_path: str) -> bool:
        """
        Entfernt ein Modell aus dem Cache.

        Args:
            model_path: Pfad zum Modell

        Returns:
            True wenn erfolgreich entfernt, False wenn nicht vorhanden
        """
        with cls._lock:
            if model_path in cls._models:
                del cls._models[model_path]
                if model_path in cls._model_metadata:
                    del cls._model_metadata[model_path]
                logger.info(f"Unloaded model: {model_path}")
                return True
            return False

    @classmethod
    def unload_all(cls) -> None:
        """Entfernt alle Modelle aus dem Cache."""
        with cls._lock:
            cls._models.clear()
            cls._model_metadata.clear()
            logger.info("All models unloaded")

    @classmethod
    def get_loaded_models(cls) -> List[str]:
        """
        Gibt Liste der geladenen Modelle zurück.

        Returns:
            Liste der Modell-Pfade
        """
        with cls._lock:
            return list(cls._models.keys())

    @classmethod
    def is_model_loaded(cls, model_path: str) -> bool:
        """
        Prüft ob ein Modell bereits geladen ist.

        Args:
            model_path: Pfad zum Modell

        Returns:
            True wenn geladen, False sonst
        """
        with cls._lock:
            return model_path in cls._models


class EnsembleCoordinator:
    """
    Koordiniert Multi-Model Ensemble.

    Features:
    - Parallele Analysen mit mehreren Modellen
    - Echte llama-cpp Integration
    - Ensemble-Voting
    - Confidence-Weighted Voting
    - Timeout- und Error-Handling

    Usage:
        coordinator = EnsembleCoordinator(config)
        result = coordinator.run_ensemble(bug, models)
    """

    # Agreement-Levels
    AGREEMENT_UNANIMOUS = "unanimous"
    AGREEMENT_MAJORITY = "majority"
    AGREEMENT_PLURALITY = "plurality"
    AGREEMENT_NONE = "none"

    def __init__(
        self,
        config: Optional[Any] = None,
        models: Optional[List[str]] = None,
        stack_name: str = "stack_a",
    ) -> None:
        """
        Initialisiert Ensemble Coordinator.

        Args:
            config: Config-Instanz für Modell-Pfade
            models: Liste von Modell-IDs
            stack_name: Name des Hardware-Stacks (stack_a oder stack_b)
        """
        self.config = config
        self.stack_name = stack_name
        self.models = models or [
            "primary",
            "secondary",
        ]

        self._model_loader = ModelLoader()

        logger.debug(
            f"EnsembleCoordinator initialisiert: {len(self.models)} Modelle, "
            f"Stack: {stack_name}"
        )

    def _get_model_config(self, model_id: str) -> ModelConfig:
        """
        Lädt Modell-Konfiguration aus Config.

        Args:
            model_id: Modell-ID (z.B. "primary", "secondary")

        Returns:
            ModelConfig mit Pfad und Parametern

        Raises:
            ValueError: Wenn Modell-Konfiguration nicht gefunden wird
        """
        if self.config is None:
            raise ValueError(
                f"Config not set, cannot load model config for: {model_id}"
            )

        try:
            hardware_config = self.config.get_hardware_profile(self.stack_name)
            model_data = hardware_config.models.get(model_id, {})

            if not model_data:
                raise ValueError(
                    f"Model '{model_id}' not found in stack '{self.stack_name}'"
                )

            return ModelConfig.from_dict(model_data)

        except Exception as e:
            logger.error(f"Failed to get model config for {model_id}: {e}")
            raise ValueError(f"Cannot load model config: {e}") from e

    def _create_analysis_prompt(self, bug: Dict[str, Any]) -> str:
        """
        Erstellt Prompt für Bug-Analyse.

        Args:
            bug: Bug-Information

        Returns:
            Formatierter Prompt
        """
        bug_id = bug.get("bug_id", "unknown")
        bug_type = bug.get("bug_type", "unknown")
        file_path = bug.get("file_path", "")
        line_number = bug.get("line_number", 0)
        description = bug.get("description", "")
        code_snippet = bug.get("code_snippet", "")

        prompt = f"""<|system|>
Du bist ein erfahrener Software-Entwickler und Debugging-Experte.
Analysiere den folgenden Bug und erstelle eine präzise Hypothese.

<|user|>
Bug-ID: {bug_id}
Typ: {bug_type}
Datei: {file_path}
Zeile: {line_number}

Beschreibung:
{description}

Code-Snippet:
```
{code_snippet}
```

Aufgabe:
1. Identifiziere die Root-Cause des Bugs
2. Erkläre warum der Bug auftritt
3. Beschreibe die betroffenen Komponenten
4. Schlage eine Lösung vor

Formatiere die Antwort als:
HYPOTHESE: <kurze Zusammenfassung>
URSACHE: <detaillierte Erklärung>
BETROFFEN: <betroffene Komponenten>
LÖSUNG: <Lösungsvorschlag>
<|assistant|>
"""

        return prompt

    def _run_parallel_analyses(
        self,
        bug: Dict[str, Any],
        model_ids: List[str],
    ) -> List[ModelResponse]:
        """
        Führt Analysen mit mehreren Modellen parallel aus.

        Verwendet echte llama-cpp Modelle mit ThreadPoolExecutor.

        Args:
            bug: Bug-Information
            model_ids: Liste der Modell-IDs

        Returns:
            Liste von ModelResponse Objekten
        """
        results: Dict[str, ModelResponse] = {}
        start_time = time.time()

        def analyze_with_model(model_id: str) -> Tuple[str, Optional[ModelResponse]]:
            """
            Analysiert Bug mit einem Modell.

            Args:
                model_id: Modell-ID

            Returns:
                Tuple aus (model_id, ModelResponse oder None bei Fehler)
            """
            model_start = time.time()

            try:
                # Lade Modell-Konfiguration
                model_config = self._get_model_config(model_id)

                # Lade oder cache Modell
                model = ModelLoader.get_model(
                    model_path=model_config.path,
                    n_gpu_layers=model_config.n_gpu_layers,
                    n_threads=model_config.n_threads,
                    n_batch=model_config.n_batch,
                    n_ctx=model_config.context_length,
                    verbose=False,
                )

                # Erstelle Prompt
                prompt = self._create_analysis_prompt(bug)

                # Führe Inferenz mit Timeout durch
                response = model(
                    prompt,
                    max_tokens=512,
                    temperature=0.1,
                    stop=["</s>", "\n\n", "<|user|>"],
                    echo=False,
                )

                # Extrahiere Antwort
                hypothesis = response["choices"][0]["text"].strip()

                # Parse Antwort für strukturierte Extraktion
                parsed = self._parse_model_response(hypothesis, bug)

                response_time = (time.time() - model_start) * 1000

                logger.info(
                    f"Model {model_id} completed analysis in {response_time:.0f}ms"
                )

                return model_id, ModelResponse(
                    model_id=model_id,
                    hypothesis=parsed["hypothesis"],
                    confidence=parsed["confidence"],
                    reasoning=parsed["reasoning"],
                    patch_suggestion=parsed["patch_suggestion"],
                    response_time_ms=response_time,
                    metadata={
                        "model_path": model_config.path,
                        "n_gpu_layers": model_config.n_gpu_layers,
                        "success": True,
                    },
                )

            except FileNotFoundError as e:
                logger.error(f"Model {model_id} file not found: {e}")
                return model_id, ModelResponse(
                    model_id=model_id,
                    hypothesis="",
                    confidence=0.0,
                    reasoning=f"Model file not found: {e}",
                    response_time_ms=(time.time() - model_start) * 1000,
                    metadata={"error": "file_not_found", "success": False},
                )

            except RuntimeError as e:
                logger.error(f"Model {model_id} runtime error: {e}")
                return model_id, ModelResponse(
                    model_id=model_id,
                    hypothesis="",
                    confidence=0.0,
                    reasoning=f"Model loading failed: {e}",
                    response_time_ms=(time.time() - model_start) * 1000,
                    metadata={"error": "runtime_error", "success": False},
                )

            except Exception as e:
                logger.error(f"Model {model_id} failed: {e}")
                return model_id, ModelResponse(
                    model_id=model_id,
                    hypothesis="",
                    confidence=0.0,
                    reasoning=f"Error: {e}",
                    response_time_ms=(time.time() - model_start) * 1000,
                    metadata={"error": "unknown", "success": False},
                )

        # Parallele Ausführung mit ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=len(model_ids)) as executor:
            # Submit alle Tasks
            futures: Dict[Future, str] = {
                executor.submit(analyze_with_model, model_id): model_id
                for model_id in model_ids
            }

            # Warte auf Ergebnisse mit Timeout
            for future in as_completed(futures, timeout=MODEL_ANALYSIS_TIMEOUT):
                model_id = futures[future]
                try:
                    result_model_id, response = future.result()
                    if response is not None:
                        results[result_model_id] = response
                except TimeoutError:
                    logger.error(f"Model {model_id} analysis timed out")
                    results[model_id] = ModelResponse(
                        model_id=model_id,
                        hypothesis="",
                        confidence=0.0,
                        reasoning="Analysis timed out",
                        response_time_ms=MODEL_ANALYSIS_TIMEOUT * 1000,
                        metadata={"error": "timeout", "success": False},
                    )
                except Exception as e:
                    logger.error(f"Model {model_id} future failed: {e}")
                    results[model_id] = ModelResponse(
                        model_id=model_id,
                        hypothesis="",
                        confidence=0.0,
                        reasoning=f"Execution failed: {e}",
                        response_time_ms=0.0,
                        metadata={"error": "execution_failed", "success": False},
                    )

        total_time = (time.time() - start_time) * 1000
        logger.info(
            f"Parallel analyses completed: {len(results)}/{len(model_ids)} models, "
            f"total time: {total_time:.0f}ms"
        )

        return list(results.values())

    def _parse_model_response(
        self,
        response_text: str,
        bug: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Parst Modell-Antwort in strukturierte Daten.

        Args:
            response_text: Rohe Modell-Antwort
            bug: Bug-Information für Kontext

        Returns:
            Dict mit hypothesis, confidence, reasoning, patch_suggestion
        """
        # Einfaches Parsing für strukturierte Antworten
        hypothesis = ""
        reasoning = ""
        patch_suggestion = ""
        confidence = 0.5  # Default confidence

        lines = response_text.split("\n")
        current_section = ""

        for line in lines:
            line = line.strip()
            if line.startswith("HYPOTHESE:"):
                current_section = "hypothesis"
                hypothesis = line.replace("HYPOTHESE:", "").strip()
            elif line.startswith("URSACHE:"):
                current_section = "reasoning"
                reasoning = line.replace("URSACHE:", "").strip()
            elif line.startswith("LÖSUNG:"):
                current_section = "patch"
                patch_suggestion = line.replace("LÖSUNG:", "").strip()
            elif line.startswith("BETROFFEN:"):
                # Betroffene Komponenten zum Reasoning hinzufügen
                affected = line.replace("BETROFFEN:", "").strip()
                if reasoning:
                    reasoning += f"\nBetroffen: {affected}"
                else:
                    reasoning = f"Betroffen: {affected}"
            elif current_section == "hypothesis":
                hypothesis += " " + line
            elif current_section == "reasoning":
                reasoning += " " + line
            elif current_section == "patch":
                patch_suggestion += " " + line

        # Falls kein strukturiertes Format, verwende gesamte Antwort als Hypothese
        if not hypothesis and response_text:
            hypothesis = response_text[:200]
            reasoning = response_text[200:400] if len(response_text) > 200 else ""

        # Confidence basierend auf Antwort-Länge und Struktur
        if hypothesis and reasoning and patch_suggestion:
            confidence = 0.8
        elif hypothesis and reasoning:
            confidence = 0.7
        elif hypothesis:
            confidence = 0.6

        return {
            "hypothesis": hypothesis.strip(),
            "confidence": confidence,
            "reasoning": reasoning.strip(),
            "patch_suggestion": patch_suggestion.strip(),
        }

    def run_ensemble(
        self,
        bug: Dict[str, Any],
        models: Optional[List[str]] = None,
    ) -> EnsembleResult:
        """
        Führt Multi-Model Ensemble durch.

        Args:
            bug: Bug-Information
            models: Liste von Modellen

        Returns:
            EnsembleResult
        """
        logger.info(f"Starte Multi-Model Ensemble für {bug.get('bug_id', 'unknown')}")

        result = EnsembleResult()
        result.models_used = models or self.models
        result.total_models = len(result.models_used)

        # Parallele Analysen mit echten Modellen
        responses = self._run_parallel_analyses(bug, result.models_used)
        result.all_responses = responses

        # Voting durchführen
        result.votes = self._perform_voting(responses)
        result.winning_hypothesis = self._get_winning_hypothesis(result.votes)
        result.agreement_level = self._calculate_agreement(result.votes, len(responses))
        result.metadata["voting_complete"] = True

        logger.info(
            f"Ensemble abgeschlossen: {result.winning_hypothesis[:50]}... "
            f"({result.agreement_level})"
        )

        return result

    def _perform_voting(
        self,
        responses: List[ModelResponse],
    ) -> Dict[str, int]:
        """
        Führt Voting durch.

        Args:
            responses: Modell-Antworten

        Returns:
            Stimmen pro Hypothese
        """
        votes: Dict[str, int] = {}

        for response in responses:
            if not response.hypothesis:
                continue  # Überspringe fehlerhafte Antworten

            hypothesis = response.hypothesis
            votes[hypothesis] = votes.get(hypothesis, 0) + 1

        return votes

    def _get_winning_hypothesis(self, votes: Dict[str, int]) -> str:
        """
        Ermittelt Gewinnende Hypothese.

        Args:
            votes: Stimmen

        Returns:
            Gewinnende Hypothese
        """
        if not votes:
            return ""

        return max(votes.keys(), key=lambda k: votes[k])

    def _calculate_agreement(
        self,
        votes: Dict[str, int],
        total_models: int,
    ) -> str:
        """
        Berechnet Übereinstimmungs-Level.

        Args:
            votes: Stimmen
            total_models: Anzahl Modelle

        Returns:
            Agreement-Level
        """
        if not votes or total_models == 0:
            return self.AGREEMENT_NONE

        max_votes = max(votes.values())

        if max_votes == total_models:
            return self.AGREEMENT_UNANIMOUS
        elif max_votes > total_models / 2:
            return self.AGREEMENT_MAJORITY
        elif max_votes > 1:
            return self.AGREEMENT_PLURALITY
        else:
            return self.AGREEMENT_NONE

    def get_weighted_voting(
        self,
        responses: List[ModelResponse],
    ) -> Dict[str, float]:
        """
        Gewichtete Voting mit Confidence.

        Args:
            responses: Modell-Antworten

        Returns:
            Gewichtete Stimmen
        """
        weighted_votes: Dict[str, float] = {}

        for response in responses:
            if not response.hypothesis:
                continue

            hypothesis = response.hypothesis
            confidence = response.confidence
            weighted_votes[hypothesis] = weighted_votes.get(hypothesis, 0) + confidence

        return weighted_votes

    def __call__(self, state: Any) -> Dict[str, Any]:
        """
        Callable für LangGraph.

        Args:
            state: AgentState

        Returns:
            State-Updates
        """
        bug = getattr(state, "current_bug", {})
        models = getattr(state, "ensemble_models", None)

        result = self.run_ensemble(bug, models)

        return {
            "ensemble_result": result.to_dict(),
            "winning_hypothesis": result.winning_hypothesis,
            "metadata": {
                "ensemble_complete": True,
                "agreement_level": result.agreement_level,
                "total_models": result.total_models,
            },
        }
