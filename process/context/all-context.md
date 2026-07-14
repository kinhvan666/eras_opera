---
name: context:all-context
description: "Root context router for ErasOpera — OPERA Cloud → Kimball dimensional warehouse; stack, structure, routing"
keywords: overview, architecture, stack, opera cloud, kimball, warehouse, dimensional, etl, elt, dbt, postgres, python, hospitality, routing, feature areas
related: []
date: 13-07-26
---

# ErasOpera - All Context

Last updated: 2026-07-13

This file is the root context entrypoint for the repo.

Use it for two things:

1. quick routing to the right context pack or root file
2. broad architecture and repository understanding

Start here before loading deeper context files.

---

## What ErasOpera Is

**ErasOpera is a hospitality data warehouse / analytics platform built on Oracle OPERA Cloud.**

It extracts operational data from Oracle OPERA Cloud (hotel Property Management System) via its
REST APIs, then transforms that data into a **Kimball-style dimensional model** (fact + dimension
tables, star schema) in PostgreSQL to power BI and reporting for hotel operations.

- **Data sources:** 40 Oracle OPERA Cloud OpenAPI (Swagger 2.0) specs live in `docs/` — Reservation,
  Rate, Block, Cashiering, Accounts Receivable, CRM, Front Desk, Housekeeping, Inventory, Activity,
  Sales Event, Provisioning, and configuration/master-data services (all release 26.2.0.0; Nor1
  Upsell is 24.4.0.0). These specs are the authoritative schema source-of-truth for extraction.
- **Methodology:** Ralph Kimball dimensional modeling. `docs/The Data Warehouse Toolkit - Kimball.pdf`
  is the reference for star-schema design (grain, conformed dimensions, slowly changing dimensions).
- **Shape:** ELT/ETL — Python extract/load from OPERA Cloud APIs → raw/staging in Postgres → dbt
  SQL models build the dimensional layer.

**Project stage:** greenfield. No application source code or manifest exists yet — this repo
currently holds the API specs, the Kimball reference, and this agent harness. Architecture is being
established through the RIPER-5 workflow.

---

## How This File Works (the `all-*.md` Convention)

Every `process/context/` directory has one `all-*.md` entrypoint that acts as an attachable quick
router for that domain. This root file (`all-context.md`) is the top-level router. Context groups
each have their own `all-{group}.md` entrypoint.

**The pattern:**

```
process/context/
  all-context.md                      <-- THIS FILE: root router
  planning/
    all-planning.md                   <-- group router for planning
  tests/
    all-tests.md                      <-- group router for tests
  database/
    all-database.md                   <-- group router for the Kimball warehouse
```

**How agents use it:**

1. Agent reads `all-context.md` first (this file)
2. Finds the relevant context group from the routing tables below
3. Reads that group's `all-{group}.md` entrypoint
4. Only then loads the specific deep doc needed

This layered routing keeps context windows small. Never load the whole `process/context/` tree.

---

## Quick Start

For most substantial tasks:

1. read this file first
2. choose the smallest relevant root file or context group from the tables below
3. only then load deeper files

---

## Current Root Entry Points

<!-- The two tables below (Root Entry Points + Context Groups) are GENERATED from each
     context doc's frontmatter by `discover-context.mjs --emit-routing`. Do NOT hand-edit
     between the GENERATED markers — your edits will be overwritten on the next rebuild.
     To change a row, edit the owning doc's frontmatter (description / keywords) and re-emit.
     `--check-routing` fails lint if this block drifts from the frontmatter on disk. -->

<!-- GENERATED:routing -->
| File | Read when |
|---|---|
| `process/context/all-context.md` | any substantial planning, research, review, or implementation task |
| `process/context/database/all-database.md` | Kimball dimensional model, PostgreSQL warehouse, dbt transformation layer — the database group entrypoint/router |
| `process/context/planning/all-planning.md` | Planning context router for ErasOpera — plan-shape calibration, SIMPLE vs COMPLEX, plan examples |
| `process/context/tests/all-tests.md` | Testing context router for ErasOpera — pytest (extract/load) + dbt test (dimensional model), commands, debugging |

## Current Context Groups

| Group | Entry point | Scope |
|---|---|---|
| `database/` | `process/context/database/all-database.md` | Kimball dimensional model, PostgreSQL warehouse, dbt transformation layer — the database group entrypoint/router |
| `planning/` | `process/context/planning/all-planning.md` | Planning context router for ErasOpera — plan-shape calibration, SIMPLE vs COMPLEX, plan examples |
| `tests/` | `process/context/tests/all-tests.md` | Testing context router for ErasOpera — pytest (extract/load) + dbt test (dimensional model), commands, debugging |
<!-- /GENERATED:routing -->

## Task Routing Table

| If the task involves... | Load first | Then load |
|---|---|---|
| architecture or stack questions | `all-context.md` | this file (section below) |
| dimensional model / warehouse / dbt / schema work | `all-context.md`, `database/all-database.md` | the OPERA spec in `docs/` for the source domain |
| OPERA Cloud API extraction (any domain) | `all-context.md` | the matching feature `_GUIDE.md` under `process/features/` + the domain's spec in `docs/` |
| testing or verification | `all-context.md`, `tests/all-tests.md` | the specific test doc |
| creating a new plan | `all-context.md`, `planning/all-planning.md` | the relevant example PRD |
| context maintenance | `all-context.md` | run `vc-audit-context` after edits |

## Feature Areas (OPERA domain → feature folder)

Feature-scoped work lives under `process/features/{feature}/`. Domain-to-feature mapping:

| Feature folder | OPERA Cloud source APIs (in `docs/`) |
|---|---|
| `booking-core` | Reservation, Reservation Async, Reservation Master Data Mgmt, Rate, Rate Plan Async, Block, Block Config, Block Reservation Async, Channel Config, Nor1 Upsell |
| `financials` | Cashiering, Cashiering Async, Accounts Receivables, Back Office Operations |
| `operations` | Front Desk Config, Front Desk Operations, Housekeeping, Inventory, Inventory Async, Room Config, Room Rotation (Config + Service), Activity, Activity Management, Leisure Management, Event Config, Sales Event Management |
| `crm-profiles` | Customer Management Service, Customer Relationship Management, CRM Async, CRM Config |

**Shared config / master-data services** (used across domains, not a feature folder yet): Enterprise
Configuration, Integration Configuration, Integration Processor, Export Configuration, Content
Service, DataValueMapping, List of Values Management, Report Master Data Management, Provisioning.

## Context Group Lifecycle

Context groups are durable knowledge domains, not feature folders.

Create a group when:

- a topic has 3+ durable docs
- a single doc exceeds roughly 800 lines with separable subtopics
- multiple agents repeatedly need only one slice of a large context file
- the topic maps to a stable operational domain (tests, database, ingestion, etc.)

Do not create a group when the content is a temporary report, a plan/execution artifact, or is
feature-specific (that belongs in `process/features/...`).

Run the `vc-audit-context` skill after every context organization change.

## Naming Convention

There are no `README.md` files inside `process/context/`. Canonical entrypoints use `all-*.md`:

- root: `process/context/all-context.md`
- group: `process/context/{group}/all-{group}.md`

## Context Update Protocol

When durable project knowledge changes:

1. update the smallest relevant context file
2. update this file if routing, ownership, naming, or groups changed
3. update the owning `all-{group}.md` entrypoint when a group exists
4. run `vc-audit-context`

---

## Repository Structure

```
ErasOpera/
  docs/                      -- source-of-truth inputs (READ-ONLY reference)
    OPERA Cloud *.json       -- 40 Oracle OPERA Cloud OpenAPI (Swagger 2.0) specs, v26.2.0.0
    Nor1 Integrated Upsell API (24.4.0.0).json
    The Data Warehouse Toolkit - Kimball.pdf   -- dimensional modeling reference
  process/
    context/                 -- this context system (all-context.md + groups)
    general-plans/           -- general plans (active/completed/backlog, task-folder convention)
    features/                -- feature-scoped storage (booking-core, financials, operations, crm-profiles)
    development-protocols/    -- RIPER-5 methodology docs
  .claude/ .codex/ .agents/  -- agent harness (agents + skills)
  vibecode-pro-max-kit/      -- the harness installer source (NOT part of the ErasOpera app)
  AGENTS.md  CLAUDE.md        -- managed protocol files
```

> **Note:** application source code (Python extract/load, dbt project, Postgres DDL/migrations) does
> not exist yet. When created, expect a Python package + a dbt project directory; update this section.

## Technology Stack

- **Language / runtime:** Python (data engineering — extract/load layer). Version + package manager
  (pip / uv / poetry) TBD at first EXECUTE.
- **Warehouse:** PostgreSQL (hosts raw/staging + the Kimball dimensional model).
- **Transformation:** dbt (SQL models) builds fact/dimension tables. dbt tests assert model integrity.
- **Orchestration:** none yet — start with scripts/cron; adopt Dagster/Airflow/Prefect later if needed.
- **Data sources:** Oracle OPERA Cloud REST APIs (OAuth-secured; specs in `docs/`).
- **Modeling methodology:** Kimball dimensional modeling (star schema, conformed dimensions, SCDs).

## Key Patterns and Conventions

- **`docs/` is the schema source-of-truth.** OPERA Cloud OpenAPI specs define the shape of every
  extracted entity. When building an extractor or a staging model, read the matching spec in `docs/`
  first rather than guessing field names.
- **ELT layering:** raw (as-pulled from API) → staging (cleaned/typed) → dimensional (dbt
  fact/dimension). Keep the raw layer immutable/append-only for reprocessing.
- **Dimensional discipline:** every fact table declares its grain explicitly; dimensions are
  conformed across domains (a `dim_property`, `dim_date`, `dim_guest` should be shared, not
  duplicated per feature). See `database/all-database.md`.
- **Async APIs:** several OPERA services have an "Asynchronous" variant (Reservation Async, Cashiering
  Async, etc.) for bulk/deferred pulls — prefer these for large historical backfills.
- **Naming:** follow Python (`snake_case`) and dbt (`snake_case` models, `stg_`/`dim_`/`fct_`
  prefixes) conventions once the code layer is established.

## Environment and Configuration

Config files and env var groups do not exist yet (greenfield). Anticipated env var categories
(names only, populate when the code layer lands):

- **OPERA Cloud auth:** OAuth client id/secret, token URL, app key, environment/hostname, hotel/chain code
- **Warehouse:** `DATABASE_URL` (or discrete `PG*` host/port/user/password/db) for Postgres
- **dbt:** profile/target settings (`profiles.yml`)

Never store secret values in context files — record variable names only.

## Scan Metadata

- Generated: 2026-07-13T02:27:34Z
- HEAD: no-git (not a git working tree at scan time)
- Mode: fresh
- Package manager: none yet (Python; pip/uv/poetry TBD)
