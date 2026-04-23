"""
Report Aggregator Agent für GlitchHunter Swarm.

Agent für Konsolidierung und Aggregation aller Findings.
"""

import logging
from typing import Any, Dict, List

from agent.agents.base import BaseAgent
from agent.state import SwarmFinding

logger = logging.getLogger(__name__)


class ReportAggregatorAgent(BaseAgent):
    """
    Agent für Report-Aggregation.

    Konsolidiert alle Findings und erstellt Reports.

    Usage:
        agent = ReportAggregatorAgent()
        results = await agent.analyze(
            repo_path,
            static=static_findings,
            dynamic=dynamic_findings,
            exploit=exploit_findings,
            refactor=refactor_findings,
        )
        aggregated = await agent.get_findings()
    """

    def __init__(self):
        """Initialisiert den Report Aggregator Agent."""
        super().__init__(name="ReportAggregator")
        self._aggregated_findings: List[SwarmFinding] = []

        logger.info("ReportAggregatorAgent initialisiert")

    async def analyze(
        self,
        repo_path: str = None,
        static: List[SwarmFinding] = None,
        dynamic: List[SwarmFinding] = None,
        exploit: List[SwarmFinding] = None,
        refactor: List[SwarmFinding] = None,
        predictions: List[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Aggregiert alle Findings.

        Args:
            repo_path: Pfad zum Repository (optional)
            static: Static Scanner Findings
            dynamic: Dynamic Tracer Findings
            exploit: Exploit Generator Findings
            refactor: Refactoring Bot Findings
            predictions: Prediction Ergebnisse
            **kwargs: Zusätzliche Argumente

        Returns:
            Analyse-Ergebnis
        """
        logger.info("ReportAggregator: Konsolidiere findings")
        self._aggregated_findings.clear()

        static = static or []
        dynamic = dynamic or []
        exploit = exploit or []
        refactor = refactor or []
        predictions = predictions or []

        # Alle Findings zusammenführen
        all_findings = static + dynamic + exploit + refactor

        # Deduplizieren (gleiche file_path + line + category)
        seen = set()
        aggregated = []

        for finding in all_findings:
            key = (finding.file_path, finding.line_start, finding.category)
            if key not in seen:
                seen.add(key)

                # Wenn von mehreren Agenten gefunden, confidence erhöhen
                matching = [
                    f
                    for f in all_findings
                    if (f.file_path, f.line_start, f.category) == key
                ]
                if len(matching) > 1:
                    finding.confidence = min(1.0, finding.confidence * 1.2)
                    finding.metadata["confirmed_by"] = [f.agent for f in matching]

                aggregated.append(finding)

        # Nach severity sortieren
        severity_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
            "info": 4,
        }
        aggregated.sort(key=lambda f: severity_order.get(f.severity, 5))

        self._aggregated_findings = aggregated

        logger.info(f"ReportAggregator: {len(aggregated)} unique findings")

        return {
            "success": True,
            "aggregated_count": len(aggregated),
            "input_counts": {
                "static": len(static),
                "dynamic": len(dynamic),
                "exploit": len(exploit),
                "refactor": len(refactor),
            },
        }

    async def get_findings(self) -> List[Dict[str, Any]]:
        """
        Extrahiert alle aggregierten Findings.

        Returns:
            Liste von Findings als Dict
        """
        return [f.to_dict() for f in self._aggregated_findings]

    def get_findings_objects(self) -> List[SwarmFinding]:
        """
        Extrahiert alle Findings als Objekte.

        Returns:
            Liste von SwarmFinding Objekten
        """
        return self._aggregated_findings.copy()
