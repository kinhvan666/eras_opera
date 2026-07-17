-- eras_dbt/models/dimensional/dim_property.sql
-- Property dimension - one row per distinct hotel_id observed in stg_reservations.
-- room_count: real extracted value from stg_hotel_config; NULL when no snapshot exists.
-- hotel_name: from stg_hotel_config; NULL when no snapshot.
-- Never falls back to hardcoded defaults (locked AC5 requirement).
select
    p.hotel_id,
    c.hotel_name,
    c.room_count
from (
    select distinct hotel_id
    from {{ ref('stg_reservations') }}
    where hotel_id is not null
) p
left join {{ ref('stg_hotel_config') }} c
    on p.hotel_id = c.hotel_id
