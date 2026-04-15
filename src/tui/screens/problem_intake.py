"""
Problem Intake Screen - Eingabemaske für neue Probleme.

Nutzer kann hier:
- Problembeschreibung eingeben
- Titel bearbeiten
- Problemtyp auswählen (oder automatisch erkennen lassen)
- Zielzustand definieren
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import (
    Header,
    Footer,
    Static,
    Input,
    TextArea,
    Button,
    Label,
)
from textual.binding import Binding


class ProblemIntakeScreen(Screen):
    """Screen für Problemaufnahme."""
    
    CSS = """
    ProblemIntakeScreen {
        align: center middle;
    }
    
    #intake-container {
        width: 80%;
        height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    
    #intake-title {
        text-align: center;
        text-style: bold;
        padding: 1 0;
    }
    
    #intake-form {
        height: 100%;
    }
    
    .form-group {
        margin: 1 0;
    }
    
    .form-group Label {
        text-style: bold;
        color: $text-muted;
    }
    
    #description-input {
        height: 40%;
        border: solid $primary;
    }
    
    #button-row {
        height: auto;
        margin-top: 1;
        align: center middle;
    }
    
    Button {
        margin: 0 1;
        min-width: 15;
    }
    
    #submit-button {
        background: $success;
    }
    
    #cancel-button {
        background: $error;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+s", "submit", "Speichern"),
        Binding("escape", "cancel", "Abbrechen"),
    ]
    
    def __init__(self, repo_path: str):
        """
        Initialisiert ProblemIntakeScreen.
        
        Args:
            repo_path: Pfad zum Repository
        """
        super().__init__()
        self.repo_path = repo_path
    
    def compose(self) -> ComposeResult:
        """UI-Komponenten zusammenstellen."""
        yield Header(show_clock=True)
        
        with Container(id="intake-container"):
            yield Static("📝 Neues Problem aufnehmen", id="intake-title")
            
            with Vertical(id="intake-form"):
                # Titel
                with Vertical(classes="form-group"):
                    yield Label("Titel (optional):")
                    yield Input(
                        placeholder="Kurzer Titel für das Problem...",
                        id="title-input",
                    )
                
                # Beschreibung
                with Vertical(classes="form-group"):
                    yield Label("Problembeschreibung:")
                    yield TextArea(
                        language="markdown",
                        id="description-input",
                        placeholder=(
                            "Beschreibe das Problem so detailliert wie möglich...\n\n"
                            "Beispiele:\n"
                            "- 'Das Startup ist zu langsam'\n"
                            "- 'STL-Dateien werden nicht verarbeitet'\n"
                            "- 'Ich möchte diesen Schritt automatisieren'"
                        ),
                    )
                
                # Zielzustand
                with Vertical(classes="form-group"):
                    yield Label("Zielzustand (optional):")
                    yield Input(
                        placeholder="Was soll erreicht werden?...",
                        id="goal-input",
                    )
                
                # Button-Row
                with Horizontal(id="button-row"):
                    yield Button(
                        "📤 Speichern",
                        id="submit-button",
                        variant="success",
                    )
                    yield Button(
                        "❌ Abbrechen",
                        id="cancel-button",
                        variant="error",
                    )
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Fokus auf Titel-Input setzen."""
        try:
            self.query_one("#title-input", Input).focus()
        except Exception:
            pass  # Widget might not be ready yet
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Button-Clicks verarbeiten."""
        if event.button.id == "submit-button":
            self.action_submit()
        elif event.button.id == "cancel-button":
            self.action_cancel()
    
    def action_submit(self) -> None:
        """Problem speichern."""
        # Werte auslesen
        try:
            title_input = self.query_one("#title-input", Input)
            description_input = self.query_one("#description-input", TextArea)
            goal_input = self.query_one("#goal-input", Input)
            
            title = title_input.value
            description = description_input.text
            goal = goal_input.value
        except Exception as e:
            self.notify(
                f"❌ Fehler beim Auslesen: {e}",
                severity="error",
            )
            return
        
        # Validierung
        if not description or not description.strip():
            self.notify(
                "⚠️ Bitte gib eine Problembeschreibung ein",
                severity="error",
            )
            return
        
        # Problem erstellen (über Parent-App)
        try:
            from problem.manager import ProblemManager
            from pathlib import Path
            
            manager = ProblemManager(repo_path=Path(self.repo_path))
            problem = manager.intake_problem(
                description=description,
                title=title if title else None,
                source="tui",
            )
            
            # Erfolgsmeldung
            self.notify(
                f"✅ Problem erstellt: {problem.id}",
                severity="information",
            )
            
            # Zurück zur Problem-Übersicht
            from .problem_overview import ProblemOverviewScreen
            self.app.pop_screen()
            self.app.push_screen(
                ProblemOverviewScreen(repo_path=self.repo_path)
            )
            
        except Exception as e:
            self.notify(
                f"❌ Fehler beim Speichern: {e}",
                severity="error",
            )
    
    def action_cancel(self) -> None:
        """Vorgang abbrechen."""
        self.app.pop_screen()
