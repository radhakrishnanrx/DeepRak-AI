"""Main GrepRAG class: case-insensitive regex search over a Markdown corpus."""

from __future__ import annotations

import pathlib
import re
from typing import Any

from pydantic import BaseModel, Field

from deeprak.rag.chunker import Chunk, MarkdownChunker
from deeprak.rag.filters import RAGFilter


class RAGMatch(BaseModel):
    """A single pattern match within a Markdown chunk.

    Attributes
    ----------
    source_path:
        Path to the file that contains this match.
    heading_path:
        Breadcrumb of headings leading to the matched chunk.
    line_number:
        1-based line number of the matched line within the *source file*.
    matched_line:
        The exact line that triggered the match (stripped of trailing newline).
    context_before:
        Up to *context_lines* lines immediately before the match within the
        chunk body.
    context_after:
        Up to *context_lines* lines immediately after the match within the
        chunk body.
    frontmatter:
        Parsed frontmatter of the source file.
    chunk_text:
        Full text of the chunk that contains this match.
    """

    source_path: str
    heading_path: list[str] = Field(default_factory=list)
    line_number: int
    matched_line: str
    context_before: list[str] = Field(default_factory=list)
    context_after: list[str] = Field(default_factory=list)
    frontmatter: dict[str, Any] = Field(default_factory=dict)
    chunk_text: str


def _compile_patterns(patterns: list[str]) -> list[re.Pattern[str]]:
    """Compile each pattern string as a case-insensitive regex."""
    return [re.compile(p, re.IGNORECASE) for p in patterns]


def _matches_any(line: str, compiled: list[re.Pattern[str]]) -> bool:
    """Return ``True`` if *line* matches at least one compiled pattern."""
    return any(p.search(line) for p in compiled)


def _collect_md_files(root: pathlib.Path) -> list[pathlib.Path]:
    """Recursively collect all ``*.md`` files under *root*, sorted."""
    return sorted(root.rglob("*.md"))


def _build_matches_for_chunk(
    chunk: Chunk,
    compiled: list[re.Pattern[str]],
    context_lines: int,
) -> list[RAGMatch]:
    """Scan *chunk* for pattern hits and return one :class:`RAGMatch` per hit."""
    body_lines = chunk.text.splitlines()
    matches: list[RAGMatch] = []

    for rel_idx, line in enumerate(body_lines):
        if not _matches_any(line, compiled):
            continue

        abs_line_number = chunk.start_line + rel_idx

        before_start = max(0, rel_idx - context_lines)
        after_end = min(len(body_lines), rel_idx + context_lines + 1)

        context_before = [line_.rstrip("\n") for line_ in body_lines[before_start:rel_idx]]
        context_after = [line_.rstrip("\n") for line_ in body_lines[rel_idx + 1 : after_end]]

        matches.append(
            RAGMatch(
                source_path=chunk.source_path,
                heading_path=chunk.heading_path,
                line_number=abs_line_number,
                matched_line=line.rstrip("\n"),
                context_before=context_before,
                context_after=context_after,
                frontmatter=chunk.frontmatter,
                chunk_text=chunk.text,
            )
        )

    return matches


class GrepRAG:
    """Case-insensitive regex search engine over a local Markdown corpus.

    The corpus is never loaded into memory all at once; files are read,
    chunked, and scanned one at a time so the memory footprint stays
    proportional to the largest single file rather than the whole corpus.

    Args:
        corpus_root:           Root directory walked recursively for ``*.md``.
        chunker:               Custom MarkdownChunker; default created if None.
        default_context_lines: Surrounding lines included in each RAGMatch
                               when caller does not override.

    Raises:
        ValueError: If *corpus_root* does not exist or is not a directory.
    """

    def __init__(
        self,
        corpus_root: pathlib.Path,
        chunker: MarkdownChunker | None = None,
        default_context_lines: int = 3,
    ) -> None:
        if not corpus_root.exists():
            raise ValueError(f"corpus_root does not exist: {corpus_root}")
        if not corpus_root.is_dir():
            raise ValueError(f"corpus_root is not a directory: {corpus_root}")

        self._corpus_root = corpus_root
        self._chunker = chunker if chunker is not None else MarkdownChunker()
        self._default_context_lines = default_context_lines

    def search(
        self,
        patterns: list[str] | str,
        filter_: RAGFilter | None = None,
        context_lines: int | None = None,
        max_results: int = 50,
    ) -> list[RAGMatch]:
        """Search the corpus for lines matching any of *patterns*.

        Args:
            patterns:      One pattern string or a list of pattern strings.
                           A line matches if any pattern hits (OR semantics).
            filter_:       Optional RAGFilter applied to each chunk before
                           scanning lines.
            context_lines: Override default context lines for this call.
            max_results:   Hard cap on the number of RAGMatch objects returned.

        Returns:
            Matches ordered by ``(source_path, line_number)``.
        """
        if isinstance(patterns, str):
            patterns = [patterns]

        compiled = _compile_patterns(patterns)
        ctx = context_lines if context_lines is not None else self._default_context_lines
        results: list[RAGMatch] = []

        for md_file in _collect_md_files(self._corpus_root):
            if len(results) >= max_results:
                break

            chunks = self._chunker.chunk_file(md_file)

            for chunk in chunks:
                if len(results) >= max_results:
                    break
                if filter_ is not None and not filter_.matches(chunk):
                    continue

                hits = _build_matches_for_chunk(chunk, compiled, ctx)
                remaining = max_results - len(results)
                results.extend(hits[:remaining])

        results.sort(key=lambda m: (m.source_path, m.line_number))
        return results

    def search_files_only(
        self,
        pattern: str,
        filter_: RAGFilter | None = None,
    ) -> list[pathlib.Path]:
        """Return paths of files containing at least one match for *pattern*.

        Faster alternative to :meth:`search` when callers only need to know
        which files are relevant, not the exact lines.

        Args:
            pattern: A single case-insensitive regex pattern.
            filter_: Optional filter; when set, file is included only if at
                     least one of its chunks passes the filter.

        Returns:
            Sorted list of matching file paths.
        """
        compiled = re.compile(pattern, re.IGNORECASE)
        matched_paths: list[pathlib.Path] = []

        for md_file in _collect_md_files(self._corpus_root):
            try:
                content = md_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            if filter_ is not None:
                chunks = self._chunker.chunk_file(md_file)
                if not any(filter_.matches(c) for c in chunks):
                    continue

            if compiled.search(content):
                matched_paths.append(md_file)

        return matched_paths
