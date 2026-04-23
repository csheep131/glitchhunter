"""
Web-UI für GlitchHunter v3.0.

FastAPI Backend mit React Dashboard für:
- Repository-Analyse
- Live-Ergebnisse
- Team-Collaboration
- Auto-Refactoring
"""

from ui.web.backend.app import create_app, main

__all__ = ["create_app", "main"]
