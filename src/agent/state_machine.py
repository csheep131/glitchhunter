"""
State machine for GlitchHunter agent workflow.

Uses LangGraph to define a state machine with states for:
- Ingestion: Repository parsing and mapping
- Shield: Pre-filtering and security scanning
- Hypothesis: Bug hypothesis generation
- Analyzer: Causal hypothesis testing
- Observer: Evidence evaluation
- LLiftPrioritizer: Candidate prioritization
- PatchLoop: Iterative patch generation and verification
- Finalizer: Report generation and rule learning
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, TypedDict

from langgraph.graph import END, StateGraph

logger = logging.getLogger(__name__)


@dataclass
class Candidate:
    """Bug candidate for analysis."""

    file_path: str
    bug_type: str
    description: str
    line_start: int
    line_end: int
    severity: str = "medium"
    confidence: float = 0.5
    evidence: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "bug_type": self.bug_type,
            "description": self.description,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "severity": self.severity,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


@dataclass
class Hypothesis:
    """Bug hypothesis."""

    candidate: Candidate
    hypothesis: str
    confidence: float
    evidence: List[str] = field(default_factory=list)
    tested: bool = False
    verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "candidate": self.candidate.to_dict(),
            "hypothesis": self.hypothesis,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "tested": self.tested,
            "verified": self.verified,
        }


@dataclass
class Patch:
    """Generated patch."""

    hypothesis: Hypothesis
    patch_diff: str
    verified: bool = False
    applied: bool = False
    test_results: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hypothesis": self.hypothesis.to_dict(),
            "patch_diff": self.patch_diff,
            "verified": self.verified,
            "applied": self.applied,
            "test_results": self.test_results,
        }


@dataclass
class AnalysisState:
    """
    State data for the analysis workflow.

    Attributes:
        repo_path: Path to the repository being analyzed
        current_state: Current state name
        prefilter_result: Result from pre-filter pipeline
        symbol_graph: Symbol graph from repository mapping
        candidates: List of bug candidates
        hypotheses: List of bug hypotheses
        patches: List of generated patches
        verified_patches: List of verified patches
        escalated_issues: List of issues requiring escalation
        errors: List of errors encountered
        metadata: Additional metadata
    """

    repo_path: Optional[Path] = None
    current_state: str = "init"
    prefilter_result: Optional[Any] = None
    symbol_graph: Optional[Any] = None
    candidates: List[Candidate] = field(default_factory=list)
    hypotheses: List[Hypothesis] = field(default_factory=list)
    patches: List[Patch] = field(default_factory=list)
    verified_patches: List[Patch] = field(default_factory=list)
    escalated_issues: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "repo_path": str(self.repo_path) if self.repo_path else None,
            "current_state": self.current_state,
            "candidates_count": len(self.candidates),
            "hypotheses_count": len(self.hypotheses),
            "patches_count": len(self.patches),
            "verified_patches_count": len(self.verified_patches),
            "escalated_issues_count": len(self.escalated_issues),
            "errors_count": len(self.errors),
            "metadata": self.metadata,
        }


class StateGraphInput(TypedDict):
    """Input type for LangGraph state."""

    repo_path: str
    current_state: str
    prefilter_result: Optional[Dict[str, Any]]
    symbol_graph: Optional[Dict[str, Any]]
    candidates: List[Dict[str, Any]]
    hypotheses: List[Dict[str, Any]]
    patches: List[Dict[str, Any]]
    verified_patches: List[Dict[str, Any]]
    escalated_issues: List[Dict[str, Any]]
    errors: List[str]
    metadata: Dict[str, Any]


class StateMachine:
    """
    State machine for GlitchHunter workflow.

    Coordinates the analysis pipeline using LangGraph state machine
    with conditional transitions based on analysis results.

    States:
    1. Ingestion: Repository scanning, symbol graph building
    2. Shield: Pre-filtering (Semgrep, AST, complexity, Git churn)
    3. Hypothesis: Generate 3-5 hypotheses per candidate
    4. Analyzer: Test hypotheses causally
    5. Observer: Evaluate evidence
    6. LLiftPrioritizer: Prioritize candidates
    7. PatchLoop: Generate and verify patches
    8. Finalizer: Generate report and learn rules

    Example:
        >>> machine = StateMachine()
        >>> result = machine.run("/path/to/repo")
    """

    def __init__(self) -> None:
        """Initialize state machine."""
        self.workflow = self._build_graph()
        self.app = self.workflow.compile()

        logger.debug("StateMachine initialized")

    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph state machine.

        Returns:
            Configured StateGraph
        """
        workflow = StateGraph(StateGraphInput)

        # Add nodes (states)
        workflow.add_node("ingestion", self._ingestion_state)
        workflow.add_node("shield", self._shield_state)
        workflow.add_node("hypothesis", self._hypothesis_state)
        workflow.add_node("analyzer", self._analyzer_state)
        workflow.add_node("observer", self._observer_state)
        workflow.add_node("llift_prioritizer", self._llift_prioritizer_state)
        workflow.add_node("patch_loop", self._patch_loop_state)
        workflow.add_node("finalizer", self._finalizer_state)

        # Set entry point
        workflow.set_entry_point("ingestion")

        # Add edges with conditions
        workflow.add_conditional_edges(
            "ingestion",
            self._route_from_ingestion,
            {
                "shield": "shield",
                "error": END,
            },
        )

        workflow.add_conditional_edges(
            "shield",
            self._route_from_shield,
            {
                "hypothesis": "hypothesis",
                "finalizer": "finalizer",
                "error": END,
            },
        )

        workflow.add_conditional_edges(
            "hypothesis",
            self._route_from_hypothesis,
            {
                "analyzer": "analyzer",
                "finalizer": "finalizer",
                "error": END,
            },
        )

        workflow.add_conditional_edges(
            "analyzer",
            self._route_from_analyzer,
            {
                "observer": "observer",
                "error": END,
            },
        )

        workflow.add_conditional_edges(
            "observer",
            self._route_from_observer,
            {
                "llift_prioritizer": "llift_prioritizer",
                "escalate": "hypothesis",
                "error": END,
            },
        )

        workflow.add_conditional_edges(
            "llift_prioritizer",
            self._route_from_llift_prioritizer,
            {
                "patch_loop": "patch_loop",
                "finalizer": "finalizer",
                "error": END,
            },
        )

        workflow.add_conditional_edges(
            "patch_loop",
            self._route_from_patch_loop,
            {
                "patch_loop": "patch_loop",  # Loop for more patches
                "finalizer": "finalizer",
                "escalate": "hypothesis",  # Re-hypothesize on escalation
                "error": END,
            },
        )

        workflow.add_conditional_edges(
            "finalizer",
            self._route_from_finalizer,
            {
                "done": END,
                "error": END,
            },
        )

        return workflow

    def _ingestion_state(self, state: StateGraphInput) -> StateGraphInput:
        """
        Ingestion state: Parse repository and build symbol graph.

        Args:
            state: Current state

        Returns:
            Updated state
        """
        logger.info("Entering INGESTION state")

        try:
            repo_path = Path(state["repo_path"])

            if not repo_path.exists():
                state["errors"].append(f"Repository not found: {repo_path}")
                return state

            # Initialize repository mapper
            from ..mapper.repo_mapper import RepositoryMapper

            mapper = RepositoryMapper(repo_path)

            # Scan repository
            manifest = mapper.scan_repository()
            state["metadata"]["manifest"] = manifest.to_dict()

            # Build symbol graph
            symbol_graph = mapper.build_graph()
            state["symbol_graph"] = symbol_graph.to_dict()

            state["current_state"] = "ingestion"
            state["metadata"]["ingestion_complete"] = True
            state["metadata"]["repo_path"] = str(repo_path)
            state["metadata"]["symbol_count"] = len(symbol_graph)

            logger.info(
                f"Ingestion complete for {repo_path}: "
                f"{len(symbol_graph)} symbols"
            )

        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            state["errors"].append(f"Ingestion error: {e}")

        return state

    def _shield_state(self, state: StateGraphInput) -> StateGraphInput:
        """
        Shield state: Run pre-filter pipeline.

        Args:
            state: Current state

        Returns:
            Updated state
        """
        logger.info("Entering SHIELD state")

        try:
            from ..prefilter.pipeline import PreFilterPipeline

            repo_path = Path(state["repo_path"])

            pipeline = PreFilterPipeline(repo_path)
            result = pipeline.run()

            state["current_state"] = "shield"
            state["prefilter_result"] = {
                "security_findings": result.total_security_issues,
                "correctness_findings": result.total_correctness_issues,
                "complexity_hotspots": len(result.complexity_result.hotspots) if result.complexity_result else 0,
                "git_hotspots": len(result.churn_analysis.hotspots) if result.churn_analysis else 0,
                "prioritized_files": [
                    p.file_path for p in result.candidates[:20]
                ],
            }

            # Convert candidates
            state["candidates"] = [c.to_dict() for c in result.candidates]

            state["metadata"]["shield_complete"] = True

            logger.info(
                f"Shield complete: {result.total_security_issues} security, "
                f"{result.total_correctness_issues} correctness, "
                f"{len(result.candidates)} candidates"
            )

        except Exception as e:
            logger.error(f"Shield failed: {e}")
            state["errors"].append(f"Shield error: {e}")

        return state

    def _hypothesis_state(self, state: StateGraphInput) -> StateGraphInput:
        """
        Hypothesis state: Generate bug hypotheses.

        Args:
            state: Current state

        Returns:
            Updated state
        """
        logger.info("Entering HYPOTHESIS state")

        try:
            hypotheses = []

            # Generate hypotheses for top candidates
            for candidate_dict in state.get("candidates", [])[:10]:
                candidate = Candidate(
                    file_path=candidate_dict.get("file_path", ""),
                    bug_type=candidate_dict.get("bug_type", "unknown"),
                    description=candidate_dict.get("description", ""),
                    line_start=candidate_dict.get("line_start", 0),
                    line_end=candidate_dict.get("line_end", 0),
                    severity=candidate_dict.get("severity", "medium"),
                )

                # Generate 3-5 hypotheses per candidate
                for i in range(3):
                    hypothesis = Hypothesis(
                        candidate=candidate,
                        hypothesis=f"Hypothesis {i + 1} for {candidate.file_path}",
                        confidence=0.5 - (i * 0.1),
                    )
                    hypotheses.append(hypothesis)

            state["current_state"] = "hypothesis"
            state["hypotheses"] = [h.to_dict() for h in hypotheses]
            state["metadata"]["hypothesis_complete"] = True

            logger.info(f"Generated {len(hypotheses)} hypotheses")

        except Exception as e:
            logger.error(f"Hypothesis generation failed: {e}")
            state["errors"].append(f"Hypothesis error: {e}")

        return state

    def _analyzer_state(self, state: StateGraphInput) -> StateGraphInput:
        """
        Analyzer state: Test hypotheses causally.

        Args:
            state: Current state

        Returns:
            Updated state
        """
        logger.info("Entering ANALYZER state")

        try:
            # Test each hypothesis
            for hyp_dict in state.get("hypotheses", []):
                hyp_dict["tested"] = True
                # Simulate causal testing
                hyp_dict["verified"] = True  # Placeholder

            state["current_state"] = "analyzer"
            state["metadata"]["analyzer_complete"] = True

            logger.info(f"Tested {len(state.get('hypotheses', []))} hypotheses")

        except Exception as e:
            logger.error(f"Analyzer failed: {e}")
            state["errors"].append(f"Analyzer error: {e}")

        return state

    def _observer_state(self, state: StateGraphInput) -> StateGraphInput:
        """
        Observer state: Evaluate evidence.

        Args:
            state: Current state

        Returns:
            Updated state
        """
        logger.info("Entering OBSERVER state")

        try:
            # Evaluate evidence for each hypothesis
            for hyp_dict in state.get("hypotheses", []):
                if hyp_dict.get("verified"):
                    hyp_dict["evidence"].append("Evidence from causal analysis")

            state["current_state"] = "observer"
            state["metadata"]["observer_complete"] = True

            logger.info("Evidence evaluation complete")

        except Exception as e:
            logger.error(f"Observer failed: {e}")
            state["errors"].append(f"Observer error: {e}")

        return state

    def _llift_prioritizer_state(self, state: StateGraphInput) -> StateGraphInput:
        """
        LLiftPrioritizer state: Prioritize candidates.

        Args:
            state: Current state

        Returns:
            Updated state
        """
        logger.info("Entering LLIFT_PRIORITIZER state")

        try:
            # Sort hypotheses by confidence
            hypotheses = state.get("hypotheses", [])
            hypotheses.sort(key=lambda h: h.get("confidence", 0), reverse=True)
            state["hypotheses"] = hypotheses

            state["current_state"] = "llift_prioritizer"
            state["metadata"]["prioritizer_complete"] = True

            logger.info(f"Prioritized {len(hypotheses)} hypotheses")

        except Exception as e:
            logger.error(f"LLiftPrioritizer failed: {e}")
            state["errors"].append(f"LLiftPrioritizer error: {e}")

        return state

    def _patch_loop_state(self, state: StateGraphInput) -> StateGraphInput:
        """
        Patch loop state: Generate and verify patches iteratively.

        Args:
            state: Current state

        Returns:
            Updated state
        """
        logger.info("Entering PATCH_LOOP state")

        try:
            patches = []

            # Generate patches for verified hypotheses
            for hyp_dict in state.get("hypotheses", []):
                if hyp_dict.get("verified"):
                    patch = Patch(
                        hypothesis=Hypothesis(
                            candidate=Candidate(
                                file_path=hyp_dict["candidate"]["file_path"],
                                bug_type=hyp_dict["candidate"]["bug_type"],
                                description=hyp_dict["candidate"]["description"],
                                line_start=hyp_dict["candidate"]["line_start"],
                                line_end=hyp_dict["candidate"]["line_end"],
                            ),
                            hypothesis=hyp_dict["hypothesis"],
                            confidence=hyp_dict["confidence"],
                            evidence=hyp_dict.get("evidence", []),
                            tested=hyp_dict.get("tested", False),
                            verified=hyp_dict.get("verified", False),
                        ),
                        patch_diff=f"# TODO: Generate patch for {hyp_dict['hypothesis']}",
                        verified=False,
                        applied=False,
                    )
                    patches.append(patch)

            state["current_state"] = "patch_loop"
            state["patches"] = [p.to_dict() for p in patches]
            state["metadata"]["patch_loop_complete"] = True

            logger.info(f"Generated {len(patches)} patches")

        except Exception as e:
            logger.error(f"Patch loop failed: {e}")
            state["errors"].append(f"Patch loop error: {e}")

        return state

    def _finalizer_state(self, state: StateGraphInput) -> StateGraphInput:
        """
        Finalizer state: Generate report and learn rules.

        Args:
            state: Current state

        Returns:
            Updated state
        """
        logger.info("Entering FINALIZER state")

        try:
            state["current_state"] = "finalizer"
            state["metadata"]["finalizer_complete"] = True
            state["metadata"]["analysis_complete"] = True

            # Generate summary
            state["metadata"]["summary"] = {
                "candidates_analyzed": len(state.get("candidates", [])),
                "hypotheses_generated": len(state.get("hypotheses", [])),
                "patches_generated": len(state.get("patches", [])),
                "verified_patches": len(state.get("verified_patches", [])),
            }

            logger.info("Finalizer complete")

        except Exception as e:
            logger.error(f"Finalizer failed: {e}")
            state["errors"].append(f"Finalizer error: {e}")

        return state

    def _route_from_ingestion(
        self, state: StateGraphInput
    ) -> Literal["shield", "error"]:
        """Route from ingestion state."""
        if state.get("errors"):
            return "error"
        return "shield"

    def _route_from_shield(
        self, state: StateGraphInput
    ) -> Literal["hypothesis", "finalizer", "error"]:
        """Route from shield state."""
        if state.get("errors"):
            return "error"

        candidates = state.get("candidates", [])
        if not candidates:
            return "finalizer"

        return "hypothesis"

    def _route_from_hypothesis(
        self, state: StateGraphInput
    ) -> Literal["analyzer", "finalizer", "error"]:
        """Route from hypothesis state."""
        if state.get("errors"):
            return "error"

        hypotheses = state.get("hypotheses", [])
        if not hypotheses:
            return "finalizer"

        return "analyzer"

    def _route_from_analyzer(
        self, state: StateGraphInput
    ) -> Literal["observer", "error"]:
        """Route from analyzer state."""
        if state.get("errors"):
            return "error"
        return "observer"

    def _route_from_observer(
        self, state: StateGraphInput
    ) -> Literal["llift_prioritizer", "escalate", "error"]:
        """Route from observer state."""
        if state.get("errors"):
            return "error"

        # Check if any hypotheses were verified
        hypotheses = state.get("hypotheses", [])
        verified = [h for h in hypotheses if h.get("verified")]

        if not verified:
            return "escalate"

        return "llift_prioritizer"

    def _route_from_llift_prioritizer(
        self, state: StateGraphInput
    ) -> Literal["patch_loop", "finalizer", "error"]:
        """Route from llift_prioritizer state."""
        if state.get("errors"):
            return "error"

        hypotheses = state.get("hypotheses", [])
        verified = [h for h in hypotheses if h.get("verified")]

        if not verified:
            return "finalizer"

        return "patch_loop"

    def _route_from_patch_loop(
        self,
        state: StateGraphInput,
    ) -> Literal["patch_loop", "finalizer", "escalate", "error"]:
        """Route from patch loop state."""
        if state.get("errors"):
            return "error"

        patches = state.get("patches", [])
        verified = state.get("verified_patches", [])

        # Continue looping if we have unverified patches
        if len(verified) < len(patches) and len(patches) < 10:
            return "patch_loop"

        # Escalate if no patches were verified
        if len(verified) == 0 and len(patches) > 0:
            return "escalate"

        return "finalizer"

    def _route_from_finalizer(
        self, state: StateGraphInput
    ) -> Literal["done", "error"]:
        """Route from finalizer state."""
        if state.get("errors"):
            return "error"
        return "done"

    def run(self, repo_path: str) -> Dict[str, Any]:
        """
        Run the complete workflow.

        Args:
            repo_path: Path to repository

        Returns:
            Final state dictionary
        """
        logger.info(f"Starting workflow for {repo_path}")

        initial_state: StateGraphInput = {
            "repo_path": repo_path,
            "current_state": "init",
            "prefilter_result": None,
            "symbol_graph": None,
            "candidates": [],
            "hypotheses": [],
            "patches": [],
            "verified_patches": [],
            "escalated_issues": [],
            "errors": [],
            "metadata": {},
        }

        try:
            result = self.app.invoke(initial_state)
            logger.info("Workflow completed")
            return result

        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            return {
                "repo_path": repo_path,
                "current_state": "error",
                "errors": [str(e)],
                "metadata": {"workflow_failed": True},
            }


def build_workflow() -> StateMachine:
    """
    Build and return a new state machine instance.

    Returns:
        Configured StateMachine
    """
    return StateMachine()
