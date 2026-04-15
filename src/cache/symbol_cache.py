"""
Symbol-Graph Cache für GlitchHunter v2.0

Persistenter Disk-Cache für Symbol-Graphen mit Redis-ähnlicher API.
"""

import json
import hashlib
import logging
import pickle
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import sqlite3
import threading

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Ein Eintrag im Symbol-Cache."""
    key: str
    data: Any
    file_hash: str
    file_path: str
    mtime: float
    created_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "file_hash": self.file_hash,
            "file_path": self.file_path,
            "mtime": self.mtime,
            "created_at": self.created_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "access_count": self.access_count,
        }


class SymbolCache:
    """
    Persistenter Cache für Symbol-Graphen.
    
    Features:
    - SQLite-basierte Metadaten-Speicherung
    - Pickle-basierte Datenspeicherung
    - LRU-Eviction
    - TTL-Support
    - Thread-safe
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_size_mb: int = 512,
        default_ttl_hours: int = 168,  # 1 Woche
    ):
        self.cache_dir = cache_dir or Path.home() / ".glitchhunter" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_mb = max_size_mb
        self.default_ttl = timedelta(hours=default_ttl_hours)
        self._lock = threading.RLock()
        
        # SQLite für Metadaten
        self.db_path = self.cache_dir / "cache.db"
        self._init_db()
        
        # Stats
        self.hits = 0
        self.misses = 0
        
        logger.info(f"SymbolCache initialisiert: {self.cache_dir}")
    
    def _init_db(self) -> None:
        """Initialisiert die SQLite-Datenbank."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    mtime REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    accessed_at TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    size_bytes INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_accessed ON cache_entries(accessed_at)
            """)
            conn.commit()
    
    def get(self, file_path: str, content: str) -> Optional[Any]:
        """
        Holt gecachte Daten für eine Datei.
        
        Args:
            file_path: Pfad zur Datei
            content: Aktueller Datei-Inhalt für Hash-Vergleich
            
        Returns:
            Gecachte Daten oder None
        """
        key = self._make_key(file_path)
        current_hash = self._hash_content(content)
        
        with self._lock:
            entry = self._get_entry(key)
            
            if entry is None:
                self.misses += 1
                logger.debug(f"Cache-Miss: {file_path}")
                return None
            
            # Prüfe ob Datei geändert wurde
            if entry.file_hash != current_hash:
                self.misses += 1
                logger.debug(f"Cache-Stale (hash mismatch): {file_path}")
                self._delete_entry(key)
                return None
            
            # Prüfe TTL
            if datetime.utcnow() - entry.created_at > self.default_ttl:
                self.misses += 1
                logger.debug(f"Cache-Expired: {file_path}")
                self._delete_entry(key)
                return None
            
            # Lade Daten
            data = self._load_data(key)
            if data is not None:
                self.hits += 1
                self._update_access(key)
                logger.debug(f"Cache-Hit: {file_path}")
            else:
                self.misses += 1
            
            return data
    
    def set(
        self,
        file_path: str,
        content: str,
        data: Any,
        mtime: Optional[float] = None,
    ) -> bool:
        """
        Speichert Daten im Cache.
        
        Args:
            file_path: Pfad zur Datei
            content: Datei-Inhalt für Hash
            data: Zu cachende Daten
            mtime: Optional modification time
            
        Returns:
            True wenn erfolgreich
        """
        key = self._make_key(file_path)
        file_hash = self._hash_content(content)
        
        if mtime is None:
            try:
                mtime = Path(file_path).stat().st_mtime
            except:
                mtime = 0.0
        
        with self._lock:
            # Speichere Daten
            if not self._save_data(key, data):
                return False
            
            # Speichere Metadaten
            entry = CacheEntry(
                key=key,
                data=None,  # Nicht in DB speichern
                file_hash=file_hash,
                file_path=file_path,
                mtime=mtime,
            )
            self._store_entry(entry)
            
            # Cleanup wenn nötig
            self._maybe_evict()
        
        logger.debug(f"Cache-Set: {file_path}")
        return True
    
    def invalidate(self, file_path: str) -> bool:
        """Invalidiert einen Cache-Eintrag."""
        key = self._make_key(file_path)
        with self._lock:
            return self._delete_entry(key)
    
    def invalidate_all(self) -> int:
        """Leert den kompletten Cache."""
        with self._lock:
            count = 0
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT key FROM cache_entries")
                for row in cursor.fetchall():
                    key = row[0]
                    data_path = self._data_path(key)
                    if data_path.exists():
                        data_path.unlink()
                    count += 1
                conn.execute("DELETE FROM cache_entries")
                conn.commit()
            
            self.hits = 0
            self.misses = 0
            logger.info(f"Cache geleert: {count} Einträge entfernt")
            return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Gibt Cache-Statistiken zurück."""
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*), SUM(size_bytes) FROM cache_entries")
                row = cursor.fetchone()
                entry_count = row[0] or 0
                total_size = row[1] or 0
            
            return {
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": hit_rate,
                "entry_count": entry_count,
                "total_size_mb": total_size / (1024 * 1024),
                "max_size_mb": self.max_size_mb,
                "cache_dir": str(self.cache_dir),
            }
    
    def _make_key(self, file_path: str) -> str:
        """Erstellt einen Cache-Key aus Dateipfad."""
        return hashlib.sha256(file_path.encode()).hexdigest()[:32]
    
    def _hash_content(self, content: str) -> str:
        """Erstellt einen Hash des Datei-Inhalts."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _data_path(self, key: str) -> Path:
        """Gibt den Pfad zur Datendatei zurück."""
        # Verteile auf Unterverzeichnisse für bessere Performance
        subdir = key[:2]
        (self.cache_dir / subdir).mkdir(exist_ok=True)
        return self.cache_dir / subdir / f"{key}.pkl"
    
    def _load_data(self, key: str) -> Optional[Any]:
        """Lädt Daten aus Datei."""
        path = self._data_path(key)
        if not path.exists():
            return None
        try:
            with open(path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.warning(f"Fehler beim Laden von Cache-Daten: {e}")
            return None
    
    def _save_data(self, key: str, data: Any) -> bool:
        """Speichert Daten in Datei."""
        path = self._data_path(key)
        try:
            with open(path, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            return True
        except Exception as e:
            logger.warning(f"Fehler beim Speichern von Cache-Daten: {e}")
            return False
    
    def _get_entry(self, key: str) -> Optional[CacheEntry]:
        """Holt einen Eintrag aus der DB."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT key, file_hash, file_path, mtime, created_at, 
                          accessed_at, access_count 
                   FROM cache_entries WHERE key = ?""",
                (key,)
            )
            row = cursor.fetchone()
            
            if row is None:
                return None
            
            return CacheEntry(
                key=row[0],
                data=None,
                file_hash=row[1],
                file_path=row[2],
                mtime=row[3],
                created_at=datetime.fromisoformat(row[4]),
                accessed_at=datetime.fromisoformat(row[5]),
                access_count=row[6],
            )
    
    def _store_entry(self, entry: CacheEntry) -> None:
        """Speichert einen Eintrag in der DB."""
        data_path = self._data_path(entry.key)
        size_bytes = data_path.stat().st_size if data_path.exists() else 0
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO cache_entries 
                   (key, file_hash, file_path, mtime, created_at, accessed_at, access_count, size_bytes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry.key,
                    entry.file_hash,
                    entry.file_path,
                    entry.mtime,
                    entry.created_at.isoformat(),
                    entry.accessed_at.isoformat(),
                    entry.access_count,
                    size_bytes,
                )
            )
            conn.commit()
    
    def _update_access(self, key: str) -> None:
        """Aktualisiert Zugriffsstatistiken."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """UPDATE cache_entries 
                   SET accessed_at = ?, access_count = access_count + 1
                   WHERE key = ?""",
                (datetime.utcnow().isoformat(), key)
            )
            conn.commit()
    
    def _delete_entry(self, key: str) -> bool:
        """Löscht einen Eintrag."""
        data_path = self._data_path(key)
        if data_path.exists():
            data_path.unlink()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
            conn.commit()
            return cursor.rowcount > 0
    
    def _maybe_evict(self) -> None:
        """Führt LRU-Eviction durch wenn nötig."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT SUM(size_bytes) FROM cache_entries")
            total_size = cursor.fetchone()[0] or 0
            max_bytes = self.max_size_mb * 1024 * 1024
            
            if total_size <= max_bytes:
                return
            
            # Entferne älteste Einträge
            to_remove = int(total_size - max_bytes * 0.8)  # Ziel: 80% der Max-Größe
            cursor = conn.execute(
                """SELECT key, size_bytes FROM cache_entries 
                   ORDER BY accessed_at ASC LIMIT 100"""
            )
            
            removed = 0
            for row in cursor.fetchall():
                key, size = row
                self._delete_entry(key)
                removed += size
                if removed >= to_remove:
                    break
            
            logger.info(f"LRU-Eviction: {removed / (1024*1024):.1f} MB entfernt")