# ADR-002 — No UI in v0.1

- **Status**: Accepted
- **Date**: 2026-05-10
- **Deciders**: radhakrishnanrx (maintainer)

## Context

The maintainer's prior agent platform initiative (a private predecessor) failed primarily because architecture became frontend-heavy before the orchestration runtime was stable. Workflows became prompt-driven through a UI rather than engine-driven through a typed runtime. State management drifted between UI and backend. Premium model tokens were burned on UI rendering tasks. The framework's coherence collapsed under the weight of frontend complexity.

Agent frameworks that ship a UI early (a pattern observed across the 2024-2026 agent-framework ecosystem) tend to converge on the same failure modes: the UI's expressive limits define the runtime's capabilities, instead of the runtime defining what the UI can show. The runtime becomes a backend for the UI rather than a primitive that any UI could be built on top of.

DeepRak's value proposition is the runtime — orchestration, delegation, RAG, context, memory, policy. None of that requires a UI to deliver value. A user can compose DeepRak primitives in a Python script, a Jupyter notebook, an MCP server, a CLI, a web app, or a CI pipeline. Forcing a specific UI in the runtime would foreclose all of those.

## Decision

DeepRak v0.1 ships **no UI**. No web dashboard. No TUI. No graphical workflow editor.

Outputs are Python objects (returned from API calls), structured logs, and rendered markdown when explicitly requested. Examples in `examples/` are Python scripts that print results to stdout.

A CLI may be added in v0.2 **only if** there is a clear reusable command surface (e.g., `deeprak run-workflow workflows/x.yaml`). Even then, the CLI is a thin wrapper over the Python API, not a parallel implementation.

A web UI is explicitly **out of scope** for the foreseeable future. Users who need a UI can build one on top of DeepRak; the maintainer will not build it.

## Consequences

**Positive:**

- The runtime can evolve at the speed of a small library, not at the speed of a UI's release cycle.
- All public API surface area is testable from `pytest`. No browser, no headless rendering.
- Deployment surface is "import deeprak" — no separate frontend build, no static asset hosting, no CORS, no auth-on-the-frontend dance.
- Users in environments where UIs are inappropriate (CI, MCP servers, batch pipelines) get full functionality.

**Negative:**

- Less immediately demoable. A README screenshot of `>>> deeprak.delegate.route(...)` is less viral than a screenshot of a workflow editor.
- Newcomer ramp-up requires comfort with Python. Not all interested users are Python-fluent.
- Some patterns (workflow visualization, run-history exploration) genuinely benefit from a UI. Users will have to roll their own or wait.

**Neutral:**

- Forces example-driven documentation. Every concept is shown via a runnable Python file. This is harder upfront and clearer in the long run.

## Alternatives Considered

1. **Streamlit-based exploratory UI** — rejected. Conflates "demo of what DeepRak can do" with "DeepRak's interface." First-time users would expect the Streamlit app to be the product.

2. **Optional CLI in v0.1** — rejected for v0.1 only. CLI design takes meaningful time and the runtime API needs to stabilize first. Lands in v0.2 if there's clear demand.

3. **Workflow YAML editor (web)** — rejected. A workflow YAML file in any text editor is sufficient and avoids a permanent UI maintenance burden.

## Validation

This ADR is partly a forcing function: by committing publicly that DeepRak ships no UI, the maintainer is defended from the gradual creep that killed the predecessor project. The ADR is the boundary marker.

## Revisit Trigger

Revisit this ADR when **all** of the following become simultaneously true:

- A clearly reusable command surface has emerged from real DeepRak usage (not speculative)
- At least 50 GitHub stars (signal of a user community whose feedback should shape the project)
- A clear maintainer commitment to sustain a CLI without slowing the runtime
