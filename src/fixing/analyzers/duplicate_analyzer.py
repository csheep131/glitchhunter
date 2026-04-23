"""
Duplicate Code Analyzer.

Analysiert Code auf Duplikate:
- Exakte Duplikate
- Ähnliche Code-Blöcke
- Copy-Paste Muster
"""

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fixing.analyzers.base import BaseAnalyzer
from fixing.types import RefactoringSuggestion

logger = logging.getLogger(__name__)


class DuplicateAnalyzer(BaseAnalyzer):
    """
    Analyzer für Code-Duplikate.

    Usage:
        analyzer = DuplicateAnalyzer()
        metrics = analyzer.analyze(file_path, content)
        suggestions = analyzer.get_suggestions()
    """

    def __init__(self, min_lines: int = 3, similarity_threshold: float = 0.8):
        """
        Initialisiert Duplicate Analyzer.

        Args:
            min_lines: Minimale Zeilen für Duplikat-Erkennung
            similarity_threshold: Ähnlichkeits-Schwelle
        """
        super().__init__(name="DuplicateAnalyzer")
        self.min_lines = min_lines
        self.similarity_threshold = similarity_threshold

    def analyze(
        self,
        file_path: Path,
        content: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Analysiert Code auf Duplikate.

        Args:
            file_path: Pfad zur Datei
            content: Code-Inhalt

        Returns:
            Duplikat-Metriken
        """
        logger.info(f"Analyzing duplicates for {file_path}")

        try:
            duplicates = self._find_duplicates(content)
            metrics = self._calculate_metrics(duplicates, content)

            self._set_metrics(metrics)

            # Suggestions generieren
            self._generate_suggestions(file_path, content, duplicates)

            return metrics

        except Exception as e:
            logger.error(f"Duplicate analysis failed: {e}")
            return {"error": str(e)}

    def _find_duplicates(
        self,
        content: str,
    ) -> List[Dict[str, Any]]:
        """
        Findet Code-Duplikate.

        Args:
            content: Code-Inhalt

        Returns:
            Liste von Duplikaten
        """
        duplicates = []
        lines = content.split("\n")

        # Hash-basierte Duplikatsuche für Blöcke
        block_hashes: Dict[str, List[Tuple[int, int]]] = {}

        # Blöcke verschiedener Größen prüfen
        for block_size in range(self.min_lines, min(10, len(lines))):
            for i in range(len(lines) - block_size + 1):
                block = lines[i : i + block_size]

                # Leere Zeilen und Kommentare filtern
                filtered = [
                    line.strip()
                    for line in block
                    if line.strip() and not line.strip().startswith("#")
                ]

                if len(filtered) < self.min_lines:
                    continue

                # Hash berechnen
                block_key = "\n".join(filtered)
                block_hash = hashlib.md5(block_key.encode()).hexdigest()[:8]

                if block_hash not in block_hashes:
                    block_hashes[block_hash] = []
                block_hashes[block_hash].append((i, i + block_size))

        # Duplikate mit >1 Vorkommen extrahieren
        for block_hash, occurrences in block_hashes.items():
            if len(occurrences) > 1:
                duplicates.append({
                    "hash": block_hash,
                    "occurrences": occurrences,
                    "count": len(occurrences),
                    "lines": lines[occurrences[0][0] : occurrences[0][1]],
                })

        return duplicates

    def _calculate_metrics(
        self,
        duplicates: List[Dict[str, Any]],
        content: str,
    ) -> Dict[str, Any]:
        """
        Berechnet Duplikat-Metriken.

        Args:
            duplicates: Gefundene Duplikate
            content: Code-Inhalt

        Returns:
            Metriken
        """
        lines = content.split("\n")
        total_lines = len(lines)

        # Duplizierte Zeilen zählen
        duplicated_lines = set()
        for dup in duplicates:
            for start, end in dup["occurrences"]:
                for i in range(start, end):
                    duplicated_lines.add(i)

        duplication_rate = len(duplicated_lines) / total_lines if total_lines > 0 else 0

        return {
            "duplicate_blocks": len(duplicates),
            "duplicated_lines": len(duplicated_lines),
            "duplication_rate": duplication_rate,
            "total_lines": total_lines,
        }

    def _generate_suggestions(
        self,
        file_path: Path,
        content: str,
        duplicates: List[Dict[str, Any]],
    ) -> None:
        """
        Generiert Refactoring-Vorschläge.

        Args:
            file_path: Pfad zur Datei
            content: Code-Inhalt
            duplicates: Gefundene Duplikate
        """
        lines = content.split("\n")

        for dup in duplicates:
            if dup["count"] >= 2:
                start, end = dup["occurrences"][0]
                code = "\n".join(lines[start:end])

                suggestion = RefactoringSuggestion(
                    id=f"duplicate_{dup['hash']}",
                    file_path=str(file_path),
                    line_start=start + 1,
                    line_end=end,
                    category="duplication",
                    title=f"Duplicate Code ({dup['count']} occurrences)",
                    description=(
                        f"Code-Duplikat gefunden ({dup['count']} Vorkommen). "
                        f"Empfehlung: In gemeinsame Funktion extrahieren."
                    ),
                    original_code=code,
                    suggested_code="# TODO: Extract common code to helper function",
                    confidence=0.8,
                    risk_level="medium",
                    estimated_impact=f"Reduziere Code-Duplikation ({dup['count']} Vorkommen)",
                    metadata={"occurrences": dup["count"]},
                )
                self._add_suggestion(suggestion)

    def get_suggestions(self) -> List[RefactoringSuggestion]:
        """
        Extrahiert alle Refactoring-Vorschläge.

        Returns:
            Liste von RefactoringSuggestions
        """
        return self._suggestions.copy()

    def find_similar_blocks(
        self,
        content: str,
        threshold: float = None,
    ) -> List[Dict[str, Any]]:
        """
        Findet ähnliche Code-Blöcke (fuzzy matching).

        Args:
            content: Code-Inhalt
            threshold: Ähnlichkeits-Schwelle

        Returns:
            Liste von ähnlichen Blöcken
        """
        threshold = threshold or self.similarity_threshold
        similar = []
        lines = content.split("\n")

        # TODO: Implementierung für fuzzy matching
        # Würde Token-basierten Vergleich erfordern

        return similar
