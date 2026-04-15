"""
Tests für Problem-Solver CLI Commands.

Testet die CLI-Commands gemäß PROBLEM_SOLVER.md Phase 1.3.
Parallele Struktur zu bestehenden Bug-Hunting-Tests.
"""

import argparse
import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.problem.cli import (
    cmd_problem_intake,
    cmd_problem_list,
    cmd_problem_show,
    cmd_problem_classify,
    cmd_problem_delete,
    cmd_problem_stats,
    setup_problem_parser,
)
from src.problem.models import ProblemCase, ProblemType, ProblemSeverity, ProblemStatus


@pytest.fixture
def temp_repo():
    """Erstellt temporäres Repository für Tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        # Config erstellen
        config_file = repo_path / "config.yaml"
        config_file.write_text("""
repository:
  path: {}
  
api:
  host: 0.0.0.0
  port: 8000
  debug: false

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
""".format(str(repo_path)))
        
        yield repo_path


@pytest.fixture
def mock_config(temp_repo):
    """Mocked Config.load um temporäres Repo zu verwenden."""
    # Mock muss auf 'core.config.Config.load' gesetzt werden (ohne src. Präfix)
    # da die CLI 'from core.config import Config' verwendet
    with patch('core.config.Config.load') as MockLoad:
        mock_config_instance = MagicMock()
        mock_config_instance.repository.path = str(temp_repo)
        MockLoad.return_value = mock_config_instance
        yield mock_config_instance


class TestCmdProblemIntake:
    """Tests für cmd_problem_intake."""
    
    def test_intake_with_description(self, temp_repo, mock_config, capsys):
        """Intake mit Beschreibung als Argument."""
        args = argparse.Namespace(
            description="Die API ist sehr langsam",
            file=None,
            title=None,
            config=None,
        )
        
        result = cmd_problem_intake(args)
        
        assert result == 0
        captured = capsys.readouterr()
        assert "✅ Problem created:" in captured.out
        assert "ID: prob_" in captured.out
    
    def test_intake_with_title(self, temp_repo, mock_config, capsys):
        """Intake mit benutzerdefiniertem Titel."""
        args = argparse.Namespace(
            description="Die API ist sehr langsam",
            file=None,
            title="Performance Problem",
            config=None,
        )
        
        result = cmd_problem_intake(args)
        
        assert result == 0
        captured = capsys.readouterr()
        assert "Title: Performance Problem" in captured.out
    
    def test_intake_from_file(self, temp_repo, mock_config, capsys):
        """Intake aus Datei lesen."""
        # Problem-Beschreibung in Datei schreiben
        problem_file = temp_repo / "problem.txt"
        problem_file.write_text("Performance Probleme im System")
        
        args = argparse.Namespace(
            description=None,
            file=str(problem_file),
            title=None,
            config=None,
        )
        
        result = cmd_problem_intake(args)
        
        assert result == 0
        captured = capsys.readouterr()
        assert "✅ Problem created:" in captured.out
    
    def test_intake_file_not_found(self, temp_repo, mock_config, capsys):
        """Intake mit nicht-existierender Datei."""
        args = argparse.Namespace(
            description=None,
            file="/nonexistent/file.txt",
            title=None,
            config=None,
        )
        
        result = cmd_problem_intake(args)
        
        assert result == 1
        captured = capsys.readouterr()
        assert "Error reading file:" in captured.err
    
    def test_intake_empty_description(self, temp_repo, mock_config, capsys):
        """Intake mit leerer Beschreibung."""
        args = argparse.Namespace(
            description="",
            file=None,
            title=None,
            config=None,
        )
        
        result = cmd_problem_intake(args)
        
        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Empty problem description" in captured.err
    
    def test_intake_whitespace_description(self, temp_repo, mock_config, capsys):
        """Intake mit Whitespace-Beschreibung."""
        args = argparse.Namespace(
            description="   \n   ",
            file=None,
            title=None,
            config=None,
        )
        
        result = cmd_problem_intake(args)
        
        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Empty problem description" in captured.err


class TestCmdProblemList:
    """Tests für cmd_problem_list."""
    
    def test_list_empty(self, temp_repo, mock_config, capsys):
        """Liste ohne Probleme."""
        args = argparse.Namespace(
            status=None,
            type=None,
            config=None,
        )
        
        result = cmd_problem_list(args)
        
        assert result == 0
        captured = capsys.readouterr()
        assert "No problems found" in captured.out
    
    def test_list_with_problems(self, temp_repo, mock_config, capsys):
        """Liste mit Problemen."""
        # Erst Problem erstellen
        from src.problem.manager import ProblemManager
        manager = ProblemManager(repo_path=temp_repo)
        manager.intake_problem("Problem A")
        manager.intake_problem("Problem B")
        
        args = argparse.Namespace(
            status=None,
            type=None,
            config=None,
        )
        
        result = cmd_problem_list(args)
        
        assert result == 0
        captured = capsys.readouterr()
        assert "Total: 2 problem(s)" in captured.out
        assert "ID" in captured.out
        assert "Title" in captured.out
    
    def test_list_filter_by_status(self, temp_repo, mock_config, capsys):
        """Liste nach Status filtern."""
        from src.problem.manager import ProblemManager
        manager = ProblemManager(repo_path=temp_repo)
        manager.intake_problem("Problem A")
        manager.intake_problem("Problem B")
        
        args = argparse.Namespace(
            status="intake",
            type=None,
            config=None,
        )
        
        result = cmd_problem_list(args)
        
        assert result == 0
        captured = capsys.readouterr()
        # Sollte nur intake Probleme zeigen
    
    def test_list_invalid_status(self, temp_repo, mock_config, capsys):
        """Liste mit ungültigem Status-Filter."""
        args = argparse.Namespace(
            status="invalid_status",
            type=None,
            config=None,
        )
        
        result = cmd_problem_list(args)
        
        assert result == 1
        captured = capsys.readouterr()
        assert "Invalid status: invalid_status" in captured.err
    
    def test_list_invalid_type(self, temp_repo, mock_config, capsys):
        """Liste mit ungültigem Typ-Filter."""
        args = argparse.Namespace(
            status=None,
            type="invalid_type",
            config=None,
        )
        
        result = cmd_problem_list(args)
        
        assert result == 1
        captured = capsys.readouterr()
        assert "Invalid type: invalid_type" in captured.err


class TestCmdProblemShow:
    """Tests für cmd_problem_show."""
    
    def test_show_existing_problem(self, temp_repo, mock_config, capsys):
        """Show für existierendes Problem."""
        from src.problem.manager import ProblemManager
        manager = ProblemManager(repo_path=temp_repo)
        problem = manager.intake_problem(
            "Performance Problem in der API",
            title="API Performance",
        )
        
        args = argparse.Namespace(
            problem_id=problem.id,
            config=None,
        )
        
        result = cmd_problem_show(args)
        
        assert result == 0
        captured = capsys.readouterr()
        assert "Problem: API Performance" in captured.out
        assert problem.id in captured.out
        assert "Performance" in captured.out
    
    def test_show_nonexistent_problem(self, temp_repo, mock_config, capsys):
        """Show für nicht-existierendes Problem."""
        args = argparse.Namespace(
            problem_id="prob_nonexistent",
            config=None,
        )
        
        result = cmd_problem_show(args)
        
        assert result == 1
        captured = capsys.readouterr()
        assert "Problem prob_nonexistent not found" in captured.err


class TestCmdProblemClassify:
    """Tests für cmd_problem_classify."""
    
    def test_classify_existing_problem(self, temp_repo, mock_config, capsys):
        """Classify für existierendes Problem."""
        from src.problem.manager import ProblemManager
        manager = ProblemManager(repo_path=temp_repo)
        problem = manager.intake_problem("Die API ist sehr langsam mit Timeouts")
        
        args = argparse.Namespace(
            problem_id=problem.id,
            config=None,
        )
        
        result = cmd_problem_classify(args)
        
        assert result == 0
        captured = capsys.readouterr()
        assert "✅ Classification complete" in captured.out
        assert problem.id in captured.out
    
    def test_classify_nonexistent_problem(self, temp_repo, mock_config, capsys):
        """Classify für nicht-existierendes Problem."""
        args = argparse.Namespace(
            problem_id="prob_nonexistent",
            config=None,
        )
        
        result = cmd_problem_classify(args)
        
        assert result == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.err


class TestCmdProblemDelete:
    """Tests für cmd_problem_delete."""
    
    def test_delete_with_confirmation(self, temp_repo, mock_config, capsys, monkeypatch):
        """Delete mit Bestätigung."""
        from src.problem.manager import ProblemManager
        manager = ProblemManager(repo_path=temp_repo)
        problem = manager.intake_problem("Test Problem")
        
        # Bestätigung simulieren
        monkeypatch.setattr('builtins.input', lambda _: 'y')
        
        args = argparse.Namespace(
            problem_id=problem.id,
            force=False,
            config=None,
        )
        
        result = cmd_problem_delete(args)
        
        assert result == 0
        captured = capsys.readouterr()
        assert f"✅ Problem {problem.id} deleted" in captured.out
    
    def test_delete_cancelled(self, temp_repo, mock_config, capsys, monkeypatch):
        """Delete abgebrochen."""
        from src.problem.manager import ProblemManager
        manager = ProblemManager(repo_path=temp_repo)
        problem = manager.intake_problem("Test Problem")
        
        # Ablehnung simulieren
        monkeypatch.setattr('builtins.input', lambda _: 'n')
        
        args = argparse.Namespace(
            problem_id=problem.id,
            force=False,
            config=None,
        )
        
        result = cmd_problem_delete(args)
        
        assert result == 0
        captured = capsys.readouterr()
        assert "Delete cancelled" in captured.out
    
    def test_delete_with_force(self, temp_repo, mock_config, capsys):
        """Delete ohne Bestätigung (force)."""
        from src.problem.manager import ProblemManager
        manager = ProblemManager(repo_path=temp_repo)
        problem = manager.intake_problem("Test Problem")
        
        args = argparse.Namespace(
            problem_id=problem.id,
            force=True,
            config=None,
        )
        
        result = cmd_problem_delete(args)
        
        assert result == 0
        captured = capsys.readouterr()
        assert f"✅ Problem {problem.id} deleted" in captured.out
    
    def test_delete_nonexistent_problem(self, temp_repo, mock_config, capsys):
        """Delete für nicht-existierendes Problem."""
        args = argparse.Namespace(
            problem_id="prob_nonexistent",
            force=True,
            config=None,
        )
        
        result = cmd_problem_delete(args)
        
        assert result == 1
        captured = capsys.readouterr()
        assert "Problem prob_nonexistent not found" in captured.err


class TestCmdProblemStats:
    """Tests für cmd_problem_stats."""
    
    def test_stats_empty(self, temp_repo, mock_config, capsys):
        """Stats ohne Probleme."""
        args = argparse.Namespace(
            config=None,
        )
        
        result = cmd_problem_stats(args)
        
        assert result == 0
        captured = capsys.readouterr()
        assert "📊 Problem Statistics" in captured.out
        assert "Total Problems: 0" in captured.out
    
    def test_stats_with_problems(self, temp_repo, mock_config, capsys):
        """Stats mit Problemen."""
        from src.problem.manager import ProblemManager
        manager = ProblemManager(repo_path=temp_repo)
        manager.intake_problem("Problem A")
        manager.intake_problem("Problem B")
        manager.intake_problem("Problem C")
        
        args = argparse.Namespace(
            config=None,
        )
        
        result = cmd_problem_stats(args)
        
        assert result == 0
        captured = capsys.readouterr()
        assert "Total Problems: 3" in captured.out
        assert "By Type:" in captured.out
        assert "By Status:" in captured.out


class TestSetupProblemParser:
    """Tests für Parser-Setup."""
    
    def test_parser_setup(self):
        """Parser wird korrekt eingerichtet."""
        import argparse
        parser = argparse.ArgumentParser(prog="glitchhunter")
        subparsers = parser.add_subparsers()
        
        setup_problem_parser(subparsers)
        
        # Testen ob Commands verfügbar sind
        args = parser.parse_args(["problem", "intake", "Test"])
        assert args.problem_command == "intake"
        assert hasattr(args, 'func')
    
    def test_parser_list_command(self):
        """List Command wird erkannt."""
        import argparse
        parser = argparse.ArgumentParser(prog="glitchhunter")
        subparsers = parser.add_subparsers()
        
        setup_problem_parser(subparsers)
        
        args = parser.parse_args(["problem", "list"])
        assert args.problem_command == "list"
    
    def test_parser_show_command(self):
        """Show Command wird erkannt."""
        import argparse
        parser = argparse.ArgumentParser(prog="glitchhunter")
        subparsers = parser.add_subparsers()
        
        setup_problem_parser(subparsers)
        
        args = parser.parse_args(["problem", "show", "prob_123"])
        assert args.problem_command == "show"
        assert args.problem_id == "prob_123"
    
    def test_parser_classify_command(self):
        """Classify Command wird erkannt."""
        import argparse
        parser = argparse.ArgumentParser(prog="glitchhunter")
        subparsers = parser.add_subparsers()
        
        setup_problem_parser(subparsers)
        
        args = parser.parse_args(["problem", "classify", "prob_123"])
        assert args.problem_command == "classify"
    
    def test_parser_delete_command(self):
        """Delete Command wird erkannt."""
        import argparse
        parser = argparse.ArgumentParser(prog="glitchhunter")
        subparsers = parser.add_subparsers()
        
        setup_problem_parser(subparsers)
        
        args = parser.parse_args(["problem", "delete", "prob_123", "--force"])
        assert args.problem_command == "delete"
        assert args.force is True
    
    def test_parser_stats_command(self):
        """Stats Command wird erkannt."""
        import argparse
        parser = argparse.ArgumentParser(prog="glitchhunter")
        subparsers = parser.add_subparsers()
        
        setup_problem_parser(subparsers)
        
        args = parser.parse_args(["problem", "stats"])
        assert args.problem_command == "stats"


class TestIntegration:
    """Integrationstests für kompletten Workflow."""
    
    def test_full_workflow(self, temp_repo, mock_config, capsys, monkeypatch):
        """Kompletter Workflow: intake -> list -> show -> classify -> delete."""
        from src.problem.manager import ProblemManager
        
        # 1. Problem aufnehmen
        args_intake = argparse.Namespace(
            description="Performance Problem in der API",
            file=None,
            title="API Performance",
            config=None,
        )
        result = cmd_problem_intake(args_intake)
        assert result == 0
        
        # Problem ID aus Output extrahieren
        captured = capsys.readouterr()
        problem_id = None
        for line in captured.out.split('\n'):
            if "ID: prob_" in line:
                problem_id = line.split("ID: ")[1].strip()
                break
        
        assert problem_id is not None
        
        # 2. Problem auflisten
        args_list = argparse.Namespace(
            status=None,
            type=None,
            config=None,
        )
        result = cmd_problem_list(args_list)
        assert result == 0
        
        # 3. Problem zeigen
        args_show = argparse.Namespace(
            problem_id=problem_id,
            config=None,
        )
        result = cmd_problem_show(args_show)
        assert result == 0
        
        # 4. Problem klassifizieren
        args_classify = argparse.Namespace(
            problem_id=problem_id,
            config=None,
        )
        result = cmd_problem_classify(args_classify)
        assert result == 0
        
        # 5. Stats zeigen
        args_stats = argparse.Namespace(
            config=None,
        )
        result = cmd_problem_stats(args_stats)
        assert result == 0
        
        # 6. Problem löschen
        monkeypatch.setattr('builtins.input', lambda _: 'y')
        args_delete = argparse.Namespace(
            problem_id=problem_id,
            force=False,
            config=None,
        )
        result = cmd_problem_delete(args_delete)
        assert result == 0
        
        # 7. Verify deletion
        manager = ProblemManager(repo_path=temp_repo)
        assert manager.get_problem(problem_id) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
