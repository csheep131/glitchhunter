"""
Repository mapper for GlitchHunter.

Builds symbol graphs, extracts dependencies, and analyzes repository structure
using Tree-sitter and NetworkX. Supports Python, JavaScript/TypeScript, Rust,
and extensible to Go, Java, C/C++, C#.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from mapper.symbol_graph import SymbolGraph, SymbolNode, EDGE_TYPE_CALLS, EDGE_TYPE_IMPORTS, EDGE_TYPE_EXTENDS, EDGE_TYPE_IMPLEMENTS, EDGE_TYPE_MEMBER_OF, EDGE_TYPE_DEFINES
from core.ignore import IgnoreManager

logger = logging.getLogger(__name__)


@dataclass
class RepoManifest:
    """
    Repository manifest with metadata.

    Attributes:
        repo_path: Path to the repository
        languages: Detected languages
        file_count: Total number of files
        total_lines: Total lines of code
        entry_points: List of entry point files
        dependencies: Project dependencies
    """

    repo_path: str
    languages: List[str] = field(default_factory=list)
    file_count: int = 0
    total_lines: int = 0
    entry_points: List[str] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "repo_path": self.repo_path,
            "languages": self.languages,
            "file_count": self.file_count,
            "total_lines": self.total_lines,
            "entry_points": self.entry_points,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
        }


# Language to file extension mapping
LANGUAGE_EXTENSIONS: Dict[str, List[str]] = {
    "python": [".py", ".pyw"],
    "javascript": [".js", ".jsx", ".mjs", ".cjs"],
    "typescript": [".ts", ".tsx"],
    "rust": [".rs"],
    "go": [".go"],
    "java": [".java"],
    "c": [".c", ".h"],
    "cpp": [".cpp", ".cc", ".cxx", ".hpp", ".hh"],
    "csharp": [".cs"],
}

# Entry point patterns per language
ENTRY_POINT_PATTERNS: Dict[str, List[str]] = {
    "python": ["main.py", "__main__.py", "app.py", "wsgi.py", "asgi.py"],
    "javascript": ["index.js", "main.js", "app.js", "server.js"],
    "typescript": ["index.ts", "main.ts", "app.ts"],
    "rust": ["main.rs", "lib.rs"],
    "go": ["main.go"],
    "java": ["Main.java", "Application.java"],
}


class RepositoryMapper:
    """
    Maps repository structure and builds symbol graphs.

    Uses Tree-sitter for AST parsing and NetworkX for graph representation.
    Provides methods for dependency analysis and call graph construction.
    Supports incremental scanning with cache persistence.

    Attributes:
        repo_path: Path to the repository
        symbol_graph: Built symbol graph
        languages: Detected languages in the repository

    Example:
        >>> mapper = RepositoryMapper(Path("/path/to/repo"))
        >>> manifest = mapper.scan_repository()
        >>> mapper.build_graph()
        >>> graph = mapper.symbol_graph
    """

    def __init__(
        self,
        repo_path: Path,
        persist_path: Optional[Path] = None,
        auto_persist: bool = True,
    ) -> None:
        """
        Initialize repository mapper.

        Args:
            repo_path: Path to the repository
            persist_path: Optional path for symbol graph persistence
            auto_persist: If True, enable auto-save on shutdown
        """
        self.repo_path = repo_path
        self.persist_path = persist_path
        self.auto_persist = auto_persist

        # Initialize symbol graph with persistence
        self.symbol_graph = SymbolGraph(
            repo_path=str(repo_path),
            persist_path=str(persist_path) if persist_path else None,
            auto_persist=auto_persist,
        )

        self.languages: Set[str] = set()
        self._parsers: Dict[str, Any] = {}
        self._parser_cache: Dict[str, Any] = {}
        self.ignore_manager = IgnoreManager(repo_path)

        logger.debug(f"RepositoryMapper initialized for {repo_path}")

    def scan_repository(self) -> RepoManifest:
        """
        Scan repository and create manifest.

        Returns:
            RepoManifest with repository metadata
        """
        logger.info(f"📂 Scanning repository: {self.repo_path}")

        manifest = RepoManifest(repo_path=str(self.repo_path))
        file_count = 0
        total_lines = 0
        detected_languages: Set[str] = set()

        # Detect languages and count files
        logger.info("   └─ Detecting languages and counting files...")
        for lang, extensions in LANGUAGE_EXTENSIONS.items():
            lang_file_count = 0
            for ext in extensions:
                for file_path in self.repo_path.rglob(f"*{ext}"):
                    # Skip hidden directories and common ignore patterns
                    if self._should_ignore(file_path):
                        continue

                    lang_file_count += 1
                    file_count += 1

                    # Count lines
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            total_lines += sum(1 for _ in f)
                    except Exception:
                        pass

            if lang_file_count > 0:
                detected_languages.add(lang)
                manifest.dependencies[lang] = []

        self.languages = detected_languages
        manifest.languages = list(detected_languages)
        manifest.file_count = file_count
        manifest.total_lines = total_lines

        # Find entry points
        logger.info("   └─ Finding entry points...")
        manifest.entry_points = self._find_entry_points()

        # Read project dependencies
        logger.info("   └─ Reading project dependencies...")
        manifest.dependencies = self._read_project_dependencies()

        manifest.metadata = {
            "scanned_at": str(Path.cwd()),
            "language_distribution": {
                lang: len(list(self.repo_path.rglob(f"*{LANGUAGE_EXTENSIONS[lang][0]}")))
                for lang in detected_languages
            },
        }

        logger.info(
            f"✅ Repository scan complete: {file_count} files, "
            f"{total_lines} lines, languages: {manifest.languages}"
        )

        return manifest

    def parse_all_files(self) -> None:
        """
        Parse all supported files in the repository.

        Extracts symbols from all files and adds them to the symbol graph.
        """
        logger.info("📄 Parsing all files in repository...")

        symbols_parsed = 0
        for language in self.languages:
            extensions = LANGUAGE_EXTENSIONS.get(language, [])
            for ext in extensions:
                for file_path in self.repo_path.rglob(f"*{ext}"):
                    if self._should_ignore(file_path):
                        continue

                    try:
                        symbols = self.parse_file(file_path)
                        symbols_parsed += len(symbols)
                        if len(symbols) > 0:
                            logger.debug(f"  ✓ {file_path.name}: {len(symbols)} symbols")
                    except Exception as e:
                        logger.warning(f"Failed to parse {file_path}: {e}")

        logger.info(f"✅ Parsing complete: {symbols_parsed} symbols extracted")

    def build_graph(self, incremental: bool = True) -> SymbolGraph:
        """
        Build symbol graph for the repository.

        Parses all files and extracts symbols with their relationships.
        Supports incremental scanning with cache.

        Args:
            incremental: If True, only parse changed files when cache is valid

        Returns:
            Built SymbolGraph
        """
        # Try to use cache for incremental scan
        if incremental and self._can_use_cache():
            logger.info("✅ Using cached symbol graph (incremental scan)")
            # Only parse changed files
            changed_files = self.scan_changed_files()
            if changed_files:
                logger.info(f"   └─ Parsing {len(changed_files)} changed file(s)...")
                self._parse_files(changed_files)
            return self.symbol_graph

        logger.info("🕸️  Building symbol graph (full scan)...")

        # Parse all files
        self.parse_all_files()

        # Extract edges (relationships) between symbols
        logger.info("   └─ Extracting import relationships...")
        self._extract_import_edges()
        logger.info("   └─ Extracting call relationships...")
        self._extract_call_edges()
        logger.info("   └─ Extracting inheritance relationships...")
        self._extract_inheritance_edges()

        stats = self.symbol_graph.get_stats()
        logger.info(
            f"✅ Symbol graph complete: {stats['symbol_count']} symbols, "
            f"{stats['edge_count']} edges, {stats['file_count']} files"
        )

        return self.symbol_graph

    def _can_use_cache(self) -> bool:
        """
        Prüft ob Cache verwendet werden kann.

        Returns:
            True if cache exists and is valid
        """
        if not self.symbol_graph.persist_path:
            return False

        # Check if persist file exists
        pickle_path = (
            self.symbol_graph.persist_path.with_suffix(".pkl")
            if self.symbol_graph.persist_path.suffix != ".pkl"
            else self.symbol_graph.persist_path
        )

        if not pickle_path.exists():
            logger.debug(f"Cache file not found: {pickle_path}")
            return False

        # Try to load - will validate hash internally
        return self.symbol_graph.load_pickle(str(pickle_path))

    def _parse_files(self, file_paths: List[str]) -> None:
        """
        Parse specific files and update symbol graph.

        Args:
            file_paths: List of file paths to parse
        """
        symbols_parsed = 0
        for file_path_str in file_paths:
            file_path = Path(file_path_str)
            if not file_path.is_absolute():
                file_path = self.repo_path / file_path_str

            if self.ignore_manager.should_ignore(file_path):
                continue

            try:
                language = self.get_file_language(file_path)
                if language == "unknown":
                    continue

                symbols = self.parse_file(file_path)
                symbols_parsed += len(symbols)
                logger.debug(f"  ✓ {file_path.name}: {len(symbols)} symbols")
            except Exception as e:
                logger.warning(f"Failed to parse {file_path}: {e}")

        logger.debug(f"Incremental parse complete: {symbols_parsed} symbols")

    def get_file_language(self, file_path: Path) -> str:
        """
        Get programming language for a file.

        Args:
            file_path: Path to the file

        Returns:
            Language name or 'unknown'
        """
        extension = file_path.suffix.lower()

        for language, extensions in LANGUAGE_EXTENSIONS.items():
            if extension in extensions:
                return language

        return "unknown"

    def parse_file(self, file_path: Path) -> List[Any]:
        """
        Parse a file and extract symbols.

        Uses Tree-sitter for AST-based symbol extraction.

        Args:
            file_path: Path to the file

        Returns:
            List of extracted SymbolNode objects
        """
        if not file_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return []

        language = self.get_file_language(file_path)
        if language == "unknown":
            logger.debug(f"  ⊘ {file_path.name}: unsupported language")
            return []
        
        logger.debug(f"  🌳 {file_path.name}: parsing with Tree-sitter ({language})")

        try:
            if language == "python":
                return self._parse_python_file(file_path)
            elif language in ("javascript", "typescript"):
                return self._parse_javascript_file(file_path)
            elif language == "rust":
                return self._parse_rust_file(file_path)
            elif language == "go":
                return self._parse_go_file(file_path)
            elif language == "java":
                return self._parse_java_file(file_path)
            else:
                logger.debug(f"Parsing not implemented for {language}")
                return []

        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return []

    def _parse_python_file(self, file_path: Path) -> List[Any]:
        """Parse Python file and extract symbols."""

        symbols = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            content = "".join(lines)
            tree = self._get_tree_sitter_tree(content, "python")

            if tree:
                return self._extract_python_symbols(tree, str(file_path), lines)

            # Fallback: regex-based extraction
            import re

            for line_num, line in enumerate(lines, 1):
                # Function definitions
                func_match = re.search(r"^(\s*)def\s+(\w+)\s*\(", line)
                if func_match:
                    indent = len(func_match.group(1))
                    func_name = func_match.group(2)
                    symbol_type = "method" if indent > 0 else "function"

                    # Find function end (simplified)
                    line_end = self._find_block_end(lines, line_num - 1, indent)

                    symbol = SymbolNode(
                        name=func_name,
                        type=symbol_type,
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_end,
                        language="python",
                    )
                    symbols.append(symbol)
                    self.symbol_graph.add_symbol(
                        name=func_name,
                        type=symbol_type,
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_end,
                    )

                # Class definitions
                class_match = re.search(r"^(\s*)class\s+(\w+)", line)
                if class_match:
                    class_name = class_match.group(2)
                    line_end = self._find_block_end(lines, line_num - 1, len(class_match.group(1)))

                    symbol = SymbolNode(
                        name=class_name,
                        type="class",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_end,
                        language="python",
                    )
                    symbols.append(symbol)
                    self.symbol_graph.add_symbol(
                        name=class_name,
                        type="class",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_end,
                    )

                # Import statements
                import_match = re.search(r"^(?:from\s+([\w.]+)\s+)?import\s+(.+)", line)
                if import_match:
                    from_module = import_match.group(1)
                    imports = import_match.group(2)

                    for imp in imports.split(","):
                        imp_name = imp.strip().split(" as ")[-1].strip()
                        symbol = SymbolNode(
                            name=imp_name,
                            type="import",
                            file_path=str(file_path),
                            line_start=line_num,
                            line_end=line_num,
                            metadata={"from_module": from_module} if from_module else {},
                            language="python",
                        )
                        symbols.append(symbol)
                        self.symbol_graph.add_symbol(
                            name=imp_name,
                            type="import",
                            file_path=str(file_path),
                            line_start=line_num,
                            line_end=line_num,
                            metadata={"from_module": from_module} if from_module else {},
                        )

        except Exception as e:
            logger.error(f"Error in Python parsing {file_path}: {e}")

        return symbols

    def _parse_javascript_file(self, file_path: Path) -> List[Any]:
        """Parse JavaScript/TypeScript file and extract symbols."""

        symbols = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            content = "".join(lines)
            tree = self._get_tree_sitter_tree(content, "javascript")

            if tree:
                return self._extract_javascript_symbols(tree, str(file_path), lines)

            # Fallback: regex-based extraction
            import re

            for line_num, line in enumerate(lines, 1):
                # Function declarations
                func_match = re.search(r"function\s+(\w+)\s*\(", line)
                if func_match:
                    func_name = func_match.group(1)
                    symbol = SymbolNode(
                        name=func_name,
                        type="function",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 20,  # Estimate
                        language="javascript",
                    )
                    symbols.append(symbol)
                    self.symbol_graph.add_symbol(
                        name=func_name,
                        type="function",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 20,
                    )

                # Arrow functions assigned to constants
                arrow_match = re.search(r"const\s+(\w+)\s*=\s*(?:async\s+)?\(", line)
                if arrow_match:
                    func_name = arrow_match.group(1)
                    symbol = SymbolNode(
                        name=func_name,
                        type="function",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 20,
                        language="javascript",
                    )
                    symbols.append(symbol)
                    self.symbol_graph.add_symbol(
                        name=func_name,
                        type="function",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 20,
                    )

                # Class declarations
                class_match = re.search(r"class\s+(\w+)", line)
                if class_match:
                    class_name = class_match.group(1)
                    symbol = SymbolNode(
                        name=class_name,
                        type="class",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 50,
                        language="javascript",
                    )
                    symbols.append(symbol)
                    self.symbol_graph.add_symbol(
                        name=class_name,
                        type="class",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 50,
                    )

                # Import statements
                import_match = re.search(
                    r"import\s+(?:{([^}]+)}|(\w+))\s+from\s+['\"]([^'\"]+)['\"]", line
                )
                if import_match:
                    named_imports = import_match.group(1)
                    default_import = import_match.group(2)
                    from_module = import_match.group(3)

                    imports = []
                    if named_imports:
                        imports = [i.strip().split(" as ")[-1].strip() for i in named_imports.split(",")]
                    if default_import:
                        imports.append(default_import)

                    for imp_name in imports:
                        symbol = SymbolNode(
                            name=imp_name,
                            type="import",
                            file_path=str(file_path),
                            line_start=line_num,
                            line_end=line_num,
                            metadata={"from_module": from_module},
                            language="javascript",
                        )
                        symbols.append(symbol)
                        self.symbol_graph.add_symbol(
                            name=imp_name,
                            type="import",
                            file_path=str(file_path),
                            line_start=line_num,
                            line_end=line_num,
                            metadata={"from_module": from_module},
                        )

        except Exception as e:
            logger.error(f"Error in JavaScript parsing {file_path}: {e}")

        return symbols

    def _parse_rust_file(self, file_path: Path) -> List[Any]:
        """Parse Rust file and extract symbols."""

        symbols = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            content = "".join(lines)
            tree = self._get_tree_sitter_tree(content, "rust")

            if tree:
                return self._extract_rust_symbols(tree, str(file_path), lines)

            # Fallback: regex-based extraction
            import re

            for line_num, line in enumerate(lines, 1):
                # Function definitions
                func_match = re.search(r"^(?:pub\s+)?(?:unsafe\s+)?fn\s+(\w+)", line)
                if func_match:
                    func_name = func_match.group(1)
                    symbol = SymbolNode(
                        name=func_name,
                        type="function",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 30,
                        language="rust",
                    )
                    symbols.append(symbol)
                    self.symbol_graph.add_symbol(
                        name=func_name,
                        type="function",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 30,
                    )

                # Struct definitions
                struct_match = re.search(r"^(?:pub\s+)?struct\s+(\w+)", line)
                if struct_match:
                    struct_name = struct_match.group(1)
                    symbol = SymbolNode(
                        name=struct_name,
                        type="struct",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 50,
                        language="rust",
                    )
                    symbols.append(symbol)
                    self.symbol_graph.add_symbol(
                        name=struct_name,
                        type="struct",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 50,
                    )

                # Enum definitions
                enum_match = re.search(r"^(?:pub\s+)?enum\s+(\w+)", line)
                if enum_match:
                    enum_name = enum_match.group(1)
                    symbol = SymbolNode(
                        name=enum_name,
                        type="enum",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 50,
                        language="rust",
                    )
                    symbols.append(symbol)
                    self.symbol_graph.add_symbol(
                        name=enum_name,
                        type="enum",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 50,
                    )

                # Trait definitions
                trait_match = re.search(r"^(?:pub\s+)?trait\s+(\w+)", line)
                if trait_match:
                    trait_name = trait_match.group(1)
                    symbol = SymbolNode(
                        name=trait_name,
                        type="trait",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 50,
                        language="rust",
                    )
                    symbols.append(symbol)
                    self.symbol_graph.add_symbol(
                        name=trait_name,
                        type="trait",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 50,
                    )

                # Use statements
                use_match = re.search(r"use\s+([^;]+);", line)
                if use_match:
                    use_path = use_match.group(1)
                    # Extract the last component as the symbol name
                    parts = use_path.strip().split("::")
                    if parts:
                        imp_name = parts[-1].split(" as ")[-1].strip()
                        symbol = SymbolNode(
                            name=imp_name,
                            type="import",
                            file_path=str(file_path),
                            line_start=line_num,
                            line_end=line_num,
                            metadata={"use_path": use_path},
                            language="rust",
                        )
                        symbols.append(symbol)
                        self.symbol_graph.add_symbol(
                            name=imp_name,
                            type="import",
                            file_path=str(file_path),
                            line_start=line_num,
                            line_end=line_num,
                            metadata={"use_path": use_path},
                        )

        except Exception as e:
            logger.error(f"Error in Rust parsing {file_path}: {e}")

        return symbols

    def _parse_go_file(self, file_path: Path) -> List[Any]:
        """Parse Go file and extract symbols."""

        symbols = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            import re

            for line_num, line in enumerate(lines, 1):
                # Function definitions
                func_match = re.search(r"func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(", line)
                if func_match:
                    func_name = func_match.group(1)
                    symbol = SymbolNode(
                        name=func_name,
                        type="function",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 30,
                        language="go",
                    )
                    symbols.append(symbol)
                    self.symbol_graph.add_symbol(
                        name=func_name,
                        type="function",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 30,
                    )

                # Type definitions (structs, interfaces)
                type_match = re.search(r"type\s+(\w+)\s+(?:struct|interface)", line)
                if type_match:
                    type_name = type_match.group(1)
                    symbol = SymbolNode(
                        name=type_name,
                        type="class",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 50,
                        language="go",
                    )
                    symbols.append(symbol)
                    self.symbol_graph.add_symbol(
                        name=type_name,
                        type="class",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 50,
                    )

                # Import statements
                import_match = re.search(r'import\s+(?:\(|")([^"\s()]+)', line)
                if import_match:
                    import_path = import_match.group(1)
                    imp_name = import_path.split("/")[-1]
                    symbol = SymbolNode(
                        name=imp_name,
                        type="import",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num,
                        metadata={"import_path": import_path},
                        language="go",
                    )
                    symbols.append(symbol)
                    self.symbol_graph.add_symbol(
                        name=imp_name,
                        type="import",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num,
                        metadata={"import_path": import_path},
                    )

        except Exception as e:
            logger.error(f"Error in Go parsing {file_path}: {e}")

        return symbols

    def _parse_java_file(self, file_path: Path) -> List[Any]:
        """Parse Java file and extract symbols."""

        symbols = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            import re

            for line_num, line in enumerate(lines, 1):
                # Class definitions
                class_match = re.search(r"(?:public\s+)?class\s+(\w+)", line)
                if class_match:
                    class_name = class_match.group(1)
                    symbol = SymbolNode(
                        name=class_name,
                        type="class",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 100,
                        language="java",
                    )
                    symbols.append(symbol)
                    self.symbol_graph.add_symbol(
                        name=class_name,
                        type="class",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num + 100,
                    )

                # Method definitions
                method_match = re.search(
                    r"(?:public|private|protected)?\s+(?:static\s+)?\w+\s+(\w+)\s*\(", line
                )
                if method_match and "class" not in line:
                    method_name = method_match.group(1)
                    if method_name not in ("if", "while", "for", "switch"):
                        symbol = SymbolNode(
                            name=method_name,
                            type="method",
                            file_path=str(file_path),
                            line_start=line_num,
                            line_end=line_num + 30,
                            language="java",
                        )
                        symbols.append(symbol)
                        self.symbol_graph.add_symbol(
                            name=method_name,
                            type="method",
                            file_path=str(file_path),
                            line_start=line_num,
                            line_end=line_num + 30,
                        )

                # Import statements
                import_match = re.search(r"import\s+([^;]+);", line)
                if import_match:
                    import_path = import_match.group(1)
                    imp_name = import_path.split(".")[-1]
                    symbol = SymbolNode(
                        name=imp_name,
                        type="import",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num,
                        metadata={"import_path": import_path},
                        language="java",
                    )
                    symbols.append(symbol)
                    self.symbol_graph.add_symbol(
                        name=imp_name,
                        type="import",
                        file_path=str(file_path),
                        line_start=line_num,
                        line_end=line_num,
                        metadata={"import_path": import_path},
                    )

        except Exception as e:
            logger.error(f"Error in Java parsing {file_path}: {e}")

        return symbols

    def _get_tree_sitter_tree(self, content: str, language: str) -> Optional[Any]:
        """Get Tree-sitter AST for content."""
        try:
            import tree_sitter
            from tree_sitter import Language, Parser

            parser = self._get_or_create_parser(language)
            if parser is None:
                return None

            tree = parser.parse(bytes(content, "utf-8"))
            return tree

        except ImportError:
            logger.debug("Tree-sitter not available")
            return None
        except Exception as e:
            logger.debug(f"Tree-sitter parsing failed: {e}")
            return None

    def _get_or_create_parser(self, language: str) -> Optional[Any]:
        """Get or create Tree-sitter parser for language."""
        if language in self._parser_cache:
            return self._parser_cache[language]

        try:
            from tree_sitter import Language, Parser

            # Load language module
            if language == "python":
                import tree_sitter_python

                lang = Language(tree_sitter_python.language())
            elif language == "javascript":
                import tree_sitter_javascript

                lang = Language(tree_sitter_javascript.language())
            elif language == "typescript":
                import tree_sitter_typescript

                lang = Language(tree_sitter_typescript.language_tsx())
            elif language == "rust":
                import tree_sitter_rust

                lang = Language(tree_sitter_rust.language())
            elif language == "go":
                import tree_sitter_go

                lang = Language(tree_sitter_go.language())
            elif language == "java":
                import tree_sitter_java

                lang = Language(tree_sitter_java.language())
            else:
                return None

            parser = Parser(lang)
            self._parser_cache[language] = parser
            return parser

        except ImportError:
            return None
        except Exception as e:
            logger.error(f"Failed to create parser for {language}: {e}")
            return None

    def _extract_python_symbols(
        self, tree: Any, file_path: str, lines: List[str]
    ) -> List[Any]:
        """Extract Python symbols from Tree-sitter AST."""

        symbols = []
        root = tree.root_node

        def walk(node: Any) -> None:
            if node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = name_node.text.decode("utf-8")
                    params_node = node.child_by_field_name("parameters")
                    params = []
                    if params_node:
                        for child in params_node.children:
                            if child.type == "identifier":
                                params.append(child.text.decode("utf-8"))

                    symbol = SymbolNode(
                        name=name,
                        type="function",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        language="python",
                        metadata={"parameters": params},
                    )
                    symbols.append(symbol)
                    self.symbol_graph.add_symbol(
                        name=name,
                        type="function",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        metadata={"parameters": params},
                    )

            elif node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = name_node.text.decode("utf-8")
                    symbol = SymbolNode(
                        name=name,
                        type="class",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        language="python",
                    )
                    symbols.append(symbol)
                    self.symbol_graph.add_symbol(
                        name=name,
                        type="class",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                    )

            elif node.type == "import_statement":
                for child in node.children:
                    if child.type == "dotted_name":
                        name = child.text.decode("utf-8")
                        symbol = SymbolNode(
                            name=name.split(".")[-1],
                            type="import",
                            file_path=file_path,
                            line_start=node.start_point[0] + 1,
                            line_end=node.end_point[0] + 1,
                            language="python",
                            metadata={"import_path": name},
                        )
                        symbols.append(symbol)
                        self.symbol_graph.add_symbol(
                            name=name.split(".")[-1],
                            type="import",
                            file_path=file_path,
                            line_start=node.start_point[0] + 1,
                            line_end=node.end_point[0] + 1,
                            metadata={"import_path": name},
                        )

            # Recurse
            for child in node.children:
                walk(child)

        walk(root)
        return symbols

    def _extract_javascript_symbols(
        self, tree: Any, file_path: str, lines: List[str]
    ) -> List[Any]:
        """Extract JavaScript/TypeScript symbols from Tree-sitter AST."""

        symbols = []
        root = tree.root_node

        def walk(node: Any) -> None:
            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = name_node.text.decode("utf-8")
                    symbol = SymbolNode(
                        name=name,
                        type="function",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        language="javascript",
                    )
                    symbols.append(symbol)
                    self.symbol_graph.add_symbol(
                        name=name,
                        type="function",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                    )

            elif node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = name_node.text.decode("utf-8")
                    symbol = SymbolNode(
                        name=name,
                        type="class",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        language="javascript",
                    )
                    symbols.append(symbol)
                    self.symbol_graph.add_symbol(
                        name=name,
                        type="class",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                    )

            for child in node.children:
                walk(child)

        walk(root)
        return symbols

    def _extract_rust_symbols(
        self, tree: Any, file_path: str, lines: List[str]
    ) -> List[Any]:
        """Extract Rust symbols from Tree-sitter AST."""

        symbols = []
        root = tree.root_node

        def walk(node: Any) -> None:
            if node.type == "function_item":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = name_node.text.decode("utf-8")
                    symbol = SymbolNode(
                        name=name,
                        type="function",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        language="rust",
                    )
                    symbols.append(symbol)
                    self.symbol_graph.add_symbol(
                        name=name,
                        type="function",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                    )

            elif node.type == "struct_item":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = name_node.text.decode("utf-8")
                    symbol = SymbolNode(
                        name=name,
                        type="struct",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        language="rust",
                    )
                    symbols.append(symbol)
                    self.symbol_graph.add_symbol(
                        name=name,
                        type="struct",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                    )

            for child in node.children:
                walk(child)

        walk(root)
        return symbols

    def _find_block_end(
        self, lines: List[str], start_idx: int, base_indent: int
    ) -> int:
        """Find the end of a code block based on indentation."""
        end_line = start_idx + 1

        for i in range(start_idx + 1, min(start_idx + 100, len(lines))):
            line = lines[i]
            stripped = line.lstrip()
            if not stripped or stripped.startswith("#"):
                continue

            current_indent = len(line) - len(stripped)
            if current_indent <= base_indent and stripped:
                break
            end_line = i + 1

        return end_line

    def _find_entry_points(self) -> List[str]:
        """Find potential entry points in the repository."""
        entry_points = []

        for language, patterns in ENTRY_POINT_PATTERNS.items():
            for pattern in patterns:
                for file_path in self.repo_path.rglob(pattern):
                    if not self._should_ignore(file_path):
                        entry_points.append(str(file_path))

        return entry_points

    def _read_project_dependencies(self) -> Dict[str, List[str]]:
        """Read project dependencies from package files."""
        dependencies = {}

        # Python: requirements.txt, pyproject.toml, setup.py
        requirements_file = self.repo_path / "requirements.txt"
        if requirements_file.exists():
            try:
                with open(requirements_file, "r", encoding="utf-8") as f:
                    deps = []
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            # Extract package name (ignore version specifiers)
                            pkg_name = line.split("==")[0].split(">=")[0].split("<")[0].strip()
                            if pkg_name:
                                deps.append(pkg_name)
                    dependencies["python"] = deps
            except Exception as e:
                logger.warning(f"Failed to read requirements.txt: {e}")

        # JavaScript/Node.js: package.json
        package_json = self.repo_path / "package.json"
        if package_json.exists():
            try:
                import json

                with open(package_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    deps = []
                    for dep_type in ["dependencies", "devDependencies", "peerDependencies"]:
                        if dep_type in data:
                            deps.extend(list(data[dep_type].keys()))
                    dependencies["javascript"] = deps
            except Exception as e:
                logger.warning(f"Failed to read package.json: {e}")

        # Rust: Cargo.toml
        cargo_toml = self.repo_path / "Cargo.toml"
        if cargo_toml.exists():
            try:
                import re

                with open(cargo_toml, "r", encoding="utf-8") as f:
                    content = f.read()
                    deps = []
                    # Simple regex to extract dependencies
                    for match in re.finditer(r'^(\w[\w-]*)\s*=', content, re.MULTILINE):
                        dep_name = match.group(1)
                        if dep_name not in ("dependencies", "dev-dependencies", "build-dependencies"):
                            deps.append(dep_name)
                    dependencies["rust"] = deps
            except Exception as e:
                logger.warning(f"Failed to read Cargo.toml: {e}")

        return dependencies

    def _should_ignore(self, file_path: Path) -> bool:
        """Check if file should be ignored (hidden, in .git, etc.)."""
        return self.ignore_manager.should_ignore(file_path)

    def _extract_import_edges(self) -> None:
        """Extract IMPORTS edges between symbols."""

        for file_path, symbol_ids in self.symbol_graph._file_to_symbols.items():
            for symbol_id in symbol_ids:
                symbol = self.symbol_graph.get_symbol(symbol_id.split(":")[-1])
                if symbol and symbol.type == "import":
                    from_module = symbol.metadata.get("from_module", "")
                    if from_module:
                        # Try to find the imported symbol
                        for other_file, other_ids in self.symbol_graph._file_to_symbols.items():
                            for other_id in other_ids:
                                other_symbol = self.symbol_graph.get_symbol(other_id.split(":")[-1])
                                if other_symbol and other_symbol.name == symbol.name:
                                    self.symbol_graph.add_edge(
                                        from_symbol=symbol.name,
                                        to_symbol=other_symbol.name,
                                        edge_type=EDGE_TYPE_IMPORTS,
                                        metadata={"from_module": from_module},
                                    )

    def _extract_call_edges(self) -> None:
        """Extract CALLS edges between symbols (simplified)."""
        # This would require deeper AST analysis to find function calls
        # For now, we'll skip this and rely on Tree-sitter queries in parse methods
        pass

    def _extract_inheritance_edges(self) -> None:
        """Extract EXTENDS and IMPLEMENTS edges."""
        # This would require parsing class inheritance from AST
        # For now, we'll skip this and rely on Tree-sitter queries in parse methods
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Get repository mapping statistics."""
        return {
            "repo_path": str(self.repo_path),
            "languages": list(self.languages),
            "symbol_count": len(self.symbol_graph),
            "edge_count": self.symbol_graph._graph.number_of_edges(),
            "file_count": self.symbol_graph.get_file_count(),
            "graph_stats": self.symbol_graph.get_stats(),
        }

    def scan_changed_files(self) -> List[str]:
        """
        Returns list of changed files since last commit (via git).

        Returns:
            List of changed file paths relative to repo root
        """
        import subprocess

        try:
            # Check if git repository
            git_dir = self.repo_path / ".git"
            if not git_dir.exists():
                logger.debug("Not a git repository, skipping change detection")
                return []

            # Get changed files from last commit
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            changed_files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
            logger.debug(f"Detected {len(changed_files)} changed file(s) via git")
            return changed_files

        except subprocess.CalledProcessError as e:
            logger.debug(f"Git diff failed: {e.stderr.strip() if e.stderr else str(e)}")
            return []
        except Exception as e:
            logger.debug(f"Change detection failed: {e}")
            return []

    def invalidate_cache(self) -> None:
        """
        Invalidate and remove cached symbol graph.

        Forces full rebuild on next build_graph() call.
        """
        if self.symbol_graph.persist_path:
            try:
                pickle_path = (
                    self.symbol_graph.persist_path.with_suffix(".pkl")
                    if self.symbol_graph.persist_path.suffix != ".pkl"
                    else self.symbol_graph.persist_path
                )
                json_path = self.symbol_graph.persist_path.with_suffix(".json")

                if pickle_path.exists():
                    pickle_path.unlink()
                    logger.info(f"Cache invalidated: {pickle_path}")

                if json_path.exists():
                    json_path.unlink()
                    logger.info(f"Cache invalidated: {json_path}")

            except Exception as e:
                logger.warning(f"Failed to invalidate cache: {e}")

    def clear(self) -> None:
        """Clear the symbol graph."""
        self.symbol_graph.clear()
        self.languages.clear()
        self._parsers.clear()
        self._parser_cache.clear()
        logger.debug("RepositoryMapper cleared")
