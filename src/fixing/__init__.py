"""
Fixing module for GlitchHunter.

Provides regression test generation, semantic diff validation,
and pre-apply validation for patches.

Exports:
    - RegressionTestGenerator: Generates property-based tests
    - SemanticDiffValidator: Validates semantic changes
    - PreApplyValidator: Validates patches before applying
"""

from .regression_test_generator import RegressionTestGenerator, TestSpec
from .semantic_diff import SemanticDiffValidator, SemanticDiff, SymbolChange
from .escalation_manager import EscalationManager, EscalationContext, HumanReport

__all__ = [
    "RegressionTestGenerator",
    "TestSpec",
    "SemanticDiffValidator",
    "SemanticDiff",
    "SymbolChange",
    "EscalationManager",
    "EscalationContext",
    "HumanReport",
]
