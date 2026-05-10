"""Smoke tests: verify the package imports and core types behave as documented.

These exist so CI matrix-tests something real on every Python version. The
deeper unit tests for orchestrator / memory / context / policy land in v0.2
when those modules ship.
"""

from __future__ import annotations

import deeprak
from deeprak.delegate import (
    DelegateRequest,
    DelegateResponse,
    LiteLLMAdapter,
    ModelRouter,
    ModelTier,
    TaskClassifier,
    TaskType,
    TierConfig,
)
from deeprak.rag import (
    Chunk,
    GrepRAG,
    MarkdownChunker,
    RAGFilter,
    RAGMatch,
)


def test_version_is_string() -> None:
    assert isinstance(deeprak.__version__, str)
    assert deeprak.__version__.count(".") == 2


def test_model_tier_ordering() -> None:
    assert ModelTier.SMALL < ModelTier.STANDARD < ModelTier.PREMIUM


def test_model_tier_from_string_case_insensitive() -> None:
    assert ModelTier.from_string("small") is ModelTier.SMALL
    assert ModelTier.from_string("STANDARD") is ModelTier.STANDARD
    assert ModelTier.from_string("Premium") is ModelTier.PREMIUM


def test_task_type_recommended_tier_mapping() -> None:
    assert TaskType.recommended_tier(TaskType.PARSING) is ModelTier.SMALL
    assert TaskType.recommended_tier(TaskType.TRANSFORMATION) is ModelTier.SMALL
    assert TaskType.recommended_tier(TaskType.SUMMARIZATION) is ModelTier.STANDARD
    assert TaskType.recommended_tier(TaskType.REASONING) is ModelTier.PREMIUM
    assert TaskType.recommended_tier(TaskType.SYNTHESIS) is ModelTier.PREMIUM


def test_classifier_picks_synthesis_over_summarization() -> None:
    classifier = TaskClassifier()
    task_type = classifier.classify("Plan and summarize the next sprint.")
    assert task_type is TaskType.SYNTHESIS


def test_classifier_default_is_summarization() -> None:
    classifier = TaskClassifier()
    task_type, confidence = classifier.classify_with_confidence(
        "yes please respond yes please respond"
    )
    assert task_type is TaskType.SUMMARIZATION
    assert confidence < 0.5


def test_classifier_high_confidence_on_single_match() -> None:
    classifier = TaskClassifier()
    _, confidence = classifier.classify_with_confidence("Please summarize this paragraph.")
    assert confidence == 1.0


def test_tier_config_models_required() -> None:
    cfg = TierConfig(tier=ModelTier.SMALL, models=["gpt-4o-mini"])
    assert cfg.primary_model() == "gpt-4o-mini"
    assert cfg.fallback_models() == []


def test_delegate_request_minimal() -> None:
    req = DelegateRequest(prompt="hi")
    assert req.prompt == "hi"
    assert req.task_type is None


def test_public_api_surface() -> None:
    """Catches accidental removal of public symbols."""
    public_symbols = {
        DelegateRequest,
        DelegateResponse,
        LiteLLMAdapter,
        ModelRouter,
        ModelTier,
        TaskClassifier,
        TaskType,
        TierConfig,
        Chunk,
        GrepRAG,
        MarkdownChunker,
        RAGFilter,
        RAGMatch,
    }
    assert len(public_symbols) == 13
