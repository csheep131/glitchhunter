"""Report Browser Screen - Zeigt bestehende Reports super an."""

from pathlib import Path
from typing import Optional

from textual.screen import Screen
from textual.widgets import (
    Static, Button, DataTable, ListView, ListItem, Label,
    TabbedContent, TabPane, RichLog, ProgressBar
)
from textual.containers import Vertical, Horizontal, Grid, ScrollableContainer
from textual.reactive import reactive
from textual.worker import Worker

from tui.report_manager import get_report_manager, ProjectReport, ReportCandidate


class ReportBrowserScreen(Screen):
    """Screen für super Report-Verwaltung und -Anzeige."""

    DEFAULT_CSS = """
    ReportBrowserScreen {
        align: center middle;
    }
    ReportBrowserScreen > Grid {
        grid-size: 3 2;
        grid-columns: 1fr 2fr 1fr;
        grid-rows: auto 1fr;
        width: 98%;
        height: 98%;
        border: solid $primary;
        padding: 1;
    }
    ReportBrowserScreen #header {
        column-span: 3;
        height: auto;
        border-bottom: solid $primary;
        padding-bottom: 1;
        margin-bottom: 1;
    }
    ReportBrowserScreen #header Static {
        text-align: center;
        text-style: bold;
        color: $primary;
    }
    ReportBrowserScreen #project-panel {
        border: solid $surface-darken-2;
        padding: 0 1;
        height: 100%;
    }
    ReportBrowserScreen #report-detail {
        border: solid $surface-darken-2;
        padding: 1;
        height: 100%;
    }
    ReportBrowserScreen #action-panel {
        border: solid $surface-darken-2;
        padding: 1;
        height: 100%;
    }
    ReportBrowserScreen #button-bar {
        height: auto;
        margin-top: 1;
    }
    ReportBrowserScreen Button {
        margin: 0 1;
        width: 100%;
    }
    ReportBrowserScreen DataTable {
        height: 1fr;
        border: solid $surface-darken-2;
    }
    ReportBrowserScreen .stats-grid {
        grid-size: 2;
        grid-columns: 1fr 1fr;
        height: auto;
        margin: 1 0;
    }
    ReportBrowserScreen .stat-box {
        border: solid $surface-darken-2;
        padding: 1;
        text-align: center;
    }
    ReportBrowserScreen .stat-value {
        text-style: bold;
        color: $primary;
        text-align: center;
    }
    ReportBrowserScreen .stat-label {
        text-style: dim;
        text-align: center;
    }
    ReportBrowserScreen RichLog {
        height: 15;
        border: solid $surface-darken-2;
        padding: 0 1;
    }
    ReportBrowserScreen ProgressBar {
        margin: 1 0;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Zurück"),
        ("r", "refresh", "Refresh"),
        ("f", "fix", "Fix Starten"),
        ("d", "delete", "Löschen"),
    ]

    # Reactive state
    selected_project: reactive[Optional[str]] = reactive(None)
    selected_report: reactive[Optional[ProjectReport]] = reactive(None)
    projects: reactive[list] = reactive([])
    is_fixing: reactive[bool] = reactive(False)

    def __init__(self, project_path: Optional[Path] = None, **kwargs):
        super().__init__(**kwargs)
        self.project_path = project_path
        self.report_manager = get_report_manager()
        self.reports: list = []

    def compose(self):
        """Compose the screen."""
        with Grid():
            # Header
            with Vertical(id="header"):
                yield Static("📊 GLITCHHUNTER REPORT CENTER", classes="title")
                yield Static("Verwalte Reports und starte Fix-Läufe")

            # Left panel - Projects
            with Vertical(id="project-panel"):
                yield Static("📁 Projekte:")
                yield ListView(id="project-listview")
                yield Static("", id="project-stats")

            # Middle panel - Report Detail
            with Vertical(id="report-detail"):
                yield TabbedContent(
                    TabPane("📊 Übersicht", self._compose_overview_tab()),
                    TabPane("📄 Details", self._compose_details_tab()),
                    TabPane("📝 Markdown", self._compose_markdown_tab()),
                    id="report-tabs"
                )

            # Right panel - Actions
            with Vertical(id="action-panel"):
                yield Static("🔧 Aktionen:")
                with Vertical(id="button-bar"):
                    yield Button(
                        "🚀 Fix-Lauf starten [F]",
                        id="btn-fix",
                        variant="success",
                        disabled=True
                    )
                    yield Button(
                        "🔍 Report anzeigen",
                        id="btn-view",
                        variant="primary"
                    )
                    yield Button(
                        "📂 Ordner öffnen",
                        id="btn-folder"
                    )
                    yield Button(
                        "🗑️ Löschen [D]",
                        id="btn-delete",
                        variant="error"
                    )
                    yield Button(
                        "🔄 Refresh [R]",
                        id="btn-refresh"
                    )
                    yield Button(
                        "✅ Schließen [ESC]",
                        id="btn-close"
                    )

                # Progress/Log Bereich
                yield Static("📜 Log:")
                yield RichLog(id="fix-log")

    def _compose_overview_tab(self):
        """Compose overview tab."""
        with Vertical():
            with Grid(classes="stats-grid"):
                with Vertical(classes="stat-box"):
                    yield Static("0", classes="stat-value", id="stat-candidates")
                    yield Static("Kandidaten", classes="stat-label")
                with Vertical(classes="stat-box"):
                    yield Static("0", classes="stat-value", id="stat-patches")
                    yield Static("Patches", classes="stat-label")
                with Vertical(classes="stat-box"):
                    yield Static("0", classes="stat-value", id="stat-findings")
                    yield Static("Findings", classes="stat-label")
                with Vertical(classes="stat-box"):
                    yield Static("0", classes="stat-value", id="stat-score")
                    yield Static("Ø Score", classes="stat-label")

            yield Static("📋 Top Kandidaten:")
            yield DataTable(id="candidates-table")

    def _compose_details_tab(self):
        """Compose details tab."""
        with ScrollableContainer():
            yield Static(id="details-content")

    def _compose_markdown_tab(self):
        """Compose markdown tab."""
        with ScrollableContainer():
            yield Static(id="markdown-content")

    def on_mount(self):
        """Initialize on mount."""
        # Setup candidates table
        table = self.query_one("#candidates-table", DataTable)
        table.add_columns("Datei", "Score", "Komplexität", "Hotspot")
        table.cursor_type = "row"

        self._load_projects()

    def _load_projects(self):
        """Lädt Projektliste."""
        listview = self.query_one("#project-listview", ListView)
        listview.clear()

        # Get all reports and group by project
        all_reports = self.report_manager.scan_directory()
        projects_data = {}

        for report in all_reports:
            name = report.project_name
            if name not in projects_data:
                projects_data[name] = {
                    "name": name,
                    "reports": [],
                    "total_candidates": 0,
                    "total_hypotheses": 0,
                    "total_patches": 0,
                }
            projects_data[name]["reports"].append(report)
            projects_data[name]["total_candidates"] += report.candidates_analyzed
            projects_data[name]["total_hypotheses"] += report.hypotheses_generated
            projects_data[name]["total_patches"] += report.patches_generated

        self.projects = list(projects_data.values())

        if not self.projects:
            listview.append(ListItem(Label("Keine Reports vorhanden")))
            return

        for project in self.projects:
            name = project["name"]
            count = len(project["reports"])
            total_candidates = project["total_candidates"]
            total_hypotheses = project["total_hypotheses"]

            # Get latest report for icon
            latest = max(project["reports"], key=lambda r: r.created_at)
            icon = latest.status_icon if latest else "📂"

            # Build label
            label_parts = [f"{icon} {name}", f"   {count} Reports"]
            if total_candidates > 0:
                label_parts.append(f"📁 {total_candidates} Kandidaten")
            if total_hypotheses > 0:
                label_parts.append(f"💡 {total_hypotheses} Hypothesen")

            item = ListItem(Label("\n".join(label_parts)))
            item.data = name
            listview.append(item)

        # Wenn ein spezifisches Projekt angegeben wurde, wähle es
        if self.project_path:
            project_name = self.report_manager._get_project_name(self.project_path)
            for i, proj in enumerate(self.projects):
                if proj["name"] == project_name:
                    listview.index = i
                    self._select_project(project_name)
                    break

    def on_list_view_selected(self, event: ListView.Selected):
        """Handle project selection."""
        item = event.item
        if hasattr(item, 'data') and item.data:
            self._select_project(item.data)

    def _select_project(self, project_name: str):
        """Zeigt Reports für ein Projekt an."""
        self.selected_project = project_name

        # Finde Projekt
        project = None
        for proj in self.projects:
            if proj["name"] == project_name:
                project = proj
                break

        if not project:
            return

        # Update project stats
        stats = self.query_one("#project-stats", Static)
        stats.update(
            f"📊 {len(project['reports'])} Reports\n"
            f"📁 {project['total_candidates']} Kandidaten\n"
            f"💡 {project['total_hypotheses']} Hypothesen\n"
            f"🔧 {project['total_patches']} Patches"
        )

        # Lade neuesten Report
        if project["reports"]:
            latest = max(project["reports"], key=lambda r: r.created_at)
            self.selected_report = latest
            self._update_report_display()

    def _update_report_display(self):
        """Aktualisiert Report-Anzeige."""
        report = self.selected_report
        if not report:
            return

        # Update stats - use summary data
        candidates_count = report.candidates_analyzed
        hypotheses = report.hypotheses_generated
        patches = report.verified_patches_count or report.patches_generated

        self.query_one("#stat-candidates", Static).update(str(candidates_count))
        self.query_one("#stat-patches", Static).update(str(patches))
        self.query_one("#stat-findings", Static).update(str(report.findings_count))
        self.query_one("#stat-score", Static).update(str(hypotheses))

        # Update stat labels
        self.query_one("#stat-score").parent.query_one(".stat-label").update("Hypothesen")

        # Update candidates table
        table = self.query_one("#candidates-table", DataTable)
        table.clear()

        # Sortiere nach Score (höchste zuerst)
        sorted_candidates = sorted(
            report.candidates,
            key=lambda c: c.total_score,
            reverse=True
        )[:20]  # Max 20

        if sorted_candidates:
            for c in sorted_candidates:
                table.add_row(
                    c.display_name[:30],
                    f"{c.total_score:.1f}",
                    str(c.complexity),
                    f"{c.hotspot_score:.1f}"
                )
        else:
            # Show placeholder if no candidates data
            table.add_row("* Keine Kandidaten-Details verfügbar", "-", "-", "-")

        # Update details tab
        details = self.query_one("#details-content", Static)
        details.update(self._format_details(report))

        # Update markdown tab
        md = self.query_one("#markdown-content", Static)
        md_content = self.report_manager.load_report_markdown(report)
        if md_content:
            # Truncate for display
            md.update(md_content[:3000] + "\n\n...")
        else:
            md.update("*Kein Markdown verfügbar*")

        # Enable/disable fix button
        fix_btn = self.query_one("#btn-fix", Button)
        if report.is_fixable:
            fix_btn.disabled = False
            fix_btn.label = f"🚀 Fix-Lauf starten ({len(report.candidates)} Kandidaten)"
        else:
            fix_btn.disabled = True
            fix_btn.label = "✅ Bereits gefixt" if report.verified_patches_count > 0 else "🚀 Fix-Lauf starten"

    def _format_details(self, report: ProjectReport) -> str:
        """Formatiert Report-Details."""
        lines = [
            f"📊 {report.display_name}",
            "",
            f"📝 Typ: {report.report_type.upper()}",
            f"📅 Erstellt: {report.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"📁 Projekt: {report.project_name}",
            f"🗂️  State: {report.state}",
            "",
            "📈 Zusammenfassung:",
            f"  • Kandidaten: {len(report.candidates)}",
            f"  • Findings: {report.findings_count}",
            f"  • Patches: {report.verified_patches_count}",
            "",
        ]

        if report.errors:
            lines.append("⚠️ Fehler:")
            for err in report.errors[:5]:
                lines.append(f"  • {err}")

        return "\n".join(lines)

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        if event.button.id == "btn-fix":
            self._start_fix_run()
        elif event.button.id == "btn-view":
            self._view_full_report()
        elif event.button.id == "btn-folder":
            self._open_report_location()
        elif event.button.id == "btn-delete":
            self._delete_report()
        elif event.button.id == "btn-refresh":
            self.action_refresh()
        elif event.button.id == "btn-close":
            self.action_cancel()

    def _start_fix_run(self):
        """Startet Fix-Lauf für den ausgewählten Report."""
        if not self.selected_report:
            self.notify("Kein Report ausgewählt", severity="warning")
            return

        report = self.selected_report

        if not report.is_fixable:
            self.notify("Dieser Report kann nicht gefixt werden", severity="warning")
            return

        # Zeige Fix-Confirmation Screen
        self.app.push_screen(FixConfirmationScreen(report, self._do_fix_run))

    def _do_fix_run(self, report: ProjectReport, options: dict):
        """Führt Fix-Lauf durch."""
        self.is_fixing = True
        log = self.query_one("#fix-log", RichLog)
        log.clear()
        log.write("🚀 Starte Fix-Lauf...")
        log.write(f"📁 Projekt: {report.project_name}")
        log.write(f"📊 Kandidaten: {len(report.candidates)}")

        # Hier würde die tatsächliche Fix-Logik kommen
        # Für jetzt simulieren wir
        import asyncio

        async def simulate_fix():
            for i, candidate in enumerate(report.candidates[:5], 1):
                log.write(f"\n🔧 Bearbeite {candidate.display_name}...")
                await asyncio.sleep(0.5)
                log.write(f"   Score: {candidate.total_score:.1f}")
                await asyncio.sleep(0.5)

            log.write("\n✅ Fix-Lauf abgeschlossen!")
            self.is_fixing = False
            self.notify("Fix-Lauf abgeschlossen", severity="information")

        self.run_worker(simulate_fix())

    def _view_full_report(self):
        """Zeigt vollen Report an."""
        if not self.selected_report:
            self.notify("Kein Report ausgewählt", severity="warning")
            return

        self.app.push_screen(ReportViewerScreen(self.selected_report))

    def _open_report_location(self):
        """Öffnet Report-Verzeichnis im System."""
        if not self.selected_project:
            self.notify("Kein Projekt ausgewählt", severity="warning")
            return

        project_dir = self.report_manager.base_dir / self.selected_project
        if project_dir.exists():
            import subprocess
            try:
                subprocess.run(["xdg-open", str(project_dir)], check=False)
                self.notify(f"Geöffnet: {project_dir}")
            except Exception as e:
                self.notify(f"Konnte nicht öffnen: {e}", severity="error")

    def _delete_report(self):
        """Löscht den ausgewählten Report."""
        if not self.selected_report:
            self.notify("Kein Report ausgewählt", severity="warning")
            return

        report = self.selected_report
        self.app.push_screen(ConfirmDeleteScreen(report, self._do_delete))

    def _do_delete(self, report: ProjectReport):
        """Führt Löschung durch."""
        if self.report_manager.delete_report(report.report_id):
            self.notify("Report gelöscht", severity="information")
            self._load_projects()
        else:
            self.notify("Fehler beim Löschen", severity="error")

    def action_refresh(self):
        """Refresh data."""
        self._load_projects()
        self.notify("Aktualisiert", severity="information")

    def action_fix(self):
        """Start fix run."""
        self._start_fix_run()

    def action_cancel(self):
        """Close screen."""
        self.app.pop_screen()


class FixConfirmationScreen(Screen):
    """Bestätigungs-Dialog für Fix-Lauf."""

    DEFAULT_CSS = """
    FixConfirmationScreen {
        align: center middle;
    }
    FixConfirmationScreen > Vertical {
        width: 70;
        height: auto;
        border: solid $success;
        padding: 1 2;
        background: $surface-darken-1;
    }
    FixConfirmationScreen Static {
        text-align: center;
        margin-bottom: 1;
    }
    FixConfirmationScreen #title {
        text-style: bold;
        color: $success;
    }
    FixConfirmationScreen #candidates-list {
        height: 10;
        border: solid $surface-darken-2;
        padding: 0 1;
        margin: 1 0;
    }
    """

    def __init__(self, report: ProjectReport, on_confirm, **kwargs):
        super().__init__(**kwargs)
        self.report = report
        self.on_confirm = on_confirm

    def compose(self):
        """Compose the screen."""
        with Vertical():
            yield Static("🚀 FIX-LAUF STARTEN", id="title")
            yield Static(f"Projekt: {self.report.project_name}")
            yield Static(f"Kandidaten: {len(self.report.candidates)}")

            # Top candidates
            yield Static("\n📋 Top Kandidaten:")
            with Vertical(id="candidates-list"):
                for c in sorted(self.report.candidates, key=lambda x: x.total_score, reverse=True)[:5]:
                    yield Static(f"  • {c.display_name} (Score: {c.total_score:.1f})")

            yield Static("\n⚙️ Optionen:")
            # Hier könnten Checkboxen für Optionen sein

            with Horizontal():
                yield Button("✅ Fix-Lauf starten", id="btn-confirm", variant="success")
                yield Button("❌ Abbrechen", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        if event.button.id == "btn-confirm":
            options = {
                "auto_apply": True,
                "sandbox": True,
            }
            self.on_confirm(self.report, options)
            self.app.pop_screen()
        elif event.button.id == "btn-cancel":
            self.app.pop_screen()


class ReportViewerScreen(Screen):
    """Screen für vollständige Report-Anzeige."""

    DEFAULT_CSS = """
    ReportViewerScreen {
        align: center middle;
    }
    ReportViewerScreen > Vertical {
        width: 95%;
        height: 95%;
        border: solid $primary;
        padding: 1;
    }
    ReportViewerScreen #report-header {
        height: auto;
        border-bottom: solid $primary;
        padding-bottom: 1;
        margin-bottom: 1;
    }
    ReportViewerScreen #report-header Static {
        text-style: bold;
        color: $primary;
    }
    ReportViewerScreen RichLog {
        height: 1fr;
        border: solid $surface-darken-2;
        padding: 0 1;
    }
    ReportViewerScreen #button-bar {
        height: auto;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("escape", "close", "Schließen"),
        ("j", "toggle_format", "JSON/Markdown"),
    ]

    def __init__(self, report: ProjectReport, **kwargs):
        super().__init__(**kwargs)
        self.report = report
        self.report_manager = get_report_manager()
        self.showing_json = False

    def compose(self):
        """Compose the screen."""
        with Vertical():
            with Vertical(id="report-header"):
                yield Static(f"📊 {self.report.display_name}")
                yield Static(f"Projekt: {self.report.project_name}")
                yield Static(f"Status: {self.report.status_icon} {self.report.state}")

            yield RichLog(id="report-content", highlight=True, markup=True)

            with Horizontal(id="button-bar"):
                yield Button("📄 Markdown [J]", id="btn-md", variant="primary")
                yield Button("📋 JSON", id="btn-json")
                yield Button("📂 Ordner", id="btn-folder")
                yield Button("✅ Schließen [ESC]", id="btn-close")

    def on_mount(self):
        """Load report content."""
        self._load_markdown()

    def _load_markdown(self):
        """Lädt Markdown-Inhalt."""
        log = self.query_one("#report-content", RichLog)
        log.clear()

        content = self.report_manager.load_report_markdown(self.report)
        if content:
            # Split by lines and write
            for line in content.split('\n')[:200]:  # Max 200 lines
                log.write(line)
        else:
            log.write("*Konnte Report nicht laden*")

        self.showing_json = False

    def _load_json(self):
        """Lädt JSON-Inhalt."""
        log = self.query_one("#report-content", RichLog)
        log.clear()

        data = self.report_manager.load_report_content(self.report)
        if data:
            import json
            json_str = json.dumps(data, indent=2, default=str)
            for line in json_str.split('\n')[:200]:
                log.write(line)
        else:
            log.write("*Konnte JSON nicht laden*")

        self.showing_json = True

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        if event.button.id == "btn-md":
            self._load_markdown()
        elif event.button.id == "btn-json":
            self._load_json()
        elif event.button.id == "btn-folder":
            self._open_folder()
        elif event.button.id == "btn-close":
            self.action_close()

    def _open_folder(self):
        """Open report folder."""
        if self.report.json_path and self.report.json_path.exists():
            import subprocess
            try:
                subprocess.run(
                    ["xdg-open", str(self.report.json_path.parent)],
                    check=False
                )
            except Exception as e:
                self.notify(f"Fehler: {e}", severity="error")

    def action_close(self):
        """Close screen."""
        self.app.pop_screen()

    def action_toggle_format(self):
        """Toggle JSON/Markdown view."""
        if self.showing_json:
            self._load_markdown()
        else:
            self._load_json()


class ConfirmDeleteScreen(Screen):
    """Bestätigungs-Dialog für Löschung."""

    DEFAULT_CSS = """
    ConfirmDeleteScreen {
        align: center middle;
    }
    ConfirmDeleteScreen > Vertical {
        width: 60;
        height: auto;
        border: solid $error;
        padding: 1 2;
        background: $surface-darken-1;
    }
    ConfirmDeleteScreen Static {
        text-align: center;
        margin-bottom: 1;
    }
    ConfirmDeleteScreen #title {
        text-style: bold;
        color: $error;
    }
    """

    def __init__(self, report: ProjectReport, on_confirm, **kwargs):
        super().__init__(**kwargs)
        self.report = report
        self.on_confirm = on_confirm

    def compose(self):
        """Compose the screen."""
        with Vertical():
            yield Static("⚠️ LÖSCHEN BESTÄTIGEN", id="title")
            yield Static(f"Report: {self.report.display_name}")
            yield Static(f"Kandidaten: {len(self.report.candidates)}")
            yield Static("\nWirklich löschen?")

            with Horizontal():
                yield Button("✅ Ja, löschen", id="btn-confirm", variant="error")
                yield Button("❌ Abbrechen", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        if event.button.id == "btn-confirm":
            self.on_confirm(self.report)
            self.app.pop_screen()
        elif event.button.id == "btn-cancel":
            self.app.pop_screen()
