"""Quick Scan Screen - Modal for starting analysis with options."""

from pathlib import Path
from textual.screen import ModalScreen
from textual.widgets import Static, Button, Checkbox, Label
from textual.containers import Vertical, Horizontal, Grid
from textual.reactive import reactive


class QuickScanScreen(ModalScreen):
    """Modal screen for quick analysis options."""

    DEFAULT_CSS = """
    QuickScanScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    
    #quick-scan-dialog {
        width: 60;
        height: auto;
        border: thick #3d5afe;
        background: #12121e;
        padding: 1 2;
    }
    
    #quick-scan-dialog .title {
        text-align: center;
        text-style: bold;
        color: #3d5afe;
        margin-bottom: 1;
    }
    
    #quick-scan-dialog .path-info {
        background: #050508;
        padding: 0 1;
        margin-bottom: 1;
        border: solid #1a1a2e;
    }
    
    #quick-scan-dialog Checkbox {
        margin: 0 1;
    }
    
    #quick-scan-dialog .mcp-box {
        border: solid #64ffda;
        margin-top: 1;
        padding: 0 1;
        background: #0a1916;
    }
    
    #quick-scan-dialog Horizontal {
        height: auto;
        margin-top: 2;
        align: center middle;
    }
    
    #quick-scan-dialog Button {
        margin: 0 1;
    }
    """

    def __init__(self, project_path: Path):
        super().__init__()
        self.project_path = project_path

    def compose(self):
        """Compose the modal layout."""
        with Vertical(id="quick-scan-dialog"):
            yield Static("🚀 SCHNELL-ANALYSE", classes="title")
            
            with Vertical(classes="path-info"):
                yield Static(f"Projekt: [bold]{self.project_path.name}[/]")
                yield Static(f"Pfad: [dim]{self.project_path}[/]")
            
            yield Static("Wähle Scan-Optionen:")
            yield Checkbox("Security Scan", value=True, id="opt-security")
            yield Checkbox("Correctness Scan", value=True, id="opt-correctness")
            yield Checkbox("Patches generieren", value=True, id="opt-patches")
            
            with Vertical(classes="mcp-box"):
                yield Checkbox(
                    "SocratiCode Deep Indexing (Empfohlen)", 
                    value=True, 
                    id="opt-index-mcp"
                )
                yield Static(
                    "[dim]Verbessert das Codebase-Verständnis durch semantische Suche.[/]",
                    classes="mcp-hint"
                )

            with Horizontal():
                yield Button("🚀 Scan starten", variant="primary", id="btn-start")
                yield Button("❌ Abbrechen", variant="error", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        if event.button.id == "btn-start":
            # Get values
            security = self.query_one("#opt-security", Checkbox).value
            correctness = self.query_one("#opt-correctness", Checkbox).value
            patches = self.query_one("#opt-patches", Checkbox).value
            index_mcp = self.query_one("#opt-index-mcp", Checkbox).value
            
            # Close and start analysis via app
            self.dismiss({
                "path": str(self.project_path),
                "security": security,
                "correctness": correctness,
                "patches": patches,
                "index_mcp": index_mcp
            })
        elif event.button.id == "btn-cancel":
            self.dismiss(None)
