"""
Stack-spezifische Adapter für Problem-Solver.

Gemäß PROBLEM_SOLVER.md Phase 2.4:
- Capability-Profile für Stack A und Stack B
- Stack-spezifische Ausführungsfähigkeiten
- Feature-Flags pro Stack
- Transparente Darstellung von Stack-Unterschieden
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pathlib import Path


class StackID(Enum):
    """Verfügbare Stacks."""
    STACK_A = "stack_a"
    STACK_B = "stack_b"
    AUTO = "auto"  # Automatische Auswahl


class CapabilityLevel(Enum):
    """Fähigkeitsstufen."""
    NOT_SUPPORTED = "not_supported"  # Nicht unterstützt
    LIMITED = "limited"  # Eingeschränkt
    FULL = "full"  # Vollständig
    ENHANCED = "enhanced"  # Erweitert
    
    def __lt__(self, other):
        """Vergleicht CapabilityLevel für Sortierung."""
        order = {
            CapabilityLevel.NOT_SUPPORTED: 0,
            CapabilityLevel.LIMITED: 1,
            CapabilityLevel.FULL: 2,
            CapabilityLevel.ENHANCED: 3,
        }
        return order.get(self, 0) < order.get(other, 0)
    
    def __gt__(self, other):
        """Vergleicht CapabilityLevel für Sortierung."""
        order = {
            CapabilityLevel.NOT_SUPPORTED: 0,
            CapabilityLevel.LIMITED: 1,
            CapabilityLevel.FULL: 2,
            CapabilityLevel.ENHANCED: 3,
        }
        return order.get(self, 0) > order.get(other, 0)


@dataclass
class StackCapability:
    """
    Beschreibt eine einzelne Fähigkeit eines Stacks.
    """
    
    name: str
    level: CapabilityLevel
    description: str = ""
    
    # Details
    requirements: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    notes: str = ""
    
    def to_dict(self) -> dict:
        """Konvertiert zu Dictionary."""
        return {
            "name": self.name,
            "level": self.level.value,
            "description": self.description,
            "requirements": self.requirements,
            "limitations": self.limitations,
            "notes": self.notes,
        }
    
    def is_supported(self) -> bool:
        """Ist diese Fähigkeit unterstützt?"""
        return self.level != CapabilityLevel.NOT_SUPPORTED


@dataclass
class StackProfile:
    """
    Vollständiges Profil eines Stacks.
    
    Beschreibt alle Fähigkeiten und Eigenschaften.
    """
    
    stack_id: StackID
    name: str
    description: str = ""
    
    # Fähigkeiten
    capabilities: Dict[str, StackCapability] = field(default_factory=dict)
    
    # Ressourcen
    max_memory_gb: float = 0.0
    max_cpu_cores: int = 0
    gpu_available: bool = False
    gpu_memory_gb: float = 0.0
    
    # Features
    features: Dict[str, bool] = field(default_factory=dict)
    
    # Metadaten
    version: str = "1.0"
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        """Konvertiert zu Dictionary."""
        return {
            "stack_id": self.stack_id.value,
            "name": self.name,
            "description": self.description,
            "capabilities": {
                name: cap.to_dict() for name, cap in self.capabilities.items()
            },
            "resources": {
                "max_memory_gb": self.max_memory_gb,
                "max_cpu_cores": self.max_cpu_cores,
                "gpu_available": self.gpu_available,
                "gpu_memory_gb": self.gpu_memory_gb,
            },
            "features": self.features,
            "version": self.version,
            "last_updated": self.last_updated,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "StackProfile":
        """Erstellt StackProfile aus Dict."""
        capabilities = {
            name: StackCapability(
                name=cap["name"],
                level=CapabilityLevel(cap["level"]),
                description=cap.get("description", ""),
                requirements=cap.get("requirements", []),
                limitations=cap.get("limitations", []),
                notes=cap.get("notes", ""),
            )
            for name, cap in data.get("capabilities", {}).items()
        }
        
        return cls(
            stack_id=StackID(data["stack_id"]),
            name=data["name"],
            description=data.get("description", ""),
            capabilities=capabilities,
            max_memory_gb=data.get("resources", {}).get("max_memory_gb", 0.0),
            max_cpu_cores=data.get("resources", {}).get("max_cpu_cores", 0),
            gpu_available=data.get("resources", {}).get("gpu_available", False),
            gpu_memory_gb=data.get("resources", {}).get("gpu_memory_gb", 0.0),
            features=data.get("features", {}),
            version=data.get("version", "1.0"),
            last_updated=data.get("last_updated", datetime.now().isoformat()),
        )
    
    def add_capability(
        self,
        name: str,
        level: CapabilityLevel,
        description: str = "",
        requirements: Optional[List[str]] = None,
        limitations: Optional[List[str]] = None,
    ) -> StackCapability:
        """Fügt eine Fähigkeit hinzu."""
        cap = StackCapability(
            name=name,
            level=level,
            description=description,
            requirements=requirements or [],
            limitations=limitations or [],
        )
        self.capabilities[name] = cap
        self.last_updated = datetime.now().isoformat()
        return cap
    
    def get_capability(self, name: str) -> Optional[StackCapability]:
        """Returns Fähigkeit nach Name."""
        return self.capabilities.get(name)
    
    def is_capable(self, name: str) -> bool:
        """Kann dieser Stack eine Fähigkeit ausführen?"""
        cap = self.get_capability(name)
        return cap.is_supported() if cap else False
    
    def has_feature(self, name: str) -> bool:
        """Hat dieser Stack ein Feature?"""
        return self.features.get(name, False)
    
    def get_execution_order(
        self,
        subproblem_ids: List[str],
        dependencies: Dict[str, List[str]],
    ) -> List[str]:
        """
        Berechnet stack-spezifische Ausführungsreihenfolge.
        
        Args:
            subproblem_ids: IDs der Teilprobleme
            dependencies: Dependency-Graph (sp_id -> Liste der Vorgänger)
        
        Returns:
            Sortierte Liste von IDs
        
        Beispiel:
            dependencies = {"sp2": ["sp1"]} bedeutet: sp2 hängt von sp1 ab,
            also muss sp1 zuerst ausgeführt werden.
        """
        # Einfache topologische Sortierung
        # Stack-spezifische Optimierungen können hier hinzugefügt werden
        from collections import deque
        
        # in_degree zählt wie viele Vorgänger ein Knoten hat
        in_degree = {sp_id: 0 for sp_id in subproblem_ids}
        
        # dependencies[sp_id] = Liste der Vorgänger von sp_id
        # Also: für jeden Vorgänger erhöhen wir den in_degree von sp_id
        for sp_id, predecessors in dependencies.items():
            in_degree[sp_id] = len(predecessors)
        
        # Starte mit Knoten ohne Vorgänger
        queue = deque([sp_id for sp_id in subproblem_ids if in_degree[sp_id] == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            # Finde alle Nachfolger (Knoten die von current abhängen)
            for sp_id, predecessors in dependencies.items():
                if current in predecessors:
                    in_degree[sp_id] -= 1
                    if in_degree[sp_id] == 0:
                        queue.append(sp_id)
        
        # Restliche hinzufügen (falls zyklische Abhängigkeiten)
        remaining = [sp_id for sp_id in subproblem_ids if sp_id not in result]
        result.extend(remaining)
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """Returns Statistik über Stack-Profil."""
        total_caps = len(self.capabilities)
        supported = sum(
            1 for cap in self.capabilities.values()
            if cap.is_supported()
        )
        
        by_level = {}
        for cap in self.capabilities.values():
            level = cap.level.value
            by_level[level] = by_level.get(level, 0) + 1
        
        enabled_features = sum(1 for v in self.features.values() if v)
        
        return {
            "stack_id": self.stack_id.value,
            "total_capabilities": total_caps,
            "supported_capabilities": supported,
            "capability_coverage": (supported / total_caps * 100) if total_caps > 0 else 0,
            "by_level": by_level,
            "enabled_features": enabled_features,
            "total_features": len(self.features),
            "resources": {
                "memory_gb": self.max_memory_gb,
                "cpu_cores": self.max_cpu_cores,
                "gpu": f"{self.gpu_memory_gb}GB" if self.gpu_available else "N/A",
            },
        }


class StackAdapterManager:
    """
    Manager für Stack-Adapter.
    
    Verwaltet Profile für beide Stacks und ermöglicht
    stack-spezifische Entscheidungen.
    """
    
    # Standard-Capabilities für beide Stacks
    STANDARD_CAPABILITIES = [
        ("code_analysis", "Code-Analyse und Parsing"),
        ("symbol_graph", "Symbol-Graph Erstellung"),
        ("complexity_analysis", "Komplexitäts-Analyse"),
        ("security_scan", "Security-Scan (Semgrep)"),
        ("llm_analysis", "LLM-basierte Analyse"),
        ("hypothesis_generation", "Hypothesen-Generierung"),
        ("evidence_collection", "Evidence-Sammlung"),
        ("patch_generation", "Patch-Generierung"),
        ("patch_verification", "Patch-Verifikation"),
        ("test_generation", "Test-Generierung"),
        ("dynamic_analysis", "Dynamic Analysis / Fuzzing"),
        ("coverage_tracking", "Coverage-Tracking"),
        ("report_generation", "Report-Generierung"),
        ("tui_support", "TUI-Unterstützung"),
        ("api_support", "API-Unterstützung"),
    ]
    
    def __init__(self, repo_path: Optional[Path] = None):
        """
        Initialisiert StackAdapterManager.
        
        Args:
            repo_path: Pfad zum Repository
        """
        self.repo_path = repo_path
        self.profiles: Dict[StackID, StackProfile] = {}
        
        # Standard-Profile laden
        self._load_default_profiles()
    
    def _load_default_profiles(self) -> None:
        """Lädt Standard-Profile für beide Stacks."""
        
        # Stack A: Standard-Stack (8GB VRAM)
        stack_a = StackProfile(
            stack_id=StackID.STACK_A,
            name="Stack A (Standard)",
            description="Standard-Stack für 8GB GPU Konfiguration",
            max_memory_gb=32,
            max_cpu_cores=8,
            gpu_available=True,
            gpu_memory_gb=8.0,
        )
        
        # Capabilities für Stack A
        for name, description in self.STANDARD_CAPABILITIES:
            level = CapabilityLevel.FULL
            # Dynamic Analysis nur LIMITED für Stack A
            if name == "dynamic_analysis":
                level = CapabilityLevel.LIMITED
            
            stack_a.add_capability(
                name=name,
                level=level,
                description=description,
            )
        
        # Features für Stack A
        stack_a.features = {
            "ensemble_mode": False,  # Nur Stack B
            "multi_model_voting": False,
            "parallel_fuzzing": False,
            "enhanced_reports": True,
            "tui_full": True,
            "api_full": True,
        }
        
        # Stack B: Enhanced-Stack (24GB VRAM)
        stack_b = StackProfile(
            stack_id=StackID.STACK_B,
            name="Stack B (Enhanced)",
            description="Enhanced-Stack für 24GB GPU Konfiguration",
            max_memory_gb=64,
            max_cpu_cores=16,
            gpu_available=True,
            gpu_memory_gb=24.0,
        )
        
        # Capabilities für Stack B (alle FULL oder ENHANCED)
        for name, description in self.STANDARD_CAPABILITIES:
            level = CapabilityLevel.ENHANCED if name in (
                "llm_analysis", "dynamic_analysis", "patch_generation"
            ) else CapabilityLevel.FULL
            
            stack_b.add_capability(
                name=name,
                level=level,
                description=description,
            )
        
        # Features für Stack B (mehr Features)
        stack_b.features = {
            "ensemble_mode": True,
            "multi_model_voting": True,
            "parallel_fuzzing": True,
            "enhanced_reports": True,
            "tui_full": True,
            "api_full": True,
            "auto_fix": True,
            "goal_validation": True,
        }
        
        # Speichern
        self.profiles[StackID.STACK_A] = stack_a
        self.profiles[StackID.STACK_B] = stack_b
    
    def get_profile(self, stack_id: StackID) -> StackProfile:
        """Returns Profil für Stack."""
        return self.profiles.get(stack_id)
    
    def get_all_profiles(self) -> Dict[StackID, StackProfile]:
        """Returns alle Profile."""
        return self.profiles.copy()
    
    def compare_stacks(
        self,
        capability_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Vergleicht beide Stacks.
        
        Args:
            capability_name: Optionale spezifische Fähigkeit
        
        Returns:
            Vergleichs-Dict
        """
        stack_a = self.profiles.get(StackID.STACK_A)
        stack_b = self.profiles.get(StackID.STACK_B)
        
        if not stack_a or not stack_b:
            return {}
        
        comparison = {
            "stack_a": {
                "name": stack_a.name,
                "capabilities": stack_a.get_statistics(),
            },
            "stack_b": {
                "name": stack_b.name,
                "capabilities": stack_b.get_statistics(),
            },
            "differences": {},
        }
        
        if capability_name:
            # Spezifische Fähigkeit vergleichen
            cap_a = stack_a.get_capability(capability_name)
            cap_b = stack_b.get_capability(capability_name)

            comparison["differences"][capability_name] = {
                "stack_a": cap_a.to_dict() if cap_a else None,
                "stack_b": cap_b.to_dict() if cap_b else None,
                "winner": "stack_b" if (
                    cap_b and cap_a and cap_b.level > cap_a.level
                ) else "stack_a" if cap_a else "stack_b",
            }
        else:
            # Allgemeine Unterschiede
            stats_a = stack_a.get_statistics()
            stats_b = stack_b.get_statistics()
            
            comparison["differences"]["capability_coverage"] = {
                "stack_a": stats_a["capability_coverage"],
                "stack_b": stats_b["capability_coverage"],
                "difference": stats_b["capability_coverage"] - stats_a["capability_coverage"],
            }
            
            comparison["differences"]["resources"] = {
                "memory": {
                    "stack_a": stack_a.max_memory_gb,
                    "stack_b": stack_b.max_memory_gb,
                },
                "cpu": {
                    "stack_a": stack_a.max_cpu_cores,
                    "stack_b": stack_b.max_cpu_cores,
                },
                "gpu": {
                    "stack_a": stack_a.gpu_memory_gb,
                    "stack_b": stack_b.gpu_memory_gb,
                },
            }
        
        return comparison
    
    def recommend_stack(
        self,
        problem_type: str,
        required_capabilities: Optional[List[str]] = None,
    ) -> StackID:
        """
        Empfiehlt besten Stack für Problem.
        
        Args:
            problem_type: Typ des Problems
            required_capabilities: Geforderte Fähigkeiten
        
        Returns:
            Empfohlene StackID
        """
        # Standard-Empfehlungen
        recommendations = {
            "performance": StackID.STACK_B,  # Braucht mehr Ressourcen
            "dynamic_analysis": StackID.STACK_B,
            "ensemble": StackID.STACK_B,
            "bug": StackID.STACK_A,  # Geht auch mit Stack A
            "missing_feature": StackID.STACK_A,
            "ux_issue": StackID.STACK_A,
        }
        
        # Basierend auf Problemtyp
        if problem_type in recommendations:
            return recommendations[problem_type]
        
        # Basierend auf required Capabilities
        if required_capabilities:
            for cap_name in required_capabilities:
                cap_a = self.profiles[StackID.STACK_A].get_capability(cap_name)
                cap_b = self.profiles[StackID.STACK_B].get_capability(cap_name)

                if cap_b and cap_a and cap_b.level > cap_a.level:
                    return StackID.STACK_B
        
        # Default zu Stack A (ressourcenschonender)
        return StackID.STACK_A
    
    def validate_stack_compatibility(
        self,
        solution_plan_id: str,
        stack_id: StackID,
    ) -> Dict[str, Any]:
        """
        Validiert ob Solution-Plan mit Stack kompatibel ist.
        
        Args:
            solution_plan_id: ID des Solution-Plans
            stack_id: Ziel-Stack
        
        Returns:
            Validierungs-Ergebnis
        """
        profile = self.get_profile(stack_id)
        if not profile:
            return {
                "compatible": False,
                "errors": ["Stack-Profil nicht gefunden"],
            }
        
        # Hier könnte man den Solution-Plan laden und prüfen
        # Für Phase 2.4 reicht ein Stub
        return {
            "compatible": True,
            "warnings": [],
            "stack": profile.name,
        }


def create_stack_adapter(repo_path: Optional[Path] = None) -> StackAdapterManager:
    """
    Factory-Funktion für StackAdapterManager.
    
    Args:
        repo_path: Pfad zum Repository
    
    Returns:
        Initialisierter StackAdapterManager
    """
    return StackAdapterManager(repo_path=repo_path)
