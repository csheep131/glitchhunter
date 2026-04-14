"""
Tests for PreFilter module.

Unit tests for SemgrepRunner, ASTAnalyzer, and PreFilterPipeline.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from prefilter.ast_analyzer import ASTAnalyzer, ASTSymbol
from prefilter.semgrep_runner import SemgrepResult, SemgrepRunner


class TestSemgrepRunner:
    """Test cases for SemgrepRunner."""

    def test_init(self) -> None:
        """Test SemgrepRunner initialization."""
        runner = SemgrepRunner()
        assert runner.semgrep_path == "semgrep"
        assert runner.timeout == 300

    def test_init_with_custom_path(self) -> None:
        """Test initialization with custom semgrep path."""
        runner = SemgrepRunner(semgrep_path="/usr/local/bin/semgrep")
        assert runner.semgrep_path == "/usr/local/bin/semgrep"

    def test_is_available_success(self) -> None:
        """Test availability check when semgrep is installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="1.60.0")
            runner = SemgrepRunner()
            assert runner.is_available()

    def test_is_available_failure(self) -> None:
        """Test availability check when semgrep is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            runner = SemgrepRunner()
            assert not runner.is_available()

    def test_get_version_success(self) -> None:
        """Test version retrieval."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="semgrep 1.60.0"
            )
            runner = SemgrepRunner()
            version = runner.get_version()
            assert version == "semgrep 1.60.0"

    def test_get_version_failure(self) -> None:
        """Test version retrieval failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Failed")
            runner = SemgrepRunner()
            version = runner.get_version()
            assert version is None

    def test_parse_output(self) -> None:
        """Test parsing Semgrep JSON output."""
        runner = SemgrepRunner()
        json_output = """
        {
            "results": [
                {
                    "rule_id": "python.lang.security.sql-injection",
                    "message": "SQL injection vulnerability",
                    "severity": "ERROR",
                    "path": "src/auth.py",
                    "start": {"line": 42, "col": 10},
                    "end": {"line": 45, "col": 20},
                    "extra": {
                        "lines": "query = f'SELECT * FROM users WHERE...'",
                        "fix": "Use parameterized queries"
                    }
                }
            ],
            "errors": []
        }
        """

        repo_path = Path("/test/repo")
        result = runner._parse_output(json_output, repo_path)

        assert isinstance(result, SemgrepResult)
        assert result.finding_count == 1
        assert result.rules_matched == 1

        finding = result.findings[0]
        assert finding.rule_id == "python.lang.security.sql-injection"
        assert finding.severity == "ERROR"
        assert finding.file_path == "/test/repo/src/auth.py"
        assert finding.line_start == 42

    def test_parse_output_empty(self) -> None:
        """Test parsing empty output."""
        runner = SemgrepRunner()
        json_output = '{"results": [], "errors": []}'

        repo_path = Path("/test/repo")
        result = runner._parse_output(json_output, repo_path)

        assert result.finding_count == 0
        assert result.rules_matched == 0

    def test_parse_output_invalid_json(self) -> None:
        """Test parsing invalid JSON."""
        runner = SemgrepRunner()
        json_output = "not valid json"

        repo_path = Path("/test/repo")
        result = runner._parse_output(json_output, repo_path)

        assert result.finding_count == 0
        assert len(result.errors) > 0

    def test_by_severity(self) -> None:
        """Test grouping findings by severity."""
        result = SemgrepResult(
            findings=[
                MagicMock(severity="ERROR"),
                MagicMock(severity="WARNING"),
                MagicMock(severity="WARNING"),
                MagicMock(severity="INFO"),
            ]
        )

        grouped = result.by_severity()

        assert len(grouped["ERROR"]) == 1
        assert len(grouped["WARNING"]) == 2
        assert len(grouped["INFO"]) == 1

    def test_has_critical(self) -> None:
        """Test has_critical property."""
        result_no_critical = SemgrepResult(
            findings=[MagicMock(severity="WARNING")]
        )
        assert not result_no_critical.has_critical

        result_with_critical = SemgrepResult(
            findings=[MagicMock(severity="ERROR")]
        )
        assert result_with_critical.has_critical


class TestASTAnalyzer:
    """Test cases for ASTAnalyzer."""

    def test_init(self) -> None:
        """Test ASTAnalyzer initialization."""
        analyzer = ASTAnalyzer()
        assert "python" in analyzer.languages
        assert "javascript" in analyzer.languages

    def test_detect_language_python(self) -> None:
        """Test language detection for Python."""
        analyzer = ASTAnalyzer()
        lang = analyzer._detect_language(Path("test.py"))
        assert lang == "python"

    def test_detect_language_javascript(self) -> None:
        """Test language detection for JavaScript."""
        analyzer = ASTAnalyzer()
        lang = analyzer._detect_language(Path("test.js"))
        assert lang == "javascript"

    def test_detect_language_typescript(self) -> None:
        """Test language detection for TypeScript."""
        analyzer = ASTAnalyzer()
        lang = analyzer._detect_language(Path("test.ts"))
        assert lang == "typescript"

    def test_detect_language_unknown(self) -> None:
        """Test language detection for unknown extension."""
        analyzer = ASTAnalyzer()
        lang = analyzer._detect_language(Path("test.xyz"))
        assert lang is None

    def test_parse_file_nonexistent(self) -> None:
        """Test parsing nonexistent file."""
        analyzer = ASTAnalyzer()
        with pytest.raises(Exception):
            analyzer.parse_file(Path("/nonexistent/file.py"))

    def test_parse_file_success(self, tmp_path: Path) -> None:
        """Test parsing valid Python file."""
        # Create a temporary Python file
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def hello():
    print("Hello, World!")

class MyClass:
    pass
""")

        analyzer = ASTAnalyzer()

        # Skip if tree-sitter not available
        try:
            import tree_sitter_python  # noqa: F401
        except ImportError:
            pytest.skip("tree-sitter-python not installed")

        tree = analyzer.parse_file(test_file)
        assert tree is not None

    def test_extract_symbols(self, tmp_path: Path) -> None:
        """Test symbol extraction."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def my_function(arg1, arg2):
    return arg1 + arg2

class MyClass:
    def method(self):
        pass
""")

        analyzer = ASTAnalyzer()

        # Skip if tree-sitter not available
        try:
            import tree_sitter_python  # noqa: F401
        except ImportError:
            pytest.skip("tree-sitter-python not installed")

        symbols = analyzer.extract_symbols(test_file)

        # Should find at least the function and class
        assert len(symbols) >= 1

    def test_get_language_stats(self, tmp_path: Path) -> None:
        """Test language statistics."""
        # Create test files
        (tmp_path / "test.py").write_text("print('hello')")
        (tmp_path / "test.js").write_text("console.log('hello')")

        analyzer = ASTAnalyzer()
        stats = analyzer.get_language_stats(tmp_path)

        assert "python" in stats or "javascript" in stats


class TestPreFilterPipeline:
    """Test cases for PreFilterPipeline."""

    def test_init(self, tmp_path: Path) -> None:
        """Test PreFilterPipeline initialization."""
        from prefilter.pipeline import PreFilterPipeline

        pipeline = PreFilterPipeline(tmp_path)

        assert pipeline.repo_path == tmp_path
        assert pipeline.semgrep_runner is not None
        assert pipeline.ast_analyzer is not None
        assert pipeline.complexity_analyzer is not None
        assert pipeline.git_analyzer is not None

    def test_run_minimal(self, tmp_path: Path) -> None:
        """Test running pipeline with minimal options."""
        from prefilter.pipeline import PreFilterPipeline

        # Create a simple Python file
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        pipeline = PreFilterPipeline(tmp_path)

        # Run with security and git disabled (no git repo)
        result = pipeline.run(
            run_security=False,
            run_correctness=False,
            run_complexity=False,
            run_git=False,
        )

        assert result is not None
        assert result.stats is not None
