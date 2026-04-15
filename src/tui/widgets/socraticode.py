"""SocratiCode Widget - Shows MCP integration status."""

from textual.widgets import Static, DataTable
from textual.containers import Vertical


class SocratiCodeWidget(Static):
    """Widget displaying SocratiCode MCP integration status."""
    
    DEFAULT_CSS = """
    SocratiCodeWidget {
        border: solid $primary;
        padding: 1;
    }
    SocratiCodeWidget > .title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    SocratiCodeWidget > .status-row {
        padding: 0 1;
    }
    SocratiCodeWidget > .indicator {
        text-align: center;
        margin: 1 0;
    }
    SocratiCodeWidget > DataTable {
        height: auto;
        max-height: 6;
        border: none;
        margin-top: 1;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.soc_data = {
            "enabled": False,
            "connected": False,
            "server_url": "",
            "indexed_projects": 0,
            "features": [],
        }
    
    def compose(self):
        """Compose the widget layout."""
        yield Static("🔍 SOCRATICODE", classes="title")
        yield Static("", classes="indicator", id="soc-indicator")
        yield Static("", classes="status-row", id="soc-url")
        yield Static("", classes="status-row", id="soc-projects")
        yield DataTable(id="soc-features")
    
    def on_mount(self):
        """Initialize with loading state."""
        self.query_one("#soc-indicator", Static).update("🟡 Checking...")
        table = self.query_one("#soc-features", DataTable)
        table.add_columns("Features")
    
    def update_data(self, data: dict):
        """Update widget with real data from API."""
        self.soc_data = data
        
        # Status indicator
        indicator = self.query_one("#soc-indicator", Static)
        if not data.get("enabled"):
            indicator.update("[bold #616161]○ DISABLED[/]")
        elif data.get("connected"):
            indicator.update("[bold #00e676]● CONNECTED[/]")
        else:
            indicator.update("[bold #ff1744]○ OFFLINE[/]")
        
        # Server URL
        url = data.get("server_url", "")
        self.query_one("#soc-url", Static).update(
            f"[b]Server:[/b] {url}" if url else "[b]Server:[/b] Not configured"
        )
        
        # Indexed projects
        projects = data.get("indexed_projects", 0)
        self.query_one("#soc-projects", Static).update(
            f"[b]Projects:[/b] {projects} indexed"
        )
        
        # Features table
        table = self.query_one("#soc-features", DataTable)
        table.clear()
        features = data.get("features", [])
        if features:
            for feat in features:
                icon = "✓" if data.get("connected") else "○"
                table.add_row(f"{icon} {feat.replace('_', ' ').title()}")
        else:
            table.add_row("No features available")
