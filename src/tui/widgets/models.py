"""Models Widget - Shows available AI models."""

from textual.widgets import Static, DataTable
from textual.containers import Vertical


class ModelsWidget(Static):
    """Widget displaying available models and their status."""
    
    DEFAULT_CSS = """
    ModelsWidget {
        border: solid $primary;
        padding: 1;
    }
    ModelsWidget > .title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    ModelsWidget > DataTable {
        height: 1fr;
        border: none;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.models = []
    
    def compose(self):
        """Compose the widget layout."""
        yield Static("🤖 MODELLE", classes="title")
        yield DataTable(id="models-table")
    
    def on_mount(self):
        """Initialize the data table."""
        table = self.query_one("#models-table", DataTable)
        table.add_columns("Status", "Name", "Role", "Size")
        table.add_row("🟡", "Loading...", "-", "-")
    
    def update_data(self, models: list):
        """Update widget with real model data from API."""
        self.models = models
        table = self.query_one("#models-table", DataTable)
        table.clear()
        
        if not models:
            table.add_row("⚪", "No models found", "-", "-")
            return
        
        for model in models:
            status = "✅" if model.get("available") else "⬜"
            name = model.get("name", "Unknown")
            role = model.get("role", "unknown").title()
            size = model.get("size_gb")
            size_str = f"{size:.1f} GB" if size else "-"
            
            table.add_row(status, name, role, size_str)
