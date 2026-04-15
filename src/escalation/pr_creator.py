"""
PR Creator für GlitchHunter Escalation Level 4.

Erstellt Draft-PRs auf GitHub und GitLab mit automatischen Fix-Patches.

Features:
- GitHub Integration via PyGithub
- GitLab Integration via python-gitlab
- Auto-Branch-Erstellung
- Patch-Anwendung
- Commit & Push
- Draft-PR/MR-Erstellung mit Labels
"""

import logging
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from git import GitCommandError, Repo

logger = logging.getLogger(__name__)


@dataclass
class PRResult:
    """
    Ergebnis einer PR-Erstellung.

    Attributes:
        success: Erfolgreich erstellt
        url: URL zur PR/MR
        number: PR/MR-Nummer
        state: Status (open/closed)
        draft: Ist Draft-PR
        platform: Plattform (github/gitlab)
        error: Fehlermeldung falls fehlgeschlagen
        metadata: Zusätzliche Metadaten
    """

    success: bool
    url: str = ""
    number: int = 0
    state: str = ""
    draft: bool = False
    platform: str = ""
    error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "success": self.success,
            "url": self.url,
            "number": self.number,
            "state": self.state,
            "draft": self.draft,
            "platform": self.platform,
            "error": self.error,
            "metadata": self.metadata,
        }


class BasePRCreator(ABC):
    """
    Abstrakte Basisklasse für PR-Creator.

    Definiert gemeinsames Interface für GitHub und GitLab.
    """

    def __init__(self, local_repo_path: Optional[str] = None) -> None:
        """
        Initialisiert PR-Creator.

        Args:
            local_repo_path: Pfad zum lokalen Repository (optional).
        """
        self.local_repo_path = local_repo_path
        self.local_repo: Optional[Repo] = None

    @abstractmethod
    def create_draft_pr(
        self,
        bug: Dict[str, Any],
        fix_suggestions: List[str],
        patch_diff: str,
        branch_name: Optional[str] = None,
    ) -> PRResult:
        """
        Erstellt Draft-PR mit Fix.

        Args:
            bug: Bug-Informationen
            fix_suggestions: Liste von Fix-Beschreibungen
            patch_diff: Unified Diff des Patches
            branch_name: Branch-Name (optional)

        Returns:
            PRResult mit PR-Informationen
        """
        pass

    @abstractmethod
    def _generate_pr_body(self, bug: Dict[str, Any], fix_suggestions: List[str]) -> str:
        """
        Generiert PR-Beschreibung.

        Args:
            bug: Bug-Informationen
            fix_suggestions: Fix-Vorschläge

        Returns:
            PR-Beschreibung als String
        """
        pass

    def _generate_branch_name(self, bug: Dict[str, Any]) -> str:
        """
        Generiert Branch-Namen aus Bug-Informationen.

        Args:
            bug: Bug-Informationen

        Returns:
            Branch-Name im Format glitchhunter/fix-{bug_id}
        """
        bug_id = bug.get("bug_id", bug.get("id", "unknown"))
        # Bug-ID auf 8 Zeichen kürzen für lesbare Branch-Namen
        bug_id_short = str(bug_id)[:8]
        return f"glitchhunter/fix-{bug_id_short}"

    def _clone_or_open_repo(self, remote_url: Optional[str] = None) -> Repo:
        """
        Öffnet lokales Repository oder klont von Remote.

        Args:
            remote_url: Remote-URL zum Klonen (falls kein lokales Repo)

        Returns:
            GitPython Repo-Objekt

        Raises:
            ValueError: Wenn kein lokales Repo vorhanden und keine Remote-URL
            GitCommandError: Wenn Klonen fehlschlägt
        """
        if self.local_repo_path and Path(self.local_repo_path).exists():
            logger.debug(f"Öffne existierendes Repository: {self.local_repo_path}")
            self.local_repo = Repo(self.local_repo_path)
            return self.local_repo

        if remote_url:
            logger.debug(f"Klone Repository von: {remote_url}")
            temp_dir = tempfile.mkdtemp(prefix="glitchhunter_")
            self.local_repo = Repo.clone_from(remote_url, temp_dir)
            self.local_repo_path = temp_dir
            return self.local_repo

        raise ValueError(
            "Kein lokales Repository vorhanden und keine Remote-URL angegeben. "
            "Bitte local_repo_path oder remote_url bereitstellen."
        )

    def _create_branch(self, branch_name: str, base_branch: str = "main") -> None:
        """
        Erstellt neuen Branch vom Base-Branch.

        Args:
            branch_name: Name des neuen Branches
            base_branch: Basis-Branch (default: main)

        Raises:
            GitCommandError: Wenn Branch-Erstellung fehlschlägt
        """
        if not self.local_repo:
            raise RuntimeError("Repository nicht initialisiert. _clone_or_open_repo zuerst aufrufen.")

        logger.debug(f"Erstelle Branch '{branch_name}' von '{base_branch}'")

        # Sicherstellen, dass wir auf dem Base-Branch sind
        self.local_repo.git.checkout(base_branch)

        # Neuen Branch erstellen und wechseln
        self.local_repo.git.checkout("-b", branch_name)

        logger.info(f"Branch '{branch_name}' erstellt")

    def _apply_patch(self, patch_diff: str) -> List[str]:
        """
        Wendet Unified Diff Patch auf Repository an.

        Args:
            patch_diff: Unified Diff als String

        Returns:
            Liste der geänderten Dateien

        Raises:
            ValueError: Wenn Patch ungültig ist
            RuntimeError: Wenn Patch-Anwendung fehlschlägt
        """
        if not self.local_repo:
            raise RuntimeError("Repository nicht initialisiert.")

        if not patch_diff.strip():
            logger.warning("Leerer Patch übersprungen")
            return []

        logger.debug("Wende Patch an")

        # Patch in temporäre Datei schreiben
        with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f:
            f.write(patch_diff)
            patch_file = f.name

        try:
            # Patch anwenden mit git apply
            self.local_repo.git.apply(patch_file)

            # Geänderte Dateien ermitteln
            changed_files = []
            for line in patch_diff.split("\n"):
                if line.startswith("+++ b/"):
                    changed_files.append(line[6:])
                elif line.startswith("+++ "):
                    changed_files.append(line[4:])

            logger.info(f"Patch erfolgreich angewendet: {len(changed_files)} Datei(en)")
            return changed_files

        except GitCommandError as e:
            raise RuntimeError(f"Patch-Anwendung fehlgeschlagen: {e}") from e

        finally:
            # Temporäre Datei aufräumen
            Path(patch_file).unlink(missing_ok=True)

    def _commit_and_push(
        self,
        branch: str,
        message: str,
        remote_name: str = "origin",
    ) -> None:
        """
        Commit und Push zu Remote.

        Args:
            branch: Branch-Name
            message: Commit-Message
            remote_name: Name des Remote (default: origin)

        Raises:
            RuntimeError: Wenn Commit oder Push fehlschlägt
        """
        if not self.local_repo:
            raise RuntimeError("Repository nicht initialisiert.")

        logger.debug(f"Committe Änderungen: {message}")

        # Alle geänderten Dateien stagen
        self.local_repo.git.add("-A")

        # Commit erstellen
        self.local_repo.git.commit("-m", message)

        logger.debug(f"Push zu Remote '{remote_name}/{branch}'")

        # Push zu Remote
        try:
            self.local_repo.git.push(remote_name, branch)
            logger.info(f"Commit und Push erfolgreich: {branch}")
        except GitCommandError as e:
            raise RuntimeError(f"Push fehlgeschlagen: {e}") from e


class GitHubPRCreator(BasePRCreator):
    """
    Erstellt Draft-PRs auf GitHub.

    Usage:
        creator = GitHubPRCreator(token, owner, repo_name)
        result = creator.create_draft_pr(bug, fix_suggestions, patch_diff)
    """

    def __init__(
        self,
        token: str,
        owner: str,
        repo_name: str,
        local_repo_path: Optional[str] = None,
        remote_url: Optional[str] = None,
    ) -> None:
        """
        Initialisiert GitHub PR-Creator.

        Args:
            token: GitHub Personal Access Token
            owner: Repository Owner (User oder Org)
            repo_name: Repository Name
            local_repo_path: Pfad zum lokalen Repository (optional)
            remote_url: Remote-URL zum Klonen (optional)
        """
        super().__init__(local_repo_path)

        from github import Github

        self.token = token
        self.owner = owner
        self.repo_name = repo_name
        self.remote_url = remote_url

        # GitHub Client initialisieren
        self.client = Github(token)
        self.repo = self.client.get_repo(f"{owner}/{repo_name}")

        logger.debug(f"GitHubPRCreator initialisiert für {owner}/{repo_name}")

    def create_draft_pr(
        self,
        bug: Dict[str, Any],
        fix_suggestions: List[str],
        patch_diff: str,
        branch_name: Optional[str] = None,
        base_branch: Optional[str] = None,
    ) -> PRResult:
        """
        Erstellt Draft-PR mit Fix auf GitHub.

        Args:
            bug: Bug-Informationen
            fix_suggestions: Liste von Fix-Beschreibungen
            patch_diff: Unified Diff des Patches
            branch_name: Branch-Name (optional)
            base_branch: Basis-Branch (optional, default: main)

        Returns:
            PRResult mit PR-Informationen
        """
        logger.info(f"Erstelle GitHub Draft-PR für Bug {bug.get('bug_id', 'unknown')}")

        try:
            # Repository öffnen/klonen
            if self.remote_url:
                self._clone_or_open_repo(self.remote_url)
            elif self.local_repo_path:
                self._clone_or_open_repo()
            else:
                raise ValueError(
                    "Entweder local_repo_path oder remote_url muss angegeben werden."
                )

            # Branch-Namen bestimmen
            if branch_name is None:
                branch_name = self._generate_branch_name(bug)

            # Branch erstellen
            base = base_branch or "main"
            self._create_branch(branch_name, base)

            # Patch anwenden
            self._apply_patch(patch_diff)

            # Commit-Message erstellen
            bug_type = bug.get("bug_type", "bug")
            file_path = bug.get("file_path", "")
            commit_msg = f"fix: {bug_type} in {file_path} [automated]"

            # Commit und Push
            self._commit_and_push(branch_name, commit_msg)

            # PR erstellen
            pr_title = f"Fix: {bug_type} in {file_path}"
            pr_body = self._generate_pr_body(bug, fix_suggestions)

            pr = self.repo.create_pull(
                title=pr_title,
                body=pr_body,
                base=base,
                head=branch_name,
                draft=True,
            )

            # Labels hinzufügen
            try:
                pr.add_to_labels("bug", "automated-fix", "needs-review")
                logger.debug(f"Labels hinzugefügt zu PR #{pr.number}")
            except Exception as e:
                logger.warning(f"Labels konnten nicht hinzugefügt werden: {e}")

            logger.info(f"GitHub Draft-PR erstellt: {pr.html_url}")

            return PRResult(
                success=True,
                url=pr.html_url,
                number=pr.number,
                state=pr.state,
                draft=pr.draft,
                platform="github",
                metadata={
                    "title": pr.title,
                    "created_at": pr.created_at.isoformat() if pr.created_at else None,
                    "labels": ["bug", "automated-fix", "needs-review"],
                },
            )

        except Exception as e:
            logger.error(f"GitHub PR-Erstellung fehlgeschlagen: {e}")
            return PRResult(
                success=False,
                error=str(e),
                platform="github",
                metadata={"bug_id": bug.get("bug_id", "unknown")},
            )

    def _generate_pr_body(self, bug: Dict[str, Any], fix_suggestions: List[str]) -> str:
        """
        Generiert PR-Beschreibung für GitHub.

        Args:
            bug: Bug-Informationen
            fix_suggestions: Fix-Vorschläge

        Returns:
            Formatierter Markdown-Text
        """
        bug_type = bug.get("bug_type", "unknown")
        severity = bug.get("severity", "unknown")
        file_path = bug.get("file_path", "")
        line_start = bug.get("line_start", bug.get("line_number", "?"))
        description = bug.get("description", "No description")
        confidence = bug.get("confidence", 0)

        fix_lines = "\n".join(f"- {s}" for s in fix_suggestions)

        return f"""## 🤖 Automated Fix by GlitchHunter

**Bug Type:** {bug_type}  
**Severity:** {severity}  
**File:** `{file_path}` (Line {line_start})

### Description
{description}

### Fix Summary
{fix_lines}

### Confidence
{confidence * 100:.0f}%

---
*This PR was automatically generated by [GlitchHunter](https://github.com/glitchhunter/glitchhunter)*
"""


class GitLabMRCreator(BasePRCreator):
    """
    Erstellt Draft-MRs auf GitLab.

    Usage:
        creator = GitLabMRCreator(url, token, project_id)
        result = creator.create_draft_mr(bug, fix_suggestions, patch_diff)
    """

    def __init__(
        self,
        url: str,
        token: str,
        project_id: int,
        local_repo_path: Optional[str] = None,
        remote_url: Optional[str] = None,
    ) -> None:
        """
        Initialisiert GitLab MR-Creator.

        Args:
            url: GitLab-Server-URL
            token: GitLab Private/Access Token
            project_id: GitLab Projekt-ID
            local_repo_path: Pfad zum lokalen Repository (optional)
            remote_url: Remote-URL zum Klonen (optional)
        """
        super().__init__(local_repo_path)

        from gitlab import Gitlab

        self.url = url
        self.token = token
        self.project_id = project_id
        self.remote_url = remote_url

        # GitLab Client initialisieren
        self.client = Gitlab(url, private_token=token)
        self.project = self.client.projects.get(project_id)

        logger.debug(f"GitLabMRCreator initialisiert für Projekt {project_id} auf {url}")

    def create_draft_mr(
        self,
        bug: Dict[str, Any],
        fix_suggestions: List[str],
        patch_diff: str,
        branch_name: Optional[str] = None,
        base_branch: Optional[str] = None,
    ) -> PRResult:
        """
        Erstellt Draft-MR mit Fix auf GitLab.

        Args:
            bug: Bug-Informationen
            fix_suggestions: Liste von Fix-Beschreibungen
            patch_diff: Unified Diff des Patches
            branch_name: Branch-Name (optional)
            base_branch: Basis-Branch (optional, default: main)

        Returns:
            PRResult mit MR-Informationen
        """
        logger.info(f"Erstelle GitLab Draft-MR für Bug {bug.get('bug_id', 'unknown')}")

        try:
            # Repository öffnen/klonen
            if self.remote_url:
                self._clone_or_open_repo(self.remote_url)
            elif self.local_repo_path:
                self._clone_or_open_repo()
            else:
                raise ValueError(
                    "Entweder local_repo_path oder remote_url muss angegeben werden."
                )

            # Branch-Namen bestimmen
            if branch_name is None:
                branch_name = self._generate_branch_name(bug)

            # Branch erstellen
            base = base_branch or "main"
            self._create_branch(branch_name, base)

            # Patch anwenden
            self._apply_patch(patch_diff)

            # Commit-Message erstellen
            bug_type = bug.get("bug_type", "bug")
            file_path = bug.get("file_path", "")
            commit_msg = f"fix: {bug_type} in {file_path} [automated]"

            # Commit und Push
            self._commit_and_push(branch_name, commit_msg)

            # MR erstellen
            mr_title = f"Fix: {bug_type} in {file_path}"
            mr_body = self._generate_pr_body(bug, fix_suggestions)

            # GitLab MR erstellen
            mr_data = {
                "source_branch": branch_name,
                "target_branch": base,
                "title": mr_title,
                "description": mr_body,
                "draft": True,  # GitLab 14+ unterstützt Draft-MRs
            }

            mr = self.project.mergerequests.create(mr_data)

            # Labels hinzufügen
            try:
                mr.labels = ["bug", "automated-fix", "needs-review"]
                mr.save()
                logger.debug(f"Labels hinzugefügt zu MR !{mr.iid}")
            except Exception as e:
                logger.warning(f"Labels konnten nicht hinzugefügt werden: {e}")

            logger.info(f"GitLab Draft-MR erstellt: {mr.web_url}")

            return PRResult(
                success=True,
                url=mr.web_url,
                number=mr.iid,
                state=mr.state,
                draft=mr.draft,
                platform="gitlab",
                metadata={
                    "title": mr.title,
                    "created_at": mr.created_at,
                    "labels": ["bug", "automated-fix", "needs-review"],
                    "project_id": self.project_id,
                },
            )

        except Exception as e:
            logger.error(f"GitLab MR-Erstellung fehlgeschlagen: {e}")
            return PRResult(
                success=False,
                error=str(e),
                platform="gitlab",
                metadata={"bug_id": bug.get("bug_id", "unknown")},
            )

    # Alias für Basisklassen-Kompatibilität
    create_draft_pr = create_draft_mr

    def _generate_pr_body(self, bug: Dict[str, Any], fix_suggestions: List[str]) -> str:
        """
        Generiert MR-Beschreibung für GitLab.

        Args:
            bug: Bug-Informationen
            fix_suggestions: Fix-Vorschläge

        Returns:
            Formatierter Markdown-Text
        """
        # Gleiche Logik wie GitHub
        bug_type = bug.get("bug_type", "unknown")
        severity = bug.get("severity", "unknown")
        file_path = bug.get("file_path", "")
        line_start = bug.get("line_start", bug.get("line_number", "?"))
        description = bug.get("description", "No description")
        confidence = bug.get("confidence", 0)

        fix_lines = "\n".join(f"- {s}" for s in fix_suggestions)

        return f"""## 🤖 Automated Fix by GlitchHunter

**Bug Type:** {bug_type}  
**Severity:** {severity}  
**File:** `{file_path}` (Line {line_start})

### Description
{description}

### Fix Summary
{fix_lines}

### Confidence
{confidence * 100:.0f}%

---
*This MR was automatically generated by [GlitchHunter](https://github.com/glitchhunter/glitchhunter)*
"""


class PRCreatorFactory:
    """
    Factory für PR-Creator.

    Erstellt den passenden PR-Creator basierend auf der Plattform.

    Usage:
        creator = PRCreatorFactory.create_from_config(config)
    """

    @staticmethod
    def create_github(
        token: str,
        owner: str,
        repo_name: str,
        local_repo_path: Optional[str] = None,
        remote_url: Optional[str] = None,
    ) -> GitHubPRCreator:
        """
        Erstellt GitHubPRCreator.

        Args:
            token: GitHub Token
            owner: Repository Owner
            repo_name: Repository Name
            local_repo_path: Lokaler Pfad
            remote_url: Remote-URL

        Returns:
            GitHubPRCreator Instanz
        """
        return GitHubPRCreator(
            token=token,
            owner=owner,
            repo_name=repo_name,
            local_repo_path=local_repo_path,
            remote_url=remote_url,
        )

    @staticmethod
    def create_gitlab(
        url: str,
        token: str,
        project_id: int,
        local_repo_path: Optional[str] = None,
        remote_url: Optional[str] = None,
    ) -> GitLabMRCreator:
        """
        Erstellt GitLabMRCreator.

        Args:
            url: GitLab URL
            token: GitLab Token
            project_id: Projekt-ID
            local_repo_path: Lokaler Pfad
            remote_url: Remote-URL

        Returns:
            GitLabMRCreator Instanz
        """
        return GitLabMRCreator(
            url=url,
            token=token,
            project_id=project_id,
            local_repo_path=local_repo_path,
            remote_url=remote_url,
        )

    @staticmethod
    def create_from_config(config: Any) -> Optional[BasePRCreator]:
        """
        Erstellt PR-Creator aus Config-Objekt.

        Args:
            config: Config-Objekt mit escalation.level_4_draft_pr

        Returns:
            PR-Creator Instanz oder None wenn nicht enabled
        """
        import os

        # Prüfen ob enabled
        if not hasattr(config, "escalation") or not hasattr(config.escalation, "level_4_draft_pr"):
            logger.debug("PR-Erstellung nicht in Config konfiguriert")
            return None

        pr_config = config.escalation.level_4_draft_pr

        if not pr_config.enabled:
            logger.debug("PR-Erstellung ist deaktiviert")
            return None

        # GitHub Config
        if hasattr(pr_config, "github") and pr_config.github.token_env:
            token = os.getenv(pr_config.github.token_env)
            owner = os.getenv(pr_config.github.owner_env)
            repo = os.getenv(pr_config.github.repo_env)

            if not all([token, owner, repo]):
                logger.warning(
                    f"GitHub Config unvollständig. "
                    f"Token: {bool(token)}, Owner: {bool(owner)}, Repo: {bool(repo)}"
                )
                return None

            local_path = getattr(config.paths, "temp", None)
            remote_url = getattr(pr_config.github, "remote_url", None)

            logger.info(f"Erstelle GitHub PR-Creator für {owner}/{repo}")
            return GitHubPRCreator(
                token=token,
                owner=owner,
                repo_name=repo,
                local_repo_path=local_path,
                remote_url=remote_url,
            )

        # GitLab Config
        if hasattr(pr_config, "gitlab") and pr_config.gitlab.token_env:
            url = getattr(pr_config.gitlab, "url", "https://gitlab.com")
            token = os.getenv(pr_config.gitlab.token_env)
            project_id_str = os.getenv(pr_config.gitlab.project_id_env)

            if not all([token, project_id_str]):
                logger.warning(
                    f"GitLab Config unvollständig. "
                    f"Token: {bool(token)}, Project ID: {bool(project_id_str)}"
                )
                return None

            try:
                project_id = int(project_id_str)
            except ValueError:
                logger.error(f"GitLab Project ID ist keine gültige Zahl: {project_id_str}")
                return None

            local_path = getattr(config.paths, "temp", None)
            remote_url = getattr(pr_config.gitlab, "remote_url", None)

            logger.info(f"Erstelle GitLab MR-Creator für Projekt {project_id}")
            return GitLabMRCreator(
                url=url,
                token=token,
                project_id=project_id,
                local_repo_path=local_path,
                remote_url=remote_url,
            )

        logger.debug("Keine GitHub oder GitLab Config gefunden")
        return None
