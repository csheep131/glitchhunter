"""
Tests für Solution Path Planning gemäß PROBLEM_SOLVER.md Phase 2.3.

Testet:
- SolutionPath Model (overall_score, is_quick_win, is_high_risk)
- SolutionPlan Model (add, select, get_best, auto_select, statistics)
- SolutionPlanner (create_solution_plan, path generation)
- Manager-Erweiterungen (create_solution_plan, get_solution_plan, select_solution_path)
- CLI Commands (cmd_problem_plan, cmd_problem_select_path)
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

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
    SolutionPlanner,
)
from src.problem.manager import ProblemManager


class TestSolutionPath:
    """Tests für SolutionPath Model."""

    def test_minimal_creation(self):
        """Erstellung mit minimalen Required-Feldern."""
        path = SolutionPath(
            id="path_001",
            subproblem_id="sub_001",
            title="Test Lösungsweg",
            description="Beschreibung des Lösungswegs",
        )

        assert path.id == "path_001"
        assert path.subproblem_id == "sub_001"
        assert path.title == "Test Lösungsweg"
        assert path.description == "Beschreibung des Lösungswegs"
        assert path.solution_type == SolutionType.UNKNOWN
        assert path.effectiveness == 5
        assert path.invasiveness == 5
        assert path.risk == RiskLevel.MEDIUM
        assert path.effort == 5
        assert path.testability == 5
        assert path.implementation_steps == []
        assert path.estimated_hours is None
        assert path.created_at is not None

    def test_full_creation(self):
        """Erstellung mit allen Feldern."""
        path = SolutionPath(
            id="path_002",
            subproblem_id="sub_001",
            title="Kompletter Lösungsweg",
            description="Detaillierte Beschreibung",
            solution_type=SolutionType.REFACTOR,
            effectiveness=8,
            invasiveness=6,
            risk=RiskLevel.LOW,
            effort=4,
            testability=9,
            implementation_steps=["Schritt 1", "Schritt 2"],
            required_resources=["Ressource A"],
            dependencies=["Dep B"],
            risks=["Risiko C"],
            rollback_plan="Zurücksetzen auf Stand D",
            success_metrics=["Metrik E"],
            estimated_hours=8.0,
        )

        assert path.solution_type == SolutionType.REFACTOR
        assert path.effectiveness == 8
        assert path.risk == RiskLevel.LOW
        assert len(path.implementation_steps) == 2
        assert path.estimated_hours == 8.0

    def test_to_dict(self):
        """Konvertierung zu Dictionary."""
        path = SolutionPath(
            id="path_003",
            subproblem_id="sub_001",
            title="Test",
            description="Test Beschreibung",
            solution_type=SolutionType.HOTFIX,
            effectiveness=7,
            risk=RiskLevel.LOW,
        )

        result = path.to_dict()

        assert result["id"] == "path_003"
        assert result["solution_type"] == "hotfix"
        assert result["effectiveness"] == 7
        assert result["risk"] == "low"
        assert "title" in result
        assert "description" in result

    def test_overall_score_basic(self):
        """Berechnung des Gesamtscores."""
        # Guter Pfad: hohe Wirksamkeit, niedriges Risiko
        good_path = SolutionPath(
            id="path_good",
            subproblem_id="sub_001",
            title="Good",
            description="Good path",
            effectiveness=9,
            invasiveness=2,
            risk=RiskLevel.LOW,
            effort=3,
            testability=8,
        )

        # Schlechter Pfad: niedrige Wirksamkeit, hohes Risiko
        bad_path = SolutionPath(
            id="path_bad",
            subproblem_id="sub_001",
            title="Bad",
            description="Bad path",
            effectiveness=3,
            invasiveness=8,
            risk=RiskLevel.HIGH,
            effort=9,
            testability=4,
        )

        assert good_path.overall_score() > bad_path.overall_score()
        assert 0 <= good_path.overall_score() <= 10
        assert 0 <= bad_path.overall_score() <= 10

    def test_overall_score_boundaries(self):
        """Score bleibt innerhalb 0-10."""
        # Extrem guter Pfad
        excellent = SolutionPath(
            id="path_excellent",
            subproblem_id="sub_001",
            title="Excellent",
            description="Excellent path",
            effectiveness=10,
            invasiveness=1,
            risk=RiskLevel.LOW,
            effort=1,
            testability=10,
        )

        # Extrem schlechter Pfad
        terrible = SolutionPath(
            id="path_terrible",
            subproblem_id="sub_001",
            title="Terrible",
            description="Terrible path",
            effectiveness=1,
            invasiveness=10,
            risk=RiskLevel.CRITICAL,
            effort=10,
            testability=1,
        )

        assert 0 <= excellent.overall_score() <= 10
        assert 0 <= terrible.overall_score() <= 10

    def test_is_quick_win(self):
        """Quick Win Erkennung."""
        quick_win = SolutionPath(
            id="path_quick",
            subproblem_id="sub_001",
            title="Quick Win",
            description="Quick win path",
            effectiveness=8,
            effort=3,
        )

        not_quick_win = SolutionPath(
            id="path_not_quick",
            subproblem_id="sub_001",
            title="Not Quick Win",
            description="Not quick win path",
            effectiveness=8,
            effort=5,
        )

        low_effectiveness = SolutionPath(
            id="path_low_eff",
            subproblem_id="sub_001",
            title="Low Effectiveness",
            description="Low effectiveness path",
            effectiveness=5,
            effort=3,
        )

        assert quick_win.is_quick_win() is True
        assert not_quick_win.is_quick_win() is False
        assert low_effectiveness.is_quick_win() is False

    def test_is_high_risk(self):
        """高风险 Erkennung."""
        high_risk = SolutionPath(
            id="path_high_risk",
            subproblem_id="sub_001",
            title="High Risk",
            description="High risk path",
            risk=RiskLevel.HIGH,
        )

        critical_risk = SolutionPath(
            id="path_critical_risk",
            subproblem_id="sub_001",
            title="Critical Risk",
            description="Critical risk path",
            risk=RiskLevel.CRITICAL,
        )

        medium_risk = SolutionPath(
            id="path_medium_risk",
            subproblem_id="sub_001",
            title="Medium Risk",
            description="Medium risk path",
            risk=RiskLevel.MEDIUM,
        )

        low_risk = SolutionPath(
            id="path_low_risk",
            subproblem_id="sub_001",
            title="Low Risk",
            description="Low risk path",
            risk=RiskLevel.LOW,
        )

        assert high_risk.is_high_risk() is True
        assert critical_risk.is_high_risk() is True
        assert medium_risk.is_high_risk() is False
        assert low_risk.is_high_risk() is False


class TestSolutionPlan:
    """Tests für SolutionPlan Model."""

    def test_minimal_creation(self):
        """Erstellung mit minimalen Feldern."""
        plan = SolutionPlan(problem_id="prob_001")

        assert plan.problem_id == "prob_001"
        assert plan.decomposition_id is None
        assert plan.solution_paths == {}
        assert plan.selected_paths == {}
        assert plan.overall_strategy == ""
        assert plan.created_at is not None
        assert plan.updated_at is not None

    def test_add_solution_path(self):
        """Hinzufügen eines Lösungswegs."""
        plan = SolutionPlan(problem_id="prob_001")

        path = plan.add_solution_path(
            subproblem_id="sub_001",
            title="Test Pfad",
            description="Beschreibung",
            solution_type=SolutionType.HOTFIX,
            effectiveness=7,
            effort=4,
        )

        assert path.id.startswith("path_")
        assert path.subproblem_id == "sub_001"
        assert path.solution_type == SolutionType.HOTFIX
        assert len(plan.solution_paths["sub_001"]) == 1
        assert plan.updated_at is not None

    def test_add_multiple_paths(self):
        """Mehrere Pfade für ein Teilproblem."""
        plan = SolutionPlan(problem_id="prob_001")

        plan.add_solution_path("sub_001", "Pfad 1", "Beschreibung 1")
        plan.add_solution_path("sub_001", "Pfad 2", "Beschreibung 2")
        plan.add_solution_path("sub_002", "Pfad 3", "Beschreibung 3")

        assert len(plan.solution_paths["sub_001"]) == 2
        assert len(plan.solution_paths["sub_002"]) == 1

    def test_get_paths_for_subproblem(self):
        """Abruf der Pfade für ein Teilproblem."""
        plan = SolutionPlan(problem_id="prob_001")
        path1 = plan.add_solution_path("sub_001", "Pfad 1", "Beschreibung")
        path2 = plan.add_solution_path("sub_001", "Pfad 2", "Beschreibung")

        paths = plan.get_paths_for_subproblem("sub_001")
        assert len(paths) == 2
        assert path1 in paths
        assert path2 in paths

        # Nicht existierendes Teilproblem
        empty = plan.get_paths_for_subproblem("nonexistent")
        assert empty == []

    def test_select_path(self):
        """Auswahl eines Lösungswegs."""
        plan = SolutionPlan(problem_id="prob_001")
        path = plan.add_solution_path("sub_001", "Pfad", "Beschreibung")

        success = plan.select_path("sub_001", path.id)
        assert success is True
        assert plan.selected_paths["sub_001"] == path.id

        # Nicht existierender Pfad
        failure = plan.select_path("sub_001", "nonexistent")
        assert failure is False

    def test_get_selected_path(self):
        """Abruf des ausgewählten Pfads."""
        plan = SolutionPlan(problem_id="prob_001")
        path = plan.add_solution_path("sub_001", "Pfad", "Beschreibung")
        plan.select_path("sub_001", path.id)

        selected = plan.get_selected_path("sub_001")
        assert selected == path

        # Nicht ausgewählt
        none = plan.get_selected_path("sub_002")
        assert none is None

    def test_get_best_path(self):
        """Ermittlung des besten Pfads."""
        plan = SolutionPlan(problem_id="prob_001")

        # Schlechter Pfad
        plan.add_solution_path(
            "sub_001",
            "Schlecht",
            "Beschreibung",
            effectiveness=3,
            effort=9,
            risk=RiskLevel.HIGH,
        )

        # Guter Pfad
        best = plan.add_solution_path(
            "sub_001",
            "Gut",
            "Beschreibung",
            effectiveness=9,
            effort=2,
            risk=RiskLevel.LOW,
        )

        result = plan.get_best_path("sub_001")
        assert result == best

    def test_auto_select_best_paths(self):
        """Automatische Auswahl der besten Pfade."""
        plan = SolutionPlan(problem_id="prob_001")

        plan.add_solution_path("sub_001", "Schlecht", "Beschreibung", effectiveness=3)
        plan.add_solution_path("sub_001", "Gut", "Beschreibung", effectiveness=9)

        plan.add_solution_path("sub_002", "Pfad A", "Beschreibung", effectiveness=5)
        plan.add_solution_path("sub_002", "Pfad B", "Beschreibung", effectiveness=8)

        selected = plan.auto_select_best_paths()

        assert len(selected) == 2
        assert "sub_001" in selected
        assert "sub_002" in selected

        # Beste Pfade sollten ausgewählt sein
        best_001 = plan.get_best_path("sub_001")
        best_002 = plan.get_best_path("sub_002")
        assert plan.selected_paths["sub_001"] == best_001.id
        assert plan.selected_paths["sub_002"] == best_002.id

    def test_to_dict_and_from_dict(self):
        """Serialisierung und Deserialisierung."""
        plan = SolutionPlan(problem_id="prob_001", decomposition_id="decomp_001")
        path = plan.add_solution_path(
            "sub_001",
            "Test Pfad",
            "Beschreibung",
            solution_type=SolutionType.REFACTOR,
            effectiveness=8,
            risk=RiskLevel.MEDIUM,
        )
        plan.select_path("sub_001", path.id)
        plan.overall_strategy = "Test Strategie"

        # Zu Dict konvertieren
        data = plan.to_dict()

        # Zurück konvertieren
        restored = SolutionPlan.from_dict(data)

        assert restored.problem_id == plan.problem_id
        assert restored.decomposition_id == plan.decomposition_id
        assert len(restored.solution_paths["sub_001"]) == 1
        assert restored.selected_paths["sub_001"] == path.id
        assert restored.overall_strategy == plan.overall_strategy

    def test_get_statistics(self):
        """Statistik-Ermittlung."""
        plan = SolutionPlan(problem_id="prob_001")

        # 2 Teilprobleme mit je 2 Pfaden
        plan.add_solution_path("sub_001", "Pfad 1", "Beschreibung", effectiveness=7)
        plan.add_solution_path("sub_001", "Pfad 2", "Beschreibung", effectiveness=5)
        plan.add_solution_path("sub_002", "Pfad 3", "Beschreibung", effectiveness=8)
        plan.add_solution_path("sub_002", "Pfad 4", "Beschreibung", effectiveness=6)

        # Einen auswählen
        plan.select_path("sub_001", plan.solution_paths["sub_001"][0].id)

        stats = plan.get_statistics()

        assert stats["total_subproblems"] == 2
        assert stats["total_paths"] == 4
        assert stats["paths_per_subproblem"] == 2.0
        assert stats["selected_count"] == 1
        assert stats["completion_percentage"] == 50.0
        assert "avg_effectiveness" in stats
        assert "avg_overall_score" in stats

    def test_get_statistics_empty(self):
        """Statistik mit leerem Plan."""
        plan = SolutionPlan(problem_id="prob_001")
        stats = plan.get_statistics()

        assert stats["total_subproblems"] == 0
        assert stats["total_paths"] == 0
        assert stats["paths_per_subproblem"] == 0
        # avg_overall_score ist bei leerem Plan nicht vorhanden
        assert "avg_overall_score" not in stats


class TestSolutionPlanner:
    """Tests für SolutionPlanner."""

    def test_create_solution_plan(self):
        """Erstellung eines Lösungsplans."""
        planner = SolutionPlanner()

        subproblem_ids = ["sub_001", "sub_002", "sub_003"]

        plan = planner.create_solution_plan(
            problem_id="prob_001",
            subproblem_ids=subproblem_ids,
            decomposition_id="decomp_001",
        )

        assert plan.problem_id == "prob_001"
        assert plan.decomposition_id == "decomp_001"
        assert len(plan.solution_paths) == 3

        # Jedes Teilproblem sollte Pfade haben
        for sp_id in subproblem_ids:
            assert sp_id in plan.solution_paths
            assert len(plan.solution_paths[sp_id]) > 0

        # Beste Pfade sollten ausgewählt sein
        assert len(plan.selected_paths) == 3

    def test_create_solution_plan_empty(self):
        """Erstellung mit leeren SubProblems."""
        planner = SolutionPlanner()

        plan = planner.create_solution_plan(
            problem_id="prob_001",
            subproblem_ids=[],
        )

        assert plan.problem_id == "prob_001"
        assert len(plan.solution_paths) == 0
        assert len(plan.selected_paths) == 0

    def test_infer_solution_type(self):
        """Ableitung des SolutionType aus Titel."""
        planner = SolutionPlanner()

        assert planner._infer_solution_type("Minimaler Hotfix") == SolutionType.HOTFIX
        assert planner._infer_solution_type("Refactoring") == SolutionType.REFACTOR
        assert planner._infer_solution_type("Neuentwicklung") == SolutionType.REWRITE
        assert planner._infer_solution_type("Config Änderung") == SolutionType.CONFIG_CHANGE
        assert planner._infer_solution_type("Guard Pattern") == SolutionType.GUARD
        assert planner._infer_solution_type("Automatisierung") == SolutionType.AUTOMATION
        assert planner._infer_solution_type("Unbekannt") == SolutionType.UNKNOWN

    def test_generate_implementation_steps(self):
        """Generierung von Umsetzungsschritten."""
        planner = SolutionPlanner()

        steps_hotfix = planner._generate_implementation_steps(
            SolutionType.HOTFIX, "Hotfix"
        )
        assert len(steps_hotfix) > 0
        assert "Betroffenen Code identifizieren" in steps_hotfix

        steps_refactor = planner._generate_implementation_steps(
            SolutionType.REFACTOR, "Refactoring"
        )
        assert len(steps_refactor) > 0
        assert "Bestehende Struktur analysieren" in steps_refactor

        steps_unknown = planner._generate_implementation_steps(
            SolutionType.UNKNOWN, "Unknown"
        )
        assert len(steps_unknown) > 0

    def test_create_overall_strategy(self):
        """Erstellung der Gesamt-Strategie."""
        plan = SolutionPlan(problem_id="prob_001")
        plan.add_solution_path("sub_001", "Pfad 1", "Beschreibung")
        plan.add_solution_path("sub_001", "Pfad 2", "Beschreibung")
        plan.select_path("sub_001", plan.solution_paths["sub_001"][0].id)

        planner = SolutionPlanner()
        strategy = planner._create_overall_strategy(plan)

        assert "Lösungsstrategie" in strategy
        assert "1/1" in strategy  # 1 von 1 ausgewählt
        assert "Quick Wins" in strategy


class TestManagerSolutionPlan:
    """Tests für Manager-Erweiterungen."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Erstellt temporäres Repository."""
        problems_dir = tmp_path / ".glitchhunter" / "problems"
        problems_dir.mkdir(parents=True, exist_ok=True)
        return tmp_path

    def test_create_solution_plan(self, temp_repo):
        """Test create_solution_plan Methode."""
        manager = ProblemManager(repo_path=temp_repo)

        # Problem erstellen
        problem = manager.intake_problem(
            description="Performance ist schlecht",
            title="Performance Problem",
        )

        # Lösungsplan erstellen
        plan = manager.create_solution_plan(problem.id)

        assert plan is not None
        assert plan.problem_id == problem.id
        assert len(plan.solution_paths) >= 0

    def test_create_solution_plan_with_decomposition(self, temp_repo):
        """Test mit vorhandener Decomposition."""
        manager = ProblemManager(repo_path=temp_repo)

        # Problem erstellen
        problem = manager.intake_problem(
            description="Feature fehlt",
            title="Missing Feature",
        )

        # Decomposition erstellen
        decomp = manager.decompose_problem(problem.id)

        # Lösungsplan erstellen
        plan = manager.create_solution_plan(problem.id, use_decomposition=True)

        assert plan is not None
        assert plan.problem_id == problem.id
        # Decomposition hat kein id Attribut, nur problem_id
        assert plan.decomposition_id == problem.id
        assert len(plan.solution_paths) == len(decomp.subproblems)

    def test_get_solution_plan(self, temp_repo):
        """Test get_solution_plan Methode."""
        manager = ProblemManager(repo_path=temp_repo)

        # Problem und Plan erstellen
        problem = manager.intake_problem(
            description="Test Problem",
            title="Test",
        )
        plan1 = manager.create_solution_plan(problem.id)

        # Plan laden
        plan2 = manager.get_solution_plan(problem.id)

        assert plan2 is not None
        assert plan2.problem_id == plan1.problem_id
        assert len(plan2.solution_paths) == len(plan1.solution_paths)

    def test_get_solution_plan_not_found(self, temp_repo):
        """Test für nicht existierenden Plan."""
        manager = ProblemManager(repo_path=temp_repo)

        result = manager.get_solution_plan("nonexistent")
        assert result is None

    def test_select_solution_path(self, temp_repo):
        """Test select_solution_path Methode."""
        manager = ProblemManager(repo_path=temp_repo)

        # Problem und Plan erstellen
        problem = manager.intake_problem(
            description="Test Problem",
            title="Test",
        )
        plan = manager.create_solution_plan(problem.id)
        
        # Manuell einen Pfad hinzufügen falls keine Decomposition vorhanden
        if not plan.solution_paths:
            plan.add_solution_path("sub_manual", "Manueller Pfad", "Beschreibung")
            manager._save_solution_plan(problem.id, plan)
            sp_id = "sub_manual"
            path_id = plan.solution_paths["sub_manual"][0].id
        else:
            sp_id = list(plan.solution_paths.keys())[0]
            path_id = plan.solution_paths[sp_id][0].id

        success = manager.select_solution_path(problem.id, sp_id, path_id)
        assert success is True

        # Geladenen Plan prüfen
        loaded_plan = manager.get_solution_plan(problem.id)
        assert loaded_plan.selected_paths[sp_id] == path_id

    def test_select_solution_path_not_found(self, temp_repo):
        """Test mit nicht existierendem Plan."""
        manager = ProblemManager(repo_path=temp_repo)

        success = manager.select_solution_path(
            "nonexistent", "sub_001", "path_001"
        )
        assert success is False


class TestCLICommands:
    """Tests für CLI Commands."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Erstellt temporäres Repository."""
        problems_dir = tmp_path / ".glitchhunter" / "problems"
        problems_dir.mkdir(parents=True, exist_ok=True)
        return tmp_path

    def test_cmd_problem_plan(self, temp_repo):
        """Test cmd_problem_plan Command."""
        from src.problem.cli import cmd_problem_plan
        from src.problem.manager import ProblemManager
        from core.config import Config

        # Problem und Plan vorbereiten
        manager = ProblemManager(repo_path=temp_repo)
        problem = manager.intake_problem(
            description="Test Problem",
            title="Test",
        )

        # Args simulieren
        args = MagicMock()
        args.problem_id = problem.id
        args.skip_decomposition = False

        # Mock Config.load - wird in der Funktion importiert
        mock_config = MagicMock()
        mock_config.repository.path = str(temp_repo)
        
        with patch.object(Config, 'load', return_value=mock_config):
            result = cmd_problem_plan(args)

        assert result == 0

    def test_cmd_problem_plan_not_found(self, temp_repo):
        """Test mit nicht existierendem Problem."""
        from src.problem.cli import cmd_problem_plan
        from core.config import Config

        # Args simulieren
        args = MagicMock()
        args.problem_id = "nonexistent"
        args.skip_decomposition = False

        # Mock Config.load
        mock_config = MagicMock()
        mock_config.repository.path = str(temp_repo)

        with patch.object(Config, 'load', return_value=mock_config):
            result = cmd_problem_plan(args)

        assert result == 1

    def test_cmd_problem_select_path(self, temp_repo):
        """Test cmd_problem_select_path Command."""
        from src.problem.cli import cmd_problem_select_path
        from src.problem.manager import ProblemManager
        from core.config import Config

        # Mock Config.load
        mock_config = MagicMock()
        mock_config.repository.path = str(temp_repo)

        # Problem und Plan vorbereiten
        manager = ProblemManager(repo_path=temp_repo)
        problem = manager.intake_problem(
            description="Test Problem",
            title="Test",
        )
        # Plan manuell erstellen mit SubProblems
        plan = manager.create_solution_plan(problem.id, use_decomposition=False)
        
        # Manuell einen Pfad hinzufügen da ohne Decomposition keine generiert werden
        if not plan.solution_paths:
            plan.add_solution_path("sub_manual", "Manueller Pfad", "Beschreibung")
            manager._save_solution_plan(problem.id, plan)
            sp_id = "sub_manual"
            path_id = plan.solution_paths["sub_manual"][0].id
        else:
            sp_id = list(plan.solution_paths.keys())[0]
            path_id = plan.solution_paths[sp_id][0].id

        # Args simulieren
        args = MagicMock()
        args.problem_id = problem.id
        args.subproblem_id = sp_id
        args.path_id = path_id

        with patch.object(Config, 'load', return_value=mock_config):
            result = cmd_problem_select_path(args)

        assert result == 0

    def test_cmd_problem_select_path_not_found(self, temp_repo):
        """Test mit nicht existierendem Plan."""
        from src.problem.cli import cmd_problem_select_path
        from core.config import Config

        # Mock Config.load
        mock_config = MagicMock()
        mock_config.repository.path = str(temp_repo)

        args = MagicMock()
        args.problem_id = "nonexistent"
        args.subproblem_id = "sub_001"
        args.path_id = "path_001"

        with patch.object(Config, 'load', return_value=mock_config):
            result = cmd_problem_select_path(args)

        assert result == 1
