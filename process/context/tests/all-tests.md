---
name: context:all-tests
description: "Testing context router for ErasOpera — pytest (extract/load) + dbt test (dimensional model), commands, debugging"
keywords: tests, testing, pytest, dbt test, dbt build, verification, fixtures, postgres, ci, debugging, data tests
related: [context:all-database]
date: 13-07-26
---

# ErasOpera - All Tests

Last updated: 2026-07-13

Attach this file first when the task involves testing, verification, or test debugging.

This is the fast operator guide for the testing surface: which runner to use, what command to start
with, how to debug common failures, and which deeper file to read next.

Do not load the whole `process/context/tests/` folder by default. Start here, then drill down.

---

## How This File Works

This is the `all-tests.md` entrypoint for the `tests/` context group. Agents read `all-context.md`
first and get routed here for testing tasks. This file gives quick decision rules and commands.

> **Status:** ErasOpera is greenfield — no test suite exists yet. The runners and commands below are
> the **intended** setup for the Python + dbt + Postgres stack. Replace the "(planned)" markers with
> real commands as the code and dbt project land.

---

## What This Covers

- test runner selection (Python unit vs dbt data tests)
- quick commands once the project exists
- fast debugging procedures
- current testing gaps

## Read This When

- running tests after implementing an extractor, loader, or dbt model
- deciding between a Python unit test and a dbt data test
- debugging a failing test or a warehouse assertion

## Quick Routing

(No deeper test docs yet. Add routing entries here as they are created — e.g. `dbt-tests.md`,
`extractor-tests.md`, `debugging-and-pitfalls.md`.)

## Quick Decision Guide

### Use `pytest` when (planned)

- testing Python extract/load logic: OPERA Cloud API clients, auth/token handling, pagination,
  retry, response parsing, and raw→staging transforms
- the unit is pure Python and does not require the warehouse

### Use `dbt test` when (planned)

- asserting the dimensional model: `not_null`, `unique`, `relationships`, `accepted_values` on
  staging, dimension, and fact models
- validating grain (no unexpected fan-out), conformed-dimension integrity, and SCD behavior

### Use a running Postgres when

- the test exercises real SQL, dbt model materialization, or end-to-end load → transform flows
- prefer an isolated/ephemeral test database or schema, never a shared production warehouse

## Default Verification Order

1. run the narrowest Python unit test (`pytest path::test`) for extractor/loader logic
2. run `dbt test --select <model>` for the affected model and its downstream
3. run a full `dbt build` (run + test) only when validating the whole pipeline

## Commands

| Layer | Runner | Command (planned) | Notes |
|---|---|---|---|
| Python extract/load | pytest | `pytest` / `pytest path/to/test.py::test_name` | no warehouse needed for pure units |
| Dimensional model | dbt | `dbt test --select stg_reservation+` | needs Postgres + `profiles.yml` target |
| Full pipeline | dbt | `dbt build` | run + test all models |
| Types/lint (optional) | ruff / mypy | `ruff check .` / `mypy .` | wire up when the Python package exists |

## Debugging Quick Reference

- **DB connection:** dbt and integration tests need `DATABASE_URL` (or `PG*` vars) + a valid dbt
  `profiles.yml` target pointing at a test schema.
- **OPERA API in tests:** mock the OPERA Cloud HTTP layer in unit tests (record/replay or fixtures
  built from `docs/` spec examples) — do not hit live OPERA endpoints in the unit suite.
- **Async endpoints:** the "Asynchronous" OPERA APIs return job handles — test the poll/collect loop
  with fixtures, not live jobs.

## Known Gaps

- No test suite, no pytest config, no dbt project exist yet (greenfield).
- No CI wiring yet.
- Fixtures derived from the OPERA Cloud specs in `docs/` have not been built.
