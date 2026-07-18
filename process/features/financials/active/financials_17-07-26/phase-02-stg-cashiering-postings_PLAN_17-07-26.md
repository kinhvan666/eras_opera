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
- [ ] A4. **NEW (execute-agent instruction E1):** Confirm whether `transaction_type` is a
      top-level column in `raw.cashiering_postings` OR must be extracted from `raw_data` JSONB.
      If Phase 1 stored it only in JSONB, use `raw_data->>'transactionType'` in the WHERE clause.
      Do NOT assume the column exists at the top level before reading the actual Phase 1 schema.
- [ ] A5. **NEW (execute-agent instruction E2):** Confirm that `guestInfo.reservationId.id` is
      carried through from Phase 1 — either as a top-level `reservation_id` column or as a JSONB
      path. Phase 3's fct_folio_line requires this column; if it is absent, flag a Phase 1
      supplement need before proceeding.

### Step B — Build the staging model

- [ ] B1. Write `stg_cashiering_postings.sql`: `SELECT ... FROM {{ source('raw', 'cashiering_postings') }}
      WHERE transaction_type = 'Revenue' AND transaction_code NOT BETWEEN 9000 AND 9999` (or
      equivalent prefix check) — confirm the exact exclusion boundary for "9xxx" (900-999 vs
      9000-9999 depending on transaction_code digit width) during research, not by assumption.
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
Date: 17-07-26
date: 2026-07-17
generated-by: outer-pvl

Parallel strategy: sequential
Rationale: 3/7 signals (S4 phase-program, S6 schema/source.yml, S7 3 blast-radius files); sequential correct; Phase 2 depends on Phase 1 output with a known data-shape ambiguity that must be resolved at RESEARCH before branching

Plan updates applied:
- P1: Added Step A4 — execute-agent must check whether `transaction_type` is top-level column or JSONB before writing the WHERE clause
- P2: Added Step A5 — execute-agent must confirm `reservation_id` (from `guestInfo.reservationId.id`) is carried through from Phase 1; added Step B5 to explicitly name it in the SELECT

Execute-agent instructions:
- E1: Before writing the staging model WHERE clause, read the actual `raw.cashiering_postings` table schema (or Phase 1 source code) to confirm `transaction_type` is a top-level column. If it is only in `raw_data` JSONB, use `raw_data->>'transactionType' = 'Revenue'` in the filter, NOT `transaction_type = 'Revenue'`. This is a BLOCKER if not confirmed — do not assume.
- E2: Explicitly SELECT `reservation_id` (from top-level column or JSONB path `raw_data->'guestInfo'->'reservationId'->>'id'`) as a named output column. Phase 3 builds `fct_folio_line` with `reservation_id IS NULL` for unmatched rows — the column must exist even when NULL. If Phase 1 did not extract this as a top-level column, extract it from JSONB here.
- E3: For 9xxx exclusion — use `transaction_code NOT LIKE '9%'` if transaction_code is a string, or `transaction_code NOT BETWEEN 9000 AND 9999` if integer. Confirm the data type from Phase 1 schema before writing the filter. The SPEC uses "9xxx prefix" language which is range-dependent on digit width.
- E4: The `revenue_category` CASE expression must have an ELSE 'Other' branch — never produce NULL from a missing prefix. Accepted values for the dbt test: Room, FnB, Tax, ServiceCharge, Other. If any unexpected prefix appears in real data, it is classified 'Other' and visible in reconciliation queries.
- E5: Do NOT add a dbt `relationships` test on `reservation_id` in THIS phase (Phase 2). The unmatched-postings use case means NULL reservation_id is valid and common. A relationships test with NULLs would fail. Phase 3's fct_folio_line handles this via `where reservation_id is not null` on the relationships test.

Test gates (C3 5-column table):

| criterion id | behavior | strategy | proving test | gap-resolution |
|---|---|---|---|---|
| AC-2-9xxx | Zero rows in stg_cashiering_postings with transaction_code in 9xxx range | Fully-Automated | `cd eras_dbt && dbt build --profiles-dir . --select stg_cashiering_postings` (singular dbt test: SELECT count(*) FROM stg_cashiering_postings WHERE transaction_code LIKE '9%' OR ... = 0) | A |
| AC-3-category-notnull | revenue_category is non-null for every row that passes the Revenue filter | Fully-Automated | `cd eras_dbt && dbt build --profiles-dir . --select stg_cashiering_postings` (not_null schema test on revenue_category column) | A |
| AC-3-category-values | revenue_category values restricted to Room/FnB/Tax/ServiceCharge/Other | Fully-Automated | `cd eras_dbt && dbt build --profiles-dir . --select stg_cashiering_postings` (accepted_values schema test on revenue_category) | A |
| P2-reservation-id | reservation_id column exists in stg_cashiering_postings output (nullable for unmatched rows) | Fully-Automated | `cd eras_dbt && dbt build --profiles-dir . --select stg_cashiering_postings` (not_null test is intentionally SKIPPED for reservation_id; column existence proven by successful model build) | A |

Failing stub (AC-2-9xxx):
test("should exclude all transaction_code 9xxx rows from staging", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: SELECT count(*) FROM stg_cashiering_postings WHERE transaction_code LIKE '9%' must return 0")
})

Failing stub (AC-3-category-notnull):
test("should have non-null revenue_category for every Revenue-type row", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: dbt not_null test on revenue_category")
})

Failing stub (AC-3-category-values):
test("should restrict revenue_category to accepted values", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: dbt accepted_values test on revenue_category")
})

Failing stub (P2-reservation-id):
test("should carry reservation_id as a named output column (nullable)", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: reservation_id column present in stg_cashiering_postings")
})

gap-resolution legend:
- A — proven now (gate passes in this cycle)
- B — fixed in this plan (gate added by this plan's checklist)
- C — deferred to a named later phase/plan
- D — backlog test-building stub (named residual; keep-active; continue)

Legacy line form:
- staging/9xxx-exclusion: Fully-automated: `cd eras_dbt && dbt build --profiles-dir . --select stg_cashiering_postings`
- staging/revenue-category: Fully-automated: `cd eras_dbt && dbt build --profiles-dir . --select stg_cashiering_postings`
- staging/reservation-id-carrythrough: Fully-automated: `cd eras_dbt && dbt build --profiles-dir . --select stg_cashiering_postings`

Dimension findings:
- Infra fit: PASS — dbt staging pattern mirrors stg_reservations.sql; sources.yml pattern already proven; no new dbt packages needed
- Test coverage: PASS — all AC-2 (9xxx) and AC-3 (category) gates are fully-automated dbt tests; reservation_id carrythrough proven by model build success
- Breaking changes: PASS — additive new model only; sources.yml gains one entry (existing entries unchanged); no existing model or dashboard reads stg_cashiering_postings yet
- Security surface: PASS — no auth/identity/billing changes; staging model reads from internal raw schema only; no new credentials or API surface

Open gaps:
- transaction_type column availability: CONCERN deferred to RESEARCH (Step A4) — if only in JSONB, execute-agent must adjust the WHERE clause; not a FAIL because both code paths are well-defined
- transaction_code digit width: CONCERN deferred to RESEARCH (Step A2/B1) — determines exact 9xxx boundary; caught by the zero-rows dbt test at exit gate

What this coverage does NOT prove:
- AC-2-9xxx: Does not prove the transaction_code digit width is correct (4-digit vs 3-digit changes the boundary); the exit-gate test on real data catches this at EXECUTE time
- AC-3-category-notnull: Does not prove the ELSE 'Other' branch handles all real-world unexpected prefixes correctly — coverage depends on real data in the backfill range
- P2-reservation-id: Does not prove reservation_id has the correct value (correct guestInfo.reservationId.id extraction) — spot-check recommended at Phase 3 RESEARCH

Gate: CONDITIONAL
Accepted by: session (autonomous, /goal execution) — concerns: transaction_type column availability deferred to RESEARCH (E1); reservation_id carrythrough plan fix applied (P1/P2); both are resolvable at RESEARCH + EXECUTE without plan restructuring
