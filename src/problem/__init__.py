"""
Problem-Solver Modul für GlitchHunter.

Paralleles Modul zum bestehenden Bug-Hunting-System.
Implementiert ProblemCase-Domänenmodell gemäß PROBLEM_SOLVER.md Phase 1.1/1.2.

Hinweis: Dieses Modul ist unabhängig von bestehenden Bug/Finding-Modellen.
"""

from .models import ProblemCase, ProblemType, ProblemSeverity, ProblemStatus
from .intake import ProblemIntake
from .classifier import ProblemClassifier, ClassificationResult
from .manager import ProblemManager
from .reports import ProblemReportGenerator
from .diagnosis import (
    Diagnosis,
    Cause,
    CauseType,
    DataFlow,
    Uncertainty,
    DiagnosisEngine,
)
from .decomposition import (
    SubProblem,
    SubProblemType,
    DependencyType,
    Decomposition,
    DecompositionEngine,
)
from .solution_path import (
    SolutionPath,
    SolutionType,
    RiskLevel,
    SolutionPlan,
    SolutionPlanner,
)
from .stack_adapter import (
    StackID,
    CapabilityLevel,
    StackCapability,
    StackProfile,
    StackAdapterManager,
    create_stack_adapter,
)
from .validation import (
    ValidationStatus,
    ValidationResult,
    GoalValidationReport,
    IntentValidationReport,
    GoalValidator,
    IntentValidator,
    create_validator,
)
from .auto_fix import (
    FixStatus,
    FixPatch,
    AutoFixResult,
    AutoFixEngine,
    create_auto_fix_engine,
)

__all__ = [
    "ProblemCase",
    "ProblemType",
    "ProblemSeverity",
    "ProblemStatus",
    "ProblemIntake",
    "ProblemClassifier",
    "ClassificationResult",
    "ProblemManager",
    "ProblemReportGenerator",
    "Diagnosis",
    "Cause",
    "CauseType",
    "DataFlow",
    "Uncertainty",
    "DiagnosisEngine",
    # Decomposition
    "SubProblem",
    "SubProblemType",
    "DependencyType",
    "Decomposition",
    "DecompositionEngine",
    # Solution Path Planning
    "SolutionPath",
    "SolutionType",
    "RiskLevel",
    "SolutionPlan",
    "SolutionPlanner",
    # Stack Adapter
    "StackID",
    "CapabilityLevel",
    "StackCapability",
    "StackProfile",
    "StackAdapterManager",
    "create_stack_adapter",
    # Validation
    "ValidationStatus",
    "ValidationResult",
    "GoalValidationReport",
    "IntentValidationReport",
    "GoalValidator",
    "IntentValidator",
    "create_validator",
    # Auto-Fix
    "FixStatus",
    "FixPatch",
    "AutoFixResult",
    "AutoFixEngine",
    "create_auto_fix_engine",
]
