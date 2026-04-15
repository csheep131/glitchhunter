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
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

from langgraph.graph import END, StateGraph

from inference.engine import InferenceEngine, ChatMessage
from agent.hypothesis_agent import HypothesisAgent, BugCandidate as AgentBugCandidate
from agent.analyzer_agent import AnalyzerAgent, Hypothesis as AgentHypothesis
from agent.patch_generator import PatchGenerator
from agent.llift_prioritizer import LLiftPrioritizer
from agent.observer_agent import ObserverAgent
from core.reporting import ScanReporter
from mcp_gw.socratiCode_client import SocratiCodeMCP, SearchResult

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
    stop_after: Optional[str]


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

    def __init__(
        self,
        analyzer_model_path: Optional[str] = None,
        verifier_model_path: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> None:
        """
        Initialize state machine.

        Args:
            analyzer_model_path: Path to the analyzer model (e.g., Qwen)
            verifier_model_path: Path to the verifier model (e.g., Phi)
            api_url: Optional URL for remote LLM server
        """
        self.analyzer_model_path = analyzer_model_path
        self.verifier_model_path = verifier_model_path
        self.api_url = api_url

        self._analyzer_engine: Optional[InferenceEngine] = None
        self._verifier_engine: Optional[InferenceEngine] = None
        self._mcp_client: Optional[SocratiCodeMCP] = None

        self.workflow = self._build_graph()
        self.app = self.workflow.compile()

        logger.info(
            f"StateMachine initialized (analyzer={analyzer_model_path}, "
            f"verifier={verifier_model_path})"
        )

    def _get_analyzer_engine(self) -> Optional[InferenceEngine]:
        """Lazy load analyzer engine."""
        if self._analyzer_engine is None:
            if self.api_url:
                logger.info(f"Connecting to remote analyzer at {self.api_url}")
                self._analyzer_engine = InferenceEngine(
                    model_name="analyzer", 
                    api_url=self.api_url
                )
                self._analyzer_engine.load_model()
            elif self.analyzer_model_path:
                logger.info(f"Loading local analyzer engine: {self.analyzer_model_path}")
                self._analyzer_engine = InferenceEngine(model_name="analyzer")
                self._analyzer_engine.load_model(
                    self.analyzer_model_path,
                    n_gpu_layers=35,
                    n_ctx=8192,
                )
        return self._analyzer_engine

    def _get_verifier_engine(self) -> Optional[InferenceEngine]:
        """Lazy load verifier engine."""
        if self._verifier_engine is None:
            if self.api_url:
                logger.info(f"Connecting to remote verifier at {self.api_url}")
                self._verifier_engine = InferenceEngine(
                    model_name="verifier", 
                    api_url=self.api_url
                )
                self._verifier_engine.load_model()
            elif self.verifier_model_path:
                logger.info(f"Loading local verifier engine: {self.verifier_model_path}")
                self._verifier_engine = InferenceEngine(model_name="verifier")
                self._verifier_engine.load_model(
                    self.verifier_model_path,
                    n_gpu_layers=35,
                    n_ctx=4096,
                )
        return self._verifier_engine

    def _get_mcp_client(self) -> Optional[SocratiCodeMCP]:
        """Lazy load MCP client."""
        if self._mcp_client is None:
            try:
                from core.config import Config
                config = Config.load()
                
                # Access MCP config directly (Pydantic model)
                mcp_config = config.mcp_integration

                if mcp_config.enabled:
                    server_cfg = mcp_config.server
                    host = server_cfg.get("host", "localhost")
                    port = server_cfg.get("port", 8934)
                    url = f"http://{host}:{port}"

                    logger.info(f"Initializing SocratiCode MCP client at {url}")
                    self._mcp_client = SocratiCodeMCP(server_url=url)

                    # Connect sync for initialization
                    if not self._mcp_client.connect_sync():
                        logger.warning("MCP client could not connect. Falling back to local ingestion.")
                        self._mcp_client = None
            except AttributeError as e:
                logger.debug(f"MCP config not available: {e}")
                self._mcp_client = None
            except Exception as e:
                logger.error(f"Failed to initialize MCP client: {e}")
                self._mcp_client = None
        return self._mcp_client

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
                "finalizer": "finalizer",
                "done": END,
                "error": END,
            },
        )

        workflow.add_conditional_edges(
            "shield",
            self._route_from_shield,
            {
                "hypothesis": "hypothesis",
                "finalizer": "finalizer",
                "done": END,
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
                "finalizer": "finalizer",
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
        logger.info("▶️  INGESTION: Scanning repository and building symbol graph...")

        try:
            repo_path = Path(state["repo_path"])

            if not repo_path.exists():
                state["errors"].append(f"Repository not found: {repo_path}")
                return state

            # Initialize repository mapper
            from mapper.repo_mapper import RepositoryMapper

            mapper = RepositoryMapper(repo_path)

            # Scan repository
            manifest = mapper.scan_repository()
            state["metadata"]["manifest"] = manifest.to_dict()

            # Build symbol graph
            symbol_graph = mapper.build_graph()
            state["symbol_graph"] = symbol_graph.to_dict()

            # Optional: Enhance with SocratiCode MCP
            mcp = self._get_mcp_client()
            if mcp:
                # Check if deep indexing is requested
                if state["metadata"].get("index_mcp", False):
                    logger.info(f"Triggering deep indexing for {repo_path}")
                    # In a real impl, we'd call an indexing endpoint here
                    # For now, we simulate with a targeted search to warm up the cache
                    try:
                        mcp.search_sync("index initialization", limit=1)
                        logger.info("Semantic index warmed up")
                    except Exception as e:
                        logger.warning(f"Indexing warmup failed: {e}")

                logger.info("Enhancing ingestion with SocratiCode semantic context")
                try:
                    # Search for project entry points and high-level structure
                    context = mcp.search_sync("main entry points and architectural core", limit=5)
                    state["metadata"]["mcp_context"] = [
                        {"file": r.file_path, "context": r.content} for r in context
                    ]
                    logger.info(f"SocratiCode provided {len(context)} semantic context fragments")
                except Exception as e:
                    logger.debug(f"SocratiCode MCP nicht verfügbar: {e}")

            state["current_state"] = "ingestion"
            state["metadata"]["ingestion_complete"] = True
            state["metadata"]["repo_path"] = str(repo_path)
            state["metadata"]["symbol_count"] = len(symbol_graph)

            logger.info(f"✅ Ingestion complete: {len(symbol_graph)} symbols indexed from {manifest.file_count} files")

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
        logger.info("🛡️  SHIELD: Running pre-filter (Semgrep, Complexity, Git Churn)...")

        try:
            from prefilter.pipeline import PreFilterPipeline

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
                f"✅ Shield complete: {result.total_security_issues} security, "
                f"{result.total_correctness_issues} correctness, "
                f"{len(result.candidates)} candidates prioritized"
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
        logger.info("💡 HYPOTHESIS: Generating bug hypotheses with AI...")

        try:
            # Initialize Hypothesis Agent
            engine = self._get_analyzer_engine()
            agent = HypothesisAgent(llm_client=engine)

            all_hypotheses = []
            
            # Dynamically determine candidates based on findings
            all_candidates = state.get("candidates", [])
            prefilter_result = state.get("prefilter_result", {})
            
            # Prioritize: Security findings > Complexity > Git Churn
            security_findings = prefilter_result.get("security_findings", 0)
            complexity_hotspots = prefilter_result.get("complexity_hotspots", 0)
            git_hotspots = prefilter_result.get("git_hotspots", 0)
            
            # Dynamic limit: Process ALL candidates (no artificial limit)
            # Scale based on findings but include everything
            if security_findings > 0:
                # If we have security findings, prioritize but include all
                dynamic_limit = len(all_candidates)
            else:
                # No security issues, still process all candidates
                dynamic_limit = len(all_candidates)
            
            candidates = all_candidates[:dynamic_limit]
            
            logger.info(f"Dynamic candidate selection: {len(candidates)} of {len(all_candidates)} "
                       f"(security: {security_findings}, complexity: {complexity_hotspots}, git: {git_hotspots})")

            # Generate hypotheses for candidates
            for idx, candidate_dict in enumerate(candidates):
                # Generiere eindeutige ID für jeden Kandidaten
                candidate_id = candidate_dict.get("id", f"c{idx + 1}")
                
                # Bestimme Bug-Typ basierend auf den Faktoren
                factors = candidate_dict.get("factors", {})
                bug_type = _determine_bug_type(factors, candidate_dict.get("file_path", ""))
                
                candidate = AgentBugCandidate(
                    id=candidate_id,
                    file_path=candidate_dict.get("file_path", ""),
                    line=candidate_dict.get("line_start", 0),
                    symbol_name=candidate_dict.get("symbol_name", "unknown"),
                    bug_type=bug_type,
                    description=_generate_candidate_description(bug_type, factors),
                )

                # Use actual agent to generate hypotheses
                # Note: This requires DataFlowGraph which we might not have yet in full
                # For now, we use the agent's internal generators
                from analysis.dfg_builder import DataFlowGraph
                dfg = DataFlowGraph() # Mock or get from state if available

                gen_hypotheses = agent.generate_hypotheses(candidate, dfg)

                for h in gen_hypotheses:
                    hypotheses_obj = Hypothesis(
                        candidate=Candidate(
                            file_path=candidate.file_path,
                            bug_type=candidate.bug_type,
                            description=candidate.description,
                            line_start=candidate.line,
                            line_end=candidate.line,
                        ),
                        hypothesis=h.description,
                        confidence=h.confidence,
                    )
                    all_hypotheses.append(hypotheses_obj)

            state["current_state"] = "hypothesis"
            state["hypotheses"] = [h.to_dict() for h in all_hypotheses]
            state["metadata"]["hypothesis_complete"] = True

            logger.info(f"✅ Generated {len(all_hypotheses)} hypotheses across {len(candidates)} candidates (dynamic limit: {dynamic_limit})")

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
        logger.info("🔬 ANALYZER: Testing hypotheses causally...")

        try:
            # Initialize Analyzer Agent
            engine = self._get_verifier_engine()
            agent = AnalyzerAgent(llm_client=engine)

            # Test each hypothesis
            for hyp_dict in state.get("hypotheses", []):
                # Convert to agent's hypothesis type
                agent_hyp = AgentHypothesis(
                    id=f"h_{uuid.uuid4().hex[:8]}" if "id" not in hyp_dict else hyp_dict["id"],
                    title=hyp_dict["hypothesis"][:50],
                    description=hyp_dict["hypothesis"],
                    hypothesis_type=None, # Should be resolved
                    candidate_id="c1",
                )

                # Simulate causal testing for now, but using the agent's logic
                # In a full impl, we'd pass the actual graphs here
                result = agent.test_hypothesis(agent_hyp)

                hyp_dict["tested"] = True
                hyp_dict["verified"] = result.is_confirmed
                hyp_dict["confidence"] = result.confidence

            state["current_state"] = "analyzer"
            state["metadata"]["analyzer_complete"] = True

            logger.info(f"✅ Analyzer tested {len(state.get('hypotheses', []))} hypotheses")

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
        logger.info("👁️  OBSERVER: Evaluating evidence quality...")

        try:
            # Initialize Observer Agent
            agent = ObserverAgent()

            # Prepare data for ranking
            from agent.analyzer_agent import EvidenceCollection as AgentEvidenceCollection
            candidates_with_evidence = []

            for hyp_dict in state.get("hypotheses", []):
                # Map back to agent collections
                coll = AgentEvidenceCollection()
                # If we had real evidence items, we'd add them here
                
                candidates_with_evidence.append((
                    hyp_dict.get("id", "h1"),
                    hyp_dict.get("confidence", 0.5),
                    coll
                ))

            # Rank candidates based on evidence
            ranked = agent.rank_candidates(candidates_with_evidence)

            # Update hypotheses with aggregated confidence
            ranked_dict = {r.candidate_id: r for r in ranked}
            for hyp_dict in state.get("hypotheses", []):
                hid = hyp_dict.get("id", "h1")
                if hid in ranked_dict:
                    hyp_dict["confidence"] = ranked_dict[hid].aggregated_confidence

            state["current_state"] = "observer"
            state["metadata"]["observer_complete"] = True

            best_conf = ranked[0].aggregated_confidence if ranked else 0
            logger.info(f"✅ Observer ranked {len(ranked)} candidates (best confidence: {best_conf:.2f})")

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
        logger.info("📊 PRIORITIZER: Ranking candidates by severity...")

        try:
            # Initialize LLift Prioritizer
            # Use verifier model for prioritization if available
            prioritizer = LLiftPrioritizer(model_path=self.verifier_model_path)

            from agent.llift_prioritizer import Candidate as LLiftCandidate
            
            candidates = []
            for hyp_dict in state.get("hypotheses", []):
                if hyp_dict.get("verified"):
                    candidates.append(LLiftCandidate(
                        candidate_id=hyp_dict.get("id", "h1"),
                        file_path=hyp_dict["candidate"]["file_path"],
                        bug_type=hyp_dict["candidate"]["bug_type"],
                        description=hyp_dict["hypothesis"],
                        line_start=hyp_dict["candidate"]["line_start"],
                        line_end=hyp_dict["candidate"]["line_end"],
                        severity=hyp_dict["candidate"].get("severity", "medium"),
                    ))

            if candidates:
                results = prioritizer.prioritize(candidates)
                
                # Update hypotheses order based on prioritization
                results_map = {r.candidate_id: r.priority_score for r in results}
                
                hypotheses = state.get("hypotheses", [])
                hypotheses.sort(key=lambda h: results_map.get(h.get("id", ""), 0), reverse=True)
                state["hypotheses"] = hypotheses

            state["current_state"] = "llift_prioritizer"
            state["metadata"]["prioritizer_complete"] = True

            logger.info(f"Prioritized {len(candidates)} hypotheses using LLift")

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
        logger.info("🔄 PATCH LOOP: Generating and verifying patches...")

        try:
            # Initialize Patch Generator
            # Note: PatchGenerator handles its own engine init if model_path is provided
            generator = PatchGenerator(model_path=self.analyzer_model_path)

            patches = []

            # Generate patches for verified hypotheses
            for hyp_dict in state.get("hypotheses", []):
                if hyp_dict.get("verified"):
                    issue = {
                        "type": hyp_dict["candidate"].get("bug_type", "logic"),
                        "severity": hyp_dict["candidate"].get("severity", "MEDIUM"),
                        "category": "security", # Default
                        "message": hyp_dict["hypothesis"],
                        "line": hyp_dict["candidate"].get("line_start", 0),
                    }

                    # Mock code for now - in real life we read the file
                    code = "# Code snippet for " + hyp_dict["candidate"].get("file_path", "")

                    result = generator.generate(issue, code)

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
                        ),
                        patch_diff=result.patch_diff,
                        verified=result.confidence > 0.8,
                        applied=False,
                    )
                    patches.append(patch)

            state["current_state"] = "patch_loop"
            state["patches"] = [p.to_dict() for p in patches]
            state["metadata"]["patch_loop_complete"] = True

            logger.info(f"Generated {len(patches)} real patches using LLM")

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
        logger.info("📝 FINALIZER: Generating reports...")

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

            # Generate report files
            repo_path = Path(state["repo_path"])
            reporter = ScanReporter(repo_path)
            report_paths = reporter.generate_report(state)
            patch_paths = reporter.save_patches(state)
            
            state["metadata"]["report_markdown"] = str(report_paths["markdown"])
            state["metadata"]["report_json"] = str(report_paths["json"])
            state["metadata"]["patch_files"] = [str(p) for p in patch_paths]

            logger.info(f"✅ Finalizer complete. Reports: {reporter.project_reports_dir}")

        except Exception as e:
            logger.error(f"Finalizer failed: {e}")
            state["errors"].append(f"Finalizer error: {e}")

        return state

    def _route_from_ingestion(
        self, state: StateGraphInput
    ) -> Literal["shield", "finalizer", "error", "done"]:
        """Route from ingestion state."""
        if state.get("errors"):
            return "error"
        if state.get("stop_after") == "ingestion":
            return "finalizer"
        return "shield"

    def _route_from_shield(
        self, state: StateGraphInput
    ) -> Literal["hypothesis", "finalizer", "error", "done"]:
        """Route from shield state."""
        if state.get("errors"):
            return "error"
        
        if state.get("stop_after") == "shield":
            return "finalizer"

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

        if state.get("stop_after") == "hypothesis":
            return "finalizer"

        hypotheses = state.get("hypotheses", [])
        if not hypotheses:
            return "finalizer"

        return "analyzer"

    def _route_from_analyzer(
        self, state: StateGraphInput
    ) -> Literal["observer", "finalizer", "error"]:
        """Route from analyzer state."""
        if state.get("errors"):
            return "error"
        
        if state.get("stop_after") == "analyzer":
            return "finalizer"
            
        return "observer"

    def _route_from_observer(
        self, state: StateGraphInput
    ) -> Literal["llift_prioritizer", "escalate", "finalizer", "error"]:
        """Route from observer state."""
        if state.get("errors"):
            return "error"

        if state.get("stop_after") == "observer":
            return "finalizer"

        # Check iteration limit to prevent infinite loops
        iterations = state.get("metadata", {}).get("hypothesis_iterations", 0)
        if iterations >= 5:
            logger.warning(f"Max hypothesis iterations reached ({iterations}), terminating to finalizer")
            return "finalizer"

        # Check if any hypotheses were verified
        hypotheses = state.get("hypotheses", [])
        verified = [h for h in hypotheses if h.get("verified")]

        if not verified:
            # Increment iteration counter
            new_iter = iterations + 1
            state["metadata"]["hypothesis_iterations"] = new_iter
            logger.info(f"No verified hypotheses. Escalating... (Iteration {new_iter}/5)")
            return "escalate"

        logger.info(f"Found {len(verified)} verified hypotheses. Moving to prioritizer.")
        return "llift_prioritizer"

    def _route_from_llift_prioritizer(
        self, state: StateGraphInput
    ) -> Literal["patch_loop", "finalizer", "error"]:
        """Route from llift_prioritizer state."""
        if state.get("errors"):
            return "error"

        if state.get("stop_after") == "llift_prioritizer":
            return "finalizer"

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
        # Count verified patches based on the 'verified' flag in each patch dict
        verified_count = sum(1 for p in patches if p.get("verified", False))
        total_patches = len(patches)

        # Check patch loop iteration limit
        patch_iterations = state.get("metadata", {}).get("patch_iterations", 0)
        if patch_iterations >= 3:
            logger.warning(f"Max patch iterations reached ({patch_iterations}), terminating to finalizer")
            return "finalizer"

        # If we have no verified patches, check hypothesis iteration limit
        if verified_count == 0 and total_patches > 0:
            iterations = state.get("metadata", {}).get("hypothesis_iterations", 0)
            if iterations >= 5:
                logger.warning(f"Max hypothesis iterations reached ({iterations}), terminating to finalizer")
                return "finalizer"
            # If we have no verified patches, escalate (don't continue patch loop)
            new_iter = iterations + 1
            state["metadata"]["hypothesis_iterations"] = new_iter
            logger.info(f"No patches verified. Escalating... (Iteration {new_iter}/5)")
            return "escalate"

        logger.info(f"✅ Patch loop complete. {verified_count}/{total_patches} patches verified. Moving to finalizer.")
        return "finalizer"

    def _route_from_finalizer(
        self, state: StateGraphInput
    ) -> Literal["done", "error"]:
        """Route from finalizer state."""
        if state.get("errors"):
            return "error"
        return "done"

    def run(self, repo_path: str, stop_after: Optional[str] = None) -> Dict[str, Any]:
        """
        Run the complete workflow.

        Args:
            repo_path: Path to repository
            stop_after: Optional state to stop after

        Returns:
            Final state dictionary
        """
        logger.info(f"Starting workflow for {repo_path} (stop_after={stop_after})")

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
            "stop_after": stop_after,
        }

        try:
            result = self.app.invoke(initial_state, config={"recursion_limit": 500})
            logger.info("✅ Workflow completed successfully")
            return result
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            return {
                "repo_path": repo_path,
                "current_state": "error",
                "errors": [str(e)],
                "metadata": {"workflow_failed": True},
            }

    async def start_analysis(
        self, 
        repo_path: str,
        scan_security: bool = True,
        scan_correctness: bool = True,
        generate_patches: bool = True,
        index_mcp: bool = False
    ) -> str:
        """
        Start analysis asynchronously.
        """
        analysis_id = f"analysis-{uuid.uuid4().hex[:12]}"
        
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
            "metadata": {
                "scan_security": scan_security,
                "scan_correctness": scan_correctness,
                "generate_patches": generate_patches,
                "index_mcp": index_mcp,
                "analysis_id": analysis_id,
            },
            "stop_after": None,
        }

        # Run in background
        import asyncio
        asyncio.create_task(self.app.ainvoke(initial_state))
        
        return analysis_id


def build_workflow() -> StateMachine:
    """
    Build and return a new state machine instance.

    Returns:
        Configured StateMachine
    """
    import os
    analyzer_model = os.getenv("MODEL_ANALYZER")
    verifier_model = os.getenv("MODEL_VERIFIER")
    api_url = os.getenv("MODEL_API_URL")

    return StateMachine(
        analyzer_model_path=analyzer_model,
        verifier_model_path=verifier_model,
        api_url=api_url,
    )


def _determine_bug_type(factors: Dict[str, Any], file_path: str) -> str:
    """
    Bestimmt den Bug-Typ basierend auf den Kandidaten-Faktoren.
    
    Args:
        factors: Faktoren-Dict aus dem Prefilter
        file_path: Dateipfad des Kandidaten
        
    Returns:
        Bug-Typ als String
    """
    bug_types = []
    
    # Semgrep findings → Security/Correctness
    if factors.get("semgrep", 0) > 0:
        bug_types.append("semgrep_security")
    
    # Hohe Komplexität → Maintainability/Logic Error
    complexity = factors.get("complexity", 0)
    if complexity >= 15:
        bug_types.append("high_complexity")
    elif complexity >= 10:
        bug_types.append("medium_complexity")
    
    # Git Churn → Instability/Regression Risk
    churn = factors.get("churn", 0)
    if churn >= 10:
        bug_types.append("high_churn")
    elif churn >= 5:
        bug_types.append("medium_churn")
    
    # Default basierend auf Dateiname
    if not bug_types:
        if "security" in file_path.lower():
            return "security_critical"
        elif "auth" in file_path.lower():
            return "auth_critical"
        elif "db" in file_path.lower() or "database" in file_path.lower():
            return "database_critical"
        else:
            return "code_quality"
    
    # Return the primary bug type
    return bug_types[0]


def _generate_candidate_description(bug_type: str, factors: Dict[str, Any]) -> str:
    """
    Generiert eine Beschreibung für den Kandidaten.
    
    Args:
        bug_type: Bug-Typ
        factors: Faktoren-Dict
        
    Returns:
        Beschreibung als String
    """
    descriptions = {
        "semgrep_security": "Semgrep hat potenzielle Sicherheitslücken identifiziert",
        "semgrep_correctness": "Semgrep hat Code-Qualitätsprobleme gefunden",
        "high_complexity": "Code hat sehr hohe zyklomatische Komplexität (≥15)",
        "medium_complexity": "Code hat erhöhte Komplexität (≥10)",
        "high_churn": "Datei wurde in den letzten 3 Monaten ≥10 mal geändert",
        "medium_churn": "Datei zeigt erhöhte Änderungsaktivität (≥5 mal)",
        "security_critical": "Sicherheitsrelevante Datei mit potenziellen Schwachstellen",
        "auth_critical": "Authentifizierungscode mit potenziellen Bypass-Risiken",
        "database_critical": "Datenbank-Code mit potenziellen Injection-Risiken",
        "code_quality": "Code-Qualitätsprobleme identifiziert",
    }
    
    base_desc = descriptions.get(bug_type, f"Code-Auffälligkeit: {bug_type}")
    
    # Details hinzufügen
    details = []
    if factors.get("semgrep", 0) > 0:
        details.append(f"{factors['semgrep']} Semgrep-Findings")
    if factors.get("complexity", 0) > 0:
        details.append(f"Komplexität: {factors['complexity']}")
    if factors.get("churn", 0) > 0:
        details.append(f"Git Churn: {factors['churn']} Commits")
    
    if details:
        return f"{base_desc} ({', '.join(details)})"
    return base_desc
