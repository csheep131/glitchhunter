"""
Tests für Evidence-Contract Komponenten.

Testet:
- EvidencePackage Dataclass
- ReproductionHint
- AffectedSymbols
- ViolatedInvariant
- BugScope
- RiskAssessment
- EvidencePackageBuilder
"""

import pytest
from typing import List

from agent.evidence_contract import (
    AffectedSymbols,
    BugScope,
    EvidencePackage,
    EvidencePackageBuilder,
    ReproductionHint,
    RiskAssessment,
    ViolatedInvariant,
)
from agent.evidence_types import (
    EvidenceStrength,
    InvariantType,
    RiskClass,
    Scope,
)
from agent.hypothesis_agent import Hypothesis, HypothesisType, Severity, BugCandidate


class TestReproductionHint:
    """Tests für ReproductionHint."""

    def test_is_complete_valid(self):
        """Test that valid reproduction hint is complete."""
        hint = ReproductionHint(
            description="SQL Injection through user input",
            code_snippet="cursor.execute(f'SELECT * FROM users WHERE id={user_id}')",
            input_data="' OR '1'='1' --",
            expected_behavior="Input should be parameterized",
            actual_behavior="Input is executed as SQL",
        )
        assert hint.is_complete() is True

    def test_is_complete_missing_description(self):
        """Test that empty description makes it incomplete."""
        hint = ReproductionHint(
            description="",
            code_snippet="some_code()",
        )
        assert hint.is_complete() is False

    def test_is_complete_missing_code_snippet(self):
        """Test that empty code snippet makes it incomplete."""
        hint = ReproductionHint(
            description="Some bug description",
            code_snippet="",
        )
        assert hint.is_complete() is False

    def test_to_dict(self):
        """Test dictionary conversion."""
        hint = ReproductionHint(
            description="Test description",
            code_snippet="test_code()",
            input_data="test_input",
        )
        result = hint.to_dict()
        
        assert result["description"] == "Test description"
        assert result["code_snippet"] == "test_code()"
        assert result["input_data"] == "test_input"


class TestAffectedSymbols:
    """Tests für AffectedSymbols."""

    def test_is_complete_with_symbols(self):
        """Test completeness with symbols."""
        symbols = AffectedSymbols(
            symbols=["func1", "func2"],
            symbol_graph_snippet="func1 -> func2",
            call_depth=2,
        )
        assert symbols.is_complete() is True

    def test_is_complete_empty_symbols(self):
        """Test that empty symbols list is incomplete."""
        symbols = AffectedSymbols(
            symbols=[],
        )
        assert symbols.is_complete() is False

    def test_to_dict(self):
        """Test dictionary conversion."""
        symbols = AffectedSymbols(
            symbols=["handle_login", "authenticate"],
            symbol_graph_snippet="handle_login -> authenticate",
            call_depth=1,
            is_entry_point=True,
        )
        result = symbols.to_dict()
        
        assert result["symbols"] == ["handle_login", "authenticate"]
        assert result["call_depth"] == 1
        assert result["is_entry_point"] is True


class TestViolatedInvariant:
    """Tests für ViolatedInvariant."""

    def test_is_complete_valid(self):
        """Test valid invariant."""
        invariant = ViolatedInvariant(
            invariant_type=InvariantType.DATA_FLOW,
            description="Unvalidated input reaches SQL query",
            violation_details="User input from request flows to cursor.execute() without sanitization",
            invariant_location=("src/auth.py", 42),
        )
        assert invariant.is_complete() is True

    def test_is_complete_missing_location(self):
        """Test incomplete location."""
        invariant = ViolatedInvariant(
            invariant_type=InvariantType.DATA_FLOW,
            description="Some description",
            violation_details="Some details",
            invariant_location=("", 0),
        )
        assert invariant.is_complete() is False

    def test_is_plausible_specific(self):
        """Test that specific description is plausible."""
        invariant = ViolatedInvariant(
            invariant_type=InvariantType.DATA_FLOW,
            description="Unvalidated external input flows from trust boundary to SQL query sink without sanitization",
            violation_details="User input reaches cursor.execute() directly",
        )
        assert invariant.is_plausible() is True

    def test_is_plausible_generic(self):
        """Test that generic description is not plausible."""
        invariant = ViolatedInvariant(
            invariant_type=InvariantType.DATA_FLOW,
            description="Something is wrong",
            violation_details="Error occurs",
        )
        assert invariant.is_plausible() is False

    def test_is_plausible_generic_phrases(self):
        """Test various generic phrases."""
        generic_phrases = [
            ("there is a bug", "details"),
            ("this needs fixing", "details"),
            ("error occurs", "details"),
            ("invalid state", "details"),
        ]
        
        for desc, details in generic_phrases:
            invariant = ViolatedInvariant(
                invariant_type=InvariantType.DATA_FLOW,
                description=desc,
                violation_details=details,
            )
            assert invariant.is_plausible() is False

    def test_to_dict(self):
        """Test dictionary conversion."""
        invariant = ViolatedInvariant(
            invariant_type=InvariantType.CONTROL_FLOW,
            description="Auth check can be bypassed",
            violation_details="Missing validation on admin parameter",
            invariant_location=("src/api.py", 100),
        )
        result = invariant.to_dict()
        
        assert result["invariant_type"] == "control_flow"
        assert result["invariant_location"]["file_path"] == "src/api.py"
        assert result["invariant_location"]["line"] == 100


class TestBugScope:
    """Tests für BugScope."""

    def test_is_complete_local_scope(self):
        """Test local scope is complete."""
        scope = BugScope(
            scope=Scope.LOCAL,
            affected_modules=[],
        )
        assert scope.is_complete() is True

    def test_is_complete_cross_module(self):
        """Test cross-module scope."""
        scope = BugScope(
            scope=Scope.CROSS_MODULE,
            affected_modules=["auth", "database"],
            dependency_impact="Affects public API",
        )
        assert scope.is_complete() is True

    def test_to_dict(self):
        """Test dictionary conversion."""
        scope = BugScope(
            scope=Scope.MODULE,
            affected_modules=["security"],
            dependency_impact="Module-wide impact",
            upstream_impact=False,
            downstream_impact=True,
        )
        result = scope.to_dict()
        
        assert result["scope"] == "module"
        assert result["affected_modules"] == ["security"]
        assert result["downstream_impact"] is True


class TestRiskAssessment:
    """Tests für RiskAssessment."""

    def test_is_complete_valid(self):
        """Test valid risk assessment."""
        risk = RiskAssessment(
            risk_class=RiskClass.HIGH,
            exploitability="HIGH",
            blast_radius="Multiple modules affected",
            cvss_score=7.5,
            business_impact="Data breach risk",
        )
        assert risk.is_complete() is True

    def test_is_complete_missing_fields(self):
        """Test incomplete risk assessment."""
        risk = RiskAssessment(
            risk_class=RiskClass.MEDIUM,
            exploitability="",
            blast_radius="",
        )
        assert risk.is_complete() is False

    def test_cvss_score_validation_valid(self):
        """Test valid CVSS score."""
        risk = RiskAssessment(
            risk_class=RiskClass.HIGH,
            exploitability="HIGH",
            blast_radius="Impact",
            cvss_score=7.5,
        )
        assert risk.cvss_score == 7.5

    def test_cvss_score_validation_invalid(self):
        """Test invalid CVSS score raises error."""
        with pytest.raises(ValueError, match="CVSS score must be between"):
            RiskAssessment(
                risk_class=RiskClass.HIGH,
                exploitability="HIGH",
                blast_radius="Impact",
                cvss_score=15.0,  # Invalid: > 10
            )

    def test_to_dict(self):
        """Test dictionary conversion."""
        risk = RiskAssessment(
            risk_class=RiskClass.CRITICAL,
            exploitability="HIGH",
            blast_radius="System-wide",
            cvss_score=9.0,
            business_impact="Severe business impact",
        )
        result = risk.to_dict()
        
        assert result["risk_class"] == "critical"
        assert result["cvss_score"] == 9.0
        assert result["business_impact"] == "Severe business impact"


class TestEvidencePackage:
    """Tests für EvidencePackage."""

    def create_valid_hypotheses(self) -> List[Hypothesis]:
        """Create valid hypotheses for testing."""
        return [
            Hypothesis(
                id="hypo_1",
                title="SQL Injection via user input",
                description="Unvalidated user input reaches SQL query",
                hypothesis_type=HypothesisType.SQL_INJECTION_USER_INPUT,
                candidate_id="test_candidate",
                confidence=0.8,
                severity=Severity.CRITICAL,
            ),
            Hypothesis(
                id="hypo_2",
                title="SQL Injection via dynamic query",
                description="Dynamic query construction without parameterization",
                hypothesis_type=HypothesisType.SQL_INJECTION_DYNAMIC_QUERY,
                candidate_id="test_candidate",
                confidence=0.7,
                severity=Severity.HIGH,
            ),
            Hypothesis(
                id="hypo_3",
                title="ORM misuse allowing raw SQL",
                description="ORM raw() method used with user input",
                hypothesis_type=HypothesisType.SQL_INJECTION_ORM_MISUSE,
                candidate_id="test_candidate",
                confidence=0.6,
                severity=Severity.HIGH,
            ),
        ]

    def test_is_complete_valid(self):
        """Test complete valid evidence package."""
        package = EvidencePackage(
            candidate_id="test_001",
            file_path="src/auth.py",
            line_range=(40, 50),
            reproduction_hint=ReproductionHint(
                description="SQL Injection",
                code_snippet="cursor.execute(f'SELECT...')",
            ),
            affected_symbols=AffectedSymbols(
                symbols=["handle_login", "authenticate"],
            ),
            violated_invariant=ViolatedInvariant(
                invariant_type=InvariantType.DATA_FLOW,
                description="Unvalidated input reaches SQL query without sanitization",
                violation_details="User input flows directly to cursor.execute()",
                invariant_location=("src/auth.py", 42),
            ),
            scope=BugScope(
                scope=Scope.LOCAL,
            ),
            risk_assessment=RiskAssessment(
                risk_class=RiskClass.HIGH,
                exploitability="HIGH",
                blast_radius="Module affected",
            ),
            hypotheses=self.create_valid_hypotheses(),
        )
        
        assert package.is_complete is True
        assert len(package.validation_errors) == 0

    def test_is_complete_missing_candidate_id(self):
        """Test missing candidate_id."""
        package = EvidencePackage(
            candidate_id="",
            file_path="src/auth.py",
            line_range=(40, 50),
            reproduction_hint=ReproductionHint(description="Desc", code_snippet="code()"),
            affected_symbols=AffectedSymbols(symbols=["func"]),
            violated_invariant=ViolatedInvariant(
                invariant_type=InvariantType.DATA_FLOW,
                description="Valid description",
                violation_details="Valid details",
                invariant_location=("src/auth.py", 42),
            ),
            scope=BugScope(scope=Scope.LOCAL),
            risk_assessment=RiskAssessment(
                risk_class=RiskClass.MEDIUM,
                exploitability="MEDIUM",
                blast_radius="Impact",
            ),
            hypotheses=self.create_valid_hypotheses(),
        )
        
        assert package.is_complete is False
        assert "candidate_id is required" in package.validation_errors

    def test_is_complete_missing_symbols(self):
        """Test missing affected symbols."""
        package = EvidencePackage(
            candidate_id="test_001",
            file_path="src/auth.py",
            line_range=(40, 50),
            reproduction_hint=ReproductionHint(description="Desc", code_snippet="code()"),
            affected_symbols=AffectedSymbols(symbols=[]),  # Empty!
            violated_invariant=ViolatedInvariant(
                invariant_type=InvariantType.DATA_FLOW,
                description="Valid description",
                violation_details="Valid details",
                invariant_location=("src/auth.py", 42),
            ),
            scope=BugScope(scope=Scope.LOCAL),
            risk_assessment=RiskAssessment(
                risk_class=RiskClass.MEDIUM,
                exploitability="MEDIUM",
                blast_radius="Impact",
            ),
            hypotheses=self.create_valid_hypotheses(),
        )
        
        assert package.is_complete is False
        assert "affected_symbols must contain at least one symbol" in package.validation_errors

    def test_is_complete_wrong_hypothesis_count(self):
        """Test wrong number of hypotheses."""
        # Too few hypotheses
        package = EvidencePackage(
            candidate_id="test_001",
            file_path="src/auth.py",
            line_range=(40, 50),
            reproduction_hint=ReproductionHint(description="Desc", code_snippet="code()"),
            affected_symbols=AffectedSymbols(symbols=["func"]),
            violated_invariant=ViolatedInvariant(
                invariant_type=InvariantType.DATA_FLOW,
                description="Valid description",
                violation_details="Valid details",
                invariant_location=("src/auth.py", 42),
            ),
            scope=BugScope(scope=Scope.LOCAL),
            risk_assessment=RiskAssessment(
                risk_class=RiskClass.MEDIUM,
                exploitability="MEDIUM",
                blast_radius="Impact",
            ),
            hypotheses=[self.create_valid_hypotheses()[0]],  # Only 1!
        )
        
        assert package.is_complete is False
        assert "must have at least 3 hypotheses" in package.validation_errors

    def test_evidence_score_calculation(self):
        """Test evidence score calculation."""
        hypotheses = self.create_valid_hypotheses()
        # Avg confidence: (0.8 + 0.7 + 0.6) / 3 = 0.7
        
        package = EvidencePackage(
            candidate_id="test_001",
            file_path="src/auth.py",
            line_range=(40, 50),
            reproduction_hint=ReproductionHint(
                description="Detailed description",
                code_snippet="cursor.execute(f'SELECT...')",
                input_data="' OR '1'='1'",
            ),
            affected_symbols=AffectedSymbols(
                symbols=["handle_login", "authenticate"],
                symbol_graph_snippet="graph_snippet",
                call_depth=2,
            ),
            violated_invariant=ViolatedInvariant(
                invariant_type=InvariantType.DATA_FLOW,
                description="Unvalidated input reaches SQL query",
                violation_details="User input flows to cursor.execute()",
                invariant_location=("src/auth.py", 42),
            ),
            scope=BugScope(scope=Scope.LOCAL),
            risk_assessment=RiskAssessment(
                risk_class=RiskClass.HIGH,
                exploitability="HIGH",
                blast_radius="Module affected",
            ),
            hypotheses=hypotheses,
        )
        
        # Expected score components:
        # - Hypothesis confidence: 0.7 * 0.4 = 0.28
        # - Symbol graph: 0.1 + 0.1 = 0.2
        # - Data flow (has data_flow_path in hypotheses): 0.2
        # - Reproduction: 0.1 + 0.05 + 0.05 = 0.2
        # Total: ~0.88
        
        assert package.evidence_score > 0.6
        assert package.evidence_strength == EvidenceStrength.VERY_STRONG

    def test_evidence_strength_derivation(self):
        """Test evidence strength derivation from score."""
        # Create package with low score
        package = EvidencePackage(
            candidate_id="test_001",
            file_path="src/auth.py",
            line_range=(40, 50),
            reproduction_hint=ReproductionHint(description="Desc", code_snippet="code()"),
            affected_symbols=AffectedSymbols(symbols=["func"]),
            violated_invariant=ViolatedInvariant(
                invariant_type=InvariantType.DATA_FLOW,
                description="Valid description",
                violation_details="Valid details",
                invariant_location=("src/auth.py", 42),
            ),
            scope=BugScope(scope=Scope.LOCAL),
            risk_assessment=RiskAssessment(
                risk_class=RiskClass.MEDIUM,
                exploitability="MEDIUM",
                blast_radius="Impact",
            ),
            hypotheses=self.create_valid_hypotheses(),
        )
        
        # Score should be calculated, strength derived from it
        assert 0.0 <= package.evidence_score <= 1.0
        
        if package.evidence_score < 0.4:
            assert package.evidence_strength == EvidenceStrength.WEAK
        elif package.evidence_score < 0.6:
            assert package.evidence_strength == EvidenceStrength.MODERATE
        elif package.evidence_score < 0.8:
            assert package.evidence_strength == EvidenceStrength.STRONG
        else:
            assert package.evidence_strength == EvidenceStrength.VERY_STRONG

    def test_minimum_threshold_by_risk(self):
        """Test minimum threshold varies by risk class."""
        base_kwargs = {
            "candidate_id": "test_001",
            "file_path": "src/auth.py",
            "line_range": (40, 50),
            "reproduction_hint": ReproductionHint(description="Desc", code_snippet="code()"),
            "affected_symbols": AffectedSymbols(symbols=["func"]),
            "violated_invariant": ViolatedInvariant(
                invariant_type=InvariantType.DATA_FLOW,
                description="Valid description",
                violation_details="Valid details",
                invariant_location=("src/auth.py", 42),
            ),
            "scope": BugScope(scope=Scope.LOCAL),
            "hypotheses": self.create_valid_hypotheses(),
        }
        
        # CRITICAL risk
        package_critical = EvidencePackage(
            risk_assessment=RiskAssessment(
                risk_class=RiskClass.CRITICAL,
                exploitability="HIGH",
                blast_radius="System",
            ),
            **base_kwargs
        )
        assert package_critical.get_minimum_threshold() == 0.6
        
        # HIGH risk
        package_high = EvidencePackage(
            risk_assessment=RiskAssessment(
                risk_class=RiskClass.HIGH,
                exploitability="HIGH",
                blast_radius="Multiple modules",
            ),
            **base_kwargs
        )
        assert package_high.get_minimum_threshold() == 0.6
        
        # MEDIUM risk
        package_medium = EvidencePackage(
            risk_assessment=RiskAssessment(
                risk_class=RiskClass.MEDIUM,
                exploitability="MEDIUM",
                blast_radius="Module",
            ),
            **base_kwargs
        )
        assert package_medium.get_minimum_threshold() == 0.5
        
        # LOW risk
        package_low = EvidencePackage(
            risk_assessment=RiskAssessment(
                risk_class=RiskClass.LOW,
                exploitability="LOW",
                blast_radius="Function",
            ),
            **base_kwargs
        )
        assert package_low.get_minimum_threshold() == 0.4

    def test_meets_threshold(self):
        """Test meets_threshold method."""
        package = EvidencePackage(
            candidate_id="test_001",
            file_path="src/auth.py",
            line_range=(40, 50),
            reproduction_hint=ReproductionHint(description="Desc", code_snippet="code()"),
            affected_symbols=AffectedSymbols(symbols=["func"]),
            violated_invariant=ViolatedInvariant(
                invariant_type=InvariantType.DATA_FLOW,
                description="Valid description",
                violation_details="Valid details",
                invariant_location=("src/auth.py", 42),
            ),
            scope=BugScope(scope=Scope.LOCAL),
            risk_assessment=RiskAssessment(
                risk_class=RiskClass.MEDIUM,
                exploitability="MEDIUM",
                blast_radius="Impact",
            ),
            hypotheses=self.create_valid_hypotheses(),
        )
        
        # Score should be >= 0.5 for MEDIUM risk
        # If score >= threshold, meets_threshold returns True
        assert package.meets_threshold() == (package.evidence_score >= 0.5)

    def test_to_dict(self):
        """Test dictionary conversion."""
        package = EvidencePackage(
            candidate_id="test_001",
            file_path="src/auth.py",
            line_range=(40, 50),
            reproduction_hint=ReproductionHint(description="Desc", code_snippet="code()"),
            affected_symbols=AffectedSymbols(symbols=["func"]),
            violated_invariant=ViolatedInvariant(
                invariant_type=InvariantType.DATA_FLOW,
                description="Valid description",
                violation_details="Valid details",
                invariant_location=("src/auth.py", 42),
            ),
            scope=BugScope(scope=Scope.LOCAL),
            risk_assessment=RiskAssessment(
                risk_class=RiskClass.MEDIUM,
                exploitability="MEDIUM",
                blast_radius="Impact",
            ),
            hypotheses=self.create_valid_hypotheses(),
            created_at="2026-04-14T10:00:00",
        )
        
        result = package.to_dict()
        
        assert result["candidate_id"] == "test_001"
        assert result["file_path"] == "src/auth.py"
        assert result["line_range"] == [40, 50]
        assert result["is_complete"] == package.is_complete
        assert len(result["hypotheses"]) == 3

    def test_summary(self):
        """Test summary generation."""
        package = EvidencePackage(
            candidate_id="test_001",
            file_path="src/auth.py",
            line_range=(40, 50),
            reproduction_hint=ReproductionHint(description="Desc", code_snippet="code()"),
            affected_symbols=AffectedSymbols(symbols=["func"]),
            violated_invariant=ViolatedInvariant(
                invariant_type=InvariantType.DATA_FLOW,
                description="Valid description",
                violation_details="Valid details",
                invariant_location=("src/auth.py", 42),
            ),
            scope=BugScope(scope=Scope.LOCAL),
            risk_assessment=RiskAssessment(
                risk_class=RiskClass.HIGH,
                exploitability="HIGH",
                blast_radius="Module",
            ),
            hypotheses=self.create_valid_hypotheses(),
        )
        
        summary = package.summary()
        
        assert "test_001" in summary
        assert "src/auth.py" in summary
        assert "HIGH" in summary
        assert "DATA_FLOW" in summary
        assert f"{package.evidence_score:.2f}" in summary


class TestEvidencePackageBuilder:
    """Tests für EvidencePackageBuilder."""

    def test_builder_complete_package(self):
        """Test building complete package with builder."""
        builder = EvidencePackageBuilder()
        
        package = (
            builder
            .with_candidate("test_001", "src/auth.py", (40, 50))
            .with_reproduction(ReproductionHint(
                description="SQL Injection",
                code_snippet="cursor.execute(f'SELECT...')",
            ))
            .with_symbols(AffectedSymbols(symbols=["handle_login"]))
            .with_invariant(ViolatedInvariant(
                invariant_type=InvariantType.DATA_FLOW,
                description="Unvalidated input reaches SQL",
                violation_details="User input to cursor.execute()",
                invariant_location=("src/auth.py", 42),
            ))
            .with_scope(BugScope(scope=Scope.LOCAL))
            .with_risk(RiskAssessment(
                risk_class=RiskClass.HIGH,
                exploitability="HIGH",
                blast_radius="Module",
            ))
            .with_hypotheses([
                Hypothesis(
                    id="h1",
                    title="SQL Injection",
                    description="Desc",
                    hypothesis_type=HypothesisType.SQL_INJECTION_USER_INPUT,
                    candidate_id="test_001",
                    confidence=0.7,
                )
            ])
            .add_confidence_factor("Strong data flow evidence")
            .build()
        )
        
        assert package.candidate_id == "test_001"
        assert package.file_path == "src/auth.py"
        assert len(package.confidence_factors) == 1

    def test_builder_missing_components(self):
        """Test that builder raises error for missing components."""
        builder = EvidencePackageBuilder()
        
        # Don't call all with_* methods
        builder.with_candidate("test_001", "src/auth.py", (40, 50))
        
        with pytest.raises(ValueError, match="Missing required components"):
            builder.build()
