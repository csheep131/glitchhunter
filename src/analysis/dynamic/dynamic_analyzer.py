#!/usr/bin/env python3
"""
Dynamic Analysis Engine for GlitchHunter v2.0

Orchestriert die Dynamic Analysis:
- Fuzzing-Jobs verwalten
- Crash-Analyse integrieren
- Hybrid-Analyse (Static + Dynamic)
"""

import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .coverage import CoverageTracker
from .crash_analyzer import CrashAnalyzer, CrashInfo
from .fuzzer import AFLPlusPlusFuzzer, AtherisFuzzer, LibFuzzer
from .harness_generator import HarnessGenerator, FuzzTarget

logger = logging.getLogger(__name__)


@dataclass
class DynamicAnalysisResult:
    """Ergebnis der Dynamic Analysis."""

    total_execs: int = 0
    execs_per_sec: float = 0.0
    crashes_found: int = 0
    unique_crashes: int = 0
    coverage: float = 0.0
    runtime_seconds: float = 0.0

    crashes: List[CrashInfo] = field(default_factory=list)
    coverage_paths: List[str] = field(default_factory=list)
    interesting_inputs: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_execs": self.total_execs,
            "execs_per_sec": self.execs_per_sec,
            "crashes_found": self.crashes_found,
            "unique_crashes": self.unique_crashes,
            "coverage": self.coverage,
            "runtime_seconds": self.runtime_seconds,
            "crashes": [c.to_dict() for c in self.crashes],
            "coverage_paths": self.coverage_paths,
        }


class DynamicAnalyzer:
    """
    Dynamic Analysis Engine für GlitchHunter.

    Usage:
        analyzer = DynamicAnalyzer(repo_path="/path/to/repo")
        
        # Automatische Analyse
        result = analyzer.analyze(
            timeout=3600,
            use_coverage_guided=True,
        )
        
        # Oder manuell mit Targets
        targets = analyzer.identify_targets()
        result = analyzer.fuzz_targets(targets)
    """

    def __init__(
        self,
        repo_path: Path,
        output_dir: Optional[str] = None,
    ):
        """
        Initialisiert Dynamic Analyzer.

        Args:
            repo_path: Pfad zum Repository
            output_dir: Output-Verzeichnis für Fuzzing-Ergebnisse
        """
        self.repo_path = Path(repo_path)
        self.output_dir = Path(output_dir) if output_dir else (
            self.repo_path / ".glitchhunter" / "dynamic_analysis"
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Komponenten initialisieren
        self.harness_generator = HarnessGenerator(repo_path)
        self.coverage_tracker = CoverageTracker(repo_path)

        # Fuzzer (werden bei Bedarf erstellt)
        self.afl_fuzzer: Optional[AFLPlusPlusFuzzer] = None
        self.lib_fuzzer: Optional[LibFuzzer] = None
        self.atheris_fuzzer: Optional[AtherisFuzzer] = None

    def analyze(
        self,
        max_targets: int = 5,
        timeout_per_target: int = 600,
        use_coverage_guided: bool = True,
    ) -> DynamicAnalysisResult:
        """
        Führt automatische Dynamic Analysis durch.

        Args:
            max_targets: Maximale Anzahl zu fuzzender Targets
            timeout_per_target: Timeout pro Target (Sekunden)
            use_coverage_guided: Coverage-guided fuzzing aktivieren

        Returns:
            DynamicAnalysisResult
        """
        logger.info("Starting Dynamic Analysis...")

        result = DynamicAnalysisResult()

        # 1. Fuzzing-Targets identifizieren
        logger.info("Identifying fuzzing targets...")
        targets = self.harness_generator.identify_fuzz_targets(
            max_targets=max_targets,
        )

        if not targets:
            logger.warning("No fuzzing targets found")
            return result

        logger.info(f"Found {len(targets)} potential targets")

        # 2. Für jedes Target fuzzieren
        for i, target in enumerate(targets):
            logger.info(f"Fuzzing target {i+1}/{len(targets)}: {target.function_name}")

            try:
                target_result = self._fuzz_single_target(
                    target=target,
                    timeout=timeout_per_target,
                    use_coverage_guided=use_coverage_guided,
                )

                # Ergebnisse aggregieren
                result.total_execs += target_result.total_execs
                result.crashes_found += target_result.crashes_found
                result.unique_crashes += target_result.unique_crashes
                result.crashes.extend(target_result.crashes)

                if target_result.coverage > result.coverage:
                    result.coverage = target_result.coverage

            except Exception as e:
                logger.error(f"Failed to fuzz {target.function_name}: {e}")
                continue

        # 3. Laufzeit berechnen
        result.runtime_seconds = sum(c.runtime_seconds for c in [result])

        logger.info(
            f"Dynamic Analysis complete: "
            f"{result.total_execs} execs, "
            f"{result.crashes_found} crashes ({result.unique_crashes} unique)"
        )

        return result

    def _fuzz_single_target(
        self,
        target: FuzzTarget,
        timeout: int,
        use_coverage_guided: bool,
    ) -> DynamicAnalysisResult:
        """
        Fuzzing für ein einzelnes Target.

        Args:
            target: FuzzTarget-Objekt
            timeout: Timeout in Sekunden
            use_coverage_guided: Coverage-guided fuzzing

        Returns:
            DynamicAnalysisResult für dieses Target
        """
        result = DynamicAnalysisResult()

        # Harness generieren
        harness = self.harness_generator.generate_harness(
            target=target,
            output_dir=str(self.output_dir / "harnesses"),
        )

        if not harness:
            logger.warning(f"Failed to generate harness for {target.function_name}")
            return result

        logger.info(f"Generated harness: {harness.harness_file}")

        # Fuzzer auswählen basierend auf Sprache
        if target.language == "python":
            return self._fuzz_with_atheris(target, harness, timeout, result)
        else:
            return self._fuzz_with_afl(target, harness, timeout, use_coverage_guided, result)

    def _fuzz_with_afl(
        self,
        target: FuzzTarget,
        harness: Any,
        timeout: int,
        use_coverage_guided: bool,
        result: DynamicAnalysisResult,
    ) -> DynamicAnalysisResult:
        """Fuzzing mit AFL++."""
        # AFL++ Fuzzer initialisieren
        afl_output = self.output_dir / "afl" / target.function_name
        afl_output.mkdir(parents=True, exist_ok=True)

        self.afl_fuzzer = AFLPlusPlusFuzzer(output_dir=str(afl_output))

        # Fuzzing starten
        logger.info(f"Starting AFL++ fuzzing for {target.function_name}...")
        afl_result = self.afl_fuzzer.fuzz(
            target_binary=harness.harness_file,
            input_corpus=harness.corpus_seeds[0] if harness.corpus_seeds else None,
            timeout=timeout,
        )

        # Ergebnisse übernehmen
        result.total_execs = afl_result.total_execs
        result.execs_per_sec = afl_result.execs_per_sec
        result.crashes_found = afl_result.crashes_found
        result.runtime_seconds = afl_result.runtime_seconds

        # Coverage parsen
        if use_coverage_guided:
            coverage_report = self.coverage_tracker.parse_afl_coverage(afl_output)
            result.coverage = coverage_report.total_coverage
            result.coverage_paths = coverage_report.new_coverage_paths

        # Crashes analysieren
        if afl_result.crashes_found > 0:
            crash_analyzer = CrashAnalyzer(
                target_binary=harness.harness_file,
            )
            crashes = crash_analyzer.analyze_crash_dir(
                str(afl_output / "crashes"),
            )
            result.crashes = crashes
            result.unique_crashes = len(crashes)

        return result

    def _fuzz_with_atheris(
        self,
        target: FuzzTarget,
        harness: Any,
        timeout: int,
        result: DynamicAnalysisResult,
    ) -> DynamicAnalysisResult:
        """Fuzzing mit Atheris (Python)."""
        # Atheris Fuzzer initialisieren
        atheris_output = self.output_dir / "atheris" / target.function_name
        atheris_output.mkdir(parents=True, exist_ok=True)

        self.atheris_fuzzer = AtherisFuzzer(output_dir=str(atheris_output))

        # Fuzzing starten
        logger.info(f"Starting Atheris fuzzing for {target.function_name}...")
        atheris_result = self.atheris_fuzzer.fuzz(
            harness_file=harness.harness_file,
            timeout=timeout,
        )

        # Ergebnisse übernehmen
        result.total_execs = atheris_result.total_execs
        result.execs_per_sec = atheris_result.execs_per_sec
        result.crashes_found = atheris_result.crashes_found
        result.runtime_seconds = atheris_result.runtime_seconds

        # Crashes analysieren
        if atheris_result.crashes_found > 0:
            crash_analyzer = CrashAnalyzer(
                target_binary="python",  # Python Interpreter
            )
            crashes = crash_analyzer.analyze_crash_dir(
                str(atheris_output / "crashes"),
            )
            result.crashes = crashes
            result.unique_crashes = len(crashes)

        return result

    def identify_targets(self) -> List[FuzzTarget]:
        """Identifiziert Fuzzing-Targets."""
        return self.harness_generator.identify_fuzz_targets()

    def generate_harness(self, target: FuzzTarget) -> Optional[Any]:
        """Generiert Harness für ein Target."""
        return self.harness_generator.generate_harness(target)

    def analyze_crashes(self, crash_dir: str) -> List[CrashInfo]:
        """Analysiert Crashes aus einem Verzeichnis."""
        # Target-Binary erraten oder aus Config
        target_binary = self._find_fuzz_binary()
        analyzer = CrashAnalyzer(target_binary=str(target_binary))
        return analyzer.analyze_crash_dir(crash_dir)

    def _find_fuzz_binary(self) -> Optional[Path]:
        """Sucht nach Fuzzing-Binary im Output-Verzeichnis."""
        for binary in self.output_dir.rglob("*"):
            if binary.is_file() and not binary.suffix:
                # Executable ohne Extension
                return binary
        return None

    def export_report(self, result: DynamicAnalysisResult, output_file: str) -> str:
        """
        Exportiert Dynamic Analysis Report.

        Args:
            result: Analyse-Ergebnis
            output_file: Pfad zur Report-Datei

        Returns:
            Report-String
        """
        report_lines = [
            "# 🔬 GlitchHunter Dynamic Analysis Report",
            "",
            "## Summary",
            "",
            f"- **Total Executions:** {result.total_execs:,}",
            f"- **Executions/sec:** {result.execs_per_sec:,.0f}",
            f"- **Crashes Found:** {result.crashes_found}",
            f"- **Unique Crashes:** {result.unique_crashes}",
            f"- **Coverage:** {result.coverage:.1f}%",
            f"- **Runtime:** {result.runtime_seconds:.1f}s",
            "",
        ]

        # Crashes nach Severity
        if result.crashes:
            report_lines.extend([
                "## Crashes by Severity",
                "",
            ])

            by_severity: Dict[str, int] = {}
            for crash in result.crashes:
                by_severity[crash.severity] = by_severity.get(crash.severity, 0) + 1

            for severity in ["critical", "high", "medium", "low"]:
                count = by_severity.get(severity, 0)
                if count > 0:
                    emoji = {"critical": "🚨", "high": "⚠️", "medium": "⚡", "low": "ℹ️"}.get(
                        severity, ""
                    )
                    report_lines.append(f"- {emoji} **{severity.upper()}:** {count}")

            report_lines.append("")

        # Crash-Details
        if result.crashes:
            report_lines.extend([
                "## Crash Details",
                "",
            ])

            for crash in result.crashes[:10]:  # Erste 10
                report_lines.extend([
                    f"### {crash.crash_type}",
                    "",
                    f"- **Severity:** {crash.severity}",
                    f"- **Target:** {crash.target_function or 'unknown'}",
                    f"- **Reproducible:** {'Yes' if crash.reproducible else 'No'}",
                    "",
                ])

        report = "\n".join(report_lines)

        Path(output_file).write_text(report)
        logger.info(f"Report saved: {output_file}")

        return report
