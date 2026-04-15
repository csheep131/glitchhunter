"""
Problem Manager - Zentrale Orchestrierung für Problem-Solver.

Verwaltet ProblemCases, speichert/lädt Reports und koordiniert
die verschiedenen Verarbeitungsschritte.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import ProblemCase, ProblemType, ProblemSeverity, ProblemStatus
from .intake import ProblemIntake
from .classifier import ProblemClassifier, ClassificationResult
from .diagnosis import Diagnosis, DiagnosisEngine, CauseType

logger = logging.getLogger(__name__)


class ProblemManager:
    """
    Zentrale Verwaltung für ProblemCases.
    
    Usage:
        manager = ProblemManager(repo_path=".")
        
        # Neues Problem aufnehmen
        problem = manager.intake_problem(
            description="Das Startup ist zu langsam",
            source="cli"
        )
        
        # Problem klassifizieren
        classification = manager.classify_problem(problem.id)
        
        # Problem speichern
        manager.save_problem(problem)
        
        # Alle Probleme laden
        problems = manager.list_problems()
    """
    
    def __init__(
        self,
        repo_path: Path,
        problems_dir: Optional[str] = None,
    ):
        """
        Initialisiert ProblemManager.
        
        Args:
            repo_path: Pfad zum Repository
            problems_dir: Verzeichnis für Problem-Reports (default: .glitchhunter/problems)
        """
        self.repo_path = Path(repo_path)
        self.problems_dir = Path(problems_dir) if problems_dir else (
            self.repo_path / ".glitchhunter" / "problems"
        )
        self.problems_dir.mkdir(parents=True, exist_ok=True)
        
        # Services initialisieren
        self.intake = ProblemIntake()
        self.classifier = ProblemClassifier(repo_path=repo_path)
        
        # Geladene Problems im Memory-Cache
        self._problems: Dict[str, ProblemCase] = {}
        
        # Beim Start alle existierenden Probleme laden
        self._load_all_problems()
    
    def intake_problem(
        self,
        description: str,
        title: Optional[str] = None,
        source: str = "cli",
    ) -> ProblemCase:
        """
        Nimmt neues Problem auf.
        
        Args:
            description: Problembeschreibung (roh)
            title: Optionaler Titel (wird sonst aus Beschreibung extrahiert)
            source: Quelle (cli, api, tui, file)
        
        Returns:
            Neues ProblemCase-Objekt
        """
        logger.info(f"Taking in new problem from {source}")
        
        # ProblemCase erstellen
        problem = self.intake.intake_from_text(description, source=source)
        
        # Titel überschreiben falls angegeben
        if title:
            problem.title = title
        
        # Im Cache speichern
        self._problems[problem.id] = problem
        
        # Persistieren
        self.save_problem(problem)
        
        logger.info(f"Problem created: {problem.id} - {problem.title}")
        return problem
    
    def classify_problem(self, problem_id: str) -> ClassificationResult:
        """
        Klassifiziert ein Problem detailliert.
        
        Args:
            problem_id: ID des zu klassifizierenden Problems
        
        Returns:
            ClassificationResult mit detaillierter Analyse
        
        Raises:
            ValueError: Wenn Problem nicht gefunden
        """
        problem = self.get_problem(problem_id)
        if not problem:
            raise ValueError(f"Problem {problem_id} not found")
        
        logger.info(f"Classifying problem: {problem_id}")
        
        # Klassifikation durchführen
        result = self.classifier.classify(problem)
        
        # Problem mit Klassifikation aktualisieren
        problem.problem_type = result.problem_type
        problem.affected_components = result.affected_components
        
        # Speichern
        self.save_problem(problem)
        
        logger.info(
            f"Classification complete: {result.problem_type.value} "
            f"(confidence: {result.confidence:.2f})"
        )
        
        return result
    
    def get_problem(self, problem_id: str) -> Optional[ProblemCase]:
        """
        Lädt ein ProblemCase nach ID.
        
        Args:
            problem_id: ID des Problems
        
        Returns:
            ProblemCase oder None
        """
        # Erst im Cache suchen
        if problem_id in self._problems:
            return self._problems[problem_id]
        
        # Sonst von Disk laden
        problem_file = self.problems_dir / f"{problem_id}.json"
        if problem_file.exists():
            try:
                data = json.loads(problem_file.read_text())
                problem = ProblemCase.from_dict(data)
                self._problems[problem_id] = problem
                return problem
            except Exception as e:
                logger.error(f"Failed to load problem {problem_id}: {e}")
                return None
        
        return None
    
    def list_problems(
        self,
        status_filter: Optional[ProblemStatus] = None,
        type_filter: Optional[ProblemType] = None,
    ) -> List[ProblemCase]:
        """
        Listet alle Probleme mit optionalem Filter.
        
        Args:
            status_filter: Nur Probleme mit diesem Status
            type_filter: Nur Probleme mit diesem Typ
        
        Returns:
            Liste von ProblemCases
        """
        problems = list(self._problems.values())
        
        if status_filter:
            problems = [p for p in problems if p.status == status_filter]
        
        if type_filter:
            problems = [p for p in problems if p.problem_type == type_filter]
        
        # Nach Updated-At sortieren (neueste zuerst)
        problems.sort(key=lambda p: p.updated_at, reverse=True)
        
        return problems
    
    def save_problem(self, problem: ProblemCase) -> Path:
        """
        Speichert ProblemCase persistently.
        
        Args:
            problem: Zu speicherndes ProblemCase
        
        Returns:
            Pfad zur gespeicherten Datei
        """
        # Updated-At aktualisieren
        problem.updated_at = datetime.now().isoformat()
        
        # Datei-Pfad
        problem_file = self.problems_dir / f"{problem.id}.json"
        
        # Als JSON speichern
        problem_file.write_text(
            json.dumps(problem.to_dict(), indent=2, ensure_ascii=False)
        )
        
        logger.debug(f"Problem saved: {problem_file}")
        return problem_file
    
    def update_problem(
        self,
        problem_id: str,
        updates: Dict[str, Any],
    ) -> Optional[ProblemCase]:
        """
        Aktualisiert ein ProblemCase.
        
        Args:
            problem_id: ID des Problems
            updates: Dict mit zu aktualisierenden Feldern
        
        Returns:
            Aktualisiertes ProblemCase oder None
        
        Raises:
            ValueError: Wenn Problem nicht gefunden
        """
        problem = self.get_problem(problem_id)
        if not problem:
            raise ValueError(f"Problem {problem_id} not found")
        
        # Updates anwenden mit Enum-Konvertierung
        for key, value in updates.items():
            if not hasattr(problem, key):
                continue
            
            # Enum-Werte konvertieren
            if key == "status" and isinstance(value, str):
                try:
                    value = ProblemStatus(value)
                except ValueError:
                    logger.warning(f"Invalid status value: {value}")
                    continue
            elif key == "problem_type" and isinstance(value, str):
                try:
                    value = ProblemType(value)
                except ValueError:
                    logger.warning(f"Invalid problem_type value: {value}")
                    continue
            elif key == "severity" and isinstance(value, str):
                try:
                    value = ProblemSeverity(value)
                except ValueError:
                    logger.warning(f"Invalid severity value: {value}")
                    continue
            
            setattr(problem, key, value)
        
        # Speichern
        self.save_problem(problem)
        
        logger.info(f"Problem updated: {problem_id}")
        return problem
    
    def delete_problem(self, problem_id: str) -> bool:
        """
        Löscht ein ProblemCase.
        
        Args:
            problem_id: ID des zu löschenden Problems
        
        Returns:
            True wenn erfolgreich gelöscht
        """
        problem = self.get_problem(problem_id)
        if not problem:
            return False
        
        # Von Disk löschen
        problem_file = self.problems_dir / f"{problem_id}.json"
        if problem_file.exists():
            problem_file.unlink()
        
        # Aus Cache entfernen
        if problem_id in self._problems:
            del self._problems[problem_id]
        
        logger.info(f"Problem deleted: {problem_id}")
        return True
    
    def _load_all_problems(self) -> None:
        """Lädt alle existierenden Probleme von Disk."""
        for problem_file in self.problems_dir.glob("*.json"):
            try:
                data = json.loads(problem_file.read_text())
                problem = ProblemCase.from_dict(data)
                self._problems[problem.id] = problem
            except Exception as e:
                logger.warning(f"Failed to load {problem_file}: {e}")
        
        logger.info(f"Loaded {len(self._problems)} problems from disk")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Returns Statistik über ProblemCases.

        Returns:
            Dict mit Statistiken
        """
        problems = list(self._problems.values())

        # Nach Typ gruppieren
        by_type: Dict[str, int] = {}
        for p in problems:
            type_key = p.problem_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1

        # Nach Status gruppieren
        by_status: Dict[str, int] = {}
        for p in problems:
            status_key = p.status.value
            by_status[status_key] = by_status.get(status_key, 0) + 1

        return {
            "total_problems": len(problems),
            "by_type": by_type,
            "by_status": by_status,
            "oldest_problem": min(
                (p.created_at for p in problems),
                default=None,
            ),
            "newest_problem": max(
                (p.updated_at for p in problems),
                default=None,
            ),
        }

    def generate_diagnosis(self, problem_id: str) -> Diagnosis:
        """
        Generiert Diagnose für ein Problem.
        
        Args:
            problem_id: ID des Problems
        
        Returns:
            Diagnosis-Objekt
        
        Raises:
            ValueError: Wenn Problem nicht gefunden
        """
        problem = self.get_problem(problem_id)
        if not problem:
            raise ValueError(f"Problem {problem_id} not found")
        
        logger.info(f"Generating diagnosis for problem: {problem_id}")
        
        engine = DiagnosisEngine(repo_path=self.repo_path)
        diagnosis = engine.generate_diagnosis(problem)
        
        # Diagnose speichern
        self._save_diagnosis(problem_id, diagnosis)
        
        # Problem-Status aktualisieren
        self.update_problem(problem_id, {"status": ProblemStatus.DIAGNOSIS.value})
        
        logger.info(f"Diagnosis generated: {len(diagnosis.causes)} causes identified")
        return diagnosis

    def get_diagnosis(self, problem_id: str) -> Optional[Diagnosis]:
        """
        Lädt Diagnose für ein Problem.
        
        Args:
            problem_id: ID des Problems
        
        Returns:
            Diagnosis oder None
        """
        diagnosis_file = self.problems_dir / f"{problem_id}_diagnosis.json"
        
        if diagnosis_file.exists():
            try:
                data = json.loads(diagnosis_file.read_text())
                return Diagnosis.from_dict(data)
            except Exception as e:
                logger.error(f"Failed to load diagnosis: {e}")
                return None
        
        return None

    def _save_diagnosis(self, problem_id: str, diagnosis: Diagnosis) -> Path:
        """Speichert Diagnose persistently."""
        diagnosis_file = self.problems_dir / f"{problem_id}_diagnosis.json"
        diagnosis_file.write_text(
            json.dumps(diagnosis.to_dict(), indent=2, ensure_ascii=False)
        )
        return diagnosis_file
