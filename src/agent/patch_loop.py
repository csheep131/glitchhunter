"""
Patch-Loop State Machine für GlitchHunter.

Koordination des iterativen Patch-Prozesses mit:
- Gate 1: Pre-Apply Validation
- Sandbox Execution
- Gate 2: Post-Apply Verification
- Accept / Retry / Escalate Logik
- Maximal 5 Iterationen
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from langgraph.graph import StateGraph, END

from .patch_generator import PatchGenerator, PatchResult
from .sandbox_executor import SandboxExecutor, ExecutionResult, SandboxConfig
from ..fixing.pre_apply_validator import PreApplyValidator, Gate1Result
from ..fixing.post_apply_verifier import PostApplyVerifier, Gate2Result
from ..fixing.coverage_checker import CoverageChecker, CoverageMetrics
from ..fixing.regression_test_generator import RegressionTestGenerator, TestSpec
from ..analysis.graph_comparator import GraphComparator, GraphComparison

logger = logging.getLogger(__name__)


class PatchDecision(str, Enum):
    """Entscheidung nach Patch-Loop."""

    ACCEPT = "accept"
    RETRY = "retry"
    ESCALATE = "escalate"


@dataclass
class PatchIteration:
    """
    Information über eine Patch-Iteration.

    Attributes:
        iteration_number: Iterationsnummer (1-5).
        patch: Generierter Patch.
        gate1_result: Ergebnis von Gate 1.
        execution_result: Ergebnis der Sandbox-Ausführung.
        gate2_result: Ergebnis von Gate 2.
        decision: Entscheidung (ACCEPT/RETRY/ESCALATE).
        reason: Begründung der Entscheidung.
    """

    iteration_number: int
    patch: Optional[PatchResult] = None
    gate1_result: Optional[Gate1Result] = None
    execution_result: Optional[ExecutionResult] = None
        gate2_result: Optional[Gate2Result] = None
    decision: Optional[PatchDecision] = None
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "iteration_number": self.iteration_number,
            "patch": self.patch.to_dict() if self.patch else None,
            "gate1_result": self.gate1_result.to_dict() if self.gate1_result else None,
            "execution_result": self.execution_result.to_dict() if self.execution_result else None,
            "gate2_result": self.gate2_result.to_dict() if self.gate2_result else None,
            "decision": self.decision.value if self.decision else None,
            "reason": self.reason,
        }


@dataclass
class PatchLoopState:
    """
    State für Patch-Loop.

    Attributes:
        candidate: Bug-Kandidat.
        original_code: Original-Code.
        patched_code: Gepatchter Code.
        patch_diff: Patch-Diff.
        before_graph: Graph vor Patch.
        after_graph: Graph nach Patch.
        regression_tests: Regression-Tests.
        before_coverage: Coverage vor Patch.
        iterations: Liste der Iterationen.
        current_iteration: Aktuelle Iteration (1-5).
        max_iterations: Maximale Iterationen.
        final_decision: Finale Entscheidung.
    """

    candidate: Dict[str, Any]
    original_code: str
    patched_code: str = ""
    patch_diff: str = ""
    before_graph: Dict[str, Any] = field(default_factory=dict)
    after_graph: Dict[str, Any] = field(default_factory=dict)
    regression_tests: List[TestSpec] = field(default_factory=list)
    before_coverage: Optional[CoverageMetrics] = None
    iterations: List[PatchIteration] = field(default_factory=list)
    current_iteration: int = 0
    max_iterations: int = 5
    final_decision: Optional[PatchDecision] = None

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "candidate": self.candidate,
            "original_code": self.original_code[:500],
            "patched_code": self.patched_code[:500],
            "patch_diff": self.patch_diff[:500],
            "before_graph": self.before_graph,
            "after_graph": self.after_graph,
            "regression_tests_count": len(self.regression_tests),
            "iterations": [i.to_dict() for i in self.iterations],
            "current_iteration": self.current_iteration,
            "max_iterations": self.max_iterations,
            "final_decision": self.final_decision.value if self.final_decision else None,
        }


class PatchLoopStateMachine:
    """
    State Machine für Patch-Loop.

    Ablauf:
    1. Generiere Regression-Tests (Fail2Pass)
    2. Generiere Patch
    3. Gate 1: Pre-Apply Validation
    4. Sandbox Execution (Tests ausführen)
    5. Gate 2: Post-Apply Verification
    6. Entscheidung: ACCEPT / RETRY / ESCALATE

    Usage:
        machine = PatchLoopStateMachine(candidate, original_code)
        result = machine.run()
    """

    def __init__(
        self,
        candidate: Dict[str, Any],
        original_code: str,
        before_graph: Optional[Dict[str, Any]] = None,
        before_coverage: Optional[CoverageMetrics] = None,
        max_iterations: int = 5,
        model_path: Optional[str] = None,
        language: str = "python",
    ) -> None:
        """
        Initialisiert Patch-Loop State Machine.

        Args:
            candidate: Bug-Kandidat.
            original_code: Original-Code.
            before_graph: Graph vor Patch.
            before_coverage: Coverage vor Patch.
            max_iterations: Maximale Iterationen.
            model_path: Pfad zum LLM-Modell.
            language: Programmiersprache.
        """
        self.state = PatchLoopState(
            candidate=candidate,
            original_code=original_code,
            before_graph=before_graph or {},
            before_coverage=before_coverage,
            max_iterations=max_iterations,
        )

        self.model_path = model_path
        self.language = language

        # Komponenten initialisieren
        self.patch_generator = PatchGenerator(model_path=model_path)
        self.sandbox_executor = SandboxExecutor()
        self.pre_apply_validator = PreApplyValidator(language=language)
        self.post_apply_verifier = PostApplyVerifier(model_path=model_path)
        self.coverage_checker = CoverageChecker(language=language)
        self.regression_test_generator = RegressionTestGenerator()
        self.graph_comparator = GraphComparator()

        # Workflow aufbauen
        self.workflow = self._build_graph()
        self.app = self.workflow.compile()

        logger.debug(f"PatchLoopStateMachine initialisiert: max_iterations={max_iterations}")

    def _build_graph(self) -> StateGraph:
        """
        Baut LangGraph State Machine.

        Returns:
            Configured StateGraph
        """

        def generate_regression_tests(state: Dict[str, Any]) -> Dict[str, Any]:
            """Generiere Regression-Tests."""
            logger.info("Generiere Regression-Tests (Fail2Pass)")

            # TODO: Candidate in TestSpec konvertieren
            candidate_obj = self._dict_to_candidate(state["candidate"])
            tests = self.regression_test_generator.generate_edge_case_tests(
                candidate=candidate_obj,
                num=5,
            )

            state["regression_tests"] = tests
            state["metadata"]["regression_tests_generated"] = True

            return state

        def generate_patch(state: Dict[str, Any]) -> Dict[str, Any]:
            """Generiere Patch."""
            logger.info(f"Generiere Patch (Iteration {state.get('current_iteration', 0) + 1})")

            candidate_obj = self._dict_to_candidate(state["candidate"])
            patch_result = self.patch_generator.generate(
                issue=candidate_obj.to_dict(),
                code=state["original_code"],
                language=self.language,
            )

            state["patch"] = patch_result
            state["patched_code"] = patch_result.patched_code
            state["patch_diff"] = patch_result.patch_diff

            return state

        def gate1_validation(state: Dict[str, Any]) -> Dict[str, Any]:
            """Gate 1: Pre-Apply Validation."""
            logger.info("Gate 1: Pre-Apply Validation")

            patch_result = state.get("patch")
            if not patch_result:
                state["gate1_passed"] = False
                state["gate1_error"] = "Kein Patch verfügbar"
                return state

            result = self.pre_apply_validator.validate(
                original_code=state["original_code"],
                patched_code=patch_result.patched_code,
                patch_diff=patch_result.patch_diff,
            )

            state["gate1_result"] = result
            state["gate1_passed"] = result.passed

            return state

        def sandbox_execution(state: Dict[str, Any]) -> Dict[str, Any]:
            """Sandbox: Tests ausführen."""
            logger.info("Sandbox: Tests ausführen")

            if not state.get("gate1_passed"):
                state["execution_result"] = ExecutionResult(
                    success=False,
                    error="Gate 1 nicht bestanden",
                )
                return state

            # Tests mit Sandbox ausführen
            patch_result = state.get("patch")
            test_code = self._generate_test_code(state.get("regression_tests", []))

            execution_result = self.sandbox_executor.execute_with_tests(
                code=patch_result.patched_code if patch_result else state["original_code"],
                test_code=test_code,
                language=self.language,
            )

            state["execution_result"] = execution_result
            state["tests_passed"] = execution_result.all_tests_passed

            return state

        def gate2_verification(state: Dict[str, Any]) -> Dict[str, Any]:
            """Gate 2: Post-Apply Verification."""
            logger.info("Gate 2: Post-Apply Verification")

            if not state.get("tests_passed"):
                state["gate2_result"] = Gate2Result(
                    passed=False,
                    verifier_confidence=0.0,
                )
                state["gate2_passed"] = False
                return state

            # Graph-Vergleich
            graph_comparison = self.graph_comparator.compare(
                before_graph=state.get("before_graph", {}),
                after_graph=state.get("after_graph", {}),
                graph_type="dfg",
            )

            # Verifier
            patch_result = state.get("patch")
            verifier_result = self.post_apply_verifier.verify(
                original_code=state["original_code"],
                patched_code=patch_result.patched_code if patch_result else "",
                before_graph=state.get("before_graph", {}),
                after_graph=state.get("after_graph", {}),
                test_results=[state.get("execution_result", ExecutionResult()).to_dict()],
            )

            state["gate2_result"] = verifier_result
            state["gate2_passed"] = verifier_result.passed
            state["graph_comparison"] = graph_comparison.to_dict()

            return state

        def make_decision(state: Dict[str, Any]) -> Dict[str, Any]:
            """Entscheidung treffen: ACCEPT / RETRY / ESCALATE."""
            logger.info("Treffe Entscheidung")

            gate1_passed = state.get("gate1_passed", False)
            gate2_passed = state.get("gate2_passed", False)
            tests_passed = state.get("tests_passed", False)
            current_iteration = state.get("current_iteration", 0)

            # ACCEPT wenn alle Gates bestanden
            if gate1_passed and gate2_passed and tests_passed:
                state["decision"] = PatchDecision.ACCEPT.value
                state["decision_reason"] = "Alle Gates bestanden"
                state["final_decision"] = PatchDecision.ACCEPT
                return state

            # ESCALATE wenn max Iterationen erreicht
            if current_iteration >= state.get("max_iterations", 5):
                state["decision"] = PatchDecision.ESCALATE.value
                state["decision_reason"] = f"Maximale Iterationen ({current_iteration}) erreicht"
                state["final_decision"] = PatchDecision.ESCALATE
                return state

            # RETRY für weitere Iteration
            state["decision"] = PatchDecision.RETRY.value
            state["decision_reason"] = "Gates nicht bestanden, weitere Iteration"
            return state

        # Workflow definieren
        workflow = StateGraph(dict)

        workflow.add_node("generate_regression_tests", generate_regression_tests)
        workflow.add_node("generate_patch", generate_patch)
        workflow.add_node("gate1_validation", gate1_validation)
        workflow.add_node("sandbox_execution", sandbox_execution)
        workflow.add_node("gate2_verification", gate2_verification)
        workflow.add_node("make_decision", make_decision)

        # Entry Point
        workflow.set_entry_point("generate_regression_tests")

        # Edges
        workflow.add_edge("generate_regression_tests", "generate_patch")
        workflow.add_edge("generate_patch", "gate1_validation")
        workflow.add_edge("gate1_validation", "sandbox_execution")
        workflow.add_edge("sandbox_execution", "gate2_verification")
        workflow.add_edge("gate2_verification", "make_decision")

        # Conditional Edge für Retry
        workflow.add_conditional_edges(
            "make_decision",
            lambda state: state.get("decision", "retry"),
            {
                PatchDecision.ACCEPT.value: END,
                PatchDecision.ESCALATE.value: END,
                PatchDecision.RETRY.value: "generate_patch",  # Loop back
            },
        )

        return workflow

    def run(self) -> Dict[str, Any]:
        """
        Führt kompletten Patch-Loop aus.

        Returns:
            Finale State.
        """
        logger.info("Starte Patch-Loop")

        initial_state = {
            "candidate": self.state.candidate,
            "original_code": self.state.original_code,
            "patched_code": "",
            "patch_diff": "",
            "before_graph": self.state.before_graph,
            "after_graph": {},
            "regression_tests": [],
            "before_coverage": self.state.before_coverage.to_dict() if self.state.before_coverage else None,
            "iterations": [],
            "current_iteration": 0,
            "max_iterations": self.state.max_iterations,
            "final_decision": None,
            "metadata": {},
        }

        try:
            result = self.app.invoke(initial_state)

            # Entscheidung verarbeiten
            decision = result.get("final_decision")
            if decision == PatchDecision.ACCEPT.value:
                logger.info("Patch akzeptiert")
            elif decision == PatchDecision.ESCALATE.value:
                logger.warning("Patch eskaliert")
            else:
                logger.warning("Patch-Loop ohne finale Entscheidung beendet")

            return result

        except Exception as e:
            logger.error(f"Patch-Loop fehlgeschlagen: {e}")
            return {
                "error": str(e),
                "final_decision": None,
            }

    def _dict_to_candidate(self, candidate_dict: Dict[str, Any]) -> Any:
        """Konvertiert Dict zu Candidate-Objekt."""
        from .regression_test_generator import Candidate

        return Candidate(
            file_path=candidate_dict.get("file_path", ""),
            bug_type=candidate_dict.get("bug_type", ""),
            description=candidate_dict.get("description", ""),
            line_start=candidate_dict.get("line_start", 0),
            line_end=candidate_dict.get("line_end", 0),
        )

    def _generate_test_code(self, tests: List[TestSpec]) -> str:
        """Generiert Test-Code aus TestSpecs."""
        test_code = ""
        for test in tests:
            test_code += f"\n{test.test_code}\n"
        return test_code

    def run_single_iteration(self) -> PatchIteration:
        """
        Führt einzelne Iteration aus.

        Returns:
            PatchIteration.
        """
        self.state.current_iteration += 1

        iteration = PatchIteration(iteration_number=self.state.current_iteration)

        try:
            # 1. Patch generieren
            candidate_obj = self._dict_to_candidate(self.state.candidate)
            patch_result = self.patch_generator.generate(
                issue=candidate_obj.to_dict(),
                code=self.state.original_code,
                language=self.language,
            )
            iteration.patch = patch_result
            self.state.patched_code = patch_result.patched_code
            self.state.patch_diff = patch_result.patch_diff

            # 2. Gate 1
            gate1_result = self.pre_apply_validator.validate(
                original_code=self.state.original_code,
                patched_code=patch_result.patched_code,
                patch_diff=patch_result.patch_diff,
            )
            iteration.gate1_result = gate1_result

            if not gate1_result.passed:
                iteration.decision = PatchDecision.RETRY
                iteration.reason = "Gate 1 nicht bestanden"
                self.state.iterations.append(iteration)
                return iteration

            # 3. Sandbox Execution
            test_code = self._generate_test_code(self.state.regression_tests)
            execution_result = self.sandbox_executor.execute_with_tests(
                code=patch_result.patched_code,
                test_code=test_code,
                language=self.language,
            )
            iteration.execution_result = execution_result

            if not execution_result.all_tests_passed:
                iteration.decision = PatchDecision.RETRY
                iteration.reason = "Tests nicht bestanden"
                self.state.iterations.append(iteration)
                return iteration

            # 4. Gate 2
            graph_comparison = self.graph_comparator.compare(
                before_graph=self.state.before_graph,
                after_graph=self.state.after_graph,
                graph_type="dfg",
            )

            gate2_result = self.post_apply_verifier.verify(
                original_code=self.state.original_code,
                patched_code=patch_result.patched_code,
                before_graph=self.state.before_graph,
                after_graph=self.state.after_graph,
                test_results=[execution_result.to_dict()],
            )
            iteration.gate2_result = gate2_result

            if not gate2_result.passed:
                iteration.decision = PatchDecision.RETRY
                iteration.reason = "Gate 2 nicht bestanden"
                self.state.iterations.append(iteration)
                return iteration

            # 5. ACCEPT
            iteration.decision = PatchDecision.ACCEPT
            iteration.reason = "Alle Gates bestanden"
            self.state.final_decision = PatchDecision.ACCEPT
            self.state.iterations.append(iteration)

            return iteration

        except Exception as e:
            logger.error(f"Iteration fehlgeschlagen: {e}")
            iteration.decision = PatchDecision.RETRY
            iteration.reason = f"Fehler: {e}"
            self.state.iterations.append(iteration)
            return iteration

    def run_all_iterations(self) -> PatchLoopState:
        """
        Führt alle Iterationen bis zum Erfolg oder Maximum aus.

        Returns:
            Finale State.
        """
        logger.info("Starte Patch-Loop mit allen Iterationen")

        # Regression-Tests generieren
        candidate_obj = self._dict_to_candidate(self.state.candidate)
        self.state.regression_tests = self.regression_test_generator.generate_edge_case_tests(
            candidate=candidate_obj,
            num=5,
        )

        while self.state.current_iteration < self.state.max_iterations:
            iteration = self.run_single_iteration()

            if iteration.decision == PatchDecision.ACCEPT:
                logger.info(f"Patch akzeptiert nach {self.state.current_iteration} Iterationen")
                return self.state

            if iteration.decision == PatchDecision.ESCALATE:
                logger.warning(f"Patch eskaliert nach {self.state.current_iteration} Iterationen")
                return self.state

            logger.info(f"Iteration {self.state.current_iteration}: RETRY")

        # Maximum erreicht
        self.state.final_decision = PatchDecision.ESCALATE
        logger.warning(f"Patch-Loop nach {self.state.max_iterations} Iterationen eskaliert")
        return self.state
