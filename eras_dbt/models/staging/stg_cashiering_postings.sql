-- eras_dbt/models/staging/stg_cashiering_postings.sql
-- Staging layer over raw.cashiering_postings.
-- Filters to Revenue-type postings only.
-- Derives revenue_category and net_amount from transaction_code prefix.

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

        s.raw_data->'guestInfo'->'reservationId'->>'id'                    as reservation_id,
        s.raw_data->>'cashierId'                                            as cashier_id,
        s.raw_data->>'reference'                                            as reference,

        -- Revenue category from transaction_code prefix
        case
            when s.transaction_code like '1%' then 'Room'
            -- 70xx are FB-type tax/service codes (Room prefix, FnB economic category)
            when s.transaction_code like '70%' then 'FnB'
            -- 8xxx tax codes are Room-related VAT adjustments
            when s.transaction_code like '80%' or s.transaction_code like '81%' then 'Room'
            when s.transaction_code like '2%' or s.transaction_code like '3%' or s.transaction_code like '71%' then 'FnB'
            else 'Other'
        end                                                               as revenue_category,

        -- net_amount: 7xxx and 8xxx are tax/service-charge → subtract
        case
            when s.transaction_code like '7%' or s.transaction_code like '8%'
                then -coalesce(s.posted_amount::numeric, 0)
            else coalesce(s.posted_amount::numeric, 0)
        end                                                               as net_amount

    from source s
    where s.raw_data->>'transactionType' = 'Revenue'
    and s.transaction_code not like '9%'
)

select * from staged
