"""
Tests für Goal & Intent Validation.

Tests für Problem-Solver Phase 3.1:
- ValidationResult, GoalValidationReport, IntentValidationReport Models
- GoalValidator (validate, _validate_criterion)
- IntentValidator (validate, evaluate, Scheinlösung-Erkennung)
- Manager-Erweiterungen
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import json

from src.problem.models import ProblemCase, ProblemType, ProblemSeverity, ProblemStatus
from src.problem.validation import (
    ValidationStatus,
    ValidationResult,
    GoalValidationReport,
    IntentValidationReport,
    GoalValidator,
    IntentValidator,
    create_validator,
)
from src.problem.manager import ProblemManager


# =============================================================================
# Tests für ValidationStatus Enum
# =============================================================================

class TestValidationStatus:
    """Tests für ValidationStatus Enum."""

    def test_status_values(self):
        """Alle Status-Werte sind definiert."""
        assert ValidationStatus.PENDING.value == "pending"
        assert ValidationStatus.PASSED.value == "passed"
        assert ValidationStatus.FAILED.value == "failed"
        assert ValidationStatus.PARTIAL.value == "partial"
        assert ValidationStatus.BLOCKED.value == "blocked"

    def test_status_from_string(self):
        """Erstellung aus String-Werten."""
        assert ValidationStatus("pending") == ValidationStatus.PENDING
        assert ValidationStatus("passed") == ValidationStatus.PASSED
        assert ValidationStatus("failed") == ValidationStatus.FAILED
        assert ValidationStatus("partial") == ValidationStatus.PARTIAL
        assert ValidationStatus("blocked") == ValidationStatus.BLOCKED


# =============================================================================
# Tests für ValidationResult
# =============================================================================

class TestValidationResult:
    """Tests für ValidationResult Dataclass."""

    def test_minimal_creation(self):
        """Erstellung mit minimalen Feldern."""
        result = ValidationResult(
            criterion="Performance-Test",
            status=ValidationStatus.PASSED,
        )

        assert result.criterion == "Performance-Test"
        assert result.status == ValidationStatus.PASSED
        assert result.description == ""
        assert result.evidence == []
        assert result.metrics == {}
        assert result.failure_reason == ""
        assert result.remediation_steps == []

    def test_full_creation(self):
        """Erstellung mit allen Feldern."""
        result = ValidationResult(
            criterion="API Response Time",
            status=ValidationStatus.FAILED,
            description="Antwortzeit muss unter 100ms liegen",
            evidence=["p95: 150ms", "p99: 250ms"],
            metrics={"p95": 150, "p99": 250, "target": 100},
            failure_reason="Antwortzeit überschreitet Limit",
            remediation_steps=["Caching implementieren", "Query optimieren"],
        )

        assert result.criterion == "API Response Time"
        assert result.status == ValidationStatus.FAILED
        assert result.description == "Antwortzeit muss unter 100ms liegen"
        assert len(result.evidence) == 2
        assert result.metrics["p95"] == 150
        assert result.failure_reason == "Antwortzeit überschreitet Limit"
        assert len(result.remediation_steps) == 2

    def test_to_dict(self):
        """Konvertierung zu Dictionary."""
        result = ValidationResult(
            criterion="Test Criterion",
            status=ValidationStatus.PASSED,
            description="Test Description",
            evidence=["Evidence 1"],
            metrics={"key": "value"},
            failure_reason="",
            remediation_steps=["Step 1"],
        )

        result_dict = result.to_dict()

        assert result_dict["criterion"] == "Test Criterion"
        assert result_dict["status"] == "passed"
        assert result_dict["description"] == "Test Description"
        assert result_dict["evidence"] == ["Evidence 1"]
        assert result_dict["metrics"] == {"key": "value"}
        assert result_dict["failure_reason"] == ""
        assert result_dict["remediation_steps"] == ["Step 1"]

    def test_to_dict_with_failed_status(self):
        """to_dict mit Failed-Status."""
        result = ValidationResult(
            criterion="Failed Criterion",
            status=ValidationStatus.FAILED,
            failure_reason="Something went wrong",
            remediation_steps=["Fix it", "Test it"],
        )

        result_dict = result.to_dict()

        assert result_dict["status"] == "failed"
        assert result_dict["failure_reason"] == "Something went wrong"
        assert len(result_dict["remediation_steps"]) == 2


# =============================================================================
# Tests für GoalValidationReport
# =============================================================================

class TestGoalValidationReport:
    """Tests für GoalValidationReport Dataclass."""

    def test_minimal_creation(self):
        """Erstellung mit minimalen Feldern."""
        report = GoalValidationReport(
            problem_id="prob_test_001",
            solution_plan_id="plan_001",
        )

        assert report.problem_id == "prob_test_001"
        assert report.solution_plan_id == "plan_001"
        assert report.results == []
        assert report.overall_status == ValidationStatus.PENDING
        assert report.summary == ""
        assert report.validator_version == "1.0"

    def test_to_dict(self):
        """Konvertierung zu Dictionary."""
        report = GoalValidationReport(
            problem_id="prob_test_002",
            solution_plan_id="plan_002",
            summary="Test Summary",
        )

        result = report.to_dict()

        assert result["problem_id"] == "prob_test_002"
        assert result["solution_plan_id"] == "plan_002"
        assert result["results"] == []
        assert result["overall_status"] == "pending"
        assert result["summary"] == "Test Summary"
        assert result["validator_version"] == "1.0"
        assert "validated_at" in result

    def test_add_result_updates_status(self):
        """add_result aktualisiert Gesamt-Status."""
        report = GoalValidationReport(
            problem_id="prob_test_003",
            solution_plan_id="plan_003",
        )

        # Initial PENDING
        assert report.overall_status == ValidationStatus.PENDING

        # Erstes Passed-Resultat
        report.add_result(ValidationResult(
            criterion="Test 1",
            status=ValidationStatus.PASSED,
        ))
        assert report.overall_status == ValidationStatus.PASSED

        # Zweites Passed-Resultat
        report.add_result(ValidationResult(
            criterion="Test 2",
            status=ValidationStatus.PASSED,
        ))
        assert report.overall_status == ValidationStatus.PASSED

    def test_add_result_partial_failure(self):
        """add_result mit teilweisem Failure."""
        report = GoalValidationReport(
            problem_id="prob_test_004",
            solution_plan_id="plan_004",
        )

        report.add_result(ValidationResult(
            criterion="Test 1",
            status=ValidationStatus.PASSED,
        ))
        report.add_result(ValidationResult(
            criterion="Test 2",
            status=ValidationStatus.FAILED,
        ))

        assert report.overall_status == ValidationStatus.PARTIAL

    def test_add_result_all_failed(self):
        """add_result mit allen Failures."""
        report = GoalValidationReport(
            problem_id="prob_test_005",
            solution_plan_id="plan_005",
        )

        report.add_result(ValidationResult(
            criterion="Test 1",
            status=ValidationStatus.FAILED,
        ))
        report.add_result(ValidationResult(
            criterion="Test 2",
            status=ValidationStatus.FAILED,
        ))

        assert report.overall_status == ValidationStatus.FAILED

    def test_add_result_blocked(self):
        """add_result mit Blocked-Status."""
        report = GoalValidationReport(
            problem_id="prob_test_006",
            solution_plan_id="plan_006",
        )

        report.add_result(ValidationResult(
            criterion="Test 1",
            status=ValidationStatus.PASSED,
        ))
        report.add_result(ValidationResult(
            criterion="Test 2",
            status=ValidationStatus.BLOCKED,
        ))

        assert report.overall_status == ValidationStatus.BLOCKED

    def test_get_passed_count(self):
        """Zählung bestandener Validierungen."""
        report = GoalValidationReport(
            problem_id="prob_test_007",
            solution_plan_id="plan_007",
        )

        report.add_result(ValidationResult(
            criterion="Test 1",
            status=ValidationStatus.PASSED,
        ))
        report.add_result(ValidationResult(
            criterion="Test 2",
            status=ValidationStatus.PASSED,
        ))
        report.add_result(ValidationResult(
            criterion="Test 3",
            status=ValidationStatus.FAILED,
        ))

        assert report.get_passed_count() == 2

    def test_get_failed_count(self):
        """Zählung durchgefallener Validierungen."""
        report = GoalValidationReport(
            problem_id="prob_test_008",
            solution_plan_id="plan_008",
        )

        report.add_result(ValidationResult(
            criterion="Test 1",
            status=ValidationStatus.PASSED,
        ))
        report.add_result(ValidationResult(
            criterion="Test 2",
            status=ValidationStatus.FAILED,
        ))
        report.add_result(ValidationResult(
            criterion="Test 3",
            status=ValidationStatus.FAILED,
        ))

        assert report.get_failed_count() == 2

    def test_get_statistics(self):
        """Statistik-Berechnung."""
        report = GoalValidationReport(
            problem_id="prob_test_009",
            solution_plan_id="plan_009",
        )

        report.add_result(ValidationResult(
            criterion="Test 1",
            status=ValidationStatus.PASSED,
        ))
        report.add_result(ValidationResult(
            criterion="Test 2",
            status=ValidationStatus.PASSED,
        ))
        report.add_result(ValidationResult(
            criterion="Test 3",
            status=ValidationStatus.FAILED,
        ))
        report.add_result(ValidationResult(
            criterion="Test 4",
            status=ValidationStatus.PENDING,
        ))

        stats = report.get_statistics()

        assert stats["total_criteria"] == 4
        assert stats["passed"] == 2
        assert stats["failed"] == 1
        assert stats["pending"] == 1
        assert stats["blocked"] == 0
        assert stats["overall_status"] == "partial"
        assert stats["completion_percentage"] == 50.0

    def test_get_statistics_empty(self):
        """Statistik mit leerem Report."""
        report = GoalValidationReport(
            problem_id="prob_test_010",
            solution_plan_id="plan_010",
        )

        stats = report.get_statistics()

        assert stats["total_criteria"] == 0
        assert stats["passed"] == 0
        assert stats["failed"] == 0
        assert stats["completion_percentage"] == 0


# =============================================================================
# Tests für IntentValidationReport
# =============================================================================

class TestIntentValidationReport:
    """Tests für IntentValidationReport Dataclass."""

    def test_minimal_creation(self):
        """Erstellung mit minimalen Feldern."""
        report = IntentValidationReport(
            problem_id="prob_test_001",
        )

        assert report.problem_id == "prob_test_001"
        assert report.original_problem_description == ""
        assert report.original_intent == ""
        assert report.problem_addressed is False
        assert report.symptoms_resolved is False
        assert report.root_cause_fixed is False
        assert report.no_side_effects is False
        assert report.overall_status == ValidationStatus.PENDING
        assert report.concerns == []

    def test_full_creation(self):
        """Erstellung mit allen Feldern."""
        report = IntentValidationReport(
            problem_id="prob_test_002",
            original_problem_description="API ist langsam",
            original_intent="Antwortzeit unter 100ms",
            problem_addressed=True,
            symptoms_resolved=True,
            root_cause_fixed=True,
            no_side_effects=True,
            analysis="Alle Kriterien erfüllt",
        )

        assert report.original_problem_description == "API ist langsam"
        assert report.original_intent == "Antwortzeit unter 100ms"
        assert report.problem_addressed is True
        assert report.symptoms_resolved is True
        assert report.root_cause_fixed is True
        assert report.no_side_effects is True
        assert report.analysis == "Alle Kriterien erfüllt"

    def test_to_dict(self):
        """Konvertierung zu Dictionary."""
        report = IntentValidationReport(
            problem_id="prob_test_003",
            original_problem_description="Test Problem",
            problem_addressed=True,
            symptoms_resolved=False,
            root_cause_fixed=True,
            no_side_effects=True,
        )

        result = report.to_dict()

        assert result["problem_id"] == "prob_test_003"
        assert result["original_problem_description"] == "Test Problem"
        assert result["problem_addressed"] is True
        assert result["symptoms_resolved"] is False
        assert result["root_cause_fixed"] is True
        assert result["no_side_effects"] is True
        assert result["overall_status"] == "pending"
        assert "validated_at" in result

    def test_evaluate_all_passed(self):
        """evaluate mit allen positiven Kriterien."""
        report = IntentValidationReport(
            problem_id="prob_test_004",
            problem_addressed=True,
            symptoms_resolved=True,
            root_cause_fixed=True,
            no_side_effects=True,
        )

        report.evaluate()

        assert report.overall_status == ValidationStatus.PASSED
        assert len(report.concerns) == 0

    def test_evaluate_all_failed(self):
        """evaluate mit allen negativen Kriterien."""
        report = IntentValidationReport(
            problem_id="prob_test_005",
            problem_addressed=False,
            symptoms_resolved=False,
            root_cause_fixed=False,
            no_side_effects=False,
        )

        report.evaluate()

        assert report.overall_status == ValidationStatus.FAILED

    def test_evaluate_partial(self):
        """evaluate mit teilweiser Erfüllung."""
        report = IntentValidationReport(
            problem_id="prob_test_006",
            problem_addressed=True,
            symptoms_resolved=True,
            root_cause_fixed=False,
            no_side_effects=True,
        )

        report.evaluate()

        assert report.overall_status == ValidationStatus.PARTIAL

    def test_evaluate_detects_sham_solution(self):
        """evaluate erkennt Scheinlösung."""
        report = IntentValidationReport(
            problem_id="prob_test_007",
            problem_addressed=True,
            symptoms_resolved=True,
            root_cause_fixed=False,  # Root-Cause nicht behoben
            no_side_effects=True,
        )

        report.evaluate()

        assert report.overall_status == ValidationStatus.PARTIAL
        assert len(report.concerns) == 1
        assert "Scheinlösung" in report.concerns[0]
        assert "Symptom" in report.concerns[0]
        assert "Ursache" in report.concerns[0]


# =============================================================================
# Tests für GoalValidator
# =============================================================================

class TestGoalValidator:
    """Tests für GoalValidator Klasse."""

    def test_init_default(self):
        """Initialisierung ohne repo_path."""
        validator = GoalValidator()
        assert validator.repo_path is None

    def test_init_with_repo(self):
        """Initialisierung mit repo_path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = GoalValidator(repo_path=Path(tmpdir))
            assert validator.repo_path == Path(tmpdir)

    def test_validate_empty_criteria(self):
        """Validation ohne Success Criteria."""
        problem = ProblemCase(
            id="prob_test_001",
            title="Test Problem",
            raw_description="Test Beschreibung",
            success_criteria=[],  # Keine Kriterien
        )

        validator = GoalValidator()
        report = validator.validate(problem)

        assert report.problem_id == "prob_test_001"
        assert len(report.results) == 0
        assert report.overall_status == ValidationStatus.PENDING
        assert "0 Kriterien" in report.summary

    def test_validate_with_criteria(self):
        """Validation mit Success Criteria."""
        problem = ProblemCase(
            id="prob_test_002",
            title="Performance Problem",
            raw_description="API ist langsam",
            success_criteria=[
                "Antwortzeit unter 100ms",
                "Keine Timeouts",
                "p95 < 150ms",
            ],
        )

        validator = GoalValidator()
        report = validator.validate(problem)

        assert report.problem_id == "prob_test_002"
        assert len(report.results) == 3
        assert report.overall_status == ValidationStatus.PENDING

        # Alle Kriterien sollten als Pending markiert sein
        for result in report.results:
            assert result.status == ValidationStatus.PENDING
            assert "not yet implemented" in result.failure_reason

    def test_validate_with_implemented_changes(self):
        """Validation mit implementierten Änderungen."""
        problem = ProblemCase(
            id="prob_test_003",
            title="Test Problem",
            raw_description="Test",
            success_criteria=["Criterion 1"],
        )

        implemented_changes = {
            "files_changed": ["src/api/handler.py"],
            "tests_added": 5,
        }

        validator = GoalValidator()
        report = validator.validate(problem, implemented_changes=implemented_changes)

        assert report.problem_id == "prob_test_003"
        assert len(report.results) == 1
        # Stub-Implementierung ignoriert implemented_changes

    def test_validate_statistics(self):
        """Validation erstellt korrekte Statistik."""
        problem = ProblemCase(
            id="prob_test_004",
            title="Test",
            raw_description="Test",
            success_criteria=["A", "B", "C"],
        )

        validator = GoalValidator()
        report = validator.validate(problem)

        stats = report.get_statistics()
        assert stats["total_criteria"] == 3
        assert stats["passed"] == 0
        assert stats["failed"] == 0
        assert stats["pending"] == 3


# =============================================================================
# Tests für IntentValidator
# =============================================================================

class TestIntentValidator:
    """Tests für IntentValidator Klasse."""

    def test_init_default(self):
        """Initialisierung ohne repo_path."""
        validator = IntentValidator()
        assert validator.repo_path is None

    def test_init_with_repo(self):
        """Initialisierung mit repo_path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = IntentValidator(repo_path=Path(tmpdir))
            assert validator.repo_path == Path(tmpdir)

    def test_validate_empty_solution(self):
        """Validation ohne Lösung."""
        problem = ProblemCase(
            id="prob_test_001",
            title="Test Problem",
            raw_description="Original Problem Description",
            goal_state="Goal State",
        )

        validator = IntentValidator()
        report = validator.validate(problem, solution_description="")

        assert report.problem_id == "prob_test_001"
        assert report.original_problem_description == "Original Problem Description"
        assert report.original_intent == "Goal State"
        assert report.problem_addressed is False  # Leere Lösung
        
        # Stub-Implementierung: Andere Kriterien sind True (Placeholder)
        # Aber problem_addressed=False führt zu PARTIAL Status
        assert report.overall_status == ValidationStatus.PARTIAL

    def test_validate_with_solution(self):
        """Validation mit Lösung."""
        problem = ProblemCase(
            id="prob_test_002",
            title="Test Problem",
            raw_description="Original Problem",
            goal_state="Goal",
        )

        validator = IntentValidator()
        report = validator.validate(problem, solution_description="Lösung wurde implementiert")

        # Stub-Implementierung: Alle True
        assert report.problem_addressed is True
        assert report.symptoms_resolved is True
        assert report.root_cause_fixed is True
        assert report.no_side_effects is True
        assert report.overall_status == ValidationStatus.PASSED

    def test_validate_creates_analysis(self):
        """Validation erstellt Analyse."""
        problem = ProblemCase(
            id="prob_test_003",
            title="Test",
            raw_description="Problem",
            goal_state="Goal",
        )

        validator = IntentValidator()
        report = validator.validate(problem, solution_description="Lösung")

        assert report.analysis != ""
        assert "✅" in report.analysis or "❌" in report.analysis or "⚠️" in report.analysis

    def test_check_problem_addressed_empty(self):
        """_check_problem_addressed mit leerer Lösung."""
        validator = IntentValidator()
        result = validator._check_problem_addressed("Problem", "")
        assert result is False

    def test_check_problem_addressed_with_text(self):
        """_check_problem_addressed mit Text."""
        validator = IntentValidator()
        result = validator._check_problem_addressed("Problem", "Lösung")
        assert result is True

    def test_full_workflow(self):
        """Kompletter Workflow."""
        problem = ProblemCase(
            id="prob_test_004",
            title="Performance Issue",
            raw_description="API response time is too high",
            goal_state="Response time under 100ms",
            success_criteria=["p95 < 100ms"],
        )

        validator = IntentValidator()
        report = validator.validate(
            problem,
            solution_description="Implemented caching layer",
        )

        assert report.problem_id == "prob_test_004"
        assert report.original_problem_description == "API response time is too high"
        assert report.original_intent == "Response time under 100ms"
        assert report.analysis != ""


# =============================================================================
# Tests für create_validator Factory
# =============================================================================

class TestCreateValidator:
    """Tests für create_validator Factory-Funktion."""

    def test_create_without_repo(self):
        """Factory ohne repo_path."""
        goal_validator, intent_validator = create_validator()

        assert isinstance(goal_validator, GoalValidator)
        assert isinstance(intent_validator, IntentValidator)
        assert goal_validator.repo_path is None
        assert intent_validator.repo_path is None

    def test_create_with_repo(self):
        """Factory mit repo_path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            goal_validator, intent_validator = create_validator(repo_path=repo_path)

            assert isinstance(goal_validator, GoalValidator)
            assert isinstance(intent_validator, IntentValidator)
            assert goal_validator.repo_path == repo_path
            assert intent_validator.repo_path == repo_path


# =============================================================================
# Tests für ProblemManager Integration
# =============================================================================

class TestProblemManagerValidation:
    """Integrationstests für ProblemManager Validation-Methoden."""

    @pytest.fixture
    def temp_repo(self):
        """Temporäres Repository für Tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_validate_goal_problem_not_found(self, temp_repo):
        """validate_goal mit nicht existierendem Problem."""
        manager = ProblemManager(repo_path=temp_repo)

        with pytest.raises(ValueError, match="Problem.*not found"):
            manager.validate_goal("prob_nonexistent")

    def test_validate_intent_problem_not_found(self, temp_repo):
        """validate_intent mit nicht existierendem Problem."""
        manager = ProblemManager(repo_path=temp_repo)

        with pytest.raises(ValueError, match="Problem.*not found"):
            manager.validate_intent("prob_nonexistent")

    def test_validate_goal_saves_report(self, temp_repo):
        """validate_goal speichert Report."""
        manager = ProblemManager(repo_path=temp_repo)

        # Problem erstellen
        problem = manager.intake_problem(
            description="Test Problem für Validation",
            title="Test Validation",
        )

        # Validation durchführen
        report = manager.validate_goal(problem.id)

        # Report sollte gespeichert worden sein
        report_file = temp_repo / ".glitchhunter" / "problems" / f"{problem.id}_validation.json"
        assert report_file.exists()

        # Inhalt laden und prüfen
        data = json.loads(report_file.read_text())
        assert data["problem_id"] == problem.id
        assert "results" in data
        assert "overall_status" in data

    def test_validate_intent_workflow(self, temp_repo):
        """validate_intent kompletter Workflow."""
        manager = ProblemManager(repo_path=temp_repo)

        # Problem erstellen
        problem = manager.intake_problem(
            description="Performance Problem in API",
            title="API Performance",
        )

        # Intent Validation durchführen
        report = manager.validate_intent(
            problem.id,
            solution_description="Caching implementiert",
        )

        assert report.problem_id == problem.id
        assert report.original_problem_description == "Performance Problem in API"
        assert report.analysis != ""

    def test_validate_goal_with_success_criteria(self, temp_repo):
        """validate_goal mit Success Criteria."""
        manager = ProblemManager(repo_path=temp_repo)

        # Problem mit Success Criteria erstellen
        problem = ProblemCase(
            id="prob_test_validation_001",
            title="Test Problem",
            raw_description="Test Beschreibung",
            success_criteria=[
                "Criterion 1",
                "Criterion 2",
                "Criterion 3",
            ],
        )
        manager.save_problem(problem)

        # Validation durchführen
        report = manager.validate_goal(problem.id)

        assert report.problem_id == "prob_test_validation_001"
        assert len(report.results) == 3
        stats = report.get_statistics()
        assert stats["total_criteria"] == 3
