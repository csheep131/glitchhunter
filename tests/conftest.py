"""
Pytest Conftest für Problem-Solver Tests.

Setzt sys.path korrekt für Mocks.
"""

import sys
from pathlib import Path

# src/ Verzeichnis zum Python-Pfad hinzufügen
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
