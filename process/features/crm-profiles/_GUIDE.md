# crm-profiles

<!-- Part of ErasOpera -->

## Scope

CRM-profiles covers guest and customer master data: **profiles, CRM, and loyalty/relationship
data** from OPERA Cloud. It owns extraction and staging of guest/customer entities to build the
conformed `dim_guest` (and related customer dimensions), which are shared across booking-core,
financials, and operations.

## Key Source Files

Application code does not exist yet (greenfield). Authoritative source schemas in `docs/`:

- `docs/OPERA Cloud API for Customer Management Service (26.2.0.0).json` — customer/guest profiles
- `docs/OPERA Cloud Customer Relationship Management API (26.2.0.0).json` — CRM core
- `docs/OPERA Cloud CRM Asynchronous API (26.2.0.0).json` — bulk CRM/profile pulls
- `docs/OPERA Cloud CRM Configuration API (26.2.0.0).json` — CRM reference data

## Related Context

- `process/context/database/all-database.md` — `dim_guest` design, SCD strategy, conformed dimensions
- `process/context/tests/all-tests.md` — pytest + dbt test commands
- `process/context/all-context.md` — stack and repository overview

## Current Status

Status: not-started

## Folder Contents

```
process/features/crm-profiles/
  active/       -- in-progress plans (each task in a {slug}_{date}/ task folder)
  completed/    -- archived completed plans
  backlog/      -- deferred/future plans
```

All artifacts colocate inside each `{slug}_{date}/` task folder. Do NOT create `reports/` or
`references/` sibling dirs.
