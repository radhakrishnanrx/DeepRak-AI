# DeepRak

> **A small, smart Python library that decides which AI model should answer each question — and shows you why.**

Most AI apps send every prompt to the most expensive model and hope for the best. DeepRak looks at what you're asking, picks a small/standard/premium model that fits, retries on failure, and tells you exactly which model handled the reply, how long it took, and how many tokens it cost.

You bring your own model — OpenAI, Anthropic, Azure OpenAI, or even a local Ollama install. DeepRak is the smart traffic controller in the middle.

---

## What you'll have in 5 minutes

A browser chat UI that:

- Sends your message to the right-sized AI model automatically
- Shows on the right side which model was picked, why, and how long it took
- Lets you override the model tier (small / standard / premium) with one click
- Falls back to a backup model if the first one is down

If that sounds useful, keep reading. The setup is genuinely 5 minutes for someone who has Python installed.

---

## Works on macOS, Linux, and Windows

DeepRak is a pure-Python library — anything that runs Python 3.11+ runs DeepRak. The setup steps below show the macOS/Linux command first; the **Windows (PowerShell)** equivalent is shown right after wherever it differs.

## Before you start — what you need

| Requirement | macOS | Linux | Windows |
|---|---|---|---|
| Python 3.11 or newer | `python3 --version` (install from [python.org](https://www.python.org/downloads/) or `brew install python@3.13`) | `python3 --version` (e.g., `apt install python3.12 python3.12-venv`) | `python --version` (install from [python.org](https://www.python.org/downloads/), check "Add to PATH") |
| Git | `git --version` (`brew install git` or Xcode CLT) | `apt install git` / `dnf install git` | [git-scm.com](https://git-scm.com/) installer |
| Terminal | Terminal.app or iTerm2 | Any | PowerShell 7+ or Windows Terminal (recommended over CMD) |

**Plus one AI access method** (pick whichever you have):

- **OpenAI API key** — simplest, ~$5 of credit goes a long way — get one at [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- **Anthropic API key + a [LiteLLM proxy](https://docs.litellm.ai/docs/simple_proxy)** — works the same as OpenAI once the proxy is up
- **[Ollama](https://ollama.ai/)** installed locally — free, no cloud, runs on your machine (works on all three OSes)

No Docker, no cloud account, no server.

---

## Step-by-step: get DeepRak running

### Step 1 — Clone the repo to your computer

Open a terminal and run:

```bash
git clone https://github.com/radhakrishnanrx/DeepRak-AI.git
cd DeepRak-AI
```

You're now inside the project folder.

### Step 2 — Create an isolated Python environment and install

This keeps DeepRak's dependencies separate from anything else on your machine.

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[chatbot]"
```

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[chatbot]"
```

> If PowerShell blocks the activation script with "running scripts is disabled", run once: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`.

**Windows (CMD)**: use `.venv\Scripts\activate.bat` instead of the PowerShell line.

After the install, you'll see "Successfully installed ..." lines. When the prompt comes back, you're done.

### Step 3 — Tell DeepRak which AI model to use

Pick **one** of the three options. Each block shows macOS/Linux (`export`) and Windows PowerShell (`$env:`) syntax.

**Option A — OpenAI (easiest, costs a few cents per session)**

Get a key at [platform.openai.com/api-keys](https://platform.openai.com/api-keys). Add ~$5 of credit; it lasts a long time for testing.

```bash
# macOS / Linux
export DEEPRAK_GATEWAY_URL="https://api.openai.com"
export DEEPRAK_API_KEY="sk-...your-openai-key-here..."
export DEEPRAK_MODEL_SMALL="gpt-4o-mini"
export DEEPRAK_MODEL_STANDARD="gpt-4o"
export DEEPRAK_MODEL_PREMIUM="gpt-4o"
```

```powershell
# Windows PowerShell
$env:DEEPRAK_GATEWAY_URL="https://api.openai.com"
$env:DEEPRAK_API_KEY="sk-...your-openai-key-here..."
$env:DEEPRAK_MODEL_SMALL="gpt-4o-mini"
$env:DEEPRAK_MODEL_STANDARD="gpt-4o"
$env:DEEPRAK_MODEL_PREMIUM="gpt-4o"
```

**Option B — Local Ollama (free, no cloud, runs on your laptop)**

First install [Ollama](https://ollama.ai/) (works on macOS / Linux / Windows) and run `ollama pull llama3` once, then:

```bash
# macOS / Linux
export DEEPRAK_GATEWAY_URL="http://localhost:11434/v1"
export DEEPRAK_API_KEY="ollama"
export DEEPRAK_MODEL_SMALL="phi3"
export DEEPRAK_MODEL_STANDARD="llama3"
export DEEPRAK_MODEL_PREMIUM="llama3:70b"
```

```powershell
# Windows PowerShell
$env:DEEPRAK_GATEWAY_URL="http://localhost:11434/v1"
$env:DEEPRAK_API_KEY="ollama"
$env:DEEPRAK_MODEL_SMALL="phi3"
$env:DEEPRAK_MODEL_STANDARD="llama3"
$env:DEEPRAK_MODEL_PREMIUM="llama3:70b"
```

(Pull `llama3:70b` only if you have a beefy machine; otherwise reuse `llama3` for the premium tier.)

**Option C — Anthropic Claude (requires a LiteLLM proxy in front)**

Run a [LiteLLM proxy](https://docs.litellm.ai/docs/simple_proxy) on port 4000 with your Anthropic key (works on all OSes via `pip install litellm[proxy]`), then:

```bash
# macOS / Linux
export DEEPRAK_GATEWAY_URL="http://localhost:4000"
export DEEPRAK_API_KEY="anything"
export DEEPRAK_MODEL_SMALL="claude-3-haiku-20240307"
export DEEPRAK_MODEL_STANDARD="claude-3-5-sonnet-20241022"
export DEEPRAK_MODEL_PREMIUM="claude-3-5-sonnet-20241022"
```

```powershell
# Windows PowerShell
$env:DEEPRAK_GATEWAY_URL="http://localhost:4000"
$env:DEEPRAK_API_KEY="anything"
$env:DEEPRAK_MODEL_SMALL="claude-3-haiku-20240307"
$env:DEEPRAK_MODEL_STANDARD="claude-3-5-sonnet-20241022"
$env:DEEPRAK_MODEL_PREMIUM="claude-3-5-sonnet-20241022"
```

> **Heads up**: environment variables only live for the current terminal session. If you open a new terminal, re-run the export/`$env:` lines (or save them in your shell profile / a `.env.local` file).

### Step 4 — Start the chatbot

Same command on every OS:

```bash
python examples/chatbot/server.py
```

You'll see a line like `Uvicorn running on http://127.0.0.1:8000`. Leave the terminal running. Stop it any time with **Ctrl+C**.

### Step 5 — Open it in your browser

Visit **http://127.0.0.1:8000**.

> **macOS shortcut**: `open http://127.0.0.1:8000`
> **Linux shortcut**: `xdg-open http://127.0.0.1:8000`
> **Windows shortcut**: `start http://127.0.0.1:8000`

You'll see a dark-themed chat page with two columns. Type a message and hit Send.

---

## What to look for once it's running

Try these three messages and watch the right-hand "Orchestration Timeline":

1. **`Extract the dates from: "Meeting on March 5, deadline April 12, demo May 1"`**
   → Classifies as *parsing* → routes to the **gray (SMALL)** tier. Fast and cheap.

2. **`Summarize the plot of Hamlet in two sentences.`**
   → Classifies as *summarization* → routes to the **blue (STANDARD)** tier.

3. **`Design an architecture for a global e-commerce checkout that survives a regional outage.`**
   → Classifies as *synthesis* → routes to the **purple (PREMIUM)** tier.

The badges under each AI reply show: tier · model name · latency · token count. If a fallback fired (primary model failed and a backup answered), you'll see an extra "attempts" badge.

That's the whole product in a nutshell — *the right model for the question, and you can see why*.

---

## Use it as a library (for developers)

If you want to call DeepRak from your own Python code instead of through the chatbot:

```python
from deeprak.delegate import (
    DelegateRequest, LiteLLMAdapter, ModelRouter, ModelTier, TierConfig,
)

adapter = LiteLLMAdapter(
    base_url="http://localhost:4000",
    api_key="your-key",
)

router = ModelRouter(
    tier_configs={
        ModelTier.SMALL:    TierConfig(tier=ModelTier.SMALL,    models=["gpt-4o-mini"]),
        ModelTier.STANDARD: TierConfig(tier=ModelTier.STANDARD, models=["gpt-4o"]),
        ModelTier.PREMIUM:  TierConfig(tier=ModelTier.PREMIUM,  models=["claude-3-5-sonnet-20241022"]),
    },
    adapter=adapter,
)

response = router.route(DelegateRequest(prompt="Summarize Q3 earnings."))
print(response.content)
print(f"used: model={response.model} tier={response.tier} latency={response.latency_ms}ms")
```

Five fields, three lines of config, you have intelligent model routing.

---

## What's inside the project

```
deeprak/                       The Python library
├── delegate/                  Pick the right model tier (this is the core feature)
└── rag/                       Search your local Markdown docs without a vector DB

examples/
├── chatbot/                   The browser chat UI you just ran
└── skills/                    Reusable Markdown playbooks for common AI workflows
    ├── rag-corpus-audit.md           Audit a docs corpus before plugging it into a RAG agent
    ├── agentic-threat-modeling.md    Threat-model an agent (STRIDE + PASTA, agentic-extended)
    └── ai-supply-chain-sbom-aibom.md Build SBOM/AIBOM for AI components (governance)

docs/design-decisions/         The "why" behind each design choice
├── ADR-001-no-vector-db.md
├── ADR-002-no-ui.md
├── ADR-003-litellm-as-gateway.md
├── ADR-004-grep-over-embeddings-at-small-scale.md
└── ADR-005-chat-ui-as-example-not-core.md
```

---

## Adaptive skill lifecycle

Skills aren't static documents. Each one in `examples/skills/` has a *Pre-engagement* and *Post-engagement* hooks section — meaning the skill is loaded fresh at the start of each engagement (against current threat intel, current corpus state, current dependency graph) and updated at the end (with what was actually observed). The runtime gets sharper with use instead of going stale. Plumbing for this lifecycle ships in v0.2 (`deeprak.policy` + `deeprak.memory`); the *patterns* are documented in v0.1 so you can wire them today.

---

## Common issues

| Problem | Fix |
|---|---|
| `pip install -e ".[chatbot]"` says "no matching distribution" | Make sure your `python3 --version` is 3.11 or newer. |
| Port 8000 already in use | Run with `DEEPRAK_PORT=8123 python examples/chatbot/server.py` and visit `http://127.0.0.1:8123`. |
| Browser shows "OpenAI API key invalid" or similar | macOS/Linux: `echo $DEEPRAK_API_KEY`. Windows PowerShell: `echo $env:DEEPRAK_API_KEY`. Environment variables don't survive a new terminal tab — re-set them. |
| `python: command not found` (macOS/Linux) | Use `python3` instead of `python`. |
| `python` opens 2.7 instead of 3.x (some Linux distros) | Use `python3` and `python3 -m venv .venv`. |
| PowerShell: "running scripts is disabled on this system" | Run once: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`. |
| Activated venv but `pip install` says "error: externally-managed-environment" | Confirm the venv is active — your prompt should start with `(.venv)`. If not, re-run the activate command for your OS. |
| Ollama models give weird short replies | Some small Ollama models don't follow instructions well. Try `llama3` instead of `phi3` for STANDARD tier. |
| Chatbot starts but the right panel never updates | Check the terminal where the server is running for errors. The most common cause is the gateway URL being wrong. |

---

## Learn more

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — the design principles, module map, and the adaptive-skill lifecycle in detail.
- **[docs/design-decisions/](docs/design-decisions/)** — five ADRs documenting why DeepRak ships *without* a vector DB, *without* a built-in UI, etc. The "no's" matter as much as the "yes's".
- **[SECURITY.md](SECURITY.md)** — security posture, OWASP LLM Top 10 alignment, OWASP APTS notes, vulnerability reporting.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — how to contribute. Tests required. Type checks required.

---

## License

[MIT](LICENSE) — use it, fork it, ship it. Attribution appreciated, not required.
