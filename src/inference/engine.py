"""
Inference engine for GlitchHunter.

Provides chat completion and embedding capabilities using llama-cpp-python.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..core.exceptions import InferenceError

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
    ) -> None:
        """
        Initialize inference engine.

        Args:
            model_name: Name identifier for the model
            temperature: Default temperature for generation
            max_tokens: Maximum tokens for generation
        """
        self.model_name = model_name
        self._model: Optional[Any] = None
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._is_loaded = False

        logger.debug(f"InferenceEngine initialized for model: {model_name}")

    def load_model(self, model_path: str, **kwargs) -> None:
        """
        Load a model from file.

        Args:
            model_path: Path to GGUF model file
            **kwargs: Additional arguments for llama-cpp-python

        Raises:
            InferenceError: If model loading fails
        """
        try:
            from llama_cpp import Llama

            logger.info(f"Loading model from {model_path}")

            self._model = Llama(
                model_path=model_path,
                n_ctx=kwargs.get("n_ctx", 8192),
                n_gpu_layers=kwargs.get("n_gpu_layers", 35),
                n_threads=kwargs.get("n_threads", 8),
                verbose=kwargs.get("verbose", False),
            )

            self._is_loaded = True
            logger.info(f"Model '{self.model_name}' loaded successfully")

        except ImportError as e:
            raise InferenceError(
                "llama-cpp-python not installed. Install with: pip install llama-cpp-python",
                model_name=self.model_name,
                details={"error": str(e)},
            )

        except Exception as e:
            raise InferenceError(
                f"Failed to load model: {e}",
                model_name=self.model_name,
                details={"model_path": model_path, "error": str(e)},
            )

    def unload_model(self) -> None:
        """Unload the current model and free resources."""
        if self._model is not None:
            logger.info(f"Unloading model '{self.model_name}'")
            del self._model
            self._model = None
            self._is_loaded = False

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

            logger.debug(
                f"Generating chat completion (temp={temp}, max_tokens={tokens})"
            )

            response = self._model.create_chat_completion(
                messages=formatted_messages,
                temperature=temp,
                max_tokens=tokens,
                stream=stream,
                **kwargs,
            )

            # Extract response content
            choice = response["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason", "stop")

            # Extract usage statistics
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
            logger.debug(f"Generating embeddings for {len(texts)} texts")

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
        }

    def __enter__(self) -> "InferenceEngine":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - unload model."""
        self.unload_model()
