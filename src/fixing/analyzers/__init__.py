"""
Analyzer-Module für Code-Analyse.

Enthält Analyzer für:
- Complexity-Metriken
- Code-Smells
- Duplikate
"""

from fixing.analyzers.base import BaseAnalyzer
from fixing.analyzers.complexity_analyzer import ComplexityAnalyzer
from fixing.analyzers.smell_analyzer import SmellAnalyzer
from fixing.analyzers.duplicate_analyzer import DuplicateAnalyzer

__all__ = [
    "BaseAnalyzer",
    "ComplexityAnalyzer",
    "SmellAnalyzer",
    "DuplicateAnalyzer",
]
