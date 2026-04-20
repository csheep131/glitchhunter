"""
Problem Solution Plan Screen - Lösungsplan-Ansicht.

Zeigt:
- Lösungspfade pro Teilproblem
- Bewertung (Score, Wirksamkeit, Aufwand, Risiko)
- Ausgewählte Pfade
- Stack-Empfehlung
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import (
    Header,
    Footer,
    Static,
    Button,
    Label,
    Select,
)
from textual.binding import Binding
from typing import Optional, Any, Dict


class ProblemSolutionPlanScreen(Screen):
    """Lösungsplan-Ansicht für ein Problem."""

    CSS = """
    ProblemSolutionPlanScreen {
        align: center middle;
    }

    #plan-container {
        width: 90%;
        height: 85%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #plan-title {
        text-align: center;
        text-style: bold;
        padding: 1 0;
    }

    #plan-content {
        height: 70%;
    }

    .path-section {
        margin: 1 0;
    }

    .path-item {
        margin: 0 0 1 0;
        padding: 1;
        border: solid $primary-darken-1;
    }

    .path-selected {
        border: thick $success;
        background: $success-darken-2;
    }

    .path-high-risk {
        border-left: thick $error;
    }

    .quick-win {
        border-left: thick $warning;
    }

    #stack-recommendation {
        height: auto;
        margin: 1 0;
        padding: 1;
        background: $primary-darken-2;
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
        Binding("s", "select_stack", "Stack wählen"),
        Binding("escape", "back", "Zurück"),
    ]

    def __init__(self, repo_path: str, problem_id: str):
        """
        Initialisiert ProblemSolutionPlanScreen.

        Args:
            repo_path: Pfad zum Repository
            problem_id: ID des Problems
        """
        super().__init__()
        self.repo_path = repo_path
        self.problem_id = problem_id
        self.plan: Optional[Any] = None

    def compose(self) -> ComposeResult:
        """UI-Komponenten zusammenstellen."""
        yield Header(show_clock=True)

        with Container(id="plan-container"):
            yield Static(f"📋 Lösungsplan: {self.problem_id}", id="plan-title")

            with ScrollableContainer(id="plan-content"):
                # Wird dynamisch gefüllt in on_mount
                pass

            # Stack-Empfehlung
            yield Static("", id="stack-recommendation")

            with Horizontal(id="action-row"):
                yield Button(
                    "🖥️ Stack wählen",
                    id="stack-button",
                    variant="primary",
                )
                yield Button(
                    "🔄 Aktualisieren",
                    id="refresh-button",
                    variant="default",
                )

        yield Footer()

    def on_mount(self) -> None:
        """Lösungsplan laden."""
        self._load_plan()

    def _load_plan(self) -> None:
        """Lösungsplan-Daten laden."""
        try:
            from problem.manager import ProblemManager
            from pathlib import Path

            manager = ProblemManager(repo_path=Path(self.repo_path))
            self.plan = manager.get_solution_plan(self.problem_id)

            # Falls kein Plan, erst generieren
            if not self.plan:
                self.notify(
                    "⚠️ Kein Lösungsplan vorhanden. Generiere...",
                    severity="warning",
                )
                self.plan = manager.create_solution_plan(self.problem_id)

            # Content aufbauen
            self._build_content()

            # Stack-Empfehlung anzeigen
            self._show_stack_recommendation()

        except ValueError as e:
            self.notify(f"❌ Fehler: {e}", severity="error")
            self.app.pop_screen()
        except Exception as e:
            self.notify(f"❌ Unerwarteter Fehler: {e}", severity="error")
            self.app.pop_screen()

    def _build_content(self) -> None:
        """Buildet Plan-Content."""
        if not self.plan:
            return

        content = self.query_one("#plan-content", ScrollableContainer)
        content.remove_children()

        # Für jedes Teilproblem Lösungspfade anzeigen
        for sp_id, paths in self.plan.solution_paths.items():
            with Vertical(classes="path-section"):
                yield Static(f"**Teilproblem: {sp_id}**")

                # Nach Score sortiert
                sorted_paths = sorted(
                    paths,
                    key=lambda p: p.overall_score(),
                    reverse=True,
                )

                for path in sorted_paths:
                    selected = (
                        self.plan.selected_paths.get(sp_id) == path.id
                    )
                    classes = "path-item"
                    if selected:
                        classes += " path-selected"
                    elif path.is_high_risk():
                        classes += " path-high-risk"
                    elif path.is_quick_win():
                        classes += " quick-win"

                    # Score-Visualisierung
                    score = path.overall_score()
                    score_bars = "█" * int(score) + "░" * (10 - int(score))

                    icons = []
                    if selected:
                        icons.append("✅")
                    if path.is_quick_win():
                        icons.append("💡")
                    if path.is_high_risk():
                        icons.append("⚠️")

                    yield Static(
                        f"{' '.join(icons)} **{path.title}** (Score: {score:.1f})\n"
                        f"   {score_bars}\n"
                        f"   Typ: {path.solution_type.value} | "
                        f"Wirksamkeit: {path.effectiveness}/10 | "
                        f"Aufwand: {path.effort}/10 ({path.estimated_hours or '?'}h) | "
                        f"Risiko: {path.risk.value}\n"
                        f"   Schritte: {len(path.implementation_steps)}",
                        classes=classes,
                    )

    def _show_stack_recommendation(self) -> None:
        """Zeigt Stack-Empfehlung."""
        if not self.plan:
            return

        view = self.query_one("#stack-recommendation", Static)

        try:
            from problem.manager import ProblemManager
            from pathlib import Path

            manager = ProblemManager(repo_path=Path(self.repo_path))
            recommendation = manager.recommend_stack_for_problem(self.problem_id)

            profile = manager.get_stack_profile(recommendation)

            view.update(
                f"**🖥️ Stack-Empfehlung:** {profile.name if profile else recommendation}\n"
                f"   {profile.description if profile else ''}"
            )

        except Exception as e:
            view.update(f"**⚠️ Stack-Empfehlung nicht verfügbar:** {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Button-Clicks verarbeiten."""
        if event.button.id == "stack-button":
            self.action_select_stack()
        elif event.button.id == "refresh-button":
            self._load_plan()
            self.notify("🔄 Aktualisiert", severity="information")

    def action_select_stack(self) -> None:
        """Stack-Auswahl anzeigen."""
        from .problem_stack_select import ProblemStackSelectScreen
        self.app.push_screen(
            ProblemStackSelectScreen(
                repo_path=self.repo_path,
                problem_id=self.problem_id,
            )
        )

    def action_back(self) -> None:
        """Zurück zur Decomposition."""
        self.app.pop_screen()
