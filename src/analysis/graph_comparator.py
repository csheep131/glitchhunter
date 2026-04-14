"""
Graph Comparator für GlitchHunter.

Vergleicht Before/After Data-Flow und Call-Graphs um Änderungen
zu erkennen, die durch Patches verursacht wurden.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ChangeType(str, Enum):
    """Typ der Graph-Änderung."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class NodeChange:
    """
    Änderung an einem Graph-Knoten.

    Attributes:
        node_id: Knoten-ID
        change_type: Typ der Änderung
        old_data: Alte Daten (bei MODIFIED)
        new_data: Neue Daten (bei MODIFIED)
        impact: Auswirkung (low, medium, high, critical)
    """

    node_id: str
    change_type: ChangeType
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    impact: str = "low"

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "node_id": self.node_id,
            "change_type": self.change_type.value,
            "old_data": self.old_data,
            "new_data": self.new_data,
            "impact": self.impact,
        }


@dataclass
class EdgeChange:
    """
    Änderung an einer Graph-Kante.

    Attributes:
        source: Quell-Knoten
        target: Ziel-Knoten
        change_type: Typ der Änderung
        edge_data: Kanten-Daten
        impact: Auswirkung
    """

    source: str
    target: str
    change_type: ChangeType
    edge_data: Optional[Dict[str, Any]] = None
    impact: str = "low"

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "source": self.source,
            "target": self.target,
            "change_type": self.change_type.value,
            "edge_data": self.edge_data,
            "impact": self.impact,
        }


@dataclass
class DataFlowChange:
    """
    Änderung im Datenfluss.

    Attributes:
        source: Quell-Variable/Ausdruck
        target: Ziel-Variable/Ausdruck
        change_type: Typ der Änderung
        variable: Betroffene Variable
        path: Datenfluss-Pfad
        security_relevant: Security-relevant
    """

    source: str
    target: str
    change_type: ChangeType
    variable: str
    path: List[str] = field(default_factory=list)
    security_relevant: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "source": self.source,
            "target": self.target,
            "change_type": self.change_type.value,
            "variable": self.variable,
            "path": self.path,
            "security_relevant": self.security_relevant,
        }


@dataclass
class CallChainChange:
    """
    Änderung in einer Call-Chain.

    Attributes:
        caller: Aufrufer
        callee: Aufgerufene Funktion
        change_type: Typ der Änderung
        depth: Tiefe in der Call-Chain
        chain: Vollständige Call-Chain
    """

    caller: str
    callee: str
    change_type: ChangeType
    depth: int = 0
    chain: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "caller": self.caller,
            "callee": self.callee,
            "change_type": self.change_type.value,
            "depth": self.depth,
            "chain": self.chain,
        }


@dataclass
class GraphComparison:
    """
    Ergebnis des Graph-Vergleichs.

    Attributes:
        node_changes: Änderungen an Knoten
        edge_changes: Änderungen an Kanten
        data_flow_changes: Änderungen im Datenfluss
        call_chain_changes: Änderungen in Call-Chains
        breaking_changes: Breaking Changes
        summary: Zusammenfassung
    """

    node_changes: List[NodeChange] = field(default_factory=list)
    edge_changes: List[EdgeChange] = field(default_factory=list)
    data_flow_changes: List[DataFlowChange] = field(default_factory=list)
    call_chain_changes: List[CallChainChange] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_breaking_changes(self) -> bool:
        """True wenn breaking changes vorhanden."""
        return len(self.breaking_changes) > 0

    @property
    def has_security_relevant_changes(self) -> bool:
        """True wenn security-relevante Änderungen."""
        return any(df.security_relevant for df in self.data_flow_changes)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "node_changes": [nc.to_dict() for nc in self.node_changes],
            "edge_changes": [ec.to_dict() for ec in self.edge_changes],
            "data_flow_changes": [df.to_dict() for df in self.data_flow_changes],
            "call_chain_changes": [cc.to_dict() for cc in self.call_chain_changes],
            "breaking_changes": self.breaking_changes,
            "summary": self.summary,
            "has_breaking_changes": self.has_breaking_changes,
            "has_security_relevant_changes": self.has_security_relevant_changes,
        }


class GraphComparator:
    """
    Vergleicht Before/After Graphs.

    Unterstützt:
    - Data-Flow Graphs (DFG)
    - Call-Graphs
    - Control-Flow Graphs (CFG)

    Usage:
        comparator = GraphComparator()
        comparison = comparator.compare(before_graph, after_graph, graph_type="dfg")
    """

    def __init__(self) -> None:
        """Initialisiert Graph Comparator."""
        logger.debug("GraphComparator initialisiert")

    def compare(
        self,
        before_graph: Dict[str, Any],
        after_graph: Dict[str, Any],
        graph_type: str = "dfg",
    ) -> GraphComparison:
        """
        Vergleicht Before/After Graph.

        Args:
            before_graph: Graph vor Patch.
            after_graph: Graph nach Patch.
            graph_type: Typ des Graphen ("dfg", "call", "cfg").

        Returns:
            GraphComparison mit Änderungen.
        """
        logger.info(f"Vergleiche {graph_type}-Graphen")

        comparison = GraphComparison()

        if graph_type == "dfg":
            comparison = self._compare_data_flow_graphs(before_graph, after_graph)
        elif graph_type == "call":
            comparison = self._compare_call_graphs(before_graph, after_graph)
        elif graph_type == "cfg":
            comparison = self._compare_cfg_graphs(before_graph, after_graph)
        else:
            logger.warning(f"Unbekannter Graph-Typ: {graph_type}")
            comparison = self._compare_generic_graphs(before_graph, after_graph)

        # Breaking Changes identifizieren
        comparison.breaking_changes = self._identify_breaking_changes(comparison)

        # Zusammenfassung erstellen
        comparison.summary = self._create_summary(comparison, graph_type)

        logger.info(
            f"Graph-Vergleich abgeschlossen: "
            f"{len(comparison.node_changes)} Knoten-Änderungen, "
            f"{len(comparison.edge_changes)} Kanten-Änderungen, "
            f"{len(comparison.breaking_changes)} Breaking Changes"
        )

        return comparison

    def compare_data_flow(
        self,
        before_dfg: Dict[str, Any],
        after_dfg: Dict[str, Any],
    ) -> GraphComparison:
        """
        Vergleicht Data-Flow Graphen.

        Args:
            before_dfg: DFG vor Patch.
            after_dfg: DFG nach Patch.

        Returns:
            GraphComparison.
        """
        return self.compare(before_dfg, after_dfg, graph_type="dfg")

    def compare_call_graphs(
        self,
        before_cg: Dict[str, Any],
        after_cg: Dict[str, Any],
    ) -> GraphComparison:
        """
        Vergleicht Call-Graphen.

        Args:
            before_cg: Call-Graph vor Patch.
            after_cg: Call-Graph nach Patch.

        Returns:
            GraphComparison.
        """
        return self.compare(before_cg, after_cg, graph_type="call")

    def _compare_data_flow_graphs(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any],
    ) -> GraphComparison:
        """
        Vergleicht Data-Flow Graphen.

        Args:
            before: DFG vor Patch.
            after: DFG nach Patch.

        Returns:
            GraphComparison.
        """
        comparison = GraphComparison()

        # Knoten extrahieren
        before_nodes = set(before.get("nodes", {}).keys())
        after_nodes = set(after.get("nodes", {}).keys())

        # Kanten extrahieren
        before_edges = set()
        for edge in before.get("edges", []):
            before_edges.add((edge.get("source", ""), edge.get("target", "")))

        after_edges = set()
        for edge in after.get("edges", []):
            after_edges.add((edge.get("source", ""), edge.get("target", "")))

        # Knoten-Änderungen
        added_nodes = after_nodes - before_nodes
        removed_nodes = before_nodes - after_nodes
        common_nodes = before_nodes & after_nodes

        for node_id in added_nodes:
            comparison.node_changes.append(NodeChange(
                node_id=node_id,
                change_type=ChangeType.ADDED,
                new_data=after["nodes"].get(node_id),
                impact=self._calculate_node_impact(node_id, "added", after["nodes"].get(node_id)),
            ))

        for node_id in removed_nodes:
            comparison.node_changes.append(NodeChange(
                node_id=node_id,
                change_type=ChangeType.REMOVED,
                old_data=before["nodes"].get(node_id),
                impact=self._calculate_node_impact(node_id, "removed", before["nodes"].get(node_id)),
            ))

        # Geänderte Knoten (gleiche ID, andere Daten)
        for node_id in common_nodes:
            before_data = before["nodes"].get(node_id, {})
            after_data = after["nodes"].get(node_id, {})

            if before_data != after_data:
                comparison.node_changes.append(NodeChange(
                    node_id=node_id,
                    change_type=ChangeType.MODIFIED,
                    old_data=before_data,
                    new_data=after_data,
                    impact=self._calculate_node_impact(node_id, "modified", after_data),
                ))

        # Kanten-Änderungen
        added_edges = after_edges - before_edges
        removed_edges = before_edges - after_edges

        for source, target in added_edges:
            edge_data = self._find_edge_data(after.get("edges", []), source, target)
            comparison.edge_changes.append(EdgeChange(
                source=source,
                target=target,
                change_type=ChangeType.ADDED,
                edge_data=edge_data,
                impact=self._calculate_edge_impact(source, target, "added", edge_data),
            ))

        for source, target in removed_edges:
            edge_data = self._find_edge_data(before.get("edges", []), source, target)
            comparison.edge_changes.append(EdgeChange(
                source=source,
                target=target,
                change_type=ChangeType.REMOVED,
                edge_data=edge_data,
                impact=self._calculate_edge_impact(source, target, "removed", edge_data),
            ))

        # Data-Flow-spezifische Änderungen
        comparison.data_flow_changes = self._extract_data_flow_changes(
            before, after, comparison.edge_changes
        )

        return comparison

    def _compare_call_graphs(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any],
    ) -> GraphComparison:
        """
        Vergleicht Call-Graphen.

        Args:
            before: Call-Graph vor Patch.
            after: Call-Graph nach Patch.

        Returns:
            GraphComparison.
        """
        comparison = GraphComparison()

        # Call-Edges extrahieren
        before_calls = set()
        for edge in before.get("calls", []):
            before_calls.add((edge.get("caller", ""), edge.get("callee", "")))

        after_calls = set()
        for edge in after.get("calls", []):
            after_calls.add((edge.get("caller", ""), edge.get("callee", "")))

        # Hinzugefügte Calls
        added_calls = after_calls - before_calls
        for caller, callee in added_calls:
            comparison.call_chain_changes.append(CallChainChange(
                caller=caller,
                callee=callee,
                change_type=ChangeType.ADDED,
                depth=self._calculate_call_depth(after, caller, callee),
                chain=self._build_call_chain(after, caller, callee),
            ))

        # Entfernte Calls
        removed_calls = before_calls - after_calls
        for caller, callee in removed_calls:
            comparison.call_chain_changes.append(CallChainChange(
                caller=caller,
                callee=callee,
                change_type=ChangeType.REMOVED,
                depth=self._calculate_call_depth(before, caller, callee),
                chain=self._build_call_chain(before, caller, callee),
            ))

        return comparison

    def _compare_cfg_graphs(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any],
    ) -> GraphComparison:
        """
        Vergleicht Control-Flow Graphen.

        Args:
            before: CFG vor Patch.
            after: CFG nach Patch.

        Returns:
            GraphComparison.
        """
        # CFG-Vergleich ähnlich wie DFG, aber mit Fokus auf Control-Flow
        return self._compare_data_flow_graphs(before, after)

    def _compare_generic_graphs(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any],
    ) -> GraphComparison:
        """
        Generischer Graph-Vergleich als Fallback.

        Args:
            before: Graph vor Patch.
            after: Graph nach Patch.

        Returns:
            GraphComparison.
        """
        comparison = GraphComparison()

        # Einfacher Vergleich der Struktur
        before_keys = set(before.keys())
        after_keys = set(after.keys())

        for key in after_keys - before_keys:
            comparison.node_changes.append(NodeChange(
                node_id=key,
                change_type=ChangeType.ADDED,
                new_data=after[key],
            ))

        for key in before_keys - after_keys:
            comparison.node_changes.append(NodeChange(
                node_id=key,
                change_type=ChangeType.REMOVED,
                old_data=before[key],
            ))

        return comparison

    def _extract_data_flow_changes(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any],
        edge_changes: List[EdgeChange],
    ) -> List[DataFlowChange]:
        """
        Extrahiert Data-Flow-spezifische Änderungen.

        Args:
            before: DFG vor Patch.
            after: DFG nach Patch.
            edge_changes: Kanten-Änderungen.

        Returns:
            Liste von DataFlowChange.
        """
        data_flow_changes = []

        for edge_change in edge_changes:
            # Security-relevante Data-Flows erkennen
            security_relevant = self._is_security_relevant_flow(
                edge_change.source, edge_change.target
            )

            data_flow_changes.append(DataFlowChange(
                source=edge_change.source,
                target=edge_change.target,
                change_type=edge_change.change_type,
                variable=edge_change.edge_data.get("variable", "") if edge_change.edge_data else "",
                path=self._find_data_flow_path(before, after, edge_change.source, edge_change.target),
                security_relevant=security_relevant,
            ))

        return data_flow_changes

    def _identify_breaking_changes(
        self,
        comparison: GraphComparison,
    ) -> List[str]:
        """
        Identifiziert Breaking Changes.

        Args:
            comparison: GraphComparison.

        Returns:
            Liste von Breaking Change-Beschreibungen.
        """
        breaking = []

        # Entfernte Knoten sind potenziell breaking
        for node_change in comparison.node_changes:
            if node_change.change_type == ChangeType.REMOVED:
                if node_change.impact in ("high", "critical"):
                    breaking.append(
                        f"Kritischer Knoten entfernt: {node_change.node_id}"
                    )

        # Security-relevante Data-Flow-Änderungen
        for df_change in comparison.data_flow_changes:
            if df_change.security_relevant and df_change.change_type == ChangeType.ADDED:
                breaking.append(
                    f"Neuer security-relevanter Data-Flow: "
                    f"{df_change.source} -> {df_change.target}"
                )

        # Entfernte Calls in öffentlicher API
        for call_change in comparison.call_chain_changes:
            if call_change.change_type == ChangeType.REMOVED:
                if not call_change.caller.startswith("_"):
                    breaking.append(
                        f"Öffentlicher Call entfernt: "
                        f"{call_change.caller} -> {call_change.callee}"
                    )

        return breaking

    def _create_summary(
        self,
        comparison: GraphComparison,
        graph_type: str,
    ) -> Dict[str, Any]:
        """
        Erstellt Zusammenfassung des Vergleichs.

        Args:
            comparison: GraphComparison.
            graph_type: Typ des Graphen.

        Returns:
            Zusammenfassung als Dict.
        """
        return {
            "graph_type": graph_type,
            "total_node_changes": len(comparison.node_changes),
            "total_edge_changes": len(comparison.edge_changes),
            "total_data_flow_changes": len(comparison.data_flow_changes),
            "total_call_chain_changes": len(comparison.call_chain_changes),
            "breaking_changes_count": len(comparison.breaking_changes),
            "has_breaking_changes": comparison.has_breaking_changes,
            "has_security_relevant_changes": comparison.has_security_relevant_changes,
            "added_nodes": sum(
                1 for nc in comparison.node_changes if nc.change_type == ChangeType.ADDED
            ),
            "removed_nodes": sum(
                1 for nc in comparison.node_changes if nc.change_type == ChangeType.REMOVED
            ),
            "modified_nodes": sum(
                1 for nc in comparison.node_changes if nc.change_type == ChangeType.MODIFIED
            ),
        }

    def _calculate_node_impact(
        self,
        node_id: str,
        change_type: str,
        node_data: Optional[Dict[str, Any]],
    ) -> str:
        """
        Berechnet Auswirkung einer Knoten-Änderung.

        Args:
            node_id: Knoten-ID.
            change_type: Typ der Änderung.
            node_data: Knoten-Daten.

        Returns:
            Impact-Level (low, medium, high, critical).
        """
        # Heuristiken für Impact-Berechnung
        if change_type == "removed":
            # Entfernte öffentliche Funktionen sind kritisch
            if node_data and not node_data.get("name", "").startswith("_"):
                return "high"
            return "medium"

        if change_type == "added":
            # Neue Knoten sind meist low impact
            return "low"

        if change_type == "modified":
            # Signatur-Änderungen sind high impact
            if node_data:
                if "signature" in node_data or "parameters" in node_data:
                    return "high"
            return "medium"

        return "low"

    def _calculate_edge_impact(
        self,
        source: str,
        target: str,
        change_type: str,
        edge_data: Optional[Dict[str, Any]],
    ) -> str:
        """
        Berechnet Auswirkung einer Kanten-Änderung.

        Args:
            source: Quell-Knoten.
            target: Ziel-Knoten.
            change_type: Typ der Änderung.
            edge_data: Kanten-Daten.

        Returns:
            Impact-Level.
        """
        # Security-relevante Kanten sind kritisch
        if self._is_security_relevant_flow(source, target):
            return "critical" if change_type == "added" else "high"

        # Datenfluss-Änderungen zu Sinks sind wichtig
        if edge_data and edge_data.get("is_sink", False):
            return "high"

        return "medium" if change_type == "removed" else "low"

    def _is_security_relevant_flow(self, source: str, target: str) -> bool:
        """
        Prüft ob Data-Flow security-relevant ist.

        Args:
            source: Quell-Knoten.
            target: Ziel-Knoten.

        Returns:
            True wenn security-relevant.
        """
        security_keywords = {
            "sql", "query", "execute",  # SQL
            "input", "user_input", "request",  # User Input
            "password", "secret", "token", "key",  # Secrets
            "file", "read", "write",  # File I/O
            "network", "http", "socket",  # Network
            "eval", "exec", "compile",  # Code Execution
        }

        source_lower = source.lower()
        target_lower = target.lower()

        for keyword in security_keywords:
            if keyword in source_lower or keyword in target_lower:
                return True

        return False

    def _find_edge_data(
        self,
        edges: List[Dict[str, Any]],
        source: str,
        target: str,
    ) -> Optional[Dict[str, Any]]:
        """Findet Kanten-Daten für eine Kante."""
        for edge in edges:
            if edge.get("source") == source and edge.get("target") == target:
                return edge
        return None

    def _find_data_flow_path(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any],
        source: str,
        target: str,
    ) -> List[str]:
        """
        Findet Data-Flow-Pfad zwischen Quelle und Ziel.

        Args:
            before: DFG vor Patch.
            after: DFG nach Patch.
            source: Quell-Knoten.
            target: Ziel-Knoten.

        Returns:
            Pfad als Liste von Knoten-IDs.
        """
        # Einfache BFS für Pfad-Findung
        graph = after if source in after.get("nodes", {}) else before
        nodes = graph.get("nodes", {})
        edges = graph.get("edges", [])

        # Adjacency-Liste erstellen
        adjacency: Dict[str, List[str]] = {}
        for edge in edges:
            src = edge.get("source", "")
            tgt = edge.get("target", "")
            if src not in adjacency:
                adjacency[src] = []
            adjacency[src].append(tgt)

        # BFS
        from collections import deque

        queue = deque([(source, [source])])
        visited = {source}

        while queue:
            current, path = queue.popleft()

            if current == target:
                return path

            for neighbor in adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return []

    def _calculate_call_depth(
        self,
        graph: Dict[str, Any],
        caller: str,
        callee: str,
    ) -> int:
        """
        Berechnet Tiefe eines Calls in der Call-Chain.

        Args:
            graph: Call-Graph.
            caller: Aufrufer.
            callee: Aufgerufene Funktion.

        Returns:
            Tiefe des Calls.
        """
        # Einfache Heuristik: Zähle Calls von Entry Point
        entry_points = graph.get("entry_points", [])

        if not entry_points:
            return 1

        # BFS von Entry Points
        from collections import deque

        calls = graph.get("calls", [])
        adjacency: Dict[str, List[str]] = {}
        for call in calls:
            src = call.get("caller", "")
            tgt = call.get("callee", "")
            if src not in adjacency:
                adjacency[src] = []
            adjacency[src].append(tgt)

        for entry in entry_points:
            queue = deque([(entry, 0)])
            visited = {entry}

            while queue:
                current, depth = queue.popleft()

                if current == caller:
                    return depth + 1

                for neighbor in adjacency.get(current, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, depth + 1))

        return 1

    def _build_call_chain(
        self,
        graph: Dict[str, Any],
        caller: str,
        callee: str,
    ) -> List[str]:
        """
        Baut vollständige Call-Chain.

        Args:
            graph: Call-Graph.
            caller: Aufrufer.
            callee: Aufgerufene Funktion.

        Returns:
            Call-Chain als Liste.
        """
        # Einfache Rückverfolgung zu Entry Point
        calls = graph.get("calls", [])

        # Reverse Adjacency-Liste
        reverse_adj: Dict[str, List[str]] = {}
        for call in calls:
            src = call.get("caller", "")
            tgt = call.get("callee", "")
            if tgt not in reverse_adj:
                reverse_adj[tgt] = []
            reverse_adj[tgt].append(src)

        # Rückwärts von caller zu entry point
        chain = [callee, caller]
        current = caller

        while current in reverse_adj:
            parents = reverse_adj[current]
            if not parents:
                break
            # Ersten Parent wählen (einfachste Heuristik)
            current = parents[0]
            chain.insert(0, current)

        return chain

    def __call__(self, state: Any) -> Dict[str, Any]:
        """
        Callable für LangGraph.

        Args:
            state: AgentState.

        Returns:
            State-Updates.
        """
        # TODO: Typisierung verbessern
        before_graph = getattr(state, "before_graph", {})
        after_graph = getattr(state, "after_graph", {})
        graph_type = getattr(state, "graph_type", "dfg")

        comparison = self.compare(before_graph, after_graph, graph_type)

        return {
            "graph_comparison": comparison.to_dict(),
            "metadata": {
                "has_breaking_changes": comparison.has_breaking_changes,
                "has_security_relevant_changes": comparison.has_security_relevant_changes,
                "breaking_changes_count": len(comparison.breaking_changes),
            },
        }
