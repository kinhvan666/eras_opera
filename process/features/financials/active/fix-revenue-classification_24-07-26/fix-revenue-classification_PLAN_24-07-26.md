---
name: plan:fix-revenue-classification
description: "Fix dbt revenue classification bug — 13 unmatched 7xxx/8xxx transaction codes incorrectly treated as tax postings, causing ~240M revenue understatement"
date: 24-07-26
feature: financials
phase: PLAN
---

# Implementation Plan: Fix Revenue Classification Bug in stg_cashiering_postings

**Date**: 2026-07-24
**Status**: PLANNED
**Complexity**: COMPLEX (single-file fix but high blast radius — touches the core revenue calculation pipeline)
**Fix Approach**: Combined guard — restructure `net_amount` CASE to separate matched vs unmatched tax detection, plus safe `COALESCE` default

## Overview

The dashboard reports July 2026 Total Revenue at 3.79B VND vs the OPERA Manager Report target of 3.55B VND — a gap of ~240M VND. Root cause: `stg_cashiering_postings.sql` mis-classifies 13 transaction codes (7xxx/8xxx prefix) whose `classification = 'Revenue'` in `stg_transaction_codes` but have no matching row in the LEFT JOIN (hotel_id mismatch).

The bug produces a net effect where revenue codes become negative in `net_amount`, creating a double-count gap (positive revenue becomes negative subtraction = 2x impact). One code alone (8118) accounts for a 228M VND gap.

## Goals

1. Fix `net_amount` calculation so unmatched 7xxx/8xxx transaction codes are not treated as tax postings
2. Preserve correct tax/service-charge subtraction for matched transaction codes
3. Dashboard July 2026 Total Revenue must match OPERA Manager Report within 1% (target: 3.55B)
4. No regression in existing test suite or dbt model integrity

## Scope

**In-scope:**
- `eras_dbt/models/staging/stg_cashiering_postings.sql` — `net_amount` CASE logic only

**Out-of-scope:**
- `revenue_category` column logic (minor categorization issue for unmatched codes — separate fix)
- Extractor changes
- Schema changes to `raw.cashiering_postings` or `analytics.stg_transaction_codes`
- Dashboard code changes

---

## Architecture Notes

### Bug Mechanism (4-step cascade)

```
1. 13 transaction codes (7100, 7102, 7104, 7106, 7108, 8100, 8102, 8104, 8106, 8114, 8118, 8120, 8902)
   have classification = 'Revenue' in analytics.stg_transaction_codes
2. LEFT JOIN on (transaction_code, hotel_id) produces NO MATCH → t.* is all NULL
3. COALESCE(t.tax_inclusive, true) defaults to true → assumes tax-inclusive
4. Prefix rules (transaction_code LIKE '7%' OR LIKE '8%') match → flips sign to negative
   → Revenue code 8118 (+114M) becomes -114M → 228M gap from one code
```

### Fix Design: Two-layer Classification Guard

The fix restructures the `net_amount` CASE expression into three branches:

| Branch | Condition | Action | Why |
|--------|-----------|--------|-----|
| A — Known Tax/ServiceCharge | `t.classification` matches Tax or ServiceCharge patterns | Subtract if `tax_inclusive = true` (use `COALESCE(t.tax_inclusive, true)`) | Matched codes — existing logic preserved |
| B — Unmatched prefix-based tax | `t.transaction_code IS NULL` AND prefix is 7xxx/8xxx | Subtract only if `tax_inclusive = true` (use `COALESCE(t.tax_inclusive, false)`) | Unmatched codes — default to NOT tax-inclusive (safer) |
| C — Everything else | All remaining rows | Pass through `posted_amount` as-is (revenue) | Revenue codes, unmatched non-tax prefixes |

**Key insight:** Branch B only fires for unmatched codes (no row in `stg_transaction_codes`). For matched 7xxx/8xxx tax codes, Branch A catches them via `t.classification`. For unmatched codes, defaulting `tax_inclusive` to `false` means revenue codes are not subtracted — and genuinely-unmatched tax codes contribute 0 to net_amount (a much smaller error than subtracting revenue).

### Why Combined Approach Over Single Options

**Option 1 alone (classification guard only):** Adds `AND t.classification != 'Revenue'` to prefix rules. Problem: `t.classification` is NULL for unmatched codes, so `NULL != 'Revenue'` evaluates to NULL (not TRUE) — the guard is ineffective for the exact case causing the bug.

**Option 2 alone (COALESCE default change only):** Changes `COALESCE(t.tax_inclusive, true)` → `COALESCE(t.tax_inclusive, false)` globally. Problem: genuine matched Tax/ServiceCharge codes without `tax_inclusive` set would also default to false, missing valid tax subtractions.

**Combined approach:** Branch A keeps `COALESCE(t.tax_inclusive, true)` for matched codes. Branch B uses `COALESCE(t.tax_inclusive, false)` for unmatched codes. Each branch gets the safe default for its context.

---

## Touchpoints

| File | Change type | What changes |
|------|-------------|--------------|
| `eras_dbt/models/staging/stg_cashiering_postings.sql` | Modify | `net_amount` CASE expression (lines 51-64) — restructure into 3 branches with classification guard |

**Read-only reference files:**
| File | Purpose |
|------|---------|
| `eras_dbt/models/staging/stg_transaction_codes.sql` | Understand LEFT JOIN partner columns |
| `eras_dbt/models/sources/sources.yml` | Verify source table references |
| `eras_dbt/models/staging/schema.yml` | Check existing dbt tests on stg_cashiering_postings |

## Public Contracts

**No API or schema changes.** This is a logic-only fix internal to one dbt model. Downstream models (`fct_folio_line`, dashboard queries) consume `stg_cashiering_postings.net_amount` — the column name and type are unchanged. Only the computed values change (become correct for the 13 misclassified codes).

## Blast Radius

- **Files modified:** 1 (`eras_dbt/models/staging/stg_cashiering_postings.sql`)
- **Packages touched:** dbt staging layer only
- **Downstream models affected:** `fct_folio_line` (reads `stg_cashiering_postings.net_amount`), dashboard queries
- **Risk class:** Low — no schema change, no auth/billing/secrets surface
- **Rollback surface:** Revert single file to previous commit

## Risk Assessment

### Risk Predictions

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Genuine unmatched 7xxx/8xxx tax codes now contribute 0 to net_amount (not subtracted) | Medium | Low (~tens of millions VND at most) | This is the correct conservative behavior — unmatched codes without classification data should not be assumed tax. If found, fix by ensuring transaction_codes table has complete data. |
| Revenue category for unmatched 8xxx codes stays 'Other' instead of 'FnB' | High | Low (~tens of millions VND miscategorized but not lost) | Out of scope for this fix. Separate follow-up if needed. |
| Regression in existing matched tax handling | Low | High | Branch A preserves existing logic verbatim. dbt test gate verifies. |
| dbt build failure due to SQL syntax error | Low | Medium | Syntax is straightforward CASE restructure. Dry-run via dbt compile first. |

### Rollback Plan

1. Revert `stg_cashiering_postings.sql` to previous commit: `git checkout HEAD~1 -- eras_dbt/models/staging/stg_cashiering_postings.sql`
2. Run `dbt build --select stg_cashiering_postings+ --profiles-dir .`
3. Confirm dashboard returns to pre-fix state

---

## Phase Completion Rules

- Plan is complete when all 4 sections (Touchpoints, Public Contracts, Blast Radius, Verification Evidence) are present and the validate-contract is written by vc-validate-agent
- EXECUTE is legal only after VALIDATE returns PASS or CONDITIONAL with accepted gaps
- The fix applies to exactly ONE file: `eras_dbt/models/staging/stg_cashiering_postings.sql`
- Verification is code-complete only after Gates 1-3 pass AND Gates 4-7 return expected results against live Postgres
- Phase reports must include: (a) pre-fix vs post-fix revenue totals, (b) the 13-code net_amount comparison, (c) dbt test results

---

## Implementation Checklist

### Pre-conditions

- [ ] **PC-1**: PostgreSQL container is running (`docker ps` shows `erasopera-postgres-1`)
- [ ] **PC-2**: `eras_dbt/.user.yml` credentials are valid
- [ ] **PC-3**: Current `dbt build` succeeds on `stg_cashiering_postings` (baseline)
- [ ] **PC-4**: Baseline diagnostic query confirms the 13 misclassified codes exist and produce negative `net_amount`:

```sql
SELECT transaction_code, SUM(net_amount) as total_net
FROM analytics.stg_cashiering_postings
WHERE revenue_date >= '2026-07-01' AND revenue_date < '2026-08-01'
  AND transaction_code IN ('8118','7108','8100','7100','8120','8102','8114','8106','7102','7106','8104','7104','8902')
GROUP BY transaction_code
ORDER BY total_net ASC;
```

### Step 1: Apply the fix to `stg_cashiering_postings.sql`

**File:** `eras_dbt/models/staging/stg_cashiering_postings.sql`
**Change:** Replace the `net_amount` CASE expression (lines 51-64) with the three-branch classification-aware logic below.

**Current code (lines 51-64):**
```sql
        -- net_amount calculation: Tax and ServiceCharge subtracts from gross
        case
            when (
                t.classification like '{{ "{%" }}%"Tax"%' or t.classification like '{{ "{%" }}%"ServiceCharge"%'
                or t.classification like '%"Tax"%' or t.classification like '%"ServiceCharge"%'
                or t.classification in ('Tax', 'ServiceCharge')
                or s.transaction_code like '7%' or s.transaction_code like '8%'
            ) then
                case 
                    when coalesce(t.tax_inclusive, true) = true then -coalesce(s.posted_amount::numeric, 0)
                    else 0
                end
            else coalesce(s.posted_amount::numeric, 0)
        end                                                               as net_amount
```

**Replacement code:**
```sql
        -- net_amount calculation: Tax and ServiceCharge subtracts from gross
        -- Three-branch classification-aware logic:
        --   A) Known Tax/ServiceCharge by t.classification (matched codes) → subtract if tax_inclusive
        --   B) Unmatched codes with 7xxx/8xxx prefix → subtract ONLY if tax_inclusive=true (default: false — safer)
        --   C) Everything else → revenue, pass through as-is
        case
            -- Branch A: Matched Tax/ServiceCharge codes (t.classification tells us it's tax)
            when (
                t.transaction_code is not null
                and (
                    t.classification like '{{ "{%" }}%"Tax"%' or t.classification like '{{ "{%" }}%"ServiceCharge"%'
                    or t.classification like '%"Tax"%' or t.classification like '%"ServiceCharge"%'
                    or t.classification in ('Tax', 'ServiceCharge')
                )
            ) then
                case
                    when coalesce(t.tax_inclusive, true) = true then -coalesce(s.posted_amount::numeric, 0)
                    else 0
                end
            -- Branch B: Unmatched codes with 7xxx/8xxx prefix (unknown classification — use prefix heuristic)
            -- Default tax_inclusive to FALSE for unmatched codes: safer to not-subtract revenue than to subtract it
            when (
                t.transaction_code is null
                and (s.transaction_code like '7%' or s.transaction_code like '8%')
            ) then
                case
                    when coalesce(t.tax_inclusive, false) = true then -coalesce(s.posted_amount::numeric, 0)
                    else 0
                end
            -- Branch C: Revenue codes and all other unmatched codes
            else coalesce(s.posted_amount::numeric, 0)
        end                                                               as net_amount
```

**Key changes from current code:**
1. Branch A (matched tax): added `t.transaction_code is not null` guard — only fires when JOIN succeeded
2. Branch B (unmatched prefix): NEW branch — catches unmatched 7xxx/8xxx codes with `COALESCE(t.tax_inclusive, false)` safe default
3. Branch C (revenue): unchanged — passes through `posted_amount` as-is
4. Removed `or s.transaction_code like '7%' or s.transaction_code like '8%'` from Branch A — these codes now route through Branch B when unmatched

### Step 2: Validate syntax with dbt compile

```bash
cd D:/ErasProjects/ErasOpera/eras_dbt && dbt compile --select stg_cashiering_postings --profiles-dir .
```

**Expected:** Compiles without errors. If compilation fails, check Jinja escaping of `{%` and `%}` in the LIKE patterns.

### Step 3: Rebuild stg_cashiering_postings

```bash
cd D:/ErasProjects/ErasOpera/eras_dbt && dbt run --select stg_cashiering_postings --profiles-dir .
```

**Expected:** Model rebuilds successfully. Row count unchanged from pre-fix.

### Step 4: Rebuild downstream models

```bash
cd D:/ErasProjects/ErasOpera/eras_dbt && dbt run --select stg_cashiering_postings+ --profiles-dir .
```

**Expected:** `fct_folio_line` and any other downstream models rebuild without errors.

### Step 5: Run dbt tests

```bash
cd D:/ErasProjects/ErasOpera/eras_dbt && dbt test --select stg_cashiering_postings+ --profiles-dir .
```

**Expected:** All existing dbt tests pass (no regression).

### Step 6: Verify the 13 misclassified codes are no longer negative

```sql
-- Verify all 13 codes now have net_amount >= 0 or 0 (not negative)
SELECT transaction_code, SUM(net_amount) as total_net, COUNT(*) as row_count
FROM analytics.stg_cashiering_postings
WHERE revenue_date >= '2026-07-01' AND revenue_date < '2026-08-01'
  AND transaction_code IN ('8118','7108','8100','7100','8120','8102','8114','8106','7102','7106','8104','7104','8902')
GROUP BY transaction_code
ORDER BY total_net ASC;
```

**Expected:** All 13 codes have `total_net >= 0`. Previously, these codes had negative `total_net`.

### Step 7: Verify July 2026 totals match OPERA Manager Report targets

```sql
-- Total Revenue — target: ~3.55B
SELECT SUM(net_amount) as total_revenue
FROM analytics.stg_cashiering_postings
WHERE revenue_date >= '2026-07-01' AND revenue_date < '2026-08-01';

-- Revenue by category — targets: FnB ~2.43B, Room ~1.107B
SELECT revenue_category, SUM(net_amount) as category_total
FROM analytics.stg_cashiering_postings
WHERE revenue_date >= '2026-07-01' AND revenue_date < '2026-08-01'
GROUP BY revenue_category
ORDER BY category_total DESC;
```

**Expected:** Total Revenue within 1% of 3.55B VND. FnB within 1% of 2.43B. Room within 1% of 1.107B.

### Step 8: Verify no regression in matched tax handling

```sql
-- Compare pre-fix vs post-fix net_amount for matched tax codes
-- (codes with t.classification in ('Tax', 'ServiceCharge') AND matched in stg_transaction_codes)
-- These should be UNCHANGED — the fix only affects unmatched codes
SELECT
    'pre' as version,
    -- ... (run against pre-fix state)
-- For practical verification: pick a known matched tax code and confirm its net_amount is unchanged
-- after the fix (Branch A logic is identical to the original logic for matched codes)
```

**Gate:** Spot-check 3-5 known matched tax codes to confirm their `net_amount` values are identical to pre-fix values.

---

## Verification Evidence

| Gate / Scenario | Strategy | Proves SPEC criterion |
|-----------------|----------|----------------------|
| Gate 1: `dbt compile --select stg_cashiering_postings` exits 0 | Fully-Automated | AC-6: dbt build succeeds |
| Gate 2: `dbt run --select stg_cashiering_postings` exits 0, row count unchanged | Fully-Automated | AC-6: dbt build succeeds |
| Gate 3: `dbt test --select stg_cashiering_postings+` all pass | Fully-Automated | AC-5: No regression in existing tests |
| Gate 4: SQL query — all 13 misclassified codes have `net_amount >= 0` | Fully-Automated | AC-4: Misclassified codes no longer negative |
| Gate 5: SQL query — July 2026 Total Revenue within 1% of 3.55B VND | Hybrid (requires live Postgres + data) | AC-1: Revenue matches Manager Report |
| Gate 6: SQL query — July 2026 FnB within 1% of 2.43B VND | Hybrid | AC-2: FnB matches Manager Report |
| Gate 7: SQL query — July 2026 Room within 1% of 1.107B VND | Hybrid | AC-3: Room matches Manager Report |
| Gate 8: Spot-check 3-5 matched tax codes — `net_amount` unchanged from pre-fix | Hybrid | AC-5: No regression in tax handling |
| Gate 9: Dashboard manual check — Revenue tab shows correct totals | Agent-Probe | AC-1: Revenue matches Manager Report (visual confirmation) |

Failing stubs for Gates 4-8 (SQL assertion queries — run via psql or dbt):
```sql
-- Gate 4 stub: All 13 codes non-negative
DO $$ DECLARE bad_count INT;
BEGIN
  SELECT COUNT(*) INTO bad_count
  FROM analytics.stg_cashiering_postings
  WHERE revenue_date >= '2026-07-01' AND revenue_date < '2026-08-01'
    AND transaction_code IN ('8118','7108','8100','7100','8120','8102','8114','8106','7102','7106','8104','7104','8902')
    AND net_amount < 0;
  IF bad_count > 0 THEN
    RAISE EXCEPTION 'NOT IMPLEMENTED — FAIL: % codes still have negative net_amount', bad_count;
  END IF;
END $$;
```

---

## Test Infra Improvement Notes

- dbt tests currently validate `not_null` and `unique` constraints on `stg_cashiering_postings` but have no assertion on `net_amount` sign correctness for specific transaction code prefixes. Consider adding a singular dbt test (`test_net_amount_non_negative_for_revenue_codes.sql`) that asserts `net_amount >= 0` for codes with `classification = 'Revenue'` in `stg_transaction_codes`.
- No CI pipeline — all verification is manual against live Postgres. Document results in the phase report.

---

## Resume and Execution Handoff

1. **Selected plan file path:** `process/features/financials/active/fix-revenue-classification_24-07-26/fix-revenue-classification_PLAN_24-07-26.md`
2. **Last completed phase or step:** PLAN — plan artifact written, not yet validated
3. **Validate-contract status:** Pending (vc-validate-agent writes the section)
4. **Supporting context files loaded:**
   - `process/context/all-context.md`
   - `process/context/tests/all-tests.md`
   - `process/context/database/all-database.md` (routing table entry)
   - `process/features/financials/active/_GUIDE.md`
   - `process/general-plans/active/manager_report_RCA_20260724.md` (RCA findings)
   - `process/general-plans/active/revenue-bug_23-07-26/revenue-bug_REPORT_23-07-26.md` (prior bug investigation)
5. **Next step for a fresh agent picking up mid-execution:**
   - Read this plan file in full
   - Run `find process/context/ -type f` and follow routing
   - Start at Implementation Checklist Step 1 (apply fix to `stg_cashiering_postings.sql`)
   - Run Steps 2-8 in sequence
   - Report results in a `fix-revenue-classification_REPORT_24-07-26.md` in the same task folder

---

## Validate Contract

Status: CONDITIONAL
Date: 24-07-26
date: 2026-07-24
generated-by: outer-pvl

Parallel strategy: sequential
Rationale: 0/7 signals — single-file dbt model fix, no schema/API/auth, low risk

Test gates:

| criterion id | behavior | strategy | proving test | gap-resolution |
|---|---|---|---|---|
| AC-6 | dbt compile succeeds on modified stg_cashiering_postings | Fully-Automated | `cd D:/ErasProjects/ErasOpera/eras_dbt && dbt compile --select stg_cashiering_postings --profiles-dir .` | A |
| AC-6 | dbt run succeeds, row count unchanged from pre-fix | Fully-Automated | `cd D:/ErasProjects/ErasOpera/eras_dbt && dbt run --select stg_cashiering_postings --profiles-dir .` | A |
| AC-5, AC-7 | All existing dbt tests pass on stg_cashiering_postings and downstream — no regression | Fully-Automated | `cd D:/ErasProjects/ErasOpera/eras_dbt && dbt test --select stg_cashiering_postings+ --profiles-dir .` | A |
| AC-4 | All 13 previously-misclassified codes have net_amount >= 0 | Fully-Automated | SQL via psql: `SELECT COUNT(*) FROM analytics.stg_cashiering_postings WHERE revenue_date >= '2026-07-01' AND revenue_date < '2026-08-01' AND transaction_code IN ('8118','7108','8100','7100','8120','8102','8114','8106','7102','7106','8104','7104','8902') AND net_amount < 0` — must return 0 | A |
| AC-1 | July 2026 Total Revenue within 1% of 3.55B VND | Hybrid | `SELECT SUM(net_amount) FROM analytics.stg_cashiering_postings WHERE revenue_date >= '2026-07-01' AND revenue_date < '2026-08-01'` — target 3.55B +/- 35.5M | B |
| AC-2 | July 2026 FnB revenue within 1% of 2.43B VND | Hybrid | `SELECT SUM(net_amount) FROM analytics.stg_cashiering_postings WHERE revenue_date >= '2026-07-01' AND revenue_date < '2026-08-01' AND revenue_category = 'FnB'` — target 2.43B +/- 24.3M | B |
| AC-3 | July 2026 Room revenue within 1% of 1.107B VND | Hybrid | `SELECT SUM(net_amount) FROM analytics.stg_cashiering_postings WHERE revenue_date >= '2026-07-01' AND revenue_date < '2026-08-01' AND revenue_category = 'Room'` — target 1.107B +/- 11.07M | B |
| AC-5 | 3-5 known matched tax codes — net_amount identical to pre-fix values | Hybrid | Snapshot pre-fix net_amount for 3-5 matched tax codes via `git stash` + `dbt run`; `git stash pop` + rebuild with fix; compare values. Document comparison in phase report. | B |
| AC-1 | Dashboard Revenue tab visually confirms correct totals (manual spot check) | Agent-Probe | Open Streamlit dashboard Revenue tab; verify totals match SQL Gate 5 results. No automated assertion. | C |

gap-resolution legend:
- A — proven now (gate passes in this cycle)
- B — fixed in this plan (gate added by this plan's checklist)
- C — deferred to a named later phase/plan (dashboard visual confirmation)

Failing stubs (Fully-Automated rows only):
```
Gate 1: test("should compile stg_cashiering_postings without syntax errors", () => { throw new Error("NOT IMPLEMENTED — TDD stub: dbt compile --select stg_cashiering_postings") })
Gate 2: test("should rebuild stg_cashiering_postings with row count unchanged", () => { throw new Error("NOT IMPLEMENTED — TDD stub: dbt run --select stg_cashiering_postings") })
Gate 3: test("should pass all existing dbt tests on stg_cashiering_postings and downstream", () => { throw new Error("NOT IMPLEMENTED — TDD stub: dbt test --select stg_cashiering_postings+") })
Gate 4: test("should have net_amount >= 0 for all 13 previously-misclassified codes", () => { throw new Error("NOT IMPLEMENTED — TDD stub: 13 codes non-negative SQL assertion") })
```

Dimension findings:
- Infra fit: PASS — single-file dbt model edit; all paths and commands verified on disk; no container/infra/worker changes
- Test coverage: PASS — 9 gates across 3 tiers (4 Fully-Automated, 4 Hybrid, 1 Agent-Probe); schema.yml has not_null/unique/accepted_values on stg_cashiering_postings
- Breaking changes: PASS — no schema, API contract, or column type changes; net_amount name unchanged; downstream consumers (fct_folio_line, dashboard) only consume computed values
- Security surface: PASS — no auth, billing, credentials, secrets, or trust boundary touched; pure SQL CASE logic change
- stg_cashiering_postings fix: PASS (1 CONCERN) — edit target (lines 51-64) verified exact match with actual file; Jinja escaping correct; LEFT JOIN alias usage correct. CONCERN: Step 8 SQL comparison query placeholder

Open gaps:
- net_amount sign assertion for revenue codes: known-gap: documented as NEW PLAN REQUIRED — plan suggests follow-up singular dbt test `test_net_amount_non_negative_for_revenue_codes.sql` in `eras_dbt/tests/`. Not blocking this fix.
- No CI pipeline — all verification manual against live Postgres. Known infra gap, not this plan's scope.

Execute-agent instructions:
- E1: Before Step 8 (matched tax spot-check): use `git stash` to temporarily revert fix, run `dbt run --select stg_cashiering_postings --profiles-dir .`, capture net_amount for 3-5 known matched tax codes, `git stash pop`, rebuild with fix, compare values. Document comparison in phase report.
- E2: PC-4 baseline diagnostic MUST be run BEFORE any changes and results recorded in phase report. Gate 4 uses the same 13-code IN list.

What this coverage does NOT prove:
- [Gate 1-3] Does NOT prove logical correctness — only SQL syntax validity and no regression in existing test assertions (not_null, unique, accepted_values)
- [Gate 4] Does NOT prove the 13 codes have correct positive amounts — only that they are non-negative (net_amount = 0 would pass the assertion)
- [Gate 5-7] Does NOT prove category-level revenue breakdown accuracy — only that totals are within 1% of OPERA Manager Report targets; sub-category miscategorization (e.g. Other-vs-FnB) not caught
- [Gate 8] Does NOT prove all matched tax codes are unchanged — only the 3-5 spot-checked codes verified; missed matched codes could be silently altered
- [Gate 9] Does NOT prove dashboard consistency across all tabs — only Revenue tab visually verified; Trends, Segments, Pacing tabs not checked
- [General] Does NOT prove the raw.cashiering_postings or analytics.stg_transaction_codes data sources are complete/correct — data quality gaps in source tables (e.g. missing hotel_id rows in transaction_codes) persist regardless of this fix

Gate: CONDITIONAL (0 FAILs, 1 CONCERN accepted)
Accepted by: session (autonomous, /goal execution) — CONCERN: Step 8 SQL placeholder; execute-agent instruction E1 resolves with git stash pre-fix capture


---

## Acceptance Criteria (SPEC-linked)

| ID | Criterion | Proven by |
|----|-----------|-----------|
| AC-1 | Dashboard Total Revenue for July 2026 matches OPERA Manager Report Total (3.55B VND) within 1% | Gates 5, 9 |
| AC-2 | FnB revenue matches Manager Report FnB (2.43B VND) within 1% | Gate 6 |
| AC-3 | Room revenue matches Manager Report Room (1.107B VND) within 1% | Gate 7 |
| AC-4 | The 13 misclassified transaction codes (8118, 7108, 8100, 7100, 8120, 8102, 8114, 8106, 7102, 7106, 8104, 7104, 8902) no longer produce negative `net_amount` | Gate 4 |
| AC-5 | No regression in tax/service charge handling for matched transaction codes | Gates 3, 8 |
| AC-6 | `dbt build --select stg_cashiering_postings+` succeeds with no errors | Gates 1, 2 |
| AC-7 | All existing dbt tests pass on `stg_cashiering_postings` and downstream models | Gate 3 |


---

## Autonomous Goal Block

SESSION GOAL: Fix revenue classification bug in stg_cashiering_postings — 13 unmatched 7xxx/8xxx transaction codes incorrectly treated as tax postings, causing ~240M VND revenue understatement. Apply three-branch CASE fix, verify revenue totals match OPERA Manager Report within 1%, no regression in existing dbt tests.

Charter + umbrella plan: N/A — single plan
Autonomy: autonomous — /goal execution; auto-proceed on all reversible decisions
Hard stop conditions / safety constraints:
- Do NOT execute irreversible outward-facing actions (live OPERA Cloud API calls, production DB changes without backup) not explicitly listed in the plan checklist
- Do NOT skip pre-conditions PC-1 (Postgres running), PC-2 (.user.yml valid), PC-3 (baseline dbt build succeeds)
- If any Fully-Automated gate (1-4) fails after fix: hard stop — do NOT proceed to manual verification; investigate root cause
- If Total Revenue deviates more than 5% from 3.55B target after fix: hard stop — review the fix logic before continuing

Next phase: EXECUTE — D:/ErasProjects/ErasOpera/process/features/financials/active/fix-revenue-classification_24-07-26/fix-revenue-classification_PLAN_24-07-26.md
Validate contract: inline in plan — D:/ErasProjects/ErasOpera/process/features/financials/active/fix-revenue-classification_24-07-26/fix-revenue-classification_PLAN_24-07-26.md

Execute start:
- Gate 1: cd D:/ErasProjects/ErasOpera/eras_dbt && dbt compile --select stg_cashiering_postings --profiles-dir .
- Gate 2: cd D:/ErasProjects/ErasOpera/eras_dbt && dbt run --select stg_cashiering_postings --profiles-dir .
- Gate 3: cd D:/ErasProjects/ErasOpera/eras_dbt && dbt test --select stg_cashiering_postings+ --profiles-dir .
- Gates 4-8: SQL queries against live Postgres (see validate-contract for exact SQL)
- Gate 9: Agent-Probe — open dashboard Revenue tab, verify totals
high-risk pack: no
