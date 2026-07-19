---
phase: dashboard-kpi-revenue-actual
date: 2026-07-19
status: COMPLETE_WITH_GAPS
feature: financials
plan: process/features/financials/active/financials_17-07-26/dashboard-kpi-revenue-actual_PLAN_19-07-26.md
---

# EXECUTE Exit Summary — Revenue KPI Tile Actual Revenue

## What Was Done

All 6 checklist steps implemented exactly as specified. No deviations.

- **`dashboard/data/repository.py`** (additive only, after `fetch_revenue_actual`):
  - Added `REVENUE_ACTUAL_KPI_SQL` — `SUM(posted_amount)` from `analytics.fct_folio_line`, filters `revenue_category != 'Tax'`.
  - Added `_fetch_revenue_actual_scalar(start_date, end_date, hotel_id=None)` — private, `@st.cache_data(ttl=CACHE_TTL_SECONDS)`, returns `df["revenue"].iloc[0] if not df.empty else 0.0`.
  - Added `fetch_revenue_actual_summary(start_date, end_date, hotel_id=None)` — public; computes `range_days`/`shift` (7d for ≤14-day ranges, else 30d, identical to `fetch_kpi_summary`); returns `(current_rev, prior_rev)`. No `timedelta` re-import (uses module-level line 1).
- **`dashboard/app.py`**:
  - Line 20 import: added `fetch_revenue_actual_summary`.
  - After `fetch_kpi_summary` try/except: added `try/except Exception` fetching `actual_revenue, prior_actual_revenue`, falling back to `None, None`.
  - Revenue tile call (line ~85): `kpi_card("Revenue", fmt_vnd(actual_revenue), actual_revenue, prior_actual_revenue)` — `badge` kwarg omitted (defaults None → no EST badge).

ADR, RevPAR, Occupancy tiles untouched (all retain `badge=True`).

## What Was Skipped or Deferred

- AC-6 automated fallback test — Known-Gap per validate-contract (dashboard has no pytest suite). Structural graceful-degradation verified by code review: `try/except` at correct scope.

## Test Gate Outcomes

| Gate | Strategy | Result |
|---|---|---|
| `grep -n "fetch_revenue_actual_summary" dashboard/app.py` (≥2 lines) | Fully-Automated | PASS (lines 20, 78) |
| `grep 'kpi_card("Revenue"' ... \| grep -c 'badge=True'` == 0 | Fully-Automated | PASS (0) |
| `cd extractor && poetry run pytest tests/ -v` | Fully-Automated | PASS (32/32) |
| `python -m py_compile app.py data/repository.py` | Fully-Automated | PASS (SYNTAX OK) |
| AC-1 Revenue tile ~₫8.24B for 90-day window | Agent-Probe | NOT RUN — requires running dashboard + live DB (EVL/orchestrator responsibility) |
| AC-3 prior-period delta renders | Agent-Probe | NOT RUN — same |
| AC-4 other tiles unchanged | Agent-Probe | NOT RUN — same (static review: untouched) |

## Plan Deviations

None. Implementation matches plan 1:1.

## Test Infra Gaps Found

- Dashboard has no pytest suite — new Streamlit functions (`_fetch_revenue_actual_scalar`, `fetch_revenue_actual_summary`) have no unit coverage. Carried Known-Gap from Phase 5 closeout; not introduced by this plan.

## Closeout Packet

- **Selected plan:** `process/features/financials/active/financials_17-07-26/dashboard-kpi-revenue-actual_PLAN_19-07-26.md`
- **Finished:** all 6 checklist steps; all Fully-Automated gates green.
- **Verified:** grep gates, extractor regression (32/32), Python syntax.
- **Unverified:** 3 Agent-Probe visual gates (AC-1/AC-3/AC-4) — need a running dashboard against live DB.
- **Follow-up stubs created:** none.
- **Best next state:** Keep in active/testing until Agent-Probe visual verification confirms the ₫8.24B figure; then Ready for UPDATE PROCESS archival.

## Forward Preview

### Test Infra Found
Dashboard has no automated test harness — visual/agent-probe only for UI behavior.

### Blast Radius Changes
2 files, additive. `repository.py` existing functions untouched; `app.py` Revenue tile only.

### Commands to Stay Green
- `cd extractor && poetry run pytest tests/ -v`
- `grep 'kpi_card("Revenue"' dashboard/app.py | grep -c 'badge=True'` → 0

### Dependency Changes
None. No new imports/packages.
