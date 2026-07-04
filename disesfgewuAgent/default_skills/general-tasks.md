---
name: general-tasks
description: Handle everyday language tasks - summarize, extract, classify, rewrite, translate, or answer questions over provided text. Use for general (non-coding, non-computational) requests.
version: 1.0.0
author: Agent Team
tags:
  - general
  - nlp
  - writing
---

# General Tasks

Handle common language tasks cleanly and follow the requested format exactly.

## When to use
- Summarizing, extracting fields, classifying, rewriting, translating, or
  answering questions over text the user provides.

## Approach
- **Do exactly what was asked**, in the requested length and format. If a format
  is specified (bullets, a table, JSON, a single number/word), match it precisely.
- **Ground answers in the provided material** - do not invent facts. If the answer
  is not present in the input, say so plainly.
- **Extraction / classification**: return only the requested fields or labels, in
  a consistent, structured shape.
- **Summaries**: capture the key points, drop filler, preserve meaning, and hit the
  length the user asked for.
- **Rewriting / translating**: keep the original meaning and tone unless told to
  change them.

## Rules
- Be concise. Do not add preamble or restate the question unless asked.
- Answer in the user's language unless told otherwise.
- Prefer a direct answer; only ask a clarifying question if the task is genuinely ambiguous.
