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
from .decomposition import Decomposition, DecompositionEngine
from .solution_path import SolutionPlan, SolutionPlanner
from .validation import (
    GoalValidationReport,
    IntentValidationReport,
    GoalValidator,
    IntentValidator,
)
from .stack_adapter import (
    StackID,
    StackAdapterManager,
    StackProfile,
    create_stack_adapter,
)
from .auto_fix import (
    AutoFixResult,
    AutoFixEngine,
    create_auto_fix_engine,
    FixStatus,
)

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
        
        # Stack Adapter initialisieren
        self.stack_manager = create_stack_adapter(repo_path=repo_path)

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

    def decompose_problem(self, problem_id: str) -> Decomposition:
        """
        Zerlegt ein Problem in Teilprobleme.
        
        Args:
            problem_id: ID des Problems
        
        Returns:
            Decomposition-Objekt
        
        Raises:
            ValueError: Wenn Problem nicht gefunden
        """
        problem = self.get_problem(problem_id)
        if not problem:
            raise ValueError(f"Problem {problem_id} not found")

        logger.info(f"Decomposing problem: {problem_id}")

        engine = DecompositionEngine()
        decomposition = engine.decompose_problem(problem)

        # Decomposition speichern
        self._save_decomposition(problem_id, decomposition)

        # Problem-Status aktualisieren
        self.update_problem(problem_id, {"status": ProblemStatus.PLANNING.value})

        logger.info(
            f"Decomposition complete: {len(decomposition.subproblems)} subproblems"
        )
        return decomposition

    def get_decomposition(self, problem_id: str) -> Optional[Decomposition]:
        """
        Lädt Decomposition für ein Problem.
        
        Args:
            problem_id: ID des Problems
        
        Returns:
            Decomposition oder None
        """
        decomp_file = self.problems_dir / f"{problem_id}_decomposition.json"

        if decomp_file.exists():
            try:
                data = json.loads(decomp_file.read_text())
                return Decomposition.from_dict(data)
            except Exception as e:
                logger.error(f"Failed to load decomposition: {e}")
                return None

        return None

    def _save_decomposition(
        self,
        problem_id: str,
        decomposition: Decomposition,
    ) -> Path:
        """
        Speichert Decomposition persistently.

        Args:
            problem_id: ID des Problems
            decomposition: Zu speichernde Decomposition

        Returns:
            Pfad zur gespeicherten Datei
        """
        decomp_file = self.problems_dir / f"{problem_id}_decomposition.json"
        decomp_file.write_text(
            json.dumps(decomposition.to_dict(), indent=2, ensure_ascii=False)
        )
        return decomp_file

    def create_solution_plan(
        self,
        problem_id: str,
        use_decomposition: bool = True,
    ) -> SolutionPlan:
        """
        Erstellt Lösungsplan für Problem.

        Args:
            problem_id: ID des Problems
            use_decomposition: Ob Decomposition verwendet werden soll

        Returns:
            SolutionPlan-Objekt

        Raises:
            ValueError: Wenn Problem nicht gefunden
        """
        problem = self.get_problem(problem_id)
        if not problem:
            raise ValueError(f"Problem {problem_id} not found")

        logger.info(f"Creating solution plan for problem: {problem_id}")

        # SubProblem-IDs sammeln
        decomposition = None
        if use_decomposition:
            decomposition = self.get_decomposition(problem_id)
            if decomposition:
                subproblem_ids = [sp.id for sp in decomposition.subproblems]
            else:
                # Fallback: Leere Liste
                subproblem_ids = []
        else:
            subproblem_ids = []

        # Plan erstellen
        planner = SolutionPlanner(repo_path=self.repo_path)
        plan = planner.create_solution_plan(
            problem_id=problem_id,
            subproblem_ids=subproblem_ids,
            decomposition_id=decomposition.problem_id if decomposition else None,
        )

        # Plan speichern
        self._save_solution_plan(problem_id, plan)

        logger.info(
            f"Solution plan created: {len(plan.solution_paths)} subproblems, "
            f"{sum(len(p) for p in plan.solution_paths.values())} paths"
        )
        return plan

    def get_solution_plan(self, problem_id: str) -> Optional[SolutionPlan]:
        """
        Lädt SolutionPlan für ein Problem.

        Args:
            problem_id: ID des Problems

        Returns:
            SolutionPlan oder None
        """
        plan_file = self.problems_dir / f"{problem_id}_solution_plan.json"

        if plan_file.exists():
            try:
                data = json.loads(plan_file.read_text())
                return SolutionPlan.from_dict(data)
            except Exception as e:
                logger.error(f"Failed to load solution plan: {e}")
                return None

        return None

    def select_solution_path(
        self,
        problem_id: str,
        subproblem_id: str,
        path_id: str,
    ) -> bool:
        """
        Wählt Lösungsweg für Teilproblem aus.

        Args:
            problem_id: ID des Problems
            subproblem_id: ID des Teilproblems
            path_id: ID des Lösungswegs

        Returns:
            True wenn erfolgreich
        """
        plan = self.get_solution_plan(problem_id)
        if not plan:
            return False

        success = plan.select_path(subproblem_id, path_id)
        if success:
            self._save_solution_plan(problem_id, plan)
        return success

    def _save_solution_plan(
        self,
        problem_id: str,
        plan: SolutionPlan,
    ) -> Path:
        """
        Speichert SolutionPlan persistently.

        Args:
            problem_id: ID des Problems
            plan: Zu speichernder SolutionPlan

        Returns:
            Pfad zur gespeicherten Datei
        """
        plan_file = self.problems_dir / f"{problem_id}_solution_plan.json"
        plan_file.write_text(
            json.dumps(plan.to_dict(), indent=2, ensure_ascii=False)
        )
        return plan_file

    # =========================================================================
    # Stack-spezifische Methoden (Phase 2.4)
    # =========================================================================

    def get_stack_profile(self, stack_id: str) -> Optional[StackProfile]:
        """Returns Stack-Profil."""
        try:
            stack = StackID(stack_id)
            return self.stack_manager.get_profile(stack)
        except ValueError:
            return None

    def compare_stacks(self, capability: Optional[str] = None) -> Dict[str, Any]:
        """Vergleicht beide Stacks."""
        return self.stack_manager.compare_stacks(capability)

    def recommend_stack_for_problem(
        self,
        problem_id: str,
    ) -> str:
        """
        Empfiehlt besten Stack für Problem.

        Args:
            problem_id: ID des Problems

        Returns:
            Empfohlene StackID als String
        """
        problem = self.get_problem(problem_id)
        if not problem:
            return StackID.STACK_A.value

        required_caps = problem.affected_components  # Als Proxy
        recommendation = self.stack_manager.recommend_stack(
            problem_type=problem.problem_type.value,
            required_capabilities=required_caps,
        )

        return recommendation.value

    def validate_solution_for_stack(
        self,
        problem_id: str,
        solution_plan_id: str,
        stack_id: str,
    ) -> Dict[str, Any]:
        """Validiert Solution-Plan für Stack."""
        return self.stack_manager.validate_stack_compatibility(
            solution_plan_id=solution_plan_id,
            stack_id=StackID(stack_id),
        )

    # =========================================================================
    # Validation Methods (Phase 3.1)
    # =========================================================================

    def validate_goal(
        self,
        problem_id: str,
        implemented_changes: Optional[Dict[str, Any]] = None,
    ) -> GoalValidationReport:
        """
        Führt Goal Validation durch.
        
        Prüft ob die Success Criteria des Problems erfüllt sind.
        
        Args:
            problem_id: ID des Problems
            implemented_changes: Beschreibung der Umsetzungen
        
        Returns:
            GoalValidationReport
        
        Raises:
            ValueError: Wenn Problem nicht gefunden
        """
        problem = self.get_problem(problem_id)
        if not problem:
            raise ValueError(f"Problem {problem_id} not found")
        
        logger.info(f"Validating goal for problem: {problem_id}")
        
        goal_validator = GoalValidator(repo_path=self.repo_path)
        report = goal_validator.validate(problem, implemented_changes)
        
        # Report speichern
        self._save_validation_report(problem_id, report)
        
        logger.info(
            f"Goal Validation complete: {report.get_passed_count()}/{len(report.results)} passed"
        )
        
        return report

    def validate_intent(
        self,
        problem_id: str,
        solution_description: str = "",
    ) -> IntentValidationReport:
        """
        Führt Intent Validation durch.
        
        Prüft ob das ursprüngliche Problem wirklich gelöst wurde
        oder nur Symptome behandelt wurden.
        
        Args:
            problem_id: ID des Problems
            solution_description: Beschreibung der Lösung
        
        Returns:
            IntentValidationReport
        
        Raises:
            ValueError: Wenn Problem nicht gefunden
        """
        problem = self.get_problem(problem_id)
        if not problem:
            raise ValueError(f"Problem {problem_id} not found")
        
        logger.info(f"Validating intent for problem: {problem_id}")
        
        intent_validator = IntentValidator(repo_path=self.repo_path)
        report = intent_validator.validate(problem, solution_description)
        
        logger.info(f"Intent Validation complete: {report.overall_status.value}")
        
        return report

    def _save_validation_report(
        self,
        problem_id: str,
        report: GoalValidationReport,
    ) -> Path:
        """
        Speichert Validation-Report persistently.

        Args:
            problem_id: ID des Problems
            report: Zu speichernder GoalValidationReport

        Returns:
            Pfad zur gespeicherten Datei
        """
        report_file = self.problems_dir / f"{problem_id}_validation.json"
        report_file.write_text(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
        )
        return report_file

    # =========================================================================
    # Auto-Fix Methods (Phase 3.3)
    # =========================================================================

    def auto_fix(
        self,
        problem_id: str,
        dry_run: bool = False,
        validate: bool = True,
    ) -> AutoFixResult:
        """
        Führt Auto-Fix für Problem durch.

        Args:
            problem_id: ID des Problems
            dry_run: Wenn True, keine echten Änderungen
            validate: Wenn True, Validation nach Anwendung

        Returns:
            AutoFixResult

        Raises:
            ValueError: Wenn Problem oder SolutionPlan nicht gefunden
        """
        problem = self.get_problem(problem_id)
        if not problem:
            raise ValueError(f"Problem {problem_id} not found")

        logger.info(f"Starting auto-fix for problem: {problem_id}")

        # SolutionPlan laden
        plan = self.get_solution_plan(problem_id)
        if not plan:
            raise ValueError(f"No solution plan found for {problem_id}")

        # AutoFixEngine erstellen
        engine = create_auto_fix_engine(
            repo_path=self.repo_path,
            solution_plan=plan,
            dry_run=dry_run,
        )

        # Patches generieren
        result = engine.generate_patches()

        # Patches anwenden
        if not dry_run:
            result = engine.apply_patches(result, validate=validate)

        # Result speichern
        self._save_auto_fix_result(problem_id, result)

        logger.info(
            f"Auto-Fix complete: {result.applied_count}/{len(result.patches)} applied"
        )

        return result

    def rollback_fix(
        self,
        problem_id: str,
    ) -> AutoFixResult:
        """
        Rollback von Auto-Fix.

        Args:
            problem_id: ID des Problems

        Returns:
            AutoFixResult nach Rollback

        Raises:
            ValueError: Wenn Problem oder AutoFixResult nicht gefunden
        """
        problem = self.get_problem(problem_id)
        if not problem:
            raise ValueError(f"Problem {problem_id} not found")

        logger.info(f"Rolling back auto-fix for problem: {problem_id}")

        # AutoFixResult laden
        result = self._load_auto_fix_result(problem_id)
        if not result:
            raise ValueError(f"No auto-fix result found for {problem_id}")

        # AutoFixEngine erstellen
        plan = self.get_solution_plan(problem_id)
        engine = create_auto_fix_engine(
            repo_path=self.repo_path,
            solution_plan=plan,
            dry_run=False,
        )

        # Rollback durchführen
        result = engine.rollback(result)

        # Result speichern
        self._save_auto_fix_result(problem_id, result)

        logger.info(f"Rollback complete: {result.rolled_back_count} patches rolled back")

        return result

    def _save_auto_fix_result(
        self,
        problem_id: str,
        result: AutoFixResult,
    ) -> Path:
        """
        Speichert AutoFixResult persistently.

        Args:
            problem_id: ID des Problems
            result: Zu speicherndes AutoFixResult

        Returns:
            Pfad zur gespeicherten Datei
        """
        result_file = self.problems_dir / f"{problem_id}_auto_fix.json"
        result_file.write_text(
            json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
        )
        return result_file

    def _load_auto_fix_result(
        self,
        problem_id: str,
    ) -> Optional[AutoFixResult]:
        """
        Lädt AutoFixResult von Disk.

        Args:
            problem_id: ID des Problems

        Returns:
            AutoFixResult oder None
        """
        result_file = self.problems_dir / f"{problem_id}_auto_fix.json"

        if result_file.exists():
            try:
                data = json.loads(result_file.read_text())
                return AutoFixResult.from_dict(data)
            except Exception as e:
                logger.error(f"Failed to load auto-fix result: {e}")
                return None

        return None
