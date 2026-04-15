"""Analyze Screen - Start repository analysis with directory browser."""

from pathlib import Path

from textual.screen import Screen
from textual.widgets import Static, Input, Button, Checkbox, Label
from textual.containers import Vertical, Horizontal, Grid
from textual.reactive import reactive

from tui.report_manager import get_report_manager
from tui.widgets.directory_browser import DirectoryBrowserWidget, ProjectSelectorWidget


class AnalyzeScreen(Screen):
    """Screen for starting analysis with directory browser."""

    DEFAULT_CSS = """
    AnalyzeScreen {
        align: center middle;
    }
    AnalyzeScreen > Grid {
        grid-size: 2 2;
        grid-columns: 1fr 2fr;
        grid-rows: auto 1fr;
        width: 95%;
        height: 95%;
        border: solid $primary;
        padding: 1;
    }
    AnalyzeScreen #left-panel {
        height: 100%;
        border-right: solid $surface-darken-2;
        padding-right: 1;
    }
    AnalyzeScreen #right-panel {
        height: 100%;
        padding-left: 1;
    }
    AnalyzeScreen #header {
        column-span: 2;
        height: auto;
        border-bottom: solid $primary;
        padding-bottom: 1;
        margin-bottom: 1;
    }
    AnalyzeScreen #header Static {
        text-align: center;
        text-style: bold;
        color: $primary;
    }
    AnalyzeScreen Static.selected-path {
        text-style: bold;
        color: $success;
        margin: 1 0;
    }
    AnalyzeScreen #reports-preview {
        height: auto;
        max-height: 10;
        border: solid $surface-darken-2;
        padding: 1;
        margin-top: 1;
    }
    AnalyzeScreen Checkbox {
        margin: 0 1;
    }
    AnalyzeScreen Horizontal {
        height: auto;
        margin-top: 1;
    }
    AnalyzeScreen Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Abbrechen"),
    ]

    # Reactive state
    selected_path = reactive(Path.home())
    existing_reports = reactive([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.report_manager = get_report_manager()
        self.dir_browser: DirectoryBrowserWidget = None

    def compose(self):
        """Compose the screen layout."""
        with Grid():
            # Header
            with Vertical(id="header"):
                yield Static("🔍 REPOSITORY ANALYSE", classes="title")
                yield Static("Wähle ein Verzeichnis zum Scannen")

            # Left panel - Quick access + project selector
            with Vertical(id="left-panel"):
                yield ProjectSelectorWidget(on_select=self._on_favorite_selected)

            # Right panel - Directory browser + options
            with Vertical(id="right-panel"):
                # Directory browser
                self.dir_browser = DirectoryBrowserWidget(
                    start_path=Path("/home/schaf/projects"),
                    on_select=self._on_directory_selected,
                    id="dir-browser"
                )
                yield self.dir_browser

                # Selected path display
                yield Static(
                    f"📂 Ausgewählt: {self.selected_path}",
                    id="selected-path-display",
                    classes="selected-path"
                )

                # Existing reports preview
                with Vertical(id="reports-preview"):
                    yield Static("📊 Vorhandene Reports:", id="reports-header")
                    yield Static("-", id="reports-list")

                # Options
                yield Static("🔧 Optionen:")
                with Horizontal():
                    yield Checkbox("Security Scan", value=True, id="opt-security")
                    yield Checkbox("Correctness Scan", value=True, id="opt-correctness")
                    yield Checkbox("Patches generieren", value=True, id="opt-patches")

                # Action buttons
                with Horizontal():
                    yield Button(
                        "🚀 Analyse starten",
                        variant="primary",
                        id="btn-start"
                    )
                    yield Button(
                        "📊 Reports anzeigen",
                        id="btn-reports"
                    )
                    yield Button(
                        "❌ Abbrechen",
                        variant="error",
                        id="btn-cancel"
                    )

    def _on_favorite_selected(self, path: Path):
        """Handle favorite selection."""
        self.selected_path = path
        if self.dir_browser:
            self.dir_browser.selected_path = path
            self.dir_browser._refresh_tree()
        self._update_display()

    def _on_directory_selected(self, path: Path):
        """Handle directory selection."""
        self.selected_path = path
        self._update_display()

    def _update_display(self):
        """Update display with selected path and reports."""
        # Update path display
        display = self.query_one("#selected-path-display", Static)
        display.update(f"📂 Ausgewählt: {self.selected_path}")

        # Check for existing reports
        reports = self.report_manager.get_reports_for_project(self.selected_path)
        self.existing_reports = reports

        # Update reports preview
        reports_list = self.query_one("#reports-list", Static)
        reports_header = self.query_one("#reports-header", Static)

        if reports:
            reports_header.update(f"📊 Vorhandene Reports ({len(reports)}):")
            lines = []
            for i, report in enumerate(reports[:3], 1):
                lines.append(f"{i}. {report.report_type.upper()}: {report.short_summary}")
            if len(reports) > 3:
                lines.append(f"   ... und {len(reports) - 3} weitere")
            reports_list.update("\n".join(lines))
        else:
            reports_header.update("📊 Vorhandene Reports:")
            reports_list.update("Noch keine Reports für dieses Projekt.")

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        if event.button.id == "btn-start":
            self._start_analysis()
        elif event.button.id == "btn-reports":
            self._show_reports()
        elif event.button.id == "btn-cancel":
            self.action_cancel()

    def _start_analysis(self):
        """Start analysis."""
        if not self.selected_path or not self.selected_path.exists():
            self.app.notify("Bitte wähle ein gültiges Verzeichnis", severity="error")
            return

        if not self.selected_path.is_dir():
            self.app.notify("Pfad muss ein Verzeichnis sein", severity="error")
            return

        # Get options
        security = self.query_one("#opt-security", Checkbox).value
        correctness = self.query_one("#opt-correctness", Checkbox).value
        patches = self.query_one("#opt-patches", Checkbox).value

        # Start via app
        self.app.start_analysis(
            str(self.selected_path),
            security,
            correctness,
            patches
        )
        self.app.pop_screen()

    def _show_reports(self):
        """Show reports for selected project."""
        if not self.selected_path:
            self.app.notify("Bitte wähle zuerst ein Projekt", severity="warning")
            return

        # Open report browser with this project
        from tui.screens.report_browser import ReportBrowserScreen
        self.app.push_screen(ReportBrowserScreen(self.selected_path))

    def action_cancel(self):
        """Cancel action."""
        self.app.pop_screen()


class AnalysisProgressScreen(Screen):
    """Screen für laufende Analyse mit Fortschrittsanzeige."""

    DEFAULT_CSS = """
    AnalysisProgressScreen {
        align: center middle;
    }
    AnalysisProgressScreen > Vertical {
        width: 70;
        height: auto;
        border: solid $primary;
        padding: 1 2;
    }
    AnalysisProgressScreen Static.title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    AnalysisProgressScreen Static.status {
        text-align: center;
        margin: 1 0;
    }
    AnalysisProgressScreen Static.progress {
        text-align: center;
        color: $success;
    }
    AnalysisProgressScreen #log-output {
        height: 10;
        border: solid $surface-darken-2;
        padding: 0 1;
        margin: 1 0;
    }
    """

    def __init__(self, project_path: Path, **kwargs):
        super().__init__(**kwargs)
        self.project_path = project_path
        self.logs = []

    def compose(self):
        """Compose the screen."""
        with Vertical():
            yield Static("🔍 ANALYSE LÄUFT", classes="title")
            yield Static(f"Projekt: {self.project_path.name}", classes="status")
            yield Static("⏳ Initialisiere...", id="progress-text", classes="progress")
            yield Static(id="log-output")

            with Horizontal():
                yield Button("🛑 Abbrechen", id="btn-cancel", variant="error")

    def on_mount(self):
        """Start analysis."""
        self._start_analysis()

    def _start_analysis(self):
        """Start the actual analysis."""
        # This would integrate with the actual analysis pipeline
        self.app.notify("Analyse gestartet...")

    def add_log(self, message: str):
        """Add log message."""
        self.logs.append(message)
        if len(self.logs) > 20:
            self.logs = self.logs[-20:]

        log_widget = self.query_one("#log-output", Static)
        log_widget.update("\n".join(self.logs))

    def update_progress(self, status: str):
        """Update progress text."""
        progress = self.query_one("#progress-text", Static)
        progress.update(f"⏳ {status}")

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        if event.button.id == "btn-cancel":
            self.app.pop_screen()
