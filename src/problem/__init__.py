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
]
