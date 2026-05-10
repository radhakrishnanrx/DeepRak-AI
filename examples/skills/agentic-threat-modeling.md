# Skill: Agentic Threat Modeling (STRIDE + PASTA)

> **Adaptive skill** — designed to be refined before each engagement (pre-flight gate) and updated after (post-engagement debrief). See *Adaptation Hooks* at the end.

## Purpose

Threat-model a system that uses LLMs, MCP servers, RAG pipelines, or autonomous task delegation. Standard STRIDE assumes static trust boundaries; agentic systems negotiate trust at runtime, so STRIDE alone underspecifies the surface. This skill extends STRIDE with agent-specific threat categories and layers PASTA's attacker-centric scoring on top.

## When to Use

- A new agentic feature enters detailed design (tool use, multi-step delegation, RAG-backed answers).
- An MCP server is being added or replaced.
- A new model gateway / new provider is introduced.
- After a public AI security incident in a comparable system, to refresh the model.

## Pre-Modeling Gates

1. Architecture diagram exists (C4 Level 2 minimum) showing trust boundaries.
2. Asset inventory complete: data, processes, identities, AI models, datasets, prompt assets.
3. Attacker personas confirmed: external, insider, supply-chain compromise, model-poisoning attacker.

## Phases

### Phase 1: Decomposition

List in-scope components, trust boundaries, entry points (REST/GraphQL/gRPC/MCP/UI/CLI), and crown-jewel assets. Extend the standard DFD with: model gateway, RAG store, agent tool registry, prompt template store, MCP servers (each is its own trust boundary).

### Phase 2: STRIDE per component

For every component and every cross-boundary flow, fill all six categories with **concrete threat statements** ("Attacker [action] [mechanism] -> [consequence]"). Reject cells that say only "Spoofing: possible" — that is not a threat statement.

### Phase 3: Agentic STRIDE extensions

For agent components, additionally enumerate:

- **Prompt injection (Tampering)** — direct, indirect via RAG, indirect via tool descriptions, indirect via tool outputs.
- **Tool impersonation (Spoofing)** — rogue MCP server, tool-name collision, tool-description tampering.
- **Memory poisoning (Tampering)** — adversarial entries written to shared agent memory.
- **Delegation abuse (Elevation of Privilege)** — over-broad scope on delegated subagent calls.
- **Output exfiltration (Information Disclosure)** — model output structured to leak data via attacker-readable channels.

### Phase 4: PASTA — risk and impact

For each top STRIDE finding, build attacker decision tree → estimate likelihood × impact → produce risk score with named owner and due date.

### Phase 5: Control mapping

Map each top threat to existing + missing controls using NIST 800-53, OWASP LLM Top 10 (LLM01-LLM10), and OWASP Top 10 for Agentic Applications 2026 (where applicable). Produce a residual-risk score after recommended controls.

## Anti-Patterns

1. Copying a STRIDE template without naming concrete threats.
2. Modeling only the "happy path" trust boundary (client -> server) and ignoring agent-internal boundaries (orchestrator -> tool).
3. Modeling only external attackers — supply chain compromise of a model or MCP server is statistically more common than direct external attack on agentic systems in 2026.
4. Treating the threat model as one-time. Adaptive skills refresh after every meaningful architectural change.

## References

- Microsoft STRIDE
- *Risk Centric Threat Modeling* (PASTA), UcedaVélez & Morana, 2015
- OWASP LLM Top 10 — https://genai.owasp.org/llm-top-10/
- OWASP Top 10 for Agentic Applications 2026 — https://genai.owasp.org/llmrisk/agentic-applications/
- MITRE ATLAS — adversarial tactics for AI systems

## Adaptation Hooks

- **Pre-engagement**: load this file, refresh attacker-persona list against current threat intel (pull last 7-30 days of relevant CVEs / advisories), validate that the architecture diagram is still current.
- **Post-engagement**: record which threats actually surfaced during pentest / incident review, update STRIDE-extension list with any new threat category observed, re-score residual risk, append a dated entry to `_debrief.md`.
