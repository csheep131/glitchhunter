"""
Base Interface für Tracer.

Definiert das gemeinsame Interface für alle Tracer-Implementierungen.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional


class BaseTracer(ABC):
    """
    Abstrakte Basisklasse für alle Tracer-Implementierungen.

    Jeder Tracer muss folgende Methoden implementieren:
    - trace: Haupt-Tracing-Methode
    - get_results: Extrahiert Trace-Ergebnisse

    Usage:
        class MyTracer(BaseTracer):
            async def trace(self, target: Path) -> Dict[str, Any]:
                # Implementierung
                pass
    """

    def __init__(
        self,
        name: str,
        timeout: int = 60,
        enable_coverage: bool = True,
    ):
        """
        Initialisiert den BaseTracer.

        Args:
            name: Name des Tracers
            timeout: Timeout in Sekunden
            enable_coverage: Coverage-Tracking aktivieren
        """
        self.name = name
        self.timeout = timeout
        self.enable_coverage = enable_coverage
        self._results: List[Dict[str, Any]] = []

    @abstractmethod
    async def trace(self, target: Path, **kwargs) -> Dict[str, Any]:
        """
        Führt Tracing des Ziels durch.

        Args:
            target: Ziel-Pfad (Datei oder Verzeichnis)
            **kwargs: Tracer-spezifische Argumente

        Returns:
            Trace-Ergebnis
        """
        pass

    @abstractmethod
    async def get_results(self) -> List[Dict[str, Any]]:
        """
        Extrahiert alle Trace-Ergebnisse.

        Returns:
            Liste von Trace-Ergebnissen
        """
        pass

    async def cleanup(self) -> None:
        """
        Räumt Ressourcen auf.

        Wird nach Abschluss des Tracings aufgerufen.
        """
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """
        Returns Metadaten des Tracers.

        Returns:
            Metadaten
        """
        return {
            "name": self.name,
            "timeout": self.timeout,
            "coverage_enabled": self.enable_coverage,
            "results_count": len(self._results),
        }

    def _add_result(self, result: Dict[str, Any]) -> None:
        """
        Fügt ein Trace-Ergebnis hinzu.

        Args:
            result: Trace-Ergebnis
        """
        self._results.append(result)

    def _clear_results(self) -> None:
        """Löscht alle gespeicherten Ergebnisse."""
        self._results.clear()
