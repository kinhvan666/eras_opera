-- eras_dbt/models/dimensional/fct_folio_line.sql
-- Fact table: one row per revenue posting (transaction_no grain).
-- Source: stg_cashiering_postings (Revenue-type only, Wrapper rows excluded).
-- Keeps ALL rows from staging — including rows with NULL reservation_id (unmatched postings).
-- No dim joins in the model body; hotel_id and revenue_date are raw FK keys.

with source as (
    select * from {{ ref('stg_cashiering_postings') }}
)

select
    -- Surrogate key: single-column grain, no concat_ws needed (E3)
    md5(transaction_no::text)   as fact_sk,

    -- Grain key
    transaction_no,

    -- Raw FK keys (no dim join — E4)
    hotel_id,
    revenue_date,

    -- Nullable FK to reservations (unmatched postings kept — B2, E4)
    reservation_id,

    -- Measures
    posted_amount,
    net_amount,

    -- Categorisation (derived in staging — no CASE WHEN needed here)
    revenue_category,

    -- Provenance pass-through
    cashier_id,
    reference

from source
