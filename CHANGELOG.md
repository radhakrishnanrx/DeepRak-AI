# Changelog

All notable changes to DeepRak are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-05-10

### Added
- Initial public release.
- `deeprak.delegate` — model delegation router with task classifier, model tiers, and LiteLLM-compatible adapter.
- `deeprak.rag` — local markdown-based RAG using grep + structured output. No vector database.
- Architecture document (`ARCHITECTURE.md`) explaining the 3-layer model.
- Four foundational ADRs (`docs/design-decisions/`):
  - ADR-001: No vector database in v0.1
  - ADR-002: No UI in v0.1
  - ADR-003: LiteLLM as the model gateway
  - ADR-004: Grep over embeddings at small scale
- Continuous integration: lint (ruff), type check (mypy --strict), tests (pytest, ≥70% coverage), anonymization gate.
- MIT License.

### Notes
- v0.1 is alpha. Public API may change before v1.0.
- Installable from git only: `pip install git+https://github.com/radhakrishnanrx/DeepRak-AI.git`. PyPI publish lands in v0.2.
- No web UI, no vector DB, no MCP server hosting — see ADRs for rationale.
