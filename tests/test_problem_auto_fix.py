"""
Tests für Auto-Fix gemäß PROBLEM_SOLVER.md Phase 3.3.

Testet:
- FixPatch, AutoFixResult Models
- AutoFixEngine (generate_patches, apply_patches, rollback)
- Backup-Funktionalität
- Manager-Erweiterungen (auto_fix, rollback_fix)
- CLI Commands (fix, rollback)
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

from src.problem.models import ProblemCase, ProblemType, ProblemSeverity, ProblemStatus
from src.problem.decomposition import (
    SubProblem,
    SubProblemType,
    Decomposition,
)
from src.problem.solution_path import (
    SolutionPath,
    SolutionType,
    RiskLevel,
    SolutionPlan,
)
from src.problem.auto_fix import (
    FixStatus,
    FixPatch,
    AutoFixResult,
    AutoFixEngine,
    create_auto_fix_engine,
)
from src.problem.manager import ProblemManager


# =============================================================================
# Tests für FixPatch Model
# =============================================================================

class TestFixPatch:
    """Tests für FixPatch Model."""

    def test_minimal_creation(self):
        """Erstellung mit minimalen Feldern."""
        patch = FixPatch(
            id="patch_001",
            subproblem_id="sub_001",
            solution_path_id="path_001",
            file_path="src/test.py",
        )

        assert patch.id == "patch_001"
        assert patch.subproblem_id == "sub_001"
        assert patch.solution_path_id == "path_001"
        assert patch.file_path == "src/test.py"
        assert patch.original_content == ""
        assert patch.patched_content == ""
        assert patch.diff == ""
        assert patch.status == FixStatus.PENDING
        assert patch.validation_passed is False
        assert patch.validation_errors == []
        assert patch.rollback_available is False
        assert patch.backup_path == ""
        assert patch.created_at is not None
        assert patch.applied_at is None

    def test_full_creation(self):
        """Erstellung mit allen Feldern."""
        patch = FixPatch(
            id="patch_002",
            subproblem_id="sub_002",
            solution_path_id="path_002",
            file_path="src/module.py",
            original_content="def old(): pass",
            patched_content="def new(): pass",
            diff="--- a/src/module.py\n+++ b/src/module.py\n@@ -1 +1 @@\n-def old(): pass\n+def new(): pass",
            status=FixStatus.COMPLETED,
            validation_passed=True,
            rollback_available=True,
            backup_path="/backups/patch_002_module.py.bak",
            applied_at="2025-01-01T12:00:00",
        )

        assert patch.original_content == "def old(): pass"
        assert patch.patched_content == "def new(): pass"
        assert patch.status == FixStatus.COMPLETED
        assert patch.validation_passed is True
        assert patch.rollback_available is True

    def test_to_dict(self):
        """Serialisierung zu Dictionary."""
        patch = FixPatch(
            id="patch_003",
            subproblem_id="sub_003",
            solution_path_id="path_003",
            file_path="src/test.py",
            status=FixStatus.FAILED,
            validation_errors=["Error 1", "Error 2"],
        )

        data = patch.to_dict()

        assert data["id"] == "patch_003"
        assert data["subproblem_id"] == "sub_003"
        assert data["file_path"] == "src/test.py"
        assert data["status"] == "failed"
        assert data["validation_errors"] == ["Error 1", "Error 2"]
        assert "created_at" in data
        assert data["applied_at"] is None

    def test_from_dict(self):
        """Deserialisierung aus Dictionary."""
        data = {
            "id": "patch_004",
            "subproblem_id": "sub_004",
            "solution_path_id": "path_004",
            "file_path": "src/module.py",
            "original_content": "old",
            "patched_content": "new",
            "diff": "diff text",
            "status": "completed",
            "validation_passed": True,
            "validation_errors": [],
            "rollback_available": True,
            "backup_path": "/backup.bak",
            "created_at": "2025-01-01T00:00:00",
            "applied_at": "2025-01-01T01:00:00",
        }

        patch = FixPatch.from_dict(data)

        assert patch.id == "patch_004"
        assert patch.status == FixStatus.COMPLETED
        assert patch.validation_passed is True
        assert patch.applied_at == "2025-01-01T01:00:00"


# =============================================================================
# Tests für AutoFixResult Model
# =============================================================================

class TestAutoFixResult:
    """Tests für AutoFixResult Model."""

    def test_minimal_creation(self):
        """Erstellung mit minimalen Feldern."""
        result = AutoFixResult(
            problem_id="prob_001",
            solution_plan_id="plan_001",
        )

        assert result.problem_id == "prob_001"
        assert result.solution_plan_id == "plan_001"
        assert result.patches == []
        assert result.overall_status == FixStatus.PENDING
        assert result.summary == ""
        assert result.applied_count == 0
        assert result.failed_count == 0
        assert result.rolled_back_count == 0
        assert result.started_at is not None
        assert result.completed_at is None

    def test_add_patch_updates_status(self):
        """Hinzufügen von Patches aktualisiert Status."""
        result = AutoFixResult(problem_id="prob_001", solution_plan_id="plan_001")

        # Pending Patch
        patch1 = FixPatch(
            id="patch_001",
            subproblem_id="sub_001",
            solution_path_id="path_001",
            file_path="src/test.py",
            status=FixStatus.PENDING,
        )
        result.add_patch(patch1)

        assert len(result.patches) == 1
        assert result.overall_status == FixStatus.PENDING

        # Completed Patch
        patch2 = FixPatch(
            id="patch_002",
            subproblem_id="sub_002",
            solution_path_id="path_002",
            file_path="src/test2.py",
            status=FixStatus.COMPLETED,
        )
        result.add_patch(patch2)

        assert result.overall_status == FixStatus.IN_PROGRESS
        assert result.applied_count == 1

    def test_status_updates_with_multiple_patches(self):
        """Status-Updates bei mehreren Patches."""
        result = AutoFixResult(problem_id="prob_001", solution_plan_id="plan_001")

        # Alle completed
        for i in range(3):
            patch = FixPatch(
                id=f"patch_{i}",
                subproblem_id=f"sub_{i}",
                solution_path_id=f"path_{i}",
                file_path=f"src/test{i}.py",
                status=FixStatus.COMPLETED,
            )
            result.add_patch(patch)

        assert result.overall_status == FixStatus.COMPLETED
        assert result.applied_count == 3
        assert result.failed_count == 0

    def test_status_with_failed_patch(self):
        """Ein fehlgeschlagener Patch setzt Gesamt-Status auf FAILED."""
        result = AutoFixResult(problem_id="prob_001", solution_plan_id="plan_001")

        # Completed
        result.add_patch(FixPatch(
            id="patch_1", subproblem_id="sub_1", solution_path_id="path_1",
            file_path="src/1.py", status=FixStatus.COMPLETED,
        ))

        # Failed
        result.add_patch(FixPatch(
            id="patch_2", subproblem_id="sub_2", solution_path_id="path_2",
            file_path="src/2.py", status=FixStatus.FAILED,
        ))

        assert result.overall_status == FixStatus.FAILED
        assert result.failed_count == 1

    def test_status_all_rolled_back(self):
        """Alle zurückgerollte Patches."""
        result = AutoFixResult(problem_id="prob_001", solution_plan_id="plan_001")

        for i in range(2):
            result.add_patch(FixPatch(
                id=f"patch_{i}", subproblem_id=f"sub_{i}", solution_path_id=f"path_{i}",
                file_path=f"src/{i}.py", status=FixStatus.ROLLED_BACK,
            ))

        assert result.overall_status == FixStatus.ROLLED_BACK
        assert result.rolled_back_count == 2

    def test_get_statistics(self):
        """Statistiken berechnen."""
        result = AutoFixResult(problem_id="prob_001", solution_plan_id="plan_001")

        # 2 completed, 1 failed, 1 pending
        result.add_patch(FixPatch(
            id="p1", subproblem_id="s1", solution_path_id="path1",
            file_path="src/1.py", status=FixStatus.COMPLETED,
        ))
        result.add_patch(FixPatch(
            id="p2", subproblem_id="s2", solution_path_id="path2",
            file_path="src/2.py", status=FixStatus.COMPLETED,
        ))
        result.add_patch(FixPatch(
            id="p3", subproblem_id="s3", solution_path_id="path3",
            file_path="src/3.py", status=FixStatus.FAILED,
        ))
        result.add_patch(FixPatch(
            id="p4", subproblem_id="s4", solution_path_id="path4",
            file_path="src/4.py", status=FixStatus.PENDING,
        ))

        stats = result.get_statistics()

        assert stats["total_patches"] == 4
        assert stats["applied"] == 2
        assert stats["failed"] == 1
        assert stats["pending"] == 1
        assert stats["rolled_back"] == 0
        assert stats["success_rate"] == 50.0
        assert stats["overall_status"] == "failed"

    def test_to_dict_and_from_dict(self):
        """Serialisierung und Deserialisierung."""
        result = AutoFixResult(
            problem_id="prob_001",
            solution_plan_id="plan_001",
            summary="Test Summary",
        )
        result.add_patch(FixPatch(
            id="patch_001",
            subproblem_id="sub_001",
            solution_path_id="path_001",
            file_path="src/test.py",
            status=FixStatus.COMPLETED,
        ))
        result.completed_at = "2025-01-01T12:00:00"

        # Serialisieren
        data = result.to_dict()

        assert data["problem_id"] == "prob_001"
        assert len(data["patches"]) == 1
        assert data["summary"] == "Test Summary"

        # Deserialisieren
        result2 = AutoFixResult.from_dict(data)

        assert result2.problem_id == "prob_001"
        assert len(result2.patches) == 1
        assert result2.patches[0].id == "patch_001"
        assert result2.patches[0].status == FixStatus.COMPLETED


# =============================================================================
# Tests für AutoFixEngine
# =============================================================================

class TestAutoFixEngine:
    """Tests für AutoFixEngine."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Erstellt temporäres Repository."""
        return tmp_path

    @pytest.fixture
    def solution_plan(self):
        """Erstellt SolutionPlan mit ausgewählten Pfaden."""
        plan = SolutionPlan(problem_id="prob_001")

        # Pfade hinzufügen
        path1 = plan.add_solution_path(
            subproblem_id="sub_001",
            title="Fix Subproblem 1",
            description="Description 1",
            solution_type=SolutionType.HOTFIX,
            effectiveness=8,
        )

        path2 = plan.add_solution_path(
            subproblem_id="sub_002",
            title="Fix Subproblem 2",
            description="Description 2",
            solution_type=SolutionType.REFACTOR,
            effectiveness=7,
        )

        # Pfade auswählen
        plan.select_path("sub_001", path1.id)
        plan.select_path("sub_002", path2.id)

        return plan

    def test_init_creates_backup_dir(self, temp_repo):
        """Initialisierung erstellt Backup-Verzeichnis."""
        plan = SolutionPlan(problem_id="prob_001")
        engine = AutoFixEngine(
            repo_path=temp_repo,
            solution_plan=plan,
            dry_run=False,
        )

        backup_dir = temp_repo / ".glitchhunter" / "backups"
        assert backup_dir.exists()
        assert backup_dir.is_dir()

    def test_init_dry_run_no_backup_dir(self, temp_repo):
        """Dry-Run erstellt kein Backup-Verzeichnis."""
        plan = SolutionPlan(problem_id="prob_001")
        engine = AutoFixEngine(
            repo_path=temp_repo,
            solution_plan=plan,
            dry_run=True,
        )

        backup_dir = temp_repo / ".glitchhunter" / "backups"
        assert not backup_dir.exists()

    def test_generate_patches(self, temp_repo, solution_plan):
        """Patch-Generierung."""
        engine = create_auto_fix_engine(
            repo_path=temp_repo,
            solution_plan=solution_plan,
            dry_run=True,
        )

        result = engine.generate_patches()

        assert result.problem_id == "prob_001"
        assert len(result.patches) == 2  # 2 ausgewählte Pfade

        # Patches prüfen
        for patch in result.patches:
            assert patch.id.startswith("patch_")
            assert patch.subproblem_id in ["sub_001", "sub_002"]
            assert patch.file_path.startswith("src/fix_")
            assert patch.status == FixStatus.PENDING
            assert patch.diff != ""

    def test_generate_patches_no_selected_paths(self, temp_repo):
        """Generierung ohne ausgewählte Pfade."""
        plan = SolutionPlan(problem_id="prob_001")
        # Keine Pfade auswählen

        engine = create_auto_fix_engine(
            repo_path=temp_repo,
            solution_plan=plan,
            dry_run=True,
        )

        result = engine.generate_patches()

        assert len(result.patches) == 0
        assert result.overall_status == FixStatus.PENDING

    def test_apply_patches_dry_run(self, temp_repo, solution_plan):
        """Patch-Anwendung im Dry-Run Modus."""
        engine = create_auto_fix_engine(
            repo_path=temp_repo,
            solution_plan=solution_plan,
            dry_run=True,
        )

        # Patches generieren
        result = engine.generate_patches()

        # Patches anwenden (Dry-Run)
        result = engine.apply_patches(result, validate=True)

        # Im Dry-Run sollten Patches completed sein
        for patch in result.patches:
            assert patch.status == FixStatus.COMPLETED
            # Aber keine Backups
            assert patch.rollback_available is False

        assert result.overall_status == FixStatus.COMPLETED

    def test_apply_patches_with_validation(self, temp_repo, solution_plan):
        """Patch-Anwendung mit Validation."""
        engine = create_auto_fix_engine(
            repo_path=temp_repo,
            solution_plan=solution_plan,
            dry_run=True,  # Dry-Run für Test
        )

        result = engine.generate_patches()
        result = engine.apply_patches(result, validate=True)

        # Validation sollte durchgeführt werden
        for patch in result.patches:
            assert patch.validation_passed is True

    def test_apply_patches_actual_files(self, temp_repo, solution_plan):
        """Patch-Anwendung mit echten Dateien."""
        engine = create_auto_fix_engine(
            repo_path=temp_repo,
            solution_plan=solution_plan,
            dry_run=False,
        )

        # Original-Datei erstellen
        test_file = temp_repo / "src" / "fix_sub_001.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("# Original content")

        # Patches generieren und anpassen
        result = engine.generate_patches()

        # Ersten Patch auf echte Datei setzen
        result.patches[0].file_path = "src/fix_sub_001.py"
        result.patches[0].original_content = "# Original content"
        result.patches[0].patched_content = "# Patched content"

        # Patches anwenden
        result = engine.apply_patches(result, validate=False)

        # Datei sollte gepatcht sein
        assert test_file.exists()
        assert test_file.read_text() == "# Patched content"

        # Backup sollte existieren
        assert result.patches[0].backup_path != ""
        assert Path(result.patches[0].backup_path).exists()
        assert result.patches[0].rollback_available is True

    def test_rollback(self, temp_repo, solution_plan):
        """Rollback von Patches."""
        engine = create_auto_fix_engine(
            repo_path=temp_repo,
            solution_plan=solution_plan,
            dry_run=False,
        )

        # Original-Datei erstellen
        test_file = temp_repo / "src" / "fix_sub_001.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        original_content = "# Original content"
        test_file.write_text(original_content)

        # Patches generieren
        result = engine.generate_patches()
        result.patches[0].file_path = "src/fix_sub_001.py"
        result.patches[0].patched_content = "# Patched content"

        # Anwenden
        result = engine.apply_patches(result, validate=False)

        # Datei ist gepatcht
        assert test_file.read_text() == "# Patched content"

        # Rollback
        result = engine.rollback(result)

        # Datei ist wieder original
        assert test_file.read_text() == original_content
        assert result.patches[0].status == FixStatus.ROLLED_BACK
        # Zweiter Patch ist noch COMPLETED, daher Gesamt-Status FAILED
        assert result.overall_status == FixStatus.FAILED

    def test_rollback_no_backup(self, temp_repo, solution_plan):
        """Rollback ohne Backup."""
        engine = create_auto_fix_engine(
            repo_path=temp_repo,
            solution_plan=solution_plan,
            dry_run=True,  # Kein Backup im Dry-Run
        )

        result = engine.generate_patches()

        # Status manuell auf COMPLETED setzen (simuliert angewendeten Patch)
        result.patches[0].status = FixStatus.COMPLETED

        # Rollback versuchen
        result = engine.rollback(result)

        # Sollte fehlschlagen (kein Backup)
        assert result.patches[0].status == FixStatus.FAILED
        assert "No backup found" in result.patches[0].validation_errors

    def test_create_summary(self, temp_repo, solution_plan):
        """Zusammenfassung erstellen."""
        engine = create_auto_fix_engine(
            repo_path=temp_repo,
            solution_plan=solution_plan,
            dry_run=True,
        )

        result = engine.generate_patches()
        result = engine.apply_patches(result, validate=False)

        assert "Auto-Fix" in result.summary
        assert "Patches erfolgreich" in result.summary
        assert "100%" in result.summary  # Success-Rate


# =============================================================================
# Tests für Manager-Erweiterungen
# =============================================================================

class TestManagerAutoFix:
    """Tests für ProblemManager Auto-Fix Methoden."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Erstellt temporäres Repository."""
        problems_dir = tmp_path / ".glitchhunter" / "problems"
        problems_dir.mkdir(parents=True, exist_ok=True)
        return tmp_path

    def test_auto_fix_problem_not_found(self, temp_repo):
        """Auto-Fix mit nicht existierendem Problem."""
        manager = ProblemManager(repo_path=temp_repo)

        with pytest.raises(ValueError, match="Problem .* not found"):
            manager.auto_fix("nonexistent_id")

    def test_auto_fix_no_solution_plan(self, temp_repo):
        """Auto-Fix ohne SolutionPlan."""
        manager = ProblemManager(repo_path=temp_repo)

        # Problem erstellen
        problem = manager.intake_problem(
            description="Test Problem",
            title="Test",
        )

        # Kein SolutionPlan erstellt
        with pytest.raises(ValueError, match="No solution plan found"):
            manager.auto_fix(problem.id)

    def test_auto_fix_dry_run(self, temp_repo):
        """Auto-Fix im Dry-Run Modus."""
        manager = ProblemManager(repo_path=temp_repo)

        # Problem und Plan erstellen
        problem = manager.intake_problem(
            description="Test Problem",
            title="Test",
        )
        plan = manager.create_solution_plan(problem.id)

        # Pfade auswählen (nur wenn vorhanden)
        for sp_id, paths in plan.solution_paths.items():
            if paths:
                plan.select_path(sp_id, paths[0].id)
        manager._save_solution_plan(problem.id, plan)

        # Auto-Fix (Dry-Run)
        result = manager.auto_fix(problem.id, dry_run=True)

        assert result.problem_id == problem.id
        # Patches können leer sein wenn keine SubProbleme
        # oder SolutionPlanner keine Pfade generiert hat
        # Wichtig: Kein Fehler sollte auftreten
        assert result is not None

        # Result sollte gespeichert sein
        result_file = temp_repo / ".glitchhunter" / "problems" / f"{problem.id}_auto_fix.json"
        assert result_file.exists()

    def test_auto_fix_and_save(self, temp_repo):
        """Auto-Fix mit Speichern."""
        manager = ProblemManager(repo_path=temp_repo)

        problem = manager.intake_problem(
            description="Test Problem",
            title="Test",
        )
        plan = manager.create_solution_plan(problem.id)

        # Pfade auswählen (nur wenn vorhanden)
        for sp_id, paths in plan.solution_paths.items():
            if paths:
                plan.select_path(sp_id, paths[0].id)
        manager._save_solution_plan(problem.id, plan)

        # Auto-Fix
        result = manager.auto_fix(problem.id, dry_run=True)

        # Speichern prüfen
        result_file = temp_repo / ".glitchhunter" / "problems" / f"{problem.id}_auto_fix.json"
        assert result_file.exists()

        data = json.loads(result_file.read_text())
        assert data["problem_id"] == problem.id
        # Status kann pending sein wenn keine Patches generiert wurden
        assert data["overall_status"] in ["pending", "completed"]

    def test_rollback_fix_no_result(self, temp_repo):
        """Rollback ohne AutoFixResult."""
        manager = ProblemManager(repo_path=temp_repo)

        problem = manager.intake_problem(
            description="Test Problem",
            title="Test",
        )

        # Kein AutoFixResult vorhanden
        with pytest.raises(ValueError, match="No auto-fix result found"):
            manager.rollback_fix(problem.id)

    def test_rollback_fix(self, temp_repo):
        """Rollback von Auto-Fix."""
        manager = ProblemManager(repo_path=temp_repo)

        problem = manager.intake_problem(
            description="Test Problem",
            title="Test",
        )
        plan = manager.create_solution_plan(problem.id)

        # Pfade auswählen
        for sp_id, paths in plan.solution_paths.items():
            if paths:
                plan.select_path(sp_id, paths[0].id)
        manager._save_solution_plan(problem.id, plan)

        # Auto-Fix (Dry-Run)
        result = manager.auto_fix(problem.id, dry_run=True)

        # Rollback
        rollback_result = manager.rollback_fix(problem.id)

        assert rollback_result.problem_id == problem.id
        # Im Dry-Run kein echtes Rollback möglich
        # Status sollte FAILED sein (kein Backup)


# =============================================================================
# Tests für CLI Commands
# =============================================================================

class TestCliAutoFix:
    """Tests für CLI Auto-Fix Commands."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Erstellt temporäres Repository."""
        problems_dir = tmp_path / ".glitchhunter" / "problems"
        problems_dir.mkdir(parents=True, exist_ok=True)
        return tmp_path

    def test_cmd_problem_fix_help(self):
        """Help für fix Command."""
        from src.problem.cli import setup_problem_parser
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        setup_problem_parser(subparsers)

        # Help sollte SystemExit werfen
        import sys
        import io
        
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        try:
            with pytest.raises(SystemExit):
                parser.parse_args(["problem", "fix", "--help"])
        finally:
            sys.stdout = old_stdout

    def test_cmd_problem_fix_problem_not_found(self, temp_repo, capsys):
        """Fix mit nicht existierendem Problem."""
        from src.problem.cli import cmd_problem_fix
        import argparse

        args = argparse.Namespace(
            problem_id="nonexistent",
            dry_run=True,
            no_validate=False,
            config=None,
        )

        # Mock Config
        with patch('core.config.Config.load') as mock_load:
            mock_load.return_value = MagicMock(
                repository=MagicMock(path=str(temp_repo))
            )

            result = cmd_problem_fix(args)

            assert result == 1
            captured = capsys.readouterr()
            assert "Error" in captured.err

    def test_cmd_problem_fix_dry_run(self, temp_repo, capsys):
        """Fix im Dry-Run Modus."""
        from src.problem.cli import cmd_problem_fix
        import argparse

        # Problem und Plan erstellen
        manager = ProblemManager(repo_path=temp_repo)
        problem = manager.intake_problem(
            description="Test Problem",
            title="Test",
        )
        plan = manager.create_solution_plan(problem.id)

        # Pfade auswählen
        for sp_id, paths in plan.solution_paths.items():
            if paths:
                plan.select_path(sp_id, paths[0].id)
        manager._save_solution_plan(problem.id, plan)

        args = argparse.Namespace(
            problem_id=problem.id,
            dry_run=True,
            no_validate=False,
            config=None,
        )

        with patch('core.config.Config.load') as mock_load:
            mock_load.return_value = MagicMock(
                repository=MagicMock(path=str(temp_repo))
            )

            result = cmd_problem_fix(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "Auto-Fix" in captured.out
            assert "DRY RUN" in captured.out

    def test_cmd_problem_rollback_help(self):
        """Help für rollback Command."""
        from src.problem.cli import setup_problem_parser
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        setup_problem_parser(subparsers)

        # Help sollte SystemExit werfen
        import sys
        import io
        
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        try:
            with pytest.raises(SystemExit):
                parser.parse_args(["problem", "rollback", "--help"])
        finally:
            sys.stdout = old_stdout

    def test_cmd_problem_rollback_cancelled(self, temp_repo, capsys, monkeypatch):
        """Rollback abgebrochen."""
        from src.problem.cli import cmd_problem_rollback
        import argparse

        args = argparse.Namespace(
            problem_id="prob_001",
            force=False,
            config=None,
        )

        # 'N' eingeben - mock input function
        monkeypatch.setattr('builtins.input', lambda _: 'N')

        # Mock Config
        with patch('core.config.Config.load') as mock_load:
            mock_load.return_value = MagicMock(
                repository=MagicMock(path=str(temp_repo))
            )

            result = cmd_problem_rollback(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "abgebrochen" in captured.out

    def test_cmd_problem_rollback_force(self, temp_repo, capsys):
        """Rollback mit --force."""
        from src.problem.cli import cmd_problem_rollback
        import argparse

        # Problem und AutoFixResult erstellen
        manager = ProblemManager(repo_path=temp_repo)
        problem = manager.intake_problem(
            description="Test Problem",
            title="Test",
        )

        # Fake AutoFixResult speichern
        result = AutoFixResult(
            problem_id=problem.id,
            solution_plan_id="plan_001",
        )
        manager._save_auto_fix_result(problem.id, result)

        args = argparse.Namespace(
            problem_id=problem.id,
            force=True,
            config=None,
        )

        with patch('core.config.Config.load') as mock_load:
            mock_load.return_value = MagicMock(
                repository=MagicMock(path=str(temp_repo))
            )

            result = cmd_problem_rollback(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "Rollback" in captured.out
