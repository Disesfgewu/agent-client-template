---
name: flutter-frontend-design
description: Design Flutter app screens, widgets, navigation, responsive layouts, accessibility, state surfaces, and Material or Cupertino UI structure. Use when planning mobile or desktop Flutter interfaces.
version: 1.0.0
author: Agent Team
tags:
  - flutter
  - frontend
  - mobile
  - design
---

# Flutter Frontend Design

Design Flutter interfaces as composable widget trees with clear state, navigation, and platform behavior.

## When to Use
- Planning Flutter screens, flows, reusable widgets, themes, and responsive layouts.
- Translating product requirements into Material, Cupertino, or custom Flutter UI.

## Core Workflow
1. Define the route, user intent, primary action, back behavior, and persistent state.
2. Sketch the widget tree before styling: scaffold, app bar, body, navigation, overlays, and reusable children.
3. Choose layout primitives intentionally: `Column`, `Row`, `Stack`, `ListView`, `CustomScrollView`, `Sliver*`, `Expanded`, `Flexible`, and `LayoutBuilder`.
4. Cover states: loading, empty, error, offline, permission denied, refreshing, disabled, and long content.
5. Apply theme tokens through `ThemeData`, extensions, text styles, spacing constants, and color roles.

## Layout Standards
- Avoid unbounded constraints in scrollables. Use `Expanded`, `Flexible`, or slivers where constraints matter.
- Design for text scaling, safe areas, orientation, tablets, foldables, and desktop widths when applicable.
- Prefer lazy lists for long content. Avoid building large lists with `Column`.
- Keep tap targets at least 48 logical pixels where platform conventions allow.

## Accessibility
- Add semantic labels for icon-only controls and custom widgets.
- Preserve focus order and support keyboard traversal for desktop/web builds.
- Test large text, high contrast, screen readers, and platform back gestures.

## Output
Return the route structure, widget tree, state model, theme choices, responsive rules, accessibility notes, and expected edge states.
