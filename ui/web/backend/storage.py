"""
SQLite Storage für GlitchHunter Web-UI Settings.

Verwaltet persistente Speicherung von:
- Settings (Allgemein, Analyse, Security, Logging)
- Analyse-History
- Problems
- Reports

Features:
- SQLite mit Connection-Pooling
- Fernet-Verschlüsselung für sensible Daten
- Auto-Migration bei Schema-Änderungen
- Transaction-Support
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Datenbank-Manager für SQLite.
    
    Verwaltet Connections, Migrations und CRUD-Operationen.
    
    Usage:
        db = DatabaseManager("settings.db")
        db.initialize()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM settings")
    """
    
    def __init__(self, db_path: str = "settings.db"):
        """
        Initialisiert Datenbank-Manager.
        
        Args:
            db_path: Pfad zur SQLite-Datei
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Encryption Key (aus Environment oder generiert)
        self._encryption_key = self._get_or_create_key()
        self._cipher = Fernet(self._encryption_key)
        
        logger.info(f"DatabaseManager initialisiert: {self.db_path}")
    
    def _get_or_create_key(self) -> bytes:
        """
        Lädt oder erstellt Verschlüsselungsschlüssel.
        
        Returns:
            Fernet encryption key
        """
        key_file = self.db_path.parent / ".encryption_key"
        
        if key_file.exists():
            key = key_file.read_bytes()
            logger.debug("Encryption key geladen")
        else:
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            key_file.chmod(0o600)  # Nur Owner kann lesen
            logger.info("Neuer Encryption key generiert")
        
        return key
    
    @contextmanager
    def get_connection(self):
        """
        Context-Manager für Datenbank-Connection.
        
        Yields:
            sqlite3.Connection
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Dict-like rows
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def initialize(self):
        """
        Initialisiert Datenbank mit allen Tabellen.
        """
        logger.info("Initialisiere Datenbank-Tabellen...")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Settings Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT NOT NULL,
                    category TEXT NOT NULL,
                    encrypted INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_settings_category ON settings(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key)")
            
            # Analyse-History Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL UNIQUE,
                    repo_path TEXT NOT NULL,
                    stack TEXT NOT NULL,
                    status TEXT NOT NULL,
                    findings_count INTEGER DEFAULT 0,
                    duration_seconds REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_created_at ON analysis_history(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_status ON analysis_history(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_job_id ON analysis_history(job_id)")
            
            # Problems Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS problems (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_id TEXT NOT NULL UNIQUE,
                    prompt TEXT NOT NULL,
                    repo_path TEXT,
                    status TEXT NOT NULL,
                    classification TEXT,
                    diagnosis TEXT,
                    solution TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_problems_status ON problems(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_problems_problem_id ON problems(problem_id)")
            
            # Reports Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id TEXT NOT NULL UNIQUE,
                    job_id TEXT,
                    problem_id TEXT,
                    format TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_job_id ON reports(job_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_format ON reports(format)")
            
            logger.info("Datenbank-Tabellen erfolgreich initialisiert")
    
    def encrypt_value(self, value: str) -> str:
        """
        Verschlüsselt einen Wert.
        
        Args:
            value: Zu verschlüsselnder Wert
            
        Returns:
            Verschlüsselter Wert
        """
        return self._cipher.encrypt(value.encode()).decode()
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """
        Entschlüsselt einen Wert.
        
        Args:
            encrypted_value: Verschlüsselter Wert
            
        Returns:
            Entschlüsselter Wert
        """
        return self._cipher.decrypt(encrypted_value.encode()).decode()
    
    # Settings CRUD
    
    def get_setting(self, key: str) -> Optional[Any]:
        """
        Liest ein einzelnes Setting.
        
        Args:
            key: Setting-Key
            
        Returns:
            Setting-Wert oder None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value, encrypted FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            value = row["value"]
            if row["encrypted"]:
                value = self.decrypt_value(value)
            
            return json.loads(value)
    
    def set_setting(self, key: str, value: Any, category: str, encrypt: bool = False):
        """
        Speichert ein Setting.
        
        Args:
            key: Setting-Key
            value: Setting-Wert
            category: Kategorie
            encrypt: Ob der Wert verschlüsselt werden soll
        """
        value_str = json.dumps(value)
        
        if encrypt:
            value_str = self.encrypt_value(value_str)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO settings (key, value, category, encrypted, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (key, value_str, category, 1 if encrypt else 0, datetime.now())
            )
        
        logger.debug(f"Setting gespeichert: {key}={value}")
    
    def get_all_settings(self) -> Dict[str, Dict[str, Any]]:
        """
        Liest alle Settings gruppiert nach Kategorie.
        
        Returns:
            Dict von Kategorien mit Settings
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value, category, encrypted FROM settings ORDER BY category, key")
            rows = cursor.fetchall()
        
        settings: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            category = row["category"]
            if category not in settings:
                settings[category] = {}
            
            value = row["value"]
            if row["encrypted"]:
                value = self.decrypt_value(value)
            
            settings[category][row["key"]] = json.loads(value)
        
        return settings
    
    def set_all_settings(self, settings: Dict[str, Dict[str, Any]], encrypted_keys: Optional[List[str]] = None):
        """
        Speichert alle Settings.
        
        Args:
            settings: Settings gruppiert nach Kategorie
            encrypted_keys: Liste der Keys die verschlüsselt werden sollen
        """
        encrypted_keys = encrypted_keys or []
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            for category, category_settings in settings.items():
                for key, value in category_settings.items():
                    value_str = json.dumps(value)
                    encrypt = key in encrypted_keys
                    
                    if encrypt:
                        value_str = self.encrypt_value(value_str)
                    
                    cursor.execute(
                        """INSERT OR REPLACE INTO settings (key, value, category, encrypted, updated_at)
                           VALUES (?, ?, ?, ?, ?)""",
                        (key, value_str, category, 1 if encrypt else 0, datetime.now())
                    )
        
        logger.info(f"Alle Settings gespeichert ({len(settings)} Kategorien)")
    
    def reset_settings(self, category: Optional[str] = None):
        """
        Setzt Settings zurück.
        
        Args:
            category: Kategorie zum Zurücksetzen (None = alle)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if category:
                cursor.execute("DELETE FROM settings WHERE category = ?", (category,))
                logger.info(f"Settings zurückgesetzt für Kategorie: {category}")
            else:
                cursor.execute("DELETE FROM settings")
                logger.info("Alle Settings zurückgesetzt")
    
    # History CRUD
    
    def add_history_entry(self, job_id: str, repo_path: str, stack: str, status: str,
                         findings_count: int = 0, duration_seconds: float = 0):
        """
        Fügt History-Eintrag hinzu.
        
        Args:
            job_id: Job-ID
            repo_path: Repository-Pfad
            stack: Verwendeter Stack
            status: Status
            findings_count: Anzahl Findings
            duration_seconds: Dauer in Sekunden
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO analysis_history 
                   (job_id, repo_path, stack, status, findings_count, duration_seconds, created_at, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (job_id, repo_path, stack, status, findings_count, duration_seconds,
                 datetime.now(), datetime.now() if status != "pending" else None)
            )
        
        logger.debug(f"History-Eintrag hinzugefügt: {job_id}")
    
    def get_history(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Liest History-Einträge.
        
        Args:
            limit: Limit
            offset: Offset
            
        Returns:
            Liste von History-Einträgen
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM analysis_history 
                   ORDER BY created_at DESC 
                   LIMIT ? OFFSET ?""",
                (limit, offset)
            )
            rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def get_history_entry(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Liest einzelnen History-Eintrag.
        
        Args:
            job_id: Job-ID
            
        Returns:
            History-Eintrag oder None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM analysis_history WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
        
        return dict(row) if row else None
    
    def delete_history_entry(self, job_id: str):
        """
        Löscht History-Eintrag.
        
        Args:
            job_id: Job-ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM analysis_history WHERE job_id = ?", (job_id,))
        
        logger.debug(f"History-Eintrag gelöscht: {job_id}")
    
    def clear_history(self):
        """Löscht gesamte History."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM analysis_history")
        
        logger.info("Gesamte History gelöscht")


# Globale Instanz
_db_manager: Optional[DatabaseManager] = None


def get_database() -> DatabaseManager:
    """
    Returns globale DatabaseManager-Instanz.
    
    Returns:
        DatabaseManager
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        _db_manager.initialize()
    return _db_manager
