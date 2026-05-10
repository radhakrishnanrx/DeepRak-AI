"""
Tier definitions and per-tier model configuration for the delegation subsystem.
"""

from enum import IntEnum
from typing import Final

from pydantic import BaseModel
from pydantic import field_validator


class ModelTier(IntEnum):
    """
    Ordered capability tiers for model selection.

    Higher numeric value indicates greater capability (and cost).
    """

    SMALL = 1
    STANDARD = 2
    PREMIUM = 3

    @classmethod
    def from_string(cls, s: str) -> "ModelTier":
        """
        Parse a ModelTier from a case-insensitive string name.

        Args:
            s: One of ``"small"``, ``"standard"``, or ``"premium"`` (any case).

        Returns:
            The matching ModelTier member.

        Raises:
            ValueError: If *s* does not match any tier name.
        """
        normalised = s.strip().upper()
        try:
            return cls[normalised]
        except KeyError:
            valid = ", ".join(m.name.lower() for m in cls)
            raise ValueError(f"Unknown tier {s!r}. Valid values: {valid}") from None

    def __str__(self) -> str:
        return self.name.lower()


class TierConfig(BaseModel):
    """
    Configuration for a single model tier.

    Attributes:
        tier:        The ModelTier this configuration applies to.
        models:      Ordered list of model IDs. The first entry is the primary
                     model; subsequent entries are tried in order on failure.
        max_tokens:  Upper bound on completion tokens for this tier.
        temperature: Sampling temperature applied when no per-request override
                     is provided.
    """

    tier: ModelTier
    models: list[str]
    max_tokens: int = 16_384
    temperature: float = 0.3

    _MIN_MODELS: Final[int] = 1

    @field_validator("models")
    @classmethod
    def _models_non_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("'models' must contain at least one model ID.")
        return v

    def primary_model(self) -> str:
        """
        Return the preferred (first) model ID for this tier.

        Returns:
            The first element of :attr:`models`.
        """
        return self.models[0]

    def fallback_models(self) -> list[str]:
        """
        Return the ordered list of fallback model IDs (all except the primary).

        Returns:
            A (possibly empty) list of model IDs to try after the primary fails.
        """
        return self.models[1:]
