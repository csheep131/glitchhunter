"""
Backend für GlitchHunter Web-UI.

FastAPI Server mit REST-API und WebSocket-Unterstützung.
"""

from ui.web.backend.app import create_app, main

__all__ = ["create_app", "main"]
