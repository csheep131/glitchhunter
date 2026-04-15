"""
Tests für PR Creator (GitHub/GitLab Integration).

Mock-basierte Tests ohne echte API-Calls.
"""

import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

from escalation.pr_creator import (
    BasePRCreator,
    GitHubPRCreator,
    GitLabMRCreator,
    PRResult,
    PRCreatorFactory,
)


class TestPRResult(unittest.TestCase):
    """Tests für PRResult Dataclass."""

    def test_pr_result_success(self) -> None:
        """Test erfolgreiches PR-Ergebnis."""
        result = PRResult(
            success=True,
            url="https://github.com/owner/repo/pull/123",
            number=123,
            state="open",
            draft=True,
            platform="github",
        )

        self.assertTrue(result.success)
        self.assertEqual(result.number, 123)
        self.assertEqual(result.platform, "github")

    def test_pr_result_failure(self) -> None:
        """Test fehlgeschlagenes PR-Ergebnis."""
        result = PRResult(
            success=False,
            error="API Error",
            platform="github",
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error, "API Error")
        self.assertEqual(result.number, 0)

    def test_pr_result_to_dict(self) -> None:
        """Test Konvertierung zu Dict."""
        result = PRResult(
            success=True,
            url="https://example.com/pr/1",
            number=1,
            state="open",
            draft=True,
            platform="github",
            metadata={"key": "value"},
        )

        result_dict = result.to_dict()

        self.assertIsInstance(result_dict, dict)
        self.assertEqual(result_dict["success"], True)
        self.assertEqual(result_dict["url"], "https://example.com/pr/1")
        self.assertEqual(result_dict["metadata"]["key"], "value")


class TestGitHubPRCreator(unittest.TestCase):
    """Tests für GitHubPRCreator."""

    def setUp(self) -> None:
        """Setup für Tests."""
        self.token = "fake_github_token"
        self.owner = "test_owner"
        self.repo_name = "test_repo"
        self.bug: Dict[str, Any] = {
            "bug_id": "BUG-123",
            "bug_type": "NullPointer",
            "file_path": "src/main.py",
            "line_start": 42,
            "severity": "high",
            "description": "Null pointer exception in user service",
            "confidence": 0.85,
        }
        self.fix_suggestions = [
            "Add null check before accessing user object",
            "Initialize user with default value",
        ]
        self.patch_diff = """diff --git a/src/main.py b/src/main.py
index 1234567..abcdefg 100644
--- a/src/main.py
+++ b/src/main.py
@@ -40,6 +40,9 @@ def get_user_name(user):
     if user is None:
         return "Anonymous"
+    
+    if not user.name:
+        return "Unknown"
+
     return user.name
"""

    @patch("github.Github")
    def test_init(self, mock_github: MagicMock) -> None:
        """Test Initialisierung."""
        creator = GitHubPRCreator(
            token=self.token,
            owner=self.owner,
            repo_name=self.repo_name,
        )

        self.assertEqual(creator.token, self.token)
        self.assertEqual(creator.owner, self.owner)
        self.assertEqual(creator.repo_name, self.repo_name)
        mock_github.assert_called_once_with(self.token)

    @patch("github.Github")
    @patch("escalation.pr_creator.Repo")
    def test_create_draft_pr_success(
        self,
        mock_repo: MagicMock,
        mock_github: MagicMock,
    ) -> None:
        """Test erfolgreiche PR-Erstellung."""
        # Mock GitHub API
        mock_client = MagicMock()
        mock_github.return_value = mock_client
        mock_repo_obj = MagicMock()
        mock_client.get_repo.return_value = mock_repo_obj

        # Mock PR
        mock_pr = MagicMock()
        mock_pr.html_url = "https://github.com/owner/repo/pull/123"
        mock_pr.number = 123
        mock_pr.state = "open"
        mock_pr.draft = True
        mock_pr.created_at = MagicMock()
        mock_pr.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        mock_repo_obj.create_pull.return_value = mock_pr

        # Mock lokales Repo
        mock_local_repo = MagicMock()
        mock_repo.return_value = mock_local_repo
        mock_local_repo.__bool__.return_value = True

        creator = GitHubPRCreator(
            token=self.token,
            owner=self.owner,
            repo_name=self.repo_name,
            local_repo_path="/fake/path",
        )
        # Mock local_repo direkt setzen und _clone_or_open_repo patchen
        creator.local_repo = mock_local_repo
        
        # Patch _clone_or_open_repo um das echte Klonen zu überspringen
        with patch.object(creator, '_clone_or_open_repo', return_value=mock_local_repo):
            # Patch _create_branch, _apply_patch, _commit_and_push
            with patch.object(creator, '_create_branch'):
                with patch.object(creator, '_apply_patch', return_value=["src/main.py"]):
                    with patch.object(creator, '_commit_and_push'):
                        # Test
                        result = creator.create_draft_pr(
                            bug=self.bug,
                            fix_suggestions=self.fix_suggestions,
                            patch_diff=self.patch_diff,
                        )

                        # Assertions
                        self.assertTrue(result.success)
                        self.assertEqual(result.url, "https://github.com/owner/repo/pull/123")
                        self.assertEqual(result.number, 123)
                        self.assertEqual(result.platform, "github")
                        self.assertTrue(result.draft)

                        # Verify PR creation
                        mock_repo_obj.create_pull.assert_called_once()
                        call_args = mock_repo_obj.create_pull.call_args
                        self.assertTrue(call_args.kwargs["draft"])
                        self.assertIn("Fix:", call_args.kwargs["title"])

    @patch("github.Github")
    def test_create_draft_pr_no_repo(self, mock_github: MagicMock) -> None:
        """Test PR-Erstellung ohne Repository."""
        mock_client = MagicMock()
        mock_github.return_value = mock_client

        creator = GitHubPRCreator(
            token=self.token,
            owner=self.owner,
            repo_name=self.repo_name,
        )

        result = creator.create_draft_pr(
            bug=self.bug,
            fix_suggestions=self.fix_suggestions,
            patch_diff=self.patch_diff,
        )

        self.assertFalse(result.success)
        self.assertIn("local_repo_path oder remote_url", result.error)

    @patch("github.Github")
    def test_generate_branch_name(self, mock_github: MagicMock) -> None:
        """Test Branch-Namen-Generierung."""
        mock_client = MagicMock()
        mock_github.return_value = mock_client

        creator = GitHubPRCreator(
            token=self.token,
            owner=self.owner,
            repo_name=self.repo_name,
            local_repo_path="/fake/path",
        )

        branch_name = creator._generate_branch_name(self.bug)
        self.assertEqual(branch_name, "glitchhunter/fix-BUG-123")

    @patch("github.Github")
    def test_generate_pr_body(self, mock_github: MagicMock) -> None:
        """Test PR-Beschreibung-Generierung."""
        mock_client = MagicMock()
        mock_github.return_value = mock_client

        creator = GitHubPRCreator(
            token=self.token,
            owner=self.owner,
            repo_name=self.repo_name,
            local_repo_path="/fake/path",
        )

        body = creator._generate_pr_body(self.bug, self.fix_suggestions)

        self.assertIn("🤖 Automated Fix by GlitchHunter", body)
        self.assertIn("NullPointer", body)
        self.assertIn("src/main.py", body)
        self.assertIn("Add null check before accessing user object", body)
        self.assertIn("85%", body)


class TestGitLabMRCreator(unittest.TestCase):
    """Tests für GitLabMRCreator."""

    def setUp(self) -> None:
        """Setup für Tests."""
        self.url = "https://gitlab.com"
        self.token = "fake_gitlab_token"
        self.project_id = 12345
        self.bug: Dict[str, Any] = {
            "bug_id": "BUG-456",
            "bug_type": "MemoryLeak",
            "file_path": "src/service.py",
            "line_start": 100,
            "severity": "critical",
            "description": "Memory leak in event handler",
            "confidence": 0.92,
        }
        self.fix_suggestions = [
            "Add cleanup in finally block",
            "Use context manager for resources",
        ]
        self.patch_diff = """diff --git a/src/service.py b/src/service.py
index abc123..def456 100644
--- a/src/service.py
+++ b/src/service.py
@@ -98,6 +98,8 @@ def process_event(event):
     try:
         result = handle(event)
+        return result
     finally:
+        cleanup_resources()
"""

    @patch("gitlab.Gitlab")
    def test_init(self, mock_gitlab: MagicMock) -> None:
        """Test Initialisierung."""
        mock_client = MagicMock()
        mock_gitlab.return_value = mock_client
        mock_project = MagicMock()
        mock_client.projects.get.return_value = mock_project

        creator = GitLabMRCreator(
            url=self.url,
            token=self.token,
            project_id=self.project_id,
        )

        self.assertEqual(creator.url, self.url)
        self.assertEqual(creator.project_id, self.project_id)
        mock_gitlab.assert_called_once_with(self.url, private_token=self.token)

    @patch("gitlab.Gitlab")
    @patch("escalation.pr_creator.Repo")
    def test_create_draft_mr_success(
        self,
        mock_repo: MagicMock,
        mock_gitlab: MagicMock,
    ) -> None:
        """Test erfolgreiche MR-Erstellung."""
        # Mock GitLab API
        mock_client = MagicMock()
        mock_gitlab.return_value = mock_client
        mock_project = MagicMock()
        mock_client.projects.get.return_value = mock_project

        # Mock MR
        mock_mr = MagicMock()
        mock_mr.web_url = "https://gitlab.com/owner/repo/merge_requests/456"
        mock_mr.iid = 456
        mock_mr.state = "opened"
        mock_mr.draft = True
        mock_mr.created_at = "2024-01-01T00:00:00"
        mock_mr.title = "Fix: MemoryLeak in src/service.py"
        mock_project.mergerequests.create.return_value = mock_mr

        # Mock lokales Repo
        mock_local_repo = MagicMock()
        mock_repo.return_value = mock_local_repo
        mock_local_repo.__bool__.return_value = True

        creator = GitLabMRCreator(
            url=self.url,
            token=self.token,
            project_id=self.project_id,
            local_repo_path="/fake/path",
        )
        creator.local_repo = mock_local_repo

        # Patch Helper-Methoden
        with patch.object(creator, '_clone_or_open_repo', return_value=mock_local_repo):
            with patch.object(creator, '_create_branch'):
                with patch.object(creator, '_apply_patch', return_value=["src/service.py"]):
                    with patch.object(creator, '_commit_and_push'):
                        # Test
                        result = creator.create_draft_pr(
                            bug=self.bug,
                            fix_suggestions=self.fix_suggestions,
                            patch_diff=self.patch_diff,
                        )

                        # Assertions
                        self.assertTrue(result.success)
                        self.assertEqual(result.url, "https://gitlab.com/owner/repo/merge_requests/456")
                        self.assertEqual(result.number, 456)
                        self.assertEqual(result.platform, "gitlab")
                        self.assertTrue(result.draft)

                        # Verify MR creation
                        mock_project.mergerequests.create.assert_called_once()
                        call_args = mock_project.mergerequests.create.call_args
                        self.assertTrue(call_args[0][0]["draft"])
                        self.assertIn("Fix:", call_args[0][0]["title"])


class TestPRCreatorFactory(unittest.TestCase):
    """Tests für PRCreatorFactory."""

    def setUp(self) -> None:
        """Setup für Tests."""
        # Umgebungsvariablen setzen
        os.environ["GITHUB_TOKEN"] = "fake_gh_token"
        os.environ["REPO_OWNER"] = "test_owner"
        os.environ["REPO_NAME"] = "test_repo"
        os.environ["GITLAB_TOKEN"] = "fake_gl_token"
        os.environ["GITLAB_PROJECT_ID"] = "99999"

    def tearDown(self) -> None:
        """Cleanup nach Tests."""
        for key in [
            "GITHUB_TOKEN",
            "REPO_OWNER",
            "REPO_NAME",
            "GITLAB_TOKEN",
            "GITLAB_PROJECT_ID",
        ]:
            if key in os.environ:
                del os.environ[key]

    @patch("github.Github")
    def test_create_github(self, mock_github: MagicMock) -> None:
        """Test GitHub Creator Factory."""
        creator = PRCreatorFactory.create_github(
            token="token",
            owner="owner",
            repo_name="repo",
        )

        self.assertIsInstance(creator, GitHubPRCreator)
        self.assertEqual(creator.owner, "owner")

    @patch("gitlab.Gitlab")
    def test_create_gitlab(self, mock_gitlab: MagicMock) -> None:
        """Test GitLab Creator Factory."""
        mock_client = MagicMock()
        mock_gitlab.return_value = mock_client
        mock_project = MagicMock()
        mock_client.projects.get.return_value = mock_project

        creator = PRCreatorFactory.create_gitlab(
            url="https://gitlab.com",
            token="token",
            project_id=123,
        )

        self.assertIsInstance(creator, GitLabMRCreator)
        self.assertEqual(creator.project_id, 123)

    @patch("github.Github")
    def test_create_from_config_github(self, mock_github: MagicMock) -> None:
        """Test Factory mit GitHub Config."""
        # Mock Config
        mock_config = MagicMock()
        mock_config.escalation.level_4_draft_pr.enabled = True
        mock_config.escalation.level_4_draft_pr.github.token_env = "GITHUB_TOKEN"
        mock_config.escalation.level_4_draft_pr.github.owner_env = "REPO_OWNER"
        mock_config.escalation.level_4_draft_pr.github.repo_env = "REPO_NAME"
        mock_config.escalation.level_4_draft_pr.gitlab.token_env = None

        creator = PRCreatorFactory.create_from_config(mock_config)

        self.assertIsInstance(creator, GitHubPRCreator)

    @patch("gitlab.Gitlab")
    def test_create_from_config_gitlab(self, mock_gitlab: MagicMock) -> None:
        """Test Factory mit GitLab Config."""
        # Mock Config ohne GitHub, mit GitLab
        mock_config = MagicMock()
        mock_config.escalation.level_4_draft_pr.enabled = True
        mock_config.escalation.level_4_draft_pr.github.token_env = None
        mock_config.escalation.level_4_draft_pr.gitlab.token_env = "GITLAB_TOKEN"
        mock_config.escalation.level_4_draft_pr.gitlab.project_id_env = "GITLAB_PROJECT_ID"
        mock_config.escalation.level_4_draft_pr.gitlab.url = "https://gitlab.com"

        mock_client = MagicMock()
        mock_gitlab.return_value = mock_client
        mock_project = MagicMock()
        mock_client.projects.get.return_value = mock_project

        creator = PRCreatorFactory.create_from_config(mock_config)

        self.assertIsInstance(creator, GitLabMRCreator)

    def test_create_from_config_disabled(self) -> None:
        """Test Factory bei deaktivierter PR-Erstellung."""
        mock_config = MagicMock()
        mock_config.escalation.level_4_draft_pr.enabled = False

        creator = PRCreatorFactory.create_from_config(mock_config)

        self.assertIsNone(creator)

    def test_create_from_config_missing_env(self) -> None:
        """Test Factory bei fehlenden Umgebungsvariablen."""
        # Config mit GitHub aber Token fehlt
        del os.environ["GITHUB_TOKEN"]

        mock_config = MagicMock()
        mock_config.escalation.level_4_draft_pr.enabled = True
        mock_config.escalation.level_4_draft_pr.github.token_env = "GITHUB_TOKEN"
        mock_config.escalation.level_4_draft_pr.github.owner_env = "REPO_OWNER"
        mock_config.escalation.level_4_draft_pr.github.repo_env = "REPO_NAME"

        creator = PRCreatorFactory.create_from_config(mock_config)

        self.assertIsNone(creator)


class TestBasePRCreatorHelpers(unittest.TestCase):
    """Tests für Helper-Methoden in BasePRCreator."""

    def test_generate_branch_name(self) -> None:
        """Test Branch-Namen-Generierung in Basisklasse."""
        # Verwende GitHubPRCreator da BasePRCreator abstrakt ist
        with patch("github.Github"):
            creator = GitHubPRCreator(
                token="token",
                owner="owner",
                repo_name="repo",
                local_repo_path="/fake/path",
            )

            bug = {"bug_id": "TEST-12345"}
            branch_name = creator._generate_branch_name(bug)

            self.assertEqual(branch_name, "glitchhunter/fix-TEST-123")

    def test_generate_branch_name_short_id(self) -> None:
        """Test Branch-Namen bei kurzer Bug-ID."""
        with patch("github.Github"):
            creator = GitHubPRCreator(
                token="token",
                owner="owner",
                repo_name="repo",
                local_repo_path="/fake/path",
            )

            bug = {"bug_id": "T-1"}
            branch_name = creator._generate_branch_name(bug)

            self.assertEqual(branch_name, "glitchhunter/fix-T-1")

    @patch("escalation.pr_creator.Repo")
    def test_clone_or_open_repo_existing(self, mock_repo: MagicMock) -> None:
        """Test Öffnen existierenden Repos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("github.Github"):
                creator = GitHubPRCreator(
                    token="token",
                    owner="owner",
                    repo_name="repo",
                    local_repo_path=tmpdir,
                )

                mock_repo_instance = MagicMock()
                mock_repo.return_value = mock_repo_instance

                result = creator._clone_or_open_repo()

                mock_repo.assert_called_once_with(tmpdir)
                self.assertEqual(creator.local_repo, mock_repo_instance)

    def test_clone_or_open_repo_no_path(self) -> None:
        """Test Fehler bei fehlendem Pfad."""
        with patch("github.Github"):
            creator = GitHubPRCreator(
                token="token",
                owner="owner",
                repo_name="repo",
            )

            with self.assertRaises(ValueError) as context:
                creator._clone_or_open_repo()

            self.assertIn("local_repo_path oder remote_url", str(context.exception))


class TestHumanReportGeneratorIntegration(unittest.TestCase):
    """Integrationstests für HumanReportGenerator mit PR-Creator."""

    @patch("github.Github")
    def test_human_report_generator_with_pr_creator(self, mock_github: MagicMock) -> None:
        """Test HumanReportGenerator mit aktiviertem PR-Creator."""
        from escalation.human_report_generator import HumanReportGenerator

        # Mock Config
        mock_config = MagicMock()
        mock_config.escalation.level_4_draft_pr.enabled = True
        mock_config.escalation.level_4_draft_pr.github.token_env = "GITHUB_TOKEN"
        mock_config.escalation.level_4_draft_pr.github.owner_env = "REPO_OWNER"
        mock_config.escalation.level_4_draft_pr.github.repo_env = "REPO_NAME"

        # Umgebungsvariablen setzen
        os.environ["GITHUB_TOKEN"] = "fake_token"
        os.environ["REPO_OWNER"] = "owner"
        os.environ["REPO_NAME"] = "repo"

        # Mock GitHub API
        mock_client = MagicMock()
        mock_github.return_value = mock_client
        mock_repo = MagicMock()
        mock_client.get_repo.return_value = mock_repo

        generator = HumanReportGenerator(
            config=mock_config,
            local_repo_path="/fake/path",
        )

        self.assertIsNotNone(generator.pr_creator)
        self.assertIsInstance(generator.pr_creator, GitHubPRCreator)

        # Cleanup
        del os.environ["GITHUB_TOKEN"]
        del os.environ["REPO_OWNER"]
        del os.environ["REPO_NAME"]

    def test_generate_draft_pr_no_creator(self) -> None:
        """Test generate_draft_pr ohne PR-Creator."""
        from escalation.human_report_generator import HumanReportGenerator

        generator = HumanReportGenerator()

        bug = {
            "bug_id": "BUG-789",
            "bug_type": "TypeError",
            "file_path": "src/app.py",
            "patch_diff": "diff content",
        }

        result = generator.generate_draft_pr(
            bug=bug,
            fix_suggestions=["Fix it"],
        )

        self.assertFalse(result["success"])
        self.assertIn("not enabled", result["error"])


if __name__ == "__main__":
    unittest.main()
