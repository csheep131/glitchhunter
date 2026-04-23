"""
Feature Extractor für Glitch Prediction.

Extrahiert ML-Features aus:
- Symbol-Graphen (NetworkX)
- Complexity-Metriken
- AST-Informationen
- Git Churn-Daten
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """
    Extrahiert ML-Features aus Code-Analyse-Daten.

    Usage:
        extractor = FeatureExtractor()
        features = extractor.extract_from_symbol_graph(symbol_graph, symbol_id)
    """

    # Feature-Dimensionen
    GRAPH_FEATURES = 8
    COMPLEXITY_FEATURES = 8
    STRUCTURAL_FEATURES = 8
    HISTORY_FEATURES = 8
    TOTAL_FEATURES = 32

    def __init__(self):
        """Initialisiert den Feature Extractor."""
        logger.info(f"FeatureExtractor initialisiert ({self.TOTAL_FEATURES} Dimensionen)")

    def extract_from_symbol_graph(
        self,
        symbol_graph: nx.DiGraph,
        symbol_id: str,
    ) -> Optional["FeatureVector"]:
        """
        Extrahiert Features aus einem Symbol-Graph.

        Args:
            symbol_graph: NetworkX DiGraph
            symbol_id: ID des Symbols

        Returns:
            FeatureVector oder None bei Fehler
        """
        try:
            if symbol_id not in symbol_graph:
                logger.debug(f"Symbol {symbol_id} nicht im Graph")
                return None

            # Graph-basierte Features
            graph_features = self._extract_graph_features(symbol_graph, symbol_id)

            # Strukturelle Features
            structural_features = self._extract_structural_features(symbol_graph, symbol_id)

            # Placeholder für Complexity und History
            complexity_features = np.zeros(self.COMPLEXITY_FEATURES)
            history_features = np.zeros(self.HISTORY_FEATURES)

            # Alle Features kombinieren
            all_features = np.concatenate([
                graph_features,
                complexity_features,
                structural_features,
                history_features,
            ])

            # Metadata extrahieren
            node_data = symbol_graph.nodes[symbol_id]
            metadata = {
                "symbol_type": node_data.get("type", "unknown"),
                "file_path": node_data.get("file_path", "unknown"),
            }

            from prediction.types import FeatureVector

            return FeatureVector(
                symbol_name=node_data.get("name", symbol_id),
                file_path=metadata["file_path"],
                features=all_features,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return None

    def _extract_graph_features(
        self,
        graph: nx.DiGraph,
        node_id: str,
    ) -> np.ndarray:
        """
        Extrahiert graph-basierte Features.

        Features:
        1. In-Degree (Anzahl eingehender Kanten)
        2. Out-Degree (Anzahl ausgehender Kanten)
        3. Total Degree
        4. In-Degree Centrality (normalisiert)
        5. Out-Degree Centrality (normalisiert)
        6. Betweenness Centrality
        7. PageRank Score
        8. Hub Score (HITS Algorithmus)

        Args:
            graph: NetworkX DiGraph
            node_id: Node ID

        Returns:
            8-dimensionaler numpy array
        """
        features = np.zeros(self.GRAPH_FEATURES)

        try:
            # Degree-basierte Features
            in_degree = graph.in_degree(node_id)
            out_degree = graph.out_degree(node_id)
            total_degree = in_degree + out_degree

            features[0] = in_degree
            features[1] = out_degree
            features[2] = total_degree

            # Centrality Features (normalisiert)
            n_nodes = len(graph)
            if n_nodes > 1:
                features[3] = in_degree / (n_nodes - 1)
                features[4] = out_degree / (n_nodes - 1)

            # Betweenness Centrality
            try:
                betweenness = nx.betweenness_centrality(graph, k=min(100, n_nodes))
                features[5] = betweenness.get(node_id, 0.0)
            except Exception:
                features[5] = 0.0

            # PageRank
            try:
                pagerank = nx.pagerank(graph, max_iter=100)
                features[6] = pagerank.get(node_id, 0.0)
            except Exception:
                features[6] = 0.0

            # Hub Score (HITS)
            try:
                hubs, _ = nx.hits(graph, max_iter=100)
                features[7] = hubs.get(node_id, 0.0)
            except Exception:
                features[7] = 0.0

            # Log-Transformation für stark variierende Werte
            features[0:3] = np.log1p(features[0:3])

        except Exception as e:
            logger.warning(f"Graph features extraction failed: {e}")

        return features

    def _extract_structural_features(
        self,
        graph: nx.DiGraph,
        node_id: str,
    ) -> np.ndarray:
        """
        Extrahiert strukturelle Features.

        Args:
            graph: NetworkX DiGraph
            node_id: Node ID

        Returns:
            8-dimensionaler numpy array
        """
        features = np.zeros(self.STRUCTURAL_FEATURES)

        try:
            # Nachbarn
            predecessors = list(graph.predecessors(node_id))
            successors = list(graph.successors(node_id))
            all_neighbors = set(predecessors) | set(successors)

            features[0] = len(all_neighbors)
            features[1] = min(50, len(all_neighbors) ** 2)

            # Clustering Coefficient
            try:
                clustering = nx.clustering(graph.to_undirected(), node_id)
                features[2] = clustering
            except Exception:
                features[2] = 0.0

            # Triangle Count
            try:
                triangles = nx.triangles(graph.to_undirected(), node_id)
                features[3] = triangles
            except Exception:
                features[3] = 0

            # Closeness Centrality
            try:
                closeness = nx.closeness_centrality(graph, node_id)
                features[5] = closeness
            except Exception:
                features[5] = 0.0

            # Is Leaf Node
            features[7] = 1.0 if (len(predecessors) == 0 and len(successors) > 0) else 0.0

            # Log-Transformation
            features[0:2] = np.log1p(features[0:2])

        except Exception as e:
            logger.warning(f"Structural features extraction failed: {e}")

        return features

    def batch_extract(
        self,
        symbol_graph: nx.DiGraph,
        complexity_data: Optional[Dict[str, Dict[str, Any]]] = None,
        git_data: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List["FeatureVector"]:
        """
        Extrahiert Features für alle Symbole im Graph.

        Args:
            symbol_graph: NetworkX DiGraph
            complexity_data: Optionale Complexity-Daten
            git_data: Optionale Git-Daten

        Returns:
            Liste von FeatureVector
        """
        logger.info(f"Batch extraction für {len(symbol_graph)} Symbole")

        feature_vectors = []

        for node_id in symbol_graph.nodes():
            vector = self.extract_from_symbol_graph(symbol_graph, node_id)

            if vector:
                feature_vectors.append(vector)

        logger.info(f"Extrahiert {len(feature_vectors)} feature vectors")

        return feature_vectors

    def create_feature_matrix(
        self,
        feature_vectors: List["FeatureVector"],
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Erstellt Feature-Matrix für ONNX-Modell.

        Args:
            feature_vectors: Liste von FeatureVectors

        Returns:
            Tuple (Feature-Matrix, Symbol-IDs)
        """
        if not feature_vectors:
            return np.array([]), []

        # Matrix erstellen
        matrix = np.vstack([fv.features for fv in feature_vectors])
        symbol_ids = [fv.symbol_name for fv in feature_vectors]

        logger.info(f"Feature matrix shape: {matrix.shape}")

        return matrix, symbol_ids


@dataclass
class FeatureVector:
    """
    Feature-Vektor für ein Code-Symbol.

    Attributes:
        symbol_name: Name des Symbols
        file_path: Dateipfad
        features: 32-dimensionaler Feature-Vektor
        metadata: Zusätzliche Metadaten
    """

    symbol_name: str
    file_path: str
    features: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def dimension(self) -> int:
        """Dimension des Feature-Vektors."""
        return len(self.features)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "symbol_name": self.symbol_name,
            "file_path": self.file_path,
            "features": self.features.tolist(),
            "metadata": self.metadata,
        }
