"""
Anthropic Provider for remote inference.

Supports Anthropic Claude API with native message format.
Implements chat completions via /v1/messages endpoint.

Features:
- Native Anthropic API format (not OpenAI-compatible)
- System prompt as separate field
- Token-based usage tracking
- Health check via API status

API Reference:
    https://docs.anthropic.com/claude/reference/messages_post
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


class AnthropicProvider(BaseProvider):
    """
    Anthropic Claude API provider implementation.

    Supports chat completions via Anthropic's native API format.
    Uses system prompt as separate field (not in messages array).
    Includes automatic retry with exponential backoff.

    Attributes:
        name: Provider name
        base_url: Base URL for the API
        timeout: Request timeout in seconds
        _api_key: API key for authentication
        _client: HTTP client for requests
        max_retries: Maximum number of retry attempts
        initial_delay: Initial retry delay in seconds
        max_delay: Maximum retry delay in seconds
        exponential_base: Base for exponential backoff
        anthropic_version: API version to use
    """

    # API endpoints
    MESSAGES_ENDPOINT = "/v1/messages"
    HEALTH_ENDPOINT = "/v1/messages"  # Use minimal request for health check

    # Status codes that trigger retry
    RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

    # Default model if not specified
    DEFAULT_MODEL = "claude-3-sonnet-20240229"

    def __init__(
        self,
        name: str = "anthropic",
        base_url: str = "https://api.anthropic.com",
        timeout: int = 120,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        anthropic_version: str = "2023-06-01",
    ) -> None:
        """
        Initialize the Anthropic provider.

        Args:
            name: Provider name
            base_url: Base URL for the API (default: https://api.anthropic.com)
            timeout: Request timeout in seconds
            api_key: API key for authentication
            max_retries: Maximum number of retry attempts
            initial_delay: Initial retry delay in seconds
            max_delay: Maximum retry delay in seconds
            exponential_base: Base for exponential backoff
            anthropic_version: API version header value
        """
        super().__init__(name, base_url, timeout, api_key)

        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.anthropic_version = anthropic_version

        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """
        Get or create HTTP client with Anthropic-specific headers.

        Returns:
            Async HTTP client configured for Anthropic API
        """
        if self._client is None or self._client.is_closed:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "GlitchHunter/1.0",
                "x-api-key": self._api_key or "",
                "anthropic-version": self.anthropic_version,
            }

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
        Generate a chat completion via Anthropic API.

        Converts OpenAI-format request to Anthropic format:
        - System prompt extracted from messages
        - Messages converted to Anthropic format
        - max_tokens parameter handled differently

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

        url = self._build_url(self.MESSAGES_ENDPOINT)
        payload = self._convert_request(request)

        logger.debug(
            f"Sending Anthropic chat completion request: "
            f"model={payload['model']}, messages={len(payload['messages'])}"
        )

        response_data = await self._make_request("POST", url, payload)

        return self._parse_chat_completion_response(response_data)

    def _convert_request(
        self, request: ChatCompletionRequest
    ) -> Dict[str, Any]:
        """
        Convert ChatCompletionRequest to Anthropic API format.

        Anthropic format differences:
        - System prompt is a separate field, not in messages
        - max_tokens is required
        - Different parameter names for some options

        Args:
            request: OpenAI-format request

        Returns:
            Anthropic-format payload dictionary
        """
        # Extract system message if present
        system_prompt = None
        messages = []

        for msg in request.messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                # Convert role to Anthropic format
                role = "assistant" if msg.role == "assistant" else "user"
                messages.append({"role": role, "content": msg.content})

        # Build Anthropic payload
        payload: Dict[str, Any] = {
            "model": request.model or self.DEFAULT_MODEL,
            "messages": messages,
            "max_tokens": request.max_tokens or 1024,  # Required for Anthropic
        }

        # Add system prompt if present
        if system_prompt:
            payload["system"] = system_prompt

        # Add optional parameters
        if request.temperature != 0.7:
            payload["temperature"] = request.temperature

        if request.top_p != 1.0:
            payload["top_p"] = request.top_p

        if request.stop:
            payload["stop_sequences"] = request.stop

        # Add extra kwargs for provider-specific parameters
        payload.update(request.extra_kwargs)

        return payload

    def _parse_chat_completion_response(
        self, response_data: Dict[str, Any]
    ) -> ChatCompletionResponse:
        """
        Parse Anthropic API response.

        Anthropic response format:
        {
            "id": "msg_01...",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "..."}],
            "model": "claude-3-...",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 20}
        }

        Args:
            response_data: Raw response data

        Returns:
            Parsed ChatCompletionResponse

        Raises:
            RemoteProviderError: If response format is invalid
        """
        try:
            # Extract content from Anthropic format
            content_list = response_data.get("content", [])
            if not content_list:
                raise RemoteProviderError(
                    "No content in Anthropic response",
                    provider_name=self.name,
                    details={"response": response_data},
                )

            # Get text from first text block
            content = ""
            for block in content_list:
                if block.get("type") == "text":
                    content = block.get("text", "")
                    break

            # Extract usage (Anthropic uses different field names)
            usage_data = response_data.get("usage", {})
            usage = {
                "prompt_tokens": usage_data.get("input_tokens", 0),
                "completion_tokens": usage_data.get("output_tokens", 0),
                "total_tokens": (
                    usage_data.get("input_tokens", 0)
                    + usage_data.get("output_tokens", 0)
                ),
            }

            model = response_data.get("model", "unknown")
            finish_reason = response_data.get("stop_reason", "unknown")

            return ChatCompletionResponse(
                content=content,
                model=model,
                usage=usage,
                finish_reason=finish_reason,
                index=0,
                raw_response=response_data,
            )

        except KeyError as e:
            raise RemoteProviderError(
                f"Invalid Anthropic response format: {e}",
                provider_name=self.name,
                details={"response_keys": list(response_data.keys())},
            )

    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate embeddings for text.

        Note: Anthropic does not provide an embeddings API.
        This method raises NotImplementedError.

        Args:
            request: Embedding request

        Raises:
            NotImplementedError: Anthropic does not support embeddings
        """
        raise NotImplementedError(
            f"Provider '{self.name}' does not support embeddings. "
            "Use a different provider for embedding tasks."
        )

    async def health_check(self) -> HealthStatus:
        """
        Check provider health via minimal API request.

        Sends a minimal valid request to verify API connectivity
        and authentication.

        Returns:
            Health status

        Raises:
            RemoteProviderError: If health check fails
        """
        start_time = time.time()

        try:
            url = self._build_url(self.HEALTH_ENDPOINT)

            # Send minimal valid request
            payload = {
                "model": self.DEFAULT_MODEL,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
            }

            client = await self._get_client()
            response = await client.post(url, json=payload, timeout=10.0)
            latency_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                return HealthStatus(
                    healthy=True,
                    message="Anthropic API is healthy",
                    latency_ms=latency_ms,
                    details={"endpoint": self.HEALTH_ENDPOINT},
                )
            elif response.status_code == 401:
                return HealthStatus(
                    healthy=False,
                    message="Invalid API key",
                    latency_ms=latency_ms,
                    details={"status_code": response.status_code},
                )
            else:
                return HealthStatus(
                    healthy=False,
                    message=f"Health check failed: {response.status_code}",
                    latency_ms=latency_ms,
                    details={"status_code": response.status_code},
                )

        except httpx.TimeoutException as e:
            latency_ms = (time.time() - start_time) * 1000
            return HealthStatus(
                healthy=False,
                message=f"Health check timeout: {e}",
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
                        method, url, payload, response.status_code, attempt
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
