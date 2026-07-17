---
phase: booking-core-p1e-room-config-execute
date: 2026-07-17
status: COMPLETE
feature: booking-core
plan: process/features/booking-core/active/booking-core-p1e-room-config_16-07-26/booking-core-p1e-room-config_PLAN_16-07-26.md
---

# EXECUTE Report — Real Room Count Extraction (Sub-phases 2 & 3)

## What Was Done

Sub-phases 2 (database layer) and 3 (dbt layer) implemented exactly per plan + validate-contract E1–E7. Sub-phases 1 and 4 were already DONE.

### Sub-phase 2 — append-only migration (AC2, AC5)
- `extractor/src/database.py`:
  - `setup()`: added `DROP INDEX IF EXISTS uq_enterprise_hotel_config_hotel_id;` before the `enterprise_hotel_config` CREATE TABLE block AND removed the `CREATE UNIQUE INDEX` block entirely (E1).
  - Renamed `upsert_hotel_config()` → `insert_hotel_config_snapshot()`, changed to plain `INSERT` with no `ON CONFLICT` clause (append-only).
- `extractor/src/main.py`: call site renamed to `insert_hotel_config_snapshot(...)`.
- `extractor/tests/test_main_wiring.py`: mock assertion updated to `insert_hotel_config_snapshot` (E4).
- `extractor/tests/test_hotel_config_database.py`: renamed `test_upsert_hotel_config_executes_insert_on_conflict_sql` → `test_insert_hotel_config_snapshot_uses_plain_insert` with inverted assertion `assert "ON CONFLICT" not in sql` (E2/E6); renamed all other `upsert_hotel_config` tests; added `test_insert_hotel_config_snapshot_appends_new_row` using the mock approach (E3 — no live Postgres).

### Sub-phase 3 — dbt layer (AC3, hotel_name)
- `eras_dbt/models/staging/stg_hotel_config.sql`: added `DISTINCT ON (hotel_id) ORDER BY hotel_id, extracted_at DESC` dedup (table now append-only). Kept the existing correct hotel_name path `raw_data->'hotelConfigInfo'->>'hotelName'` (E5).
- `eras_dbt/models/dimensional/dim_property.sql`: LEFT JOIN `stg_hotel_config` on hotel_id; `room_count` and `hotel_name` sourced from it; removed the `coalesce(..., var('room_count_default'))` fallback and `'Unknown Hotel'` fallback — room_count/hotel_name are now NULL when no snapshot (AC5).
- `eras_dbt/tests/test_dim_property_room_count_not_null_hotel_79017.sql`: singular dbt test scoped to hotel_id='79017' (E7 — not a generic not_null column test).

## Test Gate Outcomes
- Sub-phase 2: `cd extractor && poetry run pytest tests/test_hotel_config_database.py tests/test_hotel_config_extractor.py tests/test_main_wiring.py -v` → **12 passed**.
- Sub-phase 3: `cd eras_dbt && dbt build --select stg_hotel_config dim_property` → **PASS=6 WARN=0 ERROR=0** (incl. E7 singular test PASS — room_count=49 populated for hotel 79017, proving AC3).

## What Was Skipped or Deferred
- AC2-append hybrid (live Postgres two-call COUNT=2): used mock equivalent per E3; live Postgres path optional and not run.
- Checklist step 10 manual `psql` NULL spot-check: single-hotel test env has only hotel 79017; NULL-for-missing-hotel behavior is structurally guaranteed by the LEFT JOIN but not separately probed (matches validate-contract "What this coverage does NOT prove").

## Plan Deviations
None. All E1–E7 instructions followed as written.

## Test Infra Gaps Found
- Pre-existing dbt deprecation warning (`MissingArgumentsPropertyInGenericTestDeprecation`) on `fct_reservation_night` relationships test — unrelated to this change; non-blocking.

## Closeout Packet
- Selected plan: `process/features/booking-core/active/booking-core-p1e-room-config_16-07-26/booking-core-p1e-room-config_PLAN_16-07-26.md`
- Finished: sub-phases 2 & 3; both test gates green.
- Verified: AC1/AC2-shape/AC3/AC5/AC6 via automated gates. Unverified: live OPERA API, concurrent-extraction thread safety, downstream kpi_daily_snapshot correctness after coalesce removal (single-hotel env), AC4 dashboard KPI (backlog).
- Remaining cleanup: UPDATE PROCESS archival + context capture.
- Best next state: Ready for UPDATE PROCESS archival (pending EVL confirmation run).

## Forward Preview
### Test Infra Found
Extractor pytest uses mocked psycopg2 (no live PG); dbt build runs against dev Postgres target with real hotel 79017 snapshot.
### Blast Radius Changes
`extractor/src/database.py`, `extractor/src/main.py`, 2 extractor test files, `eras_dbt/models/staging/stg_hotel_config.sql`, `eras_dbt/models/dimensional/dim_property.sql`, new `eras_dbt/tests/test_dim_property_room_count_not_null_hotel_79017.sql`.
### Commands to Stay Green
`cd extractor && poetry run pytest tests/test_hotel_config_database.py tests/test_hotel_config_extractor.py tests/test_main_wiring.py -v` ; `cd eras_dbt && dbt build --select stg_hotel_config dim_property`
### Dependency Changes
None.
