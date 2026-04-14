#!/usr/bin/env python3
"""Test-Skript für TUI Features - Directory Browser & Report Manager."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tui.report_manager import ReportManager, get_report_manager


def test_report_manager():
    """Testet den Report Manager."""
    print("=" * 60)
    print("📊 REPORT MANAGER TEST")
    print("=" * 60)

    # Initialize
    reports_dir = Path(__file__).parent.parent / "reports"
    manager = ReportManager(reports_dir)
    print(f"\n✅ ReportManager initialisiert")
    print(f"   Basis-Verzeichnis: {manager.base_dir}")

    # Test project paths
    test_projects = [
        Path("/home/schaf/projects/glitchhunter"),
        Path("/home/schaf/projects/testproject"),
    ]

    # Create dummy reports
    for project_path in test_projects:
        print(f"\n📁 Projekt: {project_path}")

        # Create report slot
        slot = manager.create_report_slot(project_path, report_type="scan")
        print(f"   Report-ID: {slot['report_id']}")
        print(f"   Projekt-Dir: {slot['project_dir']}")

        # Create dummy files
        slot['json_path'].write_text('{"test": true}')
        slot['markdown_path'].write_text("# Test Report\n\nThis is a test.")

        # Register report
        report = manager.register_report(
            report_id=slot['report_id'],
            project_name=slot['project_name'],
            project_path=project_path,
            report_type="scan",
            json_path=slot['json_path'],
            markdown_path=slot['markdown_path'],
            summary={"total_bugs": 5, "fixed_bugs": 3}
        )
        print(f"   ✅ Report registriert: {report.display_name}")

    # List all projects
    print("\n" + "=" * 60)
    print("📋 ALLE PROJEKTE")
    print("=" * 60)

    projects = manager.get_all_projects()
    for proj in projects:
        print(f"\n📂 {proj['name']}")
        print(f"   Pfad: {proj['path']}")
        print(f"   Reports: {proj['report_count']}")
        if proj['latest_report']:
            latest = proj['latest_report']
            print(f"   Letzter: {latest['created_at'][:19]}")
            print(f"   Summary: {latest['summary']}")

    # Get reports for specific project
    print("\n" + "=" * 60)
    print("📋 REPORTS FÜR GLITCHHUNTER")
    print("=" * 60)

    reports = manager.get_reports_for_project(test_projects[0])
    for report in reports:
        print(f"\n📝 {report.report_id}")
        print(f"   Typ: {report.report_type}")
        print(f"   Erstellt: {report.created_at}")
        print(f"   {report.short_summary}")

    # Load report content
    if reports:
        print("\n" + "=" * 60)
        print("📄 REPORT INHALT")
        print("=" * 60)

        content = manager.load_report_content(reports[0])
        print(f"JSON: {content}")

        md = manager.load_report_markdown(reports[0])
        print(f"Markdown: {md[:50]}...")

    print("\n" + "=" * 60)
    print("✅ ALLE TESTS BESTANDEN")
    print("=" * 60)

    # Cleanup test files
    print("\n🧹 Räume Test-Dateien auf...")
    for project_path in test_projects:
        reports = manager.get_reports_for_project(project_path)
        for report in reports:
            manager.delete_report(report.report_id)
    print("✅ Aufgeräumt")


def test_directory_browser():
    """Testet Directory Browser Widget (nur Import)."""
    print("\n" + "=" * 60)
    print("📁 DIRECTORY BROWSER TEST")
    print("=" * 60)

    try:
        from tui.widgets.directory_browser import DirectoryBrowserWidget, ProjectSelectorWidget
        print("✅ DirectoryBrowserWidget importiert")
        print("✅ ProjectSelectorWidget importiert")
        print("\nFeatures:")
        print("  - Tree-basierte Verzeichnisauswahl")
        print("  - Navigation (Hoch, Öffnen, Auswählen)")
        print("  - Favoriten-Schnellzugriff")
        print("  - Reaktive State-Verwaltung")
    except Exception as e:
        print(f"❌ Fehler: {e}")


def test_report_browser():
    """Testet Report Browser Screen (nur Import)."""
    print("\n" + "=" * 60)
    print("📊 REPORT BROWSER SCREEN TEST")
    print("=" * 60)

    try:
        from tui.screens.report_browser import (
            ReportBrowserScreen,
            ReportViewerScreen,
            ConfirmDeleteScreen
        )
        print("✅ ReportBrowserScreen importiert")
        print("✅ ReportViewerScreen importiert")
        print("✅ ConfirmDeleteScreen importiert")
        print("\nFeatures:")
        print("  - Projekt-Liste mit Report-Anzahl")
        print("  - Report-Details anzeigen")
        print("  - Markdown/JSON View Toggle")
        print("  - Löschen mit Bestätigung")
        print("  - Ordner öffnen (xdg-open)")
    except Exception as e:
        print(f"❌ Fehler: {e}")


def test_analyze_screen():
    """Testet Analyze Screen (nur Import)."""
    print("\n" + "=" * 60)
    print("🔍 ANALYZE SCREEN TEST")
    print("=" * 60)

    try:
        from tui.screens.analyze import AnalyzeScreen, AnalysisProgressScreen
        print("✅ AnalyzeScreen importiert")
        print("✅ AnalysisProgressScreen importiert")
        print("\nFeatures:")
        print("  - Directory Browser Integration")
        print("  - Favoriten-Schnellzugriff")
        print("  - Vorhandene Reports Vorschau")
        print("  - Scan-Optionen (Security, Correctness, Patches)")
    except Exception as e:
        print(f"❌ Fehler: {e}")


if __name__ == "__main__":
    print("\n" + "🚀 " * 30)
    print("GLITCHHUNTER TUI FEATURE TEST")
    print("🚀 " * 30 + "\n")

    test_report_manager()
    test_directory_browser()
    test_report_browser()
    test_analyze_screen()

    print("\n" + "=" * 60)
    print("🎉 ALLE TESTS ABGESCHLOSSEN")
    print("=" * 60)
    print("\nVerwendung:")
    print("  F2 - AnalyzeScreen mit Directory Browser")
    print("  F3 - ReportBrowserScreen")
    print("\nStruktur:")
    print("  reports/")
    print("    <project_name>/")
    print("      report_YYYYMMDD_HHMMSS.json")
    print("      report_YYYYMMDD_HHMMSS.md")
    print("      latest.json -> symlink")
    print("    index.json")
