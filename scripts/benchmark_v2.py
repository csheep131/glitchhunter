#!/usr/bin/env python3
"""
GlitchHunter v2.0 Benchmark-Skript

Misst die Performance von GlitchHunter v2.0 Features:
- Scan-Zeit pro 1000 Zeilen Code
- Symbol-Graph Caching Performance
- Incremental Scan Performance
- Ensemble-Modus Performance

Usage:
    python scripts/benchmark_v2.py
    python scripts/benchmark_v2.py --full  # Vollständiger Benchmark
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class BenchmarkResult:
    """Hält Benchmark-Ergebnisse."""
    
    def __init__(self, name: str):
        self.name = name
        self.metrics: Dict[str, Any] = {}
        self.start_time = None
        self.end_time = None
    
    def add_metric(self, key: str, value: Any, unit: str = ""):
        self.metrics[key] = {
            "value": value,
            "unit": unit,
            "timestamp": datetime.now().isoformat(),
        }
    
    def duration(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "metrics": self.metrics,
            "duration_seconds": self.duration(),
        }


class GlitchHunterBenchmark:
    """Benchmark-Suite für GlitchHunter v2.0."""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.results: List[BenchmarkResult] = []
        self.cache_dir = repo_path / ".glitchhunter" / "benchmark"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def count_lines_of_code(self) -> int:
        """Zählt die Zeilen Code im Repository."""
        total_lines = 0
        extensions = [".py", ".js", ".ts", ".rs", ".go", ".java", ".c", ".cpp"]
        
        for ext in extensions:
            for file_path in self.repo_path.rglob(f"*{ext}"):
                # Ignoriere Test- und Build-Verzeichnisse
                if any(p in str(file_path) for p in [".git", "node_modules", "__pycache__", ".venv", "dist", "build", "htmlcov"]):
                    continue
                
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        total_lines += sum(1 for _ in f)
                except Exception:
                    pass
        
        return total_lines
    
    def run_command(self, cmd: List[str], timeout: int = 300) -> tuple:
        """Führt einen Command aus und返回t (duration, success, output)."""
        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration = time.time() - start
            return duration, result.returncode == 0, result.stdout[:500]
        except subprocess.TimeoutExpired:
            duration = time.time() - start
            return duration, False, "Timeout"
        except Exception as e:
            duration = time.time() - start
            return duration, False, str(e)
    
    def benchmark_symbol_graph_build(self) -> BenchmarkResult:
        """Misst die Zeit zum Build des Symbol-Graphs."""
        result = BenchmarkResult("Symbol-Graph Build")
        result.start_time = datetime.now()
        
        # Cache löschen für cold run
        cache_file = self.repo_path / ".glitchhunter" / "cache" / "symbol_graph.pkl"
        if cache_file.exists():
            cache_file.unlink()
        
        # Symbol-Graph Build via Python-API
        from mapper.repo_mapper import RepositoryMapper
        
        start = time.time()
        mapper = RepositoryMapper(self.repo_path)
        graph = mapper.build_graph(incremental=False)
        build_time = time.time() - start

        result.add_metric("build_time", f"{build_time:.2f}", "seconds")
        result.add_metric("symbol_count", len(graph._graph.nodes()), "symbols")
        result.add_metric("edge_count", len(graph._graph.edges()), "edges")
        result.add_metric("file_count", len(set(n.get("file_path", "") for n in graph._graph.nodes(data=True))), "files")
        
        # Cache-Test
        if cache_file.exists():
            cache_size = cache_file.stat().st_size / 1024
            result.add_metric("cache_size", f"{cache_size:.1f}", "KB")
        
        result.end_time = datetime.now()
        return result
    
    def benchmark_incremental_scan(self) -> BenchmarkResult:
        """Misst die Zeit für Incremental-Scan."""
        result = BenchmarkResult("Incremental Scan")
        result.start_time = datetime.now()
        
        from mapper.repo_mapper import RepositoryMapper
        
        # Erster Build (vollständig)
        mapper = RepositoryMapper(self.repo_path)
        mapper.build_graph(incremental=False)
        
        # Zweiter Build (incremental, sollte Cache verwenden)
        start = time.time()
        mapper2 = RepositoryMapper(self.repo_path)
        graph = mapper2.build_graph(incremental=True)
        incremental_time = time.time() - start
        
        result.add_metric("incremental_time", f"{incremental_time:.2f}", "seconds")
        result.add_metric("cache_hit", graph is not None, "boolean")
        
        result.end_time = datetime.now()
        return result
    
    def benchmark_prefilter(self) -> BenchmarkResult:
        """Misst die Prefilter-Performance."""
        result = BenchmarkResult("Prefilter Pipeline")
        result.start_time = datetime.now()
        
        from prefilter.pipeline import PreFilterPipeline
        
        start = time.time()
        pipeline = PreFilterPipeline(self.repo_path)
        prefilter_result = pipeline.run()
        prefilter_time = time.time() - start
        
        result.add_metric("prefilter_time", f"{prefilter_time:.2f}", "seconds")
        result.add_metric("candidates", len(prefilter_result.candidates), "candidates")
        result.add_metric("security_issues", prefilter_result.total_security_issues, "issues")
        result.add_metric("correctness_issues", prefilter_result.total_correctness_issues, "issues")
        
        result.end_time = datetime.now()
        return result
    
    def benchmark_full_scan(self) -> BenchmarkResult:
        """Misst die Zeit für einen vollständigen Scan."""
        result = BenchmarkResult("Full Scan (Ingestion + Shield)")
        result.start_time = datetime.now()
        
        # Ingestion
        from mapper.repo_mapper import RepositoryMapper
        mapper = RepositoryMapper(self.repo_path)
        mapper.build_graph()
        
        # Prefilter
        from prefilter.pipeline import PreFilterPipeline
        pipeline = PreFilterPipeline(self.repo_path)
        prefilter_result = pipeline.run()
        
        result.end_time = datetime.now()
        
        result.add_metric("total_time", f"{result.duration():.2f}", "seconds")
        result.add_metric("loc", self.count_lines_of_code(), "lines")
        result.add_metric("loc_per_second", f"{self.count_lines_of_code() / result.duration():.0f}", "lines/sec")
        
        return result
    
    def run_all_benchmarks(self, full: bool = False) -> dict:
        """Führt alle Benchmarks aus."""
        print("🚀 Starte GlitchHunter v2.0 Benchmarks...\n")
        
        loc = self.count_lines_of_code()
        print(f"📊 Repository: {self.repo_path}")
        print(f"   Zeilen Code: {loc:,}")
        print()
        
        # Basis-Benchmarks
        benchmarks = [
            self.benchmark_symbol_graph_build,
            self.benchmark_incremental_scan,
            self.benchmark_prefilter,
        ]
        
        if full:
            benchmarks.append(self.benchmark_full_scan)
        
        for benchmark_fn in benchmarks:
            print(f"⏱️  Running {benchmark_fn.__name__}...")
            result = benchmark_fn()
            self.results.append(result)
            print(f"   ✅ Dauer: {result.duration():.2f}s")
            for key, metric in result.metrics.items():
                print(f"   - {key}: {metric['value']} {metric.get('unit', '')}")
            print()
        
        # Summary
        summary = {
            "repository": str(self.repo_path),
            "loc": loc,
            "timestamp": datetime.now().isoformat(),
            "benchmarks": [r.to_dict() for r in self.results],
            "total_duration_seconds": sum(r.duration() for r in self.results),
        }
        
        # Speichern
        output_file = self.cache_dir / f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"💾 Ergebnisse gespeichert: {output_file}")
        print()
        
        # Performance-Bewertung
        print("📈 Performance-Bewertung:")
        prefilter_result = next((r for r in self.results if r.name == "Prefilter Pipeline"), None)
        if prefilter_result:
            loc = summary["loc"]
            loc_per_sec = loc / float(prefilter_result.metrics["prefilter_time"]["value"])
            print(f"   - Prefilter: {loc_per_sec:.0f} LOC/s")

            if loc_per_sec >= 2000:
                print("   ✅ Exzellent (>2000 LOC/s)")
            elif loc_per_sec >= 1000:
                print("   ✅ Gut (1000-2000 LOC/s)")
            else:
                print("   ⚠️  Verbesserungsbedarf (<1000 LOC/s)")
        
        return summary


def main():
    parser = argparse.ArgumentParser(description="GlitchHunter v2.0 Benchmark")
    parser.add_argument("--full", action="store_true", help="Vollständiger Benchmark inkl. Full Scan")
    parser.add_argument("--repo", type=str, default=".", help="Repository-Pfad")
    args = parser.parse_args()
    
    repo_path = Path(args.repo).absolute()
    benchmark = GlitchHunterBenchmark(repo_path)
    summary = benchmark.run_all_benchmarks(full=args.full)
    
    # Return-Code basierend auf Performance
    prefilter_result = next((r for r in benchmark.results if r.name == "Prefilter Pipeline"), None)
    if prefilter_result:
        loc = summary["loc"]
        prefilter_time = prefilter_result.metrics["prefilter_time"]["value"]
        loc_per_sec = loc / float(prefilter_time)
        
        if loc_per_sec < 500:
            print("\n⚠️  Warning: Performance unter 500 LOC/s")
            sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
