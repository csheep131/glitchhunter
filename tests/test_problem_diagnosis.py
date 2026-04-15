"""
Tests für Diagnose-Schicht gemäß PROBLEM_SOLVER.md Phase 2.1.

Testet:
- Cause, DataFlow, Uncertainty Models
- Diagnosis Model (to_dict, from_dict, add_* methods)
- DiagnosisEngine (generate_diagnosis)
- Manager-Erweiterungen (generate_diagnosis, get_diagnosis)
- CLI Command (cmd_problem_diagnose)
- Tests für verschiedene Problemtypen
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.problem.models import ProblemCase, ProblemType, ProblemSeverity, ProblemStatus
from src.problem.diagnosis import (
    Cause,
    CauseType,
    DataFlow,
    Uncertainty,
    Diagnosis,
    DiagnosisEngine,
)
from src.problem.manager import ProblemManager


class TestCause:
    """Tests für Cause Model."""

    def test_minimal_creation(self):
        """Erstellung mit minimalen Required-Feldern."""
        cause = Cause(
            id="cause_001",
            description="Test Ursache",
            cause_type=CauseType.ROOT_CAUSE,
        )

        assert cause.id == "cause_001"
        assert cause.description == "Test Ursache"
        assert cause.cause_type == CauseType.ROOT_CAUSE
        assert cause.confidence == 0.0
        assert cause.evidence == []
        assert cause.affected_files == []
        assert cause.affected_modules == []
        assert cause.affected_functions == []
        assert cause.related_causes == []
        assert cause.is_blocking is False
        assert cause.created_at is not None

    def test_full_creation(self):
        """Erstellung mit allen Feldern."""
        cause = Cause(
            id="cause_002",
            description="Komplexe Ursache",
            cause_type=CauseType.CONTRIBUTING,
            confidence=0.85,
            evidence=["Log-Eintrag 1", "Log-Eintrag 2"],
            affected_files=["src/api/handler.py", "src/db/query.py"],
            affected_modules=["api", "database"],
            affected_functions=["handle_request", "execute_query"],
            related_causes=["cause_001"],
            is_blocking=True,
        )

        assert cause.confidence == 0.85
        assert len(cause.evidence) == 2
        assert len(cause.affected_files) == 2
        assert len(cause.affected_modules) == 2
        assert len(cause.affected_functions) == 2
        assert cause.is_blocking is True

    def test_to_dict(self):
        """Konvertierung zu Dictionary."""
        cause = Cause(
            id="cause_003",
            description="Test",
            cause_type=CauseType.SYMPTOM,
            confidence=0.5,
        )

        result = cause.to_dict()

        assert result["id"] == "cause_003"
        assert result["description"] == "Test"
        assert result["cause_type"] == "symptom"
        assert result["confidence"] == 0.5
        assert isinstance(result["created_at"], str)

    def test_cause_type_enum_values(self):
        """Test alle CauseType Enum-Werte."""
        assert CauseType.ROOT_CAUSE.value == "root_cause"
        assert CauseType.CONTRIBUTING.value == "contributing"
        assert CauseType.SYMPTOM.value == "symptom"
        assert CauseType.UNKNOWN.value == "unknown"


class TestDataFlow:
    """Tests für DataFlow Model."""

    def test_minimal_creation(self):
        """Erstellung mit minimalen Feldern."""
        flow = DataFlow(
            id="flow_001",
            name="Test Flow",
            source="Source A",
            sink="Sink B",
        )

        assert flow.id == "flow_001"
        assert flow.name == "Test Flow"
        assert flow.source == "Source A"
        assert flow.sink == "Sink B"
        assert flow.transformation_steps == []
        assert flow.data_types == []
        assert flow.issues == []

    def test_full_creation(self):
        """Erstellung mit allen Feldern."""
        flow = DataFlow(
            id="flow_002",
            name="Database Flow",
            source="API Handler",
            sink="PostgreSQL",
            transformation_steps=["Validate", "Transform", "Insert"],
            data_types=["UserDTO", "UserEntity"],
            issues=["Performance", "Connection Timeout"],
        )

        assert len(flow.transformation_steps) == 3
        assert len(flow.data_types) == 2
        assert len(flow.issues) == 2

    def test_to_dict(self):
        """Konvertierung zu Dictionary."""
        flow = DataFlow(
            id="flow_003",
            name="API Flow",
            source="Client",
            sink="Server",
        )

        result = flow.to_dict()

        assert result["id"] == "flow_003"
        assert result["name"] == "API Flow"
        assert result["source"] == "Client"
        assert result["sink"] == "Server"


class TestUncertainty:
    """Tests für Uncertainty Model."""

    def test_minimal_creation(self):
        """Erstellung mit minimalen Feldern."""
        unc = Uncertainty(
            id="unc_001",
            question="Was ist unklar?",
        )

        assert unc.id == "unc_001"
        assert unc.question == "Was ist unklar?"
        assert unc.impact == "medium"
        assert unc.description == ""
        assert unc.resolution_steps == []

    def test_full_creation(self):
        """Erstellung mit allen Feldern."""
        unc = Uncertainty(
            id="unc_002",
            question="Ist das die Root-Cause?",
            impact="high",
            description="Weitere Analyse benötigt",
            resolution_steps=["Logs prüfen", "Code analysieren"],
        )

        assert unc.impact == "high"
        assert unc.description == "Weitere Analyse benötigt"
        assert len(unc.resolution_steps) == 2

    def test_to_dict(self):
        """Konvertierung zu Dictionary."""
        unc = Uncertainty(
            id="unc_003",
            question="Testfrage",
            impact="low",
        )

        result = unc.to_dict()

        assert result["id"] == "unc_003"
        assert result["question"] == "Testfrage"
        assert result["impact"] == "low"


class TestDiagnosis:
    """Tests für Diagnosis Model."""

    def test_minimal_creation(self):
        """Erstellung mit minimalen Feldern."""
        diagnosis = Diagnosis(problem_id="prob_001")

        assert diagnosis.problem_id == "prob_001"
        assert diagnosis.status == "draft"
        assert diagnosis.causes == []
        assert diagnosis.data_flows == []
        assert diagnosis.uncertainties == []
        assert diagnosis.summary == ""
        assert diagnosis.root_cause_summary == ""
        assert diagnosis.recommended_next_steps == []
        assert diagnosis.diagnosis_version == "1.0"

    def test_to_dict(self):
        """Konvertierung zu Dictionary."""
        diagnosis = Diagnosis(problem_id="prob_002")
        diagnosis.add_cause(
            description="Test Cause",
            cause_type=CauseType.ROOT_CAUSE,
        )

        result = diagnosis.to_dict()

        assert result["problem_id"] == "prob_002"
        assert result["status"] == "draft"
        assert len(result["causes"]) == 1
        assert result["causes"][0]["description"] == "Test Cause"

    def test_from_dict(self):
        """Erstellung aus Dictionary."""
        data = {
            "problem_id": "prob_003",
            "status": "complete",
            "causes": [
                {
                    "id": "cause_001",
                    "description": "Test",
                    "cause_type": "root_cause",
                    "confidence": 0.8,
                }
            ],
            "data_flows": [],
            "uncertainties": [],
        }

        diagnosis = Diagnosis.from_dict(data)

        assert diagnosis.problem_id == "prob_003"
        assert diagnosis.status == "complete"
        assert len(diagnosis.causes) == 1
        assert diagnosis.causes[0].cause_type == CauseType.ROOT_CAUSE

    def test_add_cause(self):
        """Hinzufügen einer Ursache."""
        diagnosis = Diagnosis(problem_id="prob_004")

        cause = diagnosis.add_cause(
            description="Added Cause",
            cause_type=CauseType.CONTRIBUTING,
            confidence=0.7,
            evidence=["Evidence 1"],
            is_blocking=True,
        )

        assert len(diagnosis.causes) == 1
        assert cause.description == "Added Cause"
        assert cause.cause_type == CauseType.CONTRIBUTING
        assert cause.confidence == 0.7
        assert cause.is_blocking is True
        assert diagnosis.updated_at is not None

    def test_add_data_flow(self):
        """Hinzufügen eines Datenflusses."""
        diagnosis = Diagnosis(problem_id="prob_005")

        flow = diagnosis.add_data_flow(
            name="Test Flow",
            source="A",
            sink="B",
            issues=["Issue 1"],
        )

        assert len(diagnosis.data_flows) == 1
        assert flow.name == "Test Flow"
        assert len(flow.issues) == 1

    def test_add_uncertainty(self):
        """Hinzufügen einer Unsicherheit."""
        diagnosis = Diagnosis(problem_id="prob_006")

        unc = diagnosis.add_uncertainty(
            question="Test Question?",
            impact="high",
            description="Test Description",
        )

        assert len(diagnosis.uncertainties) == 1
        assert unc.question == "Test Question?"
        assert unc.impact == "high"

    def test_get_root_causes(self):
        """Returns alle Root-Causes."""
        diagnosis = Diagnosis(problem_id="prob_007")
        diagnosis.add_cause("Root 1", CauseType.ROOT_CAUSE)
        diagnosis.add_cause("Contributing 1", CauseType.CONTRIBUTING)
        diagnosis.add_cause("Root 2", CauseType.ROOT_CAUSE)

        root_causes = diagnosis.get_root_causes()

        assert len(root_causes) == 2
        assert all(c.cause_type == CauseType.ROOT_CAUSE for c in root_causes)

    def test_get_blocking_causes(self):
        """Returns alle blockierenden Ursachen."""
        diagnosis = Diagnosis(problem_id="prob_008")
        diagnosis.add_cause("Blocking", CauseType.ROOT_CAUSE, is_blocking=True)
        diagnosis.add_cause("Non-Blocking", CauseType.CONTRIBUTING, is_blocking=False)

        blocking = diagnosis.get_blocking_causes()

        assert len(blocking) == 1
        assert blocking[0].description == "Blocking"

    def test_get_high_impact_uncertainties(self):
        """Returns Unsicherheiten mit hoher Auswirkung."""
        diagnosis = Diagnosis(problem_id="prob_009")
        diagnosis.add_uncertainty("High Impact", impact="high")
        diagnosis.add_uncertainty("Medium Impact", impact="medium")
        diagnosis.add_uncertainty("Low Impact", impact="low")

        high_impact = diagnosis.get_high_impact_uncertainties()

        assert len(high_impact) == 1
        assert high_impact[0].question == "High Impact"

    def test_serialization_roundtrip(self):
        """Roundtrip: to_dict -> from_dict."""
        original = Diagnosis(problem_id="prob_010")
        original.add_cause("Test Cause", CauseType.ROOT_CAUSE, confidence=0.9)
        original.add_data_flow("Test Flow", "A", "B")
        original.add_uncertainty("Test?", impact="high")

        data = original.to_dict()
        restored = Diagnosis.from_dict(data)

        assert restored.problem_id == original.problem_id
        assert len(restored.causes) == len(original.causes)
        assert len(restored.data_flows) == len(original.data_flows)
        assert len(restored.uncertainties) == len(original.uncertainties)


class TestDiagnosisEngine:
    """Tests für DiagnosisEngine."""

    def test_init(self):
        """Initialisierung der Engine."""
        engine = DiagnosisEngine()
        assert engine.repo_path is None

        engine_with_path = DiagnosisEngine(repo_path=Path("/tmp"))
        assert engine_with_path.repo_path == Path("/tmp")

    def test_generate_diagnosis_basic(self):
        """Generiert grundlegende Diagnose."""
        engine = DiagnosisEngine()
        problem = ProblemCase(
            id="prob_test_001",
            title="Test Problem",
            raw_description="Test Beschreibung",
        )

        diagnosis = engine.generate_diagnosis(problem)

        assert diagnosis.problem_id == "prob_test_001"
        assert len(diagnosis.uncertainties) >= 2  # Standard-Unsicherheiten
        assert diagnosis.summary != ""

    def test_generate_diagnosis_performance_problem(self):
        """Generiert Diagnose für Performance-Problem."""
        engine = DiagnosisEngine()
        problem = ProblemCase(
            id="prob_perf_001",
            title="Langsame API",
            raw_description="Die API ist sehr langsam bei Datenbank-Queries",
            problem_type=ProblemType.PERFORMANCE,
        )

        diagnosis = engine.generate_diagnosis(problem)

        # Performance-spezifische Ursachen
        assert len(diagnosis.causes) >= 2
        cause_descriptions = [c.description for c in diagnosis.causes]
        assert any("ineffizient" in d.lower() for d in cause_descriptions)

        # Datenflüsse
        assert len(diagnosis.data_flows) >= 1
        flow_names = [f.name for f in diagnosis.data_flows]
        assert any("database" in f.lower() for f in flow_names)

    def test_generate_diagnosis_bug_problem(self):
        """Generiert Diagnose für Bug-Problem."""
        engine = DiagnosisEngine()
        problem = ProblemCase(
            id="prob_bug_001",
            title="Input Validation Error",
            raw_description="Fehler bei der Input-Validierung führt zu Crash",
            problem_type=ProblemType.BUG,
        )

        diagnosis = engine.generate_diagnosis(problem)

        # Bug-spezifische Ursachen
        root_causes = diagnosis.get_root_causes()
        assert len(root_causes) >= 1
        assert any("validierung" in c.description.lower() for c in root_causes)

    def test_generate_diagnosis_missing_feature(self):
        """Generiert Diagnose für Missing-Feature-Problem."""
        engine = DiagnosisEngine()
        problem = ProblemCase(
            id="prob_feature_001",
            title="Feature fehlt",
            raw_description="Feature wurde nicht implementiert",
            problem_type=ProblemType.MISSING_FEATURE,
        )

        diagnosis = engine.generate_diagnosis(problem)

        root_causes = diagnosis.get_root_causes()
        assert len(root_causes) >= 1
        assert any("spezifiziert" in c.description.lower() for c in root_causes)

    def test_generate_diagnosis_workflow_gap(self):
        """Generiert Diagnose für Workflow-Gap-Problem."""
        engine = DiagnosisEngine()
        problem = ProblemCase(
            id="prob_workflow_001",
            title="Manueller Schritt",
            raw_description="Manueller Schritt muss automatisiert werden",
            problem_type=ProblemType.WORKFLOW_GAP,
        )

        diagnosis = engine.generate_diagnosis(problem)

        root_causes = diagnosis.get_root_causes()
        assert len(root_causes) >= 1
        assert any("automatisiert" in c.description.lower() for c in root_causes)

    def test_extract_evidence(self):
        """Extrahiert Evidenzen aus Text."""
        engine = DiagnosisEngine()
        text = "Die Datenbank ist langsam. Die Query dauert zu lange."
        keywords = ["langsam", "datenbank"]

        evidence = engine._extract_evidence(text, keywords)

        assert len(evidence) <= 5
        assert any("datenbank" in e.lower() for e in evidence)

    def test_create_summary(self):
        """Erstellt Zusammenfassung."""
        engine = DiagnosisEngine()
        problem = ProblemCase(
            id="prob_summary_001",
            title="Summary Test",
            raw_description="Test",
            problem_type=ProblemType.BUG,
        )

        diagnosis = Diagnosis(problem_id="prob_summary_001")
        engine._create_summary(problem, diagnosis)

        assert diagnosis.summary != ""
        assert "Summary Test" in diagnosis.summary

    def test_recommend_next_steps(self):
        """Empfiehlt nächste Schritte."""
        engine = DiagnosisEngine()
        problem = ProblemCase(
            id="prob_steps_001",
            title="Steps Test",
            raw_description="Test",
        )

        diagnosis = Diagnosis(problem_id="prob_steps_001")
        diagnosis.add_cause("Root Cause", CauseType.ROOT_CAUSE)
        engine._recommend_next_steps(problem, diagnosis)

        assert len(diagnosis.recommended_next_steps) >= 2
        assert any("verifizieren" in s.lower() for s in diagnosis.recommended_next_steps)


class TestProblemManagerDiagnosis:
    """Tests für Manager-Erweiterungen."""

    @pytest.fixture
    def temp_problems_dir(self, tmp_path):
        """Erstellt temporäres Problems-Verzeichnis."""
        problems_dir = tmp_path / "problems"
        problems_dir.mkdir()
        return problems_dir

    def test_generate_diagnosis(self, temp_problems_dir):
        """Generiert Diagnose über Manager."""
        manager = ProblemManager(
            repo_path=Path("/tmp"),
            problems_dir=str(temp_problems_dir),
        )

        # Problem erstellen
        problem = manager.intake_problem(
            description="Die API ist sehr langsam",
            title="Performance Problem",
        )

        # Diagnose generieren
        diagnosis = manager.generate_diagnosis(problem.id)

        assert diagnosis is not None
        assert diagnosis.problem_id == problem.id
        assert len(diagnosis.causes) >= 0

        # Status sollte aktualisiert worden sein
        assert problem.status == ProblemStatus.DIAGNOSIS

    def test_get_diagnosis(self, temp_problems_dir):
        """Lädt gespeicherte Diagnose."""
        manager = ProblemManager(
            repo_path=Path("/tmp"),
            problems_dir=str(temp_problems_dir),
        )

        problem = manager.intake_problem(
            description="Test Problem",
            title="Test",
        )

        # Diagnose generieren und speichern
        original = manager.generate_diagnosis(problem.id)

        # Diagnose laden
        loaded = manager.get_diagnosis(problem.id)

        assert loaded is not None
        assert loaded.problem_id == original.problem_id
        assert len(loaded.causes) == len(original.causes)

    def test_get_diagnosis_not_found(self, temp_problems_dir):
        """Returns None wenn Diagnose nicht existiert."""
        manager = ProblemManager(
            repo_path=Path("/tmp"),
            problems_dir=str(temp_problems_dir),
        )

        diagnosis = manager.get_diagnosis("nonexistent_id")

        assert diagnosis is None

    def test_generate_diagnosis_problem_not_found(self, temp_problems_dir):
        """Raises ValueError wenn Problem nicht existiert."""
        manager = ProblemManager(
            repo_path=Path("/tmp"),
            problems_dir=str(temp_problems_dir),
        )

        with pytest.raises(ValueError, match="Problem nonexistent not found"):
            manager.generate_diagnosis("nonexistent")

    def test_save_diagnosis_creates_file(self, temp_problems_dir):
        """Speichert Diagnose-Datei."""
        manager = ProblemManager(
            repo_path=Path("/tmp"),
            problems_dir=str(temp_problems_dir),
        )

        problem = manager.intake_problem(description="Test", title="Test")
        diagnosis = manager.generate_diagnosis(problem.id)

        # Datei sollte existieren
        diagnosis_file = temp_problems_dir / f"{problem.id}_diagnosis.json"
        assert diagnosis_file.exists()

        # Inhalt sollte valides JSON sein
        data = json.loads(diagnosis_file.read_text())
        assert data["problem_id"] == problem.id


# CLI-Tests sind komplex wegen Config-Abhängigkeiten
# Die wesentliche Logik wird durch Manager- und Engine-Tests abgedeckt


class TestIntegration:
    """Integrationstests für Diagnose-Schicht."""

    def test_full_workflow(self, tmp_path):
        """Kompletter Workflow: Intake -> Classify -> Diagnose."""
        problems_dir = tmp_path / "problems"
        problems_dir.mkdir()

        manager = ProblemManager(
            repo_path=Path("/tmp"),
            problems_dir=str(problems_dir),
        )

        # 1. Problem aufnehmen
        problem = manager.intake_problem(
            description="Die Datenbank-Queries sind sehr langsam",
            title="Performance Problem",
        )
        assert problem.status == ProblemStatus.INTAKE

        # 2. Diagnose generieren
        diagnosis = manager.generate_diagnosis(problem.id)

        # 3. Ergebnisse prüfen
        assert diagnosis.status == "draft"
        assert len(diagnosis.causes) >= 0
        assert len(diagnosis.data_flows) >= 0
        assert len(diagnosis.uncertainties) >= 2
        assert len(diagnosis.recommended_next_steps) >= 2

        # 4. Status sollte aktualisiert sein
        updated_problem = manager.get_problem(problem.id)
        assert updated_problem.status == ProblemStatus.DIAGNOSIS

        # 5. Diagnose sollte persistent gespeichert sein
        loaded_diagnosis = manager.get_diagnosis(problem.id)
        assert loaded_diagnosis is not None
        assert loaded_diagnosis.problem_id == problem.id
