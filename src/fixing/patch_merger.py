"""
Patch Merger für GlitchHunter.

Mergt akzeptierte Patches in die Main-Branch mit:
- Git-Worktree für Isolation
- Detaillierten Commit-Messages
- Bug-ID Tags
"""

import logging
import subprocess
import tempfile
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GitCommit:
    """
    Git-Commit Information.

    Attributes:
        hash: Commit-Hash
        message: Commit-Message
        files_changed: Geänderte Dateien
        timestamp: Commit-Zeitpunkt
        branch: Branch-Name
        tags: Tags
    """

    hash: str
    message: str
    files_changed: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    branch: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "hash": self.hash,
            "message": self.message,
            "files_changed": self.files_changed,
            "timestamp": self.timestamp.isoformat(),
            "branch": self.branch,
            "tags": self.tags,
        }


@dataclass
class MergeResult:
    """
    Ergebnis des Patch-Merge.

    Attributes:
        success: True wenn erfolgreich
        commit: Commit-Information
        worktree_path: Pfad zum Worktree
        error: Fehlermeldung
        merged_patches: Anzahl gemergter Patches
    """

    success: bool = False
    commit: Optional[GitCommit] = None
    worktree_path: Optional[str] = None
    error: Optional[str] = None
    merged_patches: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "success": self.success,
            "commit": self.commit.to_dict() if self.commit else None,
            "worktree_path": self.worktree_path,
            "error": self.error,
            "merged_patches": self.merged_patches,
        }


class PatchMerger:
    """
    Mergt Patches in Git-Repository.

    Features:
    - Git-Worktree für Isolation
    - Automatische Branch-Erstellung
    - Detaillierte Commit-Messages
    - Bug-ID Tags

    Usage:
        merger = PatchMerger(repo_path)
        result = merger.merge_patches(patches)
    """

    def __init__(
        self,
        repo_path: str,
        base_branch: str = "main",
        prefix: str = "glitchhunter",
    ) -> None:
        """
        Initialisiert Patch Merger.

        Args:
            repo_path: Pfad zum Repository.
            base_branch: Basis-Branch.
            prefix: Prefix für Branch-Namen.
        """
        self.repo_path = Path(repo_path)
        self.base_branch = base_branch
        self.prefix = prefix

        self._git_available = self._check_git()

        if not self._git_available:
            logger.warning("Git nicht verfügbar - Patch Merger deaktiviert")

        logger.debug(
            f"PatchMerger initialisiert: repo={repo_path}, "
            f"base_branch={base_branch}"
        )

    def _check_git(self) -> bool:
        """Prüft ob Git verfügbar ist."""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def merge_patches(
        self,
        patches: List[Dict[str, Any]],
        commit_message: Optional[str] = None,
    ) -> MergeResult:
        """
        Mergt mehrere Patches.

        Args:
            patches: Liste von Patches.
            commit_message: Optionale Commit-Message.

        Returns:
            MergeResult.
        """
        logger.info(f"Merge {len(patches)} Patches in {self.repo_path}")

        result = MergeResult()

        if not self._git_available:
            result.error = "Git nicht verfügbar"
            return result

        if not patches:
            result.error = "Keine Patches zum Mergen"
            return result

        try:
            # Worktree erstellen
            worktree_path = self._create_worktree(patches)
            result.worktree_path = worktree_path

            # Patches anwenden
            applied = self._apply_patches(worktree_path, patches)
            result.merged_patches = applied

            if applied == 0:
                result.error = "Keine Patches angewendet"
                return result

            # Commit erstellen
            commit = self._create_commit(
                worktree_path,
                patches,
                commit_message,
            )
            result.commit = commit

            # Optional: Zurück zu main mergen
            # merge_success = self._merge_to_base(worktree_path)

            result.success = True

            logger.info(
                f"Patch-Merge erfolgreich: {applied} Patches, "
                f"Commit {commit.hash[:8]}"
            )

        except Exception as e:
            logger.error(f"Patch-Merge fehlgeschlagen: {e}")
            result.error = str(e)

        return result

    def merge_single_patch(
        self,
        patch: Dict[str, Any],
    ) -> MergeResult:
        """
        Mergt einzelnen Patch.

        Args:
            patch: Patch-Dict.

        Returns:
            MergeResult.
        """
        return self.merge_patches([patch])

    def _create_worktree(self, patches: List[Dict[str, Any]]) -> str:
        """
        Erstellt isolierten Worktree.

        Args:
            patches: Liste von Patches.

        Returns:
            Pfad zum Worktree.
        """
        # Branch-Namen generieren
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bug_ids = self._extract_bug_ids(patches)
        branch_name = f"{self.prefix}/fix_{'_'.join(bug_ids)}_{timestamp}"

        # Temp-Verzeichnis für Worktree
        temp_dir = tempfile.mkdtemp(prefix="glitchhunter_")
        worktree_path = os.path.join(temp_dir, branch_name.replace("/", "_"))

        # Git-Worktree erstellen
        result = subprocess.run(
            [
                "git", "-C", str(self.repo_path),
                "worktree", "add",
                "-b", branch_name,
                worktree_path,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Worktree-Erstellung fehlgeschlagen: {result.stderr}")

        logger.info(f"Worktree erstellt: {worktree_path} (Branch: {branch_name})")
        return worktree_path

    def _apply_patches(
        self,
        worktree_path: str,
        patches: List[Dict[str, Any]],
    ) -> int:
        """
        Wendet Patches auf Worktree an.

        Args:
            worktree_path: Pfad zum Worktree.
            patches: Liste von Patches.

        Returns:
            Anzahl angewendeter Patches.
        """
        applied = 0

        for patch in patches:
            patch_diff = patch.get("patch_diff", "")
            file_path = patch.get("file_path", "")

            if not patch_diff:
                logger.warning(f"Patch ohne Diff: {file_path}")
                continue

            # Patch-Datei erstellen
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".patch", delete=False
            ) as f:
                f.write(patch_diff)
                patch_file = f.name

            try:
                # Patch anwenden
                result = subprocess.run(
                    ["git", "-C", worktree_path, "apply", patch_file],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode != 0:
                    logger.warning(
                        f"Patch-Anwendung fehlgeschlagen: {result.stderr}"
                    )
                    continue

                applied += 1
                logger.info(f"Patch angewendet: {file_path}")

            finally:
                os.unlink(patch_file)

        return applied

    def _create_commit(
        self,
        worktree_path: str,
        patches: List[Dict[str, Any]],
        custom_message: Optional[str] = None,
    ) -> GitCommit:
        """
        Erstellt Git-Commit.

        Args:
            worktree_path: Pfad zum Worktree.
            patches: Liste von Patches.
            custom_message: Optionale Commit-Message.

        Returns:
            GitCommit.
        """
        # Alle Dateien stagen
        subprocess.run(
            ["git", "-C", worktree_path, "add", "-A"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Commit-Message generieren
        if custom_message:
            message = custom_message
        else:
            message = self._generate_commit_message(patches)

        # Commit erstellen
        result = subprocess.run(
            ["git", "-C", worktree_path, "commit", "-m", message],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Commit fehlgeschlagen: {result.stderr}")

        # Commit-Hash extrahieren
        hash_result = subprocess.run(
            ["git", "-C", worktree_path, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        commit_hash = hash_result.stdout.strip()

        # Geänderte Dateien extrahieren
        files_result = subprocess.run(
            ["git", "-C", worktree_path, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        files_changed = [f.strip() for f in files_result.stdout.split("\n") if f.strip()]

        # Branch-Namen extrahieren
        branch_result = subprocess.run(
            ["git", "-C", worktree_path, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        branch_name = branch_result.stdout.strip()

        # Tags aus Bug-IDs
        tags = [f"glitchhunter/{bug_id}" for bug_id in self._extract_bug_ids(patches)]

        return GitCommit(
            hash=commit_hash,
            message=message,
            files_changed=files_changed,
            branch=branch_name,
            tags=tags,
        )

    def _generate_commit_message(self, patches: List[Dict[str, Any]]) -> str:
        """
        Generiert Commit-Message.

        Args:
            patches: Liste von Patches.

        Returns:
            Commit-Message.
        """
        bug_ids = self._extract_bug_ids(patches)
        bug_types = self._extract_bug_types(patches)
        files_changed = set()

        for patch in patches:
            file_path = patch.get("file_path", "")
            if file_path:
                files_changed.add(Path(file_path).name)

        # Title
        title = f"GlitchHunter: Fix {len(patches)} issue(s)"

        # Body
        body_lines = [
            "",
            "Automated bug fixes from GlitchHunter:",
            "",
        ]

        for i, patch in enumerate(patches, 1):
            bug_type = patch.get("bug_type", "unknown")
            file_path = patch.get("file_path", "unknown")
            description = patch.get("description", "")

            body_lines.append(f"{i}. {bug_type} in {Path(file_path).name}")
            if description:
                body_lines.append(f"   {description}")

        # Footer
        body_lines.extend([
            "",
            f"Bug IDs: {', '.join(bug_ids)}",
            f"Files changed: {', '.join(files_changed)}",
            "",
            "Generated by GlitchHunter",
        ])

        return "\n".join(body_lines)

    def _extract_bug_ids(self, patches: List[Dict[str, Any]]) -> List[str]:
        """Extrahiert Bug-IDs aus Patches."""
        bug_ids = []

        for patch in patches:
            bug_id = patch.get("bug_id", patch.get("id", ""))
            if bug_id:
                bug_ids.append(str(bug_id))

        return bug_ids[:3]  # Max 3 Bug-IDs für Branch-Namen

    def _extract_bug_types(self, patches: List[Dict[str, Any]]) -> List[str]:
        """Extrahiert Bug-Typen aus Patches."""
        bug_types = []

        for patch in patches:
            bug_type = patch.get("bug_type", "")
            if bug_type and bug_type not in bug_types:
                bug_types.append(bug_type)

        return bug_types

    def _merge_to_base(self, worktree_path: str) -> bool:
        """
        Mergt Worktree zurück zu Base-Branch.

        Args:
            worktree_path: Pfad zum Worktree.

        Returns:
            True wenn erfolgreich.
        """
        try:
            # Checkout base branch
            subprocess.run(
                ["git", "-C", str(self.repo_path), "checkout", self.base_branch],
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Merge worktree branch
            branch_result = subprocess.run(
                ["git", "-C", worktree_path, "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            worktree_branch = branch_result.stdout.strip()

            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "merge", worktree_branch, "--no-ff"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                logger.warning(f"Merge fehlgeschlagen: {result.stderr}")
                return False

            logger.info(f"Worktree gemergt in {self.base_branch}")
            return True

        except Exception as e:
            logger.error(f"Merge-to-Base fehlgeschlagen: {e}")
            return False

    def cleanup_worktree(self, worktree_path: str) -> bool:
        """
        Räumt Worktree auf.

        Args:
            worktree_path: Pfad zum Worktree.

        Returns:
            True wenn erfolgreich.
        """
        try:
            # Worktree entfernen
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "worktree", "remove", "-f", worktree_path],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                logger.warning(f"Worktree-Entfernung fehlgeschlagen: {result.stderr}")
                return False

            # Verzeichnis löschen
            if os.path.exists(worktree_path):
                import shutil
                shutil.rmtree(worktree_path)

            logger.info(f"Worktree aufgeräumt: {worktree_path}")
            return True

        except Exception as e:
            logger.error(f"Worktree-Cleanup fehlgeschlagen: {e}")
            return False

    def __call__(self, state: Any) -> Dict[str, Any]:
        """
        Callable für LangGraph.

        Args:
            state: AgentState.

        Returns:
            State-Updates.
        """
        accepted_patches = getattr(state, "accepted_patches", [])

        if not accepted_patches:
            return {"metadata": {"patches_merged": 0}}

        result = self.merge_patches(accepted_patches)

        return {
            "merge_result": result.to_dict(),
            "git_commit": result.commit.to_dict() if result.commit else None,
            "metadata": {
                "patches_merged": result.merged_patches,
                "merge_success": result.success,
                "commit_hash": result.commit.hash[:8] if result.commit else None,
            },
        }
