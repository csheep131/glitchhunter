"""
Prediction Engine für GlitchHunter.

Facade für ML-basierte Bug-Vorhersage.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import networkx as nx

from prediction.features.extractor import FeatureExtractor
from prediction.model import GlitchPredictionModel
from prediction.types import PredictionFinding, PredictionResult

logger = logging.getLogger(__name__)


class PredictionEngine:
    """
    Engine für ML-basierte Bug-Vorhersage.

    Usage:
        engine = PredictionEngine()
        findings = await engine.predict(repo_path, symbol_graph)
    """

    def __init__(
        self,
        model_path: Optional[Path] = None,
        use_cpu: bool = True,
        min_probability: float = 0.4,
    ):
        """
        Initialisiert die Prediction Engine.

        Args:
            model_path: Pfad zum ONNX-Modell
            use_cpu: Nur CPU verwenden
            min_probability: Minimale Bug-Wahrscheinlichkeit
        """
        self.model = GlitchPredictionModel(model_path=model_path, use_cpu=use_cpu)
        self.feature_extractor = FeatureExtractor()
        self.min_probability = min_probability

        logger.info(f"PredictionEngine initialisiert (min_probability={min_probability})")

    async def predict(
        self,
        repo_path: Path,
        symbol_graph: Optional[nx.DiGraph] = None,
        **kwargs,
    ) -> List[PredictionFinding]:
        """
        Führt Bug-Vorhersage für Repository durch.

        Args:
            repo_path: Pfad zum Repository
            symbol_graph: Optionaler Symbol-Graph
            **kwargs: Zusätzliche Argumente

        Returns:
            Liste von PredictionFindings
        """
        logger.info(f"Starte Bug-Prediction für {repo_path}")

        try:
            if symbol_graph is None or len(symbol_graph) == 0:
                logger.warning("Kein Symbol-Graph verfügbar")
                return []

            # Features extrahieren
            feature_vectors = self.feature_extractor.batch_extract(symbol_graph)

            if not feature_vectors:
                logger.warning("Keine Features extrahiert")
                return []

            # Feature-Matrix erstellen
            feature_matrix, symbol_ids = self.feature_extractor.create_feature_matrix(
                feature_vectors
            )

            # Batch-Prediction durchführen
            predictions = self.model.predict(feature_matrix)

            # In Findings umwandeln
            findings = self._predictions_to_findings(predictions, feature_vectors)

            # Filtern nach min_probability
            filtered = [
                f for f in findings if f.bug_probability >= self.min_probability
            ]

            logger.info(
                f"Prediction complete: {len(filtered)} findings "
                f"(von {len(predictions)} predictions)"
            )

            return filtered

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return []

    def _predictions_to_findings(
        self,
        predictions: List[PredictionResult],
        feature_vectors: List[Any],
    ) -> List[PredictionFinding]:
        """
        Konvertiert Predictions zu Findings.

        Args:
            predictions: Vorhersage-Ergebnisse
            feature_vectors: Feature-Vektoren

        Returns:
            Liste von PredictionFindings
        """
        findings = []

        for i, pred in enumerate(predictions):
            fv = feature_vectors[i] if i < len(feature_vectors) else None
            file_path = fv.file_path if fv else "unknown"
            symbol_name = fv.symbol_name if fv else f"symbol_{i}"

            severity = self._probability_to_severity(pred.bug_probability)

            finding = PredictionFinding(
                id=f"ml_pred_{i}_{symbol_name}",
                file_path=file_path,
                line_start=0,
                line_end=0,
                severity=severity,
                category="ml_prediction",
                title=f"ML Bug Prediction: {symbol_name}",
                description=self._generate_description(pred, symbol_name),
                bug_probability=pred.bug_probability,
                confidence=pred.confidence,
                feature_importance=pred.feature_importance,
                metadata={
                    "severity_score": pred.severity_score,
                    "risk_level": pred.risk_level,
                },
            )

            findings.append(finding)

        return findings

    def _probability_to_severity(self, probability: float) -> str:
        """Konvertiert Bug-Wahrscheinlichkeit zu Severity."""
        if probability >= 0.8:
            return "critical"
        elif probability >= 0.6:
            return "high"
        elif probability >= 0.4:
            return "medium"
        else:
            return "low"

    def _generate_description(
        self,
        prediction: PredictionResult,
        symbol_name: str,
    ) -> str:
        """Generiert menschenlesbare Beschreibung."""
        risk = prediction.risk_level
        prob = prediction.bug_probability * 100
        conf = prediction.confidence * 100

        return (
            f"Das ML-Modell vorhersagt ein {risk}-Risiko für einen Bug "
            f"in '{symbol_name}' mit {prob:.1f}% Wahrscheinlichkeit "
            f"(Konfidenz: {conf:.1f}%)."
        )

    def get_high_risk_predictions(
        self,
        findings: List[PredictionFinding],
        min_probability: float = 0.7,
    ) -> List[PredictionFinding]:
        """Filtert High-Risk-Predictions."""
        return [f for f in findings if f.bug_probability >= min_probability]
