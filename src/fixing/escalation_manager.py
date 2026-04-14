"""
Escalation manager for GlitchHunter.

Manages 4-level escalation hierarchy for bug fixing:
1. Context Explosion
2. Bug Decomposition
3. Multi-Model Ensemble
4. Human-in-the-Loop
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EscalationContext:
    """
    Context for an escalation.

    Attributes:
        level: Escalation level (1-4)
        reason: Reason for escalation
        original_candidate: Original bug candidate
        additional_context: Additional context gathered
        decomposed_bugs: Decomposed sub-bugs (level 2)
        model_responses: Responses from multiple models (level 3)
        human_report: Human-readable report (level 4)
    """

    level: int
    reason: str
    original_candidate: Optional[Dict[str, Any]] = None
    additional_context: Dict[str, Any] = field(default_factory=dict)
    decomposed_bugs: List[Dict[str, Any]] = field(default_factory=list)
    model_responses: List[Dict[str, Any]] = field(default_factory=list)
    human_report: Optional["HumanReport"] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "level": self.level,
            "reason": self.reason,
            "original_candidate": self.original_candidate,
            "additional_context": self.additional_context,
            "decomposed_bugs": self.decomposed_bugs,
            "model_responses": self.model_responses,
            "human_report": self.human_report.to_dict() if self.human_report else None,
        }


@dataclass
class HumanReport:
    """
    Human-readable escalation report.

    Attributes:
        title: Report title
        summary: Executive summary
        bug_description: Detailed bug description
        attempted_fixes: List of attempted fixes
        evidence: Evidence collected
        recommendation: Recommendation for human
        created_at: Report creation timestamp
    """

    title: str
    summary: str
    bug_description: str
    attempted_fixes: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    recommendation: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "summary": self.summary,
            "bug_description": self.bug_description,
            "attempted_fixes": self.attempted_fixes,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "created_at": self.created_at.isoformat(),
        }


class EscalationManager:
    """
    Manages escalation levels for bug fixing.

    Escalation Levels:
    1. Context Explosion: Gather more context (160k tokens)
    2. Bug Decomposition: Split into 2-4 sub-bugs
    3. Multi-Model Ensemble: Parallel analysis with voting
    4. Human-in-the-Loop: Generate detailed report

    Example:
        >>> manager = EscalationManager()
        >>> if manager.should_escalate(loop_count=5, no_improvement=3):
        ...     context = manager.apply_escalation()
        ...     report = manager.generate_human_report(context)
    """

    def __init__(
        self,
        max_loops: int = 10,
        no_improvement_threshold: int = 3,
    ) -> None:
        """
        Initialize escalation manager.

        Args:
            max_loops: Maximum patch loops before forced escalation
            no_improvement_threshold: Loops without improvement before escalation
        """
        self.max_loops = max_loops
        self.no_improvement_threshold = no_improvement_threshold
        self.current_level = 0
        self.escalation_history: List[EscalationContext] = []

        logger.debug(
            f"EscalationManager initialized (max_loops={max_loops}, "
            f"threshold={no_improvement_threshold})"
        )

    def should_escalate(
        self,
        current_loop: int,
        no_improvement_count: int,
    ) -> bool:
        """
        Determine if escalation is needed.

        Args:
            current_loop: Current patch loop number
            no_improvement_count: Number of loops without improvement

        Returns:
            True if escalation is needed
        """
        # Force escalation at max loops
        if current_loop >= self.max_loops:
            logger.info(f"Forced escalation at loop {current_loop}")
            return True

        # Escalate after threshold of no improvement
        if no_improvement_count >= self.no_improvement_threshold:
            logger.info(
                f"Escalation triggered: {no_improvement_count} loops without improvement"
            )
            return True

        return False

    def get_escalation_level(self) -> int:
        """
        Get current escalation level.

        Returns:
            Current escalation level (0-4)
        """
        return self.current_level

    def apply_escalation(self) -> EscalationContext:
        """
        Apply next escalation level.

        Returns:
            EscalationContext with escalation details
        """
        self.current_level = min(4, self.current_level + 1)

        context = EscalationContext(
            level=self.current_level,
            reason=self._get_level_reason(self.current_level),
        )

        # Apply level-specific actions
        if self.current_level == 1:
            context = self._apply_context_explosion(context)
        elif self.current_level == 2:
            context = self._apply_bug_decomposition(context)
        elif self.current_level == 3:
            context = self._apply_multi_model_ensemble(context)
        elif self.current_level == 4:
            context = self._apply_human_in_loop(context)

        self.escalation_history.append(context)

        logger.info(f"Escalation level {self.current_level} applied")
        return context

    def generate_human_report(
        self,
        context: EscalationContext,
    ) -> HumanReport:
        """
        Generate human-readable escalation report.

        Args:
            context: Escalation context

        Returns:
            HumanReport for human review
        """
        report = HumanReport(
            title=f"Bug Fix Escalation - Level {context.level}",
            summary=self._generate_summary(context),
            bug_description=self._generate_bug_description(context),
            attempted_fixes=self._generate_attempted_fixes(context),
            evidence=self._generate_evidence(context),
            recommendation=self._generate_recommendation(context),
        )

        context.human_report = report

        logger.info(f"Human report generated for level {context.level}")
        return report

    def _get_level_reason(self, level: int) -> str:
        """Get reason string for escalation level."""
        reasons = {
            1: "Context Explosion: Expanding context to 160k tokens",
            2: "Bug Decomposition: Splitting into sub-bugs",
            3: "Multi-Model Ensemble: Parallel analysis with voting",
            4: "Human-in-the-Loop: Manual review required",
        }
        return reasons.get(level, "Unknown escalation level")

    def _apply_context_explosion(self, context: EscalationContext) -> EscalationContext:
        """Apply Level 1: Context Explosion."""
        context.additional_context = {
            "action": "context_explosion",
            "target_tokens": 160000,
            "include_repomix": True,
            "include_git_blame": True,
            "include_dependency_graph": True,
            "include_call_chains": True,
        }
        return context

    def _apply_bug_decomposition(self, context: EscalationContext) -> EscalationContext:
        """Apply Level 2: Bug Decomposition."""
        context.decomposed_bugs = [
            {
                "sub_bug_id": 1,
                "description": "Sub-bug 1: Root cause analysis",
                "priority": "high",
            },
            {
                "sub_bug_id": 2,
                "description": "Sub-bug 2: Contributing factors",
                "priority": "medium",
            },
        ]
        context.additional_context["decomposition_strategy"] = "causal_analysis"
        return context

    def _apply_multi_model_ensemble(
        self,
        context: EscalationContext,
    ) -> EscalationContext:
        """Apply Level 3: Multi-Model Ensemble."""
        context.model_responses = [
            {"model": "analyzer_1", "hypothesis": "Hypothesis A", "confidence": 0.7},
            {"model": "analyzer_2", "hypothesis": "Hypothesis B", "confidence": 0.6},
            {"model": "analyzer_3", "hypothesis": "Hypothesis A", "confidence": 0.8},
        ]
        context.additional_context["voting_result"] = "Hypothesis A (2/3)"
        return context

    def _apply_human_in_loop(self, context: EscalationContext) -> EscalationContext:
        """Apply Level 4: Human-in-the-Loop."""
        context.additional_context = {
            "action": "human_review",
            "requires_manual_intervention": True,
            "auto_fix_attempted": True,
            "auto_fix_failed": True,
        }
        return context

    def _generate_summary(self, context: EscalationContext) -> str:
        """Generate executive summary."""
        return (
            f"Bug fix escalation to level {context.level} was triggered. "
            f"Reason: {context.reason}. "
            f"Automated fixing attempts were unsuccessful."
        )

    def _generate_bug_description(self, context: EscalationContext) -> str:
        """Generate detailed bug description."""
        if context.original_candidate:
            return str(context.original_candidate.get("description", "Unknown"))
        return "Bug description not available"

    def _generate_attempted_fixes(
        self,
        context: EscalationContext,
    ) -> List[str]:
        """Generate list of attempted fixes."""
        fixes = []

        for i, level_context in enumerate(self.escalation_history):
            fixes.append(f"Level {i + 1}: {level_context.reason}")

        return fixes

    def _generate_evidence(
        self,
        context: EscalationContext,
    ) -> List[Dict[str, Any]]:
        """Generate evidence list."""
        evidence = []

        # Add model responses as evidence
        for response in context.model_responses:
            evidence.append({
                "type": "model_response",
                "content": response,
            })

        # Add decomposed bugs as evidence
        for bug in context.decomposed_bugs:
            evidence.append({
                "type": "decomposed_bug",
                "content": bug,
            })

        return evidence

    def _generate_recommendation(self, context: EscalationContext) -> str:
        """Generate recommendation for human."""
        if context.level == 4:
            return (
                "Manual code review and fix is required. "
                "All automated approaches have been exhausted. "
                "Please review the evidence and attempted fixes."
            )
        elif context.level == 3:
            return (
                "Consider the multi-model voting result. "
                "The majority hypothesis should be prioritized."
            )
        elif context.level == 2:
            return (
                "Focus on fixing sub-bugs individually. "
                "Start with the highest priority sub-bug."
            )
        else:
            return "Continue with expanded context analysis."

    def reset(self) -> None:
        """Reset escalation state."""
        self.current_level = 0
        self.escalation_history.clear()
        logger.debug("EscalationManager reset")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current escalation status.

        Returns:
            Status dictionary
        """
        return {
            "current_level": self.current_level,
            "max_level": 4,
            "escalation_count": len(self.escalation_history),
            "history": [c.to_dict() for c in self.escalation_history],
        }
