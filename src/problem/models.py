"""
ProblemCase-Domänenmodell für GlitchHunter Problem-Solver.

Dieses Modul definiert das Hauptmodell für die Problem-Solver-Domäne.
Es ist parallel zu bestehenden Bug/Finding-Modellen aufgebaut und
verändert diese NICHT.

Gemäß PROBLEM_SOLVER.md Phase 1.1.
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path


class ProblemType(Enum):
    """
    Problemtypen gemäß PROBLEM_SOLVER.md.
    
    Klassifiziert die Art des identifizierten Problems
    für korrekte Weiterleitung an zuständige Subsysteme.
    """
    BUG = "bug"
    RELIABILITY = "reliability"
    PERFORMANCE = "performance"
    MISSING_FEATURE = "missing_feature"
    WORKFLOW_GAP = "workflow_gap"
    INTEGRATION_GAP = "integration_gap"
    UX_ISSUE = "ux_issue"
    REFACTOR_REQUIRED = "refactor_required"
    UNKNOWN = "unknown"


class ProblemSeverity(Enum):
    """
    Schweregrad des Problems.
    
    Bestimmt Priorität und Ressourcenallokation.
    """
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProblemStatus(Enum):
    """
    Status des Problems im Lösungsworkflow.
    
    Durchläuft verschiedene Phasen von der Aufnahme bis zum Abschluss.
    """
    INTAKE = "intake"  # Gerade aufgenommen, erste Klassifikation
    DIAGNOSIS = "diagnosis"  # In Diagnose, detaillierte Analyse
    PLANNING = "planning"  # In Planung, Lösung wird entworfen
    IMPLEMENTATION = "implementation"  # In Umsetzung, Lösung wird implementiert
    VALIDATION = "validation"  # In Validierung, Lösung wird getestet
    CLOSED = "closed"  # Abgeschlossen, erfolgreich gelöst
    ESCALATED = "escalated"  # Eskaliert, benötigt externe Intervention


@dataclass
class ProblemCase:
    """
    Hauptmodell für Problem-Solver.
    
    Beschreibt einen vollständigen Problemkontext parallel zu
    bestehenden Bug/Finding-Modellen. Ein ProblemCase repräsentiert
    einen ganzheitlichen Problemauftrag von der Aufnahme bis zur Lösung.
    
    Attributes:
        id: Eindeutige Identifikations-ID (z.B. "prob_20260415_001")
        title: Kurzer, prägnanter Titel des Problems
        raw_description: Unverarbeitete Rohbeschreibung des Nutzers
    
    Klassifikation:
        problem_type: Typ des Problems (Bug, Performance, etc.)
        severity: Schweregrad (Critical, High, Medium, Low)
        status: Aktueller Status im Lösungsworkflow
    
    Problem-Details:
        goal_state: Beschreibung des gewünschten Zielzustands
        constraints: Liste von Einschränkungen/Randbedingungen
        affected_components: Betroffene Systemkomponenten
        evidence: Erste Hinweise/Belege für das Problem
    
    Erfolgskriterien:
        success_criteria: Messbare Kriterien für erfolgreichen Abschluss
    
    Risikobewertung:
        risk_level: Gesamtrisikostufe (low, medium, high, critical)
        risk_factors: Spezifische Risikofaktoren
    
    Stack-Zuordnung:
        target_stack: Ziel-Stack für Lösung ("stack_a", "stack_b", "auto")
        stack_capabilities: Fähigkeiten/Anforderungen an den Stack
    
    Metadaten:
        created_at: ISO-8601 Zeitstempel der Erstellung
        updated_at: ISO-8601 Zeitstempel der letzten Aktualisierung
        source: Quelle der Problembeschreibung (cli, api, tui, file)
    
    Verweise:
        related_findings: IDs verwandter Findings aus Bug-Hunting
        related_files: Pfade zu relevanten Dateien
    """
    
    # Identifikation
    id: str
    title: str
    raw_description: str
    
    # Klassifikation
    problem_type: ProblemType = ProblemType.UNKNOWN
    severity: ProblemSeverity = ProblemSeverity.MEDIUM
    status: ProblemStatus = ProblemStatus.INTAKE
    
    # Problem-Details
    goal_state: str = ""
    constraints: List[str] = field(default_factory=list)
    affected_components: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    
    # Erfolgskriterien
    success_criteria: List[str] = field(default_factory=list)
    
    # Risikobewertung
    risk_level: str = "medium"
    risk_factors: List[str] = field(default_factory=list)
    
    # Stack-Zuordnung
    target_stack: str = "auto"
    stack_capabilities: Dict[str, Any] = field(default_factory=dict)
    
    # Metadaten
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = "cli"
    
    # Verweise auf verwandte Artefakte
    related_findings: List[str] = field(default_factory=list)
    related_files: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """
        Konvertiert ProblemCase zu Dictionary für JSON-Export.
        
        Wandelt Enum-Werte in ihre String-Repräsentationen um
        für serialisierbare Ausgabe.
        
        Returns:
            Dictionary mit allen ProblemCase-Attributen
        """
        return {
            "id": self.id,
            "title": self.title,
            "raw_description": self.raw_description,
            "problem_type": self.problem_type.value,
            "severity": self.severity.value,
            "status": self.status.value,
            "goal_state": self.goal_state,
            "constraints": self.constraints,
            "affected_components": self.affected_components,
            "evidence": self.evidence,
            "success_criteria": self.success_criteria,
            "risk_level": self.risk_level,
            "risk_factors": self.risk_factors,
            "target_stack": self.target_stack,
            "stack_capabilities": self.stack_capabilities,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source": self.source,
            "related_findings": self.related_findings,
            "related_files": self.related_files,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ProblemCase":
        """
        Erstellt ProblemCase aus Dictionary (JSON-Import).
        
        Wandelt String-Werte zurück in Enum-Typen und stellt
        Default-Werte für fehlende Felder sicher.
        
        Args:
            data: Dictionary mit ProblemCase-Daten
        
        Returns:
            Neue ProblemCase-Instanz
        
        Raises:
            KeyError: Bei fehlenden Required-Feldern (id, title, raw_description)
            ValueError: Bei ungültigen Enum-Werten
        """
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            raw_description=data.get("raw_description", ""),
            problem_type=ProblemType(data.get("problem_type", "unknown")),
            severity=ProblemSeverity(data.get("severity", "medium")),
            status=ProblemStatus(data.get("status", "intake")),
            goal_state=data.get("goal_state", ""),
            constraints=data.get("constraints", []),
            affected_components=data.get("affected_components", []),
            evidence=data.get("evidence", []),
            success_criteria=data.get("success_criteria", []),
            risk_level=data.get("risk_level", "medium"),
            risk_factors=data.get("risk_factors", []),
            target_stack=data.get("target_stack", "auto"),
            stack_capabilities=data.get("stack_capabilities", {}),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            source=data.get("source", "cli"),
            related_findings=data.get("related_findings", []),
            related_files=data.get("related_files", []),
        )
    
    def with_updates(self, **updates: Any) -> "ProblemCase":
        """
        Erstellt eine aktualisierte Kopie des ProblemCase.
        
        Folgt dem Prinzip der Immutabilität - verändert nicht
        das bestehende Objekt, sondern erstellt eine neue Instanz.
        
        Args:
            **updates: Zu aktualisierende Felder als Keyword-Arguments
        
        Returns:
            Neue ProblemCase-Instanz mit aktualisierten Werten
        
        Example:
            updated = problem.with_updates(
                status=ProblemStatus.DIAGNOSIS,
                risk_level="high"
            )
        """
        return ProblemCase(
            id=updates.get("id", self.id),
            title=updates.get("title", self.title),
            raw_description=updates.get("raw_description", self.raw_description),
            problem_type=updates.get("problem_type", self.problem_type),
            severity=updates.get("severity", self.severity),
            status=updates.get("status", self.status),
            goal_state=updates.get("goal_state", self.goal_state),
            constraints=list(updates.get("constraints", self.constraints)),
            affected_components=list(updates.get("affected_components", self.affected_components)),
            evidence=list(updates.get("evidence", self.evidence)),
            success_criteria=list(updates.get("success_criteria", self.success_criteria)),
            risk_level=updates.get("risk_level", self.risk_level),
            risk_factors=list(updates.get("risk_factors", self.risk_factors)),
            target_stack=updates.get("target_stack", self.target_stack),
            stack_capabilities=dict(updates.get("stack_capabilities", self.stack_capabilities)),
            created_at=updates.get("created_at", self.created_at),
            updated_at=updates.get("updated_at", datetime.now().isoformat()),
            source=updates.get("source", self.source),
            related_findings=list(updates.get("related_findings", self.related_findings)),
            related_files=list(updates.get("related_files", self.related_files)),
        )
