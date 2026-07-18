---
phase: phase-03-fct-folio-line
date: 2026-07-19
status: COMPLETE_WITH_GAPS
feature: financials
plan: process/features/financials/active/financials_17-07-26/phase-03-fct-folio-line_PLAN_17-07-26.md
---

## What Was Done

- Created `eras_dbt/models/dimensional/fct_folio_line.sql` — new fact table, grain = 1 row per transaction_no (12,885 rows loaded)
- Added `fct_folio_line` schema block to `eras_dbt/models/dimensional/schema.yml` — unique + not_null on fact_sk, not_null on transaction_no/hotel_id/revenue_date/posted_amount/revenue_category, documented exception on reservation_id (no relationships test per E1)
- Created `eras_dbt/tests/test_ac3_reservation_fk_match_rate.sql` — AC-3 singular test using ref() per E6

## Test Gate Outcomes

| Gate | Result | Notes |
|---|---|---|
| AC-4-unique: `dbt build --select fct_folio_line` unique test on fact_sk | PASS | 8/8 tests green (1 model + 7 schema tests) |
| AC-4-notnull: not_null on transaction_no, revenue_date, revenue_category, posted_amount | PASS | All 5 not_null tests green |
| AC-3-fk-rate: `dbt test --select test_ac3_reservation_fk_match_rate` | KNOWN-GAP | See below |
| SPEC-unmatched: count of NULL reservation_id rows | Agent-Probe: 0 rows | No unmatched postings in current data period — model structurally correct (no INNER JOIN) |

### AC-3 Known-Gap Detail

`test_ac3_reservation_fk_match_rate.sql` failed: actual unmatched rate = **64.41%** (8,299 / 12,885 non-null reservation_id rows have no match in stg_reservations).

**Root cause:** Data scope mismatch. Cashiering postings were extracted with reservation IDs in the ~16xxx range (2026 check-ins) while stg_reservations currently contains reservations in the ~11xxx range (earlier extraction window). This is not a model defect — the match rate threshold (≥95%) is unachievable until reservations are re-extracted to cover the same date range as cashiering postings.

**Classification:** `product-breakage` — data coverage gap between two extraction windows. The model is structurally correct; the test threshold is valid but cannot be satisfied with current data.

**Follow-up:** Phase 4 or a standalone extraction task should re-extract stg_reservations covering the 2026 date range that cashiering postings span.

## What Was Skipped or Deferred

- SPEC-unmatched agent-probe: 0 NULL reservation_id rows in current data. Model is structurally correct (LEFT-join-style, no INNER JOIN). If data with truly unmatched postings is loaded, NULLs will be preserved.
- AC-3-fk-rate: deferred to follow-up extraction task (see above)

## Plan Deviations

None from implementation checklist. All three files created exactly as specified.

## Test Infra Gaps Found

- AC-3 threshold (≥95%) is a data-scope gate, not a model-quality gate. It will remain red until the reservation extraction covers the same time window as cashiering postings. Consider making this test a `warn` severity or adding a config block `config(severity='warn')` in Phase 4 or a follow-up fix task.

## SPEC Achievement

Phase 3 scope: AC-3 and AC-4. Other ACs (1, 2, 5–10) are not in Phase 3 scope.

| AC | Description | Strategy | Gate | Result |
|---|---|---|---|---|
| AC-3 | ≥95% of non-null reservation_id rows match stg_reservations | Fully-Automated | `dbt test --select test_ac3_reservation_fk_match_rate` | **UNMET** — 35.59% match rate (data scope gap: cashiering postings span 2026 reservations; stg_reservations covers earlier window). Backlog note: re-extract stg_reservations for 2026-01-01+ range. |
| AC-4 | fct_folio_line has 1 row per transaction_no; no duplicates | Fully-Automated | `dbt build --select fct_folio_line` (unique + not_null tests) | **MET** — 8/8 PASS |

### SPEC Gaps

- **AC-3 unmet:** Known-gap residual. Root cause: reservation extraction window does not cover the 2026 date range that cashiering postings span. Model is correct (LEFT-style, NULLs preserved). Backlog note: expand stg_reservations extraction to cover 2026-01-01 onward before Phase 4 aggregation (or configure AC-3 test severity to `warn` for this data-gap period).

## Closeout Packet

- Selected plan: `process/features/financials/active/financials_17-07-26/phase-03-fct-folio-line_PLAN_17-07-26.md`
- Finished: fct_folio_line model + schema tests + AC-3 test file
- Verified: 8/8 dbt build gates green; agent-probe on NULL count completed
- Unverified: AC-3 threshold (data scope gap)
- Cleanup remaining: commit, umbrella state update
- Next: Phase 4 (fct_reservation_night enrichment with cashiering data) + follow-up re-extraction of stg_reservations for 2026 range

## Forward Preview

### Test Infra Found
- AC-3 singular test exists and runs; threshold cannot pass with current data — needs reservation re-extraction

### Blast Radius Changes
- `eras_dbt/models/dimensional/fct_folio_line.sql` — new (additive)
- `eras_dbt/models/dimensional/schema.yml` — fct_folio_line block added (additive)
- `eras_dbt/tests/test_ac3_reservation_fk_match_rate.sql` — new (additive)

### Commands to Stay Green
```bash
cd eras_dbt && dbt build --profiles-dir . --select fct_folio_line
# Expected: PASS=8 WARN=0 ERROR=0
```

### Dependency Changes
- Phase 4 depends on fct_folio_line being available in analytics schema — now satisfied
- AC-3 test depends on stg_reservations covering same date range as cashiering postings — not yet satisfied
