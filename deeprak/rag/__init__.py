"""
deeprak.rag — Local markdown-based retrieval-augmented generation (RAG).

No vector database required.  Point :class:`GrepRAG` at a directory of
Markdown files and it will chunk them by heading structure, apply optional
YAML-frontmatter filters, and return richly structured match objects.

Public surface
--------------
GrepRAG         - main search engine (the entry point for callers)
RAGMatch        - a single search hit with surrounding context
RAGFilter       - declarative filter applied before pattern matching
MarkdownChunker - heading-aware splitter for Markdown text
Chunk           - a single heading-delimited section of a Markdown file
"""

from deeprak.rag.chunker import Chunk
from deeprak.rag.chunker import MarkdownChunker
from deeprak.rag.filters import RAGFilter
from deeprak.rag.grep_rag import GrepRAG
from deeprak.rag.grep_rag import RAGMatch

__all__: list[str] = [
    "Chunk",
    "GrepRAG",
    "MarkdownChunker",
    "RAGFilter",
    "RAGMatch",
]
