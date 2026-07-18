---
name: plan:financials-postings-phase-04-fct-reservation-night-additive
description: "Cashiering postings pipeline — Phase 4: additive revenue columns on fct_reservation_night"
date: 17-07-26
metadata:
  node_type: memory
  type: plan
  feature: financials
  phase: phase-04
---

# Phase 04 — fct_reservation_night Additive Columns

**Program:** financials-postings
**Umbrella plan:** process/features/financials/active/financials_17-07-26/financials-postings-umbrella_PLAN_17-07-26.md
**Phase status:** PLANNED
**Report destination:** process/features/financials/active/financials_17-07-26/phase-04-fct-reservation-night-additive_REPORT_{dd-mm-yy}.md (flat in the program task folder)

---

## Purpose

Modify `eras_dbt/models/dimensional/fct_reservation_night.sql` to ADD five new columns
(`revenue_actual`, `revenue_room`, `revenue_fnb`, `revenue_tax`, `revenue_svc`), aggregated from
`fct_folio_line` grouped by `reservation_id` + `revenue_date`, left-joined onto the existing night
grain by matching `revenue_date` to the night's business date. This is the highest-risk phase in
the program: the locked SPEC and umbrella hard safety constraints require every existing column
(especially `night_amount`) to remain byte-for-byte unchanged. This phase must produce verifiable
evidence of that, not just a visual diff.

---

## Entry Gate

- Phase 3 exit gate passed: `fct_folio_line` builds green with `unique(transaction_no)` passing

---

## Blast Radius

- `eras_dbt/models/dimensional/fct_reservation_night.sql` (modified — additive columns only)
- `eras_dbt/models/dimensional/fct_reservation_night.yml` (modified — add schema tests for new
  columns; do not remove/alter existing test entries)
- New dbt test file(s) for the additive-column checksum/diff test and the voucher-stay test

---

## Implementation Checklist

### Step A — Baseline capture (before any edit)

- [ ] A1. Before editing `fct_reservation_night.sql`, capture a baseline: run
      `dbt build --profiles-dir . --select fct_reservation_night` on the CURRENT (pre-Phase-4)
      model and record a checksum or row-level snapshot of all existing columns (e.g.
      `SELECT md5(...concat of all existing columns...) FROM fct_reservation_night` or an
      equivalent dbt-native approach) for later comparison. This is the evidence artifact that
      proves the additive-only constraint held.
      **NEW (execute-agent instruction E1):** The practical baseline approach is a SQL query saved
      in the phase report, NOT a dbt test (dbt tests cannot compare pre/post state across runs).
      Run this SQL BEFORE any file edit and record the output in the phase report:
      ```sql
      SELECT
        count(*) as row_count,
        md5(string_agg(
          fact_sk || '|' || hotel_id || '|' || reservation_id || '|' ||
          business_date::text || '|' || night_amount::text,
          '|' ORDER BY fact_sk
        )) as existing_columns_checksum
      FROM dimensional.fct_reservation_night;
      ```
      Run the identical query AFTER the edit. Checksums must match exactly.
- [ ] A2. Read `eras_dbt/models/dimensional/fct_reservation_night.sql` in full to understand its
      current CTE structure, grain (reservation_id + business date, confirm exact column names),
      and existing join patterns — the new aggregation join must follow the same style.
- [ ] A3. **NEW (execute-agent instruction E2):** Confirm the exact name of the business-date
      column in fct_reservation_night. The column is named `business_date` per earlier research,
      but confirm this from the actual SQL file during A2 — the join in Step B3 depends on this
      exact name.

### Step B — Build the folio-line rollup

- [ ] B1. **Architect risk flag from INNOVATE**: decide whether the folio-line-to-reservation-night
      rollup needs its own explicit intermediate model (e.g.
      `eras_dbt/models/dimensional/int_folio_line_daily_agg.sql`) for testability, versus being
      inlined directly as a CTE inside `fct_reservation_night.sql`. Document the decision and
      rationale (testability/debuggability vs fewer files) before proceeding — this is a real
      INNOVATE-level choice being deferred into this phase's own Innovate step.
- [ ] B2. Implement the aggregation: `GROUP BY reservation_id, revenue_date` from
      `fct_folio_line`, producing `revenue_actual` (SUM of all posted_amount),
      `revenue_room`/`revenue_fnb`/`revenue_tax`/`revenue_svc` (SUM filtered by revenue_category).
- [ ] B3. LEFT JOIN this aggregation onto the existing `fct_reservation_night` grain, matching
      `revenue_date` to the night's business date column — confirm the exact business-date column
      name in `fct_reservation_night` during research (do not assume it is literally named
      `business_date`).
- [ ] B4. Ensure nights with no matching postings get `revenue_actual = NULL` (not 0) to
      distinguish "no posting data" from "genuine zero revenue posting". Phase 5 dashboard must
      handle NULL gracefully (COALESCE to 0 at the display layer). Document this NULL convention
      in the phase report so Phase 5 execute-agent is pre-warned.

### Step C — Additive-only verification (mandatory, not optional)

- [ ] C1. After the edit, re-run the checksum query from Step A1 against the NEW model output and
      diff against the Step A1 baseline — every existing column's checksum must match exactly.
      Record both checksums (pre/post) in the phase report as the empirical evidence artifact.
- [ ] C2. The checksum query from A1 is the permanent verification artifact — keep it in the phase
      report as a runnable SQL script so future changes to this model can re-run the same proof.
      No dbt test needed (dbt tests cannot capture pre/post state across model runs).

### Step D — Voucher-stay test (MUST-HAVE from INNOVATE risk flag)

- [ ] D1. Add a dedicated dbt test for VOUCHER stays verifying `revenue_actual` is NOT $0 when a
      stay has both a gross charge posting and a matching credit/voucher posting in
      `fct_folio_line`. This goes beyond AC-8's existing "both postings exist" check — AC-8 checks
      presence, this test checks the AGGREGATE is correct (net revenue is non-zero, not that the
      gross and credit cancel to exactly zero when they should net to a real amount).
- [ ] D2. Identify or construct a real test fixture: use one of the empirically-verified
      reservations from Phase 2 research context (18577414 or 18156668, per the Decision Summary)
      if either has a voucher/credit posting pattern, or find another suitable example during
      research. If no voucher fixture exists in the 2026-01-01 backfill range, document this as a
      known-gap and create a backlog note for the voucher-stay test.

---

## Exit Gate

```bash
cd eras_dbt && dbt build --profiles-dir . --select fct_reservation_night
# Expected: model builds; all existing tests still pass; new additive-column tests pass;
#   voucher-stay test passes; checksum/diff test confirms existing columns unchanged
```

- All checklist items (A-D) checked
- Existing `fct_reservation_night` columns verified byte-for-byte unchanged via checksum/diff
- New voucher-stay test passes (or known-gap documented if no voucher fixture in backfill range)
- Phase report written to report destination above, including the checksum/diff evidence

---

## Blockers That Would Justify BLOCKED Status

- Checksum/diff comparison (Step C1) reveals an existing column's values changed after the edit —
  this is a hard safety constraint violation and MUST block; do not proceed to Phase 5 with an
  unresolved additive-only violation.
- No suitable voucher/credit test fixture exists in the extracted date range — flag as a known-gap
  with backlog note rather than fabricating synthetic test data that doesn't reflect real OPERA
  posting patterns.
- Business-date column name in `fct_reservation_night` doesn't cleanly map to `revenue_date`
  (e.g. timezone or date-boundary mismatch) — may require SPEC clarification since timezone
  precision beyond date-level is explicitly out of scope.

---

## Phase Loop Progress

Orchestrator reads this before deciding which subagent to spawn next. The canonical 7-step inner loop
`R -> I -> P -> PVL -> E -> EVL -> UP` SKIPS SPEC (SPEC runs once in the outer program loop, already locked).

- [ ] 1. RESEARCH — research-agent: prior phase reports read; test context loaded; plan drift checked
- [ ] 2. INNOVATE — innovate-agent: approach decided; Decision Summary written (incl. Step B1's
      intermediate-model-vs-inline-CTE decision)
- [ ] 3. PLAN-SUPPLEMENT — plan-agent: existing phase plan updated; Inner Loop Refresh Note if sections changed (or "n/a — research clean")
- [ ] 4. PVL — vc-validate-agent: full V1-V7; validate-contract written per `.claude/skills/vc-validate-findings/references/example-validate-output.md` (Status / Gate / Plan updates applied / Execute-agent instructions / Test gates / High-risk pack / Backlog artifacts / Known gaps / Accepted by)
- [ ] 5. EXECUTE — all checklist items done; per-section test gates run and green (or gaps documented)
- [ ] 6. EVL — all EVL gates green; follow-up stubs registered; EVL HANDOFF SUMMARY written
- [ ] 7. UPDATE PROCESS — phase report written, umbrella state updated, commit done

**Validate-contract required before execute.** If step 4 (PVL) is unchecked or `## Validate Contract`
reads "(placeholder — vc-validate-agent writes this section before EXECUTE)", orchestrator must
spawn vc-validate-agent first. A partial contract missing Plan updates applied / Execute-agent
instructions / Test gates sections is treated as a placeholder.

**High-risk pack note:** this phase carries the program's hard safety constraint (additive-only,
no mutation of existing fct_reservation_night columns). VALIDATE must apply the High-Risk
Execution Handoff evidence pack per `orchestration.md` §High-Risk Execution Handoff (schema-change
class) before this phase can reach VERIFIED.

---

## Touchpoints

- `eras_dbt/models/dimensional/fct_reservation_night.sql` (modified, additive only)
- `eras_dbt/models/dimensional/fct_reservation_night.yml` (modified)
- Possibly `eras_dbt/models/dimensional/int_folio_line_daily_agg.sql` (new, if intermediate model
  chosen at Step B1)

---

## Public Contracts

- **Hard constraint**: every existing `fct_reservation_night` column (grain, `night_amount`, and
  all others) is an implicit public contract to the dashboard and any downstream BI — must remain
  byte-for-byte unchanged. This is the single most important contract in the entire program.
- New columns (`revenue_actual`, `revenue_room`, `revenue_fnb`, `revenue_tax`, `revenue_svc`) are
  a new contract consumed directly by Phase 5's dashboard wiring.
- NULL convention for no-posting nights: `revenue_actual = NULL` (not 0) — Phase 5 must COALESCE
  at display layer.

---

## Verification Evidence

| Gate / Scenario | Strategy | Proves SPEC criterion |
|---|---|---|
| Checksum/diff of existing columns, pre- vs post-edit | Hybrid | Hard safety constraint (additive-only; existing columns unchanged) |
| dbt `not_null` tests on new revenue columns (where postings exist) | Fully-Automated | AC-6 (new columns populated correctly when data present) |
| Voucher-stay dbt test (revenue_actual not $0 with gross+credit) | Fully-Automated | AC-8 extended (aggregate correctness beyond presence check) |
| Spot-check: known reservation's revenue_actual sums correctly from fct_folio_line | Agent-Probe | AC-5, AC-6 (aggregation join correctness) |

```bash
cd eras_dbt && dbt build --profiles-dir . --select fct_reservation_night
# Expected: 0 errors; all tests including checksum/diff and voucher-stay pass
```

---

## Resume and Execution Handoff

- Selected plan file path: `process/features/financials/active/financials_17-07-26/phase-04-fct-reservation-night-additive_PLAN_17-07-26.md`
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
Rationale: 4/7 signals (S2 high-risk schema mutation, S4 phase-program, S6 existing fact table modified, S7 3 blast-radius files); higher signal count than other phases due to S2 (high-risk); still sequential — modification of a single existing model does not benefit from parallelism; the additive-only constraint creates a strict before→after ordering that enforces sequential execution

Plan updates applied:
- P1: Added Step A1 note with concrete checksum SQL (md5 over fact_sk + hotel_id + reservation_id + business_date + night_amount) — clarifies the baseline capture as a SQL script saved in the phase report, not a dbt test
- P2: Added Step A3 — execute-agent must confirm exact business-date column name from the actual SQL file during research
- P3: Changed Step B4 to specify NULL (not 0) for no-posting nights with explicit Phase 5 COALESCE convention
- P4: Updated Public Contracts to document the NULL convention explicitly

Execute-agent instructions:
- E1: CRITICAL — Run the baseline checksum SQL BEFORE making ANY edit to fct_reservation_night.sql. Record both the row_count and the existing_columns_checksum in the phase report. Only then proceed with the edit. After the edit, run the identical query again and confirm both values match. A mismatch in either value is a HARD STOP — do not proceed to Phase 5.
  Baseline SQL:
  ```sql
  SELECT
    count(*) as row_count,
    md5(string_agg(
      fact_sk || '|' || hotel_id || '|' || reservation_id || '|' ||
      business_date::text || '|' || night_amount::text,
      '|' ORDER BY fact_sk
    )) as existing_columns_checksum
  FROM dimensional.fct_reservation_night;
  ```
  Note: if the actual column names differ (e.g. business_date has a different alias), adjust the SQL to match the actual column names found in Step A2.
- E2: Confirm exact column name for business date by reading fct_reservation_night.sql in full during A2. The join condition in Step B3 (`revenue_date = business_date`) depends on the exact column name. Earlier research confirms it is named `business_date` but verify from the source file.
- E3: The LEFT JOIN for the folio-line aggregation must join on BOTH `reservation_id` AND `business_date = revenue_date`. Joining on reservation_id alone would aggregate all nights for a reservation together, destroying the per-night grain. The join key is the pair `(reservation_id, business_date)`.
- E4: New revenue columns must use COALESCE in the fact table SELECT: `COALESCE(fl_agg.revenue_actual, NULL)` — actually do NOT coalesce to 0 here. Leave as NULL so downstream consumers can distinguish "no posting data" from "explicit zero". Document this in the phase report so Phase 5 knows to COALESCE at the display layer.
- E5: Voucher-stay test — if no real VOUCHER fixture exists in the 2026-01-01 backfill range, document the gap in the phase report as: "known-gap: no VOUCHER posting found in 2026-01-01 backfill range; voucher-stay aggregate correctness deferred to backlog test stub" and create a backlog note at `process/features/financials/backlog/voucher-stay-aggregate-test_note.md`. Do NOT fabricate synthetic data.
- E6: HIGH-RISK EVIDENCE PACK (schema-change class per orchestration.md §High-Risk Execution Handoff). Before marking Phase 4 DONE, write to the phase report:
  1. Pre-edit row count from E1 baseline SQL
  2. Post-edit row count (must equal pre-edit)
  3. Pre-edit checksum from E1 baseline SQL
  4. Post-edit checksum (must equal pre-edit)
  4. dbt build exit code (must be 0)
  5. List of new columns confirmed present in the model output

Test gates (C3 5-column table):

| criterion id | behavior | strategy | proving test | gap-resolution |
|---|---|---|---|---|
| ADDITIVE-CHECKSUM | Existing fct_reservation_night columns (fact_sk, hotel_id, reservation_id, business_date, night_amount) are byte-for-byte unchanged after adding new columns | Hybrid | Pre-edit: run baseline SQL from E1; record row_count + checksum. Post-edit: run identical SQL; confirm row_count and checksum match exactly. Both results recorded in phase report. | A |
| AC-6-new-cols-build | New revenue columns (revenue_actual, revenue_room, revenue_fnb, revenue_tax, revenue_svc) are present and fct_reservation_night builds cleanly | Fully-Automated | `cd eras_dbt && dbt build --profiles-dir . --select fct_reservation_night` (model build exits 0; new column schema tests pass) | A |
| AC-6-notnull-conditional | New revenue columns are non-null for reservation-nights that have matching postings in fct_folio_line | Fully-Automated | `cd eras_dbt && dbt build --profiles-dir . --select fct_reservation_night` (conditional not_null dbt test: not_null where revenue_actual is not null — i.e., prove no partial NULL within a row that has any revenue column populated) | A |
| AC-8-voucher-aggregate | For a VOUCHER stay, revenue_actual correctly reflects the net amount (gross charge + matching credit do not cancel to zero when they should net positive) | Fully-Automated | `cd eras_dbt && dbt build --profiles-dir . --select fct_reservation_night` (singular dbt test on known VOUCHER reservation_id) | D |
| AC-5-6-spot-check | Known reservation's revenue_actual sum matches manual sum of fct_folio_line posted_amount for that reservation_id + business_date | Agent-Probe | `SELECT reservation_id, business_date, revenue_actual FROM fct_reservation_night WHERE reservation_id = '[known_id]'` vs `SELECT sum(posted_amount) FROM fct_folio_line WHERE reservation_id = '[known_id]' AND revenue_date = '[date]'` | D |

Failing stub (AC-6-new-cols-build):
test("should build fct_reservation_night with new additive revenue columns present", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: dbt build fct_reservation_night exits 0 with new columns")
})

Failing stub (AC-6-notnull-conditional):
test("should have non-null revenue columns for nights with matching postings", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: conditional not_null dbt test on revenue_actual")
})

gap-resolution legend:
- A — proven now (gate passes in this cycle)
- B — fixed in this plan (gate added by this plan's checklist)
- C — deferred to a named later phase/plan
- D — backlog test-building stub (named residual; keep-active; continue)

Legacy line form:
- fct_reservation_night/additive-checksum: hybrid: pre-edit SQL checksum recorded in phase report + post-edit SQL checksum must match
- fct_reservation_night/new-cols-build: Fully-automated: `cd eras_dbt && dbt build --profiles-dir . --select fct_reservation_night`
- fct_reservation_night/voucher-aggregate: known-gap: documented as backlog test stub — requires VOUCHER fixture in backfill range
- fct_reservation_night/revenue-spot-check: agent-probe: manual SQL cross-check for known reservation_id

Dimension findings:
- Infra fit: PASS — dbt LEFT JOIN pattern on an existing fact table is straightforward; md5 surrogate key already established; no new packages or infra needed
- Test coverage: CONDITIONAL — ADDITIVE-CHECKSUM is hybrid (not fully-automated because dbt tests cannot compare pre/post snapshots; requires analyst/agent to run and record the SQL before and after the edit); AC-8 voucher test is known-gap until a VOUCHER fixture is confirmed in the backfill range
- Breaking changes: FAIL (resolved via plan fix) — original blast radius omitted the NULL convention for no-posting nights; Phase 5 needs COALESCE; fixed via P3 plan update and E4 instruction; no longer a FAIL after plan fix applied
- Security surface: PASS — no auth/identity/billing/credentials changes; modifying an existing internal dbt model with additive-only columns

High-risk execution class: schema-change (modifying existing fct_reservation_night). Evidence pack per orchestration.md §High-Risk Execution Handoff must be written to the phase report before marking Phase 4 DONE. Required artifacts: pre/post row_count, pre/post checksum, dbt build exit code, new-column list (see E6).

Open gaps:
- AC-8-voucher-aggregate: known-gap: documented as D (backlog test stub) — VOUCHER fixture availability in 2026-01-01 backfill range unknown until RESEARCH; if confirmed absent, backlog note at process/features/financials/backlog/voucher-stay-aggregate-test_note.md
- AC-5-6-spot-check: known-gap: documented as D (Agent-Probe) — requires specific reservation_id confirmed during Phase 3/4 RESEARCH

What this coverage does NOT prove:
- ADDITIVE-CHECKSUM: The hybrid checksum covers fact_sk, hotel_id, reservation_id, business_date, night_amount only. Any other existing column NOT in the checksum (e.g. a column added in a future phase) would not be covered — execute-agent must confirm the full existing column list during A2 and extend the checksum SQL if additional columns exist.
- AC-6-new-cols-build: dbt build success proves the model runs; it does NOT prove the revenue aggregation sums are numerically correct (only the spot-check Agent-Probe addresses correctness)
- AC-8-voucher-aggregate: If no VOUCHER fixture is available in the backfill range, voucher aggregate correctness remains unverified in this cycle
- ADDITIVE-CHECKSUM (hybrid): Depends on the analyst/execute-agent actually running the pre-edit SQL before making the edit. If the edit is made first and the baseline is reconstructed retroactively, the proof is invalid.

Gate: CONDITIONAL
Accepted by: session (autonomous, /goal execution) — concerns: breaking-changes FAIL resolved via P3 plan update (NULL convention documented; Phase 5 COALESCE instruction added); voucher-aggregate test is backlog-D (acceptable — no VOUCHER fixture confirmed yet); additive-checksum is hybrid not fully-automated (acceptable for schema-change class — this is the standard evidence pack approach for dbt model mutations); evidence pack E6 required in phase report before Phase 4 DONE
