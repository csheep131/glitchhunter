#!/usr/bin/env python3
"""
Minimaler Test für ParallelSwarmCoordinator.

Dieses Skript testet den Coordinator direkt ohne Web-UI,
um zu prüfen ob die Kern-Analyse funktioniert.

Usage:
    python scripts/test_coordinator_minimal.py

Expected Output:
    - Coordinator Initialisierung
    - Analyse-Ergebnis mit Findings oder Errors
"""

import asyncio
import sys
import time
from pathlib import Path

# src/ zu sys.path hinzufügen für Imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from agent.parallel_swarm import ParallelSwarmCoordinator, ParallelExecutionResult


def print_header(text: str):
    """Drucke Header."""
    print()
    print("=" * 60)
    print(text)
    print("=" * 60)


def print_section(text: str):
    """Drucke Section."""
    print()
    print(f">>> {text}")
    print("-" * 40)


async def test_coordinator(repo_path: str, max_workers: int = 2):
    """
    Testet ParallelSwarmCoordinator.
    
    Args:
        repo_path: Pfad zum Repository
        max_workers: Anzahl Worker-Threads
    """
    print_header("ParallelSwarmCoordinator Test")
    
    print_section("Konfiguration")
    print(f"  Repository:     {repo_path}")
    print(f"  Max Workers:    {max_workers}")
    print(f"  Repo exists:    {Path(repo_path).exists()}")
    
    if not Path(repo_path).exists():
        print(f"\n  ❌ Repository existiert nicht!")
        return False
    
    print_section("Initialisiere Coordinator")
    start_init = time.time()
    
    try:
        coordinator = ParallelSwarmCoordinator(max_workers=max_workers)
        init_time = time.time() - start_init
        print(f"  ✓ Coordinator initialisiert in {init_time:.2f}s")
    except Exception as e:
        print(f"  ❌ Initialisierung fehlgeschlagen: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print_section("Starte Analyse")
    start_analysis = time.time()
    
    try:
        result = await coordinator.run_swarm_parallel(repo_path)
        analysis_time = time.time() - start_analysis
        
        print(f"  ✓ Analyse abgeschlossen in {analysis_time:.2f}s")
        
        # Ergebnis auswerten
        print_section("Ergebnis")
        print(f"  Success:              {result.success}")
        print(f"  Findings:             {len(result.findings)}")
        print(f"  Errors:               {len(result.errors)}")
        print(f"  Execution Time:       {result.execution_time:.2f}s")
        print(f"  Parallelization Factor: {result.parallelization_factor:.2f}x")
        
        if result.errors:
            print_section("Errors")
            for error in result.errors:
                print(f"  - {error}")
        
        if result.findings:
            print_section(f"Findings ({len(result.findings)})")
            for i, finding in enumerate(result.findings[:5], 1):  # Nur erste 5 anzeigen
                print(f"  {i}. {finding}")
            if len(result.findings) > 5:
                print(f"  ... und {len(result.findings) - 5} weitere")
        
        # Metadata
        if hasattr(result, 'metadata') and result.metadata:
            print_section("Metadata")
            for key, value in result.metadata.items():
                print(f"  {key}: {value}")
        
        return result.success
        
    except FileNotFoundError as e:
        print(f"  ❌ Datei nicht gefunden: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    except PermissionError as e:
        print(f"  ❌ Keine Berechtigung: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    except Exception as e:
        print(f"  ❌ Analyse fehlgeschlagen: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main-Funktion."""
    # Default: Teste mit GlitchHunter-Repo selbst
    repo_path = str(PROJECT_ROOT)
    
    # Override via Command-Line-Argument
    if len(sys.argv) > 1:
        repo_path = sys.argv[1]
    
    # Test ausführen
    success = asyncio.run(test_coordinator(repo_path))
    
    # Exit-Code setzen
    print_header("Zusammenfassung")
    if success:
        print("✓ Test erfolgreich")
        sys.exit(0)
    else:
        print("❌ Test fehlgeschlagen")
        sys.exit(1)


if __name__ == "__main__":
    main()
