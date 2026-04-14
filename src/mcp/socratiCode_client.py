"""
SocratiCode MCP client for GlitchHunter.

Provides integration with SocratiCode MCP server for hybrid semantic search,
dependency graphs, and context artifacts.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.exceptions import MCPConnectionError

logger = logging.getLogger(__name__)

# Default MCP server configuration
DEFAULT_MCP_URL = "http://localhost:8934"
DEFAULT_TIMEOUT = 60


@dataclass
class SearchResult:
    """Represents a search result from MCP."""

    file_path: str
    line_start: int
    line_end: int
    content: str
    score: float
    symbol_name: Optional[str] = None
    symbol_kind: Optional[str] = None


@dataclass
class GraphResult:
    """Represents a graph query result."""

    file_path: str
    imports: List[str]
    dependents: List[str]
    symbols: List[Dict[str, Any]]


@dataclass
class ContextResult:
    """Represents a context artifact search result."""

    artifact_name: str
    content: str
    score: float
    metadata: Dict[str, Any]


@dataclass
class CircularResult:
    """Represents circular dependency detection result."""

    cycles: List[List[str]]
    total_count: int


class SocratiCodeMCP:
    """
    Client for SocratiCode MCP server.

    Provides methods for semantic search, graph queries, context artifact
    search, and circular dependency detection.

    Attributes:
        server_url: URL of the MCP server
        timeout: Request timeout in seconds
        connected: Connection status
    """

    def __init__(
        self,
        server_url: str = DEFAULT_MCP_URL,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """
        Initialize SocratiCode MCP client.

        Args:
            server_url: URL of the MCP server
            timeout: Request timeout in seconds
        """
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        self.connected = False
        self._session: Optional[Any] = None

        logger.debug(f"SocratiCodeMCP initialized for {server_url}")

    async def connect(self) -> bool:
        """
        Connect to the MCP server.

        Returns:
            True if connection successful
        """
        import httpx

        logger.info(f"Connecting to MCP server at {self.server_url}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.server_url}/health")
                if response.status_code == 200:
                    self.connected = True
                    self._session = client
                    logger.info("Connected to MCP server")
                    return True
                else:
                    logger.warning(f"MCP server health check failed: {response.status_code}")
                    return False

        except httpx.HTTPError as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            self.connected = False
            return False

        except Exception as e:
            logger.error(f"Unexpected error connecting to MCP server: {e}")
            self.connected = False
            return False

    def connect_sync(self) -> bool:
        """
        Synchronous connection to MCP server.

        Returns:
            True if connection successful
        """
        import httpx

        logger.info(f"Connecting to MCP server at {self.server_url}")

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.server_url}/health")
                if response.status_code == 200:
                    self.connected = True
                    logger.info("Connected to MCP server")
                    return True
                else:
                    logger.warning(f"MCP server health check failed: {response.status_code}")
                    return False

        except httpx.HTTPError as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            self.connected = False
            return False

        except Exception as e:
            logger.error(f"Unexpected error connecting to MCP server: {e}")
            self.connected = False
            return False

    async def search(
        self,
        query: str,
        limit: int = 10,
        file_filter: Optional[str] = None,
        language_filter: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Search the codebase semantically.

        Args:
            query: Natural language search query
            limit: Maximum number of results
            file_filter: Filter by file path
            language_filter: Filter by language

        Returns:
            List of search results

        Raises:
            MCPConnectionError: If not connected to server
        """
        if not self.connected:
            raise MCPConnectionError(
                "Not connected to MCP server. Call connect() first.",
                server_url=self.server_url,
            )

        import httpx

        params = {
            "query": query,
            "limit": limit,
        }
        if file_filter:
            params["fileFilter"] = file_filter
        if language_filter:
            params["languageFilter"] = language_filter

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.server_url}/codebase/search",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                results = []
                for item in data.get("results", []):
                    results.append(
                        SearchResult(
                            file_path=item.get("file_path", ""),
                            line_start=item.get("line_start", 0),
                            line_end=item.get("line_end", 0),
                            content=item.get("content", ""),
                            score=item.get("score", 0.0),
                            symbol_name=item.get("symbol_name"),
                            symbol_kind=item.get("symbol_kind"),
                        )
                    )
                return results

        except httpx.HTTPError as e:
            raise MCPConnectionError(
                f"Search request failed: {e}",
                server_url=self.server_url,
                details={"error": str(e)},
            )

    def search_sync(
        self,
        query: str,
        limit: int = 10,
        file_filter: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Synchronous codebase search.

        Args:
            query: Natural language search query
            limit: Maximum number of results
            file_filter: Filter by file path

        Returns:
            List of search results
        """
        if not self.connected:
            raise MCPConnectionError(
                "Not connected to MCP server",
                server_url=self.server_url,
            )

        import httpx

        params = {"query": query, "limit": limit}
        if file_filter:
            params["fileFilter"] = file_filter

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.server_url}/codebase/search",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                results = []
                for item in data.get("results", []):
                    results.append(
                        SearchResult(
                            file_path=item.get("file_path", ""),
                            line_start=item.get("line_start", 0),
                            line_end=item.get("line_end", 0),
                            content=item.get("content", ""),
                            score=item.get("score", 0.0),
                            symbol_name=item.get("symbol_name"),
                            symbol_kind=item.get("symbol_kind"),
                        )
                    )
                return results

        except httpx.HTTPError as e:
            raise MCPConnectionError(
                f"Search request failed: {e}",
                server_url=self.server_url,
            )

    async def graph_query(self, file_path: str) -> GraphResult:
        """
        Query dependency graph for a file.

        Args:
            file_path: Relative file path

        Returns:
            Graph query result

        Raises:
            MCPConnectionError: If not connected to server
        """
        if not self.connected:
            raise MCPConnectionError(
                "Not connected to MCP server",
                server_url=self.server_url,
            )

        import httpx

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.server_url}/codebase/graph/query",
                    params={"filePath": file_path},
                )
                response.raise_for_status()
                data = response.json()

                return GraphResult(
                    file_path=data.get("file_path", ""),
                    imports=data.get("imports", []),
                    dependents=data.get("dependents", []),
                    symbols=data.get("symbols", []),
                )

        except httpx.HTTPError as e:
            raise MCPConnectionError(
                f"Graph query failed: {e}",
                server_url=self.server_url,
            )

    async def context_search(
        self,
        query: str,
        artifact_name: Optional[str] = None,
    ) -> List[ContextResult]:
        """
        Search context artifacts (DB schemas, API specs, etc.).

        Args:
            query: Natural language search query
            artifact_name: Filter by artifact name

        Returns:
            List of context results

        Raises:
            MCPConnectionError: If not connected to server
        """
        if not self.connected:
            raise MCPConnectionError(
                "Not connected to MCP server",
                server_url=self.server_url,
            )

        import httpx

        params = {"query": query}
        if artifact_name:
            params["artifactName"] = artifact_name

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.server_url}/codebase/context/search",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                results = []
                for item in data.get("results", []):
                    results.append(
                        ContextResult(
                            artifact_name=item.get("artifact_name", ""),
                            content=item.get("content", ""),
                            score=item.get("score", 0.0),
                            metadata=item.get("metadata", {}),
                        )
                    )
                return results

        except httpx.HTTPError as e:
            raise MCPConnectionError(
                f"Context search failed: {e}",
                server_url=self.server_url,
            )

    async def circular_dependencies(self) -> CircularResult:
        """
        Detect circular dependencies in the codebase.

        Returns:
            Circular dependency detection result

        Raises:
            MCPConnectionError: If not connected to server
        """
        if not self.connected:
            raise MCPConnectionError(
                "Not connected to MCP server",
                server_url=self.server_url,
            )

        import httpx

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.server_url}/codebase/graph/circular",
                )
                response.raise_for_status()
                data = response.json()

                return CircularResult(
                    cycles=data.get("cycles", []),
                    total_count=data.get("total_count", 0),
                )

        except httpx.HTTPError as e:
            raise MCPConnectionError(
                f"Circular dependency detection failed: {e}",
                server_url=self.server_url,
            )

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        self.connected = False
        self._session = None
        logger.info("Disconnected from MCP server")

    def get_status(self) -> Dict[str, Any]:
        """
        Get MCP client status.

        Returns:
            Dictionary with status information
        """
        return {
            "server_url": self.server_url,
            "connected": self.connected,
            "timeout": self.timeout,
        }

    async def __aenter__(self) -> "SocratiCodeMCP":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()
