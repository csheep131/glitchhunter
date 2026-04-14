"""
Sandbox-Executor für GlitchHunter.

Führt Patches in isolierter Sandbox aus mit:
- Docker-Container für Isolation
- Git-Worktree für sichere Patch-Anwendung
- Test-Suite Execution (pytest, cargo test, npm test)
- Security-Checks vor Ausführung
"""

import logging
import subprocess
import tempfile
import shutil
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from core.exceptions import SandboxError

logger = logging.getLogger(__name__)


class TestFramework(str, Enum):
    """Test-Frameworks."""

    PYTEST = "pytest"
    CARGO_TEST = "cargo_test"
    JEST = "jest"
    VITEST = "vitest"
    GO_TEST = "go_test"
    CUSTOM = "custom"


@dataclass
class TestResult:
    """
    Ergebnis eines Test-Laufs.

    Attributes:
        passed: True wenn Test bestanden.
        test_name: Name des Tests.
        duration_ms: Test-Dauer.
        output: stdout.
        error: stderr.
        coverage_delta: Coverage-Änderung.
    """

    passed: bool = False
    test_name: str = ""
    duration_ms: float = 0.0
    output: str = ""
    error: str = ""
    coverage_delta: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "passed": self.passed,
            "test_name": self.test_name,
            "duration_ms": self.duration_ms,
            "output": self.output,
            "error": self.error,
            "coverage_delta": self.coverage_delta,
        }


@dataclass
class ExecutionResult:
    """
    Ergebnis der Sandbox-Ausführung.

    Attributes:
        success: True wenn Ausführung erfolgreich.
        output: stdout.
        error: stderr.
        exit_code: Exit-Code.
        duration_ms: Ausführungsdauer.
        security_violations: Security-Violations.
        test_results: Ergebnisse der Test-Läufe.
        worktree_path: Pfad zum Git-Worktree.
    """

    success: bool = False
    output: str = ""
    error: str = ""
    exit_code: int = -1
    duration_ms: float = 0.0
    security_violations: List[str] = field(default_factory=list)
    test_results: List[TestResult] = field(default_factory=list)
    worktree_path: Optional[str] = None

    @property
    def has_output(self) -> bool:
        """True wenn Output vorhanden."""
        return bool(self.output.strip())

    @property
    def has_error(self) -> bool:
        """True wenn Fehler aufgetreten."""
        return bool(self.error.strip()) or self.exit_code != 0

    @property
    def all_tests_passed(self) -> bool:
        """True wenn alle Tests bestanden."""
        return all(tr.passed for tr in self.test_results)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "security_violations": self.security_violations,
            "test_results": [tr.to_dict() for tr in self.test_results],
            "worktree_path": self.worktree_path,
            "all_tests_passed": self.all_tests_passed,
        }


@dataclass
class SandboxConfig:
    """
    Konfiguration für Sandbox.

    Attributes:
        docker_image: Docker-Image.
        network_disabled: Netzwerk deaktivieren.
        timeout: Timeout in Sekunden.
        memory_limit: Memory-Limit.
        cpu_limit: CPU-Limit.
        worktree_enabled: Git-Worktree aktivieren.
    """

    docker_image: str = "python:3.11-slim"
    network_disabled: bool = True
    timeout: int = 180  # 3 Minuten für Tests
    memory_limit: str = "1g"
    cpu_limit: float = 1.0
    worktree_enabled: bool = True


class SandboxExecutor:
    """
    Führt Patches in isolierter Sandbox aus.

    Features:
    - Docker-Container für Isolation
    - Git-Worktree für sichere Patch-Anwendung
    - Test-Suite Execution
    - Security-Checks vor Ausführung
    - Coverage-Messung

    Usage:
        executor = SandboxExecutor()
        result = executor.execute_patch(patch, repo_path, test_command="pytest")
    """

    def __init__(
        self,
        config: Optional[SandboxConfig] = None,
    ) -> None:
        """
        Initialisiert Sandbox-Executor.

        Args:
            config: Sandbox-Konfiguration.
        """
        self.config = config or SandboxConfig()

        self._client: Any = None
        self._docker_available = self._check_docker()
        self._git_available = self._check_git()

        if self._docker_available:
            logger.info(f"Sandbox-Executor initialisiert: {self.config.docker_image}")
        else:
            logger.warning("Docker nicht verfügbar - eingeschränkter Modus")

        if not self._git_available:
            logger.warning("Git nicht verfügbar - Worktree-Isolation deaktiviert")

    def _check_docker(self) -> bool:
        """Prüft ob Docker verfügbar ist."""
        try:
            import docker
            self._client = docker.from_env()
            self._client.ping()
            return True
        except (ImportError, Exception) as e:
            logger.debug(f"Docker nicht verfügbar: {e}")
            return False

    def _check_git(self) -> bool:
        """Prüft ob Git verfügbar ist."""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def execute_patch(
        self,
        patch_diff: str,
        repo_path: str,
        test_command: Optional[str] = None,
        language: str = "python",
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """
        Führt Patch in Sandbox aus.

        Args:
            patch_diff: Patch als Diff-String.
            repo_path: Pfad zum Repository.
            test_command: Test-Command.
            language: Programmiersprache.
            timeout: Timeout in Sekunden.

        Returns:
            ExecutionResult.
        """
        logger.info(f"Starte Patch-Ausführung in Sandbox: {repo_path}")

        start_time = time.time()
        result = ExecutionResult()

        # Security-Check vor Ausführung
        violations = self._validate_patch_security(patch_diff)
        if violations:
            result.security_violations = violations
            result.error = f"Security-Violations: {violations}"
            return result

        # Git-Worktree erstellen
        worktree_path = None
        if self._git_available and self.config.worktree_enabled:
            try:
                worktree_path = self._create_worktree(repo_path)
                result.worktree_path = worktree_path
            except Exception as e:
                logger.error(f"Worktree-Erstellung fehlgeschlagen: {e}")

        try:
            # Patch anwenden
            if worktree_path:
                patch_success = self._apply_patch_to_worktree(patch_diff, worktree_path)
            else:
                patch_success = self._apply_patch_temporary(patch_diff, repo_path)

            if not patch_success:
                result.error = "Patch-Anwendung fehlgeschlagen"
                return result

            # Tests ausführen
            if test_command:
                test_results = self._run_tests(
                    worktree_path or repo_path,
                    test_command,
                    language,
                    timeout or self.config.timeout,
                )
                result.test_results = test_results
                result.success = all(tr.passed for tr in test_results)
            else:
                result.success = True

        except Exception as e:
            logger.error(f"Sandbox-Ausführung-Fehler: {e}")
            result.error = str(e)
            result.success = False

        finally:
            # Worktree aufräumen
            if worktree_path and os.path.exists(worktree_path):
                try:
                    self._cleanup_worktree(worktree_path)
                except Exception as e:
                    logger.warning(f"Worktree-Aufräumung fehlgeschlagen: {e}")

            result.duration_ms = (time.time() - start_time) * 1000

        return result

    def _create_worktree(self, repo_path: str) -> str:
        """
        Erstellt isolierten Git-Worktree.

        Args:
            repo_path: Pfad zum Repository.

        Returns:
            Pfad zum Worktree.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            worktree_name = f"fix_{int(time.time())}"
            worktree_path = os.path.join(tmpdir, worktree_name)

            # Git-Worktree erstellen
            result = subprocess.run(
                ["git", "-C", repo_path, "worktree", "add", "-b", worktree_name, worktree_path],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                raise SandboxError(f"Worktree-Erstellung fehlgeschlagen: {result.stderr}")

            logger.info(f"Worktree erstellt: {worktree_path}")
            return worktree_path

    def _apply_patch_to_worktree(self, patch_diff: str, worktree_path: str) -> bool:
        """
        Wendet Patch auf Worktree an.

        Args:
            patch_diff: Patch als Diff-String.
            worktree_path: Pfad zum Worktree.

        Returns:
            True wenn erfolgreich.
        """
        try:
            # Patch-Datei erstellen
            with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f:
                f.write(patch_diff)
                patch_file = f.name

            # Patch anwenden
            result = subprocess.run(
                ["git", "-C", worktree_path, "apply", patch_file],
                capture_output=True,
                text=True,
                timeout=60,
            )

            os.unlink(patch_file)

            if result.returncode != 0:
                logger.error(f"Patch-Anwendung fehlgeschlagen: {result.stderr}")
                return False

            # Changes committen
            subprocess.run(
                ["git", "-C", worktree_path, "commit", "-m", "Applied patch"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            logger.info(f"Patch erfolgreich auf Worktree angewendet: {worktree_path}")
            return True

        except Exception as e:
            logger.error(f"Patch-Anwendung-Fehler: {e}")
            return False

    def _apply_patch_temporary(self, patch_diff: str, repo_path: str) -> bool:
        """
        Wendet Patch temporär an (Fallback ohne Worktree).

        Args:
            patch_diff: Patch als Diff-String.
            repo_path: Pfad zum Repository.

        Returns:
            True wenn erfolgreich.
        """
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f:
                f.write(patch_diff)
                patch_file = f.name

            result = subprocess.run(
                ["git", "-C", repo_path, "apply", "--reject", patch_file],
                capture_output=True,
                text=True,
                timeout=60,
            )

            os.unlink(patch_file)

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Temporäre Patch-Anwendung fehlgeschlagen: {e}")
            return False

    def _run_tests(
        self,
        project_path: str,
        test_command: str,
        language: str,
        timeout: int,
    ) -> List[TestResult]:
        """
        Führt Test-Suite aus.

        Args:
            project_path: Pfad zum Projekt.
            test_command: Test-Command.
            language: Programmiersprache.
            timeout: Timeout in Sekunden.

        Returns:
            Liste von TestResult.
        """
        logger.info(f"Starte Test-Ausführung: {test_command}")

        results = []

        try:
            # Tests im Docker-Container ausführen
            if self._docker_available:
                results = self._run_tests_in_docker(
                    project_path, test_command, language, timeout
                )
            else:
                # Fallback: Lokale Ausführung
                results = self._run_tests_local(project_path, test_command, language, timeout)

        except Exception as e:
            logger.error(f"Test-Ausführung fehlgeschlagen: {e}")
            results.append(TestResult(
                passed=False,
                test_name="test_execution",
                error=str(e),
            ))

        return results

    def _run_tests_in_docker(
        self,
        project_path: str,
        test_command: str,
        language: str,
        timeout: int,
    ) -> List[TestResult]:
        """
        Führt Tests in Docker-Container aus.

        Args:
            project_path: Pfad zum Projekt.
            test_command: Test-Command.
            language: Programmiersprache.
            timeout: Timeout in Sekunden.

        Returns:
            Liste von TestResult.
        """
        results = []

        try:
            # Container-Konfiguration
            container_config = {
                "image": self.config.docker_image,
                "command": ["bash", "-c", test_command],
                "detach": True,
                "network_disabled": self.config.network_disabled,
                "mem_limit": self.config.memory_limit,
                "cpu_period": 100000,
                "cpu_quota": int(self.config.cpu_limit * 100000),
                "working_dir": "/app",
                "remove": True,
            }

            # Container mit Volume erstellen
            container = self._client.containers.run(
                **container_config,
                volumes={project_path: {"bind": "/app", "mode": "ro"}},
            )

            # Warten auf Abschluss mit Timeout
            try:
                exit_result = container.wait(timeout=timeout)
                exit_code = exit_result.get("StatusCode", -1)
            except Exception:
                container.kill()
                exit_code = -1

            # Logs holen
            output = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            error = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

            # Test-Ergebnis parsen
            results.append(TestResult(
                passed=exit_code == 0,
                test_name="full_suite",
                output=output,
                error=error,
            ))

        except Exception as e:
            logger.error(f"Docker-Test-Ausführung fehlgeschlagen: {e}")
            results.append(TestResult(
                passed=False,
                test_name="docker_execution",
                error=str(e),
            ))

        return results

    def _run_tests_local(
        self,
        project_path: str,
        test_command: str,
        language: str,
        timeout: int,
    ) -> List[TestResult]:
        """
        Führt Tests lokal aus (Fallback).

        Args:
            project_path: Pfad zum Projekt.
            test_command: Test-Command.
            language: Programmiersprache.
            timeout: Timeout in Sekunden.

        Returns:
            Liste von TestResult.
        """
        results = []

        try:
            result = subprocess.run(
                test_command,
                shell=True,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            results.append(TestResult(
                passed=result.returncode == 0,
                test_name="local_suite",
                output=result.stdout,
                error=result.stderr,
            ))

        except subprocess.TimeoutExpired:
            results.append(TestResult(
                passed=False,
                test_name="local_suite",
                error=f"Timeout nach {timeout}s",
            ))
        except Exception as e:
            results.append(TestResult(
                passed=False,
                test_name="local_suite",
                error=str(e),
            ))

        return results

    def _validate_patch_security(self, patch_diff: str) -> List[str]:
        """
        Validiert Patch auf Security-Issues.

        Args:
            patch_diff: Patch als Diff-String.

        Returns:
            Liste von Security-Violations.
        """
        violations = []

        # Gefährliche Patterns im Patch suchen
        dangerous_patterns = [
            ("os.system", "System call"),
            ("os.popen", "Process execution"),
            ("subprocess", "Subprocess execution"),
            ("socket", "Network access"),
            ("eval(", "Eval execution"),
            ("exec(", "Exec execution"),
            ("__import__", "Dynamic import"),
            ("pickle.load", "Unsafe deserialization"),
            ("yaml.load(", "Unsafe YAML"),
        ]

        for line in patch_diff.split("\n"):
            if line.startswith("+"):
                for pattern, description in dangerous_patterns:
                    if pattern in line:
                        violations.append(f"Dangerous: {description} in {line.strip()[:50]}")

        return violations

    def _cleanup_worktree(self, worktree_path: str) -> None:
        """
        Räumt Worktree auf.

        Args:
            worktree_path: Pfad zum Worktree.
        """
        try:
            # Worktree entfernen
            subprocess.run(
                ["git", "worktree", "remove", "-f", worktree_path],
                capture_output=True,
                text=True,
                timeout=60,
            )
            logger.debug(f"Worktree aufgeräumt: {worktree_path}")
        except Exception as e:
            logger.warning(f"Worktree-Aufräumung fehlgeschlagen: {e}")

    def execute_code(
        self,
        code: str,
        language: str = "python",
        input_data: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Führt Code in Sandbox aus (legacy Methode).

        Args:
            code: Auszuführender Code.
            language: Programmiersprache.
            input_data: Optionale Eingabedaten.

        Returns:
            ExecutionResult.
        """
        start_time = time.time()
        result = ExecutionResult()

        if not self._docker_available:
            result.error = "Docker nicht verfügbar"
            return result

        try:
            # Container-Konfiguration
            container_config = {
                "image": self.config.docker_image,
                "command": self._build_command(code, language),
                "detach": True,
                "network_disabled": self.config.network_disabled,
                "mem_limit": self.config.memory_limit,
                "cpu_period": 100000,
                "cpu_quota": int(self.config.cpu_limit * 100000),
                "remove": True,
            }

            # Container erstellen und starten
            container = self._client.containers.run(**container_config)

            # Warten auf Abschluss
            try:
                exit_result = container.wait(timeout=self.config.timeout)
                exit_code = exit_result.get("StatusCode", -1)
            except Exception:
                container.kill()
                exit_code = -1

            # Logs holen
            output = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            error = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

            result.success = exit_code == 0
            result.output = output
            result.error = error
            result.exit_code = exit_code

        except Exception as e:
            logger.error(f"Sandbox-Ausführung-Fehler: {e}")
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    def _build_command(self, code: str, language: str) -> List[str]:
        """
        Baut Docker-Command.

        Args:
            code: Code.
            language: Sprache.

        Returns:
            Command-Liste.
        """
        if language == "python":
            return ["python3", "-c", code]
        elif language == "javascript":
            return ["node", "-e", code]
        else:
            return ["echo", f"Language {language} not supported"]

    def __call__(self, state: Any) -> Dict[str, Any]:
        """
        Callable für LangGraph.

        Args:
            state: AgentState.

        Returns:
            State-Updates.
        """
        # TODO: Typisierung verbessern
        patch_diff = getattr(state, "patch_diff", "")
        repo_path = getattr(state, "repo_path", "")
        test_command = getattr(state, "test_command", "pytest")
        language = getattr(state, "language", "python")

        result = self.execute_patch(
            patch_diff=patch_diff,
            repo_path=repo_path,
            test_command=test_command,
            language=language,
        )

        return {
            "execution_result": result.to_dict(),
            "metadata": {
                "sandbox_executed": True,
                "execution_success": result.success,
                "all_tests_passed": result.all_tests_passed,
                "duration_ms": result.duration_ms,
                "security_violations": result.security_violations,
            },
        }
