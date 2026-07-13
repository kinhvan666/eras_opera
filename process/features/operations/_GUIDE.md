# operations

<!-- Part of ErasOpera -->

## Scope

Operations covers the hotel-operations side of the OPERA Cloud data pipeline: **front desk,
housekeeping, room inventory/configuration, room rotation, and activities/events**. It owns
extraction and staging of these entities to feed facts such as `fct_housekeeping_task` and
`fct_room_inventory_daily`, plus room/activity dimensions.

## Key Source Files

Application code does not exist yet (greenfield). Authoritative source schemas in `docs/`:

- `docs/OPERA Cloud Front Desk Operations Service (26.2.0.0).json` — check-in/out, room assignment
- `docs/OPERA Cloud Front Desk Configuration API (26.2.0.0).json` — front-desk reference data
- `docs/OPERA Cloud Housekeeping Service API (26.2.0.0).json` — room status, tasks
- `docs/OPERA Cloud Inventory API (26.2.0.0).json` — room/type inventory
- `docs/Opera Cloud Inventory Asynchronous API (26.2.0.0).json` — bulk inventory pulls
- `docs/OPERA Cloud Room Configuration API (26.2.0.0).json` — rooms, room types
- `docs/OPERA Cloud Room Rotation Configuration Service API (26.2.0.0).json` — rotation config
- `docs/OPERA Cloud Room Rotation Service API (26.2.0.0).json` — rotation runtime
- `docs/OPERA Cloud Activity API (26.2.0.0).json` + `Activity Management` — guest activities
- `docs/OPERA Cloud Leisure Management API (26.2.0.0).json` — leisure/spa/golf
- `docs/OPERA Cloud Event Configuration API (26.2.0.0).json` + `Sales Event Management` — events

## Related Context

- `process/context/database/all-database.md` — dimensional model, operations fact grains, conformed dims
- `process/context/tests/all-tests.md` — pytest + dbt test commands
- `process/context/all-context.md` — stack and repository overview

## Current Status

Status: not-started

## Folder Contents

```
process/features/operations/
  active/       -- in-progress plans (each task in a {slug}_{date}/ task folder)
  completed/    -- archived completed plans
  backlog/      -- deferred/future plans
```

All artifacts colocate inside each `{slug}_{date}/` task folder. Do NOT create `reports/` or
`references/` sibling dirs.
