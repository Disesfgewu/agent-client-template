---
name: shell-commands
description: Explore, search and navigate a codebase or filesystem with shell commands like grep, find, ls, cat, sed. Use when a task needs to search code, locate files, understand a project's structure, or inspect the filesystem before answering or editing.
version: 1.0.0
author: Agent Team
tags:
  - development
  - shell
  - codebase-navigation
  - search
---

# Shell / Codebase Navigation

The system can run shell commands for you: reply with an `execute` action whose
`language` is `"shell"`. You generate the command (POSIX/bash syntax); the
stdout/stderr is returned to you.

```json
{"status": "execute", "language": "shell", "code": "grep -rn \"def \" disesfgewuAgent", "reasoning": "..."}
```

## Useful commands
- **List / structure:** `find . -type f -not -path '*/.git/*' -not -path '*/__pycache__/*'`
  or `ls -la <dir>`
- **Search code:** `grep -rn "pattern" <path>` (scope it: `--include='*.py'`)
- **Read a file:** `cat <path>`; a slice only: `sed -n '1,60p' <path>` or `head -n 40 <path>`
- **Locate a symbol/definition:** `grep -rn "class Foo\|def foo" <path>`
- **Count / overview:** `wc -l <files>`, `git log --oneline -n 20`

## Workflow: "understand / review / redesign a project"
1. **Map it:** `find` the source files to see the structure.
2. **Find entry points & key symbols:** `grep -rn` for classes/functions/config.
3. **Read selectively:** `cat`/`sed` only the files that matter — do not dump everything.
4. **Reason**, then (if editing) use the code-editing skill to change files.

## Rules
- Keep output small so it fits the context: prefer `grep -n`, `sed` ranges,
  `head`, and scoped paths over dumping whole trees or large files.
- Quote patterns and paths.
- Read before you edit; verify after you edit.
