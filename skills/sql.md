---
name: sql
description: Write, explain, optimize, and debug SQL queries (SELECT / JOIN / GROUP BY / window functions, and DDL/DML). Use when a task involves querying or changing a relational database, designing a schema, or reasoning about SQL.
version: 1.0.0
author: Agent Team
tags:
  - data
  - sql
  - database
---

# SQL

Produce correct, readable SQL and explain it.

## When to use
- Writing or fixing a SELECT / INSERT / UPDATE / DELETE / DDL statement.
- Designing a schema, adding indexes, or reasoning about query performance.
- Explaining what a query does or why it is slow.

## Approach
1. **Pin down the data**: the tables, their columns and keys, and the grain (what
   one row represents). State any assumptions if the schema is not given.
2. **State the goal in one sentence**, then write the query to match it.
3. **Write explicit, portable SQL**: qualify columns, use `JOIN ... ON` (never
   comma joins), name derived columns, and avoid `SELECT *` in a final answer.
4. **Aggregation**: every non-aggregated column in `SELECT` must appear in
   `GROUP BY`. Use `WHERE` to filter rows and `HAVING` to filter aggregates.
5. **Window functions** (`OVER (PARTITION BY ... ORDER BY ...)`) for ranking,
   running totals, and per-group math that must keep every row.
6. **Correctness over cleverness**: mind `NULL` (`NULL <> NULL`; use `IS NULL`,
   `COALESCE`), integer division, and row fan-out from one-to-many joins.

## Performance
- Filter early and select only the columns you need.
- Index the columns used in `JOIN` / `WHERE` / `ORDER BY`.
- Do not wrap an indexed column in a function inside `WHERE` (it disables the index).
- Prefer `EXISTS` over `IN` for large subqueries, and joins over correlated subqueries.

## Output
Give the query in a fenced ```sql block, then a short explanation of what it does
and the assumptions you made. If dialect matters (PostgreSQL / MySQL / SQLite /
SQL Server), say which one you used.
