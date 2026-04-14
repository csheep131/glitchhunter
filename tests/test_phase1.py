"""
Tests for Phase 1: Ingestion & Mapping modules.

Comprehensive unit tests for all Phase 1 modules.
"""

import pytest
from pathlib import Path
import tempfile
import os


# =============================================================================
# SymbolGraph Tests
# =============================================================================

class TestSymbolGraph:
    """Tests for SymbolGraph class."""

    def test_add_symbol(self):
        """Test adding a symbol to the graph."""
        from src.mapper.symbol_graph import SymbolGraph

        graph = SymbolGraph()
        graph.add_symbol(
            name="test_function",
            type="function",
            file_path="test.py",
            line_start=1,
            line_end=10,
        )

        assert len(graph) == 1
        symbol = graph.get_symbol("test_function")
        assert symbol is not None
        assert symbol.name == "test_function"
        assert symbol.type == "function"

    def test_add_edge(self):
        """Test adding an edge between symbols."""
        from src.mapper.symbol_graph import SymbolGraph, EDGE_TYPE_CALLS

        graph = SymbolGraph()
        graph.add_symbol("caller", "function", "test.py", 1, 10)
        graph.add_symbol("callee", "function", "test.py", 15, 25)
        graph.add_edge("caller", "callee", EDGE_TYPE_CALLS)

        callers = graph.get_callers("callee")
        assert "caller" in callers

        callees = graph.get_callees("caller")
        assert "callee" in callees

    def test_get_dependencies(self):
        """Test getting file dependencies."""
        from src.mapper.symbol_graph import SymbolGraph, EDGE_TYPE_IMPORTS

        graph = SymbolGraph()
        graph.add_symbol("main", "function", "main.py", 1, 10)
        graph.add_symbol("helper", "function", "helper.py", 1, 10)
        graph.add_edge("main", "helper", EDGE_TYPE_IMPORTS)

        deps = graph.get_dependencies("main.py")
        assert "helper.py" in deps

    def test_find_cycles(self):
        """Test finding circular dependencies."""
        from src.mapper.symbol_graph import SymbolGraph, EDGE_TYPE_CALLS

        graph = SymbolGraph()
        graph.add_symbol("a", "function", "test.py", 1, 5)
        graph.add_symbol("b", "function", "test.py", 10, 15)
        graph.add_symbol("c", "function", "test.py", 20, 25)

        graph.add_edge("a", "b", EDGE_TYPE_CALLS)
        graph.add_edge("b", "c", EDGE_TYPE_CALLS)
        graph.add_edge("c", "a", EDGE_TYPE_CALLS)

        cycles = graph.find_cycles(max_length=5)
        assert len(cycles) > 0

    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization."""
        from src.mapper.symbol_graph import SymbolGraph

        graph = SymbolGraph()
        graph.add_symbol("test", "function", "test.py", 1, 10)

        data = graph.to_dict()
        restored = SymbolGraph.from_dict(data)

        assert len(restored) == len(graph)
        assert restored.get_symbol("test") is not None

    def test_save_and_load_json(self):
        """Test saving and loading from JSON file."""
        from src.mapper.symbol_graph import SymbolGraph

        graph = SymbolGraph()
        graph.add_symbol("test", "function", "test.py", 1, 10)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            graph.save_json(temp_path)
            loaded = SymbolGraph.load_json(temp_path)

            assert len(loaded) == 1
            assert loaded.get_symbol("test") is not None
        finally:
            os.unlink(temp_path)


# =============================================================================
# RepositoryMapper Tests
# =============================================================================

class TestRepositoryMapper:
    """Tests for RepositoryMapper class."""

    def test_scan_repository(self):
        """Test scanning a repository."""
        from src.mapper.repo_mapper import RepositoryMapper

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test Python file
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
def hello():
    return "world"

class Test:
    pass
""")

            mapper = RepositoryMapper(Path(temp_dir))
            manifest = mapper.scan_repository()

            assert "python" in manifest.languages
            assert manifest.file_count >= 1

    def test_parse_python_file(self):
        """Test parsing a Python file."""
        from src.mapper.repo_mapper import RepositoryMapper

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
def my_function(arg1, arg2):
    pass

class MyClass:
    def method(self):
        pass

import os
from pathlib import Path
""")

            mapper = RepositoryMapper(Path(temp_dir))
            symbols = mapper.parse_file(test_file)

            assert len(symbols) >= 3  # function, class, imports

    def test_build_graph(self):
        """Test building symbol graph."""
        from src.mapper.repo_mapper import RepositoryMapper

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
def func1():
    func2()

def func2():
    pass
""")

            mapper = RepositoryMapper(Path(temp_dir))
            mapper.scan_repository()
            graph = mapper.build_graph()

            assert len(graph) >= 2


# =============================================================================
# GitChurnAnalyzer Tests
# =============================================================================

class TestGitChurnAnalyzer:
    """Tests for GitChurnAnalyzer class."""

    def test_init(self):
        """Test initialization."""
        from src.prefilter.git_churn import GitChurnAnalyzer

        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = GitChurnAnalyzer(Path(temp_dir), since_days=30)
            assert analyzer.since_days == 30

    def test_get_churn_score_no_repo(self):
        """Test churn score when repo doesn't exist."""
        from src.prefilter.git_churn import GitChurnAnalyzer

        analyzer = GitChurnAnalyzer(Path("/nonexistent"), since_days=30)
        score = analyzer.get_churn_score(Path("test.py"))
        assert score == 0.0

    def test_get_hotspots_empty(self):
        """Test getting hotspots from empty repo."""
        from src.prefilter.git_churn import GitChurnAnalyzer

        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = GitChurnAnalyzer(Path(temp_dir), since_days=30)
            hotspots = analyzer.get_hotspots(top_n=10)
            assert len(hotspots) == 0


# =============================================================================
# SemgrepRunner Tests
# =============================================================================

class TestSemgrepRunner:
    """Tests for SemgrepRunner class."""

    def test_init(self):
        """Test initialization."""
        from src.prefilter.semgrep_runner import SemgrepRunner

        runner = SemgrepRunner(timeout=60)
        assert runner.timeout == 60

    def test_is_available(self):
        """Test checking Semgrep availability."""
        from src.prefilter.semgrep_runner import SemgrepRunner

        runner = SemgrepRunner()
        # This may return True or False depending on installation
        result = runner.is_available()
        assert isinstance(result, bool)

    def test_parse_json_output(self):
        """Test parsing Semgrep JSON output."""
        from src.prefilter.semgrep_runner import SemgrepRunner

        runner = SemgrepRunner()
        json_output = """
        {
            "results": [
                {
                    "rule_id": "test-rule",
                    "message": "Test finding",
                    "severity": "WARNING",
                    "path": "test.py",
                    "start": {"line": 1, "col": 1},
                    "end": {"line": 2, "col": 10}
                }
            ],
            "errors": []
        }
        """

        result = runner.parse_json_output(json_output)
        assert result.finding_count == 1
        assert result.findings[0].rule_id == "test-rule"


# =============================================================================
# ASTAnalyzer Tests
# =============================================================================

class TestASTAnalyzer:
    """Tests for ASTAnalyzer class."""

    def test_init(self):
        """Test initialization."""
        from src.prefilter.ast_analyzer import ASTAnalyzer

        analyzer = ASTAnalyzer()
        assert "python" in analyzer.languages

    def test_parse_file_not_found(self):
        """Test parsing non-existent file."""
        from src.prefilter.ast_analyzer import ASTAnalyzer
        from src.core.exceptions import ValidationError

        analyzer = ASTAnalyzer()
        with pytest.raises(ValidationError):
            analyzer.parse_file(Path("/nonexistent/file.py"))

    def test_detect_language(self):
        """Test language detection."""
        from src.prefilter.ast_analyzer import ASTAnalyzer

        analyzer = ASTAnalyzer()
        assert analyzer._detect_language(Path("test.py")) == "python"
        assert analyzer._detect_language(Path("test.js")) == "javascript"
        assert analyzer._detect_language(Path("test.rs")) == "rust"

    def test_find_security_patterns(self):
        """Test finding security patterns."""
        from src.prefilter.ast_analyzer import ASTAnalyzer

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
password = "secret123"
os.system("echo " + user_input)
""")

            analyzer = ASTAnalyzer()
            findings = analyzer.find_security_patterns(test_file)

            assert len(findings) > 0


# =============================================================================
# ComplexityAnalyzer Tests
# =============================================================================

class TestComplexityAnalyzer:
    """Tests for ComplexityAnalyzer class."""

    def test_init(self):
        """Test initialization."""
        from src.prefilter.complexity import ComplexityAnalyzer

        analyzer = ComplexityAnalyzer(max_cyclomatic=10)
        assert analyzer.max_cyclomatic == 10

    def test_analyze_file_not_found(self):
        """Test analyzing non-existent file."""
        from src.prefilter.complexity import ComplexityAnalyzer

        analyzer = ComplexityAnalyzer()
        metrics = analyzer.analyze_file(Path("/nonexistent/file.py"))

        assert metrics.lines_of_code == 0

    def test_simple_analysis(self):
        """Test simple complexity analysis."""
        from src.prefilter.complexity import ComplexityAnalyzer

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
def simple():
    return 1

def complex():
    if True:
        if True:
            if True:
                return 1
    return 0
""")

            analyzer = ComplexityAnalyzer()
            metrics = analyzer.analyze_file(test_file)

            assert metrics.lines_of_code > 0


# =============================================================================
# RepomixWrapper Tests
# =============================================================================

class TestRepomixWrapper:
    """Tests for RepomixWrapper class."""

    def test_init(self):
        """Test initialization."""
        from src.mapper.repomix_wrapper import RepomixWrapper

        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper = RepomixWrapper(Path(temp_dir))
            assert wrapper.output_format == "xml"

    def test_is_available(self):
        """Test checking Repomix availability."""
        from src.mapper.repomix_wrapper import RepomixWrapper

        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper = RepomixWrapper(Path(temp_dir))
            result = wrapper.is_available()
            assert isinstance(result, bool)


# =============================================================================
# RegressionTestGenerator Tests
# =============================================================================

class TestRegressionTestGenerator:
    """Tests for RegressionTestGenerator class."""

    def test_init(self):
        """Test initialization."""
        from src.fixing.regression_test_generator import RegressionTestGenerator

        generator = RegressionTestGenerator()
        assert "python" in generator.frameworks

    def test_generate_test_for_bug(self):
        """Test generating test for a bug."""
        from src.fixing.regression_test_generator import RegressionTestGenerator, Candidate

        generator = RegressionTestGenerator()
        candidate = Candidate(
            file_path="test.py",
            bug_type="sql_injection",
            description="SQL injection vulnerability",
            line_start=10,
            line_end=15,
        )

        test = generator.generate_test_for_bug(candidate)

        assert test.name.startswith("test_regression_")
        assert "hypothesis" in test.test_code

    def test_detect_language(self):
        """Test language detection."""
        from src.fixing.regression_test_generator import RegressionTestGenerator

        generator = RegressionTestGenerator()
        assert generator._detect_language("test.py") == "python"
        assert generator._detect_language("test.rs") == "rust"
        assert generator._detect_language("test.js") == "javascript"


# =============================================================================
# SemanticDiffValidator Tests
# =============================================================================

class TestSemanticDiffValidator:
    """Tests for SemanticDiffValidator class."""

    def test_init(self):
        """Test initialization."""
        from src.fixing.semantic_diff import SemanticDiffValidator

        validator = SemanticDiffValidator()

    def test_compute_diff(self):
        """Test computing semantic diff."""
        from src.fixing.semantic_diff import SemanticDiffValidator

        validator = SemanticDiffValidator()

        original = """
def hello():
    return "world"
"""

        patched = """
def hello(name):
    return f"hello {name}"

def goodbye():
    pass
"""

        diff = validator.compute_diff(original, patched, language="python")

        assert "goodbye" in diff.added_symbols
        assert "hello" in diff.modified_symbols

    def test_extract_python_symbols(self):
        """Test extracting Python symbols."""
        from src.fixing.semantic_diff import SemanticDiffValidator

        validator = SemanticDiffValidator()
        code = """
def func1():
    pass

class MyClass:
    pass
"""
        symbols = validator._extract_python_symbols(code)

        assert "func1" in symbols
        assert "MyClass" in symbols


# =============================================================================
# EscalationManager Tests
# =============================================================================

class TestEscalationManager:
    """Tests for EscalationManager class."""

    def test_init(self):
        """Test initialization."""
        from src.fixing.escalation_manager import EscalationManager

        manager = EscalationManager(max_loops=5, no_improvement_threshold=2)
        assert manager.max_loops == 5

    def test_should_escalate(self):
        """Test escalation decision."""
        from src.fixing.escalation_manager import EscalationManager

        manager = EscalationManager(max_loops=5, no_improvement_threshold=3)

        # Should not escalate early
        assert not manager.should_escalate(current_loop=1, no_improvement_count=1)

        # Should escalate at max loops
        assert manager.should_escalate(current_loop=5, no_improvement_count=0)

        # Should escalate after threshold
        assert manager.should_escalate(current_loop=2, no_improvement_count=3)

    def test_apply_escalation(self):
        """Test applying escalation."""
        from src.fixing.escalation_manager import EscalationManager

        manager = EscalationManager()

        context = manager.apply_escalation()
        assert context.level == 1

        context = manager.apply_escalation()
        assert context.level == 2

    def test_generate_human_report(self):
        """Test generating human report."""
        from src.fixing.escalation_manager import EscalationManager, EscalationContext

        manager = EscalationManager()
        context = EscalationContext(level=4, reason="Test escalation")

        report = manager.generate_human_report(context)

        assert report.title is not None
        assert report.summary is not None

    def test_get_status(self):
        """Test getting status."""
        from src.fixing.escalation_manager import EscalationManager

        manager = EscalationManager()
        status = manager.get_status()

        assert status["current_level"] == 0
        assert status["max_level"] == 4


# =============================================================================
# StateMachine Tests
# =============================================================================

class TestStateMachine:
    """Tests for StateMachine class."""

    def test_init(self):
        """Test initialization."""
        from src.agent.state_machine import StateMachine

        machine = StateMachine()
        assert machine.workflow is not None

    def test_build_workflow(self):
        """Test building workflow."""
        from src.agent.state_machine import build_workflow

        workflow = build_workflow()
        assert workflow is not None
        assert workflow.app is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
