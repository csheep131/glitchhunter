#!/usr/bin/env python3
"""Demo des Report Centers - Zeigt alle Features."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tui.report_manager import ReportManager


def main():
    print("=" * 70)
    print("📊 GLITCHHUNTER REPORT CENTER DEMO")
    print("=" * 70)

    # Initialize report manager
    reports_dir = Path(__file__).parent.parent / "reports"
    rm = ReportManager(reports_dir)

    # Scan all reports
    reports = rm.scan_directory()

    print(f"\n🔍 Gefundene Reports: {len(reports)}")
    print("-" * 70)

    # Group by project
    projects = {}
    for report in reports:
        name = report.project_name
        if name not in projects:
            projects[name] = []
        projects[name].append(report)

    # Display projects
    for name, proj_reports in projects.items():
        print(f"\n📁 {name}")
        print(f"   Reports: {len(proj_reports)}")

        # Calculate totals
        total_candidates = sum(r.candidates_analyzed for r in proj_reports)
        total_hypotheses = sum(r.hypotheses_generated for r in proj_reports)
        total_patches = sum(r.patches_generated for r in proj_reports)

        print(f"   📊 Gesamt-Kandidaten: {total_candidates}")
        print(f"   💡 Gesamt-Hypothesen: {total_hypotheses}")
        print(f"   🔧 Gesamt-Patches: {total_patches}")

        # Show latest report
        latest = max(proj_reports, key=lambda r: r.created_at)
        print(f"\n   📝 Letzter Report:")
        print(f"      Datum: {latest.created_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"      Typ: {latest.report_type}")
        print(f"      Status: {latest.status_icon} {latest.short_summary}")
        print(f"      Fixable: {'✅ Ja' if latest.is_fixable else '❌ Nein'}")

        # Show report location
        print(f"      📂 {latest.json_path.parent}")

    print("\n" + "=" * 70)
    print("🚀 FEATURES DES REPORT CENTERS:")
    print("=" * 70)
    print("""
1. 📊 SUPER ÜBERSICHT
   • Alle Projekte mit Report-Anzahl
   • Aggregierte Statistiken (Kandidaten, Hypothesen, Patches)
   • Status-Icons für schnelle Übersicht

2. 📈 DETAIL-ANSICHT PRO REPORT
   • 4 Statistik-Boxen (Kandidaten, Patches, Findings, Hypothesen)
   • Top-Kandidaten Tabelle mit Scores
   • Markdown/JSON Viewer

3. 🚀 FIX-LAUF INTEGRATION
   • Starte Fix-Lauf direkt aus dem Report
   • Bestätigungs-Dialog mit Kandidaten-Liste
   • Live-Log während des Fix-Laufs

4. 📂 DATEI-MANAGEMENT
   • Öffne Report-Verzeichnis im Datei-Manager
   • Lösche alte Reports
   • Auto-Erkennung neuer Reports

5. 🎯 TASTENKÜRZEL
   • F2 - AnalyzeScreen (Directory Browser)
   • F3 - ReportCenter (diese Ansicht)
   • R - Refresh
   • F - Fix-Lauf starten
   • D - Report löschen
   • ESC - Zurück
""")

    print("=" * 70)
    print("✅ DEMO ABGESCHLOSSEN")
    print("=" * 70)
    print("\nStarte die TUI mit:")
    print("  cd /home/schaf/projects/glitchhunter")
    print("  venv/bin/python -m src.tui.app")
    print("\nDann drücke F3 für das Report Center!")


if __name__ == "__main__":
    main()
