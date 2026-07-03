---
name: flutter-frontend-code-review
description: Review Flutter frontend code for widget correctness, layout constraints, navigation, state management, accessibility, performance, and platform behavior. Use for Dart and Flutter UI pull requests.
version: 1.0.0
author: Agent Team
tags:
  - flutter
  - review
  - mobile
  - dart
---

# Flutter Frontend Code Review

Review Flutter changes for user behavior, render safety, state correctness, and maintainable widget structure.

## Review Priorities
1. User-visible correctness across normal, loading, empty, error, and offline states.
2. Layout safety: no overflow, unbounded constraints, clipped text, or unstable scroll behavior.
3. State management: providers, blocs, controllers, listeners, streams, and futures are disposed or scoped correctly.
4. Navigation: route arguments, deep links, back behavior, dialogs, sheets, and nested navigators are coherent.
5. Accessibility: semantics, text scaling, focus traversal, screen-reader labels, and tap target size.
6. Performance: rebuild scope, const constructors, list laziness, image caching, animation cost, and shader jank.

## Checklist
- `setState` is not called after dispose and async completions are guarded.
- `BuildContext` is not used unsafely across async gaps.
- Controllers, focus nodes, animation controllers, subscriptions, and timers are disposed.
- Expensive work is outside `build` unless memoized or trivial.
- Keys are used where identity matters and avoided where they create churn.
- Platform-specific behavior is gated and tested for Android, iOS, web, or desktop as applicable.

## Output
Lead with concrete findings by severity. Include file and line references, observed risk, and a focused fix. Mention any missing device class, text-scale, or platform verification.
