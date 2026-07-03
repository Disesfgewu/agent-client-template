---
name: database-review
description: Review database schema, queries, indexes, migrations, transactions, consistency, and operational risk for SQL and application persistence changes.
version: 1.0.0
author: Agent Team
tags:
  - database
  - sql
  - review
  - data
---

# Database Review

Review persistence changes for correctness, performance, integrity, and migration safety.

## When to Use
- Reviewing schema migrations, SQL queries, indexes, ORM models, data backfills, and transaction changes.
- Checking application code that changes persistence behavior or query load.

## Review Priorities
1. Correctness: constraints, nullability, uniqueness, referential integrity, and domain invariants.
2. Query performance: index use, cardinality, join shape, pagination, sort cost, and N+1 behavior.
3. Transaction safety: isolation level, lock scope, deadlock risk, idempotency, and retry behavior.
4. Migration safety: online compatibility, backfill plan, rollback, dual-read/write, and large-table impact.
5. Data protection: PII handling, encryption, retention, auditability, access control, and deletion semantics.

## Checklist
- New foreign keys and unique constraints match application assumptions.
- Indexes match actual filters, joins, ordering, and selectivity.
- Pagination is stable and avoids large offsets for high-volume tables.
- Migrations are compatible with old and new application versions during rollout.
- Backfills are chunked, resumable, observable, and safe to rerun.
- ORM eager/lazy loading behavior is explicit for changed query paths.

## Output
Lead with findings by severity. Include the migration/query affected, likely production impact, and a practical fix or rollout adjustment.
