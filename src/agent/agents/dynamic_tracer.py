"""
Dynamic Tracer Agent für GlitchHunter Swarm.

Agent für dynamische Code-Analyse mit:
- Coverage-guided Fuzzing
- Runtime Tracing
- Docker-Isolation
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

from agent.agents.base import BaseAgent
from agent.state import SwarmFinding

logger = logging.getLogger(__name__)


class DynamicTracerAgent(BaseAgent):
    """
    Agent für dynamische Code-Analyse.

    Führt Runtime-Tracing und Coverage-guided Fuzzing durch.
    Delegiert an Sandbox Dynamic Tracer für die eigentliche Arbeit.

    Usage:
        agent = DynamicTracerAgent()
        results = await agent.analyze(repo_path)
        findings = await agent.get_findings()
    """

    def __init__(
        self,
        use_docker: bool = True,
        enable_ebpf: bool = True,
        enable_fuzzing: bool = True,
    ):
        """
        Initialisiert den Dynamic Tracer Agent.

        Args:
            use_docker: Docker für Isolation verwenden
            enable_ebpf: eBPF Tracing aktivieren (Linux)
            enable_fuzzing: Coverage-guided Fuzzing aktivieren
        """
        super().__init__(name="DynamicTracer")
        self.use_docker = use_docker
        self.enable_ebpf = enable_ebpf
        self.enable_fuzzing = enable_fuzzing
        self._findings: List[SwarmFinding] = []

        logger.info(
            f"DynamicTracerAgent initialisiert: "
            f"docker={use_docker}, ebpf={enable_ebpf}, fuzzing={enable_fuzzing}"
        )

    async def analyze(self, repo_path: Path, **kwargs) -> Dict[str, Any]:
        """
        Führt dynamische Analyse durch.

        Args:
            repo_path: Pfad zum Repository
            **kwargs: Zusätzliche Argumente

        Returns:
            Analyse-Ergebnis
        """
        logger.info(f"DynamicTracer: Starte Runtime-Analyse von {repo_path}")
        self._findings.clear()

        try:
            # Delegiere an Sandbox Dynamic Tracer
            from sandbox.dynamic_tracer import DynamicTracerAgent as Tracer

            tracer = Tracer(
                use_docker=self.use_docker,
                enable_ebpf=self.enable_ebpf,
                enable_fuzzing=self.enable_fuzzing,
            )
            trace_results = await tracer.trace_repository(repo_path)

            # Ergebnisse umwandeln
            for result in trace_results:
                finding = SwarmFinding(
                    id=f"dynamic_{result.get('id', 'unknown')}",
                    agent="dynamic",
                    file_path=result.get("file_path", "unknown"),
                    line_start=result.get("line_start", 0),
                    line_end=result.get("line_end", 0),
                    severity=result.get("severity", "medium"),
                    category="runtime",
                    title=result.get("title", "Runtime Issue"),
                    description=result.get("description", "Dynamic analysis found issue"),
                    confidence=result.get("confidence", 0.6),
                    evidence=result.get("evidence", []),
                    metadata={"trace_type": result.get("trace_type", "coverage")},
                )
                self._findings.append(finding)

            logger.info(f"DynamicTracer: {len(self._findings)} findings")

            return {
                "success": True,
                "findings_count": len(self._findings),
                "repo_path": str(repo_path),
            }

        except ImportError:
            logger.warning("DynamicTracer noch nicht implementiert, überspringe")
            return {"success": False, "error": "Not implemented"}
        except Exception as e:
            logger.error(f"DynamicTracer failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_findings(self) -> List[Dict[str, Any]]:
        """
        Extrahiert alle Findings der Analyse.

        Returns:
            Liste von Findings als Dict
        """
        return [f.to_dict() for f in self._findings]

    def get_findings_objects(self) -> List[SwarmFinding]:
        """
        Extrahiert alle Findings als Objekte.

        Returns:
            Liste von SwarmFinding Objekten
        """
        return self._findings.copy()
