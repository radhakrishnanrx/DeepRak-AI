# Skill: AI Supply Chain — SBOM, AIBOM, SLSA

> **Adaptive skill** — designed to be refined before each engagement (pre-flight gate) and updated after (post-engagement debrief). See *Adaptation Hooks* at the end.

## Purpose

Inventory the AI components of a system (models, datasets, prompts, agent tools, MCP servers) for governance, vendor review, regulatory disclosure, and incident response. SBOM covers software dependencies; AIBOM extends it to AI artifacts. SLSA captures the build provenance both flow through.

## When to Use

- A new dependency lands in `requirements.txt`, `package.json`, or any container image.
- A new LLM, embedding model, fine-tuned model, or RAG pipeline is integrated.
- A new MCP server is approved for use.
- A regulator or enterprise customer asks for an SBOM/AIBOM.
- A CVE drops on a component you may be using — and you need to know in 60 seconds whether you are exposed.

## Pre-Audit Gates

1. Source-of-truth manifests located (Python `pyproject.toml`, Node `package.json`, container `Dockerfile`).
2. Output format chosen — CycloneDX 1.6 JSON as the default; SPDX 2.3 only on explicit external requirement.
3. Signing-key strategy confirmed — Sigstore keyless via OIDC is recommended; long-lived keys require HSM/secret-manager custody.
4. Retention policy agreed — typically 3+ years for compliance deliverables.

## Phases

### Phase 1: SBOM generation

Per ecosystem:

- Python — `cyclonedx-py environment` or `syft . -o cyclonedx-json`
- Node.js — `cdxgen . -t nodejs` or `syft . -o cyclonedx-json`
- Container image — `syft <image>` or `trivy image <image> --format cyclonedx`

Output to `evidence/sbom/<project>/<YYYY-MM-DD>/sbom.cdx.json`.

### Phase 2: SBOM quality audit

Validate every component has: `name`, exact `version`, `supplier`, `purl` (PackageURL), `licenses` (SPDX expression or `NOASSERTION`), SHA-256 `hashes`, and full transitive `dependencies` graph. Flag any SBOM missing fields as low-fidelity.

### Phase 3: AIBOM generation

For services using LLMs / embeddings / agents / RAG, produce a CycloneDX 1.6 ML-BOM extension covering:

- **Model components** — name, version, provider, weight hash, training-data classification, fine-tune lineage, license, model card URL.
- **Dataset provenance** — source URL, snapshot date, license, redaction status, classification.
- **Agent toolchain** — MCP server name + version + connector identity (NOT the secret), tool descriptions as registered, per-tool permissions scope.
- **Prompt assets** — system prompt ID + hash, prompt template versions, mitigations applied (input validation, output filtering, guardrails).

Use the OWASP GenAI Project AIBOM Generator (March 2026) as the recommended tool.

### Phase 4: SLSA assessment

Score the build pipeline against SLSA L1 / L2 / L3 / L4. Target L2 for first-party artifacts. Path to L3: ephemeral runners, signed commits, branch protection with required reviews, non-falsifiable provenance.

### Phase 5: Signing + attestation

`cosign sign --keyless <image>` for image signing. `cosign attest --predicate sbom.cdx.json --type cyclonedx <image>` for SBOM attestation. Enforce verification at admission via Kyverno or OPA Gatekeeper.

### Phase 6: Vulnerability triage

`grype sbom:./sbom.cdx.json` or `osv-scanner --sbom sbom.cdx.json`. For AI components, additionally check Hugging Face Vulnerable Models list and provider-specific advisories. Issue VEX statements (`vexctl create`) when a CVE in your SBOM is not exploitable in your deployment context.

## Anti-Patterns

1. SBOM generated only at release time. Ingest on every build.
2. Flat dependency list. Transitive deps are where most CVEs live.
3. SBOM without a signature or attestation — no integrity guarantee.
4. AIBOM that names only the model. A model name without version, provenance hash, dataset lineage, and license is marketing, not a bill of materials.
5. VEX statements without a re-evaluation date. Context changes; deny-statements rot.
6. Treating the SBOM as a compliance checkbox. The runbook should answer *"which of our services uses log4j 2.14?"* in under 60 seconds.

## References

- CycloneDX 1.6 — https://cyclonedx.org/specification/overview/
- SPDX 2.3 — https://spdx.github.io/spdx-spec/v2.3/
- SLSA — https://slsa.dev/
- Sigstore — https://sigstore.dev/
- OWASP GenAI Project AIBOM Generator (March 2026)
- OpenVEX — https://openvex.dev/
- NIST SSDF SP 800-218

## Adaptation Hooks

- **Pre-engagement**: load this file, pull the latest CVE feed for components in the existing SBOM (last 24-48 hrs), refresh AIBOM if any model/dataset/MCP version changed since the last debrief.
- **Post-engagement**: record SBOM/AIBOM diff (what was added/removed/upgraded), capture any new false-positive grype/trivy patterns to add to the VEX baseline, append a dated entry to `_debrief.md`, update this skill's tooling list if a better tool emerged.
