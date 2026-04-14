"""
Agent module for GlitchHunter.

Provides LangGraph-based state machine for the analysis and patch generation
workflow, plus advanced analysis agents for hypothesis generation and testing.

Exports:
    - StateMachine: State machine wrapper
    - build_workflow: Function to build the LangGraph workflow
    - PatchLoopStateMachine: Patch-Loop state machine with Gates 1-2
    - HypothesisAgent: Generates hypotheses for bug candidates
    - AnalyzerAgent: Tests hypotheses causally
    - ObserverAgent: Evaluates evidence chains
    - LLiftPrioritizer: Hybrid static + LLM prioritization
    - PatchGenerator: Generates patches for issues
    - VerifierNode: Verifies issues
    - SandboxExecutor: Executes code in Docker sandbox
"""

from .state_machine import build_workflow, StateMachine
from .patch_loop import PatchLoopStateMachine, PatchIteration, PatchDecision, PatchLoopState
from .hypothesis_agent import (
    HypothesisAgent,
    Hypothesis,
    HypothesisType,
    Severity,
    BugCandidate,
)
from .analyzer_agent import (
    AnalyzerAgent,
    HypothesisTestResult,
    CallPath,
    DataFlowPath,
    CFGPath,
    Evidence,
    EvidenceCollection,
    EvidenceType,
    FileLocation,
)
from .observer_agent import (
    ObserverAgent,
    AggregatedEvidence,
    RankedCandidate,
    EvidenceChain,
    EvidenceItem,
)
from .llift_prioritizer import (
    LLiftPrioritizer,
    PrioritizationResult,
    SemgrepResult,
    ChurnAnalysis,
)
from .patch_generator import PatchGenerator, PatchResult
from .verifier import VerifierNode, VerificationResult
from .sandbox_executor import SandboxExecutor, ExecutionResult, TestResult, SandboxConfig

__all__ = [
    # State machine
    "build_workflow",
    "StateMachine",
    # Patch Loop
    "PatchLoopStateMachine",
    "PatchIteration",
    "PatchDecision",
    "PatchLoopState",
    # Hypothesis Agent
    "HypothesisAgent",
    "Hypothesis",
    "HypothesisType",
    "Severity",
    "BugCandidate",
    # Analyzer Agent
    "AnalyzerAgent",
    "HypothesisTestResult",
    "CallPath",
    "DataFlowPath",
    "CFGPath",
    "Evidence",
    "EvidenceCollection",
    "EvidenceType",
    "FileLocation",
    # Observer Agent
    "ObserverAgent",
    "AggregatedEvidence",
    "RankedCandidate",
    "EvidenceChain",
    "EvidenceItem",
    # LLift Prioritizer
    "LLiftPrioritizer",
    "PrioritizationResult",
    "SemgrepResult",
    "ChurnAnalysis",
    # Patch Generation & Verification
    "PatchGenerator",
    "PatchResult",
    "VerifierNode",
    "VerificationResult",
    # Sandbox
    "SandboxExecutor",
    "ExecutionResult",
    "TestResult",
    "SandboxConfig",
]
