"""
MCP (Model Context Protocol) module for GlitchHunter.

Provides integration with SocratiCode MCP server for hybrid semantic search,
dependency graphs, and context artifacts.

Exports:
    - SocratiCodeMCP: Main MCP client class
    - MCPConfig: MCP configuration
"""

from mcp_gw.socratiCode_client import SocratiCodeMCP
from mcp_gw.fallback_manager import FallbackManager

__all__ = [
    "SocratiCodeMCP",
    "FallbackManager",
]
