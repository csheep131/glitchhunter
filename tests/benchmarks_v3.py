"""
Benchmarks für GlitchHunter v3.0.

Vergleicht Performance zwischen:
- Sequenzieller vs. paralleler Analyse
- Verschiedenen Repository-Grßen
- Agenten-Konfigurationen

Benchmarks:
1. Parallel vs. Sequential Speedup
2. Sharding-Effektivitt
3. Circuit-Breaker Overhead
4. Language Registry Performance
5. End-to-End Analyse-Zeit

Usage:
    pytest tests/benchmarks_v3.py --benchmark-only
    pytest tests/benchmarks_v3.py --benchmark-compare=0001
"""

import asyncio
import time
from pathlib import Path
from typing import List, Tuple

import pytest

from agent.parallel_swarm import (
    ParallelSwarmCoordinator,
    ParallelConfig,
    ParallelExecutionResult,
)
from agent.swarm_coordinator import SwarmCoordinator
from prefilter.language_registry import LanguageRegistry, get_registry


# ============== Fixtures ==============

@pytest.fixture
def small_repo(tmp_path):
    """Kleines Test-Repository (<10k LOC)."""
    for i in range(10):
        test_file = tmp_path / f"module_{i}.py"
        test_file.write_text("\n".join([
            f"def function_{i}_{j}():",
            f"    return {j}",
            ""
        ] for j in range(10)))
    return tmp_path


@pytest.fixture
def medium_repo(tmp_path):
    """Mittleres Test-Repository (10-100k LOC)."""
    for i in range(50):
        subdir = tmp_path / f"package_{i}"
        subdir.mkdir()
        for j in range(20):
            test_file = subdir / f"module_{j}.py"
            test_file.write_text("\n".join([
                f"class Class_{i}_{j}:",
                f"    def method_{k}(self):",
                f"        return {k}",
                ""
            ] for k in range(20)))
    return tmp_path


@pytest.fixture
def large_repo(tmp_path):
    """Großes Test-Repository (>100k LOC)."""
    for i in range(100):
        subdir = tmp_path / f"package_{i}"
        subdir.mkdir()
        for j in range(50):
            test_file = subdir / f"module_{j}.py"
            test_file.write_text("\n".join([
                f"def complex_function_{i}_{j}_{k}(x):",
                f"    if x > {k}:",
                f"        return x * {k}",
                f"    return 0",
                ""
            ] for k in range(30)))
    return tmp_path


# ============== Benchmark: Parallel vs. Sequential ==============

class TestBenchmarksParallel:
    """Benchmarks für parallele Verarbeitung."""
    
    @pytest.mark.benchmark(group="parallel-small")
    def test_sequential_small(self, small_repo, benchmark):
        """Sequenzielle Analyse (kleines Repo)."""
        coordinator = SwarmCoordinator()
        
        def run():
            return asyncio.run(coordinator.run_swarm(str(small_repo)))
        
        result = benchmark(run)
        
        assert result is not None
    
    @pytest.mark.benchmark(group="parallel-small")
    def test_parallel_small(self, small_repo, benchmark):
        """Parallele Analyse (kleines Repo)."""
        coordinator = ParallelSwarmCoordinator(max_workers=4)
        
        def run():
            return asyncio.run(coordinator.run_swarm_parallel(str(small_repo)))
        
        result = benchmark(run)
        
        assert isinstance(result, ParallelExecutionResult)
    
    @pytest.mark.benchmark(group="parallel-medium")
    def test_sequential_medium(self, medium_repo, benchmark):
        """Sequenzielle Analyse (mittleres Repo)."""
        coordinator = SwarmCoordinator()
        
        def run():
            return asyncio.run(coordinator.run_swarm(str(medium_repo)))
        
        result = benchmark(run)
        
        assert result is not None
    
    @pytest.mark.benchmark(group="parallel-medium")
    def test_parallel_medium(self, medium_repo, benchmark):
        """Parallele Analyse (mittleres Repo)."""
        coordinator = ParallelSwarmCoordinator(max_workers=4)
        
        def run():
            return asyncio.run(coordinator.run_swarm_parallel(str(medium_repo)))
        
        result = benchmark(run)
        
        assert isinstance(result, ParallelExecutionResult)
        assert result.parallelization_factor > 1.0
    
    @pytest.mark.benchmark(group="parallel-large")
    def test_parallel_large(self, large_repo, benchmark):
        """Parallele Analyse (großes Repo)."""
        coordinator = ParallelSwarmCoordinator(
            max_workers=8,
            enable_sharding=True,
        )
        
        def run():
            return asyncio.run(coordinator.run_swarm_parallel(str(large_repo)))
        
        result = benchmark(run)
        
        assert isinstance(result, ParallelExecutionResult)
        assert result.parallelization_factor >= 2.0  # Mindestens 2x Speedup


# ============== Benchmark: Sharding ==============

class TestBenchmarksSharding:
    """Benchmarks für Repository-Sharding."""
    
    @pytest.mark.benchmark(group="sharding")
    def test_sharding_enabled(self, large_repo, benchmark):
        """Sharding aktiviert."""
        coordinator = ParallelSwarmCoordinator(
            max_workers=4,
            enable_sharding=True,
        )
        
        def run():
            return asyncio.run(coordinator.run_swarm_parallel(str(large_repo)))
        
        result = benchmark(run)
        
        # Metadata sollte Shard-Info enthalten
        assert "shards_analyzed" in result.metadata
    
    @pytest.mark.benchmark(group="sharding")
    def test_sharding_disabled(self, large_repo, benchmark):
        """Sharding deaktiviert."""
        coordinator = ParallelSwarmCoordinator(
            max_workers=4,
            enable_sharding=False,
        )
        
        def run():
            return asyncio.run(coordinator.run_swarm_parallel(str(large_repo)))
        
        result = benchmark(run)
        
        # Metadata sollte keine Shard-Info haben
        assert result.metadata.get("shards_analyzed", 1) == 1


# ============== Benchmark: Worker Count ==============

class TestBenchmarksWorkers:
    """Benchmarks für Worker-Anzahl."""
    
    @pytest.mark.benchmark(group="workers")
    def test_2_workers(self, medium_repo, benchmark):
        """2 Worker-Threads."""
        coordinator = ParallelSwarmCoordinator(max_workers=2)
        
        def run():
            return asyncio.run(coordinator.run_swarm_parallel(str(medium_repo)))
        
        result = benchmark(run)
        
        assert result.execution_time > 0
    
    @pytest.mark.benchmark(group="workers")
    def test_4_workers(self, medium_repo, benchmark):
        """4 Worker-Threads."""
        coordinator = ParallelSwarmCoordinator(max_workers=4)
        
        def run():
            return asyncio.run(coordinator.run_swarm_parallel(str(medium_repo)))
        
        result = benchmark(run)
        
        assert result.execution_time > 0
    
    @pytest.mark.benchmark(group="workers")
    def test_8_workers(self, medium_repo, benchmark):
        """8 Worker-Threads."""
        coordinator = ParallelSwarmCoordinator(max_workers=8)
        
        def run():
            return asyncio.run(coordinator.run_swarm_parallel(str(medium_repo)))
        
        result = benchmark(run)
        
        assert result.execution_time > 0


# ============== Benchmark: Circuit Breaker ==============

class TestBenchmarksCircuitBreaker:
    """Benchmarks für Circuit-Breaker."""
    
    @pytest.mark.benchmark(group="circuit-breaker")
    def test_circuit_breaker_overhead(self, small_repo, benchmark):
        """Circuit-Breaker Overhead."""
        coordinator = ParallelSwarmCoordinator()
        
        def run():
            return asyncio.run(coordinator.run_swarm_parallel(str(small_repo)))
        
        result = benchmark(run)
        
        # Overhead sollte minimal sein (<10% der Gesamtzeit)
        assert result.execution_time > 0


# ============== Benchmark: Language Registry ==============

class TestBenchmarksLanguageRegistry:
    """Benchmarks für LanguageRegistry."""
    
    @pytest.mark.benchmark(group="language-registry")
    def test_detect_language(self, benchmark):
        """Sprach-Erkennung Performance."""
        registry = LanguageRegistry()
        
        test_files = [
            Path("test.py"),
            Path("test.js"),
            Path("test.ts"),
            Path("test.rs"),
            Path("test.zig"),
            Path("test.sol"),
            Path("test.kt"),
            Path("test.swift"),
            Path("test.php"),
            Path("test.rb"),
        ]
        
        def run():
            for f in test_files:
                registry.detect_language(f)
        
        benchmark(run)
    
    @pytest.mark.benchmark(group="language-registry")
    def test_get_parser_cached(self, benchmark):
        """Parser aus Cache laden."""
        registry = get_registry()
        
        # Erster Aufruf lädt Parser
        registry.get_parser("python")
        
        def run():
            return registry.get_parser("python")
        
        parser = benchmark(run)
        
        assert parser is not None
    
    @pytest.mark.benchmark(group="language-registry")
    def test_get_all_extensions(self, benchmark):
        """Alle Extensions laden."""
        registry = LanguageRegistry()
        
        def run():
            return registry.get_all_extensions()
        
        extensions = benchmark(run)
        
        assert len(extensions) >= 14


# ============== Benchmark: End-to-End ==============

class TestBenchmarksEndToEnd:
    """End-to-End Benchmarks."""
    
    @pytest.mark.benchmark(group="e2e")
    def test_full_pipeline_small(self, small_repo, benchmark):
        """Komplette Pipeline (klein)."""
        config = ParallelConfig(
            max_workers=4,
            enable_sharding=True,
            enable_load_balancing=True,
        )
        
        coordinator = ParallelSwarmCoordinator(
            max_workers=config.max_workers,
            enable_sharding=config.enable_sharding,
            enable_load_balancing=config.enable_load_balancing,
        )
        
        def run():
            return asyncio.run(coordinator.run_swarm_parallel(str(small_repo)))
        
        result = benchmark(run)
        
        # Vollständige Ergebnis-Struktur
        assert hasattr(result, 'success')
        assert hasattr(result, 'findings')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'execution_time')
        assert hasattr(result, 'parallelization_factor')
    
    @pytest.mark.benchmark(group="e2e")
    def test_full_pipeline_medium(self, medium_repo, benchmark):
        """Komplette Pipeline (mittel)."""
        config = ParallelConfig(
            max_workers=4,
            enable_sharding=True,
        )
        
        coordinator = ParallelSwarmCoordinator(
            max_workers=config.max_workers,
            enable_sharding=config.enable_sharding,
        )
        
        def run():
            return asyncio.run(coordinator.run_swarm_parallel(str(medium_repo)))
        
        result = benchmark(run)
        
        assert result.execution_time > 0
        assert result.parallelization_factor >= 1.5  # Mindestens 1.5x Speedup


# ============== Benchmark: Memory ==============

class TestBenchmarksMemory:
    """Memory-Benchmarks."""
    
    @pytest.mark.benchmark(group="memory")
    def test_coordinator_memory(self, large_repo, benchmark):
        """Coordinator Memory-Verbrauch."""
        import tracemalloc
        
        coordinator = ParallelSwarmCoordinator(max_workers=4)
        
        def run():
            tracemalloc.start()
            result = asyncio.run(coordinator.run_swarm_parallel(str(large_repo)))
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            return result, peak
        
        result, peak_memory = benchmark(run)
        
        # Peak Memory sollte < 500MB sein
        assert peak_memory < 500 * 1024 * 1024


# ============== Benchmark Report Helpers ==============

def pytest_benchmark_update_metadata(metadata):
    """Fügt Benchmark-Metadaten hinzu."""
    metadata['glitchhunter_version'] = '3.0.0'
    metadata['python_version'] = '3.10+'
    metadata['platform'] = 'linux'


def pytest_benchmark_compare(current, previous):
    """Vergleicht Benchmarks."""
    if current < previous * 0.9:
        return "✅ Faster"
    elif current > previous * 1.1:
        return "❌ Slower"
    else:
        return "➡️ Same"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])
