"""Prompt enhancer — rewrites a vague pentest prompt into a structured plan.

Takes a free-form operator prompt and produces a structured execution plan
(intent, target, engagement type, phases, recommended skills, safety gates)
by asking a premium-tier model to extract the structure as JSON.
"""

from __future__ import annotations

import json
import time
from typing import Any

from pydantic import BaseModel

from deeprak.delegate import DelegateRequest, ModelRouter, ModelTier

SYSTEM_PROMPT = (
    "You are a senior penetration testing planner. Given a user prompt, extract structured "
    "information and return ONLY valid JSON with exactly these keys:\n"
    '  "intent"            : string — concise restatement of what the user wants to achieve\n'
    '  "target"            : string or null — URL, IP, hostname, or asset name if identifiable\n'
    '  "engagement_type"   : one of: web_application | infrastructure | api | '
    "active_directory | mobile | cloud | unknown\n"
    '  "phases"            : array of strings — ordered canonical phases '
    "(e.g. recon, vuln_analysis, exploitation, post_exploitation, reporting)\n"
    '  "recommended_skills": array of strings — skill filenames or generic categories\n'
    '  "safety_gates"      : array of strings — mandatory checks before proceeding '
    "(e.g. scope validation, operator approval before exploitation)\n\n"
    "Return ONLY the JSON object. No prose, no markdown, no code fences."
)

_ENGAGEMENT_TYPES = frozenset(
    {"web_application", "infrastructure", "api", "active_directory", "mobile", "cloud", "unknown"}
)


class EnhancedPrompt(BaseModel):
    intent: str
    target: str | None
    engagement_type: str
    phases: list[str]
    recommended_skills: list[str]
    safety_gates: list[str]
    original_prompt: str
    model: str
    latency_ms: int


def _strip_fence(raw: str) -> str:
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        if s.endswith("```"):
            s = s.rsplit("```", 1)[0]
    return s.strip()


def _parse_response(raw: str, original_prompt: str, model: str, latency_ms: int) -> EnhancedPrompt:
    try:
        data: dict[str, Any] = json.loads(_strip_fence(raw))
        engagement = data.get("engagement_type", "unknown")
        if engagement not in _ENGAGEMENT_TYPES:
            engagement = "unknown"
        return EnhancedPrompt(
            intent=str(data.get("intent", original_prompt)),
            target=data.get("target") or None,
            engagement_type=engagement,
            phases=[str(p) for p in data.get("phases", [])],
            recommended_skills=[str(s) for s in data.get("recommended_skills", [])],
            safety_gates=[str(g) for g in data.get("safety_gates", [])],
            original_prompt=original_prompt,
            model=model,
            latency_ms=latency_ms,
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return EnhancedPrompt(
            intent=original_prompt,
            target=None,
            engagement_type="unknown",
            phases=[],
            recommended_skills=[],
            safety_gates=["scope validation", "operator approval before exploitation"],
            original_prompt=original_prompt,
            model=model,
            latency_ms=latency_ms,
        )


class PromptEnhancer:
    """Wraps a ModelRouter to convert vague prompts into structured plans."""

    def __init__(self, router: ModelRouter) -> None:
        self._router = router

    def enhance(self, prompt: str, system_context: str | None = None) -> EnhancedPrompt:
        system = SYSTEM_PROMPT if system_context is None else f"{SYSTEM_PROMPT}\n\n{system_context}"
        req = DelegateRequest(
            prompt=prompt,
            system_prompt=system,
            tier_override=ModelTier.PREMIUM,
            temperature=0.1,
        )
        t0 = time.monotonic()
        resp = self._router.route(req)
        latency_ms = int((time.monotonic() - t0) * 1000)
        return _parse_response(resp.content, prompt, resp.model, latency_ms)

    async def aenhance(self, prompt: str, system_context: str | None = None) -> EnhancedPrompt:
        system = SYSTEM_PROMPT if system_context is None else f"{SYSTEM_PROMPT}\n\n{system_context}"
        req = DelegateRequest(
            prompt=prompt,
            system_prompt=system,
            tier_override=ModelTier.PREMIUM,
            temperature=0.1,
        )
        t0 = time.monotonic()
        resp = await self._router.aroute(req)
        latency_ms = int((time.monotonic() - t0) * 1000)
        return _parse_response(resp.content, prompt, resp.model, latency_ms)
