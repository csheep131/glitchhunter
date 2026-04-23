"""
JavaScript/TypeScript Tracer für dynamische Code-Analyse.

Coverage-Analyse für JS/TS mit:
- Istanbul/nyc Integration
- Jest Test-Ausführung
- Coverage-Berichte
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from sandbox.tracers.base import BaseTracer

logger = logging.getLogger(__name__)


class JSTracer(BaseTracer):
    """
    Tracer für JavaScript/TypeScript-Code.

    Verwendet Istanbul/nyc für Coverage-Analyse und
    Jest für Test-Ausführung.

    Usage:
        tracer = JSTracer()
        results = await tracer.trace(target_path)
    """

    def __init__(
        self,
        timeout: int = 60,
        enable_coverage: bool = True,
        min_coverage: float = 50.0,
    ):
        """
        Initialisiert den JS Tracer.

        Args:
            timeout: Timeout in Sekunden
            enable_coverage: Coverage-Tracking aktivieren
            min_coverage: Minimale Coverage für Warnung
        """
        super().__init__(
            name="JSTracer",
            timeout=timeout,
            enable_coverage=enable_coverage,
        )
        self.min_coverage = min_coverage
        self._coverage_data: Optional[Dict[str, Any]] = None

        logger.info(
            f"JSTracer initialisiert: "
            f"timeout={timeout}, min_coverage={min_coverage}%"
        )

    async def trace(self, target: Path, **kwargs) -> Dict[str, Any]:
        """
        Führt Tracing von JavaScript/TypeScript-Code durch.

        Args:
            target: Ziel-Pfad (JS/TS-Datei oder Verzeichnis)
            **kwargs: Zusätzliche Argumente

        Returns:
            Trace-Ergebnis
        """
        logger.info(f"JSTracer: Starte Trace von {target}")
        self._clear_results()

        try:
            # Prüfen ob npm/node verfügbar
            if not self._check_node_installed():
                logger.warning("Node.js nicht installiert, überspringe JS-Tracing")
                return {"success": False, "error": "Node.js not installed"}

            # package.json finden
            package_json = self._find_package_json(target)

            if package_json is None:
                logger.warning("Kein package.json gefunden")
                return {"success": False, "error": "No package.json found"}

            # Coverage mit nyc ausführen
            if self.enable_coverage:
                coverage_result = await self._run_coverage(package_json)
                self._coverage_data = coverage_result

                # Niedrige Coverage melden
                if coverage_result.get("coverage", 0) < self.min_coverage:
                    self._add_result({
                        "id": f"coverage_{package_json.parent.name}",
                        "file_path": str(package_json),
                        "line_start": 0,
                        "line_end": 0,
                        "severity": "low",
                        "category": "test_quality",
                        "title": f"Niedrige JS-Coverage: {coverage_result.get('coverage', 0):.1f}%",
                        "description": "Projekt hat niedrige Test-Coverage",
                        "confidence": 0.8,
                        "trace_type": "coverage",
                    })

            logger.info(f"JSTracer: {len(self._results)} results generiert")

            return {
                "success": True,
                "results_count": len(self._results),
                "coverage": self._coverage_data,
            }

        except Exception as e:
            logger.error(f"JS tracing failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_results(self) -> List[Dict[str, Any]]:
        """
        Extrahiert alle Trace-Ergebnisse.

        Returns:
            Liste von Trace-Ergebnissen
        """
        return self._results.copy()

    def _check_node_installed(self) -> bool:
        """
        Prüft ob Node.js installiert ist.

        Returns:
            True wenn Node.js verfügbar
        """
        import subprocess

        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _find_package_json(self, target: Path) -> Optional[Path]:
        """
        Findet package.json im Ziel-Verzeichnis.

        Args:
            target: Ziel-Pfad

        Returns:
            Pfad zu package.json oder None
        """
        if target.is_file():
            target = target.parent

        # Direktes Verzeichnis prüfen
        package_json = target / "package.json"
        if package_json.exists():
            return package_json

        # Parent-Verzeichnisse durchsuchen
        for parent in target.parents:
            package_json = parent / "package.json"
            if package_json.exists():
                return package_json

        return None

    async def _run_coverage(self, package_json: Path) -> Dict[str, Any]:
        """
        Führt Coverage-Analyse mit nyc durch.

        Args:
            package_json: Pfad zu package.json

        Returns:
            Coverage-Ergebnis
        """
        import subprocess

        project_dir = package_json.parent

        # nyc installieren falls nicht vorhanden
        await self._ensure_nyc_installed(project_dir)

        # Tests mit Coverage ausführen
        result = subprocess.run(
            ["npx", "nyc", "npm", "test"],
            capture_output=True,
            text=True,
            timeout=self.timeout,
            cwd=project_dir,
        )

        # Coverage aus Output parsen
        coverage = self._parse_nyc_output(result.stdout)

        return {
            "coverage": coverage,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    async def _ensure_nyc_installed(self, project_dir: Path) -> None:
        """
        Stellt sicher dass nyc installiert ist.

        Args:
            project_dir: Projekt-Verzeichnis
        """
        import subprocess

        try:
            subprocess.run(
                ["npm", "install", "--save-dev", "nyc"],
                capture_output=True,
                timeout=60,
                cwd=project_dir,
            )
        except Exception as e:
            logger.warning(f"nyc Installation fehlgeschlagen: {e}")

    def _parse_nyc_output(self, output: str) -> float:
        """
        Parst Coverage-Wert aus nyc Output.

        Args:
            output: nyc stdout

        Returns:
            Coverage-Prozentsatz
        """
        # Einfache Heuristik: Suche nach "All files" Zeile
        for line in output.split("\n"):
            if "All files" in line:
                try:
                    parts = line.split()
                    # Erste Zahl ist typischerweise Statement-Coverage
                    for part in parts[1:]:
                        if "%" in part:
                            return float(part.replace("%", ""))
                except Exception:
                    pass

        return 0.0
