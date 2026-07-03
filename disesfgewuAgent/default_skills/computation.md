---
name: computation
description: Reliable numeric computation - calculate, compute or evaluate an exact number - arithmetic, powers, factorials, sums, percentages, math, statistics, unit conversion, finance, combinatorics, and data crunching. Use whenever a task asks to calculate/compute a number rather than estimate it.
version: 1.0.0
author: Agent Team
tags:
  - math
  - computation
  - data
---

# Computation

Compute exact results - never guess arithmetic.

## When to use
- Any task needing a precise number: arithmetic, percentages, statistics, finance,
  unit conversion, combinatorics, or large-number math.
- Aggregating or crunching data.

## Approach
- **If code execution is available, run the calculation** with an `execute`
  (python) step instead of doing mental math, and print the result:
  ```json
  {"status": "execute", "language": "python", "code": "print(sum(range(1, 101)))", "reasoning": "..."}
  ```
  Use the standard library for exactness: `math`, `statistics`, `fractions`,
  `decimal`. Use `decimal.Decimal` for money and `fractions.Fraction` for exact
  ratios; avoid binary `float` when precision matters.
- **If code execution is not available**, show the work step by step, keep every
  intermediate value, and double-check the final arithmetic before answering.

## Rules
- Never report a computed number you did not actually compute.
- State units and how you rounded.
- For statistics, say which measure you used (mean vs median, sample vs population).
- Verify surprising results (very large/small, off by an order of magnitude) before finishing.
