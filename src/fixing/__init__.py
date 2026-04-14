"""
Fixing module for GlitchHunter.

Provides regression test generation, semantic diff validation,
pre-apply validation, post-apply verification, coverage checking,
rule learning, patch merging, and report generation.

Exports:
    - RegressionTestGenerator: Generates property-based tests
    - SemanticDiffValidator: Validates semantic changes
    - PreApplyValidator: Validates patches before applying (Gate 1)
    - PostApplyVerifier: Validates patches after applying (Gate 2)
    - CoverageChecker: Checks for coverage regressions
    - RuleLearner: Extracts patterns and generates Semgrep rules
    - PatchMerger: Merges patches with Git-Worktree
    - ReportGenerator: Generates JSON + Markdown reports
    - EscalationManager: Manages escalation hierarchy
"""

from .regression_test_generator import RegressionTestGenerator, TestSpec
from .semantic_diff import SemanticDiffValidator, SemanticDiff, SymbolChange
from .pre_apply_validator import PreApplyValidator, Gate1Result, PolicyViolation
from .post_apply_verifier import PostApplyVerifier, Gate2Result, BreakingChange
from .coverage_checker import CoverageChecker, CoverageMetrics, CoverageDiff, CoverageCheckResult
from .rule_learner import RuleLearner, CodePattern, SemgrepRule, LearningResult
from .patch_merger import PatchMerger, GitCommit, MergeResult
from .report_generator import ReportGenerator, ReportBundle, BugSummary, FixDetail
from .escalation_manager import EscalationManager, EscalationContext, HumanReport

__all__ = [
    # Regression Tests
    "RegressionTestGenerator",
    "TestSpec",
    # Semantic Diff
    "SemanticDiffValidator",
    "SemanticDiff",
    "SymbolChange",
    # Gate 1: Pre-Apply
    "PreApplyValidator",
    "Gate1Result",
    "PolicyViolation",
    # Gate 2: Post-Apply
    "PostApplyVerifier",
    "Gate2Result",
    "BreakingChange",
    # Coverage
    "CoverageChecker",
    "CoverageMetrics",
    "CoverageDiff",
    "CoverageCheckResult",
    # Rule Learning
    "RuleLearner",
    "CodePattern",
    "SemgrepRule",
    "LearningResult",
    # Patch Merging
    "PatchMerger",
    "GitCommit",
    "MergeResult",
    # Report Generation
    "ReportGenerator",
    "ReportBundle",
    "BugSummary",
    "FixDetail",
    # Escalation
    "EscalationManager",
    "EscalationContext",
    "HumanReport",
]
