"""
Prediction Engine für GlitchHunter v3.0.

Integriert ML-basierte Bug-Vorhersage in den Swarm Coordinator.
Kombiniert Vorhersagen mit statischen und dynamischen Findings.

Features:
- Batch-Prediction für gesamte Repositories
- Kombination mit Swarm Findings
- Risk-Prioritization
- Erklärbare Vorhersagen (Feature Importance)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import networkx as nx

from prediction.feature_extractor import FeatureExtractor, FeatureVector
from prediction.glitch_model import GlitchPredictionModel, PredictionResult

logger = logging.getLogger(__name__)


@dataclass
class PredictionFinding:
    """
    Finding aus ML-Vorhersage.
    
    Attributes:
        id: Eindeutige ID
        file_path: Betroffene Datei
        line_start: Startzeile
        line_end: Endzeile
        severity: Schweregrad (critical, high, medium, low)
        category: Kategorie (ml_prediction)
        title: Kurzer Titel
        description: Detaillierte Beschreibung
        bug_probability: Vorhergesagte Bug-Wahrscheinlichkeit
        confidence: Konfidenz der Vorhersage
        feature_importance: Wichtigste Features
        metadata: Zusätzliche Metadaten
    """
    id: str
    file_path: str
    line_start: int
    line_end: int
    severity: str
    category: str
    title: str
    description: str
    bug_probability: float
    confidence: float
    feature_importance: Optional[Dict[str, float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "bug_probability": self.bug_probability,
            "confidence": self.confidence,
            "feature_importance": self.feature_importance,
            "metadata": self.metadata,
        }


class PredictionEngine:
    """
    Engine für ML-basierte Bug-Vorhersage.
    
    Integration in Swarm Coordinator:
    1. Extrahiere Features aus Symbol-Graph
    2. Führe Batch-Prediction durch
    3. Kombiniere mit anderen Findings
    4. Priorisiere nach Risiko
    
    Usage:
        engine = PredictionEngine()
        findings = await engine.predict(repo_path, symbol_graph)
    """
    
    def __init__(
        self,
        model_path: Optional[Path] = None,
        use_cpu: bool = True,
        min_probability: float = 0.4,
    ):
        """
        Initialisiert die Prediction Engine.
        
        Args:
            model_path: Pfad zum ONNX-Modell
            use_cpu: Nur CPU verwenden
            min_probability: Minimale Bug-Wahrscheinlichkeit für Findings
        """
        self.model = GlitchPredictionModel(model_path=model_path, use_cpu=use_cpu)
        self.feature_extractor = FeatureExtractor()
        self.min_probability = min_probability
        
        logger.info(
            f"PredictionEngine initialisiert "
            f"(min_probability={min_probability})"
        )
    
    async def predict(
        self,
        repo_path: Path,
        symbol_graph: Optional[nx.DiGraph] = None,
        complexity_data: Optional[Dict[str, Dict[str, Any]]] = None,
        git_data: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[PredictionFinding]:
        """
        Führt Bug-Vorhersage für Repository durch.
        
        Args:
            repo_path: Pfad zum Repository
            symbol_graph: Optionaler Symbol-Graph
            complexity_data: Optionale Complexity-Daten
            git_data: Optionale Git-History-Daten
            
        Returns:
            Liste von PredictionFindings
        """
        logger.info(f"Starte Bug-Prediction für {repo_path}")
        
        try:
            # Symbol-Graph laden falls nicht bereitgestellt
            if symbol_graph is None:
                symbol_graph = await self._load_symbol_graph(repo_path)
            
            if symbol_graph is None or len(symbol_graph) == 0:
                logger.warning("Kein Symbol-Graph verfügbar, überspringe Prediction")
                return []
            
            # Features extrahieren
            feature_vectors = self.feature_extractor.batch_extract(
                symbol_graph,
                complexity_data=complexity_data,
                git_data=git_data,
            )
            
            if not feature_vectors:
                logger.warning("Keine Features extrahiert")
                return []
            
            # Feature-Matrix erstellen
            feature_matrix, symbol_ids = self.feature_extractor.create_feature_matrix(
                feature_vectors
            )
            
            # Batch-Prediction durchführen
            predictions = self.model.predict(feature_matrix)
            
            # In Findings umwandeln
            findings = self._predictions_to_findings(
                predictions, feature_vectors, symbol_ids
            )
            
            # Filtern nach min_probability
            filtered = [
                f for f in findings
                if f.bug_probability >= self.min_probability
            ]
            
            logger.info(
                f"Prediction complete: {len(filtered)} findings "
                f"(von {len(predictions)} predictions)"
            )
            
            return filtered
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return []
    
    async def _load_symbol_graph(
        self,
        repo_path: Path,
    ) -> Optional[nx.DiGraph]:
        """
        Lädt Symbol-Graph aus Cache oder erstellt neuen.
        
        Args:
            repo_path: Pfad zum Repository
            
        Returns:
            Symbol-Graph oder None
        """
        try:
            # Versuche aus mapper zu laden
            from mapper.symbol_graph import SymbolGraph
            
            cache_file = Path(repo_path) / ".glitchhunter" / "symbol_graph.pkl"
            
            if cache_file.exists():
                import pickle
                with open(cache_file, "rb") as f:
                    graph = pickle.load(f)
                    logger.info(f"Symbol-Graph geladen: {len(graph)} Symbole")
                    return graph
            else:
                # Neuen Graph erstellen
                logger.info("Erstelle neuen Symbol-Graph")
                symbol_graph = SymbolGraph()
                await symbol_graph.scan(repo_path)
                
                # Speichern
                cache_dir = cache_file.parent
                cache_dir.mkdir(parents=True, exist_ok=True)
                
                import pickle
                with open(cache_file, "wb") as f:
                    pickle.dump(symbol_graph.to_networkx(), f)
                
                return symbol_graph.to_networkx()
                
        except ImportError:
            logger.warning("mapper.symbol_graph nicht verfügbar")
            return None
        except Exception as e:
            logger.error(f"Symbol-Graph loading failed: {e}")
            return None
    
    def _predictions_to_findings(
        self,
        predictions: List[PredictionResult],
        feature_vectors: List[FeatureVector],
        symbol_ids: List[str],
    ) -> List[PredictionFinding]:
        """
        Konvertiert Predictions zu Findings.
        
        Args:
            predictions: Vorhersage-Ergebnisse
            feature_vectors: Feature-Vektoren
            symbol_ids: Symbol-IDs
            
        Returns:
            Liste von PredictionFindings
        """
        findings = []
        
        for i, pred in enumerate(predictions):
            # Feature-Vektor finden
            if i < len(feature_vectors):
                fv = feature_vectors[i]
                file_path = fv.file_path
                symbol_name = fv.symbol_name
                metadata = fv.metadata
            else:
                file_path = "unknown"
                symbol_name = f"symbol_{i}"
                metadata = {}
            
            # Severity aus prediction ableiten
            severity = self._probability_to_severity(pred.bug_probability)
            
            # Line-Informationen versuchen zu extrahieren
            line_start = metadata.get("line_start", 0)
            line_end = metadata.get("line_end", 0)
            
            finding = PredictionFinding(
                id=f"ml_pred_{i}_{symbol_name}",
                file_path=file_path,
                line_start=line_start,
                line_end=line_end,
                severity=severity,
                category="ml_prediction",
                title=f"ML Bug Prediction: {symbol_name}",
                description=self._generate_description(pred, symbol_name),
                bug_probability=pred.bug_probability,
                confidence=pred.confidence,
                feature_importance=pred.feature_importance,
                metadata={
                    **metadata,
                    "severity_score": pred.severity_score,
                    "risk_level": pred.risk_level,
                },
            )
            
            findings.append(finding)
        
        return findings
    
    def _probability_to_severity(self, probability: float) -> str:
        """Konvertiert Bug-Wahrscheinlichkeit zu Severity."""
        if probability >= 0.8:
            return "critical"
        elif probability >= 0.6:
            return "high"
        elif probability >= 0.4:
            return "medium"
        else:
            return "low"
    
    def _generate_description(
        self,
        prediction: PredictionResult,
        symbol_name: str,
    ) -> str:
        """
        Generiert menschenlesbare Beschreibung.
        
        Args:
            prediction: Vorhersage-Ergebnis
            symbol_name: Symbol-Name
            
        Returns:
            Beschreibung
        """
        risk = prediction.risk_level
        prob = prediction.bug_probability * 100
        conf = prediction.confidence * 100
        
        desc = (
            f"Das ML-Modell vorhersagt ein {risk}-Risiko für einen Bug "
            f"in '{symbol_name}' mit {prob:.1f}% Wahrscheinlichkeit "
            f"(Konfidenz: {conf:.1f}%).\n\n"
        )
        
        # Feature-Importance hinzufügen
        if prediction.feature_importance:
            desc += "**Wichtigste Features:**\n"
            for feature, value in list(prediction.feature_importance.items())[:3]:
                desc += f"- {feature}: {value:.3f}\n"
        
        return desc
    
    def combine_with_swarm_findings(
        self,
        swarm_findings: List[Dict[str, Any]],
        prediction_findings: List[PredictionFinding],
    ) -> List[Dict[str, Any]]:
        """
        Kombiniert ML-Predictions mit Swarm-Findings.
        
        Args:
            swarm_findings: Findings vom Swarm Coordinator
            prediction_findings: ML-Predictions
            
        Returns:
            Kombinierte und priorisierte Findings
        """
        logger.info(
            f"Kombiniere {len(swarm_findings)} swarm findings "
            f"mit {len(prediction_findings)} predictions"
        )
        
        combined = list(swarm_findings)  # Copy
        
        # Predictions als Dict hinzufügen
        for pred in prediction_findings:
            finding_dict = pred.to_dict()
            
            # Prüfen ob bereits vorhanden (gleiche file_path + line)
            exists = False
            for existing in combined:
                if (
                    existing.get("file_path") == pred.file_path and
                    existing.get("line_start") == pred.line_start
                ):
                    # ML-Daten zu bestehendem Finding hinzufügen
                    existing["ml_prediction"] = {
                        "bug_probability": pred.bug_probability,
                        "confidence": pred.confidence,
                        "risk_level": pred.metadata.get("risk_level"),
                    }
                    # Confidence boost wenn beide übereinstimmen
                    if existing.get("confidence", 0) > 0.5:
                        existing["confidence"] = min(1.0, existing["confidence"] * 1.2)
                    exists = True
                    break
            
            if not exists:
                combined.append(finding_dict)
        
        # Nach Risiko sortieren
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        combined.sort(key=lambda f: severity_order.get(f.get("severity", "low"), 4))
        
        logger.info(f"Kombinierte {len(combined)} findings")
        
        return combined
    
    def get_high_risk_predictions(
        self,
        findings: List[PredictionFinding],
        min_probability: float = 0.7,
    ) -> List[PredictionFinding]:
        """
        Filtert High-Risk-Predictions.
        
        Args:
            findings: Alle Predictions
            min_probability: Minimale Wahrscheinlichkeit
            
        Returns:
            High-Risk-Predictions
        """
        high_risk = [
            f for f in findings
            if f.bug_probability >= min_probability
        ]
        
        logger.info(f"High-Risk-Predictions: {len(high_risk)} (>{min_probability})")
        
        return high_risk
    
    def export_predictions(
        self,
        findings: List[PredictionFinding],
        output_path: Path,
        format: str = "json",
    ):
        """
        Exportiert Predictions in Datei.
        
        Args:
            findings: Predictions
            output_path: Ausgabepfad
            format: Format (json, csv, markdown)
        """
        import json
        
        if format == "json":
            data = [f.to_dict() for f in findings]
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Exportiert {len(findings)} predictions nach {output_path}")
        
        elif format == "markdown":
            md_content = self._generate_markdown_report(findings)
            with open(output_path, "w") as f:
                f.write(md_content)
            logger.info(f"Exportiert Markdown-Report nach {output_path}")
        
        else:
            logger.warning(f"Unbekanntes Format: {format}")
    
    def _generate_markdown_report(
        self,
        findings: List[PredictionFinding],
    ) -> str:
        """
        Generiert Markdown-Report.
        
        Args:
            findings: Predictions
            
        Returns:
            Markdown-String
        """
        lines = [
            "# GlitchHunter ML Bug Prediction Report",
            "",
            f"**Total Predictions:** {len(findings)}",
            f"**High Risk:** {sum(1 for f in findings if f.severity in ['critical', 'high'])}",
            "",
            "## Findings by Severity",
            "",
        ]
        
        # Gruppieren nach Severity
        by_severity = {}
        for f in findings:
            if f.severity not in by_severity:
                by_severity[f.severity] = []
            by_severity[f.severity].append(f)
        
        for severity in ["critical", "high", "medium", "low"]:
            if severity in by_severity:
                lines.append(f"### {severity.upper()} ({len(by_severity[severity])})")
                lines.append("")
                
                for finding in by_severity[severity][:10]:  # Top 10
                    lines.append(f"- **{finding.title}**")
                    lines.append(f"  - File: `{finding.file_path}`")
                    lines.append(f"  - Probability: {finding.bug_probability:.1%}")
                    lines.append(f"  - Confidence: {finding.confidence:.1%}")
                    lines.append("")
        
        return "\n".join(lines)
