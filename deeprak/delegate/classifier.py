"""
Prompt-based task classification for the delegation subsystem.
"""

import re
from enum import StrEnum
from typing import Final

from deeprak.delegate.tiers import ModelTier


class TaskType(StrEnum):
    """
    Canonical task categories understood by the delegation subsystem.

    Each value is a lowercase string so it round-trips cleanly through JSON.
    """

    PARSING = "parsing"
    TRANSFORMATION = "transformation"
    SUMMARIZATION = "summarization"
    REASONING = "reasoning"
    SYNTHESIS = "synthesis"

    @classmethod
    def recommended_tier(cls, task_type: "TaskType") -> ModelTier:
        """
        Return the default ModelTier recommended for *task_type*.

        Args:
            task_type: The task category to look up.

        Returns:
            The ModelTier that best matches the computational demands of the task.
        """
        mapping: dict[TaskType, ModelTier] = {
            cls.PARSING: ModelTier.SMALL,
            cls.TRANSFORMATION: ModelTier.SMALL,
            cls.SUMMARIZATION: ModelTier.STANDARD,
            cls.REASONING: ModelTier.PREMIUM,
            cls.SYNTHESIS: ModelTier.PREMIUM,
        }
        return mapping[task_type]


# Tier priority used when resolving multi-category matches: higher index wins.
_TIER_PRIORITY: Final[list[TaskType]] = [
    TaskType.PARSING,
    TaskType.TRANSFORMATION,
    TaskType.SUMMARIZATION,
    TaskType.REASONING,
    TaskType.SYNTHESIS,
]

_PRIORITY_RANK: Final[dict[TaskType, int]] = {t: i for i, t in enumerate(_TIER_PRIORITY)}


class TaskClassifier:
    """
    Keyword-based heuristic classifier that maps a natural-language prompt to a TaskType.

    Classification is intentionally lightweight (regex word-boundary scan) so it
    adds negligible latency before the actual model call.

    Args:
        keyword_overrides: Optional mapping of additional or replacement keywords to
                           TaskType values. These are merged *over* the built-in
                           DEFAULT_KEYWORDS, so callers can extend or override
                           individual entries without replacing the whole map.
    """

    DEFAULT_KEYWORDS: Final[dict[str, TaskType]] = {
        "parse": TaskType.PARSING,
        "extract": TaskType.PARSING,
        "tokenize": TaskType.PARSING,
        "deserialize": TaskType.PARSING,
        "convert": TaskType.TRANSFORMATION,
        "transform": TaskType.TRANSFORMATION,
        "translate": TaskType.TRANSFORMATION,
        "format": TaskType.TRANSFORMATION,
        "render": TaskType.TRANSFORMATION,
        "summarize": TaskType.SUMMARIZATION,
        "summary": TaskType.SUMMARIZATION,
        "condense": TaskType.SUMMARIZATION,
        "tldr": TaskType.SUMMARIZATION,
        "abridge": TaskType.SUMMARIZATION,
        "analyze": TaskType.REASONING,
        "diagnose": TaskType.REASONING,
        "decide": TaskType.REASONING,
        "reason": TaskType.REASONING,
        "evaluate": TaskType.REASONING,
        "compare": TaskType.REASONING,
        "plan": TaskType.SYNTHESIS,
        "design": TaskType.SYNTHESIS,
        "architect": TaskType.SYNTHESIS,
        "synthesize": TaskType.SYNTHESIS,
        "compose": TaskType.SYNTHESIS,
        "draft": TaskType.SYNTHESIS,
    }

    def __init__(self, keyword_overrides: dict[str, TaskType] | None = None) -> None:
        merged = dict(self.DEFAULT_KEYWORDS)
        if keyword_overrides:
            merged.update(keyword_overrides)
        self._patterns: list[tuple[re.Pattern[str], TaskType]] = [
            (re.compile(rf"\b{re.escape(kw)}\b"), task_type) for kw, task_type in merged.items()
        ]

    def classify(self, prompt: str) -> TaskType:
        """
        Classify *prompt* into a TaskType using keyword heuristics.

        Scanning is case-insensitive and uses whole-word boundaries to avoid
        false positives. When keywords from multiple categories are found, the
        highest-tier category wins. When no keyword matches, falls back to
        SUMMARIZATION (the STANDARD tier's representative task).

        Args:
            prompt: The raw user or system prompt to classify.

        Returns:
            The inferred TaskType.
        """
        task_type, _ = self.classify_with_confidence(prompt)
        return task_type

    def classify_with_confidence(self, prompt: str) -> tuple[TaskType, float]:
        """
        Classify *prompt* and return a confidence score alongside the TaskType.

        Confidence semantics:
        - ``1.0`` — exactly one category matched.
        - ``0.5`` — multiple categories matched (resolved by tier priority).
        - ``0.1`` — no keyword matched; default returned.

        Args:
            prompt: The raw user or system prompt to classify.

        Returns:
            A ``(TaskType, confidence)`` tuple where confidence is in ``[0.0, 1.0]``.
        """
        lowered = prompt.lower()
        matched: set[TaskType] = set()

        for pattern, task_type in self._patterns:
            if pattern.search(lowered):
                matched.add(task_type)

        if not matched:
            return TaskType.SUMMARIZATION, 0.1

        if len(matched) == 1:
            return next(iter(matched)), 1.0

        best = max(matched, key=lambda t: _PRIORITY_RANK[t])
        return best, 0.5
