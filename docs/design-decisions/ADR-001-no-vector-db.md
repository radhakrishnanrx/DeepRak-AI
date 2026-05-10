# ADR-001 — No Vector Database in v0.1

- **Status**: Accepted
- **Date**: 2026-05-10
- **Deciders**: radhakrishnanrx (maintainer)

## Context

Most agent frameworks ship with a vector database integration as the default RAG backend (Pinecone, Qdrant, Chroma, pgvector). At small corpus scale (under ~200 documents), this is over-engineering. It adds infrastructure dependencies, embedding cost, query latency, and a class of failure modes (stale embeddings, hybrid search tuning, reranking thresholds) that don't exist in simpler approaches.

The problem most agent-RAG demos solve at small scale is "retrieve relevant context for an LLM prompt." At that scale, structured grep with metadata filtering is faster, simpler, more debuggable, and produces equally accurate results — without an embedding model in the loop.

The problem agent-RAG benchmarks show vector retrieval winning is at large scale (10k+ documents) with diverse queries. That regime is real and important. It's not the regime DeepRak v0.1 targets.

## Decision

DeepRak v0.1 ships a **grep-based RAG implementation only**. No vector database integration. No embedding model integration in v0.1.

The `deeprak.rag.grep_rag` module reads markdown files from a configured directory, applies category and freshness filters, and returns structured matches (file path + matched line + N lines of context window).

A vector backend may be added in v0.2 **behind an opt-in flag**, never as the default for small-scale corpora. The interface is designed so that `GrepRAG` and a future `VectorRAG` are interchangeable from the orchestrator's perspective.

## Consequences

**Positive:**

- Zero infrastructure dependencies. A user can `pip install deeprak` and have working RAG against a `docs/` folder in 60 seconds.
- Latency is dominated by file I/O, typically under 50ms for corpora up to ~500 markdown files. No embedding API call.
- Results are explainable: the matched line is exactly what was retrieved. No "the embedding model thought this was similar."
- Testable without mocks: tests run against real markdown fixtures with no embedding service.

**Negative:**

- Will not scale to 10k+ documents efficiently. Users at that scale will need a vector backend.
- Cannot retrieve on semantic similarity alone (e.g., "stuff about authentication" won't surface a doc that discusses "session tokens" without keyword overlap). Users must construct queries that contain keyword overlap with target documents.
- Limited to text formats with grep-friendly structure (markdown, plain text, structured JSON). Image, audio, code-AST embeddings are not in scope for v0.1.

**Neutral:**

- Forces clear thinking about corpus structure. If grep doesn't find the answer, the corpus likely needs better headings, metadata, or chunking — not better embeddings.

## Alternatives Considered

1. **Default vector DB integration (Chroma in-memory)** — rejected. Adds an embedding model dependency for users who don't need it; embedding-model API cost is non-trivial; latency is 200-500ms vs sub-50ms for grep at small scale.

2. **Default to a hybrid (grep + vector)** — rejected. Doubles the failure surface and tuning burden for v0.1. A hybrid implementation can be added in v0.2 once the grep backend is proven.

3. **Vector-only, no grep** — rejected. Foregoes the simplicity advantage that makes DeepRak adoptable in 60 seconds.

## Validation

The maintainer's personal AI workflow system (the source pattern that motivated DeepRak) operates on roughly 90 markdown files — 41 memory entries and 49 skill playbooks — using grep-based search. In production-like daily use over 6+ months, grep retrieval has produced fewer false-positive retrievals and faster answers than the same corpus indexed in a small Chroma instance. Concrete benchmark to be published in `docs/architecture/rag.md` in a future release.

## Revisit Trigger

Revisit this ADR when **any** of the following becomes true:

- A user reports a corpus larger than 500 markdown files where grep latency exceeds 200ms p95
- Multiple users request semantic-similarity retrieval that grep cannot satisfy
- A clear superset use case emerges that requires both grep and vector retrieval simultaneously
