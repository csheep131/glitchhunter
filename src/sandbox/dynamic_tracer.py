"""
Dynamic Tracer Agent für GlitchHunter v3.0.

Facade für dynamische Code-Analyse mit:
- Coverage-guided Fuzzing
- eBPF/ptrace Tracing (Linux)
- Docker-basierter Isolation
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from sandbox.base import BaseSandbox
from sandbox.tracers.python_tracer import PythonTracer
from sandbox.tracers.js_tracer import JSTracer
from sandbox.tracers.ebpf_tracer import EbpfTracer

logger = logging.getLogger(__name__)


class DynamicTracerAgent(BaseSandbox):
    """
    Agent für dynamische Code-Analyse.

    Delegiert an spezialisierte Tracer für jede Sprache.

    Usage:
        tracer = DynamicTracerAgent()
        results = await tracer.trace_repository("/path/to/repo")
    """

    def __init__(
        self,
        use_docker: bool = True,
        enable_ebpf: bool = True,
        enable_fuzzing: bool = True,
    ):
        """
        Initialisiert den Dynamic Tracer.

        Args:
            use_docker: Docker für Isolation
            enable_ebpf: eBPF Tracing aktivieren (Linux)
            enable_fuzzing: Coverage-guided Fuzzing aktivieren
        """
        super().__init__(use_docker=use_docker, timeout=60)

        self.enable_ebpf = enable_ebpf and self._is_linux()
        self.enable_fuzzing = enable_fuzzing

        # Tracer initialisieren
        self.python_tracer = PythonTracer(
            enable_coverage=enable_fuzzing
        ) if enable_fuzzing else None
        self.js_tracer = JSTracer()
        self.ebpf_tracer = EbpfTracer() if self.enable_ebpf else None

        logger.info(
            f"DynamicTracerAgent initialisiert: "
            f"docker={use_docker}, ebpf={self.enable_ebpf}, fuzzing={self.enable_fuzzing}"
        )

    def _is_linux(self) -> bool:
        """Prüft ob Linux-System."""
        return os.uname().sysname == "Linux"

    async def trace_repository(self, repo_path: Path) -> List[Dict[str, Any]]:
        """
        Führt dynamische Analyse auf Repository-Ebene durch.

        Args:
            repo_path: Pfad zum Repository

        Returns:
            Liste von Trace-Ergebnissen
        """
        logger.info(f"DynamicTracer: Starte Repository-Analyse für {repo_path}")
        results = []

        try:
            repo = Path(repo_path)

            # Python-Dateien finden
            python_files = list(repo.glob("**/*.py"))
            logger.info(f"Found {len(python_files)} Python files")

            # Test-Dateien finden
            test_files = list(repo.glob("**/test*.py")) + list(
                repo.glob("**/*_test.py")
            )
            logger.info(f"Found {len(test_files)} test files")

            # Python Tracing
            if self.python_tracer and python_files:
                python_results = await self._trace_python(python_files, test_files)
                results.extend(python_results)

            # JavaScript-Dateien finden
            js_files = list(repo.glob("**/*.js")) + list(repo.glob("**/*.ts"))
            if js_files and self.js_tracer:
                js_results = await self._trace_javascript(js_files)
                results.extend(js_results)

            # eBPF Tracing für C/C++/Rust (nur Linux)
            if self.enable_ebpf and self.ebpf_tracer:
                native_files = (
                    list(repo.glob("**/*.c"))
                    + list(repo.glob("**/*.cpp"))
                    + list(repo.glob("**/*.rs"))
                )
                if native_files:
                    ebpf_results = await self._trace_with_ebpf(native_files)
                    results.extend(ebpf_results)

            logger.info(f"DynamicTracer: {len(results)} results generiert")

        except Exception as e:
            logger.error(f"DynamicTracer repository analysis failed: {e}")

        return results

    async def _trace_python(
        self,
        files: List[Path],
        test_files: List[Path],
    ) -> List[Dict[str, Any]]:
        """
        Coverage-guided Fuzzing für Python-Dateien.

        Args:
            files: Python-Quelldateien
            test_files: Test-Dateien

        Returns:
            Fuzzing-Ergebnisse
        """
        if not self.python_tracer:
            return []

        logger.info(f"Fuzzing {len(files)} Python files with {len(test_files)} tests")

        # Ziel-Verzeichnis bestimmen
        target = files[0].parent if files else Path(".")

        results = await self.python_tracer.trace(target, test_files=test_files)

        return await self.python_tracer.get_results()

    async def _trace_javascript(self, files: List[Path]) -> List[Dict[str, Any]]:
        """
        Trace JavaScript/TypeScript files.

        Args:
            files: JS/TS files

        Returns:
            Trace results
        """
        if not self.js_tracer:
            return []

        logger.info(f"Tracing {len(files)} JavaScript files")

        target = files[0].parent if files else Path(".")
        await self.js_tracer.trace(target)

        return await self.js_tracer.get_results()

    async def _trace_with_ebpf(self, files: List[Path]) -> List[Dict[str, Any]]:
        """
        eBPF Tracing für native Binaries.

        Args:
            files: Native source files

        Returns:
            Trace results
        """
        if not self.ebpf_tracer:
            return []

        logger.info(f"eBPF tracing {len(files)} native files")

        target = files[0] if files else Path(".")
        await self.ebpf_tracer.trace(target)

        return await self.ebpf_tracer.get_results()

    async def execute(self, code: str, **kwargs) -> Dict[str, Any]:
        """
        Führt Code in Sandbox aus (BaseSandbox Interface).

        Args:
            code: Auszuführender Code
            **kwargs: Zusätzliche Argumente

        Returns:
            Ausführungs-Ergebnis
        """
        logger.debug(f"Executing code in sandbox: {code[:100]}...")

        import tempfile

        # Code in Temp-Datei schreiben
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            dir=self.temp_dir,
            delete=False,
        ) as f:
            f.write(code)
            temp_file = f.name

        try:
            # In Docker ausführen
            if self.use_docker:
                result = self.run_in_docker(f"python {temp_file}")
            else:
                result = self.run_local(f"python {temp_file}")

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "execution_time": 0,
            }

        except Exception as e:
            logger.error(f"Sandbox execution failed: {e}")
            return {"success": False, "error": str(e)}
