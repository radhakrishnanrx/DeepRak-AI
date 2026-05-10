"""
HTTP adapter that speaks the OpenAI-compatible chat-completions protocol,
suitable for use with LiteLLM proxy or any OpenAI-compatible gateway.
"""

import asyncio
import logging
import time
from typing import Any, Final, Self

import httpx
from pydantic import BaseModel, field_validator

_log = logging.getLogger(__name__)

_DEFAULT_CHAT_COMPLETIONS_PATH: Final[str] = "/v1/chat/completions"
_RETRYABLE_STATUS_CODES: Final[frozenset[int]] = frozenset({500, 502, 503, 504})
_BACKOFF_BASE_S: Final[float] = 1.0


class _AdapterConfig(BaseModel):
    """Internal validated configuration for LiteLLMAdapter."""

    base_url: str
    api_key: str
    chat_completions_path: str = _DEFAULT_CHAT_COMPLETIONS_PATH
    timeout_s: float = 60.0
    max_retries_per_model: int = 2

    @field_validator("base_url")
    @classmethod
    def _strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

    @field_validator("chat_completions_path")
    @classmethod
    def _normalize_path(cls, v: str) -> str:
        if not v.startswith("/"):
            v = "/" + v
        return v.rstrip("/")

    @field_validator("timeout_s")
    @classmethod
    def _positive_timeout(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("timeout_s must be positive.")
        return v

    @field_validator("max_retries_per_model")
    @classmethod
    def _non_negative_retries(cls, v: int) -> int:
        if v < 0:
            raise ValueError("max_retries_per_model must be >= 0.")
        return v


class LiteLLMAdapter:
    """
    Thin HTTP adapter for OpenAI-compatible chat-completion endpoints.

    Defaults to the canonical ``/v1/chat/completions`` path used by OpenAI,
    LiteLLM proxies, Azure OpenAI, Ollama, vLLM, etc. Override
    ``chat_completions_path`` for providers that expose OpenAI-compat at a
    non-standard path — e.g. Google Gemini direct
    (``/v1beta/openai/chat/completions``).

    Handles authentication, retry-with-exponential-backoff on transient errors,
    and provides both synchronous and asynchronous call paths.

    Supports use as both a synchronous and asynchronous context manager so that
    underlying ``httpx`` connections are always closed cleanly.

    Args:
        base_url:              Root URL of the gateway (e.g. ``"http://localhost:4000"``).
                               Trailing slashes are stripped automatically.
        api_key:               Bearer token sent in the ``Authorization`` header.
        chat_completions_path: Path appended to ``base_url`` for chat-completion
                               requests. Defaults to ``"/v1/chat/completions"``.
                               Use ``"/v1beta/openai/chat/completions"`` for
                               Google Gemini's direct OpenAI-compat endpoint.
        timeout_s:             Per-request timeout in seconds. Defaults to ``60.0``.
        max_retries_per_model: How many times to retry a single model on transient
                               errors before giving up. Defaults to ``2``.

    Raises:
        pydantic.ValidationError: If any constructor argument fails validation.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        chat_completions_path: str = _DEFAULT_CHAT_COMPLETIONS_PATH,
        timeout_s: float = 60.0,
        max_retries_per_model: int = 2,
    ) -> None:
        self._cfg = _AdapterConfig(
            base_url=base_url,
            api_key=api_key,
            chat_completions_path=chat_completions_path,
            timeout_s=timeout_s,
            max_retries_per_model=max_retries_per_model,
        )
        self._sync_client = httpx.Client(timeout=self._cfg.timeout_s)
        self._async_client = httpx.AsyncClient(timeout=self._cfg.timeout_s)

    def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> dict[str, Any]:
        """
        Send a synchronous chat-completion request.

        Retries up to ``max_retries_per_model`` times on 5xx responses and
        network-level errors, using exponential backoff (1 s, 2 s, 4 s, ...).

        Args:
            model:       The model ID string forwarded to the gateway.
            messages:    OpenAI-format message list.
            max_tokens:  Maximum number of completion tokens to generate.
            temperature: Sampling temperature.

        Returns:
            The parsed JSON response body as a plain ``dict``.

        Raises:
            httpx.HTTPStatusError:  On a non-retryable 4xx response, or after
                                    all retries are exhausted for 5xx.
            httpx.TimeoutException: If the request times out on every attempt.
            httpx.ConnectError:     If the gateway is unreachable on every attempt.
        """
        url = self._cfg.base_url + self._cfg.chat_completions_path
        payload = self._build_payload(model, messages, max_tokens, temperature)
        headers = self._build_headers()

        last_exc: Exception | None = None
        for attempt in range(self._cfg.max_retries_per_model + 1):
            if attempt > 0:
                self._sync_sleep(attempt)
            try:
                response = self._sync_client.post(url, json=payload, headers=headers)
                if response.status_code in _RETRYABLE_STATUS_CODES:
                    last_exc = httpx.HTTPStatusError(
                        f"Server error {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                    _log.error(
                        "Retryable HTTP %d from %r (attempt %d/%d)",
                        response.status_code,
                        model,
                        attempt + 1,
                        self._cfg.max_retries_per_model + 1,
                    )
                    continue
                response.raise_for_status()
                result: dict[str, Any] = response.json()
                return result
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                _log.error(
                    "Network error calling %r (attempt %d/%d): %s",
                    model,
                    attempt + 1,
                    self._cfg.max_retries_per_model + 1,
                    exc,
                )
                last_exc = exc
            except httpx.HTTPStatusError:
                raise

        raise last_exc or RuntimeError(f"All attempts exhausted for model {model!r}.")

    async def acomplete(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> dict[str, Any]:
        """
        Send an asynchronous chat-completion request.

        Semantics are identical to :meth:`complete` but uses ``asyncio.sleep``
        for backoff and an ``httpx.AsyncClient`` for I/O.

        Args:
            model:       The model ID string forwarded to the gateway.
            messages:    OpenAI-format message list.
            max_tokens:  Maximum number of completion tokens to generate.
            temperature: Sampling temperature.

        Returns:
            The parsed JSON response body as a plain ``dict``.

        Raises:
            httpx.HTTPStatusError:  On a non-retryable 4xx response, or after
                                    all retries are exhausted for 5xx.
            httpx.TimeoutException: If the request times out on every attempt.
            httpx.ConnectError:     If the gateway is unreachable on every attempt.
        """
        url = self._cfg.base_url + self._cfg.chat_completions_path
        payload = self._build_payload(model, messages, max_tokens, temperature)
        headers = self._build_headers()

        last_exc: Exception | None = None
        for attempt in range(self._cfg.max_retries_per_model + 1):
            if attempt > 0:
                await self._async_sleep(attempt)
            try:
                response = await self._async_client.post(url, json=payload, headers=headers)
                if response.status_code in _RETRYABLE_STATUS_CODES:
                    last_exc = httpx.HTTPStatusError(
                        f"Server error {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                    _log.error(
                        "Retryable HTTP %d from %r (async attempt %d/%d)",
                        response.status_code,
                        model,
                        attempt + 1,
                        self._cfg.max_retries_per_model + 1,
                    )
                    continue
                response.raise_for_status()
                result: dict[str, Any] = response.json()
                return result
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                _log.error(
                    "Network error calling %r (async attempt %d/%d): %s",
                    model,
                    attempt + 1,
                    self._cfg.max_retries_per_model + 1,
                    exc,
                )
                last_exc = exc
            except httpx.HTTPStatusError:
                raise

        raise last_exc or RuntimeError(f"All async attempts exhausted for model {model!r}.")

    def close(self) -> None:
        """
        Close the underlying synchronous HTTP client.

        For the async client, prefer :meth:`aclose` when inside an async context.
        Calling ``close()`` outside an async context schedules the async client
        for cleanup on a temporary loop.
        """
        self._sync_client.close()
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self._async_client.aclose())

    async def aclose(self) -> None:
        """
        Asynchronously close both HTTP clients.

        Prefer this over :meth:`close` when already inside an async context.
        """
        self._sync_client.close()
        await self._async_client.aclose()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        self.close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        await self.aclose()

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._cfg.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _build_payload(
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> dict[str, Any]:
        return {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

    @staticmethod
    def _sync_sleep(attempt: int) -> None:
        delay = min(_BACKOFF_BASE_S * (2 ** (attempt - 1)), 30.0)
        time.sleep(delay)

    @staticmethod
    async def _async_sleep(attempt: int) -> None:
        delay = min(_BACKOFF_BASE_S * (2 ** (attempt - 1)), 30.0)
        await asyncio.sleep(delay)
