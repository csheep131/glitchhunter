"""
Swarm Coordinator für GlitchHunter v3.0.

Facade für Multi-Agent Swarm System.
Koordiniert 5+ spezialisierte Agenten für parallele Code-Analyse.

Agenten:
1. StaticScannerAgent - Statische Analyse
2. DynamicTracerAgent - Dynamische Analyse
3. ExploitGeneratorAgent - Generiert PoC-Testcases
4. RefactoringBotAgent - Auto-Refactoring
5. ReportAggregatorAgent - Konsolidiert Reports
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from langgraph.graph import StateGraph, END

from agent.state import SwarmFinding, SwarmState, SwarmStateGraphInput
from agent.agents.static_scanner import StaticScannerAgent
from agent.agents.dynamic_tracer import DynamicTracerAgent
from agent.agents.exploit_generator import ExploitGeneratorAgent
from agent.agents.refactoring_bot import RefactoringBotAgent
from agent.agents.report_aggregator import ReportAggregatorAgent
from core.config import Config

logger = logging.getLogger(__name__)


class SwarmCoordinator:
    """
    Haupt-Koordinator für den Multi-Agent Swarm.

    Usage:
        coordinator = SwarmCoordinator()
        result = await coordinator.run_swarm("/path/to/repo")
    """

    def __init__(self, config: Optional[Config] = None):
        """
        Initialisiert den Swarm Coordinator.

        Args:
            config: Optionale Konfiguration
        """
        self.config = config or Config.load()

        # Agenten initialisieren
        self.static_scanner = StaticScannerAgent()
        self.dynamic_tracer = DynamicTracerAgent()
        self.exploit_generator = ExploitGeneratorAgent()
        self.refactoring_bot = RefactoringBotAgent()
        self.report_aggregator = ReportAggregatorAgent()

        # State Graph aufbauen
        self.workflow = self._build_graph()
        self.app = self.workflow.compile()

        logger.info("SwarmCoordinator initialisiert")

    def _build_graph(self) -> StateGraph:
        """
        Baut den LangGraph State Graph für den Swarm.

        Returns:
            Konfigurierter StateGraph
        """
        workflow = StateGraph(SwarmStateGraphInput)

        # Nodes hinzufügen
        workflow.add_node("static_scan", self._run_static_scan)
        workflow.add_node("dynamic_scan", self._run_dynamic_scan)
        workflow.add_node("generate_exploits", self._run_exploit_generation)
        workflow.add_node("generate_refactors", self._run_refactor_generation)
        workflow.add_node("aggregate_reports", self._run_aggregation)
        workflow.add_node("add_predictions", self._add_predictions)

        # Entry Point
        workflow.set_entry_point("static_scan")

        # Edges
        workflow.add_edge("static_scan", "dynamic_scan")
        workflow.add_edge("dynamic_scan", "generate_exploits")
        workflow.add_edge("generate_exploits", "generate_refactors")
        workflow.add_edge("generate_refactors", "aggregate_reports")
        workflow.add_edge("aggregate_reports", "add_predictions")
        workflow.add_edge("add_predictions", END)

        return workflow

    async def _run_static_scan(self, state: SwarmStateGraphInput) -> SwarmStateGraphInput:
        """Führt Static Scan durch."""
        try:
            repo_path = Path(state["repo_path"])
            findings = await self.static_scanner.analyze(repo_path)
            swarm_findings = self.static_scanner.get_findings_objects()
            state["static_findings"] = [f.to_dict() for f in swarm_findings]
            state["current_phase"] = "static_complete"
            logger.info(f"Static scan complete: {len(swarm_findings)} findings")
        except Exception as e:
            state["errors"].append(f"Static scan failed: {e}")
            logger.error(f"Static scan failed: {e}")
        return state

    async def _run_dynamic_scan(self, state: SwarmStateGraphInput) -> SwarmStateGraphInput:
        """Führt Dynamic Scan durch."""
        try:
            repo_path = Path(state["repo_path"])
            await self.dynamic_tracer.analyze(repo_path)
            swarm_findings = self.dynamic_tracer.get_findings_objects()
            state["dynamic_findings"] = [f.to_dict() for f in swarm_findings]
            state["current_phase"] = "dynamic_complete"
            logger.info(f"Dynamic scan complete: {len(swarm_findings)} findings")
        except Exception as e:
            state["errors"].append(f"Dynamic scan failed: {e}")
            logger.error(f"Dynamic scan failed: {e}")
        return state

    async def _run_exploit_generation(self, state: SwarmStateGraphInput) -> SwarmStateGraphInput:
        """Generiert Exploits."""
        try:
            repo_path = Path(state["repo_path"])
            static_findings = [
                SwarmFinding(**f) for f in state.get("static_findings", [])
            ]
            dynamic_findings = [
                SwarmFinding(**f) for f in state.get("dynamic_findings", [])
            ]
            all_findings = static_findings + dynamic_findings

            await self.exploit_generator.analyze(repo_path, findings=all_findings)
            exploits = self.exploit_generator.get_findings_objects()
            state["exploit_findings"] = [f.to_dict() for f in exploits]
            state["current_phase"] = "exploits_complete"
            logger.info(f"Exploit generation complete: {len(exploits)} exploits")
        except Exception as e:
            state["errors"].append(f"Exploit generation failed: {e}")
            logger.error(f"Exploit generation failed: {e}")
        return state

    async def _run_refactor_generation(self, state: SwarmStateGraphInput) -> SwarmStateGraphInput:
        """Generiert Refactorings."""
        try:
            repo_path = Path(state["repo_path"])
            static_findings = [
                SwarmFinding(**f) for f in state.get("static_findings", [])
            ]
            dynamic_findings = [
                SwarmFinding(**f) for f in state.get("dynamic_findings", [])
            ]
            all_findings = static_findings + dynamic_findings

            await self.refactoring_bot.analyze(repo_path, findings=all_findings)
            refactors = self.refactoring_bot.get_findings_objects()
            state["refactor_findings"] = [f.to_dict() for f in refactors]
            state["current_phase"] = "refactors_complete"
            logger.info(f"Refactor generation complete: {len(refactors)} refactors")
        except Exception as e:
            state["errors"].append(f"Refactor generation failed: {e}")
            logger.error(f"Refactor generation failed: {e}")
        return state

    async def _run_aggregation(self, state: SwarmStateGraphInput) -> SwarmStateGraphInput:
        """Aggregiert alle Reports."""
        try:
            static = [SwarmFinding(**f) for f in state.get("static_findings", [])]
            dynamic = [SwarmFinding(**f) for f in state.get("dynamic_findings", [])]
            exploit = [SwarmFinding(**f) for f in state.get("exploit_findings", [])]
            refactor = [SwarmFinding(**f) for f in state.get("refactor_findings", [])]

            await self.report_aggregator.aggregate(
                static=static,
                dynamic=dynamic,
                exploit=exploit,
                refactor=refactor,
            )
            aggregated = self.report_aggregator.get_findings_objects()
            state["aggregated_findings"] = [f.to_dict() for f in aggregated]
            state["current_phase"] = "aggregation_complete"
            logger.info(f"Aggregation complete: {len(aggregated)} unique findings")
        except Exception as e:
            state["errors"].append(f"Aggregation failed: {e}")
            logger.error(f"Aggregation failed: {e}")
        return state

    async def _add_predictions(self, state: SwarmStateGraphInput) -> SwarmStateGraphInput:
        """Fügt Prediction-Ergebnisse hinzu."""
        try:
            # TODO: Prediction Engine integration
            state["prediction_results"] = []
            state["current_phase"] = "predictions_complete"
            logger.info("Predictions added")
        except Exception as e:
            state["errors"].append(f"Predictions failed: {e}")
            logger.error(f"Predictions failed: {e}")
        return state

    async def run_swarm(self, repo_path: str) -> Dict[str, Any]:
        """
        Führt den kompletten Swarm-Workflow aus.

        Args:
            repo_path: Pfad zum Repository

        Returns:
            Swarm-Ergebnisse
        """
        logger.info(f"🐝 SwarmCoordinator: Starte Swarm-Analyse für {repo_path}")

        initial_state: SwarmStateGraphInput = {
            "repo_path": repo_path,
            "current_phase": "init",
            "static_findings": [],
            "dynamic_findings": [],
            "exploit_findings": [],
            "refactor_findings": [],
            "aggregated_findings": [],
            "prediction_results": [],
            "errors": [],
            "metadata": {"swarm_version": "3.0", "started_at": str(asyncio.get_event_loop().time())},
            "stop_after": None,
        }

        try:
            result = await self.app.ainvoke(initial_state)

            logger.info(
                f"🐝 SwarmCoordinator: Abgeschlossen - "
                f"{len(result['aggregated_findings'])} findings"
            )

            return {
                "success": True,
                "findings": result["aggregated_findings"],
                "predictions": result["prediction_results"],
                "errors": result["errors"],
                "metadata": result["metadata"],
            }

        except Exception as e:
            logger.error(f"SwarmCoordinator failed: {e}")
            return {
                "success": False,
                "findings": [],
                "predictions": [],
                "errors": [str(e)],
                "metadata": {},
            }

    def run_swarm_sync(self, repo_path: str) -> Dict[str, Any]:
        """
        Synchroner Wrapper für run_swarm.

        Args:
            repo_path: Pfad zum Repository

        Returns:
            Swarm-Ergebnisse
        """
        return asyncio.run(self.run_swarm(repo_path))


# Convenience-Funktion für CLI/API
async def analyze_with_swarm(repo_path: str) -> Dict[str, Any]:
    """
    Convenience-Funktion für Swarm-Analyse.

    Args:
        repo_path: Pfad zum Repository

    Returns:
        Swarm-Ergebnisse
    """
    coordinator = SwarmCoordinator()
    return await coordinator.run_swarm(repo_path)
