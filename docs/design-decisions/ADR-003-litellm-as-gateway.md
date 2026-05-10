# ADR-003 — LiteLLM as the Model Gateway

- **Status**: Accepted
- **Date**: 2026-05-10
- **Deciders**: radhakrishnanrx (maintainer)

## Context

DeepRak delegates to LLMs across multiple providers (Anthropic Claude, OpenAI GPT, Google Gemini, open-weights via Ollama or vLLM). Each provider has its own SDK, its own request/response wire format, its own streaming protocol, its own error semantics, and its own rate-limit and retry surface.

Building per-provider adapters inside DeepRak would replicate work that already exists in the wider ecosystem. It would also tightly couple DeepRak's release cycle to upstream SDK changes (e.g., the Anthropic SDK has changed parameters across multiple major versions in the last 18 months). Every per-provider adapter increases the surface area DeepRak must test, document, and maintain.

A model gateway sits between application code and provider APIs. It exposes a uniform request/response shape (typically OpenAI-compatible) and translates internally to provider-native formats. LiteLLM is the most mature open-source gateway in this category as of 2026: 100+ provider integrations, OpenAI-compatible wire format, streaming support, retries, fallbacks, cost tracking. It is widely deployed and actively maintained.

## Decision

DeepRak v0.1 standardizes on **LiteLLM's wire format** as the canonical gateway interface. The `deeprak.delegate.litellm_adapter` module speaks this format. Users supply their own LiteLLM endpoint (self-hosted proxy or managed) via configuration.

DeepRak does **not** ship a LiteLLM proxy. Users choose how to deploy it:

- Self-hosted LiteLLM proxy (`pip install litellm[proxy]`)
- Managed LiteLLM SaaS (BerriAI cloud)
- Direct OpenAI-compatible endpoint (any provider that exposes one — vLLM, Ollama, AWS Bedrock with bedrock-access-gateway, etc.)
- Custom adapter the user writes implementing the same protocol

The LiteLLM dependency is **not** a hard runtime dependency of DeepRak. DeepRak speaks HTTP to whatever endpoint is configured. Users who don't want LiteLLM specifically can point DeepRak at any OpenAI-compatible endpoint.

## Consequences

**Positive:**

- DeepRak inherits LiteLLM's 100+ provider integrations without writing or maintaining adapters.
- Provider SDK churn is absorbed by LiteLLM, not by DeepRak.
- Users who already operate a LiteLLM proxy get DeepRak working without infrastructure change.
- Test fixtures can mock the OpenAI-compatible wire format (well-documented, stable) instead of N provider-specific shapes.

**Negative:**

- Provider-specific features that don't fit OpenAI's wire format may be inaccessible (e.g., Anthropic's prompt caching mechanism, Google's grounding metadata). Users who need these features must either go around DeepRak's adapter or wait for LiteLLM to surface them.
- Adds latency and a hop relative to direct provider SDK calls. Typically negligible (under 10ms for a well-deployed proxy) but real.
- Requires users to deploy or have access to a LiteLLM-compatible endpoint. Not zero-config out of the box.

**Neutral:**

- Forces DeepRak to not have opinions about provider selection. The user (or their gateway config) decides which model handles which tier. This is consistent with the goal of being enterprise-neutral.

## Alternatives Considered

1. **Per-provider native SDKs (anthropic, openai, google-genai)** — rejected. Maintenance burden would dominate DeepRak's roadmap. Locks DeepRak to provider SDK release cycles.

2. **OpenAI Python SDK as the only client** — rejected. Doesn't natively support non-OpenAI providers. Would require LiteLLM-like translation layer anyway.

3. **A custom DeepRak gateway built from scratch** — rejected. Reinvents LiteLLM badly.

4. **Bring-your-own-client interface (user passes a callable)** — considered. Falls out as a bonus of the LiteLLM-format decision: the adapter is just a thin httpx wrapper over a URL, so users wanting to substitute their own callable can do so by implementing the same protocol. May land as documented pattern in v0.2.

## Validation

A reference daily workflow has been running through a LiteLLM proxy with multiple model IDs across providers for 6+ months. The OpenAI-compatible wire format has proven sufficient for all delegation patterns DeepRak v0.1 needs, and provider SDK churn has been absorbed by the gateway rather than by application code.

## Revisit Trigger

Revisit this ADR when **any** of the following becomes true:

- LiteLLM project becomes unmaintained (no commits for 6+ months) or makes a backward-incompatible change DeepRak users push back on
- A provider feature that DeepRak users actively need is not exposed through LiteLLM and is unlikely to be added
- A clearly superior gateway emerges (an industry standard, e.g., a CNCF-graduated project)
