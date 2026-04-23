"""
Graph-basierte Feature-Extraktion.

Extrahiert Features aus Symbol-Graphen:
- Degree-basierte Features
- Centrality Measures
- PageRank und HITS
"""

import logging
from typing import Any, Dict

import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)


class GraphFeatureExtractor:
    """
    Extrahiert graph-basierte Features aus NetworkX Graphen.

    Usage:
        extractor = GraphFeatureExtractor()
        features = extractor.extract(graph, node_id)
    """

    def __init__(self):
        """Initialisiert den Graph Feature Extractor."""
        logger.info("GraphFeatureExtractor initialisiert")

    def extract(
        self,
        graph: nx.DiGraph,
        node_id: str,
    ) -> np.ndarray:
        """
        Extrahiert alle graph-basierten Features.

        Args:
            graph: NetworkX DiGraph
            node_id: Node ID

        Returns:
            8-dimensionaler numpy array
        """
        features = np.zeros(8)

        try:
            # Degree-basierte Features
            in_degree = graph.in_degree(node_id)
            out_degree = graph.out_degree(node_id)
            total_degree = in_degree + out_degree

            features[0] = in_degree
            features[1] = out_degree
            features[2] = total_degree

            # Centrality Features
            n_nodes = len(graph)
            if n_nodes > 1:
                features[3] = in_degree / (n_nodes - 1)
                features[4] = out_degree / (n_nodes - 1)

            # Betweenness Centrality
            features[5] = self._compute_betweenness(graph, node_id)

            # PageRank
            features[6] = self._compute_pagerank(graph, node_id)

            # Hub Score
            features[7] = self._compute_hub_score(graph, node_id)

            # Log-Transformation
            features[0:3] = np.log1p(features[0:3])

        except Exception as e:
            logger.warning(f"Graph feature extraction failed: {e}")

        return features

    def _compute_betweenness(
        self,
        graph: nx.DiGraph,
        node_id: str,
    ) -> float:
        """
        Berechnet Betweenness Centrality.

        Args:
            graph: NetworkX Graph
            node_id: Node ID

        Returns:
            Betweenness Wert
        """
        try:
            n_nodes = len(graph)
            betweenness = nx.betweenness_centrality(graph, k=min(100, n_nodes))
            return betweenness.get(node_id, 0.0)
        except Exception:
            return 0.0

    def _compute_pagerank(
        self,
        graph: nx.DiGraph,
        node_id: str,
    ) -> float:
        """
        Berechnet PageRank Score.

        Args:
            graph: NetworkX Graph
            node_id: Node ID

        Returns:
            PageRank Wert
        """
        try:
            pagerank = nx.pagerank(graph, max_iter=100)
            return pagerank.get(node_id, 0.0)
        except Exception:
            return 0.0

    def _compute_hub_score(
        self,
        graph: nx.DiGraph,
        node_id: str,
    ) -> float:
        """
        Berechnet Hub Score (HITS Algorithmus).

        Args:
            graph: NetworkX Graph
            node_id: Node ID

        Returns:
            Hub Score
        """
        try:
            hubs, _ = nx.hits(graph, max_iter=100)
            return hubs.get(node_id, 0.0)
        except Exception:
            return 0.0

    def get_feature_names(self) -> list[str]:
        """
        Returns Namen der Features.

        Returns:
            Liste von Feature-Namen
        """
        return [
            "in_degree",
            "out_degree",
            "total_degree",
            "in_degree_centrality",
            "out_degree_centrality",
            "betweenness_centrality",
            "pagerank_score",
            "hub_score",
        ]
