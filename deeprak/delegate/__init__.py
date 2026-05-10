"""
deeprak.delegate — Task-aware model delegation subsystem.

Routes AI tasks to appropriately-sized models based on task complexity:
cheap tasks (parsing, transformation, summarization) are sent to small/standard
models; expensive tasks (reasoning, synthesis) are escalated to premium models.
The caller supplies a tier -> concrete model-ID configuration; this package
handles classification, routing, fallback, and HTTP transport.
"""

from deeprak.delegate.classifier import TaskClassifier, TaskType
from deeprak.delegate.litellm_adapter import LiteLLMAdapter
from deeprak.delegate.router import DelegateRequest, DelegateResponse, ModelRouter
from deeprak.delegate.tiers import ModelTier, TierConfig

__all__ = [
    "DelegateRequest",
    "DelegateResponse",
    "LiteLLMAdapter",
    "ModelRouter",
    "ModelTier",
    "TaskClassifier",
    "TaskType",
    "TierConfig",
]
