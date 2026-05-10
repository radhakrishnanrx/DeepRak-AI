"""Heading-aware chunking of Markdown files for the deeprak RAG pipeline."""

from __future__ import annotations

import pathlib
import re
from typing import Any

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """A single heading-delimited section extracted from a Markdown document.

    Attributes
    ----------
    source_path:
        Absolute or relative path to the originating file (or ``"<inline>"``
        for in-memory text).
    heading_path:
        Ordered list of heading strings that form the breadcrumb to this
        chunk, e.g. ``["# Guide", "## Installation"]``.
    text:
        Raw Markdown text of the chunk body (headings themselves are
        *not* repeated inside ``text``).
    start_line:
        1-based line number of the first line of this chunk's body within
        the source file.
    end_line:
        1-based line number of the last line of this chunk's body.
    frontmatter:
        Parsed YAML frontmatter from the file. Complex values that could
        not be parsed are stored under the ``"_raw"`` key.
    """

    source_path: str
    heading_path: list[str] = Field(default_factory=list)
    text: str
    start_line: int
    end_line: int
    frontmatter: dict[str, Any] = Field(default_factory=dict)


def _extract_heading_level(line: str) -> int | None:
    """Return the ATX heading level (1-6) for *line*, or ``None``."""
    match = re.match(r"^(#{1,6})\s", line)
    if match:
        return len(match.group(1))
    return None


def _parse_frontmatter(lines: list[str]) -> tuple[dict[str, Any], int]:
    """Extract YAML frontmatter from the top of a Markdown file.

    Only simple ``key: value`` pairs are parsed inline; anything more
    complex is preserved verbatim under the ``"_raw"`` key so callers can
    handle it themselves without introducing a YAML dependency.

    Returns:
        A tuple of ``(frontmatter_dict, body_start_index)`` where
        ``body_start_index`` is the 0-based index of the first body line.
    """
    if not lines or lines[0].rstrip() != "---":
        return {}, 0

    closing_index: int | None = None
    for i in range(1, len(lines)):
        if lines[i].rstrip() in ("---", "..."):
            closing_index = i
            break

    if closing_index is None:
        return {}, 0

    raw_lines = lines[1:closing_index]
    parsed: dict[str, Any] = {}
    complex_lines: list[str] = []

    simple_kv = re.compile(r"^([A-Za-z_][A-Za-z0-9_\-]*):\s*(.*)$")

    for raw in raw_lines:
        stripped = raw.rstrip()
        m = simple_kv.match(stripped)
        if m:
            key, value = m.group(1), m.group(2).strip()
            parsed[key] = value
        else:
            complex_lines.append(stripped)

    if complex_lines:
        parsed["_raw"] = "\n".join(complex_lines)

    return parsed, closing_index + 1


class MarkdownChunker:
    """Split Markdown documents into heading-delimited :class:`Chunk` objects.

    Args:
        min_chunk_lines: Chunks whose body has fewer lines than this threshold
                         are merged into the immediately preceding sibling
                         chunk (if one exists with the same heading path).
                         Defaults to ``3``.
    """

    def __init__(self, min_chunk_lines: int = 3) -> None:
        self._min_chunk_lines = min_chunk_lines

    def chunk_file(self, path: pathlib.Path) -> list[Chunk]:
        """Chunk a Markdown file on disk.

        Args:
            path: Path to the ``.md`` file to read and chunk.

        Returns:
            Ordered list of chunks extracted from the file.
        """
        text = path.read_text(encoding="utf-8", errors="replace")
        return self.chunk_text(text, source_path=str(path))

    def chunk_text(self, text: str, source_path: str = "<inline>") -> list[Chunk]:
        """Chunk an in-memory Markdown string.

        Args:
            text:        Raw Markdown content.
            source_path: Identifier stored on each :class:`Chunk`; defaults
                         to ``"<inline>"``.

        Returns:
            Ordered list of chunks.
        """
        lines = text.splitlines(keepends=True)
        frontmatter, body_start = _parse_frontmatter(lines)
        body_lines = lines[body_start:]
        raw_chunks = self._build_raw_chunks(body_lines, body_start, source_path, frontmatter)
        return self._merge_short_chunks(raw_chunks)

    def _build_raw_chunks(
        self,
        body_lines: list[str],
        body_start: int,
        source_path: str,
        frontmatter: dict[str, Any],
    ) -> list[Chunk]:
        """Walk body lines and emit one Chunk per heading section."""
        chunks: list[Chunk] = []
        heading_stack: list[str] = []
        current_body: list[str] = []
        current_start: int = body_start + 1

        def _flush(end_line: int) -> None:
            body_text = "".join(current_body).rstrip()
            if body_text or heading_stack:
                chunks.append(
                    Chunk(
                        source_path=source_path,
                        heading_path=list(heading_stack),
                        text=body_text,
                        start_line=current_start,
                        end_line=end_line,
                        frontmatter=frontmatter,
                    )
                )

        for rel_idx, line in enumerate(body_lines):
            abs_line = body_start + rel_idx + 1
            level = _extract_heading_level(line)

            if level is not None:
                _flush(abs_line - 1)
                current_body = []
                current_start = abs_line + 1

                while heading_stack:
                    top_level = _extract_heading_level(heading_stack[-1])
                    if top_level is not None and top_level >= level:
                        heading_stack.pop()
                    else:
                        break

                heading_stack.append(line.rstrip())
            else:
                current_body.append(line)

        _flush(body_start + len(body_lines))
        return chunks

    def _merge_short_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Merge chunks shorter than min_chunk_lines into the preceding sibling."""
        if not chunks:
            return chunks

        result: list[Chunk] = []
        for chunk in chunks:
            body_lines = chunk.text.splitlines()
            too_short = len(body_lines) < self._min_chunk_lines

            if too_short and result and result[-1].heading_path == chunk.heading_path:
                prev = result[-1]
                merged_text = (prev.text + "\n" + chunk.text).strip()
                result[-1] = Chunk(
                    source_path=prev.source_path,
                    heading_path=prev.heading_path,
                    text=merged_text,
                    start_line=prev.start_line,
                    end_line=chunk.end_line,
                    frontmatter=prev.frontmatter,
                )
            else:
                result.append(chunk)

        return result
