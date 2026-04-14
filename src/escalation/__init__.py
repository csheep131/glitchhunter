"""
Escalation module for GlitchHunter.

Provides 4-level escalation hierarchy:
1. Context Explosion: Gather more context (160k tokens)
2. Bug Decomposition: Split into 2-4 sub-bugs
3. Multi-Model Ensemble: Parallel analysis with voting
4. Human-in-the-Loop: Generate detailed report

Exports:
    - ContextExplosion: Level 1 implementation
    - BugDecomposer: Level 2 implementation
    - EnsembleCoordinator: Level 3 implementation
    - HumanReportGenerator: Level 4 implementation
"""

from .context_explosion import ContextExplosion, ExplodedContext
from .bug_decomposer import BugDecomposer, DecomposedBug, DecompositionResult
from .ensemble_coordinator import EnsembleCoordinator, EnsembleResult, ModelResponse
from .human_report_generator import HumanReportGenerator, HumanReport

__all__ = [
    # Level 1
    "ContextExplosion",
    "ExplodedContext",
    # Level 2
    "BugDecomposer",
    "DecomposedBug",
    "DecompositionResult",
    # Level 3
    "EnsembleCoordinator",
    "EnsembleResult",
    "ModelResponse",
    # Level 4
    "HumanReportGenerator",
    "HumanReport",
]
