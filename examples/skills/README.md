# Sample Skills

These are short, reusable **skill templates** — structured Markdown playbooks for common AI/security workflows. Each one is intentionally short (50-80 lines) so you can fork it, fill in your own specifics, and ship.

A "skill" in this context is a structured prompt-engineering pattern with explicit phases and gates. The DeepRak runtime (`deeprak.delegate`, `deeprak.rag`) executes the model calls; the skill defines what to ask, in what order, and what to verify.

## What's in this folder

| File | Use it when |
|---|---|
| [`rag-corpus-audit.md`](rag-corpus-audit.md) | You're auditing a Markdown corpus for retrieval quality before plugging it into a RAG-backed agent. |
| [`agentic-threat-modeling.md`](agentic-threat-modeling.md) | You're threat-modeling an agentic system that uses tools, RAG, or autonomous delegation. STRIDE alone is insufficient; this skill extends it. |
| [`ai-supply-chain-sbom-aibom.md`](ai-supply-chain-sbom-aibom.md) | You need to inventory the AI components (models, datasets, prompts, agent tools) of a system for governance, vendor review, or compliance. |

## How to adapt a skill

1. Copy the file into your own project's `skills/` folder.
2. Search-replace the placeholders (corpus paths, model IDs, project-specific scope).
3. Run it manually for a few cycles to validate it on your data.
4. Wire it into your own DeepRak workflow once stable.

These are deliberately not packaged as Python code. The friction of editing Markdown is the point — skills should be inspectable, version-controllable, and reviewable by people who don't want to read Python.

## Contributing new skills

Open an issue describing the gap. Skills that are generic enough to be useful across multiple projects (not tied to a specific employer, vendor, or stack) are welcome. Skills that depend on internal-only knowledge belong in your private repo, not here.
