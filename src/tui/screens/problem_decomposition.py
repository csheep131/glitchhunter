"""
Problem Decomposition Screen - Zerlegungs-Ansicht.

Zeigt:
- Teilprobleme mit Dependencies
- Ausführungsreihenfolge
- Status je Teilproblem
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import (
    Header,
    Footer,
    Static,
    Button,
    DataTable,
    Label,
)
from textual.binding import Binding
from typing import Optional, Any


class ProblemDecompositionScreen(Screen):
    """Decomposition-Ansicht für ein Problem."""

    CSS = """
    ProblemDecompositionScreen {
        align: center middle;
    }

    #decomposition-container {
        width: 90%;
        height: 85%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #decomposition-title {
        text-align: center;
        text-style: bold;
        padding: 1 0;
    }

    #decomposition-table {
        height: 60%;
        border: solid $primary;
    }

    #dependency-view {
        height: 15%;
        border: solid $primary-darken-1;
        margin: 1 0;
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
        Binding("p", "plan", "Lösungsplan"),
        Binding("r", "refresh", "Aktualisieren"),
        Binding("escape", "back", "Zurück"),
    ]

    def __init__(self, repo_path: str, problem_id: str):
        """
        Initialisiert ProblemDecompositionScreen.

        Args:
            repo_path: Pfad zum Repository
            problem_id: ID des Problems
        """
        super().__init__()
        self.repo_path = repo_path
        self.problem_id = problem_id
        self.decomposition: Optional[Any] = None

    def compose(self) -> ComposeResult:
        """UI-Komponenten zusammenstellen."""
        yield Header(show_clock=True)

        with Container(id="decomposition-container"):
            yield Static(
                f"📊 Decomposition: {self.problem_id}",
                id="decomposition-title",
            )

            # DataTable für Teilprobleme
            yield DataTable(id="decomposition-table")

            # Dependency-View (wird dynamisch gefüllt)
            yield Static("", id="dependency-view")

            # Action-Row
            with Horizontal(id="action-row"):
                yield Button(
                    "📋 Lösungsplan",
                    id="plan-button",
                    variant="primary",
                )
                yield Button(
                    "🔄 Aktualisieren",
                    id="refresh-button",
                    variant="default",
                )

        yield Footer()

    def on_mount(self) -> None:
        """Decomposition laden."""
        self._load_decomposition()

    def _load_decomposition(self) -> None:
        """Decomposition-Daten laden."""
        try:
            from problem.manager import ProblemManager
            from pathlib import Path

            manager = ProblemManager(repo_path=Path(self.repo_path))
            self.decomposition = manager.get_decomposition(self.problem_id)

            # Falls keine Decomposition, erst generieren
            if not self.decomposition:
                self.notify(
                    "⚠️ Keine Decomposition vorhanden. Generiere...",
                    severity="warning",
                )
                self.decomposition = manager.decompose_problem(self.problem_id)

            # Tabelle füllen
            self._populate_table()

            # Dependency-View aktualisieren
            self._update_dependency_view()

        except ValueError as e:
            self.notify(f"❌ Fehler: {e}", severity="error")
            self.app.pop_screen()
        except Exception as e:
            self.notify(f"❌ Unerwarteter Fehler: {e}", severity="error")
            self.app.pop_screen()

    def _populate_table(self) -> None:
        """Füllt DataTable mit Teilproblemen."""
        if not self.decomposition:
            return

        table = self.query_one("#decomposition-table", DataTable)
        table.clear()
        table.add_columns(
            "ID",
            "Titel",
            "Typ",
            "Priorität",
            "Status",
            "Dependencies",
        )

        # Nach Ausführungsreihenfolge sortieren
        order = self.decomposition.get_execution_order()

        for i, sp in enumerate(order, 1):
            status_icon = {
                "open": "⚪",
                "in_progress": "🔵",
                "blocked": "🔴",
                "done": "✅",
            }.get(sp.status, "⚪")

            deps = ", ".join(sp.dependencies) if sp.dependencies else "-"

            table.add_row(
                f"{i}. {sp.id}",
                sp.title[:30] + "..." if len(sp.title) > 30 else sp.title,
                sp.subproblem_type.value,
                str(sp.priority),
                f"{status_icon} {sp.status}",
                deps,
                key=sp.id,
            )

    def _update_dependency_view(self) -> None:
        """Aktualisiert Dependency-Ansicht."""
        if not self.decomposition:
            return

        view = self.query_one("#dependency-view", Static)

        stats = self.decomposition.get_statistics()

        view.update(
            f"**Statistik:** "
            f"Gesamt: {stats['total_subproblems']} | "
            f"Ready: {stats['ready_count']} | "
            f"Blocked: {stats['blocked_count']} | "
            f"Blocking: {stats['blocking_count']} | "
            f"Geschätzt: {stats['total_estimated_hours']:.1f}h"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Button-Clicks verarbeiten."""
        if event.button.id == "plan-button":
            self.action_plan()
        elif event.button.id == "refresh-button":
            self._load_decomposition()
            self.notify("🔄 Aktualisiert", severity="information")

    def action_plan(self) -> None:
        """Zum Lösungsplan übergehen."""
        from .problem_solution_plan import ProblemSolutionPlanScreen
        self.app.push_screen(
            ProblemSolutionPlanScreen(
                repo_path=self.repo_path,
                problem_id=self.problem_id,
            )
        )

    def action_back(self) -> None:
        """Zurück zur Diagnose."""
        self.app.pop_screen()
