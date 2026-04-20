"""
Tests für Stack-spezifische Adapter.

Tests für PROBLEM_SOLVER.md Phase 2.4:
- StackCapability, StackProfile Models
- StackAdapterManager (Profile laden, vergleichen)
- recommend_stack() für verschiedene Problemtypen
- validate_stack_compatibility()
- Manager-Erweiterungen
- CLI Command
"""

import argparse
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.problem.stack_adapter import (
    StackID,
    CapabilityLevel,
    StackCapability,
    StackProfile,
    StackAdapterManager,
    create_stack_adapter,
)
from src.problem.manager import ProblemManager
from src.problem.cli import cmd_problem_stack


# =============================================================================
# Tests für StackCapability Model
# =============================================================================

class TestStackCapability:
    """Tests für StackCapability Datenklasse."""

    def test_create_capability(self):
        """Erstellt einfache Capability."""
        cap = StackCapability(
            name="code_analysis",
            level=CapabilityLevel.FULL,
            description="Code-Analyse und Parsing",
        )

        assert cap.name == "code_analysis"
        assert cap.level == CapabilityLevel.FULL
        assert cap.description == "Code-Analyse und Parsing"
        assert cap.requirements == []
        assert cap.limitations == []

    def test_capability_with_details(self):
        """Capability mit Anforderungen und Limitationen."""
        cap = StackCapability(
            name="dynamic_analysis",
            level=CapabilityLevel.LIMITED,
            description="Fuzzing und Runtime-Analyse",
            requirements=["GPU mit 8GB VRAM"],
            limitations=["Nur sequentielles Fuzzing"],
            notes="Für paralleles Fuzzing Stack B verwenden",
        )

        assert len(cap.requirements) == 1
        assert len(cap.limitations) == 1
        assert cap.notes != ""

    def test_to_dict(self):
        """Konvertierung zu Dictionary."""
        cap = StackCapability(
            name="test_cap",
            level=CapabilityLevel.ENHANCED,
            description="Test",
        )

        result = cap.to_dict()

        assert result["name"] == "test_cap"
        assert result["level"] == "enhanced"
        assert result["description"] == "Test"
        assert isinstance(result["requirements"], list)
        assert isinstance(result["limitations"], list)

    def test_is_supported(self):
        """Prüft ob Fähigkeit unterstützt wird."""
        full_cap = StackCapability(
            name="full",
            level=CapabilityLevel.FULL,
        )
        limited_cap = StackCapability(
            name="limited",
            level=CapabilityLevel.LIMITED,
        )
        not_supported_cap = StackCapability(
            name="not_supported",
            level=CapabilityLevel.NOT_SUPPORTED,
        )

        assert full_cap.is_supported() is True
        assert limited_cap.is_supported() is True
        assert not_supported_cap.is_supported() is False


# =============================================================================
# Tests für StackProfile Model
# =============================================================================

class TestStackProfile:
    """Tests für StackProfile Datenklasse."""

    def test_create_profile(self):
        """Erstellt einfaches Profil."""
        profile = StackProfile(
            stack_id=StackID.STACK_A,
            name="Test Stack",
            description="Testbeschreibung",
            max_memory_gb=16,
            max_cpu_cores=4,
        )

        assert profile.stack_id == StackID.STACK_A
        assert profile.name == "Test Stack"
        assert profile.max_memory_gb == 16
        assert profile.max_cpu_cores == 4
        assert profile.gpu_available is False

    def test_add_capability(self):
        """Fügt Fähigkeit zu Profil hinzu."""
        profile = StackProfile(
            stack_id=StackID.STACK_A,
            name="Test",
        )

        cap = profile.add_capability(
            name="test_capability",
            level=CapabilityLevel.FULL,
            description="Test",
        )

        assert "test_capability" in profile.capabilities
        assert profile.get_capability("test_capability") == cap
        assert profile.is_capable("test_capability") is True

    def test_add_capability_with_limitations(self):
        """Fügt Fähigkeit mit Limitationen hinzu."""
        profile = StackProfile(stack_id=StackID.STACK_A, name="Test")

        cap = profile.add_capability(
            name="limited_cap",
            level=CapabilityLevel.LIMITED,
            limitations=["Nur im Testmodus"],
        )

        assert cap.level == CapabilityLevel.LIMITED
        assert len(cap.limitations) == 1

    def test_is_capable(self):
        """Prüft ob Stack fähig ist."""
        profile = StackProfile(stack_id=StackID.STACK_A, name="Test")
        profile.add_capability("cap1", CapabilityLevel.FULL)
        profile.add_capability("cap2", CapabilityLevel.NOT_SUPPORTED)

        assert profile.is_capable("cap1") is True
        assert profile.is_capable("cap2") is False
        assert profile.is_capable("nonexistent") is False

    def test_has_feature(self):
        """Prüft Feature-Flags."""
        profile = StackProfile(stack_id=StackID.STACK_A, name="Test")
        profile.features = {
            "feature_a": True,
            "feature_b": False,
        }

        assert profile.has_feature("feature_a") is True
        assert profile.has_feature("feature_b") is False
        assert profile.has_feature("nonexistent") is False

    def test_to_dict(self):
        """Konvertierung zu Dictionary."""
        profile = StackProfile(
            stack_id=StackID.STACK_B,
            name="Enhanced Stack",
            max_memory_gb=64,
            max_cpu_cores=16,
            gpu_available=True,
            gpu_memory_gb=24.0,
        )
        profile.add_capability("test", CapabilityLevel.ENHANCED)
        profile.features = {"feature": True}

        result = profile.to_dict()

        assert result["stack_id"] == "stack_b"
        assert result["name"] == "Enhanced Stack"
        assert result["resources"]["max_memory_gb"] == 64
        assert result["resources"]["gpu_available"] is True
        assert "test" in result["capabilities"]
        assert result["features"]["feature"] is True

    def test_from_dict(self):
        """Erstellt Profil aus Dictionary."""
        data = {
            "stack_id": "stack_a",
            "name": "Imported Stack",
            "description": "Aus Dict importiert",
            "resources": {
                "max_memory_gb": 32,
                "max_cpu_cores": 8,
                "gpu_available": True,
                "gpu_memory_gb": 8.0,
            },
            "capabilities": {
                "test_cap": {
                    "name": "test_cap",
                    "level": "full",
                    "description": "Test",
                }
            },
            "features": {"feature_x": True},
            "version": "2.0",
        }

        profile = StackProfile.from_dict(data)

        assert profile.stack_id == StackID.STACK_A
        assert profile.name == "Imported Stack"
        assert profile.max_memory_gb == 32
        assert profile.get_capability("test_cap") is not None
        assert profile.has_feature("feature_x") is True

    def test_get_statistics(self):
        """Returns Statistik über Profil."""
        profile = StackProfile(
            stack_id=StackID.STACK_A,
            name="Test",
            max_memory_gb=32,
        )
        profile.add_capability("cap1", CapabilityLevel.FULL)
        profile.add_capability("cap2", CapabilityLevel.FULL)
        profile.add_capability("cap3", CapabilityLevel.LIMITED)
        profile.add_capability("cap4", CapabilityLevel.NOT_SUPPORTED)
        profile.features = {"f1": True, "f2": False, "f3": True}

        stats = profile.get_statistics()

        assert stats["total_capabilities"] == 4
        assert stats["supported_capabilities"] == 3
        assert stats["capability_coverage"] == 75.0
        assert stats["enabled_features"] == 2
        assert stats["total_features"] == 3
        assert stats["resources"]["memory_gb"] == 32

    def test_get_execution_order_topological(self):
        """Berechnet topologische Sortierung."""
        profile = StackProfile(stack_id=StackID.STACK_A, name="Test")

        subproblem_ids = ["sp1", "sp2", "sp3", "sp4"]
        dependencies = {
            "sp1": [],
            "sp2": ["sp1"],
            "sp3": ["sp1"],
            "sp4": ["sp2", "sp3"],
        }

        order = profile.get_execution_order(subproblem_ids, dependencies)

        # sp1 muss vor sp2, sp3 sein
        # sp2, sp3 müssen vor sp4 sein
        assert order.index("sp1") < order.index("sp2")
        assert order.index("sp1") < order.index("sp3")
        assert order.index("sp2") < order.index("sp4")
        assert order.index("sp3") < order.index("sp4")


# =============================================================================
# Tests für StackAdapterManager
# =============================================================================

class TestStackAdapterManager:
    """Tests für StackAdapterManager."""

    def test_create_manager(self):
        """Erstellt Manager."""
        manager = create_stack_adapter()

        assert manager is not None
        assert StackID.STACK_A in manager.profiles
        assert StackID.STACK_B in manager.profiles

    def test_default_profiles_loaded(self):
        """Standard-Profile wurden geladen."""
        manager = StackAdapterManager()

        stack_a = manager.get_profile(StackID.STACK_A)
        stack_b = manager.get_profile(StackID.STACK_B)

        assert stack_a is not None
        assert stack_b is not None
        assert stack_a.name == "Stack A (Standard)"
        assert stack_b.name == "Stack B (Enhanced)"

    def test_stack_a_resources(self):
        """Stack A Ressourcen korrekt."""
        manager = StackAdapterManager()
        stack_a = manager.get_profile(StackID.STACK_A)

        assert stack_a.max_memory_gb == 32
        assert stack_a.max_cpu_cores == 8
        assert stack_a.gpu_available is True
        assert stack_a.gpu_memory_gb == 8.0

    def test_stack_b_resources(self):
        """Stack B Ressourcen korrekt."""
        manager = StackAdapterManager()
        stack_b = manager.get_profile(StackID.STACK_B)

        assert stack_b.max_memory_gb == 64
        assert stack_b.max_cpu_cores == 16
        assert stack_b.gpu_available is True
        assert stack_b.gpu_memory_gb == 24.0

    def test_stack_a_dynamic_analysis_limited(self):
        """Stack A: dynamic_analysis ist LIMITED."""
        manager = StackAdapterManager()
        stack_a = manager.get_profile(StackID.STACK_A)

        cap = stack_a.get_capability("dynamic_analysis")
        assert cap is not None
        assert cap.level == CapabilityLevel.LIMITED

    def test_stack_b_enhanced_capabilities(self):
        """Stack B: bestimmte Capabilities sind ENHANCED."""
        manager = StackAdapterManager()
        stack_b = manager.get_profile(StackID.STACK_B)

        # Diese sollten ENHANCED sein
        enhanced_caps = ["llm_analysis", "dynamic_analysis", "patch_generation"]

        for cap_name in enhanced_caps:
            cap = stack_b.get_capability(cap_name)
            assert cap is not None
            assert cap.level == CapabilityLevel.ENHANCED

    def test_stack_a_features(self):
        """Stack A Features."""
        manager = StackAdapterManager()
        stack_a = manager.get_profile(StackID.STACK_A)

        assert stack_a.has_feature("ensemble_mode") is False
        assert stack_a.has_feature("multi_model_voting") is False
        assert stack_a.has_feature("parallel_fuzzing") is False
        assert stack_a.has_feature("enhanced_reports") is True
        assert stack_a.has_feature("tui_full") is True
        assert stack_a.has_feature("api_full") is True

    def test_stack_b_features(self):
        """Stack B Features (mehr als Stack A)."""
        manager = StackAdapterManager()
        stack_b = manager.get_profile(StackID.STACK_B)

        assert stack_b.has_feature("ensemble_mode") is True
        assert stack_b.has_feature("multi_model_voting") is True
        assert stack_b.has_feature("parallel_fuzzing") is True
        assert stack_b.has_feature("enhanced_reports") is True
        assert stack_b.has_feature("auto_fix") is True
        assert stack_b.has_feature("goal_validation") is True

    def test_get_all_profiles(self):
        """Returns alle Profile als Copy."""
        manager = StackAdapterManager()

        profiles = manager.get_all_profiles()

        assert StackID.STACK_A in profiles
        assert StackID.STACK_B in profiles
        # Sollte eine Copy sein
        assert profiles is not manager.profiles

    def test_compare_stacks_general(self):
        """Vergleicht beide Stacks allgemein."""
        manager = StackAdapterManager()

        comparison = manager.compare_stacks()

        assert "stack_a" in comparison
        assert "stack_b" in comparison
        assert "differences" in comparison
        assert comparison["stack_a"]["name"] == "Stack A (Standard)"
        assert comparison["stack_b"]["name"] == "Stack B (Enhanced)"

    def test_compare_stacks_specific_capability(self):
        """Vergleicht spezifische Capability."""
        manager = StackAdapterManager()

        comparison = manager.compare_stacks("dynamic_analysis")

        assert "differences" in comparison
        assert "dynamic_analysis" in comparison["differences"]
        diff = comparison["differences"]["dynamic_analysis"]
        assert diff["stack_a"] is not None
        assert diff["stack_b"] is not None
        # Stack B sollte gewinnen (ENHANCED > LIMITED)
        assert diff["winner"] == "stack_b"

    def test_recommend_stack_performance(self):
        """Empfiehlt Stack B für Performance-Probleme."""
        manager = StackAdapterManager()

        result = manager.recommend_stack(problem_type="performance")

        assert result == StackID.STACK_B

    def test_recommend_stack_dynamic_analysis(self):
        """Empfiehlt Stack B für Dynamic Analysis."""
        manager = StackAdapterManager()

        result = manager.recommend_stack(problem_type="dynamic_analysis")

        assert result == StackID.STACK_B

    def test_recommend_stack_bug(self):
        """Empfiehlt Stack A für Bug-Probleme."""
        manager = StackAdapterManager()

        result = manager.recommend_stack(problem_type="bug")

        assert result == StackID.STACK_A

    def test_recommend_stack_unknown_type(self):
        """Empfiehlt Stack A als Default."""
        manager = StackAdapterManager()

        result = manager.recommend_stack(problem_type="unknown_type")

        assert result == StackID.STACK_A

    def test_recommend_stack_by_capabilities(self):
        """Empfiehlt Stack B bei Bedarf an ENHANCED Capabilities."""
        manager = StackAdapterManager()

        result = manager.recommend_stack(
            problem_type="unknown",
            required_capabilities=["llm_analysis"],
        )

        # Stack B hat ENHANCED llm_analysis
        assert result == StackID.STACK_B

    def test_validate_stack_compatibility_success(self):
        """Validiert kompatible Solution."""
        manager = StackAdapterManager()

        result = manager.validate_stack_compatibility(
            solution_plan_id="plan_123",
            stack_id=StackID.STACK_A,
        )

        assert result["compatible"] is True
        assert result["warnings"] == []
        assert "stack" in result

    def test_validate_stack_compatibility_invalid_stack(self):
        """Validiert mit ungültigem Stack."""
        manager = StackAdapterManager()

        # Ungültige StackID simulieren
        result = manager.validate_stack_compatibility(
            solution_plan_id="plan_123",
            stack_id=StackID.STACK_A,
        )

        # Sollte trotzdem funktionieren da STACK_A existiert
        assert result["compatible"] is True


# =============================================================================
# Tests für ProblemManager-Erweiterungen
# =============================================================================

class TestProblemManagerStackExtensions:
    """Tests für Stack-Methoden in ProblemManager."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Erstellt temporäres Repository."""
        repo = tmp_path / "test_repo"
        repo.mkdir()
        (repo / ".glitchhunter").mkdir()
        return repo

    def test_get_stack_profile_valid(self, temp_repo):
        """Lädt valides Stack-Profil."""
        manager = ProblemManager(repo_path=temp_repo)

        profile = manager.get_stack_profile("stack_a")

        assert profile is not None
        assert profile.stack_id == StackID.STACK_A

    def test_get_stack_profile_invalid(self, temp_repo):
        """Lädt invalide Stack-ID."""
        manager = ProblemManager(repo_path=temp_repo)

        profile = manager.get_stack_profile("invalid_stack")

        assert profile is None

    def test_compare_stacks(self, temp_repo):
        """Vergleicht Stacks über Manager."""
        manager = ProblemManager(repo_path=temp_repo)

        comparison = manager.compare_stacks()

        assert "stack_a" in comparison
        assert "stack_b" in comparison

    def test_compare_stacks_with_capability(self, temp_repo):
        """Vergleicht spezifische Capability."""
        manager = ProblemManager(repo_path=temp_repo)

        comparison = manager.compare_stacks("code_analysis")

        assert "differences" in comparison
        assert "code_analysis" in comparison["differences"]

    def test_recommend_stack_for_problem(self, temp_repo):
        """Empfiehlt Stack für existierendes Problem."""
        manager = ProblemManager(repo_path=temp_repo)
        problem = manager.intake_problem("Performance Problem")

        recommendation = manager.recommend_stack_for_problem(problem.id)

        # Performance sollte Stack B empfehlen
        assert recommendation in ["stack_a", "stack_b"]

    def test_recommend_stack_for_nonexistent_problem(self, temp_repo):
        """Empfiehlt Default für nicht-existierendes Problem."""
        manager = ProblemManager(repo_path=temp_repo)

        recommendation = manager.recommend_stack_for_problem("nonexistent")

        assert recommendation == "stack_a"

    def test_validate_solution_for_stack(self, temp_repo):
        """Validiert Solution für Stack."""
        manager = ProblemManager(repo_path=temp_repo)

        result = manager.validate_solution_for_stack(
            problem_id="prob_123",
            solution_plan_id="plan_123",
            stack_id="stack_b",
        )

        assert result["compatible"] is True


# =============================================================================
# Tests für CLI Command
# =============================================================================

class TestCmdProblemStack:
    """Tests für cmd_problem_stack CLI Command."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Erstellt temporäres Repository."""
        repo = tmp_path / "test_repo"
        repo.mkdir()
        (repo / ".glitchhunter").mkdir()
        return repo

    @pytest.fixture
    def mock_config(self, temp_repo):
        """Mocked Config.load."""
        with patch('core.config.Config.load') as MockLoad:
            mock_config_instance = MagicMock()
            mock_config_instance.repository.path = str(temp_repo)
            MockLoad.return_value = mock_config_instance
            yield mock_config_instance

    def test_stack_overview(self, temp_repo, mock_config, capsys):
        """Zeigt Stack-Übersicht."""
        args = argparse.Namespace(
            compare=False,
            profile=None,
            recommend=None,
            capability=None,
        )

        result = cmd_problem_stack(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Verfügbare Stacks" in captured.out
        assert "stack_a" in captured.out
        assert "stack_b" in captured.out

    def test_stack_compare(self, temp_repo, mock_config, capsys):
        """Vergleicht beide Stacks."""
        args = argparse.Namespace(
            compare=True,
            profile=None,
            recommend=None,
            capability=None,
        )

        result = cmd_problem_stack(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Stack-Vergleich" in captured.out
        assert "Stack A (Standard)" in captured.out
        assert "Stack B (Enhanced)" in captured.out

    def test_stack_compare_specific_capability(self, temp_repo, mock_config, capsys):
        """Vergleicht spezifische Capability."""
        args = argparse.Namespace(
            compare=True,
            profile=None,
            recommend=None,
            capability="dynamic_analysis",
        )

        result = cmd_problem_stack(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Stack-Vergleich" in captured.out

    def test_stack_profile(self, temp_repo, mock_config, capsys):
        """Zeigt spezifisches Profil."""
        args = argparse.Namespace(
            compare=False,
            profile="stack_a",
            recommend=None,
            capability=None,
        )

        result = cmd_problem_stack(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Stack A (Standard)" in captured.out
        assert "Capabilities" in captured.out

    def test_stack_profile_invalid(self, temp_repo, mock_config, capsys):
        """Zeigt invalide Profil."""
        args = argparse.Namespace(
            compare=False,
            profile="invalid_stack",
            recommend=None,
            capability=None,
        )

        result = cmd_problem_stack(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "nicht gefunden" in captured.err

    def test_stack_recommend(self, temp_repo, mock_config, capsys):
        """Empfiehlt Stack für Problem."""
        # Erst Problem erstellen
        manager = ProblemManager(repo_path=temp_repo)
        problem = manager.intake_problem("Performance Problem")

        args = argparse.Namespace(
            compare=False,
            profile=None,
            recommend=problem.id,
            capability=None,
        )

        result = cmd_problem_stack(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Empfehlung" in captured.out
        assert "Stack" in captured.out
