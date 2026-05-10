"""Minimal sequential workflow runner over a ModelRouter.

A Workflow is an ordered list of typed Steps. The Orchestrator runs each
Step against the router (sync or async), captures a typed StepResult per
step, and halts on the first failure (subsequent steps are not executed).
"""

from __future__ import annotations

import time

from pydantic import BaseModel

from deeprak.delegate import DelegateRequest, ModelRouter, ModelTier, TaskType


class Step(BaseModel):
    name: str
    prompt: str
    tier_override: ModelTier | None = None
    task_type: TaskType | None = None
    system_prompt: str | None = None


class StepResult(BaseModel):
    step_name: str
    success: bool
    content: str
    model: str
    tier: ModelTier
    task_type: TaskType
    latency_ms: int
    attempts: int
    error: str | None = None


class Workflow(BaseModel):
    name: str
    steps: list[Step]


def _build_request(step: Step) -> DelegateRequest:
    return DelegateRequest(
        prompt=step.prompt,
        tier_override=step.tier_override,
        task_type=step.task_type,
        system_prompt=step.system_prompt,
    )


def _failure_result(step: Step, latency_ms: int, exc: Exception) -> StepResult:
    return StepResult(
        step_name=step.name,
        success=False,
        content="",
        model="",
        tier=step.tier_override or ModelTier.STANDARD,
        task_type=step.task_type or TaskType.SUMMARIZATION,
        latency_ms=latency_ms,
        attempts=1,
        error=f"{type(exc).__name__}: {exc}",
    )


class Orchestrator:
    """Run a Workflow over a ModelRouter, collecting per-Step results."""

    def __init__(self, router: ModelRouter) -> None:
        self._router = router

    def run(self, workflow: Workflow) -> list[StepResult]:
        results: list[StepResult] = []
        for step in workflow.steps:
            req = _build_request(step)
            t0 = time.monotonic()
            try:
                resp = self._router.route(req)
                latency_ms = int((time.monotonic() - t0) * 1000)
                results.append(
                    StepResult(
                        step_name=step.name,
                        success=True,
                        content=resp.content,
                        model=resp.model,
                        tier=resp.tier,
                        task_type=resp.task_type,
                        latency_ms=latency_ms,
                        attempts=resp.attempts,
                    )
                )
            except Exception as exc:
                latency_ms = int((time.monotonic() - t0) * 1000)
                results.append(_failure_result(step, latency_ms, exc))
                break
        return results

    async def arun(self, workflow: Workflow) -> list[StepResult]:
        results: list[StepResult] = []
        for step in workflow.steps:
            req = _build_request(step)
            t0 = time.monotonic()
            try:
                resp = await self._router.aroute(req)
                latency_ms = int((time.monotonic() - t0) * 1000)
                results.append(
                    StepResult(
                        step_name=step.name,
                        success=True,
                        content=resp.content,
                        model=resp.model,
                        tier=resp.tier,
                        task_type=resp.task_type,
                        latency_ms=latency_ms,
                        attempts=resp.attempts,
                    )
                )
            except Exception as exc:
                latency_ms = int((time.monotonic() - t0) * 1000)
                results.append(_failure_result(step, latency_ms, exc))
                break
        return results
