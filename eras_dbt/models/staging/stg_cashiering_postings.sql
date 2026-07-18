-- eras_dbt/models/staging/stg_cashiering_postings.sql
-- Staging layer over raw.cashiering_postings.
-- Filters to Revenue-type postings only (transactionType = 'Revenue' in JSONB).
-- Excludes transaction_code 9xxx rows (Wrapper/folio header — AC-2).
-- Derives revenue_category from transaction_code numeric prefix.
-- Carries reservation_id (nullable), cashier_id, reference as pass-through columns.

with source as (
    select * from {{ source('raw', 'cashiering_postings') }}
),

staged as (
    select
        -- Indexed top-level columns from extractor _to_row()
        transaction_no,
        hotel_id,
        revenue_date::date                                                as revenue_date,
        transaction_code,
        posted_amount::numeric                                            as posted_amount,

        -- reservation_id: nullable JSONB path — unmatched postings have NULL (E2, E5)
        raw_data->'guestInfo'->'reservationId'->>'id'                    as reservation_id,

        -- Pass-through provenance columns (B3)
        raw_data->>'cashierId'                                            as cashier_id,
        raw_data->>'reference'                                            as reference,

        -- Revenue category derivation from transaction_code numeric prefix (B2, E4)
        -- ELSE 'Other' is mandatory — never produce NULL for a Revenue-type row
        case
            when transaction_code like '1%' then 'Room'
            when transaction_code like '2%' then 'FnB'
            when transaction_code like '3%' then 'FnB'
            when transaction_code like '6%' then 'FnB'
            when transaction_code like '7%' then 'Tax'
            when transaction_code like '8%' then 'ServiceCharge'
            else 'Other'
        end                                                               as revenue_category

    from source
    -- Revenue-type filter: transactionType is JSONB-only, not a top-level column (E1, A4)
    where raw_data->>'transactionType' = 'Revenue'
    -- Exclude Wrapper/folio header rows: 9xxx prefix (E3, AC-2)
    and transaction_code not like '9%'
)

select * from staged
