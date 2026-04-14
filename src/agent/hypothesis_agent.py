"""
Hypothesis Agent for GlitchHunter.

Generates and ranks hypotheses for bug candidates using CogniGent-style reasoning.
"""

import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import networkx as nx

from ..analysis.cfg_builder import ControlFlowGraph
from ..analysis.dfg_builder import DataFlowGraph, TaintPath
from ..core.logging_config import get_logger

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
