"""
Static Scanner Agent für GlitchHunter Swarm.

Agent für statische Code-Analyse mit:
- PreFilter Pipeline
- Security Shield
- Semgrep Integration
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

from agent.agents.base import BaseAgent
from agent.state import SwarmFinding

logger = logging.getLogger(__name__)


class StaticScannerAgent(BaseAgent):
    """
    Agent für statische Code-Analyse.

    Verwendet bestehende PreFilter-Pipeline und Security Shield
    für statische Code-Analyse.

    Usage:
        agent = StaticScannerAgent()
        results = await agent.analyze(repo_path)
        findings = await agent.get_findings()
    """

    def __init__(self, enable_prefilter: bool = True, enable_security: bool = True):
        """
        Initialisiert den Static Scanner Agent.

        Args:
            enable_prefilter: PreFilter Pipeline aktivieren
            enable_security: Security Shield aktivieren
        """
        super().__init__(name="StaticScanner")
        self.enable_prefilter = enable_prefilter
        self.enable_security = enable_security
        self._findings: List[SwarmFinding] = []

        logger.info(
            f"StaticScannerAgent initialisiert: "
            f"prefilter={enable_prefilter}, security={enable_security}"
        )

    async def analyze(self, repo_path: Path, **kwargs) -> Dict[str, Any]:
        """
        Führt statische Analyse durch.

        Args:
            repo_path: Pfad zum Repository
            **kwargs: Zusätzliche Argumente

        Returns:
            Analyse-Ergebnis
        """
        logger.info(f"StaticScanner: Starte Analyse von {repo_path}")
        self._findings.clear()

        try:
            from prefilter.pipeline import PreFilterPipeline
            from security.shield import SecurityShield

            # Pre-Filter Pipeline
            if self.enable_prefilter:
                prefilter = PreFilterPipeline(repo_path)
                result = prefilter.run()

                # Security Findings umwandeln
                for candidate in result.candidates:
                    finding = SwarmFinding(
                        id=f"static_{candidate.get('id', 'unknown')}",
                        agent="static",
                        file_path=candidate.get("file_path", "unknown"),
                        line_start=candidate.get("line_start", 0),
                        line_end=candidate.get("line_end", 0),
                        severity=candidate.get("severity", "medium"),
                        category="correctness",
                        title=f"Code Issue in {candidate.get('file_path', 'unknown')}",
                        description=candidate.get("description", "Unspecified issue"),
                        confidence=candidate.get("confidence", 0.5),
                        metadata={"factors": candidate.get("factors", {})},
                    )
                    self._findings.append(finding)

            # Security Shield
            if self.enable_security:
                shield = SecurityShield()
                # TODO: Shield für gesamtes Repo ausführen

            logger.info(f"StaticScanner: {len(self._findings)} findings")

            return {
                "success": True,
                "findings_count": len(self._findings),
                "repo_path": str(repo_path),
            }

        except Exception as e:
            logger.error(f"StaticScanner failed: {e}")
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
