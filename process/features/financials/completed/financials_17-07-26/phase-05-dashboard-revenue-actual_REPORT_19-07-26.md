---
phase: phase-05-dashboard-revenue-actual
date: 2026-07-19
status: COMPLETE
feature: financials
plan: process/features/financials/active/financials_17-07-26/phase-05-dashboard-revenue-actual_PLAN_17-07-26.md
---

## What Was Done

Added "Actual Revenue from Postings (Cashiering)" section to the Revenue tab of the Streamlit dashboard.

Files modified (additive only):
- `dashboard/data/repository.py` — added `REVENUE_ACTUAL_SQL` constant and `fetch_revenue_actual()` cached function
- `dashboard/ui/tabs/revenue.py` — imported `fetch_revenue_actual`, added new section at bottom of `draw()`

## Schema Verification (Step A1)

Table: `analytics.fct_folio_line` confirmed in the `analytics` schema.

Columns present: `fact_sk`, `transaction_no`, `hotel_id`, `revenue_date`, `reservation_id`, `posted_amount`, `revenue_category`, `cashier_id`, `reference`

Required columns for SQL (`revenue_date`, `revenue_category`, `posted_amount`, `hotel_id`): all present. SQL unchanged from plan.

## E2 Decision — Early-Return Scope

Kept the existing early-return at line 79 (`if bdf.empty: st.info(...); return`) unchanged.

Rationale: `bdf` is fetched from `fct_reservation_night` (booking/reservation data). In practice, cashiering postings are only generated for stays that have reservations. If there are no reservation-night records for a date range (bdf.empty), there are also no folio postings for that range. Refactoring would add complexity without meaningful benefit for this hotel's operational data pattern. The accepted concern (CONDITIONAL AC) already documents this edge case.

## Spot-Check (Step E1)

Reservation IDs 18577414 and 18156668 both found in `analytics.fct_folio_line`.

Results:
```
revenue_category | sum
-----------------|---------
FnB              | 12627600
Room             | 36548300
ServiceCharge    |    28560
Tax              |    17000
```

4 categories populated. Data confirmed working.

Total rows in fct_folio_line: 12,956

## Test Gate Outcomes

| Gate | Command | Result |
|------|---------|--------|
| AC-5-import | `cd dashboard && python -c "import app"` | PASS (exit 0) |
| AC-5-schema | Verified columns in fct_folio_line against fct_folio_line.sql | PASS |
| AC-8 | grep for existing function calls/structure in revenue.py | PASS — all original sections intact |

## Plan Deviations

None. Implementation matches plan exactly:
- `REVENUE_ACTUAL_SQL` added as a module-level constant in repository.py
- `fetch_revenue_actual` uses `@st.cache_data(ttl=CACHE_TTL_SECONDS)` and follows existing fetch function pattern
- New section added at bottom of `draw()` after col1/col2/col3 block
- `chart_wrapper` used per E1 requirement (mandatory per validate contract)
- Import added on the same line as existing imports

## Test Infra Gaps Found

None new. Known gap from validate contract: no automated rendering tests for dashboard UI — Agent-Probe tier only.

## Closeout Packet

- Selected plan: `process/features/financials/active/financials_17-07-26/phase-05-dashboard-revenue-actual_PLAN_17-07-26.md`
- Finished: all 5 implementation steps (A1, B1, B2, C1, C2) + smoke test (D1) + spot-check (E1)
- Verified: AC-5-import (automated, PASS), AC-5-schema (manual check, PASS), AC-8 (grep, PASS)
- Still unverified: visual rendering in live dashboard (Agent-Probe tier — requires running dashboard in browser)
- Cleanup remaining: none — no TODOs left behind
- Best next state: EVL confirmation run, then UPDATE PROCESS archival

## EVL Gate Results

All EVL gates PASS (confirmed by visual verify session 2026-07-19):

| Gate | Result | Notes |
|------|--------|-------|
| AC-5-import | PASS | `cd dashboard && python -c "import app"` exits 0 |
| AC-5-schema | PASS | analytics.fct_folio_line confirmed; all 4 required columns present |
| AC-8 | PASS | Existing revenue sections (By Day/Month toggle, trend chart, 3-column breakdown) render correctly and untouched |
| Structural | PASS | No night_amount in new code; `@st.cache_data(ttl=CACHE_TTL_SECONDS)` decorator present |

## Visual Verify Results

Visual verification completed in browser (2026-07-19):
- Section "Actual Revenue from Postings (Cashiering)" renders correctly
- Total displayed: ₫8,375,541,915 — matches DB `SUM(posted_amount)` exactly for date range 2026-04-20 to 2026-07-19
- All 5 revenue categories visible in stacked bar chart: FnB, Other, Room, ServiceCharge, Tax
- FnB ₫4.5B confirmed legitimate: large group/event business (e.g. META EVENT TRAVEL, 564 covers/₫282M per event)
- Negative bars present and expected: OPERA correction postings

## Key Finding — KPI Tile Understatement

Revenue KPI tile shows ₫3.41B (estimated from night_amount). True actual revenue from fct_folio_line = ₫8.24B (excl. Tax; ServiceCharge = phí dịch vụ, IS revenue). Gap is ~2.4x.

ADR and RevPAR tiles also use estimated data. All three tiles will need updating in a follow-up plan. TRevPAR and TRevPOR are new metrics now computable from fct_folio_line — not yet built.

This finding does not affect Phase 5 VERIFIED status — Phase 5 scope was additive (new section only, existing tiles unchanged per AC-8). The KPI tile update is deferred follow-up work.

## SPEC Achievement

Governed by umbrella SPEC: `process/features/financials/active/financials_17-07-26/financials_SPEC_17-07-26.md`

Phase 5 criteria:
- AC-5 (repository.py contains REVENUE_ACTUAL_SQL + fetch_revenue_actual()): **MET** — confirmed by import smoke test + code review
- AC-6 (Revenue tab renders new section with total metric): **MET** — visual verify PASS, ₫8,375,541,915 displayed
- AC-7 (Altair stacked bar chart with revenue by category, wrapped in chart_wrapper): **MET** — all 5 categories rendered (FnB, Other, Room, ServiceCharge, Tax)
- AC-8 (Existing revenue displays unchanged): **MET** — AC-8 gate PASS, structural verify confirms no changes to existing sections
- AC-SPOT (Dashboard total for filtered date range matches fct_folio_line sum): **MET** — ₫8,375,541,915 verified against DB

## Forward Preview

**Test Infra Found:** No new test infra gaps. All existing patterns followed.

**Blast Radius Changes:** `dashboard/data/repository.py` and `dashboard/ui/tabs/revenue.py` — additive only, no existing code changed.

**Commands to Stay Green:**
- `cd dashboard && python -c "import app"` — import smoke test
- `cd eras_dbt && dbt test --select fct_folio_line --profiles-dir .` — dbt data tests

**Dependency Changes:** None. No new Python dependencies added.
