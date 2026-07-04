---
name: backend-design
description: Design backend services, APIs, data flows, reliability boundaries, security controls, observability, and deployment architecture. Use when planning server-side features or service changes.
version: 1.0.0
author: Agent Team
tags:
  - backend
  - architecture
  - api
  - reliability
---

# Backend Design

Design backend systems around explicit contracts, failure modes, data ownership, and operational visibility.

## When to Use
- Planning APIs, services, jobs, queues, integrations, auth, payments, data pipelines, or operational workflows.
- Choosing between synchronous APIs, events, workers, cron jobs, or batch processing.

## Core Workflow
1. Define the domain operation, caller, data owner, latency target, consistency need, and failure tolerance.
2. Specify API contracts: method, path, request, response, status codes, idempotency, pagination, and versioning.
3. Choose storage and transaction boundaries. State what must be atomic and what can be eventually consistent.
4. Design failure handling: retries, dead letters, timeouts, circuit breakers, backoff, compensation, and alerts.
5. Add security: authentication, authorization, validation, rate limits, secrets, audit logs, and least privilege.
6. Add observability: structured logs, metrics, traces, dashboards, and runbook signals.

## Design Checks
- The service has a clear owner for each piece of data it mutates.
- Public APIs are backward compatible or versioned.
- Expensive operations have bounded resource usage and cancellation behavior.
- Background jobs are idempotent and safe to retry.
- External dependencies have timeout and degradation strategies.
- Migrations and rollout steps are reversible where practical.

## Output
Return the proposed architecture, API contract, data model changes, failure modes, security controls, observability plan, rollout plan, and open tradeoffs.
