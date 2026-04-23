"""
Base-Klasse für Sandbox-Isolation.

Bietet Grundfunktionalität für sichere Code-Ausführung.
"""

import logging
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseSandbox(ABC):
    """
    Abstrakte Basisklasse für Sandbox-Isolation.
    
    Usage:
        class MySandbox(BaseSandbox):
            async def execute(self, code: str) -> Dict[str, Any]:
                # Implementierung
                pass
    """
    
    def __init__(
        self,
        use_docker: bool = True,
        timeout: int = 60,
        network_disabled: bool = True,
    ):
        """
        Initialisiert die Sandbox.
        
        Args:
            use_docker: Docker-Container verwenden
            timeout: Timeout in Sekunden
            network_disabled: Netzwerk-Zugriff deaktivieren
        """
        self.use_docker = use_docker
        self.timeout = timeout
        self.network_disabled = network_disabled
        
        self.temp_dir = tempfile.mkdtemp(prefix="glitchhunter_sandbox_")
        logger.info(f"BaseSandbox initialisiert (docker={use_docker}, timeout={timeout}s)")
    
    @abstractmethod
    async def execute(self, code: str, **kwargs) -> Dict[str, Any]:
        """
        Führt Code in der Sandbox aus.
        
        Args:
            code: Auszuführender Code
            
        Returns:
            Ausführungs-Ergebnis
        """
        pass
    
    def run_in_docker(
        self,
        command: str,
        image: str = "python:3.11-slim",
        volumes: Optional[Dict[str, str]] = None,
    ) -> subprocess.CompletedProcess:
        """
        Führt Befehl in Docker-Container aus.
        
        Args:
            command: Befehl im Container
            image: Docker-Image
            volumes: Volume-Mappings
            
        Returns:
            subprocess.CompletedProcess
        """
        if not self.use_docker:
            raise RuntimeError("Docker ist nicht aktiviert")
        
        docker_cmd = [
            "docker", "run", "--rm",
            "--network", "none" if self.network_disabled else "bridge",
            "--memory", "512m",
            "--cpus", "1.0",
            "-t", str(self.timeout),
        ]
        
        # Volumes hinzufügen
        if volumes:
            for host_path, container_path in volumes.items():
                docker_cmd.extend(["-v", f"{host_path}:{container_path}"])
        
        docker_cmd.extend([image, "bash", "-c", command])
        
        logger.debug(f"Running docker command: {' '.join(docker_cmd)}")
        
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )
        
        return result
    
    def run_local(
        self,
        command: str,
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> subprocess.CompletedProcess:
        """
        Führt Befehl lokal aus (ohne Docker).
        
        Args:
            command: Befehl
            cwd: Working Directory
            env: Environment-Variablen
            
        Returns:
            subprocess.CompletedProcess
        """
        logger.debug(f"Running local command: {command}")
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            cwd=cwd,
            env=env,
        )
        
        return result
    
    def cleanup(self):
        """Räumt Temp-Verzeichnis auf."""
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
            logger.debug(f"Cleaned up temp dir: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")
    
    def __del__(self):
        """Destructor ruft cleanup auf."""
        self.cleanup()
