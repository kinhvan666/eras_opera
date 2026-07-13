---
name: context:all-database
description: "Kimball dimensional model, PostgreSQL warehouse, dbt transformation layer — the database group entrypoint/router"
keywords: database, warehouse, kimball, dimensional model, star schema, fact, dimension, dbt, postgres, postgresql, staging, ELT, ETL, grain, conformed dimension, SCD, slowly changing dimension
related: []
date: 13-07-26
---

# Database Context

This file is the canonical database/warehouse context entrypoint for ErasOpera.

Use it after `process/context/all-context.md` when the task needs the Kimball dimensional model,
PostgreSQL warehouse conventions, or the dbt transformation layer.

---

## Scope

This group covers:

- **Kimball dimensional modeling** for ErasOpera: fact/dimension design, grain declaration,
  conformed dimensions, slowly changing dimensions (SCD types), and star-schema layout
- **PostgreSQL warehouse** conventions: raw → staging → dimensional layering, schema naming
- **dbt transformation layer**: model naming (`stg_` / `dim_` / `fct_`), materialization choices,
  data tests (`not_null`, `unique`, `relationships`, `accepted_values`)
- **OPERA Cloud source → model mapping**: how entities from the `docs/` specs land as staging and
  then feed dimensions and facts

It does not cover:

- OPERA Cloud API extraction/auth mechanics (that is Python extract/load — see the relevant feature
  `_GUIDE.md` under `process/features/` and the spec in `docs/`)
- Test running mechanics (see `process/context/tests/all-tests.md`)
- Feature-specific load plans (those live in `process/features/{feature}/`)

## Read When

Read this entrypoint when:

- designing or modifying a fact or dimension table
- adding a dbt staging model for a new OPERA Cloud entity
- deciding the grain of a fact, or whether a dimension is conformed across domains
- choosing an SCD strategy for an attribute that changes over time
- reviewing warehouse schema naming or layering

## Quick Routing

Deeper docs will be added as the warehouse takes shape. Planned (not yet created):

- a dimensional-model catalog — fact/dimension list, grains, conformed dims
- a dbt-conventions doc — dbt project layout, naming, materializations, tests
- an opera-source-mapping doc — OPERA entity → staging → dim/fact mapping

Until those exist, use the reference `docs/The Data Warehouse Toolkit - Kimball.pdf` for modeling
decisions and the matching OPERA spec in `docs/` for source field definitions.

## Design Principles (canonical for ErasOpera)

1. **Layering:** `raw` (immutable, as-pulled from OPERA API) → `staging` (typed/cleaned, one model
   per source entity, `stg_` prefix) → `dimensional` (`dim_` / `fct_`).
2. **Grain first:** every fact table declares its grain in one sentence before columns are chosen.
3. **Conformed dimensions:** shared dimensions (`dim_property`/hotel, `dim_date`, `dim_guest`,
   `dim_room_type`, `dim_rate_code`) are defined once and reused across booking-core, financials,
   operations, and crm-profiles — never re-modeled per feature.
4. **SCD:** guest and configuration attributes that change over time use an explicit SCD type
   (default Type 2 for audit-relevant history); document the choice per dimension.
5. **Reprocessable:** keep raw append-only so the dimensional layer can be rebuilt from source.

## Candidate Facts and Conformed Dimensions (initial, to refine in PLAN)

- **Facts:** `fct_reservation` (grain: reservation-night or reservation, TBD), `fct_folio_transaction`
  (cashiering), `fct_ar_transaction`, `fct_housekeeping_task`, `fct_room_inventory_daily`.
- **Conformed dimensions:** `dim_date`, `dim_property`, `dim_guest`, `dim_room_type`, `dim_rate_code`,
  `dim_room`, `dim_market_source`, `dim_channel`.

These are starting hypotheses — confirm grain and conformance during RESEARCH/PLAN against the OPERA
specs before building.

## Source Paths

- `process/context/database/all-database.md` (this file)
- `docs/The Data Warehouse Toolkit - Kimball.pdf` (modeling reference)
- `docs/OPERA Cloud *.json` (source schema specs)

## Update Triggers

Update this group when:

- a new fact or dimension is added, or a grain/conformance decision changes
- the dbt project layout or naming conventions change
- the warehouse layering (raw/staging/dimensional) or Postgres schema naming changes
- an OPERA Cloud source mapping is established or revised
