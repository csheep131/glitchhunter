"""
Type-Klassen für Auto-Refactoring.

Enthält:
- RefactoringSuggestion: Vorschlag für ein Refactoring
- RefactoringResult: Ergebnis eines Refactorings
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RefactoringSuggestion:
    """
    Vorschlag für ein Refactoring.

    Attributes:
        id: Eindeutige ID
        file_path: Betroffene Datei
        line_start: Startzeile
        line_end: Endzeile
        category: Kategorie (complexity, duplication, smell, optimization)
        title: Kurzer Titel
        description: Detaillierte Beschreibung
        original_code: Original-Code
        suggested_code: Vorgeschlagener Code
        confidence: Konfidenz (0-1)
        risk_level: Risikostufe (low, medium, high)
        estimated_impact: Geschätzte Verbesserung
        metadata: Zusätzliche Metadaten
    """

    id: str
    file_path: str
    line_start: int
    line_end: int
    category: str
    title: str
    description: str
    original_code: str
    suggested_code: str
    confidence: float = 0.5
    risk_level: str = "medium"
    estimated_impact: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Konvertiert zu Dict.

        Returns:
            Dictionary-Repräsentation der Suggestion
        """
        return {
            "id": self.id,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "original_code": self.original_code,
            "suggested_code": self.suggested_code,
            "confidence": self.confidence,
            "risk_level": self.risk_level,
            "estimated_impact": self.estimated_impact,
            "metadata": self.metadata,
        }


@dataclass
class RefactoringResult:
    """
    Ergebnis eines Refactorings.

    Attributes:
        suggestion: Ursprüngliche Suggestion
        success: Ob erfolgreich angewendet
        applied_code: Tatsächlich angewendeter Code
        git_commit: Git-Commit-Hash für Rollback
        diff: Code-Diff
        test_result: Test-Ergebnis nach Refactoring
        error: Fehlermeldung bei Misserfolg
        metadata: Zusätzliche Metadaten
    """

    suggestion: RefactoringSuggestion
    success: bool
    applied_code: Optional[str] = None
    git_commit: Optional[str] = None
    diff: Optional[str] = None
    test_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Konvertiert zu Dict.

        Returns:
            Dictionary-Repräsentation des Ergebnisses
        """
        return {
            "suggestion": self.suggestion.to_dict(),
            "success": self.success,
            "applied_code": self.applied_code,
            "git_commit": self.git_commit,
            "diff": self.diff,
            "test_result": self.test_result,
            "error": self.error,
            "metadata": self.metadata,
        }
