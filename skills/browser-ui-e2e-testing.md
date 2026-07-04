---
name: browser-ui-e2e-testing
description: Run and verify real browser UI flows for web apps. Use when Codex needs to launch a frontend or backend dev server, request approval for browser automation, use Playwright/Selenium-style clicks, typing, navigation, screenshots, viewport checks, console/network inspection, or validate whether a frontend actually works beyond static build and unit tests.
---

# Browser UI E2E Testing

Use this skill to verify a web UI with a real browser and real user interactions.

## Workflow

1. Inventory the app before running it:
   - Identify package manager, install state, dev/build/test scripts, backend dependencies, required env vars, expected ports, and database or seed requirements.
   - Prefer existing project scripts over inventing commands.
   - If dependencies are missing or browser binaries must be installed, request approval before installing them.

2. Start only the services needed for the test:
   - Launch backend and frontend dev servers as long-running processes with explicit working directories.
   - Capture the local URL and wait for readiness with HTTP checks or Playwright navigation retries.
   - Keep production URLs, destructive admin actions, and real external accounts out of the test unless the user explicitly asks.

3. Use browser automation for user-visible behavior:
   - Prefer Playwright when available; otherwise use the repo's established browser E2E framework.
   - Drive flows with mouse and keyboard actions: click controls, type into inputs, submit forms, navigate routes, open menus, and verify state changes.
   - Do not treat DOM-only assertions as enough when the user asked for real UI testing.

4. Validate the full surface:
   - Check page render, route transitions, responsive desktop/mobile viewports, form validation, loading/empty/error states, and data persistence where applicable.
   - Capture screenshots for visual inspection when layout, canvas, animation, responsive behavior, or rendering quality matters.
   - Fail on relevant console errors, unhandled exceptions, broken network requests, or unexpected non-2xx API responses.
   - For canvas, WebGL, charts, or 3D scenes, verify nonblank pixels and that the scene is framed and interactive.

5. Tie UI behavior back to system behavior:
   - When the UI writes data, verify API responses and database or repository state if the project exposes safe local checks.
   - When the UI depends on mocked data, state that the validation is mock-backed.

6. Clean up:
   - Stop any dev servers or browser processes started for the test.
   - Remove generated caches or build artifacts when they are not intended source changes.
   - Keep lockfiles only when dependency installation intentionally updated them.

## Reporting

Report the exact commands, local URLs, browser flows exercised, pass/fail result, and any residual risk. If real browser automation could not run, say why and separate fallback checks from true E2E validation.