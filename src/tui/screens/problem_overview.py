"""
Problem Overview Screen - Übersicht aller Probleme.

Zeigt:
- Liste aller Probleme
- Filter nach Status/Typ
- Schnelle Aktionen (show, classify, delete)
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import (
    Header,
    Footer,
    Static,
    DataTable,
    Button,
    Select,
    Label,
)
from textual.binding import Binding
from textual.reactive import reactive
from typing import Optional, List, Any


class ProblemOverviewScreen(Screen):
    """Übersicht aller Probleme."""
    
    CSS = """
    ProblemOverviewScreen {
        align: center middle;
    }
    
    #overview-container {
        width: 90%;
        height: 85%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    
    #overview-title {
        text-align: center;
        text-style: bold;
        padding: 1 0;
    }
    
    #filter-row {
        height: auto;
        margin: 1 0;
    }
    
    #filter-row Select {
        width: 20%;
        margin: 0 1;
    }
    
    #filter-row Label {
        width: 8;
    }
    
    #problems-table {
        height: 70%;
        border: solid $primary;
    }
    
    #action-row {
        height: auto;
        margin-top: 1;
        align: center middle;
    }
    
    Button {
        margin: 0 1;
        min-width: 15;
    }
    """
    
    BINDINGS = [
        Binding("n", "new_problem", "Neu"),
        Binding("s", "show_problem", "Anzeigen"),
        Binding("c", "classify_problem", "Klassifizieren"),
        Binding("d", "delete_problem", "Löschen"),
        Binding("r", "refresh", "Aktualisieren"),
        Binding("escape", "back", "Zurück"),
    ]
    
    # Reactive für Filter
    filter_status: reactive[Optional[str]] = reactive(None)
    filter_type: reactive[Optional[str]] = reactive(None)
    
    def __init__(self, repo_path: str):
        """
        Initialisiert ProblemOverviewScreen.
        
        Args:
            repo_path: Pfad zum Repository
        """
        super().__init__()
        self.repo_path = repo_path
        self.problems: List[Any] = []
    
    def compose(self) -> ComposeResult:
        """UI-Komponenten zusammenstellen."""
        yield Header(show_clock=True)
        
        with Container(id="overview-container"):
            yield Static("📋 Probleme Übersicht", id="overview-title")
            
            # Filter-Row
            with Horizontal(id="filter-row"):
                yield Label("Status:")
                yield Select(
                    [
                        ("Alle", None),
                        ("Intake", "intake"),
                        ("Diagnosis", "diagnosis"),
                        ("Planning", "planning"),
                        ("Implementation", "implementation"),
                        ("Validation", "validation"),
                        ("Closed", "closed"),
                    ],
                    value=None,
                    id="status-filter",
                    allow_blank=False,
                )
                
                yield Label("Typ:")
                yield Select(
                    [
                        ("Alle", None),
                        ("Bug", "bug"),
                        ("Performance", "performance"),
                        ("Missing Feature", "missing_feature"),
                        ("Workflow Gap", "workflow_gap"),
                        ("Integration Gap", "integration_gap"),
                        ("UX Issue", "ux_issue"),
                        ("Reliability", "reliability"),
                        ("Refactor", "refactor_required"),
                    ],
                    value=None,
                    id="type-filter",
                    allow_blank=False,
                )
            
            # DataTable
            yield DataTable(id="problems-table")
            
            # Action-Row
            with Horizontal(id="action-row"):
                yield Button(
                    "➕ Neu",
                    id="new-button",
                    variant="primary",
                )
                yield Button(
                    "👁️ Anzeigen",
                    id="show-button",
                    variant="default",
                )
                yield Button(
                    "🔍 Klassifizieren",
                    id="classify-button",
                    variant="warning",
                )
                yield Button(
                    "🗑️ Löschen",
                    id="delete-button",
                    variant="error",
                )
                yield Button(
                    "🔄 Aktualisieren",
                    id="refresh-button",
                    variant="default",
                )
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Tabelle initialisieren und Daten laden."""
        # DataTable konfigurieren
        table = self.query_one("#problems-table", DataTable)
        table.add_columns("ID", "Titel", "Typ", "Status", "Erstellt")
        
        # Daten laden
        self._load_problems()
    
    def _load_problems(self) -> None:
        """Probleme laden und in Tabelle anzeigen."""
        try:
            from problem.manager import ProblemManager
            from problem.models import ProblemStatus, ProblemType
            from pathlib import Path
            
            manager = ProblemManager(repo_path=Path(self.repo_path))
            
            # Filter anwenden
            status_filter: Optional[ProblemStatus] = None
            type_filter: Optional[ProblemType] = None
            
            if self.filter_status:
                try:
                    status_filter = ProblemStatus(self.filter_status)
                except ValueError:
                    pass
            
            if self.filter_type:
                try:
                    type_filter = ProblemType(self.filter_type)
                except ValueError:
                    pass
            
            # Probleme laden
            self.problems = manager.list_problems(
                status_filter=status_filter,
                type_filter=type_filter,
            )
            
            # Tabelle aktualisieren
            table = self.query_one("#problems-table", DataTable)
            table.clear()
            
            for problem in self.problems:
                # Titel auf 40 Zeichen kürzen
                title_display = problem.title[:40]
                if len(problem.title) > 40:
                    title_display += "..."
                
                table.add_row(
                    problem.id,
                    title_display,
                    problem.problem_type.value,
                    problem.status.value,
                    problem.created_at[:10],
                    key=problem.id,
                )
                
        except Exception as e:
            self.notify(
                f"❌ Fehler beim Laden: {e}",
                severity="error",
            )
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """Filter-Änderungen verarbeiten."""
        if event.select.id == "status-filter":
            self.filter_status = event.value
        elif event.select.id == "type-filter":
            self.filter_type = event.value
    
    def watch_filter_status(self, _: Any) -> None:
        """Bei Filter-Änderung Tabelle neu laden."""
        if self.is_mounted:
            self._load_problems()
    
    def watch_filter_type(self, _: Any) -> None:
        """Bei Filter-Änderung Tabelle neu laden."""
        if self.is_mounted:
            self._load_problems()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Button-Clicks verarbeiten."""
        button_id = event.button.id
        
        if button_id == "new-button":
            self.action_new_problem()
        elif button_id == "show-button":
            self.action_show_problem()
        elif button_id == "classify-button":
            self.action_classify_problem()
        elif button_id == "delete-button":
            self.action_delete_problem()
        elif button_id == "refresh-button":
            self.action_refresh()
    
    def _get_selected_problem_id(self) -> Optional[str]:
        """ID des ausgewählten Problems holen."""
        table = self.query_one("#problems-table", DataTable)
        if table.cursor_row is not None:
            try:
                row = table.get_row_at(table.cursor_row)
                if row and len(row) > 0:
                    return str(row[0])  # ID ist erste Spalte
            except Exception:
                pass
        return None
    
    def action_new_problem(self) -> None:
        """Neues Problem erstellen."""
        from .problem_intake import ProblemIntakeScreen
        self.app.push_screen(
            ProblemIntakeScreen(repo_path=self.repo_path)
        )
    
    def action_show_problem(self) -> None:
        """Problem-Details anzeigen."""
        problem_id = self._get_selected_problem_id()
        if not problem_id:
            self.notify(
                "⚠️ Bitte wähle ein Problem aus",
                severity="warning",
            )
            return
        
        from .problem_details import ProblemDetailsScreen
        self.app.push_screen(
            ProblemDetailsScreen(
                repo_path=self.repo_path,
                problem_id=problem_id,
            )
        )
    
    def action_classify_problem(self) -> None:
        """Problem klassifizieren."""
        problem_id = self._get_selected_problem_id()
        if not problem_id:
            self.notify(
                "⚠️ Bitte wähle ein Problem aus",
                severity="warning",
            )
            return
        
        # Klassifikation durchführen
        try:
            from problem.manager import ProblemManager
            from pathlib import Path
            
            manager = ProblemManager(repo_path=Path(self.repo_path))
            result = manager.classify_problem(problem_id)
            
            self.notify(
                f"✅ Klassifiziert: {result.problem_type.value} "
                f"({result.confidence:.0%})",
                severity="information",
            )
            
            # Tabelle aktualisieren
            self._load_problems()
            
        except ValueError as e:
            self.notify(f"❌ Fehler: {e}", severity="error")
        except Exception as e:
            self.notify(f"❌ Fehler: {e}", severity="error")
    
    def action_delete_problem(self) -> None:
        """Problem löschen."""
        problem_id = self._get_selected_problem_id()
        if not problem_id:
            self.notify(
                "⚠️ Bitte wähle ein Problem aus",
                severity="warning",
            )
            return
        
        # Bestätigung einholen (einfache Version)
        try:
            from problem.manager import ProblemManager
            from pathlib import Path
            
            manager = ProblemManager(repo_path=Path(self.repo_path))
            
            if manager.delete_problem(problem_id):
                self.notify(
                    f"✅ Problem {problem_id} gelöscht",
                    severity="information",
                )
                self._load_problems()
            else:
                self.notify(
                    "❌ Problem nicht gefunden",
                    severity="error",
                )
                
        except Exception as e:
            self.notify(f"❌ Fehler: {e}", severity="error")
    
    def action_refresh(self) -> None:
        """Ansicht aktualisieren."""
        self._load_problems()
        self.notify("🔄 Aktualisiert", severity="information")
    
    def action_back(self) -> None:
        """Zurück zum Hauptmenü."""
        self.app.pop_screen()
