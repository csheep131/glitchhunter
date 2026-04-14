"""
Post-Apply Verifier für GlitchHunter.

Validiert Patches NACH dem Anwenden mit:
- Verifier-Confidence >= 95%
- Graph-Vergleich (Before/After Data-Flow und Call-Graph)
- Breaking Changes Detection
- Regression Test Results
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from fixing.pre_apply_validator import Gate1Result

logger = logging.getLogger(__name__)


@dataclass
class BreakingChange:
    """
    Breaking Change-Information.

    Attributes:
        description: Beschreibung des Problems
        severity: Schweregrad (warning, error, critical)
        affected_symbols: Betroffene Symbole
        evidence: Evidenz für Breaking Change
    """

    description: str
    severity: str = "error"
    affected_symbols: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "description": self.description,
            "severity": self.severity,
            "affected_symbols": self.affected_symbols,
            "evidence": self.evidence,
        }


@dataclass
class Gate2Result:
    """
    Ergebnis der Post-Apply Validierung (Gate 2).

    Attributes:
        passed: True wenn alle Checks bestanden.
        verifier_confidence: Verifier-Confidence (0-1).
        breaking_changes: Liste von Breaking Changes.
        graph_changes: Änderungen in Graphs.
        test_results: Test-Ergebnisse.
        regression_detected: True wenn Regression erkannt.
    """

    passed: bool = False
    verifier_confidence: float = 0.0
    breaking_changes: List[BreakingChange] = field(default_factory=list)
    graph_changes: Dict[str, Any] = field(default_factory=dict)
    test_results: List[Dict[str, Any]] = field(default_factory=list)
    regression_detected: bool = False

    @property
    def has_critical_breaking_changes(self) -> bool:
        """True wenn kritische Breaking Changes."""
        return any(bc.severity == "critical" for bc in self.breaking_changes)

    @property
    def confidence_threshold_met(self) -> bool:
        """True wenn Confidence >= 95%."""
        return self.verifier_confidence >= 0.95

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "passed": self.passed,
            "verifier_confidence": self.verifier_confidence,
            "breaking_changes": [bc.to_dict() for bc in self.breaking_changes],
            "graph_changes": self.graph_changes,
            "test_results": self.test_results,
            "regression_detected": self.regression_detected,
            "has_critical_breaking_changes": self.has_critical_breaking_changes,
            "confidence_threshold_met": self.confidence_threshold_met,
        }


class PostApplyVerifier:
    """
    Validiert Patches nach dem Anwenden (Gate 2).

    Checks:
    1. Verifier-Confidence >= 95%
    2. Graph-Vergleich (Before/After)
    3. Breaking Changes Detection
    4. Regression Test Results

    Usage:
        verifier = PostApplyVerifier()
        result = verifier.verify(original_code, patched_code, before_graph, after_graph)
    """

    CONFIDENCE_THRESHOLD = 0.95  # 95% Confidence erforderlich

    def __init__(
        self,
        model_path: Optional[str] = None,
        use_llm: bool = True,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
    ) -> None:
        """
        Initialisiert Post-Apply Verifier.

        Args:
            model_path: Pfad zum LLM-Modell.
            use_llm: LLM-Verifikation aktivieren.
            confidence_threshold: Confidence-Schwelle (0-1).
        """
        self.model_path = model_path
        self.use_llm = use_llm
        self.confidence_threshold = confidence_threshold

        self._engine = None
        if use_llm and model_path:
            self._init_engine()

        logger.debug(
            f"PostApplyVerifier initialisiert: use_llm={use_llm}, "
            f"threshold={confidence_threshold}"
        )

    def _init_engine(self) -> None:
        """Initialisiert Inference-Engine."""
        try:
            from inference.engine import InferenceEngine, InferenceConfig

            self._engine = InferenceEngine(
                model_path=self.model_path,
                config=InferenceConfig(
                    temperature=0.0,  # Deterministisch für Verifikation
                    max_tokens=1024,
                ),
            )
            logger.info("Inference-Engine für Verifier initialisiert")
        except Exception as e:
            logger.warning(f"Konnte Inference-Engine nicht initialisieren: {e}")
            self.use_llm = False

    def verify(
        self,
        original_code: str,
        patched_code: str,
        before_graph: Dict[str, Any],
        after_graph: Dict[str, Any],
        test_results: Optional[List[Dict[str, Any]]] = None,
        gate1_result: Optional[Gate1Result] = None,
    ) -> Gate2Result:
        """
        Verifiziert Patch nach dem Anwenden.

        Args:
            original_code: Original-Code.
            patched_code: Gepatchter Code.
            before_graph: Graph vor Patch.
            after_graph: Graph nach Patch.
            test_results: Test-Ergebnisse.
            gate1_result: Ergebnis von Gate 1.

        Returns:
            Gate2Result.
        """
        logger.info("Starte Post-Apply Verifikation (Gate 2)")

        result = Gate2Result()

        # 1. LLM-basierte Verifikation
        if self.use_llm and self._engine:
            result.verifier_confidence = self._verify_with_llm(
                original_code, patched_code
            )
        else:
            result.verifier_confidence = self._verify_rule_based(
                original_code, patched_code, test_results
            )

        # 2. Graph-Vergleich
        result.graph_changes = self._compare_graphs(before_graph, after_graph)

        # 3. Breaking Changes identifizieren
        result.breaking_changes = self._identify_breaking_changes(
            result.graph_changes, result.verifier_confidence
        )

        # 4. Test-Ergebnisse verarbeiten
        if test_results:
            result.test_results = test_results
            result.regression_detected = self._check_for_regressions(test_results)

        # Gesamtergebnis bestimmen
        result.passed = (
            result.confidence_threshold_met
            and not result.has_critical_breaking_changes
            and not result.regression_detected
        )

        logger.info(
            f"Post-Apply Verifikation abgeschlossen: "
            f"passed={result.passed}, confidence={result.verifier_confidence:.2f}"
        )

        return result

    def _verify_with_llm(
        self,
        original_code: str,
        patched_code: str,
    ) -> float:
        """
        Verifiziert mit LLM.

        Args:
            original_code: Original-Code.
            patched_code: Gepatchter Code.

        Returns:
            Confidence-Score (0-1).
        """
        if not self._engine:
            return 0.5  # Default bei fehlender Engine

        prompt = f"""Du bist ein Code-Verifier. Überprüfe den folgenden Patch:

ORIGINAL CODE:
```python
{original_code[:2000]}
```

PATCHED CODE:
```python
{patched_code[:2000]}
```

AUFGABE:
1. Hat der Patch neue Bugs eingeführt?
2. Ist der Patch korrekt?
3. Wie hoch ist deine Confidence (0.0-1.0)?

ANTWORT (nur Zahl 0.0-1.0):
"""

        try:
            response = self._engine.generate(
                prompt=prompt,
                system_prompt="Du bist ein Code-Verifier. Antworte präzise.",
            )

            # Confidence aus Response extrahieren
            content = response.content.strip()

            # Zahl aus Text extrahieren
            import re

            match = re.search(r"(\d+\.?\d*)", content)
            if match:
                confidence = float(match.group(1))
                return min(max(confidence, 0.0), 1.0)

            return 0.5

        except Exception as e:
            logger.error(f"LLM-Verifikation-Fehler: {e}")
            return 0.5

    def _verify_rule_based(
        self,
        original_code: str,
        patched_code: str,
        test_results: Optional[List[Dict[str, Any]]] = None,
    ) -> float:
        """
        Regelbasierte Verifikation (Fallback).

        Args:
            original_code: Original-Code.
            patched_code: Gepatchter Code.
            test_results: Test-Ergebnisse.

        Returns:
            Confidence-Score (0-1).
        """
        confidence = 0.7  # Base Confidence

        # Test-Ergebnisse einbeziehen
        if test_results:
            passed_tests = sum(1 for t in test_results if t.get("passed", False))
            total_tests = len(test_results)

            if total_tests > 0:
                test_ratio = passed_tests / total_tests
                confidence = 0.5 + (test_ratio * 0.5)  # 0.5-1.0 basierend auf Tests

        # Code-Änderungen einbeziehen
        diff_lines = self._count_diff_lines(original_code, patched_code)
        if diff_lines > 100:
            confidence -= 0.2  # Große Änderungen reduzieren Confidence

        return max(min(confidence, 1.0), 0.0)

    def _compare_graphs(
        self,
        before_graph: Dict[str, Any],
        after_graph: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Vergleicht Before/After Graphs.

        Args:
            before_graph: Graph vor Patch.
            after_graph: Graph nach Patch.

        Returns:
            Graph-Comparison als Dict.
        """
        try:

            comparator = GraphComparator()
            comparison = comparator.compare(before_graph, after_graph, graph_type="dfg")

            return comparison.to_dict()

        except Exception as e:
            logger.error(f"Graph-Vergleich-Fehler: {e}")
            return {"error": str(e)}

    def _identify_breaking_changes(
        self,
        graph_changes: Dict[str, Any],
        verifier_confidence: float,
    ) -> List[BreakingChange]:
        """
        Identifiziert Breaking Changes.

        Args:
            graph_changes: Graph-Änderungen.
            verifier_confidence: Verifier-Confidence.

        Returns:
            Liste von BreakingChange.
        """
        breaking_changes = []

        # Breaking Changes aus Graph-Vergleich
        if "breaking_changes" in graph_changes:
            for bc in graph_changes.get("breaking_changes", []):
                breaking_changes.append(BreakingChange(
                    description=bc if isinstance(bc, str) else str(bc),
                    severity="critical" if "security" in str(bc).lower() else "error",
                ))

        # Security-relevante Änderungen
        if graph_changes.get("has_security_relevant_changes", False):
            breaking_changes.append(BreakingChange(
                description="Security-relevante Änderung im Data-Flow erkannt",
                severity="critical",
            ))

        # Low Confidence als Breaking Change
        if verifier_confidence < self.confidence_threshold:
            breaking_changes.append(BreakingChange(
                description=f"Verifier-Confidence zu niedrig: {verifier_confidence:.2f} < {self.confidence_threshold}",
                severity="error",
                evidence={"confidence": verifier_confidence},
            ))

        return breaking_changes

    def _check_for_regressions(
        self,
        test_results: List[Dict[str, Any]],
    ) -> bool:
        """
        Prüft auf Regressionen in Test-Ergebnissen.

        Args:
            test_results: Test-Ergebnisse.

        Returns:
            True wenn Regression erkannt.
        """
        if not test_results:
            return False

        # Regression wenn Tests fehlschlagen
        failed_tests = sum(1 for t in test_results if not t.get("passed", False))
        return failed_tests > 0

    def _count_diff_lines(self, original: str, patched: str) -> int:
        """
        Zählt Anzahl unterschiedlicher Zeilen.

        Args:
            original: Original-Code.
            patched: Gepatchter Code.

        Returns:
            Anzahl unterschiedlicher Zeilen.
        """
        original_lines = set(original.split("\n"))
        patched_lines = set(patched.split("\n"))

        added = len(patched_lines - original_lines)
        removed = len(original_lines - patched_lines)

        return added + removed

    def verify_all(
        self,
        patches: List[Dict[str, Any]],
        original_code: str,
        before_graph: Dict[str, Any],
        after_graph: Dict[str, Any],
        test_results: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Gate2Result]:
        """
        Verifiziert alle Patches.

        Args:
            patches: Liste von Patches.
            original_code: Original-Code.
            before_graph: Graph vor Patch.
            after_graph: Graph nach Patch.
            test_results: Test-Ergebnisse.

        Returns:
            Liste von Gate2Result.
        """
        results = []

        for patch in patches:
            patched_code = patch.get("patched_code", original_code)

            result = self.verify(
                original_code=original_code,
                patched_code=patched_code,
                before_graph=before_graph,
                after_graph=after_graph,
                test_results=test_results,
            )

            results.append(result)

        return results

    def __call__(self, state: Any) -> Dict[str, Any]:
        """
        Callable für LangGraph.

        Args:
            state: AgentState.

        Returns:
            State-Updates.
        """
        # TODO: Typisierung verbessern
        original_code = getattr(state, "original_code", "")
        patched_code = getattr(state, "patched_code", "")
        before_graph = getattr(state, "before_graph", {})
        after_graph = getattr(state, "after_graph", {})
        test_results = getattr(state, "test_results", [])

        result = self.verify(
            original_code=original_code,
            patched_code=patched_code,
            before_graph=before_graph,
            after_graph=after_graph,
            test_results=test_results,
        )

        return {
            "gate2_result": result.to_dict(),
            "metadata": {
                "gate2_passed": result.passed,
                "verifier_confidence": result.verifier_confidence,
                "breaking_changes_count": len(result.breaking_changes),
                "regression_detected": result.regression_detected,
            },
        }
