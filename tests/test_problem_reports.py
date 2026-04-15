"""
Tests für ProblemReportGenerator.

Testet die Report-Generierung gemäß PROBLEM_SOLVER.md Phase 1.5.
Parallele Struktur zu bestehenden Bug-Hunting-Reports.
KEINE Änderungen an bestehenden Reports.
"""

import json
import pytest
import tempfile
from datetime import datetime
from pathlib import Path

from src.problem.models import ProblemCase, ProblemType, ProblemSeverity, ProblemStatus
from src.problem.classifier import ClassificationResult
from src.problem.reports import ProblemReportGenerator


class TestProblemReportGeneratorInit:
    """Tests für ProblemReportGenerator Initialisierung."""

    def test_init_creates_output_dir(self):
        """Initialisierung erstellt Output-Verzeichnis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "reports"
            generator = ProblemReportGenerator(output_dir=str(output_dir))
            
            assert output_dir.exists()
            assert output_dir.is_dir()

    def test_init_existing_dir(self):
        """Initialisierung mit existierendem Verzeichnis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ProblemReportGenerator(output_dir=tmpdir)
            
            assert Path(tmpdir).exists()

    def test_init_nested_dir(self):
        """Initialisierung erstellt verschachtelte Verzeichnisse."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "level1" / "level2" / "reports"
            generator = ProblemReportGenerator(output_dir=str(output_dir))
            
            assert output_dir.exists()
            assert output_dir.is_dir()


class TestGenerateProblemCaseReport:
    """Tests für generate_problem_case_report."""

    def setup_method(self):
        """Test-Setup."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.generator = ProblemReportGenerator(output_dir=self.temp_dir.name)
        
        self.test_problem = ProblemCase(
            id="prob_test_001",
            title="Test Problem",
            raw_description="Dies ist ein Testproblem",
            problem_type=ProblemType.PERFORMANCE,
            severity=ProblemSeverity.HIGH,
            status=ProblemStatus.DIAGNOSIS,
            goal_state="Antwortzeit unter 100ms",
            constraints=["Keine DB-Änderungen"],
            affected_components=["api", "database"],
            success_criteria=["p95 < 100ms"],
            risk_level="high",
            risk_factors=["Produktivsystem"],
            target_stack="stack_a",
            stack_capabilities={"async": True},
            source="cli",
            related_files=["src/api/handler.py"],
        )

    def teardown_method(self):
        """Test-Aufräumen."""
        self.temp_dir.cleanup()

    def test_generate_problem_case_report_basic(self):
        """Einfacher Problem-Case-Report ohne Klassifikation."""
        report_path = self.generator.generate_problem_case_report(self.test_problem)
        
        assert report_path.exists()
        assert report_path.name == "prob_test_001_problem_case.json"
        assert report_path.suffix == ".json"

    def test_generate_problem_case_report_json_structure(self):
        """JSON-Struktur des Reports."""
        report_path = self.generator.generate_problem_case_report(self.test_problem)
        
        with open(report_path) as f:
            data = json.load(f)
        
        # Required Felder
        assert data["id"] == "prob_test_001"
        assert data["title"] == "Test Problem"
        assert data["raw_description"] == "Dies ist ein Testproblem"
        
        # Enum-Werte als Strings
        assert data["problem_type"] == "performance"
        assert data["severity"] == "high"
        assert data["status"] == "diagnosis"
        
        # Optionale Felder
        assert data["goal_state"] == "Antwortzeit unter 100ms"
        assert data["constraints"] == ["Keine DB-Änderungen"]
        assert "api" in data["affected_components"]
        assert "database" in data["affected_components"]
        assert data["success_criteria"] == ["p95 < 100ms"]
        assert data["risk_level"] == "high"
        assert data["risk_factors"] == ["Produktivsystem"]
        assert data["target_stack"] == "stack_a"
        assert data["stack_capabilities"]["async"] is True
        assert data["source"] == "cli"
        assert data["related_files"] == ["src/api/handler.py"]

    def test_generate_problem_case_report_with_classification(self):
        """Report mit Klassifikation."""
        classification = ClassificationResult(
            problem_type=ProblemType.PERFORMANCE,
            confidence=0.85,
            keywords_found=["langsam", "performance", "api"],
            indicators={"performance": 0.7, "bug": 0.2},
            alternatives=[
                {"problem_type": "bug", "confidence": 0.2},
            ],
            affected_components=["api"],
            recommended_actions=["Performance-Messung durchführen"],
        )
        
        report_path = self.generator.generate_problem_case_report(
            self.test_problem, classification
        )
        
        with open(report_path) as f:
            data = json.load(f)
        
        # Klassifikation enthalten
        assert "classification" in data
        assert data["classification"]["problem_type"] == "performance"
        assert data["classification"]["confidence"] == 0.85
        assert "langsam" in data["classification"]["keywords_found"]
        assert data["classification"]["indicators"]["performance"] == 0.7
        assert len(data["classification"]["alternatives"]) == 1

    def test_generate_problem_case_report_metadata(self):
        """Report-Metadaten."""
        report_path = self.generator.generate_problem_case_report(self.test_problem)
        
        with open(report_path) as f:
            data = json.load(f)
        
        assert "report_metadata" in data
        assert data["report_metadata"]["report_type"] == "problem_case"
        assert data["report_metadata"]["version"] == "1.0"
        assert "generated_at" in data["report_metadata"]
        
        # ISO-8601 Format prüfen
        datetime.fromisoformat(data["report_metadata"]["generated_at"])

    def test_generate_problem_case_report_file_content(self):
        """Dateiinhalt ist gültiges JSON."""
        report_path = self.generator.generate_problem_case_report(self.test_problem)
        
        # Sollte ohne Exception lesbar sein
        content = report_path.read_text(encoding="utf-8")
        data = json.loads(content)
        
        # Indentation prüfen (2 Leerzeichen)
        assert "  " in content  # Indentation vorhanden

    def test_generate_problem_case_report_ensures_ascii_false(self):
        """Unicode-Zeichen werden korrekt gespeichert."""
        problem_with_unicode = ProblemCase(
            id="prob_unicode_001",
            title="Ü-Problem mit Äöß",
            raw_description="Beschreibung mit üñíçödé",
        )
        
        report_path = self.generator.generate_problem_case_report(problem_with_unicode)
        
        with open(report_path, encoding="utf-8") as f:
            data = json.load(f)
        
        assert data["title"] == "Ü-Problem mit Äöß"
        assert data["raw_description"] == "Beschreibung mit üñíçödé"


class TestGenerateDiagnosisStub:
    """Tests für generate_diagnosis_stub."""

    def setup_method(self):
        """Test-Setup."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.generator = ProblemReportGenerator(output_dir=self.temp_dir.name)
        
        self.test_problem = ProblemCase(
            id="prob_test_002",
            title="API Performance Problem",
            raw_description="Die API ist sehr langsam bei großen Anfragen",
            problem_type=ProblemType.PERFORMANCE,
            severity=ProblemSeverity.HIGH,
            status=ProblemStatus.DIAGNOSIS,
        )
        
        self.test_classification = ClassificationResult(
            problem_type=ProblemType.PERFORMANCE,
            confidence=0.85,
            keywords_found=["langsam", "performance", "api", "dauer"],
            indicators={"performance": 0.7},
            alternatives=[
                {"problem_type": "bug", "confidence": 0.2},
                {"problem_type": "reliability", "confidence": 0.1},
            ],
            affected_components=["api", "backend"],
            recommended_actions=[
                "Performance-Messung durchführen",
                "Bottlenecks identifizieren",
            ],
        )

    def teardown_method(self):
        """Test-Aufräumen."""
        self.temp_dir.cleanup()

    def test_generate_diagnosis_stub_basic(self):
        """Einfacher Diagnosis-Stub."""
        report_path = self.generator.generate_diagnosis_stub(
            self.test_problem, self.test_classification
        )
        
        assert report_path.exists()
        assert report_path.name == "prob_test_002_diagnosis_stub.md"
        assert report_path.suffix == ".md"

    def test_generate_diagnosis_stub_markdown_header(self):
        """Markdown-Header Struktur."""
        report_path = self.generator.generate_diagnosis_stub(
            self.test_problem, self.test_classification
        )
        
        content = report_path.read_text()
        
        # Header
        assert "# 🔍 Diagnose: API Performance Problem" in content
        assert "**Problem-ID:** prob_test_002" in content
        assert "**Generiert:**" in content
        
        # Zusammenfassung
        assert "## Zusammenfassung" in content
        assert "**Problemtyp:** performance" in content
        assert "**Confidence:** 85%" in content
        assert "**Schweregrad:** high" in content
        assert "**Status:** diagnosis" in content

    def test_generate_diagnosis_stub_keywords(self):
        """Keywords-Sektion."""
        report_path = self.generator.generate_diagnosis_stub(
            self.test_problem, self.test_classification
        )
        
        content = report_path.read_text()
        
        assert "### Gefundene Keywords" in content
        
        # Keywords als Code-Blöcke
        for kw in self.test_classification.keywords_found[:15]:
            assert f"- `{kw}`" in content

    def test_generate_diagnosis_stub_alternatives(self):
        """Alternative Klassifikationen."""
        report_path = self.generator.generate_diagnosis_stub(
            self.test_problem, self.test_classification
        )
        
        content = report_path.read_text()
        
        assert "### Alternative Einstufungen" in content
        
        for alt in self.test_classification.alternatives:
            assert f"- {alt['problem_type']} (Confidence: {alt['confidence']:.0%})" in content

    def test_generate_diagnosis_stub_components(self):
        """Betroffene Komponenten."""
        report_path = self.generator.generate_diagnosis_stub(
            self.test_problem, self.test_classification
        )
        
        content = report_path.read_text()
        
        assert "### Betroffene Komponenten" in content
        
        for comp in self.test_classification.affected_components:
            assert f"- {comp}" in content

    def test_generate_diagnosis_stub_recommended_actions(self):
        """Empfohlene Schritte."""
        report_path = self.generator.generate_diagnosis_stub(
            self.test_problem, self.test_classification
        )
        
        content = report_path.read_text()
        
        assert "## Empfohlene Nächste Schritte" in content
        
        for i, action in enumerate(self.test_classification.recommended_actions, 1):
            assert f"{i}. {action}" in content

    def test_generate_diagnosis_stub_raw_description(self):
        """Ursprüngliche Beschreibung."""
        report_path = self.generator.generate_diagnosis_stub(
            self.test_problem, self.test_classification
        )
        
        content = report_path.read_text()
        
        assert "## Ursprüngliche Beschreibung" in content
        assert self.test_problem.raw_description in content

    def test_generate_diagnosis_stub_disclaimer(self):
        """Disclaimer am Ende."""
        report_path = self.generator.generate_diagnosis_stub(
            self.test_problem, self.test_classification
        )
        
        content = report_path.read_text()
        
        assert "---" in content
        assert "*Dies ist eine automatische Erstdiagnose." in content
        assert "Eine detaillierte Analyse folgt in Phase 2.*" in content

    def test_generate_diagnosis_stub_empty_keywords(self):
        """Diagnosis-Stub ohne Keywords."""
        classification_no_keywords = ClassificationResult(
            problem_type=ProblemType.BUG,
            confidence=0.5,
            keywords_found=[],
        )
        
        report_path = self.generator.generate_diagnosis_stub(
            self.test_problem, classification_no_keywords
        )
        
        content = report_path.read_text()
        
        # Keywords-Sektion sollte nicht erscheinen
        assert "### Gefundene Keywords" not in content

    def test_generate_diagnosis_stub_empty_alternatives(self):
        """Diagnosis-Stub ohne Alternativen."""
        classification_no_alts = ClassificationResult(
            problem_type=ProblemType.BUG,
            confidence=0.5,
            keywords_found=["bug"],
            alternatives=[],
        )
        
        report_path = self.generator.generate_diagnosis_stub(
            self.test_problem, classification_no_alts
        )
        
        content = report_path.read_text()
        
        # Alternativen-Sektion sollte nicht erscheinen
        assert "### Alternative Einstufungen" not in content


class TestGenerateConstraintsReport:
    """Tests für generate_constraints_report."""

    def setup_method(self):
        """Test-Setup."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.generator = ProblemReportGenerator(output_dir=self.temp_dir.name)

    def teardown_method(self):
        """Test-Aufräumen."""
        self.temp_dir.cleanup()

    def test_generate_constraints_report_basic(self):
        """Einfacher Constraints-Report."""
        problem = ProblemCase(
            id="prob_test_003",
            title="Test Problem",
            raw_description="Test",
            constraints=["Constraint 1", "Constraint 2"],
            goal_state="Ziel",
            success_criteria=["Kriterium 1"],
            risk_factors=["Risiko 1"],
            target_stack="stack_a",
        )
        
        report_path = self.generator.generate_constraints_report(problem)
        
        assert report_path.exists()
        assert report_path.name == "prob_test_003_constraints.md"

    def test_generate_constraints_report_explicit_constraints(self):
        """Explizite Constraints."""
        problem = ProblemCase(
            id="prob_test_004",
            title="Test",
            raw_description="Test",
            constraints=["Keine DB-Änderungen", "Budget begrenzt"],
        )
        
        report_path = self.generator.generate_constraints_report(problem)
        content = report_path.read_text()
        
        assert "## Explizite Einschränkungen" in content
        assert "1. Keine DB-Änderungen" in content
        assert "2. Budget begrenzt" in content

    def test_generate_constraints_report_no_explicit_constraints(self):
        """Keine expliziten Constraints."""
        problem = ProblemCase(
            id="prob_test_005",
            title="Test",
            raw_description="Test",
            constraints=[],
        )
        
        report_path = self.generator.generate_constraints_report(problem)
        content = report_path.read_text()
        
        assert "## Explizite Einschränkungen" in content
        assert "*Keine expliziten Constraints angegeben.*" in content

    def test_generate_constraints_report_implicit_performance(self):
        """Implizite Constraints für Performance-Probleme."""
        problem = ProblemCase(
            id="prob_perf_001",
            title="Performance Problem",
            raw_description="Langsam",
            problem_type=ProblemType.PERFORMANCE,
        )
        
        report_path = self.generator.generate_constraints_report(problem)
        content = report_path.read_text()
        
        assert "## Implizite Einschränkungen" in content
        assert "Lösung darf keine signifikante zusätzliche Latenz verursachen" in content
        assert "Speicherverbrauch sollte nicht exponentiell wachsen" in content

    def test_generate_constraints_report_implicit_reliability(self):
        """Implizite Constraints für Reliability-Probleme."""
        problem = ProblemCase(
            id="prob_rel_001",
            title="Reliability Problem",
            raw_description="Instabil",
            problem_type=ProblemType.RELIABILITY,
        )
        
        report_path = self.generator.generate_constraints_report(problem)
        content = report_path.read_text()
        
        assert "Lösung muss unter allen Betriebsbedingungen stabil sein" in content
        assert "Fehlertoleranz muss gewährleistet sein" in content

    def test_generate_constraints_report_implicit_missing_feature(self):
        """Implizite Constraints für Missing Features."""
        problem = ProblemCase(
            id="prob_feat_001",
            title="Missing Feature",
            raw_description="Feature fehlt",
            problem_type=ProblemType.MISSING_FEATURE,
        )
        
        report_path = self.generator.generate_constraints_report(problem)
        content = report_path.read_text()
        
        assert "Feature muss konsistent mit existierender Architektur sein" in content
        assert "Dokumentation muss mitgeliefert werden" in content

    def test_generate_constraints_report_implicit_workflow_gap(self):
        """Implizite Constraints für Workflow Gaps."""
        problem = ProblemCase(
            id="prob_wf_001",
            title="Workflow Gap",
            raw_description="Manueller Schritt",
            problem_type=ProblemType.WORKFLOW_GAP,
        )
        
        report_path = self.generator.generate_constraints_report(problem)
        content = report_path.read_text()
        
        assert "Automatisierung muss manuelle Schritte vollständig ersetzen" in content
        assert "Ausnahmen müssen erkennbar und eskalierbar sein" in content

    def test_generate_constraints_report_implicit_ux_issue(self):
        """Implizite Constraints für UX Issues."""
        problem = ProblemCase(
            id="prob_ux_001",
            title="UX Issue",
            raw_description="UI unübersichtlich",
            problem_type=ProblemType.UX_ISSUE,
        )
        
        report_path = self.generator.generate_constraints_report(problem)
        content = report_path.read_text()
        
        assert "Lösung muss intuitiv bedienbar bleiben" in content
        assert "Bestehende Workflows dürfen nicht gebrochen werden" in content

    def test_generate_constraints_report_implicit_bug(self):
        """Implizite Constraints für Bugs."""
        problem = ProblemCase(
            id="prob_bug_001",
            title="Bug",
            raw_description="Fehler im System",
            problem_type=ProblemType.BUG,
        )
        
        report_path = self.generator.generate_constraints_report(problem)
        content = report_path.read_text()
        
        assert "Fix darf keine Regressionen verursachen" in content
        assert "Bestehende Tests müssen weiterhin bestehen" in content

    def test_generate_constraints_report_always_includes_stack_constraint(self):
        """Stack-Constraint wird immer hinzugefügt."""
        problem = ProblemCase(
            id="prob_test_006",
            title="Test",
            raw_description="Test",
            problem_type=ProblemType.UNKNOWN,
        )
        
        report_path = self.generator.generate_constraints_report(problem)
        content = report_path.read_text()
        
        assert "Lösung muss im gewählten Stack umsetzbar sein" in content

    def test_generate_constraints_report_goal_state(self):
        """Zielzustand-Sektion."""
        problem = ProblemCase(
            id="prob_test_007",
            title="Test",
            raw_description="Test",
            goal_state="Antwortzeit unter 100ms",
        )
        
        report_path = self.generator.generate_constraints_report(problem)
        content = report_path.read_text()
        
        assert "## Zielzustand" in content
        assert "Antwortzeit unter 100ms" in content

    def test_generate_constraints_report_success_criteria(self):
        """Erfolgskriterien-Sektion."""
        problem = ProblemCase(
            id="prob_test_008",
            title="Test",
            raw_description="Test",
            success_criteria=["p95 < 100ms", "Keine Timeouts"],
        )
        
        report_path = self.generator.generate_constraints_report(problem)
        content = report_path.read_text()
        
        assert "## Erfolgskriterien" in content
        assert "1. p95 < 100ms" in content
        assert "2. Keine Timeouts" in content

    def test_generate_constraints_report_risk_factors(self):
        """Risikofaktoren-Sektion."""
        problem = ProblemCase(
            id="prob_test_009",
            title="Test",
            raw_description="Test",
            risk_factors=["Kundenbeschwerden", "Produktivsystem"],
        )
        
        report_path = self.generator.generate_constraints_report(problem)
        content = report_path.read_text()
        
        assert "## Risikofaktoren" in content
        assert "1. Kundenbeschwerden" in content
        assert "2. Produktivsystem" in content

    def test_generate_constraints_report_stack_info(self):
        """Stack-Informationen."""
        problem = ProblemCase(
            id="prob_test_010",
            title="Test",
            raw_description="Test",
            target_stack="stack_a",
            stack_capabilities={"async": True, "caching": False},
        )
        
        report_path = self.generator.generate_constraints_report(problem)
        content = report_path.read_text()
        
        assert "## Stack-Zuordnung" in content
        assert "**Ziel-Stack:** stack_a" in content
        assert "### Stack-spezifische Fähigkeiten" in content
        assert "- async: True" in content
        assert "- caching: False" in content

    def test_generate_constraints_report_disclaimer(self):
        """Disclaimer am Ende."""
        problem = ProblemCase(
            id="prob_test_011",
            title="Test",
            raw_description="Test",
        )
        
        report_path = self.generator.generate_constraints_report(problem)
        content = report_path.read_text()
        
        assert "---" in content
        assert "*Constraints können sich während der Diagnose präzisieren.*" in content


class TestGenerateAllReports:
    """Tests für generate_all_reports."""

    def setup_method(self):
        """Test-Setup."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.generator = ProblemReportGenerator(output_dir=self.temp_dir.name)
        
        self.test_problem = ProblemCase(
            id="prob_test_012",
            title="Complete Test",
            raw_description="Vollständiger Test",
            problem_type=ProblemType.PERFORMANCE,
        )
        
        self.test_classification = ClassificationResult(
            problem_type=ProblemType.PERFORMANCE,
            confidence=0.8,
            keywords_found=["performance"],
            recommended_actions=["Test"],
        )

    def teardown_method(self):
        """Test-Aufräumen."""
        self.temp_dir.cleanup()

    def test_generate_all_reports_with_classification(self):
        """Alle Reports mit Klassifikation."""
        reports = self.generator.generate_all_reports(
            self.test_problem, self.test_classification
        )
        
        assert "problem_case" in reports
        assert "diagnosis_stub" in reports
        assert "constraints" in reports
        
        # Alle Pfade existieren
        assert reports["problem_case"].exists()
        assert reports["diagnosis_stub"].exists()
        assert reports["constraints"].exists()

    def test_generate_all_reports_without_classification(self):
        """Alle Reports ohne Klassifikation."""
        reports = self.generator.generate_all_reports(self.test_problem)
        
        assert "problem_case" in reports
        assert "constraints" in reports
        
        # Diagnosis-Stub nur mit Klassifikation
        assert "diagnosis_stub" not in reports
        
        # Existierende Pfade
        assert reports["problem_case"].exists()
        assert reports["constraints"].exists()

    def test_generate_all_reports_file_naming(self):
        """Dateibenennung konsistent."""
        reports = self.generator.generate_all_reports(
            self.test_problem, self.test_classification
        )
        
        assert reports["problem_case"].name == "prob_test_012_problem_case.json"
        assert reports["diagnosis_stub"].name == "prob_test_012_diagnosis_stub.md"
        assert reports["constraints"].name == "prob_test_012_constraints.md"

    def test_generate_all_reports_returns_dict(self):
        """Rückgabewert ist Dict."""
        reports = self.generator.generate_all_reports(self.test_problem)
        
        assert isinstance(reports, dict)
        assert all(isinstance(k, str) for k in reports.keys())
        assert all(isinstance(v, Path) for v in reports.values())


class TestImplicitConstraintsDerivation:
    """Tests für _derive_implicit_constraints."""

    def setup_method(self):
        """Test-Setup."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.generator = ProblemReportGenerator(output_dir=self.temp_dir.name)

    def teardown_method(self):
        """Test-Aufräumen."""
        self.temp_dir.cleanup()

    def test_derive_implicit_constraints_returns_list(self):
        """Rückgabetyp ist Liste."""
        problem = ProblemCase(
            id="prob_test",
            title="Test",
            raw_description="Test",
            problem_type=ProblemType.UNKNOWN,
        )
        
        constraints = self.generator._derive_implicit_constraints(problem)
        
        assert isinstance(constraints, list)
        assert all(isinstance(c, str) for c in constraints)

    def test_derive_implicit_constraints_unknown_type(self):
        """UNKNOWN Typ hat nur Stack-Constraint."""
        problem = ProblemCase(
            id="prob_test",
            title="Test",
            raw_description="Test",
            problem_type=ProblemType.UNKNOWN,
        )
        
        constraints = self.generator._derive_implicit_constraints(problem)
        
        assert len(constraints) == 1
        assert "Lösung muss im gewählten Stack umsetzbar sein" in constraints

    def test_derive_implicit_constraints_integration_gap(self):
        """Implizite Constraints für Integration Gap."""
        problem = ProblemCase(
            id="prob_int_001",
            title="Integration Gap",
            raw_description="Integration fehlt",
            problem_type=ProblemType.INTEGRATION_GAP,
        )
        
        constraints = self.generator._derive_implicit_constraints(problem)
        
        # Integration Gap hat keine spezifischen Constraints, nur Stack
        assert "Lösung muss im gewählten Stack umsetzbar sein" in constraints

    def test_derive_implicit_constraints_refactor_required(self):
        """Implizite Constraints für Refactor Required."""
        problem = ProblemCase(
            id="prob_ref_001",
            title="Refactor Required",
            raw_description="Code muss refaktoriert werden",
            problem_type=ProblemType.REFACTOR_REQUIRED,
        )
        
        constraints = self.generator._derive_implicit_constraints(problem)
        
        # Refactor hat keine spezifischen Constraints, nur Stack
        assert "Lösung muss im gewählten Stack umsetzbar sein" in constraints
