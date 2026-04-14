"""
Complexity analyzer for GlitchHunter.

Calculates code complexity metrics using Radon and Lizard,
identifying hotspots and complex code regions.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class FunctionMetrics:
    """
    Metrics for a single function.

    Attributes:
        name: Function name
        line_start: Starting line number
        line_end: Ending line number
        cyclomatic_complexity: Cyclomatic complexity
        cognitive_complexity: Cognitive complexity
        parameters: Number of parameters
        lines: Number of lines
    """

    name: str
    line_start: int
    line_end: int
    cyclomatic_complexity: int = 0
    cognitive_complexity: int = 0
    parameters: int = 0
    lines: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "cyclomatic_complexity": self.cyclomatic_complexity,
            "cognitive_complexity": self.cognitive_complexity,
            "parameters": self.parameters,
            "lines": self.lines,
        }


@dataclass
class ComplexityMetrics:
    """
    Complexity metrics for a code unit.

    Attributes:
        file_path: File path
        name: Code unit name
        kind: Kind (function, class, module)
        cyclomatic: Cyclomatic complexity
        cognitive: Cognitive complexity
        halstead_volume: Halstead volume
        halstead_difficulty: Halstead difficulty
        lines_of_code: Lines of code
        comment_lines: Comment lines
        nesting_depth: Maximum nesting depth
        parameter_count: Number of parameters
        maintainability_index: Maintainability index
        functions: List of function metrics
    """

    file_path: str
    name: str
    kind: str
    cyclomatic: int = 0
    cognitive: int = 0
    halstead_volume: float = 0.0
    halstead_difficulty: float = 0.0
    lines_of_code: int = 0
    comment_lines: int = 0
    nesting_depth: int = 0
    parameter_count: int = 0
    maintainability_index: float = 0.0
    functions: List[FunctionMetrics] = field(default_factory=list)

    @property
    def is_complex(self) -> bool:
        """Check if code unit is considered complex."""
        return (
            self.cyclomatic > 10
            or self.cognitive > 25
            or self.nesting_depth > 4
            or self.maintainability_index < 50
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "name": self.name,
            "kind": self.kind,
            "cyclomatic_complexity": self.cyclomatic,
            "cognitive_complexity": self.cognitive,
            "halstead_volume": self.halstead_volume,
            "halstead_difficulty": self.halstead_difficulty,
            "lines_of_code": self.lines_of_code,
            "comment_lines": self.comment_lines,
            "nesting_depth": self.nesting_depth,
            "parameter_count": self.parameter_count,
            "maintainability_index": self.maintainability_index,
            "is_complex": self.is_complex,
            "functions": [f.to_dict() for f in self.functions],
        }


@dataclass
class Hotspot:
    """
    Represents a complexity hotspot.

    Attributes:
        file_path: File path
        function_name: Function name (if applicable)
        complexity_score: Combined complexity score
        metrics: Complexity metrics
        priority: Priority level (P1, P2, P3)
    """

    file_path: str
    function_name: Optional[str]
    complexity_score: float
    metrics: ComplexityMetrics
    priority: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "function_name": self.function_name,
            "complexity_score": self.complexity_score,
            "metrics": self.metrics.to_dict(),
            "priority": self.priority,
        }


@dataclass
class ComplexFunction:
    """Represents a complex function."""

    file_path: str
    name: str
    cyclomatic_complexity: int
    cognitive_complexity: int
    line_start: int
    line_end: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "name": self.name,
            "cyclomatic_complexity": self.cyclomatic_complexity,
            "cognitive_complexity": self.cognitive_complexity,
            "line_start": self.line_start,
            "line_end": self.line_end,
        }


@dataclass
class ComplexFile:
    """Represents a complex file."""

    file_path: str
    total_complexity: int
    avg_complexity: float
    max_complexity: int
    function_count: int
    lines_of_code: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "total_complexity": self.total_complexity,
            "avg_complexity": self.avg_complexity,
            "max_complexity": self.max_complexity,
            "function_count": self.function_count,
            "lines_of_code": self.lines_of_code,
        }


class ComplexityAnalyzer:
    """
    Analyzes code complexity using Radon and Lizard.

    Provides cyclomatic complexity, cognitive complexity,
    Halstead metrics, and maintainability index.

    Example:
        >>> analyzer = ComplexityAnalyzer()
        >>> hotspots = analyzer.get_hotspots(Path("/path/to/repo"))
        >>> complex_funcs = analyzer.get_complex_functions(threshold=10)
    """

    def __init__(
        self,
        max_cyclomatic: int = 15,
        max_cognitive: int = 25,
        max_nesting: int = 5,
        tool: str = "radon",
    ) -> None:
        """
        Initialize complexity analyzer.

        Args:
            max_cyclomatic: Max acceptable cyclomatic complexity
            max_cognitive: Max acceptable cognitive complexity
            max_nesting: Max acceptable nesting depth
            tool: Tool to use ("radon" or "lizard")
        """
        self.max_cyclomatic = max_cyclomatic
        self.max_cognitive = max_cognitive
        self.max_nesting = max_nesting
        self.tool = tool

        self._radon_available = False
        self._lizard_available = False

        self._check_availability()

        logger.debug(f"ComplexityAnalyzer initialized (tool={tool})")

    def _check_availability(self) -> None:
        """Check which tools are available."""
        try:
            import radon  # noqa: F401

            self._radon_available = True
            logger.debug("Radon is available")
        except ImportError:
            logger.debug("Radon not available")

        try:
            import lizard  # noqa: F401

            self._lizard_available = True
            logger.debug("Lizard is available")
        except ImportError:
            logger.debug("Lizard not available")

    def analyze_file(self, file_path: Path) -> ComplexityMetrics:
        """
        Analyze complexity of a file.

        Args:
            file_path: Path to the file

        Returns:
            ComplexityMetrics for the file
        """
        if not file_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return ComplexityMetrics(
                file_path=str(file_path),
                name=file_path.name,
                kind="module",
            )

        if self.tool == "radon" and self._radon_available:
            return self._analyze_with_radon(file_path)
        elif self._lizard_available:
            return self._analyze_with_lizard(file_path)
        else:
            return self._analyze_simple(file_path)

    def analyze_repo(self, repo_path: Path) -> Dict[str, ComplexityMetrics]:
        """
        Analyze complexity of all files in a repository.

        Args:
            repo_path: Path to the repository

        Returns:
            Dictionary mapping file paths to ComplexityMetrics
        """
        metrics: Dict[str, ComplexityMetrics] = {}

        extensions = [".py", ".js", ".ts", ".rs", ".go", ".java"]

        for ext in extensions:
            for file_path in repo_path.rglob(f"*{ext}"):
                if self._should_ignore(file_path):
                    continue

                file_metrics = self.analyze_file(file_path)
                metrics[str(file_path)] = file_metrics

        return metrics

    def get_complex_functions(
        self,
        repo_path: Path,
        threshold: int = 10,
    ) -> List[ComplexFunction]:
        """
        Get functions exceeding complexity threshold.

        Args:
            repo_path: Path to the repository
            threshold: Cyclomatic complexity threshold

        Returns:
            List of ComplexFunction objects
        """
        complex_funcs = []
        all_metrics = self.analyze_repo(repo_path)

        for file_path, metrics in all_metrics.items():
            for func in metrics.functions:
                if func.cyclomatic_complexity >= threshold:
                    complex_funcs.append(ComplexFunction(
                        file_path=file_path,
                        name=func.name,
                        cyclomatic_complexity=func.cyclomatic_complexity,
                        cognitive_complexity=func.cognitive_complexity,
                        line_start=func.line_start,
                        line_end=func.line_end,
                    ))

        # Sort by complexity descending
        complex_funcs.sort(
            key=lambda f: f.cyclomatic_complexity,
            reverse=True,
        )

        return complex_funcs

    def get_complex_files(
        self,
        repo_path: Path,
        threshold: int = 50,
    ) -> List[ComplexFile]:
        """
        Get files exceeding complexity threshold.

        Args:
            repo_path: Path to the repository
            threshold: Total complexity threshold

        Returns:
            List of ComplexFile objects
        """
        complex_files = []
        all_metrics = self.analyze_repo(repo_path)

        # Group by file
        file_data: Dict[str, List[ComplexityMetrics]] = {}
        for file_path, metrics in all_metrics.items():
            dir_path = str(Path(file_path).parent)
            if dir_path not in file_data:
                file_data[dir_path] = []
            file_data[dir_path].append(metrics)

        for dir_path, metrics_list in file_data.items():
            total_complexity = sum(m.cyclomatic for m in metrics_list)
            if total_complexity >= threshold:
                complex_files.append(ComplexFile(
                    file_path=dir_path,
                    total_complexity=total_complexity,
                    avg_complexity=total_complexity / len(metrics_list),
                    max_complexity=max(m.cyclomatic for m in metrics_list),
                    function_count=len(metrics_list),
                    lines_of_code=sum(m.lines_of_code for m in metrics_list),
                ))

        # Sort by total complexity descending
        complex_files.sort(
            key=lambda f: f.total_complexity,
            reverse=True,
        )

        return complex_files

    def get_hotspots(
        self,
        repo_path: Path,
        max_results: int = 20,
        languages: Optional[List[str]] = None,
    ) -> List[Hotspot]:
        """
        Get complexity hotspots in a repository.

        Args:
            repo_path: Path to repository
            max_results: Maximum number of hotspots
            languages: Languages to analyze

        Returns:
            List of Hotspot objects sorted by complexity
        """
        all_metrics: List[ComplexityMetrics] = []
        extensions = self._get_extensions(languages)

        # Collect metrics for all files
        for ext in extensions:
            for file_path in repo_path.rglob(f"*{ext}"):
                if self._should_ignore(file_path):
                    continue

                metrics = self.analyze_file(file_path)
                all_metrics.append(metrics)

                # Add function-level metrics
                for func in metrics.functions:
                    func_metrics = ComplexityMetrics(
                        file_path=str(file_path),
                        name=func.name,
                        kind="function",
                        cyclomatic=func.cyclomatic_complexity,
                        cognitive=func.cognitive_complexity,
                        lines_of_code=func.lines,
                        parameter_count=func.parameters,
                    )
                    all_metrics.append(func_metrics)

        # Filter complex units
        complex_units = [m for m in all_metrics if m.is_complex]

        # Calculate complexity score and sort
        hotspots = []
        for metrics in complex_units:
            score = self._calculate_complexity_score(metrics)
            priority = self._determine_priority(score, metrics)

            hotspot = Hotspot(
                file_path=metrics.file_path,
                function_name=metrics.name if metrics.kind == "function" else None,
                complexity_score=score,
                metrics=metrics,
                priority=priority,
            )
            hotspots.append(hotspot)

        # Sort by score descending
        hotspots.sort(key=lambda h: h.complexity_score, reverse=True)

        logger.info(f"Found {len(hotspots)} complexity hotspots")

        return hotspots[:max_results]

    def _analyze_with_radon(self, file_path: Path) -> ComplexityMetrics:
        """Analyze file using Radon."""
        try:
            from radon.complexity import cc_visit
            from radon.metrics import h_visit, mi_visit
            from radon.raw import analyze

            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()

            # Cyclomatic complexity
            cc_results = cc_visit(source)
            functions = []

            for cc_result in cc_results:
                func = FunctionMetrics(
                    name=cc_result.name,
                    line_start=cc_result.startline,
                    line_end=cc_result.endline,
                    cyclomatic_complexity=cc_result.complexity,
                    lines=cc_result.endline - cc_result.startline + 1,
                )
                functions.append(func)

            # Halstead metrics
            halstead = h_visit(source)
            halstead_volume = halstead.functions[0].volume if halstead.functions else 0.0
            halstead_difficulty = halstead.functions[0].difficulty if halstead.functions else 0.0

            # Maintainability index
            mi = mi_visit(source, multi=True)
            avg_mi = sum(mi.values()) / len(mi) if mi else 0.0

            # Raw metrics
            raw = analyze(source)

            return ComplexityMetrics(
                file_path=str(file_path),
                name=file_path.name,
                kind="module",
                cyclomatic=max(f.cyclomatic_complexity for f in functions) if functions else 0,
                halstead_volume=halstead_volume,
                halstead_difficulty=halstead_difficulty,
                lines_of_code=raw.loc,
                comment_lines=raw.comments,
                maintainability_index=avg_mi,
                functions=functions,
            )

        except Exception as e:
            logger.error(f"Radon analysis failed for {file_path}: {e}")
            return self._analyze_simple(file_path)

    def _analyze_with_lizard(self, file_path: Path) -> ComplexityMetrics:
        """Analyze file using Lizard."""
        try:
            import lizard

            result = lizard.analyze_file(str(file_path))
            functions = []

            for func in result.function_list:
                func_metrics = FunctionMetrics(
                    name=func.name,
                    line_start=func.start_line,
                    line_end=func.end_line,
                    cyclomatic_complexity=func.cyclomatic_complexity,
                    parameters=len(func.parameters) if func.parameters else 0,
                    lines=func.end_line - func.start_line + 1,
                )
                functions.append(func_metrics)

            return ComplexityMetrics(
                file_path=str(file_path),
                name=file_path.name,
                kind="module",
                cyclomatic=max(f.cyclomatic_complexity for f in functions) if functions else 0,
                lines_of_code=result.total_lines,
                functions=functions,
            )

        except Exception as e:
            logger.error(f"Lizard analysis failed for {file_path}: {e}")
            return self._analyze_simple(file_path)

    def _analyze_simple(self, file_path: Path) -> ComplexityMetrics:
        """Simple complexity analysis without external tools."""
        import re
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            loc = len(lines)
            comment_lines = sum(1 for l in lines if l.strip().startswith("#"))

            # Simple cyclomatic complexity estimation
            cyclomatic = 1
            keywords = ["if", "elif", "for", "while", "and", "or", "except", "with"]
            for line in lines:
                for keyword in keywords:
                    if re.search(rf"\b{keyword}\b", line):
                        cyclomatic += 1

            # Count functions
            functions = []
            import re
            for line_num, line in enumerate(lines, 1):
                func_match = re.search(r"def\s+(\w+)\s*\(", line)
                if func_match:
                    functions.append(FunctionMetrics(
                        name=func_match.group(1),
                        line_start=line_num,
                        line_end=min(line_num + 30, len(lines)),
                        cyclomatic_complexity=1,
                        lines=30,
                    ))

            # Maintainability index (simplified)
            mi = 171 - 5.2 * (loc / 100) - 0.23 * cyclomatic - 16.2

            return ComplexityMetrics(
                file_path=str(file_path),
                name=file_path.name,
                kind="module",
                cyclomatic=cyclomatic,
                lines_of_code=loc,
                comment_lines=comment_lines,
                maintainability_index=max(0, min(100, mi)),
                functions=functions,
            )

        except Exception as e:
            logger.error(f"Simple analysis failed for {file_path}: {e}")
            return ComplexityMetrics(
                file_path=str(file_path),
                name=file_path.name,
                kind="module",
            )

    def _calculate_complexity_score(self, metrics: ComplexityMetrics) -> float:
        """Calculate overall complexity score."""
        score = 0.0

        # Cyclomatic complexity (weight: 1.0)
        score += metrics.cyclomatic * 1.0

        # Cognitive complexity (weight: 0.8)
        score += metrics.cognitive * 0.8

        # Nesting depth (weight: 2.0)
        score += metrics.nesting_depth * 2.0

        # Halstead difficulty (weight: 0.5)
        score += metrics.halstead_difficulty * 0.5

        # Low maintainability penalty
        if metrics.maintainability_index < 50:
            score += (50 - metrics.maintainability_index) * 0.5

        return score

    def _determine_priority(self, score: float, metrics: ComplexityMetrics) -> str:
        """Determine priority level for a hotspot."""
        if score > 50 or metrics.cyclomatic > 20:
            return "P1"  # Critical
        elif score > 25 or metrics.cyclomatic > 15:
            return "P2"  # High
        else:
            return "P3"  # Medium

    def _get_extensions(self, languages: Optional[List[str]]) -> List[str]:
        """Get file extensions for languages."""
        ext_map = {
            "python": [".py"],
            "javascript": [".js", ".jsx"],
            "typescript": [".ts", ".tsx"],
            "rust": [".rs"],
            "go": [".go"],
            "java": [".java"],
        }

        if languages is None:
            return [".py", ".js", ".ts", ".rs", ".go", ".java"]

        extensions = []
        for lang in languages:
            extensions.extend(ext_map.get(lang, []))

        return extensions

    def _should_ignore(self, file_path: Path) -> bool:
        """Check if file should be ignored."""
        path_str = str(file_path)
        ignore_patterns = [
            "/.git/", "/node_modules/", "/__pycache__/",
            "/.venv/", "/venv/", "/dist/", "/build/",
        ]
        return any(p in path_str for p in ignore_patterns)

    def get_summary(self, repo_path: Path) -> Dict[str, Any]:
        """
        Get complexity summary for a repository.

        Args:
            repo_path: Path to repository

        Returns:
            Dictionary with summary statistics
        """
        hotspots = self.get_hotspots(repo_path, max_results=100)

        if not hotspots:
            return {
                "total_files": 0,
                "total_functions": 0,
                "avg_complexity": 0.0,
                "max_complexity": 0,
                "hotspot_count": 0,
            }

        complexities = [h.metrics.cyclomatic for h in hotspots]

        return {
            "total_files": len(set(h.file_path for h in hotspots)),
            "total_functions": len(hotspots),
            "avg_complexity": sum(complexities) / len(complexities),
            "max_complexity": max(complexities),
            "hotspot_count": len([h for h in hotspots if h.priority == "P1"]),
            "by_priority": {
                "P1": len([h for h in hotspots if h.priority == "P1"]),
                "P2": len([h for h in hotspots if h.priority == "P2"]),
                "P3": len([h for h in hotspots if h.priority == "P3"]),
            },
        }
