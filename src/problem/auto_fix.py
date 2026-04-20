"""
Auto-Fix für Problem-Solver.

Gemäß PROBLEM_SOLVER.md Phase 3.3:
- Automatische Patch-Generierung basierend auf Solution-Pfaden
- Patch-Anwendung mit Validation
- Rollback-Fähigkeit
- Integration mit bestehender Fixing-Logik
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import uuid
import json
import shutil
import logging

from .models import ProblemCase
from .solution_path import SolutionPlan, SolutionPath


logger = logging.getLogger(__name__)


class FixStatus(Enum):
    """Status eines Auto-Fix."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    BLOCKED = "blocked"


@dataclass
class FixPatch:
    """
    Beschreibt einen einzelnen Patch für ein Teilproblem.
    
    Attributes:
        id: Eindeutige Identifier für diesen Patch
        subproblem_id: Referenz zum Teilproblem
        solution_path_id: Referenz zum SolutionPath
        file_path: Pfad zur zu ändernden Datei
        original_content: Original-Inhalt vor Patch
        patched_content: Neuer Inhalt nach Patch
        diff: Diff-Darstellung der Änderung
        status: Aktueller Status des Patches
        validation_passed: True wenn Validation erfolgreich
        validation_errors: Liste von Fehlermeldungen
        rollback_available: True wenn Backup existiert
        backup_path: Pfad zum Backup
        created_at: Erstellungszeitpunkt
        applied_at: Zeitpunkt der Anwendung
    """
    
    id: str
    subproblem_id: str
    solution_path_id: str
    
    # Patch-Details
    file_path: str
    original_content: str = ""
    patched_content: str = ""
    diff: str = ""
    
    # Status
    status: FixStatus = FixStatus.PENDING
    
    # Validation
    validation_passed: bool = False
    validation_errors: List[str] = field(default_factory=list)
    
    # Rollback
    rollback_available: bool = False
    backup_path: str = ""
    
    # Metadaten
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    applied_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        """
        Konvertiert FixPatch zu Dictionary für JSON-Export.
        
        Returns:
            Dictionary mit allen FixPatch-Attributen
        """
        return {
            "id": self.id,
            "subproblem_id": self.subproblem_id,
            "solution_path_id": self.solution_path_id,
            "file_path": self.file_path,
            "original_content": self.original_content,
            "patched_content": self.patched_content,
            "diff": self.diff,
            "status": self.status.value,
            "validation_passed": self.validation_passed,
            "validation_errors": self.validation_errors,
            "rollback_available": self.rollback_available,
            "backup_path": self.backup_path,
            "created_at": self.created_at,
            "applied_at": self.applied_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "FixPatch":
        """
        Erstellt FixPatch aus Dictionary.
        
        Args:
            data: Dictionary mit FixPatch-Daten
        
        Returns:
            Neues FixPatch-Objekt
        """
        return cls(
            id=data["id"],
            subproblem_id=data["subproblem_id"],
            solution_path_id=data["solution_path_id"],
            file_path=data["file_path"],
            original_content=data.get("original_content", ""),
            patched_content=data.get("patched_content", ""),
            diff=data.get("diff", ""),
            status=FixStatus(data.get("status", "pending")),
            validation_passed=data.get("validation_passed", False),
            validation_errors=data.get("validation_errors", []),
            rollback_available=data.get("rollback_available", False),
            backup_path=data.get("backup_path", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            applied_at=data.get("applied_at"),
        )


@dataclass
class AutoFixResult:
    """
    Ergebnis einer Auto-Fix-Operation.
    
    Attributes:
        problem_id: Referenz zum Problem
        solution_plan_id: Referenz zum SolutionPlan
        patches: Liste der generierten Patches
        overall_status: Gesamt-Status der Operation
        summary: Zusammenfassung der Operation
        applied_count: Anzahl erfolgreicher Patches
        failed_count: Anzahl fehlgeschlagener Patches
        rolled_back_count: Anzahl zurückgerollter Patches
        started_at: Startzeitpunkt
        completed_at: Abschlusszeitpunkt
    """
    
    problem_id: str
    solution_plan_id: str
    
    # Patches
    patches: List[FixPatch] = field(default_factory=list)
    
    # Gesamt-Status
    overall_status: FixStatus = FixStatus.PENDING
    
    # Zusammenfassung
    summary: str = ""
    applied_count: int = 0
    failed_count: int = 0
    rolled_back_count: int = 0
    
    # Metadaten
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        """
        Konvertiert AutoFixResult zu Dictionary für JSON-Export.
        
        Returns:
            Dictionary mit allen AutoFixResult-Attributen
        """
        return {
            "problem_id": self.problem_id,
            "solution_plan_id": self.solution_plan_id,
            "patches": [p.to_dict() for p in self.patches],
            "overall_status": self.overall_status.value,
            "summary": self.summary,
            "applied_count": self.applied_count,
            "failed_count": self.failed_count,
            "rolled_back_count": self.rolled_back_count,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AutoFixResult":
        """
        Erstellt AutoFixResult aus Dictionary.
        
        Args:
            data: Dictionary mit AutoFixResult-Daten
        
        Returns:
            Neues AutoFixResult-Objekt
        """
        result = cls(
            problem_id=data["problem_id"],
            solution_plan_id=data.get("solution_plan_id", ""),
            overall_status=FixStatus(data.get("overall_status", "pending")),
            summary=data.get("summary", ""),
            applied_count=data.get("applied_count", 0),
            failed_count=data.get("failed_count", 0),
            rolled_back_count=data.get("rolled_back_count", 0),
            started_at=data.get("started_at", datetime.now().isoformat()),
            completed_at=data.get("completed_at"),
        )
        
        # Patches separat laden
        for patch_data in data.get("patches", []):
            result.patches.append(FixPatch.from_dict(patch_data))
        
        return result
    
    def add_patch(self, patch: FixPatch) -> None:
        """
        Fügt Patch hinzu.
        
        Args:
            patch: Hinzuzufügender FixPatch
        """
        self.patches.append(patch)
        self._update_overall_status()
    
    def _update_overall_status(self) -> None:
        """Aktualisiert Gesamt-Status basierend auf Patch-Status."""
        if not self.patches:
            self.overall_status = FixStatus.PENDING
            return

        statuses = [p.status for p in self.patches]

        self.applied_count = sum(1 for s in statuses if s == FixStatus.COMPLETED)
        self.failed_count = sum(1 for s in statuses if s == FixStatus.FAILED)
        self.rolled_back_count = sum(1 for s in statuses if s == FixStatus.ROLLED_BACK)

        if all(s == FixStatus.COMPLETED for s in statuses):
            self.overall_status = FixStatus.COMPLETED
        elif any(s == FixStatus.FAILED for s in statuses):
            self.overall_status = FixStatus.FAILED
        elif all(s == FixStatus.ROLLED_BACK for s in statuses):
            self.overall_status = FixStatus.ROLLED_BACK
        elif all(s == FixStatus.PENDING for s in statuses):
            self.overall_status = FixStatus.PENDING
        else:
            self.overall_status = FixStatus.IN_PROGRESS
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Returns Statistik über Auto-Fix.
        
        Returns:
            Dictionary mit Statistiken
        """
        return {
            "total_patches": len(self.patches),
            "applied": self.applied_count,
            "failed": self.failed_count,
            "rolled_back": self.rolled_back_count,
            "pending": sum(1 for p in self.patches if p.status == FixStatus.PENDING),
            "in_progress": sum(1 for p in self.patches if p.status == FixStatus.IN_PROGRESS),
            "blocked": sum(1 for p in self.patches if p.status == FixStatus.BLOCKED),
            "overall_status": self.overall_status.value,
            "success_rate": (
                self.applied_count / len(self.patches) * 100
                if self.patches else 0
            ),
        }


class AutoFixEngine:
    """
    Engine für automatische Fix-Generierung und Anwendung.
    
    Verantwortlichkeiten:
    - Patch-Generierung basierend auf SolutionPlan
    - Patch-Anwendung mit Backup
    - Validation der angewendeten Patches
    - Rollback-Funktionalität
    """
    
    def __init__(
        self,
        repo_path: Path,
        solution_plan: SolutionPlan,
        dry_run: bool = False,
    ):
        """
        Initialisiert AutoFixEngine.
        
        Args:
            repo_path: Pfad zum Repository
            solution_plan: SolutionPlan mit ausgewählten Pfaden
            dry_run: Wenn True, keine echten Änderungen
        """
        self.repo_path = repo_path
        self.solution_plan = solution_plan
        self.dry_run = dry_run
        self.backup_dir = repo_path / ".glitchhunter" / "backups"
        
        # Backup-Verzeichnis erstellen
        if not dry_run:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_patches(self) -> AutoFixResult:
        """
        Generiert Patches basierend auf SolutionPlan.
        
        Returns:
            AutoFixResult mit generierten Patches
        """
        result = AutoFixResult(
            problem_id=self.solution_plan.problem_id,
            solution_plan_id="",  # Kann später gesetzt werden
        )
        
        # Für jedes Teilproblem mit ausgewähltem Pfad
        for sp_id, path_id in self.solution_plan.selected_paths.items():
            path = self.solution_plan.get_selected_path(sp_id)
            if not path:
                logger.warning(f"Kein Pfad gefunden für {sp_id}")
                continue
            
            # Patch generieren
            patch = self._generate_patch_for_path(sp_id, path)
            result.add_patch(patch)
        
        # Zusammenfassung
        result.summary = self._create_summary(result)
        result.completed_at = datetime.now().isoformat()
        
        return result
    
    def _generate_patch_for_path(
        self,
        subproblem_id: str,
        solution_path: SolutionPath,
    ) -> FixPatch:
        """
        Generiert Patch für SolutionPath.
        
        Args:
            subproblem_id: ID des Teilproblems
            solution_path: Ausgewählter Lösungsweg
        
        Returns:
            FixPatch
        """
        patch = FixPatch(
            id=f"patch_{uuid.uuid4().hex[:8]}",
            subproblem_id=subproblem_id,
            solution_path_id=solution_path.id,
            file_path="",  # Wird aus solution_path abgeleitet
            status=FixStatus.PENDING,
        )
        
        # In echter Implementierung:
        # - Code-Analyse
        # - Patch-Generierung basierend auf solution_path
        # - Diff-Erstellung
        
        # Für Phase 3.3: Stub-Implementierung
        patch.file_path = f"src/fix_{subproblem_id[:8]}.py"
        patch.original_content = "# Original content placeholder"
        patch.patched_content = "# Patched content placeholder"
        patch.diff = (
            f"--- a/{patch.file_path}\n"
            f"+++ b/{patch.file_path}\n"
            f"@@ -1 +1 @@\n"
            f"-# Original\n"
            f"+# Patched"
        )
        
        return patch
    
    def apply_patches(
        self,
        result: AutoFixResult,
        validate: bool = True,
    ) -> AutoFixResult:
        """
        Wendet generierte Patches an.
        
        Args:
            result: AutoFixResult mit generierten Patches
            validate: Wenn True, Validation nach Anwendung
        
        Returns:
            AutoFixResult mit aktualisierten Status
        """
        for patch in result.patches:
            if patch.status != FixStatus.PENDING:
                continue
            
            try:
                # Backup erstellen
                if not self.dry_run:
                    self._create_backup(patch)

                # Patch anwenden
                if not self.dry_run:
                    self._apply_patch(patch)

                patch.status = FixStatus.COMPLETED
                patch.applied_at = datetime.now().isoformat()
                # Rollback nur verfügbar wenn nicht Dry-Run und Backup existiert
                patch.rollback_available = not self.dry_run

                # Validation
                if validate:
                    validation_result = self._validate_patch(patch)
                    patch.validation_passed = validation_result
                    if not validation_result:
                        patch.status = FixStatus.FAILED
                        patch.validation_errors = ["Validation failed"]
                
            except Exception as e:
                patch.status = FixStatus.FAILED
                patch.validation_errors.append(str(e))
                logger.error(f"Patch {patch.id} fehlgeschlagen: {e}")
        
        result.completed_at = datetime.now().isoformat()
        result._update_overall_status()
        result.summary = self._create_summary(result)
        
        return result
    
    def rollback(self, result: AutoFixResult) -> AutoFixResult:
        """
        Rollback aller angewendeten Patches.
        
        Args:
            result: AutoFixResult mit angewendeten Patches
        
        Returns:
            AutoFixResult nach Rollback
        """
        for patch in result.patches:
            if patch.status != FixStatus.COMPLETED:
                continue
            
            try:
                # Backup wiederherstellen
                if patch.backup_path and Path(patch.backup_path).exists():
                    self._restore_backup(patch)
                    patch.status = FixStatus.ROLLED_BACK
                else:
                    patch.status = FixStatus.FAILED
                    patch.validation_errors.append("No backup found")
            
            except Exception as e:
                patch.status = FixStatus.FAILED
                patch.validation_errors.append(str(e))
                logger.error(f"Rollback für Patch {patch.id} fehlgeschlagen: {e}")
        
        result._update_overall_status()
        result.summary = self._create_summary(result)
        
        return result
    
    def _create_backup(self, patch: FixPatch) -> None:
        """
        Erstellt Backup der Original-Datei.
        
        Args:
            patch: Patch für den das Backup erstellt wird
        """
        file_path = self.repo_path / patch.file_path
        if file_path.exists():
            backup_path = self.backup_dir / f"{patch.id}_{file_path.name}.bak"
            shutil.copy2(file_path, backup_path)
            patch.backup_path = str(backup_path)
            patch.rollback_available = True
            logger.debug(f"Backup erstellt: {backup_path}")
    
    def _apply_patch(self, patch: FixPatch) -> None:
        """
        Wendet Patch auf Datei an.
        
        Args:
            patch: Anzuwendender Patch
        """
        file_path = self.repo_path / patch.file_path
        
        # Verzeichnis erstellen falls nicht existiert
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Patch schreiben
        file_path.write_text(patch.patched_content)
        logger.debug(f"Patch angewendet: {file_path}")
    
    def _restore_backup(self, patch: FixPatch) -> None:
        """
        Stellt Backup wieder her.
        
        Args:
            patch: Patch dessen Backup wiederhergestellt wird
        """
        file_path = self.repo_path / patch.file_path
        backup_path = Path(patch.backup_path)
        
        if backup_path.exists():
            shutil.copy2(backup_path, file_path)
            logger.debug(f"Backup wiederhergestellt: {file_path}")
    
    def _validate_patch(self, patch: FixPatch) -> bool:
        """
        Validiert angewendeten Patch.
        
        Args:
            patch: Zu validierender Patch
        
        Returns:
            True wenn Validierung bestanden
        """
        # Stub: In echter Implementierung
        # - Syntax-Check
        # - Tests ausführen
        # - Code-Qualität prüfen
        
        return True
    
    def _create_summary(self, result: AutoFixResult) -> str:
        """
        Erstellt Zusammenfassung des Auto-Fix-Ergebnisses.
        
        Args:
            result: AutoFixResult
        
        Returns:
            Zusammenfassungs-String
        """
        stats = result.get_statistics()
        return (
            f"Auto-Fix: {stats['applied']}/{stats['total_patches']} Patches erfolgreich "
            f"({stats['success_rate']:.0f}% Success-Rate)"
        )


def create_auto_fix_engine(
    repo_path: Path,
    solution_plan: SolutionPlan,
    dry_run: bool = False,
) -> AutoFixEngine:
    """
    Factory-Funktion für AutoFixEngine.
    
    Args:
        repo_path: Pfad zum Repository
        solution_plan: SolutionPlan
        dry_run: Wenn True, keine echten Änderungen
    
    Returns:
        Initialisierte AutoFixEngine
    """
    return AutoFixEngine(
        repo_path=repo_path,
        solution_plan=solution_plan,
        dry_run=dry_run,
    )
