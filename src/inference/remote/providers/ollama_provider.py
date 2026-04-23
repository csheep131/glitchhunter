"""
Ollama Provider for remote inference.

Supports Ollama API for local and LAN deployments.
Provides both OpenAI-compatible mode and native Ollama API.

Features:
- OpenAI-compatible mode (/v1/chat/completions)
- Native Ollama API (/api/chat) as fallback
- Model pulling status check
- Local health checks without authentication
- Optional streaming support

API References:
    OpenAI-compatible: https://github.com/ollama/ollama/blob/main/docs/openai.md
    Native API: https://github.com/ollama/ollama/blob/main/docs/api.md
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from core.exceptions import (
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


class OllamaProvider(BaseProvider):
    """
    Ollama API provider implementation.

    Supports both OpenAI-compatible API and native Ollama format.
    Optimized for local and LAN deployments without authentication.
    Includes automatic model pulling detection and health checks.

    Attributes:
        name: Provider name
        base_url: Base URL for Ollama API
        timeout: Request timeout in seconds
        _client: HTTP client for requests
        max_retries: Maximum number of retry attempts
        initial_delay: Initial retry delay in seconds
        max_delay: Maximum retry delay in seconds
        exponential_base: Base for exponential backoff
        use_openai_mode: Whether to use OpenAI-compatible API
        streaming_enabled: Whether streaming is enabled
    """

    # OpenAI-compatible endpoints
    OPENAI_CHAT_ENDPOINT = "/v1/chat/completions"
    OPENAI_EMBEDDINGS_ENDPOINT = "/v1/embeddings"

    # Native Ollama endpoints
    NATIVE_CHAT_ENDPOINT = "/api/chat"
    NATIVE_EMBEDDINGS_ENDPOINT = "/api/embeddings"
    NATIVE_SHOW_ENDPOINT = "/api/show"
    NATIVE_TAGS_ENDPOINT = "/api/tags"

    # Status codes that trigger retry
    RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

    # Default model if not specified
    DEFAULT_MODEL = "llama2"

    def __init__(
        self,
        name: str = "ollama",
        base_url: str = "http://localhost:11434",
        timeout: int = 120,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        use_openai_mode: bool = True,
        streaming_enabled: bool = False,
    ) -> None:
        """
        Initialize the Ollama provider.

        Args:
            name: Provider name
            base_url: Base URL for Ollama API (default: http://localhost:11434)
            timeout: Request timeout in seconds
            api_key: API key (usually not needed for local Ollama)
            max_retries: Maximum number of retry attempts
            initial_delay: Initial retry delay in seconds
            max_delay: Maximum retry delay in seconds
            exponential_base: Base for exponential backoff
            use_openai_mode: Use OpenAI-compatible API (default: True)
            streaming_enabled: Enable streaming responses
        """
        super().__init__(name, base_url, timeout, api_key)

        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.use_openai_mode = use_openai_mode
        self.streaming_enabled = streaming_enabled

        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """
        Get or create HTTP client.

        Ollama typically runs locally without authentication.
        API key is optional and only used if explicitly configured.

        Returns:
            Async HTTP client configured for Ollama API
        """
        if self._client is None or self._client.is_closed:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "GlitchHunter/1.0",
            }

            # API key is optional for Ollama
            if self._api_key and self.use_openai_mode:
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
        Generate a chat completion via Ollama API.

        Uses OpenAI-compatible mode by default, falls back to
        native Ollama API if configured.

        Args:
            request: Chat completion request

        Returns:
            Chat completion response

        Raises:
            RemoteProviderError: If the request fails
            RateLimitExceededError: If rate limit is exceeded
        """
        if self.use_openai_mode:
            return await self._chat_completion_openai(request)
        else:
            return await self._chat_completion_native(request)

    async def _chat_completion_openai(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """
        Generate chat completion using OpenAI-compatible API.

        Args:
            request: Chat completion request

        Returns:
            Chat completion response
        """
        url = self._build_url(self.OPENAI_CHAT_ENDPOINT)
        payload = request.to_dict()

        # Remove None values for OpenAI compatibility
        payload = {k: v for k, v in payload.items() if v is not None}

        logger.debug(
            f"Sending OpenAI-compatible request to Ollama: "
            f"model={request.model}, messages={len(request.messages)}"
        )

        response_data = await self._make_request("POST", url, payload)
        return self._parse_openai_response(response_data)

    async def _chat_completion_native(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """
        Generate chat completion using native Ollama API.

        Native format differences:
        - Endpoint: /api/chat
        - Parameters: model, messages, stream, options
        - Response format differs from OpenAI

        Args:
            request: Chat completion request

        Returns:
            Chat completion response
        """
        url = self._build_url(self.NATIVE_CHAT_ENDPOINT)

        # Convert to native Ollama format
        payload = {
            "model": request.model or self.DEFAULT_MODEL,
            "messages": [msg.to_dict() for msg in request.messages],
            "stream": False,  # Disable streaming for synchronous API
            "options": {},
        }

        # Add Ollama-specific options
        if request.temperature != 0.7:
            payload["options"]["temperature"] = request.temperature

        if request.top_p != 1.0:
            payload["options"]["top_p"] = request.top_p

        if request.max_tokens:
            payload["options"]["num_predict"] = request.max_tokens

        if request.stop:
            payload["options"]["stop"] = request.stop

        logger.debug(
            f"Sending native Ollama request: "
            f"model={payload['model']}, messages={len(payload['messages'])}"
        )

        response_data = await self._make_request("POST", url, payload)
        return self._parse_native_response(response_data)

    def _parse_openai_response(
        self, response_data: Dict[str, Any]
    ) -> ChatCompletionResponse:
        """
        Parse OpenAI-compatible response from Ollama.

        Args:
            response_data: Raw response data

        Returns:
            Parsed ChatCompletionResponse
        """
        try:
            choices = response_data.get("choices", [])
            if not choices:
                raise RemoteProviderError(
                    "No choices in Ollama response",
                    provider_name=self.name,
                    details={"response": response_data},
                )

            first_choice = choices[0]
            message = first_choice.get("message", {})
            content = message.get("content", "")

            usage = response_data.get("usage", {})
            model = response_data.get("model", self.DEFAULT_MODEL)

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
                f"Invalid Ollama response format: {e}",
                provider_name=self.name,
                details={"response_keys": list(response_data.keys())},
            )

    def _parse_native_response(
        self, response_data: Dict[str, Any]
    ) -> ChatCompletionResponse:
        """
        Parse native Ollama API response.

        Native response format:
        {
            "model": "llama2",
            "message": {"role": "assistant", "content": "..."},
            "done": true,
            "total_duration": 123456789,
            "eval_count": 50,
            "prompt_eval_count": 20
        }

        Args:
            response_data: Raw response data

        Returns:
            Parsed ChatCompletionResponse
        """
        try:
            message = response_data.get("message", {})
            content = message.get("content", "")

            # Build usage from native fields
            usage = {
                "prompt_tokens": response_data.get("prompt_eval_count", 0),
                "completion_tokens": response_data.get("eval_count", 0),
                "total_tokens": (
                    response_data.get("prompt_eval_count", 0)
                    + response_data.get("eval_count", 0)
                ),
            }

            model = response_data.get("model", self.DEFAULT_MODEL)
            done = response_data.get("done", False)
            finish_reason = "stop" if done else "unknown"

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
                f"Invalid native Ollama response format: {e}",
                provider_name=self.name,
                details={"response_keys": list(response_data.keys())},
            )

    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate embeddings for text.

        Uses OpenAI-compatible mode by default, falls back to
        native Ollama API if configured.

        Args:
            request: Embedding request

        Returns:
            Embedding response

        Raises:
            RemoteProviderError: If the request fails
        """
        if self.use_openai_mode:
            return await self._embeddings_openai(request)
        else:
            return await self._embeddings_native(request)

    async def _embeddings_openai(
        self, request: EmbeddingRequest
    ) -> EmbeddingResponse:
        """
        Generate embeddings using OpenAI-compatible API.

        Args:
            request: Embedding request

        Returns:
            Embedding response
        """
        url = self._build_url(self.OPENAI_EMBEDDINGS_ENDPOINT)
        payload = request.to_dict()

        logger.debug(
            f"Sending OpenAI-compatible embeddings request: "
            f"model={request.model}"
        )

        response_data = await self._make_request("POST", url, payload)
        return self._parse_openai_embeddings_response(response_data)

    async def _embeddings_native(
        self, request: EmbeddingRequest
    ) -> EmbeddingResponse:
        """
        Generate embeddings using native Ollama API.

        Native embeddings endpoint: /api/embeddings
        Requires: model, prompt, keep_alive (optional)

        Args:
            request: Embedding request

        Returns:
            Embedding response
        """
        url = self._build_url(self.NATIVE_EMBEDDINGS_ENDPOINT)

        # Native Ollama embeddings use 'prompt' not 'input'
        payload = {
            "model": request.model or self.DEFAULT_MODEL,
            "prompt": request.input if isinstance(request.input, str) else request.input[0],
        }

        logger.debug(
            f"Sending native Ollama embeddings request: model={payload['model']}"
        )

        response_data = await self._make_request("POST", url, payload)
        return self._parse_native_embeddings_response(response_data)

    def _parse_openai_embeddings_response(
        self, response_data: Dict[str, Any]
    ) -> EmbeddingResponse:
        """
        Parse OpenAI-compatible embeddings response.

        Args:
            response_data: Raw response data

        Returns:
            Parsed EmbeddingResponse
        """
        try:
            data = response_data.get("data", [])
            if not data:
                raise RemoteProviderError(
                    "No embeddings in response",
                    provider_name=self.name,
                    details={"response": response_data},
                )

            embeddings = [item["embedding"] for item in sorted(data, key=lambda x: x.get("index", 0))]
            usage = response_data.get("usage", {})
            model = response_data.get("model", self.DEFAULT_MODEL)

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

    def _parse_native_embeddings_response(
        self, response_data: Dict[str, Any]
    ) -> EmbeddingResponse:
        """
        Parse native Ollama embeddings response.

        Native response format:
        {
            "embedding": [0.1, 0.2, ...],
            "model": "llama2"
        }

        Args:
            response_data: Raw response data

        Returns:
            Parsed EmbeddingResponse
        """
        try:
            embedding = response_data.get("embedding", [])
            model = response_data.get("model", self.DEFAULT_MODEL)

            # Native API returns single embedding, wrap in list
            embeddings = [embedding] if embedding else []

            return EmbeddingResponse(
                embeddings=embeddings,
                model=model,
                usage={},
                raw_response=response_data,
            )

        except KeyError as e:
            raise RemoteProviderError(
                f"Invalid native embeddings response format: {e}",
                provider_name=self.name,
                details={"response_keys": list(response_data.keys())},
            )

    async def health_check(self) -> HealthStatus:
        """
        Check provider health.

        For Ollama, checks:
        1. API server reachability
        2. Model availability (optional)
        3. Response latency

        Returns:
            Health status
        """
        start_time = time.time()

        try:
            # Try native tags endpoint first (most reliable)
            url = self._build_url(self.NATIVE_TAGS_ENDPOINT)
            client = await self._get_client()

            response = await client.get(url, timeout=10.0)
            latency_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                return HealthStatus(
                    healthy=True,
                    message=f"Ollama is healthy ({len(models)} models available)",
                    latency_ms=latency_ms,
                    details={"model_count": len(models), "models": [m.get("name") for m in models[:5]]},
                )
            else:
                return HealthStatus(
                    healthy=False,
                    message=f"Health check failed: {response.status_code}",
                    latency_ms=latency_ms,
                    details={"status_code": response.status_code},
                )

        except httpx.ConnectError as e:
            latency_ms = (time.time() - start_time) * 1000
            return HealthStatus(
                healthy=False,
                message=f"Cannot connect to Ollama: {e}",
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return HealthStatus(
                healthy=False,
                message=f"Health check failed: {e}",
                latency_ms=latency_ms,
            )

    async def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific model.

        Uses native Ollama /api/show endpoint to retrieve model details.

        Args:
            model_name: Name of the model

        Returns:
            Model information dictionary or None if not found
        """
        try:
            url = self._build_url(self.NATIVE_SHOW_ENDPOINT)
            payload = {"name": model_name}

            client = await self._get_client()
            response = await client.post(url, json=payload, timeout=10.0)

            if response.status_code == 200:
                return response.json()
            return None

        except Exception:
            return None

    async def list_models(self) -> List[str]:
        """
        List available models.

        Returns:
            List of model names
        """
        try:
            url = self._build_url(self.NATIVE_TAGS_ENDPOINT)
            client = await self._get_client()
            response = await client.get(url, timeout=10.0)

            if response.status_code == 200:
                data = response.json()
                return [model.get("name", "") for model in data.get("models", [])]
            return []

        except Exception:
            return []

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
