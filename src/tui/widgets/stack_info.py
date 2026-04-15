"""Stack Info Widget - Shows current hardware stack."""

from textual.widgets import Static
from textual.containers import Vertical


class StackInfoWidget(Static):
    """Widget displaying current stack information."""
    
    DEFAULT_CSS = """
    StackInfoWidget {
        border: solid $primary;
        padding: 1;
    }
    StackInfoWidget > .title {
        text-align: center;
        text-style: bold;
        color: $primary;
    }
    StackInfoWidget > .stack-row {
        padding: 0 1;
    }
    StackInfoWidget > .stack-row .label {
        color: $text-muted;
    }
    StackInfoWidget > .stack-row .value {
        color: $text;
        text-style: bold;
    }
    StackInfoWidget > .indicator {
        text-align: center;
        margin-top: 1;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.stack_data = {
            "stack_type": "unknown",
            "gpu_name": "Unknown",
            "vram_gb": 0,
            "mode": "unknown"
        }
    
    def compose(self):
        """Compose the widget layout."""
        yield Static("📊 STACK INFO", classes="title")
        yield Static("", classes="indicator", id="stack-indicator")
        yield Static("", classes="stack-row", id="stack-type")
        yield Static("", classes="stack-row", id="gpu-name")
        yield Static("", classes="stack-row", id="vram")
        yield Static("", classes="stack-row", id="mode")
    
    def update_data(self, data: dict):
        """Update widget with real data from API."""
        self.stack_data = data
        
        # Update indicator
        indicator = self.query_one("#stack-indicator", Static)
        if data.get("available"):
            indicator.update("🟢 Online")
        else:
            indicator.update("🔴 Offline")
        
        # Update fields
        self.query_one("#stack-type", Static).update(
            f"[b]Stack:[/b] {data.get('stack_type', 'unknown').upper()}"
        )
        self.query_one("#gpu-name", Static).update(
            f"[b]GPU:[/b] {data.get('gpu_name', 'Unknown')}"
        )
        self.query_one("#vram", Static).update(
            f"[b]VRAM:[/b] {data.get('vram_gb', 0)} GB"
        )
        self.query_one("#mode", Static).update(
            f"[b]Mode:[/b] {data.get('mode', 'unknown').title()}"
        )
    
    def on_mount(self):
        """Initialize with loading state."""
        self.query_one("#stack-indicator", Static).update("🟡 Loading...")
