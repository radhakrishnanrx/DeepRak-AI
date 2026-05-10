# Contributing to DeepRak

DeepRak is a personal-project-turned-public-runtime. Contributions welcome — but no SLA on reviews. I (the maintainer) batch reviews weekly.

## Ground rules

1. **Open an issue before a PR for non-trivial changes.** A 30-line fix can land directly. A new module, a public-API change, or a new dependency: discuss first.
2. **Tests are mandatory.** New code without tests will not merge. Coverage threshold: 70% (enforced in CI).
3. **Type-checked.** `mypy --strict` must pass. Public APIs are typed; private internals are typed when reasonable.
4. **Lint clean.** `ruff check .` and `ruff format --check .` must pass. The pre-commit config enforces this locally.
5. **No new dependencies without justification.** If your change adds a runtime dep, the issue must explain why. The bar is high — DeepRak is intentionally lean.

## Local setup

```bash
git clone git@github.com:radhakrishnanrx/DeepRak-AI.git
cd DeepRak-AI
uv sync --all-extras --dev    # install everything including test/lint tooling
uv run pre-commit install      # local hooks
uv run pytest                  # confirm tests pass on your machine before changing anything
```

## Workflow

1. Fork / branch off `main`.
2. Make the change. Keep commits focused.
3. Run `uv run ruff check . && uv run ruff format . && uv run mypy deeprak && uv run pytest` locally.
4. Push and open a PR. Reference the issue if one exists.
5. CI runs lint, type check, and tests across Python 3.11 / 3.12 / 3.13. All three must pass.

## Scope

DeepRak is an orchestration runtime. It is NOT:

- A web framework
- An LLM provider
- A vector database
- An MCP server
- A workflow GUI

If a contribution moves DeepRak toward any of those, expect pushback. The architectural ADRs in `docs/design-decisions/` document where the lines are.

## Code of conduct

See `CODE_OF_CONDUCT.md`. Standard contributor covenant. Be kind, be specific, be patient.

## Licensing

By contributing, you agree your contributions are licensed under the MIT License (same as the project).
