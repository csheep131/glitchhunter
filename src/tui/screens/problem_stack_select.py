"""
Problem Stack Select Screen - Stack-Auswahl.

Ermöglicht die Auswahl zwischen Stack A (Standard) und Stack B (Enhanced)
für die Problemlösung.
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import (
    Header,
    Footer,
    Static,
    Button,
    Label,
)
from textual.binding import Binding
from typing import Optional


class ProblemStackSelectScreen(Screen):
    """Stack-Auswahl für ein Problem."""

    CSS = """
    ProblemStackSelectScreen {
        align: center middle;
    }

    #stack-container {
        width: 80%;
        height: 75%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #stack-title {
        text-align: center;
        text-style: bold;
        padding: 1 0;
    }

    .stack-option {
        margin: 1 0;
        padding: 1;
        border: solid $primary;
    }

    .stack-selected {
        border: thick $success;
        background: $success-darken-2;
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
        Binding("1", "select_stack_a", "Stack A"),
        Binding("2", "select_stack_b", "Stack B"),
        Binding("escape", "back", "Zurück"),
    ]

    def __init__(self, repo_path: str, problem_id: str):
        """
        Initialisiert ProblemStackSelectScreen.

        Args:
            repo_path: Pfad zum Repository
            problem_id: ID des Problems
        """
        super().__init__()
        self.repo_path = repo_path
        self.problem_id = problem_id
        self.selected_stack: str = "stack_a"

    def compose(self) -> ComposeResult:
        """UI-Komponenten zusammenstellen."""
        yield Header(show_clock=True)

        with Container(id="stack-container"):
            yield Static("🖥️ Stack auswählen", id="stack-title")

            # Stack A Option
            with Vertical(
                id="stack-a-option",
                classes="stack-option stack-selected",
            ):
                yield Static("**Stack A (Standard)**")
                yield Static("8GB VRAM, 32GB RAM, 8 CPU-Cores")
                yield Static("Capabilities: 14/15 unterstützt")
                yield Static("Features: TUI, API, Enhanced Reports")

            # Stack B Option
            with Vertical(
                id="stack-b-option",
                classes="stack-option",
            ):
                yield Static("**Stack B (Enhanced)**")
                yield Static("24GB VRAM, 64GB RAM, 16 CPU-Cores")
                yield Static("Capabilities: 15/15 unterstützt (3 enhanced)")
                yield Static(
                    "Features: Ensemble, Multi-Model, Parallel Fuzzing, Auto-Fix"
                )

            with Horizontal(id="action-row"):
                yield Button(
                    "1️⃣ Stack A",
                    id="stack-a-button",
                    variant="primary",
                )
                yield Button(
                    "2️⃣ Stack B",
                    id="stack-b-button",
                    variant="primary",
                )
                yield Button(
                    "✅ Auswählen",
                    id="confirm-button",
                    variant="success",
                )

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Button-Clicks verarbeiten."""
        if event.button.id == "stack-a-button":
            self.action_select_stack_a()
        elif event.button.id == "stack-b-button":
            self.action_select_stack_b()
        elif event.button.id == "confirm-button":
            self.action_confirm()

    def _update_selection_ui(self) -> None:
        """Aktualisiert UI für Auswahl."""
        try:
            a_option = self.query_one("#stack-a-option", Vertical)
            b_option = self.query_one("#stack-b-option", Vertical)

            if self.selected_stack == "stack_a":
                a_option.add_class("stack-selected")
                b_option.remove_class("stack-selected")
            else:
                a_option.remove_class("stack-selected")
                b_option.add_class("stack-selected")
        except Exception:
            # Widgets might not be ready yet
            pass

    def action_select_stack_a(self) -> None:
        """Stack A auswählen."""
        self.selected_stack = "stack_a"
        self._update_selection_ui()
        self.notify("Stack A (Standard) ausgewählt", severity="information")

    def action_select_stack_b(self) -> None:
        """Stack B auswählen."""
        self.selected_stack = "stack_b"
        self._update_selection_ui()
        self.notify("Stack B (Enhanced) ausgewählt", severity="information")

    def action_confirm(self) -> None:
        """Auswahl bestätigen."""
        # In echter Implementierung: Im ProblemCase speichern
        # Hier nur Benachrichtigung
        self.notify(
            f"✅ Stack {self.selected_stack} ausgewählt",
            severity="information",
        )
        self.app.pop_screen()

    def action_back(self) -> None:
        """Zurück zum Lösungsplan."""
        self.app.pop_screen()
