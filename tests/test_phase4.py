"""
Unit Tests für Phase 4: Finalizer + Escalation Komponenten.

Tests für:
- RuleLearner
- PatchMerger
- ReportGenerator
- ContextExplosion
- BugDecomposer
- EnsembleCoordinator
- HumanReportGenerator
"""

import pytest
import sys
import tempfile
from pathlib import Path
from datetime import datetime

# Source-Path hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fixing.rule_learner import RuleLearner, CodePattern, SemgrepRule
from fixing.patch_merger import PatchMerger, GitCommit, MergeResult
from fixing.report_generator import ReportGenerator, BugSummary, FixDetail, ReportBundle
from escalation.context_explosion import ContextExplosion, ExplodedContext
from escalation.bug_decomposer import BugDecomposer, DecomposedBug
from escalation.ensemble_coordinator import EnsembleCoordinator, ModelResponse
from escalation.human_report_generator import HumanReportGenerator, HumanReport


class TestRuleLearner:
    """Tests für RuleLearner."""

    @pytest.fixture
    def learner(self):
        """Erstellt RuleLearner-Instanz."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield RuleLearner(output_dir=tmpdir)

    def test_pattern_extraction(self, learner):
        """Testet Pattern-Extraktion."""
        pattern = CodePattern(
            pattern_type="fix",
            language="python",
            pattern="def FUNC(...): pass",
            message="Test pattern",
        )
        
        assert pattern.pattern_type == "fix"
        assert pattern.to_dict()["language"] == "python"

    def test_semgrep_rule_generation(self, learner):
        """Testet Semgrep-Regel-Generierung."""
        pattern = CodePattern(
            pattern_type="vulnerability",
            language="python",
            pattern="eval(...)",
            message="Dangerous eval usage",
            severity="high",
        )
        
        semgrep_pattern = learner._convert_to_semgrep_pattern(pattern.pattern)
        assert "$FUNC" in semgrep_pattern or "..." in semgrep_pattern

    def test_language_detection(self, learner):
        """Testet Sprachenerkennung."""
        assert learner._detect_language("test.py") == "python"
        assert learner._detect_language("test.js") == "javascript"
        assert learner._detect_language("test.rs") == "rust"

    def test_severity_inference(self, learner):
        """Testet Schweregrad-Ableitung."""
        assert learner._infer_severity("sql-injection") == "critical"
        assert learner._infer_severity("high-priority-bug") == "high"
        assert learner._infer_severity("medium-warning") == "medium"

    def test_learn_from_patches(self, learner):
        """Testet Lernen aus Patches."""
        patches = [
            {
                "patch_diff": "+ fixed_code\n- old_code",
                "file_path": "test.py",
                "bug_type": "security-bug",
                "explanation": "Fixed security issue",
            }
        ]
        
        result = learner.learn_from_patches(patches)
        
        assert result.patterns is not None
        assert result.learned_at is not None


class TestPatchMerger:
    """Tests für PatchMerger."""

    @pytest.fixture
    def merger(self):
        """Erstellt PatchMerger-Instanz."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initiales Git-Repo erstellen
            import subprocess
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
            
            yield PatchMerger(tmpdir)

    def test_git_commit_creation(self):
        """Testet GitCommit Erstellung."""
        commit = GitCommit(
            hash="abc123",
            message="Test commit",
            files_changed=["file1.py", "file2.py"],
            branch="main",
            tags=["glitchhunter/bug-1"],
        )
        
        assert commit.hash == "abc123"
        assert len(commit.files_changed) == 2
        assert "glitchhunter/bug-1" in commit.tags

    def test_merge_result_serialization(self):
        """Testet MergeResult Serialisierung."""
        commit = GitCommit(hash="abc123", message="Test")
        result = MergeResult(
            success=True,
            commit=commit,
            merged_patches=2,
        )
        
        result_dict = result.to_dict()
        assert result_dict["success"] is True
        assert result_dict["merged_patches"] == 2

    def test_commit_message_generation(self, merger):
        """Testet Commit-Message-Generierung."""
        patches = [
            {
                "bug_id": "BUG-001",
                "bug_type": "security",
                "file_path": "src/auth.py",
                "description": "Fixed SQL injection",
            }
        ]
        
        message = merger._generate_commit_message(patches)
        
        assert "GlitchHunter" in message
        assert "BUG-001" in message
        assert "auth.py" in message


class TestReportGenerator:
    """Tests für ReportGenerator."""

    @pytest.fixture
    def generator(self):
        """Erstellt ReportGenerator-Instanz."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield ReportGenerator(output_dir=tmpdir)

    def test_bug_summary_creation(self):
        """Testet BugSummary Erstellung."""
        bug = BugSummary(
            bug_id="BUG-001",
            bug_type="security",
            description="SQL injection vulnerability",
            severity="critical",
            file_path="src/auth.py",
            line_number=42,
            confidence=0.95,
        )
        
        assert bug.bug_id == "BUG-001"
        assert bug.to_dict()["severity"] == "critical"

    def test_fix_detail_creation(self):
        """Testet FixDetail Erstellung."""
        fix = FixDetail(
            bug_id="BUG-001",
            patch_diff="+ sanitized\n- raw",
            explanation="Added input sanitization",
            files_changed=["src/auth.py"],
            lines_changed=2,
            verification_confidence=0.98,
        )
        
        assert fix.bug_id == "BUG-001"
        assert fix.verification_confidence == 0.98

    def test_json_report_generation(self, generator):
        """Testet JSON-Report-Generierung."""
        bugs = [
            BugSummary(
                bug_id="BUG-001",
                bug_type="security",
                description="Test bug",
                severity="high",
                file_path="test.py",
                line_number=10,
            )
        ]
        fixes = []
        
        report = generator._generate_json_report(bugs, fixes, {})
        
        assert "summary" in report
        assert report["summary"]["total_bugs"] == 1

    def test_markdown_report_generation(self, generator):
        """Testet Markdown-Report-Generierung."""
        bugs = [
            BugSummary(
                bug_id="BUG-001",
                bug_type="security",
                description="Test bug",
                severity="high",
                file_path="test.py",
                line_number=10,
            )
        ]
        fixes = []
        
        md_report = generator._generate_markdown_report(bugs, fixes, {})
        
        assert "# GlitchHunter Analysis Report" in md_report
        assert "BUG-001" in md_report

    def test_escalation_report_generation(self, generator):
        """Testet Eskalations-Report-Generierung."""
        bugs = [
            BugSummary(
                bug_id="BUG-001",
                bug_type="complex-bug",
                description="Complex issue",
                severity="high",
                file_path="test.py",
                line_number=10,
                status="escalated",
            )
        ]
        
        report = generator.generate_escalation_report(
            bugs=bugs,
            escalation_level=4,
            attempted_fixes=["Fix attempt 1", "Fix attempt 2"],
            evidence=[{"type": "test", "content": "Evidence"}],
            recommendation="Manual review required",
        )
        
        assert "Escalation Report" in report
        assert "Level 4" in report
        assert "Manual review" in report


class TestContextExplosion:
    """Tests für ContextExplosion."""

    @pytest.fixture
    def explosion(self):
        """Erstellt ContextExplosion-Instanz."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield ContextExplosion(tmpdir, use_repomix=False, use_git_blame=False)

    def test_exploded_context_creation(self):
        """Testet ExplodedContext Erstellung."""
        context = ExplodedContext(
            original_context="Original code",
            expanded_context="Expanded context",
            total_tokens=160000,
        )
        
        assert context.total_tokens == 160000
        assert context.to_dict()["total_tokens"] == 160000

    def test_token_estimation(self, explosion):
        """Testet Token-Schätzung."""
        text = "A" * 4000  # ~1000 Tokens
        tokens = explosion._estimate_tokens(text)
        
        assert tokens == 1000  # 4000 / 4 = 1000


class TestBugDecomposer:
    """Tests für BugDecomposer."""

    @pytest.fixture
    def decomposer(self):
        """Erstellt BugDecomposer-Instanz."""
        return BugDecomposer()

    def test_decomposed_bug_creation(self):
        """Testet DecomposedBug Erstellung."""
        bug = DecomposedBug(
            sub_bug_id="BUG-001.1",
            description="Root cause analysis",
            priority="high",
            parent_bug_id="BUG-001",
            confidence=0.7,
        )
        
        assert bug.sub_bug_id == "BUG-001.1"
        assert bug.priority == "high"

    def test_causal_decomposition(self, decomposer):
        """Testet kausale Zerlegung."""
        bug = {
            "bug_id": "BUG-001",
            "bug_type": "complex-bug",
            "file_path": "test.py",
        }
        
        result = decomposer.decompose(bug, strategy="causal")
        
        assert result.total_sub_bugs >= 1
        assert result.total_sub_bugs <= 4  # MAX_SUB_BUGS
        assert result.decomposition_strategy == "causal"

    def test_component_decomposition(self, decomposer):
        """Testet komponentenbasierte Zerlegung."""
        bug = {
            "bug_id": "BUG-001",
            "bug_type": "api-bug",
            "file_path": "src/api.py",
        }
        
        result = decomposer.decompose(bug, strategy="component")
        
        assert result.total_sub_bugs >= 1
        assert any("input" in sb.description.lower() for sb in result.sub_bugs)

    def test_sub_bug_prioritization(self, decomposer):
        """Testet Sub-Bug-Priorisierung."""
        sub_bugs = [
            DecomposedBug(sub_bug_id="1", description="Low priority", priority="low"),
            DecomposedBug(sub_bug_id="2", description="High priority", priority="high"),
            DecomposedBug(sub_bug_id="3", description="Medium priority", priority="medium"),
        ]
        
        prioritized = decomposer.prioritize_sub_bugs(sub_bugs)
        
        assert prioritized[0].priority == "high"
        assert prioritized[-1].priority == "low"


class TestEnsembleCoordinator:
    """Tests für EnsembleCoordinator."""

    @pytest.fixture
    def coordinator(self):
        """Erstellt EnsembleCoordinator-Instanz."""
        return EnsembleCoordinator()

    def test_model_response_creation(self):
        """Testet ModelResponse Erstellung."""
        response = ModelResponse(
            model_id="analyzer_1",
            hypothesis="Root cause is X",
            confidence=0.8,
            reasoning="Because...",
        )
        
        assert response.model_id == "analyzer_1"
        assert response.confidence == 0.8

    def test_voting(self, coordinator):
        """Testet Voting."""
        responses = [
            ModelResponse(model_id="1", hypothesis="H1", confidence=0.8),
            ModelResponse(model_id="2", hypothesis="H1", confidence=0.7),
            ModelResponse(model_id="3", hypothesis="H2", confidence=0.6),
        ]
        
        votes = coordinator._perform_voting(responses)
        
        assert votes["H1"] == 2
        assert votes["H2"] == 1

    def test_agreement_calculation(self, coordinator):
        """Testet Agreement-Berechnung."""
        votes_unanimous = {"H1": 3}
        votes_majority = {"H1": 2, "H2": 1}
        votes_plurality = {"H1": 1, "H2": 1, "H3": 1}
        
        assert coordinator._calculate_agreement(votes_unanimous, 3) == "unanimous"
        assert coordinator._calculate_agreement(votes_majority, 3) == "majority"
        assert coordinator._calculate_agreement(votes_plurality, 3) == "none"

    def test_ensemble_result(self, coordinator):
        """Testet EnsembleResult."""
        bug = {"bug_id": "BUG-001", "bug_type": "test"}
        
        result = coordinator.run_ensemble(bug)
        
        assert result.total_models == 3
        assert result.winning_hypothesis != ""
        assert result.agreement_level in ["unanimous", "majority", "plurality", "none"]


class TestHumanReportGenerator:
    """Tests für HumanReportGenerator."""

    @pytest.fixture
    def generator(self):
        """Erstellt HumanReportGenerator-Instanz."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield HumanReportGenerator(output_dir=tmpdir)

    def test_human_report_creation(self):
        """Testet HumanReport Erstellung."""
        report = HumanReport(
            title="Test Escalation",
            summary="Test summary",
            bug_description="Test bug",
            recommendation="Manual review",
        )
        
        assert report.title == "Test Escalation"
        assert report.recommendation == "Manual review"

    def test_report_generation(self, generator):
        """Testet Report-Generierung."""
        bug = {
            "bug_id": "BUG-001",
            "bug_type": "complex-bug",
            "description": "Complex issue",
            "severity": "high",
            "file_path": "test.py",
            "line_number": 42,
        }
        
        attempted_fixes = [
            {"description": "Fix 1", "result": "failed", "reason": "Tests failed"},
            {"description": "Fix 2", "result": "failed", "reason": "Gate 2 failed"},
        ]
        
        report = generator.generate(bug, attempted_fixes, [], escalation_level=4)
        
        assert "BUG-001" in report.title
        assert "Escalation" in report.title
        assert report.severity == "high"

    def test_draft_pr_generation(self, generator):
        """Testet Draft-PR-Generierung."""
        bug = {
            "bug_id": "BUG-001",
            "bug_type": "security",
            "file_path": "src/auth.py",
            "description": "SQL injection",
        }
        
        fix_suggestions = [
            "Use parameterized queries",
            "Add input validation",
        ]
        
        pr = generator.generate_draft_pr(bug, fix_suggestions)
        
        assert "Fix:" in pr["title"]
        assert "auth.py" in pr["title"]
        assert pr["draft"] is True
        assert "needs-review" in pr["labels"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
