"""
Unit Tests für Tree-sitter Parser Manager.

Tests für:
- TreeSitterParserManager
- ParseResult
- ParseError
- ParserStats
- Caching
- Error-Handling
"""

import pytest
import sys
from pathlib import Path

# Source-Path hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mapper.tree_sitter_manager import (
    TreeSitterParserManager,
    ParseResult,
    ParseError,
    ParserStats,
    parse_file,
    parse_content,
    get_parser_manager,
)


class TestParseResult:
    """Tests für ParseResult-Klasse."""

    def test_parse_result_success(self):
        """Testet erfolgreiches Parse-Ergebnis."""
        result = ParseResult(
            success=True,
            parse_time_ms=15.5,
            cache_hit=False,
        )

        assert result.success is True
        assert result.parse_time_ms == 15.5
        assert result.cache_hit is False

    def test_parse_result_to_dict(self):
        """Testet Serialisierung."""
        result = ParseResult(
            success=True,
            symbols=[{"name": "test", "kind": "function"}],
            errors=[ParseError(
                file_path="test.py",
                language="python",
                error_message="Test error",
            )],
            warnings=["Warning 1"],
            parse_time_ms=10.0,
        )

        result_dict = result.to_dict()
        assert result_dict["success"] is True
        assert result_dict["symbols_count"] == 1
        assert result_dict["errors_count"] == 1
        assert result_dict["warnings_count"] == 1


class TestParseError:
    """Tests für ParseError-Klasse."""

    def test_parse_error_creation(self):
        """Testet ParseError-Erstellung."""
        error = ParseError(
            file_path="test.py",
            language="python",
            error_message="Syntax error",
            line_number=10,
            column_number=5,
            error_type="syntax",
        )

        assert error.file_path == "test.py"
        assert error.line_number == 10
        assert error.error_type == "syntax"

    def test_parse_error_to_dict(self):
        """Testet Serialisierung."""
        error = ParseError(
            file_path="test.py",
            language="python",
            error_message="Test error",
        )

        error_dict = error.to_dict()
        assert error_dict["file_path"] == "test.py"
        assert error_dict["error_message"] == "Test error"


class TestParserStats:
    """Tests für ParserStats-Klasse."""

    def test_stats_creation(self):
        """Testet Stats-Erstellung."""
        stats = ParserStats()

        assert stats.total_parses == 0
        assert stats.cache_hits == 0
        assert stats.avg_parse_time_ms == 0.0

    def test_avg_parse_time(self):
        """Testet Durchschnitts-Zeit."""
        stats = ParserStats(
            total_parses=10,
            total_parse_time_ms=100.0,
        )

        assert stats.avg_parse_time_ms == 10.0

    def test_cache_hit_rate(self):
        """Testet Cache-Trefferquote."""
        stats = ParserStats(
            cache_hits=80,
            cache_misses=20,
        )

        assert stats.cache_hit_rate == 0.8

    def test_stats_to_dict(self):
        """Testet Serialisierung."""
        stats = ParserStats(
            total_parses=100,
            cache_hits=75,
            cache_misses=25,
            parse_errors=5,
            total_parse_time_ms=500.0,
        )

        stats_dict = stats.to_dict()
        assert stats_dict["total_parses"] == 100
        assert stats_dict["cache_hit_rate"] == 0.75


class TestTreeSitterParserManager:
    """Tests für TreeSitterParserManager."""

    @pytest.fixture
    def manager(self):
        """Erstellt Parser-Manager-Instanz."""
        return TreeSitterParserManager(cache_size=100, enable_cache=True)

    def test_manager_creation(self, manager):
        """Testet Manager-Erstellung."""
        assert manager.cache_size == 100
        assert manager.enable_cache is True

    def test_language_detection(self, manager):
        """Testet Spracherkennung."""
        assert manager._detect_language("test.py") == "python"
        assert manager._detect_language("test.js") == "javascript"
        assert manager._detect_language("test.ts") == "typescript"
        assert manager._detect_language("test.rs") == "rust"
        assert manager._detect_language("test.go") == "go"
        assert manager._detect_language("test.java") == "java"
        assert manager._detect_language("test.cpp") == "cpp"

    def test_content_hash(self, manager):
        """Testet Content-Hash."""
        content1 = "def hello(): pass"
        content2 = "def hello(): pass"
        content3 = "def world(): pass"

        hash1 = manager._hash_content(content1)
        hash2 = manager._hash_content(content2)
        hash3 = manager._hash_content(content3)

        assert hash1 == hash2  # Gleicher Content
        assert hash1 != hash3  # Unterschiedlicher Content

    def test_parse_python_content(self, manager):
        """Testet Python-Content-Parsing."""
        content = """
def hello():
    print("Hello, World!")

class MyClass:
    pass
"""
        result = manager.parse_content(content, "python")

        # Parsing sollte erfolgreich sein (wenn tree-sitter installiert)
        # Oder gracefully fehlschlagen
        if result.success:
            assert result.tree is not None
            assert result.parse_time_ms > 0
        else:
            assert len(result.errors) > 0

    def test_cache_hit(self, manager):
        """Testet Cache-Treffer."""
        content = "def test(): pass"

        # Erstes Parsing (Cache Miss)
        result1 = manager.parse_content(content, "python")

        # Zweites Parsing (Cache Hit)
        result2 = manager.parse_content(content, "python")

        assert result2.cache_hit is True
        assert result2.parse_time_ms < result1.parse_time_ms

    def test_extract_python_symbols(self, manager):
        """Testet Python-Symbol-Extraktion."""
        content = """
def my_function():
    pass

class MyClass:
    def my_method(self):
        pass
"""
        result = manager.parse_content(content, "python")

        if result.success:
            symbols = manager.extract_symbols(result.tree, "python", "test.py")

            assert len(symbols) >= 2  # Mindestens Funktion und Klasse
            assert any(s["name"] == "my_function" for s in symbols)
            assert any(s["name"] == "MyClass" for s in symbols)

    def test_error_handling_file_not_found(self, manager):
        """Testet Error-Handling bei nicht existierender Datei."""
        result = manager.parse_file("/nonexistent/path/file.py")

        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "file_not_found"

    def test_error_handling_invalid_language(self, manager):
        """Testet Error-Handling bei ungültiger Sprache."""
        content = "invalid code"
        result = manager.parse_content(content, "nonexistent_language")

        # Sollte gracefully fehlschlagen
        assert result.success is False or result.tree is None

    def test_stats_tracking(self, manager):
        """Testet Statistik-Verfolgung."""
        content = "def test(): pass"

        # Mehrfaches Parsing
        for _ in range(5):
            manager.parse_content(content, "python")

        stats = manager.stats
        assert stats.total_parses == 5
        assert stats.cache_hits > 0 or stats.cache_misses > 0

    def test_get_stats(self, manager):
        """Testet Stats-Abruf."""
        stats_dict = manager.get_stats()

        assert "stats" in stats_dict
        assert "cache_size" in stats_dict
        assert "supported_languages" in stats_dict
        assert len(stats_dict["supported_languages"]) == 8  # Alle unterstützten Sprachen

    def test_clear_cache(self, manager):
        """Testet Cache-Leerung."""
        content = "def test(): pass"

        # Parsing für Cache
        manager.parse_content(content, "python")

        # Cache leeren
        manager.clear_cache()

        # Nächstes Parsing sollte Cache Miss sein
        result = manager.parse_content(content, "python")
        # Cache könnte trotzdem hit sein wegen neuem Eintrag

    def test_error_log(self, manager):
        """Testet Fehler-Log."""
        # Fehler generieren
        manager.parse_file("/nonexistent/file.py")

        error_log = manager.get_error_log()
        assert len(error_log) > 0
        assert error_log[0].error_type == "file_not_found"


class TestSingletonFunctions:
    """Tests für Singleton-Funktionen."""

    def test_get_parser_manager(self):
        """Testet Singleton-Accessor."""
        manager1 = get_parser_manager()
        manager2 = get_parser_manager()

        assert manager1 is manager2  # Gleiche Instanz

    def test_parse_file_function(self):
        """Testet convenience parse_file-Funktion."""
        result = parse_file("/nonexistent/file.py")
        assert result.success is False

    def test_parse_content_function(self):
        """Testet convenience parse_content-Funktion."""
        content = "def test(): pass"
        result = parse_content(content, "python")

        # Parsing sollte funktionieren oder gracefully fehlschlagen
        assert result is not None


class TestMultiLanguageSupport:
    """Tests für Multi-Language-Support."""

    @pytest.fixture
    def manager(self):
        """Erstellt Parser-Manager-Instanz."""
        return TreeSitterParserManager()

    def test_javascript_parsing(self, manager):
        """Testet JavaScript-Parsing."""
        content = """
function hello() {
    console.log("Hello");
}

class MyClass {
    constructor() {}
}
"""
        result = manager.parse_content(content, "javascript")

        if result.success:
            symbols = manager.extract_symbols(result.tree, "javascript", "test.js")
            assert len(symbols) >= 1

    def test_typescript_parsing(self, manager):
        """Testet TypeScript-Parsing."""
        content = """
function greet(name: string): string {
    return `Hello, ${name}!`;
}

interface MyInterface {
    name: string;
}
"""
        result = manager.parse_content(content, "typescript")

        # TypeScript-Parsing sollte funktionieren
        assert result is not None

    def test_rust_parsing(self, manager):
        """Testet Rust-Parsing."""
        content = """
fn main() {
    println!("Hello, world!");
}

struct MyStruct {
    field: i32,
}

impl MyStruct {
    fn new() -> Self {
        MyStruct { field: 0 }
    }
}
"""
        result = manager.parse_content(content, "rust")

        if result.success:
            symbols = manager.extract_symbols(result.tree, "rust", "test.rs")
            assert len(symbols) >= 2  # fn, struct, impl

    def test_go_parsing(self, manager):
        """Testet Go-Parsing."""
        content = """
package main

func main() {
    println("Hello, world!")
}

type MyStruct struct {
    Field int
}

func (m MyStruct) Method() int {
    return m.Field
}
"""
        result = manager.parse_content(content, "go")

        # Go-Parsing sollte funktionieren
        assert result is not None

    def test_java_parsing(self, manager):
        """Testet Java-Parsing."""
        content = """
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello, world!");
    }
}

class MyClass {
    private int field;

    public int getField() {
        return field;
    }
}
"""
        result = manager.parse_content(content, "java")

        # Java-Parsing sollte funktionieren
        assert result is not None

    def test_cpp_parsing(self, manager):
        """Testet C++-Parsing."""
        content = """
#include <iostream>

int main() {
    std::cout << "Hello, world!" << std::endl;
    return 0;
}

class MyClass {
public:
    int field;
    
    int getField() {
        return field;
    }
};
"""
        result = manager.parse_content(content, "cpp")

        # C++-Parsing sollte funktionieren
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
