# Security Policy

## Reporting a vulnerability

If you find a security issue in DeepRak, please **do not** open a public GitHub issue. Instead, open a [private security advisory](https://github.com/radhakrishnanrx/DeepRak-AI/security/advisories/new) on this repository.

A response is sent within **7 days** of receipt. The maintainer is a solo operator; please be patient with non-urgent reports.

## Scope

This policy covers:

- The `deeprak` Python package (all subpackages)
- The reference chatbot in `examples/chatbot/`
- The CI workflows in `.github/workflows/`

Out of scope:

- Vulnerabilities in upstream dependencies (report those to the dependency's maintainer; DeepRak will track when we update)
- Vulnerabilities in your own model gateway, your own LiteLLM proxy, or your own provider account credentials
- Misconfiguration of `examples/chatbot/` when deployed beyond `localhost` (the reference chatbot is not production-hardened by default)

## Security posture

DeepRak is a **library**. It does not, by default:

- Store credentials anywhere on disk
- Accept inbound network traffic
- Persist user data outside paths the caller explicitly configures
- Make outbound calls to anything other than the gateway URL the caller provides

The reference chatbot (`examples/chatbot/`) is the only component in this repo that opens a network listener. It is bound to `127.0.0.1` by default and ships with no authentication. Users running it on a public network must add their own auth — DeepRak does not make that decision for you.

## OWASP GenAI Project alignment

DeepRak is designed to support patterns from the OWASP GenAI Project's 2026 portfolio. The runtime ships primitives; the user composes them with their own controls.

### OWASP LLM Top 10 (2025) — coverage map

| Risk | DeepRak primitive available |
|---|---|
| LLM01 — Prompt Injection | Output structure (`DelegateResponse`) is typed; users can validate before downstream use. Sanitization remains the user's responsibility. |
| LLM02 — Insecure Output Handling | Typed responses make output schemas explicit; users still must escape/validate at egress. |
| LLM03 — Training Data Poisoning | Out of scope (DeepRak does not train models). The AIBOM skill template covers dataset provenance. |
| LLM04 — Model DoS | Tier-based budget caps + retry limits + per-request timeouts in `LiteLLMAdapter`. |
| LLM05 — Supply Chain Vulnerabilities | The AIBOM skill template (`examples/skills/ai-supply-chain-sbom-aibom.md`) covers SBOM/AIBOM/SLSA. |
| LLM06 — Sensitive Information Disclosure | Frontmatter-aware `RAGFilter` for scope-bounded retrieval; users define classification labels. |
| LLM07 — Insecure Plugin Design | Out of scope at runtime; covered by threat-modeling skill template. |
| LLM08 — Excessive Agency | `deeprak.policy` decorators (planned v0.2) — `@requires_operator_approval`, `@within_scope`, `@rate_limited`. |
| LLM09 — Overreliance | Multi-model fallback exposes model identity in every response; users can audit which model said what. |
| LLM10 — Model Theft | Out of scope (DeepRak does not host models). |

### OWASP Top 10 for Agentic Applications (2026) — alignment

The agentic-threat-modeling skill template (`examples/skills/agentic-threat-modeling.md`) explicitly extends STRIDE with categories that map to the Agentic Top 10:

- Prompt injection (direct + indirect via RAG / tool descriptions / tool outputs)
- Tool impersonation (rogue MCP server, tool-name collision)
- Memory poisoning
- Delegation abuse (over-broad subagent scope)
- Output exfiltration

Use this skill as the entry point when threat-modeling any agentic deployment built on DeepRak.

## Alignment with public AI security frameworks

If you are building an autonomous-agent system that needs to align with public AI-security frameworks — NIST AI RMF, MITRE ATLAS, ENISA AI Threat Landscape — DeepRak provides v0.2 primitives that map onto common control areas:

| Control area | DeepRak primitive |
|---|---|
| Scope enforcement | `RAGFilter` for scope-bounded retrieval; `deeprak.policy` decorators (planned v0.2) |
| Multi-source resilience | Multi-model fallback within each tier |
| Provenance | Every `DelegateResponse` records `model`, `tier`, `task_type`, `attempts`, token counts, `latency_ms` |
| Failure handling | Retry-with-exponential-backoff on transient errors, separated from non-retryable errors |
| Transparency | The reference chatbot streams every routing decision to the UI as it happens |

Framework compliance is a property of the *system you build with DeepRak*, not of DeepRak alone — the same way Kubernetes is a substrate for compliant workloads but does not itself certify compliance. Wire the primitives above into your application's audit log, approval channel, and dual-model QC pattern.

## Disclosure

After a fix lands, the maintainer publishes a security advisory describing the issue, the affected versions, and the fix. Reporters who wish to be credited will be — those who prefer to remain anonymous will be.
