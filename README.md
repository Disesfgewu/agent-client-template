# agent-client-template

A skills-driven, multi-provider LLM agent client you can use as a template.

Give it a task (optionally with files), and it will:

1. **Retrieve relevant skills** via vector search and inject them into the prompt.
2. **Read attached files** (pdf / xlsx / docx / pptx / jpg / png / zip / tar / tar.gz, plus any plain-text or
   source file) into context.
3. **Route across LLM providers** (OpenAI / Anthropic / Google / Ollama) with
   difficulty-tiered, token-aware selection and automatic failover.
4. **Run an iterative `done` / `continue` loop** until the task is complete,
   compressing context memory when it grows too large and splitting prompts that
   exceed the largest model window.
5. **Optionally execute Python it writes** (opt-in) to compute real results.
6. **Persist each session** to `history/` as JSON.

---

## Table of contents

- [Architecture](#architecture)
- [Project structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
  - [1. Models & API endpoints](#1-models--api-endpoints)
  - [2. Embedding provider](#2-embedding-provider)
  - [3. Skills](#3-skills)
- [Research-grounded skill design](#research-grounded-skill-design)
- [Usage](#usage)
- [How it works](#how-it-works)
- [Testing](#testing)
- [Notes & limitations](#notes--limitations)
- [References](#references)

---

## Architecture

Four modules, orchestrated by `AgentClient`:

| Module | Class | Responsibility |
| --- | --- | --- |
| `disesfgewuAgent/agent.py` | `AgentClient` | Orchestration: prompt building, token accounting, splitting, the iteration loop, context compression, history. |
| `disesfgewuAgent/llmRouter.py` | `llmRouter` | Multi-provider routing across the `openai` / `anthropic` / `google` / `ollama` protocols, with token-aware selection and failover. |
| `disesfgewuAgent/skillLoader.py` | `skillLoader` | Skill RAG: parse `skills/*.md`, embed descriptions, and run FAISS similarity search. |
| `disesfgewuAgent/inputFileManager.py` | `inputFileManager` | Extract text/metadata from txt / md / pdf / xlsx / docx / pptx / jpg / png / zip / tar / tar.gz. |

---

## Project structure

```
agent-client-template/
├── disesfgewuAgent/
│   ├── agent.py              # AgentClient orchestrator
│   ├── llmRouter.py          # multi-provider router
│   ├── skillLoader.py        # skill embedding + FAISS search
│   └── inputFileManager.py   # file -> text/metadata/archive extraction
├── config/
│   ├── api.example.json      # template: copy to api.local.json
│   ├── api.local.json        # YOUR models + keys (gitignored)
│   ├── skills.example.json   # template: copy to skills.json
│   └── skills.json           # skill index + cached embeddings (gitignored)
├── skills/
│   ├── code-review.md        # a skill = markdown + YAML frontmatter
│   ├── code-editing.md       # lets the agent modify files (with code exec)
│   ├── shell-commands.md     # search/navigate a codebase via grep/find/...
│   ├── debugging.md
│   └── testing.md
├── history/                  # per-session JSON logs (gitignored)
├── tests/                    # unit + live integration tests
├── example.py                # runnable end-to-end demo (scripted)
├── demo.py                   # interactive agent TUI (rich): shows each step
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

Optional extras: `pip install ".[demo]"` (the `rich` CLI TUI) and
`pip install ".[web]"` (the `ddgs` search library used by the `web-research`
skill).

Or just install the runtime dependencies and run from a checkout:

```bash
pip install -r requirements.txt
```

Requires Python 3.9+. Configuration (models, keys, skills) is **never** bundled
into the package — you inject it at runtime (see below), so the same install
works from a checkout or from site-packages. The **default skills** *are* bundled
in the package under `disesfgewuAgent/default_skills/`. When you construct an
agent without skill paths, it uses that installed skills directory and creates only
a private local registry/cache at `./.agent/skills.json`.

---

## Configuration

There are three things to configure: **models**, an **embedding provider**, and
optionally your project-local **skills**. Bundled default skills are available without any project-local `skills/` directory. The `config/*.local`/`*.json`, `.agent/`, and `.env` files are gitignored,
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
  heuristic scored over the *raw task* — its token length, **size of attached
  files** (reviewing/redesigning a big file or project escalates), number of
  attached files, matched skills, and reasoning keywords (EN/CN) — so injected
  skill text doesn't skew it. Ties broken by window size. No extra API call.

For the multi-step action loop, the router requests **JSON output mode** from
providers that support it (OpenAI `response_format`, Google `responseMimeType`,
Ollama `format`), so even smaller models return valid, properly-escaped JSON and
the agentic protocol doesn't break on quotes/newlines inside generated code.
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

**Bundled default skills.** The package includes `disesfgewuAgent/default_skills/*.md`. If `AgentClient` is created without `skillConfigPath` and `skillFolderPath`, it calls `bootstrap_default_skills()`, keeps the bundled skill Markdown files in the installed package location, and creates a private local registry at `./.agent/skills.json`. That registry is where embeddings are cached, so runtime config does not need to be committed or exposed. `config/skills.example.json` remains a shareable template; `config/skills.json` and `.agent/` are local-only. To use your own project skills, pass both `skillConfigPath` and `skillFolderPath`.

```python
agent = AgentClient(apiConfig=models)  # uses package default skills; creates ./.agent/skills.json
```

**Code-editing skill.** The bundled `code-editing` skill turns the agent into a
Codex-style code editor: when a task asks to modify a file (and
`enableCodeExecution=True`), it reads the file, applies a minimal targeted patch,
writes it back to disk, and verifies — all via `execute` steps. Attached files
now carry their path in the `[FILES]` section so the agent knows where to write.

### Research-grounded skill design

The bundled skill set follows a lightweight `Metadata + Instructions + Resources` model. In this repository, the metadata that matters most for retrieval is the YAML `description`, because `skillLoader` embeds that field and uses FAISS similarity search before the Markdown body is injected.

The practical design target is **CP-grounding**: maximize useful task coverage and grounded answers per injected token. A good skill should be easy to retrieve, specific enough to avoid overlap, short enough to fit prompt budgets, explicit about evidence, and conservative about state-changing tools.

| Design concern | Local rule |
| --- | --- |
| Demand fit | Prioritize high-demand workflows such as web research, code generation/review, data analysis, document/file work, and debugging. |
| Retrieval fit | Put realistic trigger terms in `description`; body-only trigger wording is too late for selection. |
| Grounding fit | Require evidence collection, citations, local file inspection, calculation checks, or validation steps where the task depends on facts. |
| Token cost | Keep operational instructions concise; move long references, schemas, templates, or scripts into resources when needed. |
| Redundancy cost | Split skills only when they serve distinct intents; merge near-duplicates that compete for the same query. |
| Risk cost | Classify operations as L0-L3 and require approval/dry-run for writes, execution, external export, deployment, database mutation, or financial actions. |

The `skill-creator` skill is the default entry point for creating or revising skills in this repo: it defines frontmatter, body structure, resource boundaries, registry updates, and validation steps. The `skills-optimize` skill then encodes the CP-grounding audit model and exposes an API-shaped operation contract for future tooling: `audit`, `register`, `lint`, `retrieve_test`, `suggest_rewrite`, `apply_rewrite`, and `score_cp_grounding`.

Two security skills add a stricter control layer: `agent-skill-security-audit` classifies skills into the 6-category / 20-subcategory taxonomy and assigns L0-L3 risk under worst-case interpretation; `agent-action-safety-control` gates runtime actions with an action manifest, deny-by-default L3 rules, scoped confirmation, dry-run preference, rollback planning, and audit logging. This design is intentionally stricter than per-layer or lexical allowlists because OpenClaw security studies show cross-layer composition, malicious skill distribution, prompt injection, and command identity ambiguity can bypass local-only checks.

---

## Usage

For an interactive agent TUI (a `rich`-rendered terminal UI that shows the agent
reasoning, running code, and observing output step by step — not just a chat
bot), run:

```bash
python demo.py
```

It streams each step of the agent loop, executes Python the agent writes, keeps
conversation memory, and supports `/file <path>` (inline too), `/reset`, and
`/exit`. See [`example.py`](example.py) for a scripted end-to-end example. The
programmatic essentials:

```python
import asyncio
from disesfgewuAgent import AgentClient

async def main():
    # All config is injected explicitly — nothing is read from the install dir.
    async with AgentClient(
        "config/skills.json",       # skill index (omit to auto-bootstrap bundled default skills)
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

`AgentClient(skillConfigPath, skillFolderPath, apiConfig, contextWindowSize=32000, historyDir=None, routingStrategy="taskComplex", complexityScoreThreshold=3, maxTurnsInContext=6, enableCodeExecution=False, codeExecutionTimeout=30)`

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
- `complexityScoreThreshold` — score at/above which a task is treated as
  complex (default `3`). Raise it to keep more tasks on the cheaper models.
- `maxTurnsInContext` — how many past turns `chat()` feeds back as context.
- `mode` — role/profile label (default `"general"`); tags the result and frames
  the prompt. Useful as an agent's role in a crew.
- `enableCodeExecution` — allow the agent to run Python it writes (see below).
  **Off by default.**
- `enableShell` — allow the agent to run shell commands (grep/find/...). **Off by default.**
- `enableFileEdit` — allow the agent to apply `edit_file` patches (returns a
  diff in the result). **Off by default.**
- `codeExecutionTimeout` — per-run timeout (seconds) for executed code/commands.
- `onEvent(event)` — observe each step of the loop (planning / reasoning / execute
  / output) for a live UI.
- `onApprove(action) -> bool` — safety gate called before any execution; return
  falsy to block it.

Whatever the order, the router always **skips models whose context window is
too small for the input** and uses the first one that both ranks well and
fits — so a long task never gets sent to a model that can't hold it.

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

- `await agent.ask(inputStr=None, inputFiles=None, systemPrompt="", userPrompt=None) -> dict` — run one independent task. `ask("task")` remains supported; API integrations should prefer explicit `systemPrompt` and `userPrompt`.
- `await agent.chat(message=None, inputFiles=None, systemPrompt="", userPrompt=None) -> dict` — like `ask()` but remembers prior turns; `agent.resetConversation()` clears it.
- `await agent.aclose()` — close the underlying HTTP client (or use `async with`).

`systemPrompt` is trusted caller policy for the current run. `userPrompt` is untrusted user content and is scanned before prompt construction for prompt-injection indicators such as instruction override, system prompt extraction, secret exfiltration, unsafe execution, destructive actions, and data/instruction boundary confusion. If flagged, the prompt includes a `[USER PROMPT SECURITY CHECK]` section based on the `prompt-injection-guard` safety skill and instructs the model to treat conflicting content as data.

Both return a **fixed-schema result dict** (JSON-serialisable). A stable core is
always present; capability-specific fields appear only when that capability is
enabled, so a *generic* agent never carries coding fields:

```python
{
  "mode": "general",   # the agent's role/profile label (see `mode` arg)
  "status": "done",    # "done" | "max_iterations"
  "answer": "...",      # the final text
  "reasoning": "...",
  "steps": [ ... ],     # every step the agent took (reasoning / execute / edit / ...)
  "error": "",
  "iterations": 2,
  # only when enableCodeExecution/enableShell:
  "commands": [ {"language","code","stdout","stderr","exit_code"} ],
  # only when enableFileEdit:
  "files_changed": ["path"],
  "diffs": [ {"path", "diff"} ],   # unified diff of each edit
}
```

Use `mode` (default `"general"`; e.g. `"coding"`, `"sql"`, `"research"`) to label
the agent's role — handy when composing several agents into a crew. It frames the
result and prompt; the coding fields above are gated by *capabilities*, not by mode.

> **Lifecycle:** `ask()` does **not** close the router, so the same client can be
> reused across independent tasks. Manage the connection with `async with` or by
> calling `aclose()` when done.

### Execution & tools (opt-in)

The **package provides the environment**; **skills teach which commands to use**.
The response protocol gains an `execute` action —
`{"status": "execute", "language": "python|shell", "code": "..."}` — and the agent
runs it, feeds stdout/stderr back, then returns a `done` answer with the output
and an explanation. This is how the agent *actually computes / searches / edits*
instead of guessing.

- `enableCodeExecution=True` — run **Python** the agent writes (subprocess + `codeExecutionTimeout`).
- `enableShell=True` — run **shell commands** (`grep`, `find`, `ls`, `cat`, `sed`, ...),
  via `bash` when available so POSIX syntax works cross-platform (Git Bash on Windows).
- Bundled skills drive these: `shell-commands` (search/navigate a codebase) and
  `code-editing` (Codex-style read → patch → write → verify).

**Safety gate.** Pass `onApprove(action) -> bool`; the agent calls it *before*
running anything and skips the action if it returns falsy. The embedding app owns
the policy — an interactive prompt (see [`demo.py`](demo.py): `y / N / always`), an
allow-list, or auto-approve. `onEvent(event)` streams each step (planning,
reasoning, execute, output) so a UI can render the loop live.

> ⚠️ **Security:** execution runs LLM-generated code/commands on your machine.
> Both flags are **off by default**; there is no sandbox beyond subprocess +
> timeout, so combine them with `onApprove` (or an allow-list) for untrusted use.
> As an embeddable **package** (not a standalone product), the host application
> decides what is permitted.

---

## How it works

A single `ask()` runs this pipeline:

1. **Reset state** — clears per-conversation memory/history so the client is reusable.
2. **Separate prompt channels** — keep trusted `systemPrompt` separate from untrusted `userPrompt`; scan `userPrompt` for prompt-injection and unsafe-action indicators before building the final prompt.
3. **Gather inputs** — load the skill index, extract any attached files, and run
   vector search to pick the top matching skills (cosine similarity, default
   `min_score=0.3`, `top_k=3`).
4. **Iteration loop** (up to 2000 by default, configurable with `maxIterations`):
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

## References

These papers inform the default skill design, retrieval metadata, CP-grounding objective, and safety gates:

1. George Ling, Shanshan Zhong, and Richard Huang. 2026. *Agent Skills: A Data-Driven Analysis of Claude Skills for Extending Large Language Model Functionality*. arXiv:2602.08004. DOI: https://doi.org/10.48550/arXiv.2602.08004
2. Zhiyuan Li, Jingzheng Wu, Xiang Ling, Xing Cui, and Tianyue Luo. 2026. *Towards Secure Agent Skills: Architecture, Threat Taxonomy, and Security Analysis*. arXiv:2604.02837. DOI: https://doi.org/10.48550/arXiv.2604.02837
3. Yi Liu, Weizhe Wang, Ruitao Feng, Yao Zhang, Guangquan Xu, Gelei Deng, Yuekang Li, and Leo Zhang. 2026. *Agent Skills in the Wild: An Empirical Study of Security Vulnerabilities at Scale*. arXiv:2601.10338. DOI: https://doi.org/10.48550/arXiv.2601.10338
4. Haoyu Gao, Jai Lal Lulla, Hong Yi Lin, Sebastian Baltes, Christoph Treude, and Mansooreh Zahedi. 2026. *From Registry to Repository: How AI Agent Skills Are Written, Adapted, and Maintained*. arXiv:2607.00911. DOI: https://doi.org/10.48550/arXiv.2607.00911
5. Yuntao Wang, Jianle Ba, Han Liu, Yanghe Pan, Jintao Wei, Zhou Su, Tom H. Luan, and Linkang Du. 2026. *Security of OpenClaw Agents: Fundamentals, Attacks, and Countermeasures*. arXiv:2605.25435. DOI: https://doi.org/10.48550/arXiv.2605.25435
6. Surada Suwansathit, Yuxuan Zhang, and Guofei Gu. 2026. *A Security Analysis of the OpenClaw AI Agent Framework*. arXiv:2603.27517. DOI: https://doi.org/10.48550/arXiv.2603.27517
7. Bowen Wei, Yunbei Zhang, Jinhao Pan, Kai Mei, Xiao Wang, Jihun Hamm, Ziwei Zhu, and Yingqiang Ge. 2026. *ClawSafety: "Safe" LLMs, Unsafe Agents*. arXiv:2604.01438. DOI: https://doi.org/10.48550/arXiv.2604.01438

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
