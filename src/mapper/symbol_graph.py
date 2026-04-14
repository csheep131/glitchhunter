"""
Symbol graph for GlitchHunter.

Represents code symbols and their relationships using NetworkX directed graphs.
Provides comprehensive symbol tracking, edge relationships, and graph operations.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

logger = logging.getLogger(__name__)


# Edge types for symbol relationships
EDGE_TYPE_CALLS = "CALLS"  # Function call
EDGE_TYPE_IMPORTS = "IMPORTS"  # Import relationship
EDGE_TYPE_EXTENDS = "EXTENDS"  # Class inheritance
EDGE_TYPE_IMPLEMENTS = "IMPLEMENTS"  # Interface implementation
EDGE_TYPE_ACCESSES = "ACCESSES"  # Field access
EDGE_TYPE_DEFINES = "DEFINES"  # Definition
EDGE_TYPE_MEMBER_OF = "MEMBER_OF"  # Member of a class


@dataclass
class SymbolNode:
    """
    Represents a code symbol in the graph.

    Attributes:
        name: Symbol name
        type: Symbol type (function, class, method, variable, import, module)
        file_path: Path to the file containing the symbol
        line_start: Starting line number (1-based)
        line_end: Ending line number (1-based)
        metadata: Additional symbol metadata
    """

    name: str
    type: str
    file_path: str
    line_start: int
    line_end: int
    signature: Optional[str] = None
    docstring: Optional[str] = None
    language: str = "python"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert symbol to dictionary."""
        return {
            "name": self.name,
            "type": self.type,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "signature": self.signature,
            "docstring": self.docstring,
            "language": self.language,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SymbolNode":
        """Create SymbolNode from dictionary."""
        return cls(
            name=data.get("name", ""),
            type=data.get("type", "unknown"),
            file_path=data.get("file_path", ""),
            line_start=data.get("line_start", 0),
            line_end=data.get("line_end", 0),
            signature=data.get("signature"),
            docstring=data.get("docstring"),
            language=data.get("language", "python"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SymbolEdge:
    """
    Represents a relationship between two symbols.

    Attributes:
        from_symbol: Source symbol name
        to_symbol: Target symbol name
        edge_type: Type of relationship
        metadata: Additional edge metadata
    """

    from_symbol: str
    to_symbol: str
    edge_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert edge to dictionary."""
        return {
            "from_symbol": self.from_symbol,
            "to_symbol": self.to_symbol,
            "edge_type": self.edge_type,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SymbolEdge":
        """Create SymbolEdge from dictionary."""
        return cls(
            from_symbol=data.get("from_symbol", ""),
            to_symbol=data.get("to_symbol", ""),
            edge_type=data.get("edge_type", ""),
            metadata=data.get("metadata", {}),
        )


class SymbolGraph:
    """
    Graph representation of code symbols and their relationships.

    Uses NetworkX DiGraph to represent directed relationships between
    symbols (functions, classes, variables, etc.). Supports serialization
    to/from JSON for persistence.

    Attributes:
        graph: NetworkX DiGraph instance

    Example:
        >>> graph = SymbolGraph()
        >>> graph.add_symbol("main", "function", "main.py", 1, 50)
        >>> graph.add_symbol("helper", "function", "utils.py", 10, 30)
        >>> graph.add_edge("main", "helper", EDGE_TYPE_CALLS)
        >>> callers = graph.get_callers("helper")
        >>> ["main"]
    """

    def __init__(self) -> None:
        """Initialize symbol graph."""
        self._graph: nx.DiGraph = nx.DiGraph()
        self._symbols: Dict[str, SymbolNode] = {}
        self._file_to_symbols: Dict[str, Set[str]] = {}

        logger.debug("SymbolGraph initialized")

    def add_symbol(
        self,
        name: str,
        type: str,
        file_path: str,
        line_start: int,
        line_end: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a symbol to the graph.

        Args:
            name: Symbol name
            type: Symbol type (function, class, method, etc.)
            file_path: Path to the file containing the symbol
            line_start: Starting line number
            line_end: Ending line number
            metadata: Additional metadata
        """
        symbol_id = self._make_symbol_id(name, file_path, line_start)

        if symbol_id in self._symbols:
            logger.debug(f"Symbol '{symbol_id}' already exists, updating")

        symbol = SymbolNode(
            name=name,
            type=type,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            metadata=metadata or {},
        )

        self._symbols[symbol_id] = symbol
        self._graph.add_node(
            symbol_id,
            name=name,
            type=type,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            **(metadata or {}),
        )

        # Track symbols by file
        if file_path not in self._file_to_symbols:
            self._file_to_symbols[file_path] = set()
        self._file_to_symbols[file_path].add(symbol_id)

        logger.debug(f"Added symbol '{symbol_id}' ({type})")

    def add_edge(
        self,
        from_symbol: str,
        to_symbol: str,
        edge_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a relationship between symbols.

        Args:
            from_symbol: Source symbol name
            to_symbol: Target symbol name
            edge_type: Type of relationship (CALLS, IMPORTS, etc.)
            metadata: Additional metadata
        """
        # Find symbol IDs by name
        from_id = self._find_symbol_id_by_name(from_symbol)
        to_id = self._find_symbol_id_by_name(to_symbol)

        if from_id is None:
            logger.warning(f"Source symbol '{from_symbol}' not found")
            return

        if to_id is None:
            logger.warning(f"Target symbol '{to_symbol}' not found")
            return

        self._graph.add_edge(
            from_id,
            to_id,
            edge_type=edge_type,
            **(metadata or {}),
        )

        logger.debug(f"Added edge: {from_symbol} --[{edge_type}]--> {to_symbol}")

    def get_symbol(self, name: str) -> Optional[SymbolNode]:
        """
        Get a symbol by name.

        Args:
            name: Symbol name

        Returns:
            SymbolNode or None if not found
        """
        symbol_id = self._find_symbol_id_by_name(name)
        if symbol_id is None:
            return None
        return self._symbols.get(symbol_id)

    def get_callers(self, symbol_name: str) -> List[str]:
        """
        Get all symbols that call/use this symbol.

        Args:
            symbol_name: Symbol name

        Returns:
            List of caller symbol names
        """
        symbol_id = self._find_symbol_id_by_name(symbol_name)
        if symbol_id is None:
            return []

        caller_ids = list(self._graph.predecessors(symbol_id))
        return [self._symbols[sid].name for sid in caller_ids if sid in self._symbols]

    def get_callees(self, symbol_name: str) -> List[str]:
        """
        Get all symbols that this symbol calls/uses.

        Args:
            symbol_name: Symbol name

        Returns:
            List of callee symbol names
        """
        symbol_id = self._find_symbol_id_by_name(symbol_name)
        if symbol_id is None:
            return []

        callee_ids = list(self._graph.successors(symbol_id))
        return [self._symbols[sid].name for sid in callee_ids if sid in self._symbols]

    def get_dependencies(self, file_path: str) -> List[str]:
        """
        Get all files that this file depends on.

        Args:
            file_path: File path

        Returns:
            List of dependent file paths
        """
        symbol_ids = self._file_to_symbols.get(file_path, set())
        dependent_files = set()

        for symbol_id in symbol_ids:
            # Get all symbols this symbol depends on (CALLS, IMPORTS edges)
            try:
                for successor in self._graph.successors(symbol_id):
                    edge_data = self._graph.get_edge_data(symbol_id, successor)
                    if edge_data and edge_data.get("edge_type") in (
                        EDGE_TYPE_CALLS,
                        EDGE_TYPE_IMPORTS,
                    ):
                        if successor in self._symbols:
                            dependent_files.add(self._symbols[successor].file_path)
            except nx.NetworkXError:
                continue

        return list(dependent_files)

    def find_cycles(self, max_length: int = 10) -> List[List[str]]:
        """
        Find circular dependencies in the graph.

        Args:
            max_length: Maximum cycle length to find

        Returns:
            List of cycles (each cycle is a list of symbol names)
        """
        cycles = []
        for cycle in nx.simple_cycles(self._graph):
            if len(cycle) <= max_length:
                cycle_names = [
                    self._symbols[sid].name for sid in cycle if sid in self._symbols
                ]
                cycles.append(cycle_names)
        return cycles

    def get_paths_between(
        self, source: str, target: str, max_depth: int = 20
    ) -> List[List[str]]:
        """
        Find all paths between two symbols.

        Args:
            source: Source symbol name
            target: Target symbol name
            max_depth: Maximum path length

        Returns:
            List of paths (each path is a list of symbol names)
        """
        source_id = self._find_symbol_id_by_name(source)
        target_id = self._find_symbol_id_by_name(target)

        if source_id is None or target_id is None:
            return []

        paths = []
        try:
            for path in nx.all_simple_paths(
                self._graph, source=source_id, target=target_id, cutoff=max_depth
            ):
                path_names = [
                    self._symbols[sid].name for sid in path if sid in self._symbols
                ]
                paths.append(path_names)
        except nx.NetworkXNoPath:
            pass

        return paths

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert graph to dictionary representation.

        Returns:
            Dictionary with nodes, edges, and stats
        """
        nodes = [symbol.to_dict() for symbol in self._symbols.values()]
        edges = []

        for source, target, data in self._graph.edges(data=True):
            edge = SymbolEdge(
                from_symbol=self._symbols[source].name if source in self._symbols else "",
                to_symbol=self._symbols[target].name if target in self._symbols else "",
                edge_type=data.get("edge_type", "unknown"),
                metadata={k: v for k, v in data.items() if k != "edge_type"},
            )
            edges.append(edge.to_dict())

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": self.get_stats(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SymbolGraph":
        """
        Create SymbolGraph from dictionary.

        Args:
            data: Dictionary with nodes and edges

        Returns:
            SymbolGraph instance
        """
        graph = cls()

        # Add nodes
        for node_data in data.get("nodes", []):
            symbol = SymbolNode.from_dict(node_data)
            symbol_id = graph._make_symbol_id(
                symbol.name, symbol.file_path, symbol.line_start
            )
            graph._symbols[symbol_id] = symbol
            graph._graph.add_node(
                symbol_id,
                name=symbol.name,
                type=symbol.type,
                file_path=symbol.file_path,
                line_start=symbol.line_start,
                line_end=symbol.line_end,
                **symbol.metadata,
            )
            if symbol.file_path not in graph._file_to_symbols:
                graph._file_to_symbols[symbol.file_path] = set()
            graph._file_to_symbols[symbol.file_path].add(symbol_id)

        # Add edges
        for edge_data in data.get("edges", []):
            edge = SymbolEdge.from_dict(edge_data)
            from_id = graph._find_symbol_id_by_name(edge.from_symbol)
            to_id = graph._find_symbol_id_by_name(edge.to_symbol)

            if from_id and to_id:
                graph._graph.add_edge(
                    from_id,
                    to_id,
                    edge_type=edge.edge_type,
                    **edge.metadata,
                )

        return graph

    def save_json(self, path: str) -> None:
        """
        Save graph to JSON file.

        Args:
            path: File path to save to
        """
        data = self.to_dict()
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"SymbolGraph saved to {path}")

    @classmethod
    def load_json(cls, path: str) -> "SymbolGraph":
        """
        Load graph from JSON file.

        Args:
            path: File path to load from

        Returns:
            SymbolGraph instance
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        logger.info(f"SymbolGraph loaded from {path}")
        return cls.from_dict(data)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get graph statistics.

        Returns:
            Dictionary with graph statistics
        """
        return {
            "symbol_count": len(self._symbols),
            "edge_count": self._graph.number_of_edges(),
            "file_count": len(self._file_to_symbols),
            "is_directed": self._graph.is_directed(),
            "density": nx.density(self._graph),
            "avg_in_degree": sum(d for _, d in self._graph.in_degree())
            / max(1, len(self._symbols)),
            "avg_out_degree": sum(d for _, d in self._graph.out_degree())
            / max(1, len(self._symbols)),
            "cycle_count": len(self.find_cycles(max_length=5)),
        }

    def clear(self) -> None:
        """Clear the graph."""
        self._graph.clear()
        self._symbols.clear()
        self._file_to_symbols.clear()
        logger.debug("SymbolGraph cleared")

    def _make_symbol_id(self, name: str, file_path: str, line_start: int) -> str:
        """
        Create unique symbol ID.

        Args:
            name: Symbol name
            file_path: File path
            line_start: Starting line number

        Returns:
            Unique symbol identifier
        """
        return f"{file_path}:{line_start}:{name}"

    def _find_symbol_id_by_name(self, name: str) -> Optional[str]:
        """
        Find symbol ID by name (with file path disambiguation if needed).

        Args:
            name: Symbol name

        Returns:
            Symbol ID or None if not found
        """
        # Try exact match first
        for symbol_id, symbol in self._symbols.items():
            if symbol.name == name:
                return symbol_id

        # Try with file path prefix
        if ":" in name:
            parts = name.split(":")
            if len(parts) >= 3:
                file_path = parts[0]
                symbol_name = parts[-1]
                for symbol_id, symbol in self._symbols.items():
                    if symbol.name == symbol_name and symbol.file_path == file_path:
                        return symbol_id

        return None

    def get_symbols_by_file(self, file_path: str) -> List[SymbolNode]:
        """
        Get all symbols in a file.

        Args:
            file_path: File path

        Returns:
            List of symbols in the file
        """
        symbol_ids = self._file_to_symbols.get(file_path, set())
        return [self._symbols[sid] for sid in symbol_ids if sid in self._symbols]

    def get_all_symbols(self) -> List[SymbolNode]:
        """
        Get all symbols in the graph.

        Returns:
            List of all symbols
        """
        return list(self._symbols.values())

    def __contains__(self, symbol_name: str) -> bool:
        """Check if symbol exists."""
        return self._find_symbol_id_by_name(symbol_name) is not None

    def __len__(self) -> int:
        """Return number of symbols."""
        return len(self._symbols)

    def __repr__(self) -> str:
        """String representation."""
        stats = self.get_stats()
        return (
            f"SymbolGraph(symbols={stats['symbol_count']}, "
            f"edges={stats['edge_count']}, files={stats['file_count']})"
        )
