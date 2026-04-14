"""
API module for GlitchHunter.

Provides FastAPI server with endpoints for analysis, status, and escalation.

Exports:
    - create_app: Factory function for FastAPI app
"""

from api.server import create_app, main

__all__ = [
    "create_app",
    "main",
]
