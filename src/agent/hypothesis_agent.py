"""
Hypothesis Agent for GlitchHunter.

Generates and ranks hypotheses for bug candidates using CogniGent-style reasoning.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from analysis.cfg_builder import ControlFlowGraph
from analysis.dfg_builder import DataFlowGraph, TaintPath
from core.logging_config import get_logger

from agent.evidence_contract import (
    AffectedSymbols,
    BugScope,
    EvidencePackage,
    EvidencePackageBuilder,
    ReproductionHint,
    RiskAssessment,
    ViolatedInvariant,
)
from agent.evidence_types import InvariantType, RiskClass, Scope

logger = get_logger(__name__)


class HypothesisType(str, Enum):
    """Types of bug hypotheses."""

    # SQL Injection
    SQL_INJECTION_USER_INPUT = "sql_injection_user_input"
    SQL_INJECTION_PREPARED_BYPASS = "sql_injection_prepared_bypass"
    SQL_INJECTION_ORM_MISUSE = "sql_injection_orm_misuse"
    SQL_INJECTION_DYNAMIC_QUERY = "sql_injection_dynamic_query"
    SQL_INJECTION_SECOND_ORDER = "sql_injection_second_order"

    # Broken Authentication
    AUTH_TOKEN_MISSING = "auth_token_missing"
    AUTH_SESSION_FIXATION = "auth_session_fixation"
    AUTH_JWT_SIGNATURE = "auth_jwt_signature"
    AUTH_PASSWORD_NOT_HASHED = "auth_password_not_hashed"
    AUTH_BYPASS_PARAMETER = "auth_bypass_parameter"

    # Race Condition
    RACE_CHECK_THEN_ACT = "race_check_then_act"
    RACE_NON_ATOMIC = "race_non_atomic"
    RACE_LAZY_INIT = "race_lazy_initialization"
    RACE_DOUBLE_CHECKED_LOCK = "race_double_checked_lock"
    RACE_CONCURRENT_MODIFICATION = "race_concurrent_modification"

    # Other vulnerability types
    XSS_REFLECTED = "xss_reflected"
    XSS_STORED = "xss_stored"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    FILE_WRITE_UNVALIDATED = "file_write_unvalidated"


class Severity(str, Enum):
    """Severity levels for hypotheses."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


@dataclass
class Hypothesis:
    """
    Represents a bug hypothesis.

    Attributes:
        id: Unique identifier
        title: Short descriptive title
        description: Detailed description
        hypothesis_type: Type of hypothesis
        candidate_id: ID of the bug candidate
        affected_symbols: List of affected code symbols
        data_flow_path: Optional data flow path
        confidence: Confidence score (0.0-1.0)
        evidence_required: List of evidence needed to confirm
        severity: Severity level
    """

    id: str
    title: str
    description: str
    hypothesis_type: HypothesisType
    candidate_id: str
    affected_symbols: List[str] = field(default_factory=list)
    data_flow_path: Optional[List[str]] = None
    confidence: float = 0.5
    evidence_required: List[str] = field(default_factory=list)
    severity: Severity = Severity.MEDIUM

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "hypothesis_type": self.hypothesis_type.value,
            "candidate_id": self.candidate_id,
            "affected_symbols": self.affected_symbols,
            "data_flow_path": self.data_flow_path,
            "confidence": self.confidence,
            "evidence_required": self.evidence_required,
            "severity": self.severity.value,
        }


@dataclass
class BugCandidate:
    """
    Represents a bug candidate for hypothesis generation.

    Attributes:
        id: Unique identifier
        file_path: Source file path
        line: Line number
        symbol_name: Name of the symbol
        bug_type: Type of bug
        description: Bug description
        severity: Initial severity assessment
    """

    id: str
    file_path: str
    line: int
    symbol_name: str
    bug_type: str
    description: str
    severity: Severity = Severity.MEDIUM


class HypothesisAgent:
    """
    Hypothesis Agent for bug analysis.

    Generates 3-5 hypotheses per bug candidate using pattern-based
    reasoning and data-flow analysis.
    """

    # SQL Injection hypothesis templates
    SQL_INJECTION_HYPOTHESES = [
        {
            "type": HypothesisType.SQL_INJECTION_USER_INPUT,
            "title": "User input reaches SQL query without sanitization",
            "description": (
                "Untrusted user input flows directly into a SQL query constructor "
                "without proper sanitization or parameterization."
            ),
            "evidence_required": [
                "Direct data flow from input source to SQL execution",
                "Absence of parameterized query usage",
                "String concatenation in query construction",
            ],
            "severity": Severity.CRITICAL,
        },
        {
            "type": HypothesisType.SQL_INJECTION_PREPARED_BYPASS,
            "title": "Prepared statement is bypassed",
            "description": (
                "A prepared statement exists but is bypassed through dynamic "
                "query construction or improper parameter binding."
            ),
            "evidence_required": [
                "Prepared statement usage in code",
                "Dynamic query modification",
                "Parameter binding bypass",
            ],
            "severity": Severity.HIGH,
        },
        {
            "type": HypothesisType.SQL_INJECTION_ORM_MISUSE,
            "title": "ORM is misused",
            "description": (
                "ORM methods are misused, allowing raw SQL injection through "
                "unsafe methods like raw() or execute()."
            ),
            "evidence_required": [
                "ORM usage (SQLAlchemy, Django ORM, etc.)",
                "Raw SQL method calls",
                "User input in raw queries",
            ],
            "severity": Severity.HIGH,
        },
        {
            "type": HypothesisType.SQL_INJECTION_DYNAMIC_QUERY,
            "title": "Dynamic query construction",
            "description": (
                "SQL queries are constructed dynamically using string "
                "concatenation or formatting with user input."
            ),
            "evidence_required": [
                "String formatting in SQL context",
                "f-string or .format() usage",
                "User-controlled variables in query",
            ],
            "severity": Severity.CRITICAL,
        },
        {
            "type": HypothesisType.SQL_INJECTION_SECOND_ORDER,
            "title": "Second-order injection",
            "description": (
                "User input is stored and later used in a SQL query without "
                "proper sanitization, enabling second-order injection."
            ),
            "evidence_required": [
                "User input stored in database",
                "Retrieved data used in query",
                "Missing sanitization on retrieval",
            ],
            "severity": Severity.HIGH,
        },
    ]

    # Authentication bypass hypothesis templates
    AUTH_BYPASS_HYPOTHESES = [
        {
            "type": HypothesisType.AUTH_TOKEN_MISSING,
            "title": "Token validation missing",
            "description": (
                "Authentication token validation is missing or can be bypassed "
                "by omitting the token or providing an empty value."
            ),
            "evidence_required": [
                "Authentication check in code path",
                "Missing token validation",
                "Unauthenticated access possible",
            ],
            "severity": Severity.CRITICAL,
        },
        {
            "type": HypothesisType.AUTH_SESSION_FIXATION,
            "title": "Session fixation possible",
            "description": (
                "Session ID is not regenerated after authentication, allowing "
                "session fixation attacks."
            ),
            "evidence_required": [
                "Session usage in authentication",
                "Missing session regeneration",
                "Pre-authentication session usage",
            ],
            "severity": Severity.HIGH,
        },
        {
            "type": HypothesisType.AUTH_JWT_SIGNATURE,
            "title": "JWT signature not verified",
            "description": (
                "JWT token signature verification is missing or disabled, "
                "allowing token forgery."
            ),
            "evidence_required": [
                "JWT token usage",
                "Missing signature verification",
                "Algorithm 'none' accepted",
            ],
            "severity": Severity.CRITICAL,
        },
        {
            "type": HypothesisType.AUTH_PASSWORD_NOT_HASHED,
            "title": "Password not hashed",
            "description": (
                "Passwords are stored or compared without proper hashing, "
                "exposing credentials."
            ),
            "evidence_required": [
                "Password comparison in code",
                "Missing hash function",
                "Plain text storage",
            ],
            "severity": Severity.CRITICAL,
        },
        {
            "type": HypothesisType.AUTH_BYPASS_PARAMETER,
            "title": "Auth bypass via parameter manipulation",
            "description": (
                "Authentication can be bypassed by manipulating request "
                "parameters (e.g., admin=false -> admin=true)."
            ),
            "evidence_required": [
                "User-controlled auth parameters",
                "Boolean or role checks",
                "Missing server-side validation",
            ],
            "severity": Severity.HIGH,
        },
    ]

    # Race condition hypothesis templates
    RACE_CONDITION_HYPOTHESES = [
        {
            "type": HypothesisType.RACE_CHECK_THEN_ACT,
            "title": "Check-then-act without synchronization",
            "description": (
                "A condition is checked and then acted upon without atomic "
                "synchronization, allowing race conditions."
            ),
            "evidence_required": [
                "Conditional check followed by action",
                "Shared resource access",
                "Missing lock or atomic operation",
            ],
            "severity": Severity.HIGH,
        },
        {
            "type": HypothesisType.RACE_NON_ATOMIC,
            "title": "Non-atomic compound action",
            "description": (
                "A compound action (read-modify-write) is not atomic, allowing "
                "concurrent modification."
            ),
            "evidence_required": [
                "Read-modify-write pattern",
                "Shared variable access",
                "Missing atomic operations",
            ],
            "severity": Severity.HIGH,
        },
        {
            "type": HypothesisType.RACE_LAZY_INIT,
            "title": "Lazy initialization race",
            "description": (
                "Lazy initialization of a shared resource is not thread-safe, "
                "allowing multiple initializations."
            ),
            "evidence_required": [
                "Lazy initialization pattern",
                "Null check before init",
                "Missing double-checked locking",
            ],
            "severity": Severity.MEDIUM,
        },
        {
            "type": HypothesisType.RACE_DOUBLE_CHECKED_LOCK,
            "title": "Double-checked locking broken",
            "description": (
                "Double-checked locking pattern is implemented incorrectly, "
                "allowing race conditions in Python."
            ),
            "evidence_required": [
                "Double-checked locking pattern",
                "Missing volatile/memory barrier",
                "Python GIL reliance",
            ],
            "severity": Severity.MEDIUM,
        },
        {
            "type": HypothesisType.RACE_CONCURRENT_MODIFICATION,
            "title": "Concurrent collection modification",
            "description": (
                "A collection is modified while being iterated, or multiple "
                "threads modify it concurrently without synchronization."
            ),
            "evidence_required": [
                "Collection iteration",
                "Concurrent modification",
                "Missing thread-safe collection",
            ],
            "severity": Severity.MEDIUM,
        },
    ]

    def __init__(self, llm_client: Optional[Any] = None) -> None:
        """
        Initialize the Hypothesis Agent.

        Args:
            llm_client: Optional LLM client for enhanced hypothesis generation
        """
        self._llm_client = llm_client
        self._generated_hypotheses: List[Hypothesis] = []

    def generate_hypotheses(
        self,
        candidate: BugCandidate,
        data_flow_graph: DataFlowGraph,
        cfg: Optional[ControlFlowGraph] = None,
    ) -> List[Hypothesis]:
        """
        Generate hypotheses for a bug candidate.

        Args:
            candidate: Bug candidate to analyze
            data_flow_graph: Data-flow graph for analysis
            cfg: Optional control-flow graph

        Returns:
            List of generated hypotheses, ranked by confidence
        """
        logger.info(f"Generating hypotheses for candidate: {candidate.id}")

        hypotheses: List[Hypothesis] = []

        # Generate based on bug type
        if "sql" in candidate.bug_type.lower() or "injection" in candidate.bug_type.lower():
            hypotheses.extend(self.generate_for_injection(candidate, data_flow_graph))
        elif "auth" in candidate.bug_type.lower() or "bypass" in candidate.bug_type.lower():
            hypotheses.extend(self.generate_for_auth_bypass(candidate, data_flow_graph))
        elif "race" in candidate.bug_type.lower() or "concurrent" in candidate.bug_type.lower():
            hypotheses.extend(self.generate_for_race_condition(candidate, data_flow_graph))
        else:
            # Generic hypothesis generation
            hypotheses.extend(self._generate_generic_hypotheses(candidate, data_flow_graph))

        # Rank hypotheses
        ranked = self.rank_hypotheses(hypotheses)

        # Store for later use
        self._generated_hypotheses.extend(ranked)

        logger.info(f"Generated {len(ranked)} hypotheses for candidate {candidate.id}")

        return ranked

    def generate_for_injection(
        self,
        candidate: BugCandidate,
        data_flow_graph: DataFlowGraph,
        max_hypotheses: int = 5,
    ) -> List[Hypothesis]:
        """
        Generate SQL injection hypotheses.

        Args:
            candidate: Bug candidate
            data_flow_graph: Data-flow graph
            max_hypotheses: Maximum number of hypotheses to generate

        Returns:
            List of injection hypotheses
        """
        hypotheses: List[Hypothesis] = []

        # Analyze taint paths
        taint_paths = self._analyze_taint_paths(data_flow_graph, candidate)

        for template in self.SQL_INJECTION_HYPOTHESES[:max_hypotheses]:
            hypothesis = Hypothesis(
                id=f"hypo_{uuid.uuid4().hex[:8]}",
                title=template["title"],
                description=self._customize_description(
                    template["description"], candidate, taint_paths
                ),
                hypothesis_type=template["type"],
                candidate_id=candidate.id,
                affected_symbols=[candidate.symbol_name],
                data_flow_path=taint_paths[0].path if taint_paths else None,
                confidence=self._calculate_confidence(template["type"], taint_paths),
                evidence_required=template["evidence_required"].copy(),
                severity=template["severity"],
            )
            hypotheses.append(hypothesis)

        return hypotheses

    def generate_for_auth_bypass(
        self,
        candidate: BugCandidate,
        data_flow_graph: DataFlowGraph,
        max_hypotheses: int = 5,
    ) -> List[Hypothesis]:
        """
        Generate authentication bypass hypotheses.

        Args:
            candidate: Bug candidate
            data_flow_graph: Data-flow graph
            max_hypotheses: Maximum number of hypotheses to generate

        Returns:
            List of auth bypass hypotheses
        """
        hypotheses: List[Hypothesis] = []

        # Analyze taint paths
        taint_paths = self._analyze_taint_paths(data_flow_graph, candidate)

        for template in self.AUTH_BYPASS_HYPOTHESES[:max_hypotheses]:
            hypothesis = Hypothesis(
                id=f"hypo_{uuid.uuid4().hex[:8]}",
                title=template["title"],
                description=self._customize_description(
                    template["description"], candidate, taint_paths
                ),
                hypothesis_type=template["type"],
                candidate_id=candidate.id,
                affected_symbols=[candidate.symbol_name],
                data_flow_path=taint_paths[0].path if taint_paths else None,
                confidence=self._calculate_confidence(template["type"], taint_paths),
                evidence_required=template["evidence_required"].copy(),
                severity=template["severity"],
            )
            hypotheses.append(hypothesis)

        return hypotheses

    def generate_for_race_condition(
        self,
        candidate: BugCandidate,
        data_flow_graph: DataFlowGraph,
        max_hypotheses: int = 5,
    ) -> List[Hypothesis]:
        """
        Generate race condition hypotheses.

        Args:
            candidate: Bug candidate
            data_flow_graph: Data-flow graph
            max_hypotheses: Maximum number of hypotheses to generate

        Returns:
            List of race condition hypotheses
        """
        hypotheses: List[Hypothesis] = []

        # Note: Race condition detection would require more advanced analysis
        # For now, we generate hypotheses based on patterns
        # race_conditions = data_flow_graph.find_race_conditions()

        for template in self.RACE_CONDITION_HYPOTHESES[:max_hypotheses]:
            hypothesis = Hypothesis(
                id=f"hypo_{uuid.uuid4().hex[:8]}",
                title=template["title"],
                description=self._customize_description(
                    template["description"], candidate, []
                ),
                hypothesis_type=template["type"],
                candidate_id=candidate.id,
                affected_symbols=[candidate.symbol_name],
                confidence=self._calculate_confidence(template["type"], []),
                evidence_required=template["evidence_required"].copy(),
                severity=template["severity"],
            )
            hypotheses.append(hypothesis)

        return hypotheses

    def rank_hypotheses(self, hypotheses: List[Hypothesis]) -> List[Hypothesis]:
        """
        Rank hypotheses by confidence and severity.

        Args:
            hypotheses: List of hypotheses to rank

        Returns:
            Ranked list of hypotheses
        """
        # Sort by confidence (descending), then severity
        severity_order = {
            Severity.CRITICAL: 4,
            Severity.HIGH: 3,
            Severity.MEDIUM: 2,
            Severity.LOW: 1,
        }

        ranked = sorted(
            hypotheses,
            key=lambda h: (h.confidence, severity_order[h.severity]),
            reverse=True,
        )

        logger.debug(f"Ranked {len(hypotheses)} hypotheses")

        return ranked

    def _analyze_taint_paths(
        self,
        data_flow_graph: DataFlowGraph,
        candidate: BugCandidate,
    ) -> List[TaintPath]:
        """
        Analyze taint paths for a candidate.

        Args:
            data_flow_graph: Data-flow graph
            candidate: Bug candidate

        Returns:
            List of relevant taint paths
        """
        taint_paths: List[TaintPath] = []

        # Find taint sources near the candidate
        for source in data_flow_graph.taint_sources:
            paths = data_flow_graph.track_taint(source.node)
            taint_paths.extend(paths)

        return taint_paths

    def _customize_description(
        self,
        base_description: str,
        candidate: BugCandidate,
        taint_paths: List[TaintPath],
    ) -> str:
        """
        Customize hypothesis description based on candidate context.

        Args:
            base_description: Base description template
            candidate: Bug candidate
            taint_paths: Relevant taint paths

        Returns:
            Customized description
        """
        description = base_description
        description += f"\n\nLocation: {candidate.file_path}:{candidate.line}"
        description += f"\nSymbol: {candidate.symbol_name}"

        if taint_paths:
            description += f"\nTaint path length: {taint_paths[0].length}"

        return description

    def _calculate_confidence(
        self,
        hypothesis_type: HypothesisType,
        taint_paths: List[TaintPath],
    ) -> float:
        """
        Calculate confidence score for a hypothesis.

        Args:
            hypothesis_type: Type of hypothesis
            taint_paths: Relevant taint paths

        Returns:
            Confidence score between 0.0 and 1.0
        """
        base_confidence = 0.5

        # Boost confidence based on taint path evidence
        if taint_paths:
            # More taint paths = higher confidence
            path_bonus = min(0.3, len(taint_paths) * 0.1)
            base_confidence += path_bonus

            # Shorter paths = higher confidence
            shortest_path = min(len(p.path) for p in taint_paths)
            if shortest_path <= 3:
                base_confidence += 0.1
            elif shortest_path <= 5:
                base_confidence += 0.05

        # Type-specific adjustments
        high_confidence_types = {
            HypothesisType.SQL_INJECTION_USER_INPUT,
            HypothesisType.SQL_INJECTION_DYNAMIC_QUERY,
            HypothesisType.AUTH_JWT_SIGNATURE,
            HypothesisType.AUTH_PASSWORD_NOT_HASHED,
        }

        if hypothesis_type in high_confidence_types:
            base_confidence = min(1.0, base_confidence + 0.1)

        return min(1.0, base_confidence)

    def _generate_generic_hypotheses(
        self,
        candidate: BugCandidate,
        data_flow_graph: DataFlowGraph,
    ) -> List[Hypothesis]:
        """
        Generate generic hypotheses when bug type is unknown.

        Args:
            candidate: Bug candidate
            data_flow_graph: Data-flow graph

        Returns:
            List of generic hypotheses
        """
        hypotheses: List[Hypothesis] = []

        # Create a generic hypothesis based on available data
        taint_paths = self._analyze_taint_paths(data_flow_graph, candidate)

        if taint_paths:
            # Data flow vulnerability
            hypothesis = Hypothesis(
                id=f"hypo_{uuid.uuid4().hex[:8]}",
                title="Potential data flow vulnerability",
                description=(
                    f"Analysis indicates a potential vulnerability in the data flow "
                    f"at {candidate.file_path}:{candidate.line}. "
                    f"Untrusted data may reach a sensitive sink."
                ),
                hypothesis_type=HypothesisType.SQL_INJECTION_USER_INPUT,
                candidate_id=candidate.id,
                affected_symbols=[candidate.symbol_name],
                data_flow_path=taint_paths[0].path if taint_paths else None,
                confidence=0.4,
                evidence_required=[
                    "Verify data flow path",
                    "Check for sanitization",
                    "Review sink usage",
                ],
                severity=Severity.MEDIUM,
            )
            hypotheses.append(hypothesis)

        # Add a generic control-flow hypothesis
        hypothesis = Hypothesis(
            id=f"hypo_{uuid.uuid4().hex[:8]}",
            title="Potential control-flow vulnerability",
            description=(
                f"Control-flow analysis indicates a potential issue at "
                f"{candidate.file_path}:{candidate.line}. "
                f"Execution path may be manipulated."
            ),
            hypothesis_type=HypothesisType.AUTH_BYPASS_PARAMETER,
            candidate_id=candidate.id,
            affected_symbols=[candidate.symbol_name],
            confidence=0.3,
            evidence_required=[
                "Review control flow",
                "Check branch conditions",
                "Verify input validation",
            ],
            severity=Severity.MEDIUM,
        )
        hypotheses.append(hypothesis)

        return hypotheses

    def get_generated_hypotheses(self) -> List[Hypothesis]:
        """
        Get all generated hypotheses.

        Returns:
            List of all generated hypotheses
        """
        return self._generated_hypotheses.copy()

    def clear_hypotheses(self) -> None:
        """Clear all generated hypotheses."""
        self._generated_hypotheses = []
        logger.debug("Hypotheses cleared")

    def generate_evidence_package(
        self,
        candidate: BugCandidate,
        data_flow_graph: DataFlowGraph,
        cfg: Optional[ControlFlowGraph] = None,
    ) -> EvidencePackage:
        """
        Generate complete evidence package for a bug candidate.
        
        This method creates the mandatory evidence package that must be
        validated by EvidenceGate before any automatic fix can proceed.
        
        Args:
            candidate: Bug candidate to analyze
            data_flow_graph: Data-flow graph for analysis
            cfg: Optional control-flow graph
            
        Returns:
            Complete EvidencePackage instance
        """
        logger.info(f"Generating evidence package for candidate: {candidate.id}")
        
        # 1. Generate hypotheses first (already implemented)
        hypotheses = self.generate_hypotheses(candidate, data_flow_graph, cfg)
        
        # 2. Extract affected symbols from symbol graph
        affected_symbols = self._extract_affected_symbols(candidate, data_flow_graph)
        
        # 3. Identify violated invariant
        violated_invariant = self._identify_violated_invariant(
            candidate, data_flow_graph, cfg, hypotheses
        )
        
        # 4. Determine scope
        scope = self._determine_scope(candidate, data_flow_graph, affected_symbols)
        
        # 5. Assess risk
        risk_assessment = self._assess_risk(candidate, hypotheses, scope)
        
        # 6. Generate reproduction hint
        reproduction_hint = self._generate_reproduction_hint(
            candidate, data_flow_graph, hypotheses
        )
        
        # 7. Build evidence package using builder
        builder = EvidencePackageBuilder()
        package = (
            builder
            .with_candidate(
                candidate_id=candidate.id,
                file_path=candidate.file_path,
                line_range=(candidate.line, candidate.line + 5),  # Approximate range
            )
            .with_reproduction(reproduction_hint)
            .with_symbols(affected_symbols)
            .with_invariant(violated_invariant)
            .with_scope(scope)
            .with_risk(risk_assessment)
            .with_hypotheses(hypotheses)
            .build()
        )
        
        logger.info(
            f"Evidence package generated for {candidate.id}: "
            f"score={package.evidence_score:.2f}, strength={package.evidence_strength.value}"
        )
        
        return package

    def _extract_affected_symbols(
        self,
        candidate: BugCandidate,
        data_flow_graph: DataFlowGraph,
    ) -> AffectedSymbols:
        """
        Extract affected symbols from data-flow graph.
        
        Args:
            candidate: Bug candidate
            data_flow_graph: Data-flow graph
            
        Returns:
            AffectedSymbols with identified symbols
        """
        symbols = [candidate.symbol_name]
        
        # Find symbols connected via data flow
        try:
            # Get nodes near the candidate location
            for node_id, node_data in data_flow_graph.graph.nodes(data=True):
                if node_data.get("file_path") == candidate.file_path:
                    node_line = node_data.get("line", 0)
                    # Symbols within ±10 lines
                    if abs(node_line - candidate.line) <= 10:
                        symbol = node_data.get("symbol")
                        if symbol and symbol not in symbols:
                            symbols.append(symbol)
        except Exception as e:
            logger.warning(f"Error extracting symbols from DFG: {e}")
        
        # Calculate call depth (simplified)
        call_depth = 0
        try:
            # Count hops from entry point (simplified heuristic)
            call_depth = len(symbols)  # Rough estimate
        except Exception:
            pass
        
        # Determine if any symbol is an entry point
        is_entry_point = any(
            symbol.startswith(("handle_", "api_", "route_", "endpoint_"))
            for symbol in symbols
        )
        
        return AffectedSymbols(
            symbols=symbols,
            symbol_graph_snippet=self._generate_symbol_graph_snippet(symbols, data_flow_graph),
            call_depth=call_depth,
            is_entry_point=is_entry_point,
        )

    def _generate_symbol_graph_snippet(
        self,
        symbols: List[str],
        data_flow_graph: DataFlowGraph,
    ) -> str:
        """
        Generate text snippet of symbol graph.
        
        Args:
            symbols: List of symbols
            data_flow_graph: Data-flow graph
            
        Returns:
            Text representation of symbol relationships
        """
        lines = []
        lines.append("Symbol Graph Snippet:")
        lines.append("=" * 40)
        
        for symbol in symbols[:5]:  # Limit to 5 symbols
            lines.append(f"  • {symbol}")
        
        lines.append("=" * 40)
        
        return "\n".join(lines)

    def _identify_violated_invariant(
        self,
        candidate: BugCandidate,
        data_flow_graph: DataFlowGraph,
        cfg: Optional[ControlFlowGraph],
        hypotheses: List[Hypothesis],
    ) -> ViolatedInvariant:
        """
        Identify the violated invariant based on hypotheses.
        
        Args:
            candidate: Bug candidate
            data_flow_graph: Data-flow graph
            cfg: Optional control-flow graph
            hypotheses: Generated hypotheses
            
        Returns:
            ViolatedInvariant describing the violation
        """
        # Map hypothesis type to invariant type
        type_to_invariant = {
            HypothesisType.SQL_INJECTION_USER_INPUT: InvariantType.DATA_FLOW,
            HypothesisType.SQL_INJECTION_DYNAMIC_QUERY: InvariantType.DATA_FLOW,
            HypothesisType.SQL_INJECTION_ORM_MISUSE: InvariantType.DATA_FLOW,
            HypothesisType.SQL_INJECTION_PREPARED_BYPASS: InvariantType.DATA_FLOW,
            HypothesisType.SQL_INJECTION_SECOND_ORDER: InvariantType.DATA_FLOW,
            
            HypothesisType.AUTH_TOKEN_MISSING: InvariantType.CONTROL_FLOW,
            HypothesisType.AUTH_SESSION_FIXATION: InvariantType.STATE,
            HypothesisType.AUTH_JWT_SIGNATURE: InvariantType.CONTROL_FLOW,
            HypothesisType.AUTH_PASSWORD_NOT_HASHED: InvariantType.DATA_FLOW,
            HypothesisType.AUTH_BYPASS_PARAMETER: InvariantType.CONTROL_FLOW,
            
            HypothesisType.RACE_CHECK_THEN_ACT: InvariantType.TIMING,
            HypothesisType.RACE_NON_ATOMIC: InvariantType.TIMING,
            HypothesisType.RACE_LAZY_INIT: InvariantType.TIMING,
            HypothesisType.RACE_DOUBLE_CHECKED_LOCK: InvariantType.TIMING,
            HypothesisType.RACE_CONCURRENT_MODIFICATION: InvariantType.STATE,
            
            HypothesisType.XSS_REFLECTED: InvariantType.DATA_FLOW,
            HypothesisType.XSS_STORED: InvariantType.DATA_FLOW,
            HypothesisType.PATH_TRAVERSAL: InvariantType.CONTROL_FLOW,
            HypothesisType.COMMAND_INJECTION: InvariantType.DATA_FLOW,
            HypothesisType.FILE_WRITE_UNVALIDATED: InvariantType.CONTROL_FLOW,
        }
        
        # Get most common invariant type from hypotheses
        if hypotheses:
            primary_hypothesis = hypotheses[0]  # Highest confidence
            invariant_type = type_to_invariant.get(
                primary_hypothesis.hypothesis_type,
                InvariantType.DATA_FLOW,
            )
        else:
            invariant_type = InvariantType.DATA_FLOW
        
        # Generate specific description based on bug type
        description = self._generate_invariant_description(candidate, invariant_type)
        violation_details = self._generate_violation_details(candidate, data_flow_graph)
        
        return ViolatedInvariant(
            invariant_type=invariant_type,
            description=description,
            violation_details=violation_details,
            invariant_location=(candidate.file_path, candidate.line),
        )

    def _generate_invariant_description(
        self,
        candidate: BugCandidate,
        invariant_type: InvariantType,
    ) -> str:
        """
        Generate specific invariant description.
        
        Args:
            candidate: Bug candidate
            invariant_type: Type of invariant
            
        Returns:
            Specific description (not generic)
        """
        bug_type_lower = candidate.bug_type.lower()
        
        if invariant_type == InvariantType.DATA_FLOW:
            if "sql" in bug_type_lower or "injection" in bug_type_lower:
                return (
                    "Unvalidated external input flows from a trust boundary source "
                    "to a SQL query sink without proper sanitization or parameterization. "
                    "The data flow invariant requires all external input to be sanitized "
                    "before reaching sensitive sinks."
                )
            elif "xss" in bug_type_lower:
                return (
                    "Unescaped user input flows from HTTP request to HTML output "
                    "without proper encoding. The data flow invariant requires all "
                    "user input to be context-appropriately encoded before output."
                )
            else:
                return (
                    "Untrusted data flows from source to sink without validation. "
                    "The data flow invariant requires validation at trust boundaries."
                )
        
        elif invariant_type == InvariantType.CONTROL_FLOW:
            if "auth" in bug_type_lower or "bypass" in bug_type_lower:
                return (
                    "Authentication/authorization check can be bypassed through "
                    "manipulated control flow. The control flow invariant requires "
                    "all execution paths to pass through authentication checks."
                )
            elif "path" in bug_type_lower:
                return (
                    "File path validation is missing or bypassable. The control flow "
                    "invariant requires all file paths to be validated against allowed "
                    "directories before access."
                )
            else:
                return (
                    "Critical validation check can be bypassed through control flow "
                    "manipulation. The control flow invariant requires all paths to "
                    "pass through validation."
                )
        
        elif invariant_type == InvariantType.TIMING:
            return (
                "Concurrent access to shared state is not properly synchronized. "
                "The timing invariant requires atomic access to shared mutable state "
                "or proper locking mechanisms."
            )
        
        elif invariant_type == InvariantType.STATE:
            return (
                "Object or system state becomes inconsistent after operation. "
                "The state invariant requires state to remain consistent before "
                "and after method execution."
            )
        
        else:
            return (
                f"Invariant violation detected in {candidate.bug_type}. "
                "The specific invariant depends on the bug context."
            )

    def _generate_violation_details(
        self,
        candidate: BugCandidate,
        data_flow_graph: DataFlowGraph,
    ) -> str:
        """
        Generate specific violation details.
        
        Args:
            candidate: Bug candidate
            data_flow_graph: Data-flow graph
            
        Returns:
            Specific violation details
        """
        details = []
        details.append(f"Location: {candidate.file_path}:{candidate.line}")
        details.append(f"Symbol: {candidate.symbol_name}")
        
        # Add taint path info if available
        try:
            taint_paths = []
            for source in getattr(data_flow_graph, 'taint_sources', []):
                paths = data_flow_graph.track_taint(source.node)
                taint_paths.extend(paths)
            
            if taint_paths:
                shortest = min(taint_paths, key=lambda p: p.length)
                details.append(f"Taint path length: {shortest.length}")
                details.append(f"Source: {shortest.source}")
                details.append(f"Sink: {shortest.sink}")
        except Exception as e:
            logger.debug(f"Could not extract taint path: {e}")
        
        return "\n".join(details)

    def _determine_scope(
        self,
        candidate: BugCandidate,
        data_flow_graph: DataFlowGraph,
        affected_symbols: AffectedSymbols,
    ) -> BugScope:
        """
        Determine the scope of the bug.
        
        Args:
            candidate: Bug candidate
            data_flow_graph: Data-flow graph
            affected_symbols: Affected symbols
            
        Returns:
            BugScope with scope assessment
        """
        # Analyze affected modules
        affected_modules = set()
        
        # Current file's module
        try:
            from pathlib import Path
            path = Path(candidate.file_path)
            if len(path.parts) > 1:
                affected_modules.add(path.parts[-2])  # Parent directory
        except Exception:
            pass
        
        # Determine scope based on symbols and entry point
        if affected_symbols.is_entry_point:
            scope = Scope.CROSS_MODULE
        elif len(affected_symbols.symbols) > 5:
            scope = Scope.MODULE
        elif len(affected_symbols.symbols) > 10:
            scope = Scope.SYSTEM
        else:
            scope = Scope.LOCAL
        
        # Dependency impact description
        dependency_impact = "No direct dependency impact detected."
        if scope == Scope.CROSS_MODULE:
            dependency_impact = (
                "Bug affects public API, may impact downstream consumers."
            )
        
        return BugScope(
            scope=scope,
            affected_modules=list(affected_modules),
            dependency_impact=dependency_impact,
            upstream_impact=affected_symbols.is_entry_point,
            downstream_impact=scope in [Scope.CROSS_MODULE, Scope.SYSTEM],
        )

    def _assess_risk(
        self,
        candidate: BugCandidate,
        hypotheses: List[Hypothesis],
        scope: BugScope,
    ) -> RiskAssessment:
        """
        Assess risk level for the bug.
        
        Args:
            candidate: Bug candidate
            hypotheses: Generated hypotheses
            scope: Bug scope
            
        Returns:
            RiskAssessment with risk classification
        """
        # Get highest severity from hypotheses
        if hypotheses:
            max_severity = max(hypotheses, key=lambda h: h.severity).severity
        else:
            max_severity = candidate.severity
        
        # Map severity to risk class
        severity_to_risk = {
            Severity.LOW: RiskClass.LOW,
            Severity.MEDIUM: RiskClass.MEDIUM,
            Severity.HIGH: RiskClass.HIGH,
            Severity.CRITICAL: RiskClass.CRITICAL,
        }
        risk_class = severity_to_risk.get(max_severity, RiskClass.MEDIUM)
        
        # Determine exploitability
        exploitability = "MEDIUM"
        bug_type_lower = candidate.bug_type.lower()
        
        if "injection" in bug_type_lower or "bypass" in bug_type_lower:
            exploitability = "HIGH"
        elif "race" in bug_type_lower:
            exploitability = "MEDIUM"
        elif scope.scope == Scope.LOCAL:
            exploitability = "LOW"
        
        # Determine blast radius
        if scope.scope == Scope.SYSTEM:
            blast_radius = "System-wide impact possible"
        elif scope.scope == Scope.CROSS_MODULE:
            blast_radius = "Multiple modules affected"
        elif scope.scope == Scope.MODULE:
            blast_radius = "Single module affected"
        else:
            blast_radius = "Local function impact only"
        
        # Estimate CVSS score (simplified)
        cvss_map = {
            RiskClass.CRITICAL: 9.0,
            RiskClass.HIGH: 7.5,
            RiskClass.MEDIUM: 5.0,
            RiskClass.LOW: 2.5,
        }
        cvss_score = cvss_map.get(risk_class, 5.0)
        
        # Business impact
        business_impact = self._estimate_business_impact(candidate, risk_class)
        
        return RiskAssessment(
            risk_class=risk_class,
            exploitability=exploitability,
            blast_radius=blast_radius,
            cvss_score=cvss_score,
            business_impact=business_impact,
        )

    def _estimate_business_impact(
        self,
        candidate: BugCandidate,
        risk_class: RiskClass,
    ) -> str:
        """
        Estimate business impact.
        
        Args:
            candidate: Bug candidate
            risk_class: Risk classification
            
        Returns:
            Business impact description
        """
        bug_type_lower = candidate.bug_type.lower()
        
        if "sql" in bug_type_lower or "injection" in bug_type_lower:
            return "Potential data breach, regulatory compliance violation (GDPR, PCI-DSS)"
        elif "auth" in bug_type_lower:
            return "Unauthorized access to user accounts or admin functions"
        elif "race" in bug_type_lower:
            return "Data corruption or inconsistent state under load"
        elif risk_class == RiskClass.CRITICAL:
            return "Severe business impact requiring immediate response"
        elif risk_class == RiskClass.HIGH:
            return "Significant business impact requiring prompt attention"
        else:
            return "Moderate business impact, schedule for normal fix cycle"

    def _generate_reproduction_hint(
        self,
        candidate: BugCandidate,
        data_flow_graph: DataFlowGraph,
        hypotheses: List[Hypothesis],
    ) -> ReproductionHint:
        """
        Generate reproduction hint for the bug.
        
        Args:
            candidate: Bug candidate
            data_flow_graph: Data-flow graph
            hypotheses: Generated hypotheses
            
        Returns:
            ReproductionHint with reproduction details
        """
        # Generate minimal code snippet
        code_snippet = self._generate_minimal_code_snippet(candidate)
        
        # Generate test input based on bug type
        input_data = self._generate_test_input(candidate, hypotheses)
        
        # Expected vs actual behavior
        expected_behavior = self._describe_expected_behavior(candidate)
        actual_behavior = self._describe_actual_behavior(candidate)
        
        # Description
        description = (
            f"To reproduce {candidate.bug_type} in {candidate.symbol_name}: "
            f"Provide malicious input that exploits the vulnerability. "
            f"See code snippet for the vulnerable location."
        )
        
        return ReproductionHint(
            description=description,
            code_snippet=code_snippet,
            input_data=input_data,
            expected_behavior=expected_behavior,
            actual_behavior=actual_behavior,
        )

    def _generate_minimal_code_snippet(self, candidate: BugCandidate) -> str:
        """
        Generate minimal code snippet showing the bug.
        
        Args:
            candidate: Bug candidate
            
        Returns:
            Code snippet
        """
        return (
            f"# Vulnerable code location\n"
            f"# File: {candidate.file_path}\n"
            f"# Line: {candidate.line}\n"
            f"# Function: {candidate.symbol_name}\n"
            f"# Bug Type: {candidate.bug_type}\n"
            f"# Description: {candidate.description}"
        )

    def _generate_test_input(
        self,
        candidate: BugCandidate,
        hypotheses: List[Hypothesis],
    ) -> str:
        """
        Generate test input that triggers the bug.
        
        Args:
            candidate: Bug candidate
            hypotheses: Generated hypotheses
            
        Returns:
            Test input string
        """
        bug_type_lower = candidate.bug_type.lower()
        
        if "sql" in bug_type_lower or "injection" in bug_type_lower:
            return "' OR '1'='1' -- ";
        elif "xss" in bug_type_lower:
            return "<script>alert('XSS')</script>";
        elif "path" in bug_type_lower:
            return "../../../etc/passwd";
        elif "auth" in bug_type_lower or "bypass" in bug_type_lower:
            return "admin=true";
        elif "race" in bug_type_lower:
            return "concurrent_request_1, concurrent_request_2";
        else:
            return "malicious_input_placeholder";

    def _describe_expected_behavior(self, candidate: BugCandidate) -> str:
        """
        Describe expected (correct) behavior.
        
        Args:
            candidate: Bug candidate
            
        Returns:
            Expected behavior description
        """
        bug_type_lower = candidate.bug_type.lower()
        
        if "sql" in bug_type_lower or "injection" in bug_type_lower:
            return "Input should be sanitized or parameterized before SQL query execution"
        elif "xss" in bug_type_lower:
            return "User input should be HTML-encoded before output"
        elif "auth" in bug_type_lower or "bypass" in bug_type_lower:
            return "Authentication check should be enforced on all code paths"
        elif "race" in bug_type_lower:
            return "Concurrent access should be properly synchronized"
        else:
            return "Input validation and proper error handling should be in place"

    def _describe_actual_behavior(self, candidate: BugCandidate) -> str:
        """
        Describe actual (buggy) behavior.
        
        Args:
            candidate: Bug candidate
            
        Returns:
            Actual behavior description
        """
        return (
            f"Due to {candidate.bug_type}, unvalidated input reaches sensitive sink, "
            f"allowing potential exploitation. {candidate.description}"
        )
