# Regression-Proof Patch Loop

**Version:** 2.0  
**Date:** April 13, 2026  
**Status:** Architecture Specification  
**Single Source of Truth:** [STATE_MACHINE_STATUS.md](STATE_MACHINE_STATUS.md) für Implementierungs-Status

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Fail2Pass Principle](#2-fail2pass-principle)
3. [Safety Gates 1-4](#3-safety-gates-1-4)
4. [Test Generation Strategies](#4-test-generation-strategies)
5. [Semantic Diff Algorithm](#5-semantic-diff-algorithm)
6. [Graph Comparison](#6-graph-comparison)
7. [Configuration Reference](#7-configuration-reference)

---

## 1. Architecture Overview

### 1.1 High-Level Architecture

The Regression-Proof Patch Loop is a **test-driven, evidence-based** approach to automated bug fixing that guarantees no new bugs are introduced during the fixing process. Unlike traditional patch loops that simply generate and apply patches, our system implements four safety gates that must all pass before a patch is accepted.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    REGRESSION-PROOF PATCH LOOP                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Input: Prioritized Bug Candidates (from Phase 2)                           │
│          │                                                                   │
│          ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  3.1 REGRESSION TEST GENERATION (Fail2Pass Principle)                │   │
│  │  ┌──────────────────────────────────────────────────────────────┐    │   │
│  │  │ • Analyzer generates property-based tests for exact bug      │    │   │
│  │  │ • 3-5 edge-case tests from Data-Flow Graph                   │    │   │
│  │  │ • Tests MUST fail BEFORE patch (Fail2Pass)                   │    │   │
│  │  │ • Languages: Python (hypothesis), Rust (proptest), JS (jest) │    │   │
│  │  └──────────────────────────────────────────────────────────────┘    │   │
│  │          │                                                            │   │
│  │          ▼ Fail2Pass Check                                            │   │
│  │  ┌──────────────────────────────────────────────────────────────┐    │   │
│  │  │  IF tests pass BEFORE patch → INVALID TESTS → Retry          │    │   │
│  │  │  IF tests fail BEFORE patch → CONTINUE to Gate 1             │    │   │
│  │  └──────────────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│          │                                                                   │
│          ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  SAFETY GATE 1: PRE-APPLY VALIDATION                                 │   │
│  │  ┌──────────────────────────────────────────────────────────────┐    │   │
│  │  │ • Syntax Check + Linter + Static Analysis                    │    │   │
│  │  │ • Semantic Diff (Tree-sitter-based):                         │    │   │
│  │  │   - Shows exact variable/call/data-flow changes              │    │   │
│  │  │   - Detects unintended side effects                          │    │   │
│  │  │ • Policy Check:                                                │    │   │
│  │  │   - Max 3 files touched                                        │    │   │
│  │  │   - Max 160 lines changed                                      │    │   │
│  │  │   - No new dependencies                                        │    │   │
│  │  └──────────────────────────────────────────────────────────────┘    │   │
│  │          │                                                            │   │
│  │          ▼ Gate 1 Result                                              │   │
│  │  ┌──────────────────────────────────────────────────────────────┐    │   │
│  │  │  IF FAIL → Discard patch immediately, no apply               │    │   │
│  │  │  IF PASS → Continue to Atomic Apply                          │    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│          │                                                                   │
│          ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  3.3 ATOMIC APPLY IN SANDBOX (git-worktree + Docker)                 │   │
│  │  ┌──────────────────────────────────────────────────────────────┐    │   │
│  │  │ • Patch applied on separate git worktree only                │    │   │
│  │  │ • Full test suite execution:                                 │    │   │
│  │  │   - All existing tests                                       │    │   │
│  │  │   - New regression tests (from 3.1)                          │    │   │
│  │  │   - Security tests (BOLA, Injection, etc. from Phase 2)      │    │   │
│  │  │ • Coverage check: Patch must not reduce coverage             │    │   │
│  │  │ • Network disabled, timeout 60s                              │    │   │
│  │  └──────────────────────────────────────────────────────────────┘    │   │
│  │          │                                                            │   │
│  │          ▼ Test Results                                               │   │
│  │  ┌──────────────────────────────────────────────────────────────┐    │   │
│  │  │  IF ANY TEST FAILS → Reject patch, rollback worktree         │    │   │
│  │  │  IF ALL TESTS PASS → Continue to Gate 2                      │    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│          │                                                                   │
│          ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  SAFETY GATE 2: POST-APPLY VERIFIER + GRAPH COMPARISON               │   │
│  │  ┌──────────────────────────────────────────────────────────────┐    │   │
│  │  │ • Verifier receives:                                         │    │   │
│  │  │   - Original code + Patch                                    │    │   │
│  │  │   - Before/After Data-Flow Graph                             │    │   │
│  │  │   - Before/After Call Graph                                  │    │   │
│  │  │   - All test outputs                                         │    │   │
│  │  │ • Prompt: "Has this patch introduced new bugs?               │    │   │
│  │  │   Show concrete evidence in graph or tests."                 │    │   │
│  │  │ • Additional: Small "Regression-Agent" (Phi-4-mini)          │    │   │
│  │  │   checks only for "breaking changes"                         │    │   │
│  │  └──────────────────────────────────────────────────────────────┘    │   │
│  │          │                                                            │   │
│  │          ▼ Gate 2 Result                                              │   │
│  │  ┌──────────────────────────────────────────────────────────────┐    │   │
│  │  │  IF verifier_confidence < 95% "no new bugs" → Reject         │    │   │
│  │  │  IF verifier_confidence >= 95% → Continue to Accept          │    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│          │                                                                   │
│          ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  3.5 ACCEPT / RETRY / ESCALATE                                       │   │
│  │  ┌──────────────────────────────────────────────────────────────┐    │   │
│  │  │  ACCEPT (ALL conditions must be true):                       │    │   │
│  │  │  ✓ All tests passed (including regression tests)             │    │   │
│  │  │  ✓ No coverage regression                                    │    │   │
│  │  │  ✓ Static score non-regressive                               │    │   │
│  │  │  ✓ Semantic diff shows no unexpected side effects            │    │   │
│  │  │  ✓ Verifier confidence >= 95% "no new bugs"                  │    │   │
│  │  │                                                               │    │   │
│  │  │  RETRY:                                                      │    │   │
│  │  │  • Loop restarts with smaller scope (more minimal patch)     │    │   │
│  │  │  • Max 5 iterations                                          │    │   │
│  │  │                                                               │    │   │
│  │  │  ESCALATE (after 2× no progress):                            │    │   │
│  │  │  • Full report: "Fix not possible without major refactoring" │    │   │
│  │  │  • Escalation-First Fixing (see Section 3.6)                 │    │   │
│  │  └──────────────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Output: AcceptedPatch | EscalationReport                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Interaction

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COMPONENT INTERACTION                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐      │
│  │ RegressionTest  │─────▶│ SemanticDiff    │─────▶│ SandboxExecutor │      │
│  │ Generator       │      │ Engine          │      │                 │      │
│  └─────────────────┘      └─────────────────┘      └────────┬────────┘      │
│         │                      │                            │               │
│         │                      │                            │               │
│         ▼                      ▼                            ▼               │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐      │
│  │ Fail2Pass       │      │ Gate1Result     │      │ TestResults     │      │
│  │ Validator       │      │ (Pass/Fail)     │      │ (Pass/Fail)     │      │
│  └─────────────────┘      └─────────────────┘      └────────┬────────┘      │
│                                                              │               │
│                                                              ▼               │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐      │
│  │ Escalation      │◀─────│ Gate2Result     │◀─────│ GraphComparator │      │
│  │ Manager         │      │ (Pass/Fail)     │      │                 │      │
│  └─────────────────┘      └─────────────────┘      └─────────────────┘      │
│                                                                              │
│  Data Flow:                                                                  │
│  ──────────                                                                  │
│  1. RegressionTestGenerator creates tests from DFG                          │
│  2. Fail2PassValidator ensures tests fail on original code                  │
│  3. SemanticDiffEngine analyzes patch impact                                │
│  4. Gate1Result determines if patch proceeds                                │
│  5. SandboxExecutor runs tests in isolation                                 │
│  6. TestResults determine if tests pass                                     │
│  7. GraphComparator compares before/after graphs                            │
│  8. Gate2Result determines final acceptance                                 │
│  9. EscalationManager handles failures                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 State Transitions

```python
# src/fixing/patch_loop_state.py

from typing import TypedDict, List, Optional, Literal
from typing_extensions import NotRequired


class PatchLoopState(TypedDict):
    """State machine state for regression-proof patch loop."""

    # Input
    candidate: dict
    original_code: str
    data_flow_graph: dict
    control_flow_graph: dict

    # Phase 3.1: Regression Test Generation
    regression_tests: NotRequired[List[dict]]
    fail2pass_validated: NotRequired[bool]

    # Gate 1: Pre-Apply Validation
    gate1_passed: NotRequired[bool]
    gate1_result: NotRequired[dict]

    # Phase 3.3: Atomic Apply
    patch_applied: NotRequired[bool]
    test_results: NotRequired[List[dict]]
    coverage_delta: NotRequired[float]

    # Gate 2: Post-Apply Verifier
    gate2_passed: NotRequired[bool]
    gate2_result: NotRequired[dict]
    verifier_confidence: NotRequired[float]

    # Decision
    iteration_count: int
    decision: NotRequired[Literal["accept", "retry", "escalate"]]
    accepted_patch: NotRequired[dict]
```

---

## 2. Fail2Pass Principle

### 2.1 Core Concept

**Fail2Pass** ensures that regression tests are **valid and meaningful** by requiring them to fail on the original (buggy) code before any patch is applied.

```
┌──────────────────────────────────────────────────────────────┐
│                 FAIL2PASS WORKFLOW                            │
│                                                               │
│  Step 1: Generate Tests                                      │
│          ↓                                                    │
│  Step 2: Run Tests on ORIGINAL Code                          │
│          ↓                                                    │
│  Step 3: Check Results                                       │
│          ├─→ ALL TESTS PASS → INVALID TESTS → Regenerate    │
│          └─→ SOME TESTS FAIL → VALID TESTS → Continue       │
│                                                               │
│  Rationale: If tests pass on buggy code, they don't test    │
│             the actual bug and are useless for regression.   │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 Why Fail2Pass?

Traditional automated fixing systems generate tests that may:

1. **Test irrelevant properties** - Tests pass regardless of bug presence
2. **Miss the actual bug** - Tests don't exercise the buggy code path
3. **Have wrong expectations** - Tests expect wrong behavior as normal

Fail2Pass solves this by inverting the validation:

| Traditional Approach | Fail2Pass Approach |
|---------------------|-------------------|
| Generate tests | Generate tests |
| Apply patch | **Run tests on ORIGINAL code** |
| Run tests | **Verify tests FAIL** |
| Verify tests pass | Apply patch |
| | Run tests |
| | Verify tests PASS |

### 2.3 Implementation

```python
# src/fixing/regression_test_generator.py

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import networkx as nx


class TestFramework(Enum):
    HYPOTHESIS = "hypothesis"  # Python
    PROPTESt = "proptest"      # Rust
    JEST = "jest"              # JavaScript
    FAST_CHECK = "fast-check"  # TypeScript


@dataclass
class RegressionTest:
    """Represents a single regression test."""
    id: str
    framework: TestFramework
    code: str
    description: str
    edge_case_type: str
    expected_failure_on_original: bool
    actual_failure_on_original: Optional[bool] = None


class RegressionTestGenerator:
    """Generates property-based tests from Data-Flow Graph analysis."""

    def __init__(
        self,
        data_flow_graph: nx.DiGraph,
        control_flow_graph: nx.DiGraph,
        bug_location: Dict[str, Any],
        language: str
    ):
        self.dfg = data_flow_graph
        self.cfg = control_flow_graph
        self.bug_location = bug_location
        self.language = language
        self.tests: List[RegressionTest] = []

    def generate_tests(self) -> List[RegressionTest]:
        """Generates 3-5 edge-case tests from DFG analysis."""
        self.tests = []

        # 1. Null/None Flow Test
        null_path = self._find_null_flow_path()
        if null_path:
            test = self._create_null_test(null_path)
            self.tests.append(test)

        # 2. Negative Value Test
        neg_path = self._find_negative_value_path()
        if neg_path:
            test = self._create_negative_test(neg_path)
            self.tests.append(test)

        # 3. Race Condition Test (if concurrent access detected)
        if self._detect_concurrent_access():
            test = self._create_race_condition_test()
            self.tests.append(test)

        # 4. Boundary Value Test
        boundary_path = self._find_boundary_path()
        if boundary_path:
            test = self._create_boundary_test(boundary_path)
            self.tests.append(test)

        # 5. Type Mismatch Test
        type_path = self._find_type_mismatch_path()
        if type_path:
            test = self._create_type_mismatch_test(type_path)
            self.tests.append(test)

        return self.tests[:5]  # Max 5 tests

    def validate_fail2pass(
        self,
        tests: List[RegressionTest],
        original_code: str,
        test_runner: Any
    ) -> Tuple[bool, List[RegressionTest]]:
        """
        Validates that tests fail on original (buggy) code.

        Returns:
            Tuple of (is_valid, failing_tests)
            - is_valid: True if at least one test fails
            - failing_tests: List of tests that failed on original code
        """
        failing_tests = []

        for test in tests:
            result = test_runner.execute(test.code, original_code)

            if not result.passed:
                test.actual_failure_on_original = True
                failing_tests.append(test)
            else:
                test.actual_failure_on_original = False

        # At least one test must fail for Fail2Pass validation
        is_valid = len(failing_tests) > 0

        return is_valid, failing_tests

    def _find_null_flow_path(self) -> Optional[List[str]]:
        """Finds data flow paths where null/None could propagate."""
        # Look for variable definitions without initialization
        for node in self.dfg.nodes():
            if self.dfg.nodes[node].get("type") == "variable_definition":
                if not self.dfg.nodes[node].get("initialized", True):
                    # Trace where this variable flows
                    path = self._trace_variable_flow(node)
                    if path:
                        return path
        return None

    def _find_negative_value_path(self) -> Optional[List[str]]:
        """Finds paths where negative values could cause issues."""
        # Look for numeric operations without bounds checking
        for node in self.dfg.nodes():
            if self.dfg.nodes[node].get("operation") in ["subtract", "multiply", "divide"]:
                if not self._has_bounds_check(node):
                    return self._trace_to_sink(node)
        return None

    def _detect_concurrent_access(self) -> bool:
        """Detects potential concurrent access patterns."""
        # Look for shared state without synchronization
        for node in self.dfg.nodes():
            if self.dfg.nodes[node].get("access_type") == "write":
                if not self.dfg.nodes[node].get("synchronized", True):
                    # Check if multiple threads could access
                    if self._has_multiple_callers(node):
                        return True
        return False

    def _find_boundary_path(self) -> Optional[List[str]]:
        """Finds boundary value test cases."""
        # Look for array/list operations
        for node in self.dfg.nodes():
            if self.dfg.nodes[node].get("operation") in ["index", "slice"]:
                if not self._has_bounds_check(node):
                    return self._trace_to_sink(node)
        return None

    def _find_type_mismatch_path(self) -> Optional[List[str]]:
        """Finds potential type mismatch scenarios."""
        # Look for dynamic type operations
        for node in self.dfg.nodes():
            if self.dfg.nodes[node].get("type") == "function_call":
                if not self.dfg.nodes[node].get("type_checked", True):
                    return self._trace_return_value(node)
        return None

    def _create_null_test(self, path: List[str]) -> RegressionTest:
        """Creates a null injection test."""
        if self.language == "python":
            return RegressionTest(
                id=f"null_test_{len(self.tests)}",
                framework=TestFramework.HYPOTHESIS,
                code=self._generate_python_null_test(path),
                description="Tests handling of None values in data flow",
                edge_case_type="null_injection",
                expected_failure_on_original=True
            )
        elif self.language == "rust":
            return RegressionTest(
                id=f"null_test_{len(self.tests)}",
                framework=TestFramework.PROPTES,
                code=self._generate_rust_option_test(path),
                description="Tests handling of None/Option in data flow",
                edge_case_type="null_injection",
                expected_failure_on_original=True
            )
        else:
            return RegressionTest(
                id=f"null_test_{len(self.tests)}",
                framework=TestFramework.FAST_CHECK,
                code=self._generate_ts_null_test(path),
                description="Tests handling of null/undefined in data flow",
                edge_case_type="null_injection",
                expected_failure_on_original=True
            )

    def _create_negative_test(self, path: List[str]) -> RegressionTest:
        """Creates a negative value test."""
        # Similar pattern for negative values
        pass

    def _create_race_condition_test(self) -> RegressionTest:
        """Creates a concurrent access test."""
        pass

    def _create_boundary_test(self, path: List[str]) -> RegressionTest:
        """Creates a boundary value test."""
        pass

    def _create_type_mismatch_test(self, path: List[str]) -> RegressionTest:
        """Creates a type mismatch test."""
        pass
```

---

## 3. Safety Gates 1-4

### 3.1 Gate 1: Pre-Apply Validation

**Purpose:** Catch invalid patches before they touch the codebase.

```
┌──────────────────────────────────────────────────────────────┐
│              PRE-APPLY VALIDATION GATE                        │
│                                                               │
│  Input: Proposed Patch (.diff format)                         │
│          │                                                    │
│          ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  1. Syntax Check                                     │    │
│  │      • Parse patch with Tree-sitter                  │    │
│  │      • Verify all modified files are syntactically   │    │
│  │        valid for their language                      │    │
│  └──────────────────────────────────────────────────────┘    │
│          │ PASS → Continue                                    │
│          ▼ FAIL → Reject                                      │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  2. Linter Check                                     │    │
│  │      • Run language-specific linter                  │    │
│  │      • Check for style violations, unused imports    │    │
│  └──────────────────────────────────────────────────────┘    │
│          │ PASS → Continue                                    │
│          ▼ FAIL → Reject                                      │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  3. Static Analysis                                  │    │
│  │      • Run static analyzer (Semgrep, mypy, etc.)     │    │
│  │      • Check for new warnings introduced by patch    │    │
│  └──────────────────────────────────────────────────────┘    │
│          │ PASS → Continue                                    │
│          ▼ FAIL → Reject                                      │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  4. Semantic Diff (Tree-sitter-based)                │    │
│  │      • Compare AST before and after patch            │    │
│  │      • Show exact variables/calls/data-flows changed │    │
│  │      • Detect unintended side effects                │    │
│  └──────────────────────────────────────────────────────┘    │
│          │ PASS → Continue                                    │
│          ▼ FAIL → Reject                                      │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  5. Policy Check                                     │    │
│  │      • Max 3 files touched                           │    │
│  │      • Max 160 lines changed                         │    │
│  │      • No new dependencies added                     │    │
│  └──────────────────────────────────────────────────────┘    │
│          │                                                    │
│          ▼                                                    │
│  Output: Gate1Result {                                        │
│    passed: bool,                                              │
│    static_score_before: float,                                │
│    static_score_after: float,                                 │
│    semantic_diff: SemanticDiff,                               │
│    policy_violations: List[str]                               │
│  }                                                            │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Gate 1 Implementation

```python
# src/fixing/gate1_pre_apply.py

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import subprocess


@dataclass
class Gate1Result:
    """Result of Pre-Apply Validation Gate."""
    passed: bool
    syntax_valid: bool
    linter_valid: bool
    static_analysis_valid: bool
    semantic_diff_clean: bool
    policy_compliant: bool

    static_score_before: float
    static_score_after: float

    semantic_diff: Optional[Dict]
    policy_violations: List[str]

    errors: List[str]


class Gate1PreApplyValidator:
    """Validates patches before application."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_files = config.get("patch_policy", {}).get("max_files_touched", 3)
        self.max_lines = config.get("patch_policy", {}).get("max_changed_lines", 160)

    async def validate(self, patch: str, original_code: Dict[str, str]) -> Gate1Result:
        """Validates a patch against all Gate 1 criteria."""
        errors = []
        policy_violations = []

        # 1. Parse patch
        parsed_patch = self._parse_patch(patch)

        # 2. Policy check
        policy_compliant, policy_violations = self._check_policy(
            parsed_patch,
            self.max_files,
            self.max_lines
        )
        if not policy_compliant:
            errors.extend(policy_violations)

        # 3. Syntax check for each modified file
        syntax_valid = True
        for file_path, new_code in parsed_patch.modified_files.items():
            if not self._check_syntax(file_path, new_code):
                syntax_valid = False
                errors.append(f"Syntax error in {file_path}")

        # 4. Linter check
        linter_valid = True
        for file_path, new_code in parsed_patch.modified_files.items():
            if not await self._run_linter(file_path, new_code):
                linter_valid = False
                errors.append(f"Linter violations in {file_path}")

        # 5. Static analysis
        static_score_before = self._compute_static_score(original_code)
        static_score_after = self._compute_static_score(parsed_patch.new_code)
        static_analysis_valid = static_score_after >= static_score_before

        if not static_analysis_valid:
            errors.append(
                f"Static score regressed: {static_score_before:.2f} → {static_score_after:.2f}"
            )

        # 6. Semantic diff
        semantic_diff = self._compute_semantic_diff(original_code, parsed_patch)
        semantic_diff_clean = len(semantic_diff.get("side_effects", [])) == 0

        if not semantic_diff_clean:
            errors.extend([
                f"Side effect: {se['description']}"
                for se in semantic_diff.get("side_effects", [])
            ])

        # Final result
        passed = (
            syntax_valid and
            linter_valid and
            static_analysis_valid and
            semantic_diff_clean and
            policy_compliant
        )

        return Gate1Result(
            passed=passed,
            syntax_valid=syntax_valid,
            linter_valid=linter_valid,
            static_analysis_valid=static_analysis_valid,
            semantic_diff_clean=semantic_diff_clean,
            policy_compliant=policy_compliant,
            static_score_before=static_score_before,
            static_score_after=static_score_after,
            semantic_diff=semantic_diff,
            policy_violations=policy_violations,
            errors=errors
        )

    def _parse_patch(self, patch: str) -> ParsedPatch:
        """Parses a .diff format patch."""
        # Implementation using difflib or custom parser
        pass

    def _check_policy(
        self,
        patch: Any,
        max_files: int,
        max_lines: int
    ) -> tuple[bool, List[str]]:
        """Checks patch against policy constraints."""
        violations = []

        if len(patch.modified_files) > max_files:
            violations.append(
                f"Too many files touched: {len(patch.modified_files)} > {max_files}"
            )

        if patch.total_lines_changed > max_lines:
            violations.append(
                f"Too many lines changed: {patch.total_lines_changed} > {max_lines}"
            )

        if patch.new_dependencies:
            violations.append(
                f"New dependencies not allowed: {patch.new_dependencies}"
            )

        return len(violations) == 0, violations

    def _check_syntax(self, file_path: str, code: str) -> bool:
        """Checks syntax validity for a file."""
        language = self._detect_language(file_path)

        if language == "python":
            try:
                compile(code, file_path, 'exec')
                return True
            except SyntaxError:
                return False

        elif language in ["javascript", "typescript"]:
            # Use acorn or typescript compiler
            pass

        elif language == "rust":
            # Use rustc --emit=metadata
            pass

        return True

    async def _run_linter(self, file_path: str, code: str) -> bool:
        """Runs language-specific linter."""
        language = self._detect_language(file_path)

        if language == "python":
            result = await self._run_ruff(code)
            return result.returncode == 0

        elif language in ["javascript", "typescript"]:
            result = await self._run_eslint(code)
            return result.returncode == 0

        elif language == "rust":
            result = await self._run_clippy(code)
            return result.returncode == 0

        return True

    def _compute_static_score(self, code: Dict[str, str]) -> float:
        """Computes static analysis score."""
        # Run Semgrep and compute score based on findings
        pass

    def _compute_semantic_diff(
        self,
        original_code: Dict[str, str],
        patch: Any
    ) -> Dict:
        """Computes semantic diff using Tree-sitter."""
        from .semantic_diff import SemanticDiffEngine
        engine = SemanticDiffEngine()
        return engine.compute_diff(original_code, patch)
```

### 3.3 Gate 2: Post-Apply Verifier + Graph Comparison

**Purpose:** Detect new bugs introduced by the patch using graph comparison.

```
┌──────────────────────────────────────────────────────────────┐
│           POST-APPLY VERIFIER + GRAPH COMPARISON              │
│                                                               │
│  Input:                                                       │
│    • Original code + Patch                                   │
│    • Before/After Data-Flow Graph                            │
│    • Before/After Call Graph                                 │
│    • All test outputs                                        │
│          │                                                    │
│          ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  1. Graph Comparison                                 │    │
│  │      • Compare DFG before/after                      │    │
│  │      • Compare Call Graph before/after               │    │
│  │      • Detect new data flows (potential bugs)        │    │
│  │      • Detect removed flows (broken functionality)   │    │
│  └──────────────────────────────────────────────────────┘    │
│          │                                                    │
│          ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  2. Breaking Change Detection                        │    │
│  │      • Removed public API                            │    │
│  │      • Signature changes                             │    │
│  │      • Behavior changes                              │    │
│  └──────────────────────────────────────────────────────┘    │
│          │                                                    │
│          ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  3. Verifier LLM Evaluation                          │    │
│  │      • Prompt: "Has this patch introduced new bugs?  │    │
│  │        Show concrete evidence in graph or tests."    │    │
│  │      • Temperature: 0.0 (deterministic)              │    │
│  │      • Output: confidence score + reasoning          │    │
│  └──────────────────────────────────────────────────────┘    │
│          │                                                    │
│          ▼                                                    │
│  Output: Gate2Result {                                        │
│    passed: bool,                                              │
│    verifier_confidence: float,                                │
│    breaking_changes: List[str],                               │
│    graph_changes: GraphComparison                             │
│  }                                                            │
└──────────────────────────────────────────────────────────────┘
```

### 3.4 Gate 2 Implementation

```python
# src/fixing/gate2_post_apply.py

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import networkx as nx


@dataclass
class Gate2Result:
    """Result of Post-Apply Verifier Gate."""
    passed: bool
    verifier_confidence: float
    verifier_reasoning: str

    breaking_changes: List[str]
    graph_changes: Dict

    test_failures: List[str]


class Gate2PostApplyVerifier:
    """Verifies patches after application."""

    def __init__(self, config: Dict[str, Any], llm_client: Any):
        self.config = config
        self.llm = llm_client
        self.confidence_threshold = config.get(
            "fixing_policy", {}
        ).get("verifier_confidence_threshold", 0.95)

    async def verify(
        self,
        original_code: Dict[str, str],
        patched_code: Dict[str, str],
        original_dfg: nx.DiGraph,
        patched_dfg: nx.DiGraph,
        original_cg: nx.DiGraph,
        patched_cg: nx.DiGraph,
        test_results: List[Dict]
    ) -> Gate2Result:
        """Verifies a patch after application."""

        # 1. Graph comparison
        graph_comparator = GraphComparator(
            original_dfg, patched_dfg,
            original_cg, patched_cg
        )
        graph_changes = graph_comparator.compare()

        # 2. Breaking change detection
        breaking_changes = self._detect_breaking_changes(
            original_cg, patched_cg
        )

        # 3. Test failure analysis
        test_failures = [
            f"Test {r['test_id']}: {r['output']}"
            for r in test_results
            if not r['passed']
        ]

        # 4. LLM verification
        verifier_prompt = self._build_verifier_prompt(
            original_code,
            patched_code,
            graph_changes,
            breaking_changes,
            test_results
        )

        verifier_response = await self.llm.generate(
            prompt=verifier_prompt,
            max_tokens=2000,
            temperature=0.0  # Deterministic
        )

        # Parse response
        confidence = self._parse_confidence(verifier_response)
        reasoning = self._parse_reasoning(verifier_response)

        # Final decision
        passed = (
            confidence >= self.confidence_threshold and
            len(breaking_changes) == 0 and
            len(test_failures) == 0
        )

        return Gate2Result(
            passed=passed,
            verifier_confidence=confidence,
            verifier_reasoning=reasoning,
            breaking_changes=breaking_changes,
            graph_changes=graph_changes,
            test_failures=test_failures
        )

    def _build_verifier_prompt(
        self,
        original_code: Dict[str, str],
        patched_code: Dict[str, str],
        graph_changes: Dict,
        breaking_changes: List[str],
        test_results: List[Dict]
    ) -> str:
        """Builds the verifier LLM prompt."""
        return f"""
# Patch Verification Task

You are a code verification expert. Your task is to determine if this patch
has introduced any new bugs or regressions.

## Original Code
```
{self._format_code(original_code)}
```

## Patched Code
```
{self._format_code(patched_code)}
```

## Graph Changes

### Data-Flow Graph Changes
{self._format_graph_changes(graph_changes['dfg'])}

### Call Graph Changes
{self._format_graph_changes(graph_changes['cg'])}

## Breaking Changes Detected
{self._format_list(breaking_changes) if breaking_changes else "None"}

## Test Results
{self._format_test_results(test_results)}

## Task

Analyze the above information and answer:

**"Has this patch introduced any new bugs or regressions?"**

Provide:
1. **Confidence Score** (0.0 to 1.0): How confident are you that no new
   bugs were introduced?
2. **Reasoning**: Concrete evidence from the code, graphs, or tests that
   supports your conclusion.

Be extremely conservative. If you see ANY evidence of potential bugs,
report it and lower your confidence score.

## Response Format

Confidence: <float 0.0-1.0>
Reasoning: <your detailed analysis>
"""

    def _detect_breaking_changes(
        self,
        original_cg: nx.DiGraph,
        patched_cg: nx.DiGraph
    ) -> List[str]:
        """Detects breaking changes in call graph."""
        breaking = []

        # Check for removed public functions
        original_funcs = set(original_cg.nodes())
        patched_funcs = set(patched_cg.nodes())

        removed_funcs = original_funcs - patched_funcs
        for func in removed_funcs:
            if self._is_public_function(original_cg, func):
                breaking.append(f"Removed public function: {func}")

        # Check for signature changes
        for func in original_funcs & patched_funcs:
            old_sig = self._get_function_signature(original_cg, func)
            new_sig = self._get_function_signature(patched_cg, func)

            if old_sig != new_sig:
                breaking.append(
                    f"Signature changed for {func}: {old_sig} → {new_sig}"
                )

        return breaking

    def _parse_confidence(self, response: str) -> float:
        """Parses confidence score from LLM response."""
        # Extract "Confidence: 0.95" from response
        import re
        match = re.search(r'Confidence:\s*([\d.]+)', response)
        if match:
            return float(match.group(1))
        return 0.0

    def _parse_reasoning(self, response: str) -> str:
        """Parses reasoning from LLM response."""
        import re
        match = re.search(r'Reasoning:\s*(.+)', response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return response
```

---

## 4. Test Generation Strategies (Language-Specific)

### 4.1 Python (hypothesis)

```yaml
# config.yaml
regression_testing:
  python:
    framework: "hypothesis"
    max_examples: 50
    deadline: 500  # ms
    suppress_health_check: ["data_too_large"]
    strategies:
      - "null_injection"
      - "negative_values"
      - "boundary_values"
      - "type_mismatch"
      - "race_condition"
```

```python
# Example: Property-based test for SQL Injection bug
from hypothesis import given, strategies as st
import pytest

class TestSQLInjection:
    """Regression tests for SQL injection vulnerability."""

    @given(user_input=st.text().filter(lambda x: "'" in x or '"' in x))
    def test_user_input_sanitized(self, user_input):
        """Test that user input is properly sanitized."""
        # This test MUST fail on the original buggy code
        query = build_query(user_input)

        # Property: No SQL keywords should appear after sanitization
        assert "SELECT" not in query or user_input not in query
        assert "DROP" not in query
        assert "DELETE" not in query

    @given(value=st.integers().filter(lambda x: x < 0))
    def test_negative_id_handling(self, value):
        """Test handling of negative ID values."""
        # Property: Negative IDs should be rejected
        result = get_user_by_id(value)
        assert result is None or result.is_valid
```

### 4.2 Rust (proptest)

```yaml
# config.yaml
regression_testing:
  rust:
    framework: "proptest"
    cases: 256
    max_local_rejects: 1024
    max_global_rejects: 1024
    fork: true
    strategies:
      - "overflow"
      - "underflow"
      - "bounds_check"
      - "concurrent_access"
```

```rust
// Example: Property-based test for buffer overflow
use proptest::prelude::*;

proptest! {
    #[test]
    fn test_buffer_bounds_check(input in prop::string::string_regex(".*").unwrap()) {
        // This test MUST fail on the original buggy code
        let result = process_input(&input);

        // Property: No out-of-bounds access
        prop_assert!(result.is_ok());
        prop_assert!(result.unwrap().len() <= input.len());
    }

    #[test]
    fn test_integer_overflow(a in 0i32.., b in 0i32..) {
        // Property: No overflow in multiplication
        if let Some(product) = a.checked_mul(b) {
            let result = compute_area(a, b);
            prop_assert_eq!(result, product);
        }
    }
}
```

### 4.3 JavaScript (Jest + fast-check)

```yaml
# config.yaml
regression_testing:
  javascript:
    framework: "jest + fast-check"
    numRuns: 100
    interruptAfter: 10000  # ms
    maxSkips: 1000
    strategies:
      - "xss_injection"
      - "null_undefined"
      - "type_confusion"
      - "async_race"
```

```javascript
// Example: Property-based test for XSS vulnerability
import fc from 'fast-check';

describe('XSS Prevention', () => {
  it('should sanitize user input containing script tags', () => {
    fc.assert(
      fc.property(
        fc.string().filter(s => s.includes('<script>')),
        (maliciousInput) => {
          // This test MUST fail on the original buggy code
          const sanitized = sanitizeInput(maliciousInput);

          // Property: No script tags in output
          expect(sanitized).not.toContain('<script>');
          expect(sanitized).not.toContain('javascript:');
        }
      )
    );
  });

  it('should handle null and undefined inputs', () => {
    fc.assert(
      fc.property(
        fc.oneof(fc.constant(null), fc.constant(undefined)),
        (input) => {
          const result = processUserInput(input);
          expect(result).toBeDefined();
          expect(result.isValid).toBe(false);
        }
      )
    );
  });
});
```

---

## 5. Semantic Diff Algorithm

### 5.1 Tree-sitter Implementation

```python
# src/fixing/semantic_diff.py

from tree_sitter import Language, Parser
import networkx as nx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ASTNode:
    """Represents an AST node."""
    type: str
    text: str
    start_point: tuple
    end_point: tuple
    children: List['ASTNode']


@dataclass
class SemanticDiffResult:
    """Result of semantic diff computation."""
    changed_nodes: List[ASTNode]
    data_flow_changes: Dict
    call_graph_changes: Dict
    side_effects: List[Dict]
    is_clean: bool


class SemanticDiffEngine:
    """Tree-sitter-based semantic diff showing exact code changes."""

    def __init__(self):
        self.parsers = {}
        self._load_languages()

    def _load_languages(self):
        """Loads Tree-sitter languages."""
        from tree_sitter import Language

        languages = {
            'python': 'tree-sitter-python.so',
            'javascript': 'tree-sitter-javascript.so',
            'typescript': 'tree-sitter-typescript.so',
            'rust': 'tree-sitter-rust.so',
        }

        for lang_name, so_path in languages.items():
            try:
                lang = Language(so_path, lang_name.replace('-', '_'))
                parser = Parser()
                parser.set_language(lang)
                self.parsers[lang_name] = parser
            except Exception as e:
                print(f"Warning: Could not load {lang_name}: {e}")

    def compute_diff(
        self,
        old_code: Dict[str, str],
        new_code: Dict[str, str]
    ) -> Dict[str, SemanticDiffResult]:
        """Computes semantic diff between two code versions."""
        results = {}

        for file_path in set(old_code.keys()) | set(new_code.keys()):
            old_content = old_code.get(file_path, "")
            new_content = new_code.get(file_path, "")

            if old_content == new_content:
                continue

            language = self._detect_language(file_path)
            if language not in self.parsers:
                continue

            parser = self.parsers[language]
            old_tree = parser.parse(bytes(old_content, 'utf8'))
            new_tree = parser.parse(bytes(new_content, 'utf8'))

            # Extract changed nodes
            changed_nodes = self._find_changed_nodes(old_tree, new_tree)

            # Analyze impact on data flows
            data_flow_changes = self._analyze_data_flow_impact(
                changed_nodes, old_content, new_content
            )

            # Analyze impact on call graph
            call_graph_changes = self._analyze_call_graph_impact(
                changed_nodes, old_content, new_content
            )

            # Detect side effects
            side_effects = self._detect_side_effects(
                changed_nodes, old_content, new_content
            )

            results[file_path] = SemanticDiffResult(
                changed_nodes=changed_nodes,
                data_flow_changes=data_flow_changes,
                call_graph_changes=call_graph_changes,
                side_effects=side_effects,
                is_clean=len(side_effects) == 0
            )

        return results

    def _find_changed_nodes(
        self,
        old_tree: Any,
        new_tree: Any
    ) -> List[ASTNode]:
        """Finds AST nodes that changed between versions."""
        changed = []

        def compare_trees(old_node, new_node):
            if old_node is None or new_node is None:
                return

            if old_node.type != new_node.type:
                changed.append(self._node_to_ast_node(new_node))
                return

            if old_node.text != new_node.text:
                # Node content changed - recurse to find specific changes
                old_children = old_node.children
                new_children = new_node.children

                for i in range(min(len(old_children), len(new_children))):
                    compare_trees(old_children[i], new_children[i])

                # Handle added/removed children
                for child in new_children[len(old_children):]:
                    changed.append(self._node_to_ast_node(child))

        compare_trees(old_tree.root_node, new_tree.root_node)
        return changed

    def _analyze_data_flow_impact(
        self,
        changed_nodes: List[ASTNode],
        old_code: str,
        new_code: str
    ) -> Dict:
        """Analyzes how data flows are affected by changes."""
        changes = {
            'new_flows': [],
            'removed_flows': [],
            'modified_flows': []
        }

        for node in changed_nodes:
            # Check if change affects variable definitions
            if node.type in ['variable_definition', 'assignment']:
                changes['modified_flows'].append({
                    'type': 'VARIABLE_CHANGE',
                    'node': node.text,
                    'location': node.start_point
                })

            # Check if change affects function calls
            if node.type in ['call_expression', 'function_call']:
                changes['modified_flows'].append({
                    'type': 'CALL_CHANGE',
                    'node': node.text,
                    'location': node.start_point
                })

        return changes

    def _analyze_call_graph_impact(
        self,
        changed_nodes: List[ASTNode],
        old_code: str,
        new_code: str
    ) -> Dict:
        """Analyzes how call graph is affected by changes."""
        changes = {
            'new_calls': [],
            'removed_calls': [],
            'modified_calls': []
        }

        for node in changed_nodes:
            if node.type in ['function_definition', 'method_definition']:
                changes['modified_calls'].append({
                    'type': 'FUNCTION_CHANGE',
                    'node': node.text,
                    'location': node.start_point
                })

        return changes

    def _detect_side_effects(
        self,
        changed_nodes: List[ASTNode],
        old_code: str,
        new_code: str
    ) -> List[Dict]:
        """Detects unintended side effects of changes."""
        side_effects = []

        for node in changed_nodes:
            # Check if change affects unrelated scope
            if self._affects_unrelated_scope(node, old_code, new_code):
                side_effects.append({
                    'type': 'SCOPE_LEAK',
                    'description': f"Change in {node.text} affects unrelated scope",
                    'location': node.start_point
                })

            # Check if change introduces new data flow
            if self._introduces_new_data_flow(node, old_code, new_code):
                side_effects.append({
                    'type': 'NEW_DATA_FLOW',
                    'description': f"New data flow introduced by {node.text}",
                    'location': node.start_point
                })

            # Check if change removes existing functionality
            if self._removes_functionality(node, old_code, new_code):
                side_effects.append({
                    'type': 'REMOVED_FUNCTIONALITY',
                    'description': f"Existing functionality removed by {node.text}",
                    'location': node.start_point
                })

        return side_effects

    def _node_to_ast_node(self, node) -> ASTNode:
        """Converts Tree-sitter node to ASTNode."""
        return ASTNode(
            type=node.type,
            text=node.text.decode('utf8') if isinstance(node.text, bytes) else node.text,
            start_point=node.start_point,
            end_point=node.end_point,
            children=[]
        )

    def _detect_language(self, file_path: str) -> str:
        """Detects language from file extension."""
        if file_path.endswith('.py'):
            return 'python'
        elif file_path.endswith('.js'):
            return 'javascript'
        elif file_path.endswith('.ts'):
            return 'typescript'
        elif file_path.endswith('.rs'):
            return 'rust'
        return 'unknown'
```

---

## 6. Graph Comparison

### 6.1 NetworkX Before/After Comparison

```python
# src/fixing/graph_comparator.py

import networkx as nx
from typing import List, Dict, Any, Set, Tuple
from dataclasses import dataclass


@dataclass
class DFGChange:
    """Represents a change in Data-Flow Graph."""
    source: str
    target: str
    change_type: str  # 'NEW_FLOW', 'REMOVED_FLOW', 'MODIFIED_FLOW'
    risk_level: str  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'


@dataclass
class CGChange:
    """Represents a change in Call Graph."""
    caller: str
    callee: str
    change_type: str  # 'NEW_CALL', 'REMOVED_CALL', 'MODIFIED_CALL'
    risk_level: str


@dataclass
class BreakingChange:
    """Represents a breaking change."""
    type: str  # 'REMOVED_API', 'SIGNATURE_CHANGE', 'BEHAVIOR_CHANGE'
    element: str
    severity: str  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'


@dataclass
class GraphComparisonResult:
    """Result of graph comparison."""
    dfg_changes: List[DFGChange]
    cg_changes: List[CGChange]
    breaking_changes: List[BreakingChange]
    regression_score: float  # 0.0 (bad) to 1.0 (good)
    is_safe: bool


class GraphComparator:
    """Compares before/after graphs to detect regression."""

    def __init__(
        self,
        original_dfg: nx.DiGraph,
        patched_dfg: nx.DiGraph,
        original_cg: nx.DiGraph,
        patched_cg: nx.DiGraph
    ):
        self.original_dfg = original_dfg
        self.patched_dfg = patched_dfg
        self.original_cg = original_cg
        self.patched_cg = patched_cg

    def compare(self) -> GraphComparisonResult:
        """Compares graphs and detects regressions."""
        result = GraphComparisonResult(
            dfg_changes=[],
            cg_changes=[],
            breaking_changes=[],
            regression_score=1.0,
            is_safe=True
        )

        # 1. Data-Flow Graph Comparison
        result.dfg_changes = self._compare_dfg()

        # 2. Call Graph Comparison
        result.cg_changes = self._compare_cg()

        # 3. Detect Breaking Changes
        result.breaking_changes = self._detect_breaking_changes()

        # 4. Compute Regression Score
        result.regression_score = self._compute_regression_score(result)

        # 5. Determine if safe
        result.is_safe = (
            result.regression_score >= 0.95 and
            len(result.breaking_changes) == 0
        )

        return result

    def _compare_dfg(self) -> List[DFGChange]:
        """Compares data-flow graphs."""
        changes = []

        # Find new data flows (potential new bugs)
        for edge in self.patched_dfg.edges():
            if edge not in self.original_dfg.edges():
                changes.append(DFGChange(
                    source=edge[0],
                    target=edge[1],
                    change_type='NEW_FLOW',
                    risk_level=self._assess_flow_risk(edge, self.patched_dfg)
                ))

        # Find removed data flows (potential broken functionality)
        for edge in self.original_dfg.edges():
            if edge not in self.patched_dfg.edges():
                changes.append(DFGChange(
                    source=edge[0],
                    target=edge[1],
                    change_type='REMOVED_FLOW',
                    risk_level='MEDIUM'
                ))

        return changes

    def _compare_cg(self) -> List[CGChange]:
        """Compares call graphs."""
        changes = []

        # Find new calls
        for edge in self.patched_cg.edges():
            if edge not in self.original_cg.edges():
                changes.append(CGChange(
                    caller=edge[0],
                    callee=edge[1],
                    change_type='NEW_CALL',
                    risk_level=self._assess_call_risk(edge, self.patched_cg)
                ))

        # Find removed calls
        for edge in self.original_cg.edges():
            if edge not in self.patched_cg.edges():
                changes.append(CGChange(
                    caller=edge[0],
                    callee=edge[1],
                    change_type='REMOVED_CALL',
                    risk_level='LOW'
                ))

        return changes

    def _detect_breaking_changes(self) -> List[BreakingChange]:
        """Detects breaking changes in the patch."""
        breaking = []

        # Check for removed public API
        removed_functions = (
            set(self.original_cg.nodes()) - set(self.patched_cg.nodes())
        )
        for func in removed_functions:
            if self._is_public_function(func):
                breaking.append(BreakingChange(
                    type='REMOVED_API',
                    element=func,
                    severity='HIGH'
                ))

        # Check for signature changes
        for node in self.original_cg.nodes():
            if node in self.patched_cg.nodes():
                old_sig = self._get_signature(node, self.original_cg)
                new_sig = self._get_signature(node, self.patched_cg)
                if old_sig != new_sig:
                    breaking.append(BreakingChange(
                        type='SIGNATURE_CHANGE',
                        element=node,
                        severity='MEDIUM'
                    ))

        return breaking

    def _compute_regression_score(
        self,
        result: GraphComparisonResult
    ) -> float:
        """Computes regression score based on changes."""
        score = 1.0

        # Penalize new data flows (potential bugs)
        for change in result.dfg_changes:
            if change.change_type == 'NEW_FLOW':
                if change.risk_level == 'CRITICAL':
                    score -= 0.2
                elif change.risk_level == 'HIGH':
                    score -= 0.1
                elif change.risk_level == 'MEDIUM':
                    score -= 0.05

        # Penalize breaking changes
        for change in result.breaking_changes:
            if change.severity == 'CRITICAL':
                score -= 0.3
            elif change.severity == 'HIGH':
                score -= 0.15
            elif change.severity == 'MEDIUM':
                score -= 0.05

        return max(0.0, score)

    def _assess_flow_risk(
        self,
        edge: Tuple[str, str],
        graph: nx.DiGraph
    ) -> str:
        """Assesses risk level of a new data flow."""
        source, target = edge

        # Critical: User input → Security-sensitive operation
        if self._is_user_input(source) and self._is_security_sensitive(target):
            return 'CRITICAL'

        # High: External data → Database
        if self._is_external_data(source) and self._is_database(target):
            return 'HIGH'

        # Medium: Any new flow to sensitive operation
        if self._is_security_sensitive(target):
            return 'MEDIUM'

        return 'LOW'

    def _assess_call_risk(
        self,
        edge: Tuple[str, str],
        graph: nx.DiGraph
    ) -> str:
        """Assesses risk level of a new call."""
        caller, callee = edge

        # Critical: Public API → Security-sensitive function
        if self._is_public_api(caller) and self._is_security_sensitive(callee):
            return 'CRITICAL'

        # High: Any new call to security-sensitive function
        if self._is_security_sensitive(callee):
            return 'HIGH'

        return 'LOW'

    def _is_user_input(self, node: str) -> bool:
        """Checks if node represents user input."""
        return 'input' in node.lower() or 'request' in node.lower()

    def _is_security_sensitive(self, node: str) -> bool:
        """Checks if node is security-sensitive."""
        sensitive_keywords = [
            'sql', 'query', 'execute', 'eval', 'exec',
            'auth', 'token', 'password', 'secret', 'key',
            'file', 'write', 'delete', 'drop', 'create'
        ]
        return any(kw in node.lower() for kw in sensitive_keywords)

    def _is_public_function(self, func: str) -> bool:
        """Checks if function is public API."""
        return not func.startswith('_')

    def _get_signature(
        self,
        node: str,
        graph: nx.DiGraph
    ) -> str:
        """Gets function signature from graph."""
        return graph.nodes[node].get('signature', '')
```

---

## 7. Configuration Reference

### 7.1 Complete Configuration

```yaml
# config.yaml - Regression-Proof Fixing Section

fixing_policy:
  # Patch constraints
  max_files_touched: 3
  max_changed_lines: 160
  allow_new_dependencies: false

  # Verifier settings
  verifier_confidence_threshold: 0.95
  verifier_model: "phi-4-mini"
  verifier_temperature: 0.0  # Deterministic

  # Iteration limits
  max_iterations: 5
  escalate_after_no_progress: 2

# Regression Testing Configuration
regression_testing:
  enabled: true
  fail2pass_required: true
  min_tests: 3
  max_tests: 5

  # Language-specific frameworks
  python:
    framework: "hypothesis"
    max_examples: 50
    deadline: 500  # ms
    suppress_health_check: ["data_too_large"]
    strategies:
      - "null_injection"
      - "negative_values"
      - "boundary_values"
      - "type_mismatch"
      - "race_condition"

  rust:
    framework: "proptest"
    cases: 256
    max_local_rejects: 1024
    max_global_rejects: 1024
    fork: true
    strategies:
      - "overflow"
      - "underflow"
      - "bounds_check"
      - "concurrent_access"

  javascript:
    framework: "jest + fast-check"
    numRuns: 100
    interruptAfter: 10000  # ms
    maxSkips: 1000
    strategies:
      - "xss_injection"
      - "null_undefined"
      - "type_confusion"
      - "async_race"

  typescript:
    framework: "jest + fast-check"
    numRuns: 100
    interruptAfter: 10000  # ms
    maxSkips: 1000
    strategies:
      - "xss_injection"
      - "null_undefined"
      - "type_confusion"
      - "async_race"

# Safety Gates Configuration
safety_gates:
  gate1_pre_apply:
    enabled: true
    syntax_check: true
    linter_check: true
    static_analysis: true
    semantic_diff: true
    policy_check: true

    # Static analysis tools
    tools:
      python: ["ruff", "mypy", "semgrep"]
      javascript: ["eslint", "semgrep"]
      typescript: ["eslint", "tsc", "semgrep"]
      rust: ["clippy", "semgrep"]

  gate2_post_apply:
    enabled: true
    graph_comparison: true
    breaking_change_detection: true
    verifier_llm: true

    # Graph comparison settings
    dfg_comparison: true
    cg_comparison: true
    risk_threshold: "MEDIUM"  # Report MEDIUM and above

# Sandbox Configuration
sandbox:
  enabled: true
  backend: "docker"
  network_disabled: true
  timeout_seconds: 180
  memory_limit: "2g"
  cpu_limit: 2.0

  # Test execution
  run_all_tests: true
  run_regression_tests: true
  run_security_tests: true

  # Coverage
  coverage_required: true
  coverage_threshold: 0.8  # Minimum 80% coverage
  coverage_non_regressive: true  # Must not reduce coverage

# Semantic Diff Configuration
semantic_diff:
  enabled: true
  tree_sitter_languages:
    - python
    - javascript
    - typescript
    - rust
    - go
    - java
    - cpp

  # Side effect detection
  detect_scope_leaks: true
  detect_new_data_flows: true
  detect_removed_functionality: true

# Graph Comparison Configuration
graph_comparison:
  enabled: true
  backend: "networkx"

  # Change detection
  detect_new_flows: true
  detect_removed_flows: true
  detect_modified_flows: true

  # Risk assessment
  risk_assessment_enabled: true
  critical_keywords:
    - sql
    - query
    - execute
    - eval
    - auth
    - token
    - password
```

### 7.2 Environment Variables

```bash
# .env - Regression-Proof Fixing

# Gate thresholds
GLITCHHUNTER_VERIFIER_CONFIDENCE_THRESHOLD=0.95
GLITCHHUNTER_MAX_ITERATIONS=5

# Sandbox settings
GLITCHHUNTER_SANDBOX_TIMEOUT=180
GLITCHHUNTER_SANDBOX_MEMORY_LIMIT=2g

# Coverage requirements
GLITCHHUNTER_COVERAGE_THRESHOLD=0.8
GLITCHHUNTER_COVERAGE_NON_REGRESSIVE=true

# Test generation
GLITCHHUNTER_MIN_TESTS=3
GLITCHHUNTER_MAX_TESTS=5
GLITCHHUNTER_FAIL2PASS_REQUIRED=true
```

---

## Appendix A: Example Test Cases

### A.1 Python SQL Injection Test

```python
# tests/regression/test_sql_injection.py

from hypothesis import given, strategies as st
import pytest
from src.database.user_repository import UserRepository


class TestSQLInjectionRegression:
    """Regression tests for SQL injection fix."""

    @pytest.fixture
    def repo(self, db_connection):
        return UserRepository(db_connection)

    @given(
        username=st.text().filter(lambda x: "'" in x or '"' in x),
        password=st.text()
    )
    def test_username_with_quotes_sanitized(self, username, password, repo):
        """Tests that usernames with quotes are sanitized."""
        # This test MUST fail on original buggy code
        result = repo.create_user(username, password)

        # Property: No SQL injection should occur
        assert result.success is True
        assert "SQL error" not in result.message

    @given(
        malicious_input=st.oneof(
            st.just("' OR '1'='1"),
            st.just("'; DROP TABLE users; --"),
            st.just("' UNION SELECT * FROM users --")
        )
    )
    def test_common_injection_patterns_blocked(self, malicious_input, repo):
        """Tests that common injection patterns are blocked."""
        result = repo.get_user_by_username(malicious_input)

        # Property: Injection should not return unintended data
        assert result is None or result.is_sanitized
```

### A.2 Rust Buffer Overflow Test

```rust
// tests/regression/test_buffer_overflow.rs

use proptest::prelude::*;
use crate::buffer::SafeBuffer;

proptest! {
    #[test]
    fn test_buffer_bounds_always_checked(
        input in prop::string::string_regex("[a-zA-Z0-9]{0,1000}").unwrap()
    ) {
        // This test MUST fail on original buggy code
        let buffer = SafeBuffer::new(1024);
        let result = buffer.write(&input);

        // Property: No out-of-bounds access
        prop_assert!(result.is_ok());

        // Property: Written data can be read back
        if let Ok(bytes_written) = result {
            let read_data = buffer.read(0, bytes_written);
            prop_assert_eq!(read_data.as_bytes(), input.as_bytes());
        }
    }

    #[test]
    fn test_negative_offset_rejected(offset in -1000i32..0i32) {
        // Property: Negative offsets should be rejected
        let buffer = SafeBuffer::new(1024);
        let result = buffer.read_at_offset(offset as usize, 10);

        prop_assert!(result.is_err());
    }
}
```

---

**END OF DOCUMENT**
