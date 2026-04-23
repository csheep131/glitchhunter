"""
Base Interface für Refactoring-Implementierungen.

Definiert das gemeinsame Interface für alle Refactoring-Typen.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

from fixing.types import RefactoringSuggestion, RefactoringResult


class BaseRefactoring(ABC):
    """
    Abstrakte Basisklasse für alle Refactoring-Implementierungen.

    Jedes Refactoring muss folgende Methoden implementieren:
    - can_apply: Prüft ob Refactoring anwendbar ist
    - apply: Führt das Refactoring durch

    Usage:
        class MyRefactoring(BaseRefactoring):
            def can_apply(self, suggestion: RefactoringSuggestion) -> bool:
                # Implementierung
                pass

            def apply(self, content: str, suggestion: RefactoringSuggestion) -> str:
                # Implementierung
                pass
    """

    def __init__(self, name: str):
        """
        Initialisiert das BaseRefactoring.

        Args:
            name: Name des Refactoring-Typs
        """
        self.name = name

    @abstractmethod
    def can_apply(self, suggestion: RefactoringSuggestion) -> bool:
        """
        Prüft ob das Refactoring auf die Suggestion anwendbar ist.

        Args:
            suggestion: RefactoringSuggestion

        Returns:
            True wenn anwendbar
        """
        pass

    @abstractmethod
    def apply(
        self,
        content: str,
        suggestion: RefactoringSuggestion,
    ) -> str:
        """
        Führt das Refactoring durch.

        Args:
            content: Original-Code
            suggestion: RefactoringSuggestion

        Returns:
            Refactorierter Code
        """
        pass

    def validate(
        self,
        original: str,
        refactored: str,
        suggestion: RefactoringSuggestion,
    ) -> bool:
        """
        Validiert das Refactoring-Ergebnis.

        Args:
            original: Original-Code
            refactored: Refactorierter Code
            suggestion: Ursprüngliche Suggestion

        Returns:
            True wenn validiert
        """
        # Basis-Validierung: Code darf nicht leer sein
        if not refactored.strip():
            return False

        # Syntax-Validierung (wenn möglich)
        try:
            compile(refactored, "<string>", "exec")
            return True
        except SyntaxError:
            return False

    def get_metadata(self) -> Dict[str, Any]:
        """
        Returns Metadaten des Refactorings.

        Returns:
            Metadaten
        """
        return {"name": self.name}
