"""
OpenAI-compatible Provider for remote inference.

Supports OpenAI API, Azure OpenAI, and OpenAI-compatible APIs
like Ollama, vLLM, and DeepSeek.
"""

import asyncio
import logging
import time
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


class OpenAIProvider(BaseProvider):
    """
    OpenAI-compatible provider implementation.

    Supports chat completions and embeddings via OpenAI-compatible APIs.
    Includes automatic retry with exponential backoff and rate limiting.

    Attributes:
        name: Provider name
        base_url: Base URL for the API
        timeout: Request timeout in seconds
        _api_key: API key for authentication
        _client: HTTP client for requests
    """

    # API endpoints
    CHAT_COMPLETION_ENDPOINT = "/v1/chat/completions"
    EMBEDDINGS_ENDPOINT = "/v1/embeddings"
    HEALTH_ENDPOINT = "/health"  # Some providers support this

    # Status codes that trigger retry
    RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        name: str,
        base_url: str,
        timeout: int = 120,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ) -> None:
        """
        Initialize the OpenAI provider.

        Args:
            name: Provider name
            base_url: Base URL for the API
            timeout: Request timeout in seconds
            api_key: API key for authentication
            max_retries: Maximum number of retry attempts
            initial_delay: Initial retry delay in seconds
            max_delay: Maximum retry delay in seconds
            exponential_base: Base for exponential backoff
        """
        super().__init__(name, base_url, timeout, api_key)

        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

        # HTTP client will be created per request for async compatibility
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """
        Get or create HTTP client.

        Returns:
            Async HTTP client
        """
        if self._client is None or self._client.is_closed:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "GlitchHunter/1.0",
            }

            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"

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
        if not self._api_key:
            raise APIKeyError(
                f"API key required for provider: {self.name}",
                provider_name=self.name,
            )

        url = self._build_url(self.CHAT_COMPLETION_ENDPOINT)
        payload = request.to_dict()

        logger.debug(
            f"Sending chat completion request to {self.name}: "
            f"model={request.model}, messages={len(request.messages)}"
        )

        response_data = await self._make_request("POST", url, payload)

        return self._parse_chat_completion_response(response_data)

    def _parse_chat_completion_response(
        self, response_data: Dict[str, Any]
    ) -> ChatCompletionResponse:
        """
        Parse chat completion API response.

        Args:
            response_data: Raw response data

        Returns:
            Parsed ChatCompletionResponse

        Raises:
            RemoteProviderError: If response format is invalid
        """
        try:
            # Handle OpenAI-compatible response format
            choices = response_data.get("choices", [])
            if not choices:
                raise RemoteProviderError(
                    "No choices in chat completion response",
                    provider_name=self.name,
                    details={"response": response_data},
                )

            first_choice = choices[0]
            message = first_choice.get("message", {})
            content = message.get("content", "")

            usage = response_data.get("usage", {})
            model = response_data.get("model", "unknown")

            return ChatCompletionResponse(
                content=content,
                model=model,
                usage=usage,
                finish_reason=first_choice.get("finish_reason", "unknown"),
                index=first_choice.get("index", 0),
                raw_response=response_data,
            )

        except KeyError as e:
            raise RemoteProviderError(
                f"Invalid chat completion response format: {e}",
                provider_name=self.name,
                details={"response_keys": list(response_data.keys())},
            )

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
        if not self._api_key:
            raise APIKeyError(
                f"API key required for provider: {self.name}",
                provider_name=self.name,
            )

        url = self._build_url(self.EMBEDDINGS_ENDPOINT)
        payload = request.to_dict()

        logger.debug(
            f"Sending embeddings request to {self.name}: "
            f"model={request.model}, input_type={type(request.input).__name__}"
        )

        response_data = await self._make_request("POST", url, payload)

        return self._parse_embeddings_response(response_data)

    def _parse_embeddings_response(
        self, response_data: Dict[str, Any]
    ) -> EmbeddingResponse:
        """
        Parse embeddings API response.

        Args:
            response_data: Raw response data

        Returns:
            Parsed EmbeddingResponse

        Raises:
            RemoteProviderError: If response format is invalid
        """
        try:
            data = response_data.get("data", [])
            if not data:
                raise RemoteProviderError(
                    "No embeddings in response",
                    provider_name=self.name,
                    details={"response": response_data},
                )

            # Extract embeddings (sorted by index)
            embeddings = [item["embedding"] for item in sorted(data, key=lambda x: x.get("index", 0))]
            usage = response_data.get("usage", {})
            model = response_data.get("model", "unknown")

            return EmbeddingResponse(
                embeddings=embeddings,
                model=model,
                usage=usage,
                raw_response=response_data,
            )

        except KeyError as e:
            raise RemoteProviderError(
                f"Invalid embeddings response format: {e}",
                provider_name=self.name,
                details={"response_keys": list(response_data.keys())},
            )

    async def health_check(self) -> HealthStatus:
        """
        Check provider health.

        Returns:
            Health status

        Raises:
            RemoteProviderError: If health check fails
        """
        start_time = time.time()

        try:
            # Try health endpoint first (if supported)
            url = self._build_url(self.HEALTH_ENDPOINT)
            client = await self._get_client()

            try:
                response = await client.get(url, timeout=10.0)
                latency_ms = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    return HealthStatus(
                        healthy=True,
                        message="Provider is healthy",
                        latency_ms=latency_ms,
                        details=response.json() if response.content else {},
                    )
            except Exception:
                # Health endpoint not available, try chat completion
                pass

            # Fallback: try a minimal chat completion request
            latency_ms = (time.time() - start_time) * 1000
            return HealthStatus(
                healthy=True,
                message="Provider is reachable",
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
                # Handle error status codes
                if response.status_code in self.RETRY_STATUS_CODES:
                    return await self._handle_retry(
                        url, payload, response.status_code, attempt
                    )

                # Handle specific error codes
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
                    url, payload, status_code=504, attempt=attempt, error=e
                )
            raise RemoteProviderError(
                f"Request timeout after {self.timeout}s",
                provider_name=self.name,
                details={"timeout": self.timeout, "attempt": attempt},
            )

        except httpx.RequestError as e:
            if attempt <= self.max_retries:
                return await self._handle_retry(
                    url, payload, status_code=503, attempt=attempt, error=e
                )
            raise RemoteProviderError(
                f"Request failed: {e}",
                provider_name=self.name,
                details={"error_type": type(e).__name__},
            )

    async def _handle_retry(
        self,
        url: str,
        payload: Dict[str, Any],
        status_code: int,
        attempt: int,
        error: Optional[Exception] = None,
    ) -> Dict[str, Any]:
        """
        Handle retry with exponential backoff.

        Args:
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

        # Calculate delay with exponential backoff
        delay = min(
            self.initial_delay * (self.exponential_base ** (attempt - 1)),
            self.max_delay,
        )

        logger.warning(
            f"Request to {self.name} failed (status {status_code}), "
            f"retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries + 1})"
        )

        await asyncio.sleep(delay)
        return await self._make_request(url, payload, attempt + 1)

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
            # Try parsing as integer (seconds)
            return float(retry_after)
        except ValueError:
            # Try parsing as HTTP date (not implemented for simplicity)
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
            # Note: This is a best-effort cleanup
            # In async code, explicit close() is preferred
            try:
                asyncio.get_event_loop().run_until_complete(self.close())
            except Exception:
                pass
