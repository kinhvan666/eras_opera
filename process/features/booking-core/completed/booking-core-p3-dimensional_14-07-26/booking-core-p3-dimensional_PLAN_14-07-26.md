---
name: plan:booking-core-p3-dimensional
description: "Phase 3 of booking-core: build the Kimball dimensional layer (dim_date, dim_property, dim_guest, dim_rate, fct_reservation_night) on top of stg_reservations."
date: 14-07-26
feature: booking-core
phase: "3"
---

# Plan: Booking Core - Phase 3 (Dimensional Model)

Date: 14-07-26
Status: Draft — pending VALIDATE
Complexity: COMPLEX

## Overview & Goals

Phase 1 landed raw reservation JSON in `raw.booking_core_reservations`. Phase 2 built
`stg_reservations`, a thin staging model exposing 11 columns (`reservation_id`,
`confirmation_no`, `arrival_date`, `departure_date`, `created_at`, `updated_at`, `profile_id`,
`guest_first_name`, `guest_last_name`, `room_type`, `total_amount`) — with a CONDITIONAL
validate-contract flagging that the JSON paths were unverified against live data.

Phase 3 builds the Kimball dimensional layer the SPEC calls for:

- `dim_date` — calendar dimension
- `dim_property` — conformed hotel/property dimension
- `dim_guest` — Type 2 SCD guest dimension (address history)
- `dim_rate` — rate plan / market / source-of-business dimension (SPEC's locked name; the
  context doc `process/context/database/all-database.md` still lists the provisional name
  `dim_rate_code` — that doc was not updated during INNOVATE and is a known follow-up for
  UPDATE PROCESS, not something this plan edits)
- `fct_reservation_night` — the grain-declared fact table, one row per property per
  reservation per night (SPEC AC2)

**Goal:** deliver a queryable star schema over reservation data sufficient to power the V1
leadership dashboard KPIs in the SPEC (occupancy, ADR, RevPAR, room nights, lead time,
cancellation rate), while explicitly closing the Phase 2 CONDITIONAL gap before building on
top of it.

**Non-goals (Out of Scope, per SPEC):** `dim_block`/Block API integration (Block was never
extracted in Phase 1), folio-level financials, real-time sync, channel/source-of-business
profitability modeling, and full automation of AC4 (source-report reconciliation) / AC7 (CDC
integration test) — these are flagged as known-gaps below, not silently dropped.

## 2. Touchpoints & Blast Radius

### Files to Modify

- `eras_dbt/models/staging/stg_reservations.sql` — extend in place with `hotel_id`, guest
  address columns, and `rate_plan_code` / `market_code` / `source_of_business`. All new fields
  come from the same raw reservation JSON row already scanned by this model — no sibling
  staging model is created (INNOVATE decision 3).
- `eras_dbt/models/staging/schema.yml` — add column docs/tests for the new staging columns.
- `eras_dbt/dbt_project.yml` — add a materialization override for `fct_reservation_night`
  (INNOVATE decision 6); the `staging` folder's `+materialized: view` default must not apply
  to the new fact.

### Files to Create

- `eras_dbt/models/dimensional/dim_date.sql`
- `eras_dbt/models/dimensional/dim_property.sql`
- `eras_dbt/models/dimensional/dim_rate.sql`
- `eras_dbt/models/dimensional/fct_reservation_night.sql`
- `eras_dbt/models/dimensional/schema.yml` — column tests (`unique`, `not_null`,
  `relationships`) for all four models above
- `eras_dbt/snapshots/dim_guest_snapshot.sql` — dbt native snapshot config, populating the
  currently-empty `eras_dbt/snapshots/` folder (INNOVATE decision 2). This is the mechanism for
  `dim_guest`'s Type 2 SCD — there is no separate `dim_guest.sql` model; the snapshot table
  itself (`snapshots.dim_guest_snapshot` or equivalent, per dbt's snapshot schema convention)
  is the dimension.

### Files to Read (context, not modified)

- `docs/OPERA Cloud Reservation API (26.2.0.0).json` — schema source of truth (paths confirmed
  during this PLAN session — see §3 Step 1 for the exact paths)
- `process/features/booking-core/active/booking-core-p2-staging_13-07-26/booking-core-p2-staging_PLAN_13-07-26.md`
  — Phase 2 plan + its CONDITIONAL validate-contract (the open gap this plan closes first)
- `process/context/database/all-database.md` — Kimball/dbt conventions

### Public Contracts

- `stg_reservations` gains new nullable columns (`hotel_id`, `guest_city`, `guest_postal_code`,
  `guest_state`, `guest_country_code`, `rate_plan_code`, `market_code`, `source_of_business`).
  Existing consumers (none yet outside this feature) are unaffected — additive change only.
- `dim_date`, `dim_property`, `dim_rate` — new public dimension tables in the `dev` schema,
  keyed by surrogate/natural keys (see checklist for grain).
- `snapshots.dim_guest_snapshot` — new public SCD2 dimension table (via dbt snapshot), keyed by
  `profile_id` + `dbt_valid_from`/`dbt_valid_to`.
- `fct_reservation_night` — new public fact table. **Grain: one row per property, per
  reservation, per stay night** (composite key: `hotel_id`, `reservation_id`,
  `business_date`). This is the SPEC's mandated primary fact grain (SPEC Constraints).

### Blast Radius

- **Scope:** Medium. Touches one existing staging model (additive columns only, non-breaking)
  and introduces 5 new dbt artifacts (4 dimensional models + 1 snapshot) plus a project-level
  materialization config change scoped to one model.
- **Impact:** Medium. `fct_reservation_night` is new-build, not a rebuild of existing consumer
  surface — nothing downstream depends on it yet. The staging extension is additive (new
  columns only, no renames/drops), so the existing `unique`+`not_null` tests on
  `stg_reservations.reservation_id` are unaffected.
- **Risk Class:** Low-Medium. No auth, billing, or public-facing API surface. The primary risk
  is silently-wrong JSON path extraction repeating the Phase 2 pattern — mitigated by the
  mandatory staging-verification gate in the checklist below (§3 Step 2) before any dimensional
  SQL is written.

## 3. Implementation Checklist

Steps are strictly ordered: extend and verify staging first, then build dimensions, then build
the fact (which references the dimensions).

### Part A: Close the Phase 2 Gap — Extend and Verify Staging

1. **Confirm JSON paths against the OPERA Reservation API spec and the actual
   `stg_reservations.sql`.** The following paths were confirmed during this PLAN session by
   reading `docs/OPERA Cloud Reservation API (26.2.0.0).json` example payloads (lines
   ~28561–28691) alongside the current committed `stg_reservations.sql`:
   - `hotel_id`: `raw_data->>'hotelId'` — a top-level sibling of `createDateTime` /
     `lastModifyDateTime` (already used in the current model), NOT nested under `roomStay`.
   - Guest address: `raw_data->'reservationGuest'->'address'->>'cityName'`,
     `...->>'postalCode'`, `...->>'state'`, `...->'country'->>'code'` — nested under the same
     `reservationGuest` object already used for `givenName`/`surname`.
   - Rate/market fields: `raw_data->'roomStay'->>'ratePlanCode'`,
     `...->>'marketCode'`, `...->>'sourceOfBusiness'` — siblings of `roomType` and
     `rateAmount`, already used under `roomStay` in the current model.
   - These paths follow the *actual* committed model's path shape (`roomStay` /
     `reservationGuest` nesting), not the divergent shape in the Phase 2 plan document — per
     RESEARCH findings, the committed SQL is the ground truth to extend, not the stale plan doc.

2. **Extend `eras_dbt/models/staging/stg_reservations.sql`** by adding the following columns to
   the `staged` CTE select list (append, do not reorder or rename existing columns):
   ```sql
   raw_data->>'hotelId' as hotel_id,
   raw_data->'reservationGuest'->'address'->>'cityName' as guest_city,
   raw_data->'reservationGuest'->'address'->>'postalCode' as guest_postal_code,
   raw_data->'reservationGuest'->'address'->>'state' as guest_state,
   raw_data->'reservationGuest'->'address'->'country'->>'code' as guest_country_code,
   raw_data->'roomStay'->>'ratePlanCode' as rate_plan_code,
   raw_data->'roomStay'->>'marketCode' as market_code,
   raw_data->'roomStay'->>'sourceOfBusiness' as source_of_business
   ```

3. **Add column docs to `eras_dbt/models/staging/schema.yml`** for the 8 new columns (name +
   short description; no tests required yet at staging grain beyond the existing
   `reservation_id` unique/not_null).

4. **MANDATORY GATE — run and manually inspect before writing any dimensional SQL:**
   ```bash
   dbt run --select stg_reservations
   ```
   Then:
   ```sql
   SELECT hotel_id, guest_city, guest_postal_code, guest_state, guest_country_code,
          rate_plan_code, market_code, source_of_business
   FROM dev.stg_reservations
   LIMIT 20;
   ```
   Manually confirm all 8 new columns contain sensible non-null-for-most-rows values matching
   the raw JSON. **Do not proceed to Part B until this gate passes.** This directly closes the
   Phase 2 CONDITIONAL gap (unverified JSON paths) before stacking 4 new dependent models on an
   unverified foundation.

### Part B: Build Dimensions

5. **`dim_date`** — standard calendar dimension. Generate via `generate_series` over a date
   range covering the observed `arrival_date`/`departure_date` span in `stg_reservations` (plus
   a configurable buffer). Grain: one row per calendar date. Columns: `date_day` (PK),
   `year`, `quarter`, `month`, `month_name`, `day_of_week`, `day_name`, `is_weekend`.

6. **`dim_property`** — one row per distinct `hotel_id` observed in `stg_reservations`. This is
   deliberately minimal (no property master-data API was extracted in Phase 1) — columns:
   `hotel_id` (PK), plus a placeholder `hotel_name` if resolvable from raw JSON, else omit.
   Note in the model that a future phase should replace this with a real property
   master-data feed if/when Enterprise Configuration data lands.

7. **`dim_rate`** — one row per distinct (`rate_plan_code`, `market_code`,
   `source_of_business`) combination observed in `stg_reservations`. Named `dim_rate` per the
   locked SPEC, not `dim_rate_code` (the context doc's stale provisional name — flag for
   UPDATE PROCESS, do not edit `all-database.md` in this plan). Grain: one row per unique
   rate/market/source combination. Surrogate key via `{{ dbt_utils.generate_surrogate_key(...) }}`
   is NOT available (no packages.yml exists — see INNOVATE decision 1's same constraint);
   use a deterministic `md5()`-based surrogate key instead, or a natural composite key if the
   three columns are jointly unique and non-null enough — decide at EXECUTE time based on the
   Part A verification data.

8. **`dim_guest` snapshot** — create `eras_dbt/snapshots/dim_guest_snapshot.sql` using dbt's
   native `snapshot` block (`strategy: check`, `check_cols: [guest_city, guest_postal_code,
   guest_state, guest_country_code]`, unique key `profile_id`) against `stg_reservations`
   (or a light guest-only intermediate select if `stg_reservations` has multiple rows per
   `profile_id` — decide based on Part A data; snapshots require one row per unique key per
   invocation). This populates the currently-empty `eras_dbt/snapshots/` folder per INNOVATE
   decision 2. Do NOT hand-write incremental SCD2 merge logic.

### Part C: Build the Fact

9. **`fct_reservation_night`** — explode each `stg_reservations` row into one row per night
   between `arrival_date` (inclusive) and `departure_date` (exclusive) using native Postgres
   `generate_series(arrival_date, departure_date - interval '1 day', interval '1 day')` in a
   lateral join (INNOVATE decision 1 — no dbt-utils `date_spine`, no packages.yml). Columns:
   `hotel_id`, `reservation_id`, `business_date` (composite grain key), `profile_id` (FK →
   `dim_guest_snapshot`), `rate_plan_code`/`market_code`/`source_of_business` (FK → `dim_rate`),
   `room_type`, `total_amount` (or a per-night allocation — decide at EXECUTE time; SPEC KPIs
   treat this as an estimate pending the `financials` feature).

10. **Add a materialization override** for `fct_reservation_night` — either a model-level
    `{{ config(materialized='table') }}` (or `incremental`) directly in
    `fct_reservation_night.sql`, or a `models.eras_dbt.dimensional.+materialized: table` block
    in `dbt_project.yml`. Do not let it inherit the staging folder's `+materialized: view`
    default (INNOVATE decision 6) — night-explosion multiplies row count and a view would
    recompute the lateral join on every query.

11. **Add tests in `eras_dbt/models/dimensional/schema.yml`:**
    - `dim_date.date_day`, `dim_property.hotel_id`, `dim_rate.<surrogate key>`: `unique` +
      `not_null`
    - `fct_reservation_night`: composite-key uniqueness test (`dbt_utils.unique_combination_of_columns`
      is unavailable without packages.yml — use a `unique` test on a generated surrogate key
      column instead, or a custom singular test) on (`hotel_id`, `reservation_id`,
      `business_date`) — proves SPEC AC2 (grain)
    - `fct_reservation_night.hotel_id` → `relationships` test against `dim_property.hotel_id`
    - `fct_reservation_night.rate_plan_code`/`market_code`/`source_of_business` composite →
      `relationships`-style check against `dim_rate` (exact test shape decided at EXECUTE
      based on the surrogate-key decision in Step 7)

12. **Run the full new surface:**
    ```bash
    dbt run --select stg_reservations+
    dbt snapshot --select dim_guest_snapshot
    dbt test --select stg_reservations+
    ```

## 4. Verification & Evidence (Acceptance Criteria Mapping)

| Criterion | Behavior | Strategy | Proving Test | Gap Resolution |
|---|---|---|---|---|
| AC1 | `fct_reservation_night` has one row per night of every active/arrived reservation | Fully-Automated | `dbt run --select fct_reservation_night` + row-count sanity check against `stg_reservations` night-span sum | B — proven by this plan's checklist Step 9/12 |
| AC2 | Grain is one row per property/reservation/night, no duplicates | Fully-Automated | dbt `unique` test on composite surrogate key (Step 11) | B — proven by this plan's checklist Step 11 |
| AC3 | `dim_guest` is Type 2 SCD, correctly tracks guest address history | Hybrid | `dbt snapshot` run + manual simulated address change (no fixture yet — see §5) verifying new row with updated `dbt_valid_from`/`dbt_valid_to` and preserved old record | B — snapshot infra built by this plan; the simulated-change fixture is a Test Infra gap (see §5), not a blocker |
| AC4 | Total reservation nights matches OPERA source daily summary report | Hybrid (per SPEC) | Manual reconciliation query vs. source report | C — deferred; no automated reconciliation pipeline exists yet, SPEC explicitly names this a long-term goal, not a Phase 3 deliverable |
| AC5 | All PKs in dim/fact tables are non-null and unique | Fully-Automated | dbt `unique`/`not_null` tests on all new models (Step 11) | B — proven by this plan's checklist |
| AC6 | FK relationships between fact and dimensions hold | Fully-Automated | dbt `relationships` tests (Step 11) | B — proven by this plan's checklist |
| AC7 | Extraction correctly filters on `lastUpdateDate` for CDC | Agent-Probe (per SPEC: integration test against mock source) | N/A this phase | C — deferred/known-gap; this is an extractor-layer (Phase 1) concern, not buildable in the dbt dimensional layer this plan covers. Flag for a future extractor-focused phase, not this plan. |

Gap-resolution legend (matches Phase 2 plan's convention): A = proven now, B = fixed by this
plan's checklist, C = deferred to a named later phase, D = backlog test-infra stub.

## 5. Test Infra Improvement Notes

- **dbt snapshot infra is net-new to this repo.** `eras_dbt/snapshots/` is currently empty
  (only `.gitkeep`). This plan is the first to populate it. No prior snapshot conventions exist
  to follow — the snapshot config in Step 8 establishes the pattern for future SCD2 dimensions
  (e.g. a future `dim_room_type` or `dim_property` SCD2 upgrade).
- **No seed/fixture exists for simulating a guest address change.** AC3's Hybrid verification
  needs a way to mutate `raw.booking_core_reservations` (or an intermediate layer) for one
  profile's address, re-run the snapshot, and inspect the resulting two rows. Building a
  reusable dbt seed fixture for this is out of scope for this plan (Hybrid/manual verification
  is acceptable per SPEC AC3's own `proven by` language) but is a natural follow-up for
  `process/context/tests/all-tests.md` once a broader test-fixture strategy is established.
- **No `packages.yml` exists.** Several standard dbt-utils conveniences
  (`generate_surrogate_key`, `date_spine`, `unique_combination_of_columns`) are unavailable.
  This plan works around that with native Postgres SQL (per INNOVATE decisions 1 and this
  plan's Steps 7/11) rather than introducing a new dependency mid-phase. Adopting dbt-utils is
  a reasonable future improvement but is out of scope here (no new dependencies per Blast
  Radius above).

## 6. Backlog Note (Non-Blocking)

No PII retention policy exists yet for `dim_guest`'s indefinitely-retained address history via
SCD2 (guest addresses persist forever across snapshot versions with no purge/anonymization
path). This is a compliance-adjacent gap worth tracking but is explicitly not a blocker for
this phase — flagging here for UPDATE PROCESS / backlog capture, not resolving it now.

## 7. Phase Completion Rules

This phase is complete when:

- Part A's mandatory staging-verification gate (Step 4) has passed with manually-inspected,
  sensible output for all 8 new `stg_reservations` columns.
- All 4 new dimensional models (`dim_date`, `dim_property`, `dim_rate`) plus the
  `dim_guest_snapshot` snapshot run successfully via `dbt run`/`dbt snapshot`.
- `fct_reservation_night` runs successfully with the mandated materialization override in
  place (not inheriting the staging `view` default).
- All dbt tests in `eras_dbt/models/dimensional/schema.yml` pass (`dbt test --select
  stg_reservations+`).
- AC1, AC2, AC5, AC6 are proven per the table in §4; AC3 has passed its Hybrid manual check;
  AC4 and AC7 are explicitly logged as deferred known-gaps (not silently dropped).

## 8. Resume and Execution Handoff

- **Selected plan file path:** `D:\ErasProjects\ErasOpera\process\features\booking-core\active\booking-core-p3-dimensional_14-07-26\booking-core-p3-dimensional_PLAN_14-07-26.md`
- **Last completed phase or step:** Phase 2 (dbt Staging Models) — CONDITIONAL gate accepted;
  this plan's Part A closes that gap before Part B/C build on top of it.
- **Validate-contract status:** Pending (this is a new plan)
- **Supporting context files loaded:** `process/context/all-context.md`,
  `process/context/database/all-database.md`, `process/context/planning/all-planning.md`,
  `process/context/tests/all-tests.md`, the locked booking-core SPEC, the Phase 2 plan +
  validate-contract, the current committed `stg_reservations.sql`/`schema.yml`/`sources.yml`/
  `dbt_project.yml`, and the OPERA Reservation API spec (JSON paths confirmed against live spec
  examples — see §3 Step 1).
- **Next step for a fresh agent:** `ENTER VALIDATE MODE` for this plan. Do not route to EXECUTE
  until VALIDATE completes — Part A's staging-extension SQL and Part B/C's dimensional/fact SQL
  are both non-trivial surfaces per this repo's VALIDATE Gate skip conditions.

## Validate Contract

Status: CONDITIONAL
Date: 14-07-26
date: 2026-07-14
generated-by: outer-pvl

Parallel strategy: parallel-subagents
Rationale: 5 independent dimension checks (infra fit, test coverage, breaking changes, security
surface, feasibility) plus a JSON-path cross-reference against the OPERA spec have no
inter-dependencies and no shared file edits — no coordination needed, so parallel-subagents is
sufficient. Agent-team was not warranted (no adversarial debate or overlapping blast radius).

Test gates (5-column table):

| criterion id | behavior | strategy | proving test | gap-resolution |
|---|---|---|---|---|
| p3-1 (AC1) | `fct_reservation_night` has one row per night of every reservation | Fully-Automated | `dbt run --select fct_reservation_night` + row-count sanity check vs. `stg_reservations` night-span sum (Step 9/12) | B |
| p3-2 (AC2) | Grain is one row per property/reservation/night, no duplicates | Fully-Automated | dbt `unique` test on composite surrogate key (Step 11) | B |
| p3-3 (AC3) | `dim_guest` SCD2 correctly tracks guest address history | Hybrid (plan) vs. Fully-Automated (SPEC) | `dbt snapshot` run + **manual** simulated address change, no fixture built (Step 8, §5) | D — mislabeled B in the plan's own §4 table; see Dimension findings |
| p3-4 (AC4) | Total reservation nights matches OPERA source daily summary report | Hybrid | Manual reconciliation query | C — deferred per SPEC, correctly not claimed as covered |
| p3-5 (AC5) | All PKs in dim/fact tables non-null and unique | Fully-Automated | dbt `unique`/`not_null` tests (Step 11) | B |
| p3-6 (AC6) | FK relationships between fact and dimensions hold | Fully-Automated | dbt `relationships` tests (Step 11) | B |
| p3-7 (AC7) | Extraction filters on `lastUpdateDate` for CDC | Agent-Probe (per SPEC) | N/A this phase — extractor-layer concern | C — correctly deferred to a future extractor phase, not silently dropped |
| p3-8 | JSON paths for `hotel_id`, guest address, rate/market/source-of-business exist in the OPERA Reservation API and match the plan's claimed shape | Fully-Automated (VALIDATE-time) | Cross-referenced against `docs/OPERA Cloud Reservation API (26.2.0.0).json` example payload (lines 28561–28691) and schema defs (`addressSearchType` L32956, rate/market fields L35750–35820) | A — verified in this VALIDATE pass, see Dimension findings |
| p3-9 | Staging extension is additive, does not break Phase 2's existing `reservation_id` unique/not_null tests | Fully-Automated | Inspection of `stg_reservations.sql` (append-only column list) + `schema.yml` (untouched `reservation_id` test block) | A — verified in this VALIDATE pass |
| p3-10 | `fct_reservation_night` has an explicit non-view materialization override | Fully-Automated | Plan Step 10 + Phase Completion Rules §7 | B |
| p3-11 | Mandatory staging re-verification gate is an ordered checklist step before Part B/C | Fully-Automated | Plan §3 Step 4, positioned before Step 5 | A — verified in this VALIDATE pass |

gap-resolution legend:
- A — proven now (verified in this VALIDATE pass)
- B — fixed by this plan's checklist (gate added, will pass once EXECUTE runs it)
- C — deferred to a named later phase/plan
- D — backlog test-infra stub (named residual; keep-active; continue)

Dimension findings:
- Infra fit: PASS — dbt native `generate_series` (Postgres), dbt native `snapshot` block, and a
  model-level/`dbt_project.yml` materialization override are all standard, already-available
  tooling. No `packages.yml`/new dependency introduced, consistent with INNOVATE decisions 1, 2,
  6. `eras_dbt/snapshots/` is currently empty except `.gitkeep` — confirmed; this plan is
  correctly the first to populate it.
- Test coverage: CONCERN (non-blocking) — AC1, AC2, AC5, AC6 are proven by standard dbt tests and
  will pass mechanically once run (B). AC4/AC7 are correctly labeled C (deferred, not silently
  dropped) and match the SPEC's own deferral language. **AC3 is a real gap**: SPEC AC3 states
  strategy `Fully-Automated` ("dbt test that simulates a guest address change and verifies...");
  the plan's §4 table also labels this gap-resolution `B` ("proven by this plan's checklist"),
  but the actual Step 8 + §5 content describes a **manual**, un-fixtured verification ("no seed/fixture
  exists... out of scope for this plan"). The dbt snapshot *infrastructure* is proven (B — it will
  run and produce a mechanically-correct SCD2 table), but the *behavioral proof* that address
  changes are captured correctly is Hybrid/manual, not Fully-Automated. This is a labeling
  mismatch (should be D, not B) rather than a functional planning defect — the plan discloses the
  real gap honestly in prose (§5), it just doesn't self-tag it correctly in the summary table.
- Breaking changes: PASS — confirmed via direct inspection of the committed
  `eras_dbt/models/staging/stg_reservations.sql` (11 existing columns) and `schema.yml` (only
  `reservation_id` unique/not_null tests exist). The plan's Step 2 SQL appends 8 new columns to
  the same `staged` CTE select list without touching the existing 11 — additive, non-breaking.
  `eras_dbt/dbt_project.yml` currently has only `staging: +materialized: view`; the plan's Step 10
  materialization override targets a new `dimensional` model only and does not modify the
  existing staging block.
- Security surface: CONCERN, accepted — guest address PII is retained indefinitely via SCD2
  snapshot with no purge/anonymization path. The plan explicitly discloses this in §6 Backlog
  Note as non-blocking for this phase and flags it for UPDATE PROCESS/backlog capture rather than
  silently omitting it. No credentials or auth surface touched.
- Feasibility (Part A — staging extension): PASS — JSON path claims verified against
  `docs/OPERA Cloud Reservation API (26.2.0.0).json`:
  - `hotel_id` → `raw_data->>'hotelId'`: confirmed top-level sibling of `createDateTime`/
    `lastModifyDateTime` in the example payload (line 28677), NOT nested under `roomStay`. Matches
    plan's claim exactly.
  - Guest address → `raw_data->'reservationGuest'->'address'->>'cityName'` /`'postalCode'`/
    `'state'`/`->'country'->>'code'`: confirmed via the `addressSearchType` schema definition
    (L32956–32989: `cityName`, `postalCode`, `state`, `country`) and the example payload
    (L28611–28618, nested under `reservationGuest`). Matches plan's claim exactly.
  - `rate_plan_code`/`market_code`/`source_of_business` → `raw_data->'roomStay'->>'ratePlanCode'`/
    `'marketCode'`/`'sourceOfBusiness'`: confirmed as siblings of `roomType`/`rateAmount` under
    `roomStay` in the example payload (L28578, L28589–28591). Note: the abstract schema
    definition block for rate plan fields (L35809) names the analogous field `sourceCode`, but
    every concrete example instance in the spec (L2032, L10608, L28590, L28737, L28894) uses the
    literal key `sourceOfBusiness` — this is an internal inconsistency in the OPERA spec's own
    schema-vs-example naming, not a defect in the plan. Since Phase 1 lands raw JSON exactly as
    returned by the live API (which will match the example instance shape, not the abstract
    schema's field name), the plan's path is correct.
  - All 3 field groups' JSON paths are VERIFIED against the spec — this resolves the specific new
    fields for this phase. It does NOT resolve the carried-forward Phase 1/2 CONDITIONAL gaps
    (live-endpoint auth/params unverified; the *original* 11 columns' paths never verified against
    a real live pull) — those remain open and are correctly not re-claimed as fixed by this plan.
    This plan's mandatory Step 4 gate is the intended mechanism to close them at EXECUTE time, not
    at VALIDATE time.
- Feasibility (Part B/C — dimensional/fact SQL): PASS — `generate_series(arrival_date,
  departure_date - interval '1 day', interval '1 day')` correctly excludes the checkout day,
  matching the Kimball reservation-night grain (a guest is not "in-house" the night they check
  out). dbt's native `snapshot` block with `strategy: check` is a standard, battle-tested SCD2
  pattern — mechanically sound. Step 8 correctly self-identifies and flags the risk that
  `stg_reservations` may have multiple rows per `profile_id` (multiple reservations per guest),
  which would violate dbt snapshot's one-row-per-unique-key-per-invocation requirement, and
  provides a fallback (light guest-only intermediate select) — this is a disclosed, mitigated
  execute-time decision point, not a silent gap. `dim_rate`'s surrogate-key choice (md5 vs.
  natural key) is likewise an explicitly disclosed execute-time decision, reasonable given no
  `packages.yml`/dbt-utils is available.

Open gaps:
- AC3's proving test is mislabeled `B` in the plan's own §4 table; it is functionally a `D`
  (backlog test-infra stub) — the SCD2 mechanism is proven, the behavioral correctness (does an
  address change actually produce a new historized row) is not automated and has no fixture.
  Accepted as a known-gap for this phase per the plan's own §5 disclosure; building the fixture is
  legitimate future scope, not required to ship this phase's dimensional layer.
- Carried-forward Phase 1 CONDITIONAL gap (live OPERA endpoint/params never verified) — still open,
  unaffected by this plan; this plan does not touch the extractor.
- Carried-forward Phase 2 CONDITIONAL gap (JSON paths never verified against a real live pull;
  committed `stg_reservations.sql` diverges from the Phase 2 plan document) — still open for the
  *original* 11 columns. This plan's Part A Step 4 mandatory gate is designed to close this at
  EXECUTE time (for both the original 11 and the 8 new columns together) — it is not closed by
  VALIDATE itself, since no live `dbt run` has occurred yet.
- PII retention (guest address, indefinite via SCD2, no purge path) — disclosed, non-blocking,
  backlogged per plan §6.

What this coverage does NOT prove:
- That the live OPERA Reservation API actually returns data in the exact shape of the spec's
  example payloads (spec examples are illustrative, not a live-data guarantee) — this is exactly
  why Part A Step 4's mandatory `dbt run` + manual inspection gate exists and must not be skipped.
- That AC3's SCD2 *behavior* is correct end-to-end (only that the mechanism is dbt-native and
  standard) — no automated fixture proves this yet.
- Business-logic accuracy of per-night revenue allocation in `fct_reservation_night` (Step 9 notes
  `total_amount` is "an estimate pending the `financials` feature" — this is a SPEC-acknowledged
  limitation, not a defect of this plan).
- Anything about `dim_block`, folio-level financials, real-time sync, or channel/source-of-business
  profitability modeling — all explicitly Out of Scope per the SPEC and this plan's Non-goals.

Gate: CONDITIONAL
Accepted by: recommended for acceptance — the two carried-forward Phase 1/2 gaps are structural
(they require a live `dbt run`, which is an EXECUTE-time action, not something VALIDATE or PLAN
can resolve on paper) and this plan's own Step 4 gate is the correct closure mechanism. The AC3
test-fixture gap is disclosed, scoped, and non-blocking to the core dimensional-layer deliverable.
The PII backlog note is disclosed and appropriately deferred. None of these gaps require a
plan-supplement cycle — they are genuine known-gaps in the same category as the already-accepted
AC4/AC7 deferrals, not planning defects. Recommend orchestrator accept and proceed to EXECUTE.
