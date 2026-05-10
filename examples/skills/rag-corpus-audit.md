# Skill: RAG Corpus Audit

> **Adaptive skill** — designed to be refined before each engagement (pre-flight gate) and updated after (post-engagement debrief). See *Adaptation Hooks* at the end.

## Purpose

Audit a Markdown corpus for retrieval quality before plugging it into a RAG-backed agent. Catches the most common production failure modes: missing frontmatter, inconsistent headings, stale content, classified data leaks, ambiguous chunks. Runs against `deeprak.rag.GrepRAG` directly — no vector DB needed at small scale.

## When to Use

- A new corpus is being onboarded into a RAG-backed agent.
- A retrieval-quality regression is observed (wrong sources cited, missing answers).
- A quarterly corpus health review is due.
- Before exporting a corpus to a vendor / external partner / customer.

## Pre-Audit Gates

1. Corpus root path confirmed.
2. Classification expectations documented (which docs are public vs internal vs restricted).
3. Sample queries collected from real users (10-20 minimum).
4. Acceptable retrieval metrics agreed (e.g., at least one top-3 hit on >= 90% of sample queries).

## Phases

### Phase 1: Inventory

- Count files. Histogram by directory. Largest 10 files. Smallest 10 files.
- Frontmatter coverage: % files with `---` block, % with each expected key (`title`, `category`, `tags`, `last_updated`).
- Heading depth distribution (`#`, `##`, `###`, ...) — flag files with no headings or single-line giants.

### Phase 2: Freshness

- Sort files by `last_updated`. Flag any older than your freshness budget (e.g., 180 days).
- Cross-reference Git history: when was each file last touched? Frontmatter `last_updated` should match within a tolerance.

### Phase 3: Classification leak check

- Search corpus for tokens that should not appear in this scope (PII patterns, internal-only terms, vendor names).
- Use word-boundary regex; track false positives explicitly.

### Phase 4: Retrieval smoke test

- Run sample queries against `deeprak.rag.GrepRAG.search(...)`.
- For each query, record: top match path, match line, distance to expected answer.
- Score: query has at least one hit in top-3 → pass; no hits → fail; wrong-doc top hit → review.

### Phase 5: Chunking review

- For the 10 longest files, sample 3 random chunks each. Read aloud. Does the chunk stand alone or does it require neighboring context to make sense?
- Decide: tighten heading structure, reduce file size, or accept and document.

## Output

A short report containing inventory tables, freshness flags, classification-leak hits, retrieval-smoke-test scores, and chunking observations. Actionable items are owner-tagged with due dates.

## Anti-Patterns

1. Auditing only structure, never content. Bad chunks pass structural checks.
2. Using only synthetic queries. Real user queries surface real failures; synthetic queries flatter the audit.
3. Ignoring `last_updated` drift between frontmatter and Git history. The drift IS the signal.
4. Treating the audit as one-time. Adaptive skills run on a cadence, not just at onboarding.

## References

- OWASP GenAI Project — Data Security Risks 2026
- RAGAS evaluation framework — faithfulness, context precision, context recall

## Adaptation Hooks

- **Pre-engagement** (skill loads at engagement start): re-read this file, check whether thresholds have been adjusted by prior post-engagement updates, refresh the sample-query list from the most recent debrief.
- **Post-engagement** (skill updates at engagement end): record which thresholds triggered, which new failure modes were observed, whether sample queries should be added or retired. Append a dated entry to a sibling `_debrief.md` and update this skill's thresholds in place.
