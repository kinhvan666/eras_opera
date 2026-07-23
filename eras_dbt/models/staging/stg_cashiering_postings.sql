-- eras_dbt/models/staging/stg_cashiering_postings.sql
-- Staging layer over raw.cashiering_postings.
-- Filters to Revenue-type postings only (transactionType = 'Revenue' in JSONB).
-- Excludes transaction_code 9xxx rows (Wrapper/folio header — AC-2).
-- Derives revenue_category from transaction_code numeric prefix.
-- Carries reservation_id (nullable), cashier_id, reference as pass-through columns.

with source as (
    select * from {{ source('raw', 'cashiering_postings') }}
),

tc as (
    select * from {{ ref('stg_transaction_codes') }}
),

staged as (
    select
        -- Indexed top-level columns from extractor _to_row()
        s.transaction_no,
        s.hotel_id,
        s.revenue_date::date                                                as revenue_date,
        s.transaction_code,
        s.posted_amount::numeric                                            as posted_amount,

        -- reservation_id: nullable JSONB path — unmatched postings have NULL (E2, E5)
        s.raw_data->'guestInfo'->'reservationId'->>'id'                    as reservation_id,

        -- Pass-through provenance columns (B3)
        s.raw_data->>'cashierId'                                            as cashier_id,
        s.raw_data->>'reference'                                            as reference,

        -- Use classification from transaction codes if available, fallback to prefix
        case
            when t.classification is not null then t.classification
            when s.transaction_code like '1%' then 'Room'
            when s.transaction_code like '2%' then 'FnB'
            when s.transaction_code like '3%' then 'FnB'
            when s.transaction_code like '6%' then 'FnB'
            when s.transaction_code like '7%' then 'Tax'
            when s.transaction_code like '8%' then 'ServiceCharge'
            else 'Other'
        end                                                               as revenue_category,
        
        -- net_amount calculation: excludes Tax and ServiceCharge
        case
            when t.classification in ('Tax', 'ServiceCharge') then 0
            when s.transaction_code like '7%' or s.transaction_code like '8%' then 0
            else coalesce(s.posted_amount::numeric, 0)
        end                                                               as net_amount

    from source s
    left join tc t on s.transaction_code = t.transaction_code and s.hotel_id = t.hotel_id
    -- Revenue-type filter: transactionType is JSONB-only, not a top-level column (E1, A4)
    where s.raw_data->>'transactionType' = 'Revenue'
    -- Exclude Wrapper/folio header rows: 9xxx prefix (E3, AC-2)
    and s.transaction_code not like '9%'
)

select * from staged
