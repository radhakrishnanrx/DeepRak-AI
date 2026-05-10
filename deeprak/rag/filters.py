"""Declarative filters applied to Chunks before pattern matching."""

from __future__ import annotations

import datetime
import fnmatch
from typing import Any

from pydantic import BaseModel

from deeprak.rag.chunker import Chunk


def _parse_tags(raw: Any) -> list[str]:
    """Normalise a frontmatter ``tags`` value into a flat list of strings."""
    if isinstance(raw, list):
        return [str(t).strip().lower() for t in raw if str(t).strip()]
    if isinstance(raw, str):
        return [t.strip().lower() for t in raw.split(",") if t.strip()]
    return []


def _parse_datetime(raw: Any) -> datetime.datetime | None:
    """Parse *raw* as ISO 8601 datetime; return ``None`` if unparseable."""
    if not raw or not isinstance(raw, str):
        return None
    raw = raw.strip()
    if not raw:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.UTC)
            return dt
        except ValueError:
            continue
    return None


class RAGFilter(BaseModel):
    """Declarative filter that gates which chunks are eligible for matching.

    All active fields must pass simultaneously (logical AND). A field is
    *active* when it is not ``None``.

    Attributes
    ----------
    categories:
        Accepted values for the ``category`` frontmatter key.
    tags:
        The chunk's ``tags`` field must contain at least one of these
        (case-insensitive).
    min_last_updated:
        The chunk's ``last_updated`` (ISO 8601) must be on or after this
        datetime.
    path_glob:
        Shell-style glob (``fnmatch``) matched against ``chunk.source_path``.
    frontmatter_match:
        Every ``{key: value}`` pair must be present in the chunk's
        frontmatter (string equality, case-sensitive).
    """

    categories: list[str] | None = None
    tags: list[str] | None = None
    min_last_updated: datetime.datetime | None = None
    path_glob: str | None = None
    frontmatter_match: dict[str, str] | None = None

    def matches(self, chunk: Chunk) -> bool:
        """Return ``True`` if *chunk* satisfies every active filter criterion."""
        if not self._check_categories(chunk):
            return False
        if not self._check_tags(chunk):
            return False
        if not self._check_min_last_updated(chunk):
            return False
        if not self._check_path_glob(chunk):
            return False
        return self._check_frontmatter_match(chunk)

    def _check_categories(self, chunk: Chunk) -> bool:
        if self.categories is None:
            return True
        raw = chunk.frontmatter.get("category")
        if raw is None:
            return False
        return str(raw).strip() in self.categories

    def _check_tags(self, chunk: Chunk) -> bool:
        if self.tags is None:
            return True
        raw = chunk.frontmatter.get("tags")
        if raw is None:
            return False
        chunk_tags = set(_parse_tags(raw))
        filter_tags = {t.strip().lower() for t in self.tags}
        return bool(chunk_tags & filter_tags)

    def _check_min_last_updated(self, chunk: Chunk) -> bool:
        if self.min_last_updated is None:
            return True
        raw = chunk.frontmatter.get("last_updated")
        chunk_dt = _parse_datetime(raw)
        if chunk_dt is None:
            return False
        threshold = self.min_last_updated
        if threshold.tzinfo is None:
            threshold = threshold.replace(tzinfo=datetime.UTC)
        return chunk_dt >= threshold

    def _check_path_glob(self, chunk: Chunk) -> bool:
        if self.path_glob is None:
            return True
        return fnmatch.fnmatch(chunk.source_path, self.path_glob)

    def _check_frontmatter_match(self, chunk: Chunk) -> bool:
        if self.frontmatter_match is None:
            return True
        for key, expected in self.frontmatter_match.items():
            actual = chunk.frontmatter.get(key)
            if actual is None or str(actual) != expected:
                return False
        return True
