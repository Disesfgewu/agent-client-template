---
name: package-framework-analysis
description: Analyze and use real package, SDK, library, or framework APIs before implementing code. Use when the user asks Codex to build with, integrate, scaffold around, review, debug, migrate, or extend a named framework/package/repository, especially when the API may be local, private, unfamiliar, newly changed, or ambiguous. Prevents hallucinated imports/classes/methods by requiring source/docs/tests inspection before coding.
---

# Package And Framework Analysis

Use this skill when a task depends on a specific package, SDK, framework, or local repository API. The goal is to discover the real interface first, then implement against it.

## Core Rule

Do not invent classes, modules, methods, decorators, configuration files, CLIs, or lifecycle patterns for a named framework. If the interface is unknown, inspect it before writing integration code.

## Discovery Workflow

1. Identify the package or framework named by the user.
2. Determine whether it is local source, an installed dependency, generated code, or external documentation.
3. Inspect the most authoritative local sources first:
   - `pyproject.toml`, `setup.py`, `setup.cfg`, `package.json`, `composer.json`, `go.mod`, `Cargo.toml`, or equivalent package metadata.
   - Public exports such as `__init__.py`, `index.ts`, `src/index.*`, or documented entrypoints.
   - README, docs, examples, tests, demos, and existing call sites.
   - CLI modules, router/adapter classes, plugin registries, config loaders, and typed interfaces.
4. Use fast search to map the API:
   - Search the exact framework name.
   - Search exports/imports: `from package`, `import package`, `package.`, `class .*Client`, `def .*`, `async def .*`.
   - Search examples and tests before designing a new wrapper.
5. Summarize the discovered public API in working notes before coding when the task is non-trivial.

## Implementation Rules

- Prefer the framework's documented public interface over internal modules.
- Create small domain wrappers around the real API when the project needs business-specific behavior.
- Keep compatibility helpers honest: they may locate or import the real package, but must not redefine the framework.
- If running a generated subproject from a source checkout needs import help, add only a minimal path fallback that imports the real package from the repository root.
- If the package is not present locally and browsing is unavailable, state the gap and implement only a clearly marked adapter boundary or stub requested by the user.
- Preserve config injection. Do not hard-code secrets, API keys, endpoints, model names, or user-specific paths.

## Review Checklist

Before finishing, check:

- Imports resolve to the real package or documented module.
- No fake replacement classes shadow the framework name.
- Names used in examples match real exported symbols.
- Tests or smoke checks exercise the integration path.
- README or comments explain required config without exposing secrets.

## Red Flags

Stop and inspect more if you are about to:

- Create a file named after the framework that contains made-up core classes.
- Define generic classes such as `Agent`, `Framework`, `Client`, `Message`, or `Decision` because the API is unclear.
- Translate a user's framework name into a plausible but unverified architecture.
- Assume a CLI command, plugin format, or config schema without evidence from source, docs, or tests.