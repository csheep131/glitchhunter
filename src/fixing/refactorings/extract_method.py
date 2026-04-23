"""
Extract Method Refactoring.

Extrahiert Code-Blöcke in separate Methoden.
"""

import logging
from typing import Any, Dict

from fixing.refactorings.base import BaseRefactoring
from fixing.types import RefactoringSuggestion

logger = logging.getLogger(__name__)


class ExtractMethodRefactoring(BaseRefactoring):
    """
    Extract Method Refactoring-Implementierung.

    Extrahiert Code-Blöcke in separate Methoden für:
    - Reduzierung von Complexity
    - Verbesserung der Lesbarkeit
    - Wiederverwendbarkeit

    Usage:
        refactoring = ExtractMethodRefactoring()
        if refactoring.can_apply(suggestion):
            new_code = refactoring.apply(content, suggestion)
    """

    def __init__(self):
        """Initialisiert Extract Method Refactoring."""
        super().__init__(name="ExtractMethod")

    def can_apply(self, suggestion: RefactoringSuggestion) -> bool:
        """
        Prüft ob Extract Method anwendbar ist.

        Args:
            suggestion: RefactoringSuggestion

        Returns:
            True wenn anwendbar
        """
        return (
            suggestion.category == "complexity"
            or "extract" in suggestion.title.lower()
        )

    def apply(
        self,
        content: str,
        suggestion: RefactoringSuggestion,
    ) -> str:
        """
        Führt Extract Method Refactoring durch.

        Args:
            content: Original-Code
            suggestion: RefactoringSuggestion

        Returns:
            Refactorierter Code
        """
        lines = content.split("\n")

        # Zeilen extrahieren
        if suggestion.line_start > 0 and suggestion.line_end > 0:
            start_idx = suggestion.line_start - 1
            end_idx = suggestion.line_end

            # Zu extrahierenden Code holen
            extract_code = lines[start_idx:end_idx]

            # Neue Methoden-Generierung (Placeholder)
            method_name = self._generate_method_name(suggestion)
            new_method = self._create_method(method_name, extract_code)

            # Neue Methode einfügen (nach aktueller Methode)
            lines[start_idx:end_idx] = [f"    {method_name}()"]
            lines.insert(start_idx, new_method)

        return "\n".join(lines)

    def _generate_method_name(self, suggestion: RefactoringSuggestion) -> str:
        """
        Generiert Methodennamen aus Suggestion.

        Args:
            suggestion: RefactoringSuggestion

        Returns:
            Methodenname
        """
        # Aus Title ableiten
        title = suggestion.title.lower()
        if "extract" in title:
            return "extracted_method"
        return f"helper_{suggestion.id}"

    def _create_method(self, name: str, code_lines: list[str]) -> str:
        """
        Erstellt neue Methode aus Code-Zeilen.

        Args:
            name: Methodenname
            code_lines: Code-Zeilen

        Returns:
            Methodendefinition
        """
        # Indentation korrigieren
        indented = "\n".join(f"    {line}" for line in code_lines)

        return f"def {name}():\n{indented}\n"
