"""
Fallback manager for GlitchHunter MCP.

Provides local fallback infrastructure when SocratiCode MCP server is unavailable.
Uses ChromaDB for embeddings, NetworkX for graphs, and Repomix for context.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.exceptions import ValidationError
from ..mapper.symbol_graph import SymbolGraph

logger = logging.getLogger(__name__)


class FallbackManager:
    """
    Manages local fallback infrastructure for MCP.

    When the SocratiCode MCP server is unavailable, this class provides
    local implementations of search, graph queries, and context management
    using ChromaDB, NetworkX, and Repomix.

    Attributes:
        repo_path: Path to the repository
        chroma_path: Path to ChromaDB storage
        symbol_graph: Local symbol graph
        chroma_client: ChromaDB client (lazy-initialized)
    """

    def __init__(
        self,
        repo_path: Path,
        chroma_path: Optional[Path] = None,
    ) -> None:
        """
        Initialize fallback manager.

        Args:
            repo_path: Path to the repository
            chroma_path: Path to ChromaDB storage (optional)
        """
        self.repo_path = repo_path
        self.chroma_path = chroma_path or (repo_path / ".chroma")
        self.symbol_graph = SymbolGraph()
        self._chroma_client: Optional[Any] = None
        self._collection: Optional[Any] = None
        self._initialized = False

        logger.debug(f"FallbackManager initialized for {repo_path}")

    def use_mcp(self) -> bool:
        """
        Check if MCP should be used (vs. fallback).

        Returns:
            True if MCP is preferred (fallback available if needed)
        """
        # For now, always prefer MCP if available
        # Fallback is used only when MCP connection fails
        return True

    def initialize(self) -> bool:
        """
        Initialize fallback infrastructure.

        Returns:
            True if initialization successful
        """
        if self._initialized:
            return True

        try:
            # Initialize ChromaDB
            self._init_chroma()

            # Build local symbol graph
            self._build_symbol_graph()

            self._initialized = True
            logger.info("Fallback infrastructure initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize fallback: {e}")
            return False

    def fallback_search(
        self,
        query: str,
        limit: int = 10,
        file_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fallback semantic search using local ChromaDB.

        Args:
            query: Search query
            limit: Maximum results
            file_filter: Filter by file path

        Returns:
            List of search results
        """
        if not self._initialized:
            if not self.initialize():
                return []

        try:
            if self._collection is None:
                logger.warning("ChromaDB collection not available")
                return []

            # Generate embedding for query (using simple hash-based fallback)
            query_embedding = self._generate_embedding(query)

            # Query ChromaDB
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where={"file_path": file_filter} if file_filter else None,
            )

            # Format results
            formatted_results = []
            if results and "documents" in results:
                for i, doc in enumerate(results["documents"][0]):
                    formatted_results.append(
                        {
                            "file_path": results["metadatas"][0][i].get(
                                "file_path", ""
                            ),
                            "content": doc,
                            "score": results["distances"][0][i]
                            if "distances" in results
                            else 0.0,
                            "line_start": results["metadatas"][0][i].get(
                                "line_start", 0
                            ),
                        }
                    )

            return formatted_results

        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
            return []

    def fallback_graph(self, file_path: str) -> Dict[str, Any]:
        """
        Fallback graph query using local NetworkX graph.

        Args:
            file_path: File path to query

        Returns:
            Graph query result
        """
        if not self._initialized:
            if not self.initialize():
                return {"imports": [], "dependents": [], "symbols": []}

        try:
            # Get symbols from the file
            symbols = self.symbol_graph.get_symbols_by_file(file_path)

            imports = []
            dependents = []

            for symbol in symbols:
                symbol_id = self.symbol_graph._make_symbol_id(symbol)

                # Get dependencies (imports)
                deps = self.symbol_graph.get_dependencies(symbol_id)
                for dep_id in deps:
                    dep_symbol = self.symbol_graph.get_symbol(dep_id)
                    if dep_symbol and dep_symbol.file_path != file_path:
                        imports.append(dep_symbol.file_path)

                # Get dependents
                dependents_ids = self.symbol_graph.get_dependents(symbol_id)
                for dep_id in dependents_ids:
                    dep_symbol = self.symbol_graph.get_symbol(dep_id)
                    if dep_symbol and dep_symbol.file_path != file_path:
                        dependents.append(dep_symbol.file_path)

            return {
                "file_path": file_path,
                "imports": list(set(imports)),
                "dependents": list(set(dependents)),
                "symbols": [s.to_dict() for s in symbols],
            }

        except Exception as e:
            logger.error(f"Fallback graph query failed: {e}")
            return {"imports": [], "dependents": [], "symbols": []}

    def fallback_context_search(
        self,
        query: str,
        artifact_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fallback context search (simplified).

        Args:
            query: Search query
            artifact_name: Filter by artifact name

        Returns:
            List of context results
        """
        # TODO: Implement context artifact indexing and search
        # For now, return empty results
        logger.warning("Context search not implemented in fallback mode")
        return []

    def fallback_circular_dependencies(self) -> List[List[str]]:
        """
        Fallback circular dependency detection.

        Returns:
            List of cycles
        """
        if not self._initialized:
            if not self.initialize():
                return []

        try:
            cycles = self.symbol_graph.find_cycles(max_length=10)

            # Convert to file paths
            file_cycles = []
            for cycle in cycles:
                file_cycle = []
                for symbol_id in cycle:
                    symbol = self.symbol_graph.get_symbol(symbol_id)
                    if symbol:
                        file_cycle.append(symbol.file_path)
                if file_cycle:
                    file_cycles.append(list(set(file_cycle)))

            return file_cycles

        except Exception as e:
            logger.error(f"Fallback circular dependency detection failed: {e}")
            return []

    def _init_chroma(self) -> None:
        """Initialize ChromaDB client and collection."""
        try:
            import chromadb
            from chromadb.config import Settings

            # Ensure directory exists
            self.chroma_path.mkdir(parents=True, exist_ok=True)

            # Initialize persistent client
            self._chroma_client = chromadb.PersistentClient(
                path=str(self.chroma_path)
            )

            # Get or create collection
            self._collection = self._chroma_client.get_or_create_collection(
                name="codebase",
                metadata={"description": "Code embeddings for fallback search"},
            )

            logger.debug(f"ChromaDB initialized at {self.chroma_path}")

        except ImportError:
            logger.warning("ChromaDB not available, falling back to basic search")
            self._chroma_client = None
            self._collection = None

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self._chroma_client = None
            self._collection = None

    def _build_symbol_graph(self) -> None:
        """Build local symbol graph."""
        try:
            from ..mapper.repo_mapper import RepositoryMapper

            mapper = RepositoryMapper(self.repo_path)
            self.symbol_graph = mapper.build_symbol_graph(max_files=500)

            logger.debug(
                f"Symbol graph built: {self.symbol_graph.get_symbol_count()} symbols"
            )

        except Exception as e:
            logger.error(f"Failed to build symbol graph: {e}")

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate a simple embedding for text.

        This is a placeholder - in production, use a proper embedding model.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (128 dimensions)
        """
        # Simple hash-based embedding (not semantic, just for demo)
        import hashlib

        embedding_dim = 128
        hash_bytes = hashlib.md5(text.encode()).digest()

        # Convert hash to float vector
        embedding = []
        for i in range(embedding_dim):
            byte_idx = i % len(hash_bytes)
            # Normalize to [-1, 1]
            value = (hash_bytes[byte_idx] / 128.0) - 1.0
            embedding.append(value)

        return embedding

    def index_file(self, file_path: Path, content: str) -> None:
        """
        Index a file in ChromaDB.

        Args:
            file_path: Path to the file
            content: File content
        """
        if self._collection is None:
            logger.warning("ChromaDB not initialized, skipping index")
            return

        try:
            # Split content into chunks (by lines)
            lines = content.split("\n")
            chunk_size = 50  # lines per chunk

            for i in range(0, len(lines), chunk_size):
                chunk = "\n".join(lines[i : i + chunk_size])
                line_start = i + 1

                # Generate ID
                doc_id = f"{file_path}:{line_start}"

                # Generate embedding
                embedding = self._generate_embedding(chunk)

                # Add to collection
                self._collection.add(
                    documents=[chunk],
                    embeddings=[embedding],
                    ids=[doc_id],
                    metadatas=[
                        {
                            "file_path": str(file_path),
                            "line_start": line_start,
                            "line_end": i + chunk_size,
                        }
                    ],
                )

            logger.debug(f"Indexed {file_path}")

        except Exception as e:
            logger.error(f"Failed to index {file_path}: {e}")

    def get_status(self) -> Dict[str, Any]:
        """
        Get fallback manager status.

        Returns:
            Dictionary with status information
        """
        return {
            "repo_path": str(self.repo_path),
            "chroma_path": str(self.chroma_path),
            "initialized": self._initialized,
            "chroma_available": self._chroma_client is not None,
            "symbol_count": self.symbol_graph.get_symbol_count(),
            "graph_edge_count": self.symbol_graph.get_edge_count(),
        }

    def clear(self) -> None:
        """Clear all fallback data."""
        self.symbol_graph.clear()
        if self._collection:
            self._collection.delete(where={})
        self._initialized = False
        logger.debug("FallbackManager cleared")
