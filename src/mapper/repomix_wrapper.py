"""
Repomix wrapper for GlitchHunter.

Provides integration with Repomix for packing repository context into
XML format for LLM consumption.
"""

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class RepomixWrapper:
    """
    Wrapper for Repomix CLI tool.

    Repomix packs repository files into a single XML/Markdown file
    suitable for LLM context.

    Attributes:
        repo_path: Path to the repository
        output_format: Output format (xml, markdown)

    Example:
        >>> wrapper = RepomixWrapper(Path("/path/to/repo"))
        >>> output_path = wrapper.pack_repo()
        >>> content = wrapper.read_output(output_path)
    """

    def __init__(
        self,
        repo_path: Path,
        output_format: str = "xml",
        repomix_path: Optional[str] = None,
    ) -> None:
        """
        Initialize Repomix wrapper.

        Args:
            repo_path: Path to the repository
            output_format: Output format ("xml" or "markdown")
            repomix_path: Path to repomix executable
        """
        self.repo_path = repo_path
        self.output_format = output_format
        self.repomix_path = repomix_path or "repomix"
        self._packed_size: Optional[int] = None
        self._token_estimate: Optional[int] = None

        logger.debug(
            f"RepomixWrapper initialized for {repo_path} (format={output_format})"
        )

    def pack_repo(
        self,
        output_format: str = "xml",
    ) -> str:
        """
        Pack entire repository into a single string.

        Args:
            output_format: Output format ("xml", "markdown", "plain")

        Returns:
            Packed repository content as string
        """
        if not self.repo_path.exists():
            raise ValidationError(
                f"Repository path does not exist: {self.repo_path}",
                field="repo_path",
            )

        # Create temporary output file
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=self._get_extension(output_format),
            delete=False,
        ) as tmp:
            output_path = Path(tmp.name)

        try:
            cmd = [
                self.repomix_path,
                "--output",
                str(output_path),
                "--format",
                output_format,
                "--stdout",
            ]

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Repomix failed: {result.stderr}")

            content = result.stdout

            # Cache size
            self._packed_size = len(content.encode("utf-8"))
            self._token_estimate = self._estimate_tokens(content)

            logger.info(f"Repository packed: {self._packed_size} bytes")
            return content

        except subprocess.TimeoutExpired:
            raise RuntimeError("Repomix timed out after 5 minutes")

        except FileNotFoundError:
            raise RuntimeError(
                f"Repomix not found at '{self.repomix_path}'. "
                "Install with: npm install -g repomix"
            )

        finally:
            # Clean up temp file
            if output_path.exists():
                output_path.unlink()

    def pack_subdirectory(
        self,
        subdir: str,
        output_format: str = "xml",
    ) -> str:
        """
        Pack a specific subdirectory.

        Args:
            subdir: Subdirectory path relative to repo root
            output_format: Output format

        Returns:
            Packed subdirectory content as string
        """
        subdir_path = self.repo_path / subdir

        if not subdir_path.exists():
            raise ValidationError(
                f"Subdirectory does not exist: {subdir}",
                field="subdirectory",
            )

        try:
            cmd = [
                self.repomix_path,
                "--format",
                output_format,
                "--stdout",
                str(subdir_path),
            ]

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Repomix failed: {result.stderr}")

            content = result.stdout

            self._packed_size = len(content.encode("utf-8"))
            self._token_estimate = self._estimate_tokens(content)

            logger.info(f"Subdirectory '{subdir}' packed: {self._packed_size} bytes")
            return content

        except subprocess.TimeoutExpired:
            raise RuntimeError("Repomix timed out after 5 minutes")

        except FileNotFoundError:
            raise RuntimeError(f"Repomix not found at '{self.repomix_path}'")

    def pack_files(
        self,
        file_paths: List[str],
        output_format: str = "xml",
    ) -> str:
        """
        Pack specific files.

        Args:
            file_paths: List of file paths relative to repo root
            output_format: Output format

        Returns:
            Packed files content as string
        """
        # Validate files exist
        for file_path in file_paths:
            full_path = self.repo_path / file_path
            if not full_path.exists():
                raise ValidationError(
                    f"File does not exist: {file_path}",
                    field="file_paths",
                )

        try:
            cmd = [
                self.repomix_path,
                "--format",
                output_format,
                "--stdout",
            ] + file_paths

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Repomix failed: {result.stderr}")

            content = result.stdout

            self._packed_size = len(content.encode("utf-8"))
            self._token_estimate = self._estimate_tokens(content)

            logger.info(f"Packed {len(file_paths)} files: {self._packed_size} bytes")
            return content

        except subprocess.TimeoutExpired:
            raise RuntimeError("Repomix timed out after 5 minutes")

        except FileNotFoundError:
            raise RuntimeError(f"Repomix not found at '{self.repomix_path}'")

    def get_packed_size(self) -> int:
        """
        Get size of last packed output in bytes.

        Returns:
            Size in bytes
        """
        return self._packed_size or 0

    def estimate_token_count(self) -> int:
        """
        Estimate token count of last packed output.

        Uses simple heuristic: ~4 characters per token for English text.

        Returns:
            Estimated token count
        """
        return self._token_estimate or 0

    def is_available(self) -> bool:
        """
        Check if Repomix is available.

        Returns:
            True if Repomix is installed
        """
        try:
            result = subprocess.run(
                [self.repomix_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_version(self) -> Optional[str]:
        """
        Get Repomix version.

        Returns:
            Version string or None
        """
        try:
            result = subprocess.run(
                [self.repomix_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None

    def _get_extension(self, output_format: str) -> str:
        """Get file extension for output format."""
        extensions = {
            "xml": ".xml",
            "markdown": ".md",
            "plain": ".txt",
        }
        return extensions.get(output_format, ".txt")

    def _estimate_tokens(self, content: str) -> int:
        """
        Estimate token count for content.

        Uses heuristic: ~4 characters per token for English text.

        Args:
            content: Text content

        Returns:
            Estimated token count
        """
        # Simple character-based estimation
        return len(content) // 4
