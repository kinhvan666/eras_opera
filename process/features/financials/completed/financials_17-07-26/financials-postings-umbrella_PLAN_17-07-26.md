---
name: plan:financials-postings-umbrella
description: "Cashiering postings pipeline — umbrella/orchestration plan for the 5-phase program (extractor -> staging -> fct_folio_line -> fct_reservation_night additive columns -> dashboard)"
date: 17-07-26
metadata:
  node_type: memory
  type: plan
  feature: financials
  phase: umbrella
---

# Cashiering Postings Pipeline — Umbrella Plan

**Date:** 17-07-26
**Complexity:** COMPLEX
**Status:** PLANNED

- Program type: PHASE PROGRAM (5 phases, strictly sequential — each phase's output is the next phase's input)
- SPEC (locked): `process/features/financials/active/financials_17-07-26/financials_SPEC_17-07-26.md` (10 ACs)
- Feature folder: `process/features/financials/`

---

## Program Goal Charter

```
Cashiering Postings Pipeline — Program Goal Charter

North star:
- Replace the dashboard's estimated night_amount revenue proxy with real OPERA Cloud
  cashiering posting data, split by revenue category (Room / F&B / Tax / ServiceCharge), so
  hotel management sees actual recognized revenue instead of an estimate.

Definition of done (an unattended agent must be able to do all of these):
1. Extract raw cashiering postings from OPERA Cloud /financialPostings (7-day windows,
   backfill 2026-01-01 -> today) into raw.cashiering_postings, upserted on transaction_no.
2. Build stg_cashiering_postings (Revenue-type only, 9xxx/Wrapper excluded, revenue_category
   derived from transaction_code prefix) and fct_folio_line (grain = 1 row per transaction_no).
3. Add additive revenue_actual/revenue_room/revenue_fnb/revenue_tax/revenue_svc columns onto
   fct_reservation_night without touching any existing column (esp. night_amount).
4. Show real revenue_actual (with category breakdown) in the dashboard Revenue/Trends/Pacing
   tabs, replacing the "(estimated)" label.

What "verified" means (program level):
- All 10 SPEC ACs individually mapped to a passing gate (dbt test, pytest, or agent-probe
  spot-check against a real reservation's folio).
- A spot-checked reservation shows dashboard revenue_actual matching its OPERA folio total.
- validate-contract gates must be recorded alongside phase gates and regression evidence for a
  phase to reach VERIFIED. A phase without a validate-contract (or documented skip reason)
  cannot be marked VERIFIED.

Scope tiers -> phase mapping:
- Tier 1 Extraction (raw layer) -> Phase 1
- Tier 2 Staging + category derivation -> Phase 2
- Tier 3 Fact grain (fct_folio_line) -> Phase 3
- Tier 4 Additive rollup onto fct_reservation_night -> Phase 4
- Tier 5 Dashboard consumption -> Phase 5
- This program retires the "(estimated)" revenue proxy tier entirely.

Explicitly out of scope (deferred tier):
- adults/children extraction from cashiering data
- lastModifiedDate incremental extraction strategy (this program is full-window backfill only)
- timezone precision beyond date-level (revenue_date, not revenue_datetime)
- POS-vs-Night-Audit cashierID (998/999) split in the dashboard — provenance columns are
  carried through staging/fact for future use but no dashboard split is built this program
- multi-currency handling (VND only, per locked SPEC)
- /transactionCodes lookup API — category derivation stays prefix-based only

Hard safety constraints (non-negotiable, per phase):
- All new dbt models/columns are ADDITIVE ONLY. fct_reservation_night's existing columns
  (especially night_amount) must remain byte-for-byte unchanged — verified by a diff/checksum
  test in Phase 4, not just visual review.
- transaction_no is the sole raw/fact dedup key; never derive dedup from any other field.
- No destructive migration of existing fct_reservation_night rows or columns at any phase.
- Commit each phase's execution changes before starting the next phase.
  Keep process/plan/context commits separate from execution commits.
```

---

## Stable Program Goal (copy-paste this to start autonomous execution)

```
SESSION GOAL: financials — Cashiering Postings Pipeline
Ref: process/features/financials/active/financials_17-07-26/financials-postings-umbrella_PLAN_17-07-26.md

TARGET: Complete ALL 5 phases until:
- dbt build --profiles-dir . exits 0 with all new/changed models + tests green
- extractor pytest suite exits 0 (incl. new cashiering extractor + window-chunking unit tests)
- fct_reservation_night existing columns verified unchanged (checksum/diff test)
- dashboard Revenue/Trends/Pacing tabs render revenue_actual with category breakdown
- Test tiers: automated (iterate-until-green) / hybrid (fix-if-in-blast-radius) / agent-probe (record-judgment)

AUTONOMY: Before ANY subagent spawn, read:
1. Umbrella ## Current Execution State -> loop step + validate-contract status
2. Phase plan ## Phase Loop Progress -> first unchecked box = next subagent to spawn

PER-PHASE LOOP (7-step inner loop R -> I -> P -> PVL -> E -> EVL -> UP, never skip, never reorder; SKIPS SPEC — SPEC runs once in the outer program loop, already locked):
  1. RESEARCH -> 2. INNOVATE -> 3. PLAN-SUPPLEMENT -> 4. PVL -> 5. EXECUTE -> 6. EVL -> 7. UPDATE-PROCESS
- PLAN-SUPPLEMENT: plan-agent writes research/innovate gaps into phase plan (or marks "n/a — clean")
- PVL NEVER skipped; contract must follow example-validate-output.md full format;
  partial contract (missing Plan updates applied / Execute-agent instructions / Test gates) =
  blocked same as placeholder
- Every subagent FIRST ACTION: run vc-context-discovery (load context group files +
  process/context/tests/all-tests.md routing chain) AND vc-plan-discovery (same-feature full
  depth active/backlog/completed/reports/refs + other features active-only + general-plans active)
- Every phase-END: invoke vc-agent-strategy-compare for next step strategy recommendation

Report via phase reports. No approval between phases unless hard stop hit.

HARD STOPS (pause, wait for user):
- Irreversible/outward-facing action without explicit validate-contract instruction
- Net gate = BLOCKED with no backlog resolution path
- Any change that would ALTER an existing fct_reservation_night column value (additive-only violation)
- Validate-contract is placeholder and vc-validate-agent cannot run

SAFETY (never override):
- fct_reservation_night existing columns (esp. night_amount) must stay byte-for-byte unchanged
- transaction_no is the sole dedup key
- Commit each phase before advancing; process and execution commits separate

TEST GATES (every phase exit):
  cd extractor && poetry run pytest tests/ -v
  cd eras_dbt && dbt build --profiles-dir .
  node .claude/skills/vc-generate-plan/scripts/validate-plan-artifact.mjs <phase-plan-path>

VALIDATE CONTRACT: Per-phase contracts written by vc-validate-agent into each phase plan before EXECUTE.

START: Phase 1, loop step RESEARCH (pending). Spawn vc-research-agent for Phase 1.
```

---

## Phase Sequence

| Phase | Plan file | Scope summary | Depends on |
|---|---|---|---|
| 0 (pre-program) | this file | Confirm folder structure, baseline audit, create sub-phase plans | — |
| 1 — Extractor + raw table | `process/features/financials/active/financials_17-07-26/phase-01-cashiering-extractor_PLAN_17-07-26.md` | `CashieringExtractor` + `raw.cashiering_postings` + `generate_7day_windows()` pure function | Phase 0 |
| 2 — Staging model | `process/features/financials/active/financials_17-07-26/phase-02-stg-cashiering-postings_PLAN_17-07-26.md` | `stg_cashiering_postings.sql` — Revenue filter, 9xxx exclusion, revenue_category derivation | Phase 1 |
| 3 — fct_folio_line | `process/features/financials/active/financials_17-07-26/phase-03-fct-folio-line_PLAN_17-07-26.md` | New fact table, grain = 1 row per transaction_no, uniqueness test | Phase 2 |
| 4 — fct_reservation_night additive columns | `process/features/financials/active/financials_17-07-26/phase-04-fct-reservation-night-additive_PLAN_17-07-26.md` | Additive revenue_actual/room/fnb/tax/svc columns + voucher-stay dbt test | Phase 3 |
| 5 — Dashboard wiring | `process/features/financials/active/financials_17-07-26/phase-05-dashboard-revenue-actual_PLAN_17-07-26.md` | Switch Revenue/Trends/Pacing tabs to revenue_actual, category chart | Phase 4 |

### Join Conditions

- Phase 1 MUST NOT start until Phase 0 exit gate passes.
- Phase 2 MUST NOT start until Phase 1 exit gate passes (raw table populated, extractor tests green).
- Phase 3 MUST NOT start until Phase 2 exit gate passes (staging model builds, category derivation tested).
- Phase 4 MUST NOT start until Phase 3 exit gate passes (fct_folio_line unique on transaction_no).
- Phase 5 MUST NOT start until Phase 4 exit gate passes (additive columns verified, existing columns unchanged).

---

## Per-Phase Entry / Exit Gates

| Phase | Entry | Exit gate |
|---|---|---|
| 0 | Program start | Phase plan files created; SPEC + INNOVATE decision reconciled |
| 1 | Phase 0 complete | `poetry run pytest tests/ -v` green incl. new cashiering extractor + window-chunking unit tests; `raw.cashiering_postings` populated for a small date range; upsert on transaction_no verified (re-run does not duplicate rows) |
| 2 | Phase 1 exit met | `dbt build --profiles-dir .` green for `stg_cashiering_postings`; zero rows for transaction_code 9xxx (AC-2); revenue_category populated for all rows |
| 3 | Phase 2 exit met | `dbt build --profiles-dir .` green for `fct_folio_line`; dbt `unique` test on transaction_no passes (AC-4) |
| 4 | Phase 3 exit met | `dbt build --profiles-dir .` green; existing fct_reservation_night columns checksum-identical before/after; new voucher-stay dbt test passes (revenue_actual not $0 when gross+credit postings both exist) |
| 5 | Phase 4 exit met | Dashboard renders revenue_actual across Revenue/Trends/Pacing (+Segments if confirmed in-scope during Phase 5 research); category breakdown chart present; "(estimated)" label removed; spot-check reservation matches OPERA folio total |

---

## Per-Phase Loop

Each phase executes the canonical 7-step inner loop `R -> I -> P -> PVL -> E -> EVL -> UP`. This inner
loop SKIPS SPEC — SPEC runs once in the outer program loop (already locked), not per phase. The 7 steps map to:

1. **RESEARCH** — spawn research-agent: load context, read prior phase reports, check plan drift, document findings
2. **INNOVATE** — spawn innovate-agent: decide approach; write Decision Summary (chosen approach + rejected alternatives)
3. **PLAN-SUPPLEMENT** — spawn plan-agent: if research/innovate found gaps/pre-conditions not in checklist, add them; otherwise mark "n/a — research clean" and tick step 3
4. **PVL** — spawn vc-validate-agent: full V1-V7; validate-contract written per `.claude/skills/vc-validate-findings/references/example-validate-output.md` format (Status / Gate / Plan updates applied / Execute-agent instructions / Test gates / High-risk pack / Backlog artifacts / Known gaps / Accepted by)
5. **EXECUTE** — spawn vc-execute-agent per approved plan and validate-contract
6. **EVL** — spawn vc-tester: run phase test gates to green; register follow-up stubs; write EVL HANDOFF SUMMARY
7. **UPDATE-PROCESS** — write phase report to durable report path, rewrite umbrella `## Current Execution State` section (overwrite, not append — git history is the audit log)

**PVL is NEVER skipped.** A placeholder `## Validate Contract` = blocked. Do not spawn execute-agent while the Validate Contract section reads "(placeholder — vc-validate-agent writes this section before EXECUTE)".

---

## Autonomous Execution Rules (During /goal)

During /goal execution of this phase program:
- Agent self-decides at all V5 gates — no user approval needed between phases
- CONDITIONAL net gate: proceed autonomously, fixes applied in-flight, gaps on record
- BLOCKED net gate: document items in backlog, continue with remaining phase plans; backlog is always a valid resolution — always find a path forward
- Hard stops (must pause for user approval):
  - Irreversible/outward-facing action without explicit contract instruction (push to remote, mutate production DB, run against production OPERA Cloud tenant without confirmed creds)
  - Any candidate change that would ALTER (not add to) an existing fct_reservation_night column value
  - Plan file explicitly marks "pause required" at a step
- Agent writes phase reports, updates phase plans, creates new sub-plans as needed — all autonomously
- The phase report is the communication channel for conflicts, errors, and learnings — not inline questions

---

## Global Constraints

- All new dbt models/columns are additive only — zero changes to existing `night_amount` or any
  other existing `fct_reservation_night` column.
- `transaction_no` is the sole raw/fact dedup key. No `/transactionCodes` lookup API call —
  category derivation is prefix-based only (explicitly out of scope).
- 7-day chunking is mandatory (API span constraint) and must be implemented as a pure,
  independently unit-testable function (AC-9) — `generate_7day_windows(start, end)`.
- VND currency only — no multi-currency handling.
- Backfill starts 2026-01-01; window count self-corrects from the pure date-arithmetic function
  (do not hardcode an expected window count in any test).
- After every phase that touches agent/harness files (none expected in this program, but if it
  happens), run the parity validator and confirm it exits 0 before declaring phase DONE.
- Commit each phase's execution changes before starting the next phase. Keep process/plan/context
  commits separate from execution commits.

---

## Durable Report Destinations

| Phase | Report path (inside task folder) |
|---|---|
| 0 (pre-program) | `process/features/financials/active/financials_17-07-26/phase-00-planning_REPORT_17-07-26.md` |
| 1 — Extractor + raw table | `process/features/financials/active/financials_17-07-26/phase-01-cashiering-extractor_REPORT_{dd-mm-yy}.md` |
| 2 — Staging model | `process/features/financials/active/financials_17-07-26/phase-02-stg-cashiering-postings_REPORT_{dd-mm-yy}.md` |
| 3 — fct_folio_line | `process/features/financials/active/financials_17-07-26/phase-03-fct-folio-line_REPORT_{dd-mm-yy}.md` |
| 4 — fct_reservation_night additive columns | `process/features/financials/active/financials_17-07-26/phase-04-fct-reservation-night-additive_REPORT_{dd-mm-yy}.md` |
| 5 — Dashboard wiring | `process/features/financials/active/financials_17-07-26/phase-05-dashboard-revenue-actual_REPORT_{dd-mm-yy}.md` |

---

## Program Status Table

| Phase | Status |
|---|---|
| 0 — Pre-program (plan creation) | CODE DONE (this umbrella + 5 phase plans written) |
| 01 — Extractor + raw table | ✅ VERIFIED (2026-07-18 — 32/32 pytest pass; 18,245 postings in raw.cashiering_postings; idempotency confirmed) |
| 02 — Staging model | ✅ VERIFIED (2026-07-18 — dbt build PASS 6/6; 12,885 rows; 5 revenue_category values; 0 wrapper rows) |
| 03 — fct_folio_line | ✅ VERIFIED (2026-07-19 — dbt build PASS 8/8; 12,885 rows; AC-3 known-gap: data scope, not model bug) |
| 04 — fct_reservation_night additive columns | BLOCKED-skipped (2026-07-19 — user decision: fct_folio_line already has Room/FnB/Tax/ServiceCharge breakdown; additive columns not needed; ADR stays on night_amount) |
| 05 — Dashboard wiring | ✅ VERIFIED (2026-07-19 — AC-5-import PASS, AC-5-schema PASS, AC-8 PASS; visual verify PASS: ₫8,375,541,915 total matches DB sum; all 5 revenue categories rendered) |

Status values: PLANNED | CODE DONE | TESTING | VERIFIED | BLOCKED | COMPLETE

---

## Touchpoints

- `extractor/src/extractors/cashiering.py` (new)
- `extractor/src/database.py` (raw.cashiering_postings upsert wiring)
- `extractor/src/main.py` (orchestration wiring)
- `eras_dbt/models/sources/sources.yml` (new source table entry)
- `eras_dbt/models/staging/stg_cashiering_postings.sql` (new)
- `eras_dbt/models/dimensional/fct_folio_line.sql` (new)
- `eras_dbt/models/dimensional/fct_reservation_night.sql` (additive columns only)
- `dashboard/app.py` (Revenue/Trends/Pacing tabs)

---

## Public Contracts

- `fct_reservation_night` existing columns (grain, `night_amount`, and every other pre-existing
  column) are an implicit public contract to the dashboard and any downstream BI — unchanged.
- New `fct_folio_line` grain (1 row per transaction_no) is a new public contract for future
  financials work (e.g. reconciliation reporting) — must hold from Phase 3 onward.
- Dashboard revenue displays move from estimated to actual — this is an intentional, user-visible
  behavior change communicated via removal of the "(estimated)" label (AC-7).

---

## Blast Radius

Files directly modified or created:

- 1 new extractor module: `extractor/src/extractors/cashiering.py`
- Modified: `extractor/src/database.py`, `extractor/src/main.py`
- 1 new raw table: `raw.cashiering_postings` (schema managed by extractor, not dbt)
- 1 modified: `eras_dbt/models/sources/sources.yml`
- 2 new dbt models: `stg_cashiering_postings.sql`, `fct_folio_line.sql`
- 1 modified dbt model: `fct_reservation_night.sql` (additive only)
- New dbt tests: uniqueness on `fct_folio_line.transaction_no`, voucher-stay revenue_actual
  non-zero test, existing-column checksum/diff test
- Modified: `dashboard/app.py` (Revenue/Trends/Pacing tabs + new category chart)

Risk class: schema change (new tables + additive columns on an existing fact table) — treated as
high-risk per program hard safety constraints; Phase 4 carries the highest risk (must not mutate
existing columns).

---

## Verification Evidence

```bash
# Extractor unit + integration tests (all phases touching extractor/)
cd extractor && poetry run pytest tests/ -v
# Expected: 0 failures, new cashiering + window-chunking tests included and passing

# dbt build (staging + dimensional layers)
cd eras_dbt && dbt build --profiles-dir .
# Expected: 0 errors; new/changed models + tests (uniqueness, voucher-stay, additive-column checksum) all pass

# Plan artifact structure validator (run per phase plan after write)
node .claude/skills/vc-generate-plan/scripts/validate-plan-artifact.mjs <phase-plan-path>
# Expected: no FAIL lines

# Umbrella artifact structure validator
node .claude/skills/vc-generate-phase-program/scripts/validate-umbrella-artifact.mjs process/features/financials/active/financials_17-07-26/financials-postings-umbrella_PLAN_17-07-26.md
# Expected: no FAIL lines
```

---

## Resume and Execution Handoff

- Selected plan file path: `process/features/financials/active/financials_17-07-26/financials-postings-umbrella_PLAN_17-07-26.md`
- Last completed phase: Phase 0 (this umbrella plan + 5 phase plans = Phase 0 artifact)
- Validate-contract status: pending (vc-validate-agent writes per-phase, starting with Phase 1)
- Next step for a fresh agent: Read this umbrella plan, read the Phase 1 plan
  (`phase-01-cashiering-extractor_PLAN_17-07-26.md`), then run Phase 1 research subagent before
  any EXECUTE work.
- Current phase: Phase 1 — Extractor + raw table
- Next action: Spawn vc-research-agent for Phase 1
- Execute-agent start instruction: Read this file. Read Phase 1 plan. Run research subagent first.

---

## Current Execution State

Last updated: 2026-07-19
Current phase: PROGRAM COMPLETE (5 of 5 phases done; Phase 4 BLOCKED-skipped by user decision)
Phase 1 name: Extractor + raw table
Phase 1 status: ✅ VERIFIED
Phase 1 EVL: PASS (32/32 pytest; E2E 18,245 postings; idempotency confirmed)
Phase 1 report: process/features/financials/active/financials_17-07-26/phase-01-cashiering-extractor_REPORT_18-07-26.md
Phase 2 name: Staging model
Phase 2 status: ✅ VERIFIED
Phase 2 EVL: PASS (dbt build PASS 6/6; 12,885 rows; 5 revenue_category values; 0 wrapper rows)
Phase 2 report: process/features/financials/active/financials_17-07-26/phase-02-stg-cashiering-postings_REPORT_18-07-26.md
Phase 3 name: fct_folio_line
Phase 3 status: ✅ VERIFIED
Phase 3 EVL: PASS=8/8 dbt build (fct_folio_line unique+notnull); AC-3 KNOWN-GAP (data scope — 35% match rate vs 95% threshold; needs reservation re-extraction for 2026 range; not a model bug)
Phase 3 report: process/features/financials/active/financials_17-07-26/phase-03-fct-folio-line_REPORT_19-07-26.md
Phase 4 name: fct_reservation_night additive columns
Phase 4 status: BLOCKED-skipped (2026-07-19 — user decision: fct_folio_line already has per-category breakdown; additive columns on fct_reservation_night not needed)
Phase 5 name: Dashboard wiring
Phase 5 status: ✅ VERIFIED (2026-07-19)
Phase 5 EVL: PASS — AC-5-import PASS, AC-5-schema PASS, AC-8 PASS; visual verify PASS: ₫8,375,541,915 total matches DB sum; all 5 revenue categories rendered; negative bars = OPERA correction postings (expected)
Phase 5 report: process/features/financials/active/financials_17-07-26/phase-05-dashboard-revenue-actual_REPORT_19-07-26.md
Next phase: NONE — program complete. Follow-up work: KPI tile update (revenue/ADR/RevPAR tiles currently use estimated night_amount; actual revenue from fct_folio_line is ~2.4x larger — ₫8.24B vs ₫3.41B EST). New plan needed for that follow-up.

Validate-contract status: Phase 1 CONDITIONAL (accepted, inner-pvl: phase-01); Phase 2 CONDITIONAL (accepted, inner-pvl: phase-02); Phase 3 CONDITIONAL (accepted, inner-pvl: phase-03); Phase 4 BLOCKED-skipped (no contract); Phase 5 CONDITIONAL (accepted, inner-pvl: phase-05)
Program Net Gate: Phase 1 PASS; Phase 2 PASS; Phase 3 PASS (AC-3 known-gap on record); Phase 4 BLOCKED-skipped; Phase 5 PASS (visual verify confirmed)

Key finding (Phase 5 verify): Revenue KPI tile shows ₫3.41B (estimated from night_amount); true actual revenue = ₫8.24B (fct_folio_line excl. Tax). Understatement ~2.4x. TRevPAR and TRevPOR metrics are now computable but not yet built. FnB ₫4.5B is legitimate large group/event business (META EVENT TRAVEL etc., 564 covers/₫282M per event). Negative revenue bars = OPERA correction postings, expected behavior.

Known gaps carried forward to follow-up plan:
- AC-3 FK rate: 35% reservation FK match; needs reservation re-extraction for 2026-01-01+ range
- KPI tiles (Revenue, ADR, RevPAR) still use estimated night_amount — require separate follow-up plan
- Dashboard automated rendering tests: no pytest suite for Streamlit UI (structural gap)
- TRevPAR / TRevPOR: new metrics now possible but not yet built

Loop step values: RESEARCH | INNOVATE | PLAN-SUPPLEMENT | PVL | EXECUTE | EVL | UPDATE-PROCESS
Program status: COMPLETE. Task folder remains in active/ pending follow-up KPI tile work.

Note: The Stable Program Goal above is fixed. This section is the only part that changes — update-process-agent rewrites it after every phase closeout (overwrite, not append — git history is the audit log).

---

## Test Infra Improvement Notes

(none identified yet)

---

## Pre-PVL Conflict Resolution

No package conflicts — all phases are parallel-safe. This program is strictly sequential (each
phase's model output is the next phase's model input), so no two phases will ever edit the same
file concurrently; the sequential Phase Sequence table above is the sole ordering constraint.

---

## Validate Contract

(placeholder — vc-validate-agent writes this section before EXECUTE)
