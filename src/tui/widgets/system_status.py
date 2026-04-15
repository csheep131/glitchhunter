"""System Status Widget - Shows system resources."""

from textual.widgets import Static, ProgressBar
from textual.containers import Vertical


class SystemStatusWidget(Static):
    """Widget displaying system resource usage."""
    
    DEFAULT_CSS = """
    SystemStatusWidget {
        border: solid $primary;
        padding: 1;
    }
    SystemStatusWidget > .title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    SystemStatusWidget > .resource-row {
        padding: 0 1;
        height: auto;
    }
    SystemStatusWidget > .resource-row .label {
        color: $text-muted;
        width: 12;
    }
    SystemStatusWidget > .resource-row .value {
        color: $text;
    }
    SystemStatusWidget ProgressBar {
        margin: 0 1;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.system_data = {}
    
    def compose(self):
        """Compose the widget layout."""
        yield Static("💻 SYSTEM", classes="title")
        yield Static("", id="cpu-row", classes="resource-row")
        yield ProgressBar(id="cpu-bar", total=100.0)
        yield Static("", id="ram-row", classes="resource-row")
        yield ProgressBar(id="ram-bar", total=100.0)
        yield Static("", id="gpu-row", classes="resource-row")
        yield Static("", id="uptime-row", classes="resource-row")
    
    def update_data(self, data: dict, uptime: int = 0):
        """Update widget with real system data from API."""
        self.system_data = data
        
        # CPU
        cpu_percent = data.get("cpu_percent", 0)
        self.query_one("#cpu-row", Static).update(f"[b]CPU:[/b] {cpu_percent:.1f}%")
        self.query_one("#cpu-bar", ProgressBar).update(progress=cpu_percent)
        
        # RAM
        ram_used = data.get("ram_used_gb", 0)
        ram_total = data.get("ram_total_gb", 32)
        ram_percent = (ram_used / ram_total * 100) if ram_total > 0 else 0
        self.query_one("#ram-row", Static).update(
            f"[b]RAM:[/b] {ram_used:.1f} / {ram_total:.1f} GB"
        )
        self.query_one("#ram-bar", ProgressBar).update(progress=ram_percent)
        
        # GPU/VRAM
        vram_used = data.get("vram_used_gb")
        vram_total = data.get("vram_total_gb")
        gpu_temp = data.get("gpu_temp_c")
        
        gpu_str = "[b]GPU:[/b] "
        if vram_total:
            vram_used_str = f"{vram_used:.1f}" if vram_used else "?"
            gpu_str += f"VRAM {vram_used_str}/{vram_total:.0f}GB"
        else:
            gpu_str += "N/A"
        
        if gpu_temp:
            gpu_str += f" | {gpu_temp}°C"
        
        self.query_one("#gpu-row", Static).update(gpu_str)
        
        # Uptime
        hours = uptime // 3600
        minutes = (uptime % 3600) // 60
        self.query_one("#uptime-row", Static).update(
            f"[b]Uptime:[/b] {hours}h {minutes}m"
        )
    
    def on_mount(self):
        """Initialize with loading state."""
        self.query_one("#cpu-row", Static).update("[dim]Loading...[/dim]")
