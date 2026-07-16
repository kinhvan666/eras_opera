-- eras_dbt/models/staging/stg_hotel_config.sql
-- Extracts hotel name and room count from raw Enterprise Configuration API response.
-- Source: GET /ent/config/v1/hotels/{hotelId} -> raw.enterprise_hotel_config
select
    hotel_id,
    raw_data->'hotelConfigInfo'->>'hotelName'                                        as hotel_name,
    coalesce(
        physical_room_count,
        (raw_data->'hotelConfigInfo'->'generalInformation'->>'roomCount')::int
    )                                                                                as room_count,
    extracted_at
from {{ source('raw', 'enterprise_hotel_config') }}
