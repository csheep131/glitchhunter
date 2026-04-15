"""Report Manager - Verwaltet Reports pro Projekt."""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ReportCandidate:
    """Ein Kandidat aus dem Report."""
    file_path: str
    total_score: float
    factors: Dict[str, Any]
    complexity: int = 0
    hotspot_score: float = 0.0

    @property
    def display_name(self) -> str:
        """Kurzer Dateiname für Anzeige."""
        return Path(self.file_path).name


@dataclass
class ProjectReport:
    """Ein Report für ein spezifisches Projekt."""

    report_id: str
    project_name: str
    project_path: Path
    created_at: datetime
    report_type: str  # 'scan', 'fix', 'security', 'full'
    json_path: Optional[Path] = None
    markdown_path: Optional[Path] = None
    summary: Dict[str, Any] = field(default_factory=dict)

    # Neue Felder für GlitchHunter-Format
    findings_count: int = 0
    candidates: List[ReportCandidate] = field(default_factory=list)
    verified_patches_count: int = 0
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    state: str = "unknown"

    @property
    def display_name(self) -> str:
        """Anzeigename für den Report."""
        date_str = self.created_at.strftime("%Y-%m-%d %H:%M")
        return f"{self.project_name} - {self.report_type.upper()} ({date_str})"

    @property
    def candidates_analyzed(self) -> int:
        """Anzahl analysierter Kandidaten (aus Summary)."""
        return self.summary.get("candidates_analyzed", len(self.candidates))

    @property
    def hypotheses_generated(self) -> int:
        """Anzahl generierter Hypothesen."""
        return self.summary.get("hypotheses_generated", 0)

    @property
    def patches_generated(self) -> int:
        """Anzahl generierter Patches."""
        return self.summary.get("patches_generated", 0)

    @property
    def short_summary(self) -> str:
        """Kurze Zusammenfassung."""
        candidates = self.candidates_analyzed
        patches = self.verified_patches_count or self.patches_generated
        hypotheses = self.hypotheses_generated

        if patches > 0:
            return f"🔧 {patches} Patches | 📊 {hypotheses} Hypothesen"
        elif hypotheses > 0:
            return f"💡 {hypotheses} Hypothesen | 📁 {candidates} Kandidaten"
        elif candidates > 0:
            return f"📁 {candidates} Kandidaten analysiert"
        else:
            return f"📊 Scan abgeschlossen"

    @property
    def status_icon(self) -> str:
        """Status-Icon basierend auf Report-Ergebnissen."""
        if self.verified_patches_count > 0 or self.patches_generated > 0:
            return "✅"
        elif self.hypotheses_generated > 0:
            return "💡"
        elif self.findings_count > 0 or self.candidates_analyzed > 0:
            return "📊"
        return "📝"

    @property
    def is_fixable(self) -> bool:
        """Kann ein Fix-Lauf gestartet werden?"""
        has_candidates = self.candidates_analyzed > 0 or len(self.candidates) > 0
        no_patches = self.verified_patches_count == 0 and self.patches_generated == 0
        return has_candidates and no_patches


class ReportManager:
    """
    Verwaltet alle Reports für GlitchHunter.

    Ordnerstruktur:
        reports/
        ├── <project_name>/
        │   ├── report_20250414_120000.json
        │   ├── report_20250414_120000.md
        │   └── latest.json (Symlink zum neuesten)
        └── index.json (Index aller Reports)

    Unterstützt auch flache Struktur:
        reports/
        ├── <name>_scan_YYYYMMDD_HHMMSS.json
        └── <name>_scan_YYYYMMDD_HHMMSS.md
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialisiert den Report Manager.

        Args:
            base_dir: Basis-Verzeichnis für Reports (default: ./reports)
        """
        self.base_dir = base_dir or Path("reports")
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Index laden
        self.index_path = self.base_dir / "index.json"
        self._load_index()

        logger.info(f"ReportManager initialisiert: {self.base_dir}")

    def _load_index(self):
        """Lädt den Report-Index."""
        if self.index_path.exists():
            try:
                with open(self.index_path, 'r') as f:
                    self.index = json.load(f)
            except Exception as e:
                logger.warning(f"Konnte Index nicht laden: {e}")
                self.index = {"reports": [], "version": "1.0"}
        else:
            self.index = {"reports": [], "version": "1.0"}

    def _save_index(self):
        """Speichert den Report-Index."""
        try:
            with open(self.index_path, 'w') as f:
                json.dump(self.index, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Konnte Index nicht speichern: {e}")

    def _parse_timestamp(self, filename: str) -> Optional[datetime]:
        """Parst Zeitstempel aus Dateinamen."""
        # Format: *_YYYYMMDD_HHMMSS.json
        match = re.search(r'(\d{8})_(\d{6})', filename)
        if match:
            try:
                return datetime.strptime(match.group(0), "%Y%m%d_%H%M%S")
            except ValueError:
                pass
        return None

    def _parse_report_type(self, filename: str) -> str:
        """Parst Report-Typ aus Dateinamen."""
        if "_fix_" in filename or "_fixed_" in filename:
            return "fix"
        elif "_scan_" in filename or "_scanned_" in filename:
            return "scan"
        elif "_security_" in filename:
            return "security"
        return "scan"

    def _extract_project_name(self, filename: str) -> str:
        """Extrahiert Projektnamen aus Dateinamen."""
        # Format: <name>_<type>_YYYYMMDD_HHMMSS.json
        parts = filename.split('_')
        if len(parts) >= 2:
            # Remove timestamp parts
            for i, part in enumerate(parts):
                if re.match(r'\d{8}', part):
                    return '_'.join(parts[:i])
        return Path(filename).stem

    def _load_glitchhunter_report(self, json_path: Path) -> Optional[Dict[str, Any]]:
        """Lädt ein GlitchHunter-Format Report."""
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)

            # Parse candidates
            candidates = []
            for c in data.get("candidates", []):
                factors = c.get("factors", {})
                candidates.append(ReportCandidate(
                    file_path=c.get("file_path", ""),
                    total_score=c.get("total_score", 0.0),
                    factors=factors,
                    complexity=factors.get("complexity", 0),
                    hotspot_score=factors.get("hotspot", 0.0)
                ))

            return {
                "project_name": data.get("project_name", "unknown"),
                "repo_path": data.get("repo_path", ""),
                "timestamp": data.get("timestamp", ""),
                "findings_count": data.get("findings_count", 0),
                "verified_patches_count": data.get("verified_patches_count", 0),
                "candidates": candidates,
                "errors": data.get("errors", []),
                "metadata": data.get("metadata", {}),
                "summary": data.get("summary", {}),
                "state": data.get("metadata", {}).get("analysis_complete", False) and "finalizer" or "unknown",
            }
        except Exception as e:
            logger.warning(f"Konnte Report nicht parsen {json_path}: {e}")
            return None

    def scan_directory(self) -> List[ProjectReport]:
        """
        Scannt das Reports-Verzeichnis nach allen Reports.

        Struktur:
            reports/
              <projektname>/
                scans/
                  *_scan_*.json
                patches/
                  *_fix_*.json

        Returns:
            Liste von ProjectReport Objekten
        """
        reports = []

        # Durchsuche Projekt-Verzeichnisse
        for project_dir in self.base_dir.iterdir():
            if not project_dir.is_dir():
                continue

            project_name = project_dir.name

            # 1. Suche in scans/
            scans_dir = project_dir / "scans"
            if scans_dir.exists():
                for json_file in scans_dir.glob("*_scan_*.json"):
                    report = self._parse_report_file(json_file, project_name, "scan")
                    if report:
                        reports.append(report)

            # 2. Suche in patches/
            patches_dir = project_dir / "patches"
            if patches_dir.exists():
                for json_file in patches_dir.glob("*_fix_*.json"):
                    report = self._parse_report_file(json_file, project_name, "fix")
                    if report:
                        reports.append(report)

            # 3. Suche direkt im Projektverzeichnis (alte Struktur)
            for json_file in project_dir.glob("report_*.json"):
                report = self._parse_report_file(json_file, project_name, "scan")
                if report:
                    reports.append(report)

        # Sortiere nach Datum (neueste zuerst)
        reports.sort(key=lambda r: r.created_at, reverse=True)
        return reports

    def _parse_report_file(self, json_file: Path, project_name: str, default_type: str) -> Optional[ProjectReport]:
        """Parst eine einzelne Report-Datei."""
        timestamp = self._parse_timestamp(json_file.name)
        if not timestamp:
            return None

        report_type = self._parse_report_type(json_file.name)
        if report_type == "scan" and default_type == "fix":
            report_type = "fix"

        data = self._load_glitchhunter_report(json_file)
        if not data:
            return None

        # Suche zugehörige Markdown-Datei
        md_path = json_file.with_suffix('.md')
        if not md_path.exists():
            md_path = None

        return ProjectReport(
            report_id=f"{project_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}",
            project_name=data.get("project_name", project_name),
            project_path=Path(data.get("repo_path", ".")),
            created_at=timestamp,
            report_type=report_type,
            json_path=json_file,
            markdown_path=md_path,
            summary=data.get("summary", {}),
            findings_count=data.get("findings_count", 0),
            candidates=data.get("candidates", []),
            verified_patches_count=data.get("verified_patches_count", 0),
            errors=data.get("errors", []),
            metadata=data.get("metadata", {}),
            state=data.get("state", "unknown"),
        )

    def _get_project_name(self, project_path: Path) -> str:
        """Extrahiert Projektnamen aus Pfad."""
        # Verwende letzten Ordnernamen oder 'unknown'
        name = project_path.name or project_path.parent.name
        # Sanitize für Dateisystem
        return "".join(c for c in name if c.isalnum() or c in '-_').lower() or "project"

    def _get_project_dir(self, project_name: str) -> Path:
        """Gibt Projekt-Report-Verzeichnis zurück."""
        project_dir = self.base_dir / project_name
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def create_report_slot(
        self,
        project_path: Path,
        report_type: str = "scan"
    ) -> Dict[str, Path]:
        """
        Erstellt Pfade für einen neuen Report.

        Args:
            project_path: Pfad zum Projekt
            report_type: Typ des Reports

        Returns:
            Dict mit Pfaden für JSON und Markdown
        """
        project_name = self._get_project_name(project_path)
        project_dir = self._get_project_dir(project_name)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_id = f"{project_name}_{timestamp}"

        json_path = project_dir / f"report_{timestamp}.json"
        md_path = project_dir / f"report_{timestamp}.md"

        return {
            "report_id": report_id,
            "project_name": project_name,
            "project_dir": project_dir,
            "json_path": json_path,
            "markdown_path": md_path,
            "timestamp": timestamp,
        }

    def register_report(
        self,
        report_id: str,
        project_name: str,
        project_path: Path,
        report_type: str,
        json_path: Path,
        markdown_path: Path,
        summary: Dict[str, Any]
    ) -> ProjectReport:
        """
        Registriert einen fertigen Report.

        Args:
            report_id: Eindeutige Report-ID
            project_name: Name des Projekts
            project_path: Pfad zum Projekt
            report_type: Typ des Reports
            json_path: Pfad zur JSON-Datei
            markdown_path: Pfad zur Markdown-Datei
            summary: Zusammenfassung

        Returns:
            ProjectReport Objekt
        """
        # Zum Index hinzufügen
        report_entry = {
            "report_id": report_id,
            "project_name": project_name,
            "project_path": str(project_path),
            "report_type": report_type,
            "created_at": datetime.now().isoformat(),
            "json_path": str(json_path),
            "markdown_path": str(markdown_path),
            "summary": summary,
        }

        self.index["reports"].append(report_entry)
        self._save_index()

        # Latest-Symlink aktualisieren
        self._update_latest_symlink(project_name, json_path, markdown_path)

        logger.info(f"Report registriert: {report_id}")

        return ProjectReport(
            report_id=report_id,
            project_name=project_name,
            project_path=project_path,
            created_at=datetime.now(),
            report_type=report_type,
            json_path=json_path,
            markdown_path=markdown_path,
            summary=summary,
        )

    def _update_latest_symlink(
        self,
        project_name: str,
        json_path: Path,
        markdown_path: Path
    ):
        """Aktualisiert 'latest' Symlinks."""
        project_dir = self._get_project_dir(project_name)

        try:
            latest_json = project_dir / "latest.json"
            latest_md = project_dir / "latest.md"

            # Remove old symlinks
            if latest_json.is_symlink() or latest_json.exists():
                latest_json.unlink()
            if latest_md.is_symlink() or latest_md.exists():
                latest_md.unlink()

            # Create new symlinks (relative)
            latest_json.symlink_to(json_path.name)
            latest_md.symlink_to(markdown_path.name)

        except Exception as e:
            logger.warning(f"Konnte latest-Symlink nicht erstellen: {e}")

    def get_reports_for_project(self, project_path: Path) -> List[ProjectReport]:
        """
        Gibt alle Reports für ein Projekt zurück.

        Args:
            project_path: Pfad zum Projekt

        Returns:
            Liste von ProjectReport Objekten
        """
        all_reports = self.scan_directory()
        project_name = self._get_project_name(project_path)

        return [
            r for r in all_reports
            if r.project_name == project_name or
            str(r.project_path) == str(project_path)
        ]

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """
        Gibt eine Liste aller Projekte mit Reports zurück.

        Returns:
            Liste mit Projekt-Infos
        """
        reports = self.scan_directory()
        projects = {}

        for report in reports:
            name = report.project_name
            if name not in projects:
                projects[name] = {
                    "name": name,
                    "path": str(report.project_path),
                    "report_count": 0,
                    "latest_report": None,
                    "total_candidates": 0,
                    "total_patches": 0,
                }

            projects[name]["report_count"] += 1
            projects[name]["total_candidates"] += len(report.candidates)
            projects[name]["total_patches"] += report.verified_patches_count

            # Track latest
            if (not projects[name]["latest_report"] or
                report.created_at > projects[name]["latest_report"]["created_at"]):
                projects[name]["latest_report"] = report

        return list(projects.values())

    def get_report_by_id(self, report_id: str) -> Optional[ProjectReport]:
        """
        Gibt einen Report anhand seiner ID zurück.

        Args:
            report_id: Report-ID

        Returns:
            ProjectReport oder None
        """
        all_reports = self.scan_directory()
        for report in all_reports:
            if report.report_id == report_id:
                return report
        return None

    def load_report_content(self, report: ProjectReport) -> Optional[Dict[str, Any]]:
        """
        Lädt den Inhalt eines Reports.

        Args:
            report: ProjectReport Objekt

        Returns:
            Report-Inhalt als Dict
        """
        if not report.json_path or not report.json_path.exists():
            return None

        try:
            with open(report.json_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Konnte Report nicht laden: {e}")
            return None

    def load_report_markdown(self, report: ProjectReport) -> Optional[str]:
        """
        Lädt den Markdown-Inhalt eines Reports.

        Args:
            report: ProjectReport Objekt

        Returns:
            Markdown-Inhalt als String
        """
        if not report.markdown_path or not report.markdown_path.exists():
            return None

        try:
            with open(report.markdown_path, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Konnte Markdown nicht laden: {e}")
            return None

    def get_latest_report(self, project_path: Path) -> Optional[ProjectReport]:
        """
        Gibt den neuesten Report für ein Projekt zurück.

        Args:
            project_path: Pfad zum Projekt

        Returns:
            ProjectReport oder None
        """
        reports = self.get_reports_for_project(project_path)
        return reports[0] if reports else None

    def delete_report(self, report_id: str) -> bool:
        """
        Löscht einen Report.

        Args:
            report_id: Report-ID

        Returns:
            True wenn erfolgreich
        """
        report = self.get_report_by_id(report_id)
        if not report:
            return False

        try:
            # Dateien löschen
            if report.json_path and report.json_path.exists():
                report.json_path.unlink()
            if report.markdown_path and report.markdown_path.exists():
                report.markdown_path.unlink()

            # Aus Index entfernen
            self.index["reports"] = [
                r for r in self.index["reports"]
                if r.get("report_id") != report_id
            ]
            self._save_index()

            logger.info(f"Report gelöscht: {report_id}")
            return True

        except Exception as e:
            logger.error(f"Konnte Report nicht löschen: {e}")
            return False

    def get_scan_candidates(self, report: ProjectReport) -> List[Tuple[str, float]]:
        """
        Gibt Kandidaten für Fix-Lauf zurück.

        Args:
            report: ProjectReport

        Returns:
            Liste von (file_path, score) Tupeln
        """
        return [
            (c.file_path, c.total_score)
            for c in report.candidates
        ]


# Singleton-Instanz für globale Verwendung
_report_manager: Optional[ReportManager] = None


def get_report_manager(base_dir: Optional[Path] = None) -> ReportManager:
    """Gibt globale ReportManager-Instanz zurück."""
    global _report_manager
    if _report_manager is None:
        _report_manager = ReportManager(base_dir)
    return _report_manager
