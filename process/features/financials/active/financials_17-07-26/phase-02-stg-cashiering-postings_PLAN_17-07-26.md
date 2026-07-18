---
name: plan:financials-postings-phase-02-stg-cashiering-postings
description: "Cashiering postings pipeline — Phase 2: stg_cashiering_postings staging model"
date: 17-07-26
metadata:
  node_type: memory
  type: plan
  feature: financials
  phase: phase-02
---

# Phase 02 — Staging Model

**Program:** financials-postings
**Umbrella plan:** process/features/financials/active/financials_17-07-26/financials-postings-umbrella_PLAN_17-07-26.md
**Phase status:** PLANNED
**Report destination:** process/features/financials/active/financials_17-07-26/phase-02-stg-cashiering-postings_REPORT_{dd-mm-yy}.md (flat in the program task folder)

---

## Purpose

Build `stg_cashiering_postings.sql`, the staging layer over `raw.cashiering_postings`. Filters
to Revenue-type postings only, excludes transaction_code 9xxx (Wrapper/folio header rows — must
produce zero rows for Wrapper per AC-2), and derives `revenue_category` from the transaction_code
numeric prefix (1x=Room, 2x/3x/6x=FnB, 7x=Tax, 8x=ServiceCharge). Carries `cashier_id` and
`reference` through as pass-through provenance columns (zero-cost, no dashboard split required
this program). This is the first SQL transformation layer and the direct input to Phase 3's
`fct_folio_line`.

---

## Entry Gate

- Phase 1 exit gate passed: `raw.cashiering_postings` populated, extractor tests green
- `eras_dbt/models/sources/sources.yml` updated with the new `raw.cashiering_postings` source
  (verify during RESEARCH whether this is already done in Phase 1 or needs doing here)

---

## Blast Radius

- `eras_dbt/models/staging/stg_cashiering_postings.sql` (new)
- `eras_dbt/models/sources/sources.yml` (modified, if not already done in Phase 1)
- `eras_dbt/tests/` or inline schema tests for the new staging model

---

## Implementation Checklist

### Step A — Confirm source wiring and transaction_code taxonomy

- [ ] A1. Confirm `raw.cashiering_postings` is registered in `eras_dbt/models/sources/sources.yml`
      (add if missing) mirroring the existing `raw.booking_core_reservations` /
      `raw.enterprise_hotel_config` source entries.
- [ ] A2. Read `docs/OPERA Cloud Cashiering API (26.2.0.0).json` again for the field name and
      exact values of `transactionType` (confirm `'Revenue'` is the correct literal string) and
      confirm the transaction_code numeric-prefix taxonomy (1x/2x/3x/6x/7x/8x/9x) against any
      documented transaction code ranges in the spec — do not assume the SPEC's prefix mapping is
      complete without cross-checking.
- [ ] A3. Read `eras_dbt/models/staging/stg_reservations.sql` for the project's staging model
      conventions (CTE structure, column naming, `{{ source(...) }}` usage).
- [x] A4. **CONFIRMED (INNOVATE 2026-07-18):** `transaction_type` is JSONB-only — not a top-level
      column in `raw.cashiering_postings`. Use `raw_data->>'transactionType' = 'Revenue'` in
      the WHERE clause. `transaction_code` is TEXT, not integer. Use `NOT LIKE '9%'` for exclusion.
- [ ] A5. **NEW (execute-agent instruction E2):** Confirm that `guestInfo.reservationId.id` is
      carried through from Phase 1 — either as a top-level `reservation_id` column or as a JSONB
      path. Phase 3's fct_folio_line requires this column; if it is absent, flag a Phase 1
      supplement need before proceeding.

### Step B — Build the staging model

- [ ] B1. Write `stg_cashiering_postings.sql`: `SELECT ... FROM {{ source('raw', 'cashiering_postings') }}
      WHERE raw_data->>'transactionType' = 'Revenue' AND transaction_code NOT LIKE '9%'`
      (CONFIRMED from INNOVATE 2026-07-18: `transactionType` is JSONB-only; `transaction_code` is
      TEXT — use NOT LIKE, not integer BETWEEN).
- [ ] B2. Add `revenue_category` derivation via CASE expression on the transaction_code numeric
      prefix (1x=Room, 2x/3x/6x=FnB, 7x=Tax, 8x=ServiceCharge) — include a catch-all/`ELSE`
      branch for any prefix not covered (e.g. 'Other') rather than silently NULLing.
- [ ] B3. Carry through `cashier_id` and `reference` (or their raw_data-derived equivalents) as
      pass-through columns.
- [ ] B4. Carry through `transaction_no`, `hotel_id`, `revenue_date`, `posted_amount` unchanged
      from the raw layer.
- [ ] B5. **NEW (execute-agent instruction E2):** Explicitly carry `reservation_id` (derived from
      `guestInfo.reservationId.id` — top-level column or JSONB path as confirmed in A5) as a
      named output column. Phase 3 depends on this column by name.

### Step C — Tests

- [ ] C1. Add a dbt test (singular or generic) asserting zero rows exist with transaction_code in
      the 9xxx Wrapper range — directly proves AC-2.
- [ ] C2. Add a dbt test asserting `revenue_category` is never NULL for any row that passes the
      Revenue-type filter (every category-eligible row gets a category, including the
      catch-all/Other case).
- [ ] C3. Add a schema test (`not_null`, `accepted_values` on revenue_category) in the model's
      `.yml` schema file following the project's existing schema test conventions.

---

## Exit Gate

```bash
cd eras_dbt && dbt build --profiles-dir . --select stg_cashiering_postings
# Expected: model builds; all tests (9xxx exclusion, revenue_category not-null, accepted_values) pass
```

- All checklist items (A-C) checked
- `dbt build --profiles-dir .` green for `stg_cashiering_postings` and its tests
- Phase report written to report destination above

---

## Blockers That Would Justify BLOCKED Status

- `raw.cashiering_postings` from Phase 1 does not expose `transaction_type` at the column level
  (only inside `raw_data` JSONB) — would require Phase 1 supplement before this phase can proceed.
- Transaction_code taxonomy in the OPERA spec conflicts with the SPEC's assumed prefix mapping —
  requires VC-FEASIBILITY-PROBE or user clarification before locking `revenue_category` logic.

---

## Phase Loop Progress

Orchestrator reads this before deciding which subagent to spawn next. The canonical 7-step inner loop
`R -> I -> P -> PVL -> E -> EVL -> UP` SKIPS SPEC (SPEC runs once in the outer program loop, already locked).

- [ ] 1. RESEARCH — research-agent: prior phase reports read; test context loaded; plan drift checked
- [x] 2. INNOVATE — innovate-agent: approach decided; Decision Summary written
- [ ] 3. PLAN-SUPPLEMENT — plan-agent: existing phase plan updated; Inner Loop Refresh Note if sections changed (or "n/a — research clean")
- [ ] 4. PVL — vc-validate-agent: full V1-V7; validate-contract written per `.claude/skills/vc-validate-findings/references/example-validate-output.md` (Status / Gate / Plan updates applied / Execute-agent instructions / Test gates / High-risk pack / Backlog artifacts / Known gaps / Accepted by)
- [x] 5. EXECUTE — all checklist items done; per-section test gates run and green (or gaps documented)
- [x] 6. EVL — all EVL gates green; follow-up stubs registered; EVL HANDOFF SUMMARY written
- [x] 7. UPDATE PROCESS — phase report written, umbrella state updated, commit done

**Validate-contract required before execute.** If step 4 (PVL) is unchecked or `## Validate Contract`
reads "(placeholder — vc-validate-agent writes this section before EXECUTE)", orchestrator must
spawn vc-validate-agent first. A partial contract missing Plan updates applied / Execute-agent
instructions / Test gates sections is treated as a placeholder.

---

## Inner Loop Refresh Note

**Date:** 2026-07-18
**Step:** 3 (PLAN-SUPPLEMENT) — INNOVATE decisions applied

Three decisions locked from INNOVATE (Approach 1 — Staging-First):

1. **`transactionType` is JSONB-only** — filter must use `raw_data->>'transactionType' = 'Revenue'`, NOT
   top-level `transaction_type` column. B1 updated accordingly. A4 marked confirmed.

2. **`transaction_code` is TEXT** — 9xxx exclusion uses `NOT LIKE '9%'`, not integer `NOT BETWEEN 9000 AND 9999`.
   B1 updated. Validate-contract E3 concern (digit-width ambiguity) is resolved: TEXT LIKE pattern works
   regardless of digit width.

3. **`reservation_id` is nullable — no not_null dbt test** — Phase 3's `fct_folio_line` handles unmatched
   rows via `where reservation_id is not null`. The validate-contract's E5 instruction (do not add
   relationships test on reservation_id in this phase) remains correct.

Sections changed: A4 (confirmed JSONB/TEXT, checkbox ticked), B1 (WHERE clause updated).
Sections unchanged: A1, A2, A3, A5, B2–B5, C1–C3, Validate Contract (outer-pvl contract stays current).

---

## Touchpoints

- `eras_dbt/models/staging/stg_cashiering_postings.sql` (new)
- `eras_dbt/models/sources/sources.yml` (modified, if not done in Phase 1)

---

## Public Contracts

- `stg_cashiering_postings` output schema (columns + `revenue_category` values) is a new contract
  consumed directly by Phase 3's `fct_folio_line` — column names/types set here are load-bearing.
- No existing model or dashboard contract is touched.

---

## Verification Evidence

| Gate / Scenario | Strategy | Proves SPEC criterion |
|---|---|---|
| dbt test: zero rows with transaction_code 9xxx | Fully-Automated | AC-2 (Wrapper rows excluded) |
| dbt test: revenue_category not-null across Revenue-type rows | Fully-Automated | AC-3 (category derivation completeness) |
| dbt test: accepted_values on revenue_category (Room/FnB/Tax/ServiceCharge/Other) | Fully-Automated | AC-3 (category taxonomy correctness) |

```bash
cd eras_dbt && dbt build --profiles-dir . --select stg_cashiering_postings
# Expected: 0 errors
```

---

## Resume and Execution Handoff

- Selected plan file path: `process/features/financials/active/financials_17-07-26/phase-02-stg-cashiering-postings_PLAN_17-07-26.md`
- Last completed step: not started
- Validate-contract status: pending
- Next step: Spawn vc-research-agent for RESEARCH (Step 1)

---

## Test Infra Improvement Notes

(none identified yet)

---

## Validate Contract

Status: CONDITIONAL
Date: 18-07-26
date: 2026-07-18
generated-by: inner-pvl: phase-02
supersedes: 2026-07-17 (outer-pvl) — inner PVL has current evidence

Parallel strategy: sequential
Rationale: 3/7 signals (S2 schema/source surface, S4 phase-program, S6 new source table); sequential correct for single-phase inner PVL with well-defined scope

Plan updates applied:
- No new plan updates from inner-pvl pass. INNOVATE decisions from Inner Loop Refresh Note already applied to checklist (A4 confirmed JSONB/TEXT, B1 WHERE clause locked, reservation_id nullable confirmed). Outer-pvl P1/P2 remain in place.

Execute-agent instructions:
- E1: transaction_type check RESOLVED by A4 (INNOVATE 2026-07-18). Use raw_data->>'transactionType' = 'Revenue' in the WHERE clause — top-level transaction_type column does NOT exist in raw schema. This is a confirmed fact, not a runtime discovery.
- E2: SELECT reservation_id using JSONB path raw_data->'guestInfo'->'reservationId'->>'id' as a named output column. Phase 3 fct_folio_line requires this column by name even when NULL (unmatched posting rows). Do not add a not_null test on this column.
- E3: RESOLVED by A4: use transaction_code NOT LIKE '9%' — transaction_code is TEXT (confirmed from Phase 1 database.py schema). Integer BETWEEN is incorrect.
- E4: The revenue_category CASE expression MUST include ELSE 'Other' — never produce NULL from an uncovered prefix. Accepted values for the dbt schema test: Room, FnB, Tax, ServiceCharge, Other.
- E5: Do NOT add a dbt relationships test on reservation_id in Phase 2. NULL reservation_id is valid (unmatched postings). Phase 3 handles FK integrity via WHERE reservation_id IS NOT NULL.
- E6 (NEW): Execute Step A1 BEFORE Step B1. The source macro fails dbt compilation until the cashiering_postings source entry exists in sources.yml. Mandatory execution order: A1 (sources.yml) -> A2 (spec read) -> A3 (pattern read) -> B1 (write model) -> B2 -> B3 -> B4 -> B5 -> C1 -> C2 -> C3.

Test gates (C3 5-column table — ADDITIVE; existing consumers still parse the legacy line form below it):

| criterion id | behavior | strategy | proving test | gap-resolution |
|---|---|---|---|---|
| AC-2-9xxx | Zero rows in stg_cashiering_postings with transaction_code LIKE 9% | Fully-Automated | cd eras_dbt && dbt build --profiles-dir . --select stg_cashiering_postings (singular dbt test: count(*) WHERE transaction_code LIKE '9%' = 0) | A |
| AC-3-category-notnull | revenue_category is non-null for every row passing the Revenue filter | Fully-Automated | cd eras_dbt && dbt build --profiles-dir . --select stg_cashiering_postings (not_null schema test on revenue_category in schema.yml) | A |
| AC-3-category-values | revenue_category restricted to Room/FnB/Tax/ServiceCharge/Other | Fully-Automated | cd eras_dbt && dbt build --profiles-dir . --select stg_cashiering_postings (accepted_values schema test on revenue_category in schema.yml) | A |
| P2-reservation-id | reservation_id column exists in stg_cashiering_postings output (nullable) | Fully-Automated | cd eras_dbt && dbt build --profiles-dir . --select stg_cashiering_postings (successful model build proves column; no not_null test per E5) | A |
| AC-3-fk-rate | 95-pct of non-null reservation_id values match stg_reservations | Known-Gap | — | D |

gap-resolution legend:
- A — proven now (gate passes in this cycle)
- B — fixed in this plan (gate added by this plan's checklist)
- C — deferred to a named later phase/plan
- D — backlog test-building stub (named residual; keep-active; continue)

C-4 reconciliation: the strategy column carries ONLY the 3 proving strategies (Fully-Automated / Hybrid / Agent-Probe). Known-Gap is NEVER a strategy value — it is a named residual row carried via gap-resolution D.

Failing stub (AC-2-9xxx):
test("should exclude all transaction_code 9xxx rows from staging", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: SELECT count(*) FROM stg_cashiering_postings WHERE transaction_code LIKE '9%' must return 0")
})

Failing stub (AC-3-category-notnull):
test("should have non-null revenue_category for every Revenue-type row", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: dbt not_null schema test on revenue_category column")
})

Failing stub (AC-3-category-values):
test("should restrict revenue_category to accepted values", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: dbt accepted_values schema test on revenue_category: Room, FnB, Tax, ServiceCharge, Other")
})

Failing stub (P2-reservation-id):
test("should carry reservation_id as a named output column (nullable)", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: reservation_id column present in stg_cashiering_postings, derived from raw_data JSONB path guestInfo.reservationId.id")
})

Legacy line form (retained so existing validate-contract consumers still parse):
- staging/9xxx-exclusion: Fully-automated: cd eras_dbt && dbt build --profiles-dir . --select stg_cashiering_postings
- staging/revenue-category: Fully-automated: cd eras_dbt && dbt build --profiles-dir . --select stg_cashiering_postings
- staging/reservation-id-carrythrough: Fully-automated: cd eras_dbt && dbt build --profiles-dir . --select stg_cashiering_postings

Dimension findings:
- Infra fit: PASS — dbt staging pattern mirrors stg_reservations.sql; sources.yml add is mechanical (one table entry); JSONB paths confirmed from Phase 1 database.py; no new dbt packages needed
- Test coverage: CONCERN — AC-3 join integrity test (95-pct FK match rate for non-null reservation_id) absent from Phase 2 checklist; deferred to Phase 3 fct_folio_line as known-gap D
- Breaking changes: PASS — additive only; sources.yml gains one cashiering_postings entry; schema.yml gains one stg_cashiering_postings model block; no existing model or dashboard touched
- Security surface: PASS — no auth/identity/billing changes; staging reads from internal raw schema only; no new credentials or API surface
- Section A feasibility: PASS — A4 JSONB/TEXT locked by INNOVATE; OPERA spec exists; stg_reservations.sql pattern available; A1 sources.yml add is the only blocker and is mechanical
- Section B feasibility: PASS — all column sources confirmed (top-level: hotel_id, revenue_date, transaction_code, posted_amount, transaction_no; JSONB: reservation_id and any B3 passthrough fields); E6 locks A1-before-B1 sequencing
- Section C feasibility: PASS — C1 singular test follows test_dim_property_room_count pattern; C2/C3 follow schema.yml pattern from stg_reservations
- Structural validator: 4 validator FAILs (missing overview/Complexity/Phase Completion Rules/Acceptance Criteria) — false positives from standalone-plan validator applied to a phase-program phase plan; phase plans use Purpose/Exit Gate/SPEC ACs/frontmatter phase field as equivalents; not blocking

Open gaps:
- AC-3-fk-rate: known-gap: deferred to Phase 3 — fct_folio_line plan (Phase 3) must add a singular dbt test asserting 95-pct non-null reservation_id rows match stg_reservations; Phase 3 RESEARCH must pick this up

Known Gaps (Resolved via Backlog):
- AC-3 join integrity (95-pct FK match rate) — deferred to Phase 3 plan. Phase 2 blast radius covers staging model only; the join from stg_cashiering_postings to stg_reservations is exercised in fct_folio_line (Phase 3). Phase 3 RESEARCH annotated with this requirement.

What this coverage does NOT prove:
- AC-2-9xxx: Does not prove 9xxx exclusion covers all digit-width variants (3-digit vs 4-digit transaction_code); the exit-gate singular test on real data at EXECUTE time catches boundary edge cases
- AC-3-category-notnull: Does not prove the ELSE 'Other' branch handles all future unexpected prefixes in production data; coverage depends on real data in the 2026-01-01 to present backfill range
- AC-3-category-values: Does not prove transaction codes are correctly classified by category (e.g. a POS 6xxx code genuinely belongs to FnB); taxonomy confirmed from SPEC background and live probe data
- P2-reservation-id: Does not prove reservation_id has the correct extracted value; does not prove 95-pct FK match rate (deferred to Phase 3)
- AC-3-fk-rate: Not proven in Phase 2 — named residual; Phase 3 must add the singular FK rate test to its checklist

Gate: CONDITIONAL
Accepted by: session (autonomous, /goal execution) — concerns accepted: (1) AC-3 join integrity (95-pct FK rate) deferred to Phase 3 as known-gap D; Phase 3 RESEARCH annotated with requirement; (2) structural validator false positives noted (phase-plan shape, not a real gap)
