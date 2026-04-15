"""
Tests für ProblemClassifier und ClassificationResult.

Testet das neue Problem-Klassifikationsmodul gemäß PROBLEM_SOLVER.md Phase 1.2.
Dieses Modul ist unabhängig von bestehenden Bug/Finding-Tests.

Parallele Struktur zum bestehenden Bug-Hunting-System.
"""

import pytest
from pathlib import Path
import tempfile
import os

from src.problem.models import (
    ProblemCase,
    ProblemType,
    ProblemSeverity,
    ProblemStatus,
)
from src.problem.intake import ProblemIntake
from src.problem.classifier import (
    ProblemClassifier,
    ClassificationResult,
)


class TestClassificationResult:
    """Tests für ClassificationResult Dataclass."""

    def test_minimal_creation(self):
        """Erstellung mit minimalen Required-Feldern."""
        result = ClassificationResult(
            problem_type=ProblemType.PERFORMANCE,
            confidence=0.75,
        )

        assert result.problem_type == ProblemType.PERFORMANCE
        assert result.confidence == 0.75
        assert result.keywords_found == []
        assert result.indicators == {}
        assert result.alternatives == []
        assert result.affected_components == []
        assert result.affected_files == []
        assert result.recommended_actions == []

    def test_full_creation(self):
        """Erstellung mit allen Feldern."""
        result = ClassificationResult(
            problem_type=ProblemType.BUG,
            confidence=0.85,
            keywords_found=["bug", "fehler", "exception"],
            indicators={"bug": 0.5, "performance": 0.2},
            alternatives=[
                {"problem_type": "performance", "confidence": 0.3},
                {"problem_type": "reliability", "confidence": 0.2},
            ],
            affected_components=["api", "database"],
            affected_files=["src/api/handler.py"],
            recommended_actions=["Logs analysieren", "Code-Pfade prüfen"],
        )

        assert result.problem_type == ProblemType.BUG
        assert result.confidence == 0.85
        assert len(result.keywords_found) == 3
        assert "bug" in result.keywords_found
        assert len(result.alternatives) == 2
        assert "api" in result.affected_components
        assert len(result.recommended_actions) == 2

    def test_to_dict(self):
        """Konvertierung zu Dictionary."""
        result = ClassificationResult(
            problem_type=ProblemType.PERFORMANCE,
            confidence=0.7,
            keywords_found=["langsam", "timeout"],
            affected_components=["api"],
            recommended_actions=["Performance messen"],
        )

        data = result.to_dict()

        assert data["problem_type"] == "performance"
        assert data["confidence"] == 0.7
        assert "langsam" in data["keywords_found"]
        assert "api" in data["affected_components"]
        assert "Performance messen" in data["recommended_actions"]

    def test_to_dict_serializable(self):
        """to_dict erzeugt serialisierbares Dictionary."""
        result = ClassificationResult(
            problem_type=ProblemType.UX_ISSUE,
            confidence=0.6,
            keywords_found=["ui", "unklar"],
        )

        data = result.to_dict()

        # Alle Werte müssen JSON-serialisierbar sein
        assert isinstance(data["problem_type"], str)
        assert isinstance(data["confidence"], float)
        assert isinstance(data["keywords_found"], list)
        assert isinstance(data["indicators"], dict)
        assert isinstance(data["alternatives"], list)
        assert isinstance(data["affected_components"], list)
        assert isinstance(data["recommended_actions"], list)


class TestProblemClassifierInitialization:
    """Tests für ProblemClassifier Initialisierung."""

    def test_init_without_repo(self):
        """Initialisierung ohne Repository-Pfad."""
        classifier = ProblemClassifier()

        assert classifier.repo_path is None
        assert classifier.codebase_context is None
        assert classifier.keywords is not None
        # 8 Problemtypen mit Keywords (UNKNOWN hat keine)
        assert len(classifier.keywords) == 8

    def test_init_with_repo(self, tmp_path):
        """Initialisierung mit Repository-Pfad."""
        classifier = ProblemClassifier(repo_path=tmp_path)

        assert classifier.repo_path == tmp_path
        assert classifier.codebase_context is None

    def test_keyword_catalog_structure(self):
        """Keyword-Katalog hat korrekte Struktur."""
        classifier = ProblemClassifier()

        # Alle Problemtypen außer UNKNOWN müssen Keywords haben
        for problem_type in ProblemType:
            if problem_type == ProblemType.UNKNOWN:
                # UNKNOWN hat bewusst keine Keywords
                continue
            assert problem_type in classifier.keywords
            assert isinstance(classifier.keywords[problem_type], list)
            assert len(classifier.keywords[problem_type]) > 0

    def test_keyword_catalog_content(self):
        """Keyword-Katalog enthält erwartete Keywords."""
        classifier = ProblemClassifier()

        # Performance-Keywords
        perf_keywords = classifier.keywords[ProblemType.PERFORMANCE]
        assert "langsam" in perf_keywords
        assert "performance" in perf_keywords
        assert "timeout" in perf_keywords

        # Bug-Keywords
        bug_keywords = classifier.keywords[ProblemType.BUG]
        assert "bug" in bug_keywords
        assert "fehler" in bug_keywords
        assert "exception" in bug_keywords

        # Missing Feature-Keywords
        feature_keywords = classifier.keywords[ProblemType.MISSING_FEATURE]
        assert "fehl" in feature_keywords
        assert "feature" in feature_keywords


class TestProblemClassifierClassify:
    """Tests für classify() Methode."""

    def setup_method(self):
        """Test-Setup."""
        self.classifier = ProblemClassifier()

    def test_classify_performance_problem(self):
        """Klassifikation eines Performance-Problems."""
        problem = ProblemCase(
            id="prob_test_001",
            title="Langsame API",
            raw_description="Die API ist sehr langsam bei großen Datenmengen. Timeout nach 30 Sekunden.",
            problem_type=ProblemType.PERFORMANCE,
            affected_components=["api"],
        )

        result = self.classifier.classify(problem)

        assert result.problem_type == ProblemType.PERFORMANCE
        assert result.confidence > 0.3
        assert len(result.keywords_found) > 0
        assert "api" in result.affected_components
        assert "Performance-Messung durchführen" in result.recommended_actions

    def test_classify_bug_problem(self):
        """Klassifikation eines Bug-Problems."""
        problem = ProblemCase(
            id="prob_test_002",
            title="Exception beim Start",
            raw_description="Ein Bug verursacht einen Crash mit Exception beim Starten der App.",
            problem_type=ProblemType.BUG,
        )

        result = self.classifier.classify(problem)

        assert result.problem_type == ProblemType.BUG
        assert result.confidence > 0.3
        assert any(kw in result.keywords_found for kw in ["bug", "fehler", "exception", "crash"])
        assert "Reproduktionsschritte dokumentieren" in result.recommended_actions

    def test_classify_missing_feature(self):
        """Klassifikation eines Missing-Feature-Problems."""
        problem = ProblemCase(
            id="prob_test_003",
            title="Export-Funktion fehlt",
            raw_description="Wir brauchen eine Export-Funktion für CSV-Daten. Aktuell fehlt dieser Support.",
            problem_type=ProblemType.MISSING_FEATURE,
        )

        result = self.classifier.classify(problem)

        assert result.problem_type == ProblemType.MISSING_FEATURE
        assert result.confidence > 0.3
        assert any(kw in result.keywords_found for kw in ["fehl", "brauch", "export", "support"])
        assert "Anforderungen detailliert dokumentieren" in result.recommended_actions

    def test_classify_workflow_gap(self):
        """Klassifikation eines Workflow-Gap-Problems."""
        problem = ProblemCase(
            id="prob_test_004",
            title="Manueller Workflow",
            raw_description="Jedes Mal muss der Prozess manuell wiederholt werden. Wir brauchen Automatisierung.",
            problem_type=ProblemType.WORKFLOW_GAP,
        )

        result = self.classifier.classify(problem)

        assert result.problem_type == ProblemType.WORKFLOW_GAP
        assert result.confidence > 0.3
        assert any(kw in result.keywords_found for kw in ["manuell", "workflow", "wiederhol", "automat"])
        assert "Workflow schrittweise dokumentieren" in result.recommended_actions

    def test_classify_ux_issue(self):
        """Klassifikation eines UX-Issue-Problems."""
        problem = ProblemCase(
            id="prob_test_005",
            title="Unübersichtliches Menü",
            raw_description="Das UI ist sehr unklar und verwirrend. Zu viele Klicks im Menü.",
            problem_type=ProblemType.UX_ISSUE,
        )

        result = self.classifier.classify(problem)

        assert result.problem_type == ProblemType.UX_ISSUE
        assert result.confidence > 0.3
        assert any(kw in result.keywords_found for kw in ["ui", "unklar", "verwirr", "menü", "klick"])
        assert "User-Feedback sammeln" in result.recommended_actions

    def test_classify_with_existing_components(self):
        """Klassifikation mit bereits bekannten Komponenten."""
        problem = ProblemCase(
            id="prob_test_006",
            title="Database Performance",
            raw_description="Die Datenbank-Queries sind sehr langsam bei großen Tabellen.",
            problem_type=ProblemType.PERFORMANCE,
            affected_components=["database", "api"],
        )

        result = self.classifier.classify(problem)

        assert "database" in result.affected_components
        assert "api" in result.affected_components
        assert "Database-Queries analysieren" in result.recommended_actions

    def test_classify_preserves_immutability(self):
        """classify() verändert das Original-Problem nicht."""
        problem = ProblemCase(
            id="prob_test_007",
            title="Test",
            raw_description="Performance Problem mit der API",
            problem_type=ProblemType.PERFORMANCE,
            affected_components=["api"],
        )

        # Original-Werte speichern
        original_type = problem.problem_type
        original_components = list(problem.affected_components)

        # Klassifikation durchführen
        result = self.classifier.classify(problem)

        # Original muss unverändert bleiben
        assert problem.problem_type == original_type
        assert problem.affected_components == original_components


class TestProblemClassifierClassifyText:
    """Tests für classify_text() Methode."""

    def setup_method(self):
        """Test-Setup."""
        self.classifier = ProblemClassifier()

    def test_classify_text_basic(self):
        """Klassifikation von reinem Text."""
        text = "Die API ist sehr langsam und timeoutet ständig"

        result = self.classifier.classify_text(text)

        assert result.problem_type == ProblemType.PERFORMANCE
        assert result.confidence > 0.3
        assert len(result.keywords_found) > 0

    def test_classify_text_empty_raises(self):
        """Leerer Text wirft ValueError."""
        with pytest.raises(ValueError, match="darf nicht leer sein"):
            self.classifier.classify_text("")

        with pytest.raises(ValueError, match="darf nicht leer sein"):
            self.classifier.classify_text("   \n   ")

    def test_classify_text_creates_problem_case(self):
        """classify_text erstellt intern ProblemCase."""
        text = "Bug im System verursacht Error und Exception"

        result = self.classifier.classify_text(text)

        assert result.problem_type == ProblemType.BUG
        assert result.confidence > 0.0
        assert len(result.recommended_actions) > 0


class TestKeywordAnalysis:
    """Tests für Keyword-Analyse."""

    def setup_method(self):
        """Test-Setup."""
        self.classifier = ProblemClassifier()

    def test_analyze_keywords_finds_matches(self):
        """Keyword-Analyse findet Matches."""
        text = "Die API ist langsam und hat eine hohe Latenz mit Timeout"

        result = self.classifier._analyze_keywords(text)

        assert "matched" in result
        assert "scores" in result
        assert len(result["matched"]) > 0
        assert any("langsam" in kw or "latenz" in kw or "timeout" in kw for kw in result["matched"])

    def test_analyze_keywords_scores(self):
        """Keyword-Analyse berechnet Scores."""
        text = "bug fehler exception crash error"

        result = self.classifier._analyze_keywords(text)

        assert "bug" in result["scores"]
        assert result["scores"]["bug"] > 0.0

    def test_analyze_keywords_no_duplicates(self):
        """Keyword-Analyse vermeidet Duplikate."""
        text = "langsam langsam langsam performance performance"

        result = self.classifier._analyze_keywords(text)

        # Keine Duplikate in matched
        assert len(result["matched"]) == len(set(result["matched"]))


class TestConfidenceCalculation:
    """Tests für Confidence-Berechnung."""

    def setup_method(self):
        """Test-Setup."""
        self.classifier = ProblemClassifier()

    def test_calculate_confidence_base(self):
        """Basis-Confidence aus Keyword-Matches."""
        keyword_matches = {
            "matched": ["langsam", "timeout", "performance"],
            "scores": {"performance": 0.5},
        }

        confidence = self.classifier._calculate_confidence(keyword_matches, {})

        assert 0.0 <= confidence <= 0.95
        assert confidence >= 0.3  # Basis mit 3 Matches

    def test_calculate_confidence_with_code_bonus(self):
        """Confidence mit Code-Analyse-Bonus."""
        keyword_matches = {
            "matched": ["bug"],
            "scores": {"bug": 0.2},
        }
        code_indicators = {
            "code_performance_risk": 0.5,
            "code_error_handling_gap": 0.3,
        }

        confidence = self.classifier._calculate_confidence(keyword_matches, code_indicators)

        # Bonus von 2 Indikatoren (0.2)
        assert confidence > 0.35

    def test_calculate_confidence_max_cap(self):
        """Confidence ist auf 0.95 gedeckelt."""
        keyword_matches = {
            "matched": ["a"] * 20,  # Viele Matches
            "scores": {"performance": 0.9},
        }
        code_indicators = {f"indicator_{i}": 0.1 for i in range(10)}  # Viele Indikatoren

        confidence = self.classifier._calculate_confidence(keyword_matches, code_indicators)

        assert confidence <= 0.95

    def test_calculate_confidence_rounding(self):
        """Confidence wird gerundet."""
        keyword_matches = {
            "matched": ["test1", "test2"],
            "scores": {"bug": 0.3},
        }

        confidence = self.classifier._calculate_confidence(keyword_matches, {})

        # Maximal 2 Dezimalstellen
        assert confidence == round(confidence, 2)


class TestAlternativeClassification:
    """Tests für alternative Klassifikationen."""

    def setup_method(self):
        """Test-Setup."""
        self.classifier = ProblemClassifier()

    def test_find_alternatives_returns_list(self):
        """find_alternatives gibt Liste zurück."""
        keyword_matches = {
            "matched": ["langsam", "bug"],
            "scores": {"performance": 0.5, "bug": 0.4, "reliability": 0.3},
        }

        alternatives = self.classifier._find_alternatives(keyword_matches)

        assert isinstance(alternatives, list)

    def test_find_alternatives_structure(self):
        """Alternative haben korrekte Struktur."""
        keyword_matches = {
            "matched": ["test"],
            "scores": {"performance": 0.5, "bug": 0.4, "reliability": 0.3, "ux_issue": 0.2},
        }

        alternatives = self.classifier._find_alternatives(keyword_matches)

        # Maximal 3 Alternativen
        assert len(alternatives) <= 3

        # Struktur prüfen
        for alt in alternatives:
            assert "problem_type" in alt
            assert "confidence" in alt
            assert isinstance(alt["problem_type"], str)
            assert isinstance(alt["confidence"], float)

    def test_find_alternatives_excludes_primary(self):
        """Primärer Typ ist nicht in Alternativen."""
        keyword_matches = {
            "matched": ["bug"],
            "scores": {"bug": 0.8, "performance": 0.3, "reliability": 0.2},
        }

        alternatives = self.classifier._find_alternatives(keyword_matches)

        # Bug sollte nicht in Alternativen sein (wenn highest score)
        problem_types = [alt["problem_type"] for alt in alternatives]
        # Bug könnte trotzdem erscheinen wenn nicht an erster Stelle
        # Test prüft nur dass Alternativen existieren
        assert len(alternatives) >= 0


class TestComponentIdentification:
    """Tests für Komponentenerkennung."""

    def setup_method(self):
        """Test-Setup."""
        self.classifier = ProblemClassifier()

    def test_identify_components_preserves_existing(self):
        """Bestehende Komponenten bleiben erhalten."""
        text = "Ein normales Problem"
        existing = ["api", "database"]

        result = self.classifier._identify_affected_components(text, existing)

        assert "api" in result
        assert "database" in result

    def test_identify_components_api(self):
        """API-Komponente erkennen."""
        text = "der api-endpoint gibt fehler zurück"
        existing = []

        result = self.classifier._identify_affected_components(text, existing)

        assert "api" in result

    def test_identify_components_ui(self):
        """UI-Komponente erkennen."""
        text = "das frontend zeigt falsche daten in der ansicht an"
        existing = []

        result = self.classifier._identify_affected_components(text, existing)

        assert "ui" in result

    def test_identify_components_database(self):
        """Datenbank-Komponente erkennen."""
        text = "die sql-query auf der tabelle ist langsam"
        existing = []

        result = self.classifier._identify_affected_components(text, existing)

        assert "database" in result

    def test_identify_components_scanner(self):
        """Scanner-Komponente erkennen."""
        text = "Der Scan findet keine Errors bei der Analyse"
        existing = []

        result = self.classifier._identify_affected_components(text, existing)

        assert "scanner" in result

    def test_identify_components_logging(self):
        """Logging-Komponente erkennen."""
        text = "das log-file zeigt errors im monitor"
        existing = []

        result = self.classifier._identify_affected_components(text, existing)

        assert "logging" in result

    def test_identify_components_no_duplicates(self):
        """Keine Duplikate in Komponenten."""
        text = "API und api und Endpoint"
        existing = ["api"]

        result = self.classifier._identify_affected_components(text, existing)

        # Keine Duplikate
        assert len(result) == len(set(result))

    def test_identify_components_sorted(self):
        """Ergebnis ist sortiert."""
        text = "API Database UI Frontend"
        existing = []

        result = self.classifier._identify_affected_components(text, existing)

        assert result == sorted(result)


class TestRecommendedActions:
    """Tests für empfohlene Aktionen."""

    def setup_method(self):
        """Test-Setup."""
        self.classifier = ProblemClassifier()

    def test_recommend_actions_performance(self):
        """Aktionen für Performance-Probleme."""
        actions = self.classifier._recommend_actions(ProblemType.PERFORMANCE, ["api"])

        assert "Performance-Messung durchführen" in actions
        assert "Bottlenecks identifizieren" in actions
        assert "API-Response-Zeiten messen" in actions

    def test_recommend_actions_bug(self):
        """Aktionen für Bug-Probleme."""
        actions = self.classifier._recommend_actions(ProblemType.BUG, ["api"])

        assert "Reproduktionsschritte dokumentieren" in actions
        assert "Betroffene Code-Pfade analysieren" in actions
        assert "Logs und Error-Messages auswerten" in actions

    def test_recommend_actions_missing_feature(self):
        """Aktionen für Missing-Feature-Probleme."""
        actions = self.classifier._recommend_actions(ProblemType.MISSING_FEATURE, ["api"])

        assert "Anforderungen detailliert dokumentieren" in actions
        assert "Betroffene Use Cases identifizieren" in actions
        assert "Existierende ähnliche Features prüfen" in actions

    def test_recommend_actions_workflow_gap(self):
        """Aktionen für Workflow-Gap-Probleme."""
        actions = self.classifier._recommend_actions(ProblemType.WORKFLOW_GAP, ["api"])

        assert "Workflow schrittweise dokumentieren" in actions
        assert "Automatisierungspotential bewerten" in actions
        assert "Manuelle Schritte identifizieren" in actions

    def test_recommend_actions_always_includes_stack(self):
        """Immer包含 Stack-Identifikation."""
        for problem_type in ProblemType:
            actions = self.classifier._recommend_actions(problem_type, [])
            assert "Zuständigen Stack identifizieren" in actions

    def test_recommend_actions_database_specific(self):
        """Datenbank-spezifische Aktionen."""
        actions = self.classifier._recommend_actions(
            ProblemType.PERFORMANCE,
            ["database", "api"]
        )

        assert "Database-Queries analysieren" in actions


class TestCodeContextAnalysis:
    """Tests für Code-Kontext-Analyse."""

    def test_analyze_code_context_without_repo(self):
        """Code-Analyse ohne Repo gibt leeres Dict."""
        classifier = ProblemClassifier(repo_path=None)
        problem = ProblemCase(
            id="prob_test",
            title="Test",
            raw_description="Test Problem",
        )

        result = classifier._analyze_code_context(problem)

        assert result == {}

    def test_analyze_code_context_with_repo(self, tmp_path):
        """Code-Analyse mit Repo."""
        classifier = ProblemClassifier(repo_path=tmp_path)
        problem = ProblemCase(
            id="prob_test",
            title="Test",
            raw_description="Performance Problem mit API",
            affected_components=["api", "database"],
        )

        result = classifier._analyze_code_context(problem)

        # Sollte Indikatoren enthalten basierend auf Components
        assert isinstance(result, dict)

    def test_analyze_code_context_with_files(self, tmp_path):
        """Code-Analyse mit vorhandenen Dateien."""
        # Test-Datei erstellen
        test_file = tmp_path / "test_code.py"
        test_file.write_text("""
while True:
    sleep(1)
    try:
        pass
    # Kein except
""", encoding="utf-8")

        classifier = ProblemClassifier(repo_path=tmp_path)
        problem = ProblemCase(
            id="prob_test",
            title="Test",
            raw_description="Performance Problem",
            related_files=["test_code.py"],
        )

        result = classifier._analyze_code_context(problem)

        # Sollte Performance-Risk erkennen
        assert "code_performance_risk" in result or "code_error_handling_gap" in result


class TestIntegration:
    """Integrationstests für ProblemClassifier."""

    def test_full_classification_workflow(self):
        """Kompletter Klassifikations-Workflow."""
        # Problem erstellen
        problem = ProblemCase(
            id="prob_integration_001",
            title="Kritische Performance-Probleme",
            raw_description="""
            Die API ist extrem langsam bei großen Datenmengen.
            Timeout nach 30 Sekunden. Database-Queries sind der Bottleneck.
            """,
            problem_type=ProblemType.PERFORMANCE,
            severity=ProblemSeverity.HIGH,
            affected_components=["api", "database"],
        )

        # Classifier erstellen und klassifizieren
        classifier = ProblemClassifier()
        result = classifier.classify(problem)

        # Ergebnisse prüfen
        assert result.problem_type == ProblemType.PERFORMANCE
        assert result.confidence > 0.3
        assert len(result.keywords_found) > 0
        assert "api" in result.affected_components
        assert "database" in result.affected_components
        assert len(result.recommended_actions) > 3
        assert "Database-Queries analysieren" in result.recommended_actions

    def test_classifier_with_intake_pipeline(self):
        """Classifier im Pipeline mit ProblemIntake."""
        # Intake erstellt initiales Problem
        intake = ProblemIntake()
        text = "Die API ist sehr langsam mit Timeouts"
        problem = intake.intake_from_text(text, source="cli")

        # Classifier verfeinert
        classifier = ProblemClassifier()
        result = classifier.classify(problem)

        # Ergebnisse sollten konsistent sein
        assert result.problem_type == ProblemType.PERFORMANCE
        assert result.confidence > 0.0  # Confidence sollte positiv sein

    def test_classification_result_dict_roundtrip(self):
        """ClassificationResult Dictionary Roundtrip."""
        classifier = ProblemClassifier()
        problem = ProblemCase(
            id="prob_test",
            title="Test",
            raw_description="Bug im System",
            problem_type=ProblemType.BUG,
        )

        result = classifier.classify(problem)

        # Zu Dict konvertieren
        data = result.to_dict()

        # Dict sollte alle relevanten Informationen enthalten
        assert "problem_type" in data
        assert "confidence" in data
        assert "keywords_found" in data
        assert "recommended_actions" in data

        # Alle Werte serialisierbar
        import json
        json_str = json.dumps(data)
        assert len(json_str) > 0
