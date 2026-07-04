---
name: web-frontend-design
description: Design web frontend UIs and components - layout, responsive design, accessibility, design systems, and HTML/CSS/React structure. Use when building or planning a web page, UI component, screen, or frontend layout.
version: 1.0.0
author: Agent Team
tags:
  - frontend
  - web
  - ui
  - design
---

# Web Frontend Design

Design clear, accessible, responsive web screens and components.

## When to Use
- Creating or redesigning a web page, dashboard, component, form, navigation, or flow.
- Translating product requirements into React, Vue, Svelte, HTML, CSS, or design-system structure.

## Core Workflow
1. Define the user goal, primary action, secondary actions, and information priority.
2. Choose the smallest layout that supports the task: single column, split view, grid, table, wizard, or dense tool surface.
3. Build from existing tokens and components first. Add new tokens only when reuse is impossible.
4. Design all states: loading, empty, error, disabled, hover, focus, selected, long text, small screen, and offline where relevant.
5. Verify with real or representative content, not placeholder-only layouts.

## Layout Standards
- Use semantic landmarks (`main`, `nav`, `aside`, `section`) and ordered headings.
- Use CSS grid for two-dimensional layout and flexbox for one-dimensional alignment.
- Prefer `rem`, `%`, `fr`, `minmax()`, `min()`, `max()`, and `clamp()` for robust sizing.
- Avoid horizontal overflow. Fixed widths require a clear reason and responsive bounds.
- Keep control groups stable so hover, labels, loading text, and validation messages do not shift core layout.

## Visual Design
- Establish hierarchy through spacing, typography, weight, and placement before adding decoration.
- Use restrained color: one primary action color, neutral surfaces, and semantic status colors.
- Avoid nested cards and decorative-only gradients. Cards should represent repeated items, tools, or modal content.
- Icons should clarify compact controls; text buttons should name commands.

## Accessibility
- Buttons, links, inputs, labels, and dialogs must use correct semantics.
- Meet WCAG AA contrast, provide visible focus, and never rely on color alone.
- Every interactive path must work by keyboard. Form errors must be programmatically connected.
- Images need meaningful `alt` text unless decorative.

## Output
Return implementation-ready structure: layout rationale, component tree, key CSS rules, responsive breakpoints, covered states, and accessibility decisions.
