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

## Current Implementation State (as of 2026-07-19)

The `eras_dbt/` dbt project is built and running against a dev PostgreSQL instance.

### Raw Layer (PostgreSQL `raw` schema)

| Table | Source | Insert pattern | Key column |
|---|---|---|---|
| `raw.booking_core_reservations` | OPERA Cloud Reservation API | Upsert (ON CONFLICT DO UPDATE) | reservation_id |
| `raw.enterprise_hotel_config` | OPERA Cloud Enterprise Config + Room Config APIs | Append-only (plain INSERT, no unique constraint) — one row per extraction run | extracted_at |
| `raw.cashiering_postings` | OPERA Cloud Cashiering API (`/financialPostings`) | Upsert (ON CONFLICT (transaction_no) DO UPDATE) | transaction_no (INTEGER PK) |

`raw.cashiering_postings` schema: `transaction_no INTEGER PRIMARY KEY, hotel_id TEXT, revenue_date DATE, transaction_code TEXT, posted_amount NUMERIC, raw_data JSONB NOT NULL, extracted_at TIMESTAMPTZ DEFAULT NOW()`. Table created inside `insert_cashiering_postings()` (not in `setup()`). Stores ALL transaction types raw (Revenue + Payment + Wrapper) — Revenue filter applied in staging.

### Staging Models (`eras_dbt/models/staging/`)

| Model | Key logic |
|---|---|
| `stg_reservations` | Flattens raw JSON from `raw.booking_core_reservations`; parses arrival/departure dates, rates, segments |
| `stg_hotel_config` | Deduplicates append-only `raw.enterprise_hotel_config` via `DISTINCT ON (hotel_id) ORDER BY extracted_at DESC`; extracts `room_count` (physical_room_count) and `hotel_name` (from `raw_data->'hotelConfigInfo'->>'hotelName'`) |
| `stg_cashiering_postings` | Filters `raw.cashiering_postings` to Revenue-type rows only (`raw_data->>'transactionType' = 'Revenue'`); excludes 9xxx Wrapper rows (`transaction_code NOT LIKE '9%'`); derives `revenue_category` from transaction_code prefix (1x=Room, 2x/3x/6x=FnB, 7x=Tax, 8x=ServiceCharge, ELSE=Other); carries `reservation_id` (JSONB path, nullable), `cashier_id`, `reference`; 12,885 rows as of 2026-07-18 backfill |

### Dimensional Models (`eras_dbt/models/dimensional/`)

| Model | Grain | Key columns | Notes |
|---|---|---|---|
| `dim_date` | One row per calendar date | date_key, date, year, month, quarter, day_of_week | Standard calendar dimension |
| `dim_property` | One row per distinct hotel_id in stg_reservations | hotel_id, hotel_name, room_count | **room_count is real extracted value** from stg_hotel_config (NULL when no snapshot, never hardcoded); hotel_name also from stg_hotel_config |
| `dim_rate` | One row per distinct rate_code | rate_code, rate_description | From stg_reservations |
| `fct_reservation_night` | One row per reservation-night | hotel_id, date_key, rate_code, room_nights, revenue, occupancy, revpar | Primary fact; powers dashboard KPIs |
| `fct_folio_line` | One row per cashiering posting (`transaction_no`) | fact_sk (md5), transaction_no, hotel_id, revenue_date, revenue_category, posted_amount, reservation_id (nullable FK), cashier_id, reference | Cashiering fact; 12,885 rows (2026 backfill); independently queryable for unmatched-posting reconciliation (NULL reservation_id rows preserved) |

### dbt Tests

- `schema.yml` files in `staging/` and `dimensional/` carry standard `not_null` / `unique` / `relationships` tests
- `eras_dbt/tests/test_dim_property_room_count_not_null_hotel_79017.sql` — singular test asserting dim_property.room_count IS NOT NULL for hotel_id='79017' (physical_room_count=49 confirmed via Room Config API)
- `eras_dbt/tests/test_ac3_reservation_fk_match_rate.sql` — singular test asserting ≥95% FK match rate between non-null reservation_id in stg_cashiering_postings and stg_reservations. Currently fails (35% match — data scope gap: cashiering covers 2026; stg_reservations covers earlier window). Will pass once reservation extraction is expanded to cover 2026+.

### dbt Commands

```bash
cd eras_dbt && dbt build --select stg_hotel_config dim_property --profiles-dir .   # space-separated targets
cd eras_dbt && dbt build --profiles-dir .                                           # full rebuild
cd eras_dbt && dbt test --profiles-dir .                                            # tests only
```

Use `--profiles-dir .` when `eras_dbt/.user.yml` holds the credentials (gitignored).

### Python Extractor (`extractor/`)

- Package manager: **poetry** (`pyproject.toml` at repo root, `poetry.lock`)
- `extractor/src/`: `client.py` (OPERA Cloud OAuth + HTTP), `database.py` (raw table setup + insert methods), `main.py` (orchestration)
- `HotelConfigExtractor`: calls Enterprise Config + Room Config APIs; writes via `insert_hotel_config_snapshot()` (append-only, no ON CONFLICT)
- `ReservationExtractor`: calls Reservation API; writes via `insert_raw_data()` (upsert)
- `CashieringExtractor`: calls Cashiering API (`/financialPostings`); writes via `insert_cashiering_postings()` (upsert on transaction_no); extracts in ≤30-day windows; `hasMore` primary pagination stop + `len(chunk) < limit` safety fallback; `BACKFILL_START_DATE = date(2026, 1, 1)` module constant; constructor takes `client` only (DB operations called directly in `main.py`)

### Dashboard (`dashboard/`)

- Streamlit app (`dashboard/app.py`) with Dockerfile
- Tabs: Revenue, Trends, Segments, Pacing — reads from `analytics.dim_property`, `analytics.fct_reservation_night`, and KPI views

---

## Quick Routing

Deeper docs will be added as the warehouse grows. Planned (not yet created):

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
   `dim_room_type`, `dim_rate`) are defined once and reused across booking-core, financials,
   operations, and crm-profiles — never re-modeled per feature.
4. **SCD:** guest and configuration attributes that change over time use an explicit SCD type
   (default Type 2 for audit-relevant history); document the choice per dimension.
5. **Reprocessable:** keep raw append-only so the dimensional layer can be rebuilt from source.

## Candidate Facts and Conformed Dimensions (initial, to refine in PLAN)

- **Facts:** `fct_reservation` (grain: reservation-night or reservation, TBD), `fct_folio_transaction`
  (cashiering), `fct_ar_transaction`, `fct_housekeeping_task`, `fct_room_inventory_daily`.
- **Conformed dimensions:** `dim_date`, `dim_property`, `dim_guest`, `dim_room_type`, `dim_rate`,
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
