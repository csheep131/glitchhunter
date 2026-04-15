"""
Tests für Problem-Solver TUI Integration.

Da Textual nicht in der Test-Umgebung installiert ist, testen wir hier:
- Integration mit ProblemManager
- CSS/Bindings als String-Checks (ohne Import)
- File-Existenz und Syntax-Checks
"""

import pytest
from pathlib import Path
import ast


class TestProblemIntakeScreenFile:
    """Tests für ProblemIntakeScreen Datei."""
    
    @pytest.fixture
    def screen_file(self):
        """Lädt den Datei-Inhalt."""
        file_path = Path(__file__).parent.parent / "src" / "tui" / "screens" / "problem_intake.py"
        return file_path.read_text()
    
    def test_file_exists(self):
        """Test dass Datei existiert."""
        file_path = Path(__file__).parent.parent / "src" / "tui" / "screens" / "problem_intake.py"
        assert file_path.exists()
    
    def test_syntax_valid(self):
        """Test dass Python-Syntax valide ist."""
        file_path = Path(__file__).parent.parent / "src" / "tui" / "screens" / "problem_intake.py"
        code = file_path.read_text()
        
        # Sollte ohne Fehler parsen
        ast.parse(code)
    
    def test_has_class_definition(self, screen_file):
        """Test dass Klasse definiert ist."""
        assert "class ProblemIntakeScreen" in screen_file
        assert "Screen" in screen_file
    
    def test_has_css(self, screen_file):
        """Test dass CSS definiert ist."""
        assert "CSS" in screen_file
        assert "#intake-container" in screen_file
        assert "#intake-title" in screen_file
        assert "#description-input" in screen_file
    
    def test_has_bindings(self, screen_file):
        """Test dass Bindings definiert sind."""
        assert "BINDINGS" in screen_file
        assert "ctrl+s" in screen_file
        assert "escape" in screen_file
    
    def test_has_submit_action(self, screen_file):
        """Test dass submit Action existiert."""
        assert "def action_submit" in screen_file
        assert "ProblemManager" in screen_file
        assert "intake_problem" in screen_file
    
    def test_has_cancel_action(self, screen_file):
        """Test dass cancel Action existiert."""
        assert "def action_cancel" in screen_file
        assert "pop_screen" in screen_file
    
    def test_has_validation(self, screen_file):
        """Test dass Validierung existiert."""
        assert "if not description" in screen_file
        assert "notify" in screen_file
        assert "severity=\"error\"" in screen_file
    
    def test_has_compose(self, screen_file):
        """Test dass compose Methode existiert."""
        assert "def compose" in screen_file
        assert "Header" in screen_file
        assert "Footer" in screen_file
        assert "Input" in screen_file
        assert "TextArea" in screen_file
        assert "Button" in screen_file


class TestProblemOverviewScreenFile:
    """Tests für ProblemOverviewScreen Datei."""
    
    @pytest.fixture
    def screen_file(self):
        """Lädt den Datei-Inhalt."""
        file_path = Path(__file__).parent.parent / "src" / "tui" / "screens" / "problem_overview.py"
        return file_path.read_text()
    
    def test_file_exists(self):
        """Test dass Datei existiert."""
        file_path = Path(__file__).parent.parent / "src" / "tui" / "screens" / "problem_overview.py"
        assert file_path.exists()
    
    def test_syntax_valid(self):
        """Test dass Python-Syntax valide ist."""
        file_path = Path(__file__).parent.parent / "src" / "tui" / "screens" / "problem_overview.py"
        code = file_path.read_text()
        ast.parse(code)
    
    def test_has_class_definition(self, screen_file):
        """Test dass Klasse definiert ist."""
        assert "class ProblemOverviewScreen" in screen_file
        assert "Screen" in screen_file
    
    def test_has_css(self, screen_file):
        """Test dass CSS definiert ist."""
        assert "CSS" in screen_file
        assert "#overview-container" in screen_file
        assert "#problems-table" in screen_file
        assert "DataTable" in screen_file
    
    def test_has_bindings(self, screen_file):
        """Test dass Bindings definiert sind."""
        assert "BINDINGS" in screen_file
        assert '"n"' in screen_file  # Neu
        assert '"s"' in screen_file  # Show
        assert '"c"' in screen_file  # Classify
        assert '"d"' in screen_file  # Delete
        assert '"r"' in screen_file  # Refresh
        assert '"escape"' in screen_file  # Back
    
    def test_has_filters(self, screen_file):
        """Test dass Filter definiert sind."""
        assert "filter_status" in screen_file
        assert "filter_type" in screen_file
        assert "reactive" in screen_file
    
    def test_has_load_problems(self, screen_file):
        """Test dass load_problems Methode existiert."""
        assert "def _load_problems" in screen_file
        assert "ProblemManager" in screen_file
        assert "list_problems" in screen_file
    
    def test_has_filter_actions(self, screen_file):
        """Test dass Filter-Actions existieren."""
        assert "on_select_changed" in screen_file
        assert "watch_filter_status" in screen_file
        assert "watch_filter_type" in screen_file


class TestProblemDetailsScreenFile:
    """Tests für ProblemDetailsScreen Datei."""
    
    @pytest.fixture
    def screen_file(self):
        """Lädt den Datei-Inhalt."""
        file_path = Path(__file__).parent.parent / "src" / "tui" / "screens" / "problem_details.py"
        return file_path.read_text()
    
    def test_file_exists(self):
        """Test dass Datei existiert."""
        file_path = Path(__file__).parent.parent / "src" / "tui" / "screens" / "problem_details.py"
        assert file_path.exists()
    
    def test_syntax_valid(self):
        """Test dass Python-Syntax valide ist."""
        file_path = Path(__file__).parent.parent / "src" / "tui" / "screens" / "problem_details.py"
        code = file_path.read_text()
        ast.parse(code)
    
    def test_has_class_definition(self, screen_file):
        """Test dass Klasse definiert ist."""
        assert "class ProblemDetailsScreen" in screen_file
        assert "Screen" in screen_file
    
    def test_has_css(self, screen_file):
        """Test dass CSS definiert ist."""
        assert "CSS" in screen_file
        assert "#details-container" in screen_file
        assert "#details-content" in screen_file
        assert ".detail-section" in screen_file
    
    def test_has_bindings(self, screen_file):
        """Test dass Bindings definiert sind."""
        assert "BINDINGS" in screen_file
        assert '"e"' in screen_file  # Edit
        assert '"c"' in screen_file  # Classify
        assert '"escape"' in screen_file  # Back
    
    def test_has_load_problem(self, screen_file):
        """Test dass load_problem Methode existiert."""
        assert "def _load_problem" in screen_file
        assert "ProblemManager" in screen_file
        assert "get_problem" in screen_file
    
    def test_shows_details(self, screen_file):
        """Test dass Details angezeigt werden."""
        assert "problem.title" in screen_file
        assert "problem.problem_type" in screen_file
        assert "problem.status" in screen_file
        assert "problem.raw_description" in screen_file


class TestAppIntegration:
    """Tests für App-Integration."""
    
    @pytest.fixture
    def app_file(self):
        """Lädt den Datei-Inhalt."""
        file_path = Path(__file__).parent.parent / "src" / "tui" / "app.py"
        return file_path.read_text()
    
    def test_file_exists(self):
        """Test dass Datei existiert."""
        file_path = Path(__file__).parent.parent / "src" / "tui" / "app.py"
        assert file_path.exists()
    
    def test_syntax_valid(self):
        """Test dass Python-Syntax valide ist."""
        file_path = Path(__file__).parent.parent / "src" / "tui" / "app.py"
        code = file_path.read_text()
        ast.parse(code)
    
    def test_has_problem_import(self, app_file):
        """Test dass Problem-Solver importiert wird."""
        assert "ProblemOverviewScreen" in app_file
        assert "from tui.screens.problem_overview" in app_file
    
    def test_has_problem_button(self, app_file):
        """Test dass Problem-Solver Button existiert."""
        assert "btn-problems" in app_file
        assert "Problem-Solver" in app_file
    
    def test_has_problem_binding(self, app_file):
        """Test dass F4 Binding existiert."""
        assert '"f4"' in app_file
        assert "problems" in app_file
    
    def test_has_problem_action(self, app_file):
        """Test dass action_problems existiert."""
        assert "def action_problems" in app_file
        assert "ProblemOverviewScreen" in app_file
    
    def test_has_repo_path_property(self, app_file):
        """Test dass repo_path Property existiert."""
        assert "def repo_path" in app_file
        assert "return self.selected_path" in app_file
    
    def test_has_button_handler(self, app_file):
        """Test dass Button-Handler existiert."""
        assert "btn-problems" in app_file
        assert "action_problems" in app_file


class TestIntegration:
    """Integrationstests für kompletten Workflow mit ProblemManager."""
    
    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Erstellt temporäres Repository."""
        repo = tmp_path / "test_repo"
        repo.mkdir()
        (repo / ".glitchhunter").mkdir()
        return repo
    
    def test_full_workflow(self, temp_repo):
        """Kompletter Workflow: Create -> List -> Show -> Classify."""
        from problem.manager import ProblemManager
        
        # 1. Problem erstellen
        manager = ProblemManager(repo_path=temp_repo)
        problem = manager.intake_problem(
            description="Die API ist sehr langsam",
            title="API Performance",
        )
        
        assert problem.id.startswith("prob_")
        assert problem.title == "API Performance"
        assert problem.status.value == "intake"
        
        # 2. Problem auflisten
        problems = manager.list_problems()
        assert len(problems) == 1
        assert problems[0].id == problem.id
        
        # 3. Problem Details laden
        loaded_problem = manager.get_problem(problem.id)
        assert loaded_problem is not None
        assert loaded_problem.id == problem.id
        
        # 4. Problem klassifizieren
        classification = manager.classify_problem(problem.id)
        assert classification is not None
        assert classification.problem_type is not None
        assert classification.confidence >= 0
        assert classification.confidence <= 1
        
        # 5. Statistik
        stats = manager.get_statistics()
        assert stats["total_problems"] == 1
        assert "by_type" in stats
        assert "by_status" in stats
    
    def test_problem_manager_delete(self, temp_repo):
        """Test Problem löschen."""
        from problem.manager import ProblemManager
        
        manager = ProblemManager(repo_path=temp_repo)
        problem = manager.intake_problem("Test Problem")
        
        # Löschen
        result = manager.delete_problem(problem.id)
        assert result is True
        
        # Sollte nicht mehr existieren
        loaded = manager.get_problem(problem.id)
        assert loaded is None
    
    def test_problem_manager_filter_by_status(self, temp_repo):
        """Test Filter nach Status."""
        from problem.manager import ProblemManager
        from problem.models import ProblemStatus
        
        manager = ProblemManager(repo_path=temp_repo)
        manager.intake_problem("Problem A")
        manager.intake_problem("Problem B")
        
        # Filter nach intake (alle sollten im intake Status sein)
        problems = manager.list_problems(status_filter=ProblemStatus.INTAKE)
        assert len(problems) == 2
        
        for problem in problems:
            assert problem.status == ProblemStatus.INTAKE
    
    def test_problem_with_goal(self, temp_repo):
        """Test Problem mit Zielzustand."""
        from problem.manager import ProblemManager
        
        manager = ProblemManager(repo_path=temp_repo)
        problem = manager.intake_problem(
            description="Das Startup ist zu langsam",
            title="Startup Performance",
        )
        
        # Goal kann nachträglich gesetzt werden
        updated = problem.with_updates(
            goal_state="Startup unter 2 Sekunden",
        )
        
        assert updated.goal_state == "Startup unter 2 Sekunden"
        assert updated.id == problem.id  # ID bleibt gleich
    
    def test_problem_with_components(self, temp_repo):
        """Test Problem mit Komponenten."""
        from problem.manager import ProblemManager
        
        manager = ProblemManager(repo_path=temp_repo)
        problem = manager.intake_problem(
            description="API Timeout bei großen Anfragen",
        )
        
        # Komponenten können nachträglich gesetzt werden
        updated = problem.with_updates(
            affected_components=["API", "Database", "Cache"],
        )
        
        assert len(updated.affected_components) == 3
        assert "API" in updated.affected_components


class TestScreensInitFile:
    """Tests für screens/__init__.py."""
    
    def test_init_file_exists(self):
        """Test dass __init__.py existiert."""
        file_path = Path(__file__).parent.parent / "src" / "tui" / "screens" / "__init__.py"
        assert file_path.exists()
