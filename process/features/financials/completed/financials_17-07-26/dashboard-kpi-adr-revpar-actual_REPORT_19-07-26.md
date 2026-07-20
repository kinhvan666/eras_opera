---
phase: dashboard-kpi-adr-revpar-actual
date: 2026-07-19
status: COMPLETE_WITH_GAPS
feature: financials
plan: process/features/financials/active/financials_17-07-26/dashboard-kpi-adr-revpar-actual_PLAN_19-07-26.md
---

# EXECUTE Exit Summary — ADR & RevPAR Actual KPI Tiles

## What Was Done

Implemented Plan B+C (steps 1–7) exactly as specified. Two files changed, additive only.

**`dashboard/data/repository.py`** — added after `fetch_revenue_actual_summary`:
- 3 SQL constants: `ROOM_REVENUE_SQL` (fct_folio_line, revenue_category = 'Room'), `ROOM_NIGHTS_SQL` (fct_reservation_night, excl. Cancelled/NoShow), `ROOM_COUNT_SQL` (dim_property MAX room_count)
- `_fetch_adr_revpar_inputs(start_date, end_date, hotel_id=None)` — private, `@st.cache_data`; ADR = room_rev / room_nights (guarded >0), RevPAR = room_rev / (room_count × days) (guarded >0); `days = (end_date - start_date).days + 1`
- `fetch_adr_revpar_actual_summary(...)` — public; 7d/30d prior-period shift matching `fetch_kpi_summary`; returns `(curr_adr, curr_revpar, prior_adr, prior_revpar)`
- `timedelta` NOT re-imported (already at line 1) — constraint honored

**`dashboard/app.py`**:
- Import expanded to include `fetch_adr_revpar_actual_summary`
- Added try/except block after the `actual_revenue` block → sets `actual_adr, actual_revpar, prior_actual_adr, prior_actual_revpar` (None fallback)
- ADR tile (row1[2]): now `kpi_card("ADR", fmt_vnd(actual_adr), actual_adr, prior_actual_adr)` — `badge=True` removed
- RevPAR tile (row1[3]): now `kpi_card("RevPAR", fmt_vnd(actual_revpar), actual_revpar, prior_actual_revpar)` — `badge=True` removed
- Occupancy tile (row1[1]): untouched, retains `badge=True`

## Test Gate Outcomes

| Gate | Strategy | Result |
|---|---|---|
| `cd extractor && poetry run pytest tests/ -v` | Fully-Automated | PASS — 32/32 passed in 1.79s (no regression) |
| `py_compile` repository.py + app.py | Fully-Automated (syntax) | PASS — SYNTAX OK |
| Dashboard import / ADR ≈₫2.56M / RevPAR ≈₫783,795 tile values | Hybrid | NOT RUN — requires live Streamlit + Postgres; deferred to manual verification |
| Occupancy badge retained / None renders as "—" | Agent-Probe | NOT RUN in headless session; code-verified (Occupancy untouched; `fmt_vnd(None)` → "—") |

## What Was Skipped or Deferred

- Step 8 manual verification (visual dashboard check) — Hybrid/agent-probe gate; needs running Streamlit against `erasopera-postgres-1` (port 5434). Recommend the user run `cd dashboard && streamlit run app.py` with a 90-day window and confirm ADR ≈ ₫2,560,399, RevPAR ≈ ₫783,795, Occupancy still shows EST badge.

## Plan Deviations

None. All 7 code steps match the plan verbatim.

## Test Infra Gaps Found

- No automated unit-test suite exists for `dashboard/data/repository.py` (pre-existing gap across the whole dashboard layer; accepted as known-gap in the CONDITIONAL validate-contract). Not introduced by this change.

## Closeout Packet

- Selected plan: `process/features/financials/active/financials_17-07-26/dashboard-kpi-adr-revpar-actual_PLAN_19-07-26.md`
- Finished: all code steps 1–7; both automated gates green
- Verified: extractor regression (32/32), Python syntax of both changed files
- Still unverified: live dashboard tile values + visual badge check (Hybrid/agent-probe — needs running app)
- Classification: **Keep in active/testing** — code-complete, automated gates green, but Hybrid tile-value verification pending user confirmation on running dashboard

## Forward Preview

- **Test Infra Found:** dashboard layer has no unit tests (known-gap, unchanged)
- **Blast Radius Changes:** `dashboard/data/repository.py`, `dashboard/app.py` only
- **Commands to Stay Green:** `cd extractor && poetry run pytest tests/ -v`
- **Dependency Changes:** none
