"""
Git churn analyzer for GlitchHunter.

Analyzes Git history to identify frequently changed files (churn),
hotspots, and blame information. Provides comprehensive Git history
analysis for bug localization.
"""

import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class GitCommit:
    """
    Represents a Git commit.

    Attributes:
        hash: Commit hash
        author: Author name
        date: Commit date
        message: Commit message
        changed_files: List of changed file paths
    """

    hash: str
    author: str
    date: datetime
    message: str
    changed_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hash": self.hash,
            "author": self.author,
            "date": self.date.isoformat(),
            "message": self.message,
            "changed_files": self.changed_files,
        }


@dataclass
class BlameLine:
    """
    Represents a line from git blame.

    Attributes:
        line_number: Line number (1-based)
        content: Line content
        commit_hash: Commit hash that last changed this line
        author: Author name
        date: Commit date
    """

    line_number: int
    content: str
    commit_hash: str
    author: str
    date: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "line_number": self.line_number,
            "content": self.content,
            "commit_hash": self.commit_hash,
            "author": self.author,
            "date": self.date.isoformat(),
        }


@dataclass
class Hotspot:
    """
    Represents a Git history hotspot.

    Attributes:
        file_path: File path
        churn_score: Churn score
        complexity_score: Complexity score
        hotspot_score: Combined hotspot score
        commit_count: Number of commits
        recent_commits: Recent commits affecting this file
    """

    file_path: str
    churn_score: float
    complexity_score: float
    hotspot_score: float
    commit_count: int
    recent_commits: List[GitCommit] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "churn_score": self.churn_score,
            "complexity_score": self.complexity_score,
            "hotspot_score": self.hotspot_score,
            "commit_count": self.commit_count,
            "recent_commits": [c.to_dict() for c in self.recent_commits],
        }


@dataclass
class ChurnAnalysis:
    """
    Complete churn analysis result.

    Attributes:
        file_scores: Map of file paths to churn scores
        commits: List of commits in the analysis period
        hotspots: List of identified hotspots
        analyzed_at: Analysis timestamp
    """

    file_scores: Dict[str, float] = field(default_factory=dict)
    commits: List[GitCommit] = field(default_factory=list)
    hotspots: List[Hotspot] = field(default_factory=list)
    analyzed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_scores": self.file_scores,
            "commits": [c.to_dict() for c in self.commits],
            "hotspots": [h.to_dict() for h in self.hotspots],
            "analyzed_at": self.analyzed_at.isoformat(),
        }


class GitChurnAnalyzer:
    """
    Analyzes Git repository history for churn and hotspots.

    Uses git log, git blame, and git diff to extract history
    metrics and identify frequently changed code regions.

    Attributes:
        repo_path: Path to the Git repository
        since_days: Number of days to analyze

    Example:
        >>> analyzer = GitChurnAnalyzer(Path("/path/to/repo"), since_days=90)
        >>> analysis = analyzer.analyze_repo()
        >>> hotspots = analyzer.get_hotspots(top_n=20)
    """

    def __init__(
        self,
        repo_path: Path,
        since_days: int = 90,
    ) -> None:
        """
        Initialize Git churn analyzer.

        Args:
            repo_path: Path to the Git repository
            since_days: Number of days to analyze (default: 90)
        """
        self.repo_path = repo_path
        self.since_days = since_days
        self._since_date = datetime.now() - timedelta(days=since_days)
        self._complexity_cache: Dict[str, float] = {}

        logger.debug(f"GitChurnAnalyzer initialized for {repo_path} (since={since_days}d)")

    def analyze_repo(self, since: str = "3 months") -> ChurnAnalysis:
        """
        Analyze repository Git history.

        Args:
            since: Time period to analyze (e.g., "3 months", "90 days")

        Returns:
            ChurnAnalysis with complete analysis results
        """
        logger.info(f"Analyzing Git history for {self.repo_path} (since={since})")

        analysis = ChurnAnalysis(analyzed_at=datetime.now())

        # Parse since parameter
        since_days = self._parse_since_parameter(since)
        self.since_days = since_days
        self._since_date = datetime.now() - timedelta(days=since_days)

        # Get all commits in the period
        analysis.commits = self._get_all_commits(since_days)

        # Calculate churn scores for all files
        changed_files = set()
        for commit in analysis.commits:
            changed_files.update(commit.changed_files)

        for file_path in changed_files:
            score = self.get_churn_score(Path(file_path))
            analysis.file_scores[file_path] = score

        # Calculate hotspots
        analysis.hotspots = self.get_hotspots(top_n=50)

        logger.info(
            f"Analysis complete: {len(analysis.commits)} commits, "
            f"{len(analysis.file_scores)} files, "
            f"{len(analysis.hotspots)} hotspots"
        )

        return analysis

    def get_churn_score(self, file_path: Path) -> float:
        """
        Get churn score for a file.

        Churn score is calculated as:
        churn_score = commit_count * avg_changed_lines

        Args:
            file_path: Path to the file (relative to repo root)

        Returns:
            Churn score (higher = more churn)
        """
        if not self.repo_path.exists():
            logger.warning(f"Repository does not exist: {self.repo_path}")
            return 0.0

        try:
            # Get commit count
            commit_count = self._get_commit_count(file_path)

            # Get average changed lines per commit
            total_changed = self._get_total_changed_lines(file_path)
            avg_changed = total_changed / commit_count if commit_count > 0 else 0

            # Churn score formula
            churn_score = commit_count * max(1, avg_changed / 10.0)

            return churn_score

        except Exception as e:
            logger.error(f"Failed to get churn score for {file_path}: {e}")
            return 0.0

    def get_hotspots(self, top_n: int = 20) -> List[Hotspot]:
        """
        Get Git history hotspots.

        Hotspot score formula:
        hotspot_score = churn_score * complexity_score * recency_weight

        Args:
            top_n: Number of top hotspots to return

        Returns:
            List of Hotspot objects sorted by hotspot_score
        """
        if not self.repo_path.exists():
            return []

        try:
            # Get all changed files
            changed_files = self._get_changed_files()

            # Calculate hotspot score for each file
            hotspots = []
            for file_path in changed_files:
                churn_score = self.get_churn_score(Path(file_path))
                if churn_score == 0:
                    continue

                complexity_score = self._get_complexity_score(file_path)
                recency_weight = self._get_recency_weight(file_path)

                # Hotspot score formula
                hotspot_score = churn_score * complexity_score * recency_weight

                # Get recent commits for this file
                recent_commits = self.get_recent_changes(Path(file_path), limit=5)

                hotspot = Hotspot(
                    file_path=file_path,
                    churn_score=churn_score,
                    complexity_score=complexity_score,
                    hotspot_score=hotspot_score,
                    commit_count=self._get_commit_count(Path(file_path)),
                    recent_commits=recent_commits,
                )
                hotspots.append(hotspot)

            # Sort by hotspot_score descending
            hotspots.sort(key=lambda h: h.hotspot_score, reverse=True)

            logger.info(f"Found {len(hotspots)} hotspots")
            return hotspots[:top_n]

        except Exception as e:
            logger.error(f"Failed to get hotspots: {e}")
            return []

    def get_blame(self, file_path: Path) -> List[BlameLine]:
        """
        Get git blame information for a file.

        Args:
            file_path: Path to the file (relative to repo root)

        Returns:
            List of BlameLine objects
        """
        if not self.repo_path.exists():
            return []

        full_path = self.repo_path / file_path
        if not full_path.exists():
            logger.warning(f"File does not exist: {full_path}")
            return []

        try:
            cmd = [
                "git",
                "blame",
                "--line-porcelain",
                str(file_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=120,
            )

            if result.returncode != 0:
                logger.warning(f"Git blame failed: {result.stderr}")
                return []

            return self._parse_blame_output(result.stdout)

        except subprocess.TimeoutExpired:
            logger.warning(f"Git blame timed out for {file_path}")
            return []

        except Exception as e:
            logger.error(f"Git blame failed: {e}")
            return []

    def get_recent_changes(self, file_path: Path, limit: int = 5) -> List[GitCommit]:
        """
        Get recent commits for a file.

        Args:
            file_path: Path to the file
            limit: Maximum number of commits to return

        Returns:
            List of GitCommit objects
        """
        if not self.repo_path.exists():
            return []

        try:
            cmd = [
                "git",
                "log",
                f"--since={self.since_days} days ago",
                "--format=%H|%an|%ai|%s",
                "--max-count",
                str(limit),
                "--",
                str(file_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=30,
            )

            if result.returncode != 0:
                return []

            commits = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("|")
                if len(parts) >= 4:
                    commit_hash = parts[0]
                    author = parts[1]
                    date_str = parts[2]
                    message = parts[3]

                    try:
                        date = datetime.fromisoformat(date_str)
                    except ValueError:
                        date = datetime.now()

                    # Get changed files for this commit
                    changed_files = self._get_commit_files(commit_hash)

                    commit = GitCommit(
                        hash=commit_hash,
                        author=author,
                        date=date,
                        message=message,
                        changed_files=changed_files,
                    )
                    commits.append(commit)

            return commits

        except Exception as e:
            logger.error(f"Failed to get recent changes: {e}")
            return []

    def calculate_hotspot_score(
        self,
        file_path: str,
        churn_score: Optional[float] = None,
        complexity_score: Optional[float] = None,
        recency_weight: Optional[float] = None,
    ) -> float:
        """
        Calculate hotspot score for a file.

        Formula: hotspot_score = churn_score * complexity_score * recency_weight

        Args:
            file_path: File path
            churn_score: Pre-calculated churn score (optional)
            complexity_score: Pre-calculated complexity score (optional)
            recency_weight: Pre-calculated recency weight (optional)

        Returns:
            Hotspot score
        """
        if churn_score is None:
            churn_score = self.get_churn_score(Path(file_path))

        if complexity_score is None:
            complexity_score = self._get_complexity_score(file_path)

        if recency_weight is None:
            recency_weight = self._get_recency_weight(file_path)

        return churn_score * complexity_score * recency_weight

    def _get_commit_count(self, file_path: Path) -> int:
        """Get number of commits for a file."""
        try:
            cmd = [
                "git",
                "log",
                "--oneline",
                f"--since={self.since_days} days ago",
                "--",
                str(file_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=30,
            )

            if result.returncode == 0:
                lines = [l for l in result.stdout.split("\n") if l.strip()]
                return len(lines)
            return 0

        except Exception:
            return 0

    def _get_total_changed_lines(self, file_path: Path) -> int:
        """Get total changed lines for a file."""
        try:
            cmd = [
                "git",
                "log",
                "--numstat",
                f"--since={self.since_days} days ago",
                "--",
                str(file_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=30,
            )

            if result.returncode != 0:
                return 0

            total = 0
            for line in result.stdout.split("\n"):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            if parts[0] != "-":
                                total += int(parts[0])
                            if parts[1] != "-":
                                total += int(parts[1])
                        except ValueError:
                            continue

            return total

        except Exception:
            return 0

    def _get_changed_files(self) -> List[str]:
        """Get list of files changed in the time period."""
        try:
            cmd = [
                "git",
                "log",
                "--name-only",
                "--format=",
                f"--since={self.since_days} days ago",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=60,
            )

            if result.returncode == 0:
                files = set()
                for line in result.stdout.split("\n"):
                    if line.strip():
                        files.add(line.strip())
                return list(files)
            return []

        except Exception as e:
            logger.error(f"Failed to get changed files: {e}")
            return []

    def _get_all_commits(self, since_days: int) -> List[GitCommit]:
        """Get all commits in the time period."""
        try:
            cmd = [
                "git",
                "log",
                f"--since={since_days} days ago",
                "--format=%H|%an|%ai|%s",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=60,
            )

            if result.returncode != 0:
                return []

            commits = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("|")
                if len(parts) >= 4:
                    commit_hash = parts[0]
                    author = parts[1]
                    date_str = parts[2]
                    message = parts[3]

                    try:
                        date = datetime.fromisoformat(date_str)
                    except ValueError:
                        date = datetime.now()

                    changed_files = self._get_commit_files(commit_hash)

                    commit = GitCommit(
                        hash=commit_hash,
                        author=author,
                        date=date,
                        message=message,
                        changed_files=changed_files,
                    )
                    commits.append(commit)

            return commits

        except Exception as e:
            logger.error(f"Failed to get commits: {e}")
            return []

    def _get_commit_files(self, commit_hash: str) -> List[str]:
        """Get list of files changed in a commit."""
        try:
            cmd = [
                "git",
                "show",
                "--name-only",
                "--format=",
                commit_hash,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=30,
            )

            if result.returncode == 0:
                files = []
                for line in result.stdout.split("\n"):
                    if line.strip():
                        files.append(line.strip())
                return files
            return []

        except Exception:
            return []

    def _parse_blame_output(self, output: str) -> List[BlameLine]:
        """Parse git blame porcelain output."""
        blame_info = []
        current_info: Dict[str, Any] = {}
        line_number = 0

        for line in output.split("\n"):
            if not line:
                continue

            # Parse commit hash line
            if len(line) >= 40 and all(c in "0123456789abcdef" for c in line[:40]):
                if current_info and "content" in current_info:
                    blame_info.append(self._create_blame_info(current_info, line_number))
                    line_number += 1
                current_info = {"commit_hash": line[:40]}

            # Parse metadata lines
            elif line.startswith("\t"):
                current_info["content"] = line[1:]

            elif line.startswith("author "):
                current_info["author"] = line[7:]

            elif line.startswith("author-time "):
                try:
                    timestamp = int(line[12:])
                    current_info["date"] = datetime.fromtimestamp(timestamp)
                except ValueError:
                    pass

        # Add last entry
        if current_info and "content" in current_info:
            blame_info.append(self._create_blame_info(current_info, line_number))

        return blame_info

    def _create_blame_info(self, info: Dict[str, Any], line_number: int) -> BlameLine:
        """Create BlameLine from parsed data."""
        return BlameLine(
            line_number=line_number + 1,
            content=info.get("content", ""),
            commit_hash=info.get("commit_hash", ""),
            author=info.get("author", "unknown"),
            date=info.get("date", datetime.now()),
        )

    def _get_complexity_score(self, file_path: str) -> float:
        """
        Get complexity score for a file.

        Uses simple heuristics based on file size and type.
        In production, this would use the ComplexityAnalyzer.

        Args:
            file_path: File path

        Returns:
            Complexity score (1.0 - 10.0)
        """
        if file_path in self._complexity_cache:
            return self._complexity_cache[file_path]

        try:
            full_path = self.repo_path / file_path
            if not full_path.exists():
                return 1.0

            # Count lines of code
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            loc = len([l for l in lines if l.strip() and not l.strip().startswith("#")])

            # Base complexity on LOC
            if loc < 100:
                complexity = 1.0
            elif loc < 300:
                complexity = 2.0
            elif loc < 500:
                complexity = 4.0
            elif loc < 1000:
                complexity = 6.0
            else:
                complexity = 8.0

            # Adjust by file type
            extension = Path(file_path).suffix.lower()
            if extension in (".py", ".js", ".ts"):
                complexity *= 1.2
            elif extension in (".rs", ".go"):
                complexity *= 1.0
            elif extension in (".java", ".cpp"):
                complexity *= 1.1

            self._complexity_cache[file_path] = min(10.0, complexity)
            return self._complexity_cache[file_path]

        except Exception:
            return 1.0

    def _get_recency_weight(self, file_path: str) -> float:
        """
        Get recency weight for a file.

        More recent changes = higher weight.

        Args:
            file_path: File path

        Returns:
            Recency weight (0.5 - 2.0)
        """
        try:
            recent_commits = self.get_recent_changes(Path(file_path), limit=1)
            if not recent_commits:
                return 1.0

            last_commit = recent_commits[0]
            days_since = (datetime.now() - last_commit.date).days

            if days_since == 0:
                return 2.0
            elif days_since <= 7:
                return 1.8
            elif days_since <= 14:
                return 1.5
            elif days_since <= 30:
                return 1.2
            elif days_since <= 60:
                return 1.0
            else:
                return 0.8

        except Exception:
            return 1.0

    def _parse_since_parameter(self, since: str) -> int:
        """Parse since parameter to days."""
        since_lower = since.lower()

        if "day" in since_lower:
            try:
                return int(since_lower.split()[0])
            except ValueError:
                return 90
        elif "week" in since_lower:
            try:
                return int(since_lower.split()[0]) * 7
            except ValueError:
                return 90
        elif "month" in since_lower:
            try:
                return int(since_lower.split()[0]) * 30
            except ValueError:
                return 90
        else:
            return 90

    def is_repository_clean(self) -> bool:
        """Check if repository has uncommitted changes."""
        try:
            cmd = ["git", "status", "--porcelain"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=10,
            )
            return result.returncode == 0 and not result.stdout.strip()
        except Exception:
            return False

    def get_current_branch(self) -> Optional[str]:
        """Get current Git branch name."""
        try:
            cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None

    def get_remote_url(self) -> Optional[str]:
        """Get Git remote URL."""
        try:
            cmd = ["git", "remote", "get-url", "origin"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None
