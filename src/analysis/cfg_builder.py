"""
Control-Flow Graph Builder for GlitchHunter.

Builds Control-Flow Graphs for complex path analysis.
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


class EdgeType(str, Enum):
    """Types of edges in the control-flow graph."""

    SEQUENTIAL = "sequential"
    BRANCH = "branch"
    LOOP = "loop"
    EXCEPTION = "exception"
    JUMP = "jump"


class LoopType(str, Enum):
    """Types of loops."""

    FOR = "for"
    WHILE = "while"
    DO_WHILE = "do_while"
    ASYNC_FOR = "async_for"


@dataclass
class BasicBlock:
    """
    Represents a basic block in the CFG.

    A basic block is a maximal sequence of consecutive statements
    with a single entry point and a single exit point.

    Attributes:
        id: Unique identifier for the block
        statements: List of statement strings
        line_start: Starting line number
        line_end: Ending line number
        predecessors: List of predecessor block IDs
        successors: List of successor block IDs
    """

    id: str
    statements: List[str] = field(default_factory=list)
    line_start: int = 0
    line_end: int = 0
    predecessors: List[str] = field(default_factory=list)
    successors: List[str] = field(default_factory=list)

    def add_statement(self, statement: str, line: int) -> None:
        """
        Add a statement to the block.

        Args:
            statement: Statement string
            line: Line number
        """
        self.statements.append(statement)
        if self.line_start == 0 or line < self.line_start:
            self.line_start = line
        if line > self.line_end:
            self.line_end = line


@dataclass
class CFGEdge:
    """
    Represents an edge in the CFG.

    Attributes:
        source: Source block ID
        target: Target block ID
        edge_type: Type of control flow edge
        condition: Optional condition for branch edges
    """

    source: str
    target: str
    edge_type: EdgeType
    condition: Optional[str] = None


@dataclass
class Loop:
    """
    Represents a loop in the CFG.

    Attributes:
        header: Header block ID (loop condition)
        body: List of block IDs in the loop body
        back_edge: Back edge source block ID
        loop_type: Type of loop
    """

    header: str
    body: List[str] = field(default_factory=list)
    back_edge: str = ""
    loop_type: LoopType = LoopType.WHILE


@dataclass
class Conditional:
    """
    Represents a conditional branch.

    Attributes:
        condition_node: Condition block ID
        true_branch: List of block IDs in the true branch
        false_branch: List of block IDs in the false branch
        merge_node: Merge block ID where branches converge
    """

    condition_node: str
    true_branch: List[str] = field(default_factory=list)
    false_branch: List[str] = field(default_factory=list)
    merge_node: str = ""


@dataclass
class ExceptionPath:
    """
    Represents an exception handling path.

    Attributes:
        try_block: Try block ID
        catch_blocks: List of catch/except block IDs
        finally_block: Optional finally block ID
        exception_type: Exception type being caught
    """

    try_block: str
    catch_blocks: List[str] = field(default_factory=list)
    finally_block: Optional[str] = None
    exception_type: str = ""


@dataclass
class ControlFlowGraph:
    """
    Complete Control-Flow Graph.

    Attributes:
        graph: NetworkX directed graph
        entry_node: Entry block ID
        exit_node: Exit block ID
        basic_blocks: List of basic blocks
        loops: List of loops
    """

    graph: nx.DiGraph = field(default_factory=nx.DiGraph)
    entry_node: str = "entry"
    exit_node: str = "exit"
    basic_blocks: List[BasicBlock] = field(default_factory=list)
    loops: List[Loop] = field(default_factory=list)


class ControlFlowGraphBuilder:
    """
    Builds Control-Flow Graphs from AST.

    This builder creates a CFG that represents all possible execution
    paths through a function or method.
    """

    def __init__(self) -> None:
        """Initialize the Control-Flow Graph Builder."""
        self._graph = nx.DiGraph()
        self._blocks: Dict[str, BasicBlock] = {}
        self._loops: List[Loop] = []
        self._conditionals: List[Conditional] = []
        self._exception_paths: List[ExceptionPath] = []
        self._entry_node = "entry"
        self._exit_node = "exit"
        self._current_function = ""
        self._block_counter = 0
        self._current_block: Optional[str] = None

    def build_from_ast(self, ast_tree: ast.AST, function_name: str = "") -> ControlFlowGraph:
        """
        Build a Control-Flow Graph from an AST.

        Args:
            ast_tree: Python AST tree
            function_name: Optional function name to focus on

        Returns:
            Complete ControlFlowGraph

        Raises:
            GraphAnalysisError: If AST traversal fails
        """
        try:
            logger.info(f"Building control-flow graph for function: {function_name}")

            self._graph = nx.DiGraph()
            self._blocks = {}
            self._loops = []
            self._conditionals = []
            self._exception_paths = []
            self._block_counter = 0

            # Create entry and exit nodes
            self._create_block("entry", line_start=0)
            self._create_block("exit", line_start=0)
            self._entry_node = "entry"
            self._exit_node = "exit"

            # Find the target function if specified
            if function_name:
                target_func = self._find_function(ast_tree, function_name)
                if target_func:
                    self._current_function = function_name
                    self._visit_function(target_func)
            else:
                # Build CFG for the entire module
                self._visit_module(ast_tree)

            # Build basic blocks list
            basic_blocks = list(self._blocks.values())

            # Find loops
            self._find_loops()

            logger.info(
                f"CFG built: {len(self._graph.nodes)} nodes, "
                f"{len(self._graph.edges)} edges, "
                f"{len(basic_blocks)} blocks, "
                f"{len(self._loops)} loops"
            )

            return ControlFlowGraph(
                graph=self._graph,
                entry_node=self._entry_node,
                exit_node=self._exit_node,
                basic_blocks=basic_blocks,
                loops=self._loops,
            )
        except Exception as e:
            logger.error(f"Failed to build control-flow graph: {e}")
            raise GraphAnalysisError(
                message=f"Failed to build control-flow graph: {e}",
                graph_type="control_flow",
                details={"error_type": type(e).__name__},
            )

    def _create_block(self, block_id: str, line_start: int = 0) -> BasicBlock:
        """
        Create a new basic block.

        Args:
            block_id: Unique block identifier
            line_start: Starting line number

        Returns:
            Created BasicBlock
        """
        block = BasicBlock(id=block_id, line_start=line_start)
        self._blocks[block_id] = block
        self._graph.add_node(
            block_id,
            type="block",
            line_start=line_start,
        )
        return block

    def _add_edge(
        self,
        source: str,
        target: str,
        edge_type: EdgeType,
        condition: Optional[str] = None,
    ) -> None:
        """
        Add an edge to the CFG.

        Args:
            source: Source block ID
            target: Target block ID
            edge_type: Type of edge
            condition: Optional condition for branch edges
        """
        self._graph.add_edge(
            source,
            target,
            type=edge_type.value,
            condition=condition,
        )

        # Update block successors/predecessors
        if source in self._blocks:
            if target not in self._blocks[source].successors:
                self._blocks[source].successors.append(target)
        if target in self._blocks:
            if source not in self._blocks[target].predecessors:
                self._blocks[target].predecessors.append(source)

    def _find_function(self, ast_tree: ast.AST, function_name: str) -> Optional[ast.FunctionDef | ast.AsyncFunctionDef]:
        """
        Find a function definition in the AST.

        Args:
            ast_tree: AST tree to search
            function_name: Name of the function to find

        Returns:
            Function definition node or None
        """
        for node in ast.walk(ast_tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == function_name:
                    return node
        return None

    def _visit_module(self, ast_tree: ast.AST) -> None:
        """
        Visit all top-level statements in a module.

        Args:
            ast_tree: Module AST
        """
        if isinstance(ast_tree, ast.Module):
            # Connect entry to first statement
            prev_block = self._entry_node

            for stmt in ast_tree.body:
                next_block = self._visit_statement(stmt, prev_block)
                if next_block:
                    prev_block = next_block

            # Connect last statement to exit
            if prev_block != self._entry_node:
                self._add_edge(prev_block, self._exit_node, EdgeType.SEQUENTIAL)

    def _visit_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        """
        Visit a function definition.

        Args:
            node: Function definition AST node
        """
        # Create function entry block
        func_entry = f"func_entry:{node.name}"
        self._create_block(func_entry, line_start=node.lineno)
        self._add_edge(self._entry_node, func_entry, EdgeType.SEQUENTIAL)

        # Process function body
        prev_block = func_entry
        for stmt in node.body:
            next_block = self._visit_statement(stmt, prev_block)
            if next_block:
                prev_block = next_block

        # Connect to function exit
        func_exit = f"func_exit:{node.name}"
        self._create_block(func_exit, line_start=node.lineno)
        if prev_block != func_entry:
            self._add_edge(prev_block, func_exit, EdgeType.SEQUENTIAL)
        self._add_edge(func_exit, self._exit_node, EdgeType.SEQUENTIAL)

    def _visit_statement(self, node: ast.AST, prev_block: str) -> Optional[str]:
        """
        Visit a statement and create corresponding CFG nodes.

        Args:
            node: Statement AST node
            prev_block: Previous block ID

        Returns:
            Next block ID or None
        """
        self._current_block = prev_block

        if isinstance(node, ast.Assign) or isinstance(node, ast.AnnAssign):
            return self._visit_assignment(node, prev_block)
        elif isinstance(node, ast.If):
            return self._visit_if(node, prev_block)
        elif isinstance(node, ast.For) or isinstance(node, ast.AsyncFor):
            return self._visit_for(node, prev_block)
        elif isinstance(node, ast.While):
            return self._visit_while(node, prev_block)
        elif isinstance(node, ast.Return):
            return self._visit_return(node, prev_block)
        elif isinstance(node, ast.Try):
            return self._visit_try(node, prev_block)
        elif isinstance(node, ast.With) or isinstance(node, ast.AsyncWith):
            return self._visit_with(node, prev_block)
        elif isinstance(node, ast.Raise):
            return self._visit_raise(node, prev_block)
        elif isinstance(node, ast.Break):
            return self._visit_break(node, prev_block)
        elif isinstance(node, ast.Continue):
            return self._visit_continue(node, prev_block)
        elif isinstance(node, ast.Expr):
            return self._visit_expr(node, prev_block)
        else:
            # Generic statement
            return self._visit_generic(node, prev_block)

    def _visit_assignment(
        self, node: ast.Assign | ast.AnnAssign, prev_block: str
    ) -> Optional[str]:
        """
        Visit an assignment statement.

        Args:
            node: Assignment AST node
            prev_block: Previous block ID

        Returns:
            Next block ID
        """
        block_id = f"assign:{self._block_counter}"
        self._block_counter += 1

        self._create_block(block_id, line_start=node.lineno)
        self._add_edge(prev_block, block_id, EdgeType.SEQUENTIAL)

        # Add statement to block
        try:
            stmt_str = ast.unparse(node)
            self._blocks[block_id].add_statement(stmt_str, node.lineno)
        except Exception:
            self._blocks[block_id].add_statement(f"<assignment>", node.lineno)

        return block_id

    def _visit_if(self, node: ast.If, prev_block: str) -> Optional[str]:
        """
        Visit an if statement.

        Args:
            node: If statement AST node
            prev_block: Previous block ID

        Returns:
            Merge block ID
        """
        # Condition block
        cond_block = f"if_cond:{self._block_counter}"
        self._block_counter += 1
        self._create_block(cond_block, line_start=node.lineno)
        self._add_edge(prev_block, cond_block, EdgeType.SEQUENTIAL)

        try:
            cond_str = ast.unparse(node.test)
        except Exception:
            cond_str = "<condition>"

        # True branch
        true_block = f"if_true:{self._block_counter}"
        self._block_counter += 1
        self._create_block(true_block, line_start=node.lineno)

        # False branch
        false_block = f"if_false:{self._block_counter}"
        self._block_counter += 1
        self._create_block(false_block, line_start=node.lineno)

        # Add branch edges
        self._add_edge(cond_block, true_block, EdgeType.BRANCH, condition=f"if {cond_str}")
        self._add_edge(cond_block, false_block, EdgeType.BRANCH, condition=f"else")

        # Process true branch body
        true_prev = true_block
        for stmt in node.body:
            next_block = self._visit_statement(stmt, true_prev)
            if next_block:
                true_prev = next_block

        # Process false branch body (elif/else)
        false_prev = false_block
        for stmt in node.orelse:
            next_block = self._visit_statement(stmt, false_prev)
            if next_block:
                false_prev = next_block

        # Merge block
        merge_block = f"if_merge:{self._block_counter}"
        self._block_counter += 1
        self._create_block(merge_block, line_start=node.lineno)

        # Connect branches to merge
        if true_prev != true_block or len(node.body) == 0:
            self._add_edge(true_prev, merge_block, EdgeType.SEQUENTIAL)
        if false_prev != false_block or len(node.orelse) == 0:
            self._add_edge(false_prev, merge_block, EdgeType.SEQUENTIAL)

        # Record conditional
        self._conditionals.append(
            Conditional(
                condition_node=cond_block,
                true_branch=[true_block],
                false_branch=[false_block],
                merge_node=merge_block,
            )
        )

        return merge_block

    def _visit_for(
        self, node: ast.For | ast.AsyncFor, prev_block: str
    ) -> Optional[str]:
        """
        Visit a for loop.

        Args:
            node: For loop AST node
            prev_block: Previous block ID

        Returns:
            Block after loop
        """
        # Loop header block
        header_block = f"for_header:{self._block_counter}"
        self._block_counter += 1
        self._create_block(header_block, line_start=node.lineno)
        self._add_edge(prev_block, header_block, EdgeType.SEQUENTIAL)

        # Loop body start
        body_start = f"for_body:{self._block_counter}"
        self._block_counter += 1
        self._create_block(body_start, line_start=node.lineno)

        # Add loop edge
        self._add_edge(header_block, body_start, EdgeType.LOOP)

        # Process loop body
        body_prev = body_start
        body_blocks = [body_start]
        for stmt in node.body:
            next_block = self._visit_statement(stmt, body_prev)
            if next_block:
                body_blocks.append(next_block)
                body_prev = next_block

        # Back edge to header
        self._add_edge(body_prev, header_block, EdgeType.LOOP)

        # Exit block (after loop)
        exit_block = f"for_exit:{self._block_counter}"
        self._block_counter += 1
        self._create_block(exit_block, line_start=node.lineno)
        self._add_edge(header_block, exit_block, EdgeType.SEQUENTIAL)

        # Record loop
        loop_type = LoopType.ASYNC_FOR if isinstance(node, ast.AsyncFor) else LoopType.FOR
        self._loops.append(
            Loop(
                header=header_block,
                body=body_blocks,
                back_edge=body_prev,
                loop_type=loop_type,
            )
        )

        return exit_block

    def _visit_while(self, node: ast.While, prev_block: str) -> Optional[str]:
        """
        Visit a while loop.

        Args:
            node: While loop AST node
            prev_block: Previous block ID

        Returns:
            Block after loop
        """
        # Condition block
        cond_block = f"while_cond:{self._block_counter}"
        self._block_counter += 1
        self._create_block(cond_block, line_start=node.lineno)
        self._add_edge(prev_block, cond_block, EdgeType.SEQUENTIAL)

        try:
            cond_str = ast.unparse(node.test)
        except Exception:
            cond_str = "<condition>"

        # Loop body start
        body_start = f"while_body:{self._block_counter}"
        self._block_counter += 1
        self._create_block(body_start, line_start=node.lineno)

        # Add loop edge (true branch)
        self._add_edge(cond_block, body_start, EdgeType.LOOP, condition=f"while {cond_str}")

        # Process loop body
        body_prev = body_start
        body_blocks = [body_start]
        for stmt in node.body:
            next_block = self._visit_statement(stmt, body_prev)
            if next_block:
                body_blocks.append(next_block)
                body_prev = next_block

        # Back edge to condition
        self._add_edge(body_prev, cond_block, EdgeType.LOOP)

        # Exit block (false branch)
        exit_block = f"while_exit:{self._block_counter}"
        self._block_counter += 1
        self._create_block(exit_block, line_start=node.lineno)
        self._add_edge(cond_block, exit_block, EdgeType.SEQUENTIAL, condition="else")

        # Record loop
        self._loops.append(
            Loop(
                header=cond_block,
                body=body_blocks,
                back_edge=body_prev,
                loop_type=LoopType.WHILE,
            )
        )

        return exit_block

    def _visit_return(self, node: ast.Return, prev_block: str) -> Optional[str]:
        """
        Visit a return statement.

        Args:
            node: Return AST node
            prev_block: Previous block ID

        Returns:
            None (return exits the function)
        """
        return_block = f"return:{self._block_counter}"
        self._block_counter += 1
        self._create_block(return_block, line_start=node.lineno)
        self._add_edge(prev_block, return_block, EdgeType.SEQUENTIAL)

        try:
            if node.value:
                stmt_str = f"return {ast.unparse(node.value)}"
            else:
                stmt_str = "return"
            self._blocks[return_block].add_statement(stmt_str, node.lineno)
        except Exception:
            self._blocks[return_block].add_statement("<return>", node.lineno)

        # Connect to exit
        self._add_edge(return_block, self._exit_node, EdgeType.JUMP)

        return None

    def _visit_try(self, node: ast.Try, prev_block: str) -> Optional[str]:
        """
        Visit a try-except statement.

        Args:
            node: Try statement AST node
            prev_block: Previous block ID

        Returns:
            Block after try-except
        """
        # Try block start
        try_block = f"try:{self._block_counter}"
        self._block_counter += 1
        self._create_block(try_block, line_start=node.lineno)
        self._add_edge(prev_block, try_block, EdgeType.SEQUENTIAL)

        # Process try body
        try_prev = try_block
        for stmt in node.body:
            next_block = self._visit_statement(stmt, try_prev)
            if next_block:
                try_prev = next_block

        # Exception paths
        catch_blocks = []
        for handler in node.handlers:
            handler_block = f"except:{self._block_counter}"
            self._block_counter += 1
            self._create_block(handler_block, line_start=handler.lineno)

            # Exception type
            exc_type = ""
            if handler.type:
                try:
                    exc_type = ast.unparse(handler.type)
                except Exception:
                    exc_type = "<exception>"

            # Add exception edge
            self._add_edge(
                try_block,
                handler_block,
                EdgeType.EXCEPTION,
                condition=exc_type,
            )

            # Process handler body
            handler_prev = handler_block
            for stmt in handler.body:
                next_block = self._visit_statement(stmt, handler_prev)
                if next_block:
                    handler_prev = next_block

            catch_blocks.append(handler_block)

        # Finally block
        finally_block = None
        if node.finalbody:
            finally_block = f"finally:{self._block_counter}"
            self._block_counter += 1
            self._create_block(finally_block, line_start=node.lineno)

            finally_prev = finally_block
            for stmt in node.finalbody:
                next_block = self._visit_statement(stmt, finally_prev)
                if next_block:
                    finally_prev = next_block

        # Merge block
        merge_block = f"try_merge:{self._block_counter}"
        self._block_counter += 1
        self._create_block(merge_block, line_start=node.lineno)

        # Connect normal flow
        if try_prev != try_block:
            self._add_edge(try_prev, merge_block, EdgeType.SEQUENTIAL)

        # Connect exception handlers
        for cb in catch_blocks:
            self._add_edge(cb, merge_block, EdgeType.SEQUENTIAL)

        # Connect finally
        if finally_block:
            self._add_edge(finally_block, merge_block, EdgeType.SEQUENTIAL)

        # Record exception path
        exc_type = ""
        if node.handlers and node.handlers[0].type:
            try:
                exc_type = ast.unparse(node.handlers[0].type)
            except Exception:
                pass

        self._exception_paths.append(
            ExceptionPath(
                try_block=try_block,
                catch_blocks=catch_blocks,
                finally_block=finally_block,
                exception_type=exc_type,
            )
        )

        return merge_block

    def _visit_with(
        self, node: ast.With | ast.AsyncWith, prev_block: str
    ) -> Optional[str]:
        """
        Visit a with statement.

        Args:
            node: With statement AST node
            prev_block: Previous block ID

        Returns:
            Block after with statement
        """
        # With entry block
        with_block = f"with:{self._block_counter}"
        self._block_counter += 1
        self._create_block(with_block, line_start=node.lineno)
        self._add_edge(prev_block, with_block, EdgeType.SEQUENTIAL)

        # Process with body
        body_prev = with_block
        for stmt in node.body:
            next_block = self._visit_statement(stmt, body_prev)
            if next_block:
                body_prev = next_block

        # With exit (implicit cleanup)
        exit_block = f"with_exit:{self._block_counter}"
        self._block_counter += 1
        self._create_block(exit_block, line_start=node.lineno)
        self._add_edge(body_prev, exit_block, EdgeType.SEQUENTIAL)

        return exit_block

    def _visit_raise(self, node: ast.Raise, prev_block: str) -> Optional[str]:
        """
        Visit a raise statement.

        Args:
            node: Raise AST node
            prev_block: Previous block ID

        Returns:
            None (raise exits normal flow)
        """
        raise_block = f"raise:{self._block_counter}"
        self._block_counter += 1
        self._create_block(raise_block, line_start=node.lineno)
        self._add_edge(prev_block, raise_block, EdgeType.SEQUENTIAL)

        try:
            if node.exc:
                stmt_str = f"raise {ast.unparse(node.exc)}"
            else:
                stmt_str = "raise"
            self._blocks[raise_block].add_statement(stmt_str, node.lineno)
        except Exception:
            self._blocks[raise_block].add_statement("<raise>", node.lineno)

        # Exception edge to exit (unhandled exception)
        self._add_edge(raise_block, self._exit_node, EdgeType.EXCEPTION)

        return None

    def _visit_break(self, node: ast.Break, prev_block: str) -> Optional[str]:
        """
        Visit a break statement.

        Args:
            node: Break AST node
            prev_block: Previous block ID

        Returns:
            None (break exits loop)
        """
        break_block = f"break:{self._block_counter}"
        self._block_counter += 1
        self._create_block(break_block, line_start=node.lineno)
        self._add_edge(prev_block, break_block, EdgeType.SEQUENTIAL)

        # Break edge - would need to find enclosing loop
        # For now, just mark it
        self._blocks[break_block].add_statement("break", node.lineno)

        return None

    def _visit_continue(self, node: ast.Continue, prev_block: str) -> Optional[str]:
        """
        Visit a continue statement.

        Args:
            node: Continue AST node
            prev_block: Previous block ID

        Returns:
            None (continue goes to loop condition)
        """
        continue_block = f"continue:{self._block_counter}"
        self._block_counter += 1
        self._create_block(continue_block, line_start=node.lineno)
        self._add_edge(prev_block, continue_block, EdgeType.SEQUENTIAL)

        # Continue edge - would need to find enclosing loop
        self._blocks[continue_block].add_statement("continue", node.lineno)

        return None

    def _visit_expr(self, node: ast.Expr, prev_block: str) -> Optional[str]:
        """
        Visit an expression statement.

        Args:
            node: Expression AST node
            prev_block: Previous block ID

        Returns:
            Next block ID
        """
        expr_block = f"expr:{self._block_counter}"
        self._block_counter += 1
        self._create_block(expr_block, line_start=node.lineno)
        self._add_edge(prev_block, expr_block, EdgeType.SEQUENTIAL)

        try:
            stmt_str = ast.unparse(node)
            self._blocks[expr_block].add_statement(stmt_str, node.lineno)
        except Exception:
            self._blocks[expr_block].add_statement("<expr>", node.lineno)

        return expr_block

    def _visit_generic(self, node: ast.AST, prev_block: str) -> Optional[str]:
        """
        Visit a generic statement.

        Args:
            node: AST node
            prev_block: Previous block ID

        Returns:
            Next block ID
        """
        generic_block = f"stmt:{self._block_counter}"
        self._block_counter += 1
        self._create_block(generic_block, line_start=node.lineno)
        self._add_edge(prev_block, generic_block, EdgeType.SEQUENTIAL)

        self._blocks[generic_block].add_statement(
            f"<{node.__class__.__name__}>",
            node.lineno if hasattr(node, "lineno") else 0,
        )

        return generic_block

    def _find_loops(self) -> None:
        """Find all loops in the CFG using dominator analysis."""
        # Loops are already tracked during AST visit
        # This method can be used for additional loop detection
        pass

    def get_basic_blocks(self) -> List[BasicBlock]:
        """
        Get all basic blocks in the CFG.

        Returns:
            List of BasicBlock objects
        """
        return list(self._blocks.values())

    def get_edges(self) -> List[CFGEdge]:
        """
        Get all edges in the CFG.

        Returns:
            List of CFGEdge objects
        """
        edges = []
        for source, target, data in self._graph.edges(data=True):
            edge_type = EdgeType(data.get("type", EdgeType.SEQUENTIAL.value))
            condition = data.get("condition")
            edges.append(
                CFGEdge(
                    source=source,
                    target=target,
                    edge_type=edge_type,
                    condition=condition,
                )
            )
        return edges

    def find_loops(self) -> List[Loop]:
        """
        Find all loops in the CFG.

        Returns:
            List of Loop objects
        """
        return self._loops.copy()

    def find_conditionals(self) -> List[Conditional]:
        """
        Find all conditional branches in the CFG.

        Returns:
            List of Conditional objects
        """
        return self._conditionals.copy()

    def find_exception_paths(self) -> List[ExceptionPath]:
        """
        Find all exception handling paths in the CFG.

        Returns:
            List of ExceptionPath objects
        """
        return self._exception_paths.copy()

    def get_reachable_nodes(self, from_node: str, to_node: str) -> List[List[str]]:
        """
        Get all reachable paths between two nodes.

        Args:
            from_node: Source node ID
            to_node: Target node ID

        Returns:
            List of paths (each path is a list of node IDs)
        """
        try:
            # Get all simple paths (limit to prevent explosion)
            paths = list(
                nx.all_simple_paths(
                    self._graph,
                    source=from_node,
                    target=to_node,
                    cutoff=50,  # Limit path length
                )
            )
            return paths
        except nx.NetworkXError as e:
            logger.error(f"Error finding reachable nodes: {e}")
            return []
        except ValueError:
            # Nodes not in graph
            return []

    def get_dominators(self, node: str) -> List[str]:
        """
        Get all dominators of a node.

        A node D dominates node N if every path from the entry node
        to N must go through D.

        Args:
            node: Node ID to find dominators for

        Returns:
            List of dominator node IDs
        """
        try:
            # Compute dominator tree
            dominators = nx.algorithms.dominance.immediate_dominators(
                self._graph, self._entry_node
            )

            # Collect all dominators by walking up the tree
            result = []
            current = node
            while current in dominators:
                dominator = dominators[current]
                if dominator == current:
                    break
                result.append(dominator)
                current = dominator

            return result
        except nx.NetworkXError as e:
            logger.error(f"Error computing dominators: {e}")
            return []
        except KeyError:
            # Node not in graph
            return []

    def get_graph(self) -> nx.DiGraph:
        """
        Get the underlying NetworkX graph.

        Returns:
            NetworkX DiGraph
        """
        return self._graph

    def get_entry_node(self) -> str:
        """
        Get the entry node ID.

        Returns:
            Entry node ID
        """
        return self._entry_node

    def get_exit_node(self) -> str:
        """
        Get the exit node ID.

        Returns:
            Exit node ID
        """
        return self._exit_node
