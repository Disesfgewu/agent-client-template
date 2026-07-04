---
name: web-frontend-code-review
description: Review web frontend code for user-facing regressions, accessibility, responsive layout, state handling, framework correctness, and maintainability. Use for React, Vue, Svelte, HTML, CSS, and browser UI pull requests.
version: 1.0.0
author: Agent Team
tags:
  - frontend
  - web
  - review
  - accessibility
---

# Web Frontend Code Review

Review web UI changes from the user's perspective first, then inspect framework and code quality.

## When to Use
- Reviewing React, Vue, Svelte, HTML, CSS, routing, forms, component libraries, or design-system changes.
- Checking a web UI before merge, release, or handoff.

## Review Priorities
1. User-visible correctness: does the screen do the promised thing for real data?
2. Accessibility: semantics, keyboard paths, focus, labels, contrast, alt text, and dialog behavior.
3. Responsive behavior: mobile, tablet, desktop, zoom, long text, and overflow.
4. State coverage: loading, empty, error, disabled, optimistic, stale, and permission-denied states.
5. Framework correctness: hooks, memoization, reactivity, cleanup, hydration, routing, and server/client boundaries.
6. Maintainability: component boundaries, prop shape, duplicated logic, CSS leakage, and testability.

## Findings Checklist
- Forms validate clearly and submit only valid payloads.
- Async effects cancel or ignore stale responses.
- Lists have stable keys and virtualization where needed.
- CSS selectors are scoped and do not depend on fragile DOM depth.
- Event handlers do not break nested controls or keyboard behavior.
- Browser APIs are guarded for SSR and unsupported environments.
- Images, fonts, and bundles are sized for performance budgets.
- Tests cover the interaction and state that changed.

## Output
Lead with findings ordered by severity. Include file and line references, user impact, and the smallest practical fix. If no issues are found, say so and name any unverified viewport, browser, or assistive-technology risk.
