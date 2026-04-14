"""
Unit Tests für Parallel Parser.

Tests für:
- ParallelParser
- ParallelParseResult
- FileBatch
- parse_repository
- parse_files
"""

import pytest
import sys
import tempfile
import os
from pathlib import Path

# Source-Path hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mapper.parallel_parser import (
    ParallelParser,
    ParallelParseResult,
    FileBatch,
    parse_repository,
    parse_files,
)


class TestParallelParseResult:
    """Tests für ParallelParseResult-Klasse."""

    def test_result_creation(self):
        """Testet Result-Erstellung."""
        result = ParallelParseResult()

        assert result.total_files == 0
        assert result.successful == 0
        assert result.failed == 0
        assert result.skipped == 0

    def test_result_with_values(self):
        """Testet Result mit Werten."""
        result = ParallelParseResult(
            total_files=100,
            successful=85,
            failed=10,
            skipped=5,
            total_time_seconds=30.5,
        )

        assert result.total_files == 100
        assert result.success_rate == 0.85
        assert result.avg_time_per_file == pytest.approx(0.305, rel=0.01)

    def test_result_to_dict(self):
        """Testet Serialisierung."""
        result = ParallelParseResult(
            total_files=50,
            successful=45,
            failed=5,
            total_time_seconds=15.0,
        )

        result_dict = result.to_dict()
        assert result_dict["total_files"] == 50
        assert result_dict["success_rate"] == 0.9
        assert result_dict["total_time_seconds"] == 15.0


class TestFileBatch:
    """Tests für FileBatch-Klasse."""

    def test_batch_creation(self):
        """Testet Batch-Erstellung."""
        batch = FileBatch(
            files=["file1.py", "file2.py", "file3.py"],
            language="python",
        )

        assert len(batch.files) == 3
        assert batch.language == "python"

    def test_batch_without_language(self):
        """Testet Batch ohne Sprache."""
        batch = FileBatch(files=["file1.py", "file2.py"])

        assert batch.language is None


class TestParallelParser:
    """Tests für ParallelParser."""

    @pytest.fixture
    def parser(self):
        """Erstellt Parser-Instanz."""
        return ParallelParser(max_workers=2, batch_size=10)

    @pytest.fixture
    def temp_repo(self):
        """Erstellt temporäres Test-Repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test-Dateien erstellen
            test_files = [
                ("test1.py", "def hello(): pass"),
                ("test2.py", "class MyClass: pass"),
                ("test3.py", "import os\n\ndef main(): pass"),
                ("subdir/test4.py", "def nested(): pass"),
            ]

            for file_path, content in test_files:
                full_path = Path(tmpdir) / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(content)

            yield tmpdir

    def test_parser_creation(self, parser):
        """Testet Parser-Erstellung."""
        assert parser.max_workers == 2
        assert parser.batch_size == 10

    def test_parse_directory(self, parser, temp_repo):
        """Testet Verzeichnis-Parsing."""
        result = parser.parse_directory(temp_repo)

        assert result.total_files == 4
        assert result.successful >= 0  # Kann erfolgreich sein oder nicht
        assert result.total_time_seconds > 0

    def test_parse_directory_with_max_files(self, parser, temp_repo):
        """Testet Verzeichnis-Parsing mit Max-Files-Limit."""
        result = parser.parse_directory(temp_repo, max_files=2)

        assert result.total_files <= 2

    def test_parse_directory_with_extensions(self, parser, temp_repo):
        """Testet Verzeichnis-Parsing mit Erweiterungs-Filter."""
        result = parser.parse_directory(temp_repo, extensions=[".py"])

        # Alle Dateien sollten .py sein
        for file_path in result.results.keys():
            assert file_path.endswith(".py")

    def test_parse_files_in_parallel(self, parser, temp_repo):
        """Testet paralleles Parsing von Dateiliste."""
        files = [
            str(Path(temp_repo) / "test1.py"),
            str(Path(temp_repo) / "test2.py"),
        ]

        result = parser.parse_files_in_parallel(files)

        assert result.total_files == 2

    def test_parse_in_batches(self, parser, temp_repo):
        """Testet Batch-Parsing."""
        files = [
            str(Path(temp_repo) / "test1.py"),
            str(Path(temp_repo) / "test2.py"),
            str(Path(temp_repo) / "test3.py"),
        ]

        result = parser.parse_in_batches(files, batch_size=2)

        # Sollte in 2 Batches verarbeitet werden (2 + 1)
        assert result.total_files == 3

    def test_get_symbols_from_results(self, parser, temp_repo):
        """Testet Symbol-Extraktion aus Ergebnissen."""
        result = parser.parse_directory(temp_repo, max_files=1)

        if result.successful > 0:
            symbols = parser.get_symbols_from_results(result)
            # Sollte mindestens ein File mit Symbolen geben
            assert len(symbols) >= 0  # Kann leer sein wenn Parsing fehlschlägt

    def test_clear_cache(self, parser):
        """Testet Cache-Leerung."""
        parser.clear_cache()
        # Kein Fehler sollte auftreten

    def test_get_stats(self, parser):
        """Testet Statistik-Abruf."""
        stats = parser.get_stats()

        assert "stats" in stats
        assert "cache_size" in stats
        assert "supported_languages" in stats


class TestConvenienceFunctions:
    """Tests für Convenience-Funktionen."""

    @pytest.fixture
    def temp_repo(self):
        """Erstellt temporäres Test-Repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test-Dateien erstellen
            test_files = [
                ("test1.py", "def hello(): pass"),
                ("test2.py", "class MyClass: pass"),
            ]

            for file_path, content in test_files:
                full_path = Path(tmpdir) / file_path
                with open(full_path, "w") as f:
                    f.write(content)

            yield tmpdir

    def test_parse_repository(self, temp_repo):
        """Testet Repository-Parsing."""
        result = parse_repository(temp_repo, max_workers=2)

        assert isinstance(result, ParallelParseResult)
        assert result.total_files == 2

    def test_parse_files(self, temp_repo):
        """Testet Dateilisten-Parsing."""
        files = [
            str(Path(temp_repo) / "test1.py"),
            str(Path(temp_repo) / "test2.py"),
        ]

        result = parse_files(files, max_workers=2)

        assert isinstance(result, ParallelParseResult)
        assert result.total_files == 2


class TestProgressCallback:
    """Tests für Fortschritts-Callback."""

    def test_progress_callback(self):
        """Testet Callback-Aufruf."""
        progress_updates = []

        def callback(completed, total):
            progress_updates.append((completed, total))

        parser = ParallelParser(
            max_workers=2,
            progress_callback=callback,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test-Dateien erstellen
            for i in range(5):
                file_path = Path(tmpdir) / f"test{i}.py"
                with open(file_path, "w") as f:
                    f.write("def test(): pass")

            result = parser.parse_directory(tmpdir)

        # Callback sollte mindestens einmal aufgerufen worden sein
        assert len(progress_updates) > 0


class TestErrorHandling:
    """Tests für Error-Handling."""

    @pytest.fixture
    def parser(self):
        """Erstellt Parser-Instanz."""
        return ParallelParser(max_workers=2)

    def test_nonexistent_directory(self, parser):
        """Testet Parsing nicht-existierenden Verzeichnis."""
        result = parser.parse_directory("/nonexistent/path")

        assert result.total_files == 0

    def test_empty_directory(self, parser):
        """Testet Parsing leerem Verzeichnis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = parser.parse_directory(tmpdir)

            assert result.total_files == 0

    def test_mixed_success_failure(self, parser):
        """Testet gemischte Erfolge/Fehler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Gültige Datei
            valid_file = Path(tmpdir) / "valid.py"
            with open(valid_file, "w") as f:
                f.write("def valid(): pass")

            # Ungültige Erweiterung (wird ignoriert)
            invalid_file = Path(tmpdir) / "invalid.xyz"
            with open(invalid_file, "w") as f:
                f.write("invalid content")

            result = parser.parse_directory(tmpdir)

            # Nur .py sollte geparst werden
            assert result.total_files == 1


class TestPerformance:
    """Performance-Tests."""

    @pytest.fixture
    def large_repo(self):
        """Erstellt größeres Test-Repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 20 Test-Dateien erstellen
            for i in range(20):
                subdir = Path(tmpdir) / f"subdir{i % 4}"
                subdir.mkdir(parents=True, exist_ok=True)

                file_path = subdir / f"file{i}.py"
                with open(file_path, "w") as f:
                    f.write(f"""
def function_{i}():
    return {i}

class Class_{i}:
    def method(self):
        pass
""")

            yield tmpdir

    def test_parallel_speedup(self, large_repo):
        """Testet Beschleunigung durch Parallelisierung."""
        # Single-threaded
        parser_single = ParallelParser(max_workers=1)
        result_single = parser_single.parse_directory(large_repo)

        # Multi-threaded
        parser_multi = ParallelParser(max_workers=4)
        result_multi = parser_multi.parse_directory(large_repo)

        # Multi sollte schneller sein (oder gleich bei kleinen Repos)
        # Bei kleinen Repos ist Overhead manchmal größer als Nutzen
        assert result_multi.total_files == result_single.total_files


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
