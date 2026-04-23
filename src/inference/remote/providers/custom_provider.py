"""
Custom Provider for remote inference.

Generic provider for arbitrary APIs with configurable endpoints,
authentication methods, and response parsing.

Features:
- Configurable endpoints via YAML
- Multiple request formats (OpenAI, Anthropic, Raw)
- Multiple authentication methods (Bearer, API Key, None)
- Response parsing with JSON path extraction
- Flexible header configuration

Configuration Example:
    custom_api:
      name: "custom"
      base_url: "http://localhost:8080"
      api_key_env: "CUSTOM_API_KEY"
      config:
        endpoint: "/chat"
        request_format: "openai"  # or "anthropic", "raw"
        response_path: "choices.0.message.content"
        auth_method: "bearer"  # or "api_key", "none"
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from core.exceptions import (
    APIKeyError,
    RateLimitExceededError,
    RemoteProviderError,
)

from ..base_provider import (
    BaseProvider,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    EmbeddingRequest,
    EmbeddingResponse,
    HealthStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class CustomProviderConfig:
    """
    Configuration for CustomProvider.

    Attributes:
        endpoint: API endpoint path (e.g., "/chat")
        request_format: Request format ("openai", "anthropic", "raw")
        response_path: JSON path to extract content (e.g., "choices.0.message.content")
        auth_method: Authentication method ("bearer", "api_key", "none")
        headers: Additional headers to include
        timeout: Request timeout in seconds
        health_endpoint: Optional health check endpoint
        health_method: HTTP method for health check ("GET", "POST")
        embeddings_endpoint: Optional embeddings endpoint
        embeddings_format: Embeddings request format
        embeddings_response_path: JSON path for embeddings extraction
    """

    endpoint: str = "/v1/chat/completions"
    request_format: str = "openai"
    response_path: str = "choices.0.message.content"
    auth_method: str = "bearer"
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: int = 120
    health_endpoint: Optional[str] = "/health"
    health_method: str = "GET"
    embeddings_endpoint: Optional[str] = None
    embeddings_format: str = "openai"
    embeddings_response_path: str = "data.0.embedding"

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        valid_formats = {"openai", "anthropic", "raw"}
        if self.request_format not in valid_formats:
            raise ValueError(
                f"Invalid request_format: {self.request_format}. "
                f"Must be one of: {valid_formats}"
            )

        valid_auth_methods = {"bearer", "api_key", "none"}
        if self.auth_method not in valid_auth_methods:
            raise ValueError(
                f"Invalid auth_method: {self.auth_method}. "
                f"Must be one of: {valid_auth_methods}"
            )


class CustomProvider(BaseProvider):
    """
    Custom API provider with configurable behavior.

    Supports arbitrary APIs through configuration:
    - Configurable endpoints and HTTP methods
    - Multiple authentication schemes
    - JSON path-based response parsing
    - Flexible request format transformation

    Attributes:
        name: Provider name
        base_url: Base URL for the API
        timeout: Request timeout in seconds
        _api_key: API key for authentication
        _client: HTTP client for requests
        config: CustomProviderConfig instance
        max_retries: Maximum number of retry attempts
        initial_delay: Initial retry delay in seconds
        max_delay: Maximum retry delay in seconds
        exponential_base: Base for exponential backoff
    """

    # Status codes that trigger retry
    RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        name: str = "custom",
        base_url: str = "http://localhost:8080",
        timeout: int = 120,
        api_key: Optional[str] = None,
        config: Optional[CustomProviderConfig] = None,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ) -> None:
        """
        Initialize the Custom provider.

        Args:
            name: Provider name
            base_url: Base URL for the API
            timeout: Request timeout in seconds
            api_key: API key for authentication
            config: CustomProviderConfig instance (uses defaults if None)
            max_retries: Maximum number of retry attempts
            initial_delay: Initial retry delay in seconds
            max_delay: Maximum retry delay in seconds
            exponential_base: Base for exponential backoff
        """
        super().__init__(name, base_url, timeout, api_key)

        self.config = config or CustomProviderConfig()
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """
        Get or create HTTP client with configured authentication.

        Returns:
            Async HTTP client configured for custom API
        """
        if self._client is None or self._client.is_closed:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "GlitchHunter/1.0",
            }

            # Add configured authentication
            if self.config.auth_method == "bearer" and self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            elif self.config.auth_method == "api_key" and self._api_key:
                headers["X-API-Key"] = self._api_key
            # auth_method == "none" requires no headers

            # Add custom headers from config
            headers.update(self.config.headers)

            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
                follow_redirects=True,
            )

        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def chat_completion(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """
        Generate a chat completion via custom API.

        Transforms request based on configured format and
        parses response using configured JSON path.

        Args:
            request: Chat completion request

        Returns:
            Chat completion response

        Raises:
            RemoteProviderError: If the request fails
            RateLimitExceededError: If rate limit is exceeded
            APIKeyError: If API key is required but missing
        """
        if self.config.auth_method != "none" and not self._api_key:
            raise APIKeyError(
                f"API key required for provider: {self.name}",
                provider_name=self.name,
            )

        url = self._build_url(self.config.endpoint)
        payload = self._build_request_payload(request)

        logger.debug(
            f"Sending custom API request to {self.name}: "
            f"endpoint={self.config.endpoint}, format={self.config.request_format}"
        )

        response_data = await self._make_request("POST", url, payload)

        return self._parse_chat_completion_response(response_data)

    def _build_request_payload(
        self, request: ChatCompletionRequest
    ) -> Dict[str, Any]:
        """
        Build request payload based on configured format.

        Args:
            request: ChatCompletionRequest to transform

        Returns:
            Dictionary payload for HTTP request
        """
        if self.config.request_format == "openai":
            return self._build_openai_format(request)
        elif self.config.request_format == "anthropic":
            return self._build_anthropic_format(request)
        else:  # raw
            return self._build_raw_format(request)

    def _build_openai_format(
        self, request: ChatCompletionRequest
    ) -> Dict[str, Any]:
        """
        Build OpenAI-compatible request format.

        Args:
            request: ChatCompletionRequest

        Returns:
            OpenAI-format payload dictionary
        """
        payload = request.to_dict()
        # Remove None values for cleaner request
        return {k: v for k, v in payload.items() if v is not None}

    def _build_anthropic_format(
        self, request: ChatCompletionRequest
    ) -> Dict[str, Any]:
        """
        Build Anthropic-style request format.

        System prompt separated from messages.

        Args:
            request: ChatCompletionRequest

        Returns:
            Anthropic-format payload dictionary
        """
        system_prompt = None
        messages = []

        for msg in request.messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                role = "assistant" if msg.role == "assistant" else "user"
                messages.append({"role": role, "content": msg.content})

        payload: Dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens or 1024,
        }

        if system_prompt:
            payload["system"] = system_prompt

        if request.temperature != 0.7:
            payload["temperature"] = request.temperature

        if request.top_p != 1.0:
            payload["top_p"] = request.top_p

        payload.update(request.extra_kwargs)
        return payload

    def _build_raw_format(
        self, request: ChatCompletionRequest
    ) -> Dict[str, Any]:
        """
        Build raw request format (pass-through).

        Uses extra_kwargs as base and adds messages.

        Args:
            request: ChatCompletionRequest

        Returns:
            Raw-format payload dictionary
        """
        payload = dict(request.extra_kwargs)
        payload["messages"] = [msg.to_dict() for msg in request.messages]
        payload["model"] = request.model

        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens

        if request.temperature != 0.7:
            payload["temperature"] = request.temperature

        return payload

    def _parse_chat_completion_response(
        self, response_data: Dict[str, Any]
    ) -> ChatCompletionResponse:
        """
        Parse chat completion response using configured JSON path.

        Args:
            response_data: Raw response data

        Returns:
            Parsed ChatCompletionResponse

        Raises:
            RemoteProviderError: If response parsing fails
        """
        try:
            # Extract content using JSON path
            content = self._extract_json_path(
                response_data, self.config.response_path
            )

            if content is None:
                raise RemoteProviderError(
                    f"Could not extract content using path: {self.config.response_path}",
                    provider_name=self.name,
                    details={"response": response_data},
                )

            # Extract usage if available
            usage = self._extract_usage(response_data)

            # Extract model if available
            model = response_data.get("model", "unknown")

            # Extract finish_reason if available
            finish_reason = self._extract_finish_reason(response_data)

            return ChatCompletionResponse(
                content=str(content),
                model=model,
                usage=usage,
                finish_reason=finish_reason,
                index=0,
                raw_response=response_data,
            )

        except Exception as e:
            raise RemoteProviderError(
                f"Failed to parse custom API response: {e}",
                provider_name=self.name,
                details={"response_keys": list(response_data.keys())},
            )

    def _extract_json_path(
        self, data: Dict[str, Any], path: str
    ) -> Optional[Any]:
        """
        Extract value from nested dictionary using dot notation path.

        Args:
            data: Dictionary to extract from
            path: Dot notation path (e.g., "choices.0.message.content")

        Returns:
            Extracted value or None if path not found
        """
        if not path:
            return None

        keys = path.split(".")
        current: Any = data

        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list):
                try:
                    index = int(key)
                    current = current[index] if 0 <= index < len(current) else None
                except (ValueError, IndexError):
                    return None
            else:
                return None

            if current is None:
                return None

        return current

    def _extract_usage(self, response_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Extract token usage from response.

        Args:
            response_data: Raw response data

        Returns:
            Usage dictionary with token counts
        """
        usage_data = response_data.get("usage", {})
        return {
            "prompt_tokens": usage_data.get("prompt_tokens", 0),
            "completion_tokens": usage_data.get("completion_tokens", 0),
            "total_tokens": usage_data.get("total_tokens", 0),
        }

    def _extract_finish_reason(self, response_data: Dict[str, Any]) -> str:
        """
        Extract finish reason from response.

        Args:
            response_data: Raw response data

        Returns:
            Finish reason string
        """
        # Try OpenAI format
        choices = response_data.get("choices", [])
        if choices and isinstance(choices, list) and len(choices) > 0:
            first_choice = choices[0]
            if isinstance(first_choice, dict):
                return first_choice.get("finish_reason", "unknown")

        # Try Anthropic format
        stop_reason = response_data.get("stop_reason")
        if stop_reason:
            return str(stop_reason)

        return "unknown"

    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate embeddings for text.

        Args:
            request: Embedding request

        Returns:
            Embedding response

        Raises:
            RemoteProviderError: If embeddings not configured or request fails
        """
        if not self.config.embeddings_endpoint:
            raise NotImplementedError(
                f"Provider '{self.name}' does not have embeddings endpoint configured. "
                "Set embeddings_endpoint in CustomProviderConfig."
            )

        if self.config.auth_method != "none" and not self._api_key:
            raise APIKeyError(
                f"API key required for provider: {self.name}",
                provider_name=self.name,
            )

        url = self._build_url(self.config.embeddings_endpoint)
        payload = self._build_embeddings_payload(request)

        logger.debug(
            f"Sending embeddings request to {self.name}: "
            f"endpoint={self.config.embeddings_endpoint}"
        )

        response_data = await self._make_request("POST", url, payload)
        return self._parse_embeddings_response(response_data)

    def _build_embeddings_payload(
        self, request: EmbeddingRequest
    ) -> Dict[str, Any]:
        """
        Build embeddings request payload.

        Args:
            request: EmbeddingRequest

        Returns:
            Payload dictionary for embeddings request
        """
        if self.config.embeddings_format == "openai":
            return request.to_dict()
        else:
            # Generic format
            return {
                "input": request.input,
                "model": request.model,
            }

    def _parse_embeddings_response(
        self, response_data: Dict[str, Any]
    ) -> EmbeddingResponse:
        """
        Parse embeddings response.

        Args:
            response_data: Raw response data

        Returns:
            Parsed EmbeddingResponse
        """
        try:
            # Try to extract embeddings using configured path
            embedding = self._extract_json_path(
                response_data, self.config.embeddings_response_path
            )

            if embedding is None:
                # Fallback: try common paths
                embedding = self._extract_json_path(response_data, "data.0.embedding")
                if embedding is None:
                    embedding = self._extract_json_path(response_data, "embeddings.0")

            if embedding is None:
                raise RemoteProviderError(
                    "Could not extract embeddings from response",
                    provider_name=self.name,
                    details={"response": response_data},
                )

            # Handle different embedding formats
            # If embedding is a list of floats, it's a single embedding vector
            # If embedding is a list of lists, it's multiple embeddings
            if isinstance(embedding, list):
                if len(embedding) > 0 and isinstance(embedding[0], (int, float)):
                    # Single embedding vector (list of floats)
                    embeddings = [embedding]
                elif len(embedding) > 0 and isinstance(embedding[0], list):
                    # Multiple embeddings (list of lists)
                    embeddings = embedding
                else:
                    embeddings = [embedding]
            else:
                embeddings = [[embedding]]

            # Extract usage
            usage_data = response_data.get("usage", {})
            usage = {
                "prompt_tokens": usage_data.get("prompt_tokens", 0),
                "total_tokens": usage_data.get("total_tokens", 0),
            }

            model = response_data.get("model", "unknown")

            return EmbeddingResponse(
                embeddings=embeddings,
                model=model,
                usage=usage,
                raw_response=response_data,
            )

        except Exception as e:
            raise RemoteProviderError(
                f"Failed to parse embeddings response: {e}",
                provider_name=self.name,
                details={"response_keys": list(response_data.keys())},
            )

    async def health_check(self) -> HealthStatus:
        """
        Check provider health.

        Uses configured health endpoint or falls back to
        main endpoint with minimal request.

        Returns:
            Health status
        """
        start_time = time.time()

        try:
            client = await self._get_client()

            if self.config.health_endpoint:
                url = self._build_url(self.config.health_endpoint)

                if self.config.health_method == "GET":
                    response = await client.get(url, timeout=10.0)
                else:
                    response = await client.post(url, json={}, timeout=10.0)

                latency_ms = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    return HealthStatus(
                        healthy=True,
                        message="Custom API is healthy",
                        latency_ms=latency_ms,
                        details={"endpoint": self.config.health_endpoint},
                    )
                else:
                    return HealthStatus(
                        healthy=False,
                        message=f"Health check failed: {response.status_code}",
                        latency_ms=latency_ms,
                        details={"status_code": response.status_code},
                    )
            else:
                # No health endpoint configured, try main endpoint
                latency_ms = (time.time() - start_time) * 1000
                return HealthStatus(
                    healthy=True,
                    message="Provider is reachable (no health endpoint configured)",
                    latency_ms=latency_ms,
                )

        except httpx.ConnectError as e:
            latency_ms = (time.time() - start_time) * 1000
            return HealthStatus(
                healthy=False,
                message=f"Cannot connect: {e}",
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return HealthStatus(
                healthy=False,
                message=f"Health check failed: {e}",
                latency_ms=latency_ms,
            )

    async def _make_request(
        self,
        method: str,
        url: str,
        payload: Dict[str, Any],
        attempt: int = 1,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method
            url: Request URL
            payload: Request payload
            attempt: Current attempt number

        Returns:
            Response data

        Raises:
            RemoteProviderError: If all retries fail
            RateLimitExceededError: If rate limit exceeded after retries
        """
        client = await self._get_client()

        try:
            logger.debug(
                f"Making {method} request to {url} (attempt {attempt}/{self.max_retries + 1})"
            )

            response = await client.request(method, url, json=payload)
            response_data = response.json()

            if response.status_code >= 400:
                if response.status_code in self.RETRY_STATUS_CODES:
                    return await self._handle_retry(
                        method, url, payload, response.status_code, attempt
                    )

                if response.status_code == 401:
                    raise APIKeyError(
                        f"Invalid API key for provider: {self.name}",
                        provider_name=self.name,
                        details={"status_code": response.status_code},
                    )

                if response.status_code == 429:
                    retry_after = self._parse_retry_after(response)
                    raise RateLimitExceededError(
                        f"Rate limit exceeded for provider: {self.name}",
                        limit_type="requests",
                        retry_after=retry_after,
                        details={"status_code": response.status_code},
                    )

                raise RemoteProviderError(
                    f"API request failed: {response.status_code}",
                    provider_name=self.name,
                    status_code=response.status_code,
                    details={"response": response_data},
                )

            return response_data

        except httpx.TimeoutException as e:
            if attempt <= self.max_retries:
                return await self._handle_retry(
                    method, url, payload, status_code=504, attempt=attempt, error=e
                )
            raise RemoteProviderError(
                f"Request timeout after {self.timeout}s",
                provider_name=self.name,
                details={"timeout": self.timeout, "attempt": attempt},
            )

        except httpx.RequestError as e:
            if attempt <= self.max_retries:
                return await self._handle_retry(
                    method, url, payload, status_code=503, attempt=attempt, error=e
                )
            raise RemoteProviderError(
                f"Request failed: {e}",
                provider_name=self.name,
                details={"error_type": type(e).__name__},
            )

    async def _handle_retry(
        self,
        method: str,
        url: str,
        payload: Dict[str, Any],
        status_code: int,
        attempt: int,
        error: Optional[Exception] = None,
    ) -> Dict[str, Any]:
        """
        Handle retry with exponential backoff.

        Args:
            method: HTTP method
            url: Request URL
            payload: Request payload
            status_code: HTTP status code that triggered retry
            attempt: Current attempt number
            error: Optional exception that triggered retry

        Returns:
            Response data from retry attempt

        Raises:
            RemoteProviderError: If all retries exhausted
        """
        if attempt > self.max_retries:
            error_msg = f"All {self.max_retries + 1} attempts failed"
            if error:
                error_msg += f": {error}"
            raise RemoteProviderError(
                error_msg,
                provider_name=self.name,
                status_code=status_code,
                details={"final_attempt": attempt},
            )

        delay = min(
            self.initial_delay * (self.exponential_base ** (attempt - 1)),
            self.max_delay,
        )

        logger.warning(
            f"Request to {self.name} failed (status {status_code}), "
            f"retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries + 1})"
        )

        await asyncio.sleep(delay)
        return await self._make_request(method, url, payload, attempt + 1)

    def _parse_retry_after(self, response: httpx.Response) -> Optional[float]:
        """
        Parse Retry-After header from response.

        Args:
            response: HTTP response

        Returns:
            Retry-after value in seconds, or None if not present
        """
        retry_after = response.headers.get("Retry-After")
        if not retry_after:
            return None

        try:
            return float(retry_after)
        except ValueError:
            return None

    def get_provider_name(self) -> str:
        """
        Get the provider name.

        Returns:
            Provider name
        """
        return self.name

    def __del__(self) -> None:
        """Cleanup HTTP client on deletion."""
        if self._client and not self._client.is_closed:
            try:
                asyncio.get_event_loop().run_until_complete(self.close())
            except Exception:
                pass
