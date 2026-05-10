"""Core unit tests for deeprak.rag — chunker, filter, search."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from deeprak.rag import Chunk, GrepRAG, MarkdownChunker, RAGFilter

# ---------------------------------------------------------------------------
# MarkdownChunker
# ---------------------------------------------------------------------------


def test_chunker_no_frontmatter_no_headings() -> None:
    chunker = MarkdownChunker()
    chunks = chunker.chunk_text("just a paragraph\nwith two lines\n")
    assert len(chunks) == 1
    assert chunks[0].heading_path == []
    assert "just a paragraph" in chunks[0].text


def test_chunker_with_frontmatter_and_headings() -> None:
    text = (
        "---\n"
        "title: Demo\n"
        "category: docs\n"
        "---\n"
        "# Top\n"
        "intro line\n"
        "more intro\n"
        "yet more intro\n"
        "## Sub\n"
        "sub line a\n"
        "sub line b\n"
        "sub line c\n"
    )
    chunks = MarkdownChunker().chunk_text(text)
    assert any(c.heading_path == ["# Top"] for c in chunks)
    assert any(c.heading_path == ["# Top", "## Sub"] for c in chunks)
    assert chunks[0].frontmatter["title"] == "Demo"
    assert chunks[0].frontmatter["category"] == "docs"


def test_chunker_chunk_file(tmp_path: Path) -> None:
    f = tmp_path / "doc.md"
    f.write_text("# H\nbody line one\nbody line two\nbody line three\n")
    chunks = MarkdownChunker().chunk_file(f)
    assert len(chunks) >= 1
    assert chunks[0].source_path == str(f)


# ---------------------------------------------------------------------------
# RAGFilter
# ---------------------------------------------------------------------------


def _make_chunk(**fm: object) -> Chunk:
    return Chunk(
        source_path="x.md",
        heading_path=["# H"],
        text="body",
        start_line=1,
        end_line=2,
        frontmatter=dict(fm),
    )


def test_filter_passes_when_no_criteria() -> None:
    chunk = _make_chunk()
    assert RAGFilter().matches(chunk)


def test_filter_categories() -> None:
    f = RAGFilter(categories=["docs", "guides"])
    assert f.matches(_make_chunk(category="docs"))
    assert not f.matches(_make_chunk(category="other"))
    assert not f.matches(_make_chunk())  # missing category


def test_filter_tags_csv_or_list() -> None:
    f = RAGFilter(tags=["security", "Privacy"])
    assert f.matches(_make_chunk(tags="security, infra"))
    assert f.matches(_make_chunk(tags=["privacy", "audit"]))
    assert not f.matches(_make_chunk(tags="infra"))


def test_filter_min_last_updated() -> None:
    threshold = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
    f = RAGFilter(min_last_updated=threshold)
    assert f.matches(_make_chunk(last_updated="2026-06-01"))
    assert not f.matches(_make_chunk(last_updated="2025-06-01"))
    assert not f.matches(_make_chunk())


def test_filter_path_glob() -> None:
    f = RAGFilter(path_glob="docs/*.md")
    assert f.matches(Chunk(source_path="docs/api.md", text="t", start_line=1, end_line=1))
    assert not f.matches(Chunk(source_path="src/api.py", text="t", start_line=1, end_line=1))


# ---------------------------------------------------------------------------
# GrepRAG
# ---------------------------------------------------------------------------


def test_grep_rag_rejects_missing_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="does not exist"):
        GrepRAG(tmp_path / "nope")


def test_grep_rag_rejects_file_root(tmp_path: Path) -> None:
    f = tmp_path / "x.md"
    f.write_text("# H\n")
    with pytest.raises(ValueError, match="not a directory"):
        GrepRAG(f)


def test_grep_rag_search_returns_matches(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text(
        "# Topic\nthe quick brown fox\njumps over the lazy dog\nanother line\n"
    )
    (tmp_path / "b.md").write_text("# Other\nno match here\n")
    rag = GrepRAG(tmp_path)
    results = rag.search("brown fox")
    assert len(results) == 1
    assert results[0].matched_line == "the quick brown fox"
    assert results[0].source_path.endswith("a.md")


def test_grep_rag_search_files_only(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("alpha beta gamma\n")
    (tmp_path / "b.md").write_text("delta epsilon\n")
    rag = GrepRAG(tmp_path)
    paths = rag.search_files_only("beta")
    assert len(paths) == 1
    assert paths[0].name == "a.md"


def test_grep_rag_search_max_results(tmp_path: Path) -> None:
    body = "\n".join(f"hit on line {i}" for i in range(20)) + "\n"
    (tmp_path / "a.md").write_text(body)
    rag = GrepRAG(tmp_path)
    assert len(rag.search("hit", max_results=5)) == 5
