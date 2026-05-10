# ADR-004 — Grep Over Embeddings at Small Scale

- **Status**: Accepted
- **Date**: 2026-05-10
- **Deciders**: radhakrishnanrx (maintainer)

## Context

ADR-001 establishes that DeepRak v0.1 ships no vector database. This ADR documents the **positive** technical claim that motivates that choice: at corpus sizes under approximately 200 documents, structured grep with metadata filtering and context windowing is competitive with — and often superior to — naive vector retrieval on three measurable axes: accuracy, latency, and explainability.

This is a contested claim in 2026. The default answer in agent-framework documentation is "RAG = embeddings + vector DB." The cost of that default is high (embedding model API spend, ingestion latency, query latency, infrastructure complexity, hybrid-search tuning) and the benefit at small scale is often imaginary. Asserting this claim publicly, with documentation and benchmark, is part of DeepRak's brand position.

## Decision

The DeepRak `rag` module is **grep-first** at v0.1. The retrieval interface returns:

- Source file path
- Line number of the match
- Matched line text
- N lines of surrounding context (configurable, default 3)
- Optional metadata extracted from the file's frontmatter (category, tags, last-updated)

Filtering is applied as additional grep constraints (file pattern, frontmatter key/value match, date range). Results are deduplicated by file and ranked by match density per file by default, with overrideable ranking strategies.

A future vector backend (v0.2+) will implement the same interface, so users can switch backends with a configuration change. The interface is designed to be backend-agnostic.

## Consequences

**Positive:**

- Retrieval results are inspectable and exact. The user sees the literal matched line, not "we think this is similar."
- No embedding API cost. No GPU. No model loading. No per-query embedding latency.
- Sub-50ms typical retrieval for corpora up to ~500 markdown files on commodity hardware.
- Robust to typos in target documents and synonyms (when the user knows to query with synonyms). Less robust to genuinely paraphrased content (see Negative below).
- Pre-existing tools (`ripgrep`, `grep -rE`) are available everywhere. Diagnosing retrieval issues is "I can run this query myself."

**Negative:**

- Pure grep does not retrieve on semantic similarity. A query for "authentication" will not surface a doc that only discusses "session tokens" if the keyword does not overlap.
- Mitigation: users construct queries with multiple keyword candidates. The `deeprak.rag.grep_rag` module accepts a list of patterns and combines results.
- Long-form documents with single relevant paragraphs are returned as whole-document hits. Mitigation: heading-aware chunking (`deeprak.rag.chunker`) splits long markdown by section before searching.
- Non-text formats (images, tables, structured data) are out of scope until the corpus loader is extended.

**Neutral:**

- Forces users to maintain corpus structure (consistent headings, frontmatter, naming) — the same discipline that makes vector retrieval also work better. The discipline is good either way.

## Alternatives Considered

1. **Default to a small embedding model (e.g., `all-MiniLM-L6-v2`)** — rejected for v0.1. Adds an embedding model dependency, embedding cost (or GPU), and an ingestion step. Saves nothing at small scale where keyword-overlap queries already work.

2. **BM25 (lexical retrieval with TF-IDF weighting)** — considered. Lands as an option in v0.2 between grep and vector. BM25 is a reasonable middle ground but adds a tokenizer + index dependency that grep avoids. v0.1 ships grep; v0.2 may add BM25 for users who want better ranking without the embedding overhead.

3. **Hybrid grep + lightweight semantic re-rank** — considered for v0.2+. Useful when the user knows their corpus has both keyword-discoverable and paraphrase-discoverable content. Not in v0.1 scope.

## Validation

A benchmark comparing grep-based retrieval against a baseline vector retrieval (Chroma + `text-embedding-3-small`) on the maintainer's 41-file markdown corpus is planned for `docs/architecture/rag.md`. Preliminary observations from 6 months of daily use:

- Grep-based retrieval has produced fewer false-positive top-3 results than Chroma on the same corpus.
- Grep-based retrieval p95 latency is approximately 30ms; Chroma p95 with the same corpus indexed is approximately 220ms (mostly embedding-API call).
- Grep-based retrieval has zero infrastructure cost; Chroma + embeddings costs approximately $0.10 per 1000 queries at 2026 OpenAI prices.

These are anecdotal observations from a single corpus. The published benchmark in v0.2 will use multiple corpora and standard retrieval evaluation metrics (Recall@K, MRR, NDCG).

## Revisit Trigger

Revisit this ADR when **any** of the following becomes true:

- A reproducible benchmark on a corpus relevant to DeepRak users shows vector retrieval outperforming grep on accuracy metrics
- A user submits a corpus where grep-based retrieval consistently fails on real queries
- Corpus sizes in DeepRak deployments routinely exceed 1000 documents (where vector retrieval's amortized cost wins)
