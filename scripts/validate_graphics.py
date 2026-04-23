#!/usr/bin/env python3
"""
Validierungsskript: Prüft alle generierten Grafiken auf Qualität.

Checks:
1. Datei existiert
2. Mindestgröße (≥5KB)
3. Bildformat (PNG)
4. Transparenter Hintergrund (optional)
5. Unschärfe-Erkennung (optional, mit ImageMagick)
"""

import sys
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
# KONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

ASSETS_DIR = Path("/home/schaf/projects/glitchhunter/ui/web/frontend/assets")

EXPECTED_FILES = {
    "nav": [
        "dashboard.png",
        "problem.png",
        "refactor.png",
        "reports.png",
        "history.png",
        "stacks.png",
        "models.png",
        "testing.png",
        "hardware.png",
        "settings.png",
    ],
    "status": [
        "online.png",
        "offline.png",
        "error.png",
        "warning.png",
    ],
    "logo": [
        "logo_256.png",
        "logo_512.png",
        "logo_favicon.png",
    ],
    "decorative": [
        "yggdrasil_banner.png",
        "bifrost_divider.png",
    ],
    "empty_states": [
        "empty_box.png",
        "empty_search.png",
        "empty_data.png",
    ],
}

MIN_FILE_SIZE = 5000  # 5KB

# ═══════════════════════════════════════════════════════════════════════════
# VALIDIERUNG
# ═══════════════════════════════════════════════════════════════════════════

def check_file_exists(folder: str, filename: str) -> dict:
    """Prüft ob Datei existiert."""
    path = ASSETS_DIR / folder / filename
    return {
        "exists": path.exists(),
        "path": str(path),
        "size": path.stat().st_size if path.exists() else 0,
    }

def check_file_size(size: int, min_size: int = MIN_FILE_SIZE) -> dict:
    """Prüft Mindestgröße."""
    return {
        "valid": size >= min_size,
        "size": size,
        "min_size": min_size,
        "message": f"{'✅' if size >= min_size else '❌'} Größe: {size} bytes (min: {min_size})"
    }

def check_png_format(path: Path) -> dict:
    """Prüft PNG-Format."""
    try:
        with open(path, "rb") as f:
            header = f.read(8)
            is_png = header[:4] == b'\x89PNG'
            return {
                "valid": is_png,
                "message": f"{'✅' if is_png else '❌'} PNG-Format"
            }
    except Exception as e:
        return {
            "valid": False,
            "message": f"❌ Fehler beim Lesen: {e}"
        }

def validate_folder(folder: str, files: list) -> dict:
    """Validiert alle Dateien in einem Ordner."""
    results = []
    stats = {"total": len(files), "valid": 0, "invalid": 0, "missing": 0}
    
    print(f"\n📁 Ordner: /{folder}/")
    print("─" * 70)
    
    for filename in files:
        file_check = check_file_exists(folder, filename)
        
        if not file_check["exists"]:
            print(f"  ❌ {filename} - NICHT GEFUNDEN")
            stats["missing"] += 1
            results.append({"file": filename, "status": "missing"})
            continue
        
        # Größe prüfen
        size_check = check_file_size(file_check["size"])
        
        # Format prüfen
        path = Path(file_check["path"])
        format_check = check_png_format(path)
        
        # Zusammenfassung
        is_valid = size_check["valid"] and format_check["valid"]
        
        if is_valid:
            print(f"  ✅ {filename}")
            print(f"     {size_check['message']}")
            print(f"     {format_check['message']}")
            stats["valid"] += 1
            results.append({"file": filename, "status": "valid"})
        else:
            print(f"  ❌ {filename}")
            print(f"     {size_check['message']}")
            print(f"     {format_check['message']}")
            stats["invalid"] += 1
            results.append({"file": filename, "status": "invalid"})
    
    return {"folder": folder, "stats": stats, "results": results}

def main():
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + "  🐛  GLITCHHUNTER GRAPHICS VALIDATION".center(68) + "║")
    print("║" + "  Prüft alle generierten Grafiken auf Qualität".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    
    all_stats = {"total": 0, "valid": 0, "invalid": 0, "missing": 0}
    all_results = []
    
    for folder, files in EXPECTED_FILES.items():
        result = validate_folder(folder, files)
        all_stats["total"] += result["stats"]["total"]
        all_stats["valid"] += result["stats"]["valid"]
        all_stats["invalid"] += result["stats"]["invalid"]
        all_stats["missing"] += result["stats"]["missing"]
        all_results.append(result)
    
    # Zusammenfassung
    print("\n" + "=" * 70)
    print("📊 ZUSAMMENFASSUNG")
    print("=" * 70)
    print(f"  Gesamt: {all_stats['total']} Dateien")
    print(f"  ✅ Gültig: {all_stats['valid']}")
    print(f"  ❌ Ungültig: {all_stats['invalid']}")
    print(f"  ❌ Fehlend: {all_stats['missing']}")
    print(f"  Quote: {all_stats['valid']/all_stats['total']*100:.1f}%")
    
    if all_stats["invalid"] == 0 and all_stats["missing"] == 0:
        print("\n  🎉 ALLE GRAFIKEN GÜLTIG!")
        return True
    else:
        print("\n  ⚠️  Einige Grafiken benötigen Aufmerksamkeit!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
