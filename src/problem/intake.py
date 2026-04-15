"""
Problem Intake Service für GlitchHunter Problem-Solver.

Service für die initiale Problemaufnahme. Nimmt rohe Problembeschreibungen
entgegen und erstellt daraus erste strukturierte ProblemCase-Instanzen.

Dieses Modul ist Teil des parallelen Problem-Solver-Systems und
beeinflusst NICHT das bestehende Bug-Hunting-System.

Gemäß PROBLEM_SOLVER.md Phase 1.1.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List

from .models import ProblemCase, ProblemType, ProblemSeverity, ProblemStatus


class ProblemIntake:
    """
    Service für Problemaufnahme.
    
    Nimmt rohe Problembeschreibungen entgegen und erstellt
    daraus erste ProblemCase-Strukturen mit initialer Klassifikation.
    
    Der Intake-Prozess umfasst:
    1. Extraktion eines Titels aus der Rohbeschreibung
    2. Automatische Klassifikation des Problemtyps
    3. Identifikation betroffener Komponenten
    4. Generierung einer eindeutigen ID
    5. Erstellung der ProblemCase-Instanz
    
    Example:
        intake = ProblemIntake()
        problem = intake.intake_from_text(
            "Die API ist sehr langsam bei großen Datenmengen",
            source="cli"
        )
    """
    
    def intake_from_text(self, text: str, source: str = "cli") -> ProblemCase:
        """
        Erstellt ProblemCase aus Textbeschreibung.
        
        Führt initiale Analyse der Rohbeschreibung durch und extrahiert
        relevante Informationen für die Problemklassifikation.
        
        Args:
            text: Rohbeschreibung des Problems (vom Nutzer eingegeben)
            source: Quelle der Beschreibung (cli, api, tui, file)
        
        Returns:
            ProblemCase mit erster Strukturierung und Klassifikation
        
        Raises:
            ValueError: Wenn Text leer oder nur Whitespace ist
        """
        # Validierung der Eingabe
        if not text or not text.strip():
            raise ValueError("Problembeschreibung darf nicht leer sein")
        
        # Initiale Klassifikation durchführen
        problem_type = self._classify_problem_type(text)
        
        # Titel extrahieren (erste Zeile oder Zusammenfassung)
        title = self._extract_title(text)
        
        # Erste betroffene Komponenten identifizieren
        affected = self._identify_affected_components(text)
        
        # Initiale Risikobewertung basierend auf Schweregrad
        severity = self._assess_severity(text, problem_type)
        
        return ProblemCase(
            id=self._generate_id(),
            title=title,
            raw_description=text,
            problem_type=problem_type,
            severity=severity,
            affected_components=affected,
            source=source,
        )
    
    def _classify_problem_type(self, text: str) -> ProblemType:
        """
        Führt erste Klassifikation des Problemtyps basierend auf Keywords durch.
        
        Analysiert den Text auf charakteristische Begriffe und Muster
        um den wahrscheinlichen Problemtyp zu bestimmen.
        
        Args:
            text: Zu analysierende Problembeschreibung
        
        Returns:
            ProblemType Enum-Wert
        """
        text_lower = text.lower()
        
        # Performance-Indikatoren
        performance_keywords = [
            "langsam", "slow", "performance", "dauer", "zeit",
            "latenz", "verzögerung", "timeout", "häng", "block"
        ]
        if any(word in text_lower for word in performance_keywords):
            return ProblemType.PERFORMANCE
        
        # Feature-Indikatoren (fehlende Funktionalität)
        feature_keywords = [
            "fehl", "missing", "wolle", "brauch", "feature",
            "funktion", "könn", "sollte", "unterstütz"
        ]
        if any(word in text_lower for word in feature_keywords):
            return ProblemType.MISSING_FEATURE
        
        # Workflow-Indikatoren (manuelle Prozesse, Lücken im Ablauf)
        workflow_keywords = [
            "manual", "manuell", "workflow", "schritt", "automat",
            "prozess", "ablauf", "kette", "mehrere"
        ]
        if any(word in text_lower for word in workflow_keywords):
            return ProblemType.WORKFLOW_GAP
        
        # UX-Indikatoren (Benutzerfreundlichkeit, Oberfläche)
        ux_keywords = [
            "ui", "bedien", "übersicht", "unklar", "user",
            "oberfläche", "ansicht", "darstellung", "lesbar", "farbe"
        ]
        if any(word in text_lower for word in ux_keywords):
            return ProblemType.UX_ISSUE
        
        # Zuverlässigkeits-Indikatoren
        reliability_keywords = [
            "zuverläss", "stabil", "inkonsistent", "unvorhersehbar",
            "flaky", "intermittierend", "gelegentlich"
        ]
        if any(word in text_lower for word in reliability_keywords):
            return ProblemType.RELIABILITY
        
        # Integrations-Indikatoren
        integration_keywords = [
            "integration", "schnittstelle", "api", "extern",
            "dienst", "service", "kommunikation", "verbindung"
        ]
        if any(word in text_lower for word in integration_keywords):
            return ProblemType.INTEGRATION_GAP
        
        # Refactoring-Indikatoren
        refactor_keywords = [
            "refactor", "struktur", "wartbar", "technisch",
            "schuld", "code qualität", "dupliziert"
        ]
        if any(word in text_lower for word in refactor_keywords):
            return ProblemType.REFACTOR_REQUIRED
        
        # Bug-Indikatoren (explizite Fehler)
        bug_keywords = [
            "bug", "fehler", "crash", "fail", "nicht",
            "exception", "error", "falsch", "kaputt", "defekt"
        ]
        if any(word in text_lower for word in bug_keywords):
            return ProblemType.BUG
        
        # Default: Unbekannter Typ
        return ProblemType.UNKNOWN
    
    def _extract_title(self, text: str) -> str:
        """
        Extrahiert einen kurzen, prägnanten Titel aus dem Text.
        
        Verwendet die erste Zeile oder die ersten 80 Zeichen
        als zusammenfassenden Titel.
        
        Args:
            text: Vollständige Problembeschreibung
        
        Returns:
            Kurzer Titel (maximal 80 Zeichen)
        """
        lines = text.strip().split("\n")
        if lines:
            # Erste Zeile verwenden, auf 80 Zeichen begrenzen
            title = lines[0].strip()
            if len(title) > 80:
                title = title[:77] + "..."
            return title
        
        # Fallback: Ersten Teil des Textes verwenden
        title = text.strip()[:80]
        if len(text.strip()) > 80:
            title += "..."
        return title
    
    def _identify_affected_components(self, text: str) -> List[str]:
        """
        Identifiziert erste betroffene Systemkomponenten.
        
        Durchsucht den Text nach Hinweisen auf beteiligte
        Systemteile und Module.
        
        Args:
            text: Problembeschreibung
        
        Returns:
            Liste von Komponentennamen
        """
        components = []
        text_lower = text.lower()
        
        # API-Komponente
        if any(term in text_lower for term in ["api", "endpoint", "route", "handler"]):
            components.append("api")
        
        # UI/Frontend-Komponente
        if any(term in text_lower for term in ["ui", "frontend", "oberfläche", "ansicht", "gui"]):
            components.append("ui")
        
        # Datenbank-Komponente
        if any(term in text_lower for term in ["datenbank", "db", "database", "sql", "query"]):
            components.append("database")
        
        # Scanner-Komponente
        if any(term in text_lower for term in ["scan", "scanner", "analyse", "prüfung"]):
            components.append("scanner")
        
        # Cache-Komponente
        if any(term in text_lower for term in ["cache", "puffer", "speicher"]):
            components.append("cache")
        
        # Agent/Inference-Komponente
        if any(term in text_lower for term in ["agent", "inference", "llm", "modell", "ki"]):
            components.append("agent")
        
        # Konfigurations-Komponente
        if any(term in text_lower for term in ["config", "konfig", "einstellung", "yaml"]):
            components.append("config")
        
        return components
    
    def _assess_severity(self, text: str, problem_type: ProblemType) -> ProblemSeverity:
        """
        Bewertet initiale Schweregrad des Problems.
        
        Berücksichtigt Problemtyp und spezifische Indikatoren
        im Text für eine erste Priorisierung.
        
        Args:
            text: Problembeschreibung
            problem_type: Klassifizierter Problemtyp
        
        Returns:
            ProblemSeverity Enum-Wert
        """
        text_lower = text.lower()
        
        # Critical-Indikatoren (sofortiges Handeln erforderlich)
        critical_keywords = [
            "kritisch", "critical", "notfall", "emergency",
            "produktiv", "production", "ausfall", "down",
            "datenverlust", "security", "sicherheit", "leck"
        ]
        if any(word in text_lower for word in critical_keywords):
            return ProblemSeverity.CRITICAL
        
        # High-Indikatoren (hohe Priorität)
        high_keywords = [
            "hoch", "high", "dringend", "urgent", "wichtig",
            "block", "blocker", "verhindert", "unmöglich"
        ]
        if any(word in text_lower for word in high_keywords):
            return ProblemSeverity.HIGH
        
        # Low-Indikatoren (niedrige Priorität)
        low_keywords = [
            "niedrig", "low", "klein", "minor", "kosmetik",
            "optional", "nice to have", "gelegentlich"
        ]
        if any(word in text_lower for word in low_keywords):
            return ProblemSeverity.LOW
        
        # Default basierend auf Problemtyp
        severity_by_type = {
            ProblemType.BUG: ProblemSeverity.MEDIUM,
            ProblemType.RELIABILITY: ProblemSeverity.HIGH,
            ProblemType.PERFORMANCE: ProblemSeverity.MEDIUM,
            ProblemType.MISSING_FEATURE: ProblemSeverity.LOW,
            ProblemType.WORKFLOW_GAP: ProblemSeverity.MEDIUM,
            ProblemType.INTEGRATION_GAP: ProblemSeverity.MEDIUM,
            ProblemType.UX_ISSUE: ProblemSeverity.LOW,
            ProblemType.REFACTOR_REQUIRED: ProblemSeverity.LOW,
            ProblemType.UNKNOWN: ProblemSeverity.MEDIUM,
        }
        
        return severity_by_type.get(problem_type, ProblemSeverity.MEDIUM)
    
    def _generate_id(self) -> str:
        """
        Generiert eine eindeutige ID für den ProblemCase.
        
        Format: prob_YYYYMMDD_<unique_hex>
        
        Returns:
            Eindeutige ID
        """
        date_part = datetime.now().strftime("%Y%m%d")
        unique_part = uuid.uuid4().hex[:6]
        return f"prob_{date_part}_{unique_part}"
