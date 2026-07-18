---
name: plan:financials-postings-phase-03-fct-folio-line
description: "Cashiering postings pipeline — Phase 3: fct_folio_line fact table"
date: 17-07-26
metadata:
  node_type: memory
  type: plan
  feature: financials
  phase: phase-03
---

# Phase 03 — fct_folio_line

**Program:** financials-postings
**Umbrella plan:** process/features/financials/active/financials_17-07-26/financials-postings-umbrella_PLAN_17-07-26.md
**Phase status:** PLANNED
**Report destination:** process/features/financials/active/financials_17-07-26/phase-03-fct-folio-line_REPORT_{dd-mm-yy}.md (flat in the program task folder)

---

## Purpose

Build the new fact table `fct_folio_line.sql` at grain = one row per posting (`transaction_no`).
This is the Kimball-discipline fact layer that Phase 4 aggregates into `fct_reservation_night`.
It must also remain independently queryable for reconciliation of postings that have no matching
reservation (unmatched-postings case called out in the locked SPEC) — this fact table is not
merely an intermediate throwaway, it is a durable analytical asset in its own right.

---

## Entry Gate

- Phase 2 exit gate passed: `stg_cashiering_postings` builds green, revenue_category populated
  and tested

---

## Blast Radius

- `eras_dbt/models/dimensional/fct_folio_line.sql` (new)
- `eras_dbt/models/dimensional/fct_folio_line.yml` (new schema/test file, or inline schema tests
  per project convention — confirm during RESEARCH which pattern `fct_reservation_night` uses)

---

## Implementation Checklist

### Step A — Confirm grain and join key

- [ ] A1. Read `eras_dbt/models/dimensional/fct_reservation_night.sql` and its accompanying schema
      file (if any) to confirm the project's fact-table conventions: grain declaration comment,
      surrogate key pattern, foreign key naming (`reservation_id` vs `reservation_no`), and
      dbt test conventions (`unique`, `not_null`, `relationships`).
- [ ] A2. Confirm the join key from `stg_cashiering_postings` to the reservation dimension is
      `guestInfo.reservationId.id` (per locked SPEC) — trace this through `stg_cashiering_postings`
      output columns from Phase 2 to confirm the column is actually carried through (if not,
      flag as a Phase 2 supplement need).

### Step B — Build fct_folio_line

- [ ] B1. Write `fct_folio_line.sql`: one row per `transaction_no`, selecting from
      `stg_cashiering_postings`, surfacing `reservation_id` (derived from the SPEC's join key),
      `revenue_date`, `revenue_category`, `posted_amount`, `hotel_id`, plus provenance
      (`cashier_id`, `reference`) carried through from Phase 2.
- [ ] B2. Ensure the model remains queryable/visible on its own for reconciliation of postings
      with `reservation_id IS NULL` (unmatched postings) — do NOT inner-join away unmatched rows;
      keep them in the fact with a NULL foreign key, per the locked SPEC's reconciliation
      requirement.

### Step C — Tests (AC-4 is an explicit acceptance criterion)

- [ ] C1. Add dbt `unique` test on `transaction_no` — this is the grain-defining test and is
      explicitly required by AC-4 (must be present and passing, not merely implied).
- [ ] C2. Add `not_null` test on `transaction_no`, `revenue_date`, `revenue_category`,
      `posted_amount`.
- [ ] C3. Add a `relationships` test (or documented exception) from `reservation_id` to the
      reservation dimension, allowing NULLs (unmatched postings are valid, not a failure).
      **NEW (execute-agent instruction E1):** Standard dbt `relationships` test fails on NULL FK
      values. Use `where: "reservation_id is not null"` on the relationships test to exclude NULLs.
      This is not a workaround — it is the correct semantics: unmatched rows are expected and
      are NOT a referential integrity failure.

---

## Exit Gate

```bash
cd eras_dbt && dbt build --profiles-dir . --select fct_folio_line
# Expected: model builds; unique test on transaction_no passes; not_null tests pass
```

- All checklist items (A-C) checked
- `dbt build --profiles-dir .` green for `fct_folio_line` including the unique(transaction_no) test
- Phase report written to report destination above

---

## Blockers That Would Justify BLOCKED Status

- `guestInfo.reservationId.id` is not actually present/reliable in the staged data (Phase 2's
  staging model does not carry it through) — requires a Phase 2 supplement before this phase can
  complete.
- Grain violation discovered (a transaction_no appears more than once in raw data due to an
  extraction bug) — routes back to Phase 1 as a regression, not fixable in this phase's scope.

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

- `eras_dbt/models/dimensional/fct_folio_line.sql` (new)
- `eras_dbt/models/dimensional/fct_folio_line.yml` (new)

---

## Public Contracts

- `fct_folio_line` grain (1 row per transaction_no) is a new durable contract, both for Phase 4's
  aggregation and for future reconciliation/ad-hoc reporting use — must hold going forward.
- No existing model or dashboard contract is touched.

---

## Verification Evidence

| Gate / Scenario | Strategy | Proves SPEC criterion |
|---|---|---|
| dbt `unique` test on transaction_no | Fully-Automated | AC-4 (fact grain = 1 row per transaction_no) |
| dbt `not_null` tests on key columns | Fully-Automated | AC-4 (data completeness at grain) |
| Manual query: unmatched postings (reservation_id IS NULL) still visible | Agent-Probe | SPEC reconciliation requirement (unmatched postings not silently dropped) |

```bash
cd eras_dbt && dbt build --profiles-dir . --select fct_folio_line
# Expected: 0 errors
```

---

## Resume and Execution Handoff

- Selected plan file path: `process/features/financials/active/financials_17-07-26/phase-03-fct-folio-line_PLAN_17-07-26.md`
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
Rationale: 3/7 signals (S4 phase-program, S6 new fact table, S7 2 blast-radius files); sequential correct; Phase 3 depends on Phase 2 reservation_id carrythrough which was flagged as a CONCERN — must be verified at RESEARCH before EXECUTE proceeds

Plan updates applied:
- P1: Added Step C3 clarification note: use `where: "reservation_id is not null"` on the dbt relationships test — standard dbt relationships test fails on NULL FK; this is the correct semantics for unmatched postings, not a workaround

Execute-agent instructions:
- E1: The dbt `relationships` test on `reservation_id` MUST include `where: "reservation_id is not null"`. Without this, the test will fail for all unmatched postings (NULL FK), which is valid behavior per the locked SPEC. Correct syntax in the .yml schema file: `- dbt_utils.relationships: {to: ref('dim_reservation'), field: reservation_id, where: "reservation_id is not null"}` (or the dbt core `relationships` test with the `where` config). Confirm the exact dbt relationships test syntax against the project's existing schema file conventions during RESEARCH.
- E2: Before writing fct_folio_line.sql, verify the `reservation_id` column is actually present in `stg_cashiering_postings` output (Phase 2 instruction E2 added it; confirm during RESEARCH by reading the Phase 2 report or the actual staging model). If absent, this is a BLOCKER — surface a Phase 2 supplement need, do not proceed with a fct_folio_line that silently has no reservation linkage.
- E3: The surrogate key pattern for this fact table should follow fct_reservation_night.sql's `md5(concat_ws('|', ...))` pattern. Use `transaction_no` as the sole natural key input to the md5 (since transaction_no is the unique grain). Confirm the exact md5 concat pattern from fct_reservation_night during RESEARCH.
- E4: Do NOT inner-join to any dimension in the main model body. The unmatched-postings use case requires all rows from stg_cashiering_postings to appear in fct_folio_line, including those with NULL reservation_id. Any dimension enrichment (e.g. hotel_id label from dim_property) must use a LEFT JOIN.

Test gates (C3 5-column table):

| criterion id | behavior | strategy | proving test | gap-resolution |
|---|---|---|---|---|
| AC-4-unique | fct_folio_line has exactly one row per transaction_no (grain integrity) | Fully-Automated | `cd eras_dbt && dbt build --profiles-dir . --select fct_folio_line` (dbt unique test on transaction_no) | A |
| AC-4-notnull | transaction_no, revenue_date, revenue_category, posted_amount are all non-null | Fully-Automated | `cd eras_dbt && dbt build --profiles-dir . --select fct_folio_line` (dbt not_null schema tests) | A |
| AC-4-fk-integrity | reservation_id references a valid reservation when not NULL (unmatched nulls are valid) | Fully-Automated | `cd eras_dbt && dbt build --profiles-dir . --select fct_folio_line` (dbt relationships test with where: "reservation_id is not null") | A |
| SPEC-unmatched | Postings with no matching reservation remain visible in fct_folio_line (reservation_id IS NULL rows exist and are not dropped) | Agent-Probe | `SELECT count(*) FROM fct_folio_line WHERE reservation_id IS NULL` — confirm > 0 if any unmatched postings exist in the backfill range (if 0, document in phase report as "no unmatched postings in test period — model is structurally correct") | D |

Failing stub (AC-4-unique):
test("should have exactly one row per transaction_no", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: dbt unique test on transaction_no in fct_folio_line")
})

Failing stub (AC-4-notnull):
test("should have non-null values for all grain-defining columns", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: dbt not_null tests on transaction_no, revenue_date, revenue_category, posted_amount")
})

Failing stub (AC-4-fk-integrity):
test("should pass FK integrity check for non-null reservation_id values only", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: dbt relationships test with where: reservation_id is not null")
})

gap-resolution legend:
- A — proven now (gate passes in this cycle)
- B — fixed in this plan (gate added by this plan's checklist)
- C — deferred to a named later phase/plan
- D — backlog test-building stub (named residual; keep-active; continue)

Legacy line form:
- fct_folio_line/grain-unique: Fully-automated: `cd eras_dbt && dbt build --profiles-dir . --select fct_folio_line`
- fct_folio_line/not-null: Fully-automated: `cd eras_dbt && dbt build --profiles-dir . --select fct_folio_line`
- fct_folio_line/fk-integrity: Fully-automated: `cd eras_dbt && dbt build --profiles-dir . --select fct_folio_line`
- fct_folio_line/unmatched-visible: agent-probe: SELECT count(*) FROM fct_folio_line WHERE reservation_id IS NULL

Dimension findings:
- Infra fit: PASS — dbt fact table pattern mirrors fct_reservation_night.sql; no new dbt packages needed; md5 surrogate key pattern is established
- Test coverage: CONDITIONAL — AC-4 grain tests are Fully-Automated; unmatched-postings verification is Agent-Probe (no automated CI gate for unmatched count > 0, since count may legitimately be 0 in test periods)
- Breaking changes: PASS — additive new model; no existing fact/dim tables are touched; no dashboard references fct_folio_line yet
- Security surface: PASS — new read-only dbt model over internal staging data; no credentials or API surface changes

Open gaps:
- SPEC-unmatched: known-gap: documented as Agent-Probe — count of unmatched postings depends on real data in the backfill window; cannot be automated without a known-unmatched fixture in the test DB

What this coverage does NOT prove:
- AC-4-unique: Does not prove transaction_no uniqueness originates correctly from Phase 1 extraction (the unique test catches duplication AT this layer, but does not prove Phase 1 has no extraction-level duplication that was deduplicated by Phase 2 upstream)
- AC-4-fk-integrity: Does not prove reservation_id values correctly correspond to actual reservations in dim_reservation (only proves FK referential integrity, not business-key correctness)
- SPEC-unmatched: Does not prove the unmatched count is correct against what OPERA Cloud actually has — spot-check against OPERA reporting is the only way to verify

Gate: CONDITIONAL
Accepted by: session (autonomous, /goal execution) — concerns: relationships test NULL handling fixed via P1 plan update and E1 instruction; reservation_id carrythrough dependency from Phase 2 acknowledged via E2 instruction; unmatched-postings gate is Agent-Probe (acceptable known-gap for dbt fact models)
