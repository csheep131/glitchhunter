"""
Agent-Module für GlitchHunter Swarm.

Enthält spezialisierte Agenten für:
- Statische Analyse
- Dynamische Analyse
- Exploit-Generierung
- Refactoring
- Report-Aggregation
"""

from agent.agents.base import BaseAgent
from agent.agents.static_scanner import StaticScannerAgent
from agent.agents.dynamic_tracer import DynamicTracerAgent
from agent.agents.exploit_generator import ExploitGeneratorAgent
from agent.agents.refactoring_bot import RefactoringBotAgent
from agent.agents.report_aggregator import ReportAggregatorAgent

__all__ = [
    "BaseAgent",
    "StaticScannerAgent",
    "DynamicTracerAgent",
    "ExploitGeneratorAgent",
    "RefactoringBotAgent",
    "ReportAggregatorAgent",
]
