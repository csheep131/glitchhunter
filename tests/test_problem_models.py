"""
Tests für ProblemCase-Domänenmodell und ProblemIntake Service.

Testet das neue Problem-Solver-Modul gemäß PROBLEM_SOLVER.md Phase 1.1.
Dieses Modul ist unabhängig von bestehenden Bug/Finding-Tests.
"""

import pytest
from datetime import datetime

from src.problem.models import (
    ProblemCase,
    ProblemType,
    ProblemSeverity,
    ProblemStatus,
)
from src.problem.intake import ProblemIntake


class TestProblemType:
    """Tests für ProblemType Enum."""
    
    def test_problem_type_values(self):
        """Alle Problemtypen sind definiert."""
        assert ProblemType.BUG.value == "bug"
        assert ProblemType.RELIABILITY.value == "reliability"
        assert ProblemType.PERFORMANCE.value == "performance"
        assert ProblemType.MISSING_FEATURE.value == "missing_feature"
        assert ProblemType.WORKFLOW_GAP.value == "workflow_gap"
        assert ProblemType.INTEGRATION_GAP.value == "integration_gap"
        assert ProblemType.UX_ISSUE.value == "ux_issue"
        assert ProblemType.REFACTOR_REQUIRED.value == "refactor_required"
        assert ProblemType.UNKNOWN.value == "unknown"
    
    def test_problem_type_from_string(self):
        """Erstellung aus String-Werten."""
        assert ProblemType("bug") == ProblemType.BUG
        assert ProblemType("performance") == ProblemType.PERFORMANCE
        assert ProblemType("unknown") == ProblemType.UNKNOWN


class TestProblemSeverity:
    """Tests für ProblemSeverity Enum."""
    
    def test_severity_values(self):
        """Alle Schweregrade sind definiert."""
        assert ProblemSeverity.CRITICAL.value == "critical"
        assert ProblemSeverity.HIGH.value == "high"
        assert ProblemSeverity.MEDIUM.value == "medium"
        assert ProblemSeverity.LOW.value == "low"
    
    def test_severity_from_string(self):
        """Erstellung aus String-Werten."""
        assert ProblemSeverity("critical") == ProblemSeverity.CRITICAL
        assert ProblemSeverity("medium") == ProblemSeverity.MEDIUM


class TestProblemStatus:
    """Tests für ProblemStatus Enum."""
    
    def test_status_values(self):
        """Alle Status-Werte sind definiert."""
        assert ProblemStatus.INTAKE.value == "intake"
        assert ProblemStatus.DIAGNOSIS.value == "diagnosis"
        assert ProblemStatus.PLANNING.value == "planning"
        assert ProblemStatus.IMPLEMENTATION.value == "implementation"
        assert ProblemStatus.VALIDATION.value == "validation"
        assert ProblemStatus.CLOSED.value == "closed"
        assert ProblemStatus.ESCALATED.value == "escalated"
    
    def test_default_status_is_intake(self):
        """Standard-Status ist INTAKE."""
        assert ProblemStatus.INTAKE == ProblemStatus("intake")


class TestProblemCase:
    """Tests für ProblemCase Dataclass."""
    
    def test_minimal_creation(self):
        """Erstellung mit minimalen Required-Feldern."""
        problem = ProblemCase(
            id="prob_test_001",
            title="Test Problem",
            raw_description="Dies ist ein Testproblem",
        )
        
        assert problem.id == "prob_test_001"
        assert problem.title == "Test Problem"
        assert problem.raw_description == "Dies ist ein Testproblem"
        assert problem.problem_type == ProblemType.UNKNOWN
        assert problem.severity == ProblemSeverity.MEDIUM
        assert problem.status == ProblemStatus.INTAKE
        assert problem.source == "cli"
    
    def test_full_creation(self):
        """Erstellung mit allen Feldern."""
        problem = ProblemCase(
            id="prob_test_002",
            title="Performance Problem",
            raw_description="Die API ist sehr langsam",
            problem_type=ProblemType.PERFORMANCE,
            severity=ProblemSeverity.HIGH,
            status=ProblemStatus.DIAGNOSIS,
            goal_state="Antwortzeit unter 100ms",
            constraints=["Keine Datenbank-Änderungen", "Budget begrenzt"],
            affected_components=["api", "database"],
            evidence=[{"source": "logs", "message": "Timeout nach 30s"}],
            success_criteria=["p95 < 100ms", "Keine Timeouts"],
            risk_level="high",
            risk_factors=["Kundenbeschwerden", "Produktivsystem"],
            target_stack="stack_a",
            stack_capabilities={"async": True, "caching": True},
            source="api",
            related_findings=["finding_001"],
            related_files=["src/api/handler.py"],
        )
        
        assert problem.problem_type == ProblemType.PERFORMANCE
        assert problem.severity == ProblemSeverity.HIGH
        assert problem.status == ProblemStatus.DIAGNOSIS
        assert problem.goal_state == "Antwortzeit unter 100ms"
        assert len(problem.constraints) == 2
        assert len(problem.affected_components) == 2
        assert len(problem.evidence) == 1
        assert len(problem.success_criteria) == 2
        assert problem.risk_level == "high"
        assert len(problem.risk_factors) == 2
        assert problem.target_stack == "stack_a"
        assert problem.stack_capabilities["async"] is True
        assert problem.source == "api"
        assert len(problem.related_findings) == 1
        assert len(problem.related_files) == 1
    
    def test_to_dict(self):
        """Konvertierung zu Dictionary."""
        problem = ProblemCase(
            id="prob_test_003",
            title="Test",
            raw_description="Beschreibung",
            problem_type=ProblemType.BUG,
            severity=ProblemSeverity.MEDIUM,
            status=ProblemStatus.INTAKE,
        )
        
        result = problem.to_dict()
        
        assert result["id"] == "prob_test_003"
        assert result["title"] == "Test"
        assert result["raw_description"] == "Beschreibung"
        assert result["problem_type"] == "bug"
        assert result["severity"] == "medium"
        assert result["status"] == "intake"
        assert isinstance(result["created_at"], str)
        assert isinstance(result["updated_at"], str)
    
    def test_from_dict(self):
        """Erstellung aus Dictionary."""
        data = {
            "id": "prob_test_004",
            "title": "Import Test",
            "raw_description": "Aus Dictionary",
            "problem_type": "performance",
            "severity": "high",
            "status": "planning",
            "goal_state": "Schneller werden",
            "constraints": ["Keine Änderungen"],
            "affected_components": ["api"],
            "evidence": [],
            "success_criteria": ["< 100ms"],
            "risk_level": "medium",
            "risk_factors": [],
            "target_stack": "auto",
            "stack_capabilities": {},
            "created_at": "2026-04-15T10:00:00",
            "updated_at": "2026-04-15T11:00:00",
            "source": "cli",
            "related_findings": [],
            "related_files": [],
        }
        
        problem = ProblemCase.from_dict(data)
        
        assert problem.id == "prob_test_004"
        assert problem.title == "Import Test"
        assert problem.problem_type == ProblemType.PERFORMANCE
        assert problem.severity == ProblemSeverity.HIGH
        assert problem.status == ProblemStatus.PLANNING
        assert problem.goal_state == "Schneller werden"
    
    def test_from_dict_with_defaults(self):
        """from_dict mit fehlenden Feldern verwendet Defaults."""
        data = {
            "id": "prob_test_005",
            "title": "Minimal",
            "raw_description": "Nur Required",
        }
        
        problem = ProblemCase.from_dict(data)
        
        assert problem.problem_type == ProblemType.UNKNOWN
        assert problem.severity == ProblemSeverity.MEDIUM
        assert problem.status == ProblemStatus.INTAKE
        assert problem.source == "cli"
        assert problem.target_stack == "auto"
        assert problem.risk_level == "medium"
        assert problem.constraints == []
        assert problem.affected_components == []
    
    def test_from_dict_invalid_enum_values(self):
        """from_dict mit ungültigen Enum-Werten."""
        data = {
            "id": "prob_test_006",
            "title": "Invalid Enums",
            "raw_description": "Test",
            "problem_type": "invalid_type",
            "severity": "invalid_severity",
            "status": "invalid_status",
        }
        
        # Sollte ValueError werfen bei ungültigen Enum-Werten
        with pytest.raises(ValueError):
            ProblemCase.from_dict(data)
    
    def test_with_updates_immutability(self):
        """with_updates erstellt neue Instanz (Immutabilität)."""
        original = ProblemCase(
            id="prob_test_007",
            title="Original",
            raw_description="Beschreibung",
            status=ProblemStatus.INTAKE,
            risk_level="low",
        )
        
        updated = original.with_updates(
            status=ProblemStatus.DIAGNOSIS,
            risk_level="high",
        )
        
        # Original unverändert
        assert original.status == ProblemStatus.INTAKE
        assert original.risk_level == "low"
        
        # Aktualisierte Kopie hat neue Werte
        assert updated.status == ProblemStatus.DIAGNOSIS
        assert updated.risk_level == "high"
        
        # Unterschiedliche IDs
        assert id(original) != id(updated)
    
    def test_with_updates_timestamp(self):
        """with_updates aktualisiert updated_at Zeitstempel."""
        original = ProblemCase(
            id="prob_test_008",
            title="Original",
            raw_description="Beschreibung",
        )
        
        original_updated_at = original.updated_at
        
        import time
        time.sleep(0.01)  # Kurze Verzögerung für Zeitstempel-Unterschied
        
        updated = original.with_updates(title="Aktualisiert")
        
        assert updated.updated_at != original_updated_at
        assert updated.updated_at > original_updated_at
    
    def test_with_updates_list_copy(self):
        """with_updates erstellt Kopien von Listen."""
        original = ProblemCase(
            id="prob_test_009",
            title="Original",
            raw_description="Beschreibung",
            affected_components=["api", "db"],
        )
        
        updated = original.with_updates(
            affected_components=["ui", "frontend"]
        )
        
        # Listen sind unabhängig
        assert original.affected_components == ["api", "db"]
        assert updated.affected_components == ["ui", "frontend"]
        
        # Änderung an Original beeinflusst nicht Kopie
        original.affected_components.append("cache")
        assert "cache" not in updated.affected_components


class TestProblemIntake:
    """Tests für ProblemIntake Service."""
    
    def setup_method(self):
        """Test-Setup."""
        self.intake = ProblemIntake()
    
    def test_intake_from_text_basic(self):
        """Einfache Problemaufnahme."""
        text = "Die API ist sehr langsam bei großen Datenmengen"
        
        problem = self.intake.intake_from_text(text, source="cli")
        
        assert problem.id.startswith("prob_")
        assert problem.title == "Die API ist sehr langsam bei großen Datenmengen"
        assert problem.raw_description == text
        assert problem.problem_type == ProblemType.PERFORMANCE
        assert problem.source == "cli"
        assert "api" in problem.affected_components
    
    def test_intake_empty_text_raises(self):
        """Leerer Text wirft ValueError."""
        with pytest.raises(ValueError, match="darf nicht leer sein"):
            self.intake.intake_from_text("", source="cli")
        
        with pytest.raises(ValueError, match="darf nicht leer sein"):
            self.intake.intake_from_text("   \n   ", source="cli")
    
    def test_classify_bug(self):
        """Bug-Erkennung."""
        bug_texts = [
            "Ein Bug verursacht einen Crash",
            "Exception beim Starten der App",
            "Error beim Verarbeiten der Daten",
            "Das System ist kaputt",
        ]
        
        for text in bug_texts:
            result = self.intake._classify_problem_type(text)
            assert result == ProblemType.BUG, f"Failed for: {text}"
    
    def test_classify_performance(self):
        """Performance-Probleme erkennen."""
        perf_texts = [
            "Die API ist sehr langsam",
            "Lange Ladezeiten bei Reports",
            "Timeout nach 30 Sekunden",
            "Performance ist schlecht",
            "Hohe Latenz bei Anfragen",
        ]
        
        for text in perf_texts:
            result = self.intake._classify_problem_type(text)
            assert result == ProblemType.PERFORMANCE, f"Failed for: {text}"
    
    def test_classify_missing_feature(self):
        """Fehlende Features erkennen."""
        feature_texts = [
            "Es fehlt eine Export-Funktion",
            "Wir brauchen ein Dashboard",
            "Missing feature für Batch-Verarbeitung",
            "Sollte CSV-Import unterstützen",
        ]
        
        for text in feature_texts:
            result = self.intake._classify_problem_type(text)
            assert result == ProblemType.MISSING_FEATURE, f"Failed for: {text}"
    
    def test_classify_workflow_gap(self):
        """Workflow-Lücken erkennen."""
        workflow_texts = [
            "Manueller Schritt im Deploy-Prozess",
            "Workflow ist nicht automatisiert",
            "Mehrere Schritte nötig für einfachen Vorgang",
            "Prozess erfordert manuelle Intervention",
        ]
        
        for text in workflow_texts:
            result = self.intake._classify_problem_type(text)
            assert result == ProblemType.WORKFLOW_GAP, f"Failed for: {text}"
    
    def test_classify_ux_issue(self):
        """UX-Probleme erkennen."""
        ux_texts = [
            "Die UI ist unübersichtlich",
            "Bedienoberfläche ist verwirrend",
            "Die Ansicht ist unklar dargestellt",
            "Farben sind schlecht lesbar",
        ]
        
        for text in ux_texts:
            result = self.intake._classify_problem_type(text)
            assert result == ProblemType.UX_ISSUE, f"Failed for: {text}"
    
    def test_classify_unknown(self):
        """Unbekannte Problemtypen."""
        unknown_text = "Irgendetwas ist komisch im System"
        
        result = self.intake._classify_problem_type(unknown_text)
        assert result == ProblemType.UNKNOWN
    
    def test_extract_title_single_line(self):
        """Titel-Extraktion aus einzelner Zeile."""
        text = "Dies ist ein Problemtitel"
        result = self.intake._extract_title(text)
        assert result == "Dies ist ein Problemtitel"
    
    def test_extract_title_multiline(self):
        """Titel-Extraktion aus mehreren Zeilen."""
        text = "Erste Zeile ist der Titel\nZweite Zeile ist Beschreibung"
        result = self.intake._extract_title(text)
        assert result == "Erste Zeile ist der Titel"
    
    def test_extract_title_truncation(self):
        """Titel wird bei 80 Zeichen abgeschnitten."""
        long_text = "A" * 100
        result = self.intake._extract_title(long_text)
        assert len(result) == 80
        assert result.endswith("...")
    
    def test_identify_components_api(self):
        """API-Komponente erkennen."""
        text = "Der API-Endpoint gibt Fehler zurück"
        result = self.intake._identify_affected_components(text)
        assert "api" in result
    
    def test_identify_components_ui(self):
        """UI-Komponente erkennen."""
        text = "Das Frontend zeigt falsche Daten an"
        result = self.intake._identify_affected_components(text)
        assert "ui" in result
    
    def test_identify_components_database(self):
        """Datenbank-Komponente erkennen."""
        text = "Die Datenbank-Query ist zu langsam"
        result = self.intake._identify_affected_components(text)
        assert "database" in result
    
    def test_identify_components_scanner(self):
        """Scanner-Komponente erkennen."""
        text = "Der Scanner findet keine Probleme"
        result = self.intake._identify_affected_components(text)
        assert "scanner" in result
    
    def test_identify_components_multiple(self):
        """Mehrere Komponenten erkennen."""
        text = "API und Datenbank haben Probleme"
        result = self.intake._identify_affected_components(text)
        assert "api" in result
        assert "database" in result
    
    def test_assess_severity_critical(self):
        """Critical Schweregrad erkennen."""
        critical_texts = [
            "Kritischer Fehler im Produktivsystem",
            "Security Leak entdeckt",
            "Datenverlust aufgetreten",
            "Production ist down",
        ]
        
        for text in critical_texts:
            problem_type = self.intake._classify_problem_type(text)
            result = self.intake._assess_severity(text, problem_type)
            assert result == ProblemSeverity.CRITICAL, f"Failed for: {text}"
    
    def test_assess_severity_high(self):
        """High Schweregrad erkennen."""
        high_texts = [
            "Dringendes Problem, muss sofort gelöst werden",
            "Blocker für das Release",
            "Verhindert weitere Arbeit",
        ]
        
        for text in high_texts:
            problem_type = self.intake._classify_problem_type(text)
            result = self.intake._assess_severity(text, problem_type)
            assert result == ProblemSeverity.HIGH, f"Failed for: {text}"
    
    def test_assess_severity_low(self):
        """Low Schweregrad erkennen."""
        low_texts = [
            "Niedrige Priorität, kleine Verbesserung",
            "Nice to have Feature",
            "Kosmetisches Problem, low priority",
        ]
        
        for text in low_texts:
            problem_type = self.intake._classify_problem_type(text)
            result = self.intake._assess_severity(text, problem_type)
            assert result == ProblemSeverity.LOW, f"Failed for: {text}"
    
    def test_generate_id_format(self):
        """ID-Generierung Format."""
        id1 = self.intake._generate_id()
        id2 = self.intake._generate_id()
        
        # Format: prob_YYYYMMDD_<hex>
        assert id1.startswith("prob_")
        assert len(id1.split("_")) == 3
        
        # IDs sind eindeutig
        assert id1 != id2
    
    def test_intake_full_workflow(self):
        """Kompletter Intake-Workflow."""
        text = """
        Kritischer Performance-Probleme in der API.
        
        Die Antwortzeiten sind sehr hoch bei großen Datenmengen.
        Betroffen sind alle Datenbank-Queries.
        
        Ziel: Antwortzeit unter 100ms
        Einschränkung: Keine Schema-Änderungen möglich
        """
        
        problem = self.intake.intake_from_text(text, source="api")
        
        assert problem.id.startswith("prob_")
        assert problem.problem_type == ProblemType.PERFORMANCE
        assert problem.severity == ProblemSeverity.CRITICAL
        assert "api" in problem.affected_components
        assert "database" in problem.affected_components
        assert problem.status == ProblemStatus.INTAKE
        assert problem.source == "api"


class TestIntegration:
    """Integrationstests für ProblemCase und ProblemIntake."""
    
    def test_intake_to_dict_roundtrip(self):
        """Intake erstellt ProblemCase, Roundtrip über dict."""
        intake = ProblemIntake()
        text = "Performance Problem in der API"
        
        # Problem aufnehmen
        problem = intake.intake_from_text(text, source="cli")
        
        # Zu dict konvertieren
        data = problem.to_dict()
        
        # Aus dict wiederherstellen
        restored = ProblemCase.from_dict(data)
        
        # Werte vergleichen
        assert restored.id == problem.id
        assert restored.title == problem.title
        assert restored.problem_type == problem.problem_type
        assert restored.severity == problem.severity
        assert restored.raw_description == problem.raw_description
    
    def test_multiple_intakes_independent(self):
        """Mehrere Intakes erstellen unabhängige Probleme."""
        intake = ProblemIntake()
        
        problem1 = intake.intake_from_text("Problem A")
        problem2 = intake.intake_from_text("Problem B")
        
        assert problem1.id != problem2.id
        assert problem1.title != problem2.title
        assert problem1.raw_description != problem2.raw_description
