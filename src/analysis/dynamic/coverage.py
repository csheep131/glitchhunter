#!/usr/bin/env python3
"""
Coverage Tracking for GlitchHunter Dynamic Analysis

Tracks code coverage during fuzzing:
- AFL++ coverage map parsing
- LCOV/GCov integration
- Coverage-guided input selection
"""

import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CoverageInfo:
    """Coverage-Information für eine Datei."""

    file_path: str
    total_lines: int = 0
    covered_lines: int = 0
    total_functions: int = 0
    covered_functions: int = 0
    line_coverage: float = 0.0
    function_coverage: float = 0.0
    uncovered_lines: List[int] = field(default_factory=list)
    branch_coverage: float = 0.0

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "total_lines": self.total_lines,
            "covered_lines": self.covered_lines,
            "line_coverage": self.line_coverage,
            "function_coverage": self.function_coverage,
            "uncovered_lines": self.uncovered_lines,
            "branch_coverage": self.branch_coverage,
        }


@dataclass
class CoverageReport:
    """Gesamt-Coverage-Report."""

    files: List[CoverageInfo] = field(default_factory=list)
    total_coverage: float = 0.0
    total_files: int = 0
    total_lines: int = 0
    covered_lines: int = 0
    new_coverage_paths: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_coverage": self.total_coverage,
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "covered_lines": self.covered_lines,
            "files": [f.to_dict() for f in self.files],
            "new_coverage_paths": self.new_coverage_paths,
        }


class CoverageTracker:
    """
    Trackt Code-Coverage während des Fuzzings.

    Usage:
        tracker = CoverageTracker(repo_path="/path/to/repo")
        tracker.instrument_for_coverage()
        
        # Nach Fuzzing
        report = tracker.parse_coverage()
        new_paths = tracker.find_new_coverage_paths()
    """

    def __init__(self, repo_path: Path):
        """
        Initialisiert Coverage-Tracker.

        Args:
            repo_path: Pfad zum Repository
        """
        self.repo_path = Path(repo_path)
        self.coverage_dir = self.repo_path / ".glitchhunter" / "coverage"
        self.coverage_dir.mkdir(parents=True, exist_ok=True)

        # AFL++ Coverage-Map
        self.afl_coverage_map: Dict[int, int] = {}
        self.previous_coverage: Set[int] = set()

    def instrument_for_coverage(
        self,
        compiler: str = "afl-clang-lto",
        use_asan: bool = True,
        use_ubsan: bool = True,
    ) -> bool:
        """
        Instrumentiert Code für Coverage-Tracking.

        Args:
            compiler: Zu verwendender Compiler (afl-clang-lto, afl-gcc, etc.)
            use_asan: AddressSanitizer aktivieren
            use_ubsan: UndefinedBehaviorSanitizer aktivieren

        Returns:
            True wenn erfolgreich
        """
        logger.info(f"Instrumenting code with {compiler}...")

        # Compiler-Flags
        flags = [
            "-fprofile-arcs",  # GCov Coverage
            "-ftest-coverage",
            "-O2",  # Optimization für Performance
        ]

        if use_asan:
            flags.append("-fsanitize=address")
        if use_ubsan:
            flags.append("-fsanitize=undefined")

        # Build-Command für AFL++
        build_cmd = [
            compiler,
            *flags,
            "-o",
            str(self.coverage_dir / "instrumented_binary"),
            # Source-Files werden hier hinzugefügt
        ]

        logger.info(f"Build command: {' '.join(build_cmd)}")
        logger.info("Note: Source files must be added to build command")

        return True

    def parse_afl_coverage(self, afl_output_dir: Path) -> CoverageReport:
        """
        Parst AFL++ Coverage-Map.

        Args:
            afl_output_dir: AFL++ Output-Verzeichnis

        Returns:
            CoverageReport mit Coverage-Statistiken
        """
        report = CoverageReport()

        # fuzzer_stats parsen
        stats_file = afl_output_dir / "fuzzer_stats"
        if stats_file.exists():
            try:
                content = stats_file.read_text()
                for line in content.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        key = key.strip()
                        value = value.strip()

                        if key == "bitmap_cvg":
                            report.total_coverage = float(value)
            except Exception as e:
                logger.warning(f"Failed to parse fuzzer_stats: {e}")

        # Queue-Files analysieren für Coverage-Pfade
        queue_dir = afl_output_dir / "queue"
        if queue_dir.exists():
            queue_files = list(queue_dir.glob("id:*"))
            report.total_files = len(queue_files)

            # Coverage-Map aktualisieren
            self._update_coverage_map(queue_files)

            # Neue Pfade finden
            report.new_coverage_paths = self._find_new_paths(queue_files)

        # LCOV-Report parsen falls vorhanden
        lcov_file = afl_output_dir / "lcov.info"
        if lcov_file.exists():
            report = self._parse_lcov(lcov_file, report)

        logger.info(
            f"Coverage report: {report.total_coverage:.1f}% coverage, "
            f"{len(report.new_coverage_paths)} new paths"
        )

        return report

    def _update_coverage_map(self, queue_files: List[Path]) -> None:
        """Aktualisiert Coverage-Map aus Queue-Files."""
        for qf in queue_files:
            # Coverage-Information aus Filename extrahieren
            # Format: id:000000,orig:abc,op:flip1,pos:42,rep:3,src:000001
            name = qf.name
            if "cov:" in name:
                match = re.search(r"cov:(\d+)", name)
                if match:
                    cov_id = int(match.group(1))
                    if cov_id not in self.previous_coverage:
                        self.afl_coverage_map[cov_id] = (
                            self.afl_coverage_map.get(cov_id, 0) + 1
                        )
                    self.previous_coverage.add(cov_id)

    def _find_new_paths(self, queue_files: List[Path]) -> List[str]:
        """Findet neue Coverage-Pfade."""
        new_paths = []

        for qf in queue_files:
            name = qf.name
            if "+cov" in name:
                new_paths.append(str(qf))

        return new_paths

    def _parse_lcov(self, lcov_file: Path, report: CoverageReport) -> CoverageReport:
        """Parst LCOV Coverage-Report."""
        try:
            content = lcov_file.read_text()

            current_file: Optional[CoverageInfo] = None
            files_found = 0

            for line in content.split("\n"):
                line = line.strip()

                if line.startswith("SF:"):
                    # New file: SF:/path/to/file.py
                    if current_file:
                        report.files.append(current_file)
                        files_found += 1

                    file_path = line[3:]
                    current_file = CoverageInfo(file_path=file_path)

                elif line.startswith("DA:"):
                    # Line coverage: DA:42,1
                    if current_file:
                        current_file.total_lines += 1
                        parts = line[3:].split(",")
                        if len(parts) >= 2:
                            line_num = int(parts[0])
                            exec_count = int(parts[1])
                            if exec_count > 0:
                                current_file.covered_lines += 1
                            else:
                                current_file.uncovered_lines.append(line_num)

                elif line.startswith("FN:"):
                    # Function: FN:42,function_name
                    if current_file:
                        current_file.total_functions += 1

                elif line.startswith("FNDA:"):
                    # Function coverage: FNDA:1,function_name
                    if current_file:
                        parts = line[5:].split(",", 1)
                        if len(parts) >= 1 and int(parts[0]) > 0:
                            current_file.covered_functions += 1

                elif line == "end_of_record":
                    if current_file:
                        # Coverage-Prozente berechnen
                        if current_file.total_lines > 0:
                            current_file.line_coverage = (
                                current_file.covered_lines
                                / current_file.total_lines
                            ) * 100
                        if current_file.total_functions > 0:
                            current_file.function_coverage = (
                                current_file.covered_functions
                                / current_file.total_functions
                            ) * 100

                        report.files.append(current_file)
                        files_found += 1
                        current_file = None

            # Letzte Datei hinzufügen
            if current_file:
                report.files.append(current_file)
                files_found += 1

            # Gesamt-Statistiken
            report.total_files = files_found
            report.total_lines = sum(f.total_lines for f in report.files)
            report.covered_lines = sum(f.covered_lines for f in report.files)

            if report.total_lines > 0:
                report.total_coverage = (
                    report.covered_lines / report.total_lines
                ) * 100

        except Exception as e:
            logger.error(f"Failed to parse LCOV: {e}")

        return report

    def generate_lcov_report(
        self,
        binary_path: str,
        output_format: str = "html",
    ) -> Optional[str]:
        """
        Generiert LCOV Coverage-Report.

        Args:
            binary_path: Pfad zum instrumentierten Binary
            output_format: "html", "text", oder "json"

        Returns:
            Pfad zum generierten Report oder None
        """
        logger.info(f"Generating LCOV report ({output_format})...")

        # GCov ausführen
        try:
            result = subprocess.run(
                ["gcov", "-r", binary_path],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                logger.warning(f"gcov failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"gcov execution failed: {e}")
            return None

        # LCOV Report generieren
        lcov_cmd = [
            "lcov",
            "--capture",
            "--directory",
            str(self.repo_path),
            "--output-file",
            str(self.coverage_dir / "coverage.info"),
        ]

        try:
            subprocess.run(lcov_cmd, check=True, timeout=120)
        except Exception as e:
            logger.error(f"lcov capture failed: {e}")
            return None

        # HTML-Report generieren
        if output_format == "html":
            html_dir = self.coverage_dir / "html"
            html_dir.mkdir(parents=True, exist_ok=True)

            genhtml_cmd = [
                "genhtml",
                str(self.coverage_dir / "coverage.info"),
                "--output-directory",
                str(html_dir),
            ]

            try:
                subprocess.run(genhtml_cmd, check=True, timeout=120)
                logger.info(f"HTML report generated: {html_dir}")
                return str(html_dir)
            except Exception as e:
                logger.error(f"genhtml failed: {e}")
                return None

        return str(self.coverage_dir / "coverage.info")

    def find_interesting_inputs(
        self,
        queue_dir: Path,
        min_coverage_gain: float = 0.01,
    ) -> List[Path]:
        """
        Findet interessante Inputs mit Coverage-Gewinn.

        Args:
            queue_dir: AFL++ Queue-Verzeichnis
            min_coverage_gain: Minimaler Coverage-Gewinn

        Returns:
            Liste interessanter Input-Files
        """
        interesting = []

        for qf in queue_dir.glob("id:*"):
            # Coverage-Information aus Filename
            name = qf.name
            if "+cov" in name:
                interesting.append(qf)
                continue

            # Alternative: Cov-Metrik im Namen
            match = re.search(r"cov:(\d+)", name)
            if match:
                cov = int(match.group(1))
                if cov >= min_coverage_gain * 100:
                    interesting.append(qf)

        logger.info(f"Found {len(interesting)} interesting inputs")
        return interesting

    def export_coverage_summary(self) -> str:
        """
        Exportiert Coverage-Zusammenfassung als JSON.

        Returns:
            JSON-String mit Coverage-Summary
        """
        import json

        summary = {
            "coverage_map_size": len(self.afl_coverage_map),
            "unique_coverage_points": len(self.previous_coverage),
            "coverage_dir": str(self.coverage_dir),
        }

        return json.dumps(summary, indent=2)
