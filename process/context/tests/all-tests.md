---
name: context:all-tests
description: "Testing context router for ErasOpera — pytest (extract/load) + dbt test (dimensional model), commands, debugging"
keywords: tests, testing, pytest, dbt test, dbt build, verification, fixtures, postgres, ci, debugging, data tests, respx, mock, asyncio
related: [context:all-database]
date: 18-07-26
---

# ErasOpera - All Tests

Last updated: 2026-07-18

Attach this file first when the task involves testing, verification, or test debugging.

This is the fast operator guide for the testing surface: which runner to use, what command to start
with, how to debug common failures, and which deeper file to read next.

Do not load the whole `process/context/tests/` folder by default. Start here, then drill down.

---

## How This File Works

This is the `all-tests.md` entrypoint for the `tests/` context group. Agents read `all-context.md`
first and get routed here for testing tasks. This file gives quick decision rules and commands.

---

## What This Covers

- test runner selection (Python unit vs dbt data tests)
- quick commands for the Python extractor suite and dbt dimensional model
- fast debugging procedures and known pitfalls
- current testing gaps

## Read This When

- running tests after implementing an extractor, loader, or dbt model
- deciding between a Python unit test and a dbt data test
- debugging a failing test or a warehouse assertion

## Quick Routing

(No deeper test docs yet. Add routing entries here as they are created — e.g. `dbt-tests.md`,
`extractor-tests.md`, `debugging-and-pitfalls.md`.)

## Quick Decision Guide

### Use `pytest` when

- testing Python extract/load logic: OPERA Cloud API clients, auth/token handling, pagination,
  retry, response parsing, and raw→staging transforms
- the unit is pure Python and does not require the warehouse
- testing database insert methods with a mocked psycopg2 connection

### Use `dbt test` when

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

| Layer | Runner | Command | Notes |
|---|---|---|---|
| Python extract/load (all tests) | pytest | `cd extractor && poetry run pytest tests/ -v` | no warehouse needed for unit tests |
| Single test file | pytest | `cd extractor && poetry run pytest tests/test_cashiering_extractor.py -v` | scope to one file |
| Single test | pytest | `cd extractor && poetry run pytest tests/test_foo.py::test_name -v` | scope to one test |
| Dimensional model | dbt | `cd eras_dbt && dbt test --select stg_cashiering_postings+ --profiles-dir .` | needs Postgres + .user.yml |
| Full pipeline | dbt | `cd eras_dbt && dbt build --profiles-dir .` | run + test all models |
| Types/lint (optional) | ruff / mypy | `ruff check .` / `mypy .` | wire up as needed |

**Run from project root:** both pytest and dbt commands use `cd extractor` or `cd eras_dbt` first.
poetry manages the Python package at repo root (`pyproject.toml`); always invoke via `poetry run pytest`.

## Current Test Suite State (as of 2026-07-18)

### Extractor pytest suite (`extractor/tests/`)

32 tests, 0 failures. Layout:

| File | Count | What it covers |
|---|---|---|
| `test_main_wiring.py` | 2 | Wiring: all 3 extractors (Reservation, HotelConfig, Cashiering) called in main() |
| `test_cashiering_extractor.py` | 11 | CashieringExtractor: 6 window edge cases, pagination primary+fallback, multipage, all-type storage, column extraction |
| `test_cashiering_database.py` | 5 | insert_cashiering_postings: table-in-method, ON CONFLICT, raw_data overwrite, empty no-op, commit |
| (pre-existing extractor + hotel_config tests) | 14 | ReservationExtractor, HotelConfigExtractor, database insert_raw_data |

### dbt test suite (`eras_dbt/tests/`)

- `schema.yml` files in `staging/` and `dimensional/`: standard `not_null` / `unique` / `relationships` tests on all current models
- `tests/test_dim_property_room_count_not_null_hotel_79017.sql`: singular test asserting `dim_property.room_count IS NOT NULL` for hotel_id='79017'

## Mock Patterns (Extractor Tests)

### Mocked HTTP — respx + pytest-asyncio

Extractor tests use `respx` to mock OPERA Cloud HTTP calls and `pytest-asyncio` for async test functions. Pattern from `test_cashiering_extractor.py`:

```python
import respx
import httpx
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def mock_client():
    client = MagicMock()
    client.fetch_one = AsyncMock(return_value={...})
    return client

@respx.mock
@pytest.mark.asyncio
async def test_extraction(mock_client):
    ...
```

Key: `fetch_one` is an `AsyncMock` (not `MagicMock`) since it is awaited in the extractor.

### Mocked DB — psycopg2 cursor monkeypatch

Database method tests (`test_cashiering_database.py`) mock the psycopg2 connection/cursor:

```python
from unittest.mock import MagicMock, patch

@patch('extractor.src.database.execute_values')
def test_insert(mock_execute_values, mock_db):
    ...
```

**Critical pitfall:** `execute_values` (from `psycopg2.extras`) must be patched at `extractor.src.database.execute_values` (where it is imported), NOT at `psycopg2.extras.execute_values`. If you patch the wrong location, the real `execute_values` is called, which mogrifies against the cursor and throws because the cursor is a MagicMock.

### Pagination test fixtures

Multi-page fixture pattern: return `{"postings": [...50 items...], "hasMore": True}` on first call, then `{"postings": [...partial...], "hasMore": False}` on second call. Use `side_effect` on the `AsyncMock`:

```python
mock_client.fetch_one.side_effect = [page_1_response, page_2_response]
```

## Debugging Quick Reference

- **DB connection:** dbt and integration tests need `DATABASE_URL` (or `PG*` vars) + a valid dbt
  `profiles.yml` target (at `eras_dbt/.user.yml`, gitignored) pointing at a test schema.
  Pass `--profiles-dir .` from within `eras_dbt/`.
- **OPERA API in tests:** mock the OPERA Cloud HTTP layer in unit tests using `respx` —
  do not hit live OPERA endpoints in the unit suite. See mock patterns above.
- **Async endpoints:** the "Asynchronous" OPERA APIs return job handles — test the poll/collect loop
  with fixtures, not live jobs.
- **pytest-asyncio:** async tests require `@pytest.mark.asyncio` decorator; ensure `pytest-asyncio`
  is in `pyproject.toml` dev dependencies.
- **respx conflict:** if `respx.mock` interferes with another test's HTTP calls, scope it with
  `with respx.mock:` as a context manager instead of a decorator.

## Known Gaps

- E2E (live OPERA Cloud) tests are not in CI — require real credentials; run manually against
  sandboxed OPERA environment. Document results in phase reports.
- Mocked-DB upsert tests assert SQL structure via captured SQL strings + params, not real
  PostgreSQL ON CONFLICT behavior. Real-DB verification requires a live Postgres instance.
- No CI pipeline wired yet — all tests run locally via `poetry run pytest`.
- dbt tests require a live PostgreSQL instance with `eras_dbt/.user.yml` credentials (gitignored).
