"""
Goal & Intent Validation für Problem-Solver.

Gemäß PROBLEM_SOLVER.md Phase 3:
- Goal Validation: Prüft ob Success Criteria erfüllt sind
- Intent Validation: Prüft ob ursprüngliches Problem gelöst wurde
- Scheinlösungen erkennen
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

from .models import ProblemCase


class ValidationStatus(Enum):
    """Status einer Validierung."""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    BLOCKED = "blocked"


@dataclass
class ValidationResult:
    """
    Ergebnis einer Validierungsprüfung.
    
    Attributes:
        criterion: Zu prüfendes Kriterium
        status: Status der Validierung
        description: Beschreibung des Kriteriums
        evidence: Liste von Belegen/Nachweisen
        metrics: Metriken und Messwerte
        failure_reason: Grund für Failure (falls zutreffend)
        remediation_steps: Schritte zur Behebung (falls zutreffend)
    """
    
    criterion: str  # Zu prüfendes Kriterium
    status: ValidationStatus
    description: str = ""
    
    # Details
    evidence: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Bei Failure
    failure_reason: str = ""
    remediation_steps: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Konvertiert ValidationResult zu Dictionary."""
        return {
            "criterion": self.criterion,
            "status": self.status.value,
            "description": self.description,
            "evidence": self.evidence,
            "metrics": self.metrics,
            "failure_reason": self.failure_reason,
            "remediation_steps": self.remediation_steps,
        }


@dataclass
class GoalValidationReport:
    """
    Vollständiger Goal-Validation-Report.
    
    Attributes:
        problem_id: ID des validierten Problems
        solution_plan_id: ID des Lösungsplans
        results: Einzelne Validierungsergebnisse
        overall_status: Gesamt-Status der Validierung
        summary: Zusammenfassung der Ergebnisse
        validated_at: Zeitstempel der Validierung
        validator_version: Version des Validators
    """
    
    problem_id: str
    solution_plan_id: str
    
    # Einzelne Validierungsergebnisse
    results: List[ValidationResult] = field(default_factory=list)
    
    # Gesamt-Status
    overall_status: ValidationStatus = ValidationStatus.PENDING
    
    # Zusammenfassung
    summary: str = ""
    
    # Metadaten
    validated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    validator_version: str = "1.0"
    
    def to_dict(self) -> dict:
        """Konvertiert GoalValidationReport zu Dictionary."""
        return {
            "problem_id": self.problem_id,
            "solution_plan_id": self.solution_plan_id,
            "results": [r.to_dict() for r in self.results],
            "overall_status": self.overall_status.value,
            "summary": self.summary,
            "validated_at": self.validated_at,
            "validator_version": self.validator_version,
        }
    
    def add_result(self, result: ValidationResult) -> None:
        """
        Fügt Validierungsergebnis hinzu.
        
        Args:
            result: ValidationResult hinzuzufügen
        """
        self.results.append(result)
        self._update_overall_status()
    
    def _update_overall_status(self) -> None:
        """Aktualisiert Gesamt-Status basierend auf Einzelresultaten."""
        if not self.results:
            self.overall_status = ValidationStatus.PENDING
            return
        
        statuses = [r.status for r in self.results]
        
        # Wenn alle pending sind, bleibt Status PENDING
        if all(s == ValidationStatus.PENDING for s in statuses):
            self.overall_status = ValidationStatus.PENDING
        elif all(s == ValidationStatus.PASSED for s in statuses):
            self.overall_status = ValidationStatus.PASSED
        elif all(s == ValidationStatus.FAILED for s in statuses):
            self.overall_status = ValidationStatus.FAILED
        elif any(s == ValidationStatus.BLOCKED for s in statuses):
            self.overall_status = ValidationStatus.BLOCKED
        elif any(s == ValidationStatus.FAILED for s in statuses):
            self.overall_status = ValidationStatus.PARTIAL
        else:
            self.overall_status = ValidationStatus.PARTIAL
    
    def get_passed_count(self) -> int:
        """Returns Anzahl bestandener Validierungen."""
        return sum(1 for r in self.results if r.status == ValidationStatus.PASSED)
    
    def get_failed_count(self) -> int:
        """Returns Anzahl durchgefallener Validierungen."""
        return sum(1 for r in self.results if r.status == ValidationStatus.FAILED)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Returns Statistik über Validation."""
        return {
            "total_criteria": len(self.results),
            "passed": self.get_passed_count(),
            "failed": self.get_failed_count(),
            "pending": sum(1 for r in self.results if r.status == ValidationStatus.PENDING),
            "blocked": sum(1 for r in self.results if r.status == ValidationStatus.BLOCKED),
            "overall_status": self.overall_status.value,
            "completion_percentage": (
                self.get_passed_count() / len(self.results) * 100
                if self.results else 0
            ),
        }


@dataclass
class IntentValidationReport:
    """
    Intent-Validation-Report.
    
    Prüft ob das ursprüngliche Problem wirklich gelöst wurde.
    
    Attributes:
        problem_id: ID des validierten Problems
        original_problem_description: Original-Problembeschreibung
        original_intent: Ursprüngliche Intent/Goal
        problem_addressed: Ob Problem adressiert wurde
        symptoms_resolved: Ob Symptome gelöst wurden
        root_cause_fixed: Ob Root-Cause behoben wurde
        no_side_effects: Ob keine unerwünschten Nebeneffekte
        analysis: Analyse-Zusammenfassung
        concerns: Liste von Bedenken
        overall_status: Gesamt-Status
        validated_at: Zeitstempel der Validierung
    """
    
    problem_id: str
    
    # Original Problem
    original_problem_description: str = ""
    original_intent: str = ""
    
    # Validierung
    problem_addressed: bool = False
    symptoms_resolved: bool = False
    root_cause_fixed: bool = False
    no_side_effects: bool = False
    
    # Details
    analysis: str = ""
    concerns: List[str] = field(default_factory=list)
    
    # Status
    overall_status: ValidationStatus = ValidationStatus.PENDING
    
    validated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        """Konvertiert IntentValidationReport zu Dictionary."""
        return {
            "problem_id": self.problem_id,
            "original_problem_description": self.original_problem_description,
            "original_intent": self.original_intent,
            "problem_addressed": self.problem_addressed,
            "symptoms_resolved": self.symptoms_resolved,
            "root_cause_fixed": self.root_cause_fixed,
            "no_side_effects": self.no_side_effects,
            "analysis": self.analysis,
            "concerns": self.concerns,
            "overall_status": self.overall_status.value,
            "validated_at": self.validated_at,
        }
    
    def evaluate(self) -> None:
        """
        Bewertet Intent-Validation.
        
        Setzt overall_status basierend auf den Einzelprüfungen.
        Erkennt Scheinlösungen (Symptom behandelt, nicht Ursache).
        """
        # Alle positiven Kriterien
        positive = [
            self.problem_addressed,
            self.symptoms_resolved,
            self.root_cause_fixed,
            self.no_side_effects,
        ]
        
        # Alle negativen Kriterien
        negative = [
            not self.problem_addressed,
            not self.symptoms_resolved,
            not self.root_cause_fixed,
            not self.no_side_effects,
        ]
        
        # Wenn alle Kriterien False sind -> FAILED
        if all(negative):
            self.overall_status = ValidationStatus.FAILED
        elif all(positive):
            self.overall_status = ValidationStatus.PASSED
        else:
            self.overall_status = ValidationStatus.PARTIAL
        
        # Scheinlösung erkennen
        if self.problem_addressed and not self.root_cause_fixed:
            self.concerns.append(
                "⚠️ Mögliche Scheinlösung: Symptom wurde behandelt, nicht die Ursache"
            )


class GoalValidator:
    """
    Validator für Success Criteria.
    
    Prüft ob die definierten Erfolgskriterien erfüllt sind.
    """
    
    def __init__(self, repo_path: Optional[Path] = None):
        """
        Initialisiert GoalValidator.
        
        Args:
            repo_path: Pfad zum Repository
        """
        self.repo_path = repo_path
    
    def validate(
        self,
        problem: ProblemCase,
        implemented_changes: Optional[Dict[str, Any]] = None,
    ) -> GoalValidationReport:
        """
        Führt Goal Validation durch.
        
        Args:
            problem: ProblemCase mit Success Criteria
            implemented_changes: Optional: Beschreibung der Umsetzungen
        
        Returns:
            GoalValidationReport
        """
        report = GoalValidationReport(
            problem_id=problem.id,
            solution_plan_id="",  # Kann später gesetzt werden
        )
        
        # Success Criteria prüfen
        for criterion in problem.success_criteria:
            result = self._validate_criterion(criterion, problem, implemented_changes)
            report.add_result(result)
        
        # Zusammenfassung
        stats = report.get_statistics()
        report.summary = (
            f"Goal Validation: {stats['passed']}/{stats['total_criteria']} Kriterien erfüllt "
            f"({stats['completion_percentage']:.0f}%)"
        )
        
        return report
    
    def _validate_criterion(
        self,
        criterion: str,
        problem: ProblemCase,
        implemented_changes: Optional[Dict[str, Any]],
    ) -> ValidationResult:
        """
        Prüft einzelnes Erfolgskriterium.
        
        Args:
            criterion: Zu prüfendes Kriterium
            problem: ProblemCase
            implemented_changes: Beschriebung der Umsetzungen
        
        Returns:
            ValidationResult
        """
        # Stub-Implementierung für Phase 3.1
        # In echter Implementierung: Konkrete Prüfungen durchführen
        
        result = ValidationResult(
            criterion=criterion,
            status=ValidationStatus.PENDING,
            description=criterion,
        )
        
        # Hier würden konkrete Prüfungen stattfinden:
        # - Code-Analyse
        # - Test-Execution
        # - Performance-Messung
        # - User-Feedback
        
        # Für jetzt: Als Pending markieren
        result.failure_reason = "Validation not yet implemented"
        result.remediation_steps = [
            "Konkrete Prüflogik implementieren",
            "Test-Cases ausführen",
            "Metriken sammeln",
        ]
        
        return result


class IntentValidator:
    """
    Validator für Intent Validation.
    
    Prüft ob das ursprüngliche Problem wirklich gelöst wurde
    oder nur Symptome behandelt wurden.
    """
    
    def __init__(self, repo_path: Optional[Path] = None):
        """
        Initialisiert IntentValidator.
        
        Args:
            repo_path: Pfad zum Repository
        """
        self.repo_path = repo_path
    
    def validate(
        self,
        problem: ProblemCase,
        solution_description: str = "",
    ) -> IntentValidationReport:
        """
        Führt Intent Validation durch.
        
        Args:
            problem: ProblemCase mit Original-Beschreibung
            solution_description: Beschreibung der Lösung
        
        Returns:
            IntentValidationReport
        """
        report = IntentValidationReport(
            problem_id=problem.id,
            original_problem_description=problem.raw_description,
            original_intent=problem.goal_state,
        )
        
        # Analysieren ob Problem adressiert wurde
        report.problem_addressed = self._check_problem_addressed(
            problem.raw_description,
            solution_description,
        )
        
        # Analysieren ob Symptome gelöst wurden
        report.symptoms_resolved = self._check_symptoms_resolved(
            problem,
            solution_description,
        )
        
        # Analysieren ob Root-Cause behoben wurde
        report.root_cause_fixed = self._check_root_cause_fixed(
            problem,
            solution_description,
        )
        
        # Auf Side-Effects prüfen
        report.no_side_effects = self._check_no_side_effects(
            solution_description,
        )
        
        # Analyse durchführen
        report.evaluate()
        
        # Zusammenfassung
        report.analysis = self._create_analysis(report)
        
        return report
    
    def _check_problem_addressed(
        self,
        original_problem: str,
        solution_description: str,
    ) -> bool:
        """
        Prüft ob das ursprüngliche Problem adressiert wurde.
        
        Args:
            original_problem: Original-Problembeschreibung
            solution_description: Beschreibung der Lösung
        
        Returns:
            True wenn Problem adressiert wurde
        """
        # Stub: In echter Implementierung semantische Analyse
        # Hier: Einfache Heuristik
        return len(solution_description) > 0
    
    def _check_symptoms_resolved(
        self,
        problem: ProblemCase,
        solution_description: str,
    ) -> bool:
        """
        Prüft ob Symptome gelöst wurden.
        
        Args:
            problem: ProblemCase
            solution_description: Beschreibung der Lösung
        
        Returns:
            True wenn Symptome gelöst
        """
        # Stub: In echter Implementierung konkrete Metriken prüfen
        return True
    
    def _check_root_cause_fixed(
        self,
        problem: ProblemCase,
        solution_description: str,
    ) -> bool:
        """
        Prüft ob Root-Cause behoben wurde.
        
        Args:
            problem: ProblemCase
            solution_description: Beschreibung der Lösung
        
        Returns:
            True wenn Root-Cause behoben
        """
        # Stub: In echter Implementierung Diagnose-Analyse
        return True
    
    def _check_no_side_effects(
        self,
        solution_description: str,
    ) -> bool:
        """
        Prüft auf unerwünschte Nebeneffekte.
        
        Args:
            solution_description: Beschreibung der Lösung
        
        Returns:
            True wenn keine Side-Effects
        """
        # Stub: In echter Implementierung Regression-Tests
        return True
    
    def _create_analysis(self, report: IntentValidationReport) -> str:
        """
        Erstellt Analyse-Zusammenfassung.
        
        Args:
            report: IntentValidationReport
        
        Returns:
            Analyse-Text
        """
        parts = []
        
        if report.problem_addressed:
            parts.append("✅ Problem wurde adressiert")
        else:
            parts.append("❌ Problem wurde nicht adressiert")
        
        if report.symptoms_resolved:
            parts.append("✅ Symptome wurden gelöst")
        else:
            parts.append("❌ Symptome bestehen weiter")
        
        if report.root_cause_fixed:
            parts.append("✅ Root-Cause wurde behoben")
        else:
            parts.append("⚠️ Root-Cause wurde nicht behoben")
            parts.append("  → Mögliche Scheinlösung!")
        
        if report.no_side_effects:
            parts.append("✅ Keine unerwünschten Nebeneffekte")
        else:
            parts.append("⚠️ Unerwünschte Nebeneffekte erkannt")
        
        return "\n".join(parts)


def create_validator(repo_path: Optional[Path] = None):
    """
    Factory-Funktion für Validator.
    
    Args:
        repo_path: Pfad zum Repository
    
    Returns:
        Tuple aus GoalValidator und IntentValidator
    """
    return GoalValidator(repo_path), IntentValidator(repo_path)
