"""
Analyzer Agent for GlitchHunter.

Performs causal testing of hypotheses using call-graph and data-flow analysis.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from analysis.cfg_builder import ControlFlowGraph
from analysis.dfg_builder import (
    DataFlow,
    DataFlowGraph,
    DataFlowGraphBuilder,
)
from core.logging_config import get_logger

from agent.hypothesis_agent import Hypothesis

logger = get_logger(__name__)


class EvidenceType(str, Enum):
    """Types of evidence."""

    DIRECT_DATA_FLOW = "direct_data_flow"
    CALL_CHAIN = "call_chain"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    PATTERN_MATCH = "pattern_match"
    CONTROL_FLOW = "control_flow"
    TAINT_PATH = "taint_path"


@dataclass
class FileLocation:
    """
    Represents a file location.

    Attributes:
        file_path: Source file path
        line: Line number
        column: Column number (optional)
    """

    file_path: str
    line: int
    column: int = 0


@dataclass
class CallPath:
    """
    Represents a call path in the call graph.

    Attributes:
        path: List of symbol names in the path
        length: Path length
        file_locations: List of file locations
    """

    path: List[str]
    length: int = 0
    file_locations: List[FileLocation] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Calculate path length after initialization."""
        self.length = len(self.path)


@dataclass
class DataFlowPath:
    """
    Represents a data flow path.

    Attributes:
        path: List of node identifiers in the path
        flow_type: Type of data flow
        has_taint: Whether the path has taint
        is_sanitized: Whether the path is sanitized
    """

    path: List[str]
    flow_type: str = ""
    has_taint: bool = False
    is_sanitized: bool = False


@dataclass
class CFGPath:
    """
    Represents a control-flow graph path.

    Attributes:
        path: List of block IDs in the path
        length: Path length
        has_branch: Whether the path contains branches
        has_loop: Whether the path contains loops
    """

    path: List[str]
    length: int = 0
    has_branch: bool = False
    has_loop: bool = False

    def __post_init__(self) -> None:
        """Calculate path length after initialization."""
        self.length = len(self.path)


@dataclass
class Evidence:
    """
    Represents a piece of evidence.

    Attributes:
        evidence_type: Type of evidence
        description: Description of the evidence
        weight: Evidence weight (0.0-1.0)
        quality: Evidence quality (1.0 direct, 0.7 indirect, 0.5 semantic)
    """

    evidence_type: EvidenceType
    description: str
    weight: float = 1.0
    quality: float = 1.0


@dataclass
class EvidenceCollection:
    """
    Collection of evidence for a hypothesis.

    Attributes:
        positive_evidence: List of positive evidence
        negative_evidence: List of negative evidence
        evidence_score: Overall evidence score
    """

    positive_evidence: List[Evidence] = field(default_factory=list)
    negative_evidence: List[Evidence] = field(default_factory=list)
    evidence_score: float = 0.0

    def add_positive(self, evidence: Evidence) -> None:
        """Add positive evidence."""
        self.positive_evidence.append(evidence)
        self._recalculate_score()

    def add_negative(self, evidence: Evidence) -> None:
        """Add negative evidence."""
        self.negative_evidence.append(evidence)
        self._recalculate_score()

    def _recalculate_score(self) -> None:
        """Recalculate the overall evidence score."""
        positive_score = sum(
            e.weight * e.quality for e in self.positive_evidence
        )
        negative_score = sum(
            e.weight * e.quality for e in self.negative_evidence
        )

        # Normalize score to 0.0-1.0
        total = positive_score + negative_score
        if total > 0:
            self.evidence_score = positive_score / total
        else:
            self.evidence_score = 0.0


@dataclass
class HypothesisTestResult:
    """
    Result of testing a hypothesis.

    Attributes:
        hypothesis: The tested hypothesis
        is_confirmed: Whether the hypothesis is confirmed
        confidence: Confidence score
        evidence_collection: Collection of evidence
        call_paths: List of call paths
        data_flow_paths: List of data flow paths
        cfg_paths: List of CFG paths
    """

    hypothesis: Hypothesis
    is_confirmed: bool = False
    confidence: float = 0.0
    evidence_collection: EvidenceCollection = field(default_factory=EvidenceCollection)
    call_paths: List[CallPath] = field(default_factory=list)
    data_flow_paths: List[DataFlowPath] = field(default_factory=list)
    cfg_paths: List[CFGPath] = field(default_factory=list)


class AnalyzerAgent:
    """
    Analyzer Agent for causal hypothesis testing.

    Tests hypotheses by walking call graphs, data flows, and control-flow
    graphs to collect evidence.
    """

    def __init__(
        self,
        symbol_graph: Optional[nx.DiGraph] = None,
        llm_client: Optional[Any] = None,
    ) -> None:
        """
        Initialize the Analyzer Agent.

        Args:
            symbol_graph: Optional symbol graph for call analysis
            llm_client: Optional LLM client for semantic analysis
        """
        self._symbol_graph = symbol_graph
        self._llm_client = llm_client
        self._test_results: List[HypothesisTestResult] = []

    def test_hypothesis(
        self,
        hypothesis: Hypothesis,
        symbol_graph: Optional[nx.DiGraph] = None,
        dfg: Optional[DataFlowGraph] = None,
        cfg: Optional[ControlFlowGraph] = None,
    ) -> HypothesisTestResult:
        """
        Test a hypothesis using causal analysis.

        Args:
            hypothesis: Hypothesis to test
            symbol_graph: Symbol graph for call analysis
            dfg: Data-flow graph
            cfg: Control-flow graph

        Returns:
            Test result with evidence and confidence
        """
        logger.info(f"Testing hypothesis: {hypothesis.id} - {hypothesis.title}")

        result = HypothesisTestResult(hypothesis=hypothesis)

        # Use provided graphs or stored ones
        symbol_graph = symbol_graph or self._symbol_graph

        # Walk call graph
        if symbol_graph and hypothesis.affected_symbols:
            call_paths = self._walk_call_graph_for_hypothesis(
                hypothesis, symbol_graph
            )
            result.call_paths = call_paths

            # Add evidence from call paths
            for path in call_paths:
                if path.length > 0:
                    evidence = Evidence(
                        evidence_type=EvidenceType.CALL_CHAIN,
                        description=f"Call chain found: {' -> '.join(path.path)}",
                        weight=0.7,
                        quality=min(1.0, 0.5 + 0.1 * path.length),
                    )
                    result.evidence_collection.add_positive(evidence)

        # Walk data flow
        if dfg and hypothesis.data_flow_path:
            data_flow_paths = self._walk_data_flow_for_hypothesis(
                hypothesis, dfg
            )
            result.data_flow_paths = data_flow_paths

            # Add evidence from data flow paths
            for path in data_flow_paths:
                evidence = Evidence(
                    evidence_type=EvidenceType.DIRECT_DATA_FLOW,
                    description=f"Data flow path with {len(path.path)} nodes",
                    weight=1.0 if path.has_taint else 0.5,
                    quality=0.8 if not path.is_sanitized else 0.3,
                )
                if path.has_taint and not path.is_sanitized:
                    result.evidence_collection.add_positive(evidence)
                else:
                    result.evidence_collection.add_negative(evidence)

        # Walk CFG
        if cfg:
            cfg_paths = self._walk_cfg_for_hypothesis(hypothesis, cfg)
            result.cfg_paths = cfg_paths

            # Add evidence from CFG paths
            for path in cfg_paths:
                evidence = Evidence(
                    evidence_type=EvidenceType.CONTROL_FLOW,
                    description=f"Control flow path with {path.length} blocks",
                    weight=0.6,
                    quality=0.7 if path.has_branch else 0.5,
                )
                result.evidence_collection.add_positive(evidence)

        # Compute confidence
        result.confidence = self.compute_confidence(
            result.evidence_collection
        )

        # Determine if hypothesis is confirmed
        result.is_confirmed = result.confidence >= 0.7

        # Store result
        self._test_results.append(result)

        logger.info(
            f"Hypothesis {hypothesis.id}: confirmed={result.is_confirmed}, "
            f"confidence={result.confidence:.2f}"
        )

        return result

    def walk_call_graph(
        self,
        from_symbol: str,
        to_symbol: str,
        symbol_graph: Optional[nx.DiGraph] = None,
    ) -> List[CallPath]:
        """
        Walk the call graph between two symbols.

        Args:
            from_symbol: Source symbol
            to_symbol: Target symbol
            symbol_graph: Symbol graph (optional)

        Returns:
            List of call paths
        """
        graph = symbol_graph or self._symbol_graph
        if not graph:
            logger.warning("No symbol graph available for call graph walk")
            return []

        call_paths: List[CallPath] = []

        try:
            # Find all simple paths
            paths = nx.all_simple_paths(
                graph,
                source=from_symbol,
                target=to_symbol,
                cutoff=20,
            )

            for path in paths:
                # Create file locations (would need symbol info in real impl)
                locations = [
                    FileLocation(file_path="unknown", line=0)
                    for _ in path
                ]

                call_paths.append(
                    CallPath(
                        path=path,
                        file_locations=locations,
                    )
                )
        except nx.NetworkXError as e:
            logger.error(f"Error walking call graph: {e}")
        except ValueError:
            # Nodes not in graph
            pass

        return call_paths

    def walk_data_flow(
        self,
        from_node: str,
        to_node: str,
        dfg: Optional[DataFlowGraph] = None,
    ) -> List[DataFlowPath]:
        """
        Walk the data flow between two nodes.

        Args:
            from_node: Source node
            to_node: Target node
            dfg: Data-flow graph (optional)

        Returns:
            List of data flow paths
        """
        if not dfg:
            logger.warning("No data-flow graph available")
            return []

        data_flow_paths: List[DataFlowPath] = []

        try:
            # Find path in DFG graph
            path = nx.shortest_path(dfg.graph, from_node, to_node)

            # Check for taint
            has_taint = False
            is_sanitized = False

            for node in path:
                if node in dfg.graph.nodes:
                    node_data = dfg.graph.nodes[node]
                    if node_data.get("taint_source"):
                        has_taint = True
                    if node_data.get("is_sanitized"):
                        is_sanitized = True

            # Determine flow type
            flow_type = ""
            for flow in dfg.flows:
                if flow.source == from_node and flow.sink == to_node:
                    flow_type = flow.flow_type.value
                    break

            data_flow_paths.append(
                DataFlowPath(
                    path=path,
                    flow_type=flow_type,
                    has_taint=has_taint,
                    is_sanitized=is_sanitized,
                )
            )
        except nx.NetworkXNoPath:
            pass
        except nx.NetworkXError as e:
            logger.error(f"Error walking data flow: {e}")

        return data_flow_paths

    def walk_cfg(
        self,
        function_name: str,
        start_node: str,
        end_node: str,
        cfg: Optional[ControlFlowGraph] = None,
    ) -> List[CFGPath]:
        """
        Walk the control-flow graph between two nodes.

        Args:
            function_name: Function name
            start_node: Start block
            end_node: End block
            cfg: Control-flow graph (optional)

        Returns:
            List of CFG paths
        """
        if not cfg:
            logger.warning("No CFG available")
            return []

        cfg_paths: List[CFGPath] = []

        try:
            # Find all simple paths
            paths = nx.all_simple_paths(
                cfg.graph,
                source=start_node,
                target=end_node,
                cutoff=50,
            )

            for path in paths:
                # Check for branches and loops
                has_branch = False
                has_loop = False

                for block_id in path:
                    if "if" in block_id or "cond" in block_id:
                        has_branch = True
                    if "loop" in block_id or "for" in block_id or "while" in block_id:
                        has_loop = True

                cfg_paths.append(
                    CFGPath(
                        path=path,
                        has_branch=has_branch,
                        has_loop=has_loop,
                    )
                )
        except nx.NetworkXNoPath:
            pass
        except nx.NetworkXError as e:
            logger.error(f"Error walking CFG: {e}")

        return cfg_paths

    def collect_evidence(
        self,
        hypothesis: Hypothesis,
        paths: Dict[str, List[Any]],
    ) -> EvidenceCollection:
        """
        Collect evidence from various paths.

        Args:
            hypothesis: Hypothesis being tested
            paths: Dictionary of paths (call_paths, data_flow_paths, cfg_paths)

        Returns:
            Collection of evidence
        """
        collection = EvidenceCollection()

        # Evidence from call paths
        call_paths = paths.get("call_paths", [])
        for path in call_paths:
            if isinstance(path, CallPath) and path.length > 0:
                collection.add_positive(
                    Evidence(
                        evidence_type=EvidenceType.CALL_CHAIN,
                        description=f"Call chain: {' -> '.join(path.path[:5])}...",
                        weight=0.7,
                        quality=min(1.0, 0.5 + 0.1 * min(path.length, 5)),
                    )
                )

        # Evidence from data flow paths
        data_flow_paths = paths.get("data_flow_paths", [])
        for path in data_flow_paths:
            if isinstance(path, DataFlowPath):
                if path.has_taint and not path.is_sanitized:
                    collection.add_positive(
                        Evidence(
                            evidence_type=EvidenceType.TAINT_PATH,
                            description=f"Tainted data flow with {len(path.path)} nodes",
                            weight=1.0,
                            quality=0.9,
                        )
                    )
                else:
                    collection.add_negative(
                        Evidence(
                            evidence_type=EvidenceType.TAINT_PATH,
                            description="Data flow is sanitized or not tainted",
                            weight=0.5,
                            quality=0.7,
                        )
                    )

        # Evidence from CFG paths
        cfg_paths = paths.get("cfg_paths", [])
        for path in cfg_paths:
            if isinstance(path, CFGPath):
                collection.add_positive(
                    Evidence(
                        evidence_type=EvidenceType.CONTROL_FLOW,
                        description=f"Control flow path with {path.length} blocks",
                        weight=0.6,
                        quality=0.7 if path.has_branch else 0.5,
                    )
                )

        return collection

    def compute_confidence(
        self,
        evidence_collection: EvidenceCollection,
    ) -> float:
        """
        Compute confidence score from evidence collection.

        Args:
            evidence_collection: Collection of evidence

        Returns:
            Confidence score between 0.0 and 1.0
        """
        return evidence_collection.evidence_score

    def _walk_call_graph_for_hypothesis(
        self,
        hypothesis: Hypothesis,
        symbol_graph: nx.DiGraph,
    ) -> List[CallPath]:
        """
        Walk call graph for a hypothesis.

        Args:
            hypothesis: Hypothesis to analyze
            symbol_graph: Symbol graph

        Returns:
            List of call paths
        """
        if not hypothesis.affected_symbols:
            return []

        # Walk between affected symbols
        call_paths: List[CallPath] = []
        symbols = hypothesis.affected_symbols

        for i, from_symbol in enumerate(symbols):
            for to_symbol in symbols[i + 1 :]:
                paths = self.walk_call_graph(from_symbol, to_symbol, symbol_graph)
                call_paths.extend(paths)

        return call_paths

    def _walk_data_flow_for_hypothesis(
        self,
        hypothesis: Hypothesis,
        dfg: DataFlowGraph,
    ) -> List[DataFlowPath]:
        """
        Walk data flow for a hypothesis.

        Args:
            hypothesis: Hypothesis to analyze
            dfg: Data-flow graph

        Returns:
            List of data flow paths
        """
        data_flow_paths: List[DataFlowPath] = []

        # Use hypothesis data flow path if available
        if hypothesis.data_flow_path:
            path_nodes = hypothesis.data_flow_path
            if len(path_nodes) >= 2:
                paths = self.walk_data_flow(
                    path_nodes[0],
                    path_nodes[-1],
                    dfg,
                )
                data_flow_paths.extend(paths)

        # Also check taint sources to sinks
        for source in dfg.taint_sources:
            paths = dfg.track_taint(source.node)
            for taint_path in paths:
                data_flow_paths.append(
                    DataFlowPath(
                        path=taint_path.path,
                        has_taint=True,
                        is_sanitized=not taint_path.is_vulnerable,
                    )
                )

        return data_flow_paths

    def _walk_cfg_for_hypothesis(
        self,
        hypothesis: Hypothesis,
        cfg: ControlFlowGraph,
    ) -> List[CFGPath]:
        """
        Walk CFG for a hypothesis.

        Args:
            hypothesis: Hypothesis to analyze
            cfg: Control-flow graph

        Returns:
            List of CFG paths
        """
        cfg_paths: List[CFGPath] = []

        # Walk from entry to exit
        if cfg.entry_node and cfg.exit_node:
            paths = self.walk_cfg(
                hypothesis.affected_symbols[0] if hypothesis.affected_symbols else "func",
                cfg.entry_node,
                cfg.exit_node,
                cfg,
            )
            cfg_paths.extend(paths)

        return cfg_paths

    def get_test_results(self) -> List[HypothesisTestResult]:
        """
        Get all test results.

        Returns:
            List of test results
        """
        return self._test_results.copy()

    def clear_results(self) -> None:
        """Clear all test results."""
        self._test_results = []
        logger.debug("Test results cleared")

    def set_symbol_graph(self, symbol_graph: nx.DiGraph) -> None:
        """
        Set the symbol graph.

        Args:
            symbol_graph: Symbol graph to use
        """
        self._symbol_graph = symbol_graph
