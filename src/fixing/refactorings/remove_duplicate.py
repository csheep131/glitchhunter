"""
Remove Duplicate Code Refactoring.

Entfernt Code-Duplikate durch Extraktion in gemeinsame Funktionen.
"""

import logging
from typing import Any, Dict, List

from fixing.refactorings.base import BaseRefactoring
from fixing.types import RefactoringSuggestion

logger = logging.getLogger(__name__)


class RemoveDuplicateRefactoring(BaseRefactoring):
    """
    Remove Duplicate Code Refactoring-Implementierung.

    Entfernt Code-Duplikate durch:
    - Extraktion in gemeinsame Funktionen
    - Verwenden von Helper-Methoden
    - Konsolidierung von Logik

    Usage:
        refactoring = RemoveDuplicateRefactoring()
        if refactoring.can_apply(suggestion):
            new_code = refactoring.apply(content, suggestion)
    """

    def __init__(self):
        """Initialisiert Remove Duplicate Refactoring."""
        super().__init__(name="RemoveDuplicate")

    def can_apply(self, suggestion: RefactoringSuggestion) -> bool:
        """
        Prüft ob Remove Duplicate anwendbar ist.

        Args:
            suggestion: RefactoringSuggestion

        Returns:
            True wenn anwendbar
        """
        return (
            suggestion.category == "duplication"
            or "duplicate" in suggestion.title.lower()
        )

    def apply(
        self,
        content: str,
        suggestion: RefactoringSuggestion,
    ) -> str:
        """
        Führt Remove Duplicate Refactoring durch.

        Args:
            content: Original-Code
            suggestion: RefactoringSuggestion

        Returns:
            Refactorierter Code
        """
        lines = content.split("\n")

        # Duplikate durch Helper-Funktion ersetzen
        if suggestion.line_start > 0:
            start_idx = suggestion.line_start - 1
            end_idx = suggestion.line_end

            # Helper-Funktion erstellen
            helper_name = self._generate_helper_name(suggestion)
            helper_code = self._create_helper(helper_name, suggestion)

            # Original-Code durch Helper-Aufruf ersetzen
            lines[start_idx:end_idx] = [f"    {helper_name}()"]

            # Helper-Funktion am Anfang einfügen
            lines.insert(0, helper_code)
            lines.insert(1, "")

        return "\n".join(lines)

    def _generate_helper_name(self, suggestion: RefactoringSuggestion) -> str:
        """
        Generiert Helper-Methodennamen.

        Args:
            suggestion: RefactoringSuggestion

        Returns:
            Methodenname
        """
        return f"common_{suggestion.id}"

    def _create_helper(
        self,
        name: str,
        suggestion: RefactoringSuggestion,
    ) -> str:
        """
        Erstellt Helper-Funktion.

        Args:
            name: Methodenname
            suggestion: RefactoringSuggestion

        Returns:
            Helper-Funktionsdefinition
        """
        # suggested_code verwenden falls vorhanden
        code = suggestion.suggested_code or suggestion.original_code

        # Indentation korrigieren
        indented = "\n".join(f"    {line}" for line in code.split("\n"))

        return f"def {name}():\n{indented}"

    def find_duplicates(self, content: str) -> List[Dict[str, Any]]:
        """
        Findet Code-Duplikate im Inhalt.

        Args:
            content: Code-Inhalt

        Returns:
            Liste von Duplikat-Informationen
        """
        duplicates = []
        lines = content.split("\n")

        # Einfache Hash-basierte Duplikatsuche
        line_hashes: Dict[str, List[int]] = {}

        for i, line in enumerate(lines):
            stripped = line.strip()
            if len(stripped) > 10:
                h = hash(stripped)
                if h not in line_hashes:
                    line_hashes[h] = []
                line_hashes[h].append(i)

        # Duplikate mit >1 Vorkommen
        for h, occurrences in line_hashes.items():
            if len(occurrences) > 1:
                duplicates.append({
                    "hash": str(h)[:8],
                    "lines": occurrences,
                    "count": len(occurrences),
                    "code": lines[occurrences[0]],
                })

        return duplicates
