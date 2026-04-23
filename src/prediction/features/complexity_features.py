"""
Complexity-basierte Feature-Extraktion.

Extrahiert Complexity-Metriken:
- Cyclomatic Complexity
- Cognitive Complexity
- Lines of Code
- Maintainability Index
"""

import logging
from typing import Any, Dict

import numpy as np

logger = logging.getLogger(__name__)


class ComplexityFeatureExtractor:
    """
    Extrahiert Complexity-basierte Features.

    Usage:
        extractor = ComplexityFeatureExtractor()
        features = extractor.extract(complexity_metrics)
    """

    def __init__(self):
        """Initialisiert den Complexity Feature Extractor."""
        logger.info("ComplexityFeatureExtractor initialisiert")

    def extract(
        self,
        complexity_metrics: Dict[str, Any],
    ) -> np.ndarray:
        """
        Extrahiert alle Complexity-Features.

        Args:
            complexity_metrics: Complexity-Metriken

        Returns:
            8-dimensionaler numpy array
        """
        features = np.zeros(8)

        try:
            # Cyclomatic Complexity
            cc = complexity_metrics.get("cyclomatic", 1)
            features[0] = min(100, cc) / 100.0

            # Cognitive Complexity
            cog = complexity_metrics.get("cognitive", 0)
            features[1] = min(100, cog) / 100.0

            # Lines of Code
            loc = complexity_metrics.get("lines", 0)
            features[2] = np.log1p(loc) / 10.0

            # Parameter Count
            params = complexity_metrics.get("parameters", 0)
            features[3] = min(10, params) / 10.0

            # Nesting Depth
            depth = complexity_metrics.get("nesting", 1)
            features[4] = min(10, depth) / 10.0

            # Function Count
            funcs = complexity_metrics.get("function_count", 1)
            features[5] = np.log1p(funcs) / 5.0

            # Class Size
            class_size = complexity_metrics.get("class_size", 0)
            features[6] = min(500, class_size) / 500.0

            # Maintainability Index (invertiert)
            mi = complexity_metrics.get("maintainability", 50)
            features[7] = (100 - mi) / 100.0

        except Exception as e:
            logger.warning(f"Complexity feature extraction failed: {e}")

        return features

    def get_feature_names(self) -> list[str]:
        """
        Returns Namen der Features.

        Returns:
            Liste von Feature-Namen
        """
        return [
            "cyclomatic_complexity",
            "cognitive_complexity",
            "lines_of_code",
            "parameter_count",
            "nesting_depth",
            "function_count",
            "class_size",
            "maintainability_index",
        ]
