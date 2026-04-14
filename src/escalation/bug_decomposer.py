"""
Bug Decomposer für GlitchHunter Escalation Level 2.

Zerlegt komplexe Bugs in 2-4 Sub-Bugs mit eigenen Mini-Loops.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DecomposedBug:
    """
    Zerlegter Sub-Bug.

    Attributes:
        sub_bug_id: Sub-Bug-ID
        description: Beschreibung
        priority: Priorität (high, medium, low)
        parent_bug_id: Parent-Bug-ID
        file_path: Dateipfad
        hypothesis: Hypothese für Sub-Bug
        confidence: Konfidenz
    """

    sub_bug_id: str
    description: str
    priority: str = "medium"
    parent_bug_id: str = ""
    file_path: str = ""
    hypothesis: str = ""
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "sub_bug_id": self.sub_bug_id,
            "description": self.description,
            "priority": self.priority,
            "parent_bug_id": self.parent_bug_id,
            "file_path": self.file_path,
            "hypothesis": self.hypothesis,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class DecompositionResult:
    """
    Ergebnis der Bug-Zerlegung.

    Attributes:
        original_bug: Originaler Bug
        sub_bugs: Zerlegte Sub-Bugs
        decomposition_strategy: Zerlegungs-Strategie
        total_sub_bugs: Anzahl Sub-Bugs
    """

    original_bug: Dict[str, Any]
    sub_bugs: List[DecomposedBug] = field(default_factory=list)
    decomposition_strategy: str = ""
    total_sub_bugs: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "original_bug": self.original_bug,
            "sub_bugs": [sb.to_dict() for sb in self.sub_bugs],
            "decomposition_strategy": self.decomposition_strategy,
            "total_sub_bugs": self.total_sub_bugs,
        }


class BugDecomposer:
    """
    Zerlegt komplexe Bugs in Sub-Bugs.

    Strategien:
    - Causal Analysis: Nach Ursachen zerlegen
    - Component-Based: Nach Komponenten zerlegen
    - Symptom-Based: Nach Symptomen zerlegen

    Usage:
        decomposer = BugDecomposer()
        result = decomposer.decompose(complex_bug)
    """

    MAX_SUB_BUGS = 4  # Maximal 4 Sub-Bugs

    def __init__(self) -> None:
        """Initialisiert Bug Decomposer."""
        logger.debug("BugDecomposer initialisiert")

    def decompose(
        self,
        bug: Dict[str, Any],
        strategy: str = "causal",
    ) -> DecompositionResult:
        """
        Zerlegt Bug in Sub-Bugs.

        Args:
            bug: Originaler Bug.
            strategy: Zerlegungs-Strategie.

        Returns:
            DecompositionResult.
        """
        logger.info(f"Zerlege Bug: {bug.get('bug_id', 'unknown')} mit {strategy}")

        result = DecompositionResult(
            original_bug=bug,
            decomposition_strategy=strategy,
        )

        if strategy == "causal":
            result.sub_bugs = self._decompose_causal(bug)
        elif strategy == "component":
            result.sub_bugs = self._decompose_component(bug)
        elif strategy == "symptom":
            result.sub_bugs = self._decompose_symptom(bug)
        else:
            result.sub_bugs = self._decompose_default(bug)

        # Auf MAX_SUB_BUGS begrenzen
        result.sub_bugs = result.sub_bugs[: self.MAX_SUB_BUGS]
        result.total_sub_bugs = len(result.sub_bugs)

        logger.info(f"Bug zerlegt in {result.total_sub_bugs} Sub-Bugs")

        return result

    def _decompose_causal(self, bug: Dict[str, Any]) -> List[DecomposedBug]:
        """
        Zerlegt nach Ursachen (Causal Analysis).

        Args:
            bug: Bug.

        Returns:
            Liste von Sub-Bugs.
        """
        sub_bugs = []
        bug_id = bug.get("bug_id", "unknown")
        bug_type = bug.get("bug_type", "unknown")
        file_path = bug.get("file_path", "")

        # Standard-Zerlegung für Causal Analysis
        sub_bugs.append(DecomposedBug(
            sub_bug_id=f"{bug_id}.1",
            description=f"Root cause analysis for {bug_type}",
            priority="high",
            parent_bug_id=bug_id,
            file_path=file_path,
            hypothesis="Root cause is in the initial data flow",
            confidence=0.7,
            metadata={"analysis_type": "root_cause"},
        ))

        sub_bugs.append(DecomposedBug(
            sub_bug_id=f"{bug_id}.2",
            description=f"Contributing factors for {bug_type}",
            priority="medium",
            parent_bug_id=bug_id,
            file_path=file_path,
            hypothesis="Secondary factors amplify the issue",
            confidence=0.5,
            metadata={"analysis_type": "contributing_factors"},
        ))

        sub_bugs.append(DecomposedBug(
            sub_bug_id=f"{bug_id}.3",
            description=f"Side effects of {bug_type}",
            priority="low",
            parent_bug_id=bug_id,
            file_path=file_path,
            hypothesis="Side effects propagate through the system",
            confidence=0.4,
            metadata={"analysis_type": "side_effects"},
        ))

        return sub_bugs

    def _decompose_component(self, bug: Dict[str, Any]) -> List[DecomposedBug]:
        """
        Zerlegt nach Komponenten.

        Args:
            bug: Bug.

        Returns:
            Liste von Sub-Bugs.
        """
        sub_bugs = []
        bug_id = bug.get("bug_id", "unknown")
        bug_type = bug.get("bug_type", "unknown")
        file_path = bug.get("file_path", "")

        # Nach Komponenten zerlegen
        sub_bugs.append(DecomposedBug(
            sub_bug_id=f"{bug_id}.1",
            description=f"Input validation issue in {bug_type}",
            priority="high",
            parent_bug_id=bug_id,
            file_path=file_path,
            hypothesis="Input is not properly validated",
            confidence=0.6,
            metadata={"component": "input"},
        ))

        sub_bugs.append(DecomposedBug(
            sub_bug_id=f"{bug_id}.2",
            description=f"Processing logic issue in {bug_type}",
            priority="high",
            parent_bug_id=bug_id,
            file_path=file_path,
            hypothesis="Processing logic has flaws",
            confidence=0.6,
            metadata={"component": "processing"},
        ))

        sub_bugs.append(DecomposedBug(
            sub_bug_id=f"{bug_id}.3",
            description=f"Output handling issue in {bug_type}",
            priority="medium",
            parent_bug_id=bug_id,
            file_path=file_path,
            hypothesis="Output is not properly handled",
            confidence=0.5,
            metadata={"component": "output"},
        ))

        return sub_bugs

    def _decompose_symptom(self, bug: Dict[str, Any]) -> List[DecomposedBug]:
        """
        Zerlegt nach Symptomen.

        Args:
            bug: Bug.

        Returns:
            Liste von Sub-Bugs.
        """
        sub_bugs = []
        bug_id = bug.get("bug_id", "unknown")
        bug_type = bug.get("bug_type", "unknown")
        file_path = bug.get("file_path", "")

        # Nach Symptomen zerlegen
        sub_bugs.append(DecomposedBug(
            sub_bug_id=f"{bug_id}.1",
            description=f"Primary symptom of {bug_type}",
            priority="high",
            parent_bug_id=bug_id,
            file_path=file_path,
            hypothesis="Primary symptom indicates core issue",
            confidence=0.7,
            metadata={"symptom_type": "primary"},
        ))

        sub_bugs.append(DecomposedBug(
            sub_bug_id=f"{bug_id}.2",
            description=f"Secondary symptoms of {bug_type}",
            priority="medium",
            parent_bug_id=bug_id,
            file_path=file_path,
            hypothesis="Secondary symptoms are cascading effects",
            confidence=0.5,
            metadata={"symptom_type": "secondary"},
        ))

        return sub_bugs

    def _decompose_default(self, bug: Dict[str, Any]) -> List[DecomposedBug]:
        """
        Standard-Zerlegung.

        Args:
            bug: Bug.

        Returns:
            Liste von Sub-Bugs.
        """
        return self._decompose_causal(bug)

    def prioritize_sub_bugs(
        self,
        sub_bugs: List[DecomposedBug],
    ) -> List[DecomposedBug]:
        """
        Priorisiert Sub-Bugs.

        Args:
            sub_bugs: Liste von Sub-Bugs.

        Returns:
            Priorisierte Liste.
        """
        priority_order = {"high": 0, "medium": 1, "low": 2}

        return sorted(
            sub_bugs,
            key=lambda sb: (
                priority_order.get(sb.priority, 2),
                -sb.confidence,
            ),
        )

    def __call__(self, state: Any) -> Dict[str, Any]:
        """
        Callable für LangGraph.

        Args:
            state: AgentState.

        Returns:
            State-Updates.
        """
        bug = getattr(state, "current_bug", {})
        strategy = getattr(state, "decomposition_strategy", "causal")

        result = self.decompose(bug, strategy)

        return {
            "decomposition_result": result.to_dict(),
            "sub_bugs": [sb.to_dict() for sb in result.sub_bugs],
            "metadata": {
                "decomposition_complete": True,
                "total_sub_bugs": result.total_sub_bugs,
                "strategy": result.decomposition_strategy,
            },
        }
