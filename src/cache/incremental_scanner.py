"""
Incremental Scanner für GlitchHunter v2.0

Scannt nur geänderte Dateien seit dem letzten Scan.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import hashlib
import sqlite3
import threading

logger = logging.getLogger(__name__)


@dataclass
class FileState:
    """Zustand einer Datei für Incremental Scan."""
    path: str
    mtime: float
    size: int
    content_hash: str
    last_scanned: datetime
    scan_result_hash: Optional[str] = None


@dataclass
class ScanDelta:
    """Delta zwischen zwei Scans."""
    added: List[str]              # Neue Dateien
    modified: List[str]           # Geänderte Dateien
    deleted: List[str]            # Gelöschte Dateien
    unchanged: List[str]          # Unveränderte Dateien
    total_files: int
    incremental: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "added": self.added,
            "modified": self.modified,
            "deleted": self.deleted,
            "unchanged_count": len(self.unchanged),
            "total_files": self.total_files,
            "incremental": self.incremental,
            "scan_scope": len(self.added) + len(self.modified),
        }


class IncrementalScanner:
    """
    Incremental Scanner für effiziente wiederholte Scans.
    
    Features:
    - Trackt Datei-Zustände (mtime, size, hash)
    - Erkennt hinzugefügte/geänderte/gelöschte Dateien
    - Nutzt SymbolCache für Scan-Ergebnisse
    - Git-Integration für Commit-basierte Scans
    """
    
    def __init__(
        self,
        project_path: Path,
        cache_dir: Optional[Path] = None,
    ):
        self.project_path = Path(project_path)
        self.cache_dir = cache_dir or Path.home() / ".glitchhunter" / "incremental"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        
        # SQLite für Datei-Zustände
        self.db_path = self.cache_dir / f"{self._project_id()}.db"
        self._init_db()
        
        # Statistiken
        self.stats = {
            "total_scans": 0,
            "files_scanned": 0,
            "time_saved_ms": 0,
        }
        
        logger.info(f"IncrementalScanner initialisiert für {project_path}")
    
    def _project_id(self) -> str:
        """Erstellt eine eindeutige ID für das Projekt."""
        path_str = str(self.project_path.resolve())
        return hashlib.sha256(path_str.encode()).hexdigest()[:16]
    
    def _init_db(self) -> None:
        """Initialisiert die SQLite-Datenbank."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_states (
                    path TEXT PRIMARY KEY,
                    mtime REAL NOT NULL,
                    size INTEGER NOT NULL,
                    content_hash TEXT NOT NULL,
                    last_scanned TEXT NOT NULL,
                    scan_result_hash TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_scanned ON file_states(last_scanned)
            """)
            conn.commit()
    
    def compute_delta(
        self,
        files: List[Path],
        force_full: bool = False,
    ) -> ScanDelta:
        """
        Berechnet das Delta zwischen aktuellem Zustand und letztem Scan.
        
        Args:
            files: Liste der zu scannenden Dateien
            force_full: Wenn True, werden alle Dateien als modified markiert
            
        Returns:
            ScanDelta mit Kategorisierung der Dateien
        """
        if force_full:
            return ScanDelta(
                added=[],
                modified=[str(f) for f in files],
                deleted=[],
                unchanged=[],
                total_files=len(files),
                incremental=False,
            )
        
        added = []
        modified = []
        unchanged = []
        
        current_paths = {str(f.resolve()) for f in files}
        
        with self._lock:
            for file_path in files:
                path_str = str(file_path.resolve())
                current_state = self._get_file_state(file_path)
                
                if current_state is None:
                    # Datei existiert nicht mehr oder ist neu
                    if file_path.exists():
                        added.append(path_str)
                    continue
                
                stored_state = self._get_stored_state(path_str)
                
                if stored_state is None:
                    added.append(path_str)
                elif self._state_changed(stored_state, current_state):
                    modified.append(path_str)
                else:
                    unchanged.append(path_str)
            
            # Finde gelöschte Dateien
            all_stored = self._get_all_stored_paths()
            deleted = list(all_stored - current_paths)
        
        delta = ScanDelta(
            added=added,
            modified=modified,
            deleted=deleted,
            unchanged=unchanged,
            total_files=len(files),
            incremental=True,
        )
        
        logger.info(f"Scan-Delta: +{len(added)} ~{len(modified)} -{len(deleted)} ={len(unchanged)}")
        return delta
    
    def update_state(
        self,
        file_path: Path,
        scan_result: Any,
    ) -> None:
        """
        Aktualisiert den Zustand einer Datei nach dem Scan.
        
        Args:
            file_path: Pfad zur Datei
            scan_result: Ergebnis des Scans (wird gehasht)
        """
        path_str = str(file_path.resolve())
        
        try:
            stat = file_path.stat()
            content = file_path.read_text(errors='ignore')
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            result_hash = hashlib.sha256(
                json.dumps(scan_result, sort_keys=True, default=str).encode()
            ).hexdigest()[:16]
            
            state = FileState(
                path=path_str,
                mtime=stat.st_mtime,
                size=stat.st_size,
                content_hash=content_hash,
                last_scanned=datetime.utcnow(),
                scan_result_hash=result_hash,
            )
            
            with self._lock:
                self._store_state(state)
        
        except Exception as e:
            logger.warning(f"Konnte Zustand nicht aktualisieren für {file_path}: {e}")
    
    def get_files_to_scan(
        self,
        files: List[Path],
        use_cache: bool = True,
    ) -> Tuple[List[Path], ScanDelta]:
        """
        Gibt die Liste der tatsächlich zu scannenden Dateien zurück.
        
        Args:
            files: Alle potenziellen Dateien
            use_cache: Ob Caching verwendet werden soll
            
        Returns:
            (Dateien die gescannt werden müssen, ScanDelta)
        """
        if not use_cache:
            return files, ScanDelta(
                added=[],
                modified=[str(f) for f in files],
                deleted=[],
                unchanged=[],
                total_files=len(files),
                incremental=False,
            )
        
        delta = self.compute_delta(files)
        to_scan = [Path(p) for p in delta.added + delta.modified]
        
        # Statistik
        if delta.incremental and len(files) > 0:
            saved = len(delta.unchanged)
            self.stats["files_scanned"] += len(to_scan)
            logger.info(f"Incremental Scan: {saved}/{len(files)} Dateien übersprungen")
        
        return to_scan, delta
    
    def invalidate_file(self, file_path: Path) -> bool:
        """Invalidiert den Zustand einer Datei."""
        path_str = str(file_path.resolve())
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM file_states WHERE path = ?",
                    (path_str,)
                )
                conn.commit()
                return cursor.rowcount > 0
    
    def invalidate_all(self) -> int:
        """Leert alle gespeicherten Zustände."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM file_states")
                conn.commit()
                count = cursor.rowcount
                logger.info(f"Incremental Scanner geleert: {count} Einträge")
                return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Gibt Statistiken zurück."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM file_states")
                tracked_files = cursor.fetchone()[0]
            
            return {
                "tracked_files": tracked_files,
                "total_scans": self.stats["total_scans"],
                "files_scanned": self.stats["files_scanned"],
                "project_path": str(self.project_path),
            }
    
    def _get_file_state(self, file_path: Path) -> Optional[FileState]:
        """Erstellt den aktuellen Zustand einer Datei."""
        try:
            if not file_path.exists():
                return None
            
            stat = file_path.stat()
            content = file_path.read_text(errors='ignore')
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            
            return FileState(
                path=str(file_path.resolve()),
                mtime=stat.st_mtime,
                size=stat.st_size,
                content_hash=content_hash,
                last_scanned=datetime.utcnow(),
            )
        except Exception as e:
            logger.debug(f"Konnte Datei-Zustand nicht lesen: {e}")
            return None
    
    def _get_stored_state(self, path: str) -> Optional[FileState]:
        """Holt den gespeicherten Zustand einer Datei."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT path, mtime, size, content_hash, last_scanned, scan_result_hash
                   FROM file_states WHERE path = ?""",
                (path,)
            )
            row = cursor.fetchone()
            
            if row is None:
                return None
            
            return FileState(
                path=row[0],
                mtime=row[1],
                size=row[2],
                content_hash=row[3],
                last_scanned=datetime.fromisoformat(row[4]),
                scan_result_hash=row[5],
            )
    
    def _store_state(self, state: FileState) -> None:
        """Speichert den Zustand einer Datei."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO file_states
                   (path, mtime, size, content_hash, last_scanned, scan_result_hash)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    state.path,
                    state.mtime,
                    state.size,
                    state.content_hash,
                    state.last_scanned.isoformat(),
                    state.scan_result_hash,
                )
            )
            conn.commit()
    
    def _state_changed(self, old: FileState, new: FileState) -> bool:
        """Prüft ob sich der Zustand geändert hat."""
        return (
            old.mtime != new.mtime or
            old.size != new.size or
            old.content_hash != new.content_hash
        )
    
    def _get_all_stored_paths(self) -> Set[str]:
        """Gibt alle gespeicherten Pfade zurück."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT path FROM file_states")
            return {row[0] for row in cursor.fetchall()}