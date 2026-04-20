"""
Tests für TUI Problem-Solver Advanced Screens (Phase 2.5).

Testet:
- Screen Initialisierung
- Integration mit Manager
- Navigation zwischen Screens (grundlegend)
"""

import pytest
from pathlib import Path

from src.tui.screens.problem_diagnosis import ProblemDiagnosisScreen
from src.tui.screens.problem_decomposition import ProblemDecompositionScreen
from src.tui.screens.problem_solution_plan import ProblemSolutionPlanScreen
from src.tui.screens.problem_stack_select import ProblemStackSelectScreen


class TestProblemDiagnosisScreen:
    """Tests für ProblemDiagnosisScreen."""

    def test_init(self):
        """Test Initialisierung."""
        screen = ProblemDiagnosisScreen(
            repo_path="/test/repo",
            problem_id="prob_001",
        )

        assert screen.repo_path == "/test/repo"
        assert screen.problem_id == "prob_001"
        assert screen.diagnosis is None

    def test_css_defined(self):
        """Test dass CSS definiert ist."""
        assert ProblemDiagnosisScreen.CSS is not None
        assert "#diagnosis-container" in ProblemDiagnosisScreen.CSS

    def test_bindings_defined(self):
        """Test dass Bindings definiert sind."""
        assert len(ProblemDiagnosisScreen.BINDINGS) >= 2
        binding_keys = [b.key for b in ProblemDiagnosisScreen.BINDINGS]
        assert "d" in binding_keys
        assert "escape" in binding_keys


class TestProblemDecompositionScreen:
    """Tests für ProblemDecompositionScreen."""

    def test_init(self):
        """Test Initialisierung."""
        screen = ProblemDecompositionScreen(
            repo_path="/test/repo",
            problem_id="prob_001",
        )

        assert screen.repo_path == "/test/repo"
        assert screen.problem_id == "prob_001"
        assert screen.decomposition is None

    def test_css_defined(self):
        """Test dass CSS definiert ist."""
        assert ProblemDecompositionScreen.CSS is not None
        assert "#decomposition-container" in ProblemDecompositionScreen.CSS

    def test_bindings_defined(self):
        """Test dass Bindings definiert sind."""
        assert len(ProblemDecompositionScreen.BINDINGS) >= 2
        binding_keys = [b.key for b in ProblemDecompositionScreen.BINDINGS]
        assert "p" in binding_keys
        assert "escape" in binding_keys


class TestProblemSolutionPlanScreen:
    """Tests für ProblemSolutionPlanScreen."""

    def test_init(self):
        """Test Initialisierung."""
        screen = ProblemSolutionPlanScreen(
            repo_path="/test/repo",
            problem_id="prob_001",
        )

        assert screen.repo_path == "/test/repo"
        assert screen.problem_id == "prob_001"
        assert screen.plan is None

    def test_css_defined(self):
        """Test dass CSS definiert ist."""
        assert ProblemSolutionPlanScreen.CSS is not None
        assert "#plan-container" in ProblemSolutionPlanScreen.CSS

    def test_bindings_defined(self):
        """Test dass Bindings definiert sind."""
        assert len(ProblemSolutionPlanScreen.BINDINGS) >= 1
        binding_keys = [b.key for b in ProblemSolutionPlanScreen.BINDINGS]
        assert "escape" in binding_keys


class TestProblemStackSelectScreen:
    """Tests für ProblemStackSelectScreen."""

    def test_init(self):
        """Test Initialisierung."""
        screen = ProblemStackSelectScreen(
            repo_path="/test/repo",
            problem_id="prob_001",
        )

        assert screen.repo_path == "/test/repo"
        assert screen.problem_id == "prob_001"
        assert screen.selected_stack == "stack_a"

    def test_css_defined(self):
        """Test dass CSS definiert ist."""
        assert ProblemStackSelectScreen.CSS is not None
        assert "#stack-container" in ProblemStackSelectScreen.CSS

    def test_bindings_defined(self):
        """Test dass Bindings definiert sind."""
        assert len(ProblemStackSelectScreen.BINDINGS) >= 2
        binding_keys = [b.key for b in ProblemStackSelectScreen.BINDINGS]
        assert "1" in binding_keys
        assert "2" in binding_keys
        assert "escape" in binding_keys

    def test_stack_selection_default(self):
        """Test dass Standard-Stack 'stack_a' ist."""
        screen = ProblemStackSelectScreen(
            repo_path="/test/repo",
            problem_id="prob_001",
        )
        assert screen.selected_stack == "stack_a"


class TestScreenIntegration:
    """Integration Tests für Screens mit Manager."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Erstellt temporäres Repository."""
        problems_dir = tmp_path / ".glitchhunter" / "problems"
        problems_dir.mkdir(parents=True, exist_ok=True)
        return tmp_path

    def test_diagnosis_screen_manager_integration(self, temp_repo):
        """Test Integration mit ProblemManager."""
        from problem.manager import ProblemManager

        # Problem und Diagnose erstellen
        manager = ProblemManager(repo_path=temp_repo)
        problem = manager.intake_problem(
            description="Performance Problem",
            title="Test Performance",
        )
        diagnosis = manager.generate_diagnosis(problem.id)

        # Screen erstellen
        screen = ProblemDiagnosisScreen(
            repo_path=str(temp_repo),
            problem_id=problem.id,
        )

        # Verify screen properties
        assert screen.repo_path == str(temp_repo)
        assert screen.problem_id == problem.id

        # Verify diagnosis exists
        assert diagnosis is not None
        assert diagnosis.summary is not None

    def test_decomposition_screen_manager_integration(self, temp_repo):
        """Test Integration mit ProblemManager für Decomposition."""
        from problem.manager import ProblemManager

        manager = ProblemManager(repo_path=temp_repo)
        problem = manager.intake_problem(
            description="Feature fehlt",
            title="Test Feature",
        )
        decomp = manager.decompose_problem(problem.id)

        screen = ProblemDecompositionScreen(
            repo_path=str(temp_repo),
            problem_id=problem.id,
        )

        # Verify screen properties
        assert screen.repo_path == str(temp_repo)
        assert screen.problem_id == problem.id

        # Verify decomposition exists
        assert decomp is not None
        assert len(decomp.subproblems) > 0

    def test_plan_screen_manager_integration(self, temp_repo):
        """Test Integration mit ProblemManager für Plan."""
        from problem.manager import ProblemManager

        manager = ProblemManager(repo_path=temp_repo)
        problem = manager.intake_problem(
            description="Refactor needed",
            title="Test Refactor",
        )
        plan = manager.create_solution_plan(problem.id)

        screen = ProblemSolutionPlanScreen(
            repo_path=str(temp_repo),
            problem_id=problem.id,
        )

        # Verify screen properties
        assert screen.repo_path == str(temp_repo)
        assert screen.problem_id == problem.id

        # Verify plan exists
        assert plan is not None
        assert plan.problem_id == problem.id

    def test_full_workflow_integration(self, temp_repo):
        """Test kompletter Workflow: Diagnose -> Decomposition -> Plan."""
        from problem.manager import ProblemManager

        manager = ProblemManager(repo_path=temp_repo)

        # 1. Problem erstellen
        problem = manager.intake_problem(
            description="Komplexes Problem mit mehreren Ursachen",
            title="Komplexes Test Problem",
        )

        # 2. Diagnose generieren
        diagnosis = manager.generate_diagnosis(problem.id)
        assert diagnosis is not None
        assert len(diagnosis.causes) > 0

        # 3. Decomposition erstellen
        decomp = manager.decompose_problem(problem.id)
        assert decomp is not None
        assert len(decomp.subproblems) > 0

        # 4. Lösungsplan erstellen
        plan = manager.create_solution_plan(problem.id)
        assert plan is not None
        assert plan.problem_id == problem.id

        # 5. Screens erstellen (ohne UI-Tests)
        diagnosis_screen = ProblemDiagnosisScreen(
            repo_path=str(temp_repo),
            problem_id=problem.id,
        )
        decomp_screen = ProblemDecompositionScreen(
            repo_path=str(temp_repo),
            problem_id=problem.id,
        )
        plan_screen = ProblemSolutionPlanScreen(
            repo_path=str(temp_repo),
            problem_id=problem.id,
        )
        stack_screen = ProblemStackSelectScreen(
            repo_path=str(temp_repo),
            problem_id=problem.id,
        )

        # Verify alle Screens wurden korrekt initialisiert
        assert diagnosis_screen.repo_path == str(temp_repo)
        assert decomp_screen.repo_path == str(temp_repo)
        assert plan_screen.repo_path == str(temp_repo)
        assert stack_screen.repo_path == str(temp_repo)

        assert diagnosis_screen.problem_id == problem.id
        assert decomp_screen.problem_id == problem.id
        assert plan_screen.problem_id == problem.id
        assert stack_screen.problem_id == problem.id


class TestScreenImports:
    """Tests für korrekte Imports."""

    def test_screens_module_exports(self):
        """Test dass alle Screens im Modul exportiert werden."""
        from src.tui.screens import (
            ProblemDiagnosisScreen,
            ProblemDecompositionScreen,
            ProblemSolutionPlanScreen,
            ProblemStackSelectScreen,
        )

        assert ProblemDiagnosisScreen is not None
        assert ProblemDecompositionScreen is not None
        assert ProblemSolutionPlanScreen is not None
        assert ProblemStackSelectScreen is not None

    def test_screen_classes_match_imports(self):
        """Test dass importierte Klassen den direkten entsprechen."""
        from src.tui.screens import (
            ProblemDiagnosisScreen as ImportedDiagnosis,
            ProblemDecompositionScreen as ImportedDecomp,
            ProblemSolutionPlanScreen as ImportedPlan,
            ProblemStackSelectScreen as ImportedStack,
        )

        assert ImportedDiagnosis == ProblemDiagnosisScreen
        assert ImportedDecomp == ProblemDecompositionScreen
        assert ImportedPlan == ProblemSolutionPlanScreen
        assert ImportedStack == ProblemStackSelectScreen
