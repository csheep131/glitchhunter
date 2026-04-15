"""
Llama.cpp Backend für GlitchHunter v2.0

CPU-only Fallback mit GGUF-Quantisierung.
"""

import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple
import json

logger = logging.getLogger(__name__)


@dataclass
class LlamaConfig:
    """Konfiguration für llama.cpp Backend."""
    model_path: str
    context_size: int = 8192
    threads: int = -1  # -1 = auto (alle Kerne)
    batch_size: int = 512
    gpu_layers: int = 0  # 0 = CPU-only
    temperature: float = 0.2
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    
    def to_cli_args(self) -> List[str]:
        """Konvertiert zu llama.cpp CLI Argumenten."""
        args = [
            "-m", self.model_path,
            "-c", str(self.context_size),
            "-b", str(self.batch_size),
            "-n", str(self.context_size),
        ]
        
        if self.threads > 0:
            args.extend(["-t", str(self.threads)])
        
        if self.gpu_layers > 0:
            args.extend(["-ngl", str(self.gpu_layers)])
        
        args.extend([
            "--temp", str(self.temperature),
            "--top-p", str(self.top_p),
            "--top-k", str(self.top_k),
            "--repeat-penalty", str(self.repeat_penalty),
        ])
        
        return args


class LlamaCppBackend:
    """
    Llama.cpp Backend für lokale CPU-Inference.
    
    Features:
    - GGUF-Modell-Support (Q4_K_M, Q5_K_M)
    - CPU-optimierte Inference
    - Streaming-Output
    - Hardware-Auto-Detection
    """
    
    # Bekannte gute Modelle für Code-Tasks
    RECOMMENDED_MODELS = {
        "qwen2.5-coder-7b": {
            "url": "https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
            "filename": "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
            "size_gb": 4.5,
        },
        "deepseek-coder-6.7b": {
            "url": "https://huggingface.co/TheBloke/DeepSeek-Coder-6.7B-Instruct-GGUF",
            "filename": "deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
            "size_gb": 4.0,
        },
        "phi-4": {
            "url": "https://huggingface.co/bartowski/phi-4-GGUF",
            "filename": "phi-4-Q4_K_M.gguf",
            "size_gb": 2.8,
        },
        "codellama-7b": {
            "url": "https://huggingface.co/TheBloke/CodeLlama-7B-Instruct-GGUF",
            "filename": "codellama-7b-instruct.Q4_K_M.gguf",
            "size_gb": 4.0,
        },
    }
    
    def __init__(self, config: Optional[LlamaConfig] = None):
        self.config = config
        self.models_dir = Path.home() / ".glitchhunter" / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._llama_binary: Optional[str] = None
        
    @classmethod
    def is_available(cls) -> bool:
        """Prüft ob llama.cpp verfügbar ist."""
        return cls._find_llama_binary() is not None
    
    @classmethod
    def _find_llama_binary(cls) -> Optional[str]:
        """Findet die llama-cli Binary."""
        # Prüfe gängige Pfade
        candidates = [
            "llama-cli",
            "llama",
            "/usr/local/bin/llama-cli",
            "/usr/bin/llama-cli",
            str(Path.home() / ".local/bin/llama-cli"),
            str(Path.home() / "llama.cpp/build/bin/llama-cli"),
        ]
        
        for candidate in candidates:
            try:
                result = subprocess.run(
                    [candidate, "--version"],
                    capture_output=True,
                    timeout=2,
                )
                if result.returncode == 0:
                    return candidate
            except:
                continue
        
        return None
    
    def setup(self) -> bool:
        """Initialisiert das Backend."""
        self._llama_binary = self._find_llama_binary()
        
        if not self._llama_binary:
            logger.error("llama-cli nicht gefunden. Bitte installieren:")
            logger.error("  git clone https://github.com/ggerganov/llama.cpp")
            logger.error("  cd llama.cpp && cmake -B build && cmake --build build")
            return False
        
        if self.config is None:
            # Auto-Config basierend auf verfügbarem Modell
            self.config = self._auto_configure()
        
        if not Path(self.config.model_path).exists():
            logger.error(f"Modell nicht gefunden: {self.config.model_path}")
            logger.info("Verwende 'download_model()' um ein Modell herunterzuladen")
            return False
        
        logger.info(f"Llama.cpp Backend bereit: {self._llama_binary}")
        logger.info(f"Modell: {self.config.model_path}")
        return True
    
    def _auto_configure(self) -> LlamaConfig:
        """Erstellt automatisch die beste Konfiguration."""
        # Finde verfügbares Modell
        available_models = list(self.models_dir.glob("*.gguf"))
        
        if available_models:
            model_path = str(available_models[0])
        else:
            # Default-Modell
            model_path = str(self.models_dir / "qwen2.5-coder-7b-instruct-q4_k_m.gguf")
        
        # Auto-Threads (alle Kerne)
        import multiprocessing
        threads = multiprocessing.cpu_count()
        
        return LlamaConfig(
            model_path=model_path,
            threads=threads,
        )
    
    def download_model(
        self,
        model_name: str,
        progress_callback: Optional[callable] = None,
    ) -> bool:
        """
        Lädt ein empfohlenes Modell herunter.
        
        Args:
            model_name: Name des Modells aus RECOMMENDED_MODELS
            progress_callback: Optional callback(progress_percent)
            
        Returns:
            True wenn erfolgreich
        """
        if model_name not in self.RECOMMENDED_MODELS:
            logger.error(f"Unbekanntes Modell: {model_name}")
            logger.info(f"Verfügbar: {list(self.RECOMMENDED_MODELS.keys())}")
            return False
        
        info = self.RECOMMENDED_MODELS[model_name]
        filename = info["filename"]
        output_path = self.models_dir / filename
        
        if output_path.exists():
            logger.info(f"Modell bereits vorhanden: {output_path}")
            return True
        
        # Verwende huggingface-cli oder wget
        url = f"{info['url']}/resolve/main/{filename}"
        
        logger.info(f"Lade Modell herunter: {filename} ({info['size_gb']} GB)")
        logger.info(f"URL: {url}")
        
        try:
            # Versuche huggingface-cli
            result = subprocess.run(
                ["huggingface-cli", "download", info["url"].split("/")[-2], filename],
                cwd=self.models_dir,
                capture_output=True,
                timeout=3600,
            )
            
            if result.returncode == 0:
                logger.info(f"Modell heruntergeladen: {output_path}")
                return True
            
        except Exception as e:
            logger.warning(f"huggingface-cli fehlgeschlagen: {e}")
        
        # Fallback: Direkter Download
        try:
            import urllib.request
            
            def download_progress(block_num, block_size, total_size):
                if progress_callback and total_size > 0:
                    progress = min(100, int(block_num * block_size * 100 / total_size))
                    progress_callback(progress)
            
            urllib.request.urlretrieve(
                url, output_path, reporthook=download_progress
            )
            logger.info(f"Modell heruntergeladen: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Download fehlgeschlagen: {e}")
            return False
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 1024,
        stop_sequences: Optional[List[str]] = None,
    ) -> str:
        """
        Generiert Text mit llama.cpp.
        
        Args:
            prompt: Eingabe-Prompt
            max_tokens: Maximale Tokens zu generieren
            stop_sequences: Optionale Stopp-Sequenzen
            
        Returns:
            Generierter Text
        """
        if not self._llama_binary or not self.config:
            raise RuntimeError("Backend nicht initialisiert. Rufe setup() auf.")
        
        # Erstelle Prompt-Datei
        prompt_file = self.models_dir / "temp_prompt.txt"
        prompt_file.write_text(prompt, encoding='utf-8')
        
        # Baue Kommando
        args = [
            self._llama_binary,
            "-m", self.config.model_path,
            "-f", str(prompt_file),
            "-c", str(self.config.context_size),
            "-n", str(max_tokens),
            "--temp", str(self.config.temperature),
            "--top-p", str(self.config.top_p),
            "--top-k", str(self.config.top_k),
            "--repeat-penalty", str(self.config.repeat_penalty),
            "--no-display-prompt",  # Nur Output, nicht den Prompt wiederholen
        ]
        
        if self.config.threads > 0:
            args.extend(["-t", str(self.config.threads)])
        
        # Füge Stopp-Sequenzen hinzu
        if stop_sequences:
            for seq in stop_sequences:
                args.extend(["--reverse-prompt", seq])
        
        logger.debug(f"llama.cpp Aufruf: {' '.join(args[:10])}...")
        
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=300,
            )
            
            if result.returncode != 0:
                logger.error(f"llama.cpp Fehler: {result.stderr}")
                return ""
            
            output = result.stdout.strip()
            
            # Entferne Prompt aus Output falls vorhanden
            if output.startswith(prompt):
                output = output[len(prompt):].strip()
            
            return output
            
        except subprocess.TimeoutExpired:
            logger.error("llama.cpp Timeout")
            return ""
        except Exception as e:
            logger.error(f"llama.cpp Fehler: {e}")
            return ""
        finally:
            # Cleanup
            if prompt_file.exists():
                prompt_file.unlink()
    
    def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 1024,
    ) -> Iterator[str]:
        """
        Streamt generierten Text.
        
        Args:
            prompt: Eingabe-Prompt
            max_tokens: Maximale Tokens
            
        Yields:
            Chunks des generierten Texts
        """
        if not self._llama_binary or not self.config:
            raise RuntimeError("Backend nicht initialisiert")
        
        prompt_file = self.models_dir / "temp_prompt.txt"
        prompt_file.write_text(prompt, encoding='utf-8')
        
        args = [
            self._llama_binary,
            "-m", self.config.model_path,
            "-f", str(prompt_file),
            "-n", str(max_tokens),
            "--temp", str(self.config.temperature),
            "--no-display-prompt",
        ]
        
        if self.config.threads > 0:
            args.extend(["-t", str(self.config.threads)])
        
        try:
            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            
            accumulated = ""
            while True:
                char = process.stdout.read(1)
                if not char:
                    break
                accumulated += char
                yield char
            
            process.wait()
            
        except Exception as e:
            logger.error(f"Streaming Fehler: {e}")
        finally:
            if prompt_file.exists():
                prompt_file.unlink()
    
    def get_model_info(self) -> Dict[str, Any]:
        """Gibt Informationen über das aktuelle Modell."""
        if not self.config:
            return {}
        
        model_path = Path(self.config.model_path)
        
        info = {
            "model_path": str(model_path),
            "exists": model_path.exists(),
            "config": {
                "context_size": self.config.context_size,
                "threads": self.config.threads,
                "temperature": self.config.temperature,
            },
        }
        
        if model_path.exists():
            stat = model_path.stat()
            info["size_mb"] = stat.st_size / (1024 * 1024)
        
        return info
    
    def benchmark(self) -> Dict[str, Any]:
        """Führt einen schnellen Benchmark durch."""
        prompt = "// Write a function to calculate fibonacci numbers\ndef fibonacci(n):"
        
        import time
        start = time.time()
        
        output = self.generate(prompt, max_tokens=256)
        
        duration = time.time() - start
        tokens = len(output.split())  # Grobe Schätzung
        
        return {
            "duration_seconds": duration,
            "estimated_tokens": tokens,
            "tokens_per_second": tokens / duration if duration > 0 else 0,
            "prompt": prompt,
            "output_preview": output[:200] + "..." if len(output) > 200 else output,
        }