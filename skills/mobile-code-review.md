---
name: mobile-code-review
description: Review mobile application code for Android, iOS, React Native, Flutter, and cross-platform app behavior including lifecycle, permissions, offline handling, performance, and release risk.
version: 1.0.0
author: Agent Team
tags:
  - mobile
  - review
  - android
  - ios
---

# Mobile Code Review

Review mobile code with the device lifecycle, platform constraints, and release risk in mind.

## When to Use
- Reviewing Android, iOS, React Native, Flutter, Kotlin, Swift, Dart, or mobile backend integration changes.
- Checking app behavior before TestFlight, Play internal testing, or production release.

## Review Priorities
1. Lifecycle correctness: app backgrounding, rotation, process death, resume, and navigation stack restoration.
2. Permissions and privacy: request timing, fallback states, data minimization, and platform policy compliance.
3. Network resilience: timeout, retry, cancellation, offline cache, idempotency, and stale data handling.
4. Performance: startup, main-thread work, memory, image loading, animations, battery, and background tasks.
5. Platform UX: safe areas, keyboard handling, gestures, accessibility, localization, and text scaling.
6. Release safety: feature flags, migrations, crash reporting, analytics, and rollback paths.

## Checklist
- No secrets, tokens, or private keys are bundled in the app.
- Storage is appropriate for sensitivity: keychain/keystore for credentials, encrypted storage when needed.
- Push notifications, deep links, universal links, and app links handle invalid payloads safely.
- Background work respects OS limits and user battery expectations.
- Tests cover lifecycle, permission denial, offline mode, and migration paths where changed.

## Output
Findings first, ordered by severity. Include user impact, affected platform, file and line references, and the smallest fix that reduces release risk.
