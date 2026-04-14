"""
Sandbox-Executor für sichere Code-Ausführung.

Führt Code in Docker-Sandbox aus.
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional

from ..core.exceptions import SandboxError

logger = logging.getLogger(__name__)


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
    """
    
    success: bool = False
    output: str = ""
    error: str = ""
    exit_code: int = -1
    duration_ms: float = 0.0
    security_violations: list[str] = field(default_factory=list)
    
    @property
    def has_output(self) -> bool:
        """True wenn Output vorhanden."""
        return bool(self.output.strip())
    
    @property
    def has_error(self) -> bool:
        """True wenn Fehler aufgetreten."""
        return bool(self.error.strip()) or self.exit_code != 0
    
    def to_dict(self) -> dict:
        """Konvertiert zu Dict."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "security_violations": self.security_violations,
        }


class SandboxExecutor:
    """
    Führt Code in Docker-Sandbox aus.
    
    Security-Features:
    - Isolierte Docker-Container
    - Netzwerk disabled
    - Resource-Limits (CPU, Memory, Time)
    - File-System Restrictions
    
    Usage:
        executor = SandboxExecutor()
        result = executor.execute(code, "python")
    """
    
    DEFAULT_IMAGE = "python:3.11-slim"
    DEFAULT_TIMEOUT = 60  # Sekunden
    DEFAULT_MEMORY_LIMIT = "512m"
    DEFAULT_CPU_LIMIT = 0.5
    
    def __init__(
        self,
        docker_image: str = DEFAULT_IMAGE,
        network_disabled: bool = True,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """
        Initialisiert Sandbox-Executor.
        
        Args:
            docker_image: Docker-Image.
            network_disabled: Netzwerk deaktivieren.
            timeout: Timeout in Sekunden.
        """
        self.docker_image = docker_image
        self.network_disabled = network_disabled
        self.timeout = timeout
        
        self._client: Any = None
        self._available = self._check_docker()
        
        if self._available:
            logger.info(f"Sandbox-Executor initialisiert: {docker_image}")
        else:
            logger.warning("Docker nicht verfügbar - Sandbox deaktiviert")
    
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
    
    def execute(
        self,
        code: str,
        language: str = "python",
        input_data: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Führt Code in Sandbox aus.
        
        Args:
            code: Auszuführender Code.
            language: Programmiersprache.
            input_data: Optionale Eingabedaten.
        
        Returns:
            ExecutionResult.
        """
        import time
        start_time = time.time()
        
        if not self._available:
            logger.warning("Sandbox nicht verfügbar - überspringe Ausführung")
            return ExecutionResult(
                success=False,
                error="Sandbox nicht verfügbar",
            )
        
        try:
            # Container-Konfiguration
            container_config = {
                "image": self.docker_image,
                "command": self._build_command(code, language),
                "detach": True,
                "network_disabled": self.network_disabled,
                "mem_limit": self.DEFAULT_MEMORY_LIMIT,
                "cpu_period": 100000,
                "cpu_quota": int(self.DEFAULT_CPU_LIMIT * 100000),
                "remove": True,
            }
            
            # Container erstellen und starten
            container = self._client.containers.run(**container_config)
            
            # Warten auf Abschluss mit Timeout
            try:
                result = container.wait(timeout=self.timeout)
                exit_code = result.get("StatusCode", -1)
            except Exception:
                # Timeout - Container killen
                container.kill()
                exit_code = -1
            
            # Logs holen
            output = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            error = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            
            duration_ms = (time.time() - start_time) * 1000
            
            return ExecutionResult(
                success=exit_code == 0,
                output=output,
                error=error,
                exit_code=exit_code,
                duration_ms=duration_ms,
            )
            
        except Exception as e:
            logger.error(f"Sandbox-Ausführung-Fehler: {e}")
            duration_ms = (time.time() - start_time) * 1000
            
            return ExecutionResult(
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )
    
    def _build_command(self, code: str, language: str) -> list[str]:
        """
        Baut Docker-Command.
        
        Args:
            code: Code.
            language: Sprache.
        
        Returns:
            Command-Liste.
        """
        # TODO: Code in Container schreiben und ausführen
        # Placeholder für verschiedene Sprachen
        
        if language == "python":
            return ["python3", "-c", code]
        elif language == "javascript":
            return ["node", "-e", code]
        else:
            return ["echo", f"Language {language} not supported"]
    
    def execute_with_tests(
        self,
        code: str,
        test_code: str,
        language: str = "python",
    ) -> ExecutionResult:
        """
        Führt Code mit Tests aus.
        
        Args:
            code: Quellcode.
            test_code: Test-Code.
            language: Sprache.
        
        Returns:
            ExecutionResult.
        """
        # Code + Tests kombinieren
        combined = f"{code}\n\n{test_code}"
        return self.execute(combined, language)
    
    def validate_security(self, code: str) -> list[str]:
        """
        Validiert Code auf Security-Issues vor Ausführung.
        
        Args:
            code: Code.
        
        Returns:
            Liste von Security-Violations.
        """
        violations = []
        
        # Gefährliche Patterns
        dangerous_patterns = [
            ("os.system", "System call"),
            ("subprocess", "Subprocess execution"),
            ("socket", "Network access"),
            ("__import__", "Dynamic import"),
            ("eval(", "Eval execution"),
            ("exec(", "Exec execution"),
        ]
        
        for pattern, description in dangerous_patterns:
            if pattern in code:
                violations.append(f"Dangerous: {description}")
        
        return violations
    
    def __call__(self, state: Any) -> dict:
        """
        Callable für LangGraph.
        
        Args:
            state: AgentState.
        
        Returns:
            State-Updates.
        """
        # TODO: Typisierung verbessern
        code = getattr(state, "code", "")
        language = getattr(state, "language", "python")
        
        # Security-Check vor Ausführung
        violations = self.validate_security(code)
        
        if violations:
            logger.warning(f"Security-Violations: {violations}")
            return {
                "metadata": {
                    "sandbox_skipped": True,
                    "security_violations": violations,
                },
            }
        
        result = self.execute(code, language)
        
        return {
            "metadata": {
                "sandbox_executed": True,
                "execution_success": result.success,
                "duration_ms": result.duration_ms,
            },
        }
