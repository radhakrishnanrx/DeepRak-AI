# Architecture

DeepRak is a small Python library that routes AI tasks to right-sized models, retrieves local context, compresses what it sends, and persists state — without prescribing a UI, a vector database, or a hosting model.

This document is intentionally short. The detailed reasoning lives in `docs/design-decisions/` (the ADRs). The core code lives in `deeprak/`. Everything else is configuration and examples.

---

## Principles

1. **Engine-driven, not prompt-driven.** Workflows are typed objects. Prompts are templates with typed inputs and outputs.
2. **Delegation before premium reasoning.** Small models handle parsing, transformation, and summarization. Premium models are reserved for synthesis and reasoning.
3. **Compress before escalating.** When context grows beyond budget, summarize or drop before reaching for a bigger model.
4. **Pluggable backends.** Model gateway, RAG store, and memory store are interfaces. Swap any one without touching the others.
5. **Human-guided autonomy.** Sensitive operations go through policy gates — operator approval, scope checks, rate limits. Default is to ask, not to act.
6. **Incremental.** Versions ship in small steps. Architectural shifts go through ADRs.

---

## Modules (v0.1)

| Module | Status in v0.1 | What it does |
|---|---|---|
| `deeprak.delegate` | ✅ Implemented | Tier-aware model routing across SMALL / STANDARD / PREMIUM. OpenAI-compat HTTP adapter (configurable path for non-canonical providers like Gemini direct). Multi-model fallback. Sync + async. |
| `deeprak.rag` | ✅ Implemented | Heading-aware Markdown chunker + grep-based retrieval with frontmatter filters. No vector DB. |
| `deeprak.enhance` | ✅ Implemented | `PromptEnhancer` — converts a vague pentest prompt into a structured plan (intent, target, engagement type, phases, recommended skills, safety gates) via a premium-tier model. |
| `deeprak.orchestrator` | ✅ Implemented | Minimal sequential `Workflow` runner. Typed `Step` → `StepResult` with success/error capture and halt-on-failure. |
| `deeprak.audit` | ✅ Implemented | Append-only JSONL audit log with SHA-256 hash chain. Supports OWASP APTS / NIST AI RMF audit-trail requirements. |
| `deeprak.context` | 🚧 Planned (v0.3) | Token counting + summarize-to-budget compression. |
| `deeprak.memory` | 🚧 Planned (v0.3) | Append-only Markdown + JSON memory store. |
| `deeprak.policy` | 🚧 Planned (v0.3) | Composable gate decorators (operator approval, scope, rate limit). |

The v0.2 modules ship as typed interfaces in v0.1; their implementations land alongside their tests in v0.2.

---

## Provider flexibility

DeepRak speaks the OpenAI-compatible `/v1/chat/completions` wire format. That covers most of the 2026 model ecosystem directly or through a thin proxy:

- **Direct API keys** — OpenAI works natively. Anthropic / Google Gemini work via a LiteLLM proxy.
- **Enterprise gateways** — Azure OpenAI, AWS Bedrock (with bedrock-access-gateway), self-hosted LiteLLM.
- **Self-hosted runtimes** — Ollama, vLLM, llama.cpp server.

You point DeepRak at a `base_url` and supply an `api_key`. DeepRak forwards them in the `Authorization` header and reads the response. Credentials never leave the configured gateway URL.

See `examples/chatbot/README.md` for runnable configurations across four common provider patterns.

---

## What's intentionally not here

These are documented in the ADRs, not omitted by accident:

- No web UI in the runtime ([ADR-002](docs/design-decisions/ADR-002-no-ui.md)). A reference chatbot lives in `examples/`, not in `deeprak/` ([ADR-005](docs/design-decisions/ADR-005-chat-ui-as-example-not-core.md)).
- No vector database ([ADR-001](docs/design-decisions/ADR-001-no-vector-db.md), [ADR-004](docs/design-decisions/ADR-004-grep-over-embeddings-at-small-scale.md)).
- No bundled model gateway — DeepRak speaks the OpenAI-compatible protocol; you bring the gateway ([ADR-003](docs/design-decisions/ADR-003-litellm-as-gateway.md)).
- No multi-agent topologies in v0.1.
- No PyPI publish in v0.1 — install from git.

---

## Security posture

DeepRak is a library. It does not store credentials, accept inbound network traffic by default, or persist data outside paths you explicitly configure. The reference chatbot in `examples/` does open a local HTTP listener; users running it in production should add their own auth.

For the security-conscious deployment story — including alignment with public AI-security frameworks (OWASP LLM Top 10, NIST AI RMF, MITRE ATLAS) — see `SECURITY.md`.

---

## Adaptive skill lifecycle

DeepRak is designed for an **engagement-driven adaptive workflow**: each unit of work (an "engagement") is bracketed by skill load + skill update.

```
  pre-engagement gate                    post-engagement debrief
  ───────────────────────                ───────────────────────
  - re-load skill from disk              - record what triggered
  - check thresholds against              - update thresholds in place
    fresh threat intel                    - capture new failure modes
  - validate inputs (corpus,              - append dated entry to
    architecture, dependencies)             a sibling _debrief.md
        │                                       │
        ▼                                       ▼
              ┌────────────────────┐
              │  engagement runs   │
              │  (orchestrator     │
              │   executes the     │
              │   skill's phases)  │
              └────────────────────┘
```

Skills live as Markdown playbooks (`examples/skills/`) with an explicit *Adaptation Hooks* section at the bottom describing how the skill self-updates. The runtime does not auto-rewrite skills — every change is a Git commit you can review. What the runtime does provide:

- A pre-engagement gate primitive (planned in `deeprak.policy`, v0.2) that loads skill state and validates pre-conditions
- A post-engagement debrief primitive (planned in `deeprak.memory`, v0.2) that captures structured outcomes and appends to the skill's debrief log
- A skill loader (`deeprak.rag.GrepRAG` works today) so skills are searchable and discoverable

The result: skills evolve with use instead of going stale. The first 10 engagements teach the skill what real failure modes look like; the next 100 sharpen it.

## Extending DeepRak

The library is designed to be forked, vendored, or composed. There is no plugin registry, no entry-point magic, and no central authority.

- **New tier** → add a `ModelTier` value and route to it.
- **New retrieval backend** → implement the same interface as `GrepRAG.search()` and inject it.
- **New gateway** → implement an adapter with `complete(...)` / `acomplete(...)`. The protocol is `dict[str, Any]` in, `dict[str, Any]` out, OpenAI-compatible.
- **New policy** → add a decorator under `deeprak.policy` and apply it to your workflow steps.

Open an issue if you want a pattern documented as a first-class extension point.
