-- eras_dbt/models/staging/stg_hotel_config.sql
-- Extracts hotel name and room count from raw Enterprise Configuration API response.
-- Source: GET /ent/config/v1/hotels/{hotelId} -> raw.enterprise_hotel_config
-- raw.enterprise_hotel_config is append-only (one row per extraction run), so dedup
-- to the latest snapshot per hotel via DISTINCT ON (hotel_id) ORDER BY extracted_at DESC.
with source as (
    select * from {{ source('raw', 'enterprise_hotel_config') }}
    where hotel_id is not null
),
deduped as (
    select distinct on (hotel_id)
        hotel_id,
        raw_data,
        physical_room_count,
        extracted_at
    from source
    order by hotel_id, extracted_at desc
)
select
    hotel_id,
    raw_data->'hotelConfigInfo'->>'hotelName'                                        as hotel_name,
    coalesce(
        physical_room_count,
        (raw_data->'hotelConfigInfo'->'generalInformation'->>'roomCount')::int
    )                                                                                as room_count,
    extracted_at
from deduped
