# agent-client-template

A skills-driven, multi-provider LLM agent client you can use as a template.

Give it a task (optionally with files), and it will:

1. **Retrieve relevant skills** via vector search and inject them into the prompt.
2. **Read attached files** (txt / md / pdf / xlsx / docx / pptx) into context.
3. **Route across LLM providers** (OpenAI / Anthropic / Google / Ollama) with
   token-aware selection and automatic failover.
4. **Run an iterative `done` / `continue` loop** until the task is complete,
   compressing context memory when it grows too large and splitting prompts that
   exceed the largest model window.
5. **Persist each session** to `history/` as JSON.

---

## Table of contents

- [Architecture](#architecture)
- [Project structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
  - [1. Models & API endpoints](#1-models--api-endpoints)
  - [2. Embedding provider](#2-embedding-provider)
  - [3. Skills](#3-skills)
- [Usage](#usage)
- [How it works](#how-it-works)
- [Testing](#testing)
- [Notes & limitations](#notes--limitations)

---

## Architecture

Four modules, orchestrated by `AgentClient`:

| Module | Class | Responsibility |
| --- | --- | --- |
| `disesfgewuAgent/agent.py` | `AgentClient` | Orchestration: prompt building, token accounting, splitting, the iteration loop, context compression, history. |
| `disesfgewuAgent/llmRouter.py` | `llmRouter` | Multi-provider routing across the `openai` / `anthropic` / `google` / `ollama` protocols, with token-aware selection and failover. |
| `disesfgewuAgent/skillLoader.py` | `skillLoader` | Skill RAG: parse `skills/*.md`, embed descriptions, and run FAISS similarity search. |
| `disesfgewuAgent/inputFileManager.py` | `inputFileManager` | Extract plain text from txt / md / pdf / xlsx / docx / pptx. |

---

## Project structure

```
agent-client-template/
├── disesfgewuAgent/
│   ├── agent.py              # AgentClient orchestrator
│   ├── llmRouter.py          # multi-provider router
│   ├── skillLoader.py        # skill embedding + FAISS search
│   └── inputFileManager.py   # file -> text extraction
├── config/
│   ├── api.example.json      # template: copy to api.local.json
│   ├── api.local.json        # YOUR models + keys (gitignored)
│   ├── skills.example.json   # template: copy to skills.json
│   └── skills.json           # skill index + cached embeddings (gitignored)
├── skills/
│   ├── code-review.md        # a skill = markdown + YAML frontmatter
│   ├── debugging.md
│   └── testing.md
├── history/                  # per-session JSON logs (gitignored)
├── tests/                    # unit + live integration tests
├── example.py                # runnable end-to-end demo
├── pyproject.toml            # packaging metadata (pip install .)
├── .env.example              # template: copy to .env
└── requirements.txt
```

---

## Installation

As an installable package (exposes the `disesfgewuAgent` import):

```bash
pip install .
# or, for development:
pip install -e .
```

Or just install the runtime dependencies and run from a checkout:

```bash
pip install -r requirements.txt
```

Requires Python 3.9+. Configuration (models, keys, skills) is **never** bundled
into the package — you inject it at runtime (see below), so the same install
works from a checkout or from site-packages.

---

## Configuration

There are three things to configure: **models**, an **embedding provider**, and
your **skills**. The `config/*.local`/`*.json` and `.env` files are gitignored,
so your keys never get committed.

```bash
cp config/api.example.json   config/api.local.json
cp config/skills.example.json config/skills.json
cp .env.example              .env
```

### 1. Models & API endpoints

`config/api.local.json` is a JSON **array** of model entries. Each entry:

| Field | Meaning |
| --- | --- |
| `provider` | Free-form label for your own reference. |
| `protocol` | One of `openai`, `anthropic`, `google`, `ollama`. Determines the request/response shape. Defaults to `openai`. |
| `endpointUrl` | Full chat/messages endpoint URL (see per-protocol notes below). |
| `modelName` | Model identifier sent to the provider; also the lookup key in this client. |
| `maxInputToken` | Input window. Used for token-aware routing — prompts larger than this skip the model. |
| `maxOutputToken` | Max output tokens (sent as `max_tokens` / `num_predict` / `maxOutputTokens`). |
| `tier` | Optional capability tier (integer, higher = more capable; default `2`). Drives difficulty-based routing — see below. |
| `apiKey` | Provider key. Leave `""` for local Ollama. |

**Routing strategy.** `AgentClient`'s `routingStrategy` (default `"taskComplex"`)
decides the order in which models are tried; `connect()` then skips any whose
window can't hold the input and uses the first that succeeds:

- `"taskComplex"` (default) — **difficulty tiering**: easy tasks try the
  lowest-`tier` (cheapest) model first to save cost; hard tasks try the
  highest-`tier` (most capable) first. Difficulty is a free, composite
  heuristic scored over the *raw task only* (its token length, number of
  attached files, number of matched skills, and reasoning keywords in English
  and Chinese) — so injected skill text doesn't skew it. Ties broken by window
  size. No extra API call is made.
- `"maxTokens"` — always prefer the largest context window.
- `""` — use config order as-is (the list is the priority).

So with `deepseek-v4-flash` at `tier 1` and `deepseek-v4-pro` at `tier 3`, a
quick question routes to Flash while a large/complex one routes to Pro.

Per-protocol `endpointUrl` conventions:

- **openai** — `.../v1/chat/completions`
- **anthropic** — `.../v1/messages`
- **google** — base URL only (e.g. `https://generativelanguage.googleapis.com`);
  the client appends `/v1beta/models/<modelName>:generateContent`.
- **ollama** — `http://localhost:11434/api/chat`

Add as many models as you like. The router tries them in order and fails over to
the next when one errors or cannot fit the input. See
[`config/api.example.json`](config/api.example.json) for a full four-protocol example.

### 2. Embedding provider

Skill search needs an embedding model, configured in `.env`. It uses an
OpenAI-compatible embeddings API (the default points at NVIDIA NIM):

```ini
EMBEDDING_URL=https://integrate.api.nvidia.com/v1
EMBEDDING_API=your-embedding-key
EMBEDDING_MODEL=nvidia/nv-embed-v1
```

Any OpenAI-compatible embeddings endpoint works — just point `EMBEDDING_URL`,
`EMBEDDING_API`, and `EMBEDDING_MODEL` at it.

### 3. Skills

A **skill** is a Markdown file in `skills/` with YAML frontmatter. Its
`description` is what gets embedded and matched against incoming tasks; its body
is injected into the prompt when selected.

```markdown
---
name: code-review
description: Reviews code for bugs, security issues, and style violations. Use when reviewing pull requests or auditing code.
version: 1.0.0
tags: [development, review]
---

# Code Review Best Practices
...body that will be injected into the prompt when this skill matches...
```

To **add a new skill**:

1. Create `skills/my-skill.md` with frontmatter (include a good `description`).
2. Register it in `config/skills.json`:
   ```json
   {
     "my-skill": { "relativePath": "my-skill.md" }
   }
   ```
3. On the next run, its embedding is computed once and cached back into
   `config/skills.json` (so subsequent runs are fast).

The `skills.json` index is the source of truth for which skills exist; the
`embedding` field is filled in automatically.

---

## Usage

See [`example.py`](example.py) for a complete script. The essentials:

```python
import asyncio
from disesfgewuAgent import AgentClient

async def main():
    # All config is injected explicitly — nothing is read from the install dir.
    async with AgentClient(
        "config/skills.json",       # skill index
        "skills",                   # skills directory
        "config/api.local.json",    # model config: a path OR a list of dicts
        contextWindowSize=32000,
        historyDir="history",       # optional; omit to disable session logging
    ) as agent:
        # Simple task
        print(await agent.ask("What is 2 + 2? Reply with just the number."))

        # Reusable: per-conversation state resets on every ask()
        print(await agent.ask("List three code-review best practices."))

        # Task over local files
        print(await agent.ask(
            "Summarize this document.",
            inputFiles=["report.pdf"],
        ))

asyncio.run(main())
```

`AgentClient(skillConfigPath, skillFolderPath, apiConfig, contextWindowSize=32000, historyDir=None, routingStrategy="taskComplex")`

- `skillConfigPath` — path to `config/skills.json`.
- `skillFolderPath` — path to the `skills/` directory.
- `apiConfig` — your model config: a path to a JSON file **or** an in-memory
  `list` of model dicts (same shape as `config/api.example.json`).
- `contextWindowSize` — soft token threshold at which context memory is compressed.
- `historyDir` — directory for per-session JSON logs; `None` (default) disables
  disk writes, which is usually what you want when used as a library.
- `routingStrategy` — model-selection strategy: `"taskComplex"` (default,
  difficulty tiering), `"maxTokens"`, or `""` (config order). See
  [Configuration](#1-models--api-endpoints).

Passing config in-memory (no files needed):

```python
models = [{
    "provider": "openai", "protocol": "openai",
    "endpointUrl": "https://api.openai.com/v1/chat/completions",
    "modelName": "gpt-4o-mini", "maxInputToken": 128000,
    "maxOutputToken": 16384, "apiKey": "sk-...",
}]
agent = AgentClient("config/skills.json", "skills", models)
```

Key methods:

- `await agent.ask(inputStr, inputFiles=None) -> str` — run a task, return the answer.
- `await agent.aclose()` — close the underlying HTTP client (or use `async with`).

> **Lifecycle:** `ask()` does **not** close the router, so the same client can be
> reused across independent tasks. Manage the connection with `async with` or by
> calling `aclose()` when done.

---

## How it works

A single `ask()` runs this pipeline:

1. **Reset state** — clears per-conversation memory/history so the client is reusable.
2. **Gather inputs** — load the skill index, extract any attached files, and run
   vector search to pick the top matching skills (cosine similarity, default
   `min_score=0.3`, `top_k=3`).
3. **Iteration loop** (up to 10 by default):
   - Build the prompt from `[SKILLS] / [CONTEXT MEMORY] / [INFORMATIONS FROM LAST] /
     [FILES] / [TASK]`.
   - If context memory exceeds `contextWindowSize`, **compress** it (summarize,
     chunking the summary itself if needed; keep the original if it didn't shrink).
   - If the prompt exceeds the largest model window, **split** the task into
     overlapping chunks, process them in parallel, and merge.
   - Route to a model via `llmRouter.connect()` (token-aware, with failover).
   - Parse the response as JSON (tolerant of ```` ```json ```` fences and prose).
     `status: "done"` returns the answer; `status: "continue"` feeds progress
     into the next iteration.
4. **Persist** the session to `history/session_<timestamp>.json`.

The agent expects models to answer in this JSON envelope:

```json
{"status": "done", "answer": "final answer", "reasoning": "..."}
{"status": "continue", "answer": "current progress", "reasoning": "...", "next_action": "..."}
```

---

## Testing

Tests are split into **offline unit tests** (no network, always run) and **live
integration tests** (real API calls, skipped unless configured).

```bash
# Everything (live tests auto-skip if config/api.local.json or EMBEDDING_API is missing)
python -m unittest discover -s tests -v

# Offline unit tests only — fast, deterministic, no keys needed
python -m unittest \
  tests.test_agent.TestAgentLogic \
  tests.test_llmRouter.TestLLMRouterLogic \
  tests.test_llmRouter.TestLLMRouterTokenGuard \
  tests.test_skillLoader.TestSkillLoaderLogic \
  tests.test_inputFileManager -v

# Live end-to-end integration tests (needs a working api.local.json + EMBEDDING_API)
python -m unittest tests.test_integration -v
```

The live suites (`tests.test_integration`, and the `*Real` / `*AsyncAPI` classes)
are guarded by `@unittest.skipUnless(live_api_available(), ...)`, so a fresh
clone without configuration still gets a green run. They are **not mocked** — they
exercise the full pipeline against your configured endpoints and consume real API
quota, so they require the endpoints to be reachable and within rate limits.

---

## Notes & limitations

- **Provider compatibility:** `max_tokens` is sent on the OpenAI protocol; some
  gateways expect `max_completion_tokens` instead. Verify against your endpoint.
- **Text encoding:** non-UTF-8 `.txt` files fall back to latin-1 (never crashes,
  but CJK encodings such as Big5/GBK may render as mojibake). Use a charset
  detector if you expect those.
- **Secrets:** `config/api.local.json`, `config/skills.json`, `.env`, and
  `history/` are gitignored. Never commit real keys.
- **JSON contract:** models that don't return the `status`/`answer` envelope are
  treated as a completed answer (best-effort fallback).
