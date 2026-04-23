"""
History Manager für GlitchHunter Web-UI.

Verwaltet Verlauf aller Analysen und Probleme:
- SQLite-Speicherung für Persistenz
- Aggregation für Statistiken
- Cleanup für alte Einträge
- Vergleichsfunktionen

Features:
- Analyse-History (Jobs)
- Problem-History
- Statistik-Aggregation
- Auto-Cleanup
"""

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class HistoryManager:
    """
    Manager für Analyse- und Problem-History.
    
    Features:
    - SQLite-Speicherung
    - Pagination
    - Filterung
    - Statistik-Aggregation
    - Auto-Cleanup
    
    Usage:
        manager = HistoryManager()
        manager.initialize()
        manager.add_analysis_entry(...)
        history = manager.get_history(...)
    """
    
    def __init__(self, db_path: str = "history.db"):
        """
        Initialisiert History-Manager.
        
        Args:
            db_path: Pfad zur SQLite-Datei
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"HistoryManager initialisiert: {self.db_path}")
    
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
        Initialisiert Datenbank-Tabellen.
        """
        logger.info("Initialisiere History-Tabellen...")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Analyse-History Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL UNIQUE,
                    repo_path TEXT NOT NULL,
                    stack TEXT NOT NULL DEFAULT 'stack_b',
                    status TEXT NOT NULL,
                    findings_count INTEGER DEFAULT 0,
                    critical_count INTEGER DEFAULT 0,
                    high_count INTEGER DEFAULT 0,
                    medium_count INTEGER DEFAULT 0,
                    low_count INTEGER DEFAULT 0,
                    duration_seconds REAL,
                    parallelization_factor REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_analysis_created_at 
                ON analysis_history(created_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_analysis_status 
                ON analysis_history(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_analysis_repo 
                ON analysis_history(repo_path)
            """)
            
            # Problem-History Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS problem_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_id TEXT NOT NULL UNIQUE,
                    prompt TEXT NOT NULL,
                    repo_path TEXT,
                    classification TEXT,
                    status TEXT NOT NULL,
                    with_ml_prediction INTEGER DEFAULT 1,
                    with_code_analysis INTEGER DEFAULT 1,
                    auto_fix INTEGER DEFAULT 0,
                    duration_seconds REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_problem_created_at 
                ON problem_history(created_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_problem_status 
                ON problem_history(status)
            """)
            
            # Report-History Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS report_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id TEXT NOT NULL UNIQUE,
                    job_id TEXT,
                    problem_id TEXT,
                    format TEXT NOT NULL,
                    file_size INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_report_created_at 
                ON report_history(created_at)
            """)
            
            # Statistics View (für schnelle Aggregation)
            cursor.execute("""
                CREATE VIEW IF NOT EXISTS analysis_stats AS
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as total_analyses,
                    SUM(findings_count) as total_findings,
                    AVG(duration_seconds) as avg_duration,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count
                FROM analysis_history
                GROUP BY DATE(created_at)
            """)
            
            logger.info("History-Tabellen erfolgreich initialisiert")
    
    # ============== Analysis History ==============
    
    def add_analysis_entry(
        self,
        job_id: str,
        repo_path: str,
        status: str,
        stack: str = "stack_b",
        findings_count: int = 0,
        critical_count: int = 0,
        high_count: int = 0,
        medium_count: int = 0,
        low_count: int = 0,
        duration_seconds: float = 0,
        parallelization_factor: float = 1.0,
    ):
        """
        Fügt Analyse-Eintrag hinzu.
        
        Args:
            job_id: Job-ID
            repo_path: Repository-Pfad
            status: Status (pending, running, completed, failed)
            stack: Hardware-Stack
            findings_count: Anzahl Findings
            critical_count: Critical Findings
            high_count: High Findings
            medium_count: Medium Findings
            low_count: Low Findings
            duration_seconds: Dauer in Sekunden
            parallelization_factor: Parallelisierungs-Faktor
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO analysis_history 
                   (job_id, repo_path, stack, status, findings_count, 
                    critical_count, high_count, medium_count, low_count,
                    duration_seconds, parallelization_factor, 
                    created_at, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    job_id, repo_path, stack, status,
                    findings_count, critical_count, high_count, medium_count, low_count,
                    duration_seconds, parallelization_factor,
                    datetime.now(),
                    datetime.now() if status in ["completed", "failed"] else None,
                )
            )
        
        logger.debug(f"Analysis-Eintrag hinzugefügt: {job_id}")
    
    def get_analysis_history(
        self,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[str] = None,
        repo_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Holt Analyse-History.
        
        Args:
            limit: Limit
            offset: Offset
            status_filter: Status-Filter
            repo_filter: Repository-Filter
            
        Returns:
            Liste von Einträgen
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM analysis_history WHERE 1=1"
            params = []
            
            if status_filter:
                query += " AND status = ?"
                params.append(status_filter)
            
            if repo_filter:
                query += " AND repo_path LIKE ?"
                params.append(f"%{repo_filter}%")
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def get_analysis_entry(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Holt einzelnen Analyse-Eintrag.
        
        Args:
            job_id: Job-ID
            
        Returns:
            Eintrag oder None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM analysis_history WHERE job_id = ?",
                (job_id,)
            )
            row = cursor.fetchone()
        
        return dict(row) if row else None
    
    def delete_analysis_entry(self, job_id: str):
        """
        Löscht Analyse-Eintrag.
        
        Args:
            job_id: Job-ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM analysis_history WHERE job_id = ?",
                (job_id,)
            )
        
        logger.debug(f"Analysis-Eintrag gelöscht: {job_id}")
    
    # ============== Problem History ==============
    
    def add_problem_entry(
        self,
        problem_id: str,
        prompt: str,
        status: str,
        repo_path: Optional[str] = None,
        classification: Optional[str] = None,
        with_ml_prediction: bool = True,
        with_code_analysis: bool = True,
        auto_fix: bool = False,
        duration_seconds: float = 0,
    ):
        """
        Fügt Problem-Eintrag hinzu.
        
        Args:
            problem_id: Problem-ID
            prompt: Prompt-Text
            status: Status
            repo_path: Repository-Pfad
            classification: Klassifikation
            with_ml_prediction: ML Prediction verwendet
            with_code_analysis: Code-Analyse verwendet
            auto_fix: Auto-Fix verwendet
            duration_seconds: Dauer in Sekunden
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO problem_history 
                   (problem_id, prompt, repo_path, classification, status,
                    with_ml_prediction, with_code_analysis, auto_fix,
                    duration_seconds, created_at, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    problem_id, prompt, repo_path, classification, status,
                    1 if with_ml_prediction else 0,
                    1 if with_code_analysis else 0,
                    1 if auto_fix else 0,
                    duration_seconds,
                    datetime.now(),
                    datetime.now() if status in ["completed", "failed"] else None,
                )
            )
        
        logger.debug(f"Problem-Eintrag hinzugefügt: {problem_id}")
    
    def get_problem_history(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Holt Problem-History.
        
        Args:
            limit: Limit
            offset: Offset
            
        Returns:
            Liste von Einträgen
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM problem_history 
                   ORDER BY created_at DESC 
                   LIMIT ? OFFSET ?""",
                (limit, offset)
            )
            rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    # ============== Report History ==============
    
    def add_report_entry(
        self,
        report_id: str,
        format: str,
        job_id: Optional[str] = None,
        problem_id: Optional[str] = None,
        file_size: int = 0,
    ):
        """
        Fügt Report-Eintrag hinzu.
        
        Args:
            report_id: Report-ID
            format: Format (json, markdown, html)
            job_id: Job-ID
            problem_id: Problem-ID
            file_size: Dateigröße in Bytes
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO report_history 
                   (report_id, job_id, problem_id, format, file_size, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (report_id, job_id, problem_id, format, file_size, datetime.now())
            )
        
        logger.debug(f"Report-Eintrag hinzugefügt: {report_id}")
    
    def get_report_history(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Holt Report-History.
        
        Args:
            limit: Limit
            offset: Offset
            
        Returns:
            Liste von Einträgen
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM report_history 
                   ORDER BY created_at DESC 
                   LIMIT ? OFFSET ?""",
                (limit, offset)
            )
            rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    # ============== Statistics ==============
    
    def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Holt Statistik für letzte X Tage.
        
        Args:
            days: Anzahl Tage
            
        Returns:
            Statistik-Dict
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Analyse-Statistiken
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_analyses,
                    SUM(findings_count) as total_findings,
                    AVG(duration_seconds) as avg_duration,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM analysis_history
                WHERE created_at >= datetime('now', '-' || ? || ' days')
            """, (days,))
            analysis_stats = dict(cursor.fetchone())
            
            # Problem-Statistiken
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_problems,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as solved,
                    SUM(CASE WHEN auto_fix = 1 THEN 1 ELSE 0 END) as auto_fixed
                FROM problem_history
                WHERE created_at >= datetime('now', '-' || ? || ' days')
            """, (days,))
            problem_stats = dict(cursor.fetchone())
            
            # Report-Statistiken
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_reports,
                    format,
                    COUNT(*) as count
                FROM report_history
                WHERE created_at >= datetime('now', '-' || ? || ' days')
                GROUP BY format
            """, (days,))
            report_stats = {row["format"]: row["count"] for row in cursor.fetchall()}
            
            return {
                "period_days": days,
                "analysis": analysis_stats,
                "problems": problem_stats,
                "reports": report_stats,
            }
    
    def get_daily_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Holt tägliche Statistiken.
        
        Args:
            days: Anzahl Tage
            
        Returns:
            Liste von täglichen Statistiken
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM analysis_stats
                WHERE date >= date('now', '-' || ? || ' days')
                ORDER BY date DESC
            """, (days,))
            rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    # ============== Cleanup ==============
    
    def cleanup(self, older_than_days: int = 90):
        """
        Bereinigt alte Einträge.
        
        Args:
            older_than_days: Lösche Einträge älter als X Tage
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Alte Analyse-Einträge löschen
            cursor.execute("""
                DELETE FROM analysis_history
                WHERE created_at < datetime('now', '-' || ? || ' days')
            """, (older_than_days,))
            analysis_deleted = cursor.rowcount
            
            # Alte Problem-Einträge löschen
            cursor.execute("""
                DELETE FROM problem_history
                WHERE created_at < datetime('now', '-' || ? || ' days')
            """, (older_than_days,))
            problem_deleted = cursor.rowcount
            
            # Alte Report-Einträge löschen
            cursor.execute("""
                DELETE FROM report_history
                WHERE created_at < datetime('now', '-' || ? || ' days')
            """, (older_than_days,))
            report_deleted = cursor.rowcount
            
            logger.info(
                f"Cleanup abgeschlossen: "
                f"{analysis_deleted} Analysen, "
                f"{problem_deleted} Probleme, "
                f"{report_deleted} Reports gelöscht"
            )
    
    def clear_all(self):
        """
        Löscht alle Einträge.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM analysis_history")
            cursor.execute("DELETE FROM problem_history")
            cursor.execute("DELETE FROM report_history")
        
        logger.info("Alle History-Einträge gelöscht")


# ============== Globale Instanz ==============

_history_manager: Optional[HistoryManager] = None


def get_history_manager() -> HistoryManager:
    """
    Returns globale HistoryManager-Instanz.
    
    Returns:
        HistoryManager
    """
    global _history_manager
    if _history_manager is None:
        _history_manager = HistoryManager()
        _history_manager.initialize()
    return _history_manager
