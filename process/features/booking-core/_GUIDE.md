# booking-core

<!-- Part of ErasOpera -->

## Scope

Booking-core covers the revenue/booking heart of the OPERA Cloud data pipeline: **reservations,
rates, and blocks**. It owns extraction of these entities from OPERA Cloud and their staging into
the warehouse so they can feed `fct_reservation` and conformed dimensions (`dim_guest`,
`dim_rate_code`, `dim_room_type`, `dim_property`, `dim_date`).

## Key Source Files

Application code does not exist yet (greenfield). The authoritative source schemas are the OPERA
Cloud specs in `docs/`:

- `docs/OPERA Cloud Reservation API (26.2.0.0).json` — core reservation CRUD/read
- `docs/OPERA Cloud Reservation Asynchronous API (26.2.0.0).json` — bulk/deferred reservation pulls
- `docs/OPERA Cloud Reservation Master Data Management API (26.2.0.0).json` — reservation reference data
- `docs/OPERA Cloud Rate API (26.2.0.0).json` — rate codes/plans
- `docs/Opera Cloud Rate Plan Asynchronous Service API (26.2.0.0).json` — bulk rate pulls
- `docs/OPERA Cloud Block API (26.2.0.0).json` — group blocks
- `docs/OPERA Cloud Block Configuration API (26.2.0.0).json` — block reference data
- `docs/OPERA Cloud Block Reservation Asynchronous API (26.2.0.0).json` — bulk block-reservation pulls
- `docs/OPERA Cloud Channel Configuration API (26.2.0.0).json` — distribution channels
- `docs/Nor1 Integrated Upsell API (24.4.0.0).json` — upsell offers/acceptance

## Related Context

- `process/context/database/all-database.md` — dimensional model, `fct_reservation` grain, conformed dims
- `process/context/tests/all-tests.md` — pytest (extractors) + dbt test commands
- `process/context/all-context.md` — stack and repository overview

## Current Status

Status: not-started

## Folder Contents

```
process/features/booking-core/
  active/       -- in-progress plans (each task in a {slug}_{date}/ task folder)
  completed/    -- archived completed plans
  backlog/      -- deferred/future plans
```

All artifacts colocate inside each `{slug}_{date}/` task folder. Do NOT create `reports/` or
`references/` sibling dirs.
