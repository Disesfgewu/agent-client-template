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

Apply changes to source files safely and precisely, like a coding agent. You do
this by writing small Python scripts and running them with the `execute` action
(read the file, patch it, write it back, verify).

## When to use
- The task asks to modify, fix, refactor, rename, or add/remove code in a file.
- A file is attached under `[FILES]` with its path, or a path is given in the task.

## Workflow

1. **Read the current file** with an `execute` step, so you edit the real content:
   ```python
   path = r"<the path shown in [FILES] or given in the task>"
   src = open(path, encoding="utf-8").read()
   print(src)
   ```

2. **Plan a minimal, targeted change.** Preserve everything unrelated. Replace the
   smallest span that must change; do not rewrite the whole file.

3. **Apply the edit and write it back** with an `execute` step:
   ```python
   old = "<exact snippet to replace>"
   new = "<replacement snippet>"
   assert src.count(old) == 1, f"need exactly one match, found {src.count(old)}"
   open(path, "w", encoding="utf-8").write(src.replace(old, new, 1))
   print("edit applied")
   ```
   If `old` is not unique, include more surrounding context until it matches once.

4. **Verify** with another `execute` step: re-read the file, import/run it, or run
   the tests. If verification fails, iterate until it passes.

5. **Report** in your final `done` answer: which file changed, what changed, and why.

## Rules
- Make the smallest correct edit; never rewrite an entire file for a small change.
- Keep the file syntactically valid and match the surrounding style/indentation.
- Never touch unrelated code.
- Always verify after editing; only finish once the change is confirmed to work.
