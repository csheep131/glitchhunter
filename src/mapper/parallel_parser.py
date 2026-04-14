"""
Parallel Parser für GlitchHunter.

Parallele Datei-Analyse mit:
- Multiprocessing für CPU-bound Parsing
- Batch-Processing für große Repositories
- Inkrementelle Analyse (nur geänderte Dateien)
- Fortschritts-Tracking

Usage:
    parser = ParallelParser(max_workers=4)
    results = parser.parse_directory("/path/to/repo")
"""

import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
import time

from mapper.tree_sitter_manager import (
    TreeSitterParserManager,
    ParseResult,
    get_parser_manager,
    parse_file,
)

logger = logging.getLogger(__name__)


@dataclass
class ParallelParseResult:
    """
    Ergebnis des parallelen Parsens.

    Attributes:
        total_files: Gesamtanzahl Dateien
        successful: Erfolgreich geparst
        failed: Fehlgeschlagen
        skipped: Übersprungen (Cache)
        errors: Liste von Fehlern
        total_time_seconds: Gesamtzeit
        avg_time_per_file: Durchschnittszeit pro Datei
    """

    total_files: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    total_time_seconds: float = 0.0
    results: Dict[str, ParseResult] = field(default_factory=dict)

    @property
    def avg_time_per_file(self) -> float:
        """Durchschnittszeit pro Datei."""
        if self.total_files == 0:
            return 0.0
        return self.total_time_seconds / self.total_files

    @property
    def success_rate(self) -> float:
        """Erfolgsquote."""
        if self.total_files == 0:
            return 0.0
        return self.successful / self.total_files

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "total_files": self.total_files,
            "successful": self.successful,
            "failed": self.failed,
            "skipped": self.skipped,
            "success_rate": round(self.success_rate, 2),
            "total_time_seconds": round(self.total_time_seconds, 2),
            "avg_time_per_file": round(self.avg_time_per_file, 4),
            "errors_count": len(self.errors),
        }


@dataclass
class FileBatch:
    """
    Batch von Dateien zum Parsen.

    Attributes:
        files: Liste von Dateipfaden
        language: Sprache für alle Dateien (optional)
    """

    files: List[str]
    language: Optional[str] = None


def _parse_single_file(args: Tuple[str, Optional[str]]) -> Tuple[str, ParseResult]:
    """
    Parst einzelne Datei (für Multiprocessing).

    Args:
        args: Tuple aus (file_path, language).

    Returns:
        Tuple aus (file_path, ParseResult).
    """
    file_path, language = args
    result = parse_file(file_path, language)
    return (file_path, result)


class ParallelParser:
    """
    Paralleler Parser für große Repositories.

    Features:
    - Multiprocessing für CPU-bound Parsing
    - Batch-Processing
    - Fortschritts-Tracking
    - Inkrementelle Analyse

    Usage:
        parser = ParallelParser(max_workers=4)
        results = parser.parse_directory("/path/to/repo")
    """

    def __init__(
        self,
        max_workers: Optional[int] = None,
        batch_size: int = 50,
        progress_callback: Optional[callable] = None,
    ) -> None:
        """
        Initialisiert ParallelParser.

        Args:
            max_workers: Maximale Worker-Anzahl (default: CPU-Kerne).
            batch_size: Batch-Größe für Processing.
            progress_callback: Callback für Fortschritts-Updates.
        """
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.batch_size = batch_size
        self.progress_callback = progress_callback

        # Parser-Manager (wird in jedem Process neu erstellt)
        self._parser_manager: Optional[TreeSitterParserManager] = None

        logger.debug(
            f"ParallelParser initialisiert: max_workers={self.max_workers}, "
            f"batch_size={self.batch_size}"
        )

    @property
    def parser_manager(self) -> TreeSitterParserManager:
        """Holt oder erstellt Parser-Manager."""
        if self._parser_manager is None:
            self._parser_manager = TreeSitterParserManager()
        return self._parser_manager

    def parse_directory(
        self,
        directory: str,
        extensions: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        max_files: Optional[int] = None,
    ) -> ParallelParseResult:
        """
        Parst alle Dateien in einem Verzeichnis.

        Args:
            directory: Verzeichnis-Pfad.
            extensions: Zu parse Erweiterungen (default: alle unterstützten).
            exclude_patterns: Auszuschließende Patterns.
            max_files: Maximale Anzahl Dateien.

        Returns:
            ParallelParseResult.
        """
        start_time = time.time()

        logger.info(f"Starte paralleles Parsing von {directory}")

        # Dateien sammeln
        files = self._collect_files(
            directory,
            extensions,
            exclude_patterns,
            max_files,
        )

        if not files:
            logger.warning(f"Keine Dateien zum Parsen gefunden in {directory}")
            return ParallelParseResult()

        logger.info(f"Found {len(files)} files to parse")

        # Progress-Tracking
        result = ParallelParseResult(total_files=len(files))
        completed = 0

        # Paralleles Parsing
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Futures einreichen
            future_to_file = {
                executor.submit(_parse_single_file, (f, None)): f
                for f in files
            }

            # Ergebnisse sammeln
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                completed += 1

                try:
                    file_path, parse_result = future.result()
                    result.results[file_path] = parse_result

                    if parse_result.success:
                        result.successful += 1
                    else:
                        result.failed += 1
                        result.errors.extend([e.to_dict() for e in parse_result.errors])

                except Exception as e:
                    result.failed += 1
                    result.errors.append({
                        "file_path": file_path,
                        "error": str(e),
                        "error_type": "exception",
                    })
                    logger.error(f"Parse error for {file_path}: {e}")

                # Fortschritt melden
                if self.progress_callback:
                    self.progress_callback(completed, len(files))

                # Logging alle 10%
                if completed % max(1, len(files) // 10) == 0:
                    progress = (completed / len(files)) * 100
                    logger.info(f"Parsing progress: {progress:.1f}% ({completed}/{len(files)})")

        result.total_time_seconds = time.time() - start_time

        logger.info(
            f"Parallel parsing completed: {result.successful}/{len(files)} successful "
            f"in {result.total_time_seconds:.2f}s"
        )

        return result

    def parse_files_in_parallel(
        self,
        files: List[str],
        languages: Optional[Dict[str, str]] = None,
    ) -> ParallelParseResult:
        """
        Parst explizite Liste von Dateien parallel.

        Args:
            files: Liste von Dateipfaden.
            languages: Optional Mapping von file_path → language.

        Returns:
            ParallelParseResult.
        """
        start_time = time.time()
        result = ParallelParseResult(total_files=len(files))

        if not files:
            return result

        logger.info(f"Parsing {len(files)} files with {self.max_workers} workers")

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Futures mit Sprachen
            future_to_file = {}
            for file_path in files:
                language = languages.get(file_path) if languages else None
                future = executor.submit(_parse_single_file, (file_path, language))
                future_to_file[future] = file_path

            # Ergebnisse sammeln
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]

                try:
                    file_path, parse_result = future.result()
                    result.results[file_path] = parse_result

                    if parse_result.success:
                        result.successful += 1
                    else:
                        result.failed += 1
                        result.errors.extend([e.to_dict() for e in parse_result.errors])

                except Exception as e:
                    result.failed += 1
                    result.errors.append({
                        "file_path": file_path,
                        "error": str(e),
                        "error_type": "exception",
                    })

        result.total_time_seconds = time.time() - start_time

        return result

    def parse_in_batches(
        self,
        files: List[str],
        batch_size: Optional[int] = None,
    ) -> ParallelParseResult:
        """
        Parst Dateien in Batches.

        Args:
            files: Liste von Dateien.
            batch_size: Batch-Größe.

        Returns:
            ParallelParseResult.
        """
        batch_size = batch_size or self.batch_size
        result = ParallelParseResult(total_files=len(files))

        # Dateien in Batches aufteilen
        batches = [
            files[i:i + batch_size]
            for i in range(0, len(files), batch_size)
        ]

        logger.info(f"Processing {len(files)} files in {len(batches)} batches")

        for i, batch in enumerate(batches, 1):
            logger.info(f"Processing batch {i}/{len(batches)} ({len(batch)} files)")

            # Batch parallel parsen
            batch_result = self.parse_files_in_parallel(batch)

            # Ergebnisse aggregieren
            result.successful += batch_result.successful
            result.failed += batch_result.failed
            result.errors.extend(batch_result.errors)
            result.results.update(batch_result.results)

            # Fortschritt
            if self.progress_callback:
                completed = sum(len(b) for b in batches[:i])
                self.progress_callback(completed, len(files))

        result.total_time_seconds = sum(
            r.total_time_seconds for r in [result]  # Vereinfacht
        )

        return result

    def _collect_files(
        self,
        directory: str,
        extensions: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        max_files: Optional[int] = None,
    ) -> List[str]:
        """
        Sammelt Dateien aus Verzeichnis.

        Args:
            directory: Verzeichnis-Pfad.
            extensions: Zu parse Erweiterungen.
            exclude_patterns: Auszuschließende Patterns.
            max_files: Maximale Anzahl Dateien.

        Returns:
            Liste von Dateipfaden.
        """
        from mapper.tree_sitter_manager import TreeSitterParserManager

        # Unterstützte Erweiterungen
        if extensions:
            valid_extensions = set(extensions)
        else:
            # Alle unterstützten Erweiterungen sammeln
            valid_extensions = set()
            for lang_config in TreeSitterParserManager.SUPPORTED_LANGUAGES.values():
                valid_extensions.update(lang_config["extensions"])

        # Exclude-Patterns
        exclude = set(exclude_patterns or [])
        exclude_dirs = {p for p in exclude if not p.startswith("*")}
        exclude_files = {p for p in exclude if p.startswith("*")}

        files = []
        dir_path = Path(directory)

        for file_path in dir_path.rglob("*"):
            # Nur Dateien
            if not file_path.is_file():
                continue

            # Erweiterung prüfen
            if file_path.suffix.lower() not in valid_extensions:
                continue

            # Exclude-Dirs prüfen
            if any(excl in str(file_path) for excl in exclude_dirs):
                continue

            # Exclude-Files prüfen
            if any(file_path.match(pattern) for pattern in exclude_files):
                continue

            files.append(str(file_path))

            # Max-Files-Limit
            if max_files and len(files) >= max_files:
                break

        return files

    def get_symbols_from_results(
        self,
        results: ParallelParseResult,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extrahiert Symbole aus Parse-Ergebnissen.

        Args:
            results: ParallelParseResult.

        Returns:
            Dict mapping file_path → symbols.
        """
        symbols_by_file = {}

        for file_path, parse_result in results.results.items():
            if parse_result.success and parse_result.tree:
                # Sprache erkennen
                language = self.parser_manager._detect_language(file_path)

                # Symbole extrahieren
                symbols = self.parser_manager.extract_symbols(
                    parse_result.tree,
                    language,
                    file_path,
                )

                symbols_by_file[file_path] = symbols

        return symbols_by_file

    def clear_cache(self) -> None:
        """Leert alle Caches."""
        self.parser_manager.clear_cache()
        logger.info("ParallelParser cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Holt Parser-Statistiken.

        Returns:
            Statistiken als Dict.
        """
        return self.parser_manager.get_stats()


def parse_repository(
    repo_path: str,
    max_workers: int = 4,
    progress_callback: Optional[callable] = None,
) -> ParallelParseResult:
    """
    Convenience-Funktion zum Parsen eines Repositories.

    Args:
        repo_path: Pfad zum Repository.
        max_workers: Maximale Worker-Anzahl.
        progress_callback: Callback für Fortschritt.

    Returns:
        ParallelParseResult.
    """
    parser = ParallelParser(
        max_workers=max_workers,
        progress_callback=progress_callback,
    )

    return parser.parse_directory(repo_path)


def parse_files(
    files: List[str],
    max_workers: int = 4,
) -> ParallelParseResult:
    """
    Convenience-Funktion zum Parsen einer Dateiliste.

    Args:
        files: Liste von Dateipfaden.
        max_workers: Maximale Worker-Anzahl.

    Returns:
        ParallelParseResult.
    """
    parser = ParallelParser(max_workers=max_workers)
    return parser.parse_files_in_parallel(files)
