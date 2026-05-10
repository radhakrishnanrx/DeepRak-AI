"""
Request routing logic: maps a DelegateRequest to a DelegateResponse by selecting
the appropriate tier and model, then delegating to the LiteLLMAdapter.
"""

import logging
import time
from typing import TYPE_CHECKING

from pydantic import BaseModel

from deeprak.delegate.classifier import TaskClassifier
from deeprak.delegate.classifier import TaskType
from deeprak.delegate.tiers import ModelTier
from deeprak.delegate.tiers import TierConfig

if TYPE_CHECKING:
    from deeprak.delegate.litellm_adapter import LiteLLMAdapter

_log = logging.getLogger(__name__)

_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({500, 502, 503, 504})


class DelegateRequest(BaseModel):
    """
    Encapsulates all inputs required to route and execute a single model call.

    Attributes:
        prompt:        The user-facing prompt text.
        task_type:     Explicit task category. When ``None``, the classifier
                       infers the category from *prompt*.
        tier_override: Force a specific ModelTier, bypassing the task-type
                       recommendation.
        max_tokens:    Per-request token cap; overrides the tier default when set.
        temperature:   Per-request sampling temperature; overrides tier default.
        system_prompt: Optional system message prepended to the conversation.
    """

    prompt: str
    task_type: TaskType | None = None
    tier_override: ModelTier | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    system_prompt: str | None = None


class DelegateResponse(BaseModel):
    """
    The result of a routed model call, including provenance and usage metadata.

    Attributes:
        content:           The model's text response.
        model:             The concrete model ID that produced the response.
        tier:              The ModelTier that was used.
        task_type:         The resolved TaskType (classified or explicit).
        prompt_tokens:     Number of tokens in the input.
        completion_tokens: Number of tokens in the output.
        latency_ms:        Wall-clock time from first request to final response, ms.
        attempts:          Total number of model calls made (1 = no retries needed).
    """

    content: str
    model: str
    tier: ModelTier
    task_type: TaskType
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    attempts: int


def _build_messages(
    prompt: str,
    system_prompt: str | None,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if system_prompt is not None:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    return messages


def _extract_response_fields(
    raw: dict[str, object],
    model: str,
    tier: ModelTier,
    task_type: TaskType,
    latency_ms: int,
    attempts: int,
) -> DelegateResponse:
    choices = raw.get("choices", [])
    if not isinstance(choices, list) or not choices:
        raise ValueError(f"Unexpected response shape from model {model!r}: {raw!r}")

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise ValueError(f"Unexpected choice shape from model {model!r}: {first_choice!r}")

    message = first_choice.get("message", {})
    if not isinstance(message, dict):
        raise ValueError(f"Unexpected message shape from model {model!r}: {message!r}")

    content = message.get("content", "")
    if not isinstance(content, str):
        content = str(content)

    usage_obj = raw.get("usage", {})
    usage: dict[str, object] = usage_obj if isinstance(usage_obj, dict) else {}

    prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
    completion_tokens = int(usage.get("completion_tokens", 0) or 0)

    return DelegateResponse(
        content=content,
        model=model,
        tier=tier,
        task_type=task_type,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        attempts=attempts,
    )


class ModelRouter:
    """
    Selects the appropriate model tier and concrete model for each request,
    then delegates execution to a :class:`~deeprak.delegate.litellm_adapter.LiteLLMAdapter`.

    Fallback behaviour: if the primary model returns a retryable error (5xx or
    network timeout), the router tries each fallback model in order before
    propagating the exception.

    Args:
        tier_configs: Mapping from every ModelTier to its TierConfig. All three
                      tiers (SMALL, STANDARD, PREMIUM) must be present.
        classifier:   Optional pre-configured TaskClassifier. A default instance
                      is created when ``None``.
        adapter:      The HTTP adapter used to call the model gateway. Required.

    Raises:
        ValueError: If *tier_configs* is missing any ModelTier, or if *adapter*
                    is ``None``.
    """

    def __init__(
        self,
        tier_configs: dict[ModelTier, TierConfig],
        classifier: TaskClassifier | None = None,
        adapter: "LiteLLMAdapter | None" = None,
    ) -> None:
        missing = [t for t in ModelTier if t not in tier_configs]
        if missing:
            names = ", ".join(str(t) for t in missing)
            raise ValueError(f"tier_configs is missing required tiers: {names}")

        if adapter is None:
            raise ValueError(
                "adapter is required. Provide a configured LiteLLMAdapter instance."
            )

        self._tier_configs = tier_configs
        self._classifier = classifier if classifier is not None else TaskClassifier()
        self._adapter = adapter

    def route(self, request: DelegateRequest) -> DelegateResponse:
        """
        Synchronously route *request* to the best available model.

        Args:
            request: The fully or partially specified delegation request.

        Returns:
            A DelegateResponse populated with the model output and metadata.

        Raises:
            RuntimeError: If all models for the selected tier fail.
            ValueError:   If the adapter returns an unexpected response shape.
        """
        task_type, tier, tier_config, max_tokens, temperature, messages = (
            self._resolve_request(request)
        )

        models = [tier_config.primary_model(), *tier_config.fallback_models()]
        start = time.monotonic()
        last_exc: Exception | None = None

        for attempt, model in enumerate(models, start=1):
            try:
                raw = self._adapter.complete(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                latency_ms = int((time.monotonic() - start) * 1000)
                return _extract_response_fields(
                    raw, model, tier, task_type, latency_ms, attempt
                )
            except Exception as exc:
                if self._is_retryable(exc):
                    _log.error(
                        "Retryable error on model %r (attempt %d/%d): %s",
                        model,
                        attempt,
                        len(models),
                        exc,
                    )
                    last_exc = exc
                    continue
                raise

        raise RuntimeError(
            f"All {len(models)} model(s) for tier {tier} failed."
        ) from last_exc

    async def aroute(self, request: DelegateRequest) -> DelegateResponse:
        """
        Asynchronously route *request* to the best available model.

        Args:
            request: The fully or partially specified delegation request.

        Returns:
            A DelegateResponse populated with the model output and metadata.

        Raises:
            RuntimeError: If all models for the selected tier fail.
            ValueError:   If the adapter returns an unexpected response shape.
        """
        task_type, tier, tier_config, max_tokens, temperature, messages = (
            self._resolve_request(request)
        )

        models = [tier_config.primary_model(), *tier_config.fallback_models()]
        start = time.monotonic()
        last_exc: Exception | None = None

        for attempt, model in enumerate(models, start=1):
            try:
                raw = await self._adapter.acomplete(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                latency_ms = int((time.monotonic() - start) * 1000)
                return _extract_response_fields(
                    raw, model, tier, task_type, latency_ms, attempt
                )
            except Exception as exc:
                if self._is_retryable(exc):
                    _log.error(
                        "Retryable error on model %r (async attempt %d/%d): %s",
                        model,
                        attempt,
                        len(models),
                        exc,
                    )
                    last_exc = exc
                    continue
                raise

        raise RuntimeError(
            f"All {len(models)} model(s) for tier {tier} failed."
        ) from last_exc

    def _resolve_request(
        self,
        request: DelegateRequest,
    ) -> tuple[TaskType, ModelTier, TierConfig, int, float, list[dict[str, str]]]:
        task_type = (
            request.task_type
            if request.task_type is not None
            else self._classifier.classify(request.prompt)
        )

        tier = (
            request.tier_override
            if request.tier_override is not None
            else TaskType.recommended_tier(task_type)
        )

        tier_config = self._tier_configs[tier]
        max_tokens = (
            request.max_tokens if request.max_tokens is not None else tier_config.max_tokens
        )
        temperature = (
            request.temperature if request.temperature is not None else tier_config.temperature
        )
        messages = _build_messages(request.prompt, request.system_prompt)

        return task_type, tier, tier_config, max_tokens, temperature, messages

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        import httpx

        if isinstance(exc, httpx.TimeoutException):
            return True
        if isinstance(exc, httpx.ConnectError):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code in _RETRYABLE_STATUS_CODES
        return False
