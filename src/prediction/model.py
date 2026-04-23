"""
Glitch Prediction Model mit ONNX.

ML-Modell für Bug-Vorhersage basierend auf Feature-Vektoren.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from prediction.types import PredictionResult

logger = logging.getLogger(__name__)


class GlitchPredictionModel:
    """
    ONNX-basiertes Vorhersagemodell für Bugs.

    Usage:
        model = GlitchPredictionModel()
        predictions = model.predict(feature_matrix)
    """

    RISK_THRESHOLDS = {
        "critical": 0.8,
        "high": 0.6,
        "medium": 0.4,
        "low": 0.0,
    }

    def __init__(
        self,
        model_path: Optional[Path] = None,
        use_cpu: bool = True,
    ):
        """
        Initialisiert das Vorhersagemodell.

        Args:
            model_path: Pfad zum ONNX-Modell
            use_cpu: Nur CPU verwenden
        """
        self.model_path = model_path
        self.use_cpu = use_cpu
        self.session = None
        self.input_name = None
        self.feature_names = self._get_feature_names()

        self._load_model()
        logger.info(f"GlitchPredictionModel initialisiert (CPU={use_cpu})")

    def _get_feature_names(self) -> List[str]:
        """Returns Feature-Namen für Interpretation."""
        return [
            # Graph Features (0-7)
            "in_degree",
            "out_degree",
            "total_degree",
            "in_degree_centrality",
            "out_degree_centrality",
            "betweenness_centrality",
            "pagerank_score",
            "hub_score",
            # Complexity Features (8-15)
            "cyclomatic_complexity",
            "cognitive_complexity",
            "lines_of_code",
            "parameter_count",
            "nesting_depth",
            "function_count",
            "class_size",
            "maintainability_index",
            # Structural Features (16-23)
            "neighbor_count_1hop",
            "neighbor_count_2hop",
            "clustering_coefficient",
            "triangle_count",
            "eccentricity",
            "closeness_centrality",
            "community_size",
            "is_leaf_node",
            # History Features (24-31)
            "churn_rate",
            "bug_fix_rate",
            "days_since_change",
            "contributor_count",
            "avg_commit_size",
            "refactor_count",
            "hotspot_score",
            "age_days",
        ]

    def _load_model(self):
        """Lädt ONNX-Modell oder erstellt Dummy."""
        try:
            import onnxruntime as ort

            if self.model_path and self.model_path.exists():
                providers = ["CPUExecutionProvider"]
                if not self.use_cpu:
                    providers.insert(0, "CUDAExecutionProvider")

                self.session = ort.InferenceSession(
                    str(self.model_path),
                    providers=providers,
                )
                self.input_name = self.session.get_inputs()[0].name
                logger.info(f"ONNX-Modell geladen: {self.model_path}")
            else:
                self._create_dummy_model()
                logger.info("Dummy-Modell erstellt (kein ONNX-Modell gefunden)")

        except ImportError:
            logger.warning("onnxruntime nicht installiert, verwende Dummy-Modell")
            self._create_dummy_model()
        except Exception as e:
            logger.error(f"Modell-Laden fehlgeschlagen: {e}")
            self._create_dummy_model()

    def _create_dummy_model(self):
        """Erstellt einfaches Dummy-Modell für Demo-Zwecke."""
        self.session = None
        self.input_name = None
        logger.debug("Dummy model initialized")

    def predict(
        self,
        feature_matrix: np.ndarray,
    ) -> List[PredictionResult]:
        """
        Führt Batch-Vorhersage durch.

        Args:
            feature_matrix: (n_samples, 32) Feature-Matrix

        Returns:
            Liste von PredictionResult
        """
        if feature_matrix.size == 0:
            return []

        logger.info(f"Predicting bugs für {feature_matrix.shape[0]} samples")

        try:
            if self.session is not None:
                bug_probs, severity_scores = self.session.run(
                    None,
                    {self.input_name: feature_matrix.astype(np.float32)},
                )
                bug_probs = bug_probs.flatten()
                severity_scores = severity_scores.flatten()
            else:
                bug_probs, severity_scores = self._predict_dummy(feature_matrix)

            # Ergebnisse erstellen
            results = []
            for i in range(len(bug_probs)):
                risk_level = self._get_risk_level(bug_probs[i])
                confidence = self._estimate_confidence(feature_matrix[i])

                results.append(
                    PredictionResult(
                        symbol_name=f"symbol_{i}",
                        file_path="unknown",
                        bug_probability=float(bug_probs[i]),
                        severity_score=float(severity_scores[i]),
                        risk_level=risk_level,
                        confidence=confidence,
                        feature_importance=self._get_feature_importance(
                            feature_matrix[i]
                        ),
                    )
                )

            logger.info(
                f"Vorhersage abgeschlossen: "
                f"Ø bug_prob={np.mean(bug_probs):.2f}, "
                f"high_risk={sum(1 for p in bug_probs if p > 0.6)}"
            )

            return results

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return []

    def _predict_dummy(
        self,
        feature_matrix: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Dummy-Vorhersage mit Heuristiken.

        Args:
            feature_matrix: Feature-Matrix

        Returns:
            (bug_probabilities, severity_scores)
        """
        n_samples = feature_matrix.shape[0]
        bug_probs = np.zeros(n_samples)
        severity_scores = np.zeros(n_samples)

        for i in range(n_samples):
            features = feature_matrix[i]

            complexity_score = np.mean(features[8:16])
            history_score = np.mean(features[24:32])
            graph_score = np.mean(features[0:8])

            bug_prob = (
                0.4 * complexity_score + 0.3 * history_score + 0.3 * graph_score
            )
            bug_prob += np.random.normal(0, 0.1)
            bug_prob = np.clip(bug_prob, 0.0, 1.0)

            severity = bug_prob * (0.8 + 0.4 * np.random.random())
            severity = np.clip(severity, 0.0, 1.0)

            bug_probs[i] = bug_prob
            severity_scores[i] = severity

        return bug_probs, severity_scores

    def _get_risk_level(self, bug_probability: float) -> str:
        """Bestimmt Risikostufe aus Bug-Wahrscheinlichkeit."""
        if bug_probability >= self.RISK_THRESHOLDS["critical"]:
            return "critical"
        elif bug_probability >= self.RISK_THRESHOLDS["high"]:
            return "high"
        elif bug_probability >= self.RISK_THRESHOLDS["medium"]:
            return "medium"
        else:
            return "low"

    def _estimate_confidence(self, features: np.ndarray) -> float:
        """Schätzt Konfidenz der Vorhersage."""
        missing = np.sum(features == 0)
        total = len(features)
        confidence = 1.0 - (missing / total)

        std = np.std(features)
        if 0.1 < std < 0.5:
            confidence += 0.1

        return min(1.0, confidence)

    def _get_feature_importance(
        self,
        features: np.ndarray,
    ) -> Dict[str, float]:
        """Berechnet Feature-Importance für Interpretierbarkeit."""
        importance = {}

        for i, name in enumerate(self.feature_names):
            importance[name] = float(features[i])

        sorted_importance = dict(
            sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
        )

        return sorted_importance

    def predict_single(
        self,
        feature_vector: np.ndarray,
        symbol_name: str = "unknown",
        file_path: str = "unknown",
    ) -> PredictionResult:
        """
        Führt Vorhersage für ein einzelnes Symbol durch.

        Args:
            feature_vector: (32,) Feature-Vektor
            symbol_name: Name des Symbols
            file_path: Dateipfad

        Returns:
            PredictionResult
        """
        feature_matrix = feature_vector.reshape(1, -1)
        results = self.predict(feature_matrix)

        if results:
            result = results[0]
            result.symbol_name = symbol_name
            result.file_path = file_path
            return result

        return PredictionResult(
            symbol_name=symbol_name,
            file_path=file_path,
            bug_probability=0.5,
            severity_score=0.5,
            risk_level="medium",
            confidence=0.5,
        )
