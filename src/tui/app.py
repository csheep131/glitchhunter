"""GlitchHunter TUI - Terminal User Interface."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button
from textual.containers import Grid, Horizontal, Vertical
from textual.reactive import reactive
from textual.binding import Binding

from tui.api_client import TUIApiClient
from tui.report_manager import get_report_manager
from tui.widgets.stack_info import StackInfoWidget
from tui.widgets.models import ModelsWidget
from tui.widgets.system_status import SystemStatusWidget
from tui.widgets.log_view import LogViewWidget
from tui.widgets.socraticode import SocratiCodeWidget
from tui.widgets.directory_browser import DirectoryBrowserWidget
from tui.screens.analyze import AnalyzeScreen
from tui.screens.quick_scan import QuickScanScreen
from tui.screens.report_browser import ReportBrowserScreen
from tui.screens.problem_overview import ProblemOverviewScreen


class GlitchHunterTUI(App):
    """Main TUI Application for GlitchHunter."""
    
    CSS = """
    Screen {
        background: #0a0a0f;
        color: #e0e0e0;
    }
    
    #main-grid {
        grid-size: 2 2;
        grid-columns: 1fr 2fr;
        grid-rows: 2fr 1fr;
        height: 100%;
        padding: 0 1;
    }
    
    #sidebar {
        height: 100%;
        border-right: tall #1a1a2e;
        padding-right: 1;
    }
    
    #main-content {
        height: 100%;
        padding-left: 1;
    }
    
    #action-bar {
        height: auto;
        border: thick #3d5afe;
        background: #12121e;
        padding: 1;
        margin-bottom: 1;
    }
    
    #action-bar Button {
        margin: 0 1;
        background: #1a1a2e;
        border: solid #3d5afe;
    }
    
    #action-bar Button:hover {
        background: #3d5afe;
        color: white;
    }
    
    #log-panel {
        column-span: 2;
        height: 100%;
        margin-top: 1;
        background: #050508;
    }
    
    Header {
        background: #1a1a2e;
        color: #3d5afe;
        text-style: bold;
        border-bottom: solid #3d5afe;
    }
    
    Footer {
        background: #1a1a2e;
        color: #64ffda;
    }
    
    /* Global classes */
    .title {
        color: #3d5afe;
        text-style: bold;
        text-align: center;
    }
    
    .status-online { color: #00e676; }
    .status-offline { color: #ff1744; }
    .status-warning { color: #ffea00; }
    """
    
    BINDINGS = [
        Binding("q,escape", "quit", "Beenden", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("f2", "analyze", "Analyse", show=True),
        Binding("f3", "reports", "Reports", show=True),
        Binding("f4", "problems", "Problem-Solver", show=True),
        Binding("f5", "restart_api", "API Restart", show=True),
        Binding("?", "help", "Hilfe", show=True),
    ]
    
    # App state
    api_online = reactive(False)
    selected_path = reactive(Path.home())
    current_stack = reactive({})
    models = reactive([])
    system_data = reactive({})
    socraticode_data = reactive({})
    uptime = reactive(0)

    @property
    def repo_path(self) -> Path:
        """Returns the current repository path."""
        return self.selected_path

    def __init__(self):
        super().__init__()
        self.api_client = TUIApiClient()
        self.refresh_task: Optional[asyncio.Task] = None
    
    def compose(self) -> ComposeResult:
        """Compose the main UI layout."""
        yield Header(show_clock=True)
        
        with Grid(id="main-grid"):
            # Sidebar
            with Vertical(id="sidebar"):
                yield StackInfoWidget()
                yield SocratiCodeWidget()
                yield ModelsWidget()
                yield SystemStatusWidget()

            # Main content area
            with Vertical(id="main-content"):
                with Horizontal(id="action-bar"):
                    yield Button("🔍 Analyse (F2)", id="btn-analyze", variant="primary")
                    yield Button("📊 Reports (F3)", id="btn-reports")
                    yield Button("📝 Problem-Solver", id="btn-problems", variant="success")
                    yield Button("🔄 Refresh (F5)", id="btn-refresh")
                    yield Button("⚙️ API Restart", id="btn-api-restart", variant="error")

                yield DirectoryBrowserWidget(
                    id="main-browser",
                    on_select=self._on_directory_selected
                )

            # Logs full width at bottom
            with Vertical(id="log-panel"):
                yield LogViewWidget()
        
        yield Footer()
    
    async def on_mount(self):
        """Initialize on mount."""
        self.title = "GlitchHunter TUI"
        self.sub_title = "Connecting..."
        
        # Check API connection
        if self.api_client.is_api_online():
            self.api_online = True
            self.sub_title = "STATION ONLINE"
            self.log_message("Control Center link established", "INFO")
        else:
            self.api_online = False
            self.sub_title = "STATION DISCONNECTED"
            self.log_message("API not available - Reconnecting...", "ERROR")
            self.notify("API Offline. Bitte './scripts/run_stack_a.sh api' prüfen.", severity="error")
        
        # Start refresh loop
        self.refresh_task = asyncio.create_task(self._refresh_loop())
        
        # Initial data load
        await self.refresh_data()
    
    async def on_unmount(self):
        """Cleanup on unmount."""
        if self.refresh_task:
            self.refresh_task.cancel()
        await self.api_client.close()
    
    async def _refresh_loop(self):
        """Background task to refresh data every 2 seconds."""
        while True:
            try:
                await asyncio.sleep(2)
                await self.refresh_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log_message(f"Refresh error: {e}", "ERROR")
    
    async def refresh_data(self):
        """Fetch fresh data from API."""
        try:
            # Get complete status
            status = await self.api_client.get_status()
            
            if status:
                self.api_online = True
                
                # Update stack info
                stack = status.get("current_stack", {})
                self.current_stack = stack
                self.query_one(StackInfoWidget).update_data(stack)
                
                # Update models
                models = status.get("models", [])
                self.models = models
                self.query_one(ModelsWidget).update_data(models)
                
                # Update system status
                system = status.get("system", {})
                uptime = status.get("uptime_seconds", 0)
                self.system_data = system
                self.uptime = uptime
                self.query_one(SystemStatusWidget).update_data(system, uptime)
                
                # Update SocratiCode status
                socraticode = status.get("socraticode", {})
                self.socraticode_data = socraticode
                self.query_one(SocratiCodeWidget).update_data(socraticode)
                
                # Update title with stack
                stack_type = stack.get("stack_type", "unknown").upper()
                indicator = "●" if self.api_online else "○"
                self.sub_title = f"{indicator} {stack_type} | {stack.get('gpu_name', 'Unknown')}"
            else:
                if self.api_online:
                    self.api_online = False
                    self.sub_title = "○ DISCONNECTED"
                    self.log_message("Link to API lost", "ERROR")
        
        except Exception as e:
            if self.api_online:
                self.log_message(f"Data refresh failed: {e}", "ERROR")
    
    def log_message(self, message: str, level: str = "INFO"):
        """Add message to log view."""
        try:
            log_widget = self.query_one(LogViewWidget)
            log_widget.add_log(message, level)
        except Exception:
            pass  # Log widget might not be ready yet
    
    # Action handlers
    def action_refresh(self):
        """Manual refresh."""
        self.log_message("Manual refresh...", "INFO")
        asyncio.create_task(self.refresh_data())

    def action_analyze(self):
        """Open analyze screen or quick scan modal."""
        if self.selected_path and self.selected_path.exists() and self.selected_path.is_dir():
            # If path already selected on dashboard, show quick menu
            def handle_quick_scan(data):
                if data:
                    self.start_analysis(
                        data["path"],
                        data["security"],
                        data["correctness"],
                        data["patches"],
                        data["index_mcp"]
                    )
            
            self.push_screen(QuickScanScreen(self.selected_path), handle_quick_scan)
        else:
            # Otherwise open full browser
            self.push_screen(AnalyzeScreen())

    def action_reports(self):
        """Open report browser."""
        self.push_screen(ReportBrowserScreen())

    def action_problems(self):
        """Open Problem-Solver overview."""
        self.push_screen(ProblemOverviewScreen(repo_path=str(self.repo_path)))

    def action_restart_api(self):
        """Restart API."""
        self.log_message("API restart requested (not implemented)", "WARNING")
        self.notify("API restart not yet implemented", severity="warning")
    
    def action_help(self):
        """Show help."""
        help_text = """
        [b]GlitchHunter TUI - Hilfe[/b]

        [b]Tastenkürzel:[/b]
        • F2 - Analyse starten (Directory Browser)
        • F3 - Report Center (Reports + Fix-Läufe)
        • F4 - Problem-Solver (Neu!)
        • R - Daten aktualisieren
        • F5 - API neu starten
        • Q / Escape - Beenden
        • ? - Diese Hilfe

        [b]Report Center Features:[/b]
        • 📊 Super Übersicht aller Reports
        • 📈 Statistiken pro Projekt
        • 📋 Top Kandidaten Liste
        • 🚀 Fix-Lauf direkt starten
        • 📄 Markdown/JSON Viewer

        [b]Problem-Solver (Neu):[/b]
        • 📝 Probleme aufnehmen und verwalten
        • 🔍 Probleme klassifizieren (AI-gestützt)
        • 📋 Probleme nach Status/Typ filtern
        • 👁️ Details anzeigen

        [b]Neu:[/b]
        • Directory Browser - Wähle Verzeichnisse visuell
        • Report Manager - Auto-Erkennung aller Reports
        • Fix-Lauf Integration - Starte direkt aus Reports
        • Problem-Solver - Ganzheitliches Problem-Management

        [b]Panels:[/b]
        • Stack Info - Zeigt aktiven Stack (A/B)
        • Modelle - Verfügbare AI Modelle
        • System - CPU/RAM/GPU Auslastung
        • SocratiCode - Code-Index Status
        • Logs - Echtzeit-Logs
        """
        self.notify(help_text, title="Hilfe", timeout=10)
    
    def _on_directory_selected(self, path: Path):
        """Handle directory selection from main browser."""
        self.selected_path = path
        self.log_message(f"Selected project path: {path}", "INFO")
        self.notify(f"Projekt gewählt: {path.name}")

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-analyze":
            self.action_analyze()
        elif button_id == "btn-reports":
            self.action_reports()
        elif button_id == "btn-problems":
            self.action_problems()
        elif button_id == "btn-refresh":
            self.action_refresh()
        elif button_id == "btn-api-stop":
            self.log_message("API shutdown requested", "WARNING")
            self.notify("API shutdown not yet implemented", severity="warning")
    
    def start_analysis(self, repo_path: str, security: bool, correctness: bool, patches: bool, index_mcp: bool = False):
        """Start analysis via API with report management."""
        self.log_message(f"Starting analysis: {repo_path} (MCP Index: {index_mcp})", "INFO")

        # Create report slot for this analysis
        project_path = Path(repo_path)
        report_manager = get_report_manager()
        report_slot = report_manager.create_report_slot(
            project_path,
            report_type="fix" if patches else "scan"
        )

        self.log_message(f"Report will be saved to: {report_slot['project_dir']}", "INFO")

        async def do_analysis():
            try:
                result = await self.api_client.start_analysis(
                    repo_path, 
                    security=security, 
                    correctness=correctness, 
                    patches=patches,
                    index_mcp=index_mcp
                )
                if result:
                    analysis_id = result.get("analysis_id", "unknown")
                    self.log_message(f"Analysis started: {analysis_id}", "INFO")
                    if index_mcp:
                        self.log_message("Indexing project in SocratiCode...", "INFO")
                    self.notify(f"Analyse gestartet: {analysis_id}", severity="information")

                    # Store report paths in result for later
                    result["report_slot"] = report_slot
                else:
                    self.log_message("Failed to start analysis", "ERROR")
                    self.notify("Fehler beim Starten", severity="error")
            except Exception as e:
                self.log_message(f"Analysis error: {e}", "ERROR")
                self.notify(f"Fehler: {e}", severity="error")

        asyncio.create_task(do_analysis())


def main():
    """Main entry point."""
    app = GlitchHunterTUI()
    app.run()


if __name__ == "__main__":
    main()
