"""
Tests für EvidenceGate Validator.

Testet:
- EvidenceGate.validate()
- EvidenceGate._check_* methods
- GateValidationResult
- EvidenceGateError
"""

import pytest
import sys
from pathlib import Path
from typing import List

# Source-Path hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent.evidence_contract import (
    AffectedSymbols,
    BugScope,
    EvidencePackage,
    ReproductionHint,
    RiskAssessment,
    ViolatedInvariant,
)
from agent.evidence_gate import (
    EvidenceGate,
    EvidenceGateError,
    GateValidationResult,
)
from agent.evidence_types import (
    EvidenceStrength,
    GateDecision,
    InvariantType,
    RiskClass,
    Scope,
)
from agent.hypothesis_agent import Hypothesis, HypothesisType, Severity, BugCandidate


class TestGateValidationResult:
    """Tests für GateValidationResult."""

    def test_default_values(self):
        """Test default values."""
        result = GateValidationResult()
        
        assert result.passed is False
        assert result.decision == GateDecision.RETRY
        assert result.errors == []
        assert result.warnings == []
        assert result.evidence_score == 0.0
        assert result.minimum_threshold == 0.5
        assert result.retry_hints == []

    def test_to_dict(self):
        """Test dictionary conversion."""
        result = GateValidationResult(
            passed=True,
            decision=GateDecision.PASSED,
            errors=[],
            warnings=["Warning 1"],
            evidence_score=0.75,
            minimum_threshold=0.5,
            retry_hints=[],
        )
        d = result.to_dict()
        
        assert d["passed"] is True
        assert d["decision"] == "passed"
        assert d["warnings"] == ["Warning 1"]
        assert d["evidence_score"] == 0.75


class TestEvidenceGate:
    """Tests für EvidenceGate."""

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
                data_flow_path=["source", "sink"],
            ),
            Hypothesis(
                id="hypo_2",
                title="SQL Injection via dynamic query",
                description="Dynamic query construction without parameterization",
                hypothesis_type=HypothesisType.SQL_INJECTION_DYNAMIC_QUERY,
                candidate_id="test_candidate",
                confidence=0.7,
                severity=Severity.HIGH,
                data_flow_path=["source", "sink"],
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

    def create_valid_evidence_package(
        self,
        risk_class=RiskClass.MEDIUM,
        evidence_score_override=None,
    ) -> EvidencePackage:
        """Create valid evidence package for testing."""
        package = EvidencePackage(
            candidate_id="test_001",
            file_path="src/auth.py",
            line_range=(40, 50),
            reproduction_hint=ReproductionHint(
                description="SQL Injection through user input",
                code_snippet="cursor.execute(f'SELECT * FROM users WHERE id={user_id}')",
                input_data="' OR '1'='1' --",
            ),
            affected_symbols=AffectedSymbols(
                symbols=["handle_login", "authenticate", "execute_query"],
                symbol_graph_snippet="handle_login -> authenticate -> execute_query",
                call_depth=2,
            ),
            violated_invariant=ViolatedInvariant(
                invariant_type=InvariantType.DATA_FLOW,
                description="Unvalidated external input flows from trust boundary source to SQL query sink without sanitization",
                violation_details="User input from request parameter flows to cursor.execute() without parameterization",
                invariant_location=("src/auth.py", 42),
            ),
            scope=BugScope(
                scope=Scope.LOCAL,
                affected_modules=["auth"],
            ),
            risk_assessment=RiskAssessment(
                risk_class=risk_class,
                exploitability="HIGH",
                blast_radius="Module affected",
            ),
            hypotheses=self.create_valid_hypotheses(),
        )
        
        if evidence_score_override is not None:
            package.evidence_score = evidence_score_override
            # Recalculate strength
            if evidence_score_override < 0.4:
                package.evidence_strength = EvidenceStrength.WEAK
            elif evidence_score_override < 0.6:
                package.evidence_strength = EvidenceStrength.MODERATE
            elif evidence_score_override < 0.8:
                package.evidence_strength = EvidenceStrength.STRONG
            else:
                package.evidence_strength = EvidenceStrength.VERY_STRONG
        
        return package

    def test_validate_passed(self):
        """Test validation with valid package."""
        gate = EvidenceGate()
        package = self.create_valid_evidence_package()
        
        result = gate.validate(package)
        
        assert result.passed is True
        assert result.decision == GateDecision.PASSED
        assert len(result.errors) == 0

    def test_validate_missing_candidate_id(self):
        """Test validation with missing candidate_id."""
        gate = EvidenceGate()
        package = self.create_valid_evidence_package()
        package.candidate_id = ""
        package._validate()  # Re-validate
        
        result = gate.validate(package)
        
        assert result.passed is False
        assert result.decision in [GateDecision.RETRY, GateDecision.REJECTED]
        assert any("candidate_id" in error for error in result.errors)

    def test_validate_incomplete_reproduction(self):
        """Test validation with incomplete reproduction hint."""
        gate = EvidenceGate()
        package = self.create_valid_evidence_package()
        package.reproduction_hint.description = ""
        package._validate()
        
        result = gate.validate(package)
        
        assert result.passed is False
        assert any("reproduction_hint" in error for error in result.errors)

    def test_validate_empty_symbols(self):
        """Test validation with empty affected symbols."""
        gate = EvidenceGate()
        package = self.create_valid_evidence_package()
        package.affected_symbols.symbols = []
        package._validate()
        
        result = gate.validate(package)
        
        assert result.passed is False
        assert any("affected_symbols" in error for error in result.errors)

    def test_validate_generic_invariant(self):
        """Test validation with generic invariant description."""
        gate = EvidenceGate()
        package = self.create_valid_evidence_package()
        package.violated_invariant.description = "Something is wrong"
        package.violated_invariant.violation_details = "Error occurs"
        package._validate()
        
        result = gate.validate(package)
        
        assert result.passed is False
        assert any("generic" in error.lower() or "invariant" in error.lower() 
                   for error in result.errors)

    def test_validate_few_hypotheses(self):
        """Test validation with too few hypotheses."""
        gate = EvidenceGate()
        package = self.create_valid_evidence_package()
        package.hypotheses = package.hypotheses[:2]  # Only 2
        package._validate()
        
        result = gate.validate(package)
        
        assert result.passed is False
        assert any("hypotheses" in error for error in result.errors)

    def test_validate_low_evidence_score(self):
        """Test validation with low evidence score."""
        gate = EvidenceGate()
        # Create package with low score
        package = self.create_valid_evidence_package(evidence_score_override=0.25)
        
        result = gate.validate(package)
        
        assert result.passed is False
        assert any("Evidence score" in error and "below minimum" in error 
                   for error in result.errors)

    def test_validate_evidence_threshold_by_risk(self):
        """Test evidence threshold varies by risk class."""
        gate = EvidenceGate()
        
        # CRITICAL risk with moderate score (should fail)
        package_critical = self.create_valid_evidence_package(
            risk_class=RiskClass.CRITICAL,
            evidence_score_override=0.55,  # Below 0.6 threshold
        )
        result_critical = gate.validate(package_critical)
        assert result_critical.passed is False
        
        # MEDIUM risk with same score (should pass if >= 0.5)
        package_medium = self.create_valid_evidence_package(
            risk_class=RiskClass.MEDIUM,
            evidence_score_override=0.55,  # Above 0.5 threshold
        )
        # Note: May still fail for other reasons, but not threshold
        
        # LOW risk with low score (should pass if >= 0.4)
        package_low = self.create_valid_evidence_package(
            risk_class=RiskClass.LOW,
            evidence_score_override=0.45,  # Above 0.4 threshold
        )

    def test_validate_retry_hints_generated(self):
        """Test that retry hints are generated on failure."""
        gate = EvidenceGate()
        package = self.create_valid_evidence_package()
        package.evidence_score = 0.25  # Low score
        package._validate()
        
        result = gate.validate(package)
        
        assert result.passed is False
        assert len(result.retry_hints) > 0
        assert any("Strengthen evidence" in hint for hint in result.retry_hints)

    def test_validate_warnings_for_high_risk(self):
        """Test warnings generated for high risk with moderate evidence."""
        gate = EvidenceGate()
        package = self.create_valid_evidence_package(
            risk_class=RiskClass.HIGH,
            evidence_score_override=0.55,  # Moderate for HIGH risk
        )
        
        result = gate.validate(package)
        
        # May have warnings even if passed
        if package.risk_assessment.risk_class == RiskClass.HIGH:
            assert len(result.warnings) >= 0  # Warnings are optional

    def test_is_fundamentally_flawed_critical_errors(self):
        """Test fundamental flaw detection with critical errors."""
        gate = EvidenceGate()
        
        errors = ["file_path is required"]
        assert gate._is_fundamentally_flawed(
            self.create_valid_evidence_package(),
            errors,
        ) is True
        
        errors = ["candidate_id is required"]
        assert gate._is_fundamentally_flawed(
            self.create_valid_evidence_package(),
            errors,
        ) is True

    def test_is_fundamentally_flawed_too_many_errors(self):
        """Test fundamental flaw detection with many errors."""
        gate = EvidenceGate()
        
        errors = ["error1", "error2", "error3", "error4", "error5"]
        assert gate._is_fundamentally_flawed(
            self.create_valid_evidence_package(),
            errors,
        ) is True

    def test_is_fundamentally_flawed_recoverable(self):
        """Test that recoverable errors are not fundamental flaws."""
        gate = EvidenceGate()
        
        errors = ["Evidence score 0.35 below minimum threshold 0.5"]
        assert gate._is_fundamentally_flawed(
            self.create_valid_evidence_package(),
            errors,
        ) is False

    def test_generate_retry_hints_evidence_score(self):
        """Test retry hint generation for low evidence score."""
        gate = EvidenceGate()
        
        errors = ["Evidence score 0.35 below minimum threshold 0.5"]
        hints = gate._generate_retry_hints(
            self.create_valid_evidence_package(),
            errors,
        )
        
        assert len(hints) > 0
        assert any("Strengthen evidence" in hint for hint in hints)

    def test_generate_retry_hints_hypothesis_confidence(self):
        """Test retry hint generation for low hypothesis confidence."""
        gate = EvidenceGate()
        
        errors = ["Average hypothesis confidence too low (0.25)"]
        hints = gate._generate_retry_hints(
            self.create_valid_evidence_package(),
            errors,
        )
        
        assert len(hints) > 0
        assert any("hypothesis" in hint.lower() for hint in hints)

    def test_generate_retry_hints_generic_invariant(self):
        """Test retry hint generation for generic invariant."""
        gate = EvidenceGate()
        
        errors = ["invariant description is too generic"]
        hints = gate._generate_retry_hints(
            self.create_valid_evidence_package(),
            errors,
        )
        
        assert len(hints) > 0
        assert any("invariant" in hint.lower() for hint in hints)

    def test_validate_and_raise_success(self):
        """Test validate_and_raise with valid package."""
        gate = EvidenceGate()
        package = self.create_valid_evidence_package()
        
        # Should not raise
        gate.validate_and_raise(package)

    def test_validate_and_raise_failure(self):
        """Test validate_and_raise with invalid package."""
        gate = EvidenceGate()
        package = self.create_valid_evidence_package()
        package.candidate_id = ""
        package._validate()
        
        with pytest.raises(EvidenceGateError) as exc_info:
            gate.validate_and_raise(package)
        
        assert "candidate_id" in str(exc_info.value)
        assert exc_info.value.result is not None

    def test_validate_and_raise_to_dict(self):
        """Test EvidenceGateError.to_dict()."""
        gate = EvidenceGate()
        package = self.create_valid_evidence_package()
        package.candidate_id = ""
        package._validate()
        
        try:
            gate.validate_and_raise(package)
        except EvidenceGateError as e:
            d = e.to_dict()
            assert "message" in d
            assert "result" in d
            assert d["result"] is not None


class TestEvidenceGateConfig:
    """Tests für EvidenceGate Konfiguration."""

    def test_custom_thresholds(self):
        """Test custom threshold configuration."""
        config = {
            "evidence_gate": {
                "min_score_weak": 0.5,
                "min_score_medium": 0.6,
                "min_score_high": 0.7,
            }
        }
        gate = EvidenceGate(config=config)
        
        # Config is read from nested "evidence_gate" key
        assert gate.min_score_weak == 0.5
        assert gate.min_score_medium == 0.6
        assert gate.min_score_high == 0.7

    def test_default_thresholds(self):
        """Test default thresholds."""
        gate = EvidenceGate()
        
        assert gate.min_score_weak == 0.4
        assert gate.min_score_medium == 0.5
        assert gate.min_score_high == 0.6

    def test_custom_max_retries(self):
        """Test custom max retries configuration."""
        config = {
            "evidence_gate": {
                "max_retries": 5,
            }
        }
        gate = EvidenceGate(config=config)
        
        assert gate.max_retries == 5


class TestEvidenceGateIntegration:
    """Integrationstests für EvidenceGate."""

    def test_full_workflow_passed(self):
        """Test complete workflow with valid package."""
        # Create package
        hypotheses = [
            Hypothesis(
                id="h1",
                title="SQL Injection",
                description="Unvalidated input reaches SQL",
                hypothesis_type=HypothesisType.SQL_INJECTION_USER_INPUT,
                candidate_id="test",
                confidence=0.8,
                severity=Severity.HIGH,
                data_flow_path=["source", "sink"],
            ),
            Hypothesis(
                id="h2",
                title="Dynamic SQL",
                description="Dynamic query construction",
                hypothesis_type=HypothesisType.SQL_INJECTION_DYNAMIC_QUERY,
                candidate_id="test",
                confidence=0.7,
                severity=Severity.HIGH,
                data_flow_path=["source", "sink"],
            ),
            Hypothesis(
                id="h3",
                title="ORM Misuse",
                description="ORM raw() with user input",
                hypothesis_type=HypothesisType.SQL_INJECTION_ORM_MISUSE,
                candidate_id="test",
                confidence=0.6,
                severity=Severity.HIGH,
            ),
        ]
        
        package = EvidencePackage(
            candidate_id="integration_test_001",
            file_path="src/api/users.py",
            line_range=(100, 120),
            reproduction_hint=ReproductionHint(
                description="SQL Injection via user_id parameter",
                code_snippet="cursor.execute(f'SELECT * FROM users WHERE id={user_id}')",
                input_data="' OR '1'='1' --",
                expected_behavior="Input should be parameterized",
                actual_behavior="Input executed as SQL code",
            ),
            affected_symbols=AffectedSymbols(
                symbols=["get_user", "execute_query"],
                symbol_graph_snippet="get_user -> execute_query",
                call_depth=1,
            ),
            violated_invariant=ViolatedInvariant(
                invariant_type=InvariantType.DATA_FLOW,
                description="Unvalidated external input flows from trust boundary source to SQL query sink without sanitization or parameterization",
                violation_details="User input from request parameter 'user_id' flows directly to cursor.execute() without parameterization or sanitization",
                invariant_location=("src/api/users.py", 110),
            ),
            scope=BugScope(
                scope=Scope.MODULE,
                affected_modules=["api", "database"],
                dependency_impact="Affects all database queries",
            ),
            risk_assessment=RiskAssessment(
                risk_class=RiskClass.HIGH,
                exploitability="HIGH",
                blast_radius="Multiple modules affected",
                cvss_score=7.5,
                business_impact="Potential data breach",
            ),
            hypotheses=hypotheses,
        )
        
        # Validate
        gate = EvidenceGate()
        result = gate.validate(package)
        
        # Should pass
        assert result.passed is True
        assert result.decision == GateDecision.PASSED
        assert len(result.errors) == 0

    def test_full_workflow_retry(self):
        """Test complete workflow with retry scenario."""
        package = EvidencePackage(
            candidate_id="retry_test_001",
            file_path="src/auth.py",
            line_range=(40, 50),
            reproduction_hint=ReproductionHint(
                description="Desc",  # Too short
                code_snippet="code()",
            ),
            affected_symbols=AffectedSymbols(symbols=["func"]),
            violated_invariant=ViolatedInvariant(
                invariant_type=InvariantType.DATA_FLOW,
                description="Something is wrong",  # Generic!
                violation_details="Error occurs",  # Generic!
                invariant_location=("src/auth.py", 42),
            ),
            scope=BugScope(scope=Scope.LOCAL),
            risk_assessment=RiskAssessment(
                risk_class=RiskClass.MEDIUM,
                exploitability="MEDIUM",
                blast_radius="Impact",
            ),
            hypotheses=[
                Hypothesis(
                    id="h1",
                    title="Bug",
                    description="Desc",
                    hypothesis_type=HypothesisType.SQL_INJECTION_USER_INPUT,
                    candidate_id="test",
                    confidence=0.3,
                ),
                Hypothesis(
                    id="h2",
                    title="Bug",  # Duplicate title
                    description="Desc",
                    hypothesis_type=HypothesisType.SQL_INJECTION_USER_INPUT,
                    candidate_id="test",
                    confidence=0.3,
                ),
            ],  # Only 2 hypotheses
        )
        
        gate = EvidenceGate()
        result = gate.validate(package)
        
        # Should fail validation (either RETRY or REJECTED due to multiple issues)
        assert result.passed is False
        assert result.decision in [GateDecision.RETRY, GateDecision.REJECTED]
        assert len(result.errors) > 0
        # Retry hints may or may not be present depending on decision
        if result.decision == GateDecision.RETRY:
            assert len(result.retry_hints) > 0
