# ADR-005 — Chat UI Lives in `examples/`, Not in the `deeprak` Package

- **Status**: Accepted
- **Date**: 2026-05-10
- **Deciders**: radhakrishnanrx (maintainer)
- **Supersedes / Refines**: ADR-002 (No UI in v0.1) — narrows the rule rather than overturning it

## Context

ADR-002 states that DeepRak v0.1 ships no UI. That decision still holds for the **runtime package** (`deeprak/`).

Separate concern: people evaluating an orchestration runtime want to try it without writing Python. A 30-second "open the browser, type a message, see the runtime route to a model and reply" demo earns more trust than a code sample. The cost of providing this is small if the UI is intentionally minimal and lives outside the runtime package.

The trap to avoid is letting a UI (even a "small" one) accrete over time and end up shaping the runtime's design. ADR-002's lesson is real. ADR-005 narrows the rule: **no UI in `deeprak/` itself, but a reference UI is welcome in `examples/`**, where it imports DeepRak as a library, has its own optional dependencies, and is fork-and-adapt material — not core.

## Decision

DeepRak v0.1 ships a **reference chatbot in `examples/chatbot/`**:

- Backend: a single FastAPI ASGI app in `examples/chatbot/server.py` (~150-200 lines) that imports `deeprak.delegate.ModelRouter` and serves a JSON `/chat` endpoint plus a static `index.html`.
- Frontend: a single-file `examples/chatbot/static/index.html` with vanilla HTML/CSS/JavaScript. No build tooling. No framework. No bundler.
- Optional dependencies: declared as a `chatbot` extra in `pyproject.toml` (`pip install deeprak[chatbot]` pulls in `fastapi` and `uvicorn`). The runtime's core dependencies do not include these.
- README in `examples/chatbot/README.md` explains setup, configuration, and how to adapt.

The reference chatbot is **not** part of DeepRak's public API contract. Breaking changes to the example app are not breaking changes to DeepRak. Users who run it in production should fork and own it.

## Consequences

**Positive:**

- Anyone can `pip install deeprak[chatbot]` then `python examples/chatbot/server.py` and see DeepRak routing real model calls in 60 seconds, with no Python knowledge required.
- The runtime package stays pure (ADR-002 intact). No FastAPI, no JavaScript, no ASGI deps in core dependencies.
- Demonstrates the LiteLLMAdapter end-to-end with a real I/O surface, which is more convincing than unit tests as adoption material.
- Forks for each user's own use case start from a working baseline, not from scratch.

**Negative:**

- Users who don't read the README may pip-install DeepRak and be confused when no UI is exposed by default.
- The example needs maintenance as DeepRak's public API evolves. This is documented as not-a-breaking-change to manage expectations.

**Neutral:**

- Sets a pattern: future "things people want but don't belong in core" land in `examples/` first. If they prove load-bearing, they can graduate to a sibling package; they do not graduate into `deeprak/`.

## Alternatives Considered

1. **Keep ADR-002 strict; no UI anywhere in this repo.** Rejected. Newcomer ramp-up suffers, and it is no harder for a fork-friendly example to live in the same repo as the runtime than in a separate one. The maintenance is the same; discoverability is better.

2. **Ship a full SPA (React/Vue) build.** Rejected. The point of the reference chatbot is "minimum viable trust-building UI." A Webpack toolchain undermines that.

3. **Ship the chatbot as a separate repo.** Considered. Splitting it later is fine if the example grows. For v0.1, having it in the same repo means newcomers see it the moment they land on the README — which is the point.

## Validation

The chatbot is treated as success when **all** of the following hold:

- A user with Python installed can clone the repo, `pip install -e ".[chatbot]"`, set two environment variables (`DEEPRAK_GATEWAY_URL`, `DEEPRAK_API_KEY`), and run the example in under 60 seconds.
- The example shows `tier`, `model`, `latency_ms`, and `attempts` from each response in the UI, making DeepRak's routing decisions visible.
- The example's source is under 250 lines of Python and 200 lines of HTML/CSS/JS combined.

## Revisit Trigger

Revisit this ADR when **any** of the following becomes true:

- The reference chatbot exceeds 500 lines combined and is no longer "minimum viable"
- A user community emerges around the chatbot and wants features that warrant a sibling package
- A native `deeprak chat` CLI replaces the need for the HTML demo (likely lands in v0.3 alongside a CLI)
