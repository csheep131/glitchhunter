"""
Feature Extractor für Glitch Prediction.

Extrahiert ML-Features aus:
- Symbol-Graphen (NetworkX)
- Complexity-Metriken
- AST-Informationen
- Git Churn-Daten

Features:
1. Graph-basierte Features (Symbol-Graph)
   - Node Degree (in/out)
   - Betweenness Centrality
   - PageRank Score
   - Community-Zugehörigkeit

2. Complexity Features
   - Cyclomatic Complexity
   - Cognitive Complexity
   - Lines of Code
   - Parameter Count

3. Code Quality Features
   - Churn Rate (Git)
   - Bug-History
   - Test Coverage
"""

import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)


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


class FeatureExtractor:
    """
    Extrahiert ML-Features aus Code-Analyse-Daten.
    
    Usage:
        extractor = FeatureExtractor()
        features = extractor.extract(symbol_graph, complexity_metrics)
    """
    
    # Feature-Dimensionen
    GRAPH_FEATURES = 8  # Graph-basierte Features
    COMPLEXITY_FEATURES = 8  # Complexity-Metriken
    STRUCTURAL_FEATURES = 8  # Strukturelle Features
    HISTORY_FEATURES = 8  # Historie-Features
    TOTAL_FEATURES = GRAPH_FEATURES + COMPLEXITY_FEATURES + STRUCTURAL_FEATURES + HISTORY_FEATURES
    
    def __init__(self):
        """Initialisiert den Feature Extractor."""
        logger.info(f"FeatureExtractor initialisiert ({self.TOTAL_FEATURES} Dimensionen)")
    
    def extract_from_symbol_graph(
        self,
        symbol_graph: nx.DiGraph,
        symbol_id: str,
    ) -> Optional[FeatureVector]:
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
            
            # Placeholder für Complexity und History (werden separat extrahiert)
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
                features[3] = in_degree / (n_nodes - 1)  # In-Degree Centrality
                features[4] = out_degree / (n_nodes - 1)  # Out-Degree Centrality
            
            # Betweenness Centrality (teuer, nur wenn benötigt)
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
        
        Features:
        1. Anzahl direkter Nachbarn (1-hop)
        2. Anzahl 2-hop Nachbarn
        3. Clustering Coefficient
        4. Triangle Count
        5. Eccentricity (maximale Distanz)
        6. Closeness Centrality
        7. Community Size (wenn detektiert)
        8. Is Leaf Node (Boolean)
        
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
            
            features[0] = len(all_neighbors)  # 1-hop neighbors
            features[1] = min(50, len(all_neighbors) ** 2)  # 2-hop Schätzung
            
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
            
            # Eccentricity (nur wenn connected)
            try:
                if nx.is_connected(graph.to_undirected()):
                    eccentricity = nx.eccentricity(graph.to_undirected(), node_id)
                    features[4] = 1.0 / (1.0 + eccentricity)  # Invers normalisiert
            except Exception:
                features[4] = 0.0
            
            # Closeness Centrality
            try:
                closeness = nx.closeness_centrality(graph, node_id)
                features[5] = closeness
            except Exception:
                features[5] = 0.0
            
            # Community Size (einfache Heuristik)
            try:
                communities = nx.community.greedy_modularity_communities(graph.to_undirected())
                for comm in communities:
                    if node_id in comm:
                        features[6] = min(100, len(comm))
                        break
            except Exception:
                features[6] = 0.0
            
            # Is Leaf Node
            features[7] = 1.0 if (len(predecessors) == 0 and len(successors) > 0) else 0.0
            
            # Log-Transformation
            features[0:2] = np.log1p(features[0:2])
            
        except Exception as e:
            logger.warning(f"Structural features extraction failed: {e}")
        
        return features
    
    def add_complexity_features(
        self,
        feature_vector: FeatureVector,
        complexity_metrics: Dict[str, Any],
    ) -> FeatureVector:
        """
        Fügt Complexity-Features hinzu.
        
        Features:
        1. Cyclomatic Complexity (normalisiert)
        2. Cognitive Complexity
        3. Lines of Code (log)
        4. Parameter Count
        5. Nested Depth
        6. Function Count (in File)
        7. Class Size (wenn applicable)
        8. Maintenance Index
        
        Args:
            feature_vector: Bestehender Feature-Vektor
            complexity_metrics: Complexity-Metriken
            
        Returns:
            Aktualisierter FeatureVector
        """
        try:
            complexity = np.zeros(self.COMPLEXITY_FEATURES)
            
            # Cyclomatic Complexity
            cc = complexity_metrics.get("cyclomatic", 1)
            complexity[0] = min(100, cc) / 100.0
            
            # Cognitive Complexity
            cog = complexity_metrics.get("cognitive", 0)
            complexity[1] = min(100, cog) / 100.0
            
            # Lines of Code
            loc = complexity_metrics.get("lines", 0)
            complexity[2] = np.log1p(loc) / 10.0
            
            # Parameter Count
            params = complexity_metrics.get("parameters", 0)
            complexity[3] = min(10, params) / 10.0
            
            # Nesting Depth
            depth = complexity_metrics.get("nesting", 1)
            complexity[4] = min(10, depth) / 10.0
            
            # Function Count
            funcs = complexity_metrics.get("function_count", 1)
            complexity[5] = np.log1p(funcs) / 5.0
            
            # Class Size
            class_size = complexity_metrics.get("class_size", 0)
            complexity[6] = min(500, class_size) / 500.0
            
            # Maintainability Index (0-100)
            mi = complexity_metrics.get("maintainability", 50)
            complexity[7] = (100 - mi) / 100.0  # Invertiert (höher = schlechter)
            
            # In place update
            feature_vector.features[
                self.GRAPH_FEATURES:self.GRAPH_FEATURES + self.COMPLEXITY_FEATURES
            ] = complexity
            
            feature_vector.metadata["complexity"] = complexity_metrics
            
        except Exception as e:
            logger.warning(f"Complexity features addition failed: {e}")
        
        return feature_vector
    
    def add_history_features(
        self,
        feature_vector: FeatureVector,
        git_metrics: Dict[str, Any],
    ) -> FeatureVector:
        """
        Fügt Git-History-Features hinzu.
        
        Features:
        1. Churn Rate (commits pro Monat)
        2. Bug Fix Rate
        3. Days Since Last Change
        4. Contributor Count
        5. Avg Commit Size
        6. Refactor Count
        7. Hotspot Score
        8. Age (Tage seit erstem Commit)
        
        Args:
            feature_vector: Bestehender Feature-Vektor
            git_metrics: Git-Metriken
            
        Returns:
            Aktualisierter FeatureVector
        """
        try:
            history = np.zeros(self.HISTORY_FEATURES)
            
            # Churn Rate
            churn = git_metrics.get("churn_rate", 0)
            history[0] = min(50, churn) / 50.0
            
            # Bug Fix Rate
            bug_rate = git_metrics.get("bug_fixes", 0)
            history[1] = min(20, bug_rate) / 20.0
            
            # Days Since Last Change
            days = git_metrics.get("days_since_change", 30)
            history[2] = 1.0 - min(365, days) / 365.0  # Neuere Änderungen = höher
            
            # Contributor Count
            contributors = git_metrics.get("contributors", 1)
            history[3] = min(20, contributors) / 20.0
            
            # Avg Commit Size
            commit_size = git_metrics.get("avg_commit_size", 50)
            history[4] = min(1000, commit_size) / 1000.0
            
            # Refactor Count
            refactors = git_metrics.get("refactors", 0)
            history[5] = min(10, refactors) / 10.0
            
            # Hotspot Score
            hotspot = git_metrics.get("hotspot_score", 0)
            history[6] = min(1.0, hotspot)
            
            # Age
            age = git_metrics.get("age_days", 0)
            history[7] = min(1000, age) / 1000.0
            
            # In place update
            feature_vector.features[
                self.GRAPH_FEATURES + self.COMPLEXITY_FEATURES + self.STRUCTURAL_FEATURES:
            ] = history
            
            feature_vector.metadata["git"] = git_metrics
            
        except Exception as e:
            logger.warning(f"History features addition failed: {e}")
        
        return feature_vector
    
    def batch_extract(
        self,
        symbol_graph: nx.DiGraph,
        complexity_data: Optional[Dict[str, Dict[str, Any]]] = None,
        git_data: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[FeatureVector]:
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
                # Complexity hinzufügen wenn verfügbar
                if complexity_data and vector.file_path in complexity_data:
                    vector = self.add_complexity_features(
                        vector, complexity_data[vector.file_path]
                    )
                
                # Git-Daten hinzufügen wenn verfügbar
                if git_data and vector.file_path in git_data:
                    vector = self.add_history_features(vector, git_data[vector.file_path])
                
                feature_vectors.append(vector)
        
        logger.info(f"Extrahiert {len(feature_vectors)} feature vectors")
        
        return feature_vectors
    
    def create_feature_matrix(
        self,
        feature_vectors: List[FeatureVector],
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
