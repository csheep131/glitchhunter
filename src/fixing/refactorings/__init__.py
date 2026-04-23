"""
Refactoring-Module für Auto-Refactoring.

Enthält Refactoring-Implementierungen für:
- Extract Method
- Remove Duplicate
- Replace Magic Number
- Simplify Condition
"""

from fixing.refactorings.base import BaseRefactoring
from fixing.refactorings.extract_method import ExtractMethodRefactoring
from fixing.refactorings.remove_duplicate import RemoveDuplicateRefactoring
from fixing.refactorings.replace_magic_number import ReplaceMagicNumberRefactoring
from fixing.refactorings.simplify_condition import SimplifyConditionRefactoring

__all__ = [
    "BaseRefactoring",
    "ExtractMethodRefactoring",
    "RemoveDuplicateRefactoring",
    "ReplaceMagicNumberRefactoring",
    "SimplifyConditionRefactoring",
]
