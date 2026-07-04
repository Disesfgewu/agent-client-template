---
name: full-stack-app-scaffold
description: Build and verify complete full-stack application scaffolds with backend, database, frontend, tests, documentation, dependency checks, and cleanup. Use when Codex is asked to create, regenerate, or review a project/app/site with both server/API/database and frontend UI, especially in an existing target directory where stale scaffold files may already exist.
---

# Full-Stack App Scaffold

Use this skill when creating or reviewing a full-stack app. A scaffold is not complete until the canonical backend, database, frontend, tests, docs, and validation commands all line up.

## Start With Inventory

Before writing files into an existing target directory:

1. List the current top-level files and app entrypoints.
2. Identify stale or superseded scaffold paths from previous attempts.
3. Decide whether to replace, migrate, or preserve each existing subtree.
4. Avoid leaving two runnable apps with overlapping routes or contradictory README instructions.

If destructive cleanup is needed, restrict it to the requested project directory and verify resolved paths first.

## Required Completion Criteria

A generated full-stack project should have:

- One canonical backend entrypoint, documented in README.
- One canonical frontend entrypoint, documented in README.
- Database schema, initialization path, and test-safe database override.
- API contracts matching frontend service calls.
- Deterministic fallback for AI/LLM features when keys or config are absent.
- Tests for database initialization, CRUD, and at least one end-to-end API smoke path.
- Frontend `package.json`, lockfile when dependencies are installed, and a successful build check.
- README commands that match the actual files and working directories.

## Backend Checks

- Keep route handlers thin; place database operations in a repository/CRUD layer.
- Use dependency-injected sessions for request-scoped work where practical.
- Provide environment variables for database path and external configs.
- Do not hard-code user secrets or machine-specific config paths.
- For AI agents inside web apps, disable shell/code/file-edit capabilities unless explicitly required.
- If an old backend remains, either remove it or clearly mark it as legacy and ensure README does not point to it.

## Frontend Checks

- Ensure frontend API paths match backend routes and dev-server proxy settings.
- Build real UI files, not only empty directories.
- Run `npm install` when needed before build verification.
- Run the build script; do not claim the frontend works if `tsc`, Vite, or bundling fails.
- Run or inspect dependency audit output. Fix high/critical issues when a compatible upgrade is available; otherwise report the residual risk.
- Remove generated `node_modules`, `dist`, and TypeScript build info after validation unless the user asked to keep build artifacts. Keep lockfiles for reproducibility.

## Documentation Checks

- README setup commands must match actual paths and filenames.
- Mention backend and frontend startup commands separately.
- Include API config and database environment variables.
- Avoid stale names from previous scaffolds.
- Scan rendered markdown for obvious typos, broken code fences, extra backticks, and mojibake.

## Final Verification

Before finishing, run the narrowest practical set:

1. Python syntax/import check for backend files.
2. Backend tests.
3. API smoke test with an isolated temporary database.
4. Frontend dependency install when needed.
5. Frontend build.
6. Dependency audit or explicit residual-risk note.
7. Cleanup of runtime artifacts such as databases, caches, `node_modules`, `dist`, and `*.tsbuildinfo` when appropriate.

Report what passed, what failed, and any remaining manual setup.