---
name: plan:financials-postings-phase-05-dashboard-revenue-actual
description: "Cashiering postings pipeline — Phase 5: dashboard wiring to revenue_actual"
date: 17-07-26
metadata:
  node_type: memory
  type: plan
  feature: financials
  phase: phase-05
---

# Phase 05 — Dashboard Wiring

**Program:** financials-postings
**Umbrella plan:** process/features/financials/active/financials_17-07-26/financials-postings-umbrella_PLAN_17-07-26.md
**Phase status:** PLANNED
**Report destination:** process/features/financials/active/financials_17-07-26/phase-05-dashboard-revenue-actual_REPORT_{dd-mm-yy}.md (flat in the program task folder)

---

## Purpose

Switch `dashboard/app.py`'s revenue calculations from the estimated `night_amount` proxy to the
new real `revenue_actual` column, remove the "(estimated)" label, and add a category breakdown
chart (Room/F&B/Tax/ServiceCharge) to the Revenue tab. This is the final, user-facing phase — the
entire program's value is only realized once this phase lands.

---

## Entry Gate

- Phase 4 exit gate passed: additive columns present on `fct_reservation_night`, verified
  unchanged existing columns, voucher-stay test passing

---

## Blast Radius

- `dashboard/app.py` (modified — category breakdown chart added to Revenue tab, "(estimated)" labels removed)
- `dashboard/data/repository.py` (modified — REVENUE_BREAKDOWN_SQL and fetch_kpi_daily_segmented updated from night_amount to revenue_actual)
- `eras_dbt/models/marts/kpi_daily_snapshot.sql` (modified — total_revenue/adr/revpar CTEs switched from night_amount to revenue_actual; night_amount column preserved for backward compatibility)
- `eras_dbt/models/marts/kpi_pickup.sql` (review — determine whether pickup_revenue should switch to revenue_actual; document decision; forward-looking metric may stay on night_amount as known-gap)

**Note added by PVL (outer-pvl, 2026-07-17):** original blast radius listed only `dashboard/app.py`. Expanded to include `dashboard/data/repository.py`, `eras_dbt/models/marts/kpi_daily_snapshot.sql`, and `eras_dbt/models/marts/kpi_pickup.sql` because `night_amount` is NOT referenced in `app.py` directly — the actual revenue SQL is in `data/repository.py` and the mart models. Execute-agent must read these files first, not just `app.py`.

---

## Implementation Checklist

### Step A — Scout every night_amount usage (MUST-HAVE from INNOVATE risk flag)

- [ ] A1. Read `dashboard/app.py`, `dashboard/data/repository.py`, `eras_dbt/models/marts/kpi_daily_snapshot.sql`, `eras_dbt/models/marts/kpi_pickup.sql`, and `eras_dbt/models/marts/kpi_pacing.sql` in full. Enumerate EVERY place reading `night_amount` for revenue calculations. IMPORTANT: `app.py` does NOT directly reference `night_amount` — the actual SQL is in `data/repository.py` (REVENUE_BREAKDOWN_SQL uses `sum(night_amount) as revenue`; `fetch_kpi_daily_segmented` uses `sum(night_amount) as total_revenue`) and in `kpi_daily_snapshot.sql` (sum/adr/revpar CTEs). Do NOT stop at `app.py` alone — the scout must read the data layer and mart models.
- [ ] A2. For each usage found, note whether it's a direct sum, an average, a per-segment
      breakdown, or a pacing/time-series calculation — the swap-in of `revenue_actual` may need
      different handling per usage type (e.g. pacing calculations may need date-range awareness
      that a simple aggregate does not).

### Step B — Switch revenue source

- [ ] B1. Revenue tab: the revenue source for the Revenue tab flows through `kpi_daily_snapshot.total_revenue` (read via `fetch_kpi_daily()` in `data/repository.py`). Update `eras_dbt/models/marts/kpi_daily_snapshot.sql` to replace `sum(f.night_amount)` with `sum(f.revenue_actual)` for total_revenue, and update adr/revpar formulas accordingly.
- [ ] B2. Trends tab: reads the same `kpi_daily_snapshot.total_revenue` — covered by the B1 mart update.
- [ ] B3. Pacing tab: reads from `analytics.kpi_pacing` which sources from `kpi_daily_snapshot` — covered by the B1 mart update (no direct change to kpi_pacing.sql needed).
- [ ] B4. Segments tab: `fetch_kpi_daily_segmented()` in `data/repository.py` runs raw SQL with `sum(night_amount) as total_revenue` — update to `sum(revenue_actual)` if AC-6 scope includes segments; if segments are intentionally excluded from the revenue_actual switch, document as a known-gap.
- [ ] B5. Remove any "(estimated)" label/caption/tooltip text found during Step A1's scout.
- [ ] B6. Update `dashboard/data/repository.py` `REVENUE_BREAKDOWN_SQL`: replace `sum(night_amount) as revenue` with `sum(revenue_actual) as revenue` in the `fct_reservation_night` query (this powers the Revenue tab's Market/Rate/Room-Type breakdown charts).
- [ ] B7. Decide on `kpi_pickup.sql` revenue field: if pickup revenue should show actual postings, update `sum(night_amount)` to `sum(revenue_actual)` in kpi_pickup.sql; if pickup is kept as estimated (acceptable since forward-looking dates may have no postings), document the decision in the phase report.
- [ ] B8. Confirm `night_amount` is preserved as a column in `kpi_daily_snapshot.sql` (not dropped) for backward compatibility — only the total_revenue/adr/revpar aggregations switch to revenue_actual.

### Step C — Category breakdown chart (AC-7)

- [ ] C1. Add a new chart to the Revenue tab breaking down revenue by category
      (Room/F&B/Tax/ServiceCharge) using `revenue_room`/`revenue_fnb`/`revenue_tax`/`revenue_svc`
      columns from Phase 4 — follow the existing chart library/style already used elsewhere in
      `app.py` (confirm which charting library — likely Plotly or Streamlit-native — during
      research, do not introduce a new one). The chart data query may need a new or extended
      SQL in `data/repository.py` that returns the category columns.

### Step D — Spot-check verification (program-level definition of done)

- [ ] D1. Pick one real reservation from the backfilled date range with known folio activity
      (e.g. one of the empirically-verified reservations 18577414/18156668 from earlier phase
      research, if within a date range that has both room + F&B/tax/service charges).
- [ ] D2. Manually confirm the dashboard's displayed `revenue_actual` for that reservation/night
      matches the sum of its actual OPERA folio postings — this is the program's stated
      definition-of-done check ("dashboard shows real revenue matching folio data for a
      spot-checked reservation").

---

## Exit Gate

```bash
cd dashboard && python -c "import app"  # or the project's actual dashboard smoke-test command — confirm during research
# Expected: no import/syntax errors

# Manual/agent-probe verification
# Launch dashboard, navigate to Revenue/Trends/Pacing (+Segments if in scope), confirm revenue_actual
# displays, "(estimated)" label is gone, category breakdown chart renders on Revenue tab
```

- All checklist items (A-D) checked
- Dashboard renders `revenue_actual` across all confirmed tabs with no "(estimated)" label
  remaining
- Category breakdown chart present on Revenue tab
- Spot-check reservation confirms dashboard revenue matches real OPERA folio total
- Phase report written to report destination above

---

## Blockers That Would Justify BLOCKED Status

- Segments tab usage of `night_amount` is ambiguous even after Step A1's scout (mixed usage,
  partially revenue-related) — may require a scoped follow-up decision rather than blocking the
  whole phase; document as a known-gap if genuinely ambiguous.
- Spot-check reservation's dashboard revenue does NOT match its OPERA folio total — this is a
  program-level definition-of-done failure and must route back to Phase 3/4 as a regression, not
  be patched superficially in the dashboard layer.

---

## Phase Loop Progress

Orchestrator reads this before deciding which subagent to spawn next. The canonical 7-step inner loop
`R -> I -> P -> PVL -> E -> EVL -> UP` SKIPS SPEC (SPEC runs once in the outer program loop, already locked).

- [ ] 1. RESEARCH — research-agent: prior phase reports read; test context loaded; plan drift checked
- [ ] 2. INNOVATE — innovate-agent: approach decided; Decision Summary written
- [ ] 3. PLAN-SUPPLEMENT — plan-agent: existing phase plan updated; Inner Loop Refresh Note if sections changed (or "n/a — research clean")
- [ ] 4. PVL — vc-validate-agent: full V1-V7; validate-contract written per `.claude/skills/vc-validate-findings/references/example-validate-output.md` (Status / Gate / Plan updates applied / Execute-agent instructions / Test gates / High-risk pack / Backlog artifacts / Known gaps / Accepted by)
- [ ] 5. EXECUTE — all checklist items done; per-section test gates run and green (or gaps documented)
- [ ] 6. EVL — all EVL gates green; follow-up stubs registered; EVL HANDOFF SUMMARY written
- [ ] 7. UPDATE PROCESS — phase report written, umbrella state updated, commit done

**Validate-contract required before execute.** If step 4 (PVL) is unchecked or `## Validate Contract`
reads "(placeholder — vc-validate-agent writes this section before EXECUTE)", orchestrator must
spawn vc-validate-agent first. A partial contract missing Plan updates applied / Execute-agent
instructions / Test gates sections is treated as a placeholder.

---

## Touchpoints

- `dashboard/app.py` (modified — category breakdown chart, remove "(estimated)" labels)
- `dashboard/data/repository.py` (modified — REVENUE_BREAKDOWN_SQL and fetch_kpi_daily_segmented: night_amount → revenue_actual)
- `eras_dbt/models/marts/kpi_daily_snapshot.sql` (modified — total_revenue/adr/revpar: night_amount → revenue_actual)
- `eras_dbt/models/marts/kpi_pickup.sql` (review — pickup_revenue field decision)

---

## Public Contracts

- Dashboard revenue display is a user-visible behavior change (estimated -> actual) — intentional
  and communicated via the "(estimated)" label removal per AC-7.
- `kpi_daily_snapshot.total_revenue` switches from `sum(night_amount)` to `sum(revenue_actual)` — intentional change to all downstream consumers (Pacing tab reads `current_revenue` from kpi_pacing which derives from kpi_daily_snapshot).
- `night_amount` column preserved in `kpi_daily_snapshot` for backward compatibility.

---

## Verification Evidence

| Gate / Scenario | Strategy | Proves SPEC criterion |
|---|---|---|
| Dashboard smoke test (imports/renders without error) | Fully-Automated | Baseline regression safety |
| Every night_amount usage in repository.py/kpi_daily_snapshot.sql enumerated and swapped or explicitly excluded | Agent-Probe | AC-7 (revenue source switch, complete coverage not partial) |
| Category breakdown chart renders with 4 categories on Revenue tab | Agent-Probe | AC-7 (category breakdown requirement) |
| Spot-check: dashboard revenue_actual for a real reservation matches OPERA folio total | Agent-Probe | Program-level definition of done |

```bash
cd dashboard && python -c "import app"
# Expected: no errors (adjust command per actual project convention discovered during research)
```

---

## Resume and Execution Handoff

- Selected plan file path: `process/features/financials/active/financials_17-07-26/phase-05-dashboard-revenue-actual_PLAN_17-07-26.md`
- Last completed step: not started
- Validate-contract status: pending
- Next step: Spawn vc-research-agent for RESEARCH (Step 1)

---

## Test Infra Improvement Notes

(none identified yet)

---

## Validate Contract

Status: CONDITIONAL
Date: 17-07-26
date: 2026-07-17
generated-by: outer-pvl

Parallel strategy: sequential
Rationale: 2/7 signals present (S4 phase-program, S6 high-risk class in Phase 4); Phase 5 itself is a consumer-only phase; sequential is the correct strategy for the strictly-ordered program execution

Plan updates applied:
- P1: Added dashboard/data/repository.py, eras_dbt/models/marts/kpi_daily_snapshot.sql, eras_dbt/models/marts/kpi_pickup.sql to Blast Radius (missing files found by Layer 2 infra check — night_amount is in these files, NOT in app.py)
- P2: Updated Step A1 to explicitly scout data/repository.py and mart models (app.py has no direct night_amount references)
- P3: Added Steps B6-B8 with specific file targets for the repository.py and kpi_daily_snapshot.sql changes
- P4: Updated Touchpoints section to match expanded blast radius

Execute-agent instructions:
- E1 (CRITICAL): Read `dashboard/data/repository.py` BEFORE reading `dashboard/app.py` — the revenue SQL is in repository.py (REVENUE_BREAKDOWN_SQL line 71, fetch_kpi_daily_segmented line 103). `app.py` does not reference `night_amount` directly.
- E2: `kpi_daily_snapshot.sql` is the primary target for Revenue/Trends/Pacing tab switch. Update the `sum(f.night_amount)` in the `operational` CTE (lines 20, 24-25, 27 of kpi_daily_snapshot.sql) to `sum(f.revenue_actual)` — but keep `night_amount` as a separate column if needed for backward compatibility.
- E3: `REVENUE_BREAKDOWN_SQL` in repository.py (line 75: `sum(night_amount) as revenue`) — change to `sum(revenue_actual) as revenue`.
- E4: `fetch_kpi_daily_segmented()` in repository.py (line 105: `sum(night_amount) as total_revenue`) — change to `sum(revenue_actual) as total_revenue` if segments are in AC-6 scope.
- E5: `kpi_pickup.sql` decision — forward-looking reservations will have revenue_actual = NULL (no postings yet); keeping pickup on `night_amount` is acceptable and preferable; document in phase report as a named known-gap.
- E6: Category breakdown chart (Step C1): use Altair (already in use across all tabs — confirmed from ui/tabs/revenue.py imports); add a stacked bar chart with `revenue_room`, `revenue_fnb`, `revenue_tax`, `revenue_svc` from a new SQL query joining fct_reservation_night directly.
- E7: Pacing tab: no direct change needed — kpi_pacing.sql reads from kpi_daily_snapshot; once kpi_daily_snapshot.sql is updated (E2), pacing revenue will automatically reflect actual postings.

Test gates (C3 5-column table):

| criterion id | behavior | strategy | proving test | gap-resolution |
|---|---|---|---|---|
| P5-import | Dashboard app imports without error after changes | Fully-Automated | `cd dashboard && python -c "import app"` exits 0 | A |
| AC-6-KPIs | Revenue/ADR/RevPAR source from revenue_actual in kpi_daily_snapshot | Agent-Probe | Launch dashboard; view Revenue tab for a date range with known postings; confirm total_revenue differs from prior estimated value and matches posting sum | D |
| AC-7-chart | Category breakdown chart present with Room/FnB/Tax/ServiceCharge categories | Agent-Probe | View Revenue tab; confirm 4-category chart renders; category totals sum to headline Revenue KPI (within rounding) | D |
| AC-7-label | "(estimated)" label removed from all confirmed revenue displays | Agent-Probe | Grep `dashboard/` for "(estimated)" after changes; confirm 0 occurrences | D |
| SPOT-CHECK | Dashboard revenue_actual for a known reservation matches OPERA folio total | Agent-Probe | Select reservation 18577414 or 18156668; compare dashboard Revenue for its stay dates against OPERA folio total | D |

Failing stub (Fully-Automated tier — P5-import):
test("should import dashboard app without errors after revenue_actual wiring", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: cd dashboard && python -c 'import app' exits 0")
})

gap-resolution legend:
- A — proven now (gate passes in this cycle)
- B — fixed in this plan (gate added by this plan's checklist)
- C — deferred to a named later phase/plan
- D — backlog test-building stub (named residual; keep-active; continue)

Legacy line form:
- dashboard/app.py: Fully-automated: `cd dashboard && python -c "import app"` exits 0
- Revenue KPIs (kpi_daily_snapshot → repository.py → dashboard): agent-probe: launch dashboard, compare revenue to known posting sum
- Category breakdown chart: agent-probe: visual confirmation on Revenue tab
- Spot-check: agent-probe: compare dashboard vs OPERA folio for known reservation

Dimension findings:
- Infra fit: CONCERN — blast radius was incomplete; dashboard revenue chain goes through data/repository.py and eras_dbt/models/marts/kpi_daily_snapshot.sql (both added to blast radius by PVL P1-P4 plan fixes above)
- Test coverage: CONCERN — only smoke test (import check) is fully automated; all revenue-correctness gates are Agent-Probe (no automated assertion against known posting values in CI)
- Breaking changes: CONCERN — kpi_daily_snapshot.sql change intentionally alters total_revenue/adr/revpar for ALL dashboard consumers simultaneously; night_amount column preserved; kpi_pickup.sql pickup_revenue decision is a named known-gap
- Security surface: PASS — no auth/identity/billing/secrets changes; purely a SQL source-column swap

Open gaps:
- kpi_pickup.sql: known-gap: documented — pickup revenue kept on night_amount (forward-looking reservations have no postings; revenue_actual = NULL for future dates). Document in phase report.
- Segments tab revenue scope: known-gap: documented — decision on whether fetch_kpi_daily_segmented should use revenue_actual deferred to Phase 5 RESEARCH (the Segments tab may appropriately stay on night_amount if it shows room-night-based segmentation not total revenue)
- No automated CI gate for revenue-correctness comparison: known-gap: documented as NEW PLAN REQUIRED for a future automated KPI verification plan

What this coverage does NOT prove:
- P5-import: Does not prove revenue values are numerically correct after source switch — only that the app starts
- AC-6-KPIs: Does not verify against an independent OPERA revenue report (spot-check is analyst-manual, not automated)
- AC-7-chart: Does not assert category totals mathematically — visual confirmation only
- SPOT-CHECK: Not automated; depends on analyst selecting an appropriate reservation with verified folio

Gate: CONDITIONAL
Accepted by: session (autonomous, /goal execution) — concerns: blast-radius expansion applied as plan fix (P1-P4); kpi_pickup.sql pickup revenue kept on night_amount as named known-gap; Segments tab revenue scope decision deferred to RESEARCH; no automated revenue-correctness CI gate (backlog)
