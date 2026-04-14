"""
Ensemble Coordinator für GlitchHunter Escalation Level 3.

Koordiniert parallele Analysen mit mehreren Modellen und Ensemble-Voting.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


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


class EnsembleCoordinator:
    """
    Koordiniert Multi-Model Ensemble.

    Features:
    - Parallele Analysen mit mehreren Modellen
    - Ensemble-Voting
    - Confidence-Weighted Voting

    Usage:
        coordinator = EnsembleCoordinator()
        result = coordinator.run_ensemble(bug, models)
    """

    # Agreement-Levels
    AGREEMENT_UNANIMOUS = "unanimous"
    AGREEMENT_MAJORITY = "majority"
    AGREEMENT_PLURALITY = "plurality"
    AGREEMENT_NONE = "none"

    def __init__(
        self,
        models: Optional[List[str]] = None,
    ) -> None:
        """
        Initialisiert Ensemble Coordinator.

        Args:
            models: Liste von Modell-IDs.
        """
        self.models = models or [
            "analyzer_1",
            "analyzer_2",
            "analyzer_3",
        ]

        logger.debug(f"EnsembleCoordinator initialisiert: {len(self.models)} Modelle")

    def run_ensemble(
        self,
        bug: Dict[str, Any],
        models: Optional[List[str]] = None,
    ) -> EnsembleResult:
        """
        Führt Multi-Model Ensemble durch.

        Args:
            bug: Bug-Information.
            models: Liste von Modellen.

        Returns:
            EnsembleResult.
        """
        logger.info(f"Starte Multi-Model Ensemble für {bug.get('bug_id', 'unknown')}")

        result = EnsembleResult()
        result.models_used = models or self.models
        result.total_models = len(result.models_used)

        # Parallele Analysen simulieren
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

    def _run_parallel_analyses(
        self,
        bug: Dict[str, Any],
        models: List[str],
    ) -> List[ModelResponse]:
        """
        Führt parallele Analysen durch.

        Args:
            bug: Bug.
            models: Modelle.

        Returns:
            Liste von ModelResponse.
        """
        import time
        responses = []

        for model_id in models:
            start_time = time.time()

            # Simulation der Modell-Analyse
            # In der Realität würde hier das Modell aufgerufen werden
            hypothesis = self._simulate_model_analysis(bug, model_id)

            response = ModelResponse(
                model_id=model_id,
                hypothesis=hypothesis,
                confidence=0.5 + (hash(model_id) % 30) / 100,  # Simulierte Confidence
                reasoning=f"Analysis from {model_id}",
                response_time_ms=(time.time() - start_time) * 1000,
            )

            responses.append(response)

        return responses

    def _simulate_model_analysis(
        self,
        bug: Dict[str, Any],
        model_id: str,
    ) -> str:
        """
        Simuliert Modell-Analyse.

        Args:
            bug: Bug.
            model_id: Modell-ID.

        Returns:
            Hypothese.
        """
        bug_type = bug.get("bug_type", "unknown")
        file_path = bug.get("file_path", "")

        # Verschiedene Hypothesen für verschiedene Modelle
        hypotheses = {
            "analyzer_1": f"Root cause in {file_path}: Missing input validation",
            "analyzer_2": f"Root cause in {file_path}: Incorrect data flow handling",
            "analyzer_3": f"Root cause in {file_path}: Race condition in async code",
        }

        return hypotheses.get(model_id, f"Unknown issue in {file_path}")

    def _perform_voting(
        self,
        responses: List[ModelResponse],
    ) -> Dict[str, int]:
        """
        Führt Voting durch.

        Args:
            responses: Modell-Antworten.

        Returns:
            Stimmen pro Hypothese.
        """
        votes: Dict[str, int] = {}

        for response in responses:
            hypothesis = response.hypothesis
            votes[hypothesis] = votes.get(hypothesis, 0) + 1

        return votes

    def _get_winning_hypothesis(self, votes: Dict[str, int]) -> str:
        """
        Ermittelt Gewinnende Hypothese.

        Args:
            votes: Stimmen.

        Returns:
            Gewinnende Hypothese.
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
            votes: Stimmen.
            total_models: Anzahl Modelle.

        Returns:
            Agreement-Level.
        """
        if not votes:
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
            responses: Modell-Antworten.

        Returns:
            Gewichtete Stimmen.
        """
        weighted_votes: Dict[str, float] = {}

        for response in responses:
            hypothesis = response.hypothesis
            confidence = response.confidence
            weighted_votes[hypothesis] = weighted_votes.get(hypothesis, 0) + confidence

        return weighted_votes

    def __call__(self, state: Any) -> Dict[str, Any]:
        """
        Callable für LangGraph.

        Args:
            state: AgentState.

        Returns:
            State-Updates.
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
