"""
Diagnose-Schicht für Problem-Solver.

Gemäß PROBLEM_SOLVER.md Phase 2.1:
- Strukturierte Diagnose aus ProblemCase
- Vermutete Hauptursachen
- Betroffene Dateien/Module
- Relevante Datenflüsse
- Offene Unsicherheiten
- Empfohlene Analyseschritte
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .models import ProblemCase, ProblemType


class CauseType(Enum):
    """Typen von Ursachen."""
    ROOT_CAUSE = "root_cause"  # Hauptursache
    CONTRIBUTING = "contributing"  # Mitwirkender Faktor
    SYMPTOM = "symptom"  # Nur Symptom
    UNKNOWN = "unknown"


@dataclass
class Cause:
    """
    Eine identifizierte Ursache.
    
    Beschreibt eine vermutete oder bestätigte Ursache
    des Problems.
    """
    
    id: str
    description: str
    cause_type: CauseType
    
    # Details
    confidence: float = 0.0  # 0.0 - 1.0
    evidence: List[str] = field(default_factory=list)
    
    # Lokalisierung
    affected_files: List[str] = field(default_factory=list)
    affected_modules: List[str] = field(default_factory=list)
    affected_functions: List[str] = field(default_factory=list)
    
    # Zusammenhänge
    related_causes: List[str] = field(default_factory=list)  # IDs
    is_blocking: bool = False  # Blockiert Lösung
    
    # Metadaten
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        """Konvertiert Cause zu Dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "cause_type": self.cause_type.value,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "affected_files": self.affected_files,
            "affected_modules": self.affected_modules,
            "affected_functions": self.affected_functions,
            "related_causes": self.related_causes,
            "is_blocking": self.is_blocking,
            "created_at": self.created_at,
        }


@dataclass
class DataFlow:
    """
    Beschreibt einen relevanten Datenfluss.
    
    Wichtig für Probleme mit Datenverarbeitung.
    """
    
    id: str
    name: str
    source: str  # Wo Daten herkommen
    sink: str  # Wo Daten hingehen
    
    # Details
    transformation_steps: List[str] = field(default_factory=list)
    data_types: List[str] = field(default_factory=list)
    
    # Probleme im Fluss
    issues: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Konvertiert DataFlow zu Dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "source": self.source,
            "sink": self.sink,
            "transformation_steps": self.transformation_steps,
            "data_types": self.data_types,
            "issues": self.issues,
        }


@dataclass
class Uncertainty:
    """
    Eine offene Unsicherheit in der Diagnose.
    
    Beschreibt was noch unklar ist und weiter
    analysiert werden muss.
    """
    
    id: str
    question: str  # Was ist unklar?
    
    # Details
    impact: str = "medium"  # low, medium, high
    description: str = ""
    
    # Wie klären?
    resolution_steps: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Konvertiert Uncertainty zu Dictionary."""
        return {
            "id": self.id,
            "question": self.question,
            "impact": self.impact,
            "description": self.description,
            "resolution_steps": self.resolution_steps,
        }


@dataclass
class Diagnosis:
    """
    Vollständige Diagnose für ein ProblemCase.
    
    Hauptmodell der Diagnose-Schicht.
    """
    
    # Referenz zum Problem
    problem_id: str
    
    # Diagnose-Status
    status: str = "draft"  # draft, complete, validated
    
    # Ursachen
    causes: List[Cause] = field(default_factory=list)
    
    # Datenflüsse
    data_flows: List[DataFlow] = field(default_factory=list)
    
    # Unsicherheiten
    uncertainties: List[Uncertainty] = field(default_factory=list)
    
    # Zusammenfassung
    summary: str = ""
    root_cause_summary: str = ""
    
    # Empfehlungen
    recommended_next_steps: List[str] = field(default_factory=list)
    
    # Metadaten
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    diagnosis_version: str = "1.0"
    
    def to_dict(self) -> dict:
        """Konvertiert Diagnosis zu Dictionary."""
        return {
            "problem_id": self.problem_id,
            "status": self.status,
            "causes": [c.to_dict() for c in self.causes],
            "data_flows": [d.to_dict() for d in self.data_flows],
            "uncertainties": [u.to_dict() for u in self.uncertainties],
            "summary": self.summary,
            "root_cause_summary": self.root_cause_summary,
            "recommended_next_steps": self.recommended_next_steps,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "diagnosis_version": self.diagnosis_version,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Diagnosis":
        """Erstellt Diagnose aus Dict."""
        causes = [
            Cause(
                id=c["id"],
                description=c["description"],
                cause_type=CauseType(c["cause_type"]),
                confidence=c.get("confidence", 0.0),
                evidence=c.get("evidence", []),
                affected_files=c.get("affected_files", []),
                affected_modules=c.get("affected_modules", []),
                affected_functions=c.get("affected_functions", []),
                related_causes=c.get("related_causes", []),
                is_blocking=c.get("is_blocking", False),
                created_at=c.get("created_at", datetime.now().isoformat()),
            )
            for c in data.get("causes", [])
        ]
        
        data_flows = [
            DataFlow(
                id=d["id"],
                name=d["name"],
                source=d["source"],
                sink=d["sink"],
                transformation_steps=d.get("transformation_steps", []),
                data_types=d.get("data_types", []),
                issues=d.get("issues", []),
            )
            for d in data.get("data_flows", [])
        ]
        
        uncertainties = [
            Uncertainty(
                id=u["id"],
                question=u["question"],
                impact=u.get("impact", "medium"),
                description=u.get("description", ""),
                resolution_steps=u.get("resolution_steps", []),
            )
            for u in data.get("uncertainties", [])
        ]
        
        return cls(
            problem_id=data["problem_id"],
            status=data.get("status", "draft"),
            causes=causes,
            data_flows=data_flows,
            uncertainties=uncertainties,
            summary=data.get("summary", ""),
            root_cause_summary=data.get("root_cause_summary", ""),
            recommended_next_steps=data.get("recommended_next_steps", []),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            diagnosis_version=data.get("diagnosis_version", "1.0"),
        )
    
    def add_cause(
        self,
        description: str,
        cause_type: CauseType,
        confidence: float = 0.5,
        evidence: Optional[List[str]] = None,
        affected_files: Optional[List[str]] = None,
        is_blocking: bool = False,
    ) -> Cause:
        """
        Fügt eine Ursache hinzu.
        
        Args:
            description: Beschreibung der Ursache
            cause_type: Typ der Ursache
            confidence: Confidence-Score (0-1)
            evidence: Liste von Evidenzen
            affected_files: Betroffene Dateien
            is_blocking: Ob diese Ursache die Lösung blockiert
        
        Returns:
            Neue Cause-Instanz
        """
        import uuid
        cause = Cause(
            id=f"cause_{uuid.uuid4().hex[:8]}",
            description=description,
            cause_type=cause_type,
            confidence=confidence,
            evidence=evidence or [],
            affected_files=affected_files or [],
            is_blocking=is_blocking,
        )
        self.causes.append(cause)
        self.updated_at = datetime.now().isoformat()
        return cause
    
    def add_data_flow(
        self,
        name: str,
        source: str,
        sink: str,
        transformation_steps: Optional[List[str]] = None,
        data_types: Optional[List[str]] = None,
        issues: Optional[List[str]] = None,
    ) -> DataFlow:
        """
        Fügt einen Datenfluss hinzu.
        
        Args:
            name: Name des Datenflusses
            source: Wo Daten herkommen
            sink: Wo Daten hingehen
            transformation_steps: Verarbeitungsschritte
            data_types: Datentypen im Fluss
            issues: Probleme im Fluss
        
        Returns:
            Neue DataFlow-Instanz
        """
        import uuid
        data_flow = DataFlow(
            id=f"flow_{uuid.uuid4().hex[:8]}",
            name=name,
            source=source,
            sink=sink,
            transformation_steps=transformation_steps or [],
            data_types=data_types or [],
            issues=issues or [],
        )
        self.data_flows.append(data_flow)
        self.updated_at = datetime.now().isoformat()
        return data_flow
    
    def add_uncertainty(
        self,
        question: str,
        impact: str = "medium",
        description: str = "",
        resolution_steps: Optional[List[str]] = None,
    ) -> Uncertainty:
        """
        Fügt eine Unsicherheit hinzu.
        
        Args:
            question: Was ist unklar?
            impact: Auswirkung der Unklarheit
            description: Detaillierte Beschreibung
            resolution_steps: Wie klären?
        
        Returns:
            Neue Uncertainty-Instanz
        """
        import uuid
        uncertainty = Uncertainty(
            id=f"uncertainty_{uuid.uuid4().hex[:8]}",
            question=question,
            impact=impact,
            description=description,
            resolution_steps=resolution_steps or [],
        )
        self.uncertainties.append(uncertainty)
        self.updated_at = datetime.now().isoformat()
        return uncertainty
    
    def get_root_causes(self) -> List[Cause]:
        """Returns alle Root-Causes."""
        return [
            c for c in self.causes
            if c.cause_type == CauseType.ROOT_CAUSE
        ]
    
    def get_blocking_causes(self) -> List[Cause]:
        """Returns alle blockierenden Ursachen."""
        return [c for c in self.causes if c.is_blocking]
    
    def get_high_impact_uncertainties(self) -> List[Uncertainty]:
        """Returns Unsicherheiten mit hoher Auswirkung."""
        return [
            u for u in self.uncertainties
            if u.impact == "high"
        ]


class DiagnosisEngine:
    """
    Engine zur automatischen Diagnose-Generierung.
    
    Analysiert ein ProblemCase und generiert daraus
    eine erste strukturierte Diagnose.
    """
    
    def __init__(self, repo_path: Optional[Path] = None):
        """
        Initialisiert Diagnose-Engine.
        
        Args:
            repo_path: Pfad zum Repository für Code-Analyse
        """
        self.repo_path = repo_path
    
    def generate_diagnosis(self, problem: ProblemCase) -> Diagnosis:
        """
        Generiert Diagnose aus ProblemCase.
        
        Args:
            problem: Zu analysierendes Problem
        
        Returns:
            Diagnosis-Objekt
        """
        diagnosis = Diagnosis(problem_id=problem.id)
        
        # 1. Ursachen analysieren
        self._analyze_causes(problem, diagnosis)
        
        # 2. Datenflüsse identifizieren
        self._identify_data_flows(problem, diagnosis)
        
        # 3. Unsicherheiten erfassen
        self._capture_uncertainties(problem, diagnosis)
        
        # 4. Zusammenfassung erstellen
        self._create_summary(problem, diagnosis)
        
        # 5. Nächste Schritte empfehlen
        self._recommend_next_steps(problem, diagnosis)
        
        return diagnosis
    
    def _analyze_causes(
        self,
        problem: ProblemCase,
        diagnosis: Diagnosis,
    ) -> None:
        """
        Analysiert mögliche Ursachen.
        
        Nutzt Problem-Beschreibung und Klassifikation
        für erste Ursachenhypothesen.
        """
        text = problem.raw_description.lower()
        
        # Heuristische Ursachen basierend auf Problemtyp
        if problem.problem_type == ProblemType.PERFORMANCE:
            # Typische Performance-Ursachen
            diagnosis.add_cause(
                description="Ineffiziente Algorithmen oder Datenstrukturen",
                cause_type=CauseType.CONTRIBUTING,
                confidence=0.6,
                evidence=self._extract_evidence(text, [
                    "langsam", "performance", "ineffizient", "dauer"
                ]),
                is_blocking=False,
            )
            
            diagnosis.add_cause(
                description="Database-Queries ohne Index",
                cause_type=CauseType.CONTRIBUTING,
                confidence=0.5,
                evidence=self._extract_evidence(text, ["datenbank", "query", "sql"]),
                is_blocking=False,
            )
        
        elif problem.problem_type == ProblemType.BUG:
            # Typische Bug-Ursachen
            diagnosis.add_cause(
                description="Fehlende Input-Validierung",
                cause_type=CauseType.ROOT_CAUSE,
                confidence=0.7,
                evidence=self._extract_evidence(text, ["input", "validation", "fehler"]),
                is_blocking=True,
            )
        
        elif problem.problem_type == ProblemType.MISSING_FEATURE:
            diagnosis.add_cause(
                description="Feature wurde nicht spezifiziert",
                cause_type=CauseType.ROOT_CAUSE,
                confidence=0.8,
                evidence=[],
                is_blocking=False,
            )
        
        elif problem.problem_type == ProblemType.WORKFLOW_GAP:
            diagnosis.add_cause(
                description="Manueller Schritt nicht automatisiert",
                cause_type=CauseType.ROOT_CAUSE,
                confidence=0.8,
                evidence=self._extract_evidence(text, ["manuell", "manual", "schritt"]),
                is_blocking=False,
            )
    
    def _identify_data_flows(
        self,
        problem: ProblemCase,
        diagnosis: Diagnosis,
    ) -> None:
        """Identifiziert relevante Datenflüsse."""
        text = problem.raw_description.lower()
        
        # Einfache Heuristiken
        if "datenbank" in text or "database" in text:
            diagnosis.add_data_flow(
                name="Database-Zugriff",
                source="Application Logic",
                sink="Database",
                issues=["Mögliche Performance-Probleme bei Queries"],
            )
        
        if "api" in text or "schnittstell" in text:
            diagnosis.add_data_flow(
                name="API-Kommunikation",
                source="Client / External",
                sink="Backend API",
                issues=["Mögliche Latenz oder Fehler bei API-Calls"],
            )
        
        if "ui" in text or "frontend" in text:
            diagnosis.add_data_flow(
                name="UI-Datenfluss",
                source="Backend API",
                sink="User Interface",
                issues=["Mögliche Render-Probleme oder State-Inkonsistenzen"],
            )
    
    def _capture_uncertainties(
        self,
        problem: ProblemCase,
        diagnosis: Diagnosis,
    ) -> None:
        """Erfasst offene Unsicherheiten."""
        # Standard-Unsicherheiten für jede Diagnose
        diagnosis.add_uncertainty(
            question="Ist die identifizierte Ursache die tatsächliche Root-Cause?",
            impact="high",
            description="Weitere Analyse erforderlich um Root-Cause zu bestätigen",
            resolution_steps=[
                "Reproduktionsschritte dokumentieren",
                "Logs analysieren",
                "Betroffene Code-Pfade untersuchen",
            ],
        )
        
        diagnosis.add_uncertainty(
            question="Welche weiteren Komponenten sind betroffen?",
            impact="medium",
            description="Scope des Problems noch nicht vollständig geklärt",
            resolution_steps=[
                "Abhängigkeiten analysieren",
                "Integration Points prüfen",
                "Side-Effects identifizieren",
            ],
        )
    
    def _create_summary(
        self,
        problem: ProblemCase,
        diagnosis: Diagnosis,
    ) -> None:
        """Erstellt Zusammenfassung der Diagnose."""
        root_causes = diagnosis.get_root_causes()
        
        if root_causes:
            diagnosis.root_cause_summary = "\n".join(
                f"- {c.description} (Confidence: {c.confidence:.0%})"
                for c in root_causes
            )
        
        diagnosis.summary = (
            f"Diagnose für Problem '{problem.title}':\n\n"
            f"Problemtyp: {problem.problem_type.value}\n"
            f"Anzahl Ursachen: {len(diagnosis.causes)}\n"
            f"Anzahl Datenflüsse: {len(diagnosis.data_flows)}\n"
            f"Offene Unsicherheiten: {len(diagnosis.uncertainties)}"
        )
    
    def _recommend_next_steps(
        self,
        problem: ProblemCase,
        diagnosis: Diagnosis,
    ) -> None:
        """Empfiehlt nächste Analyseschritte."""
        steps = []
        
        # Basierend auf Ursachen
        for cause in diagnosis.causes:
            if cause.cause_type == CauseType.ROOT_CAUSE:
                steps.append(f"Root-Cause verifizieren: {cause.description}")
        
        # Basierend auf Unsicherheiten
        for uncertainty in diagnosis.get_high_impact_uncertainties():
            steps.append(f"Unklarheit klären: {uncertainty.question}")
        
        # Immer hinzufügen
        steps.append("Betroffene Code-Pfade analysieren")
        steps.append("Reproduktionsschritte dokumentieren")
        
        diagnosis.recommended_next_steps = steps
    
    def _extract_evidence(
        self,
        text: str,
        keywords: List[str],
    ) -> List[str]:
        """Extrahiert Evidenzen aus Text basierend auf Keywords."""
        evidence = []
        text_lower = text.lower()
        
        for keyword in keywords:
            if keyword in text_lower:
                # Satz extrahieren der Keyword enthält
                for sentence in text.split("."):
                    if keyword in sentence.lower():
                        evidence.append(sentence.strip() + ".")
                        break
        
        return evidence[:5]  # Max 5 Evidenzen
