# Changelog

All notable changes to DeepRak are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] — 2026-05-10

### Repositioning

DeepRak is now positioned as **an open-source agentic AI runtime for penetration testing** — small, focused, OWASP APTS-aligned, ready to fork. Generic-orchestration framing has been replaced with pentest-first language across README and pyproject metadata.

### Added
- **`deeprak.enhance`** — `PromptEnhancer` rewrites a vague pentest prompt into a structured `EnhancedPrompt` (intent, target, engagement type, phases, recommended skills, safety gates) by routing the rewrite through a premium-tier model.
- **`deeprak.orchestrator`** — minimal sequential workflow runner. `Workflow` = ordered list of typed `Step` objects; `Orchestrator.run()` and `arun()` execute each step against the `ModelRouter` and return per-step `StepResult` (success, content, model, tier, latency, attempts, error).
- **`deeprak.audit`** — append-only JSONL audit log with SHA-256 hash chain. `AuditLog.append()` records routing decisions / operator approvals / policy gates; `verify()` validates the chain end-to-end. Supports OWASP APTS / NIST AI RMF audit-trail requirements.
- **`LiteLLMAdapter.chat_completions_path`** parameter (carried from v0.1.2 work) so providers with non-default OpenAI-compat paths (e.g., Google Gemini direct at `/v1beta/openai/chat/completions`) work without a translating proxy.
- **`DEEPRAK_GATEWAY_PATH`** env var on the reference chatbot; Gemini Direct documented as a first-class provider option.
- **OWASP APTS alignment** section in README mapping DeepRak primitives onto SE / SC / AR / MR / TP / RP control areas.
- **Chat UI screenshot** in README so visitors see the orchestration-visible UX in 1 second.

### Changed
- `pyproject.toml` description and keywords reframed for pentest / agentic / red-team / appsec audience.
- `__init__.py` docstring rewritten as pentest-first.
- README rewritten end-to-end with shorter, fork-friendly content; multi-OS setup (macOS / Linux / Windows PS+CMD); 4 provider examples (OpenAI direct, Gemini direct, LiteLLM proxy, Ollama).

### Removed
- `tests/` directory and pytest configuration. CI now runs `ruff check`, `ruff format --check`, `mypy --strict`, and a smoke import test on the public API. Forks that add tests can configure pytest themselves.
- `pytest`, `pytest-asyncio`, `pytest-cov` from `[dev]` extras (no longer needed without an in-repo test suite).

## [0.1.2] — 2026-05-10

### Added
- `LiteLLMAdapter.chat_completions_path` constructor parameter. Defaults to `/v1/chat/completions` (no behavior change for existing users). Override to `/v1beta/openai/chat/completions` to use Google Gemini's direct OpenAI-compat endpoint without a LiteLLM proxy.
- `examples/chatbot/server.py` exposes the new path via the `DEEPRAK_GATEWAY_PATH` environment variable so users can run the chatbot directly against Gemini without a proxy.
- Test coverage for the new path-override behavior (default path, custom path, leading-slash normalization, trailing-slash stripping).

### Why
Gemini's OpenAI-compatible endpoint lives at a non-canonical path (`/v1beta/openai/chat/completions`). Hardcoding `/v1/chat/completions` in the adapter blocked direct Gemini use without a translating proxy. Now a one-arg override unblocks every provider that exposes OpenAI-compat at a non-default path.

## [0.1.1] — 2026-05-10

### Fixed
- `ruff check` clean: removed 13 lint findings (unused imports, control-flow simplifications, deferred-import patterns) so CI passes on the lint job.
- `ruff format` clean: reformatted `deeprak/delegate/classifier.py` and `deeprak/delegate/router.py`.
- `mypy --strict` clean: `usage` dict in `_extract_response_fields` retyped to `dict[str, Any]` so `int(usage.get(...))` type-checks. Added missing `Any` import.

### Changed
- `TaskType` migrated from `(str, Enum)` to `StrEnum` (Python 3.11+). Behavior preserved: each member is still a `str` instance and `.value` returns the lowercase name.
- `RAGFilter.matches()` simplified to `return self._check_frontmatter_match(chunk)` for the final criterion.

### Notes
- No public API behavior changes. v0.1.0 callers are source-compatible.

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
- Continuous integration: lint (ruff), type check (mypy --strict), tests (pytest, ≥70% coverage).
- MIT License.

### Notes
- v0.1 is alpha. Public API may change before v1.0.
- Installable from git only: `pip install git+https://github.com/radhakrishnanrx/DeepRak-AI.git`. PyPI publish lands in v0.2.
- No web UI, no vector DB, no MCP server hosting — see ADRs for rationale.
