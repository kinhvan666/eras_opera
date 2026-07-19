---
name: plan:dashboard-kpi-revenue-actual
description: Replace estimated revenue (night_amount) with actual revenue from fct_folio_line in the Revenue KPI tile
date: 19-07-26
feature: financials
phase: "simple"
---

# Dashboard KPI Revenue Actual — Plan

Complexity: SIMPLE
Date: 19-07-26
Status: ⏳ PLANNED
**Feature:** financials

Context loaded from `process/context/all-context.md`. Test context: `process/context/tests/all-tests.md`.

## Overview

The Revenue KPI tile on the dashboard homepage shows estimated revenue from `kpi_daily_snapshot` (night_amount-based). Actual revenue from `fct_folio_line` is ~2.4x larger (₫8.24B actual vs ₫3.41B estimated over 90 days). This plan replaces the estimated figure with actual posted revenue and removes the "EST" badge.

## Goals

- Revenue KPI tile displays actual posted revenue (excluding Tax) from `analytics.fct_folio_line`
- Prior-period comparison uses the same shift logic (7-day for ≤14-day range, else 30-day)
- "EST" badge is removed from the Revenue tile
- ADR, RevPAR, and Occupancy tiles are untouched

## Scope

**In scope:** Revenue KPI tile only — `dashboard/data/repository.py` + `dashboard/app.py`

**Out of scope:** dbt models, extractor, database schema, other KPI tiles

## Touchpoints

- `dashboard/data/repository.py` — add SQL constant + 2 new functions (~20 lines after line 134)
- `dashboard/app.py` — 1 import change, 4 lines added, 1 KPI tile call changed

## Public Contracts

- New public function: `fetch_revenue_actual_summary(start_date, end_date, hotel_id=None) -> (float, float)` — returns `(current_rev, prior_rev)` scalars
- Private helper: `_fetch_revenue_actual_scalar(start_date, end_date, hotel_id=None)` — cached DB query
- SQL filter: `revenue_category != 'Tax'` — excludes tax postings from revenue total
- Shift logic: 7-day for date ranges ≤14 days, 30-day otherwise (identical to `fetch_kpi_summary`)

## Blast Radius

- **Files changed:** 2
- **Risk class:** LOW — no schema changes, no new dependencies, no auth/API/billing surface
- `dashboard/data/repository.py` — additive only; existing functions untouched
- `dashboard/app.py` — 1 import + 4 lines + 1 modified call; no structural change

## Implementation Checklist

1. **[repository.py] Add SQL constant** after the existing `REVENUE_ACTUAL_SQL` block (after line 134):
   - Constant name: `REVENUE_ACTUAL_KPI_SQL`
   - Query: `SELECT SUM(posted_amount) AS revenue FROM analytics.fct_folio_line WHERE revenue_date BETWEEN %(start_date)s AND %(end_date)s AND (%(hotel_id)s::text IS NULL OR hotel_id = %(hotel_id)s) AND revenue_category != 'Tax'`

2. **[repository.py] Add private cached helper** `_fetch_revenue_actual_scalar(start_date, end_date, hotel_id=None)` immediately after the SQL constant:
   - Decorated with `@st.cache_data(ttl=CACHE_TTL_SECONDS)`
   - Opens connection via `psycopg2.connect(DATABASE_URL)`
   - Runs `REVENUE_ACTUAL_KPI_SQL` with params dict
   - Returns `df["revenue"].iloc[0] if not df.empty else 0.0`

3. **[repository.py] Add public function** `fetch_revenue_actual_summary(start_date, end_date, hotel_id=None)` after the helper:
   - Docstring: "Actual revenue KPI (excl. Tax) for current and prior period. Same shift logic as fetch_kpi_summary."
   - Do NOT import `timedelta` inside the function — it is already imported at module level (line 1)
   - Computes `range_days`, `shift`, calls `_fetch_revenue_actual_scalar` for both current and prior windows
   - Returns `(current_rev, prior_rev)`

4. **[app.py] Update import** on line 20:
   - Add `fetch_revenue_actual_summary` to the existing `from data.repository import ...` line

5. **[app.py] Fetch actual revenue** after line 75 (after `current, prior = fetch_kpi_summary(...)`):
   - Wrap in `try/except Exception` to degrade gracefully if DB unavailable
   - On exception: set `actual_revenue, prior_actual_revenue = None, None`

6. **[app.py] Replace KPI tile call** for Revenue (currently line 85):
   - Old: `kpi_card("Revenue", fmt_vnd(current['total_revenue']), current["total_revenue"], g(prior, "total_revenue"), badge=True)`
   - New: `kpi_card("Revenue", fmt_vnd(actual_revenue), actual_revenue, prior_actual_revenue)`
   - Omit `badge=True` → defaults to `None` → no EST badge rendered

## Acceptance Criteria

- AC-1: Revenue KPI tile shows ~₫8.24B (actual) for the 90-day window, not ~₫3.41B (estimated)
- AC-2: No "EST" badge appears on the Revenue tile
- AC-3: Prior-period delta arrow/percentage renders correctly (not None/error)
- AC-4: Occupancy, ADR, and RevPAR tiles are unchanged
- AC-5: Dashboard loads without error when `fct_folio_line` is accessible
- AC-6: Dashboard degrades gracefully (no crash) if `fetch_revenue_actual_summary` raises

## Phase Completion Rules

This is a SIMPLE (one-session) plan. No phase gates or approval checkpoints between steps.

- Implement checklist steps 1–6 continuously in a single EXECUTE session
- Run verification gates after all steps are complete (do not interleave)
- Status transitions: ⏳ PLANNED → 🚧 IN PROGRESS (on EXECUTE start) → ✅ VERIFIED (after all gates green)
- Phase is VERIFIED only when: grep gates pass AND visual agent-probe confirms actual revenue figure

## Verification Evidence

<!-- P1 fix applied by vc-validate-agent (19-07-26): badge grep scoped to Revenue tile only; original grep -c "badge=True" would return 3 (Occupancy/ADR/RevPAR retain badge=True) -->

| Gate / Scenario | Strategy | Proves SPEC criterion |
|---|---|---|
| Dashboard loads, Revenue tile shows actual figure (~₫8.24B for 90-day window) | Agent-Probe (visual check in running dashboard) | AC-1, AC-2 |
| Other KPI tiles (Occupancy, ADR, RevPAR) are unchanged | Agent-Probe (visual check) | AC-4 |
| Prior-period comparison renders (percentage delta shown, not error) | Agent-Probe | AC-3 |
| `cd extractor && poetry run pytest tests/ -v` passes — no regressions | Fully-Automated | AC-5, AC-6 |
| `grep -n "fetch_revenue_actual_summary" dashboard/app.py` shows import and call | Fully-Automated (grep) | AC-1 |
| `grep 'kpi_card("Revenue"' dashboard/app.py \| grep -c 'badge=True'` count is 0 (badge removed from Revenue tile only; other tiles retain badge=True) | Fully-Automated (grep) | AC-2 |

## Dependencies

- `analytics.fct_folio_line` table must be populated (confirmed: 18,245 postings in place from Phase 1–3 financials work)
- `psycopg2`, `pandas`, `streamlit` already imported in `repository.py` — no new dependencies
- `timedelta` already imported at top of `repository.py` (line 1) — do NOT re-import inside function

## Risks

- **None identified** — additive read-only change against an existing populated table. No schema change, no new dependency, no auth surface.
- Graceful fallback (`try/except`) ensures dashboard does not crash if query fails.

## Test Infra Improvement Notes

(none identified yet)

## Resume and Execution Handoff

1. **Selected plan file path:** `process/features/financials/active/financials_17-07-26/dashboard-kpi-revenue-actual_PLAN_19-07-26.md`
2. **Last completed phase or step:** PLAN — not started
3. **Validate-contract status:** written (19-07-26) — Gate: CONDITIONAL
4. **Supporting context files loaded:** `process/context/all-context.md`, research findings from scout
5. **Next step for a fresh agent:** Read this plan and the validate-contract below. Implement checklist steps 1–6 in order. Run grep gates after implementation to confirm. Start dashboard and visually verify Revenue tile value.

## Validate Contract

Status: CONDITIONAL
Date: 19-07-26
date: 2026-07-19
generated-by: inner-pvl: plan-a

Parallel strategy: sequential
Rationale: 0/7 signals (2 files, additive-only, no fan-out needed) — single sequential agent appropriate.

Test gates (C3 5-column table — ADDITIVE; existing consumers still parse the legacy line form below it):

| criterion id | behavior | strategy | proving test | gap-resolution |
|---|---|---|---|---|
| AC-1 | Revenue KPI tile shows actual revenue (~₫8.24B for 90-day window) | Agent-Probe | Start dashboard; set 90-day date range (today–90d to today); verify Revenue tile shows ~₫8.24B not ~₫3.41B | A |
| AC-2-import | fetch_revenue_actual_summary imported and called in app.py | Fully-Automated | `grep -n "fetch_revenue_actual_summary" dashboard/app.py` exits 0 and shows ≥2 lines (import + call) | A |
| AC-2-badge | EST badge absent from Revenue tile (badge=True removed from Revenue kpi_card call) | Fully-Automated | `grep 'kpi_card("Revenue"' dashboard/app.py \| grep -c 'badge=True'` returns 0 | A |
| AC-3 | Prior-period delta renders correctly (arrow and percentage shown) | Agent-Probe | Verify Revenue tile shows percentage delta arrow, not None or error; prior_actual_revenue computed via 7-day or 30-day shift | A |
| AC-4 | Occupancy, ADR, RevPAR tiles unchanged | Agent-Probe | Verify other 3 KPI tiles show correct values and retain badge=True (EST badge present); data is unchanged from pre-plan state | A |
| AC-5 | Extractor pytest suite unaffected | Fully-Automated | `cd extractor && poetry run pytest tests/ -v` exits 0 (32/32) | A |
| AC-6 | Dashboard degrades gracefully if fetch_revenue_actual_summary raises | Known-Gap | try/except block verified by code review (correct location after line 75); no automated fallback test | D |

Failing stub (AC-2-import):
test("should find fetch_revenue_actual_summary imported and called in dashboard/app.py", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: grep -n fetch_revenue_actual_summary dashboard/app.py shows >=2 lines")
})

Failing stub (AC-2-badge):
test("should have no badge=True on Revenue kpi_card call in dashboard/app.py", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: grep 'kpi_card(Revenue)' dashboard/app.py | grep -c 'badge=True' returns 0")
})

Failing stub (AC-5):
test("should pass extractor pytest suite with no regressions after dashboard changes", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: cd extractor && poetry run pytest tests/ -v exits 0 (32/32)")
})

gap-resolution legend:
- A — proven now (gate passes in this cycle)
- B — fixed in this plan (gate added by this plan's checklist)
- C — deferred to a named later phase/plan
- D — backlog test-building stub (named residual; keep-active; continue)

C-4 reconciliation: the `strategy:` column carries ONLY the 3 proving strategies (Fully-Automated / Hybrid / Agent-Probe). Known-Gap is NEVER a `strategy:` value — it is a named residual row carried via gap-resolution D, never a strategy that proves a behavior.

Legacy line form (retained so existing validate-contract consumers still parse):
- repository.py new functions: Fully-automated: `grep -n "fetch_revenue_actual_summary" dashboard/data/repository.py` exits 0
- app.py import+call: Fully-automated: `grep -n "fetch_revenue_actual_summary" dashboard/app.py` shows >=2 lines
- badge removal: Fully-automated: `grep 'kpi_card("Revenue"' dashboard/app.py | grep -c 'badge=True'` returns 0
- extractor regression: Fully-automated: `cd extractor && poetry run pytest tests/ -v` exits 0 (32/32)
- Revenue tile actual value: agent-probe: visual check — Revenue tile shows ~₫8.24B for 90-day range, not ~₫3.41B
- dashboard unit tests: known-gap: documented — dashboard has no pytest suite (structural gap per all-tests.md)

Dimension findings:
- Infra fit: PASS — no infra changes; all deps already imported in repository.py (timedelta line 1, psycopg2 line 4, streamlit line 5, CACHE_TTL_SECONDS/DATABASE_URL line 7); analytics.fct_folio_line confirmed populated (18,245 rows, ₫8.24B excl Tax per Phase 3 verification); DB connection pattern identical to existing functions
- Test coverage: CONCERN — no unit tests for new dashboard functions (_fetch_revenue_actual_scalar, fetch_revenue_actual_summary); shift-calculation logic tested only via agent-probe; extractor pytest covers extractor not dashboard; badge grep corrected via P1 plan update (original grep -c "badge=True" would return 3 not 0)
- Breaking changes: PASS — additive only; no existing repository.py functions modified; kpi_card() handles None for current/prior per components.py line 5 (`if prior is None or current is None or prior == 0: return ""`); other KPI tiles untouched
- Security surface: PASS — read-only SELECT query on analytics.fct_folio_line; no auth/billing/secret surface; no new external dependencies; DB connection pattern unchanged

Open gaps:
- Dashboard unit test suite: no pytest coverage for new Streamlit functions (known-gap: documented — dashboard has no test infra; structural gap carried from Phase 5 program closeout)
- AC-6 graceful fallback: verified structurally by code review (try/except at correct scope); no automated assertion for the fallback path

What this coverage does NOT prove:
- AC-2-import grep: does not prove fetch_revenue_actual_summary returns correct computed values; does not prove DB query returns correct results at runtime; does not prove shift logic (7-day vs 30-day cutoff) is arithmetically correct
- AC-2-badge grep: does not prove badge is absent at HTML render time; does not assert that the change was applied to the correct line (only that no Revenue kpi_card call has badge=True)
- AC-5 pytest: does not exercise any dashboard code; proves only that extractor tests remain green (no regression from file imports or module-level side effects)
- Agent-probe scenarios (AC-1, AC-3, AC-4): visual judgment only; no programmatic assertion of exact revenue figure; relies on live DB being accessible during verification

Gate: CONDITIONAL (AC-6 fallback accepted as known-gap; test coverage CONCERN accepted; P1 badge-grep fix applied before this contract was written)
Accepted by: session (autonomous, /goal execution) — concerns: (1) no dashboard unit tests for new functions [known-gap: documented; dashboard has no test infra]; (2) badge grep corrected via P1 plan update

## Autonomous Goal Block

SESSION GOAL: Revenue KPI tile — replace estimated night_amount with actual revenue from fct_folio_line
Charter + umbrella plan: N/A — standalone follow-up plan (umbrella financials-postings-umbrella_PLAN_17-07-26.md is PROGRAM COMPLETE; this plan is not in the original phase sequence)
Autonomy: auto-proceed on all reversible decisions; no approval gates between checklist steps 1-6; surface only hard stops
Hard stop conditions / safety constraints:
- Do NOT modify dbt models, extractor code, or database schema (explicitly out of scope)
- Do NOT remove badge=True from Occupancy, ADR, or RevPAR tiles (AC-4 — those tiles must stay unchanged)
- Do NOT import timedelta inside the new function body (already imported at module level line 1)
- Hard stop if making any outward-facing change not covered by this validate-contract
Next phase: EXECUTE: process/features/financials/active/financials_17-07-26/dashboard-kpi-revenue-actual_PLAN_19-07-26.md
Validate contract: inline in plan (## Validate Contract section above, Gate: CONDITIONAL)
Execute start: grep -n "fetch_revenue_actual_summary" dashboard/app.py | grep 'kpi_card("Revenue"' dashboard/app.py | grep -c 'badge=True' | cd extractor && poetry run pytest tests/ -v | Agent-Probe: Revenue tile ~8.24B VND for 90-day range | high-risk pack: no
