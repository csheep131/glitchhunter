"""
Base Interface für Analyzer-Implementierungen.

Definiert das gemeinsame Interface für alle Code-Analyzer.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List

from fixing.types import RefactoringSuggestion


class BaseAnalyzer(ABC):
    """
    Abstrakte Basisklasse für alle Analyzer-Implementierungen.

    Jeder Analyzer muss folgende Methoden implementieren:
    - analyze: Analysiert Code und findet Issues
    - get_suggestions: Extrahiert Refactoring-Vorschläge

    Usage:
        class MyAnalyzer(BaseAnalyzer):
            def analyze(self, file_path: Path, content: str) -> Dict[str, Any]:
                # Implementierung
                pass

            def get_suggestions(self) -> List[RefactoringSuggestion]:
                # Implementierung
                pass
    """

    def __init__(self, name: str):
        """
        Initialisiert den BaseAnalyzer.

        Args:
            name: Name des Analyzers
        """
        self.name = name
        self._suggestions: List[RefactoringSuggestion] = []
        self._metrics: Dict[str, Any] = {}

    @abstractmethod
    def analyze(self, file_path: Path, content: str, **kwargs) -> Dict[str, Any]:
        """
        Analysiert Code und findet Issues.

        Args:
            file_path: Pfad zur Datei
            content: Code-Inhalt
            **kwargs: Analyzer-spezifische Argumente

        Returns:
            Analyse-Ergebnis
        """
        pass

    @abstractmethod
    def get_suggestions(self) -> List[RefactoringSuggestion]:
        """
        Extrahiert alle Refactoring-Vorschläge.

        Returns:
            Liste von RefactoringSuggestions
        """
        pass

    def get_metrics(self) -> Dict[str, Any]:
        """
        Returns gesammelte Metriken.

        Returns:
            Metriken
        """
        return self._metrics.copy()

    def get_metadata(self) -> Dict[str, Any]:
        """
        Returns Metadaten des Analyzers.

        Returns:
            Metadaten
        """
        return {
            "name": self.name,
            "suggestions_count": len(self._suggestions),
        }

    def _add_suggestion(self, suggestion: RefactoringSuggestion) -> None:
        """
        Fügt eine Refactoring-Suggestion hinzu.

        Args:
            suggestion: RefactoringSuggestion
        """
        self._suggestions.append(suggestion)

    def _clear_suggestions(self) -> None:
        """Löscht alle gespeicherten Suggestionen."""
        self._suggestions.clear()

    def _set_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Setzt Analyse-Metriken.

        Args:
            metrics: Metriken
        """
        self._metrics = metrics
