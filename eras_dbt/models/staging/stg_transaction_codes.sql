-- eras_dbt/models/staging/stg_transaction_codes.sql
-- Extracts transaction codes from the OPERA Cloud API response.
-- Source: GET /csh/v1/hotels/{hotelId}/transactionCodes -> raw.transaction_codes

with source as (
    select * from {{ source('raw', 'transaction_codes') }}
    where hotel_id is not null
),
deduped as (
    select distinct on (hotel_id)
        hotel_id,
        raw_data,
        extracted_at
    from source
    order by hotel_id, extracted_at desc
),
unnested as (
    select
        hotel_id,
        jsonb_array_elements(
            coalesce(
                raw_data->'transactionCodes',
                raw_data->'trxCodes',
                raw_data->'hotelTransactionCodes'
            )
        ) as tc,
        extracted_at
    from deduped
)
select distinct on (hotel_id, tc->>'transactionCode')
    hotel_id,
    tc->>'transactionCode' as transaction_code,
    tc->>'description' as description,
    case when tc->>'transactionCodeType' like '{' || '%' then tc->'transactionCodeType'->>'code' else tc->>'transactionCodeType' end as transaction_code_type,
    case when tc->>'transactionGroup' like '{' || '%' then tc->'transactionGroup'->>'code' else tc->>'transactionGroup' end as transaction_group,
    case when tc->>'transactionSubGroup' like '{' || '%' then tc->'transactionSubGroup'->>'code' else tc->>'transactionSubGroup' end as transaction_sub_group,
    case when tc->>'classification' like '{' || '%' then coalesce(tc->'classification'->'transactionType'->>'code', tc->'classification'->>'code') else tc->>'classification' end as classification,
    tc->'generatesSetup' as generates_setup,
    extracted_at
from unnested
order by hotel_id, tc->>'transactionCode', extracted_at desc
