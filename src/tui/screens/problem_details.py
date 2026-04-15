"""
Problem Details Screen - Detaillierte Problem-Ansicht.

Zeigt alle Details eines ausgewählten Problems inklusive:
- Basis-Informationen (ID, Titel, Typ, Status)
- Beschreibung und Zielzustand
- Betroffene Komponenten
- Erfolgskriterien und Constraints
- Metadaten
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
)
from textual.binding import Binding
from typing import Optional, Any


class ProblemDetailsScreen(Screen):
    """Detail-Ansicht für ein Problem."""
    
    CSS = """
    ProblemDetailsScreen {
        align: center middle;
    }
    
    #details-container {
        width: 85%;
        height: 85%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    
    #details-title {
        text-align: center;
        text-style: bold;
        padding: 1 0;
    }
    
    #details-content {
        height: 75%;
    }
    
    .detail-section {
        margin: 1 0;
        border: solid $primary-darken-1;
        padding: 1;
    }
    
    .detail-section Label {
        text-style: bold;
        color: $text-muted;
    }
    
    .detail-section Static {
        margin: 0 0 1 0;
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
        Binding("e", "edit", "Bearbeiten"),
        Binding("c", "classify", "Klassifizieren"),
        Binding("escape", "back", "Zurück"),
    ]
    
    def __init__(self, repo_path: str, problem_id: str):
        """
        Initialisiert ProblemDetailsScreen.
        
        Args:
            repo_path: Pfad zum Repository
            problem_id: ID des anzuzeigenden Problems
        """
        super().__init__()
        self.repo_path = repo_path
        self.problem_id = problem_id
        self.problem: Optional[Any] = None
    
    def compose(self) -> ComposeResult:
        """UI-Komponenten zusammenstellen."""
        yield Header(show_clock=True)
        
        with Container(id="details-container"):
            yield Static(f"📄 Problem-Details: {self.problem_id}", id="details-title")
            
            with ScrollableContainer(id="details-content"):
                # Wird dynamisch gefüllt in on_mount
                yield Static("Lade Problem-Daten...", id="loading-message")
            
            with Horizontal(id="action-row"):
                yield Button(
                    "✏️ Bearbeiten",
                    id="edit-button",
                    variant="primary",
                )
                yield Button(
                    "🔍 Klassifizieren",
                    id="classify-button",
                    variant="warning",
                )
                yield Button(
                    "🔄 Aktualisieren",
                    id="refresh-button",
                    variant="default",
                )
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Problem-Daten laden."""
        self._load_problem()
    
    def _load_problem(self) -> None:
        """Problem-Daten laden und anzeigen."""
        try:
            from problem.manager import ProblemManager
            from pathlib import Path
            
            manager = ProblemManager(repo_path=Path(self.repo_path))
            self.problem = manager.get_problem(self.problem_id)
            
            if not self.problem:
                self.notify(
                    f"❌ Problem {self.problem_id} nicht gefunden",
                    severity="error",
                )
                self.app.pop_screen()
                return
            
            # Content aufbauen
            content = self.query_one("#details-content", ScrollableContainer)
            
            # Loading-Nachricht entfernen
            try:
                loading = content.query_one("#loading-message", Static)
                loading.remove()
            except Exception:
                pass
            
            # Basis-Informationen
            with Vertical(classes="detail-section"):
                yield Static(f"**ID:** {self.problem.id}")
                yield Static(f"**Titel:** {self.problem.title}")
                yield Static(f"**Typ:** {self.problem.problem_type.value}")
                yield Static(f"**Status:** {self.problem.status.value}")
                yield Static(f"**Schweregrad:** {self.problem.severity.value}")
                yield Static(f"**Erstellt:** {self.problem.created_at}")
                yield Static(f"**Aktualisiert:** {self.problem.updated_at}")
            
            # Beschreibung
            with Vertical(classes="detail-section"):
                yield Label("Beschreibung:")
                yield Static(self.problem.raw_description)
            
            # Zielzustand
            if self.problem.goal_state:
                with Vertical(classes="detail-section"):
                    yield Label("Zielzustand:")
                    yield Static(self.problem.goal_state)
            
            # Betroffene Komponenten
            if self.problem.affected_components:
                with Vertical(classes="detail-section"):
                    yield Label("Betroffene Komponenten:")
                    for comp in self.problem.affected_components:
                        yield Static(f"  • {comp}")
            
            # Erfolgskriterien
            if self.problem.success_criteria:
                with Vertical(classes="detail-section"):
                    yield Label("Erfolgskriterien:")
                    for criteria in self.problem.success_criteria:
                        yield Static(f"  • {criteria}")
            
            # Constraints
            if self.problem.constraints:
                with Vertical(classes="detail-section"):
                    yield Label("Constraints:")
                    for constraint in self.problem.constraints:
                        yield Static(f"  • {constraint}")
            
            # Verweise
            if self.problem.related_files:
                with Vertical(classes="detail-section"):
                    yield Label("Verwandte Dateien:")
                    for file_path in self.problem.related_files:
                        yield Static(f"  • {file_path}")
            
            if self.problem.related_findings:
                with Vertical(classes="detail-section"):
                    yield Label("Verwandte Findings:")
                    for finding_id in self.problem.related_findings:
                        yield Static(f"  • {finding_id}")
            
        except Exception as e:
            self.notify(
                f"❌ Fehler beim Laden: {e}",
                severity="error",
            )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Button-Clicks verarbeiten."""
        button_id = event.button.id
        
        if button_id == "edit-button":
            self.action_edit()
        elif button_id == "classify-button":
            self.action_classify()
        elif button_id == "refresh-button":
            self._load_problem()
            self.notify("🔄 Aktualisiert", severity="information")
    
    def action_edit(self) -> None:
        """Problem bearbeiten (zukünftig)."""
        self.notify(
            "⚠️ Bearbeiten kommt in nächster Version",
            severity="warning",
        )
    
    def action_classify(self) -> None:
        """Problem klassifizieren."""
        if not self.problem:
            self.notify(
                "⚠️ Problem nicht geladen",
                severity="warning",
            )
            return
        
        try:
            from problem.manager import ProblemManager
            from pathlib import Path
            
            manager = ProblemManager(repo_path=Path(self.repo_path))
            result = manager.classify_problem(self.problem_id)
            
            self.notify(
                f"✅ Klassifiziert: {result.problem_type.value} "
                f"({result.confidence:.0%})",
                severity="information",
            )
            
            # Reload
            self._load_problem()
            
        except ValueError as e:
            self.notify(f"❌ Fehler: {e}", severity="error")
        except Exception as e:
            self.notify(f"❌ Fehler: {e}", severity="error")
    
    def action_back(self) -> None:
        """Zurück zur Übersicht."""
        self.app.pop_screen()
