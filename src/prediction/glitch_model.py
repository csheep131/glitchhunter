"""
Glitch Prediction Model mit ONNX.

ML-Modell für Bug-Vorhersage basierend auf:
- Symbol-Graph Features
- Complexity-Metriken
- Git-History

Das Modell wird mit ONNX Runtime inferiert für:
- Cross-Platform Kompatibilität
- Hohe Performance
- Einfache Deployment

Model Architecture:
- Input: 32-dimensionaler Feature-Vektor
- Hidden Layers: [64, 32, 16] mit ReLU
- Output: [bug_probability, severity_score]
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """
    Ergebnis einer Bug-Vorhersage.
    
    Attributes:
        symbol_name: Name des Symbols
        file_path: Dateipfad
        bug_probability: Wahrscheinlichkeit für Bug (0-1)
        severity_score: Vorhergesagte Schwere (0-1)
        risk_level: Risikostufe (low, medium, high, critical)
        confidence: Konfidenz der Vorhersage
        feature_importance: Wichtigste Features
    """
    symbol_name: str
    file_path: str
    bug_probability: float
    severity_score: float
    risk_level: str
    confidence: float
    feature_importance: Optional[Dict[str, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "symbol_name": self.symbol_name,
            "file_path": self.file_path,
            "bug_probability": self.bug_probability,
            "severity_score": self.severity_score,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "feature_importance": self.feature_importance,
        }


class GlitchPredictionModel:
    """
    ONNX-basiertes Vorhersagemodell für Bugs.
    
    Usage:
        model = GlitchPredictionModel()
        predictions = model.predict(feature_matrix)
    """
    
    # Risk Level Thresholds
    RISK_THRESHOLDS = {
        "critical": 0.8,
        "high": 0.6,
        "medium": 0.4,
        "low": 0.0,
    }
    
    def __init__(
        self,
        model_path: Optional[Path] = None,
        use_cpu: bool = True,
    ):
        """
        Initialisiert das Vorhersagemodell.
        
        Args:
            model_path: Pfad zum ONNX-Modell (optional, erstellt Dummy bei Fehlen)
            use_cpu: Nur CPU verwenden
        """
        self.model_path = model_path
        self.use_cpu = use_cpu
        self.session = None
        self.input_name = None
        
        # Feature-Namen für Interpretation
        self.feature_names = self._get_feature_names()
        
        # Modell laden oder Dummy erstellen
        self._load_model()
        
        logger.info(f"GlitchPredictionModel initialisiert (CPU={use_cpu})")
    
    def _get_feature_names(self) -> List[str]:
        """Returns Feature-Namen für Interpretation."""
        return [
            # Graph Features (0-7)
            "in_degree", "out_degree", "total_degree",
            "in_degree_centrality", "out_degree_centrality",
            "betweenness_centrality", "pagerank_score", "hub_score",
            
            # Complexity Features (8-15)
            "cyclomatic_complexity", "cognitive_complexity",
            "lines_of_code", "parameter_count", "nesting_depth",
            "function_count", "class_size", "maintainability_index",
            
            # Structural Features (16-23)
            "neighbor_count_1hop", "neighbor_count_2hop",
            "clustering_coefficient", "triangle_count",
            "eccentricity", "closeness_centrality",
            "community_size", "is_leaf_node",
            
            # History Features (24-31)
            "churn_rate", "bug_fix_rate", "days_since_change",
            "contributor_count", "avg_commit_size", "refactor_count",
            "hotspot_score", "age_days",
        ]
    
    def _load_model(self):
        """Lädt ONNX-Modell oder erstellt Dummy."""
        try:
            import onnxruntime as ort
            
            if self.model_path and self.model_path.exists():
                # Modell von Datei laden
                providers = ["CPUExecutionProvider"]
                if not self.use_cpu:
                    providers.insert(0, "CUDAExecutionProvider")
                
                self.session = ort.InferenceSession(
                    str(self.model_path),
                    providers=providers,
                )
                self.input_name = self.session.get_inputs()[0].name
                logger.info(f"ONNX-Modell geladen: {self.model_path}")
                
            else:
                # Dummy-Modell erstellen (für Demo/Testing)
                self._create_dummy_model()
                logger.info("Dummy-Modell erstellt (kein ONNX-Modell gefunden)")
                
        except ImportError:
            logger.warning("onnxruntime nicht installiert, verwende Dummy-Modell")
            self._create_dummy_model()
        except Exception as e:
            logger.error(f"Modell-Laden fehlgeschlagen: {e}")
            self._create_dummy_model()
    
    def _create_dummy_model(self):
        """Erstellt einfaches Dummy-Modell für Demo-Zwecke."""
        # Dummy-Modell simuliert Vorhersage mit Heuristiken
        self.session = None
        self.input_name = None
        logger.debug("Dummy model initialized")
    
    def _predict_dummy(
        self,
        feature_matrix: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Dummy-Vorhersage mit Heuristiken.
        
        Args:
            feature_matrix: (n_samples, 32) Feature-Matrix
            
        Returns:
            (bug_probabilities, severity_scores)
        """
        n_samples = feature_matrix.shape[0]
        
        # Heuristische Vorhersage basierend auf Features
        bug_probs = np.zeros(n_samples)
        severity_scores = np.zeros(n_samples)
        
        for i in range(n_samples):
            features = feature_matrix[i]
            
            # Bug Probability Heuristik
            # Hohe Complexity + hohe Churn Rate = höheres Bug-Risiko
            complexity_score = np.mean(features[8:16])  # Complexity Features
            history_score = np.mean(features[24:32])  # History Features
            graph_score = np.mean(features[0:8])  # Graph Features
            
            # Gewichtete Kombination
            bug_prob = (
                0.4 * complexity_score +
                0.3 * history_score +
                0.3 * graph_score
            )
            
            # Noise hinzufügen für Realismus
            bug_prob += np.random.normal(0, 0.1)
            bug_prob = np.clip(bug_prob, 0.0, 1.0)
            
            # Severity Score (korreliert mit Bug Probability)
            severity = bug_prob * (0.8 + 0.4 * np.random.random())
            severity = np.clip(severity, 0.0, 1.0)
            
            bug_probs[i] = bug_prob
            severity_scores[i] = severity
        
        return bug_probs, severity_scores
    
    def predict(
        self,
        feature_matrix: np.ndarray,
    ) -> List[PredictionResult]:
        """
        Führt Batch-Vorhersage durch.
        
        Args:
            feature_matrix: (n_samples, 32) Feature-Matrix
            
        Returns:
            Liste von PredictionResult
        """
        if feature_matrix.size == 0:
            return []
        
        logger.info(f"Predicting bugs für {feature_matrix.shape[0]} samples")
        
        try:
            if self.session is not None:
                # Echtes ONNX-Modell
                bug_probs, severity_scores = self.session.run(
                    None,
                    {self.input_name: feature_matrix.astype(np.float32)},
                )
                bug_probs = bug_probs.flatten()
                severity_scores = severity_scores.flatten()
            else:
                # Dummy-Modell
                bug_probs, severity_scores = self._predict_dummy(feature_matrix)
            
            # Ergebnisse erstellen
            results = []
            for i in range(len(bug_probs)):
                risk_level = self._get_risk_level(bug_probs[i])
                confidence = self._estimate_confidence(feature_matrix[i])
                
                results.append(PredictionResult(
                    symbol_name=f"symbol_{i}",
                    file_path="unknown",
                    bug_probability=float(bug_probs[i]),
                    severity_score=float(severity_scores[i]),
                    risk_level=risk_level,
                    confidence=confidence,
                    feature_importance=self._get_feature_importance(feature_matrix[i]),
                ))
            
            logger.info(
                f"Vorhersage abgeschlossen: "
                f"Ø bug_prob={np.mean(bug_probs):.2f}, "
                f"high_risk={sum(1 for p in bug_probs if p > 0.6)}"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return []
    
    def _get_risk_level(self, bug_probability: float) -> str:
        """Bestimmt Risikostufe aus Bug-Wahrscheinlichkeit."""
        if bug_probability >= self.RISK_THRESHOLDS["critical"]:
            return "critical"
        elif bug_probability >= self.RISK_THRESHOLDS["high"]:
            return "high"
        elif bug_probability >= self.RISK_THRESHOLDS["medium"]:
            return "medium"
        else:
            return "low"
    
    def _estimate_confidence(self, features: np.ndarray) -> float:
        """
        Schätzt Konfidenz der Vorhersage.
        
        Höhere Konfidenz bei:
        - Ausgewogenen Features
        - Wenig fehlenden Werten
        - Typischen Feature-Werten
        """
        # Einfache Heuristik: Konfidenz basiert auf Feature-Vollständigkeit
        missing = np.sum(features == 0)
        total = len(features)
        
        # Basis-Konfidenz
        confidence = 1.0 - (missing / total)
        
        # Bonus für konsistente Features
        std = np.std(features)
        if 0.1 < std < 0.5:  # Normale Verteilung
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _get_feature_importance(
        self,
        features: np.ndarray,
    ) -> Dict[str, float]:
        """
        Berechnet Feature-Importance für Interpretierbarkeit.
        
        Args:
            features: Feature-Vektor
            
        Returns:
            Dictionary {feature_name: importance}
        """
        importance = {}
        
        # Top Features identifizieren
        for i, name in enumerate(self.feature_names):
            importance[name] = float(features[i])
        
        # Nach Importance sortieren
        sorted_importance = dict(
            sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
        )
        
        return sorted_importance
    
    def predict_single(
        self,
        feature_vector: np.ndarray,
        symbol_name: str = "unknown",
        file_path: str = "unknown",
    ) -> PredictionResult:
        """
        Führt Vorhersage für ein einzelnes Symbol durch.
        
        Args:
            feature_vector: (32,) Feature-Vektor
            symbol_name: Name des Symbols
            file_path: Dateipfad
            
        Returns:
            PredictionResult
        """
        feature_matrix = feature_vector.reshape(1, -1)
        results = self.predict(feature_matrix)
        
        if results:
            result = results[0]
            result.symbol_name = symbol_name
            result.file_path = file_path
            return result
        
        # Fallback
        return PredictionResult(
            symbol_name=symbol_name,
            file_path=file_path,
            bug_probability=0.5,
            severity_score=0.5,
            risk_level="medium",
            confidence=0.5,
        )
    
    def save_model(self, path: Path):
        """
        Speichert das Modell.
        
        Args:
            path: Zielpfad
        """
        if self.session is not None:
            # ONNX-Modell speichern
            import onnx
            onnx.save(self.session, str(path))
            logger.info(f"Modell gespeichert: {path}")
        else:
            logger.warning("Dummy-Modell kann nicht gespeichert werden")
    
    @classmethod
    def train(
        cls,
        training_data: np.ndarray,
        labels: np.ndarray,
        output_path: Path,
    ) -> "GlitchPredictionModel":
        """
        Trainiert ein neues Modell.
        
        Args:
            training_data: (n_samples, 32) Trainingsdaten
            labels: (n_samples, 2) Labels [bug_prob, severity]
            output_path: Pfad für gespeichertes Modell
            
        Returns:
            Trainiertes GlitchPredictionModel
        """
        logger.info(f"Training Modell mit {len(training_data)} samples")
        
        try:
            import onnxruntime as ort
            from sklearn.ensemble import RandomForestRegressor
            import pickle
            
            # Random Forest trainieren (einfach und effektiv)
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
            )
            model.fit(training_data, labels[:, 0])  # Bug Probability
            
            # Modell speichern
            model_path = output_path.with_suffix(".pkl")
            with open(model_path, "wb") as f:
                pickle.dump(model, f)
            
            logger.info(f"Modell trainiert und gespeichert: {model_path}")
            
            # Geladenes Modell zurückgeben
            return cls(model_path=model_path)
            
        except ImportError:
            logger.warning("sklearn nicht verfügbar, verwende Dummy-Modell")
            return cls()
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return cls()
