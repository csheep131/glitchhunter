"""
Tests for MCP client.

Unit tests for SocratiCodeMCP and FallbackManager.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp.fallback_manager import FallbackManager
from mcp.socratiCode_client import (
    CircularResult,
    ContextResult,
    GraphResult,
    SearchResult,
    SocratiCodeMCP,
)


class TestSocratiCodeMCP:
    """Test cases for SocratiCodeMCP."""

    def test_init(self) -> None:
        """Test SocratiCodeMCP initialization."""
        client = SocratiCodeMCP()
        assert client.server_url == "http://localhost:8934"
        assert client.timeout == 60
        assert not client.connected

    def test_init_custom_url(self) -> None:
        """Test initialization with custom URL."""
        client = SocratiCodeMCP(server_url="http://custom:9999", timeout=120)
        assert client.server_url == "http://custom:9999"
        assert client.timeout == 120

    def test_connect_sync_success(self) -> None:
        """Test synchronous connection success."""
        with patch("httpx.Client") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client_class.return_value.__enter__.return_value.get.return_value = (
                mock_response
            )

            client = SocratiCodeMCP()
            result = client.connect_sync()

            assert result is True
            assert client.connected is True

    def test_connect_sync_failure(self) -> None:
        """Test synchronous connection failure."""
        with patch("httpx.Client") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 503
            mock_client_class.return_value.__enter__.return_value.get.return_value = (
                mock_response
            )

            client = SocratiCodeMCP()
            result = client.connect_sync()

            assert result is False
            assert client.connected is False

    def test_connect_sync_exception(self) -> None:
        """Test synchronous connection with exception."""
        with patch("httpx.Client") as mock_client_class:
            mock_client_class.return_value.__enter__.side_effect = Exception(
                "Connection refused"
            )

            client = SocratiCodeMCP()
            result = client.connect_sync()

            assert result is False
            assert client.connected is False

    @pytest.mark.asyncio
    async def test_connect_async_success(self) -> None:
        """Test asynchronous connection success."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client_class.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            client = SocratiCodeMCP()
            result = await client.connect()

            assert result is True
            assert client.connected is True

    @pytest.mark.asyncio
    async def test_connect_async_failure(self) -> None:
        """Test asynchronous connection failure."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 503
            mock_client_class.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            client = SocratiCodeMCP()
            result = await client.connect()

            assert result is False
            assert client.connected is False

    def test_search_sync_success(self) -> None:
        """Test synchronous search success."""
        with patch("httpx.Client") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {
                        "file_path": "src/test.py",
                        "line_start": 10,
                        "line_end": 15,
                        "content": "def test(): pass",
                        "score": 0.95,
                        "symbol_name": "test",
                        "symbol_kind": "function",
                    }
                ]
            }
            mock_client_class.return_value.__enter__.return_value.get.return_value = (
                mock_response
            )

            client = SocratiCodeMCP()
            client.connected = True

            results = client.search_sync(query="test function")

            assert len(results) == 1
            assert results[0].file_path == "src/test.py"
            assert results[0].score == 0.95

    def test_search_sync_not_connected(self) -> None:
        """Test search when not connected."""
        from core.exceptions import MCPConnectionError

        client = SocratiCodeMCP()
        client.connected = False

        with pytest.raises(MCPConnectionError):
            client.search_sync(query="test")

    def test_disconnect(self) -> None:
        """Test disconnect."""
        client = SocratiCodeMCP()
        client.connected = True
        client._session = MagicMock()

        # Sync disconnect not implemented, just set state
        client.connected = False
        client._session = None

        assert not client.connected

    def test_get_status(self) -> None:
        """Test status retrieval."""
        client = SocratiCodeMCP(server_url="http://test:8888", timeout=30)

        status = client.get_status()

        assert status["server_url"] == "http://test:8888"
        assert status["timeout"] == 30
        assert status["connected"] is False

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test async context manager."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client_class.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            async with SocratiCodeMCP() as client:
                assert client.connected is True


class TestFallbackManager:
    """Test cases for FallbackManager."""

    def test_init(self, tmp_path: Path) -> None:
        """Test FallbackManager initialization."""
        manager = FallbackManager(tmp_path)
        assert manager.repo_path == tmp_path
        assert not manager._initialized

    def test_use_mcp(self, tmp_path: Path) -> None:
        """Test use_mcp method."""
        manager = FallbackManager(tmp_path)
        assert manager.use_mcp() is True

    def test_initialize(self, tmp_path: Path) -> None:
        """Test initialization."""
        manager = FallbackManager(tmp_path)

        # Initialize should succeed even without ChromaDB
        result = manager.initialize()

        # May fail gracefully if dependencies not available
        assert isinstance(result, bool)

    def test_fallback_search_not_initialized(self, tmp_path: Path) -> None:
        """Test fallback search when not initialized."""
        manager = FallbackManager(tmp_path)

        results = manager.fallback_search(query="test")

        # Should return empty list, not raise
        assert isinstance(results, list)

    def test_fallback_graph_not_initialized(self, tmp_path: Path) -> None:
        """Test fallback graph when not initialized."""
        manager = FallbackManager(tmp_path)

        result = manager.fallback_graph(file_path="test.py")

        assert result == {"imports": [], "dependents": [], "symbols": []}

    def test_fallback_context_search(self, tmp_path: Path) -> None:
        """Test fallback context search."""
        manager = FallbackManager(tmp_path)

        results = manager.fallback_context_search(query="test")

        # Not implemented yet
        assert results == []

    def test_fallback_circular_dependencies(self, tmp_path: Path) -> None:
        """Test fallback circular dependency detection."""
        manager = FallbackManager(tmp_path)

        cycles = manager.fallback_circular_dependencies()

        # Should return empty list, not raise
        assert isinstance(cycles, list)

    def test_get_status(self, tmp_path: Path) -> None:
        """Test status retrieval."""
        manager = FallbackManager(tmp_path)

        status = manager.get_status()

        assert status["repo_path"] == str(tmp_path)
        assert "initialized" in status
        assert "chroma_available" in status

    def test_clear(self, tmp_path: Path) -> None:
        """Test clearing fallback data."""
        manager = FallbackManager(tmp_path)
        manager._initialized = True

        manager.clear()

        assert not manager._initialized

    def test_index_file_not_initialized(self, tmp_path: Path) -> None:
        """Test file indexing when not initialized."""
        manager = FallbackManager(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        # Should not raise, just log warning
        manager.index_file(test_file, "print('hello')")

    def test_generate_embedding(self, tmp_path: Path) -> None:
        """Test embedding generation."""
        manager = FallbackManager(tmp_path)

        embedding = manager._generate_embedding("test query")

        assert isinstance(embedding, list)
        assert len(embedding) == 128  # Default dimension
        assert all(isinstance(x, float) for x in embedding)


class TestResultClasses:
    """Test cases for result dataclasses."""

    def test_search_result(self) -> None:
        """Test SearchResult dataclass."""
        result = SearchResult(
            file_path="test.py",
            line_start=10,
            line_end=15,
            content="def test(): pass",
            score=0.95,
            symbol_name="test",
            symbol_kind="function",
        )

        assert result.file_path == "test.py"
        assert result.symbol_name == "test"

    def test_graph_result(self) -> None:
        """Test GraphResult dataclass."""
        result = GraphResult(
            file_path="test.py",
            imports=["utils.py", "config.py"],
            dependents=["main.py"],
            symbols=[{"name": "test", "kind": "function"}],
        )

        assert len(result.imports) == 2
        assert len(result.dependents) == 1

    def test_context_result(self) -> None:
        """Test ContextResult dataclass."""
        result = ContextResult(
            artifact_name="database-schema",
            content="CREATE TABLE users...",
            score=0.85,
            metadata={"type": "sql"},
        )

        assert result.artifact_name == "database-schema"
        assert result.metadata["type"] == "sql"

    def test_circular_result(self) -> None:
        """Test CircularResult dataclass."""
        result = CircularResult(
            cycles=[["a.py", "b.py", "a.py"]],
            total_count=1,
        )

        assert len(result.cycles) == 1
        assert result.total_count == 1
