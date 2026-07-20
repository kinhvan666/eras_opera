---
name: plan:dashboard-kpi-adr-revpar-actual
description: Replace estimated ADR and RevPAR KPI tiles with actual Room revenue from fct_folio_line
date: 19-07-26
feature: financials
phase: "standalone"
---

# Dashboard KPI — ADR & RevPAR Actual Values

Complexity: SIMPLE
Date: 19-07-26
Status: ⏳ PLANNED
**Date:** 19-07-26
**Feature:** financials
**Plan file:** `process/features/financials/active/financials_17-07-26/dashboard-kpi-adr-revpar-actual_PLAN_19-07-26.md`

## Overview

The ADR and RevPAR KPI tiles on the dashboard currently display estimated values derived from
`night_amount` in `fct_reservation_night`. This plan replaces them with actual Room revenue from
`analytics.fct_folio_line` (category = 'Room'), matching hospitality industry standard definitions:

- **ADR actual** = Room revenue / room nights sold (occupied, excl. Cancelled/NoShow)
- **RevPAR actual** = Room revenue / available rooms (room_count × days in period)

Verified numbers (90-day window):
- Room revenue: ₫3,456,538,207 | Room nights: 1,350 | Room count: 49
- ADR actual: ~₫2,560,399 (vs ₫2,902,363 estimated)
- RevPAR actual: ~₫783,795 (vs ₫781,085 estimated)

## Goals

1. Add `fetch_adr_revpar_actual_summary` function to `dashboard/data/repository.py`
2. Wire it into `dashboard/app.py` ADR and RevPAR KPI tiles
3. Remove `badge=True` from ADR and RevPAR tiles (Occupancy keeps badge — it stays estimated)
4. No dbt, extractor, or schema changes

## Scope

**In scope:**
- `dashboard/data/repository.py` — 3 SQL constants + 2 functions (~30 lines)
- `dashboard/app.py` — 1 import change, 4 lines added, 2 kpi_card calls changed

**Out of scope:**
- Occupancy tile (stays estimated, stays badge=True)
- `kpi_daily_snapshot.sql` (dbt mart — not changed)
- Extractor / OPERA API layer
- Revenue tile (already actual via `fetch_revenue_actual_summary`)

## Touchpoints

| File | Change type |
|---|---|
| `dashboard/data/repository.py` | Add 3 SQL constants + `_fetch_adr_revpar_inputs` + `fetch_adr_revpar_actual_summary` |
| `dashboard/app.py` | Update import, add try/except block, update 2 kpi_card calls |

## Public Contracts

- `fetch_adr_revpar_actual_summary(start_date, end_date, hotel_id=None)` → `(curr_adr, curr_revpar, prior_adr, prior_revpar)` — all values are `float | None`
- `_fetch_adr_revpar_inputs(start_date, end_date, hotel_id=None)` → `(adr, revpar)` — private, cached

No changes to existing public functions. No new API endpoints. No schema changes.

## Blast Radius

- **Files changed:** 2
- **Risk class:** LOW — additive only; existing estimated ADR/RevPAR paths replaced with new actual paths; no shared infrastructure touched
- **Rollback:** revert 2 files; no migration needed

## Implementation Checklist

### Step 1 — Add SQL constants to `dashboard/data/repository.py`

After the existing SQL constants (near `REVENUE_SQL` or equivalent), add:

```
ROOM_REVENUE_SQL = """
    SELECT COALESCE(SUM(posted_amount), 0) AS room_revenue
    FROM analytics.fct_folio_line
    WHERE revenue_date BETWEEN %(start_date)s AND %(end_date)s
      AND revenue_category = 'Room'
      AND (%(hotel_id)s::text IS NULL OR hotel_id = %(hotel_id)s)
"""

ROOM_NIGHTS_SQL = """
    SELECT COUNT(*) AS room_nights
    FROM analytics.fct_reservation_night
    WHERE business_date BETWEEN %(start_date)s AND %(end_date)s
      AND reservation_status NOT IN ('Cancelled', 'NoShow')
      AND (%(hotel_id)s::text IS NULL OR hotel_id = %(hotel_id)s)
"""

ROOM_COUNT_SQL = """
    SELECT COALESCE(MAX(room_count), 0) AS room_count
    FROM analytics.dim_property
    WHERE (%(hotel_id)s::text IS NULL OR hotel_id = %(hotel_id)s)
"""
```

### Step 2 — Add `_fetch_adr_revpar_inputs` (private, cached) to `dashboard/data/repository.py`

After the SQL constants from Step 1, add:

```
@st.cache_data(ttl=CACHE_TTL_SECONDS)
def _fetch_adr_revpar_inputs(start_date, end_date, hotel_id=None):
    with psycopg2.connect(DATABASE_URL) as conn:
        room_rev = pd.read_sql(ROOM_REVENUE_SQL, conn,
            params={"start_date": start_date, "end_date": end_date, "hotel_id": hotel_id}
        )["room_revenue"].iloc[0]
        room_nights = pd.read_sql(ROOM_NIGHTS_SQL, conn,
            params={"start_date": start_date, "end_date": end_date, "hotel_id": hotel_id}
        )["room_nights"].iloc[0]
        room_count = pd.read_sql(ROOM_COUNT_SQL, conn,
            params={"hotel_id": hotel_id}
        )["room_count"].iloc[0]
    days = (end_date - start_date).days + 1
    adr = float(room_rev) / room_nights if room_nights > 0 else None
    revpar = float(room_rev) / (room_count * days) if room_count > 0 else None
    return adr, revpar
```

Constraint: `timedelta` is already imported at top of `repository.py` — do NOT re-import.

### Step 3 — Add `fetch_adr_revpar_actual_summary` (public) to `dashboard/data/repository.py`

Immediately after `_fetch_adr_revpar_inputs`, add:

```
def fetch_adr_revpar_actual_summary(start_date, end_date, hotel_id=None):
    """Actual ADR and RevPAR for current and prior period. Same 7d/30d shift as fetch_kpi_summary."""
    range_days = (end_date - start_date).days + 1
    shift = timedelta(days=7 if range_days <= 14 else 30)
    curr_adr, curr_revpar = _fetch_adr_revpar_inputs(start_date, end_date, hotel_id)
    prior_adr, prior_revpar = _fetch_adr_revpar_inputs(
        start_date - shift, end_date - shift, hotel_id
    )
    return curr_adr, curr_revpar, prior_adr, prior_revpar
```

### Step 4 — Update import in `dashboard/app.py`

Find the line that imports from `data.repository` (currently imports `fetch_kpi_summary`,
`fetch_properties`, `fetch_revenue_actual_summary`). Add `fetch_adr_revpar_actual_summary`:

```python
from data.repository import (
    fetch_kpi_summary,
    fetch_properties,
    fetch_revenue_actual_summary,
    fetch_adr_revpar_actual_summary,
)
```

### Step 5 — Add try/except block in `dashboard/app.py` after existing `actual_revenue` block

After the `try/except` that calls `fetch_revenue_actual_summary`, add:

```python
try:
    actual_adr, actual_revpar, prior_actual_adr, prior_actual_revpar = \
        fetch_adr_revpar_actual_summary(start_date, end_date, hotel_id)
except Exception:
    actual_adr, actual_revpar, prior_actual_adr, prior_actual_revpar = None, None, None, None
```

### Step 6 — Update ADR KPI tile in `dashboard/app.py`

Find the ADR kpi_card call (in `row1[2]`). Replace:

```python
kpi_card("ADR", fmt_vnd(current['adr']), current["adr"], g(prior, "adr"), badge=True)
```

With:

```python
kpi_card("ADR", fmt_vnd(actual_adr), actual_adr, prior_actual_adr)
```

Note: `badge=True` is removed — ADR tile now shows actual values.

### Step 7 — Update RevPAR KPI tile in `dashboard/app.py`

Find the RevPAR kpi_card call (in `row1[3]`). Replace:

```python
kpi_card("RevPAR", fmt_vnd(current['revpar']), current["revpar"], g(prior, "revpar"), badge=True)
```

With:

```python
kpi_card("RevPAR", fmt_vnd(actual_revpar), actual_revpar, prior_actual_revpar)
```

Note: `badge=True` is removed. Occupancy tile (`row1[0]`) keeps `badge=True` — do NOT touch it.

### Step 8 — Manual verification

Run the dashboard and confirm:
- ADR tile shows ~₫2,560,399 for a 90-day window (not ~₫2,902,363)
- RevPAR tile shows ~₫783,795 for the same window
- Occupancy tile still shows badge/estimated label
- Revenue tab is unaffected
- No Python import errors or Streamlit runtime errors

## Phase Completion Rules

This is a SIMPLE (one-session) plan. No phase gates or approval checkpoints between steps.

- Implement checklist steps 1–7 continuously in a single EXECUTE session
- Run Step 8 manual verification after all code steps are complete
- Context loaded: `process/context/all-context.md`. Test context: `process/context/tests/all-tests.md`

## Acceptance Criteria

1. `fetch_adr_revpar_actual_summary` returns `(float|None, float|None, float|None, float|None)` for valid date ranges
2. ADR tile value matches `SUM(posted_amount) / COUNT(room_nights)` for Room category only
3. RevPAR tile value matches `SUM(posted_amount) / (room_count × days)` — denominator is available rooms, not occupied rooms
4. Both tiles display `None` gracefully (no Streamlit exception) when DB is unavailable
5. Occupancy tile still carries `badge=True`; Revenue tab unaffected
6. `timedelta` is not re-imported inside any new function body

## Verification Evidence

| Gate / Scenario | Strategy | Proves SPEC criterion |
|---|---|---|
| `poetry run pytest extractor/tests/ -v` passes (no extractor changes) | Fully-Automated | AC-4 — no regression in extractor layer |
| Dashboard loads without import error after code change | Hybrid (requires running Streamlit + Postgres) | AC-1, AC-4 |
| ADR tile value ≈ ₫2,560,399 for 90-day window | Hybrid (requires DB with fct_folio_line data) | AC-2 |
| RevPAR tile value ≈ ₫783,795 for 90-day window | Hybrid (requires DB with fct_folio_line data) | AC-3 |
| Occupancy tile retains badge label | Agent probe (visual check) | AC-5 |
| revenue_category filter = 'Room' only (no FnB/Service/Other) | Hybrid — query `SELECT DISTINCT revenue_category FROM analytics.fct_folio_line` confirms | AC-2 |
| None values render without error when DB unavailable | Agent probe (remove DB env var temporarily) | AC-4 |

## Dependencies

- `analytics.fct_folio_line` must exist and be populated (verified — 18,245 postings confirmed)
- `analytics.fct_reservation_night` must exist (verified — used by existing dashboard queries)
- `analytics.dim_property` must have `room_count` for hotel 79017 (verified — value = 49)
- `timedelta` already imported in `repository.py` (verified at line 1)
- `psycopg2`, `pandas`, `st` already imported in `repository.py` (verified)

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| `hotel_id` NULL handling differs between repositories | Low | `%(hotel_id)s::text IS NULL` pattern already used in `fetch_revenue_actual_summary` — consistent |
| `room_nights = 0` in prior period causes division by zero | Low | Guarded: `adr = float(room_rev) / room_nights if room_nights > 0 else None` |
| `room_count = 0` in dim_property | Very low | Guarded: `revpar = ... if room_count > 0 else None` |
| Prior-period shift logic mismatch with `fetch_kpi_summary` | Low | Explicitly copied: 7d shift for ≤14 day range, else 30d |

## Test Infra Improvement Notes

(none identified yet — all test coverage for this plan is hybrid/manual via running dashboard against live Postgres)

## Resume and Execution Handoff

1. **Selected plan file:** `process/features/financials/active/financials_17-07-26/dashboard-kpi-adr-revpar-actual_PLAN_19-07-26.md`
2. **Last completed phase/step:** PLAN written; VALIDATE not yet run
3. **Validate-contract status:** pending — vc-validate-agent writes this section before EXECUTE
4. **Supporting context files loaded:** `process/context/all-context.md`, `process/features/financials/active/financials_17-07-26/` (backlog handout)
5. **Next step for fresh agent:** Read this plan. Confirm Postgres is reachable (`docker ps` — look for `erasopera-postgres-1` on port 5434). Execute Steps 1–7 in order. Run Step 8 manual verification. All changes are additive — no existing functions deleted.

## Validate Contract

Status: CONDITIONAL
Date: 19-07-26
date: 2026-07-19
generated-by: inner-pvl: plan-bc

Parallel strategy: sequential
Rationale: 0/7 signals — LOW score; 2-file additive dashboard change, no fan-out needed

Test gates (C3 5-column table):

| criterion id | behavior | strategy | proving test | gap-resolution |
|---|---|---|---|---|
| AC-4-extractor | Extractor test suite passes with no regression (extractor layer unchanged) | Fully-Automated | `cd extractor && poetry run pytest tests/ -v` exits 0 | A |
| AC-1-import | fetch_adr_revpar_actual_summary is importable without error | Hybrid | `cd dashboard && python -c "from data.repository import fetch_adr_revpar_actual_summary; print('ok')"` — precondition: poetry env, Postgres accessible via DATABASE_URL | B |
| AC-2-adr | ADR tile shows actual Room revenue / room nights (≈ ₫2,560,399 for 90-day window) | Hybrid | Run `streamlit run app.py` with erasopera-postgres-1 on port 5434; set 90-day date range; verify ADR tile value | B |
| AC-3-revpar | RevPAR tile shows actual Room revenue / (room_count × days) (≈ ₫783,795 for 90-day window) | Hybrid | Same dashboard run as AC-2; verify RevPAR tile | B |
| AC-5-badge | Occupancy retains badge=True (EST label); ADR and RevPAR do not show EST | Agent-Probe | Navigate KPI row; confirm EST visible only on Occupancy tile, not ADR or RevPAR | B |
| AC-4-none | None values for actual_adr/actual_revpar render as "—" without Streamlit exception | Agent-Probe | Observe dashboard behavior when DB is unavailable or returns no rows (try/except in Step 5 returns None, None, None, None; fmt_vnd(None) returns "—" — confirmed in components.py) | B |

gap-resolution legend:
- A — proven now (gate passes in this cycle)
- B — fixed in this plan (gate added by this plan's checklist)
- C — deferred to a named later phase/plan
- D — backlog test-building stub (named residual; keep-active; continue)

C-4 reconciliation: the `strategy:` column carries ONLY the 3 proving strategies (Fully-Automated / Hybrid / Agent-Probe). Known-Gap is a named residual, not a strategy value.

Legacy line form:
- extractor regression: Fully-automated: cd extractor && poetry run pytest tests/ -v
- dashboard import: hybrid: python -c "from data.repository import fetch_adr_revpar_actual_summary" — precondition: poetry env + DATABASE_URL
- ADR/RevPAR tile values: hybrid: streamlit run app.py + live Postgres port 5434
- badge visual check: agent-probe: visual inspection of KPI row
- dashboard unit tests: known-gap: no dashboard test suite exists (pre-existing infrastructure gap)

Failing stub (Fully-Automated rows only):
```
test("should pass extractor test suite with no regression", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub for: extractor test suite passes with no regressions (cd extractor && poetry run pytest tests/ -v)")
})
```

Dimension findings:
- Infra fit: PASS — additive Python/SQL; psycopg2/pandas/streamlit/DATABASE_URL patterns already in use; no new deps
- Test coverage: CONCERN — no automated unit tests for dashboard/data/repository.py (pre-existing infrastructure gap across entire dashboard layer; not introduced by this plan); hybrid + agent-probe strategy documented in Verification Evidence
- Breaking changes: PASS — no existing functions changed; new public function additive; no schema/dbt/extractor changes
- Security surface: PASS — parameterized SQL (%(param)s::text IS NULL pattern); no auth/billing/secrets surface touched
- Section A (SQL constants): PASS — additive; insertable after REVENUE_ACTUAL_KPI_SQL (line 143); execute-agent note: insert after last SQL constant block
- Section B (_fetch_adr_revpar_inputs): PASS — mirrors _fetch_revenue_actual_scalar pattern; division-by-zero guarded; timedelta not re-imported
- Section C (fetch_adr_revpar_actual_summary): PASS — mirrors fetch_revenue_actual_summary; shift logic consistent with both fetch_kpi_summary and fetch_revenue_actual_summary
- Section D (import update): PASS — line 20 of app.py uniquely matchable; single import addition
- Section E (try/except block): PASS — insert after lines 77-80 (fetch_revenue_actual_summary try/except block)
- Section F (ADR tile update): PASS — line 94 exact match; fmt_vnd(None) returns "—" confirmed in components.py; _delta_html returns "" when current is None
- Section G (RevPAR tile update): PASS — line 96 exact match; Occupancy tile (line 92) keeps badge=True and is NOT touched; Revenue tile (line 90) already actual
- Section H (manual verification): PASS — agent-probe; reference values documented (₫2,560,399 ADR, ₫783,795 RevPAR); values may vary slightly if additional postings loaded

Open gaps:
- dashboard-unit-tests: known-gap: pre-existing infrastructure gap — no dashboard/data/repository.py test suite exists in repo; hybrid/agent-probe strategy is the established pattern for dashboard changes; not introduced by this plan

What this coverage does NOT prove:
- AC-4-extractor (pytest): Does NOT prove dashboard/data/repository.py function logic, SQL correctness, or edge-case handling
- AC-1-import (hybrid): Does NOT prove the function returns correct computed values
- AC-2-adr / AC-3-revpar (hybrid): Does NOT prove correctness when additional postings are added after plan was written; exact tile values may differ from reference if DB state has changed
- AC-5-badge (agent-probe): Does NOT automatically catch future badge regressions in CI
- AC-4-none (agent-probe): Does NOT exercise all DB failure modes (e.g. partial failure mid-three-query function)

Gate: CONDITIONAL (1 CONCERN — pre-existing dashboard layer test infrastructure gap; accepted by session under autonomous execution)
Accepted by: session (autonomous, /goal execution) — CONCERN: no automated unit tests for dashboard/data/repository.py; pre-existing infrastructure gap; hybrid + agent-probe strategy documented in Verification Evidence is the established pattern for all dashboard changes in this repo
