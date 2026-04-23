"""
Base Provider Interface for remote inference providers.

Defines the abstract base class that all remote providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ChatMessage:
    """
    Represents a chat message for LLM requests.

    Attributes:
        role: Role of the message sender (system, user, assistant)
        content: Message content
        name: Optional name for the message sender
    """

    role: str
    content: str
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert message to dictionary.

        Returns:
            Dictionary representation of the message
        """
        result: Dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name:
            result["name"] = self.name
        return result


@dataclass
class ChatCompletionRequest:
    """
    Request object for chat completion.

    Attributes:
        messages: List of chat messages
        model: Model name to use
        temperature: Sampling temperature (0-2)
        max_tokens: Maximum tokens to generate
        top_p: Nucleus sampling parameter
        frequency_penalty: Frequency penalty (-2 to 2)
        presence_penalty: Presence penalty (-2 to 2)
        stop: Stop sequences
        stream: Whether to stream responses
        n: Number of completions to generate
        extra_kwargs: Additional provider-specific parameters
    """

    messages: List[ChatMessage]
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: Optional[List[str]] = None
    stream: bool = False
    n: int = 1
    extra_kwargs: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert request to dictionary.

        Returns:
            Dictionary representation for API request
        """
        result: Dict[str, Any] = {
            "messages": [msg.to_dict() for msg in self.messages],
            "model": self.model,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "n": self.n,
        }

        if self.max_tokens is not None:
            result["max_tokens"] = self.max_tokens

        if self.stop:
            result["stop"] = self.stop

        if self.stream:
            result["stream"] = self.stream

        result.update(self.extra_kwargs)
        return result


@dataclass
class ChatCompletionResponse:
    """
    Response object for chat completion.

    Attributes:
        content: Generated content
        model: Model that generated the response
        usage: Token usage statistics
        finish_reason: Reason for completion
        index: Index of this completion (for multiple completions)
        raw_response: Raw provider response for debugging
    """

    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    index: int = 0
    raw_response: Optional[Dict[str, Any]] = None

    @property
    def prompt_tokens(self) -> int:
        """Get number of prompt tokens."""
        return self.usage.get("prompt_tokens", 0)

    @property
    def completion_tokens(self) -> int:
        """Get number of completion tokens."""
        return self.usage.get("completion_tokens", 0)

    @property
    def total_tokens(self) -> int:
        """Get total tokens used."""
        return self.usage.get("total_tokens", 0)


@dataclass
class EmbeddingRequest:
    """
    Request object for embeddings.

    Attributes:
        input: Text or list of texts to embed
        model: Model name to use
        encoding_format: Output format (float or base64)
        dimensions: Number of dimensions (if supported)
        extra_kwargs: Additional provider-specific parameters
    """

    input: str | List[str]
    model: str
    encoding_format: str = "float"
    dimensions: Optional[int] = None
    extra_kwargs: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert request to dictionary.

        Returns:
            Dictionary representation for API request
        """
        result: Dict[str, Any] = {
            "input": self.input,
            "model": self.model,
            "encoding_format": self.encoding_format,
        }

        if self.dimensions is not None:
            result["dimensions"] = self.dimensions

        result.update(self.extra_kwargs)
        return result


@dataclass
class EmbeddingResponse:
    """
    Response object for embeddings.

    Attributes:
        embeddings: List of embedding vectors
        model: Model that generated the embeddings
        usage: Token usage statistics
        raw_response: Raw provider response for debugging
    """

    embeddings: List[List[float]]
    model: str
    usage: Dict[str, int]
    raw_response: Optional[Dict[str, Any]] = None

    @property
    def prompt_tokens(self) -> int:
        """Get number of prompt tokens."""
        return self.usage.get("prompt_tokens", 0)

    @property
    def total_tokens(self) -> int:
        """Get total tokens used."""
        return self.usage.get("total_tokens", 0)


@dataclass
class HealthStatus:
    """
    Health check status.

    Attributes:
        healthy: Whether the provider is healthy
        message: Status message
        latency_ms: Response latency in milliseconds
        details: Additional status details
    """

    healthy: bool
    message: str
    latency_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


class BaseProvider(ABC):
    """
    Abstract base class for remote inference providers.

    All remote providers must implement this interface to ensure
    consistent API across different providers.

    Attributes:
        name: Provider name
        base_url: Base URL for the provider API
        timeout: Request timeout in seconds
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        timeout: int = 120,
        api_key: Optional[str] = None,
    ) -> None:
        """
        Initialize the base provider.

        Args:
            name: Provider name
            base_url: Base URL for the provider API
            timeout: Request timeout in seconds
            api_key: Optional API key for authentication
        """
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._api_key = api_key

    @abstractmethod
    async def chat_completion(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """
        Generate a chat completion.

        Args:
            request: Chat completion request

        Returns:
            Chat completion response

        Raises:
            RemoteProviderError: If the request fails
            RateLimitExceededError: If rate limit is exceeded
            APIKeyError: If API key is missing or invalid
        """
        pass

    @abstractmethod
    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate embeddings for text.

        Args:
            request: Embedding request

        Returns:
            Embedding response

        Raises:
            RemoteProviderError: If the request fails
            APIKeyError: If API key is missing or invalid
        """
        pass

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """
        Check provider health.

        Returns:
            Health status

        Raises:
            RemoteProviderError: If health check fails
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the provider name.

        Returns:
            Provider name
        """
        pass

    def get_api_key(self) -> Optional[str]:
        """
        Get the API key.

        Returns:
            API key if configured, None otherwise
        """
        return self._api_key

    def set_api_key(self, api_key: str) -> None:
        """
        Set the API key.

        Args:
            api_key: API key to use
        """
        self._api_key = api_key

    def _build_url(self, path: str) -> str:
        """
        Build full URL from path.

        Args:
            path: API path (e.g., "/v1/chat/completions")

        Returns:
            Full URL
        """
        return f"{self.base_url}{path}"

    def __repr__(self) -> str:
        """String representation of the provider."""
        return f"{self.__class__.__name__}(name={self.name}, base_url={self.base_url})"
