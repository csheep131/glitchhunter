#!/usr/bin/env python3
"""
AFL++ Fuzzer Integration for GlitchHunter

Integrates AFL++ for coverage-guided fuzzing of C/C++ code.
Supports both persistent mode and standard fuzzing.
"""

import logging
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AFLFuzzingResult:
    """Ergebnis eines AFL++ Fuzzing-Laufs."""

    total_execs: int = 0
    execs_per_sec: float = 0.0
    crashes_found: int = 0
    hangs_found: int = 0
    coverage: float = 0.0
    unique_crashes: int = 0
    runtime_seconds: float = 0.0
    crash_samples: List[Dict[str, Any]] = field(default_factory=list)
    coverage_map: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_execs": self.total_execs,
            "execs_per_sec": self.execs_per_sec,
            "crashes_found": self.crashes_found,
            "hangs_found": self.hangs_found,
            "coverage": self.coverage,
            "unique_crashes": self.unique_crashes,
            "runtime_seconds": self.runtime_seconds,
            "crash_samples": self.crash_samples,
        }


class AFLPlusPlusFuzzer:
    """
    AFL++ Fuzzer für C/C++ Code.

    Usage:
        fuzzer = AFLPlusPlusFuzzer(output_dir="/tmp/afl_output")
        result = fuzzer.fuzz(
            target_binary="./fuzz_target",
            input_corpus="./inputs",
            timeout=3600,
        )
    """

    def __init__(
        self,
        output_dir: str = "/tmp/glitchhunter_afl",
        afl_path: Optional[str] = None,
    ):
        """
        Initialisiert AFL++ Fuzzer.

        Args:
            output_dir: Verzeichnis für Fuzzing-Output (Crashes, Hangs, Queue)
            afl_path: Pfad zu AFL++ Binary (auto-detect wenn None)
        """
        self.output_dir = Path(output_dir)
        self.afl_path = afl_path or self._find_afl()
        self.work_dir = self.output_dir / "work"
        self.crash_dir = self.output_dir / "crashes"
        self.hang_dir = self.output_dir / "hangs"

        if not self.afl_path:
            logger.warning(
                "AFL++ not found. Install with: sudo apt install afl++ or pip install aflpp"
            )

    def _find_afl(self) -> Optional[str]:
        """Sucht AFL++ Installation."""
        # Versuch 1: afl-fuzz im PATH
        afl_fuzz = shutil.which("afl-fuzz")
        if afl_fuzz:
            logger.info(f"AFL++ found: {afl_fuzz}")
            return afl_fuzz

        # Versuch 2: Häufige Installationspfade
        common_paths = [
            "/usr/bin/afl-fuzz",
            "/usr/local/bin/afl-fuzz",
            "/opt/aflplusplus/afl-fuzz",
        ]
        for path in common_paths:
            if os.path.exists(path):
                logger.info(f"AFL++ found: {path}")
                return path

        return None

    def fuzz(
        self,
        target_binary: str,
        input_corpus: Optional[str] = None,
        timeout: int = 3600,
        memory_limit: int = 256,
        timeout_limit: int = 1000,
        parallel_jobs: int = 1,
    ) -> AFLFuzzingResult:
        """
        Startet AFL++ Fuzzing.

        Args:
            target_binary: Zu fuzzendes Binary (muss instrumentiert sein)
            input_corpus: Verzeichnis mit initialem Input-Corpus
            timeout: Maximale Laufzeit in Sekunden
            memory_limit: Memory-Limit in MB
            timeout_limit: Timeout pro Exec in ms
            parallel_jobs: Anzahl paralleler Fuzzer-Prozesse

        Returns:
            AFLFuzzingResult mit Statistiken und gefundenen Crashes
        """
        target = Path(target_binary)
        if not target.exists():
            raise FileNotFoundError(f"Target binary not found: {target}")

        # Verzeichnisse erstellen
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.crash_dir.mkdir(parents=True, exist_ok=True)
        self.hang_dir.mkdir(parents=True, exist_ok=True)

        # Input-Corpus vorbereiten
        if input_corpus:
            corpus_dir = Path(input_corpus)
        else:
            # Default-Corpus erstellen
            corpus_dir = self.output_dir / "default_corpus"
            corpus_dir.mkdir(parents=True, exist_ok=True)
            # Minimaler Start-Input
            (corpus_dir / "seed1").write_bytes(b"AAAAAAAAAA")

        # AFL++ Command bauen
        cmd = self._build_afl_command(
            target=str(target),
            corpus_dir=str(corpus_dir),
            memory_limit=memory_limit,
            timeout_limit=timeout_limit,
            parallel_jobs=parallel_jobs,
        )

        logger.info(f"Starting AFL++ fuzzing: {' '.join(cmd)}")
        logger.info(f"Output directory: {self.output_dir}")

        start_time = time.time()
        result = AFLFuzzingResult()

        try:
            # AFL++ starten (non-interactive mit -i und -o)
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Warten mit Timeout
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                logger.info(f"Fuzzing timeout ({timeout}s) reached, stopping...")
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()

            result.runtime_seconds = time.time() - start_time

            # Ergebnisse parsen
            result = self._parse_fuzzer_stats(result)

        except Exception as e:
            logger.error(f"AFL++ fuzzing failed: {e}")
            result.runtime_seconds = time.time() - start_time

        logger.info(
            f"Fuzzing complete: {result.total_execs} execs, "
            f"{result.crashes_found} crashes, {result.unique_crashes} unique"
        )

        return result

    def _build_afl_command(
        self,
        target: str,
        corpus_dir: str,
        memory_limit: int,
        timeout_limit: int,
        parallel_jobs: int,
    ) -> List[str]:
        """Baut AFL++ Command."""
        cmd = [
            self.afl_path or "afl-fuzz",
            "-i",
            corpus_dir,
            "-o",
            str(self.output_dir),
            "-m",
            str(memory_limit),
            "-t",
            str(timeout_limit),
            "-V",  # Validate mode (für Tests)
            "--",
            target,
            "@@",  # Input-File-Placeholder
        ]

        # Parallel-Fuzzing Optionen
        if parallel_jobs > 1:
            # Master/Slave-Setup
            cmd.insert(1, "-M")  # Master
            cmd.insert(2, "master")

        return cmd

    def _parse_fuzzer_stats(self, result: AFLFuzzingResult) -> AFLFuzzingResult:
        """Parses AFL++ Statistiken aus Output-Verzeichnis."""
        # fuzzer_stats Datei lesen
        stats_file = self.work_dir / "fuzzer_stats"
        if stats_file.exists():
            try:
                content = stats_file.read_text()
                for line in content.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        key = key.strip()
                        value = value.strip()

                        if key == "execs_done":
                            result.total_execs = int(value)
                        elif key == "execs_per_sec":
                            result.execs_per_sec = float(value)
                        elif key == "unique_crashes":
                            result.unique_crashes = int(value)
                        elif key == "unique_hangs":
                            result.hangs_found = int(value)
                        elif key == "bitmap_cvg":
                            result.coverage = float(value)
            except Exception as e:
                logger.warning(f"Failed to parse fuzzer_stats: {e}")

        # Crash-Files analysieren
        crash_dir = self.work_dir / "default_crashes"
        if crash_dir.exists():
            crash_files = list(crash_dir.glob("id:*"))
            result.crashes_found = len(crash_files)

            # Erste Crashes als Samples laden
            for crash_file in crash_files[:5]:
                try:
                    sample = {
                        "file": str(crash_file),
                        "size": crash_file.stat().st_size,
                        "content": crash_file.read_bytes()[:100].hex(),
                    }
                    result.crash_samples.append(sample)
                except Exception:
                    pass

        return result

    def minimize_corpus(self, corpus_dir: str) -> List[str]:
        """
        Minimiert Input-Corpus mit afl-cmin.

        Args:
            corpus_dir: Verzeichnis mit Corpus-Files

        Returns:
            Liste der minimalen Corpus-Files
        """
        if not self.afl_path:
            logger.warning("AFL++ not found, skipping corpus minimization")
            return []

        minimized_dir = self.output_dir / "minimized_corpus"
        minimized_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "afl-cmin",
            "-i",
            corpus_dir,
            "-o",
            str(minimized_dir),
            "--",
            # Target wird hier benötigt
        ]

        logger.info(f"Minimizing corpus: {' '.join(cmd)}")

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            minimized_files = list(minimized_dir.iterdir())
            logger.info(f"Corpus minimized to {len(minimized_files)} files")
            return [str(f) for f in minimized_files]
        except subprocess.CalledProcessError as e:
            logger.error(f"Corpus minimization failed: {e}")
            return []

    def analyze_crash(self, crash_file: str) -> Dict[str, Any]:
        """
        Analysiert einen Crash im Detail.

        Args:
            crash_file: Pfad zur Crash-Input-Datei

        Returns:
            Dict mit Crash-Analyse
        """
        crash_path = Path(crash_file)
        if not crash_path.exists():
            return {"error": "Crash file not found"}

        # Crash-Information extrahieren (aus Dateinamen)
        # Format: id:000000,sig:11,src:000001,op:flip1,pos:42
        info: Dict[str, Any] = {
            "file": str(crash_path),
            "size": crash_path.stat().st_size,
            "content": crash_path.read_bytes(),
        }

        # Metadaten aus Filename parsen
        parts = crash_path.name.split(",")
        for part in parts:
            if ":" in part:
                key, value = part.split(":", 1)
                if key == "id":
                    info["crash_id"] = value
                elif key == "sig":
                    info["signal"] = int(value)
                    info["crash_type"] = self._signal_to_type(int(value))
                elif key == "op":
                    info["mutation_op"] = value

        return info

    def _signal_to_type(self, signal: int) -> str:
        """Konvertiert Signal-Nummer zu Crash-Typ."""
        signal_types = {
            4: "SIGILL (Illegal Instruction)",
            6: "SIGABRT (Abort)",
            8: "SIGFPE (Floating Point Exception)",
            11: "SIGSEGV (Segmentation Fault)",
            7: "SIGBUS (Bus Error)",
        }
        return signal_types.get(signal, f"Unknown Signal {signal}")
