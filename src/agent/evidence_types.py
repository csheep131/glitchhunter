"""
Evidence types for GlitchHunter Evidence-Contract.

Defines enums and types used in the Evidence-Contract system
that sits between the Shield (hypothesis generation) and Patch Loop.
"""

from enum import Enum


class InvariantType(str, Enum):
    """
    Types of invariants that can be violated by a bug.
    
    These categorize the fundamental property that the bug violates.
    """

    DATA_FLOW = "data_flow"
    """
    Data flow invariant violated.
    
    Examples:
    - Untrusted input reaches sensitive sink without sanitization
    - Data of wrong type flows to consumer expecting different type
    - Null/None value propagates without null-check
    """

    CONTROL_FLOW = "control_flow"
    """
    Control flow invariant violated.
    
    Examples:
    - Authentication check can be bypassed
    - Error handling path skips validation
    - Conditional branch allows unauthorized access
    """

    STATE = "state"
    """
    State invariant violated.
    
    Examples:
    - Object state inconsistent after method call
    - Shared state modified without synchronization
    - State machine in invalid state transition
    """

    BOUNDARY = "boundary"
    """
    Boundary invariant violated.
    
    Examples:
    - Array index out of bounds
    - Numeric overflow/underflow
    - Resource limit exceeded (memory, file handles)
    """

    TIMING = "timing"
    """
    Timing invariant violated.
    
    Examples:
    - Race condition in concurrent access
    - Time-of-check to time-of-use (TOCTOU) vulnerability
    - Deadline/timeout not respected
    """

    RESOURCE = "resource"
    """
    Resource management invariant violated.
    
    Examples:
    - Resource leak (memory, file handle, connection)
    - Double-free or use-after-free
    - Resource acquired but never released
    """


class Scope(str, Enum):
    """
    Scope of impact for a bug.
    
    Determines how far-reaching the consequences of the bug are.
    """

    LOCAL = "local"
    """
    Bug is contained within a single function or method.
    
    Impact: Only the immediate function behavior is affected.
    Fix complexity: Low - typically a local change.
    """

    MODULE = "module"
    """
    Bug affects an entire module or class.
    
    Impact: Multiple functions within the module may be affected.
    Fix complexity: Medium - may require module-wide refactoring.
    """

    CROSS_MODULE = "cross_module"
    """
    Bug spans multiple modules or components.
    
    Impact: Changes in one module affect other modules.
    Fix complexity: High - requires coordinated changes across modules.
    """

    SYSTEM = "system"
    """
    Bug affects system-wide behavior or architecture.
    
    Impact: Multiple subsystems or the entire application.
    Fix complexity: Very High - may require architectural changes.
    """


class RiskClass(str, Enum):
    """
    Risk classification for a bug.
    
    Based on a combination of exploitability and impact.
    """

    LOW = "low"
    """
    Low risk bug.
    
    Characteristics:
    - Difficult to exploit (requires specific conditions)
    - Limited impact (cosmetic or minor functionality)
    - No security implications
    - Easy to fix without side effects
    
    Priority: Fix in normal development cycle.
    """

    MEDIUM = "medium"
    """
    Medium risk bug.
    
    Characteristics:
    - Moderate exploitability (some skill required)
    - Moderate impact (functionality degradation)
    - Potential security implications (low severity)
    - Fix may require testing of adjacent code
    
    Priority: Schedule for next sprint.
    """

    HIGH = "high"
    """
    High risk bug.
    
    Characteristics:
    - Easy to exploit (well-known attack vector)
    - High impact (data loss, service disruption)
    - Clear security implications (OWASP Top 10)
    - Fix requires careful regression testing
    
    Priority: Immediate attention required.
    """

    CRITICAL = "critical"
    """
    Critical risk bug.
    
    Characteristics:
    - Trivial to exploit (automated tools available)
    - Severe impact (complete system compromise)
    - Active exploitation in the wild possible
    - Requires immediate patching and monitoring
    
    Priority: Drop everything, fix now.
    """


class EvidenceStrength(str, Enum):
    """
    Qualitative assessment of evidence strength.
    
    Derived from quantitative evidence_score (0.0-1.0).
    """

    WEAK = "weak"
    """Evidence score < 0.4. Insufficient for auto-fix."""

    MODERATE = "moderate"
    """Evidence score 0.4-0.6. Proceed with caution."""

    STRONG = "strong"
    """Evidence score 0.6-0.8. Good confidence for auto-fix."""

    VERY_STRONG = "very_strong"
    """Evidence score > 0.8. High confidence for auto-fix."""


class GateDecision(str, Enum):
    """
    Decision from EvidenceGate validation.
    """

    PASSED = "passed"
    """Evidence package is complete and valid. Proceed to Patch Loop."""

    RETRY = "retry"
    """Evidence package has issues. Retry generation with feedback."""

    REJECTED = "rejected"
    """Evidence package is fundamentally flawed. Escalate to human."""


# Type aliases for documentation
EvidenceScore = float  # 0.0 to 1.0
ConfidenceLevel = float  # 0.0 to 1.0
