-- eras_dbt/models/dimensional/dim_property.sql
-- Property dimension - one row per distinct hotel_id observed in stg_reservations.
-- hotel_name and room_count sourced from Enterprise Configuration API via stg_hotel_config.
-- Fallback to var('room_count_default') when config not yet extracted for a hotel_id.
select
    r.hotel_id,
    coalesce(c.hotel_name, 'Unknown Hotel') as hotel_name,
    coalesce(c.room_count, {{ var('room_count_default') }}) as room_count
from (
    select distinct hotel_id
    from {{ ref('stg_reservations') }}
    where hotel_id is not null
) r
left join {{ ref('stg_hotel_config') }} c using (hotel_id)