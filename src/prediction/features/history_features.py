"""
History-basierte Feature-Extraktion.

Extrahiert Git-History Features:
- Churn Rate
- Bug Fix Rate
- Contributor Count
- Hotspot Score
"""

import logging
from typing import Any, Dict

import numpy as np

logger = logging.getLogger(__name__)


class HistoryFeatureExtractor:
    """
    Extrahiert History-basierte Features aus Git-Metriken.

    Usage:
        extractor = HistoryFeatureExtractor()
        features = extractor.extract(git_metrics)
    """

    def __init__(self):
        """Initialisiert den History Feature Extractor."""
        logger.info("HistoryFeatureExtractor initialisiert")

    def extract(
        self,
        git_metrics: Dict[str, Any],
    ) -> np.ndarray:
        """
        Extrahiert alle History-Features.

        Args:
            git_metrics: Git-Metriken

        Returns:
            8-dimensionaler numpy array
        """
        features = np.zeros(8)

        try:
            # Churn Rate
            churn = git_metrics.get("churn_rate", 0)
            features[0] = min(50, churn) / 50.0

            # Bug Fix Rate
            bug_rate = git_metrics.get("bug_fixes", 0)
            features[1] = min(20, bug_rate) / 20.0

            # Days Since Last Change
            days = git_metrics.get("days_since_change", 30)
            features[2] = 1.0 - min(365, days) / 365.0

            # Contributor Count
            contributors = git_metrics.get("contributors", 1)
            features[3] = min(20, contributors) / 20.0

            # Avg Commit Size
            commit_size = git_metrics.get("avg_commit_size", 50)
            features[4] = min(1000, commit_size) / 1000.0

            # Refactor Count
            refactors = git_metrics.get("refactors", 0)
            features[5] = min(10, refactors) / 10.0

            # Hotspot Score
            hotspot = git_metrics.get("hotspot_score", 0)
            features[6] = min(1.0, hotspot)

            # Age
            age = git_metrics.get("age_days", 0)
            features[7] = min(1000, age) / 1000.0

        except Exception as e:
            logger.warning(f"History feature extraction failed: {e}")

        return features

    def get_feature_names(self) -> list[str]:
        """
        Returns Namen der Features.

        Returns:
            Liste von Feature-Namen
        """
        return [
            "churn_rate",
            "bug_fix_rate",
            "days_since_change",
            "contributor_count",
            "avg_commit_size",
            "refactor_count",
            "hotspot_score",
            "age_days",
        ]
