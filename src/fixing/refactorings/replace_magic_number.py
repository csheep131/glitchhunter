"""
Replace Magic Number Refactoring.

Ersetzt Magic Numbers durch benannte Konstanten.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from fixing.refactorings.base import BaseRefactoring
from fixing.types import RefactoringSuggestion

logger = logging.getLogger(__name__)


class ReplaceMagicNumberRefactoring(BaseRefactoring):
    """
    Replace Magic Number Refactoring-Implementierung.

    Ersetzt Magic Numbers durch benannte Konstanten für:
    - Verbesserte Lesbarkeit
    - Einfachere Wartung
    - Zentrale Definition

    Usage:
        refactoring = ReplaceMagicNumberRefactoring()
        if refactoring.can_apply(suggestion):
            new_code = refactoring.apply(content, suggestion)
    """

    # Übliche Konstanten die nicht ersetzt werden
    COMMON_CONSTANTS = {"0", "1", "2", "10", "100", "1000", "-1"}

    def __init__(self):
        """Initialisiert Replace Magic Number Refactoring."""
        super().__init__(name="ReplaceMagicNumber")

    def can_apply(self, suggestion: RefactoringSuggestion) -> bool:
        """
        Prüft ob Replace Magic Number anwendbar ist.

        Args:
            suggestion: RefactoringSuggestion

        Returns:
            True wenn anwendbar
        """
        return (
            suggestion.category == "smell"
            or "magic" in suggestion.title.lower()
            or any(
                num in suggestion.original_code
                for num in ["3", "4", "5", "6", "7", "8", "9"]
            )
        )

    def apply(
        self,
        content: str,
        suggestion: RefactoringSuggestion,
    ) -> str:
        """
        Führt Replace Magic Number Refactoring durch.

        Args:
            content: Original-Code
            suggestion: RefactoringSuggestion

        Returns:
            Refactorierter Code
        """
        lines = content.split("\n")

        # Magic Number finden und ersetzen
        if suggestion.line_start > 0:
            line_idx = suggestion.line_start - 1
            line = lines[line_idx]

            # Magic Number extrahieren
            magic_number = self._extract_magic_number(suggestion.original_code)

            if magic_number:
                # Konstanten-Name generieren
                const_name = self._generate_constant_name(magic_number, suggestion)

                # In aktueller Zeile ersetzen
                new_line = re.sub(
                    rf"\b{re.escape(magic_number)}\b",
                    const_name,
                    line,
                )
                lines[line_idx] = new_line

                # Konstante am Anfang einfügen
                const_def = f"{const_name} = {magic_number}"
                lines.insert(0, const_def)

        return "\n".join(lines)

    def _extract_magic_number(self, code: str) -> Optional[str]:
        """
        Extrahiert Magic Number aus Code.

        Args:
            code: Code-Zeile

        Returns:
            Magic Number oder None
        """
        # Zahlen finden
        numbers = re.findall(r"\b([3-9]\d*)\b", code)

        for num in numbers:
            if num not in self.COMMON_CONSTANTS:
                return num

        return None

    def _generate_constant_name(
        self,
        number: str,
        suggestion: RefactoringSuggestion,
    ) -> str:
        """
        Generiert Konstanten-Namen.

        Args:
            number: Magic Number
            suggestion: RefactoringSuggestion

        Returns:
            Konstanten-Name
        """
        # Aus Suggestion ableiten wenn möglich
        if "timeout" in suggestion.description.lower():
            return "TIMEOUT_SECONDS"
        elif "max" in suggestion.description.lower():
            return f"MAX_{number}"
        elif "min" in suggestion.description.lower():
            return f"MIN_{number}"

        # Default
        return f"CONST_{number}"

    def find_magic_numbers(self, content: str) -> List[Dict[str, Any]]:
        """
        Findet Magic Numbers im Inhalt.

        Args:
            content: Code-Inhalt

        Returns:
            Liste von Magic Number Informationen
        """
        magic_numbers = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            # Kommentare überspringen
            if line.strip().startswith("#"):
                continue

            numbers = re.findall(r"\b([3-9]\d*)\b", line)

            for num in numbers:
                if num not in self.COMMON_CONSTANTS:
                    magic_numbers.append({
                        "line": i + 1,
                        "number": num,
                        "code": line.strip(),
                    })

        return magic_numbers
