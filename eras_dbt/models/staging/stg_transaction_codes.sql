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
select distinct on (hotel_id, tc->>'code')
    hotel_id,
    tc->>'code' as transaction_code,
    tc->'description'->>'defaultText' as description,
    tc->'classification'->'transactionType'->>'code' as transaction_code_type,
    tc->'classification'->'group'->>'code' as transaction_group,
    tc->'classification'->'subgroup'->>'code' as transaction_sub_group,
    tc->'classification'->>'type' as classification,
    tc->'generatesSetup' as generates_setup,
    (tc->>'taxInclusive')::boolean as tax_inclusive,
    extracted_at
from unnested
order by hotel_id, tc->>'code', extracted_at desc
