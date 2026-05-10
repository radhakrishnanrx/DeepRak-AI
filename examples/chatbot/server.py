"""Reference chatbot server demonstrating orchestration-visible chat.

Uses Server-Sent Events to stream every routing decision (classification,
tier selection, model call, fallback) so the browser can display the
runtime's decisions alongside the model's reply.

This example is fork-and-adapt material, not part of the deeprak public API.
See ADR-005 in docs/design-decisions/ for the architectural rationale.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import AsyncGenerator
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from deeprak.delegate import LiteLLMAdapter
from deeprak.delegate import ModelTier
from deeprak.delegate import TaskClassifier
from deeprak.delegate import TaskType
from deeprak.delegate import TierConfig


def _split_models(env_var: str) -> list[str]:
    raw = os.environ.get(env_var, "")
    return [m.strip() for m in raw.split(",") if m.strip()]


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            "See examples/chatbot/README.md for setup."
        )
    return value


GATEWAY_URL: str = _require_env("DEEPRAK_GATEWAY_URL")
API_KEY: str = _require_env("DEEPRAK_API_KEY")

_MODELS_SMALL = _split_models("DEEPRAK_MODEL_SMALL")
_MODELS_STANDARD = _split_models("DEEPRAK_MODEL_STANDARD")
_MODELS_PREMIUM = _split_models("DEEPRAK_MODEL_PREMIUM")

if not (_MODELS_SMALL and _MODELS_STANDARD and _MODELS_PREMIUM):
    raise RuntimeError(
        "Missing required environment variables: "
        "DEEPRAK_MODEL_SMALL / DEEPRAK_MODEL_STANDARD / DEEPRAK_MODEL_PREMIUM "
        "must each list at least one model ID."
    )

TIER_CONFIGS: dict[ModelTier, TierConfig] = {
    ModelTier.SMALL: TierConfig(tier=ModelTier.SMALL, models=_MODELS_SMALL),
    ModelTier.STANDARD: TierConfig(tier=ModelTier.STANDARD, models=_MODELS_STANDARD),
    ModelTier.PREMIUM: TierConfig(tier=ModelTier.PREMIUM, models=_MODELS_PREMIUM),
}

HOST: str = os.environ.get("DEEPRAK_HOST", "127.0.0.1")
PORT: int = int(os.environ.get("DEEPRAK_PORT", "8000"))

classifier = TaskClassifier()
adapter = LiteLLMAdapter(base_url=GATEWAY_URL, api_key=API_KEY)

app = FastAPI(title="DeepRak Chatbot Example")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(os.path.join(_STATIC_DIR, "index.html"))


class ChatRequest(BaseModel):
    message: str
    tier_override: str | None = None


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _step(name: str, detail: dict[str, Any]) -> str:
    return _sse({"type": "step", "name": name, "detail": detail})


def _resolve_tier(task_type: TaskType, override: str | None) -> tuple[ModelTier, str]:
    if override:
        try:
            tier = ModelTier.from_string(override)
            return tier, f"user override = {tier.name.lower()}"
        except ValueError:
            pass
    recommended = TaskType.recommended_tier(task_type)
    return recommended, f"task_type={task_type.value} -> {recommended.name.lower()}"


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.ConnectError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {500, 502, 503, 504}
    return False


def _extract_text_and_usage(raw: dict[str, Any]) -> tuple[str, int, int]:
    """Pull the response text + token counts out of an OpenAI-format reply."""
    choices = raw.get("choices") or []
    content = ""
    if choices and isinstance(choices[0], dict):
        message = choices[0].get("message") or {}
        if isinstance(message, dict):
            content = str(message.get("content", ""))

    usage = raw.get("usage") or {}
    prompt_tokens = int(usage.get("prompt_tokens", 0) or 0) if isinstance(usage, dict) else 0
    completion_tokens = (
        int(usage.get("completion_tokens", 0) or 0) if isinstance(usage, dict) else 0
    )
    return content, prompt_tokens, completion_tokens


async def _chat_stream(req: ChatRequest) -> AsyncGenerator[str, None]:
    task_type, confidence = classifier.classify_with_confidence(req.message)
    yield _step(
        "classifier",
        {"task_type": task_type.value, "confidence": confidence},
    )

    tier, reason = _resolve_tier(task_type, req.tier_override)
    yield _step("tier_selected", {"tier": tier.name.lower(), "reason": reason})

    tier_config = TIER_CONFIGS[tier]
    models = [tier_config.primary_model(), *tier_config.fallback_models()]
    messages = [{"role": "user", "content": req.message}]

    previous_model: str | None = None
    last_exc: Exception | None = None

    for attempt_index, model_id in enumerate(models, start=1):
        if previous_model is not None:
            yield _step(
                "fallback_used",
                {"failed_model": previous_model, "fallback_model": model_id},
            )

        yield _step("model_call_start", {"model": model_id, "attempt": attempt_index})

        t0 = time.monotonic()
        try:
            raw = await adapter.acomplete(
                model=model_id,
                messages=messages,
                max_tokens=tier_config.max_tokens,
                temperature=tier_config.temperature,
            )
        except Exception as exc:
            if _is_retryable(exc):
                previous_model = model_id
                last_exc = exc
                continue
            yield _sse({"type": "error", "message": f"{type(exc).__name__}: {exc}"})
            return

        latency_ms = int((time.monotonic() - t0) * 1000)
        content, prompt_tokens, completion_tokens = _extract_text_and_usage(raw)

        yield _step(
            "model_call_done",
            {
                "model": model_id,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "latency_ms": latency_ms,
                "attempts": attempt_index,
            },
        )

        yield _sse(
            {
                "type": "response",
                "content": content,
                "model": model_id,
                "tier": tier.name.lower(),
                "task_type": task_type.value,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "latency_ms": latency_ms,
                "attempts": attempt_index,
            }
        )
        return

    yield _sse(
        {
            "type": "error",
            "message": (
                f"All {len(models)} model(s) in tier {tier.name.lower()} failed."
                + (f" Last error: {type(last_exc).__name__}: {last_exc}" if last_exc else "")
            ),
        }
    )


@app.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _chat_stream(req),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
        },
    )


@app.on_event("shutdown")
async def _close_adapter() -> None:
    await adapter.aclose()


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )
