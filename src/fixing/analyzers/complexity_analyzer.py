"""
Complexity Analyzer für Code-Analyse.

Analysiert Code auf Complexity-Probleme:
- Cyclomatic Complexity
- Cognitive Complexity
- Nesting Depth
"""

import ast
import logging
from pathlib import Path
from typing import Any, Dict, List

from fixing.analyzers.base import BaseAnalyzer
from fixing.types import RefactoringSuggestion

logger = logging.getLogger(__name__)


class ComplexityAnalyzer(BaseAnalyzer):
    """
    Analyzer für Complexity-Metriken.

    Usage:
        analyzer = ComplexityAnalyzer()
        metrics = analyzer.analyze(file_path, content)
        suggestions = analyzer.get_suggestions()
    """

    def __init__(self, max_complexity: int = 10, max_nesting: int = 4):
        """
        Initialisiert Complexity Analyzer.

        Args:
            max_complexity: Maximale erlaubte Complexity
            max_nesting: Maximale Verschachtelungstiefe
        """
        super().__init__(name="ComplexityAnalyzer")
        self.max_complexity = max_complexity
        self.max_nesting = max_nesting

    def analyze(
        self,
        file_path: Path,
        content: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Analysiert Code auf Complexity.

        Args:
            file_path: Pfad zur Datei
            content: Code-Inhalt

        Returns:
            Complexity-Metriken
        """
        logger.info(f"Analyzing complexity for {file_path}")

        try:
            tree = ast.parse(content)
            metrics = self._calculate_metrics(tree, content)

            self._set_metrics(metrics)

            # Suggestions generieren
            self._generate_suggestions(file_path, content, tree, metrics)

            return metrics

        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Complexity analysis failed: {e}")
            return {"error": str(e)}

    def _calculate_metrics(
        self,
        tree: ast.AST,
        content: str,
    ) -> Dict[str, Any]:
        """
        Berechnet Complexity-Metriken.

        Args:
            tree: AST
            content: Code-Inhalt

        Returns:
            Metriken
        """
        lines = content.split("\n")

        return {
            "cyclomatic": self._calculate_cyclomatic(tree),
            "cognitive": self._calculate_cognitive(tree),
            "lines": len(lines),
            "nesting": self._calculate_max_nesting(tree),
            "function_count": self._count_functions(tree),
        }

    def _calculate_cyclomatic(self, tree: ast.AST) -> int:
        """
        Berechnet cyclomatic Complexity.

        Args:
            tree: AST

        Returns:
            Cyclomatic Complexity
        """
        complexity = 1

        for node in ast.walk(tree):
            if isinstance(
                node,
                (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.With),
            ):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

        return complexity

    def _calculate_cognitive(self, tree: ast.AST) -> int:
        """
        Berechnet Cognitive Complexity (vereinfacht).

        Args:
            tree: AST

        Returns:
            Cognitive Complexity
        """
        complexity = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For)):
                complexity += 1

        return complexity

    def _calculate_max_nesting(self, tree: ast.AST) -> int:
        """
        Berechnet maximale Verschachtelungstiefe.

        Args:
            tree: AST

        Returns:
            Maximale Nesting-Tiefe
        """

        def get_depth(node: ast.AST, current_depth: int = 0) -> int:
            max_depth = current_depth

            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.If, ast.While, ast.For, ast.With)):
                    child_depth = get_depth(child, current_depth + 1)
                    max_depth = max(max_depth, child_depth)
                else:
                    child_depth = get_depth(child, current_depth)
                    max_depth = max(max_depth, child_depth)

            return max_depth

        return get_depth(tree)

    def _count_functions(self, tree: ast.AST) -> int:
        """
        Zählt Funktionen im AST.

        Args:
            tree: AST

        Returns:
            Anzahl Funktionen
        """
        return sum(
            1
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )

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

        # Hohe cyclomatic Complexity
        if metrics.get("cyclomatic", 0) > self.max_complexity:
            suggestion = RefactoringSuggestion(
                id=f"complexity_{file_path.name}",
                file_path=str(file_path),
                line_start=1,
                line_end=len(lines),
                category="complexity",
                title=f"High Cyclomatic Complexity: {metrics['cyclomatic']}",
                description=(
                    f"Cyclomatic complexity von {metrics['cyclomatic']} "
                    f"überschreitet Limit von {self.max_complexity}. "
                    f"Empfehlung: In kleinere Funktionen aufteilen."
                ),
                original_code=content,
                suggested_code="# TODO: Extract methods to reduce complexity",
                confidence=0.8,
                risk_level="medium",
                estimated_impact=f"Reduziere Complexity von {metrics['cyclomatic']} auf ~{self.max_complexity}",
            )
            self._add_suggestion(suggestion)

    def get_suggestions(self) -> List[RefactoringSuggestion]:
        """
        Extrahiert alle Refactoring-Vorschläge.

        Returns:
            Liste von RefactoringSuggestions
        """
        return self._suggestions.copy()
