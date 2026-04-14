"""
Pre-filter pipeline for GlitchHunter.

Coordinates all pre-filter steps including Semgrep, AST analysis,
complexity metrics, and Git churn analysis.
"""

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from prefilter.ast_analyzer import ASTAnalyzer, ASTSymbol
from prefilter.complexity import ComplexityAnalyzer, ComplexityMetrics, Hotspot as ComplexityHotspot
from prefilter.git_churn import GitChurnAnalyzer, Hotspot as GitHotspot, ChurnAnalysis
from prefilter.semgrep_runner import SemgrepResult, SemgrepRunner, SemgrepFinding

logger = logging.getLogger(__name__)


@dataclass
class Candidate:
    """
    Represents a prioritized candidate for analysis.

    Attributes:
        file_path: File path
        total_score: Combined priority score
        factors: Score breakdown by category
    """

    file_path: str
    total_score: float
    factors: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "total_score": self.total_score,
            "factors": self.factors,
        }


@dataclass
class RepoManifest:
    """Repository manifest with metadata."""

    repo_path: str
    languages: List[str] = field(default_factory=list)
    file_count: int = 0
    total_lines: int = 0
    entry_points: List[str] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class SemgrepResult:
    """Semgrep scan result."""

    findings: List[SemgrepFinding] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class ASTResult:
    """AST analysis result."""

    symbols: List[ASTSymbol] = field(default_factory=list)
    patterns: List[Any] = field(default_factory=list)


@dataclass
class ComplexityResult:
    """Complexity analysis result."""

    file_metrics: Dict[str, ComplexityMetrics] = field(default_factory=dict)
    hotspots: List[ComplexityHotspot] = field(default_factory=list)


@dataclass
class PreFilterResult:
    """
    Result of the pre-filter pipeline.

    Attributes:
        repo_manifest: Repository manifest
        symbol_graph: Symbol graph from repo mapper
        semgrep_result: Semgrep scan results
        complexity_result: Complexity analysis results
        churn_analysis: Git churn analysis results
        candidates: Prioritized candidates
        filtered_percentage: Percentage of code filtered out
    """

    repo_manifest: Optional[RepoManifest] = None
    symbol_graph: Optional[Any] = None
    semgrep_result: Optional[SemgrepResult] = None
    complexity_result: Optional[ComplexityResult] = None
    churn_analysis: Optional[ChurnAnalysis] = None
    candidates: List[Candidate] = field(default_factory=list)
    filtered_percentage: float = 0.0

    @property
    def total_security_issues(self) -> int:
        """Get total security findings."""
        if self.semgrep_result:
            return len(self.semgrep_result.findings)
        return 0

    @property
    def has_critical_issues(self) -> bool:
        """Check if any critical issues exist."""
        return False


class PreFilterPipeline:
    """
    Pre-filter pipeline for code analysis.

    Coordinates multiple analysis passes and combines results
    to prioritize files for deep analysis.

    Attributes:
        repo_path: Path to the repository

    Example:
        >>> pipeline = PreFilterPipeline(Path("/path/to/repo"))
        >>> result = pipeline.run()
        >>> candidates = result.candidates[:10]
    """

    def __init__(
        self,
        repo_path: Path,
        rules_path: Optional[Path] = None,
        max_complexity: int = 15,
        git_since_days: int = 90,
    ) -> None:
        """
        Initialize pre-filter pipeline.

        Args:
            repo_path: Path to the repository
            rules_path: Path to custom Semgrep rules
            max_complexity: Max acceptable complexity threshold
            git_since_days: Days to analyze for Git churn
        """
        self.repo_path = repo_path
        self.semgrep_runner = SemgrepRunner(rules_path=rules_path)
        self.ast_analyzer = ASTAnalyzer()
        self.complexity_analyzer = ComplexityAnalyzer(max_cyclomatic=max_complexity)
        self.git_analyzer = GitChurnAnalyzer(repo_path=repo_path, since_days=git_since_days)

        logger.debug(f"PreFilterPipeline initialized for {repo_path}")

    def run(self) -> PreFilterResult:
        """
        Run the complete pre-filter pipeline.

        Returns:
            PreFilterResult with all analysis results
        """
        logger.info(f"Running pre-filter pipeline on {self.repo_path}")
        start_time = time.time()

        result = PreFilterResult()

        # Run all analysis steps
        result.semgrep_result = self.run_semgrep()
        ast_result = self.run_ast_analysis()
        result.complexity_result = self.run_complexity_analysis()
        result.churn_analysis = self.run_git_churn_analysis()

        # Combine results
        result = self.combine_results(result, ast_result)

        # Calculate filtered percentage
        result.filtered_percentage = self._calculate_filtered_percentage(result)

        duration = time.time() - start_time
        logger.info(
            f"Pre-filter pipeline complete in {duration:.2f}s: "
            f"{len(result.candidates)} candidates, "
            f"{result.filtered_percentage:.1f}% filtered"
        )

        return result

    def run_semgrep(self) -> SemgrepResult:
        """
        Run Semgrep security and correctness scans.

        Returns:
            SemgrepResult with combined findings
        """
        logger.info("Running Semgrep scans")

        try:
            # Run security scan
            security_result = self.semgrep_runner.run_security_scan(self.repo_path)

            # Run correctness scan
            correctness_result = self.semgrep_runner.run_correctness_scan(self.repo_path)

            # Combine findings
            all_findings = security_result.findings + correctness_result.findings
            all_errors = security_result.errors + correctness_result.errors

            return SemgrepResult(
                findings=all_findings,
                errors=all_errors,
            )

        except Exception as e:
            logger.error(f"Semgrep scan failed: {e}")
            return SemgrepResult(errors=[str(e)])

    def run_ast_analysis(self) -> ASTResult:
        """
        Run AST-based analysis.

        Returns:
            ASTResult with symbols and patterns
        """
        logger.info("Running AST analysis")

        try:
            symbols = []
            patterns = []

            # Parse Python files
            for file_path in self.repo_path.rglob("*.py"):
                if self._should_ignore(file_path):
                    continue

                file_symbols = self.ast_analyzer.parse_file(file_path)
                symbols.extend(file_symbols)

                file_patterns = self.ast_analyzer.find_patterns(file_path)
                patterns.extend(file_patterns)

            # Parse JavaScript/TypeScript files
            for ext in ["*.js", "*.ts", "*.jsx", "*.tsx"]:
                for file_path in self.repo_path.rglob(ext):
                    if self._should_ignore(file_path):
                        continue

                    file_symbols = self.ast_analyzer.parse_file(file_path)
                    symbols.extend(file_symbols)

            return ASTResult(symbols=symbols, patterns=patterns)

        except Exception as e:
            logger.error(f"AST analysis failed: {e}")
            return ASTResult()

    def run_complexity_analysis(self) -> ComplexityResult:
        """
        Run complexity analysis.

        Returns:
            ComplexityResult with metrics and hotspots
        """
        logger.info("Running complexity analysis")

        try:
            hotspots = self.complexity_analyzer.get_hotspots(
                self.repo_path, max_results=50
            )

            file_metrics = {}
            for hotspot in hotspots:
                file_metrics[hotspot.file_path] = hotspot.metrics

            return ComplexityResult(
                file_metrics=file_metrics,
                hotspots=hotspots,
            )

        except Exception as e:
            logger.error(f"Complexity analysis failed: {e}")
            return ComplexityResult()

    def run_git_churn_analysis(self) -> ChurnAnalysis:
        """
        Run Git churn analysis.

        Returns:
            ChurnAnalysis with churn metrics and hotspots
        """
        logger.info("Running Git churn analysis")

        try:
            return self.git_analyzer.analyze_repo(since="3 months")

        except Exception as e:
            logger.error(f"Git churn analysis failed: {e}")
            return ChurnAnalysis()

    def combine_results(
        self,
        prefilter_result: PreFilterResult,
        ast_result: ASTResult,
    ) -> PreFilterResult:
        """
        Combine all analysis results into prioritized candidates.

        Args:
            prefilter_result: PreFilterResult to update
            ast_result: AST analysis result

        Returns:
            Updated PreFilterResult with candidates
        """
        logger.info("Combining analysis results")

        file_scores: Dict[str, Dict[str, Any]] = {}

        # Collect all files from all sources
        all_files = set()

        # Files from Semgrep findings
        if prefilter_result.semgrep_result:
            for finding in prefilter_result.semgrep_result.findings:
                all_files.add(finding.file_path)

        # Files from complexity hotspots
        if prefilter_result.complexity_result:
            for hotspot in prefilter_result.complexity_result.hotspots:
                all_files.add(hotspot.file_path)

        # Files from Git hotspots
        if prefilter_result.churn_analysis:
            for hotspot in prefilter_result.churn_analysis.hotspots:
                all_files.add(hotspot.file_path)

        # Calculate scores for each file
        for file_path in all_files:
            score = 0.0
            factors = {}

            # Semgrep findings weight
            if prefilter_result.semgrep_result:
                semgrep_count = sum(
                    1 for f in prefilter_result.semgrep_result.findings
                    if f.file_path == file_path
                )
                if semgrep_count > 0:
                    factors["semgrep"] = semgrep_count
                    score += semgrep_count * 10.0

            # Complexity weight
            if prefilter_result.complexity_result:
                complexity_hotspot = next(
                    (h for h in prefilter_result.complexity_result.hotspots
                     if h.file_path == file_path),
                    None,
                )
                if complexity_hotspot:
                    factors["complexity"] = complexity_hotspot.metrics.cyclomatic
                    score += complexity_hotspot.complexity_score

            # Git churn weight
            if prefilter_result.churn_analysis:
                git_hotspot = next(
                    (h for h in prefilter_result.churn_analysis.hotspots
                     if h.file_path == file_path),
                    None,
                )
                if git_hotspot:
                    factors["churn"] = git_hotspot.commit_count
                    score += git_hotspot.hotspot_score

            if score > 0:
                file_scores[file_path] = {
                    "file_path": file_path,
                    "total_score": score,
                    "factors": factors,
                }

        # Sort by score and create candidates
        sorted_files = sorted(
            file_scores.values(),
            key=lambda x: x["total_score"],
            reverse=True,
        )

        prefilter_result.candidates = [
            Candidate(
                file_path=f["file_path"],
                total_score=f["total_score"],
                factors=f["factors"],
            )
            for f in sorted_files
        ]

        return prefilter_result

    def get_top_candidates(self, top_n: int = 50) -> List[Candidate]:
        """
        Get top prioritized candidates.

        Args:
            top_n: Number of candidates to return

        Returns:
            List of top candidates
        """
        # Run pipeline if not already run
        result = self.run()
        return result.candidates[:top_n]

    def _should_ignore(self, file_path: Path) -> bool:
        """Check if file should be ignored."""
        path_str = str(file_path)
        ignore_patterns = [
            "/.git/", "/node_modules/", "/__pycache__/",
            "/.venv/", "/venv/", "/dist/", "/build/",
        ]
        return any(p in path_str for p in ignore_patterns)

    def _calculate_filtered_percentage(self, result: PreFilterResult) -> float:
        """Calculate percentage of code filtered out."""
        try:
            total_files = sum(
                1 for _ in self.repo_path.rglob("*.py")
                if not self._should_ignore(_)
            )
            if total_files == 0:
                return 0.0

            candidate_files = len(set(c.file_path for c in result.candidates))
            filtered = total_files - candidate_files

            return (filtered / total_files) * 100.0

        except Exception:
            return 0.0
