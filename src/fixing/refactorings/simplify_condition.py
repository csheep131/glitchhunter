"""
Simplify Condition Refactoring.

Vereinfacht komplexe Bedingungen und verschachtelte If-Statements.
"""

import logging
from typing import Any, Dict, Tuple

from fixing.refactorings.base import BaseRefactoring
from fixing.types import RefactoringSuggestion

logger = logging.getLogger(__name__)


class SimplifyConditionRefactoring(BaseRefactoring):
    """
    Simplify Condition Refactoring-Implementierung.

    Vereinfacht komplexe Bedingungen durch:
    - Early Returns
    - Boolean Extraction
    - De Morgan's Laws

    Usage:
        refactoring = SimplifyConditionRefactoring()
        if refactoring.can_apply(suggestion):
            new_code = refactoring.apply(content, suggestion)
    """

    def __init__(self):
        """Initialisiert Simplify Condition Refactoring."""
        super().__init__(name="SimplifyCondition")

    def can_apply(self, suggestion: RefactoringSuggestion) -> bool:
        """
        Prüft ob Simplify Condition anwendbar ist.

        Args:
            suggestion: RefactoringSuggestion

        Returns:
            True wenn anwendbar
        """
        return (
            suggestion.category == "complexity"
            or "simplify" in suggestion.title.lower()
            or "condition" in suggestion.title.lower()
            or "if" in suggestion.original_code.lower()
        )

    def apply(
        self,
        content: str,
        suggestion: RefactoringSuggestion,
    ) -> str:
        """
        Führt Simplify Condition Refactoring durch.

        Args:
            content: Original-Code
            suggestion: RefactoringSuggestion

        Returns:
            Refactorierter Code
        """
        lines = content.split("\n")

        # Bedingung vereinfachen
        if suggestion.line_start > 0 and suggestion.suggested_code:
            start_idx = suggestion.line_start - 1
            end_idx = suggestion.line_end

            # Original-Zeilen ersetzen
            new_lines = suggestion.suggested_code.split("\n")
            lines[start_idx:end_idx] = new_lines

        return "\n".join(lines)

    def simplify_boolean(self, condition: str) -> str:
        """
        Vereinfacht Boolean-Ausdruck.

        Args:
            condition: Boolean-Ausdruck

        Returns:
            Vereinfachter Ausdruck
        """
        # Einfache Vereinfachungen
        simplifications = {
            "not True": "False",
            "not False": "True",
            "True and": "",
            "False or": "",
            "True or": "True",
            "False and": "False",
        }

        result = condition
        for old, new in simplifications.items():
            result = result.replace(old, new)

        return result.strip()

    def extract_condition(
        self,
        condition: str,
        name: str = None,
    ) -> Tuple[str, str]:
        """
        Extrahiert Bedingung in benannte Variable.

        Args:
            condition: Boolean-Ausdruck
            name: Variablenname

        Returns:
            Tuple (Variable-Definition, Variablenname)
        """
        if name is None:
            name = "condition"

        var_def = f"{name} = {condition}"
        return var_def, name

    def create_early_return(
        self,
        condition: str,
        body: str,
    ) -> str:
        """
        Erstellt Early Return statt verschachteltem If.

        Args:
            condition: Bedingung
            body: If-Body

        Returns:
            Refactorierter Code mit Early Return
        """
        # Negierte Bedingung für Early Return
        negated = f"not ({condition})"

        early_return = f"if {negated}:\n    return\n\n{body}"

        return early_return
