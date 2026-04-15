"""
Tree-sitter Parser Manager für GlitchHunter.

Zentrale Verwaltung von Tree-sitter Parsern mit:
- Caching für wiederholte Analysen
- Error-Handling für Parser-Fehler
- Multi-Language Support (Python, JS/TS, Rust, Go, Java, C/C++)
- Performance-Optimierung

Usage:
    parser_manager = TreeSitterParserManager()
    ast = parser_manager.parse(code, "python")
    symbols = parser_manager.extract_symbols(ast, "python")
"""

import logging
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
import functools

logger = logging.getLogger(__name__)


@dataclass
class ParserStats:
    """
    Statistik über Parser-Nutzung.

    Attributes:
        total_parses: Gesamtanzahl Parses
        cache_hits: Cache-Treffer
        cache_misses: Cache-Fehler
        parse_errors: Parse-Fehler
        avg_parse_time_ms: Durchschnittliche Parse-Zeit
    """

    total_parses: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    parse_errors: int = 0
    total_parse_time_ms: float = 0.0

    @property
    def avg_parse_time_ms(self) -> float:
        """Durchschnittliche Parse-Zeit."""
        if self.total_parses == 0:
            return 0.0
        return self.total_parse_time_ms / self.total_parses

    @property
    def cache_hit_rate(self) -> float:
        """Cache-Trefferquote."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "total_parses": self.total_parses,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "parse_errors": self.parse_errors,
            "avg_parse_time_ms": round(self.avg_parse_time_ms, 2),
            "cache_hit_rate": round(self.cache_hit_rate, 2),
        }


@dataclass
class ParseError:
    """
    Parser-Fehlerinformation.

    Attributes:
        file_path: Dateipfad
        language: Sprache
        error_message: Fehlermeldung
        line_number: Zeilennummer
        column_number: Spaltennummer
        error_type: Fehlertyp (syntax, encoding, unsupported)
    """

    file_path: str
    language: str
    error_message: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    error_type: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "file_path": self.file_path,
            "language": self.language,
            "error_message": self.error_message,
            "line_number": self.line_number,
            "column_number": self.column_number,
            "error_type": self.error_type,
        }


@dataclass
class ParseResult:
    """
    Ergebnis eines Parse-Vorgangs.

    Attributes:
        success: True wenn erfolgreich
        tree: Tree-sitter AST
        symbols: Extrahierte Symbole
        errors: Parser-Fehler
        warnings: Warnungen
        parse_time_ms: Parse-Zeit
        cache_hit: True wenn Cache-Treffer
    """

    success: bool = False
    tree: Optional[Any] = None
    symbols: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[ParseError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    parse_time_ms: float = 0.0
    cache_hit: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "success": self.success,
            "symbols_count": len(self.symbols),
            "errors_count": len(self.errors),
            "warnings_count": len(self.warnings),
            "parse_time_ms": round(self.parse_time_ms, 2),
            "cache_hit": self.cache_hit,
            "errors": [e.to_dict() for e in self.errors],
        }


class TreeSitterParserManager:
    """
    Zentraler Parser-Manager für Tree-sitter.

    Features:
    - Caching für wiederholte Analysen
    - Error-Handling für Parser-Fehler
    - Multi-Language Support
    - Performance-Statistiken

    Usage:
        manager = TreeSitterParserManager()
        result = manager.parse_file("src/code.py")
    """

    # Unterstützte Sprachen
    SUPPORTED_LANGUAGES = {
        "python": {
            "extensions": [".py", ".pyw"],
            "module": "tree_sitter_python",
        },
        "javascript": {
            "extensions": [".js", ".jsx", ".mjs"],
            "module": "tree_sitter_javascript",
        },
        "typescript": {
            "extensions": [".ts", ".tsx"],
            "module": "tree_sitter_typescript",
        },
        "rust": {
            "extensions": [".rs"],
            "module": "tree_sitter_rust",
        },
        "go": {
            "extensions": [".go"],
            "module": "tree_sitter_go",
        },
        "java": {
            "extensions": [".java"],
            "module": "tree_sitter_java",
        },
        "cpp": {
            "extensions": [".cpp", ".cc", ".cxx", ".h", ".hpp"],
            "module": "tree_sitter_cpp",
        },
        "c": {
            "extensions": [".c", ".h"],
            "module": "tree_sitter_c",
        },
    }

    def __init__(
        self,
        cache_size: int = 1000,
        enable_cache: bool = True,
    ) -> None:
        """
        Initialisiert Parser-Manager.

        Args:
            cache_size: Maximale Cache-Größe.
            enable_cache: Cache aktivieren.
        """
        self.cache_size = cache_size
        self.enable_cache = enable_cache

        # Parser-Cache
        self._parsers: Dict[str, Any] = {}
        self._languages: Dict[str, Any] = {}

        # AST-Cache (Content-Hash → AST)
        self._ast_cache: Dict[str, Tuple[Any, datetime]] = {}

        # Symbol-Cache (Content-Hash → Symbole)
        self._symbol_cache: Dict[str, Tuple[List[Dict], datetime]] = {}

        # Statistiken
        self.stats = ParserStats()

        # Fehler-Log
        self._error_log: List[ParseError] = []

        logger.debug(
            f"TreeSitterParserManager initialisiert: cache_size={cache_size}, "
            f"enable_cache={enable_cache}"
        )

    def parse_file(
        self,
        file_path: str,
        language: Optional[str] = None,
    ) -> ParseResult:
        """
        Parst Datei mit Tree-sitter.

        Args:
            file_path: Dateipfad.
            language: Optional Sprache (wird sonst erkannt).

        Returns:
            ParseResult.
        """
        import time
        start_time = time.time()

        self.stats.total_parses += 1

        try:
            # Datei lesen
            path = Path(file_path)
            if not path.exists():
                return ParseResult(
                    success=False,
                    errors=[ParseError(
                        file_path=file_path,
                        language=language or "unknown",
                        error_message=f"File not found: {file_path}",
                        error_type="file_not_found",
                    )],
                )

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Sprache erkennen
            if not language:
                language = self._detect_language(file_path)

            # Cache-Check
            if self.enable_cache:
                content_hash = self._hash_content(content)
                if content_hash in self._ast_cache:
                    self.stats.cache_hits += 1
                    cached_ast, _ = self._ast_cache[content_hash]
                    return ParseResult(
                        success=True,
                        tree=cached_ast,
                        parse_time_ms=(time.time() - start_time) * 1000,
                        cache_hit=True,
                    )
                else:
                    self.stats.cache_misses += 1

            # Parsen
            tree = self._parse_content(content, language)

            if tree is None:
                self.stats.parse_errors += 1
                return ParseResult(
                    success=False,
                    errors=[ParseError(
                        file_path=file_path,
                        language=language,
                        error_message="Failed to parse file",
                        error_type="parse_error",
                    )],
                )

            # Cache speichern
            if self.enable_cache:
                self._store_in_cache(content_hash, tree)

            parse_time_ms = (time.time() - start_time) * 1000
            self.stats.total_parse_time_ms += parse_time_ms

            return ParseResult(
                success=True,
                tree=tree,
                parse_time_ms=parse_time_ms,
            )

        except UnicodeDecodeError as e:
            self.stats.parse_errors += 1
            error = ParseError(
                file_path=file_path,
                language=language or "unknown",
                error_message=f"Encoding error: {e}",
                error_type="encoding",
            )
            self._error_log.append(error)
            return ParseResult(success=False, errors=[error])

        except Exception as e:
            self.stats.parse_errors += 1
            error = ParseError(
                file_path=file_path,
                language=language or "unknown",
                error_message=f"Parse error: {e}",
                error_type="unknown",
            )
            self._error_log.append(error)
            logger.error(f"Parse error for {file_path}: {e}")
            return ParseResult(success=False, errors=[error])

    def parse_content(
        self,
        content: str,
        language: str,
    ) -> ParseResult:
        """
        Parst Content mit Tree-sitter.

        Args:
            content: Code-Content.
            language: Sprache.

        Returns:
            ParseResult.
        """
        import time
        start_time = time.time()

        self.stats.total_parses += 1

        try:
            # Cache-Check
            if self.enable_cache:
                content_hash = self._hash_content(content)
                if content_hash in self._ast_cache:
                    self.stats.cache_hits += 1
                    cached_ast, _ = self._ast_cache[content_hash]
                    return ParseResult(
                        success=True,
                        tree=cached_ast,
                        parse_time_ms=(time.time() - start_time) * 1000,
                        cache_hit=True,
                    )
                else:
                    self.stats.cache_misses += 1

            # Parsen
            tree = self._parse_content(content, language)

            if tree is None:
                self.stats.parse_errors += 1
                return ParseResult(
                    success=False,
                    errors=[ParseError(
                        file_path="<content>",
                        language=language,
                        error_message="Failed to parse content",
                        error_type="parse_error",
                    )],
                )

            # Cache speichern
            if self.enable_cache:
                self._store_in_cache(self._hash_content(content), tree)

            parse_time_ms = (time.time() - start_time) * 1000
            self.stats.total_parse_time_ms += parse_time_ms

            return ParseResult(
                success=True,
                tree=tree,
                parse_time_ms=parse_time_ms,
            )

        except Exception as e:
            self.stats.parse_errors += 1
            error = ParseError(
                file_path="<content>",
                language=language,
                error_message=str(e),
                error_type="unknown",
            )
            self._error_log.append(error)
            return ParseResult(success=False, errors=[error])

    def extract_symbols(
        self,
        tree: Any,
        language: str,
        file_path: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Extrahiert Symbole aus AST.

        Args:
            tree: Tree-sitter AST.
            language: Sprache.
            file_path: Dateipfad.

        Returns:
            Liste von Symbolen.
        """
        # Cache-Check
        if self.enable_cache:
            # Einfacher Cache-Key aus tree und language
            cache_key = f"{language}_{id(tree)}"
            if cache_key in self._symbol_cache:
                symbols, _ = self._symbol_cache[cache_key]
                return symbols

        # Sprache-spezifische Extraktion
        if language == "python":
            symbols = self._extract_python_symbols(tree, file_path)
        elif language in ("javascript", "typescript"):
            symbols = self._extract_javascript_symbols(tree, file_path)
        elif language == "rust":
            symbols = self._extract_rust_symbols(tree, file_path)
        elif language == "go":
            symbols = self._extract_go_symbols(tree, file_path)
        elif language == "java":
            symbols = self._extract_java_symbols(tree, file_path)
        elif language in ("cpp", "c"):
            symbols = self._extract_cpp_symbols(tree, file_path)
        else:
            symbols = self._extract_generic_symbols(tree, file_path, language)

        # Cache speichern
        if self.enable_cache and symbols:
            cache_key = f"{language}_{id(tree)}"
            self._symbol_cache[cache_key] = (symbols, datetime.now())

            # Cache-Größe begrenzen
            if len(self._symbol_cache) > self.cache_size:
                # Älteste Einträge entfernen
                oldest_key = min(
                    self._symbol_cache.keys(),
                    key=lambda k: self._symbol_cache[k][1],
                )
                del self._symbol_cache[oldest_key]

        return symbols

    def _parse_content(self, content: str, language: str) -> Optional[Any]:
        """
        Parst Content mit Tree-sitter.

        Args:
            content: Code-Content.
            language: Sprache.

        Returns:
            Tree-sitter AST oder None.
        """
        try:
            parser = self._get_or_create_parser(language)
            if parser is None:
                logger.warning(f"No parser available for {language}")
                return None

            tree = parser.parse(bytes(content, "utf-8"))
            return tree

        except Exception as e:
            logger.error(f"Parse error for {language}: {e}")
            return None

    def _get_or_create_parser(self, language: str) -> Optional[Any]:
        """
        Holt oder erstellt Parser für Sprache.

        Args:
            language: Sprache.

        Returns:
            Parser oder None.
        """
        if language in self._parsers:
            return self._parsers[language]

        try:
            from tree_sitter import Language, Parser

            # Sprachmodul laden
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
            elif language == "cpp":
                import tree_sitter_cpp
                lang = Language(tree_sitter_cpp.language())
            elif language == "c":
                import tree_sitter_c
                lang = Language(tree_sitter_c.language())
            else:
                logger.warning(f"Unsupported language: {language}")
                return None

            parser = Parser(lang)

            self._languages[language] = lang
            self._parsers[language] = parser

            return parser

        except ImportError as e:
            logger.warning(f"Tree-sitter module for {language} not installed: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create parser for {language}: {e}")
            return None

    def _detect_language(self, file_path: str) -> str:
        """
        Erkennt Sprache aus Dateierweiterung.

        Args:
            file_path: Dateipfad.

        Returns:
            Sprache.
        """
        path = Path(file_path)
        extension = path.suffix.lower()

        for language, config in self.SUPPORTED_LANGUAGES.items():
            if extension in config["extensions"]:
                return language

        # Default zu Python
        return "python"

    def _hash_content(self, content: str) -> str:
        """
        Erstellt Hash für Content.

        Args:
            content: Code-Content.

        Returns:
            Content-Hash.
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _store_in_cache(self, content_hash: str, tree: Any) -> None:
        """
        Speichert AST im Cache.

        Args:
            content_hash: Content-Hash.
            tree: Tree-sitter AST.
        """
        self._ast_cache[content_hash] = (tree, datetime.now())

        # Cache-Größe begrenzen
        if len(self._ast_cache) > self.cache_size:
            # Älteste Einträge entfernen
            oldest_key = min(
                self._ast_cache.keys(),
                key=lambda k: self._ast_cache[k][1],
            )
            del self._ast_cache[oldest_key]

    def _extract_python_symbols(
        self,
        tree: Any,
        file_path: str,
    ) -> List[Dict[str, Any]]:
        """Extrahiert Python-Symbole."""
        symbols = []
        root = tree.root_node

        def walk(node: Any) -> None:
            if node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = name_node.text.decode("utf-8")
                    symbols.append({
                        "name": name,
                        "kind": "function",
                        "file_path": file_path,
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                    })

            elif node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = name_node.text.decode("utf-8")
                    symbols.append({
                        "name": name,
                        "kind": "class",
                        "file_path": file_path,
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                    })

            # Kinder durchlaufen
            for child in node.children:
                walk(child)

        walk(root)
        return symbols

    def _extract_javascript_symbols(
        self,
        tree: Any,
        file_path: str,
    ) -> List[Dict[str, Any]]:
        """Extrahiert JavaScript/TypeScript-Symbole."""
        symbols = []
        root = tree.root_node

        def walk(node: Any) -> None:
            if node.type in ("function_declaration", "method_definition"):
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = name_node.text.decode("utf-8")
                    symbols.append({
                        "name": name,
                        "kind": "function",
                        "file_path": file_path,
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                    })

            elif node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = name_node.text.decode("utf-8")
                    symbols.append({
                        "name": name,
                        "kind": "class",
                        "file_path": file_path,
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                    })

            for child in node.children:
                walk(child)

        walk(root)
        return symbols

    def _extract_rust_symbols(
        self,
        tree: Any,
        file_path: str,
    ) -> List[Dict[str, Any]]:
        """Extrahiert Rust-Symbole."""
        symbols = []
        root = tree.root_node

        def walk(node: Any) -> None:
            if node.type == "function_item":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = name_node.text.decode("utf-8")
                    symbols.append({
                        "name": name,
                        "kind": "function",
                        "file_path": file_path,
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                    })

            elif node.type == "struct_item":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = name_node.text.decode("utf-8")
                    symbols.append({
                        "name": name,
                        "kind": "struct",
                        "file_path": file_path,
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                    })

            elif node.type == "impl_item":
                # impl Blöcke für Traits/Methods
                symbols.append({
                    "name": "impl",
                    "kind": "impl",
                    "file_path": file_path,
                    "line_start": node.start_point[0] + 1,
                    "line_end": node.end_point[0] + 1,
                })

            for child in node.children:
                walk(child)

        walk(root)
        return symbols

    def _extract_go_symbols(
        self,
        tree: Any,
        file_path: str,
    ) -> List[Dict[str, Any]]:
        """Extrahiert Go-Symbole."""
        symbols = []
        root = tree.root_node

        def walk(node: Any) -> None:
            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = name_node.text.decode("utf-8")
                    symbols.append({
                        "name": name,
                        "kind": "function",
                        "file_path": file_path,
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                    })

            elif node.type == "type_declaration":
                # Type definitions
                for child in node.children:
                    if child.type == "type_spec":
                        name_node = child.child_by_field_name("name")
                        if name_node:
                            name = name_node.text.decode("utf-8")
                            symbols.append({
                                "name": name,
                                "kind": "type",
                                "file_path": file_path,
                                "line_start": child.start_point[0] + 1,
                                "line_end": child.end_point[0] + 1,
                            })

            for child in node.children:
                walk(child)

        walk(root)
        return symbols

    def _extract_java_symbols(
        self,
        tree: Any,
        file_path: str,
    ) -> List[Dict[str, Any]]:
        """Extrahiert Java-Symbole."""
        symbols = []
        root = tree.root_node

        def walk(node: Any) -> None:
            if node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = name_node.text.decode("utf-8")
                    symbols.append({
                        "name": name,
                        "kind": "class",
                        "file_path": file_path,
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                    })

            elif node.type == "method_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = name_node.text.decode("utf-8")
                    symbols.append({
                        "name": name,
                        "kind": "method",
                        "file_path": file_path,
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                    })

            for child in node.children:
                walk(child)

        walk(root)
        return symbols

    def _extract_cpp_symbols(
        self,
        tree: Any,
        file_path: str,
    ) -> List[Dict[str, Any]]:
        """Extrahiert C/C++-Symbole."""
        symbols = []
        root = tree.root_node

        def walk(node: Any) -> None:
            if node.type == "function_definition":
                name_node = node.child_by_field_name("declarator")
                if name_node:
                    name = name_node.text.decode("utf-8")
                    symbols.append({
                        "name": name,
                        "kind": "function",
                        "file_path": file_path,
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                    })

            elif node.type == "class_specifier":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = name_node.text.decode("utf-8")
                    symbols.append({
                        "name": name,
                        "kind": "class",
                        "file_path": file_path,
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                    })

            for child in node.children:
                walk(child)

        walk(root)
        return symbols

    def _extract_generic_symbols(
        self,
        tree: Any,
        file_path: str,
        language: str,
    ) -> List[Dict[str, Any]]:
        """
        Generische Symbol-Extraktion als Fallback.

        Args:
            tree: AST.
            file_path: Dateipfad.
            language: Sprache.

        Returns:
            Liste von Symbolen.
        """
        # Einfache Heuristik für unbekannte Sprachen
        symbols = []
        root = tree.root_node

        def walk(node: Any) -> None:
            # Nach Definitionen suchen (language-spezifisch)
            if "definition" in node.type or "declaration" in node.type:
                # Name finden
                for child in node.children:
                    if child.type == "identifier" or child.type == "name":
                        name = child.text.decode("utf-8")
                        symbols.append({
                            "name": name,
                            "kind": node.type,
                            "file_path": file_path,
                            "line_start": node.start_point[0] + 1,
                            "line_end": node.end_point[0] + 1,
                        })
                        break

            for child in node.children:
                walk(child)

        walk(root)
        return symbols

    def clear_cache(self) -> None:
        """Leert alle Caches."""
        self._ast_cache.clear()
        self._symbol_cache.clear()
        logger.info("Parser caches cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Holt Parser-Statistiken.

        Returns:
            Statistiken als Dict.
        """
        return {
            "stats": self.stats.to_dict(),
            "cache_size": len(self._ast_cache),
            "symbol_cache_size": len(self._symbol_cache),
            "error_log_size": len(self._error_log),
            "supported_languages": list(self.SUPPORTED_LANGUAGES.keys()),
        }

    def get_error_log(self) -> List[ParseError]:
        """
        Holt Fehler-Log.

        Returns:
            Liste von ParseError.
        """
        return self._error_log.copy()


# Singleton-Instanz für globalen Zugriff
_parser_manager: Optional[TreeSitterParserManager] = None


def get_parser_manager() -> TreeSitterParserManager:
    """
    Holt globale Parser-Manager-Instanz.

    Returns:
        TreeSitterParserManager.
    """
    global _parser_manager
    if _parser_manager is None:
        _parser_manager = TreeSitterParserManager()
    return _parser_manager


def parse_file(file_path: str, language: Optional[str] = None) -> ParseResult:
    """
    Parst Datei mit globalem Parser-Manager.

    Args:
        file_path: Dateipfad.
        language: Optional Sprache.

    Returns:
        ParseResult.
    """
    return get_parser_manager().parse_file(file_path, language)


def parse_content(content: str, language: str) -> ParseResult:
    """
    Parst Content mit globalem Parser-Manager.

    Args:
        content: Code-Content.
        language: Sprache.

    Returns:
        ParseResult.
    """
    return get_parser_manager().parse_content(content, language)
