# DeepRak — Orchestration-Visible Chat

A reference chatbot that makes the **routing layer visible** instead of hiding it. Every response shows which model handled the message, which tier was selected, classifier confidence, latency, token counts, and whether a fallback fired. The right-hand panel streams each orchestration step in real time as DeepRak processes the request.

This is the differentiation from generic chatbot examples: you see the *why* behind every model choice, not just the answer.

---

## Quick start

```bash
cd DeepRak-AI

# Install the package with chatbot extras
pip install -e ".[chatbot]"

# Point DeepRak at your model gateway
export DEEPRAK_GATEWAY_URL="http://localhost:4000"   # LiteLLM proxy or OpenAI-compatible base
export DEEPRAK_API_KEY="sk-..."

# Configure one model ID (or comma-separated list) per tier
export DEEPRAK_MODEL_SMALL="gpt-4o-mini"
export DEEPRAK_MODEL_STANDARD="gpt-4o"
export DEEPRAK_MODEL_PREMIUM="claude-3-5-sonnet-20241022"

# Start the server
python examples/chatbot/server.py
```

Open **http://127.0.0.1:8000** in your browser.

---

## What you will see

| UI area | What it shows |
|---|---|
| Left panel | Conversation history. Each AI response carries badges: tier, model ID, latency, total tokens, and an attempt-count badge if a fallback fired. |
| Right panel | Live orchestration timeline. Events stream in as DeepRak classifies the prompt, selects a tier, calls the model, and (if needed) falls back. |

Tier badge colours: **SMALL** gray / **STANDARD** blue / **PREMIUM** purple.

---

## Provider configuration examples

DeepRak is provider-agnostic — anything that exposes an OpenAI-compatible `/v1/chat/completions` endpoint works. Below are the four most common patterns.

### OpenAI direct

```bash
export DEEPRAK_GATEWAY_URL="https://api.openai.com"
export DEEPRAK_API_KEY="sk-..."
export DEEPRAK_MODEL_SMALL="gpt-4o-mini"
export DEEPRAK_MODEL_STANDARD="gpt-4o"
export DEEPRAK_MODEL_PREMIUM="gpt-4o"
```

### Anthropic Claude via LiteLLM proxy

```bash
# Run a LiteLLM proxy first: litellm --config litellm_config.yaml --port 4000
export DEEPRAK_GATEWAY_URL="http://localhost:4000"
export DEEPRAK_API_KEY="anything"        # the LiteLLM master key
export DEEPRAK_MODEL_SMALL="claude-3-haiku-20240307"
export DEEPRAK_MODEL_STANDARD="claude-3-5-sonnet-20241022"
export DEEPRAK_MODEL_PREMIUM="claude-3-5-sonnet-20241022"
```

### Azure OpenAI Enterprise

```bash
export DEEPRAK_GATEWAY_URL="https://<your-resource>.openai.azure.com/openai"
export DEEPRAK_API_KEY="<azure-api-key>"
export DEEPRAK_MODEL_SMALL="gpt-4o-mini"
export DEEPRAK_MODEL_STANDARD="gpt-4o"
export DEEPRAK_MODEL_PREMIUM="gpt-4o"
```

### Google Gemini direct (no proxy needed)

Gemini exposes an OpenAI-compatible endpoint at a non-default path, so set
`DEEPRAK_GATEWAY_PATH` accordingly. Get a key at
[aistudio.google.com/apikey](https://aistudio.google.com/apikey).

```bash
export DEEPRAK_GATEWAY_URL="https://generativelanguage.googleapis.com"
export DEEPRAK_GATEWAY_PATH="/v1beta/openai/chat/completions"
export DEEPRAK_API_KEY="<gemini-api-key>"
export DEEPRAK_MODEL_SMALL="gemini-2.5-flash-lite"
export DEEPRAK_MODEL_STANDARD="gemini-2.5-flash"
export DEEPRAK_MODEL_PREMIUM="gemini-2.5-pro"
```

### Ollama (local, no API key required)

```bash
# ollama serve  (default port 11434)
export DEEPRAK_GATEWAY_URL="http://localhost:11434/v1"
export DEEPRAK_API_KEY="ollama"          # any non-empty string is accepted
export DEEPRAK_MODEL_SMALL="phi3"
export DEEPRAK_MODEL_STANDARD="llama3"
export DEEPRAK_MODEL_PREMIUM="llama3:70b"
```

---

## Fallback behaviour

Each tier accepts a comma-separated list of model IDs:

```bash
export DEEPRAK_MODEL_PREMIUM="claude-3-5-sonnet-20241022,gpt-4o,gpt-4o-mini"
```

DeepRak tries models left-to-right. On a retryable failure (timeout, connection error, 5xx) it emits a `fallback_used` event and moves to the next model. The UI displays an attempt-count badge when more than one attempt was needed.

---

## Customisation

This example is **fork-and-adapt material**, not a supported core feature. Copy the two files (`server.py`, `static/index.html`) into your own project and modify freely. The routing logic in `server.py` is intentionally written inline (rather than calling `ModelRouter.route()`) so you can intercept each step and emit SSE events — see the `_chat_stream` async generator.

For the architectural rationale, see **ADR-005** in `docs/design-decisions/ADR-005-chat-ui-as-example-not-core.md`.

---

## Architecture

```
Browser
  |  POST /chat (JSON body)
  |  <- text/event-stream (SSE)
  v
FastAPI (server.py)
  |
  |-- TaskClassifier.classify_with_confidence(prompt)
  |-- TaskType.recommended_tier(task_type)  (or user override)
  '-- LiteLLMAdapter.acomplete(model, messages, max_tokens, temperature)
       |
       '-- LiteLLM proxy / OpenAI-compatible gateway
            '-- upstream model provider
```

- **Backend**: FastAPI + `StreamingResponse` with `text/event-stream`. No WebSockets, no message broker — a single HTTP response carries all events.
- **Frontend**: one self-contained HTML file. Vanilla JS reads the SSE stream via `fetch()` + `Response.body.getReader()` (required because `EventSource` does not support POST).
- **No build tooling**: no npm, no webpack, no TypeScript step. Open the HTML file and it works.

---

## Environment variable reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `DEEPRAK_GATEWAY_URL` | yes | — | OpenAI-compatible base URL |
| `DEEPRAK_GATEWAY_PATH` | no | `/v1/chat/completions` | Override for providers that expose OpenAI-compat at a non-default path (e.g. Gemini direct) |
| `DEEPRAK_API_KEY` | yes | — | Bearer token for the gateway |
| `DEEPRAK_MODEL_SMALL` | yes | — | Comma-separated model IDs for SMALL tier |
| `DEEPRAK_MODEL_STANDARD` | yes | — | Comma-separated model IDs for STANDARD tier |
| `DEEPRAK_MODEL_PREMIUM` | yes | — | Comma-separated model IDs for PREMIUM tier |
| `DEEPRAK_HOST` | no | `127.0.0.1` | Bind address |
| `DEEPRAK_PORT` | no | `8000` | Bind port |
