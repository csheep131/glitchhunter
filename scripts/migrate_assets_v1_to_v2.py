#!/usr/bin/env python3
"""
Migrationsskript: Aktualisiert alle HTML-Templates auf die neue Asset-Struktur V2.

Änderungen:
- Alte Asset-Pfade → Neue Ordner-Struktur
- icons.css hinzufügen
- Logo-Pfade aktualisieren
"""

import re
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
# KONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

FRONTEND_DIR = Path("/home/schaf/projects/glitchhunter/ui/web/frontend")

# Asset-Pfad Mapping (alt → neu)
PATH_MAPPINGS = {
    # Navigation Icons
    "/static/assets/icon_dashboard.png": "/static/assets/nav/dashboard.png",
    "/static/assets/icon_problem.png": "/static/assets/nav/problem.png",
    "/static/assets/icon_refactor.png": "/static/assets/nav/refactor.png",
    "/static/assets/icon_reports.png": "/static/assets/nav/reports.png",
    "/static/assets/icon_history.png": "/static/assets/nav/history.png",
    "/static/assets/icon_stacks.png": "/static/assets/nav/stacks.png",
    "/static/assets/icon_models.png": "/static/assets/nav/models.png",
    "/static/assets/icon_testing.png": "/static/assets/nav/testing.png",
    "/static/assets/icon_hardware.png": "/static/assets/nav/hardware.png",
    "/static/assets/icon_settings.png": "/static/assets/nav/settings.png",
    
    # Logo
    "/static/assets/logo_small.png": "/static/assets/logo/logo_256.png",
    
    # Decorative
    "/static/assets/bifrost_divider.png": "/static/assets/decorative/bifrost_divider.png",
    "/static/assets/yggdrasil_small.png": "/static/assets/decorative/yggdrasil_banner.png",
    "/static/assets/circuit_board.png": "/static/assets/decorative/circuit_board.png",
    "/static/assets/runes_pattern.png": "/static/assets/decorative/runes_pattern.png",
    
    # Feature Icons (in decorative)
    "/static/assets/database.png": "/static/assets/decorative/database.png",
    "/static/assets/ai_brain.png": "/static/assets/decorative/ai_brain.png",
    "/static/assets/code_file.png": "/static/assets/decorative/code_file.png",
    "/static/assets/api_connection.png": "/static/assets/decorative/api_connection.png",
    "/static/assets/security_shield.png": "/static/assets/decorative/security_shield.png",
    "/static/assets/performance_speed.png": "/static/assets/decorative/performance_speed.png",
    
    # Empty States
    "/static/assets/bug_found.png": "/static/assets/empty_states/bug_found.png",
    "/static/assets/error_alert.png": "/static/assets/empty_states/error_alert.png",
    "/static/assets/empty_state.png": "/static/assets/empty_states/empty_box.png",
    "/static/assets/success_celebration.png": "/static/assets/empty_states/success_celebration.png",
    "/static/assets/analysis_complete.png": "/static/assets/empty_states/analysis_complete.png",
    "/static/assets/analysis_running.png": "/static/assets/empty_states/analysis_running.png",
    "/static/assets/loading_spinner.png": "/static/assets/empty_states/loading_spinner.png",
    
    # Status Icons
    "/static/assets/status_online.png": "/static/assets/status/online.png",
    "/static/assets/status_offline.png": "/static/assets/status/offline.png",
    "/static/assets/status_error.png": "/static/assets/status/error.png",
    "/static/assets/status_warning.png": "/static/assets/status/warning.png",
}

# CSS-Import Mapping
CSS_IMPORTS = {
    "old": '<link rel="stylesheet" href="/static/components/base.css">',
    "new": '<link rel="stylesheet" href="/static/components/base.css">\n    <link rel="stylesheet" href="/static/components/icons.css">',
}

# ═══════════════════════════════════════════════════════════════════════════
# MIGRATION
# ═══════════════════════════════════════════════════════════════════════════

def migrate_file(file_path: Path) -> dict:
    """Migriert eine einzelne HTML-Datei."""
    stats = {"changes": 0, "css_added": False}
    
    try:
        content = file_path.read_text(encoding="utf-8")
        original = content
        
        # 1. Asset-Pfade aktualisieren
        for old_path, new_path in PATH_MAPPINGS.items():
            if old_path in content:
                content = content.replace(old_path, new_path)
                stats["changes"] += 1
        
        # 2. icons.css hinzufügen (falls nicht vorhanden)
        if '/static/components/icons.css' not in content:
            content = content.replace(CSS_IMPORTS["old"], CSS_IMPORTS["new"])
            stats["css_added"] = True
        
        # Nur schreiben wenn sich etwas geändert hat
        if content != original:
            file_path.write_text(content, encoding="utf-8")
            return stats
        else:
            return {"changes": 0, "css_added": False}
            
    except Exception as e:
        print(f"   ❌ Fehler bei {file_path.name}: {e}")
        return {"changes": 0, "css_added": False, "error": str(e)}

def main():
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + "  🐛  GLITCHHUNTER ASSET MIGRATION V1 → V2".center(68) + "║")
    print("║" + "  Aktualisiert HTML-Templates auf neue Asset-Struktur".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    
    # Alle HTML-Dateien finden
    html_files = list(FRONTEND_DIR.glob("*.html"))
    print(f"\n📊 {len(html_files)} HTML-Dateien gefunden:")
    for f in html_files:
        print(f"   - {f.name}")
    
    confirm = input("\n⚠️  Migration starten? (y/n): ").strip().lower()
    if confirm != 'y':
        print("\n❌ Abgebrochen.")
        return
    
    # Migration durchführen
    total_changes = 0
    files_modified = 0
    
    print("\n" + "=" * 70)
    print("🔄 Migriere Dateien...")
    print("=" * 70)
    
    for html_file in html_files:
        stats = migrate_file(html_file)
        
        if stats["changes"] > 0 or stats["css_added"]:
            files_modified += 1
            total_changes += stats["changes"]
            
            print(f"\n✅ {html_file.name}:")
            print(f"   - {stats['changes']} Pfad-Änderungen")
            if stats["css_added"]:
                print(f"   - icons.css hinzugefügt")
        else:
            print(f"⏭️  {html_file.name} (keine Änderungen)")
    
    # Zusammenfassung
    print("\n" + "=" * 70)
    print(f"✅ MIGRATION ABGESCHLOSSEN")
    print(f"   - {files_modified}/{len(html_files)} Dateien geändert")
    print(f"   - {total_changes} Asset-Pfade aktualisiert")
    print("=" * 70)

if __name__ == "__main__":
    main()
