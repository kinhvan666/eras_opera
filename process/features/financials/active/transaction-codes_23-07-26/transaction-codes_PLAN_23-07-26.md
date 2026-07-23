# Transaction Codes Implementation Plan

**Date**: 23-07-26
**Status**: ⏳ PLANNED
**Complexity**: SIMPLE

## Overview, Goals, Scope
Replace the hardcoded CSV approach for transaction codes by extracting them directly from the OPERA Cloud Front Desk Configuration API (`GET /transactionCodes`). The goal is to accurately calculate net revenue (excluding taxes) directly in the data warehouse, enabling the dashboard to drop its hardcoded `'Tax'` exclusion.

## Touchpoints
- `extractor/src/extractors/hotel_config.py`
- `eras_dbt/models/staging/stg_transaction_codes.sql`
- `eras_dbt/models/staging/stg_cashiering_postings.sql`
- `dashboard_v2/data/repository.py`
- `extractor/tests/test_hotel_config_database.py`
- `eras_dbt/models/staging/schema.yml`

## Public Contracts
- Extractor: Adds `transactionCodes` table or JSON output from `hotel_config.py`.
- dbt: `stg_transaction_codes` will provide `transaction_code`, `classification`, `generatesSetup`.
- dbt: `stg_cashiering_postings` will expose `net_amount`.

## Blast Radius
- Extractor package (new method in `HotelConfigExtractor`).
- dbt staging models (1 new, 1 modified).
- Dashboard data layer (`repository.py` queries).

## Acceptance Criteria
- `hotel_config.py` extracts `transactionCodes` from the OPERA Cloud API.
- `stg_transaction_codes.sql` parses `transaction_code`, `classification`, and `generatesSetup`.
- `stg_cashiering_postings.sql` calculates `net_amount`.
- Dashboard UI uses `net_amount` and removes the hardcoded `NOT IN ('Tax', 'ServiceCharge')` filter.

## Phase Completion Rules
- All tests (Python unit and dbt data tests) pass.
- Dashboard renders revenue correctly without the hardcoded filter.
- Code is merged to master.

## Verification Evidence
| Gate / Scenario | Strategy | Proves SPEC criterion |
| --- | --- | --- |
| Extract transactionCodes mock | Fully-Automated | API data extracted successfully |
| `insert_transaction_codes_snapshot` database tests | Fully-Automated | Database inserts work correctly |
| `stg_transaction_codes` builds and passes tests | Hybrid | dbt models are correct |
| `stg_transaction_codes` schema tests | Fully-Automated | dbt schema unique/not_null constraints pass |
| `stg_cashiering_postings` calculates `net_amount` | Hybrid | `net_amount` logic is correct |
| Dashboard UI renders with `net_amount` | Agent-Probe | UI removes hardcoded filter |

Failing stub:
```
test("should extract transactionCodes successfully", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub for: Extract transactionCodes mock")
})
```

## Test Infra Improvement Notes
(none identified yet)

## Implementation Checklist
1. Update `extractor/src/extractors/hotel_config.py` to add a method `fetch_transaction_codes` that calls `GET /transactionCodes` (under Front Desk Configuration API), ensuring API pagination is properly handled (e.g. using `fetch_all` or checking for `hasMore`).
2. Create `eras_dbt/models/staging/stg_transaction_codes.sql` to parse `transaction_code`, `classification`, and `generatesSetup`. Deduplicate `transaction_code` using `DISTINCT ON` to prevent DBT fan-out risk.
3. Update `eras_dbt/models/staging/stg_cashiering_postings.sql` to LEFT JOIN `stg_transaction_codes` on `transaction_code` and calculate `net_amount` based on generatesSetup/Tax logic. Use `COALESCE(s.posted_amount::numeric, 0)` to handle nulls safely.
4. Update `dashboard_v2/data/repository.py` to query `net_amount` from `analytics.fct_folio_line` (or `stg_cashiering_postings` if materialized directly to fct) and remove the `NOT IN ('Tax', 'ServiceCharge')` hardcoded filter in `REVENUE_BREAKDOWN_SQL`, `REVENUE_ACTUAL_SQL`, etc.
5. Add missing database tests in `test_hotel_config_database.py` for `insert_transaction_codes_snapshot()`.
6. Add missing schema tests in `schema.yml` for `stg_transaction_codes` (unique on `transaction_code` + `hotel_id` and `not_null` constraints).

## Dependencies, Risks, Integration Notes
- Risk: Changes in transaction code structure could impact `net_amount` calculation.
- Dependency: Needs a running Postgres database for dbt model testing.

## Resume and Execution Handoff
- Selected plan file path: `process/features/financials/active/transaction-codes_23-07-26/transaction-codes_PLAN_23-07-26.md`
- Last completed phase or step: PLAN completed.
- Validate-contract status: pending
- Supporting context files loaded: `process/context/all-context.md`, `process/context/tests/all-tests.md`
- Next step for a fresh agent picking up mid-execution: Run VALIDATE phase to generate validate-contract.

## Validate Contract

Status: PASS
Date: 26-07-26
date: 2026-07-26
generated-by: outer-pvl

Parallel strategy: sequential
Rationale: 4 signals for sequential

Test gates (C3 5-column table — ADDITIVE; existing consumers still parse the legacy line form below it):

| criterion id | behavior | strategy | proving test | gap-resolution |
|---|---|---|---|---|
| TC-1 | API data extracted successfully | Fully-Automated | Extract transactionCodes mock | A |
| TC-1b | Database inserts work correctly | Fully-Automated | `insert_transaction_codes_snapshot` database tests | A |
| TC-2 | dbt models are correct | Hybrid | `stg_transaction_codes` builds and passes tests | A |
| TC-2b | dbt schema unique/not_null constraints pass | Fully-Automated | `stg_transaction_codes` schema tests | A |
| TC-3 | `net_amount` logic is correct | Hybrid | `stg_cashiering_postings` calculates `net_amount` | A |
| TC-4 | UI removes hardcoded filter | Agent-Probe | Dashboard UI renders with `net_amount` | A |

Dimension findings:
- Infra fit: PASS — standard python/dbt project structure
- Test coverage: PASS — covers Python mock, dbt models, and UI changes
- Breaking changes: PASS — no outward-facing API breakage, only internal downstream changes
- Security surface: PASS — read-only API extraction, no PII exposure

Open gaps: none
What this coverage does NOT prove:
- Extract transactionCodes mock DOES NOT PROVE handling of 500 errors from OPERA API
- stg_transaction_codes builds DOES NOT PROVE data correctness in production env
- stg_cashiering_postings calculates DOES NOT PROVE that net_amount perfectly matches all folio scenarios
- Dashboard UI renders DOES NOT PROVE cross-browser styling compatibility

Gate: PASS (no FAILs, plan updated)
Accepted by: session (autonomous, /goal execution)

## Autonomous Goal Block

Goal: Execute the transaction codes plan (23-07-26) to extract `transactionCodes` from OPERA Cloud and compute net revenue in dbt, removing the hardcoded 'Tax' filter from the dashboard.
Reference for latest state: process/features/financials/active/transaction-codes_23-07-26/transaction-codes_PLAN_23-07-26.md
Phase: EXECUTE
Next step: EXECUTE MODE
