"""
LLift Prioritizer für GlitchHunter Phase 2.

Hybrid Static + LLM Prioritization für Bug-Candidates:
- Semgrep-Ergebnisse gewichten
- LLM-basierte Priorisierung (Phi-4-mini, DeepSeek-V3.2)
- Evidence-Weighting und Confidence-Scoring
- Stack-spezifische Optimierung (A: sequentiell, B: parallel)

Usage:
    prioritizer = LLiftPrioritizer(model_path="path/to/phi-4-mini.gguf")
    result = prioritizer.prioritize(candidates, semgrep_results)
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import time

logger = logging.getLogger(__name__)


class Priority(str, Enum):
    """Prioritäts-Level."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class StaticAnalysisType(str, Enum):
    """Typen der statischen Analyse."""

    SEMGREP = "semgrep"
    COMPLEXITY = "complexity"
    GIT_CHURN = "git_churn"
    AST_PATTERN = "ast_pattern"


@dataclass
class SemgrepResult:
    """
    Semgrep-Analyseergebnis.

    Attributes:
        rule_id: Semgrep-Regel-ID
        severity: Schweregrad
        message: Fehlermeldung
        file_path: Dateipfad
        line_number: Zeilennummer
        code_snippet: Code-Schnipsel
    """

    rule_id: str
    severity: str
    message: str
    file_path: str
    line_number: int
    code_snippet: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "code_snippet": self.code_snippet,
            "metadata": self.metadata,
        }


@dataclass
class ChurnAnalysis:
    """
    Git-Churn-Analyse.

    Attributes:
        file_path: Dateipfad
        churn_score: Churn-Score (0-1)
        complexity_score: Komplexitäts-Score (0-1)
        hotspot_score: Hotspot-Score (0-1)
        recent_commits: Anzahl recent Commits
        authors: Anzahl verschiedener Autoren
    """

    file_path: str
    churn_score: float = 0.0
    complexity_score: float = 0.0
    hotspot_score: float = 0.0
    recent_commits: int = 0
    authors: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "file_path": self.file_path,
            "churn_score": self.churn_score,
            "complexity_score": self.complexity_score,
            "hotspot_score": self.hotspot_score,
            "recent_commits": self.recent_commits,
            "authors": self.authors,
        }


@dataclass
class PrioritizationResult:
    """
    Ergebnis der Priorisierung.

    Attributes:
        candidate_id: Kandidaten-ID
        priority: Prioritäts-Level
        priority_score: Score (0-100)
        confidence: Konfidenz (0-1)
        static_score: Statische Analyse Score
        llm_score: LLM Score
        reasoning: Begründung
        semgrep_results: Semgrep-Ergebnisse
        churn_analysis: Churn-Analyse
    """

    candidate_id: str
    priority: Priority
    priority_score: float = 0.0
    confidence: float = 0.0
    static_score: float = 0.0
    llm_score: float = 0.0
    reasoning: str = ""
    semgrep_results: List[SemgrepResult] = field(default_factory=list)
    churn_analysis: Optional[ChurnAnalysis] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "candidate_id": self.candidate_id,
            "priority": self.priority.value,
            "priority_score": self.priority_score,
            "confidence": self.confidence,
            "static_score": self.static_score,
            "llm_score": self.llm_score,
            "reasoning": self.reasoning,
            "semgrep_results": [s.to_dict() for s in self.semgrep_results],
            "churn_analysis": self.churn_analysis.to_dict() if self.churn_analysis else None,
            "metadata": self.metadata,
        }


@dataclass
class Candidate:
    """
    Bug-Kandidat für Priorisierung.

    Attributes:
        candidate_id: Kandidaten-ID
        file_path: Dateipfad
        bug_type: Bug-Typ
        description: Beschreibung
        line_start: Startzeile
        line_end: Endzeile
        severity: Schweregrad
    """

    candidate_id: str
    file_path: str
    bug_type: str
    description: str
    line_start: int
    line_end: int
    severity: str = "medium"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "candidate_id": self.candidate_id,
            "file_path": self.file_path,
            "bug_type": self.bug_type,
            "description": self.description,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "severity": self.severity,
            "metadata": self.metadata,
        }


class LLiftPrioritizer:
    """
    LLift Hybrid Prioritizer.

    Kombiniert statische Analyse mit LLM-Inferenz für präzise Priorisierung:
    - Semgrep-Ergebnisse gewichten
    - Git-Churn und Komplexität einbeziehen
    - LLM-basierte Bewertung (optional)
    - Stack-spezifische Optimierung

    Usage:
        prioritizer = LLiftPrioritizer(model_path="path/to/model.gguf")
        result = prioritizer.prioritize(candidates, semgrep_results)
    """

    # Severity-Weighting
    SEVERITY_WEIGHTS = {
        "critical": 1.0,
        "high": 0.8,
        "medium": 0.5,
        "low": 0.2,
    }

    # Semgrep-Regel-Kategorien
    SECURITY_RULES = {"injection", "xss", "csrf", "auth", "crypto"}
    CORRECTNESS_RULES = {"null-pointer", "race-condition", "memory-leak"}

    def __init__(
        self,
        model_path: Optional[str] = None,
        use_llm: bool = True,
        stack: str = "A",
    ) -> None:
        """
        Initialisiert LLift Prioritizer.

        Args:
            model_path: Pfad zum LLM-Modell (Phi-4-mini, DeepSeek-V3.2).
            use_llm: LLM-Priorisierung aktivieren.
            stack: Hardware-Stack (A oder B).
        """
        self.model_path = model_path
        self.use_llm = use_llm
        self.stack = stack

        self._engine = None
        if use_llm and model_path:
            self._init_engine()

        logger.debug(
            f"LLiftPrioritizer initialisiert: use_llm={use_llm}, "
            f"stack={stack}, model={model_path}"
        )

    def _init_engine(self) -> None:
        """Initialisiert Inference-Engine."""
        try:
            from ..inference.engine import InferenceEngine, InferenceConfig

            self._engine = InferenceEngine(
                model_path=self.model_path,
                config=InferenceConfig(
                    temperature=0.1,  # Niedrig für deterministische Priorisierung
                    max_tokens=512,
                ),
            )
            logger.info("Inference-Engine für LLift initialisiert")
        except Exception as e:
            logger.warning(f"Konnte Inference-Engine nicht initialisieren: {e}")
            self.use_llm = False

    def prioritize(
        self,
        candidates: List[Candidate],
        semgrep_results: Optional[List[SemgrepResult]] = None,
        churn_analysis: Optional[List[ChurnAnalysis]] = None,
    ) -> List[PrioritizationResult]:
        """
        Priorisiert Kandidaten.

        Args:
            candidates: Liste von Kandidaten.
            semgrep_results: Semgrep-Ergebnisse.
            churn_analysis: Git-Churn-Analyse.

        Returns:
            Liste von PrioritizationResult, sortiert nach Priorität.
        """
        logger.info(f"Priorisiere {len(candidates)} Kandidaten")

        results = []

        for candidate in candidates:
            # Statische Analyse
            static_score = self._calculate_static_score(
                candidate,
                semgrep_results,
                churn_analysis,
            )

            # LLM-Analyse (optional)
            llm_score = 0.0
            reasoning = ""
            if self.use_llm and self._engine:
                llm_score, reasoning = self._analyze_with_llm(candidate, static_score)

            # Gesamtscore berechnen
            if self.use_llm:
                priority_score = (static_score * 0.6) + (llm_score * 0.4)
            else:
                priority_score = static_score

            # Priorität bestimmen
            priority = self._score_to_priority(priority_score)

            # Konfidenz berechnen
            confidence = self._calculate_confidence(static_score, llm_score)

            result = PrioritizationResult(
                candidate_id=candidate.candidate_id,
                priority=priority,
                priority_score=priority_score,
                confidence=confidence,
                static_score=static_score,
                llm_score=llm_score,
                reasoning=reasoning or f"Static score: {static_score:.2f}",
                semgrep_results=self._get_semgrep_for_candidate(
                    candidate, semgrep_results
                ),
                churn_analysis=self._get_churn_for_candidate(
                    candidate, churn_analysis
                ),
            )

            results.append(result)

        # Nach Priorität sortieren (höchste zuerst)
        results.sort(key=lambda r: r.priority_score, reverse=True)

        logger.info(
            f"Priorisierung abgeschlossen: "
            f"{len([r for r in results if r.priority == Priority.CRITICAL])} critical, "
            f"{len([r for r in results if r.priority == Priority.HIGH])} high"
        )

        return results

    def _calculate_static_score(
        self,
        candidate: Candidate,
        semgrep_results: Optional[List[SemgrepResult]],
        churn_analysis: Optional[List[ChurnAnalysis]],
    ) -> float:
        """
        Berechnet statischen Score.

        Args:
            candidate: Kandidat.
            semgrep_results: Semgrep-Ergebnisse.
            churn_analysis: Churn-Analyse.

        Returns:
            Score (0-100).
        """
        score = 0.0

        # 1. Severity-basierter Score
        severity_weight = self.SEVERITY_WEIGHTS.get(candidate.severity, 0.5)
        score += severity_weight * 40  # Max 40 Punkte

        # 2. Semgrep-Ergebnisse
        if semgrep_results:
            candidate_semgrep = self._get_semgrep_for_candidate(
                candidate, semgrep_results
            )
            if candidate_semgrep:
                # Security-Regeln höher gewichten
                for result in candidate_semgrep:
                    if any(
                        rule in result.rule_id.lower() for rule in self.SECURITY_RULES
                    ):
                        score += 15  # Security: +15 Punkte
                    elif any(
                        rule in result.rule_id.lower() for rule in self.CORRECTNESS_RULES
                    ):
                        score += 10  # Correctness: +10 Punkte
                    else:
                        score += 5  # Andere: +5 Punkte

        # 3. Git-Churn und Hotspots
        if churn_analysis:
            candidate_churn = self._get_churn_for_candidate(
                candidate, churn_analysis
            )
            if candidate_churn:
                # Hotspot-Score einbeziehen
                score += candidate_churn.hotspot_score * 20  # Max 20 Punkte

        # 4. Bug-Typ-Score
        bug_type_lower = candidate.bug_type.lower()
        if any(kw in bug_type_lower for kw in ["injection", "xss", "auth"]):
            score += 15  # Security-Bugs: +15 Punkte
        elif any(kw in bug_type_lower for kw in ["null", "race", "memory"]):
            score += 10  # Correctness-Bugs: +10 Punkte

        return min(score, 100.0)  # Max 100 Punkte

    def _analyze_with_llm(
        self,
        candidate: Candidate,
        static_score: float,
    ) -> Tuple[float, str]:
        """
        Analysiert Kandidat mit LLM.

        Args:
            candidate: Kandidat.
            static_score: Statischer Score.

        Returns:
            Tuple aus (LLM-Score, Reasoning).
        """
        prompt = f"""Du bist ein Code-Analyse-Experte. Bewerte die Priorität dieses Bugs:

BUG INFORMATION:
- ID: {candidate.candidate_id}
- Typ: {candidate.bug_type}
- Schweregrad: {candidate.severity}
- Datei: {candidate.file_path}
- Zeilen: {candidate.line_start}-{candidate.line_end}
- Beschreibung: {candidate.description}

STATISCHE ANALYSE:
- Static Score: {static_score:.2f}/100

AUFGABE:
1. Bewerte die Dringlichkeit dieses Bugs (0.0-1.0)
2. Gib eine kurze Begründung

ANTWORT (JSON):
{{
    "urgency": 0.0-1.0,
    "reasoning": "..."
}}
"""

        try:
            response = self._engine.generate(
                prompt=prompt,
                system_prompt="Du bist ein Code-Analyse-Experte. Antworte im JSON-Format.",
            )

            # JSON parsen
            import json

            content = response.content.strip()
            start = content.find("{")
            end = content.rfind("}") + 1

            if start >= 0 and end > start:
                json_str = content[start:end]
                data = json.loads(json_str)

                llm_score = float(data.get("urgency", 0.5)) * 100
                reasoning = data.get("reasoning", "")

                return llm_score, reasoning

            return 50.0, "LLM parsing failed"

        except Exception as e:
            logger.error(f"LLM-Analyse-Fehler: {e}")
            return 50.0, f"LLM error: {e}"

    def _score_to_priority(self, score: float) -> Priority:
        """
        Konvertiert Score zu Priorität.

        Args:
            score: Score (0-100).

        Returns:
            Priority.
        """
        if score >= 80:
            return Priority.CRITICAL
        elif score >= 60:
            return Priority.HIGH
        elif score >= 40:
            return Priority.MEDIUM
        else:
            return Priority.LOW

    def _calculate_confidence(
        self,
        static_score: float,
        llm_score: float,
    ) -> float:
        """
        Berechnet Konfidenz.

        Args:
            static_score: Statischer Score.
            llm_score: LLM Score.

        Returns:
            Konfidenz (0-1).
        """
        if not self.use_llm:
            return 0.7  # Default bei rein statischer Analyse

        # Konfidenz basierend auf Übereinstimmung
        diff = abs(static_score - llm_score)
        if diff < 10:
            return 0.95  # Hohe Übereinstimmung
        elif diff < 20:
            return 0.85  # Mittlere Übereinstimmung
        elif diff < 30:
            return 0.7  # Geringe Übereinstimmung
        else:
            return 0.5  # Sehr unterschiedlich

    def _get_semgrep_for_candidate(
        self,
        candidate: Candidate,
        semgrep_results: Optional[List[SemgrepResult]],
    ) -> List[SemgrepResult]:
        """Holt Semgrep-Ergebnisse für Kandidat."""
        if not semgrep_results:
            return []

        return [
            r
            for r in semgrep_results
            if r.file_path == candidate.file_path
            and abs(r.line_number - candidate.line_start) <= 5
        ]

    def _get_churn_for_candidate(
        self,
        candidate: Candidate,
        churn_analysis: Optional[List[ChurnAnalysis]],
    ) -> Optional[ChurnAnalysis]:
        """Holt Churn-Analyse für Kandidat."""
        if not churn_analysis:
            return None

        for churn in churn_analysis:
            if churn.file_path == candidate.file_path:
                return churn

        return None

    def prioritize_top_n(
        self,
        candidates: List[Candidate],
        semgrep_results: Optional[List[SemgrepResult]] = None,
        churn_analysis: Optional[List[ChurnAnalysis]] = None,
        n: int = 20,
    ) -> List[PrioritizationResult]:
        """
        Priorisiert Top-N-Kandidaten.

        Args:
            candidates: Liste von Kandidaten.
            semgrep_results: Semgrep-Ergebnisse.
            churn_analysis: Churn-Analyse.
            n: Anzahl zurückzugeben.

        Returns:
            Top-N PrioritizationResult.
        """
        results = self.prioritize(candidates, semgrep_results, churn_analysis)
        return results[:n]

    def get_priority_distribution(
        self,
        results: List[PrioritizationResult],
    ) -> Dict[str, int]:
        """
        Berechnet Prioritäts-Verteilung.

        Args:
            results: Liste von Ergebnissen.

        Returns:
            Verteilung als Dict.
        """
        distribution = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }

        for result in results:
            distribution[result.priority.value] += 1

        return distribution

    def __call__(self, state: Any) -> Dict[str, Any]:
        """
        Callable für LangGraph.

        Args:
            state: AgentState.

        Returns:
            State-Updates.
        """
        candidates = getattr(state, "candidates", [])
        semgrep_results = getattr(state, "semgrep_results", None)
        churn_analysis = getattr(state, "churn_analysis", None)

        # Konvertiere zu Candidate-Objekten
        candidate_objs = []
        for c in candidates:
            if isinstance(c, dict):
                candidate_objs.append(
                    Candidate(
                        candidate_id=c.get("id", ""),
                        file_path=c.get("file_path", ""),
                        bug_type=c.get("bug_type", ""),
                        description=c.get("description", ""),
                        line_start=c.get("line_start", 0),
                        line_end=c.get("line_end", 0),
                        severity=c.get("severity", "medium"),
                    )
                )
            elif isinstance(c, Candidate):
                candidate_objs.append(c)

        results = self.prioritize(candidate_objs, semgrep_results, churn_analysis)

        return {
            "prioritized_results": [r.to_dict() for r in results],
            "top_candidates": [r.to_dict() for r in results[:20]],
            "priority_distribution": self.get_priority_distribution(results),
            "metadata": {
                "total_candidates": len(results),
                "critical_count": sum(
                    1 for r in results if r.priority == Priority.CRITICAL
                ),
                "high_count": sum(
                    1 for r in results if r.priority == Priority.HIGH
                ),
            },
        }
