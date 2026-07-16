---
name: plan:booking-core-p1e-room-config-spec
description: "SPEC for extracting real per-property room count from OPERA Cloud Room Configuration API, replacing the hardcoded 250 in dim_property"
date: 16-07-26
feature: booking-core
---

# SPEC: Real Room Count Extraction (dim_property.room_count)

## Summary

The booking-core dashboard shows occupancy and RevPAR (revenue per available room) for each hotel
property. Both metrics depend on knowing how many rooms a property actually has. Today that number
is a hardcoded guess (`250`, or a config default) written into the warehouse model — it is correct
by coincidence for at most one property and wrong for every other. This SPEC covers replacing that
guess with the real room count pulled from OPERA Cloud, so occupancy and RevPAR are trustworthy for
every property, not just the one that happens to have 250 rooms.

## User Stories / Jobs To Be Done

- As a hotel operations manager viewing the dashboard, I want occupancy % and RevPAR to reflect my
  property's actual room count, so that I can trust the KPIs instead of manually correcting them.
- As a data/analytics owner, I want `dim_property.room_count` sourced from OPERA Cloud instead of a
  hardcoded default, so that adding a new property to the warehouse doesn't silently produce wrong
  KPIs until someone remembers to update a config value.
- As a future maintainer, I want the room-count value refreshed periodically (not captured once and
  frozen forever), so that if a property's room count changes (renovation, room block taken
  out-of-service), the dashboard reflects reality within a reasonable time.

## What The User Wants (Behavioral Outcomes)

- `dim_property.room_count` reflects a real number pulled from OPERA Cloud for each property present
  in the warehouse, not a fixed default value shared across all properties.
- Occupancy and RevPAR figures on the existing dashboard change accordingly for any property whose
  real room count differs from the current hardcoded default — this is the visible proof the fix
  worked.
- If OPERA Cloud is unreachable or returns no room data for a property, the system does not silently
  fall back to a wrong number without any trace — there must be a visible/loggable indication that a
  property's room count is stale or missing, rather than a quiet wrong default.
- The extraction runs as part of the existing extract/load process (same operational shape as
  reservation extraction), not as a manual one-off script a person has to remember to run.

## Flow / State Diagram

```
[Extractor run triggered]
        |
        v
  Call OPERA Cloud /roomsSummary  (scoped to current property via hotelId)
        |
        +-- success --> parse rooms.roomsSummary[] --> noOfRooms per hotelId
        |                          |
        |                          v
        |                 write a NEW SNAPSHOT ROW to raw room-config table
        |                 (one row per extraction run — history preserved,
        |                 NOT an upsert/overwrite like reservations)
        |                          |
        |                          v
        |                 stg_room_config (dbt staging model, dedup to
        |                 latest snapshot per property)
        |                          |
        |                          v
        |                 dim_property.room_count sourced from
        |                 stg_room_config instead of a hardcoded var
        |                          |
        |                          v
        |                 Dashboard occupancy / RevPAR recompute
        |                 using real room_count
        |
        +-- failure/empty --> existing property's room_count stays at
                               last known good value (or flagged stale) --
                               NOT silently replaced with a new wrong default
```

## Acceptance Criteria (Testable Outcomes)

1. **A real room count is retrievable per property from OPERA Cloud.**
   Calling the Room Configuration `/roomsSummary` endpoint for a known test property returns a
   room count value (`noOfRooms`) for that property's `hotelId`.
   `proven by:` extractor unit test with a fixture response for `/roomsSummary` (mocked HTTP layer,
   per existing test-context convention — no live OPERA calls in the unit suite).
   `strategy:` Fully-Automated.

2. **The extracted room count lands in the warehouse's raw layer as a snapshot, keyed by property
   and extraction run.**
   After an extraction run, the raw room-config table contains a new row per `hotelId` with its
   `noOfRooms` value and the run's timestamp — a repeat run adds a new row rather than overwriting
   the prior one, preserving history of room count changes over time.
   `proven by:` integration test against a test Postgres schema — run the extractor twice against
   fixture responses with different `noOfRooms` values, assert both snapshot rows exist.
   `strategy:` Fully-Automated (needs-container for the test Postgres instance).

3. **`dim_property.room_count` reflects the real extracted value, not the hardcoded default.**
   For a test property with a known non-250 room count fixture, `dim_property.room_count` in the
   built dbt model equals that fixture value (the latest snapshot), not the previous default.
   `proven by:` `dbt test` / `dbt build` assertion on `dim_property` comparing against seeded
   staging fixture data.
   `strategy:` Fully-Automated.

4. **Occupancy and RevPAR on the dashboard change when room_count changes.**
   Given two builds of the dimensional model with different `room_count` inputs for the same
   property, the dashboard's occupancy/RevPAR output for that property differs accordingly.
   `proven by:` existing dashboard test coverage extended to assert the KPI value is a function of
   `dim_property.room_count` (see Known Gap below — dashboard has no automated test suite yet per
   `dashboard-unit-tests_NOTE_15-07-26.md` and `dashboard-e2e-tests_NOTE_15-07-26.md` backlog notes).
   `strategy:` Hybrid — automated at the dbt/model layer (criterion 3); dashboard-level confirmation
   is a manual/backlog-tracked check until the dashboard test backlog items are picked up.

5. **A missing or failed OPERA room-config fetch does not silently overwrite good data with a wrong
   default.**
   When `/roomsSummary` returns no data or errors for a property, the extraction records/logs the
   failure and the property's `room_count` in the warehouse is left at its last known snapshot value
   (or explicitly flagged), rather than reverting to a hardcoded default.
   `proven by:` extractor unit test simulating an empty/error response, asserting no destructive
   overwrite occurs and a failure is logged.
   `strategy:` Fully-Automated.

6. **The extraction fits the existing extract/load operational pattern, scoped to the current
   property.**
   The new extractor runs via the same invocation path as the reservations extractor (same
   `__main__`/scheduling entrypoint), calling `/roomsSummary` filtered to `settings.opera_hotel_id`,
   requiring no new manual step for an operator.
   `proven by:` manual/integration check — run the existing extractor entrypoint and confirm the
   room-config extraction executes alongside reservations, scoped to the configured hotel.
   `strategy:` Agent-Probe (cost-class: cheap-local — confirms wiring, not external service
   behavior).

7. **`noOfRooms` semantics are empirically confirmed before the extraction logic is finalized.**
   A one-time, read-only live probe against the real OPERA Cloud OHIP endpoint confirms whether
   `noOfRooms` includes out-of-service/pseudo rooms or only active/sellable rooms, so downstream KPI
   calculations use a known-correct interpretation rather than an assumption.
   `proven by:` `vc-feasibility-test` / `VC-FEASIBILITY-PROBE-NEEDED` empirical probe run during
   INNOVATE or VALIDATE (double opt-in already granted by the user — see Constraints).
   `strategy:` Agent-Probe (cost-class: needs-live-provider).

## Out Of Scope

- Building a multi-property selection UI or any new dashboard page — this SPEC only fixes the data
  source behind the existing `room_count` field.
- Enterprise Configuration API integration (unrelated master-data domain).
- Room Rotation Config/Service APIs (a separate, unrelated OPERA domain — do not conflate "room
  configuration" with "room rotation").
- Per-room-type or per-room breakdown reporting (`roomSummary[]` sub-array) — only the aggregate
  `noOfRooms` count is needed for this SPEC's KPIs.
- Building any UI or reporting feature on top of the room-count history snapshots — snapshotting is
  decided for data preservation (see Constraints), but analyzing/visualizing that history is not a
  deliverable of this SPEC.
- Multi-property fetch — V1 is scoped to the single current property only (see Constraints).
- Formally relocating this capability into a future `operations` feature area — noted as a future
  review item only (see Constraints), not an action taken now.
- Building full pytest scaffolding/CI for the whole extractor package — only the tests needed to
  prove this SPEC's acceptance criteria are in scope; broader test-infrastructure buildout is
  tracked as a Known Gap / backlog item (see `ci-pipeline_NOTE_15-07-26.md`).

## Constraints

- Must reuse the existing OPERA auth/header wiring (`BaseOperaClient._set_auth_headers`) — no new
  auth mechanism.
- Must follow the existing raw → staging → dimensional layering convention (see
  `process/context/database/all-database.md`).
- Correct endpoint is `/roomsSummary` — the `/hotels/{hotelId}/rooms` endpoint is explicitly
  unsuitable (no count field, no pagination metadata) and must not be used for this purpose.
- **Raw persistence is snapshot-per-run, not upsert.** DECIDED: the raw room-config table must
  append a new row per extraction run (preserving history of room count changes over time). This is
  a deliberate deviation from the reservations raw-table pattern (`INSERT ... ON CONFLICT DO
  UPDATE`) — INNOVATE/PLAN must not default back to the reservations upsert pattern out of habit.
- **Fetch scope is single-property only.** DECIDED: `/roomsSummary` is called filtered to the
  current property via the `hotelId` query param, using `settings.opera_hotel_id` — matching the
  existing single-property assumption across the pipeline. No multi-property/unfiltered fetch in
  V1.
- **A live-provider probe is authorized.** The user has approved (double opt-in) a one-time,
  read-only `GET /roomsSummary` call against the real OPERA Cloud OHIP endpoint (current `.env`
  credentials/`opera_hotel_id`) to inspect the actual `noOfRooms` value and any accompanying fields.
  No data mutation. This probe is to be executed during INNOVATE or VALIDATE (not during SPEC) as a
  `VC-FEASIBILITY-PROBE-NEEDED` / `vc-feasibility-test` empirical check; its result becomes a locked
  design constraint on `noOfRooms` semantics (see Acceptance Criterion 7).
- This work is scoped under `booking-core` because its direct purpose is correcting KPI accuracy on
  the existing booking-core dashboard. When an `operations` feature area is established later, this
  Room Configuration integration should be reviewed for whether it should move or generalize there
  — flagged here so it isn't forgotten, not acted on now.
- No pytest test harness currently exists for `extractor/src/` (confirmed, greenfield). This SPEC's
  acceptance criteria require some minimal test coverage to be provable — INNOVATE/PLAN must decide
  how much scaffolding is introduced as part of this work versus treated as a Known Gap.

## Open Questions

None. All three questions raised during SPEC drafting have been resolved by the user as of
16-07-26. Resolved decisions:

1. **`noOfRooms` out-of-service/pseudo-room semantics — RESOLVED: live-provider probe approved.**
   The user has approved a one-time, read-only `GET /roomsSummary` call against the real OPERA
   Cloud OHIP endpoint (current `.env` credentials/`opera_hotel_id`), to inspect the actual
   `noOfRooms` value and any accompanying fields. No data mutation. This is double-opt-in
   authorization for a `needs-live-provider` cost-class feasibility probe. The probe itself is NOT
   run during SPEC — it is authorized to run during INNOVATE or VALIDATE as a
   `VC-FEASIBILITY-PROBE-NEEDED` / `vc-feasibility-test` empirical check (see Acceptance Criterion 7
   and Constraints), and its result becomes a locked design constraint at that point.

2. **Raw table persistence — RESOLVED: snapshot per extraction run.**
   Each extraction run writes a new row (snapshot), preserving history of room count changes over
   time. This is a deliberate deviation from the reservations raw-table pattern, which upserts in
   place. INNOVATE/PLAN must implement snapshot-per-run, not default to the reservations
   upsert-on-conflict pattern out of habit (see Constraints).

3. **Fetch scope — RESOLVED: single current property only.**
   `/roomsSummary` is called filtered to the current property via the `hotelId` query param, using
   `settings.opera_hotel_id`. No multi-property/unfiltered fetch is in scope for this SPEC (see
   Constraints).

## Background / Research Findings

- **Correct endpoint:** `/roomsSummary` (not `/hotels/{hotelId}/rooms`, which lacks a count field and
  pagination metadata). Response shape: `roomsSummaryDetails.rooms.roomsSummary[]`, each item
  (`configRoomsSummaryType`) has `hotelId` + `noOfRooms: integer` ("Current number of rooms") +
  `roomSummary[]` (per-room breakdown, not needed for this SPEC). Full pagination metadata present:
  `rooms.hasMore` / `rooms.totalResults` / `rooms.offset` / `rooms.limit` / `rooms.count` —
  structurally parallel to the existing reservations pagination shape (`reservations.hasMore` /
  `reservations.reservationInfo`).
- **`hotelId` is an optional query parameter** on `/roomsSummary` (not a path param), so
  `settings.opera_hotel_id` (`extractor/src/config.py`) can scope the call to the current
  single-property deployment.
- **`BaseOperaClient.fetch_all()`** (`extractor/src/client.py`) is currently hardcoded to the
  reservations JSON shape (`data.get("reservations", {})`, item key `reservationInfo`) and will need
  generalizing (parametrized root/item keys) or a sibling fetch method — an INNOVATE/PLAN decision,
  not resolved here. `_fetch_page()` (the retry-isolated method, recently fixed for a duplicate-rows
  bug) is already generic and reusable as-is.
- **Pattern to mirror (with one deliberate deviation):** `extractor/src/extractors/reservations.py`
  (extractor class) → `extractor/src/database.py` (raw JSONB table + unique index + `INSERT ... ON
  CONFLICT DO UPDATE`, see `insert_raw_data`) → `eras_dbt/models/staging/stg_reservations.sql`
  (`DISTINCT ON` dedup by `extracted_at DESC`) → `eras_dbt/models/dimensional/dim_property.sql`
  (currently: `SELECT DISTINCT hotel_id FROM stg_reservations`, `room_count` from
  `{{ var('room_count_default') }}` in `eras_dbt/dbt_project.yml`, defaulting to 250). The room-config
  raw table deviates from this pattern at the `insert_raw_data` step: snapshot-append, not
  upsert-on-conflict (user decision, see Constraints).
- **Auth already solved:** `BaseOperaClient._set_auth_headers()` handles `x-app-key`, `x-hotelid`,
  and Bearer token — no new auth code needed.
- **Origin of the problem:** the booking-core Phase 1d dashboard plan
  (`process/features/booking-core/active/booking-core-p1d-dashboard_15-07-26/booking-core-p1d-dashboard_PLAN_15-07-26.md`)
  explicitly hardcoded `room_count=250` as a stated V1 shortcut ("Missing room_count in prod...
  Hardcode 250 in dim_property for V1; env var in V2" — see its Assumptions/Risks sections). This
  SPEC is that V2 follow-up.
- **No test harness exists yet** for `extractor/src/` (confirmed via `process/context/tests/all-tests.md`
  — "No test suite, no pytest config... exist yet (greenfield)"). Acceptance criteria in this SPEC
  that require automated proof will need at least minimal pytest scaffolding introduced as part of
  the implementation, or will be explicitly logged as Known Gaps if descoped.
- **No conflicting prior plan** — verified `process/features/operations/` and
  `process/features/booking-core/` contain no existing plan/note covering room-count extraction
  beyond the hardcode-and-defer note in the p1d-dashboard plan.
- **User resolution session (16-07-26):** all 3 Open Questions from the initial SPEC draft were
  resolved in this same session — see `## Open Questions` above and the corresponding Constraints
  entries for the locked decisions.
