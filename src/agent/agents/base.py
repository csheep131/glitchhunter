"""
Base Interface für Swarm Agenten.

Definiert das gemeinsame Interface für alle Agenten im Swarm.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List


class BaseAgent(ABC):
    """
    Abstrakte Basisklasse für alle Swarm-Agenten.

    Jeder Agent muss folgende Methoden implementieren:
    - analyze: Hauptanalyse-Methode
    - get_findings: Extrahiert Findings

    Usage:
        class MyAgent(BaseAgent):
            async def analyze(self, repo_path: Path) -> Dict[str, Any]:
                # Implementierung
                pass
    """

    def __init__(self, name: str):
        """
        Initialisiert den BaseAgent.

        Args:
            name: Name des Agenten
        """
        self.name = name
        self._findings: List[Dict[str, Any]] = []

    @abstractmethod
    async def analyze(self, repo_path: Path, **kwargs) -> Dict[str, Any]:
        """
        Führt die Hauptanalyse des Agenten durch.

        Args:
            repo_path: Pfad zum Repository
            **kwargs: Agent-spezifische Argumente

        Returns:
            Analyse-Ergebnis
        """
        pass

    @abstractmethod
    async def get_findings(self) -> List[Dict[str, Any]]:
        """
        Extrahiert alle Findings der Analyse.

        Returns:
            Liste von Findings
        """
        pass

    async def cleanup(self) -> None:
        """
        Räumt Ressourcen auf.

        Wird nach Abschluss der Analyse aufgerufen.
        """
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """
        Returns Metadaten des Agenten.

        Returns:
            Metadaten
        """
        return {
            "name": self.name,
            "findings_count": len(self._findings),
        }
