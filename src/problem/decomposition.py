"""
Problem Decomposition für Problem-Solver.

Gemäß PROBLEM_SOLVER.md Phase 2.2:
- Zerlegung großer Probleme in Teilprobleme
- Dependencies zwischen Teilproblemen
- Priorisierung der Teilprobleme
- Für komplexe Probleme (Performance, Missing Feature, Workflow, etc.)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .models import ProblemCase, ProblemSeverity


class SubProblemType(Enum):
    """Typen von Teilproblemen."""
    TECHNICAL = "technical"  # Technische Umsetzung
    ANALYSIS = "analysis"  # Weitere Analyse nötig
    INTEGRATION = "integration"  # Integration mit anderem
    DOCUMENTATION = "documentation"  # Dokumentation
    TESTING = "testing"  # Tests erforderlich
    CONFIGURATION = "configuration"  # Konfiguration
    REFACTORING = "refactoring"  # Refactoring nötig
    UNKNOWN = "unknown"


class DependencyType(Enum):
    """Typen von Dependencies."""
    BLOCKS = "blocks"  # Blockiert anderes Teilproblem
    DEPENDS_ON = "depends_on"  # Hängt von anderem ab
    RELATED = "related"  # Related zu anderem
    OPTIONAL = "optional"  # Optional


@dataclass
class SubProblem:
    """
    Ein Teilproblem innerhalb einer Decomposition.
    
    Beschreibt einen Aspekt des größeren Problems.
    """
    
    # Identifikation
    id: str
    problem_id: str  # Referenz zum Parent-Problem
    title: str
    description: str
    
    # Klassifikation
    subproblem_type: SubProblemType = SubProblemType.UNKNOWN
    severity: ProblemSeverity = ProblemSeverity.MEDIUM
    
    # Priorisierung
    priority: int = 5  # 1-10 (1 = höchste Priorität)
    effort: str = "medium"  # low, medium, high, unknown
    complexity: int = 5  # 1-10
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)  # IDs von anderen SubProblems
    dependency_type: DependencyType = DependencyType.RELATED
    
    # Status
    status: str = "open"  # open, in_progress, blocked, done, skipped
    
    # Details
    affected_components: List[str] = field(default_factory=list)
    affected_files: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    
    # Schätzung
    estimated_hours: Optional[float] = None
    
    # Metadaten
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        """
        Konvertiert SubProblem zu Dictionary für JSON-Export.
        
        Returns:
            Dictionary mit allen SubProblem-Attributen
        """
        return {
            "id": self.id,
            "problem_id": self.problem_id,
            "title": self.title,
            "description": self.description,
            "subproblem_type": self.subproblem_type.value,
            "severity": self.severity.value,
            "priority": self.priority,
            "effort": self.effort,
            "complexity": self.complexity,
            "dependencies": self.dependencies,
            "dependency_type": self.dependency_type.value,
            "status": self.status,
            "affected_components": self.affected_components,
            "affected_files": self.affected_files,
            "success_criteria": self.success_criteria,
            "estimated_hours": self.estimated_hours,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    def is_blocking(self) -> bool:
        """Ist dieses Teilproblem blockierend?"""
        return self.dependency_type == DependencyType.BLOCKS
    
    def is_blocked(self) -> bool:
        """Ist dieses Teilproblem blockiert?"""
        return self.status == "blocked"
    
    def can_start(self, all_subproblems: List["SubProblem"]) -> bool:
        """Kann dieses Teilproblem gestartet werden?"""
        if self.is_blocked():
            return False
        
        # Prüfe ob alle Dependencies erledigt sind
        for dep_id in self.dependencies:
            dep = next((sp for sp in all_subproblems if sp.id == dep_id), None)
            if dep and dep.status != "done":
                return False
        
        return True


@dataclass
class Decomposition:
    """
    Vollständige Zerlegung eines Problems.
    
    Hauptmodell der Decomposition-Schicht.
    """
    
    # Referenz zum Problem
    problem_id: str
    
    # Teilprobleme
    subproblems: List[SubProblem] = field(default_factory=list)
    
    # Zusammenfassung
    summary: str = ""
    decomposition_approach: str = ""  # Wie wurde zerlegt?
    
    # Metadaten
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        """
        Konvertiert Decomposition zu Dictionary für JSON-Export.
        
        Returns:
            Dictionary mit allen Decomposition-Attributen
        """
        return {
            "problem_id": self.problem_id,
            "subproblems": [sp.to_dict() for sp in self.subproblems],
            "summary": self.summary,
            "decomposition_approach": self.decomposition_approach,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Decomposition":
        """
        Erstellt Decomposition aus Dictionary (JSON-Import).
        
        Args:
            data: Dictionary mit Decomposition-Daten
        
        Returns:
            Neue Decomposition-Instanz
        """
        subproblems = [
            SubProblem(
                id=sp["id"],
                problem_id=sp["problem_id"],
                title=sp["title"],
                description=sp["description"],
                subproblem_type=SubProblemType(sp.get("subproblem_type", "unknown")),
                severity=ProblemSeverity(sp.get("severity", "medium")),
                priority=sp.get("priority", 5),
                effort=sp.get("effort", "medium"),
                complexity=sp.get("complexity", 5),
                dependencies=sp.get("dependencies", []),
                dependency_type=DependencyType(sp.get("dependency_type", "related")),
                status=sp.get("status", "open"),
                affected_components=sp.get("affected_components", []),
                affected_files=sp.get("affected_files", []),
                success_criteria=sp.get("success_criteria", []),
                estimated_hours=sp.get("estimated_hours"),
                created_at=sp.get("created_at", datetime.now().isoformat()),
                updated_at=sp.get("updated_at", datetime.now().isoformat()),
            )
            for sp in data.get("subproblems", [])
        ]
        
        return cls(
            problem_id=data["problem_id"],
            subproblems=subproblems,
            summary=data.get("summary", ""),
            decomposition_approach=data.get("decomposition_approach", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )
    
    def add_subproblem(
        self,
        title: str,
        description: str,
        subproblem_type: SubProblemType = SubProblemType.UNKNOWN,
        priority: int = 5,
        effort: str = "medium",
        dependencies: Optional[List[str]] = None,
        affected_components: Optional[List[str]] = None,
    ) -> SubProblem:
        """
        Fügt ein Teilproblem hinzu.
        
        Args:
            title: Titel des Teilproblems
            description: Beschreibung
            subproblem_type: Typ des Teilproblems
            priority: Priorität (1-10)
            effort: Aufwand (low, medium, high)
            dependencies: IDs von Dependencies
            affected_components: Betroffene Komponenten
        
        Returns:
            Neues SubProblem
        """
        import uuid
        subproblem = SubProblem(
            id=f"sub_{uuid.uuid4().hex[:8]}",
            problem_id=self.problem_id,
            title=title,
            description=description,
            subproblem_type=subproblem_type,
            priority=priority,
            effort=effort,
            dependencies=dependencies or [],
            affected_components=affected_components or [],
        )
        self.subproblems.append(subproblem)
        self.updated_at = datetime.now().isoformat()
        return subproblem
    
    def get_subproblem(self, subproblem_id: str) -> Optional[SubProblem]:
        """Holt ein Teilproblem nach ID."""
        return next((sp for sp in self.subproblems if sp.id == subproblem_id), None)
    
    def get_blocking_subproblems(self) -> List[SubProblem]:
        """Returns alle blockierenden Teilprobleme."""
        return [sp for sp in self.subproblems if sp.is_blocking()]
    
    def get_blocked_subproblems(self) -> List[SubProblem]:
        """Returns alle blockierten Teilprobleme."""
        return [sp for sp in self.subproblems if sp.is_blocked()]
    
    def get_ready_subproblems(self) -> List[SubProblem]:
        """Returns Teilprobleme die gestartet werden können."""
        return [sp for sp in self.subproblems if sp.can_start(self.subproblems)]
    
    def get_dependency_graph(self) -> Dict[str, Set[str]]:
        """
        Returns Dependency-Graph als Adjacency-List.
        
        Returns:
            Dict mapping subproblem_id -> set of dependent ids
        """
        graph: Dict[str, Set[str]] = {}
        for sp in self.subproblems:
            graph[sp.id] = set(sp.dependencies)
        return graph
    
    def get_execution_order(self) -> List[SubProblem]:
        """
        Berechnet Ausführungsreihenfolge basierend auf Dependencies.
        
        Verwendet topologische Sortierung (Kahn's Algorithmus).
        Ein SubProblem kann erst ausgeführt werden wenn alle seine
        Dependencies (Vorgänger) erledigt sind.

        Returns:
            Sortierte Liste von SubProblems
        """
        # Topologische Sortierung
        from collections import deque

        # In-Degree berechnen: Wie viele Dependencies hat jedes SubProblem?
        # Wenn sp2.dependencies = [sp1.id], dann hängt sp2 von sp1 ab
        # -> sp2 hat In-Degree 1, sp1 hat In-Degree 0
        in_degree: Dict[str, int] = {sp.id: 0 for sp in self.subproblems}
        for sp in self.subproblems:
            # Jedes Dependency das sp hat, erhöht sp's In-Degree
            in_degree[sp.id] = len(sp.dependencies)

        # Queue mit Nodes die keine Dependencies haben (In-Degree 0)
        queue = deque([sp.id for sp in self.subproblems if in_degree[sp.id] == 0])
        result: List[SubProblem] = []

        while queue:
            # Node mit höchster Priorität (niedrigster Wert) zuerst
            queue_list = list(queue)
            queue_list.sort(
                key=lambda x: next(sp for sp in self.subproblems if sp.id == x).priority
            )

            current_id = queue_list[0]
            queue.remove(current_id)

            current = self.get_subproblem(current_id)
            if current:
                result.append(current)

            # Nachfolger aktualisieren: Alle die von current abhängen
            for sp in self.subproblems:
                if current_id in sp.dependencies:
                    in_degree[sp.id] -= 1
                    if in_degree[sp.id] == 0:
                        queue.append(sp.id)

        # Restliche (zyklische Dependencies) hinzufügen
        remaining = [sp for sp in self.subproblems if sp not in result]
        result.extend(sorted(remaining, key=lambda x: x.priority))

        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """Returns Statistik über Decomposition."""
        total = len(self.subproblems)
        by_status: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        
        for sp in self.subproblems:
            by_status[sp.status] = by_status.get(sp.status, 0) + 1
            by_type[sp.subproblem_type.value] = by_type.get(
                sp.subproblem_type.value, 0
            ) + 1
        
        total_effort_hours = sum(
            sp.estimated_hours or 0 for sp in self.subproblems
        )
        
        return {
            "total_subproblems": total,
            "by_status": by_status,
            "by_type": by_type,
            "blocking_count": len(self.get_blocking_subproblems()),
            "blocked_count": len(self.get_blocked_subproblems()),
            "ready_count": len(self.get_ready_subproblems()),
            "total_estimated_hours": total_effort_hours,
        }


class DecompositionEngine:
    """
    Engine zur automatischen Problem-Zerlegung.
    
    Zerlegt komplexe Probleme in handhabbare Teilprobleme.
    """
    
    # Standard-Zerlegungen pro Problemtyp
    STANDARD_DECOMPOSITIONS = {
        "performance": [
            ("Performance-Messung & Baseline", "Aktuellen Zustand messen und dokumentieren"),
            ("Bottleneck-Identifikation", "Engpässe im System finden"),
            ("Optimierung kritischer Pfade", "Performance-kritische Code-Pfade optimieren"),
            ("Caching-Strategie", "Caching wo sinnvoll"),
            ("Validierung", "Erfolgsmessung und Vergleich mit Baseline"),
        ],
        "missing_feature": [
            ("Anforderungsanalyse", "Detaillierte Anforderungen sammeln"),
            ("Design & Architektur", "Lösungsdesign erstellen"),
            ("Implementierung Core-Logic", "Kernfunktionalität umsetzen"),
            ("UI/UX Integration", "User Interface anpassen"),
            ("Tests & Dokumentation", "Tests schreiben und dokumentieren"),
            ("Review & Release", "Code Review und Release"),
        ],
        "workflow_gap": [
            ("Workflow-Analyse", "Bestehenden Workflow dokumentieren"),
            ("Automatisierungspotential", "Automatisierbare Schritte identifizieren"),
            ("Tool-Auswahl", "Geeignete Tools/Frameworks wählen"),
            ("Implementierung", "Automatisierung umsetzen"),
            ("Testing", "Umfassend testen"),
            ("Migration", "Von manuellem zu automatischem Workflow"),
        ],
        "integration_gap": [
            ("Schnittstellen-Analyse", "Existierende APIs dokumentieren"),
            ("Datenformat-Definition", "Formate und Protokolle definieren"),
            ("Adapter-Implementierung", "Adapter/Connector bauen"),
            ("Integration-Tests", "End-to-End Tests"),
            ("Monitoring", "Monitoring und Alerting einrichten"),
        ],
        "ux_issue": [
            ("User Research", "Nutzerfeedback sammeln"),
            ("Usability-Analyse", "Bestehende UX analysieren"),
            ("Design-Iteration", "Neue UX entwerfen"),
            ("Implementierung", "UI-Anpassungen umsetzen"),
            ("User-Testing", "Mit echten Nutzern testen"),
            ("Iterative Verbesserung", "Feedback-basierte Optimierung"),
        ],
        "bug": [
            ("Reproduktion", "Bug reproduzierbar machen"),
            ("Root-Cause-Analyse", "Ursache identifizieren"),
            ("Fix-Implementierung", "Bug fixen"),
            ("Tests", "Regressionstests schreiben"),
            ("Validierung", "Fix verifizieren"),
        ],
    }
    
    def __init__(self):
        """Initialisiert Decomposition-Engine."""
        pass
    
    def decompose_problem(self, problem: ProblemCase) -> Decomposition:
        """
        Zerlegt ein Problem in Teilprobleme.
        
        Args:
            problem: Zu zerlegendes Problem
        
        Returns:
            Decomposition-Objekt
        """
        decomposition = Decomposition(problem_id=problem.id)
        
        # Standard-Zerlegung basierend auf Problemtyp
        standard_parts = self._get_standard_decomposition(problem.problem_type.value)
        
        # Teilprobleme erstellen
        for i, (title, description) in enumerate(standard_parts, 1):
            subproblem_type = self._infer_subproblem_type(title, description)
            
            # Dependencies setzen (sequentiell)
            dependencies = []
            if i > 1 and subproblem_type != SubProblemType.ANALYSIS:
                dependencies = [decomposition.subproblems[-1].id] if decomposition.subproblems else []
            
            decomposition.add_subproblem(
                title=title,
                description=description,
                subproblem_type=subproblem_type,
                priority=i,
                dependencies=dependencies,
                affected_components=problem.affected_components.copy(),
            )
        
        # Zusammenfassung
        decomposition.decomposition_approach = self._describe_approach(
            problem.problem_type.value
        )
        decomposition.summary = self._create_summary(decomposition)
        
        return decomposition
    
    def _get_standard_decomposition(
        self,
        problem_type: str,
    ) -> List[tuple]:
        """Returns Standard-Zerlegung für Problemtyp."""
        return self.STANDARD_DECOMPOSITIONS.get(
            problem_type,
            [
                ("Analyse", "Problem detailliert analysieren"),
                ("Planung", "Lösungsweg planen"),
                ("Umsetzung", "Lösung implementieren"),
                ("Validierung", "Lösung validieren"),
            ],
        )
    
    def _infer_subproblem_type(
        self,
        title: str,
        description: str,
    ) -> SubProblemType:
        """Leitet SubProblem-Typ aus Titel/Beschreibung ab."""
        text = f"{title} {description}".lower()
        
        if any(word in text for word in ["analyse", "untersuch", "research"]):
            return SubProblemType.ANALYSIS
        elif any(word in text for word in ["test", "validier"]):
            return SubProblemType.TESTING
        elif any(word in text for word in ["dokument", "doc"]):
            return SubProblemType.DOCUMENTATION
        elif any(word in text for word in ["integrat", "adapter", "connector"]):
            return SubProblemType.INTEGRATION
        elif any(word in text for word in ["config", "einstell"]):
            return SubProblemType.CONFIGURATION
        elif any(word in text for word in ["refactor", "struktur"]):
            return SubProblemType.REFACTORING
        else:
            return SubProblemType.TECHNICAL
    
    def _describe_approach(self, problem_type: str) -> str:
        """Beschreibt den Zerlegungs-Ansatz."""
        approaches = {
            "performance": "Iterative Performance-Optimierung mit Messung und Validierung",
            "missing_feature": "Feature-Entwicklung von Anforderungen bis Release",
            "workflow_gap": "Workflow-Automatisierung in 6 Schritten",
            "integration_gap": "Integration über Adapter-Pattern mit Testing",
            "ux_issue": "User-Centered Design mit iterativer Verbesserung",
            "bug": "Systematische Bug-Analyse und Fix mit Validierung",
        }
        return approaches.get(problem_type, "Allgemeine Problemzerlegung")
    
    def _create_summary(self, decomposition: Decomposition) -> str:
        """Erstellt Zusammenfassung der Zerlegung."""
        stats = decomposition.get_statistics()
        return (
            f"Problem zerlegt in {stats['total_subproblems']} Teilprobleme:\n"
            f"- Blocking: {stats['blocking_count']}\n"
            f"- Ready to start: {stats['ready_count']}\n"
            f"- Geschätzter Aufwand: {stats['total_estimated_hours']:.1f}h"
        )
