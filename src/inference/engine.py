"""
Inference engine for GlitchHunter.

Provides chat completion and embedding capabilities using llama-cpp-python.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.exceptions import InferenceError
from hardware.profiles import InferenceConfig

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """Represents a chat message."""

    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class ChatResponse:
    """Response from chat completion."""

    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str


@dataclass
class EmbeddingResponse:
    """Response from embedding generation."""

    embeddings: List[List[float]]
    model: str
    usage: Dict[str, int]


@dataclass
class InferenceResult:
    """Result from an inference call."""

    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str = "stop"


class InferenceEngine:
    """
    Main inference engine for LLM interactions.

    Provides chat completion and embedding capabilities with support for
    temperature adjustment, streaming, and batch processing.

    Attributes:
        model_name: Name of the loaded model
        _model: Underlying model instance (llama-cpp-python)
        _temperature: Current temperature setting
        _max_tokens: Maximum tokens for generation
    """

    def __init__(
        self,
        model_name: str = "default",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 120,
    ) -> None:
        """
        Initialize inference engine.

        Args:
            model_name: Name identifier for the model
            temperature: Default temperature for generation
            max_tokens: Maximum tokens for generation
            api_url: Optional URL for remote OpenAI-compatible API
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds

        Environment Variables:
            LLAMA_NETWORK_URL: Override api_url (e.g., "http://192.168.1.100:8080")
        """
        # Environment variable takes precedence
        env_url = os.getenv("LLAMA_NETWORK_URL")
        if env_url:
            api_url = env_url
            logger.info(f"Using LLAMA_NETWORK_URL from environment: {api_url}")

        self.model_name = model_name
        self._model: Optional[Any] = None
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._api_url = api_url
        self._api_key = api_key
        self._timeout = timeout
        self._is_loaded = False
        self._is_remote = False

        logger.debug(
            f"InferenceEngine initialized for model: {model_name} "
            f"(remote: {api_url if api_url else 'No'}, timeout: {timeout}s)"
        )

    def load_model(self, model_path: Optional[str] = None, **kwargs) -> None:
        """
        Load a model (local or remote).

        Args:
            model_path: Path to GGUF model file (local only)
            **kwargs: Additional arguments
        """
        if self._api_url:
            self._load_remote(**kwargs)
        elif model_path:
            self._load_local(model_path, **kwargs)
        else:
            raise InferenceError(
                "Either model_path or api_url must be provided",
                model_name=self.model_name
            )

    def load_model_with_fallback(
        self,
        model_path: Optional[str] = None,
        remote_url: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Load model with remote-first strategy and local fallback.

        Args:
            model_path: Path to GGUF model file (for local fallback)
            remote_url: Optional override for remote URL
            **kwargs: Additional arguments

        Returns:
            True if loaded successfully (remote or local), False otherwise
        """
        # Try remote first if configured
        url_to_use = remote_url or self._api_url
        
        if url_to_use:
            try:
                logger.info(f"Attempting remote connection to {url_to_use}")
                self._api_url = url_to_use
                self._load_remote(**kwargs)
                return True
            except Exception as e:
                logger.warning(f"Remote connection failed: {e}")
                if not kwargs.get("fallback_to_local", True):
                    raise
                logger.info("Falling back to local model...")

        # Fallback to local
        if model_path:
            try:
                self._load_local(model_path, **kwargs)
                return True
            except Exception as e:
                logger.error(f"Local model loading failed: {e}")
                return False

        return False

    def _load_remote(self, **kwargs) -> None:
        """Connect to remote OpenAI-compatible API."""
        try:
            from inference.openai_api import OpenAIAPI

            logger.info(f"Connecting to remote LLM server at {self._api_url}")
            self._model = OpenAIAPI(
                base_url=self._api_url,
                api_key=self._api_key,
                timeout=self._timeout,
                **kwargs
            )
            self._is_remote = True
            self._is_loaded = True
            logger.info(f"Remote LLM connection established for '{self.model_name}'")

        except Exception as e:
            raise InferenceError(
                f"Failed to connect to remote LLM: {e}",
                model_name=self.model_name,
                details={"api_url": self._api_url, "error": str(e)},
            )

    def _load_local(self, model_path: str, **kwargs) -> None:
        """Load local GGUF model with smart fallback."""
        try:
            from llama_cpp import Llama
            from hardware.smart_fallback import get_inference_config, InferenceMode

            logger.info(f"Loading local model from {model_path}")

            # Check if we should use smart fallback
            use_smart_fallback = kwargs.get("use_smart_fallback", True)
            
            if use_smart_fallback:
                # Get optimized config based on hardware
                cpu_only = kwargs.get("cpu_only", False)
                config = get_inference_config(cpu_only=cpu_only)
                
                # Log the mode
                logger.info(f"TurboQuant mode: {config.mode.value}, "
                           f"n_gpu_layers={config.n_gpu_layers}, "
                           f"ctx={config.n_ctx}")
                
                # Use config values
                load_kwargs = config.to_llama_kwargs()
                
                # Allow overrides from kwargs
                for key in ["n_ctx", "n_gpu_layers", "n_threads", "n_batch"]:
                    if key in kwargs:
                        load_kwargs[key] = kwargs[key]
                        
                load_kwargs["verbose"] = kwargs.get("verbose", False)
            else:
                # Legacy mode: use kwargs directly
                load_kwargs = {
                    "n_ctx": kwargs.get("n_ctx", 8192),
                    "n_gpu_layers": kwargs.get("n_gpu_layers", 35),
                    "n_threads": kwargs.get("n_threads", 8),
                    "verbose": kwargs.get("verbose", False),
                }

            self._model = Llama(
                model_path=model_path,
                **load_kwargs
            )

            self._is_loaded = True
            self._is_remote = False
            
            if use_smart_fallback:
                config = get_inference_config()
                logger.info(f"Local model '{self.model_name}' loaded successfully "
                           f"({config.get_mode_description(config)})")
            else:
                logger.info(f"Local model '{self.model_name}' loaded successfully")

        except ImportError as e:
            raise InferenceError(
                "llama-cpp-python not installed. Install with: pip install llama-cpp-python",
                model_name=self.model_name,
                details={"error": str(e)},
            )

        except Exception as e:
            raise InferenceError(
                f"Failed to load local model: {e}",
                model_name=self.model_name,
                details={"model_path": model_path, "error": str(e)},
            )

    def unload_model(self) -> None:
        """Unload the current model and free resources."""
        if self._model is not None:
            logger.info(f"Unloading model '{self.model_name}'")
            
            # Explicitly delete the model object
            del self._model
            self._model = None
            self._is_loaded = False
            
            # Forced garbage collection to release VRAM
            import gc
            gc.collect()
            
            # Try to clear CUDA cache if torch is available
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    logger.debug("CUDA cache cleared")
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"Failed to clear CUDA cache: {e}")

    def is_loaded(self) -> bool:
        """
        Check if a model is currently loaded.

        Returns:
            True if model is loaded
        """
        return self._is_loaded

    def set_temperature(self, temperature: float) -> None:
        """
        Set the temperature for generation.

        Args:
            temperature: Temperature value (0.0 to 2.0)

        Raises:
            ValueError: If temperature is out of range
        """
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        self._temperature = temperature
        logger.debug(f"Temperature set to {temperature}")

    def set_max_tokens(self, max_tokens: int) -> None:
        """
        Set maximum tokens for generation.

        Args:
            max_tokens: Maximum token count
        """
        if max_tokens < 1:
            raise ValueError("max_tokens must be at least 1")
        self._max_tokens = max_tokens
        logger.debug(f"Max tokens set to {max_tokens}")

    def chat(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs,
    ) -> ChatResponse:
        """
        Generate a chat completion.

        Args:
            messages: List of chat messages
            temperature: Override temperature (optional)
            max_tokens: Override max tokens (optional)
            stream: Enable streaming (not yet implemented)
            **kwargs: Additional arguments for llama-cpp-python

        Returns:
            ChatResponse with generated content

        Raises:
            InferenceError: If generation fails
        """
        if not self._is_loaded:
            raise InferenceError(
                "No model loaded. Call load_model() first.",
                model_name=self.model_name,
            )

        try:
            temp = temperature if temperature is not None else self._temperature
            tokens = max_tokens if max_tokens is not None else self._max_tokens

            # Convert messages to llama-cpp format
            formatted_messages = [
                {"role": msg.role, "content": msg.content} for msg in messages
            ]

            if self._is_remote:
                response = self._model.chat_completion_sync(
                    messages=formatted_messages,
                    temperature=temp,
                    max_tokens=tokens,
                    stream=stream,
                    **kwargs,
                )
                
                # Extract response content (OpenAI format)
                choice = response["choices"][0]
                content = choice["message"]["content"]
                finish_reason = choice.get("finish_reason", "stop")
                usage = response.get("usage", {"prompt_tokens": 0, "completion_tokens": 0})
            else:
                response = self._model.create_chat_completion(
                    messages=formatted_messages,
                    temperature=temp,
                    max_tokens=tokens,
                    stream=stream,
                    **kwargs,
                )

                # Extract response content (llama-cpp format)
                choice = response["choices"][0]
                content = choice["message"]["content"]
                finish_reason = choice.get("finish_reason", "stop")
                usage = response.get("usage", {"prompt_tokens": 0, "completion_tokens": 0})

            return ChatResponse(
                content=content,
                model=self.model_name,
                usage=usage,
                finish_reason=finish_reason,
            )

        except Exception as e:
            raise InferenceError(
                f"Chat completion failed: {e}",
                model_name=self.model_name,
                details={"error": str(e)},
            )

    def chat_simple(
        self,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> str:
        """
        Simple chat interface with system prompt and user message.

        Args:
            system_prompt: System instruction
            user_message: User's message
            temperature: Override temperature (optional)

        Returns:
            Generated response text
        """
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_message),
        ]
        response = self.chat(messages, temperature=temperature, **kwargs)
        return response.content

    def embed(self, texts: List[str], **kwargs) -> EmbeddingResponse:
        """
        Generate embeddings for texts.

        Args:
            texts: List of texts to embed
            **kwargs: Additional arguments for embedding

        Returns:
            EmbeddingResponse with embeddings

        Raises:
            InferenceError: If embedding generation fails
        """
        if not self._is_loaded:
            raise InferenceError(
                "No model loaded. Call load_model() first.",
                model_name=self.model_name,
            )

        try:
            if self._is_remote:
                response = self._model.embeddings_sync(
                    input=texts,
                    **kwargs,
                )
                
                embeddings = [r["embedding"] for r in response["data"]]
                total_tokens = response.get("usage", {}).get("total_tokens", 0)
            else:
                embeddings = []
                total_tokens = 0

                for text in texts:
                    embedding = self._model.embeddings.create([text])
                    embeddings.append(embedding[0])
                    total_tokens += len(text.split())  # Rough token estimate

            return EmbeddingResponse(
                embeddings=embeddings,
                model=self.model_name,
                usage={"prompt_tokens": total_tokens, "total_tokens": total_tokens},
            )

        except Exception as e:
            raise InferenceError(
                f"Embedding generation failed: {e}",
                model_name=self.model_name,
                details={"error": str(e)},
            )

    def embed_single(self, text: str, **kwargs) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        response = self.embed([text], **kwargs)
        return response.embeddings[0]

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.

        Returns:
            Dictionary with model information
        """
        if not self._is_loaded:
            return {"loaded": False}

        return {
            "loaded": True,
            "model_name": self.model_name,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "is_remote": self._is_remote,
            "api_url": self._api_url if self._is_remote else None,
        }

    async def check_remote_health(self) -> bool:
        """
        Check if remote LLM server is healthy.

        Returns:
            True if server is healthy, False otherwise
        """
        if not self._api_url:
            return False

        try:
            from inference.openai_api import OpenAIAPI

            api = OpenAIAPI(
                base_url=self._api_url,
                api_key=self._api_key,
                timeout=10
            )
            is_healthy = await api.health_check()
            logger.debug(f"Remote LLM health check: {'OK' if is_healthy else 'UNHEALTHY'}")
            return is_healthy
        except Exception as e:
            logger.warning(f"Remote health check failed: {e}")
            return False

    def check_remote_health_sync(self) -> bool:
        """
        Synchronous health check for remote LLM server.

        Returns:
            True if server is healthy, False otherwise
        """
        if not self._api_url:
            return False

        try:
            from inference.openai_api import OpenAIAPI

            api = OpenAIAPI(
                base_url=self._api_url,
                api_key=self._api_key,
                timeout=10
            )
            is_healthy = api.health_check_sync()
            logger.debug(f"Remote LLM health check: {'OK' if is_healthy else 'UNHEALTHY'}")
            return is_healthy
        except Exception as e:
            logger.warning(f"Remote health check failed: {e}")
            return False

    def is_remote_server_available(self) -> bool:
        """
        Check if a remote server is configured.

        Returns:
            True if remote URL is configured
        """
        return self._api_url is not None

    def get_remote_url(self) -> Optional[str]:
        """
        Get the configured remote URL.

        Returns:
            Remote URL or None
        """
        return self._api_url

    def __enter__(self) -> "InferenceEngine":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - unload model."""
        self.unload_model()
