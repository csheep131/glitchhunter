"""
Fixing-Paket für GlitchHunter v3.0.

Bietet automatisches Refactoring mit:
- Code-Analyse (Complexity, Smells, Duplikate)
- Refactoring-Implementierungen
- Git-basiertem Rollback
"""

from fixing.types import RefactoringSuggestion, RefactoringResult
from fixing.auto_refactor import AutoRefactor

__all__ = [
    "RefactoringSuggestion",
    "RefactoringResult",
    "AutoRefactor",
]
