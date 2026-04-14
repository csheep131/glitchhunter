"""
LLift Hybrid Prioritizer for GlitchHunter.

Combines static analysis and LLM-based ranking for bug candidate prioritization.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..core.logging_config import get_logger

from .analyzer_agent import EvidenceCollection
from .hypothesis_agent import Hypothesis, Severity
from .observer_agent import RankedCandidate

logger = get_logger(__name__)


@dataclass
class SemgrepResult:
    """
    Represents a Semgrep finding.

    Attributes:
        rule_id: Semgrep rule identifier
        file_path: Source file path
        line: Line number
        message: Finding message
        severity: Finding severity
        metadata: Additional metadata
    """

    rule_id: str
    file_path: str
    line: int
    message: str
    severity: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChurnAnalysis:
    """
    Represents git churn analysis.

    Attributes:
        file_path: Source file path
        churn_score: Churn score (0.0-1.0)
        commit_count: Number of commits
        recent_changes: Recent change indicators
    """

    file_path: str
    churn_score: float = 0.0
    commit_count: int = 0
    recent_changes: List[str] = field(default_factory=list)


@dataclass
class PrioritizationResult:
    """
    Result of hybrid prioritization.

    Attributes:
        static_scores: Scores from static analysis
        llm_scores: Scores from LLM ranking
        combined_scores: Combined final scores
        final_ranking: Final ranked candidates
        reduction_achieved: Percentage reduction in candidates
    """

    static_scores: Dict[str, float] = field(default_factory=dict)
    llm_scores: Dict[str, float] = field(default_factory=dict)
    combined_scores: Dict[str, float] = field(default_factory=dict)
    final_ranking: List[RankedCandidate] = field(default_factory=list)
    reduction_achieved: float = 0.0


class LLiftPrioritizer:
    """
    LLift Hybrid Prioritizer.

    Combines static analysis scores with LLM-based ranking to prioritize
    bug candidates. Targets 40-50% LLM call reduction.
    """

    # LLM Prompt template for ranking
    LLM_RANKING_PROMPT = """
Rank these {count} bug candidates by:
1. Severity (Low, Medium, High, Critical)
2. Fix Complexity (Easy, Medium, Hard)
3. Business Impact (Low, Medium, High)
4. Confidence in root cause

Provide reasoning with code evidence for each ranking.

Candidates:
{candidate_descriptions}

Semgrep findings: {semgrep_count}
Git churn hotspots: {hotspot_count}

Return JSON with ranked candidates and scores in the following format:
{{
    "rankings": [
        {{
            "candidate_id": "...",
            "rank": 1,
            "severity": "Critical",
            "fix_complexity": "Easy",
            "business_impact": "High",
            "confidence": 0.95,
            "reasoning": "..."
        }}
    ]
}}
"""

    # Static analysis weights
    SEVERITY_WEIGHTS = {
        Severity.CRITICAL: 1.0,
        Severity.HIGH: 0.8,
        Severity.MEDIUM: 0.5,
        Severity.LOW: 0.2,
    }

    SEMGREP_SEVERITY_WEIGHTS = {
        "error": 1.0,
        "warning": 0.6,
        "info": 0.3,
    }

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        static_weight: float = 0.5,
        llm_weight: float = 0.5,
    ) -> None:
        """
        Initialize the LLift Prioritizer.

        Args:
            llm_client: Optional LLM client for ranking
            static_weight: Weight for static analysis scores (0.0-1.0)
            llm_weight: Weight for LLM scores (0.0-1.0)
        """
        self._llm_client = llm_client
        self._static_weight = static_weight
        self._llm_weight = llm_weight
        self._last_result: Optional[PrioritizationResult] = None

    def prioritize_candidates(
        self,
        candidates: List[RankedCandidate],
        semgrep_results: Optional[List[SemgrepResult]] = None,
        churn_analysis: Optional[List[ChurnAnalysis]] = None,
        top_n: int = 20,
    ) -> List[RankedCandidate]:
        """
        Prioritize candidates using hybrid static + LLM approach.

        Args:
            candidates: List of ranked candidates
            semgrep_results: Optional Semgrep findings
            churn_analysis: Optional git churn analysis
            top_n: Number of top candidates to return

        Returns:
            List of prioritized candidates
        """
        logger.info(f"Prioritizing {len(candidates)} candidates")

        # Step 1: Static ranking
        static_scores = self.static_rank(candidates, semgrep_results, churn_analysis)

        # Step 2: LLM ranking (if available)
        llm_scores = {}
        if self._llm_client:
            llm_scores = self.llm_rank(candidates, semgrep_results, churn_analysis)

        # Step 3: Combine rankings
        combined_scores = self._combine_ranks(static_scores, llm_scores)

        # Step 4: Create final ranking
        final_ranking = self._create_final_ranking(
            candidates, combined_scores, top_n
        )

        # Step 5: Calculate reduction
        reduction = self._calculate_reduction(candidates, final_ranking)

        result = PrioritizationResult(
            static_scores=static_scores,
            llm_scores=llm_scores,
            combined_scores=combined_scores,
            final_ranking=final_ranking,
            reduction_achieved=reduction,
        )

        self._last_result = result

        logger.info(
            f"Prioritization complete: {len(final_ranking)} candidates, "
            f"reduction={reduction:.1%}"
        )

        return final_ranking

    def llm_rank(
        self,
        candidates: List[RankedCandidate],
        semgrep_results: Optional[List[SemgrepResult]] = None,
        churn_analysis: Optional[List[ChurnAnalysis]] = None,
    ) -> Dict[str, float]:
        """
        Rank candidates using LLM.

        Args:
            candidates: Candidates to rank
            semgrep_results: Optional Semgrep findings
            churn_analysis: Optional git churn analysis

        Returns:
            Dictionary mapping candidate IDs to LLM scores
        """
        logger.info(f"LLM ranking {len(candidates)} candidates")

        if not self._llm_client:
            logger.warning("No LLM client available for ranking")
            # Return original confidence scores as fallback
            return {c.candidate_id: c.aggregated_confidence for c in candidates}

        # Prepare candidate descriptions
        candidate_descriptions = self._format_candidates_for_llm(candidates)

        # Count semgrep findings
        semgrep_count = len(semgrep_results) if semgrep_results else 0

        # Count churn hotspots
        hotspot_count = 0
        if churn_analysis:
            hotspot_count = sum(
                1 for c in churn_analysis if c.churn_score > 0.5
            )

        # Generate prompt
        prompt = self.LLM_RANKING_PROMPT.format(
            count=len(candidates),
            candidate_descriptions=candidate_descriptions,
            semgrep_count=semgrep_count,
            hotspot_count=hotspot_count,
        )

        try:
            # Call LLM
            response = self._call_llm(prompt)

            # Parse response
            llm_scores = self._parse_llm_response(response, candidates)

            logger.info(f"LLM ranking complete: {len(llm_scores)} candidates scored")

            return llm_scores
        except Exception as e:
            logger.error(f"LLM ranking failed: {e}")
            # Return uniform scores as fallback
            return {c.candidate_id: c.aggregated_confidence for c in candidates}

    def static_rank(
        self,
        candidates: List[RankedCandidate],
        semgrep_results: Optional[List[SemgrepResult]] = None,
        churn_analysis: Optional[List[ChurnAnalysis]] = None,
    ) -> Dict[str, float]:
        """
        Rank candidates using static analysis.

        Args:
            candidates: Candidates to rank
            semgrep_results: Optional Semgrep findings
            churn_analysis: Optional git churn analysis

        Returns:
            Dictionary mapping candidate IDs to static scores
        """
        logger.info(f"Static ranking {len(candidates)} candidates")

        scores: Dict[str, float] = {}

        # Create lookup maps
        semgrep_by_file: Dict[str, List[SemgrepResult]] = {}
        if semgrep_results:
            for result in semgrep_results:
                if result.file_path not in semgrep_by_file:
                    semgrep_by_file[result.file_path] = []
                semgrep_by_file[result.file_path].append(result)

        churn_by_file: Dict[str, ChurnAnalysis] = {}
        if churn_analysis:
            for analysis in churn_analysis:
                churn_by_file[analysis.file_path] = analysis

        # Score each candidate
        for candidate in candidates:
            score = self._calculate_static_score(
                candidate,
                semgrep_by_file,
                churn_by_file,
            )
            scores[candidate.candidate_id] = score

        logger.info(f"Static ranking complete: {len(scores)} candidates scored")

        return scores

    def _combine_ranks(
        self,
        static_scores: Dict[str, float],
        llm_scores: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Combine static and LLM rankings.

        Args:
            static_scores: Static analysis scores
            llm_scores: LLM scores

        Returns:
            Combined scores
        """
        combined: Dict[str, float] = {}

        # Get all candidate IDs
        all_ids = set(static_scores.keys()) | set(llm_scores.keys())

        for candidate_id in all_ids:
            static_score = static_scores.get(candidate_id, 0.5)
            llm_score = llm_scores.get(candidate_id, static_score)

            # Weighted combination
            combined_score = (
                self._static_weight * static_score
                + self._llm_weight * llm_score
            )

            combined[candidate_id] = combined_score

        return combined

    def get_top_candidates(self, top_n: int = 20) -> List[RankedCandidate]:
        """
        Get top N candidates from last prioritization.

        Args:
            top_n: Number of top candidates

        Returns:
            List of top candidates
        """
        if self._last_result:
            return self._last_result.final_ranking[:top_n]
        return []

    def _format_candidates_for_llm(
        self,
        candidates: List[RankedCandidate],
    ) -> str:
        """
        Format candidates for LLM prompt.

        Args:
            candidates: Candidates to format

        Returns:
            Formatted string
        """
        lines = []
        for i, candidate in enumerate(candidates[:30]):  # Limit to 30 for LLM context
            lines.append(
                f"{i + 1}. ID: {candidate.candidate_id}\n"
                f"   Original Confidence: {candidate.original_confidence:.2f}\n"
                f"   Aggregated Confidence: {candidate.aggregated_confidence:.2f}\n"
            )

            if candidate.evidence_chain:
                lines.append(
                    f"   Evidence Items: {len(candidate.evidence_chain.evidence_items)}\n"
                    f"   Chain Strength: {candidate.evidence_chain.chain_strength:.2f}\n"
                )

        return "\n".join(lines)

    def _call_llm(self, prompt: str) -> str:
        """
        Call LLM with prompt.

        Args:
            prompt: Prompt string

        Returns:
            LLM response
        """
        if hasattr(self._llm_client, "generate"):
            return self._llm_client.generate(prompt)
        elif hasattr(self._llm_client, "complete"):
            return self._llm_client.complete(prompt)
        else:
            # Default call pattern
            return str(self._llm_client(prompt))

    def _parse_llm_response(
        self,
        response: str,
        candidates: List[RankedCandidate],
    ) -> Dict[str, float]:
        """
        Parse LLM response into scores.

        Args:
            response: LLM response string
            candidates: Original candidates

        Returns:
            Dictionary of scores
        """
        scores: Dict[str, float] = {}

        try:
            # Try to parse JSON
            # Find JSON in response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)

                if "rankings" in data:
                    for ranking in data["rankings"]:
                        candidate_id = ranking.get("candidate_id", "")
                        confidence = ranking.get("confidence", 0.5)
                        scores[candidate_id] = confidence
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM JSON: {e}")
            # Fallback: use original confidence scores
            scores = {c.candidate_id: c.aggregated_confidence for c in candidates}

        return scores

    def _calculate_static_score(
        self,
        candidate: RankedCandidate,
        semgrep_by_file: Dict[str, List[SemgrepResult]],
        churn_by_file: Dict[str, ChurnAnalysis],
    ) -> float:
        """
        Calculate static analysis score for a candidate.

        Args:
            candidate: Candidate to score
            semgrep_by_file: Semgrep results by file
            churn_by_file: Churn analysis by file

        Returns:
            Static score
        """
        score = 0.0

        # Base score from aggregated confidence
        score += candidate.aggregated_confidence * 0.4

        # Evidence chain strength
        if candidate.evidence_chain:
            score += candidate.evidence_chain.chain_strength * 0.3

        # Semgrep bonus
        file_path = candidate.candidate_id.split(":")[0]
        if file_path in semgrep_by_file:
            semgrep_results = semgrep_by_file[file_path]
            semgrep_bonus = sum(
                self.SEMGREP_SEVERITY_WEIGHTS.get(r.severity, 0.3)
                for r in semgrep_results
            )
            score += min(0.2, semgrep_bonus * 0.05)

        # Churn bonus
        if file_path in churn_by_file:
            churn = churn_by_file[file_path]
            score += churn.churn_score * 0.1

        return min(1.0, score)

    def _create_final_ranking(
        self,
        candidates: List[RankedCandidate],
        combined_scores: Dict[str, float],
        top_n: int,
    ) -> List[RankedCandidate]:
        """
        Create final ranking from combined scores.

        Args:
            candidates: Original candidates
            combined_scores: Combined scores
            top_n: Number of top candidates

        Returns:
            Final ranked list
        """
        # Sort by combined score
        sorted_candidates = sorted(
            candidates,
            key=lambda c: combined_scores.get(c.candidate_id, 0.0),
            reverse=True,
        )

        # Take top N
        final_ranking = sorted_candidates[:top_n]

        # Update ranks
        for i, candidate in enumerate(final_ranking):
            candidate.rank = i + 1

        return final_ranking

    def _calculate_reduction(
        self,
        original: List[RankedCandidate],
        final: List[RankedCandidate],
    ) -> float:
        """
        Calculate reduction percentage.

        Args:
            original: Original candidate list
            final: Final candidate list

        Returns:
            Reduction percentage (0.0-1.0)
        """
        if not original:
            return 0.0

        reduction = (len(original) - len(final)) / len(original)
        return reduction

    def get_last_result(self) -> Optional[PrioritizationResult]:
        """
        Get the last prioritization result.

        Returns:
            Last result or None
        """
        return self._last_result

    def clear_result(self) -> None:
        """Clear the last result."""
        self._last_result = None
        logger.debug("Prioritizer result cleared")

    def set_weights(self, static_weight: float, llm_weight: float) -> None:
        """
        Set weighting for static and LLM scores.

        Args:
            static_weight: Weight for static scores (0.0-1.0)
            llm_weight: Weight for LLM scores (0.0-1.0)
        """
        self._static_weight = static_weight
        self._llm_weight = llm_weight
        logger.info(
            f"Weights updated: static={static_weight}, llm={llm_weight}"
        )

    def create_candidate_description(
        self,
        candidate: RankedCandidate,
        hypotheses: Optional[List[Hypothesis]] = None,
    ) -> str:
        """
        Create a detailed description of a candidate for LLM.

        Args:
            candidate: Candidate to describe
            hypotheses: Optional associated hypotheses

        Returns:
            Description string
        """
        lines = [
            f"Candidate: {candidate.candidate_id}",
            f"Original Confidence: {candidate.original_confidence:.2f}",
            f"Aggregated Confidence: {candidate.aggregated_confidence:.2f}",
            f"Rank: {candidate.rank}",
        ]

        if candidate.evidence_chain:
            lines.append(
                f"Evidence: {len(candidate.evidence_chain.evidence_items)} items, "
                f"strength={candidate.evidence_chain.chain_strength:.2f}"
            )

            if candidate.evidence_chain.weakest_link:
                weakest = candidate.evidence_chain.weakest_link
                lines.append(
                    f"Weakest Link: {weakest.evidence_type.value} - {weakest.description}"
                )

        if hypotheses:
            lines.append(f"Hypotheses: {len(hypotheses)}")
            for h in hypotheses[:3]:
                lines.append(f"  - {h.title} (confidence: {h.confidence:.2f})")

        return "\n".join(lines)
