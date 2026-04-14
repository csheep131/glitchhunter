"""
Coverage Checker für GlitchHunter.

Stellt sicher, dass Patches keine Coverage-Regression verursachen.
Unterstützt verschiedene Sprachen und Coverage-Tools.
"""

import logging
import subprocess
import tempfile
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CoverageMetrics:
    """
    Coverage-Metriken.

    Attributes:
        line_coverage: Line Coverage (0-1).
        branch_coverage: Branch Coverage (0-1).
        function_coverage: Function Coverage (0-1).
        covered_lines: Anzahl gedeckter Zeilen.
        total_lines: Gesamtanzahl Zeilen.
        covered_branches: Anzahl gedeckter Branches.
        total_branches: Gesamtanzahl Branches.
    """

    line_coverage: float = 0.0
    branch_coverage: float = 0.0
    function_coverage: float = 0.0
    covered_lines: int = 0
    total_lines: int = 0
    covered_branches: int = 0
    total_branches: int = 0

    @property
    def coverage_percentage(self) -> float:
        """Line Coverage als Prozent."""
        return self.line_coverage * 100

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "line_coverage": self.line_coverage,
            "branch_coverage": self.branch_coverage,
            "function_coverage": self.function_coverage,
            "covered_lines": self.covered_lines,
            "total_lines": self.total_lines,
            "covered_branches": self.covered_branches,
            "total_branches": self.total_branches,
            "coverage_percentage": self.coverage_percentage,
        }


@dataclass
class CoverageDiff:
    """
    Coverage-Differenz zwischen Before und After.

    Attributes:
        before: Coverage vor Patch.
        after: Coverage nach Patch.
        delta_line: Änderung Line Coverage.
        delta_branch: Änderung Branch Coverage.
        delta_function: Änderung Function Coverage.
        regression: True wenn Regression erkannt.
    """

    before: CoverageMetrics
    after: CoverageMetrics
    delta_line: float = 0.0
    delta_branch: float = 0.0
    delta_function: float = 0.0
    _regression: bool = field(default=False, repr=False)

    @property
    def regression(self) -> bool:
        """Check if regression detected (delta < -tolerance)."""
        # Use tolerance of 0.01 (1%) by default
        return self.delta_line < -0.01

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "delta_line": self.delta_line,
            "delta_branch": self.delta_branch,
            "delta_function": self.delta_function,
            "regression": self.regression,
        }


@dataclass
class CoverageCheckResult:
    """
    Ergebnis des Coverage-Checks.

    Attributes:
        passed: True wenn Check bestanden.
        coverage_diff: Coverage-Differenz.
        uncovered_files: Nicht getestete Dateien.
        uncovered_lines: Nicht getestete Zeilen.
        recommendations: Empfehlungen.
    """

    passed: bool = False
    coverage_diff: Optional[CoverageDiff] = None
    uncovered_files: List[str] = field(default_factory=list)
    uncovered_lines: List[Tuple[str, int]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "passed": self.passed,
            "coverage_diff": self.coverage_diff.to_dict() if self.coverage_diff else None,
            "uncovered_files": self.uncovered_files,
            "uncovered_lines": self.uncovered_lines,
            "recommendations": self.recommendations,
        }


class CoverageChecker:
    """
    Prüft Coverage-Regressionen.

    Unterstützte Sprachen:
    - Python: coverage.py, pytest-cov
    - Rust: cargo-tarpaulin, llvm-cov
    - JavaScript/TypeScript: istanbul/nyc, jest --coverage

    Usage:
        checker = CoverageChecker(language="python")
        result = checker.check_coverage(original_code, patched_code, test_code)
    """

    # Toleranz für Coverage-Regression (0.01 = 1%)
    COVERAGE_TOLERANCE = 0.01

    def __init__(
        self,
        language: str = "python",
        coverage_tool: Optional[str] = None,
        coverage_tolerance: float = COVERAGE_TOLERANCE,
    ) -> None:
        """
        Initialisiert Coverage Checker.

        Args:
            language: Programmiersprache.
            coverage_tool: Spezifisches Coverage-Tool.
            coverage_tolerance: Toleranz für Regression.
        """
        self.language = language
        self.coverage_tool = coverage_tool or self._default_coverage_tool(language)
        self.coverage_tolerance = coverage_tolerance

        logger.debug(
            f"CoverageChecker initialisiert: language={language}, "
            f"tool={self.coverage_tool}, tolerance={coverage_tolerance}"
        )

    def _default_coverage_tool(self, language: str) -> str:
        """Wählt default Coverage-Tool für Sprache."""
        tools = {
            "python": "coverage",
            "rust": "cargo-tarpaulin",
            "javascript": "nyc",
            "typescript": "nyc",
        }
        return tools.get(language, "unknown")

    def check_coverage(
        self,
        code: str,
        test_code: str,
        file_path: Optional[str] = None,
        before_coverage: Optional[CoverageMetrics] = None,
    ) -> CoverageCheckResult:
        """
        Prüft Coverage nach Patch.

        Args:
            code: Gepatchter Code.
            test_code: Test-Code.
            file_path: Optionaler Dateipfad.
            before_coverage: Coverage vor Patch.

        Returns:
            CoverageCheckResult.
        """
        logger.info("Starte Coverage-Check")

        result = CoverageCheckResult()

        # 1. Coverage messen
        after_coverage = self._measure_coverage(code, test_code, file_path)
        result.coverage_diff = CoverageDiff(
            before=before_coverage or CoverageMetrics(),
            after=after_coverage,
        )

        # 2. Delta berechnen
        if before_coverage:
            result.coverage_diff.delta_line = (
                after_coverage.line_coverage - before_coverage.line_coverage
            )
            result.coverage_diff.delta_branch = (
                after_coverage.branch_coverage - before_coverage.branch_coverage
            )
            result.coverage_diff.delta_function = (
                after_coverage.function_coverage - before_coverage.function_coverage
            )

            # 3. Regression prüfen
            result.coverage_diff.regression = (
                result.coverage_diff.delta_line < -self.coverage_tolerance
            )

        # 4. Empfehlungen generieren
        result.recommendations = self._generate_recommendations(result.coverage_diff)

        # 5. Gesamtergebnis
        result.passed = not (result.coverage_diff and result.coverage_diff.regression)

        logger.info(
            f"Coverage-Check abgeschlossen: passed={result.passed}, "
            f"line_coverage={after_coverage.line_coverage:.2%}"
        )

        return result

    def check_coverage_in_project(
        self,
        project_path: str,
        test_command: Optional[str] = None,
        before_coverage: Optional[CoverageMetrics] = None,
    ) -> CoverageCheckResult:
        """
        Prüft Coverage im Projekt.

        Args:
            project_path: Pfad zum Projekt.
            test_command: Test-Command.
            before_coverage: Coverage vor Patch.

        Returns:
            CoverageCheckResult.
        """
        logger.info(f"Starte Coverage-Check für Projekt: {project_path}")

        result = CoverageCheckResult()

        # Coverage-Report generieren
        coverage_report = self._run_coverage_tool(project_path, test_command)

        if coverage_report:
            after_coverage = self._parse_coverage_report(coverage_report)
            result.coverage_diff = CoverageDiff(
                before=before_coverage or CoverageMetrics(),
                after=after_coverage,
            )

            # Delta berechnen
            if before_coverage:
                result.coverage_diff.delta_line = (
                    after_coverage.line_coverage - before_coverage.line_coverage
                )
                result.coverage_diff.regression = (
                    result.coverage_diff.delta_line < -self.coverage_tolerance
                )

        result.passed = not (result.coverage_diff and result.coverage_diff.regression)

        return result

    def _measure_coverage(
        self,
        code: str,
        test_code: str,
        file_path: Optional[str] = None,
    ) -> CoverageMetrics:
        """
        Misst Coverage für Code.

        Args:
            code: Code.
            test_code: Test-Code.
            file_path: Optionaler Dateipfad.

        Returns:
            CoverageMetrics.
        """
        if self.language == "python":
            return self._measure_python_coverage(code, test_code, file_path)
        elif self.language == "rust":
            return self._measure_rust_coverage(code, test_code, file_path)
        elif self.language in ("javascript", "typescript"):
            return self._measure_javascript_coverage(code, test_code, file_path)
        else:
            logger.warning(f"Coverage-Messung für {self.language} nicht implementiert")
            return CoverageMetrics()

    def _measure_python_coverage(
        self,
        code: str,
        test_code: str,
        file_path: Optional[str] = None,
    ) -> CoverageMetrics:
        """Misst Python-Coverage mit coverage.py."""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)

                # Code schreiben
                if file_path:
                    code_file = tmpdir_path / Path(file_path).name
                else:
                    code_file = tmpdir_path / "code.py"
                code_file.write_text(code)

                # Test-Code schreiben
                test_file = tmpdir_path / "test_code.py"
                test_file.write_text(test_code)

                # Coverage.py ausführen
                result = subprocess.run(
                    [
                        "coverage", "run",
                        "--source", str(tmpdir_path),
                        "-m", "pytest",
                        str(test_file),
                        "-v",
                    ],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                # Coverage-Report generieren
                result_json = subprocess.run(
                    ["coverage", "json", "-o", str(tmpdir_path / "coverage.json")],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                # JSON parsen
                coverage_json = tmpdir_path / "coverage.json"
                if coverage_json.exists():
                    with open(coverage_json) as f:
                        data = json.load(f)
                        return self._parse_python_coverage_json(data)

        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning(f"Coverage-Messung fehlgeschlagen: {e}")

        return CoverageMetrics()

    def _parse_python_coverage_json(self, data: Dict[str, Any]) -> CoverageMetrics:
        """Parses Python-Coverage-JSON."""
        totals = data.get("totals", {})

        return CoverageMetrics(
            line_coverage=totals.get("percent_covered", 0.0) / 100.0,
            covered_lines=totals.get("covered_lines", 0),
            total_lines=totals.get("num_lines", 0),
            covered_branches=totals.get("covered_branches", 0),
            total_branches=totals.get("num_branches", 0),
            branch_coverage=totals.get("percent_covered_branches", 0.0) / 100.0,
        )

    def _measure_rust_coverage(
        self,
        code: str,
        test_code: str,
        file_path: Optional[str] = None,
    ) -> CoverageMetrics:
        """Misst Rust-Coverage mit cargo-tarpaulin."""
        try:
            # Temporäres Cargo-Projekt
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)

                # Cargo.toml
                cargo_toml = tmpdir_path / "Cargo.toml"
                cargo_toml.write_text("""
[package]
name = "coverage_test"
version = "0.1.0"
edition = "2021"

[dependencies]
""")

                # src/lib.rs
                src_dir = tmpdir_path / "src"
                src_dir.mkdir()
                lib_rs = src_dir / "lib.rs"
                lib_rs.write_text(code)

                # Tests ausführen mit Coverage
                result = subprocess.run(
                    [
                        "cargo", "tarpaulin",
                        "--out", "Json",
                        "--output-dir", str(tmpdir_path),
                    ],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                # JSON parsen
                coverage_json = tmpdir_path / "tarpaulin-results.json"
                if coverage_json.exists():
                    with open(coverage_json) as f:
                        data = json.load(f)
                        return self._parse_rust_coverage_json(data)

        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning(f"Rust-Coverage-Messung fehlgeschlagen: {e}")

        return CoverageMetrics()

    def _parse_rust_coverage_json(self, data: Dict[str, Any]) -> CoverageMetrics:
        """Parses Rust-Coverage-JSON."""
        # Tarpaulin-Format
        total_lines = 0
        covered_lines = 0

        for file_data in data.get("files", []):
            for line in file_data.get("lines", []):
                total_lines += 1
                if line.get("covered", False):
                    covered_lines += 1

        line_coverage = covered_lines / total_lines if total_lines > 0 else 0.0

        return CoverageMetrics(
            line_coverage=line_coverage,
            covered_lines=covered_lines,
            total_lines=total_lines,
        )

    def _measure_javascript_coverage(
        self,
        code: str,
        test_code: str,
        file_path: Optional[str] = None,
    ) -> CoverageMetrics:
        """Misst JavaScript-Coverage mit nyc/jest."""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)

                # package.json
                package_json = tmpdir_path / "package.json"
                package_json.write_text("""
{
    "name": "coverage-test",
    "version": "1.0.0",
    "scripts": {
        "test": "jest --coverage"
    },
    "devDependencies": {
        "jest": "^29.0.0"
    }
}
""")

                # Code schreiben
                if file_path:
                    code_file = tmpdir_path / file_path
                else:
                    code_file = tmpdir_path / "code.js"
                code_file.parent.mkdir(parents=True, exist_ok=True)
                code_file.write_text(code)

                # Tests ausführen
                result = subprocess.run(
                    ["npm", "test"],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                # Coverage-JSON parsen
                coverage_dir = tmpdir_path / "coverage"
                coverage_json = coverage_dir / "coverage-final.json"
                if coverage_json.exists():
                    with open(coverage_json) as f:
                        data = json.load(f)
                        return self._parse_javascript_coverage_json(data)

        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning(f"JavaScript-Coverage-Messung fehlgeschlagen: {e}")

        return CoverageMetrics()

    def _parse_javascript_coverage_json(self, data: Dict[str, Any]) -> CoverageMetrics:
        """Parses JavaScript-Coverage-JSON."""
        total_lines = 0
        covered_lines = 0

        for file_data in data.values():
            if isinstance(file_data, dict):
                statement_map = file_data.get("statementMap", {})
                s = file_data.get("s", {})

                for key in statement_map:
                    total_lines += 1
                    if s.get(key, 0) > 0:
                        covered_lines += 1

        line_coverage = covered_lines / total_lines if total_lines > 0 else 0.0

        return CoverageMetrics(
            line_coverage=line_coverage,
            covered_lines=covered_lines,
            total_lines=total_lines,
        )

    def _run_coverage_tool(
        self,
        project_path: str,
        test_command: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Führt Coverage-Tool im Projekt aus.

        Args:
            project_path: Pfad zum Projekt.
            test_command: Test-Command.

        Returns:
            Coverage-Report als Dict.
        """
        try:
            cmd = test_command or self._default_test_command()

            result = subprocess.run(
                cmd,
                shell=True,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=300,
            )

            # Coverage-Report suchen
            coverage_files = [
                "coverage.json",
                "coverage/coverage-final.json",
                "tarpaulin-results.json",
            ]

            for coverage_file in coverage_files:
                coverage_path = Path(project_path) / coverage_file
                if coverage_path.exists():
                    with open(coverage_path) as f:
                        return json.load(f)

        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"Coverage-Tool fehlgeschlagen: {e}")

        return None

    def _default_test_command(self) -> str:
        """Default Test-Command für Sprache."""
        commands = {
            "python": "pytest --cov=. --cov-report=json",
            "rust": "cargo tarpaulin --out Json",
            "javascript": "npm test -- --coverage",
            "typescript": "npm test -- --coverage",
        }
        return commands.get(self.language, "test")

    def _parse_coverage_report(self, report: Dict[str, Any]) -> CoverageMetrics:
        """Parses Coverage-Report basierend auf Sprache."""
        if self.language == "python":
            return self._parse_python_coverage_json(report)
        elif self.language == "rust":
            return self._parse_rust_coverage_json(report)
        elif self.language in ("javascript", "typescript"):
            return self._parse_javascript_coverage_json(report)
        else:
            return CoverageMetrics()

    def _generate_recommendations(
        self,
        coverage_diff: CoverageDiff,
    ) -> List[str]:
        """
        Generiert Empfehlungen basierend auf Coverage.

        Args:
            coverage_diff: Coverage-Differenz.

        Returns:
            Liste von Empfehlungen.
        """
        recommendations = []

        if coverage_diff.regression:
            recommendations.append(
                f"Coverage-Regression erkannt: {coverage_diff.delta_line:.2%} "
                "Verlust. Füge Tests für neue Code-Pfade hinzu."
            )

        if coverage_diff.after.line_coverage < 0.8:
            recommendations.append(
                f"Gesamt-Coverage ist niedrig ({coverage_diff.after.line_coverage:.2%}). "
                "Erwäge zusätzliche Tests zu schreiben."
            )

        if coverage_diff.after.branch_coverage < 0.7:
            recommendations.append(
                f"Branch-Coverage ist niedrig ({coverage_diff.after.branch_coverage:.2%}). "
                "Teste mehr Verzweigungen und Edge-Cases."
            )

        if not recommendations:
            recommendations.append("Coverage ist gut. Weiter so!")

        return recommendations

    def __call__(self, state: Any) -> Dict[str, Any]:
        """
        Callable für LangGraph.

        Args:
            state: AgentState.

        Returns:
            State-Updates.
        """
        # TODO: Typisierung verbessern
        code = getattr(state, "code", "")
        test_code = getattr(state, "test_code", "")
        before_coverage = getattr(state, "before_coverage", None)

        result = self.check_coverage(code, test_code, before_coverage=before_coverage)

        return {
            "coverage_result": result.to_dict(),
            "metadata": {
                "coverage_passed": result.passed,
                "regression_detected": result.coverage_diff.regression if result.coverage_diff else False,
                "line_coverage": result.coverage_diff.after.line_coverage if result.coverage_diff else 0.0,
            },
        }
