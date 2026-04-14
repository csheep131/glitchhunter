"""
Analysis module for GlitchHunter.

Provides data-flow and control-flow graph builders for advanced code analysis,
plus graph comparison for regression detection.

Exports:
    - DataFlowGraphBuilder: Builds data-flow graphs with taint tracking
    - ControlFlowGraphBuilder: Builds control-flow graphs
    - GraphComparator: Compares before/after graphs for regression detection
    - All dataclasses for graph representation
"""

from .cfg_builder import (
    BasicBlock,
    CFGEdge,
    Conditional,
    ControlFlowGraph,
    ControlFlowGraphBuilder,
    EdgeType,
    ExceptionPath,
    Loop,
    LoopType,
)
from .dfg_builder import (
    DataFlow,
    DataFlowGraph,
    DataFlowGraphBuilder,
    FlowType,
    NullPointerPath,
    RaceCondition,
    SinkType,
    TaintPath,
    TaintSink,
    TaintSource,
    TaintType,
    UninitializedVar,
    VariableNode,
    VariableScope,
)
from .graph_comparator import (
    GraphComparator,
    GraphComparison,
    NodeChange,
    EdgeChange,
    DataFlowChange,
    CallChainChange,
    ChangeType,
)

__all__ = [
    # DFG Builder
    "DataFlowGraphBuilder",
    "DataFlowGraph",
    "DataFlow",
    "VariableNode",
    "TaintSource",
    "TaintSink",
    "TaintPath",
    "UninitializedVar",
    "NullPointerPath",
    "RaceCondition",
    "FlowType",
    "TaintType",
    "SinkType",
    "VariableScope",
    # CFG Builder
    "ControlFlowGraphBuilder",
    "ControlFlowGraph",
    "BasicBlock",
    "CFGEdge",
    "Loop",
    "Conditional",
    "ExceptionPath",
    "EdgeType",
    "LoopType",
    # Graph Comparator
    "GraphComparator",
    "GraphComparison",
    "NodeChange",
    "EdgeChange",
    "DataFlowChange",
    "CallChainChange",
    "ChangeType",
]
