---
name: report:financials-phase-02-stg-cashiering-postings
description: "Phase 2 closeout — stg_cashiering_postings dbt staging model"
date: 18-07-26
metadata:
  node_type: memory
  type: report
  feature: financials
  phase: phase-02
---

# Phase 02 Report — stg_cashiering_postings Staging Model

**Plan:** process/features/financials/active/financials_17-07-26/phase-02-stg-cashiering-postings_PLAN_17-07-26.md
**Date:** 2026-07-18
**Status:** COMPLETE
**Feature:** financials
**Phase:** phase-02

---

## What Was Done

- `eras_dbt/models/staging/stg_cashiering_postings.sql` — NEW. Staging model over `raw.cashiering_postings`:
  - Revenue filter: `raw_data->>'transactionType' = 'Revenue'` (JSONB path, not top-level column)
  - 9xxx exclusion: `transaction_code NOT LIKE '9%'` (TEXT column, not integer)
  - `revenue_category` CASE WHEN on transaction_code prefix: 1x=Room, 2x/3x/6x=FnB, 7x=Tax, 8x=ServiceCharge, ELSE='Other'
  - Pass-through columns: `hotel_id`, `revenue_date`, `transaction_code`, `posted_amount`, `transaction_no`, `cashier_id`, `reference`
  - `reservation_id` derived from `raw_data->'guestInfo'->'reservationId'->>'id'` (nullable — no not_null test per E5)
- `eras_dbt/models/sources/sources.yml` — MODIFIED: added `cashiering_postings` source entry under `raw` source
- `eras_dbt/models/staging/schema.yml` — MODIFIED: added `stg_cashiering_postings` block with `not_null` on revenue_category, `accepted_values` (Room/FnB/Tax/ServiceCharge/Other)
- `eras_dbt/tests/test_stg_cashiering_postings_no_wrapper_rows.sql` — NEW: singular dbt test asserting zero rows with `transaction_code LIKE '9%'`

## What Was Skipped/Deferred

- `reservation_id` not_null test — intentionally skipped per E5 (nullable; unmatched posting rows are valid; Phase 3 handles FK via WHERE reservation_id IS NOT NULL)
- AC-3 FK join integrity (95-pct rate: non-null reservation_id rows match stg_reservations) — deferred to Phase 3 fct_folio_line plan (known-gap D from validate-contract)

## Test Gate Outcomes

| Gate | Command | Result |
|---|---|---|
| dbt build stg_cashiering_postings + tests | `cd eras_dbt && dbt build --profiles-dir . --select stg_cashiering_postings` | PASS — 6 passes, 12,885 rows, 0 errors |
| 9xxx exclusion (AC-2) | singular test: `test_stg_cashiering_postings_no_wrapper_rows.sql` | PASS — 0 rows with transaction_code LIKE '9%' |
| revenue_category not_null (AC-3) | schema test: not_null on revenue_category | PASS |
| revenue_category accepted_values (AC-3) | schema test: accepted_values Room/FnB/Tax/ServiceCharge/Other | PASS — 5 distinct values confirmed |
| reservation_id column exists (nullable) | model build success | PASS |

EVL confirmation: dbt build PASS = 6, 12,885 rows, 5 revenue_category values correct, 0 rows with 9xxx transaction_code.

## Plan Deviations

None. Execute followed the validate-contract instructions (E1–E6) exactly:
- E1: JSONB filter used (`raw_data->>'transactionType'`) — confirmed before writing model
- E2: `reservation_id` derived from JSONB path, nullable column present
- E3: `NOT LIKE '9%'` on TEXT column (not integer BETWEEN)
- E4: ELSE 'Other' branch included in CASE WHEN
- E5: No not_null test on reservation_id
- E6: sources.yml written before model (A1 before B1 sequencing respected)

## Test Infra Gaps Found

- AC-3 FK join integrity (95-pct of non-null reservation_id rows match stg_reservations) — not testable in Phase 2 blast radius; flagged as known-gap D in validate-contract; Phase 3 RESEARCH must pick this up and add a singular dbt test to fct_folio_line checklist.

## SPEC Achievement

| Criterion | Strategy | Status | Notes |
|---|---|---|---|
| AC-2: 9xxx/Wrapper rows excluded | Fully-Automated | met | singular test 0 rows confirmed |
| AC-3: revenue_category derived correctly | Fully-Automated | met | 5 values, not_null, accepted_values all pass |
| AC-3 FK rate (95-pct join) | Known-Gap | unmet | deferred to Phase 3 |

Unmet criterion backlog stub: Phase 3 plan must add singular dbt test asserting `COUNT(*) WHERE reservation_id IS NOT NULL / COUNT(*) total_non_null >= 0.95` between stg_cashiering_postings and stg_reservations.

## Closeout Packet

1. **Selected plan path:** `process/features/financials/active/financials_17-07-26/phase-02-stg-cashiering-postings_PLAN_17-07-26.md`
2. **Closeout classification:** Ready for UPDATE PROCESS archival
3. **What was finished:** stg_cashiering_postings model (SQL), sources.yml entry, schema.yml tests, singular 9xxx exclusion test
4. **Verified:** dbt build PASS (6/6), 12,885 rows, 5 revenue_category values, 0 wrapper rows. Unverified: AC-3 FK 95-pct rate (deferred to Phase 3)
4b. **Validate-contract:** present (inline in plan, Gate: CONDITIONAL — accepted concern = AC-3 FK rate deferred to Phase 3)
5. **Cleanup done:** Phase report written, plan Steps 5/6/7 ticked, umbrella state updated, context doc updated. Still needed: none
6. **Next valid state:** `ENTER UPDATE PROCESS for Phase 3 — process/features/financials/active/financials_17-07-26/phase-03-fct-folio-line_PLAN_17-07-26.md`
7. **Commit checkpoint:** Execution commit first (`feat(financials): stg_cashiering_postings dbt staging model`), then process commit
8. **Regression status:** Phase 1 surfaces checked — `extractor/` not touched; Phase 1 pytest still green (no changes to extractor package)

Drift score: MEDIUM (2 signals: 4 files touched, 2 memory-worthy observations — JSONB-only transactionType pattern + TEXT NOT LIKE pattern for code exclusion)
Recommend UPDATE PROCESS -- significant changes detected.

## Forward Preview

### Test Infra Found

- Singular dbt test pattern for row-count assertions: `test_stg_cashiering_postings_no_wrapper_rows.sql` — reuse this pattern for Phase 3 FK rate test

### Blast Radius Changes

Files added/modified vs plan blast radius:
- `eras_dbt/models/staging/stg_cashiering_postings.sql` — NEW (as planned)
- `eras_dbt/models/sources/sources.yml` — MODIFIED (as planned)
- `eras_dbt/models/staging/schema.yml` — MODIFIED (added as test surface — within blast radius)
- `eras_dbt/tests/test_stg_cashiering_postings_no_wrapper_rows.sql` — NEW (within blast radius)

No files outside the declared blast radius were touched.

### Commands to Stay Green

```bash
cd eras_dbt && dbt build --profiles-dir .
# Must include stg_cashiering_postings model + 3 tests passing
```

### Dependency Changes

None — no new dbt packages or Python deps added.
