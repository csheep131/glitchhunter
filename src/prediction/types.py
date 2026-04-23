"""
Type-Klassen für Glitch Prediction.

Enthält:
- PredictionResult: Ergebnis einer Bug-Vorhersage
- PredictionFinding: Finding aus ML-Vorhersage
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class PredictionResult:
    """
    Ergebnis einer Bug-Vorhersage.

    Attributes:
        symbol_name: Name des Symbols
        file_path: Dateipfad
        bug_probability: Wahrscheinlichkeit für Bug (0-1)
        severity_score: Vorhergesagte Schwere (0-1)
        risk_level: Risikostufe (low, medium, high, critical)
        confidence: Konfidenz der Vorhersage
        feature_importance: Wichtigste Features
    """

    symbol_name: str
    file_path: str
    bug_probability: float
    severity_score: float
    risk_level: str
    confidence: float
    feature_importance: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Konvertiert zu Dict.

        Returns:
            Dictionary-Repräsentation des Ergebnisses
        """
        return {
            "symbol_name": self.symbol_name,
            "file_path": self.file_path,
            "bug_probability": self.bug_probability,
            "severity_score": self.severity_score,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "feature_importance": self.feature_importance,
        }


@dataclass
class PredictionFinding:
    """
    Finding aus ML-Vorhersage.

    Attributes:
        id: Eindeutige ID
        file_path: Betroffene Datei
        line_start: Startzeile
        line_end: Endzeile
        severity: Schweregrad (critical, high, medium, low)
        category: Kategorie (ml_prediction)
        title: Kurzer Titel
        description: Detaillierte Beschreibung
        bug_probability: Vorhergesagte Bug-Wahrscheinlichkeit
        confidence: Konfidenz der Vorhersage
        feature_importance: Wichtigste Features
        metadata: Zusätzliche Metadaten
    """

    id: str
    file_path: str
    line_start: int
    line_end: int
    severity: str
    category: str
    title: str
    description: str
    bug_probability: float
    confidence: float
    feature_importance: Optional[Dict[str, float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Konvertiert zu Dict.

        Returns:
            Dictionary-Repräsentation des Findings
        """
        return {
            "id": self.id,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "bug_probability": self.bug_probability,
            "confidence": self.confidence,
            "feature_importance": self.feature_importance,
            "metadata": self.metadata,
        }
