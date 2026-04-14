"""
Observer Agent for GlitchHunter.

Evaluates evidence chains and computes confidence scores for bug candidates.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.logging_config import get_logger

from agent.analyzer_agent import Evidence, EvidenceCollection, EvidenceType
from agent.hypothesis_agent import Hypothesis

logger = get_logger(__name__)


@dataclass
class EvidenceItem:
    """
    Represents a single evidence item in a chain.

    Attributes:
        evidence_type: Type of evidence
        description: Description of the evidence
        weight: Evidence weight
        quality: Evidence quality
        source: Source of the evidence (file, function, etc.)
        timestamp: Optional timestamp for recency calculation
    """

    evidence_type: EvidenceType
    description: str
    weight: float = 1.0
    quality: float = 1.0
    source: str = ""
    timestamp: Optional[float] = None


@dataclass
class EvidenceChain:
    """
    Represents a chain of evidence for a candidate.

    Attributes:
        candidate_id: ID of the bug candidate
        evidence_items: List of evidence items
        chain_strength: Overall chain strength
        weakest_link: Optional weakest evidence item
    """

    candidate_id: str
    evidence_items: List[EvidenceItem] = field(default_factory=list)
    chain_strength: float = 0.0
    weakest_link: Optional[EvidenceItem] = None

    def add_evidence(self, item: EvidenceItem) -> None:
        """
        Add an evidence item to the chain.

        Args:
            item: Evidence item to add
        """
        self.evidence_items.append(item)
        self._recalculate_strength()

    def _recalculate_strength(self) -> None:
        """Recalculate the chain strength."""
        if not self.evidence_items:
            self.chain_strength = 0.0
            self.weakest_link = None
            return

        # Chain strength is limited by weakest link
        strengths = [
            item.weight * item.quality for item in self.evidence_items
        ]
        self.chain_strength = min(strengths) if strengths else 0.0

        # Find weakest link
        min_strength = min(strengths)
        for item in self.evidence_items:
            if item.weight * item.quality == min_strength:
                self.weakest_link = item
                break


@dataclass
class AggregatedEvidence:
    """
    Aggregated evidence from multiple sources.

    Attributes:
        total_positive: Total positive evidence score
        total_negative: Total negative evidence score
        evidence_count: Total number of evidence items
        strongest_evidence: Strongest piece of evidence
        evidence_types: Breakdown by evidence type
    """

    total_positive: float = 0.0
    total_negative: float = 0.0
    evidence_count: int = 0
    strongest_evidence: Optional[Evidence] = None
    evidence_types: Dict[str, float] = field(default_factory=dict)


@dataclass
class RankedCandidate:
    """
    Represents a ranked bug candidate.

    Attributes:
        candidate_id: ID of the bug candidate
        original_confidence: Original confidence score
        aggregated_confidence: Aggregated confidence after evidence evaluation
        evidence_chain: Evidence chain for the candidate
        rank: Final rank (1 = highest priority)
    """

    candidate_id: str
    original_confidence: float = 0.0
    aggregated_confidence: float = 0.0
    evidence_chain: Optional[EvidenceChain] = None
    rank: int = 0


class ObserverAgent:
    """
    Observer Agent for evidence evaluation.

    Aggregates evidence chains, computes confidence scores, and ranks
    candidates based on evidence quality.
    """

    # Evidence type weights
    EVIDENCE_WEIGHTS = {
        EvidenceType.DIRECT_DATA_FLOW: 1.0,
        EvidenceType.CALL_CHAIN: 0.7,
        EvidenceType.SEMANTIC_SIMILARITY: 0.5,
        EvidenceType.PATTERN_MATCH: 0.8,
        EvidenceType.CONTROL_FLOW: 0.6,
        EvidenceType.TAINT_PATH: 0.9,
    }

    # Quality multipliers
    QUALITY_DIRECT = 1.0
    QUALITY_INDIRECT = 0.7
    QUALITY_SEMANTIC = 0.5

    def __init__(self, git_churn: Optional[Dict[str, float]] = None) -> None:
        """
        Initialize the Observer Agent.

        Args:
            git_churn: Optional git churn data for recency factors
        """
        self._git_churn = git_churn or {}
        self._evidence_chains: Dict[str, EvidenceChain] = {}
        self._ranked_candidates: List[RankedCandidate] = []

    def aggregate_evidence(
        self,
        evidence_collections: List[EvidenceCollection],
    ) -> AggregatedEvidence:
        """
        Aggregate evidence from multiple collections.

        Args:
            evidence_collections: List of evidence collections

        Returns:
            Aggregated evidence
        """
        logger.info(f"Aggregating {len(evidence_collections)} evidence collections")

        aggregated = AggregatedEvidence()
        all_evidence: List[Evidence] = []

        for collection in evidence_collections:
            all_evidence.extend(collection.positive_evidence)
            all_evidence.extend(collection.negative_evidence)

        # Calculate totals
        for evidence in all_evidence:
            score = evidence.weight * evidence.quality

            if evidence in [e for c in evidence_collections for e in c.positive_evidence]:
                aggregated.total_positive += score
            else:
                aggregated.total_negative += score

            # Track by type
            type_key = evidence.evidence_type.value
            if type_key not in aggregated.evidence_types:
                aggregated.evidence_types[type_key] = 0.0
            aggregated.evidence_types[type_key] += score

            # Track strongest evidence
            if (
                aggregated.strongest_evidence is None
                or score > (
                    aggregated.strongest_evidence.weight
                    * aggregated.strongest_evidence.quality
                )
            ):
                aggregated.strongest_evidence = evidence

        aggregated.evidence_count = len(all_evidence)

        logger.info(
            f"Aggregated evidence: {aggregated.evidence_count} items, "
            f"positive={aggregated.total_positive:.2f}, "
            f"negative={aggregated.total_negative:.2f}"
        )

        return aggregated

    def compute_confidence_score(
        self,
        aggregated_evidence: AggregatedEvidence,
        recency_factor: float = 1.0,
    ) -> float:
        """
        Compute confidence score from aggregated evidence.

        Formula:
            confidence = Σ(evidence_weight * quality * recency_factor)

        Args:
            aggregated_evidence: Aggregated evidence
            recency_factor: Recency factor based on git churn (0.0-1.0)

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if aggregated_evidence.evidence_count == 0:
            return 0.0

        # Base confidence from positive/negative ratio
        total = (
            aggregated_evidence.total_positive
            + aggregated_evidence.total_negative
        )

        if total == 0:
            return 0.0

        base_confidence = (
            aggregated_evidence.total_positive / total
        )

        # Apply recency factor
        confidence = base_confidence * recency_factor

        # Bonus for multiple evidence types
        type_bonus = min(0.2, len(aggregated_evidence.evidence_types) * 0.05)
        confidence += type_bonus

        # Bonus for strong evidence
        if aggregated_evidence.strongest_evidence:
            strongest_score = (
                aggregated_evidence.strongest_evidence.weight
                * aggregated_evidence.strongest_evidence.quality
            )
            if strongest_score >= 0.8:
                confidence += 0.1

        return min(1.0, confidence)

    def rank_candidates(
        self,
        candidates_with_evidence: List[Tuple[str, float, EvidenceCollection]],
    ) -> List[RankedCandidate]:
        """
        Rank candidates based on evidence.

        Args:
            candidates_with_evidence: List of (candidate_id, original_confidence, evidence_collection)

        Returns:
            List of ranked candidates
        """
        logger.info(f"Ranking {len(candidates_with_evidence)} candidates")

        ranked: List[RankedCandidate] = []

        for candidate_id, original_confidence, evidence_collection in candidates_with_evidence:
            # Create evidence chain
            chain = self._create_evidence_chain(
                candidate_id, evidence_collection
            )

            # Compute aggregated confidence
            aggregated = self.aggregate_evidence([evidence_collection])
            recency = self._get_recency_factor(candidate_id)
            aggregated_confidence = self.compute_confidence_score(
                aggregated, recency
            )

            ranked.append(
                RankedCandidate(
                    candidate_id=candidate_id,
                    original_confidence=original_confidence,
                    aggregated_confidence=aggregated_confidence,
                    evidence_chain=chain,
                )
            )

        # Sort by aggregated confidence (descending)
        ranked.sort(key=lambda c: c.aggregated_confidence, reverse=True)

        # Assign ranks
        for i, candidate in enumerate(ranked):
            candidate.rank = i + 1

        self._ranked_candidates = ranked

        logger.info(
            f"Ranked candidates: top confidence={ranked[0].aggregated_confidence if ranked else 0:.2f}"
        )

        return ranked

    def get_evidence_chain(self, candidate_id: str) -> Optional[EvidenceChain]:
        """
        Get the evidence chain for a candidate.

        Args:
            candidate_id: Candidate ID

        Returns:
            Evidence chain or None
        """
        return self._evidence_chains.get(candidate_id)

    def _create_evidence_chain(
        self,
        candidate_id: str,
        evidence_collection: EvidenceCollection,
    ) -> EvidenceChain:
        """
        Create an evidence chain from a collection.

        Args:
            candidate_id: Candidate ID
            evidence_collection: Evidence collection

        Returns:
            Evidence chain
        """
        chain = EvidenceChain(candidate_id=candidate_id)

        # Add positive evidence
        for evidence in evidence_collection.positive_evidence:
            chain.add_evidence(
                EvidenceItem(
                    evidence_type=evidence.evidence_type,
                    description=evidence.description,
                    weight=evidence.weight,
                    quality=evidence.quality,
                )
            )

        # Add negative evidence (with inverted weight)
        for evidence in evidence_collection.negative_evidence:
            chain.add_evidence(
                EvidenceItem(
                    evidence_type=evidence.evidence_type,
                    description=f"NEGATIVE: {evidence.description}",
                    weight=evidence.weight * 0.5,  # Reduce impact
                    quality=evidence.quality,
                )
            )

        # Store chain
        self._evidence_chains[candidate_id] = chain

        return chain

    def _get_recency_factor(self, candidate_id: str) -> float:
        """
        Get recency factor based on git churn.

        Args:
            candidate_id: Candidate ID (may contain file path)

        Returns:
            Recency factor between 0.0 and 1.0
        """
        # Extract file path from candidate ID if possible
        file_path = candidate_id.split(":")[0] if ":" in candidate_id else candidate_id

        # Check git churn
        if file_path in self._git_churn:
            churn = self._git_churn[file_path]
            # Higher churn = more recent = higher recency factor
            return min(1.0, 0.5 + churn * 0.1)

        return 1.0  # Default recency factor

    def get_ranked_candidates(self) -> List[RankedCandidate]:
        """
        Get all ranked candidates.

        Returns:
            List of ranked candidates
        """
        return self._ranked_candidates.copy()

    def get_top_candidates(self, top_n: int = 10) -> List[RankedCandidate]:
        """
        Get top N ranked candidates.

        Args:
            top_n: Number of top candidates to return

        Returns:
            List of top candidates
        """
        return self._ranked_candidates[:top_n]

    def clear_rankings(self) -> None:
        """Clear all rankings and evidence chains."""
        self._ranked_candidates = []
        self._evidence_chains = {}
        logger.debug("Observer agent rankings cleared")

    def set_git_churn(self, git_churn: Dict[str, float]) -> None:
        """
        Set git churn data for recency calculation.

        Args:
            git_churn: Dictionary mapping file paths to churn scores
        """
        self._git_churn = git_churn

    def compute_confidence_with_weights(
        self,
        positive_evidence: List[Evidence],
        negative_evidence: List[Evidence],
        recency_factor: float = 1.0,
    ) -> float:
        """
        Compute confidence score with explicit weights.

        Args:
            positive_evidence: List of positive evidence
            negative_evidence: List of negative evidence
            recency_factor: Recency factor

        Returns:
            Confidence score
        """
        # Calculate weighted scores
        positive_score = 0.0
        negative_score = 0.0

        for evidence in positive_evidence:
            type_weight = self.EVIDENCE_WEIGHTS.get(
                evidence.evidence_type, 0.5
            )
            positive_score += type_weight * evidence.weight * evidence.quality

        for evidence in negative_evidence:
            type_weight = self.EVIDENCE_WEIGHTS.get(
                evidence.evidence_type, 0.5
            )
            negative_score += type_weight * evidence.weight * evidence.quality

        # Calculate confidence
        total = positive_score + negative_score
        if total == 0:
            return 0.0

        base_confidence = positive_score / total

        # Apply recency
        confidence = base_confidence * recency_factor

        return min(1.0, confidence)

    def analyze_evidence_quality(
        self,
        evidence_collection: EvidenceCollection,
    ) -> Dict[str, Any]:
        """
        Analyze the quality of evidence in a collection.

        Args:
            evidence_collection: Evidence collection to analyze

        Returns:
            Dictionary with quality analysis
        """
        analysis = {
            "total_items": len(evidence_collection.positive_evidence)
            + len(evidence_collection.negative_evidence),
            "positive_count": len(evidence_collection.positive_evidence),
            "negative_count": len(evidence_collection.negative_evidence),
            "evidence_types": {},
            "average_quality": 0.0,
            "average_weight": 0.0,
            "strongest_type": "",
        }

        all_evidence = (
            evidence_collection.positive_evidence
            + evidence_collection.negative_evidence
        )

        if not all_evidence:
            return analysis

        # Analyze by type
        type_scores: Dict[str, List[float]] = {}
        total_quality = 0.0
        total_weight = 0.0

        for evidence in all_evidence:
            type_key = evidence.evidence_type.value
            score = evidence.weight * evidence.quality

            if type_key not in type_scores:
                type_scores[type_key] = []
            type_scores[type_key].append(score)

            total_quality += evidence.quality
            total_weight += evidence.weight

        analysis["average_quality"] = total_quality / len(all_evidence)
        analysis["average_weight"] = total_weight / len(all_evidence)

        # Find strongest type
        type_averages = {
            t: sum(scores) / len(scores) for t, scores in type_scores.items()
        }
        if type_averages:
            analysis["strongest_type"] = max(
                type_averages, key=type_averages.get
            )

        analysis["evidence_types"] = type_averages

        return analysis
