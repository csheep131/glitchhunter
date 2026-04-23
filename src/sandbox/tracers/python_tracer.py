"""
Python Tracer für dynamische Code-Analyse.

Coverage-guides Fuzzing für Python mit:
- coverage.py Integration
- pytest Test-Ausführung
- Coverage-Analyse
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from sandbox.tracers.base import BaseTracer

logger = logging.getLogger(__name__)


class PythonTracer(BaseTracer):
    """
    Tracer für Python-Code.

    Verwendet coverage.py für Coverage-Analyse und
    pytest für Test-Ausführung.

    Usage:
        tracer = PythonTracer()
        results = await tracer.trace(target_path)
    """

    def __init__(
        self,
        timeout: int = 60,
        enable_coverage: bool = True,
        min_coverage: float = 50.0,
    ):
        """
        Initialisiert den Python Tracer.

        Args:
            timeout: Timeout in Sekunden
            enable_coverage: Coverage-Tracking aktivieren
            min_coverage: Minimale Coverage für Warnung
        """
        super().__init__(
            name="PythonTracer",
            timeout=timeout,
            enable_coverage=enable_coverage,
        )
        self.min_coverage = min_coverage
        self._coverage_data: Optional[Dict[str, Any]] = None

        logger.info(
            f"PythonTracer initialisiert: "
            f"timeout={timeout}, min_coverage={min_coverage}%"
        )

    async def trace(self, target: Path, test_files: List[Path] = None, **kwargs) -> Dict[str, Any]:
        """
        Führt Tracing von Python-Code durch.

        Args:
            target: Ziel-Pfad (Python-Datei oder Verzeichnis)
            test_files: Optionale Test-Dateien
            **kwargs: Zusätzliche Argumente

        Returns:
            Trace-Ergebnis
        """
        logger.info(f"PythonTracer: Starte Trace von {target}")
        self._clear_results()

        try:
            import coverage

            # Source-Pfade bestimmen
            if target.is_file():
                source_paths = [str(target.parent)]
            else:
                source_paths = [str(target)]

            # Coverage-Objekt erstellen
            cov = coverage.Coverage(
                branch=True,
                source=source_paths,
            )

            # Test-Dateien finden falls nicht angegeben
            if test_files is None:
                test_files = self._find_test_files(target)

            logger.info(f"Found {len(test_files)} test files")

            # Tests ausführen mit Coverage
            for test_file in test_files[:10]:  # Limit für Performance
                try:
                    cov.start()

                    # Test ausführen
                    result = self._run_test(test_file)

                    cov.stop()
                    cov.save()

                    # Coverage analysieren
                    analysis = self._analyze_coverage(cov, test_file)
                    if analysis:
                        self._add_result(analysis)

                except Exception as e:
                    logger.debug(f"Test {test_file} failed: {e}")
                    continue

            # Coverage report speichern
            self._coverage_data = self._get_coverage_summary(cov)

            logger.info(f"PythonTracer: {len(self._results)} results generiert")

            return {
                "success": True,
                "results_count": len(self._results),
                "coverage": self._coverage_data,
            }

        except ImportError:
            logger.warning("coverage.py nicht installiert, überspringe Python-Tracing")
            return {"success": False, "error": "coverage.py not installed"}
        except Exception as e:
            logger.error(f"Python tracing failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_results(self) -> List[Dict[str, Any]]:
        """
        Extrahiert alle Trace-Ergebnisse.

        Returns:
            Liste von Trace-Ergebnissen
        """
        return self._results.copy()

    def _find_test_files(self, target: Path) -> List[Path]:
        """
        Findet Test-Dateien im Ziel-Verzeichnis.

        Args:
            target: Ziel-Pfad

        Returns:
            Liste von Test-Dateien
        """
        if target.is_file():
            target = target.parent

        test_files = []
        test_files.extend(list(target.glob("**/test*.py")))
        test_files.extend(list(target.glob("**/*_test.py")))

        return test_files

    def _run_test(self, test_file: Path) -> Any:
        """
        Führt einzelnen Test aus.

        Args:
            test_file: Test-Datei

        Returns:
            Test-Ergebnis
        """
        import subprocess

        result = subprocess.run(
            ["python", "-m", "pytest", str(test_file), "-v"],
            capture_output=True,
            text=True,
            timeout=self.timeout,
            cwd=test_file.parent,
        )

        return result

    def _analyze_coverage(
        self,
        cov: Any,
        test_file: Path,
    ) -> Optional[Dict[str, Any]]:
        """
        Analysiert Coverage-Daten auf Issues.

        Args:
            cov: Coverage-Objekt
            test_file: Test-Datei

        Returns:
            Analyse-Ergebnis oder None
        """
        try:
            # Coverage report generieren
            report = cov.report(show_missing=True)

            # Niedrige Coverage als Issue melden
            if report < self.min_coverage:
                return {
                    "id": f"coverage_{test_file.name}",
                    "file_path": str(test_file),
                    "line_start": 0,
                    "line_end": 0,
                    "severity": "low",
                    "category": "test_quality",
                    "title": f"Niedrige Test-Coverage: {report:.1f}%",
                    "description": f"Test {test_file} hat nur {report:.1f}% Coverage",
                    "confidence": 0.8,
                    "evidence": [{"type": "coverage", "value": report}],
                    "trace_type": "coverage",
                }
        except Exception:
            pass

        return None

    def _get_coverage_summary(self, cov: Any) -> Dict[str, Any]:
        """
        Erstellt Coverage-Zusammenfassung.

        Args:
            cov: Coverage-Objekt

        Returns:
            Coverage-Zusammenfassung
        """
        try:
            return {
                "total_coverage": cov.report(),
                "files_analyzed": len(cov.get_data().measured_files()),
            }
        except Exception:
            return {"total_coverage": 0.0, "files_analyzed": 0}
