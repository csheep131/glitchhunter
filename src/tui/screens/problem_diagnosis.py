"""
Problem Diagnosis Screen - Diagnose-Ansicht für Probleme.

Zeigt:
- Ursachen (Root Causes, Contributing Factors)
- Datenflüsse
- Unsicherheiten
- Empfohlene nächste Schritte
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
    DataTable,
)
from textual.binding import Binding
from typing import Optional, Any


class ProblemDiagnosisScreen(Screen):
    """Diagnose-Ansicht für ein Problem."""

    CSS = """
    ProblemDiagnosisScreen {
        align: center middle;
    }

    #diagnosis-container {
        width: 90%;
        height: 85%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #diagnosis-title {
        text-align: center;
        text-style: bold;
        padding: 1 0;
    }

    #diagnosis-content {
        height: 75%;
    }

    .diagnosis-section {
        margin: 1 0;
        border: solid $primary-darken-1;
        padding: 1;
    }

    .diagnosis-section Label {
        text-style: bold;
        color: $text-muted;
    }

    .cause-item {
        margin: 0 0 1 0;
        padding: 0 0 0 1;
        border-left: thick $error;
    }

    .cause-root {
        border-left: thick $success;
    }

    .uncertainty-item {
        margin: 0 0 1 0;
        padding: 0 0 0 1;
        border-left: thick $warning;
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
        Binding("d", "decompose", "Zerlegen"),
        Binding("escape", "back", "Zurück"),
    ]

    def __init__(self, repo_path: str, problem_id: str):
        """
        Initialisiert ProblemDiagnosisScreen.

        Args:
            repo_path: Pfad zum Repository
            problem_id: ID des Problems
        """
        super().__init__()
        self.repo_path = repo_path
        self.problem_id = problem_id
        self.diagnosis: Optional[Any] = None

    def compose(self) -> ComposeResult:
        """UI-Komponenten zusammenstellen."""
        yield Header(show_clock=True)

        with Container(id="diagnosis-container"):
            yield Static(f"🔍 Diagnose: {self.problem_id}", id="diagnosis-title")

            with ScrollableContainer(id="diagnosis-content"):
                # Wird dynamisch gefüllt in on_mount
                pass

            with Horizontal(id="action-row"):
                yield Button(
                    "📊 Zerlegen",
                    id="decompose-button",
                    variant="primary",
                )
                yield Button(
                    "🔄 Aktualisieren",
                    id="refresh-button",
                    variant="default",
                )

        yield Footer()

    def on_mount(self) -> None:
        """Diagnose laden."""
        self._load_diagnosis()

    def _load_diagnosis(self) -> None:
        """Diagnose-Daten laden und anzeigen."""
        try:
            from problem.manager import ProblemManager
            from pathlib import Path

            manager = ProblemManager(repo_path=Path(self.repo_path))
            self.diagnosis = manager.get_diagnosis(self.problem_id)

            # Falls keine Diagnose existiert, erst generieren
            if not self.diagnosis:
                self.notify(
                    "⚠️ Keine Diagnose vorhanden. Generiere...",
                    severity="warning",
                )
                self.diagnosis = manager.generate_diagnosis(self.problem_id)

            # Content aufbauen
            self._build_content()

        except ValueError as e:
            self.notify(f"❌ Fehler: {e}", severity="error")
            self.app.pop_screen()
        except Exception as e:
            self.notify(f"❌ Unerwarteter Fehler: {e}", severity="error")
            self.app.pop_screen()

    def _build_content(self) -> None:
        """Buildet Diagnose-Content."""
        if not self.diagnosis:
            return

        content = self.query_one("#diagnosis-content", ScrollableContainer)
        content.remove_children()

        # Zusammenfassung
        with Vertical(classes="diagnosis-section"):
            yield Static("**Zusammenfassung**")
            yield Static(self.diagnosis.summary)

        # Root Causes
        root_causes = self.diagnosis.get_root_causes()
        if root_causes:
            with Vertical(classes="diagnosis-section"):
                yield Static(f"**🎯 Root Causes ({len(root_causes)})**")
                for cause in root_causes:
                    icon = "🚨" if cause.is_blocking else "⚠️"
                    yield Static(
                        f"{icon} {cause.description}\n"
                        f"   Confidence: {cause.confidence:.0%}",
                        classes="cause-item cause-root",
                    )

        # Contributing Causes
        contributing = [
            c for c in self.diagnosis.causes
            if c.cause_type.name == "CONTRIBUTING"
        ]
        if contributing:
            with Vertical(classes="diagnosis-section"):
                yield Static(f"**🔧 Contributing Factors ({len(contributing)})**")
                for cause in contributing:
                    yield Static(
                        f"• {cause.description}\n"
                        f"   Confidence: {cause.confidence:.0%}",
                        classes="cause-item",
                    )

        # Datenflüsse
        if self.diagnosis.data_flows:
            with Vertical(classes="diagnosis-section"):
                yield Static(f"**🔄 Datenflüsse ({len(self.diagnosis.data_flows)})**")
                for flow in self.diagnosis.data_flows:
                    yield Static(
                        f"**{flow.name}**\n"
                        f"   {flow.source} → {flow.sink}",
                    )
                    if flow.issues:
                        for issue in flow.issues:
                            yield Static(f"   ⚠️ {issue}")

        # Unsicherheiten
        if self.diagnosis.uncertainties:
            with Vertical(classes="diagnosis-section"):
                yield Static(f"**❓ Unsicherheiten ({len(self.diagnosis.uncertainties)})**")
                high_impact = self.diagnosis.get_high_impact_uncertainties()

                for unc in high_impact:
                    yield Static(
                        f"🔴 {unc.question}\n"
                        f"   Impact: {unc.impact}",
                        classes="uncertainty-item",
                    )

                other = [u for u in self.diagnosis.uncertainties if u not in high_impact]
                for unc in other:
                    yield Static(
                        f"🟡 {unc.question}",
                        classes="uncertainty-item",
                    )

        # Nächste Schritte
        if self.diagnosis.recommended_next_steps:
            with Vertical(classes="diagnosis-section"):
                yield Static(f"**📋 Nächste Schritte**")
                for i, step in enumerate(self.diagnosis.recommended_next_steps, 1):
                    yield Static(f"{i}. {step}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Button-Clicks verarbeiten."""
        if event.button.id == "decompose-button":
            self.action_decompose()
        elif event.button.id == "refresh-button":
            self._load_diagnosis()
            self.notify("🔄 Aktualisiert", severity="information")

    def action_decompose(self) -> None:
        """Zur Decomposition übergehen."""
        from .problem_decomposition import ProblemDecompositionScreen
        self.app.push_screen(
            ProblemDecompositionScreen(
                repo_path=self.repo_path,
                problem_id=self.problem_id,
            )
        )

    def action_back(self) -> None:
        """Zurück zur Übersicht."""
        self.app.pop_screen()
