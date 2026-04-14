"""
Evidence Gate for GlitchHunter.

Validates EvidencePackage instances before allowing the Patch Loop to proceed.
This is the mandatory checkpoint that prevents auto-fixes without sufficient evidence.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent.evidence_contract import EvidencePackage
from agent.evidence_types import EvidenceScore, EvidenceStrength, GateDecision, RiskClass

logger = logging.getLogger(__name__)


@dataclass
class GateValidationResult:
    """
    Result of EvidenceGate validation.
    
    Attributes:
        passed: Whether validation passed
        decision: Gate decision (PASSED/RETRY/REJECTED)
        errors: List of validation errors
        warnings: List of warnings (non-blocking)
        evidence_score: Calculated evidence score
        minimum_threshold: Minimum required score for this bug
        retry_hints: Hints for improving evidence on retry
    """

    passed: bool = False
    decision: GateDecision = GateDecision.RETRY
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    evidence_score: EvidenceScore = 0.0
    minimum_threshold: EvidenceScore = 0.5
    retry_hints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "decision": self.decision.value,
            "errors": self.errors,
            "warnings": self.warnings,
            "evidence_score": self.evidence_score,
            "minimum_threshold": self.minimum_threshold,
            "retry_hints": self.retry_hints,
        }


class EvidenceGate:
    """
    EvidenceGate validator.
    
    This gate sits between the Shield (hypothesis generation) and
    the Patch Loop (auto-fix generation). It ensures that every bug
    candidate has sufficient evidence before any automatic fix is attempted.
    
    Validation checks:
    1. Structural completeness (all required fields present)
    2. Evidence quality (score meets threshold)
    3. Invariant plausibility (not generic/placeholder)
    4. Risk-appropriate threshold (higher risk = higher evidence required)
    5. Hypothesis diversity (3-5 distinct hypotheses)
    
    Usage:
        gate = EvidenceGate(config)
        result = gate.validate(evidence_package)
        
        if result.passed:
            # Proceed to Patch Loop
            pass
        elif result.decision == GateDecision.RETRY:
            # Retry evidence generation with hints
            pass
        else:
            # Escalate to human
            pass
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize EvidenceGate.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        
        # Thresholds from config or defaults
        self.min_score_weak = self.config.get("evidence_gate", {}).get("min_score_weak", 0.4)
        self.min_score_medium = self.config.get("evidence_gate", {}).get("min_score_medium", 0.5)
        self.min_score_high = self.config.get("evidence_gate", {}).get("min_score_high", 0.6)
        
        # Maximum retries before escalation
        self.max_retries = self.config.get("evidence_gate", {}).get("max_retries", 3)
        
        logger.debug(
            f"EvidenceGate initialized: min_score_weak={self.min_score_weak}, "
            f"min_score_medium={self.min_score_medium}, min_score_high={self.min_score_high}"
        )

    def validate(self, package: EvidencePackage) -> GateValidationResult:
        """
        Validate an EvidencePackage.
        
        This is the main entry point for evidence validation. It performs
        all checks and returns a comprehensive result with errors, warnings,
        and retry hints.
        
        Args:
            package: EvidencePackage to validate
            
        Returns:
            GateValidationResult with validation outcome
        """
        logger.info(f"Validating evidence package for candidate {package.candidate_id}")
        
        result = GateValidationResult(
            evidence_score=package.evidence_score,
            minimum_threshold=package.get_minimum_threshold(),
        )
        
        # Check 1: Structural completeness
        structural_errors = self._check_structural_completeness(package)
        result.errors.extend(structural_errors)
        
        # Check 2: Evidence quality threshold
        threshold_errors = self._check_evidence_threshold(package)
        result.errors.extend(threshold_errors)
        
        # Check 3: Invariant plausibility
        invariant_errors = self._check_invariant_plausibility(package)
        result.errors.extend(invariant_errors)
        
        # Check 4: Hypothesis diversity
        hypothesis_errors = self._check_hypothesis_diversity(package)
        result.errors.extend(hypothesis_errors)
        
        # Check 5: Risk-appropriate evidence
        risk_warnings = self._check_risk_appropriate_evidence(package)
        result.warnings.extend(risk_warnings)
        
        # Determine decision
        if result.errors:
            # Has errors - decide between RETRY and REJECTED
            if self._is_fundamentally_flawed(package, result.errors):
                result.decision = GateDecision.REJECTED
                result.passed = False
                logger.warning(
                    f"Evidence package for {package.candidate_id} fundamentally flawed: {result.errors}"
                )
            else:
                result.decision = GateDecision.RETRY
                result.passed = False
                result.retry_hints = self._generate_retry_hints(package, result.errors)
                logger.info(
                    f"Evidence package for {package.candidate_id} needs improvement: {result.errors}"
                )
        else:
            # No errors - passed
            result.decision = GateDecision.PASSED
            result.passed = True
            logger.info(f"Evidence package for {package.candidate_id} validated successfully")
        
        return result

    def _check_structural_completeness(self, package: EvidencePackage) -> List[str]:
        """
        Check 1: Structural completeness.
        
        Verifies that all required fields are present and non-empty.
        This relies on the EvidencePackage's own validation.
        
        Returns:
            List of error messages (empty if complete)
        """
        errors = []
        
        if not package.is_complete:
            errors.extend(package.validation_errors)
        
        # Additional structural checks
        if not package.file_path.endswith(('.py', '.rs', '.js', '.ts', '.go', '.java', '.cpp', '.c')):
            errors.append(f"file_path does not appear to be a valid source file: {package.file_path}")
        
        if package.line_range[0] <= 0 or package.line_range[1] < package.line_range[0]:
            errors.append(f"line_range must be positive and end >= start: {package.line_range}")
        
        return errors

    def _check_evidence_threshold(self, package: EvidencePackage) -> List[str]:
        """
        Check 2: Evidence quality threshold.
        
        Verifies that the evidence score meets the minimum threshold
        for the given risk class.
        
        Returns:
            List of error messages (empty if threshold met)
        """
        errors = []
        min_threshold = package.get_minimum_threshold()
        
        if package.evidence_score < min_threshold:
            errors.append(
                f"Evidence score {package.evidence_score:.2f} below minimum threshold {min_threshold:.2f} "
                f"for risk class {package.risk_assessment.risk_class.value}"
            )
        
        # Check evidence strength
        if package.evidence_strength == EvidenceStrength.WEAK:
            errors.append(
                f"Evidence strength is WEAK ({package.evidence_score:.2f}). "
                f"Need at least MODERATE ({self.min_score_weak:.2f}+) to proceed."
            )
        
        return errors

    def _check_invariant_plausibility(self, package: EvidencePackage) -> List[str]:
        """
        Check 3: Invariant plausibility.
        
        Verifies that the violated invariant is not a generic placeholder.
        Generic descriptions like "something is wrong" indicate poor analysis.
        
        Returns:
            List of error messages (empty if plausible)
        """
        errors = []
        invariant = package.violated_invariant
        
        if not invariant.is_plausible():
            errors.append(
                "Violated invariant description is too generic. "
                "Must describe specific invariant violation (e.g., 'unvalidated input reaches SQL query'). "
                f"Got: {invariant.description}"
            )
        
        # Check violation details
        if len(invariant.violation_details) < 20:
            errors.append(
                f"Violation details too short ({len(invariant.violation_details)} chars). "
                "Must provide specific details of how the invariant is violated."
            )
        
        return errors

    def _check_hypothesis_diversity(self, package: EvidencePackage) -> List[str]:
        """
        Check 4: Hypothesis diversity.
        
        Verifies that hypotheses are diverse (not duplicates) and
        cover different aspects of the bug.
        
        Returns:
            List of error messages (empty if diverse)
        """
        errors = []
        hypotheses = package.hypotheses
        
        # Check count (already validated, but double-check)
        if len(hypotheses) < 3:
            errors.append(f"Need at least 3 hypotheses, got {len(hypotheses)}")
        elif len(hypotheses) > 5:
            errors.append(f"Maximum 5 hypotheses allowed, got {len(hypotheses)}")
        
        # Check for duplicate titles
        titles = [h.title.lower() for h in hypotheses]
        if len(titles) != len(set(titles)):
            errors.append("Duplicate hypothesis titles detected. Each hypothesis must be unique.")
        
        # Check hypothesis type diversity
        hypothesis_types = [h.hypothesis_type.value for h in hypotheses]
        unique_types = len(set(hypothesis_types))
        
        if unique_types < 2 and len(hypotheses) >= 3:
            errors.append(
                f"Low hypothesis diversity: all {len(hypotheses)} hypotheses are of the same type. "
                "Should explore different failure modes."
            )
        
        # Check confidence distribution
        confidences = [h.confidence for h in hypotheses]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        if avg_confidence < 0.3:
            errors.append(
                f"Average hypothesis confidence too low ({avg_confidence:.2f}). "
                "Need at least 0.3 average confidence."
            )
        
        return errors

    def _check_risk_appropriate_evidence(self, package: EvidencePackage) -> List[str]:
        """
        Check 5: Risk-appropriate evidence.
        
        Higher risk bugs require stronger evidence. This check
        generates warnings (not errors) for borderline cases.
        
        Returns:
            List of warning messages
        """
        warnings = []
        risk_class = package.risk_assessment.risk_class
        evidence_score = package.evidence_score
        
        # CRITICAL risks with moderate evidence
        if risk_class == RiskClass.CRITICAL and evidence_score < 0.7:
            warnings.append(
                f"CRITICAL risk bug has moderate evidence ({evidence_score:.2f}). "
                "Consider strengthening evidence before auto-fix."
            )
        
        # HIGH risk with weak reproduction hint
        if risk_class == RiskClass.HIGH:
            repro = package.reproduction_hint
            if not repro.input_data.strip():
                warnings.append(
                    "HIGH risk bug lacks concrete input data for reproduction. "
                    "Consider adding specific test input."
                )
        
        # Cross-module scope with low evidence
        if package.scope.scope.value == "cross_module" and evidence_score < 0.5:
            warnings.append(
                f"Cross-module bug has low evidence ({evidence_score:.2f}). "
                "Cross-module bugs typically require stronger evidence due to wider impact."
            )
        
        return warnings

    def _is_fundamentally_flawed(
        self,
        package: EvidencePackage,
        errors: List[str],
    ) -> bool:
        """
        Determine if evidence package is fundamentally flawed.
        
        A package is fundamentally flawed if it cannot be fixed by
        simply regenerating evidence (e.g., wrong file, no actual bug).
        
        Args:
            package: EvidencePackage to assess
            errors: List of validation errors
            
        Returns:
            True if fundamentally flawed, False if retry might help
        """
        # Critical errors that indicate fundamental flaws
        critical_errors = [
            "file_path is required",
            "candidate_id is required",
            "file_path does not appear to be a valid source file",
        ]
        
        for error in errors:
            for critical in critical_errors:
                if critical in error:
                    return True
        
        # Too many errors suggests fundamental issues
        if len(errors) >= 5:
            return True
        
        # Missing core components
        core_missing = [
            e for e in errors
            if any(core in e for core in [
                "reproduction_hint is incomplete",
                "affected_symbols must contain",
                "violated_invariant is incomplete",
            ])
        ]
        
        if len(core_missing) >= 3:
            return True
        
        return False

    def _generate_retry_hints(
        self,
        package: EvidencePackage,
        errors: List[str],
    ) -> List[str]:
        """
        Generate hints for improving evidence on retry.
        
        Provides actionable feedback for each error.
        
        Args:
            package: EvidencePackage with errors
            errors: List of validation errors
            
        Returns:
            List of retry hints
        """
        hints = []
        
        for error in errors:
            if "Evidence score" in error and "below minimum threshold" in error:
                hints.append(
                    "Strengthen evidence by: (1) adding more data flow paths, "
                    "(2) including symbol graph context, (3) providing concrete reproduction input"
                )
            
            elif "hypothesis confidence" in error:
                hints.append(
                    "Improve hypothesis quality by analyzing actual code paths rather than "
                    "generic patterns. Use data-flow graph to trace actual taint paths."
                )
            
            elif "invariant description is too generic" in error:
                hints.append(
                    "Be specific about the invariant. Instead of 'data flow issue', say "
                    "'user input from request parameter flows to SQL query without sanitization'"
                )
            
            elif "Duplicate hypothesis titles" in error:
                hints.append(
                    "Ensure each hypothesis explores a different failure mode. "
                    "For SQL injection: consider (1) direct injection, (2) ORM misuse, "
                    "(3) second-order injection as distinct hypotheses."
                )
            
            elif "reproduction_hint is incomplete" in error:
                hints.append(
                    "Add a minimal code snippet that demonstrates the bug. "
                    "Include the exact input that triggers the issue."
                )
        
        # Add general hint if evidence score is low
        if package.evidence_score < 0.4:
            hints.append(
                "General: Focus on concrete evidence - actual data flow paths from source to sink, "
                "specific affected symbols from the symbol graph, and a reproducible test case."
            )
        
        return hints

    def validate_and_raise(
        self,
        package: EvidencePackage,
    ) -> None:
        """
        Validate and raise exception if validation fails.
        
        Convenience method for use in contexts where exceptions
        are preferred over result objects.
        
        Args:
            package: EvidencePackage to validate
            
        Raises:
            EvidenceGateError: If validation fails
        """
        result = self.validate(package)
        
        if not result.passed:
            raise EvidenceGateError(
                f"Evidence validation failed for {package.candidate_id}: {result.errors}",
                result=result,
            )


class EvidenceGateError(Exception):
    """
    Exception raised when EvidenceGate validation fails.
    
    Attributes:
        message: Error message
        result: GateValidationResult with details
    """

    def __init__(self, message: str, result: Optional[GateValidationResult] = None):
        """
        Initialize exception.
        
        Args:
            message: Error message
            result: Optional validation result
        """
        super().__init__(message)
        self.result = result

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "message": str(self),
            "result": self.result.to_dict() if self.result else None,
        }
