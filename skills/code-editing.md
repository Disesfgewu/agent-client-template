---
name: code-editing
description: Modify, refactor, patch, or fix source code files on disk. Use when the task asks to edit, change, fix, refactor, rename, add, or remove code in a file, or to apply a change to a file.
version: 1.0.0
author: Agent Team
tags:
  - development
  - code-editing
  - refactoring
---

# Code Editing

Apply changes to source files safely and precisely, like a coding agent.

## When to use
- The task asks to modify, fix, refactor, rename, or add/remove code in a file.
- A file is attached under `[FILES]` with its path, or a path is given in the task.

## Workflow

1. **Read the current file first** (with `execute` shell `cat`/`sed`, or `execute`
   python `open(path).read()`), so you know the exact snippet to change:
   ```json
   {"status": "execute", "language": "shell", "code": "sed -n '1,80p' <path>"}
   ```

2. **Plan a minimal, targeted change.** Preserve everything unrelated. Change the
   smallest span that must change; never rewrite the whole file.

3. **Apply the edit with the `edit_file` action** (the system computes a diff,
   applies it, and records the change):
   ```json
   {"status": "edit_file", "path": "<path>", "old": "<exact snippet, must occur once>", "new": "<replacement>", "reasoning": "..."}
   ```
   If `old` is not unique, include more surrounding context until it matches once.
   (If `edit_file` is unavailable, fall back to `execute` python `open(path,'w')`.)

4. **Verify** with an `execute` step: re-read the file, import/run it, or run the
   tests. If verification fails, iterate until it passes.

5. **Report** in your final `done` answer: which file changed, what changed, and why.

## Rules
- Make the smallest correct edit; never rewrite an entire file for a small change.
- Keep the file syntactically valid and match the surrounding style/indentation.
- Never touch unrelated code.
- Always verify after editing; only finish once the change is confirmed to work.
