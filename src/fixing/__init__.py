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

from fixing.regression_test_generator import RegressionTestGenerator, TestSpec
from fixing.semantic_diff import SemanticDiffValidator, SemanticDiff, SymbolChange
from fixing.pre_apply_validator import PreApplyValidator, Gate1Result, PolicyViolation
from fixing.post_apply_verifier import PostApplyVerifier, Gate2Result, BreakingChange
from fixing.coverage_checker import CoverageChecker, CoverageMetrics, CoverageDiff, CoverageCheckResult
from fixing.rule_learner import RuleLearner, CodePattern, SemgrepRule, LearningResult, VectorRuleLearner, VectorRule
from fixing.patch_merger import PatchMerger, GitCommit, MergeResult
from fixing.report_generator import ReportGenerator, ReportBundle, BugSummary, FixDetail
from fixing.escalation_manager import EscalationManager, EscalationContext, HumanReport

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
    "VectorRuleLearner",
    "VectorRule",
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
