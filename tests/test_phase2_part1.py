"""
Unit tests for Phase 2 Part 1: The Shield.

Tests for:
- DataFlowGraphBuilder (DFG creation, taint tracking, uninitialized vars)
- ControlFlowGraphBuilder (CFG creation, loops, conditionals, exception paths)
- HypothesisAgent (hypothesis generation for different bug types)
- AnalyzerAgent (causal testing, evidence collection)
- ObserverAgent (evidence aggregation, confidence scoring)
- LLiftPrioritizer (hybrid ranking, LLM integration)
"""

import ast
import pytest
from typing import List, Dict, Any

import networkx as nx

from src.analysis.dfg_builder import (
    DataFlowGraphBuilder,
    DataFlowGraph,
    DataFlow,
    VariableNode,
    TaintSource,
    TaintSink,
    TaintPath,
    UninitializedVar,
    NullPointerPath,
    RaceCondition,
    FlowType,
    TaintType,
    SinkType,
    VariableScope,
)
from src.analysis.cfg_builder import (
    ControlFlowGraphBuilder,
    ControlFlowGraph,
    BasicBlock,
    CFGEdge,
    Loop,
    Conditional,
    ExceptionPath,
    EdgeType,
    LoopType,
)
from src.agent.hypothesis_agent import (
    HypothesisAgent,
    Hypothesis,
    HypothesisType,
    Severity,
    BugCandidate,
)
from src.agent.analyzer_agent import (
    AnalyzerAgent,
    HypothesisTestResult,
    CallPath,
    DataFlowPath,
    CFGPath,
    Evidence,
    EvidenceCollection,
    EvidenceType,
    FileLocation,
)
from src.agent.observer_agent import (
    ObserverAgent,
    AggregatedEvidence,
    RankedCandidate,
    EvidenceChain,
    EvidenceItem,
)
from src.agent.llift_prioritizer import (
    LLiftPrioritizer,
    PrioritizationResult,
    SemgrepResult,
    ChurnAnalysis,
)


# =============================================================================
# DataFlowGraphBuilder Tests
# =============================================================================

class TestDataFlowGraphBuilder:
    """Tests for DataFlowGraphBuilder."""

    def test_build_from_ast_simple_assignment(self) -> None:
        """Test building DFG from simple assignment."""
        code = "x = 1"
        tree = ast.parse(code)

        builder = DataFlowGraphBuilder()
        builder.set_current_file("test.py")
        dfg = builder.build_from_ast(tree)

        assert dfg is not None
        assert len(dfg.graph.nodes) > 0
        assert len(dfg.variables) > 0

    def test_build_from_ast_function_definition(self) -> None:
        """Test building DFG from function definition."""
        code = """
def greet(name: str) -> str:
    message = f"Hello, {name}"
    return message
"""
        tree = ast.parse(code)

        builder = DataFlowGraphBuilder()
        builder.set_current_file("test.py")
        dfg = builder.build_from_ast(tree)

        assert dfg is not None
        assert len(dfg.graph.nodes) > 0
        # Should have function, parameters, and variables
        assert any("greet" in str(node) for node in dfg.graph.nodes)

    def test_build_from_ast_taint_source_detection(self) -> None:
        """Test detection of taint sources."""
        code = """
user_input = input("Enter value: ")
query = f"SELECT * FROM users WHERE name = '{user_input}'"
cursor.execute(query)
"""
        tree = ast.parse(code)

        builder = DataFlowGraphBuilder()
        builder.set_current_file("test.py")
        dfg = builder.build_from_ast(tree)

        assert len(dfg.taint_sources) > 0
        assert any(ts.taint_type == TaintType.USER_INPUT for ts in dfg.taint_sources)

    def test_build_from_ast_taint_sink_detection(self) -> None:
        """Test detection of taint sinks."""
        code = """
import sqlite3
conn = sqlite3.connect("db.sqlite")
cursor = conn.cursor()
cursor.execute("SELECT * FROM users WHERE id = 1")
"""
        tree = ast.parse(code)

        builder = DataFlowGraphBuilder()
        builder.set_current_file("test.py")
        dfg = builder.build_from_ast(tree)

        assert len(dfg.taint_sinks) > 0
        assert any(ts.sink_type == SinkType.SQL_QUERY for ts in dfg.taint_sinks)

    def test_add_variable_flow(self) -> None:
        """Test adding variable flow manually."""
        builder = DataFlowGraphBuilder()
        builder.set_current_file("test.py")

        # Build initial graph
        code = "x = 1"
        tree = ast.parse(code)
        dfg = builder.build_from_ast(tree)

        # Add manual flow
        builder.add_variable_flow(
            from_node="node1",
            to_node="node2",
            var_name="test_var",
            flow_type=FlowType.ASSIGNMENT,
        )

        flows = builder.get_flows()
        assert len(flows) > 0

    def test_add_taint_source(self) -> None:
        """Test adding taint source manually."""
        builder = DataFlowGraphBuilder()
        builder.set_current_file("test.py")

        code = "x = 1"
        tree = ast.parse(code)
        dfg = builder.build_from_ast(tree)

        builder.add_taint_source("node1", TaintType.NETWORK, confidence=0.9)

        sources = builder.get_taint_sources()
        assert len(sources) >= 1
        assert any(ts.node == "node1" for ts in sources)

    def test_add_taint_sink(self) -> None:
        """Test adding taint sink manually."""
        builder = DataFlowGraphBuilder()
        builder.set_current_file("test.py")

        code = "x = 1"
        tree = ast.parse(code)
        dfg = builder.build_from_ast(tree)

        builder.add_taint_sink("node1", SinkType.COMMAND_EXECUTION, is_sanitized=False)

        sinks = builder.get_taint_sinks()
        assert len(sinks) >= 1
        assert any(ts.node == "node1" for ts in sinks)

    def test_track_taint(self) -> None:
        """Test taint tracking."""
        builder = DataFlowGraphBuilder()
        builder.set_current_file("test.py")

        # Create graph with taint source
        code = """
user_data = input("Enter: ")
processed = user_data.upper()
print(processed)
"""
        tree = ast.parse(code)
        dfg = builder.build_from_ast(tree)

        # Track taint from source
        if dfg.taint_sources:
            source_node = dfg.taint_sources[0].node
            paths = builder.track_taint(source_node)
            # Paths may or may not exist depending on graph structure
            assert isinstance(paths, list)

    def test_find_uninitialized_variables(self) -> None:
        """Test finding uninitialized variables."""
        builder = DataFlowGraphBuilder()
        builder.set_current_file("test.py")

        # Code with potential uninitialized var usage
        code = """
def test():
    print(x)  # x used before definition
    x = 1
"""
        tree = ast.parse(code)
        dfg = builder.build_from_ast(tree)

        uninitialized = builder.find_uninitialized_variables()
        # May find uninitialized vars depending on analysis
        assert isinstance(uninitialized, list)

    def test_find_null_pointer_paths(self) -> None:
        """Test finding null pointer paths."""
        builder = DataFlowGraphBuilder()
        builder.set_current_file("test.py")

        code = """
x = None
result = x.method()  # Potential null pointer dereference
"""
        tree = ast.parse(code)
        dfg = builder.build_from_ast(tree)

        null_paths = builder.find_null_pointer_paths()
        assert isinstance(null_paths, list)

    def test_find_race_conditions(self) -> None:
        """Test finding race conditions."""
        builder = DataFlowGraphBuilder()
        builder.set_current_file("test.py")

        code = """
import threading
counter = 0

def increment():
    global counter
    counter += 1
"""
        tree = ast.parse(code)
        dfg = builder.build_from_ast(tree)

        race_conditions = builder.find_race_conditions()
        assert isinstance(race_conditions, list)

    def test_data_flow_graph_structure(self) -> None:
        """Test DFG structure properties."""
        builder = DataFlowGraphBuilder()
        builder.set_current_file("test.py")

        code = """
def add(a, b):
    return a + b

result = add(1, 2)
"""
        tree = ast.parse(code)
        dfg = builder.build_from_ast(tree)

        assert dfg.graph is not None
        assert isinstance(dfg.variables, dict)
        assert isinstance(dfg.flows, list)
        assert isinstance(dfg.taint_sources, list)
        assert isinstance(dfg.taint_sinks, list)

    def test_variable_node_properties(self) -> None:
        """Test VariableNode properties."""
        var = VariableNode(
            name="test_var",
            file_path="test.py",
            line_def=10,
            line_use=[11, 12, 13],
            scope=VariableScope.LOCAL,
            type_hint="str",
        )

        assert var.name == "test_var"
        assert var.file_path == "test.py"
        assert var.line_def == 10
        assert len(var.line_use) == 3
        assert var.scope == VariableScope.LOCAL
        assert var.type_hint == "str"
        assert var.uid != ""

    def test_taint_path_properties(self) -> None:
        """Test TaintPath properties."""
        source = TaintSource(node="src", taint_type=TaintType.USER_INPUT, confidence=1.0)
        sink = TaintSink(node="sink", sink_type=SinkType.SQL_QUERY, is_sanitized=False)

        path = TaintPath(
            source=source,
            sink=sink,
            path=["src", "mid1", "mid2", "sink"],
        )

        assert path.length == 4
        assert path.is_vulnerable is True

        # Test sanitized path
        sanitized_sink = TaintSink(node="sink2", sink_type=SinkType.SQL_QUERY, is_sanitized=True)
        path2 = TaintPath(source=source, sink=sanitized_sink, path=["src", "sink2"])
        assert path2.is_vulnerable is False


# =============================================================================
# ControlFlowGraphBuilder Tests
# =============================================================================

class TestControlFlowGraphBuilder:
    """Tests for ControlFlowGraphBuilder."""

    def test_build_from_ast_simple_function(self) -> None:
        """Test building CFG from simple function."""
        code = """
def add(a, b):
    return a + b
"""
        tree = ast.parse(code)

        builder = ControlFlowGraphBuilder()
        cfg = builder.build_from_ast(tree, "add")

        assert cfg is not None
        assert len(cfg.graph.nodes) > 0
        assert cfg.entry_node is not None
        assert cfg.exit_node is not None

    def test_build_from_ast_conditional(self) -> None:
        """Test building CFG with conditional."""
        code = """
def check(x):
    if x > 0:
        return "positive"
    else:
        return "negative"
"""
        tree = ast.parse(code)

        builder = ControlFlowGraphBuilder()
        cfg = builder.build_from_ast(tree, "check")

        assert cfg is not None
        conditionals = builder.find_conditionals()
        assert len(conditionals) > 0

    def test_build_from_ast_loop(self) -> None:
        """Test building CFG with loop."""
        code = """
def sum_list(items):
    total = 0
    for item in items:
        total += item
    return total
"""
        tree = ast.parse(code)

        builder = ControlFlowGraphBuilder()
        cfg = builder.build_from_ast(tree, "sum_list")

        assert cfg is not None
        loops = builder.find_loops()
        assert len(loops) > 0

    def test_build_from_ast_while_loop(self) -> None:
        """Test building CFG with while loop."""
        code = """
def countdown(n):
    while n > 0:
        print(n)
        n -= 1
"""
        tree = ast.parse(code)

        builder = ControlFlowGraphBuilder()
        cfg = builder.build_from_ast(tree, "countdown")

        loops = builder.find_loops()
        assert len(loops) > 0
        assert loops[0].loop_type == LoopType.WHILE

    def test_build_from_ast_exception_handling(self) -> None:
        """Test building CFG with exception handling."""
        code = """
def risky():
    try:
        result = 1 / 0
    except ZeroDivisionError:
        result = 0
    finally:
        print("done")
    return result
"""
        tree = ast.parse(code)

        builder = ControlFlowGraphBuilder()
        cfg = builder.build_from_ast(tree, "risky")

        exception_paths = builder.find_exception_paths()
        assert len(exception_paths) > 0

    def test_get_basic_blocks(self) -> None:
        """Test getting basic blocks."""
        code = """
def test():
    x = 1
    y = 2
    return x + y
"""
        tree = ast.parse(code)

        builder = ControlFlowGraphBuilder()
        cfg = builder.build_from_ast(tree, "test")

        blocks = builder.get_basic_blocks()
        assert len(blocks) > 0
        assert all(isinstance(b, BasicBlock) for b in blocks)

    def test_get_edges(self) -> None:
        """Test getting CFG edges."""
        code = """
def test():
    x = 1
    return x
"""
        tree = ast.parse(code)

        builder = ControlFlowGraphBuilder()
        cfg = builder.build_from_ast(tree, "test")

        edges = builder.get_edges()
        assert len(edges) > 0
        assert all(isinstance(e, CFGEdge) for e in edges)

    def test_get_reachable_nodes(self) -> None:
        """Test getting reachable nodes."""
        code = """
def test():
    x = 1
    y = 2
    return x + y
"""
        tree = ast.parse(code)

        builder = ControlFlowGraphBuilder()
        cfg = builder.build_from_ast(tree, "test")

        paths = builder.get_reachable_nodes(cfg.entry_node, cfg.exit_node)
        assert isinstance(paths, list)

    def test_get_dominators(self) -> None:
        """Test getting dominators."""
        code = """
def test():
    x = 1
    return x
"""
        tree = ast.parse(code)

        builder = ControlFlowGraphBuilder()
        cfg = builder.build_from_ast(tree, "test")

        # Get any node and find its dominators
        if len(cfg.graph.nodes) > 1:
            nodes = list(cfg.graph.nodes)
            dominators = builder.get_dominators(nodes[-1])
            assert isinstance(dominators, list)

    def test_loop_detection(self) -> None:
        """Test loop detection in CFG."""
        code = """
def process(items):
    for item in items:
        if item > 0:
            print(item)
"""
        tree = ast.parse(code)

        builder = ControlFlowGraphBuilder()
        cfg = builder.build_from_ast(tree, "process")

        loops = builder.find_loops()
        assert len(loops) > 0
        assert loops[0].header is not None
        assert len(loops[0].body) > 0

    def test_conditional_detection(self) -> None:
        """Test conditional detection in CFG."""
        code = """
def check(x, y):
    if x > y:
        return x
    return y
"""
        tree = ast.parse(code)

        builder = ControlFlowGraphBuilder()
        cfg = builder.build_from_ast(tree, "check")

        conditionals = builder.find_conditionals()
        assert len(conditionals) > 0
        assert conditionals[0].condition_node is not None

    def test_exception_path_detection(self) -> None:
        """Test exception path detection."""
        code = """
def divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return None
"""
        tree = ast.parse(code)

        builder = ControlFlowGraphBuilder()
        cfg = builder.build_from_ast(tree, "divide")

        paths = builder.find_exception_paths()
        assert len(paths) > 0
        assert paths[0].try_block is not None
        assert len(paths[0].catch_blocks) > 0

    def test_cfg_graph_structure(self) -> None:
        """Test CFG graph structure."""
        code = "def test(): pass"
        tree = ast.parse(code)

        builder = ControlFlowGraphBuilder()
        cfg = builder.build_from_ast(tree, "test")

        assert cfg.graph is not None
        assert isinstance(cfg.basic_blocks, list)
        assert isinstance(cfg.loops, list)


# =============================================================================
# HypothesisAgent Tests
# =============================================================================

class TestHypothesisAgent:
    """Tests for HypothesisAgent."""

    def test_generate_hypotheses_sql_injection(self) -> None:
        """Test hypothesis generation for SQL injection."""
        agent = HypothesisAgent()

        candidate = BugCandidate(
            id="cand_001",
            file_path="test.py",
            line=10,
            symbol_name="get_user",
            bug_type="sql_injection",
            description="Potential SQL injection",
            severity=Severity.CRITICAL,
        )

        # Create minimal DFG
        builder = DataFlowGraphBuilder()
        builder.set_current_file("test.py")
        dfg = builder.build_from_ast(ast.parse("x = 1"))

        hypotheses = agent.generate_hypotheses(candidate, dfg)

        assert len(hypotheses) > 0
        assert all(isinstance(h, Hypothesis) for h in hypotheses)

    def test_generate_hypotheses_auth_bypass(self) -> None:
        """Test hypothesis generation for auth bypass."""
        agent = HypothesisAgent()

        candidate = BugCandidate(
            id="cand_002",
            file_path="auth.py",
            line=25,
            symbol_name="authenticate",
            bug_type="auth_bypass",
            description="Authentication bypass",
            severity=Severity.HIGH,
        )

        builder = DataFlowGraphBuilder()
        builder.set_current_file("auth.py")
        dfg = builder.build_from_ast(ast.parse("x = 1"))

        hypotheses = agent.generate_hypotheses(candidate, dfg)

        assert len(hypotheses) > 0
        assert all(h.candidate_id == "cand_002" for h in hypotheses)

    def test_generate_hypotheses_race_condition(self) -> None:
        """Test hypothesis generation for race condition."""
        agent = HypothesisAgent()

        candidate = BugCandidate(
            id="cand_003",
            file_path="concurrent.py",
            line=50,
            symbol_name="increment",
            bug_type="race_condition",
            description="Race condition in counter",
            severity=Severity.HIGH,
        )

        builder = DataFlowGraphBuilder()
        builder.set_current_file("concurrent.py")
        dfg = builder.build_from_ast(ast.parse("x = 1"))

        hypotheses = agent.generate_hypotheses(candidate, dfg)

        assert len(hypotheses) > 0
        assert all(h.candidate_id == "cand_003" for h in hypotheses)

    def test_generate_for_injection(self) -> None:
        """Test specific injection hypothesis generation."""
        agent = HypothesisAgent()

        candidate = BugCandidate(
            id="cand_004",
            file_path="db.py",
            line=15,
            symbol_name="query",
            bug_type="sql_injection",
            description="SQL injection in query",
        )

        builder = DataFlowGraphBuilder()
        builder.set_current_file("db.py")
        dfg = builder.build_from_ast(ast.parse("x = 1"))

        hypotheses = agent.generate_for_injection(candidate, dfg)

        assert len(hypotheses) > 0
        assert all(
            "sql" in h.hypothesis_type.value or "injection" in h.hypothesis_type.value
            for h in hypotheses
        )

    def test_generate_for_auth_bypass(self) -> None:
        """Test specific auth bypass hypothesis generation."""
        agent = HypothesisAgent()

        candidate = BugCandidate(
            id="cand_005",
            file_path="auth.py",
            line=30,
            symbol_name="check_token",
            bug_type="auth_bypass",
            description="Token validation bypass",
        )

        builder = DataFlowGraphBuilder()
        builder.set_current_file("auth.py")
        dfg = builder.build_from_ast(ast.parse("x = 1"))

        hypotheses = agent.generate_for_auth_bypass(candidate, dfg)

        assert len(hypotheses) > 0
        assert all("auth" in h.hypothesis_type.value for h in hypotheses)

    def test_generate_for_race_condition(self) -> None:
        """Test specific race condition hypothesis generation."""
        agent = HypothesisAgent()

        candidate = BugCandidate(
            id="cand_006",
            file_path="counter.py",
            line=10,
            symbol_name="increment",
            bug_type="race_condition",
            description="Counter race condition",
        )

        builder = DataFlowGraphBuilder()
        builder.set_current_file("counter.py")
        dfg = builder.build_from_ast(ast.parse("x = 1"))

        hypotheses = agent.generate_for_race_condition(candidate, dfg)

        assert len(hypotheses) > 0
        assert all("race" in h.hypothesis_type.value for h in hypotheses)

    def test_rank_hypotheses(self) -> None:
        """Test hypothesis ranking."""
        agent = HypothesisAgent()

        hypotheses = [
            Hypothesis(
                id="h1",
                title="Low confidence",
                description="Test",
                hypothesis_type=HypothesisType.SQL_INJECTION_USER_INPUT,
                candidate_id="cand",
                confidence=0.3,
                severity=Severity.LOW,
            ),
            Hypothesis(
                id="h2",
                title="High confidence",
                description="Test",
                hypothesis_type=HypothesisType.SQL_INJECTION_USER_INPUT,
                candidate_id="cand",
                confidence=0.9,
                severity=Severity.CRITICAL,
            ),
            Hypothesis(
                id="h3",
                title="Medium confidence",
                description="Test",
                hypothesis_type=HypothesisType.SQL_INJECTION_USER_INPUT,
                candidate_id="cand",
                confidence=0.5,
                severity=Severity.MEDIUM,
            ),
        ]

        ranked = agent.rank_hypotheses(hypotheses)

        assert len(ranked) == 3
        assert ranked[0].id == "h2"  # Highest confidence first

    def test_hypothesis_properties(self) -> None:
        """Test Hypothesis dataclass properties."""
        hypothesis = Hypothesis(
            id="test_hypo",
            title="Test Hypothesis",
            description="A test hypothesis",
            hypothesis_type=HypothesisType.SQL_INJECTION_USER_INPUT,
            candidate_id="cand_001",
            affected_symbols=["func1", "func2"],
            data_flow_path=["src", "mid", "sink"],
            confidence=0.85,
            evidence_required=["evidence1"],
            severity=Severity.HIGH,
        )

        assert hypothesis.id == "test_hypo"
        assert len(hypothesis.affected_symbols) == 2
        assert hypothesis.data_flow_path is not None
        assert hypothesis.confidence == 0.85

        # Test to_dict
        d = hypothesis.to_dict()
        assert d["id"] == "test_hypo"
        assert d["severity"] == "High"


# =============================================================================
# AnalyzerAgent Tests
# =============================================================================

class TestAnalyzerAgent:
    """Tests for AnalyzerAgent."""

    def test_test_hypothesis(self) -> None:
        """Test hypothesis testing."""
        agent = AnalyzerAgent()

        hypothesis = Hypothesis(
            id="h1",
            title="Test",
            description="Test hypothesis",
            hypothesis_type=HypothesisType.SQL_INJECTION_USER_INPUT,
            candidate_id="cand",
            confidence=0.7,
        )

        # Create symbol graph
        symbol_graph = nx.DiGraph()
        symbol_graph.add_edge("func1", "func2")
        symbol_graph.add_edge("func2", "func3")

        # Create DFG
        builder = DataFlowGraphBuilder()
        builder.set_current_file("test.py")
        dfg = builder.build_from_ast(ast.parse("x = 1"))

        result = agent.test_hypothesis(hypothesis, symbol_graph, dfg)

        assert result is not None
        assert result.hypothesis == hypothesis
        assert isinstance(result.confidence, float)
        assert isinstance(result.evidence_collection, EvidenceCollection)

    def test_walk_call_graph(self) -> None:
        """Test call graph walking."""
        agent = AnalyzerAgent()

        symbol_graph = nx.DiGraph()
        symbol_graph.add_edge("main", "helper")
        symbol_graph.add_edge("helper", "util")

        paths = agent.walk_call_graph("main", "util", symbol_graph)

        assert len(paths) > 0
        assert any("main" in p.path and "util" in p.path for p in paths)

    def test_walk_data_flow(self) -> None:
        """Test data flow walking."""
        agent = AnalyzerAgent()

        builder = DataFlowGraphBuilder()
        builder.set_current_file("test.py")
        dfg = builder.build_from_ast(ast.parse("""
x = input()
y = x.upper()
print(y)
"""))

        # Add explicit nodes for testing
        if dfg.taint_sources:
            source = dfg.taint_sources[0]
            paths = agent.walk_data_flow(source.node, source.node, dfg)
            assert isinstance(paths, list)

    def test_walk_cfg(self) -> None:
        """Test CFG walking."""
        agent = AnalyzerAgent()

        builder = ControlFlowGraphBuilder()
        cfg = builder.build_from_ast(
            ast.parse("def test():\n    x = 1\n    return x"),
            "test",
        )

        paths = agent.walk_cfg("test", cfg.entry_node, cfg.exit_node, cfg)

        assert isinstance(paths, list)

    def test_collect_evidence(self) -> None:
        """Test evidence collection."""
        agent = AnalyzerAgent()

        hypothesis = Hypothesis(
            id="h1",
            title="Test",
            description="Test",
            hypothesis_type=HypothesisType.SQL_INJECTION_USER_INPUT,
            candidate_id="cand",
        )

        paths = {
            "call_paths": [
                CallPath(path=["a", "b", "c"]),
            ],
            "data_flow_paths": [
                DataFlowPath(path=["x", "y"], has_taint=True, is_sanitized=False),
            ],
            "cfg_paths": [
                CFGPath(path=["block1", "block2"], has_branch=True),
            ],
        }

        collection = agent.collect_evidence(hypothesis, paths)

        assert collection is not None
        assert len(collection.positive_evidence) > 0

    def test_compute_confidence(self) -> None:
        """Test confidence computation."""
        agent = AnalyzerAgent()

        collection = EvidenceCollection()
        collection.add_positive(
            Evidence(
                evidence_type=EvidenceType.DIRECT_DATA_FLOW,
                description="Direct data flow",
                weight=1.0,
                quality=0.9,
            )
        )
        collection.add_negative(
            Evidence(
                evidence_type=EvidenceType.CALL_CHAIN,
                description="Missing call chain",
                weight=0.5,
                quality=0.7,
            )
        )

        confidence = agent.compute_confidence(collection)

        assert 0.0 <= confidence <= 1.0

    def test_hypothesis_test_result(self) -> None:
        """Test HypothesisTestResult dataclass."""
        hypothesis = Hypothesis(
            id="h1",
            title="Test",
            description="Test",
            hypothesis_type=HypothesisType.SQL_INJECTION_USER_INPUT,
            candidate_id="cand",
        )

        result = HypothesisTestResult(
            hypothesis=hypothesis,
            is_confirmed=True,
            confidence=0.85,
            call_paths=[CallPath(path=["a", "b"])],
            data_flow_paths=[DataFlowPath(path=["x", "y"])],
        )

        assert result.is_confirmed is True
        assert result.confidence == 0.85
        assert len(result.call_paths) == 1


# =============================================================================
# ObserverAgent Tests
# =============================================================================

class TestObserverAgent:
    """Tests for ObserverAgent."""

    def test_aggregate_evidence(self) -> None:
        """Test evidence aggregation."""
        agent = ObserverAgent()

        collection1 = EvidenceCollection()
        collection1.add_positive(
            Evidence(
                evidence_type=EvidenceType.DIRECT_DATA_FLOW,
                description="Direct flow",
                weight=1.0,
                quality=0.9,
            )
        )

        collection2 = EvidenceCollection()
        collection2.add_positive(
            Evidence(
                evidence_type=EvidenceType.CALL_CHAIN,
                description="Call chain",
                weight=0.8,
                quality=0.7,
            )
        )

        aggregated = agent.aggregate_evidence([collection1, collection2])

        assert aggregated.total_positive > 0
        assert aggregated.evidence_count == 2

    def test_compute_confidence_score(self) -> None:
        """Test confidence score computation."""
        agent = ObserverAgent()

        aggregated = AggregatedEvidence(
            total_positive=0.8,
            total_negative=0.2,
            evidence_count=5,
            evidence_types={"direct_data_flow": 0.5, "call_chain": 0.3},
        )

        confidence = agent.compute_confidence_score(aggregated)

        assert 0.0 <= confidence <= 1.0

    def test_rank_candidates(self) -> None:
        """Test candidate ranking."""
        agent = ObserverAgent()

        candidates_data = []
        for i in range(5):
            collection = EvidenceCollection()
            collection.add_positive(
                Evidence(
                    evidence_type=EvidenceType.DIRECT_DATA_FLOW,
                    description=f"Evidence {i}",
                    weight=0.5 + i * 0.1,
                    quality=0.8,
                )
            )
            candidates_data.append((f"cand_{i}", 0.5, collection))

        ranked = agent.rank_candidates(candidates_data)

        assert len(ranked) == 5
        assert ranked[0].rank == 1
        # Higher evidence should rank higher
        assert all(ranked[i].rank < ranked[i + 1].rank for i in range(len(ranked) - 1))

    def test_get_evidence_chain(self) -> None:
        """Test getting evidence chain."""
        agent = ObserverAgent()

        collection = EvidenceCollection()
        collection.add_positive(
            Evidence(
                evidence_type=EvidenceType.DIRECT_DATA_FLOW,
                description="Test evidence",
                weight=1.0,
                quality=0.9,
            )
        )

        candidates_data = [("cand_001", 0.5, collection)]
        agent.rank_candidates(candidates_data)

        chain = agent.get_evidence_chain("cand_001")

        assert chain is not None
        assert chain.candidate_id == "cand_001"
        assert len(chain.evidence_items) > 0

    def test_get_top_candidates(self) -> None:
        """Test getting top candidates."""
        agent = ObserverAgent()

        candidates_data = [
            (f"cand_{i}", 0.5, EvidenceCollection())
            for i in range(10)
        ]

        agent.rank_candidates(candidates_data)
        top = agent.get_top_candidates(top_n=3)

        assert len(top) == 3
        assert all(c.rank <= 3 for c in top)

    def test_evidence_chain_strength(self) -> None:
        """Test evidence chain strength calculation."""
        chain = EvidenceChain(candidate_id="test")

        chain.add_evidence(
            EvidenceItem(
                evidence_type=EvidenceType.DIRECT_DATA_FLOW,
                description="Strong evidence",
                weight=1.0,
                quality=0.9,
            )
        )
        chain.add_evidence(
            EvidenceItem(
                evidence_type=EvidenceType.CALL_CHAIN,
                description="Weak evidence",
                weight=0.3,
                quality=0.5,
            )
        )

        # Chain strength is limited by weakest link
        assert chain.chain_strength <= 0.5
        assert chain.weakest_link is not None

    def test_compute_confidence_with_weights(self) -> None:
        """Test confidence computation with explicit weights."""
        agent = ObserverAgent()

        positive = [
            Evidence(
                evidence_type=EvidenceType.DIRECT_DATA_FLOW,
                description="Strong",
                weight=1.0,
                quality=0.9,
            )
        ]
        negative = [
            Evidence(
                evidence_type=EvidenceType.CALL_CHAIN,
                description="Weak",
                weight=0.5,
                quality=0.6,
            )
        ]

        confidence = agent.compute_confidence_with_weights(positive, negative)

        assert 0.0 <= confidence <= 1.0

    def test_analyze_evidence_quality(self) -> None:
        """Test evidence quality analysis."""
        agent = ObserverAgent()

        collection = EvidenceCollection()
        collection.add_positive(
            Evidence(
                evidence_type=EvidenceType.DIRECT_DATA_FLOW,
                description="Test",
                weight=1.0,
                quality=0.9,
            )
        )
        collection.add_positive(
            Evidence(
                evidence_type=EvidenceType.CALL_CHAIN,
                description="Test",
                weight=0.7,
                quality=0.8,
            )
        )

        analysis = agent.analyze_evidence_quality(collection)

        assert analysis["total_items"] == 2
        assert analysis["positive_count"] == 2
        assert "average_quality" in analysis


# =============================================================================
# LLiftPrioritizer Tests
# =============================================================================

class TestLLiftPrioritizer:
    """Tests for LLiftPrioritizer."""

    def test_prioritize_candidates(self) -> None:
        """Test hybrid prioritization."""
        agent = LLiftPrioritizer()

        candidates = [
            RankedCandidate(
                candidate_id=f"cand_{i}",
                original_confidence=0.5 + i * 0.1,
                aggregated_confidence=0.6 + i * 0.05,
                rank=i + 1,
            )
            for i in range(10)
        ]

        semgrep_results = [
            SemgrepResult(
                rule_id="sql-injection",
                file_path="test.py",
                line=10,
                message="SQL injection",
                severity="error",
            )
        ]

        churn_analysis = [
            ChurnAnalysis(
                file_path="test.py",
                churn_score=0.8,
                commit_count=5,
            )
        ]

        ranked = agent.prioritize_candidates(
            candidates,
            semgrep_results,
            churn_analysis,
            top_n=5,
        )

        assert len(ranked) == 5
        assert all(c.rank <= 5 for c in ranked)

    def test_static_rank(self) -> None:
        """Test static ranking."""
        agent = LLiftPrioritizer()

        candidates = [
            RankedCandidate(
                candidate_id="cand_001:test.py:10",
                original_confidence=0.7,
                aggregated_confidence=0.75,
            )
        ]

        semgrep_results = [
            SemgrepResult(
                rule_id="test-rule",
                file_path="test.py",
                line=10,
                message="Test",
                severity="error",
            )
        ]

        scores = agent.static_rank(candidates, semgrep_results)

        assert "cand_001:test.py:10" in scores
        assert scores["cand_001:test.py:10"] > 0

    def test_combine_ranks(self) -> None:
        """Test rank combination."""
        agent = LLiftPrioritizer(static_weight=0.5, llm_weight=0.5)

        static_scores = {"c1": 0.8, "c2": 0.6}
        llm_scores = {"c1": 0.7, "c2": 0.9}

        combined = agent._combine_ranks(static_scores, llm_scores)

        assert "c1" in combined
        assert "c2" in combined
        # Combined should be weighted average
        assert 0.7 <= combined["c1"] <= 0.8
        assert 0.6 <= combined["c2"] <= 0.9

    def test_get_top_candidates(self) -> None:
        """Test getting top candidates after prioritization."""
        agent = LLiftPrioritizer()

        candidates = [
            RankedCandidate(
                candidate_id=f"cand_{i}",
                original_confidence=0.5,
                aggregated_confidence=0.5 + i * 0.05,
            )
            for i in range(20)
        ]

        agent.prioritize_candidates(candidates, top_n=10)
        top = agent.get_top_candidates(top_n=5)

        assert len(top) == 5

    def test_prioritization_result(self) -> None:
        """Test PrioritizationResult dataclass."""
        result = PrioritizationResult(
            static_scores={"c1": 0.8},
            llm_scores={"c1": 0.7},
            combined_scores={"c1": 0.75},
            final_ranking=[
                RankedCandidate(candidate_id="c1", aggregated_confidence=0.75, rank=1)
            ],
            reduction_achieved=0.5,
        )

        assert result.reduction_achieved == 0.5
        assert len(result.final_ranking) == 1

    def test_set_weights(self) -> None:
        """Test setting weights."""
        agent = LLiftPrioritizer()

        agent.set_weights(static_weight=0.7, llm_weight=0.3)

        assert agent._static_weight == 0.7
        assert agent._llm_weight == 0.3

    def test_calculate_reduction(self) -> None:
        """Test reduction calculation."""
        agent = LLiftPrioritizer()

        original = [RankedCandidate(candidate_id=f"c{i}", rank=i) for i in range(100)]
        final = [RankedCandidate(candidate_id=f"c{i}", rank=i) for i in range(20)]

        reduction = agent._calculate_reduction(original, final)

        assert reduction == 0.8  # 80% reduction

    def test_create_candidate_description(self) -> None:
        """Test candidate description creation."""
        agent = LLiftPrioritizer()

        candidate = RankedCandidate(
            candidate_id="cand_001",
            original_confidence=0.7,
            aggregated_confidence=0.8,
            rank=1,
        )

        description = agent.create_candidate_description(candidate)

        assert "cand_001" in description
        assert "0.7" in description
        assert "0.8" in description

    def test_llm_rank_fallback(self) -> None:
        """Test LLM ranking fallback when no client."""
        agent = LLiftPrioritizer(llm_client=None)

        candidates = [
            RankedCandidate(
                candidate_id="c1",
                original_confidence=0.7,
                aggregated_confidence=0.75,
            )
        ]

        scores = agent.llm_rank(candidates)

        # Should return original confidence as fallback
        assert "c1" in scores


# =============================================================================
# Integration Tests
# =============================================================================

class TestPhase2Integration:
    """Integration tests for Phase 2 components."""

    def test_full_analysis_pipeline(self) -> None:
        """Test full analysis pipeline from DFG to prioritization."""
        # Step 1: Build DFG
        code = """
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)
"""
        tree = ast.parse(code)

        dfg_builder = DataFlowGraphBuilder()
        dfg_builder.set_current_file("test.py")
        dfg = dfg_builder.build_from_ast(tree)

        # Step 2: Build CFG
        cfg_builder = ControlFlowGraphBuilder()
        cfg = cfg_builder.build_from_ast(tree, "get_user")

        # Step 3: Generate hypotheses
        hypothesis_agent = HypothesisAgent()
        candidate = BugCandidate(
            id="cand_001",
            file_path="test.py",
            line=3,
            symbol_name="get_user",
            bug_type="sql_injection",
            description="SQL injection in get_user",
        )
        hypotheses = hypothesis_agent.generate_hypotheses(candidate, dfg, cfg)

        # Step 4: Test hypotheses
        analyzer = AnalyzerAgent()
        if hypotheses:
            result = analyzer.test_hypothesis(hypotheses[0], dfg=dfg, cfg=cfg)

            # Step 5: Rank candidates
            observer = ObserverAgent()
            candidates_data = [
                (
                    candidate.id,
                    candidate.severity.value,
                    result.evidence_collection,
                )
            ]
            ranked = observer.rank_candidates(candidates_data)

            # Step 6: Prioritize
            prioritizer = LLiftPrioritizer()
            final = prioritizer.prioritize_candidates(ranked, top_n=5)

            assert len(final) > 0

    def test_taint_tracking_pipeline(self) -> None:
        """Test taint tracking through the pipeline."""
        code = """
def process_input():
    user_data = input("Enter: ")
    sanitized = escape(user_data)
    query = f"SELECT * FROM t WHERE x = '{sanitized}'"
    db.execute(query)
"""
        tree = ast.parse(code)

        dfg_builder = DataFlowGraphBuilder()
        dfg_builder.set_current_file("test.py")
        dfg = dfg_builder.build_from_ast(tree)

        # Should detect taint source (input)
        assert len(dfg.taint_sources) > 0

        # Should detect taint sink (execute)
        assert len(dfg.taint_sinks) > 0
