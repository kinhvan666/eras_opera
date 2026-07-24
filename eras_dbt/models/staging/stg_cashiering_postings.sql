-- eras_dbt/models/staging/stg_cashiering_postings.sql
-- Staging layer over raw.cashiering_postings.
-- Filters to Revenue-type postings only (transactionType = 'Revenue' in JSONB).
-- Excludes transaction_code 9xxx rows (Wrapper/folio header — AC-2).
-- Derives revenue_category and net_amount from transaction_code prefix heuristics.
-- Does NOT depend on stg_transaction_codes (API response lacked classification fields).

with source as (
    select * from {{ source('raw', 'cashiering_postings') }}
),

staged as (
    select
        s.transaction_no,
        s.hotel_id,
        s.revenue_date::date                                                as revenue_date,
        s.transaction_code,
        s.posted_amount::numeric                                            as posted_amount,

        -- reservation_id: nullable JSONB path
        s.raw_data->'guestInfo'->'reservationId'->>'id'                    as reservation_id,

        -- Pass-through provenance columns
        s.raw_data->>'cashierId'                                            as cashier_id,
        s.raw_data->>'reference'                                            as reference,

        -- Revenue category from transaction_code prefix (matched to Manager Report categories)
        case
            when s.transaction_code like '1%' then 'Room'
            when s.transaction_code like '70%' then 'Room'
            when s.transaction_code like '80%' or s.transaction_code like '81%' then 'Room'
            when s.transaction_code like '2%' or s.transaction_code like '3%' or s.transaction_code like '71%' then 'FnB'
            else 'Other'
        end                                                               as revenue_category,

        -- net_amount: 7xxx and 8xxx codes are tax/service-charge → subtract from revenue
        case
            when s.transaction_code like '7%' or s.transaction_code like '8%' then 0
            else coalesce(s.posted_amount::numeric, 0)
        end                                                               as net_amount

    from source s
    where s.raw_data->>'transactionType' = 'Revenue'
    and s.transaction_code not like '9%'
)

select * from staged
