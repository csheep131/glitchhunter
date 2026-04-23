"""
State-Klassen für den Swarm Coordinator.

Enthält:
- SwarmState: Geteilter State für den Swarm
- SwarmFinding: Einheitliches Finding-Format für alle Agenten
- SwarmStateGraphInput: TypedDict für LangGraph State
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, TypedDict

if TYPE_CHECKING:
    from agent.analyzer_agent import Evidence


@dataclass
class SwarmFinding:
    """
    Einheitliches Finding-Format für alle Swarm-Agenten.

    Attributes:
        id: Eindeutige ID
        agent: Ursprungs-Agent (static, dynamic, exploit, etc.)
        file_path: Betroffene Datei
        line_start: Startzeile
        line_end: Endzeile
        severity: Schweregrad (critical, high, medium, low, info)
        category: Kategorie (security, performance, correctness, etc.)
        title: Kurzer Titel
        description: Detaillierte Beschreibung
        evidence: Gesammelte Evidenzen
        confidence: Konfidenz (0-1)
        exploit_ready: Ob ein Exploit generiert wurde
        fix_suggestion: Vorschlag zur Behebung
        metadata: Zusätzliche Metadaten
    """

    id: str
    agent: str
    file_path: str
    line_start: int
    line_end: int
    severity: str
    category: str
    title: str
    description: str
    evidence: List["Evidence"] = field(default_factory=list)
    confidence: float = 0.5
    exploit_ready: bool = False
    fix_suggestion: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Konvertiert zu Dict für Serialisierung.

        Returns:
            Dictionary-Repräsentation des Findings
        """
        return {
            "id": self.id,
            "agent": self.agent,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "evidence": [
                e.to_dict() if hasattr(e, "to_dict") else e for e in self.evidence
            ],
            "confidence": self.confidence,
            "exploit_ready": self.exploit_ready,
            "fix_suggestion": self.fix_suggestion,
            "metadata": self.metadata,
        }


@dataclass
class SwarmState:
    """
    Geteilter State für den Swarm.

    Attributes:
        repo_path: Pfad zum Repository
        current_phase: Aktuelle Phase des Swarms
        static_findings: Findings vom Static Scanner
        dynamic_findings: Findings vom Dynamic Tracer
        exploit_findings: Findings vom Exploit Generator
        refactor_findings: Findings vom Refactoring Bot
        aggregated_findings: Konsolidierte Findings
        prediction_results: Glitch Prediction Ergebnisse
        errors: Aufgetretene Fehler
        metadata: Zusätzliche Metadaten
    """

    repo_path: Optional[str] = None
    current_phase: str = "init"
    static_findings: List[SwarmFinding] = field(default_factory=list)
    dynamic_findings: List[SwarmFinding] = field(default_factory=list)
    exploit_findings: List[SwarmFinding] = field(default_factory=list)
    refactor_findings: List[SwarmFinding] = field(default_factory=list)
    aggregated_findings: List[SwarmFinding] = field(default_factory=list)
    prediction_results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Konvertiert State zu Dict.

        Returns:
            Dictionary-Repräsentation des States
        """
        return {
            "repo_path": self.repo_path,
            "current_phase": self.current_phase,
            "static_findings_count": len(self.static_findings),
            "dynamic_findings_count": len(self.dynamic_findings),
            "exploit_findings_count": len(self.exploit_findings),
            "refactor_findings_count": len(self.refactor_findings),
            "aggregated_findings_count": len(self.aggregated_findings),
            "prediction_count": len(self.prediction_results),
            "errors_count": len(self.errors),
            "metadata": self.metadata,
        }


class SwarmStateGraphInput(TypedDict):
    """Input type für LangGraph State."""

    repo_path: str
    current_phase: str
    static_findings: List[Dict[str, Any]]
    dynamic_findings: List[Dict[str, Any]]
    exploit_findings: List[Dict[str, Any]]
    refactor_findings: List[Dict[str, Any]]
    aggregated_findings: List[Dict[str, Any]]
    prediction_results: List[Dict[str, Any]]
    errors: List[str]
    metadata: Dict[str, Any]
    stop_after: Optional[str]
