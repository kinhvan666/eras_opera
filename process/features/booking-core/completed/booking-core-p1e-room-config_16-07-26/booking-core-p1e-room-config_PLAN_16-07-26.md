---
name: plan:booking-core-p1e-room-config
description: "PLAN for extracting real per-property room count from OPERA Cloud into dim_property.room_count, replacing the hardcoded 250 default"
date: 16-07-26
feature: booking-core
---

# PLAN: Real Room Count Extraction (dim_property.room_count)

Complexity: **SIMPLE** (single cohesive feature, one plan file, 4 sequential sub-phases within one
EXECUTE pass — not a phase program; no umbrella plan).

SPEC: `booking-core-p1e-room-config_SPEC_16-07-26.md` (locked)
FEASIBILITY: `booking-core-p1e-room-config_FEASIBILITY_16-07-26.md` (VIABLE — cited, not re-run)

---

## Overview

ErasOpera extracts operational data from Oracle OPERA Cloud and loads it into a Kimball-style
dimensional model in PostgreSQL. This plan adds real per-property room count extraction from
OPERA Cloud APIs into dim_property.room_count, replacing the previously hardcoded 250-room
default. The extraction uses HotelConfigExtractor (already implemented) which calls two OPERA
Cloud endpoints: Enterprise Config API (/ent/config/v1/hotels/{hotelId}) and Room Config API
(/rm/config/v1/hotels/{hotelId}/rooms?physical=true). Raw data is stored in
raw.enterprise_hotel_config (append-only snapshots per run), then surfaced through
stg_hotel_config and joined into dim_property.

Context: process/context/all-context.md (root router), process/context/database/all-database.md
(Kimball model), process/context/tests/all-tests.md (test conventions).

---

## Acceptance Criteria

- AC1: Real per-property room count retrievable from OPERA Cloud (physical rooms only).
- AC2: Each extraction run appends a new snapshot row; history is never overwritten (plain INSERT, no ON CONFLICT).
- AC3: dim_property.room_count reflects real extracted value, not a hardcoded default.
- AC4: Dashboard occupancy/RevPAR KPI values change when room_count changes (Known Gap / backlog).
- AC5: Failed or empty fetch does not silently overwrite good data; failure logged to stderr; prior DB snapshot untouched.
- AC6: Both HotelConfigExtractor and ReservationExtractor run in a single main.py invocation.
- AC7: noOfRooms semantics confirmed empirically (FEASIBILITY VERDICT already proven, not re-run).

---

## Phase Completion Rules

This is a SIMPLE plan (not a phase program). Completion rules:
- Sub-phases 1 and 4 are DONE (implemented before VALIDATE ran).
- Sub-phase 2 is complete when: upsert_hotel_config renamed to insert_hotel_config_snapshot, ON CONFLICT removed, unique index dropped, and poetry run pytest tests/test_hotel_config_database.py tests/test_hotel_config_extractor.py tests/test_main_wiring.py -v passes green.
- Sub-phase 3 is complete when: stg_hotel_config.sql has DISTINCT ON dedup, dim_property.sql LEFT JOINs stg_hotel_config for room_count and hotel_name, and dbt build --select stg_hotel_config+dim_property passes green.
- Plan is VERIFIED when all sub-phase test gates are green AND validate-contract Gate: PASS is confirmed by EVL run.

---

## Inner Loop Refresh Note

Date: 2026-07-16
Trigger: PVL supplement — FAIL A (plan-vs-implementation conflict) and FAIL B (AC2 upsert vs append-only).
Changes applied:
- All `room_config.py` / `RoomConfigExtractor` / `raw.booking_core_room_config` / `stg_room_config.sql` references replaced with the actual `hotel_config.py` / `HotelConfigExtractor` / `raw.enterprise_hotel_config` / `stg_hotel_config.sql` implementation.
- Approach Decision 1 (`fetch_all()` generalization) superseded: `hotel_config.py` uses `fetch_one`, not `fetch_all` — generalization is not needed and has been removed from the checklist.
- Approach Decision 3 updated: upsert (`ON CONFLICT DO UPDATE`) must change to append-only `INSERT` per SPEC AC2 (user confirmed: history is wanted). Sub-phase 2 now covers this migration.
- Sub-phases 1 and 4 marked DONE (already implemented). Remaining work: sub-phase 2 (append-only change) and sub-phase 3 (stg dedup update + dim_property wiring with hotel_name bonus).
- `stg_hotel_config.sql` dedup fix added (currently missing `DISTINCT ON` — will produce duplicates once table is append-only).
- `dim_property.sql` updated to also pull `hotel_name` from `stg_hotel_config` (removes the `null::text` placeholder).
- Test update for `test_hotel_config_database.py` added to assert two inserts → two rows.

---

## Approach / Decisions (from INNOVATE — updated to match hotel_config implementation)

1. ~~**`fetch_all()` generalization**~~ **SUPERSEDED** — `HotelConfigExtractor` uses `fetch_one`
   (not `fetch_all`) for two separate endpoints: Enterprise Config API for hotel metadata, and Room
   Config API for the physical room count. No `fetch_all` generalization is needed or was built.
   Checklist items for `fetch_all()` parametrization are removed.

2. **Test scope** — existing test harness in `extractor/tests/` uses `respx` for HTTP mocking and
   `monkeypatch` for DB unit tests. New work (sub-phase 2) adds an append-semantics assertion to
   `test_hotel_config_database.py`. No new test dependencies needed.

3. **Raw table — append-only (SPEC AC2 requirement, user-confirmed)** —
   `raw.enterprise_hotel_config`: currently has `UNIQUE (hotel_id)` index and uses `ON CONFLICT DO
   UPDATE` (upsert). This must change to **plain `INSERT`, no unique index** so every extraction
   run appends a new snapshot row preserving history. Changes required:
   - Drop `uq_enterprise_hotel_config_hotel_id` unique index (or recreate table without it).
   - Rename `Database.upsert_hotel_config()` to `Database.insert_hotel_config_snapshot()` (plain
     INSERT, no `ON CONFLICT` clause — structurally separate from `insert_raw_data`'s upsert path).
   - `stg_hotel_config.sql` must add `DISTINCT ON (hotel_id) ORDER BY extracted_at DESC` to dedup
     to the latest snapshot per hotel (currently missing; will produce fan-out once append-only).

4. **Endpoints** (already implemented, no change needed):
   - Enterprise Config: `/ent/config/v1/hotels/{hotelId}` → hotel metadata including `hotel_name`.
   - Room Config: `/rm/config/v1/hotels/{hotelId}/rooms?physical=true` (paginated via `fetch_one`,
     not `fetch_all` — single call, not paginated iteration; `physical_room_count` is returned
     directly in the response, not via a `roomsSummary[]` array).

5. **Raw storage** (already implemented): one row per extraction run in
   `raw.enterprise_hotel_config`, JSONB `raw_data` column holding the full API response plus
   `physical_room_count` stored as a separate integer column for convenience.

6. **`dim_property.sql` wiring** — LEFT JOIN `stg_hotel_config` on `hotel_id`:
   - `room_count` from `stg_hotel_config` (real extracted value, NULL when no snapshot — never
     falls back to `var('room_count_default')`; locked AC5 requirement).
   - `hotel_name` from `stg_hotel_config` (bonus: removes `null::text as hotel_name` placeholder
     — this was already available in `stg_hotel_config` and was not being used).

7. **Dashboard NULL-handling** — unchanged from original plan Decision 7: dashboard SQL already
   NULL-safe via `nullif(...)`; no code change required.

8. **vc-predict verdict: GO.** Known Gap carried forward: `raw.enterprise_hotel_config` grows
   unboundedly (no retention/pruning policy) — out of scope per SPEC.

---

## Sub-Phase Ordering (sequential within this one EXECUTE pass)

```
Sub-phase 1: HotelConfigExtractor + unit tests (AC1)                                  — DONE
Sub-phase 2: append-only migration + test update (AC2, AC5)                           — REMAINING
Sub-phase 3: stg_hotel_config dedup + dim_property wiring (AC3, AC5-dash, hotel_name) — REMAINING
Sub-phase 4: wiring into main.py/__main__ entrypoint (AC6)                            — DONE
```

Each sub-phase ends with its own test gate run before the next begins (per-section gate discipline).

---

## Touchpoints

| File | Action | Sub-phase | Status |
|---|---|---|---|
| `extractor/src/extractors/hotel_config.py` | Already exists — `HotelConfigExtractor` with `fetch_hotel_config()` and `fetch_physical_room_count()` | 1 | DONE |
| `extractor/tests/test_hotel_config_extractor.py` | Already exists — AC1 unit tests | 1 | DONE |
| `extractor/src/database.py` | Modify — rename `upsert_hotel_config` → `insert_hotel_config_snapshot`; change to plain INSERT; drop unique index on `hotel_id` | 2 | REMAINING |
| `extractor/tests/test_hotel_config_database.py` | Modify — update test to assert two calls → two rows (not one); assert no unique constraint | 2 | REMAINING |
| `eras_dbt/models/staging/stg_hotel_config.sql` | Modify — add `DISTINCT ON (hotel_id) ORDER BY extracted_at DESC` dedup | 3 | REMAINING |
| `eras_dbt/models/dimensional/dim_property.sql` | Modify — LEFT JOIN `stg_hotel_config`; pull `hotel_name` + `room_count`; remove `null::text` placeholder and `coalesce` fallback | 3 | REMAINING |
| `eras_dbt/models/sources/sources.yml` | Verify — `raw.enterprise_hotel_config` already registered; no change expected | 3 | VERIFY |
| `extractor/src/main.py` | Already wires `HotelConfigExtractor`; update call site from `upsert_hotel_config` → `insert_hotel_config_snapshot` | 2 | REMAINING (call site rename only) |
| `extractor/src/__main__.py` | Already implemented — no change | 4 | DONE |
| `extractor/tests/test_main_wiring.py` | Already exists — AC6 wiring test; update mock target name if method renamed | 2 | REMAINING (mock target rename only) |

**Not touched (explicitly):**
- `extractor/src/client.py` — `fetch_all()` generalization NOT needed; `fetch_one()` is already used by `hotel_config.py`.
- `dashboard/` — SQL already NULL-safe via `nullif(...)`; no code change.
- `eras_dbt/dbt_project.yml` — `room_count_default` var left in place (unused, not removed).

---

## Public Contracts

- **`Database.insert_hotel_config_snapshot(hotel_id, data, physical_room_count)`** — replaces
  `upsert_hotel_config`. Plain INSERT, no `ON CONFLICT`. Every call appends a new row.
  Callers in `main.py` and `test_main_wiring.py` must be updated to the new name.
- **`stg_hotel_config`** — dbt model. After dedup fix: one row per `hotel_id` (latest snapshot).
  Before fix: fan-out risk once table is append-only (this is why the dedup fix is in scope).
- **`dim_property.room_count`** — column semantics change from "hardcoded default (250) or
  coalesce" to "real extracted value or NULL if no snapshot exists." Downstream consumers
  (dashboard `nullif()` SQL) already NULL-safe.
- **`dim_property.hotel_name`** — previously `null::text`; now populated from `stg_hotel_config`.
  This is an additive improvement, not a breaking change.

---

## Blast Radius

- **Packages touched:** `extractor/` (database.py + test_hotel_config_database.py + main.py rename),
  `eras_dbt/` (stg_hotel_config.sql dedup + dim_property.sql wiring).
- **Not touched:** `dashboard/`, `extractor/src/client.py`, `extractor/src/extractors/hotel_config.py`.
- **File count:** ~5 modified files — see Touchpoints table.
- **Risk class:** database.py change removes a unique index (DDL change — non-destructive to data,
  but changes table structure). No auth/billing/secrets surface. No external API contract change.
- **Runtime surface:** reuses existing extractor container and Postgres warehouse.

---

## Detailed Implementation Checklist

### Sub-phase 1 — DONE (already implemented)

- [x] `extractor/src/extractors/hotel_config.py` — `HotelConfigExtractor` with `fetch_hotel_config()` and `fetch_physical_room_count()` using `fetch_one`.
- [x] `extractor/tests/test_hotel_config_extractor.py` — AC1 unit tests passing.

### Sub-phase 2 — Append-only migration (AC2, AC5)

1. In `extractor/src/database.py`:
   a. In `setup()`, remove or change the `uq_enterprise_hotel_config_hotel_id` unique index
      definition. If the table already exists with the constraint, add a migration statement:
      `DROP INDEX IF EXISTS uq_enterprise_hotel_config_hotel_id;`
      Place this before (or replace) the `CREATE TABLE IF NOT EXISTS` block so it is idempotent
      on re-run.
   b. Rename method `upsert_hotel_config(hotel_id, data, physical_room_count)` →
      `insert_hotel_config_snapshot(hotel_id, data, physical_room_count)`.
   c. Change the SQL inside from `INSERT ... ON CONFLICT (hotel_id) DO UPDATE SET ...` to a
      plain `INSERT INTO raw.enterprise_hotel_config (hotel_id, raw_data, physical_room_count, extracted_at) VALUES (%s, %s, %s, NOW())` with no `ON CONFLICT` clause.
   d. Confirm `extracted_at` column exists in the table DDL (needed for dedup in sub-phase 3);
      add `extracted_at TIMESTAMPTZ DEFAULT NOW()` to the `CREATE TABLE IF NOT EXISTS` statement if
      not already present.

2. In `extractor/src/main.py`:
   - Update the call site from `db.upsert_hotel_config(...)` → `db.insert_hotel_config_snapshot(...)`.

3. In `extractor/tests/test_main_wiring.py`:
   - Update any mock target from `database.upsert_hotel_config` → `database.insert_hotel_config_snapshot` (or the equivalent patch path). Confirm the existing AC6 tests still pass.

4. In `extractor/tests/test_hotel_config_database.py`:
   - Add / update: `test_insert_hotel_config_snapshot_appends_new_row` — call
     `insert_hotel_config_snapshot` twice with two different `physical_room_count` values (e.g. 49
     then 52), assert `SELECT COUNT(*) FROM raw.enterprise_hotel_config` returns 2 (not 1). **Proves AC2.**
   - Confirm existing tests that patched `upsert_hotel_config` are updated to the new method name.

5. **Test gate (Sub-phase 2):**
   ```
   cd extractor && poetry run pytest tests/test_hotel_config_database.py tests/test_hotel_config_extractor.py tests/test_main_wiring.py -v
   ```
   Must pass before Sub-phase 3 begins.

### Sub-phase 3 — stg_hotel_config dedup + dim_property wiring (AC3, AC5-dash, hotel_name)

6. Modify `eras_dbt/models/staging/stg_hotel_config.sql`:
   Add `DISTINCT ON (hotel_id) ORDER BY extracted_at DESC` dedup so the model returns exactly one
   row per `hotel_id` (the latest snapshot) regardless of how many append-only rows exist in
   `raw.enterprise_hotel_config`. The updated model should look like:
   ```sql
   with source as (
       select * from {{ source('raw', 'enterprise_hotel_config') }}
   ),
   deduped as (
       select distinct on (hotel_id)
           *
       from source
       where hotel_id is not null
       order by hotel_id, extracted_at desc
   ),
   staged as (
       select
           hotel_id,
           physical_room_count as room_count,
           raw_data->>'hotelName' as hotel_name,  -- or whatever the field name is in raw_data; confirm at EXECUTE
           extracted_at as room_config_extracted_at
       from deduped
   )
   select * from staged
   ```
   Confirm the exact field path for `hotel_name` inside `raw_data` at EXECUTE by inspecting the
   existing row in `raw.enterprise_hotel_config` (e.g. `SELECT raw_data FROM raw.enterprise_hotel_config LIMIT 1`).

7. Modify `eras_dbt/models/dimensional/dim_property.sql`:
   ```sql
   -- Property dimension - one row per distinct hotel_id observed in stg_reservations
   -- room_count: real extracted value from stg_hotel_config; NULL when no snapshot exists.
   -- hotel_name: from stg_hotel_config; NULL when no snapshot.
   -- Never falls back to hardcoded defaults (locked AC5 requirement).
   select
       p.hotel_id,
       c.hotel_name,
       c.room_count
   from (
       select distinct hotel_id
       from {{ ref('stg_reservations') }}
       where hotel_id is not null
   ) p
   left join {{ ref('stg_hotel_config') }} c
       on p.hotel_id = c.hotel_id
   ```
   Remove the `coalesce(c.room_count, var('room_count_default'))` fallback if present — `room_count`
   must be NULL (not a default) when no snapshot exists (AC5).

8. Verify `eras_dbt/models/sources/sources.yml` already registers `raw.enterprise_hotel_config` as
   a source. If not, add it alongside the existing `raw.booking_core_reservations` source entry.

9. Add a dbt test asserting `dim_property.room_count IS NOT NULL` for the known hotel (hotel_id=79017,
   physical_room_count=49 confirmed in existing snapshot). If a `schema.yml` pattern exists for
   dimensional models, add the test there; otherwise create a dbt singular test SQL file. **Proves AC3.**

10. Manual verification step (no code change): run a `psql` query confirming a property with no
    `stg_hotel_config` entry produces `NULL` (not an error) for `room_count` and `hotel_name` in
    `analytics.dim_property`. Document result in phase report (AC5 dashboard-layer confirmation).

11. **Test gate (Sub-phase 3):**
    ```
    cd eras_dbt && dbt build --select stg_hotel_config+dim_property
    ```
    Must pass before closing this EXECUTE pass.

### Sub-phase 4 — DONE (already implemented)

- [x] `extractor/src/main.py` wires `HotelConfigExtractor` alongside `ReservationExtractor`.
- [x] `extractor/tests/test_main_wiring.py` covers AC6 wiring assertion.
- Note: sub-phase 4 call site rename (`upsert_hotel_config` → `insert_hotel_config_snapshot`) is
  handled in sub-phase 2 step 2 above.

---

## Verification Evidence

| Gate / Scenario | Strategy | Proves SPEC criterion |
|---|---|---|
| `cd extractor && poetry run pytest tests/test_hotel_config_extractor.py -v` | Fully-Automated | AC1 — real room count retrievable per property |
| `cd extractor && poetry run pytest tests/test_hotel_config_database.py::test_insert_hotel_config_snapshot_appends_new_row -v` (needs running Postgres) | Hybrid | AC2 — snapshot append per extraction run, not overwrite |
| `cd eras_dbt && dbt build --select stg_hotel_config dim_property` | Fully-Automated | AC3 — `dim_property.room_count` reflects real extracted value |
| Manual/deferred: dashboard KPI value changes with `room_count` input — Known Gap per SPEC (`dashboard-unit-tests_NOTE_15-07-26.md`) | Hybrid (dbt layer automated; dashboard layer backlog) | AC4 — occupancy/RevPAR changes with room_count |
| `cd extractor && poetry run pytest tests/test_hotel_config_database.py -v` (noop-on-empty test + append test) | Fully-Automated | AC5 — missing/failed fetch does not silently overwrite good data |
| `cd extractor && poetry run pytest tests/test_main_wiring.py -v` | Fully-Automated | AC6 — both extractors run in single invocation |
| FEASIBILITY VERDICT (`booking-core-p1e-room-config_FEASIBILITY_16-07-26.md`) — already run, VIABLE, cited not re-executed | Agent-Probe (cost-class: needs-live-provider, already spent) | AC7 — `noOfRooms` semantics empirically confirmed |
| Manual `psql` spot-check: hotel_id with no hotel_config snapshot → `NULL` occupancy/revpar via `nullif()` SQL | Hybrid | AC5 (dashboard-layer NULL-safety confirmation) |

---

## Test Infra Improvement Notes

- **Append-only Postgres test pattern for `extractor/tests/`**: sub-phase 2 adds the first test
  asserting multi-row append (two calls → two rows) to `test_hotel_config_database.py`. This
  requires a live Postgres connection (needs-container tier). Confirm the test Postgres fixture
  pattern used by existing `test_hotel_config_database.py` tests at EXECUTE time; the new test
  should extend that same fixture, not create a new one.
- **dbt `extracted_at` column dependency**: `stg_hotel_config.sql`'s `DISTINCT ON ... ORDER BY
  extracted_at DESC` dedup requires an `extracted_at` column in `raw.enterprise_hotel_config`.
  Confirm this column exists in the live table before running `dbt build` (checklist step 6 notes
  this). If absent, add it in the `setup()` DDL change in sub-phase 2 step 1d.

---

## Resume and Execution Handoff

1. **Selected plan file path:** `process/features/booking-core/active/booking-core-p1e-room-config_16-07-26/booking-core-p1e-room-config_PLAN_16-07-26.md` (this file)
2. **Last completed phase or step:** PVL cycle 3 complete — Gate: CONDITIONAL. Sub-phases 1 and 4 already implemented. Sub-phases 2 and 3 are the remaining EXECUTE work.
3. **Validate-contract status:** CONDITIONAL — proceed to EXECUTE. Follow execute-agent instructions E1–E7 in the validate-contract below.
4. **Supporting context files loaded:** SPEC and FEASIBILITY VERDICT (this feature folder), `process/context/database/all-database.md`, `process/context/tests/all-tests.md`, `extractor/src/database.py`, `extractor/src/main.py`, `extractor/src/extractors/hotel_config.py`, `extractor/tests/test_hotel_config_database.py`, `extractor/tests/test_hotel_config_extractor.py`, `extractor/tests/test_main_wiring.py`, `eras_dbt/models/staging/stg_hotel_config.sql`, `eras_dbt/models/dimensional/dim_property.sql`.
5. **Next step for a fresh agent picking up mid-execution:** EXECUTE runs sub-phases 2 then 3 (sub-phases 1 and 4 are already done). Sub-phases are strictly sequential; do not start sub-phase 3 before sub-phase 2's test gate (checklist step 5) is green. Follow execute-agent instructions E1–E7 from the validate-contract.

---

## Known Gaps (carried forward, not built in this plan)

- No retention/pruning policy for `raw.enterprise_hotel_config` (unbounded growth) — explicitly out of scope per SPEC.
- AC4 dashboard-level KPI-changes-with-room-count assertion — backlog, tracked in `dashboard-unit-tests_NOTE_15-07-26.md` / `dashboard-e2e-tests_NOTE_15-07-26.md`.
- Whether OOS/OOO status is transient/date-ranged vs snapshot-only (FEASIBILITY VERDICT's own known-gap) — out of scope for this SPEC's aggregate-`noOfRooms`-only focus.
- Broader pytest/CI scaffolding for `extractor/` — tracked in `ci-pipeline_NOTE_15-07-26.md`.

---

## Validate Contract

Status: CONDITIONAL
Date: 16-07-26
date: 2026-07-16
generated-by: outer-pvl
supersedes: 2026-07-16 (outer-pvl) — PVL cycle 3: DROP CONSTRAINT→DROP INDEX FAIL resolved in cycle 3 supplement; prior contract Gate: BLOCKED (cycle 2)

Parallel strategy: Sequential
Rationale: Score 4/7 HIGH (S1 multi-package + S2 schema surface + S6 DDL change + S7 5+ files). Single-plan cycle-3 re-validate; Sequential appropriate for focused investigation.

Test gates (C3 5-column table — ADDITIVE):

| criterion id | behavior | strategy | proving test | gap-resolution |
|---|---|---|---|---|
| AC1 | Real room count retrievable per property (physical rooms via Room Config API) | Fully-Automated | `cd extractor && poetry run pytest tests/test_hotel_config_extractor.py -v` | A — proven; HotelConfigExtractor fetch_physical_room_count implemented and tested |
| AC2-shape | insert_hotel_config_snapshot uses plain INSERT with no ON CONFLICT clause | Fully-Automated | `cd extractor && poetry run pytest tests/test_hotel_config_database.py -v` | B — test assertion must be inverted (assert "ON CONFLICT" not in sql); added by this plan |
| AC2-append | Each extraction run appends a new row in real Postgres (COUNT(*) = 2 after two calls) | Hybrid | `cd extractor && poetry run pytest tests/test_hotel_config_database.py::test_insert_hotel_config_snapshot_appends_new_row -v` — precondition: live Postgres | B — execute-agent may use mock approach (fully-automated) as equivalent per E3 |
| AC3 | dim_property.room_count reflects real extracted value, not hardcoded default | Fully-Automated | `cd eras_dbt && dbt build --select stg_hotel_config dim_property` | B — dbt singular test for hotel_id=79017 preferred over generic not_null per E7; added by this plan |
| AC5 | None/missing room_count does not corrupt prior data; accepted without exception | Fully-Automated | `cd extractor && poetry run pytest tests/test_hotel_config_database.py -v` | A — proven; method rename in sub-phase 2 preserves assertion |
| AC6 | Both HotelConfigExtractor and ReservationExtractor run in single invocation | Fully-Automated | `cd extractor && poetry run pytest tests/test_main_wiring.py -v` | A — proven; mock target rename in sub-phase 2 step 3 required per E4 |

gap-resolution legend:
- A — proven now (gate passes in this cycle)
- B — fixed in this plan (gate added by this plan's checklist)
- D — backlog test-building stub (named residual; keep-active; continue)

C-4 reconciliation: `strategy:` column carries ONLY Fully-Automated / Hybrid / Agent-Probe. Known-Gap is a named residual carried via gap-resolution D, not a strategy value.

Legacy line form:
- AC1 extractor: Fully-automated: `cd extractor && poetry run pytest tests/test_hotel_config_extractor.py -v`
- AC2 shape: Fully-automated: `cd extractor && poetry run pytest tests/test_hotel_config_database.py -v`
- AC2 append: Hybrid: `pytest tests/test_hotel_config_database.py::test_insert_hotel_config_snapshot_appends_new_row` + precondition: live Postgres
- AC3 dbt: Fully-automated: `cd eras_dbt && dbt build --select stg_hotel_config dim_property`
- AC6 wiring: Fully-automated: `cd extractor && poetry run pytest tests/test_main_wiring.py -v`

Failing stubs (Fully-Automated rows with gap-resolution B only):

AC2-shape failing stub:
```
test("should insert without ON CONFLICT clause — plain append INSERT", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: assert SQL text has INSERT without ON CONFLICT after rename to insert_hotel_config_snapshot")
})
```

AC3 failing stub:
```
test("should have room_count IS NOT NULL for hotel_id with existing snapshot", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: dbt singular test asserting dim_property.room_count not null for hotel_id 79017 (physical_room_count=49 confirmed in FEASIBILITY)")
})
```

Dimension findings:
- Infra fit: PASS — DROP INDEX fix applied in cycle 3 supplement; plan correctly specifies `DROP INDEX IF EXISTS uq_enterprise_hotel_config_hotel_id`; execute-agent must also remove CREATE UNIQUE INDEX (E1)
- Test coverage: CONCERN — AC2-shape test assertion must be inverted (E2); AC2 hybrid needs live Postgres; mock approach acceptable (E3)
- Breaking changes: CONCERN — method rename across 3 files; removing coalesce from dim_property risks kpi_daily_snapshot not_null tests in multi-hotel future; safe in current single-hotel environment
- Security surface: PASS — DDL-only change; no auth/billing/secrets/API contract surface; BaseOperaClient auth reused unchanged
- Sub-phase 1 feasibility: PASS — hotel_config.py confirmed, HotelConfigExtractor confirmed, test_hotel_config_extractor.py confirmed; AC1 tests pass; marked DONE
- Sub-phase 2 feasibility: CONCERN — setup() requires both DROP INDEX and removal of CREATE UNIQUE INDEX (E1); test assertion must be inverted (E2); mock target rename in test_main_wiring.py (E4)
- Sub-phase 3 feasibility: CONCERN — hotel_name JSON path placeholder in plan (use existing correct path per E5); dbt selector inconsistency (E6); prefer singular dbt test for step 9 (E7)
- Sub-phase 4 feasibility: PASS — main.py wires both extractors confirmed; test_main_wiring.py covers AC6; call site rename handled in sub-phase 2; marked DONE

Execute-agent instructions (all 7 CONCERNs resolved via explicit instructions):
- E1 (Sub-phase 2 setup()): When editing database.py setup(), perform BOTH: (a) add `DROP INDEX IF EXISTS uq_enterprise_hotel_config_hotel_id;` immediately before the `CREATE TABLE IF NOT EXISTS raw.enterprise_hotel_config` block AND (b) remove the `CREATE UNIQUE INDEX IF NOT EXISTS uq_enterprise_hotel_config_hotel_id` block entirely. Adding only (a) without (b) recreates the unique index on every run — subsequent plain INSERTs would fail with a unique violation for hotel_id already in the table.
- E2 (Sub-phase 2 test assertion): Rename `test_upsert_hotel_config_executes_insert_on_conflict_sql` to `test_insert_hotel_config_snapshot_uses_plain_insert` AND invert its assertions: change `assert "ON CONFLICT" in sql` to `assert "ON CONFLICT" not in sql`, and remove `assert "DO UPDATE" in sql` (no longer applies to plain INSERT). All other tests that call `upsert_hotel_config` must be renamed to `insert_hotel_config_snapshot`.
- E3 (Sub-phase 2 AC2-append): Prefer mock approach for AC2-append: assert that the INSERT SQL text does NOT contain `ON CONFLICT` (fully-automated, no live Postgres needed). The hybrid approach (live Postgres, two calls → COUNT(*) = 2) is acceptable but optional for this plan.
- E4 (Sub-phase 2 call site): Update test_main_wiring.py line 53: change `patched_run["db"].upsert_hotel_config.assert_called_once()` to `patched_run["db"].insert_hotel_config_snapshot.assert_called_once()`.
- E5 (Sub-phase 3 hotel_name path): When writing stg_hotel_config.sql dedup SQL, use the existing correct JSON path `raw_data->'hotelConfigInfo'->>'hotelName'` for hotel_name. Do NOT use the plan's placeholder `raw_data->>'hotelName'` — the correct path is already confirmed in the existing stg_hotel_config.sql and in existing raw.enterprise_hotel_config rows.
- E6 (Sub-phase 3 dbt selector): Use `dbt build --select stg_hotel_config dim_property` (space-separated, two model names). Do NOT use `stg_hotel_config+dim_property` — the `+` is the dbt graph operator meaning "and downstream dependents", not a list separator for multiple model targets.
- E7 (Sub-phase 3 dbt test): For step 9, write a dbt singular test file in `eras_dbt/tests/` (e.g. `test_dim_property_room_count_not_null_hotel_79017.sql`) that SELECT-asserts COUNT = 0 WHERE hotel_id = '79017' AND room_count IS NULL. Do NOT add a generic `not_null` column test to dimensional/schema.yml — a generic not_null would fail for any hotel in stg_reservations without a hotel_config snapshot.

Open gaps:
- CONCERN accepted: AC2 hybrid — execute-agent uses mock approach (E3); no live Postgres required
- CONCERN accepted: kpi_daily_snapshot not_null tests (room_count/occupancy/revpar) — safe in current single-hotel environment; backlog for multi-hotel scenario
- No retention/pruning policy for raw.enterprise_hotel_config: known-gap: documented as NEW PLAN REQUIRED — see backlog/ci-pipeline_NOTE_15-07-26.md
- AC4 dashboard-level KPI test: known-gap: documented as NEW PLAN REQUIRED — see backlog/dashboard-unit-tests_NOTE_15-07-26.md, dashboard-e2e-tests_NOTE_15-07-26.md
- OOS transient/date-ranged semantics: known-gap: documented as NEW PLAN REQUIRED — FEASIBILITY VERDICT known-gap
- Broader pytest/CI scaffolding: known-gap: documented as NEW PLAN REQUIRED — see backlog/ci-pipeline_NOTE_15-07-26.md

What this coverage does NOT prove:
- AC1: does not prove live OPERA Cloud API behavior (HTTP mocked in tests); paginated room count >1000 rooms edge case not tested in production
- AC2-shape (mock): does not prove Postgres actually enforces uniqueness removal at DB level; only proves INSERT SQL text has no ON CONFLICT clause
- AC2-append (hybrid, optional): does not prove concurrent thread safety for simultaneous extractions
- AC3 (dbt build): does not prove NULL behavior for hotels without hotel_config snapshot (single-hotel test env only); does not prove downstream kpi_daily_snapshot calculations remain correct after removing coalesce fallback
- AC5: does not prove last-known-value survives an exception thrown BEFORE the INSERT call (only proves None room_count is accepted without error)
- AC6: automated mock wiring test only; manual integration run against live Postgres not confirmed in this cycle

Gate: CONDITIONAL (0 FAILs; 7 CONCERNs accepted and addressed via execute-agent instructions E1–E7; prior FAIL resolved in cycle 3 supplement)
Accepted by: user (cycle 3 explicit acceptance after reviewing all 7 CONCERNs)

---

## Autonomous Goal Block

SESSION GOAL: Extract real per-property room count from OPERA Cloud into dim_property.room_count — replace hardcoded default 250. Phase 1e booking-core.
Charter + umbrella plan: N/A — single SIMPLE plan
Autonomy: full for reversible changes; hard stops below
Hard stop conditions:
- Gate is CONDITIONAL — proceed to EXECUTE (do not re-validate unless source changes require it)
- Do not run live OPERA API calls (needs-live-provider) without explicit re-authorization from user
- Do not apply dbt run or dbt build against production schema without prior validation on test Postgres
- Do not create both room_config.py and hotel_config.py in parallel — design conflict resolved: hotel_config.py is the sole implementation
Next phase: EXECUTE — sub-phases 2 and 3 (sub-phases 1 and 4 already DONE). Follow execute-agent instructions E1–E7 above.
Validate contract: inline in plan (## Validate Contract section above) — Gate: CONDITIONAL
Execute start: `cd extractor && poetry run pytest tests/test_hotel_config_database.py tests/test_hotel_config_extractor.py tests/test_main_wiring.py -v` | `cd eras_dbt && dbt build --select stg_hotel_config dim_property` | high-risk pack: no (DDL change is index removal only — not auth/billing/migration class)
