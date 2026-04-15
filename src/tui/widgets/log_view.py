"""Log View Widget - Shows application logs."""

from textual.widgets import Static, RichLog
from textual.containers import Vertical
from textual.reactive import reactive


class LogViewWidget(Static):
    """Widget displaying application logs."""
    
    DEFAULT_CSS = """
    LogViewWidget {
        border: solid $primary;
        padding: 1;
        height: 100%;
    }
    LogViewWidget > .title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    LogViewWidget > RichLog {
        height: 1fr;
        border: solid $surface-darken-1;
        padding: 0 1;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.max_lines = 100
    
    def compose(self):
        """Compose the widget layout."""
        yield Static("📜 LOGS", classes="title")
        yield RichLog(id="log-content", highlight=True, max_lines=self.max_lines)
    
    def add_log(self, message: str, level: str = "INFO"):
        """Add a log message to the view."""
        log = self.query_one("#log-content", RichLog)
        
        # Color based on level
        color = {
            "DEBUG": "dim",
            "INFO": "blue",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold red",
        }.get(level.upper(), "white")
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] [{color}]{level:8}[/{color}] {message}"
        
        log.write(formatted)
    
    def clear_logs(self):
        """Clear all logs."""
        log = self.query_one("#log-content", RichLog)
        log.clear()
    
    def on_mount(self):
        """Initialize with welcome message."""
        self.add_log("TUI started", "INFO")
        self.add_log("Connecting to API...", "INFO")
