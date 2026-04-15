"""
Solution Path Planning für Problem-Solver.

Gemäß PROBLEM_SOLVER.md Phase 2.3:
- Mehrere Lösungspfade pro Teilproblem
- Bewertung nach Wirksamkeit, Invasivität, Risiko, Aufwand
- Vergleich und Auswahl des besten Pfads
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pathlib import Path


class SolutionType(Enum):
    """Typen von Lösungen."""
    HOTFIX = "hotfix"  # Schneller Minimal-Fix
    GUARD = "guard"  # Guard/Timeout/Fallback
    REFACTOR = "refactor"  # Refactoring
    REWRITE = "rewrite"  # Komplettes Neuschreiben
    CONFIG_CHANGE = "config_change"  # Nur Konfiguration
    WORKAROUND = "workaround"  # Umgehung
    FEATURE_ADD = "feature_add"  # Neues Feature
    INTEGRATION = "integration"  # Integration hinzufügen
    AUTOMATION = "automation"  # Automatisierung
    UNKNOWN = "unknown"


class RiskLevel(Enum):
    """Risikostufen."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SolutionPath:
    """
    Ein möglicher Lösungsweg für ein Teilproblem.
    
    Beschreibt einen spezifischen Ansatz zur Lösung.
    """
    
    # Identifikation
    id: str
    subproblem_id: str  # Referenz zum Teilproblem
    title: str
    description: str
    
    # Klassifikation
    solution_type: SolutionType = SolutionType.UNKNOWN
    
    # Bewertung (1-10 Skala)
    effectiveness: int = 5  # Wirksamkeit (10 = sehr wirksam)
    invasiveness: int = 5  # Invasivität (10 = sehr invasiv)
    risk: RiskLevel = RiskLevel.MEDIUM
    effort: int = 5  # Aufwand (10 = sehr aufwändig)
    testability: int = 5  # Testbarkeit (10 = sehr gut testbar)
    
    # Details
    implementation_steps: List[str] = field(default_factory=list)
    required_resources: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    # Risiken
    risks: List[str] = field(default_factory=list)
    rollback_plan: str = ""
    
    # Erfolgsmessung
    success_metrics: List[str] = field(default_factory=list)
    
    # Schätzung
    estimated_hours: Optional[float] = None
    
    # Metadaten
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        """
        Konvertiert SolutionPath zu Dictionary für JSON-Export.
        
        Returns:
            Dictionary mit allen SolutionPath-Attributen
        """
        return {
            "id": self.id,
            "subproblem_id": self.subproblem_id,
            "title": self.title,
            "description": self.description,
            "solution_type": self.solution_type.value,
            "effectiveness": self.effectiveness,
            "invasiveness": self.invasiveness,
            "risk": self.risk.value,
            "effort": self.effort,
            "testability": self.testability,
            "implementation_steps": self.implementation_steps,
            "required_resources": self.required_resources,
            "dependencies": self.dependencies,
            "risks": self.risks,
            "rollback_plan": self.rollback_plan,
            "success_metrics": self.success_metrics,
            "estimated_hours": self.estimated_hours,
            "created_at": self.created_at,
        }
    
    def overall_score(self) -> float:
        """
        Berechnet Gesamtpunktzahl für Vergleich.
        
        Formel: (effectiveness + testability) - (invasiveness + risk + effort) / 3
        
        Returns:
            Score zwischen 0 und 10
        """
        risk_value = {
            RiskLevel.LOW: 2,
            RiskLevel.MEDIUM: 5,
            RiskLevel.HIGH: 8,
            RiskLevel.CRITICAL: 10,
        }.get(self.risk, 5)
        
        positive = (self.effectiveness + self.testability) / 2
        negative = (self.invasiveness + risk_value + self.effort) / 3
        
        return max(0, min(10, positive - negative + 5))
    
    def is_quick_win(self) -> bool:
        """Ist dies ein Quick Win (hohe Wirksamkeit, geringer Aufwand)?"""
        return self.effectiveness >= 7 and self.effort <= 4
    
    def is_high_risk(self) -> bool:
        """Ist dies ein高风险iger Ansatz?"""
        return self.risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)


@dataclass
class SolutionPlan:
    """
    Vollständiger Lösungsplan für ein Problem.
    
    Enthält alle Lösungspfade für alle Teilprobleme.
    """
    
    # Referenzen
    problem_id: str
    decomposition_id: Optional[str] = None
    
    # Lösungspfade pro Teilproblem
    # Key: subproblem_id, Value: List of SolutionPath
    solution_paths: Dict[str, List[SolutionPath]] = field(default_factory=dict)
    
    # Ausgewählte Pfade
    # Key: subproblem_id, Value: selected SolutionPath id
    selected_paths: Dict[str, str] = field(default_factory=dict)
    
    # Zusammenfassung
    overall_strategy: str = ""
    
    # Metadaten
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        """
        Konvertiert SolutionPlan zu Dictionary für JSON-Export.
        
        Returns:
            Dictionary mit allen SolutionPlan-Attributen
        """
        return {
            "problem_id": self.problem_id,
            "decomposition_id": self.decomposition_id,
            "solution_paths": {
                sp_id: [p.to_dict() for p in paths]
                for sp_id, paths in self.solution_paths.items()
            },
            "selected_paths": self.selected_paths,
            "overall_strategy": self.overall_strategy,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SolutionPlan":
        """Erstellt SolutionPlan aus Dict."""
        solution_paths = {}
        for sp_id, paths_data in data.get("solution_paths", {}).items():
            paths = [
                SolutionPath(
                    id=p["id"],
                    subproblem_id=p["subproblem_id"],
                    title=p["title"],
                    description=p["description"],
                    solution_type=SolutionType(p.get("solution_type", "unknown")),
                    effectiveness=p.get("effectiveness", 5),
                    invasiveness=p.get("invasiveness", 5),
                    risk=RiskLevel(p.get("risk", "medium")),
                    effort=p.get("effort", 5),
                    testability=p.get("testability", 5),
                    implementation_steps=p.get("implementation_steps", []),
                    required_resources=p.get("required_resources", []),
                    dependencies=p.get("dependencies", []),
                    risks=p.get("risks", []),
                    rollback_plan=p.get("rollback_plan", ""),
                    success_metrics=p.get("success_metrics", []),
                    estimated_hours=p.get("estimated_hours"),
                    created_at=p.get("created_at", datetime.now().isoformat()),
                )
                for p in paths_data
            ]
            solution_paths[sp_id] = paths
        
        return cls(
            problem_id=data["problem_id"],
            decomposition_id=data.get("decomposition_id"),
            solution_paths=solution_paths,
            selected_paths=data.get("selected_paths", {}),
            overall_strategy=data.get("overall_strategy", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )
    
    def add_solution_path(
        self,
        subproblem_id: str,
        title: str,
        description: str,
        solution_type: SolutionType = SolutionType.UNKNOWN,
        effectiveness: int = 5,
        invasiveness: int = 5,
        risk: RiskLevel = RiskLevel.MEDIUM,
        effort: int = 5,
        testability: int = 5,
        implementation_steps: Optional[List[str]] = None,
        estimated_hours: Optional[float] = None,
    ) -> SolutionPath:
        """
        Fügt einen Lösungsweg hinzu.
        
        Args:
            subproblem_id: Ziel-Teilproblem
            title: Titel des Lösungswegs
            description: Beschreibung
            solution_type: Typ der Lösung
            effectiveness: Wirksamkeit (1-10)
            invasiveness: Invasivität (1-10)
            risk: Risikostufe
            effort: Aufwand (1-10)
            testability: Testbarkeit (1-10)
            implementation_steps: Umsetzungsschritte
            estimated_hours: Aufwandsschätzung
        
        Returns:
            Neuer SolutionPath
        """
        import uuid
        path = SolutionPath(
            id=f"path_{uuid.uuid4().hex[:8]}",
            subproblem_id=subproblem_id,
            title=title,
            description=description,
            solution_type=solution_type,
            effectiveness=effectiveness,
            invasiveness=invasiveness,
            risk=risk,
            effort=effort,
            testability=testability,
            implementation_steps=implementation_steps or [],
            estimated_hours=estimated_hours,
        )
        
        if subproblem_id not in self.solution_paths:
            self.solution_paths[subproblem_id] = []
        
        self.solution_paths[subproblem_id].append(path)
        self.updated_at = datetime.now().isoformat()
        return path
    
    def get_paths_for_subproblem(
        self,
        subproblem_id: str,
    ) -> List[SolutionPath]:
        """Returns alle Lösungspfade für ein Teilproblem."""
        return self.solution_paths.get(subproblem_id, [])
    
    def select_path(
        self,
        subproblem_id: str,
        path_id: str,
    ) -> bool:
        """
        Wählt einen Lösungsweg aus.
        
        Args:
            subproblem_id: Teilproblem-ID
            path_id: ID des Lösungswegs
        
        Returns:
            True wenn erfolgreich
        """
        # Prüfen ob Pfad existiert
        paths = self.get_paths_for_subproblem(subproblem_id)
        if not any(p.id == path_id for p in paths):
            return False
        
        self.selected_paths[subproblem_id] = path_id
        self.updated_at = datetime.now().isoformat()
        return True
    
    def get_selected_path(
        self,
        subproblem_id: str,
    ) -> Optional[SolutionPath]:
        """Returns ausgewählter Lösungsweg für Teilproblem."""
        path_id = self.selected_paths.get(subproblem_id)
        if not path_id:
            return None
        
        paths = self.get_paths_for_subproblem(subproblem_id)
        return next((p for p in paths if p.id == path_id), None)
    
    def get_best_path(self, subproblem_id: str) -> Optional[SolutionPath]:
        """
        Returns besten Lösungsweg basierend auf Score.
        
        Args:
            subproblem_id: Teilproblem-ID
        
        Returns:
            Bester SolutionPath oder None
        """
        paths = self.get_paths_for_subproblem(subproblem_id)
        if not paths:
            return None
        
        return max(paths, key=lambda p: p.overall_score())
    
    def auto_select_best_paths(self) -> Dict[str, str]:
        """
        Wählt automatisch beste Pfade für alle Teilprobleme.
        
        Returns:
            Dict mapping subproblem_id -> selected path_id
        """
        selected = {}
        for sp_id in self.solution_paths.keys():
            best = self.get_best_path(sp_id)
            if best:
                self.select_path(sp_id, best.id)
                selected[sp_id] = best.id
        return selected
    
    def get_statistics(self) -> Dict[str, Any]:
        """Returns Statistik über Lösungsplan."""
        total_paths = sum(len(paths) for paths in self.solution_paths.values())
        selected_count = len(self.selected_paths)
        
        # Durchschnittliche Scores
        all_paths = [
            p for paths in self.solution_paths.values() for p in paths
        ]
        
        avg_scores = {}
        if all_paths:
            avg_scores = {
                "avg_effectiveness": sum(p.effectiveness for p in all_paths) / len(all_paths),
                "avg_invasiveness": sum(p.invasiveness for p in all_paths) / len(all_paths),
                "avg_effort": sum(p.effort for p in all_paths) / len(all_paths),
                "avg_testability": sum(p.testability for p in all_paths) / len(all_paths),
                "avg_overall_score": sum(p.overall_score() for p in all_paths) / len(all_paths),
            }
        
        # Quick Wins
        quick_wins = [p for p in all_paths if p.is_quick_win()]
        high_risk = [p for p in all_paths if p.is_high_risk()]
        
        return {
            "total_subproblems": len(self.solution_paths),
            "total_paths": total_paths,
            "paths_per_subproblem": total_paths / len(self.solution_paths) if self.solution_paths else 0,
            "selected_count": selected_count,
            "completion_percentage": (
                selected_count / len(self.solution_paths) * 100
                if self.solution_paths else 0
            ),
            "quick_wins": len(quick_wins),
            "high_risk_paths": len(high_risk),
            **avg_scores,
        }


class SolutionPlanner:
    """
    Planner zur automatischen Lösungswege-Generierung.
    
    Generiert mehrere Lösungspfade für Teilprobleme.
    """
    
    # Standard-Lösungsansätze pro SubProblem-Typ
    STANDARD_SOLUTIONS = {
        "technical": [
            ("Minimaler Hotfix", "Schnelle Minimal-Lösung für sofortige Entschärfung"),
            ("Refactoring", "Strukturelle Verbesserung des betroffenen Codes"),
            ("Komplette Neuentwicklung", "Full Rewrite mit modernem Ansatz"),
        ],
        "analysis": [
            ("Manuelle Analyse", "Gründliche manuelle Code-Analyse"),
            ("Automated Profiling", "Automatisierte Performance-Analyse"),
            ("External Audit", "Externes Review durch Spezialisten"),
        ],
        "integration": [
            ("Adapter-Pattern", "Adapter für Kompatibilität"),
            ("API-Gateway", "Gateway für zentrale Integration"),
            ("Direkte Integration", "Tight Coupling Integration"),
        ],
        "documentation": [
            ("Interne Dokumentation", "Code-Kommentare und README"),
            ("API-Dokumentation", "Swagger/OpenAPI Specs"),
            ("User-Guide", "Ausführliche Benutzerdokumentation"),
        ],
        "testing": [
            ("Unit Tests", "Umfassende Unit-Tests"),
            ("Integration Tests", "End-to-End Integrationstests"),
            ("Regression Tests", "Test-Suite für Regression"),
        ],
        "configuration": [
            ("Config-Änderung", "Nur Konfiguration anpassen"),
            ("Environment-Specific", "Umgebungs-spezifische Config"),
            ("Dynamic Config", "Dynamische Konfiguration"),
        ],
        "refactoring": [
            ("Inkrementelles Refactoring", "Schrittweise Verbesserung"),
            ("Big Refactor", "Großes Refactoring in einem Zug"),
            ("Strangler Pattern", "Schrittweise Migration"),
        ],
    }
    
    def __init__(self, repo_path: Optional[Path] = None):
        """
        Initialisiert SolutionPlanner.
        
        Args:
            repo_path: Pfad zum Repository für Code-Analyse
        """
        self.repo_path = repo_path
    
    def create_solution_plan(
        self,
        problem_id: str,
        subproblem_ids: List[str],
        decomposition_id: Optional[str] = None,
    ) -> SolutionPlan:
        """
        Erstellt Lösungsplan mit mehreren Pfaden pro Teilproblem.
        
        Args:
            problem_id: ID des Hauptproblems
            subproblem_ids: IDs der Teilprobleme
            decomposition_id: Optionale Referenz zur Decomposition
        
        Returns:
            SolutionPlan mit Lösungspfaden
        """
        plan = SolutionPlan(
            problem_id=problem_id,
            decomposition_id=decomposition_id,
        )
        
        # Für jedes Teilproblem Lösungspfade generieren
        for sp_id in subproblem_ids:
            self._generate_paths_for_subproblem(plan, sp_id)
        
        # Beste Pfade automatisch auswählen
        plan.auto_select_best_paths()
        
        # Gesamt-Strategie
        plan.overall_strategy = self._create_overall_strategy(plan)
        
        return plan
    
    def _generate_paths_for_subproblem(
        self,
        plan: SolutionPlan,
        subproblem_id: str,
    ) -> None:
        """Generiert Lösungspfade für ein Teilproblem."""
        # Standard-Lösungen verwenden
        # In echter Implementierung: SubProblem-Typ analysieren
        standard_solutions = self.STANDARD_SOLUTIONS.get(
            "technical",  # Default
            self.STANDARD_SOLUTIONS["technical"],
        )
        
        for i, (title, description) in enumerate(standard_solutions, 1):
            solution_type = self._infer_solution_type(title)
            
            plan.add_solution_path(
                subproblem_id=subproblem_id,
                title=title,
                description=description,
                solution_type=solution_type,
                effectiveness=8 - i,  # Erster ist meist wirksamster
                invasiveness=i * 2,  # Spätere sind invasiver
                risk=RiskLevel(["low", "medium", "high"][i-1]) if i <= 3 else RiskLevel.MEDIUM,
                effort=i * 3,
                testability=9 - i,
                implementation_steps=self._generate_implementation_steps(
                    solution_type, title
                ),
                estimated_hours=i * 4.0,
            )
    
    def _infer_solution_type(self, title: str) -> SolutionType:
        """Leitet SolutionType aus Titel ab."""
        title_lower = title.lower()
        
        if "hotfix" in title_lower or "minimal" in title_lower:
            return SolutionType.HOTFIX
        elif "refactor" in title_lower:
            return SolutionType.REFACTOR
        elif "neu" in title_lower or "rewrite" in title_lower:
            return SolutionType.REWRITE
        elif "config" in title_lower:
            return SolutionType.CONFIG_CHANGE
        elif "guard" in title_lower or "fallback" in title_lower:
            return SolutionType.GUARD
        elif "automat" in title_lower:
            return SolutionType.AUTOMATION
        else:
            return SolutionType.UNKNOWN
    
    def _generate_implementation_steps(
        self,
        solution_type: SolutionType,
        title: str,
    ) -> List[str]:
        """Generiert Umsetzungsschritte für Lösungstyp."""
        steps = {
            SolutionType.HOTFIX: [
                "Betroffenen Code identifizieren",
                "Minimalen Fix implementieren",
                "Smoke-Tests durchführen",
                "Deployen und monitoren",
            ],
            SolutionType.REFACTOR: [
                "Bestehende Struktur analysieren",
                "Refactoring-Ziele definieren",
                "Inkrementell refaktorisieren",
                "Tests nach jedem Schritt",
                "Dokumentation aktualisieren",
            ],
            SolutionType.REWRITE: [
                "Anforderungen dokumentieren",
                "Neue Architektur entwerfen",
                "Implementieren",
                "Umfassend testen",
                "Migration planen",
                "Alte Implementierung deprecated",
            ],
            SolutionType.CONFIG_CHANGE: [
                "Aktuelle Config dokumentieren",
                "Änderungen identifizieren",
                "In Test-Umgebung validieren",
                "Produktiv setzen",
                "Monitoring einrichten",
            ],
        }
        
        return steps.get(solution_type, [
            "Analyse durchführen",
            "Umsetzung planen",
            "Implementieren",
            "Testen",
            "Deployen",
        ])
    
    def _create_overall_strategy(self, plan: SolutionPlan) -> str:
        """Erstellt Gesamt-Strategie aus ausgewählten Pfaden."""
        selected_count = len(plan.selected_paths)
        total_count = len(plan.solution_paths)
        
        stats = plan.get_statistics()
        
        return (
            f"Lösungsstrategie mit {selected_count}/{total_count} ausgewählten Pfaden:\n"
            f"- {stats.get('quick_wins', 0)} Quick Wins identifiziert\n"
            f"- {stats.get('high_risk_paths', 0)}高风险ige Pfade\n"
            f"- Durchschnittlicher Score: {stats.get('avg_overall_score', 0):.1f}/10"
        )
