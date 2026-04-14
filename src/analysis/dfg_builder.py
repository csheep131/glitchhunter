"""
Data-Flow Graph Builder for GlitchHunter.

Builds complete Data-Flow Graphs with Taint-Tracking for security analysis.
"""

import ast
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

from core.exceptions import GraphAnalysisError
from core.logging_config import get_logger

logger = get_logger(__name__)


class FlowType(str, Enum):
    """Types of data flow between nodes."""

    ASSIGNMENT = "assignment"
    PARAMETER = "parameter"
    RETURN_VALUE = "return_value"
    FIELD_ACCESS = "field_access"
    GLOBAL_ACCESS = "global_access"
    IMPORT = "import"


class TaintType(str, Enum):
    """Types of taint sources."""

    USER_INPUT = "user_input"
    NETWORK = "network"
    FILE = "file"
    DATABASE = "database"
    ENVIRONMENT = "environment"
    SERIALIZED = "serialized"


class SinkType(str, Enum):
    """Types of taint sinks (vulnerability points)."""

    SQL_QUERY = "sql_query"
    COMMAND_EXECUTION = "command_execution"
    FILE_WRITE = "file_write"
    NETWORK_REQUEST = "network_request"
    CODE_EXECUTION = "code_exec"
    PATH_TRAVERSAL = "path_traversal"
    XSS = "xss"


class VariableScope(str, Enum):
    """Variable scope types."""

    LOCAL = "local"
    GLOBAL = "global"
    CLASS = "class"
    MODULE = "module"
    PARAMETER = "parameter"


@dataclass
class VariableNode:
    """
    Represents a variable in the data-flow graph.

    Attributes:
        name: Variable name
        file_path: Source file path
        line_def: Line number where variable is defined
        line_use: List of line numbers where variable is used
        scope: Variable scope (local, global, class, module)
        type_hint: Optional type annotation
    """

    name: str
    file_path: str
    line_def: int
    line_use: List[int] = field(default_factory=list)
    scope: VariableScope = VariableScope.LOCAL
    type_hint: Optional[str] = None
    uid: str = field(default="")

    def __post_init__(self) -> None:
        """Generate unique identifier after initialization."""
        if not self.uid:
            self.uid = f"{self.file_path}:{self.line_def}:{self.name}"


@dataclass
class DataFlow:
    """
    Represents a data flow between two nodes.

    Attributes:
        source: Source node identifier
        sink: Sink node identifier
        path: List of node identifiers in the flow path
        flow_type: Type of data flow
    """

    source: str
    sink: str
    path: List[str]
    flow_type: FlowType


@dataclass
class TaintSource:
    """
    Represents a taint source (untrusted input).

    Attributes:
        node: Node identifier
        taint_type: Type of taint
        confidence: Confidence score (0.0-1.0)
    """

    node: str
    taint_type: TaintType
    confidence: float = 1.0


@dataclass
class TaintSink:
    """
    Represents a taint sink (vulnerability point).

    Attributes:
        node: Node identifier
        sink_type: Type of sink
        is_sanitized: Whether the input is sanitized
    """

    node: str
    sink_type: SinkType
    is_sanitized: bool = False


@dataclass
class TaintPath:
    """
    Represents a complete taint path from source to sink.

    Attributes:
        source: Taint source
        sink: Taint sink
        path: List of node identifiers in the path
        length: Path length
        is_vulnerable: Whether the path is vulnerable (unsanitized)
    """

    source: TaintSource
    sink: TaintSink
    path: List[str]
    length: int = 0
    is_vulnerable: bool = True

    def __post_init__(self) -> None:
        """Calculate path length and vulnerability status."""
        self.length = len(self.path)
        self.is_vulnerable = not self.sink.is_sanitized


@dataclass
class UninitializedVar:
    """
    Represents an uninitialized variable usage.

    Attributes:
        var_name: Variable name
        file_path: Source file path
        line_use: Line number where uninitialized var is used
        scope: Variable scope
    """

    var_name: str
    file_path: str
    line_use: int
    scope: VariableScope


@dataclass
class NullPointerPath:
    """
    Represents a potential null pointer dereference path.

    Attributes:
        var_name: Variable name
        definition_line: Line where variable is defined
        null_assignment_line: Line where null is assigned
        dereference_line: Line where null is dereferenced
    """

    var_name: str
    definition_line: int
    null_assignment_line: int
    dereference_line: int


@dataclass
class RaceCondition:
    """
    Represents a potential race condition.

    Attributes:
        var_name: Variable name
        concurrent_accesses: List of line numbers with concurrent access
        is_synchronized: Whether access is synchronized
    """

    var_name: str
    concurrent_accesses: List[int]
    is_synchronized: bool = False


@dataclass
class DataFlowGraph:
    """
    Complete Data-Flow Graph with taint tracking.

    Attributes:
        graph: NetworkX directed graph
        variables: Dictionary of variable nodes
        flows: List of data flows
        taint_sources: List of taint sources
        taint_sinks: List of taint sinks
    """

    graph: nx.DiGraph = field(default_factory=nx.DiGraph)
    variables: Dict[str, VariableNode] = field(default_factory=dict)
    flows: List[DataFlow] = field(default_factory=list)
    taint_sources: List[TaintSource] = field(default_factory=list)
    taint_sinks: List[TaintSink] = field(default_factory=list)


class DataFlowGraphBuilder:
    """
    Builds Data-Flow Graphs from AST with taint tracking.

    This builder creates a complete data-flow graph that tracks how data
    flows through the program, identifies taint sources (untrusted input),
    and taint sinks (vulnerability points).
    """

    # Common taint source functions
    TAINT_SOURCE_PATTERNS = {
        "input": TaintType.USER_INPUT,
        "raw_input": TaintType.USER_INPUT,
        "sys.argv": TaintType.USER_INPUT,
        "request.get": TaintType.USER_INPUT,
        "request.post": TaintType.USER_INPUT,
        "request.args": TaintType.USER_INPUT,
        "request.form": TaintType.USER_INPUT,
        "urllib.request": TaintType.NETWORK,
        "requests.get": TaintType.NETWORK,
        "requests.post": TaintType.NETWORK,
        "socket.recv": TaintType.NETWORK,
        "open": TaintType.FILE,
        "io.open": TaintType.FILE,
        "file.read": TaintType.FILE,
        "cursor.execute": TaintType.DATABASE,
        "db.query": TaintType.DATABASE,
        "os.getenv": TaintType.ENVIRONMENT,
        "os.environ": TaintType.ENVIRONMENT,
        "pickle.load": TaintType.SERIALIZED,
        "yaml.load": TaintType.SERIALIZED,
    }

    # Common taint sink functions
    TAINT_SINK_PATTERNS = {
        "execute": SinkType.SQL_QUERY,
        "executemany": SinkType.SQL_QUERY,
        "raw": SinkType.SQL_QUERY,
        "eval": SinkType.CODE_EXECUTION,
        "exec": SinkType.CODE_EXECUTION,
        "compile": SinkType.CODE_EXECUTION,
        "os.system": SinkType.COMMAND_EXECUTION,
        "subprocess.call": SinkType.COMMAND_EXECUTION,
        "subprocess.run": SinkType.COMMAND_EXECUTION,
        "subprocess.Popen": SinkType.COMMAND_EXECUTION,
        "open": SinkType.FILE_WRITE,
        "write": SinkType.FILE_WRITE,
        "requests.get": SinkType.NETWORK_REQUEST,
        "requests.post": SinkType.NETWORK_REQUEST,
        "urllib.request": SinkType.NETWORK_REQUEST,
    }

    # Sanitization functions
    SANITIZATION_FUNCTIONS = {
        "escape",
        "quote",
        "sanitize",
        "clean",
        "validate",
        "filter",
        "strip",
        "html.escape",
        "urllib.parse.quote",
        "shlex.quote",
    }

    def __init__(self) -> None:
        """Initialize the Data-Flow Graph Builder."""
        self._graph = nx.DiGraph()
        self._variables: Dict[str, VariableNode] = {}
        self._flows: List[DataFlow] = []
        self._taint_sources: List[TaintSource] = []
        self._taint_sinks: List[TaintSink] = []
        self._current_scope: str = "module"
        self._current_file: str = ""
        self._sanitized_nodes: Set[str] = set()
        self._async_nodes: Set[str] = set()
        self._lock_nodes: Set[str] = set()

    def build_from_ast(self, ast_tree: ast.AST, symbol_graph: Optional[nx.DiGraph] = None) -> DataFlowGraph:
        """
        Build a complete Data-Flow Graph from an AST.

        Args:
            ast_tree: Python AST tree
            symbol_graph: Optional symbol graph for additional context

        Returns:
            Complete DataFlowGraph with taint tracking

        Raises:
            GraphAnalysisError: If AST traversal fails
        """
        try:
            logger.info("Building data-flow graph from AST")
            self._graph = nx.DiGraph()
            self._variables = {}
            self._flows = []
            self._taint_sources = []
            self._taint_sinks = []
            self._sanitized_nodes = set()
            self._async_nodes = set()
            self._lock_nodes = set()

            # Visit all nodes in the AST
            self._visit_ast(ast_tree)

            # Build flows from graph edges
            self._build_flows()

            # Track taint paths
            self._track_all_taint()

            logger.info(
                f"Data-flow graph built: {len(self._graph.nodes)} nodes, "
                f"{len(self._graph.edges)} edges, "
                f"{len(self._taint_sources)} sources, "
                f"{len(self._taint_sinks)} sinks"
            )

            return DataFlowGraph(
                graph=self._graph,
                variables=self._variables,
                flows=self._flows,
                taint_sources=self._taint_sources,
                taint_sinks=self._taint_sinks,
            )
        except Exception as e:
            logger.error(f"Failed to build data-flow graph: {e}")
            raise GraphAnalysisError(
                message=f"Failed to build data-flow graph: {e}",
                graph_type="data_flow",
                details={"error_type": type(e).__name__},
            )

    def _visit_ast(self, node: ast.AST, parent: Optional[ast.AST] = None) -> None:
        """
        Recursively visit all AST nodes.

        Args:
            node: Current AST node
            parent: Parent AST node
        """
        # Track scope changes
        old_scope = self._current_scope

        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            self._current_scope = f"function:{node.name}"
            self._add_function_node(node)
        elif isinstance(node, ast.ClassDef):
            self._current_scope = f"class:{node.name}"
            self._add_class_node(node)
        elif isinstance(node, ast.Assign):
            self._add_assignment_node(node)
        elif isinstance(node, ast.AnnAssign):
            self._add_annotated_assignment_node(node)
        elif isinstance(node, ast.AugAssign):
            self._add_augmented_assignment_node(node)
        elif isinstance(node, ast.Return):
            self._add_return_node(node)
        elif isinstance(node, ast.Call):
            self._add_call_node(node)
        elif isinstance(node, ast.Name):
            self._add_name_node(node)
        elif isinstance(node, ast.Attribute):
            self._add_attribute_node(node)
        elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            self._add_import_node(node)
        elif isinstance(node, ast.For) or isinstance(node, ast.AsyncFor):
            self._add_loop_node(node)
        elif isinstance(node, ast.While):
            self._add_loop_node(node)
        elif isinstance(node, ast.If):
            self._add_conditional_node(node)
        elif isinstance(node, ast.Try):
            self._add_try_node(node)
        elif isinstance(node, ast.With) or isinstance(node, ast.AsyncWith):
            self._add_with_node(node)

        # Visit children
        for child in ast.iter_child_nodes(node):
            self._visit_ast(child, node)

        # Restore scope
        self._current_scope = old_scope

    def _add_node(self, node_id: str, node_type: str, **kwargs: Any) -> None:
        """
        Add a node to the graph.

        Args:
            node_id: Unique node identifier
            node_type: Type of the node
            **kwargs: Additional node attributes
        """
        if not self._graph.has_node(node_id):
            self._graph.add_node(
                node_id,
                type=node_type,
                file_path=self._current_file,
                **kwargs,
            )

    def _add_edge(
        self,
        source: str,
        target: str,
        edge_type: FlowType,
        **kwargs: Any,
    ) -> None:
        """
        Add an edge to the graph.

        Args:
            source: Source node identifier
            target: Target node identifier
            edge_type: Type of data flow
            **kwargs: Additional edge attributes
        """
        self._graph.add_edge(source, target, type=edge_type.value, **kwargs)

    def _add_function_node(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """
        Add a function definition node.

        Args:
            node: Function definition AST node
        """
        node_id = f"func:{node.name}:{self._current_file}:{node.lineno}"
        self._add_node(
            node_id,
            "function",
            name=node.name,
            line=node.lineno,
            is_async=isinstance(node, ast.AsyncFunctionDef),
        )

        # Add parameters as variables
        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            var_node = VariableNode(
                name=arg.arg,
                file_path=self._current_file,
                line_def=node.lineno,
                scope=VariableScope.PARAMETER,
                type_hint=ast.unparse(arg.annotation) if arg.annotation else None,
            )
            self._variables[var_node.uid] = var_node
            self._add_node(
                var_node.uid,
                "variable",
                name=arg.arg,
                line=node.lineno,
                scope=VariableScope.PARAMETER.value,
            )
            self._add_edge(node_id, var_node.uid, FlowType.PARAMETER)

    def _add_class_node(self, node: ast.ClassDef) -> None:
        """
        Add a class definition node.

        Args:
            node: Class definition AST node
        """
        node_id = f"class:{node.name}:{self._current_file}:{node.lineno}"
        self._add_node(
            node_id,
            "class",
            name=node.name,
            line=node.lineno,
        )

    def _add_assignment_node(self, node: ast.Assign) -> None:
        """
        Add an assignment node.

        Args:
            node: Assignment AST node
        """
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_node = VariableNode(
                    name=target.id,
                    file_path=self._current_file,
                    line_def=node.lineno,
                    scope=self._get_scope(target.id),
                )
                self._variables[var_node.uid] = var_node

                source_id = self._get_node_id(node.value)
                self._add_node(
                    var_node.uid,
                    "variable",
                    name=target.id,
                    line=node.lineno,
                    scope=var_node.scope.value,
                )

                if source_id:
                    self._add_edge(source_id, var_node.uid, FlowType.ASSIGNMENT)

    def _add_annotated_assignment_node(self, node: ast.AnnAssign) -> None:
        """
        Add an annotated assignment node.

        Args:
            node: Annotated assignment AST node
        """
        if isinstance(node.target, ast.Name):
            type_hint = ast.unparse(node.annotation) if node.annotation else None
            var_node = VariableNode(
                name=node.target.id,
                file_path=self._current_file,
                line_def=node.lineno,
                scope=self._get_scope(node.target.id),
                type_hint=type_hint,
            )
            self._variables[var_node.uid] = var_node

            source_id = self._get_node_id(node.value) if node.value else None
            self._add_node(
                var_node.uid,
                "variable",
                name=node.target.id,
                line=node.lineno,
                scope=var_node.scope.value,
                type_hint=type_hint,
            )

            if source_id:
                self._add_edge(source_id, var_node.uid, FlowType.ASSIGNMENT)

    def _add_augmented_assignment_node(self, node: ast.AugAssign) -> None:
        """
        Add an augmented assignment node.

        Args:
            node: Augmented assignment AST node
        """
        if isinstance(node.target, ast.Name):
            var_id = f"var:{node.target.id}:{self._current_file}:{node.lineno}"
            source_id = self._get_node_id(node.value)

            self._add_node(
                var_id,
                "variable",
                name=node.target.id,
                line=node.lineno,
                scope=self._get_scope(node.target.id),
            )

            if source_id:
                self._add_edge(source_id, var_id, FlowType.ASSIGNMENT)

    def _add_return_node(self, node: ast.Return) -> None:
        """
        Add a return value node.

        Args:
            node: Return AST node
        """
        if node.value:
            return_id = f"return:{self._current_file}:{node.lineno}"
            source_id = self._get_node_id(node.value)

            self._add_node(
                return_id,
                "return",
                line=node.lineno,
            )

            if source_id:
                self._add_edge(source_id, return_id, FlowType.RETURN_VALUE)

    def _add_call_node(self, node: ast.Call) -> None:
        """
        Add a function call node and check for taint sources/sinks.

        Args:
            node: Call AST node
        """
        call_id = f"call:{self._current_file}:{node.lineno}"
        func_name = self._get_call_name(node)

        self._add_node(
            call_id,
            "call",
            function=func_name,
            line=node.lineno,
        )

        # Check for taint sources
        if func_name in self.TAINT_SOURCE_PATTERNS:
            taint_type = self.TAINT_SOURCE_PATTERNS[func_name]
            confidence = self._estimate_confidence(func_name, node)
            self._taint_sources.append(
                TaintSource(node=call_id, taint_type=taint_type, confidence=confidence)
            )
            self._add_node(call_id, "taint_source", taint_type=taint_type.value)

        # Check for taint sinks
        for sink_name, sink_type in self.TAINT_SINK_PATTERNS.items():
            if sink_name in func_name:
                is_sanitized = self._check_sanitization(node)
                if is_sanitized:
                    self._sanitized_nodes.add(call_id)
                self._taint_sinks.append(
                    TaintSink(node=call_id, sink_type=sink_type, is_sanitized=is_sanitized)
                )
                self._add_node(
                    call_id,
                    "taint_sink",
                    sink_type=sink_type.value,
                    is_sanitized=is_sanitized,
                )
                break

        # Add edges from arguments
        for arg in node.args:
            arg_id = self._get_node_id(arg)
            if arg_id:
                self._add_edge(arg_id, call_id, FlowType.PARAMETER)

    def _add_name_node(self, node: ast.Name) -> None:
        """
        Add a name reference node.

        Args:
            node: Name AST node
        """
        var_id = f"name:{node.id}:{self._current_file}:{node.lineno}"

        # Track variable usage
        if node.id in self._variables:
            for var in self._variables.values():
                if var.name == node.id:
                    var.line_use.append(node.lineno)

        self._add_node(
            var_id,
            "name",
            name=node.id,
            line=node.lineno,
            ctx=node.ctx.__class__.__name__,
        )

    def _add_attribute_node(self, node: ast.Attribute) -> None:
        """
        Add an attribute access node.

        Args:
            node: Attribute AST node
        """
        attr_id = f"attr:{node.attr}:{self._current_file}:{node.lineno}"
        value_id = self._get_node_id(node.value)

        self._add_node(
            attr_id,
            "attribute",
            name=node.attr,
            line=node.lineno,
        )

        if value_id:
            self._add_edge(value_id, attr_id, FlowType.FIELD_ACCESS)

    def _add_import_node(self, node: ast.Import | ast.ImportFrom) -> None:
        """
        Add an import node.

        Args:
            node: Import AST node
        """
        if isinstance(node, ast.Import):
            for alias in node.names:
                import_id = f"import:{alias.name}:{self._current_file}:{node.lineno}"
                self._add_node(
                    import_id,
                    "import",
                    module=alias.name,
                    alias=alias.asname,
                    line=node.lineno,
                )
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                import_id = (
                    f"import:{node.module}.{alias.name}:{self._current_file}:{node.lineno}"
                )
                self._add_node(
                    import_id,
                    "import",
                    module=node.module,
                    name=alias.name,
                    alias=alias.asname,
                    line=node.lineno,
                )
                if node.level > 0:
                    self._graph.nodes[import_id]["relative_level"] = node.level

    def _add_loop_node(
        self, node: ast.For | ast.While | ast.AsyncFor
    ) -> None:
        """
        Add a loop node.

        Args:
            node: Loop AST node
        """
        loop_id = f"loop:{self._current_file}:{node.lineno}"
        self._add_node(
            loop_id,
            "loop",
            line=node.lineno,
            is_async=isinstance(node, ast.AsyncFor),
        )

    def _add_conditional_node(self, node: ast.If) -> None:
        """
        Add a conditional node.

        Args:
            node: If statement AST node
        """
        cond_id = f"if:{self._current_file}:{node.lineno}"
        self._add_node(
            cond_id,
            "conditional",
            line=node.lineno,
        )

    def _add_try_node(self, node: ast.Try) -> None:
        """
        Add a try-except node.

        Args:
            node: Try statement AST node
        """
        try_id = f"try:{self._current_file}:{node.lineno}"
        self._add_node(
            try_id,
            "try",
            line=node.lineno,
        )

    def _add_with_node(self, node: ast.With | ast.AsyncWith) -> None:
        """
        Add a with statement node (context manager).

        Args:
            node: With statement AST node
        """
        with_id = f"with:{self._current_file}:{node.lineno}"
        self._add_node(
            with_id,
            "with",
            line=node.lineno,
            is_async=isinstance(node, ast.AsyncWith),
        )

        # Check for lock acquisition
        for item in node.items:
            if isinstance(item.context_expr, ast.Call):
                call_name = self._get_call_name(item.context_expr)
                if "lock" in call_name.lower() or "acquire" in call_name.lower():
                    self._lock_nodes.add(with_id)

    def _get_node_id(self, node: ast.AST) -> Optional[str]:
        """
        Get or generate a node identifier for an AST node.

        Args:
            node: AST node

        Returns:
            Node identifier string or None
        """
        if isinstance(node, ast.Name):
            return f"name:{node.id}:{self._current_file}:{node.lineno}"
        elif isinstance(node, ast.Constant):
            return f"const:{repr(node.value)}:{self._current_file}:{node.lineno}"
        elif isinstance(node, ast.Call):
            return f"call:{self._current_file}:{node.lineno}"
        elif isinstance(node, ast.Attribute):
            return f"attr:{node.attr}:{self._current_file}:{node.lineno}"
        elif isinstance(node, ast.Subscript):
            return f"subscript:{self._current_file}:{node.lineno}"
        else:
            return f"node:{node.__class__.__name__}:{self._current_file}:{node.lineno}"

    def _get_call_name(self, node: ast.Call) -> str:
        """
        Get the function name from a call node.

        Args:
            node: Call AST node

        Returns:
            Function name string
        """
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return self._get_attribute_chain(node.func)
        return "unknown"

    def _get_attribute_chain(self, node: ast.Attribute) -> str:
        """
        Get the full attribute chain (e.g., "os.system").

        Args:
            node: Attribute AST node

        Returns:
            Full attribute chain string
        """
        parts = [node.attr]
        current = node.value
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))

    def _get_scope(self, var_name: str) -> VariableScope:
        """
        Determine the scope of a variable.

        Args:
            var_name: Variable name

        Returns:
            VariableScope enum value
        """
        if self._current_scope.startswith("function:"):
            if var_name in ("self", "cls"):
                return VariableScope.CLASS
            return VariableScope.LOCAL
        elif self._current_scope.startswith("class:"):
            return VariableScope.CLASS
        return VariableScope.MODULE

    def _check_sanitization(self, node: ast.Call) -> bool:
        """
        Check if a call node has sanitized inputs.

        Args:
            node: Call AST node

        Returns:
            True if input is sanitized, False otherwise
        """
        func_name = self._get_call_name(node)

        # Check if the function itself is a sanitizer
        for sanitizer in self.SANITIZATION_FUNCTIONS:
            if sanitizer in func_name.lower():
                return True

        # Check if arguments are sanitized
        for arg in node.args:
            if isinstance(arg, ast.Call):
                arg_func_name = self._get_call_name(arg)
                for sanitizer in self.SANITIZATION_FUNCTIONS:
                    if sanitizer in arg_func_name.lower():
                        return True

        return False

    def _estimate_confidence(self, func_name: str, node: ast.Call) -> float:
        """
        Estimate confidence score for a taint source.

        Args:
            func_name: Function name
            node: Call AST node

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Direct user input has highest confidence
        if func_name in ("input", "raw_input"):
            return 1.0
        # Network sources have high confidence
        if any(x in func_name for x in ("request", "urllib", "socket")):
            return 0.9
        # File sources have medium-high confidence
        if func_name in ("open", "io.open", "file.read"):
            return 0.8
        # Database sources
        if any(x in func_name for x in ("cursor", "db.", "query")):
            return 0.85
        # Environment variables
        if "env" in func_name.lower():
            return 0.7
        # Serialized data
        if any(x in func_name for x in ("pickle", "yaml")):
            return 0.75
        return 0.6

    def _build_flows(self) -> None:
        """Build data flow list from graph edges."""
        for source, target, data in self._graph.edges(data=True):
            flow_type = FlowType(data.get("type", FlowType.ASSIGNMENT.value))
            self._flows.append(
                DataFlow(
                    source=source,
                    sink=target,
                    path=[source, target],
                    flow_type=flow_type,
                )
            )

    def _track_all_taint(self) -> None:
        """Track taint from all sources to all sinks."""
        # This is handled during node creation
        pass

    def add_variable_flow(
        self,
        from_node: str,
        to_node: str,
        var_name: str,
        flow_type: FlowType,
    ) -> None:
        """
        Add a variable flow between two nodes.

        Args:
            from_node: Source node identifier
            to_node: Target node identifier
            var_name: Variable name
            flow_type: Type of data flow
        """
        self._add_edge(from_node, to_node, flow_type, variable=var_name)
        self._flows.append(
            DataFlow(
                source=from_node,
                sink=to_node,
                path=[from_node, to_node],
                flow_type=flow_type,
            )
        )

    def add_taint_source(self, node: str, taint_type: TaintType, confidence: float = 1.0) -> None:
        """
        Add a taint source to the graph.

        Args:
            node: Node identifier
            taint_type: Type of taint
            confidence: Confidence score
        """
        self._taint_sources.append(
            TaintSource(node=node, taint_type=taint_type, confidence=confidence)
        )
        if self._graph.has_node(node):
            self._graph.nodes[node]["taint_source"] = True
            self._graph.nodes[node]["taint_type"] = taint_type.value

    def add_taint_sink(
        self,
        node: str,
        sink_type: SinkType,
        is_sanitized: bool = False,
    ) -> None:
        """
        Add a taint sink to the graph.

        Args:
            node: Node identifier
            sink_type: Type of sink
            is_sanitized: Whether the sink is sanitized
        """
        self._taint_sinks.append(
            TaintSink(node=node, sink_type=sink_type, is_sanitized=is_sanitized)
        )
        if self._graph.has_node(node):
            self._graph.nodes[node]["taint_sink"] = True
            self._graph.nodes[node]["sink_type"] = sink_type.value
            self._graph.nodes[node]["is_sanitized"] = is_sanitized

    def track_taint(self, source_node: str) -> List[TaintPath]:
        """
        Track taint from a source node to all reachable sinks.

        Args:
            source_node: Source node identifier

        Returns:
            List of taint paths from source to sinks
        """
        taint_paths: List[TaintPath] = []

        # Find the taint source
        source = None
        for ts in self._taint_sources:
            if ts.node == source_node:
                source = ts
                break

        if not source:
            logger.warning(f"Taint source not found: {source_node}")
            return []

        # Find all reachable sinks using BFS
        try:
            for sink_node in nx.descendants(self._graph, source_node):
                # Check if this is a taint sink
                for ts in self._taint_sinks:
                    if ts.node == sink_node:
                        # Find path
                        try:
                            path = nx.shortest_path(self._graph, source_node, sink_node)
                            taint_paths.append(
                                TaintPath(
                                    source=source,
                                    sink=ts,
                                    path=path,
                                )
                            )
                        except nx.NetworkXNoPath:
                            pass
        except nx.NetworkXError as e:
            logger.error(f"Error tracking taint from {source_node}: {e}")

        return taint_paths

    def find_uninitialized_variables(self) -> List[UninitializedVar]:
        """
        Find variables that are used before initialization.

        Returns:
            List of uninitialized variable usages
        """
        uninitialized: List[UninitializedVar] = []

        # Track definitions and uses
        definitions: Dict[str, int] = {}  # var_name -> line_def
        uses: Dict[str, List[int]] = {}  # var_name -> [line_use]

        for node_id, data in self._graph.nodes(data=True):
            if data.get("type") == "variable":
                var_name = data.get("name", "")
                line = data.get("line", 0)
                definitions[var_name] = line
            elif data.get("type") == "name" and data.get("ctx") == "Load":
                var_name = data.get("name", "")
                line = data.get("line", 0)
                if var_name not in uses:
                    uses[var_name] = []
                uses[var_name].append(line)

        # Check for uses before definitions
        for var_name, use_lines in uses.items():
            if var_name in definitions:
                def_line = definitions[var_name]
                for use_line in use_lines:
                    if use_line < def_line:
                        uninitialized.append(
                            UninitializedVar(
                                var_name=var_name,
                                file_path=self._current_file,
                                line_use=use_line,
                                scope=self._get_scope(var_name),
                            )
                        )

        return uninitialized

    def find_null_pointer_paths(self) -> List[NullPointerPath]:
        """
        Find potential null pointer dereference paths.

        Returns:
            List of null pointer paths
        """
        null_paths: List[NullPointerPath] = []

        # Track None/Null assignments
        null_assignments: Dict[str, int] = {}  # var_name -> line

        for node_id, data in self._graph.nodes(data=True):
            if data.get("type") == "variable":
                var_name = data.get("name", "")
                line = data.get("line", 0)

                # Check if this is a None assignment
                # This would require checking the actual value in a real implementation
                # For now, we use a heuristic based on node naming
                if "none" in node_id.lower() or "null" in node_id.lower():
                    null_assignments[var_name] = line

        # In a full implementation, we would track dereferences
        # and match them against null assignments
        # This is a simplified version

        return null_paths

    def find_race_conditions(self) -> List[RaceCondition]:
        """
        Find potential race conditions.

        Returns:
            List of potential race conditions
        """
        race_conditions: List[RaceCondition] = []

        # Track shared variables accessed in async contexts
        async_vars: Dict[str, List[int]] = {}  # var_name -> [access_lines]

        for node_id, data in self._graph.nodes(data=True):
            # Check for async functions
            if data.get("is_async"):
                # Track variables in async context
                pass

            # Check for lock-protected sections
            if node_id in self._lock_nodes:
                # Variables in this scope are protected
                pass

        # Find unprotected shared variables
        for var_name, access_lines in async_vars.items():
            if len(access_lines) > 1:
                # Check if accesses are synchronized
                is_synchronized = self._check_synchronization(var_name)
                if not is_synchronized:
                    race_conditions.append(
                        RaceCondition(
                            var_name=var_name,
                            concurrent_accesses=access_lines,
                            is_synchronized=is_synchronized,
                        )
                    )

        return race_conditions

    def _check_synchronization(self, var_name: str) -> bool:
        """
        Check if a variable access is synchronized.

        Args:
            var_name: Variable name

        Returns:
            True if synchronized, False otherwise
        """
        # In a full implementation, this would check for:
        # - Lock acquisition
        # - Semaphore usage
        # - Atomic operations
        # - Thread-safe collections
        return False

    def set_current_file(self, file_path: str) -> None:
        """
        Set the current file path for node tracking.

        Args:
            file_path: File path string
        """
        self._current_file = file_path

    def get_graph(self) -> nx.DiGraph:
        """
        Get the underlying NetworkX graph.

        Returns:
            NetworkX DiGraph
        """
        return self._graph

    def get_variables(self) -> Dict[str, VariableNode]:
        """
        Get all tracked variables.

        Returns:
            Dictionary of variable nodes
        """
        return self._variables.copy()

    def get_flows(self) -> List[DataFlow]:
        """
        Get all data flows.

        Returns:
            List of data flows
        """
        return self._flows.copy()

    def get_taint_sources(self) -> List[TaintSource]:
        """
        Get all taint sources.

        Returns:
            List of taint sources
        """
        return self._taint_sources.copy()

    def get_taint_sinks(self) -> List[TaintSink]:
        """
        Get all taint sinks.

        Returns:
            List of taint sinks
        """
        return self._taint_sinks.copy()
