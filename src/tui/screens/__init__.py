"""TUI Screens."""

from .analyze import AnalyzeScreen, AnalysisProgressScreen
from .report_browser import ReportBrowserScreen, ReportViewerScreen, ConfirmDeleteScreen
from .problem_overview import ProblemOverviewScreen
from .problem_details import ProblemDetailsScreen
from .problem_intake import ProblemIntakeScreen
from .problem_diagnosis import ProblemDiagnosisScreen
from .problem_decomposition import ProblemDecompositionScreen
from .problem_solution_plan import ProblemSolutionPlanScreen
from .problem_stack_select import ProblemStackSelectScreen

__all__ = [
    "AnalyzeScreen",
    "AnalysisProgressScreen",
    "ReportBrowserScreen",
    "ReportViewerScreen",
    "ConfirmDeleteScreen",
    # Problem-Solver Screens
    "ProblemOverviewScreen",
    "ProblemDetailsScreen",
    "ProblemIntakeScreen",
    # Problem-Solver Advanced (Phase 2.5)
    "ProblemDiagnosisScreen",
    "ProblemDecompositionScreen",
    "ProblemSolutionPlanScreen",
    "ProblemStackSelectScreen",
]
