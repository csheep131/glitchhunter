"""
Tests für Problem-Decomposition gemäß PROBLEM_SOLVER.md Phase 2.2.

Testet:
- SubProblem, Decomposition Models
- Dependency-Graph Methoden
- Execution-Order (topologische Sortierung)
- DecompositionEngine für verschiedene Problemtypen
- Manager-Erweiterungen (decompose_problem, get_decomposition)
- CLI Command (cmd_problem_decompose)
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
    DependencyType,
    Decomposition,
    DecompositionEngine,
)
from src.problem.manager import ProblemManager


class TestSubProblem:
    """Tests für SubProblem Model."""

    def test_minimal_creation(self):
        """Erstellung mit minimalen Required-Feldern."""
        subproblem = SubProblem(
            id="sub_001",
            problem_id="prob_001",
            title="Test Teilproblem",
            description="Beschreibung des Teilproblems",
        )

        assert subproblem.id == "sub_001"
        assert subproblem.problem_id == "prob_001"
        assert subproblem.title == "Test Teilproblem"
        assert subproblem.description == "Beschreibung des Teilproblems"
        assert subproblem.subproblem_type == SubProblemType.UNKNOWN
        assert subproblem.severity == ProblemSeverity.MEDIUM
        assert subproblem.priority == 5
        assert subproblem.effort == "medium"
        assert subproblem.complexity == 5
        assert subproblem.dependencies == []
        assert subproblem.dependency_type == DependencyType.RELATED
        assert subproblem.status == "open"
        assert subproblem.affected_components == []
        assert subproblem.affected_files == []
        assert subproblem.success_criteria == []
        assert subproblem.estimated_hours is None
        assert subproblem.created_at is not None
        assert subproblem.updated_at is not None

    def test_full_creation(self):
        """Erstellung mit allen Feldern."""
        subproblem = SubProblem(
            id="sub_002",
            problem_id="prob_001",
            title="Komplexes Teilproblem",
            description="Detaillierte Beschreibung",
            subproblem_type=SubProblemType.TECHNICAL,
            severity=ProblemSeverity.HIGH,
            priority=1,
            effort="high",
            complexity=8,
            dependencies=["sub_001"],
            dependency_type=DependencyType.DEPENDS_ON,
            status="in_progress",
            affected_components=["api", "database"],
            affected_files=["src/api.py", "src/db.py"],
            success_criteria=["Performance verbessert", "Tests grün"],
            estimated_hours=4.5,
        )

        assert subproblem.subproblem_type == SubProblemType.TECHNICAL
        assert subproblem.severity == ProblemSeverity.HIGH
        assert subproblem.priority == 1
        assert subproblem.effort == "high"
        assert subproblem.complexity == 8
        assert len(subproblem.dependencies) == 1
        assert subproblem.dependency_type == DependencyType.DEPENDS_ON
        assert subproblem.status == "in_progress"
        assert len(subproblem.affected_components) == 2
        assert len(subproblem.affected_files) == 2
        assert len(subproblem.success_criteria) == 2
        assert subproblem.estimated_hours == 4.5

    def test_to_dict(self):
        """Konvertierung zu Dictionary."""
        subproblem = SubProblem(
            id="sub_003",
            problem_id="prob_001",
            title="Test",
            description="Test Beschreibung",
            subproblem_type=SubProblemType.ANALYSIS,
            severity=ProblemSeverity.LOW,
            priority=3,
        )

        result = subproblem.to_dict()

        assert result["id"] == "sub_003"
        assert result["problem_id"] == "prob_001"
        assert result["title"] == "Test"
        assert result["description"] == "Test Beschreibung"
        assert result["subproblem_type"] == "analysis"
        assert result["severity"] == "low"
        assert result["priority"] == 3
        assert "created_at" in result
        assert "updated_at" in result

    def test_is_blocking(self):
        """Test is_blocking Methode."""
        blocking_sp = SubProblem(
            id="sub_block",
            problem_id="prob_001",
            title="Blocking",
            description="Blockiert andere",
            dependency_type=DependencyType.BLOCKS,
        )
        non_blocking_sp = SubProblem(
            id="sub_normal",
            problem_id="prob_001",
            title="Normal",
            description="Normal",
            dependency_type=DependencyType.RELATED,
        )

        assert blocking_sp.is_blocking() is True
        assert non_blocking_sp.is_blocking() is False

    def test_is_blocked(self):
        """Test is_blocked Methode."""
        blocked_sp = SubProblem(
            id="sub_blocked",
            problem_id="prob_001",
            title="Blocked",
            description="Ist blockiert",
            status="blocked",
        )
        open_sp = SubProblem(
            id="sub_open",
            problem_id="prob_001",
            title="Open",
            description="Ist offen",
            status="open",
        )

        assert blocked_sp.is_blocked() is True
        assert open_sp.is_blocked() is False

    def test_can_start_no_dependencies(self):
        """Test can_start ohne Dependencies."""
        sp = SubProblem(
            id="sub_001",
            problem_id="prob_001",
            title="Start",
            description="Kann starten",
            status="open",
        )

        assert sp.can_start([sp]) is True

    def test_can_start_with_dependencies(self):
        """Test can_start mit Dependencies."""
        sp1 = SubProblem(
            id="sub_001",
            problem_id="prob_001",
            title="Erstes",
            description="Ohne Dependencies",
            status="open",
        )
        sp2 = SubProblem(
            id="sub_002",
            problem_id="prob_001",
            title="Zweites",
            description="Hängt von erstem ab",
            dependencies=["sub_001"],
            status="open",
        )

        # Noch nicht startklar weil sub_001 nicht done
        assert sp2.can_start([sp1, sp2]) is False

        # Nach Abschluss von sub_001
        sp1.status = "done"
        assert sp2.can_start([sp1, sp2]) is True

    def test_can_start_when_blocked(self):
        """Test can_start wenn blockiert."""
        sp = SubProblem(
            id="sub_001",
            problem_id="prob_001",
            title="Blocked",
            description="Ist blockiert",
            status="blocked",
        )

        assert sp.can_start([sp]) is False


class TestDecomposition:
    """Tests für Decomposition Model."""

    def test_minimal_creation(self):
        """Erstellung mit minimalen Feldern."""
        decomp = Decomposition(problem_id="prob_001")

        assert decomp.problem_id == "prob_001"
        assert decomp.subproblems == []
        assert decomp.summary == ""
        assert decomp.decomposition_approach == ""
        assert decomp.created_at is not None
        assert decomp.updated_at is not None

    def test_to_dict(self):
        """Konvertierung zu Dictionary."""
        decomp = Decomposition(problem_id="prob_001")
        decomp.add_subproblem(
            title="Test Subproblem",
            description="Beschreibung",
            subproblem_type=SubProblemType.TECHNICAL,
        )

        result = decomp.to_dict()

        assert result["problem_id"] == "prob_001"
        assert len(result["subproblems"]) == 1
        assert result["subproblems"][0]["title"] == "Test Subproblem"
        assert "summary" in result
        assert "decomposition_approach" in result

    def test_from_dict(self):
        """Erstellung aus Dictionary."""
        data = {
            "problem_id": "prob_001",
            "subproblems": [
                {
                    "id": "sub_001",
                    "problem_id": "prob_001",
                    "title": "Test",
                    "description": "Test Beschreibung",
                    "subproblem_type": "technical",
                    "severity": "high",
                    "priority": 2,
                    "effort": "medium",
                    "complexity": 5,
                    "dependencies": [],
                    "dependency_type": "related",
                    "status": "open",
                    "affected_components": [],
                    "affected_files": [],
                    "success_criteria": [],
                    "estimated_hours": None,
                    "created_at": "2026-04-15T10:00:00",
                    "updated_at": "2026-04-15T10:00:00",
                }
            ],
            "summary": "Test Summary",
            "decomposition_approach": "Test Approach",
            "created_at": "2026-04-15T10:00:00",
            "updated_at": "2026-04-15T10:00:00",
        }

        decomp = Decomposition.from_dict(data)

        assert decomp.problem_id == "prob_001"
        assert len(decomp.subproblems) == 1
        assert decomp.subproblems[0].id == "sub_001"
        assert decomp.subproblems[0].subproblem_type == SubProblemType.TECHNICAL
        assert decomp.subproblems[0].severity == ProblemSeverity.HIGH
        assert decomp.summary == "Test Summary"
        assert decomp.decomposition_approach == "Test Approach"

    def test_add_subproblem(self):
        """Test add_subproblem Methode."""
        decomp = Decomposition(problem_id="prob_001")

        sp = decomp.add_subproblem(
            title="Neues Teilproblem",
            description="Beschreibung",
            subproblem_type=SubProblemType.ANALYSIS,
            priority=1,
            effort="low",
            dependencies=[],
            affected_components=["api"],
        )

        assert len(decomp.subproblems) == 1
        assert sp.id.startswith("sub_")
        assert sp.problem_id == "prob_001"
        assert sp.title == "Neues Teilproblem"
        assert sp.subproblem_type == SubProblemType.ANALYSIS
        assert sp.priority == 1
        assert sp.effort == "low"
        assert sp.affected_components == ["api"]

    def test_get_subproblem(self):
        """Test get_subproblem Methode."""
        decomp = Decomposition(problem_id="prob_001")
        sp1 = decomp.add_subproblem(title="Erstes", description="Beschreibung")
        sp2 = decomp.add_subproblem(title="Zweites", description="Beschreibung")

        result = decomp.get_subproblem(sp1.id)
        assert result == sp1

        result = decomp.get_subproblem("nonexistent")
        assert result is None

    def test_get_blocking_subproblems(self):
        """Test get_blocking_subproblems Methode."""
        decomp = Decomposition(problem_id="prob_001")
        decomp.add_subproblem(
            title="Blocking",
            description="Blockiert andere",
            dependency_type=DependencyType.BLOCKS,
        )
        decomp.add_subproblem(
            title="Normal",
            description="Normal",
            dependency_type=DependencyType.RELATED,
        )

        blocking = decomp.get_blocking_subproblems()
        assert len(blocking) == 1
        assert blocking[0].title == "Blocking"

    def test_get_blocked_subproblems(self):
        """Test get_blocked_subproblems Methode."""
        decomp = Decomposition(problem_id="prob_001")
        decomp.add_subproblem(
            title="Blocked",
            description="Ist blockiert",
            status="blocked",
        )
        decomp.add_subproblem(
            title="Open",
            description="Ist offen",
            status="open",
        )

        blocked = decomp.get_blocked_subproblems()
        assert len(blocked) == 1
        assert blocked[0].title == "Blocked"

    def test_get_ready_subproblems(self):
        """Test get_ready_subproblems Methode."""
        decomp = Decomposition(problem_id="prob_001")
        sp1 = decomp.add_subproblem(title="Erstes", description="Ohne Dependencies")
        sp2 = decomp.add_subproblem(
            title="Zweites",
            description="Mit Dependency",
            dependencies=[sp1.id],
        )

        ready = decomp.get_ready_subproblems()
        assert len(ready) == 1
        assert ready[0].id == sp1.id

        # Nach Abschluss von sp1
        sp1.status = "done"
        ready = decomp.get_ready_subproblems()
        assert len(ready) == 1
        assert ready[0].id == sp2.id

    def test_get_dependency_graph(self):
        """Test get_dependency_graph Methode."""
        decomp = Decomposition(problem_id="prob_001")
        sp1 = decomp.add_subproblem(title="Erstes", description="Beschreibung")
        sp2 = decomp.add_subproblem(
            title="Zweites",
            description="Beschreibung",
            dependencies=[sp1.id],
        )
        sp3 = decomp.add_subproblem(
            title="Drittes",
            description="Beschreibung",
            dependencies=[sp1.id, sp2.id],
        )

        graph = decomp.get_dependency_graph()

        assert len(graph) == 3
        assert graph[sp1.id] == set()
        assert graph[sp2.id] == {sp1.id}
        assert graph[sp3.id] == {sp1.id, sp2.id}

    def test_get_execution_order_no_dependencies(self):
        """Test get_execution_order ohne Dependencies."""
        decomp = Decomposition(problem_id="prob_001")
        sp1 = decomp.add_subproblem(title="Erstes", description="", priority=3)
        sp2 = decomp.add_subproblem(title="Zweites", description="", priority=1)
        sp3 = decomp.add_subproblem(title="Drittes", description="", priority=2)

        order = decomp.get_execution_order()

        # Sollte nach Priorität sortiert sein (1, 2, 3)
        assert len(order) == 3
        assert order[0].priority == 1
        assert order[1].priority == 2
        assert order[2].priority == 3

    def test_get_execution_order_with_dependencies(self):
        """Test get_execution_order mit Dependencies."""
        decomp = Decomposition(problem_id="prob_001")
        sp1 = decomp.add_subproblem(title="Erstes", description="", priority=3)
        sp2 = decomp.add_subproblem(
            title="Zweites",
            description="",
            priority=1,
            dependencies=[sp1.id],
        )

        order = decomp.get_execution_order()

        # sp1 muss vor sp2 kommen (trotz höherer Priorität)
        assert len(order) == 2
        assert order[0].id == sp1.id
        assert order[1].id == sp2.id

    def test_get_statistics(self):
        """Test get_statistics Methode."""
        decomp = Decomposition(problem_id="prob_001")
        decomp.add_subproblem(
            title="Technical",
            description="",
            subproblem_type=SubProblemType.TECHNICAL,
            status="open",
            estimated_hours=2.0,
        )
        decomp.add_subproblem(
            title="Analysis",
            description="",
            subproblem_type=SubProblemType.ANALYSIS,
            status="done",
            estimated_hours=1.5,
        )
        decomp.add_subproblem(
            title="Blocked",
            description="",
            subproblem_type=SubProblemType.TECHNICAL,
            status="blocked",
            estimated_hours=None,
        )

        stats = decomp.get_statistics()

        assert stats["total_subproblems"] == 3
        assert stats["by_status"] == {"open": 1, "done": 1, "blocked": 1}
        assert stats["by_type"] == {"technical": 2, "analysis": 1}
        assert stats["blocking_count"] == 0
        assert stats["blocked_count"] == 1
        assert stats["ready_count"] == 1  # Nur "done" ist nicht ready
        assert stats["total_estimated_hours"] == 3.5


class TestDecompositionEngine:
    """Tests für DecompositionEngine."""

    def test_engine_initialization(self):
        """Test Initialisierung der Engine."""
        engine = DecompositionEngine()
        assert engine is not None

    def test_decompose_performance_problem(self):
        """Test Zerlegung eines Performance-Problems."""
        problem = ProblemCase(
            id="prob_perf_001",
            title="Performance Problem",
            raw_description="Das System ist zu langsam",
            problem_type=ProblemType.PERFORMANCE,
            severity=ProblemSeverity.HIGH,
            affected_components=["api", "database"],
        )

        engine = DecompositionEngine()
        decomp = engine.decompose_problem(problem)

        assert decomp.problem_id == problem.id
        assert len(decomp.subproblems) >= 4
        assert "performance" in decomp.decomposition_approach.lower()

        # Standard-Zerlegung sollte enthalten sein
        titles = [sp.title for sp in decomp.subproblems]
        assert any("Performance-Messung" in t for t in titles)
        assert any("Bottleneck" in t for t in titles)
        assert any("Validierung" in t for t in titles)

    def test_decompose_missing_feature_problem(self):
        """Test Zerlegung eines Missing-Feature-Problems."""
        problem = ProblemCase(
            id="prob_feat_001",
            title="Feature fehlt",
            raw_description="Benötige User-Management",
            problem_type=ProblemType.MISSING_FEATURE,
            severity=ProblemSeverity.MEDIUM,
        )

        engine = DecompositionEngine()
        decomp = engine.decompose_problem(problem)

        assert decomp.problem_id == problem.id
        assert len(decomp.subproblems) >= 5

        titles = [sp.title for sp in decomp.subproblems]
        assert any("Anforderung" in t for t in titles)
        assert any("Design" in t or "Architektur" in t for t in titles)
        assert any("Implementierung" in t for t in titles)

    def test_decompose_bug_problem(self):
        """Test Zerlegung eines Bug-Problems."""
        problem = ProblemCase(
            id="prob_bug_001",
            title="Bug im System",
            raw_description="Fehlerhafte Ausgabe",
            problem_type=ProblemType.BUG,
            severity=ProblemSeverity.CRITICAL,
        )

        engine = DecompositionEngine()
        decomp = engine.decompose_problem(problem)

        assert decomp.problem_id == problem.id
        assert len(decomp.subproblems) >= 4

        titles = [sp.title for sp in decomp.subproblems]
        assert any("Reproduktion" in t for t in titles)
        assert any("Root-Cause" in t for t in titles)
        assert any("Fix" in t for t in titles)

    def test_decompose_unknown_problem(self):
        """Test Zerlegung eines unbekannten Problems."""
        problem = ProblemCase(
            id="prob_unknown_001",
            title="Unbekanntes Problem",
            raw_description="Irgendwas ist falsch",
            problem_type=ProblemType.UNKNOWN,
        )

        engine = DecompositionEngine()
        decomp = engine.decompose_problem(problem)

        assert decomp.problem_id == problem.id
        assert len(decomp.subproblems) >= 2

        # Default-Zerlegung sollte verwendet werden
        titles = [sp.title for sp in decomp.subproblems]
        assert any("Analyse" in t for t in titles)
        assert any("Planung" in t for t in titles)
        assert any("Umsetzung" in t for t in titles)

    def test_infer_subproblem_type_analysis(self):
        """Test automatische Typ-Erkennung für Analysis."""
        engine = DecompositionEngine()

        assert engine._infer_subproblem_type("Analyse", "Untersuchung") == SubProblemType.ANALYSIS
        assert engine._infer_subproblem_type("Research", "User Research") == SubProblemType.ANALYSIS

    def test_infer_subproblem_type_testing(self):
        """Test automatische Typ-Erkennung für Testing."""
        engine = DecompositionEngine()

        assert engine._infer_subproblem_type("Tests", "Testen") == SubProblemType.TESTING
        assert engine._infer_subproblem_type("Validierung", "Validieren") == SubProblemType.TESTING

    def test_infer_subproblem_type_integration(self):
        """Test automatische Typ-Erkennung für Integration."""
        engine = DecompositionEngine()

        assert engine._infer_subproblem_type("Integration", "Adapter") == SubProblemType.INTEGRATION
        assert engine._infer_subproblem_type("Connector", "Verbinden") == SubProblemType.INTEGRATION

    def test_affected_components_propagation(self):
        """Test dass affected_components vom Parent-Problem übernommen werden."""
        problem = ProblemCase(
            id="prob_001",
            title="Test",
            raw_description="Test",
            problem_type=ProblemType.PERFORMANCE,
            affected_components=["api", "database", "cache"],
        )

        engine = DecompositionEngine()
        decomp = engine.decompose_problem(problem)

        for sp in decomp.subproblems:
            assert "api" in sp.affected_components
            assert "database" in sp.affected_components
            assert "cache" in sp.affected_components


class TestManagerDecomposition:
    """Tests für Manager-Erweiterungen."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Erstellt temporäres Repository."""
        problems_dir = tmp_path / ".glitchhunter" / "problems"
        problems_dir.mkdir(parents=True, exist_ok=True)
        return tmp_path

    def test_decompose_problem(self, temp_repo):
        """Test decompose_problem Methode."""
        manager = ProblemManager(repo_path=temp_repo)

        # Problem erstellen
        problem = manager.intake_problem(
            description="Performance ist schlecht",
            title="Performance Problem",
        )

        # Decomposition durchführen
        decomp = manager.decompose_problem(problem.id)

        assert decomp is not None
        assert decomp.problem_id == problem.id
        assert len(decomp.subproblems) > 0

        # Status sollte auf planning gesetzt sein
        updated_problem = manager.get_problem(problem.id)
        assert updated_problem.status == ProblemStatus.PLANNING

    def test_get_decomposition(self, temp_repo):
        """Test get_decomposition Methode."""
        manager = ProblemManager(repo_path=temp_repo)

        # Problem erstellen und decomposen
        problem = manager.intake_problem(
            description="Feature fehlt",
            title="Missing Feature",
        )
        decomp1 = manager.decompose_problem(problem.id)

        # Decomposition laden
        decomp2 = manager.get_decomposition(problem.id)

        assert decomp2 is not None
        assert decomp2.problem_id == decomp1.problem_id
        assert len(decomp2.subproblems) == len(decomp1.subproblems)

    def test_get_decomposition_not_found(self, temp_repo):
        """Test get_decomposition für nicht existierende Decomposition."""
        manager = ProblemManager(repo_path=temp_repo)

        result = manager.get_decomposition("nonexistent")
        assert result is None

    def test_decompose_nonexistent_problem(self, temp_repo):
        """Test decompose_problem für nicht existierendes Problem."""
        manager = ProblemManager(repo_path=temp_repo)

        with pytest.raises(ValueError, match="Problem nonexistent not found"):
            manager.decompose_problem("nonexistent")


class TestCliDecompose:
    """Tests für CLI decompose Command."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Erstellt temporäres Repository."""
        problems_dir = tmp_path / ".glitchhunter" / "problems"
        problems_dir.mkdir(parents=True, exist_ok=True)
        return tmp_path

    def test_cmd_problem_decompose_success(self, temp_repo, capsys):
        """Test erfolgreiches decompose Command."""
        from src.problem.cli import cmd_problem_decompose
        from src.problem.manager import ProblemManager

        # Problem vorbereiten
        manager = ProblemManager(repo_path=temp_repo)
        problem = manager.intake_problem(
            description="Bug im System",
            title="Test Bug",
        )

        # Mock args
        class Args:
            problem_id = problem.id
            config = None

        args = Args()

        # Mit Mock für Config
        with patch('src.problem.cli.Config') as mock_config:
            mock_config.load.return_value.repository.path = str(temp_repo)
            result = cmd_problem_decompose(args)

        assert result == 0

        # Ausgabe prüfen
        captured = capsys.readouterr()
        assert "Problem zerlegt" in captured.out
        assert "Teilprobleme" in captured.out
        assert "Statistik" in captured.out
        assert "Ausführungsreihenfolge" in captured.out

    def test_cmd_problem_decompose_not_found(self, temp_repo, capsys):
        """Test decompose für nicht existierendes Problem."""
        from src.problem.cli import cmd_problem_decompose

        class Args:
            problem_id = "nonexistent"
            config = None

        args = Args()

        with patch('src.problem.cli.Config') as mock_config:
            mock_config.load.return_value.repository.path = str(temp_repo)
            result = cmd_problem_decompose(args)

        assert result == 1

        captured = capsys.readouterr()
        assert "Error" in captured.err
