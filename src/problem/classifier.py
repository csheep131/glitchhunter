"""
Problem Classifier für GlitchHunter Problem-Solver.

Detaillierte Problemklassifikation gemäß PROBLEM_SOLVER.md Phase 1.2.
Dieses Modul geht über die initiale Klassifikation hinaus und analysiert
Probleme tiefer für bessere Zuordnung.

Parallele Struktur zum bestehenden Bug-Hunting-System.
KEINE Änderungen an bestehenden Klassifikations-Modellen.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path

from .models import ProblemCase, ProblemType, ProblemSeverity


@dataclass
class ClassificationResult:
    """
    Ergebnis der detaillierten Problemklassifikation.
    
    Enthält umfassende Analyseergebnisse inklusive Confidence-Scores,
    alternativen Klassifikationen und empfohlenen nächsten Schritten.
    
    Attributes:
        problem_type: Primärer klassifizierter Problemtyp
        confidence: Confidence-Score zwischen 0.0 und 1.0
        keywords_found: Liste der gefundenen relevanten Keywords
        indicators: Dictionary mit Scores pro Problemtyp
        alternatives: Alternative Klassifikationen mit niedrigerer Confidence
        affected_components: Identifizierte betroffene Komponenten
        affected_files: Betroffene Dateien (falls analysiert)
        recommended_actions: Empfohlene nächste Analyseschritte
    """
    
    problem_type: ProblemType
    confidence: float  # 0.0 - 1.0
    
    # Detaillierte Analyse
    keywords_found: List[str] = field(default_factory=list)
    indicators: Dict[str, float] = field(default_factory=dict)
    
    # Alternative Klassifikationen mit niedrigerer Confidence
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    
    # Betroffene Bereiche
    affected_components: List[str] = field(default_factory=list)
    affected_files: List[str] = field(default_factory=list)
    
    # Empfohlene nächste Schritte
    recommended_actions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Konvertiert ClassificationResult zu Dictionary.
        
        Returns:
            Serialisierbares Dictionary mit allen Attributen
        """
        return {
            "problem_type": self.problem_type.value,
            "confidence": self.confidence,
            "keywords_found": self.keywords_found,
            "indicators": self.indicators,
            "alternatives": self.alternatives,
            "affected_components": self.affected_components,
            "affected_files": self.affected_files,
            "recommended_actions": self.recommended_actions,
        }


class ProblemClassifier:
    """
    Detaillierter Problemklassifikator für GlitchHunter.
    
    Geht über die initiale Klassifikation (ProblemIntake) hinaus und
    analysiert Probleme tiefer für präzisere Zuordnung.
    
    Features:
    - Erweiterte Keyword-Analyse mit gewichteten Scores
    - Code-Kontext-Analyse (falls Repository verfügbar)
    - Confidence-Berechnung mit mehreren Faktoren
    - Alternative Klassifikationen für Unsicherheit
    - Komponentenerkennung mit erweiterter Heuristik
    - Kontextspezifische Handlungsempfehlungen
    
    Example:
        classifier = ProblemClassifier(repo_path=Path("/path/to/repo"))
        result = classifier.classify(problem_case)
        print(f"Typ: {result.problem_type}, Confidence: {result.confidence}")
    """
    
    def __init__(self, repo_path: Optional[Path] = None):
        """
        Initialisiert den ProblemClassifier.
        
        Args:
            repo_path: Optionaler Pfad zum Repository für Code-Analyse.
                      Wenn None, wird nur Text-Analyse durchgeführt.
        """
        self.repo_path = repo_path
        self.codebase_context = None
        
        # Keyword-Katalog für verschiedene Problemtypen
        self.keywords = self._build_keyword_catalog()
    
    def classify(self, problem: ProblemCase) -> ClassificationResult:
        """
        Führt detaillierte Problemklassifikation durch.
        
        Analysiert das Problem umfassend mittels:
        1. Text-Analyse der Rohbeschreibung
        2. Keyword-Matching mit gewichteten Scores
        3. Code-Kontext-Analyse (falls Repo verfügbar)
        4. Confidence-Berechnung aus allen Faktoren
        5. Identifikation alternativer Klassifikationen
        6. Verfeinerung betroffener Komponenten
        7. Empfehlung konkreter nächster Schritte
        
        Args:
            problem: Zu klassifizierendes ProblemCase-Objekt
        
        Returns:
            ClassificationResult mit detaillierter Analyse
        """
        # Text-Analyse vorbereiten
        text = problem.raw_description.lower()
        
        # Keyword-Analyse durchführen
        keyword_matches = self._analyze_keywords(text)
        
        # Code-Analyse falls Repository verfügbar
        if self.repo_path:
            code_indicators = self._analyze_code_context(problem)
        else:
            code_indicators = {}
        
        # Confidence-Score berechnen
        confidence = self._calculate_confidence(keyword_matches, code_indicators)
        
        # Alternative Klassifikationen finden
        alternatives = self._find_alternatives(keyword_matches)
        
        # Betroffene Komponenten verfeinern
        affected = self._identify_affected_components(
            text,
            problem.affected_components
        )
        
        # Empfohlene Aktionen bestimmen
        recommended_actions = self._recommend_actions(problem.problem_type, affected)
        
        return ClassificationResult(
            problem_type=problem.problem_type,
            confidence=confidence,
            keywords_found=keyword_matches.get("matched", []),
            indicators={**keyword_matches.get("scores", {}), **code_indicators},
            alternatives=alternatives,
            affected_components=affected,
            affected_files=problem.related_files,
            recommended_actions=recommended_actions,
        )
    
    def classify_text(self, text: str) -> ClassificationResult:
        """
        Klassifiziert reinen Text ohne bestehendes ProblemCase.
        
        Erstellt intern ein temporäres ProblemCase-Objekt und führt
        dann die normale Klassifikation durch.
        
        Args:
            text: Problembeschreibung als Text
        
        Returns:
            ClassificationResult mit Analyseergebnissen
        
        Raises:
            ValueError: Wenn Text leer oder nur Whitespace ist
        """
        # Validierung
        if not text or not text.strip():
            raise ValueError("Text darf nicht leer sein")
        
        # Temporäres ProblemCase erstellen
        from .intake import ProblemIntake
        intake = ProblemIntake()
        temp_problem = intake.intake_from_text(text)
        
        # Normale Klassifikation durchführen
        return self.classify(temp_problem)
    
    def _build_keyword_catalog(self) -> Dict[ProblemType, List[str]]:
        """
        Buildet Keyword-Katalog für alle Problemtypen.
        
        Returns:
            Dictionary mapping ProblemType zu Keyword-Listen
        """
        return {
            ProblemType.PERFORMANCE: [
                "langsam", "slow", "performance", "dauer", "zeit", "latenz",
                "timeout", "häng", "freeze", "verzögerung", "optimier",
                "speicher", "cpu", "auslastung", "ineffizient", "block",
                "antwortzeit", "throughput", "skalier"
            ],
            ProblemType.RELIABILITY: [
                "zuverlässig", "reliability", "stabil", "instabil", "crash",
                "absturz", "fehleranfällig", "ausfall", "verfügbarkeit",
                "inkonsistent", "unvorhersehbar", "flaky", "intermittierend"
            ],
            ProblemType.MISSING_FEATURE: [
                "fehl", "missing", "wolle", "brauch", "feature", "funktion",
                "support", "unterstütz", "export", "import", "automatisch",
                "könn", "sollte", "möglichkeit", "option"
            ],
            ProblemType.WORKFLOW_GAP: [
                "manuell", "manual", "workflow", "schritt", "automat",
                "prozess", "ablauf", "wiederhol", "jedes mal", "kette",
                "mehrere", "hintereinander", "kopier"
            ],
            ProblemType.INTEGRATION_GAP: [
                "integration", "schnittstell", "api", "connect", "sync",
                "datenübertrag", "format", "konvertier", "kompatibel",
                "extern", "dienst", "service", "kommunikation", "protokoll"
            ],
            ProblemType.UX_ISSUE: [
                "ui", "bedien", "übersicht", "unklar", "user", "intuitiv",
                "verwirr", "kompliziert", "umständlich", "klick", "menü",
                "oberfläche", "ansicht", "darstellung", "lesbar", "farbe",
                "frontend", "gui", "navigation"
            ],
            ProblemType.BUG: [
                "bug", "fehler", "fail", "nicht", "falsch", "broken",
                "defekt", "funktions", "exception", "error", "crash",
                "kaputt", "exception", "traceback", "stacktrace"
            ],
            ProblemType.REFACTOR_REQUIRED: [
                "refactor", "struktur", "code", "wartbar", "tech debt",
                "qualität", "duplizier", "unübersichtlich", "technisch",
                "schuld", "clean", "architektur", "modular"
            ],
        }
    
    def _analyze_keywords(self, text: str) -> Dict[str, Any]:
        """
        Analysiert Text auf Keyword-Matches für alle Problemtypen.
        
        Durchsucht den Text nach allen Keywords aus dem Katalog und
        berechnet Scores pro Problemtyp basierend auf Match-Ratio.
        
        Args:
            text: Zu analysierender Text (bereits lowercase)
        
        Returns:
            Dictionary mit:
            - matched: Liste aller gefundenen Keywords
            - scores: Dictionary mit Score pro Problemtyp (0.0-1.0)
        """
        matched = []
        scores = {}
        
        for problem_type, keywords in self.keywords.items():
            type_matches = []
            for keyword in keywords:
                if keyword in text:
                    type_matches.append(keyword)
                    if keyword not in matched:
                        matched.append(keyword)
            
            # Score basierend auf Match-Ratio
            if type_matches and keywords:
                scores[problem_type.value] = len(type_matches) / len(keywords)
        
        return {
            "matched": list(set(matched)),
            "scores": scores,
        }
    
    def _calculate_confidence(
        self,
        keyword_matches: Dict,
        code_indicators: Dict,
    ) -> float:
        """
        Berechnet Gesamt-Confidence-Score aus allen Faktoren.
        
        Basis-Confidence kommt aus Keyword-Matches.
        Bonus aus Code-Analyse falls verfügbar.
        
        Args:
            keyword_matches: Ergebnisse der Keyword-Analyse
            code_indicators: Ergebnisse der Code-Kontext-Analyse
        
        Returns:
            Confidence-Score zwischen 0.0 und 0.95
        """
        # Basis-Confidence aus Keyword-Matches
        num_matches = len(keyword_matches.get("matched", []))
        
        # Lineare Skalierung: 3+ Matches = 0.3 Basis, jedes weitere +0.05
        base_confidence = min(0.3 + (num_matches * 0.05), 0.7)
        
        # Bonus aus Code-Analyse (10% pro Indikator)
        code_bonus = len(code_indicators) * 0.1
        
        # Gesamt-Confidence (max 0.95)
        total_confidence = min(base_confidence + code_bonus, 0.95)
        
        return round(total_confidence, 2)
    
    def _find_alternatives(
        self,
        keyword_matches: Dict,
    ) -> List[Dict[str, Any]]:
        """
        Findet alternative Klassifikationen basierend auf Keyword-Scores.
        
        Identifiziert die Top-3 alternativen Problemtypen mit der
        höchsten Score (ausgeschlossen der primäre Typ).
        
        Args:
            keyword_matches: Ergebnisse der Keyword-Analyse mit Scores
        
        Returns:
            Liste von Dictionaries mit problem_type und confidence
        """
        alternatives = []
        scores = keyword_matches.get("scores", {})
        
        # Nach Scores sortieren (absteigend)
        sorted_types = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Top 3 alternative Problemtypen (Skip first = primary type)
        for problem_type_value, score in sorted_types[1:4]:
            alternatives.append({
                "problem_type": problem_type_value,
                "confidence": round(score, 2),
            })
        
        return alternatives
    
    def _identify_affected_components(
        self,
        text: str,
        existing: List[str],
    ) -> List[str]:
        """
        Verfeinert und erweitert die Liste betroffener Komponenten.
        
        Durchsucht Text nach zusätzlichen Komponentenhinweisen und
        kombiniert mit bereits bekannten Komponenten.
        
        Args:
            text: Problembeschreibung (wird intern zu lowercase konvertiert)
            existing: Bereits bekannte betroffene Komponenten
        
        Returns:
            Erweiterte Liste betroffener Komponenten (dedupliziert, sortiert)
        """
        components = set(existing)
        text_lower = text.lower()
        
        # Erweiterte Komponentenerkennung mit spezifischen Keywords
        component_keywords = {
            "scanner": ["scan", "analyse", "find", "detect", "prüfung"],
            "api": ["api", "endpoint", "route", "request", "response", "handler"],
            "ui": ["ui", "frontend", "oberfläch", "anzeige", "button", "gui", "menü"],
            "database": ["datenbank", "db", "query", "sql", "table", "schema"],
            "config": ["config", "einstellung", "parameter", "yaml", "konfig"],
            "logging": ["log", "report", "alert", "monitor", "trace"],
            "cache": ["cache", "puffer", "speicher", "redis", "memcached"],
            "agent": ["agent", "inference", "llm", "modell", "ki", "ai"],
        }
        
        for component, keywords in component_keywords.items():
            if any(kw in text_lower for kw in keywords):
                components.add(component)
        
        return sorted(list(components))
    
    def _recommend_actions(
        self,
        problem_type: ProblemType,
        affected: List[str],
    ) -> List[str]:
        """
        Empfiehlt kontextspezifische nächste Analyseschritte.
        
        Generiert maßgeschneiderte Handlungsempfehlungen basierend
        auf Problemtyp und betroffenen Komponenten.
        
        Args:
            problem_type: Klassifizierter Problemtyp
            affected: Liste betroffener Komponenten
        
        Returns:
            Liste von Handlungsempfehlungen
        """
        actions = []
        
        # Typspezifische Aktionen
        if problem_type == ProblemType.PERFORMANCE:
            actions.append("Performance-Messung durchführen")
            actions.append("Bottlenecks identifizieren")
            if "database" in affected:
                actions.append("Database-Queries analysieren")
            if "api" in affected:
                actions.append("API-Response-Zeiten messen")
            if "cache" in affected:
                actions.append("Cache-Hit-Ratio prüfen")
        
        elif problem_type == ProblemType.MISSING_FEATURE:
            actions.append("Anforderungen detailliert dokumentieren")
            actions.append("Betroffene Use Cases identifizieren")
            actions.append("Existierende ähnliche Features prüfen")
            actions.append("Priorität mit Stakeholdern klären")
        
        elif problem_type == ProblemType.WORKFLOW_GAP:
            actions.append("Workflow schrittweise dokumentieren")
            actions.append("Automatisierungspotential bewerten")
            actions.append("Manuelle Schritte identifizieren")
            actions.append("ROI der Automatisierung berechnen")
        
        elif problem_type == ProblemType.INTEGRATION_GAP:
            actions.append("Schnittstellen-Spezifikation prüfen")
            actions.append("Datenformate analysieren")
            actions.append("Protokoll-Kompatibilität testen")
            actions.append("Fehlerbehandlung dokumentieren")
        
        elif problem_type == ProblemType.UX_ISSUE:
            actions.append("User-Feedback sammeln")
            actions.append("Usability-Test durchführen")
            actions.append("Best Practices vergleichen")
            actions.append("Accessibility prüfen")
        
        elif problem_type == ProblemType.BUG:
            actions.append("Reproduktionsschritte dokumentieren")
            actions.append("Betroffene Code-Pfade analysieren")
            actions.append("Logs und Error-Messages auswerten")
            actions.append("Unit-Tests für Regression hinzufügen")
        
        elif problem_type == ProblemType.RELIABILITY:
            actions.append("Fehlermuster analysieren")
            actions.append("Monitoring-Daten auswerten")
            actions.append("Retry-Mechanismen prüfen")
            actions.append("Fallback-Strategien dokumentieren")
        
        elif problem_type == ProblemType.REFACTOR_REQUIRED:
            actions.append("Code-Quality-Metriken analysieren")
            actions.append("Tech-Debt quantifizieren")
            actions.append("Refactoring-Prioritäten setzen")
            actions.append("Test-Abdeckung prüfen")
        
        # Immer hinzufügen: Stack-Zuordnung
        actions.append("Zuständigen Stack identifizieren")
        
        return actions
    
    def _analyze_code_context(
        self,
        problem: ProblemCase,
    ) -> Dict[str, float]:
        """
        Analysiert Code-Kontext falls Repository verfügbar ist.
        
        Durchsucht betroffene Dateien nach relevanten Mustern und
        extrahiert zusätzliche Indikatoren für die Klassifikation.
        
        Args:
            problem: ProblemCase mit Kontext-Informationen
        
        Returns:
            Dictionary mit Code-basierten Indikatoren
        """
        indicators = {}
        
        # Nur wenn repo_path gesetzt
        if not self.repo_path:
            return indicators
        
        # Einfache Heuristiken basierend auf Problem-Beschreibung
        text = problem.raw_description.lower()
        
        # Nach betroffenen Dateien suchen (falls angegeben)
        for file_path in problem.related_files:
            full_path = self.repo_path / file_path
            if full_path.exists():
                try:
                    content = full_path.read_text(encoding="utf-8").lower()
                    
                    # Performance-Indikatoren im Code
                    if any(kw in content for kw in ["while true", "sleep", "timeout", "lock"]):
                        indicators["code_performance_risk"] = 0.5
                    
                    # Error-Handling-Indikatoren
                    if "try:" in content and "except" not in content:
                        indicators["code_error_handling_gap"] = 0.3
                    
                    # Komplexitäts-Indikatoren
                    nesting_depth = content.count("    ") // content.count("\n") if "\n" in content else 0
                    if nesting_depth > 4:
                        indicators["code_complexity_high"] = 0.4
                
                except (IOError, UnicodeDecodeError):
                    # Datei nicht lesbar - ignorieren
                    pass
        
        # Component-basierte Indikatoren
        for component in problem.affected_components:
            if component == "database":
                indicators["database_context"] = 0.3
            elif component == "api":
                indicators["api_context"] = 0.3
        
        return indicators
