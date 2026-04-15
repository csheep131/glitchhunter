"""
Ignore management for GlitchHunter.

Loads and applies ignore patterns from .glitchignore files.
"""

import logging
import fnmatch
from pathlib import Path
from typing import List, Optional, Set

logger = logging.getLogger(__name__)

DEFAULT_IGNORE_PATTERNS = [
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "__pycache__",
    "venv",
    ".venv",
    "env",
    ".env",
    "target",  # Rust
    "dist",
    "build",
    ".cache",
    ".temp",
    ".pytest_cache",
    "*.pyc",
    "*.pyo",
    "*.so",
    "*.o",
    "*.a",
]


class IgnoreManager:
    """
    Manages exclusion patterns for repository scanning.

    Loads defaults and custom patterns from .glitchignore.
    """

    def __init__(self, repo_path: Path) -> None:
        """
        Initialize the ignore manager.

        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = repo_path.resolve()
        self.patterns: List[str] = DEFAULT_IGNORE_PATTERNS.copy()
        self._load_glitchignore()
        logger.debug(f"IgnoreManager initialized with {len(self.patterns)} patterns for {repo_path}")

    def _load_glitchignore(self) -> None:
        """Load custom patterns from .glitchignore file."""
        ignore_file = self.repo_path / ".glitchignore"
        if ignore_file.exists():
            try:
                with open(ignore_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            self.patterns.append(line)
                logger.info(f"Loaded custom ignore patterns from {ignore_file}")
            except Exception as e:
                logger.warning(f"Failed to read {ignore_file}: {e}")

    def should_ignore(self, path: Path) -> bool:
        """
        Check if a file or directory should be ignored.

        Args:
            path: Path to check

        Returns:
            True if the path should be ignored
        """
        # Resolve path relative to repo root
        try:
            rel_path = path.resolve().relative_to(self.repo_path)
        except ValueError:
            # Path not under repo root
            return False

        path_parts = rel_path.parts
        
        # Check each part of the path against patterns
        for part in path_parts:
            for pattern in self.patterns:
                # Direct match or glob match
                if part == pattern or fnmatch.fnmatch(part, pattern):
                    return True
                
        # Also check the full relative path string for patterns like "logs/*.log"
        path_str = str(rel_path)
        for pattern in self.patterns:
            if fnmatch.fnmatch(path_str, pattern):
                return True

        return False
