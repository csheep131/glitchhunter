"""
Code Smell Analyzer.

Analysiert Code auf Code-Smells:
- Magic Numbers
- Long Methods
- Long Parameter Lists
"""

import ast
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

from fixing.analyzers.base import BaseAnalyzer
from fixing.types import RefactoringSuggestion

logger = logging.getLogger(__name__)


class SmellAnalyzer(BaseAnalyzer):
    """
    Analyzer für Code-Smells.

    Usage:
        analyzer = SmellAnalyzer()
        metrics = analyzer.analyze(file_path, content)
        suggestions = analyzer.get_suggestions()
    """

    # Konfiguration
    MAX_METHOD_LINES = 50
    MAX_PARAMS = 5
    COMMON_CONSTANTS = {"0", "1", "2", "10", "100", "1000", "-1"}

    def __init__(
        self,
        max_method_lines: int = 50,
        max_params: int = 5,
    ):
        """
        Initialisiert Smell Analyzer.

        Args:
            max_method_lines: Maximale Methoden-Länge
            max_params: Maximale Parameter-Anzahl
        """
        super().__init__(name="SmellAnalyzer")
        self.max_method_lines = max_method_lines
        self.max_params = max_params

    def analyze(
        self,
        file_path: Path,
        content: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Analysiert Code auf Code-Smells.

        Args:
            file_path: Pfad zur Datei
            content: Code-Inhalt

        Returns:
            Smell-Metriken
        """
        logger.info(f"Analyzing code smells for {file_path}")

        try:
            tree = ast.parse(content)
            metrics = self._calculate_metrics(tree, content, file_path)

            self._set_metrics(metrics)

            # Suggestions generieren
            self._generate_suggestions(file_path, content, tree, metrics)

            return metrics

        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Smell analysis failed: {e}")
            return {"error": str(e)}

    def _calculate_metrics(
        self,
        tree: ast.AST,
        content: str,
        file_path: Path,
    ) -> Dict[str, Any]:
        """
        Berechnet Smell-Metriken.

        Args:
            tree: AST
            content: Code-Inhalt
            file_path: Dateipfad

        Returns:
            Metriken
        """
        lines = content.split("\n")
        functions = self._find_functions(tree)

        return {
            "lines": len(lines),
            "function_count": len(functions),
            "magic_numbers": len(self._find_magic_numbers(content)),
            "long_methods": sum(
                1 for f in functions if f.get("lines", 0) > self.max_method_lines
            ),
            "long_param_lists": sum(
                1 for f in functions if f.get("params", 0) > self.max_params
            ),
        }

    def _find_functions(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """
        Findet alle Funktionen im AST.

        Args:
            tree: AST

        Returns:
            Liste von Funktions-Informationen
        """
        functions = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Zeilenanzahl berechnen
                end_line = getattr(node, "end_lineno", node.lineno)
                lines = end_line - node.lineno + 1

                # Parameter zählen
                params = len(node.args.args)

                functions.append({
                    "name": node.name,
                    "line_start": node.lineno,
                    "line_end": end_line,
                    "lines": lines,
                    "params": params,
                })

        return functions

    def _find_magic_numbers(self, content: str) -> List[Dict[str, Any]]:
        """
        Findet Magic Numbers im Code.

        Args:
            content: Code-Inhalt

        Returns:
            Liste von Magic Numbers
        """
        magic = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            # Kommentare überspringen
            if line.strip().startswith("#"):
                continue

            # Zahlen finden
            numbers = re.findall(r"\b([3-9]\d*)\b", line)

            for num in numbers:
                if num not in self.COMMON_CONSTANTS:
                    magic.append({
                        "line": i + 1,
                        "number": num,
                        "code": line.strip(),
                    })

        return magic

    def _generate_suggestions(
        self,
        file_path: Path,
        content: str,
        tree: ast.AST,
        metrics: Dict[str, Any],
    ) -> None:
        """
        Generiert Refactoring-Vorschläge.

        Args:
            file_path: Pfad zur Datei
            content: Code-Inhalt
            tree: AST
            metrics: Metriken
        """
        lines = content.split("\n")
        functions = self._find_functions(tree)

        # Long Methods
        for func in functions:
            if func["lines"] > self.max_method_lines:
                suggestion = RefactoringSuggestion(
                    id=f"long_method_{func['name']}",
                    file_path=str(file_path),
                    line_start=func["line_start"],
                    line_end=func["line_end"],
                    category="smell",
                    title=f"Long Method: {func['name']} ({func['lines']} lines)",
                    description=(
                        f"Methode ist {func['lines']} Zeilen lang. "
                        f"Empfehlung: In kleinere Methoden aufteilen."
                    ),
                    original_code="\n".join(
                        lines[func["line_start"] - 1 : func["line_end"]]
                    ),
                    suggested_code="# TODO: Extract methods",
                    confidence=0.7,
                    risk_level="medium",
                    estimated_impact="Verbessere Wartbarkeit",
                )
                self._add_suggestion(suggestion)

        # Magic Numbers
        magic_numbers = self._find_magic_numbers(content)
        for magic in magic_numbers[:5]:  # Limit auf 5
            suggestion = RefactoringSuggestion(
                id=f"magic_{magic['line']}_{magic['number']}",
                file_path=str(file_path),
                line_start=magic["line"],
                line_end=magic["line"],
                category="smell",
                title=f"Magic Number: {magic['number']}",
                description=(
                    f"Magic number {magic['number']} sollte als Konstante "
                    "definiert werden"
                ),
                original_code=magic["code"],
                suggested_code=f"CONST_{magic['number']} = {magic['number']}",
                confidence=0.6,
                risk_level="low",
                estimated_impact="Verbessere Code-Lesbarkeit",
            )
            self._add_suggestion(suggestion)

    def get_suggestions(self) -> List[RefactoringSuggestion]:
        """
        Extrahiert alle Refactoring-Vorschläge.

        Returns:
            Liste von RefactoringSuggestions
        """
        return self._suggestions.copy()
