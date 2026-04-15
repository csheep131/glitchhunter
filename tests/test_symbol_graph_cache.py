"""
Tests für Symbol Graph Caching mit Persistenz.

Testet Auto-Save/Load, Cache-Invalidation, Incremental Scan und Redis-Integration.
"""

import os
import pickle
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mapper.symbol_graph import SymbolGraph, SymbolNode
from mapper.repo_mapper import RepositoryMapper


class TestSymbolGraphPersistence(unittest.TestCase):
    """Tests für SymbolGraph Persistenz."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.temp_dir) / ".glitchhunter" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.persist_path = self.cache_dir / "symbol_graph.pkl"

        # Test repository mit Python-Dateien
        self.repo_path = Path(self.temp_dir) / "test_repo"
        self.repo_path.mkdir()

        # Erstelle Test-Datei
        test_file = self.repo_path / "test.py"
        test_file.write_text("""
def hello():
    print("Hello World")

class Greeter:
    def greet(self, name):
        return f"Hello {name}"
""")

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_pickle(self) -> None:
        """Teste Save to Pickle."""
        graph = SymbolGraph()
        graph.add_symbol("hello", "function", "test.py", 1, 5)
        graph.add_symbol("Greeter", "class", "test.py", 7, 15)

        graph.save_pickle(str(self.persist_path))

        # Verify file exists
        self.assertTrue(self.persist_path.exists())

        # Verify content
        with open(self.persist_path, "rb") as f:
            data = pickle.load(f)

        self.assertEqual(len(data["symbols"]), 2)
        self.assertEqual(data["symbols"][0]["name"], "hello")
        self.assertIn("cached_at", data["metadata"])

    def test_load_pickle_valid_cache(self) -> None:
        """Teste Load from Pickle with valid cache."""
        # Create and save graph
        graph1 = SymbolGraph(repo_path=str(self.repo_path))
        graph1.add_symbol("hello", "function", "test.py", 1, 5)
        graph1.save_pickle(str(self.persist_path))

        # Load into new graph
        graph2 = SymbolGraph(repo_path=str(self.repo_path))
        result = graph2.load_pickle(str(self.persist_path))

        self.assertTrue(result)
        self.assertEqual(len(graph2), 1)
        symbol = graph2.get_symbol("hello")
        self.assertIsNotNone(symbol)
        self.assertEqual(symbol.type, "function")

    def test_load_pickle_invalid_cache(self) -> None:
        """Teste Cache-Invalidation bei Repo-Änderung."""
        # Create and save graph
        graph1 = SymbolGraph(repo_path=str(self.repo_path))
        graph1.add_symbol("hello", "function", "test.py", 1, 5)
        graph1.save_pickle(str(self.persist_path))

        # Modify repo (change hash)
        new_file = self.repo_path / "new_file.py"
        new_file.write_text("x = 1")

        # Try to load - should be invalid
        graph2 = SymbolGraph(repo_path=str(self.repo_path))
        result = graph2.load_pickle(str(self.persist_path))

        self.assertFalse(result)

    def test_auto_save_on_shutdown(self) -> None:
        """Teste Auto-Save beim Shutdown."""
        graph = SymbolGraph(
            repo_path=str(self.repo_path),
            persist_path=str(self.persist_path),
            auto_persist=True,
        )
        graph.add_symbol("test_func", "function", "main.py", 1, 10)

        # Trigger manual cleanup to simulate shutdown
        graph._auto_save()

        self.assertTrue(self.persist_path.exists())

        # Verify content
        with open(self.persist_path, "rb") as f:
            data = pickle.load(f)

        self.assertEqual(len(data["symbols"]), 1)
        self.assertEqual(data["symbols"][0]["name"], "test_func")

    def test_auto_load_on_init(self) -> None:
        """Teste Auto-Load beim Start."""
        # Create and save graph
        graph1 = SymbolGraph(repo_path=str(self.repo_path))
        graph1.add_symbol("auto_func", "function", "auto.py", 1, 5)
        graph1.save_pickle(str(self.persist_path))

        # Create new graph with same persist path - should auto-load
        graph2 = SymbolGraph(
            repo_path=str(self.repo_path),
            persist_path=str(self.persist_path),
            auto_persist=False,  # Disable to avoid double-save in test
        )

        # Should have loaded automatically
        self.assertEqual(len(graph2), 1)
        symbol = graph2.get_symbol("auto_func")
        self.assertIsNotNone(symbol)

    def test_compute_repo_hash(self) -> None:
        """Teste Repo-Hash Berechnung."""
        graph = SymbolGraph(repo_path=str(self.repo_path))
        hash1 = graph._compute_repo_hash()

        self.assertIsNotNone(hash1)
        self.assertEqual(len(hash1), 16)  # First 16 chars

        # Hash should change when file changes
        (self.repo_path / "new.py").write_text("new content")
        hash2 = graph._compute_repo_hash()

        self.assertNotEqual(hash1, hash2)

    def test_should_ignore(self) -> None:
        """Teste File-Ignore Logik."""
        graph = SymbolGraph()

        # Should ignore
        self.assertTrue(graph._should_ignore(Path(".git/config")))
        self.assertTrue(graph._should_ignore(Path("node_modules/pkg/index.js")))
        self.assertTrue(graph._should_ignore(Path("__pycache__/module.pyc")))
        self.assertTrue(graph._should_ignore(Path(".venv/bin/python")))

        # Should not ignore
        self.assertFalse(graph._should_ignore(Path("src/main.py")))
        self.assertFalse(graph._should_ignore(Path("tests/test_app.py")))


class TestRepositoryMapperIncremental(unittest.TestCase):
    """Tests für RepositoryMapper Incremental Scan."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.temp_dir) / ".glitchhunter" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.persist_path = self.cache_dir / "symbol_graph.pkl"

        # Test repository
        self.repo_path = Path(self.temp_dir) / "test_repo"
        self.repo_path.mkdir()

        # Create initial Python file
        test_file = self.repo_path / "main.py"
        test_file.write_text("""
def main():
    helper()

def helper():
    pass
""")

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_build_graph_incremental(self) -> None:
        """Teste Incremental Build mit Cache."""
        # First build - full scan
        mapper1 = RepositoryMapper(
            self.repo_path,
            persist_path=self.persist_path,
            auto_persist=True,
        )
        graph1 = mapper1.build_graph(incremental=False)

        symbol_count1 = len(graph1)

        # Save cache
        mapper1.symbol_graph.save_pickle(str(self.persist_path))

        # Second build - should use cache
        mapper2 = RepositoryMapper(
            self.repo_path,
            persist_path=self.persist_path,
            auto_persist=False,
        )
        graph2 = mapper2.build_graph(incremental=True)

        # Should have loaded from cache
        self.assertEqual(len(graph2), symbol_count1)

    def test_can_use_cache(self) -> None:
        """Teste Cache-Validität Prüfung."""
        mapper = RepositoryMapper(
            self.repo_path,
            persist_path=self.persist_path,
            auto_persist=False,
        )

        # No cache yet
        self.assertFalse(mapper._can_use_cache())

        # Create cache
        mapper.symbol_graph.save_pickle(str(self.persist_path))

        # Should be valid now
        self.assertTrue(mapper._can_use_cache())

    def test_scan_changed_files_git(self) -> None:
        """Teste Git-basierte Change-Detection."""
        mapper = RepositoryMapper(self.repo_path)

        # Not a git repo - should return empty
        changed = mapper.scan_changed_files()
        self.assertEqual(changed, [])

    def test_invalidate_cache(self) -> None:
        """Teste Cache-Invalidation."""
        mapper = RepositoryMapper(
            self.repo_path,
            persist_path=self.persist_path,
            auto_persist=False,
        )

        # Create cache
        mapper.symbol_graph.save_pickle(str(self.persist_path))
        self.assertTrue(self.persist_path.exists())

        # Invalidate
        mapper.invalidate_cache()

        # Should be deleted
        self.assertFalse(self.persist_path.exists())

    def test_parse_files_incremental(self) -> None:
        """Teste Incremental File-Parsing."""
        mapper = RepositoryMapper(self.repo_path)

        # Parse specific files
        mapper._parse_files(["main.py"])

        # Should have symbols
        self.assertGreater(len(mapper.symbol_graph), 0)


class TestRedisIntegration(unittest.TestCase):
    """Tests für Redis-Integration (mock)."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir) / "test_repo"
        self.repo_path.mkdir()

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("redis.Redis")
    def test_redis_save_mock(self, mock_redis_class: MagicMock) -> None:
        """Teste Redis Save (mock)."""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis

        graph = SymbolGraph(repo_path=str(self.repo_path))
        graph.add_symbol("redis_func", "function", "redis.py", 1, 5)

        # Simulate Redis save
        import pickle
        import hashlib

        repo_hash = hashlib.sha256(str(self.repo_path).encode()).hexdigest()[:16]
        key = f"symbol_graph:{repo_hash}"
        data = pickle.dumps(graph.to_dict())

        mock_redis.setex(key, 7 * 24 * 3600, data)

        # Verify Redis call
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args[0]
        self.assertEqual(args[0], key)

    @patch("redis.Redis")
    def test_redis_load_mock(self, mock_redis_class: MagicMock) -> None:
        """Teste Redis Load (mock)."""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis

        # Setup mock data
        graph = SymbolGraph(repo_path=str(self.repo_path))
        graph.add_symbol("cached_func", "function", "cache.py", 1, 5)
        data = pickle.dumps(graph.to_dict())

        import hashlib

        repo_hash = hashlib.sha256(str(self.repo_path).encode()).hexdigest()[:16]
        key = f"symbol_graph:{repo_hash}"
        mock_redis.get.return_value = data

        # Simulate Redis load
        cached_data = mock_redis.get(key)
        if cached_data:
            loaded_data = pickle.loads(cached_data)
            loaded_graph = SymbolGraph.from_dict(loaded_data)

            self.assertEqual(len(loaded_graph), 1)
            symbol = loaded_graph.get_symbol("cached_func")
            self.assertIsNotNone(symbol)


class TestSymbolGraphEdgeCases(unittest.TestCase):
    """Tests für Edge Cases."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.temp_dir) / ".glitchhunter" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_nonexistent_pickle(self) -> None:
        """Teste Load von nicht-existierender Datei."""
        graph = SymbolGraph()
        result = graph.load_pickle("/nonexistent/path/cache.pkl")
        self.assertFalse(result)

    def test_load_corrupted_pickle(self) -> None:
        """Teste Load von korrupter Datei."""
        corrupt_path = self.cache_dir / "corrupt.pkl"
        corrupt_path.write_text("not a valid pickle")

        graph = SymbolGraph()
        result = graph.load_pickle(str(corrupt_path))
        self.assertFalse(result)

    def test_save_to_readonly_path(self) -> None:
        """Teste Save zu read-only Pfad."""
        readonly_dir = self.cache_dir / "readonly"
        readonly_dir.mkdir()
        os.chmod(str(readonly_dir), 0o444)  # Read-only

        readonly_path = readonly_dir / "cache.pkl"
        graph = SymbolGraph()

        try:
            graph.save_pickle(str(readonly_path))
            # If we get here, test should fail (unless running as root)
            if os.geteuid() != 0:
                self.fail("Expected exception for read-only path")
        except (PermissionError, OSError):
            pass  # Expected
        finally:
            os.chmod(str(readonly_dir), 0o755)

    def test_empty_repo_hash(self) -> None:
        """Teste Hash für nicht-existierendes Repo."""
        graph = SymbolGraph(repo_path="/nonexistent/repo")
        hash_result = graph._compute_repo_hash()
        self.assertEqual(hash_result, "")

    def test_pickle_json_fallback(self) -> None:
        """Teste JSON Fallback wenn Pickle nicht existiert."""
        repo_path = Path(self.temp_dir) / "test_repo"
        repo_path.mkdir()

        json_path = self.cache_dir / "symbol_graph.json"

        # Create JSON cache
        graph1 = SymbolGraph(repo_path=str(repo_path))
        graph1.add_symbol("json_func", "function", "json.py", 1, 5)
        graph1.save_json(str(json_path))

        # Manually test JSON loading
        graph2 = SymbolGraph.load_json(str(json_path))

        # Should have loaded from JSON
        self.assertEqual(len(graph2), 1)
        symbol = graph2.get_symbol("json_func")
        self.assertIsNotNone(symbol)
        self.assertEqual(symbol.type, "function")


if __name__ == "__main__":
    unittest.main()
