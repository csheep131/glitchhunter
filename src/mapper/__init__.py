"""
Repository mapper module for GlitchHunter.

Provides repository analysis, symbol extraction, and dependency graph building
using Tree-sitter and NetworkX.

Exports:
    - RepositoryMapper: Main repository analysis class
    - RepomixWrapper: Wrapper for Repomix context packing
    - SymbolGraph: Symbol graph representation
    - TreeSitterParserManager: Central parser management with caching
    - ParallelParser: Parallel file parsing with multiprocessing
    - parse_file: Convenience function for file parsing
    - parse_content: Convenience function for content parsing
    - parse_repository: Convenience function for repository parsing
"""

from mapper.repo_mapper import RepositoryMapper
from mapper.repomix_wrapper import RepomixWrapper
from mapper.symbol_graph import SymbolGraph
from mapper.tree_sitter_manager import (
    TreeSitterParserManager,
    ParseResult,
    ParseError,
    ParserStats,
    get_parser_manager,
    parse_file,
    parse_content,
)
from mapper.parallel_parser import (
    ParallelParser,
    ParallelParseResult,
    FileBatch,
    parse_repository,
    parse_files,
)

__all__ = [
    # Main Mapper
    "RepositoryMapper",
    "RepomixWrapper",
    "SymbolGraph",
    # Tree-sitter Manager
    "TreeSitterParserManager",
    "ParseResult",
    "ParseError",
    "ParserStats",
    # Parallel Parser
    "ParallelParser",
    "ParallelParseResult",
    "FileBatch",
    # Convenience Functions
    "get_parser_manager",
    "parse_file",
    "parse_content",
    "parse_repository",
    "parse_files",
]
