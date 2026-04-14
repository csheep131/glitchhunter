"""
Evidence Contract for GlitchHunter.

Defines the EvidencePackage dataclass that represents the mandatory
evidence package required before any automatic bug fix can proceed.
"""

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from agent.evidence_types import (
    ConfidenceLevel,
    EvidenceScore,
    EvidenceStrength,
    GateDecision,
    InvariantType,
    RiskClass,
    Scope,
)

if TYPE_CHECKING:
    from agent.hypothesis_agent import Hypothesis

logger = logging.getLogger(__name__)


@dataclass
class ReproductionHint:
    """
    Reproduction hint for the bug.
    
    Attributes:
        description: Human-readable description of how to reproduce
        code_snippet: Minimal code snippet that demonstrates the bug
        input_data: Test input that triggers the bug
        expected_behavior: What should happen (correct behavior)
        actual_behavior: What actually happens (buggy behavior)
    """

    description: str
    code_snippet: str
    input_data: str = ""
    expected_behavior: str = ""
    actual_behavior: str = ""

    def is_complete(self) -> bool:
        """Check if all required fields are non-empty."""
        return bool(self.description.strip() and self.code_snippet.strip())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "description": self.description,
            "code_snippet": self.code_snippet,
            "input_data": self.input_data,
            "expected_behavior": self.expected_behavior,
            "actual_behavior": self.actual_behavior,
        }


@dataclass
class AffectedSymbols:
    """
    Information about affected code symbols.
    
    Attributes:
        symbols: List of symbol names (functions, classes, variables)
        symbol_graph_snippet: GraphML or text representation of symbol relationships
        call_depth: Depth in call graph from entry point
        is_entry_point: Whether any affected symbol is a public API
    """

    symbols: List[str] = field(default_factory=list)
    symbol_graph_snippet: str = ""
    call_depth: int = 0
    is_entry_point: bool = False

    def is_complete(self) -> bool:
        """Check if at least one symbol is identified."""
        return len(self.symbols) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbols": self.symbols,
            "symbol_graph_snippet": self.symbol_graph_snippet[:500],  # Truncated
            "call_depth": self.call_depth,
            "is_entry_point": self.is_entry_point,
        }


@dataclass
class ViolatedInvariant:
    """
    Description of the violated invariant.
    
    Attributes:
        invariant_type: Type of invariant (DATA_FLOW, CONTROL_FLOW, etc.)
        description: Human-readable description of the invariant
        violation_details: Specific details of how it's violated
        invariant_location: File and line where invariant should hold
    """

    invariant_type: InvariantType
    description: str
    violation_details: str
    invariant_location: Tuple[str, int] = ("", 0)  # (file_path, line)

    def is_complete(self) -> bool:
        """Check if invariant is properly described."""
        return bool(
            self.description.strip()
            and self.violation_details.strip()
            and self.invariant_location[0]
        )

    def is_plausible(self) -> bool:
        """
        Check if invariant is plausible (not generic/placeholder).
        
        Generic descriptions like "something is wrong" are not plausible.
        """
        generic_phrases = [
            "something is wrong",
            "there is a bug",
            "this needs fixing",
            "error occurs",
            "invalid state",
        ]

        description_lower = self.description.lower()
        details_lower = self.violation_details.lower()

        # Check if description or details are too generic
        for phrase in generic_phrases:
            if phrase in description_lower or phrase in details_lower:
                return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "invariant_type": self.invariant_type.value,
            "description": self.description,
            "violation_details": self.violation_details,
            "invariant_location": {
                "file_path": self.invariant_location[0],
                "line": self.invariant_location[1],
            },
        }


@dataclass
class BugScope:
    """
    Scope assessment for the bug.
    
    Attributes:
        scope: Scope level (LOCAL, MODULE, CROSS_MODULE, SYSTEM)
        affected_modules: List of affected module/package names
        dependency_impact: Description of impact on dependencies
        upstream_impact: Does this affect upstream consumers?
        downstream_impact: Does this affect downstream dependencies?
    """

    scope: Scope
    affected_modules: List[str] = field(default_factory=list)
    dependency_impact: str = ""
    upstream_impact: bool = False
    downstream_impact: bool = False

    def is_complete(self) -> bool:
        """Check if scope is properly classified."""
        return bool(self.scope and len(self.affected_modules) >= 0)  # Can be empty for LOCAL

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "scope": self.scope.value,
            "affected_modules": self.affected_modules,
            "dependency_impact": self.dependency_impact,
            "upstream_impact": self.upstream_impact,
            "downstream_impact": self.downstream_impact,
        }


@dataclass
class RiskAssessment:
    """
    Risk assessment for the bug.
    
    Attributes:
        risk_class: Risk classification (LOW, MEDIUM, HIGH, CRITICAL)
        exploitability: How easy is it to exploit? (LOW/MEDIUM/HIGH)
        blast_radius: What systems/components are affected?
        cvss_score: Optional CVSS 3.1 score (0.0-10.0)
        business_impact: Description of business impact
    """

    risk_class: RiskClass
    exploitability: str  # "LOW", "MEDIUM", "HIGH"
    blast_radius: str
    cvss_score: Optional[float] = None
    business_impact: str = ""

    def __post_init__(self):
        """Validate CVSS score if provided."""
        if self.cvss_score is not None:
            if not (0.0 <= self.cvss_score <= 10.0):
                raise ValueError(f"CVSS score must be between 0.0 and 10.0, got {self.cvss_score}")

    def is_complete(self) -> bool:
        """Check if risk assessment is complete."""
        return bool(
            self.risk_class
            and self.exploitability.strip()
            and self.blast_radius.strip()
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "risk_class": self.risk_class.value,
            "exploitability": self.exploitability,
            "blast_radius": self.blast_radius,
            "cvss_score": self.cvss_score,
            "business_impact": self.business_impact,
        }


@dataclass
class EvidencePackage:
    """
    Complete evidence package for a bug candidate.
    
    This is the mandatory contract that must be fulfilled before
    any automatic bug fix can proceed.
    
    Attributes:
        candidate_id: Unique identifier for the bug candidate
        file_path: Source file containing the bug
        line_range: Line range (start, end) of the bug location
        
        # Core evidence components (all mandatory)
        reproduction_hint: How to reproduce the bug
        affected_symbols: Which code symbols are affected
        violated_invariant: What invariant is violated
        scope: Scope of the bug impact
        risk_assessment: Risk classification
        
        # Hypotheses from HypothesisAgent
        hypotheses: List of 3-5 hypotheses
        
        # Evidence quality metrics
        evidence_strength: Calculated strength (WEAK to VERY_STRONG)
        evidence_score: Raw score (0.0-1.0)
        confidence_factors: Factors affecting confidence
        
        # Validation state
        is_complete: Whether all required fields are filled
        validation_errors: List of validation error messages
        created_at: Timestamp of creation
    """

    candidate_id: str
    file_path: str
    line_range: Tuple[int, int]

    # Core evidence components
    reproduction_hint: ReproductionHint
    affected_symbols: AffectedSymbols
    violated_invariant: ViolatedInvariant
    scope: BugScope
    risk_assessment: RiskAssessment

    # Hypotheses
    hypotheses: List["Hypothesis"] = field(default_factory=list)

    # Evidence quality
    evidence_strength: EvidenceStrength = EvidenceStrength.WEAK
    evidence_score: EvidenceScore = 0.0
    confidence_factors: List[str] = field(default_factory=list)

    # Validation state
    is_complete: bool = False
    validation_errors: List[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self):
        """Validate and calculate derived fields."""
        self._validate()
        self._calculate_evidence_score()

    def _validate(self):
        """Validate all required fields."""
        errors = []

        # Check basic fields
        if not self.candidate_id.strip():
            errors.append("candidate_id is required")

        if not self.file_path.strip():
            errors.append("file_path is required")

        if not self.line_range or len(self.line_range) != 2:
            errors.append("line_range must be a tuple of (start, end)")

        # Check core components
        if not self.reproduction_hint.is_complete():
            errors.append("reproduction_hint is incomplete (description and code_snippet required)")

        if not self.affected_symbols.is_complete():
            errors.append("affected_symbols must contain at least one symbol")

        if not self.violated_invariant.is_complete():
            errors.append("violated_invariant is incomplete")

        if not self.violated_invariant.is_plausible():
            errors.append("violated_invariant description is too generic")

        if not self.scope.is_complete():
            errors.append("scope is not properly classified")

        if not self.risk_assessment.is_complete():
            errors.append("risk_assessment is incomplete")

        # Check hypotheses
        if len(self.hypotheses) < 3:
            errors.append(f"must have at least 3 hypotheses, got {len(self.hypotheses)}")

        if len(self.hypotheses) > 5:
            errors.append(f"must have at most 5 hypotheses, got {len(self.hypotheses)}")

        self.validation_errors = errors
        self.is_complete = len(errors) == 0

    def _calculate_evidence_score(self):
        """
        Calculate evidence score from various factors.
        
        Score components:
        - Hypothesis confidence (avg): 0-0.4
        - Symbol graph evidence: 0-0.2
        - Data flow evidence: 0-0.2
        - Reproduction clarity: 0-0.2
        """
        score = 0.0

        # Hypothesis confidence (40% weight)
        if self.hypotheses:
            avg_confidence = sum(h.confidence for h in self.hypotheses) / len(self.hypotheses)
            score += avg_confidence * 0.4

        # Symbol graph evidence (20% weight)
        if self.affected_symbols.symbol_graph_snippet:
            score += 0.1
        if self.affected_symbols.call_depth > 0:
            score += 0.1

        # Data flow evidence (20% weight)
        has_data_flow = any(h.data_flow_path for h in self.hypotheses)
        if has_data_flow:
            score += 0.2

        # Reproduction clarity (20% weight)
        repro = self.reproduction_hint
        if repro.description.strip():
            score += 0.1
        if repro.code_snippet.strip():
            score += 0.05
        if repro.input_data.strip():
            score += 0.05

        # Clamp to 0.0-1.0
        self.evidence_score = min(1.0, max(0.0, score))

        # Derive strength from score
        if self.evidence_score < 0.4:
            self.evidence_strength = EvidenceStrength.WEAK
        elif self.evidence_score < 0.6:
            self.evidence_strength = EvidenceStrength.MODERATE
        elif self.evidence_score < 0.8:
            self.evidence_strength = EvidenceStrength.STRONG
        else:
            self.evidence_strength = EvidenceStrength.VERY_STRONG

    def get_minimum_threshold(self) -> EvidenceScore:
        """
        Get minimum evidence score threshold for auto-fix.
        
        Returns:
            Minimum score required to proceed to Patch Loop
        """
        # CRITICAL and HIGH risks need stronger evidence
        if self.risk_assessment.risk_class in [RiskClass.CRITICAL, RiskClass.HIGH]:
            return 0.6
        elif self.risk_assessment.risk_class == RiskClass.MEDIUM:
            return 0.5
        else:
            return 0.4

    def meets_threshold(self) -> bool:
        """Check if evidence score meets minimum threshold."""
        return self.evidence_score >= self.get_minimum_threshold()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "candidate_id": self.candidate_id,
            "file_path": self.file_path,
            "line_range": list(self.line_range),
            "reproduction_hint": self.reproduction_hint.to_dict(),
            "affected_symbols": self.affected_symbols.to_dict(),
            "violated_invariant": self.violated_invariant.to_dict(),
            "scope": self.scope.to_dict(),
            "risk_assessment": self.risk_assessment.to_dict(),
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "evidence_strength": self.evidence_strength.value,
            "evidence_score": self.evidence_score,
            "confidence_factors": self.confidence_factors,
            "is_complete": self.is_complete,
            "validation_errors": self.validation_errors,
            "created_at": self.created_at,
        }

    def summary(self) -> str:
        """Generate human-readable summary."""
        return f"""
Evidence Package Summary
========================
Candidate: {self.candidate_id}
Location: {self.file_path}:{self.line_range[0]}-{self.line_range[1]}

Risk: {self.risk_assessment.risk_class.value.upper()} | 
Scope: {self.scope.scope.value.upper()} | 
Invariant: {self.violated_invariant.invariant_type.value}

Evidence Score: {self.evidence_score:.2f} ({self.evidence_strength.value})
Meets Threshold: {self.meets_threshold()}

Hypotheses: {len(self.hypotheses)} (avg confidence: {sum(h.confidence for h in self.hypotheses) / len(self.hypotheses) if self.hypotheses else 0:.2f})

Validation: {'PASSED' if self.is_complete else 'FAILED'}
{f"Errors: {', '.join(self.validation_errors)}" if self.validation_errors else ""}
""".strip()


@dataclass
class EvidencePackageBuilder:
    """
    Builder for creating EvidencePackage instances.
    
    Provides a fluent interface for constructing evidence packages
    with proper validation at each step.
    """

    def __init__(self):
        """Initialize builder with defaults."""
        self._candidate_id = ""
        self._file_path = ""
        self._line_range: Tuple[int, int] = (0, 0)
        self._reproduction_hint: Optional[ReproductionHint] = None
        self._affected_symbols: Optional[AffectedSymbols] = None
        self._violated_invariant: Optional[ViolatedInvariant] = None
        self._scope: Optional[BugScope] = None
        self._risk_assessment: Optional[RiskAssessment] = None
        self._hypotheses: List[Hypothesis] = []
        self._confidence_factors: List[str] = []

    def with_candidate(self, candidate_id: str, file_path: str, line_range: Tuple[int, int]) -> "EvidencePackageBuilder":
        """Set candidate identification."""
        self._candidate_id = candidate_id
        self._file_path = file_path
        self._line_range = line_range
        return self

    def with_reproduction(self, hint: ReproductionHint) -> "EvidencePackageBuilder":
        """Set reproduction hint."""
        self._reproduction_hint = hint
        return self

    def with_symbols(self, symbols: AffectedSymbols) -> "EvidencePackageBuilder":
        """Set affected symbols."""
        self._affected_symbols = symbols
        return self

    def with_invariant(self, invariant: ViolatedInvariant) -> "EvidencePackageBuilder":
        """Set violated invariant."""
        self._violated_invariant = invariant
        return self

    def with_scope(self, scope: BugScope) -> "EvidencePackageBuilder":
        """Set bug scope."""
        self._scope = scope
        return self

    def with_risk(self, risk: RiskAssessment) -> "EvidencePackageBuilder":
        """Set risk assessment."""
        self._risk_assessment = risk
        return self

    def with_hypotheses(self, hypotheses: List["Hypothesis"]) -> "EvidencePackageBuilder":
        """Set hypotheses."""
        self._hypotheses = hypotheses
        return self

    def add_confidence_factor(self, factor: str) -> "EvidencePackageBuilder":
        """Add confidence factor."""
        self._confidence_factors.append(factor)
        return self

    def build(self) -> EvidencePackage:
        """
        Build the EvidencePackage.
        
        Returns:
            Validated EvidencePackage instance
        """
        from datetime import datetime

        if not all([
            self._reproduction_hint,
            self._affected_symbols,
            self._violated_invariant,
            self._scope,
            self._risk_assessment,
        ]):
            raise ValueError("Missing required components. Use all with_* methods before build().")

        package = EvidencePackage(
            candidate_id=self._candidate_id,
            file_path=self._file_path,
            line_range=self._line_range,
            reproduction_hint=self._reproduction_hint,
            affected_symbols=self._affected_symbols,
            violated_invariant=self._violated_invariant,
            scope=self._scope,
            risk_assessment=self._risk_assessment,
            hypotheses=self._hypotheses,
            confidence_factors=self._confidence_factors,
            created_at=datetime.now().isoformat(),
        )

        return package
