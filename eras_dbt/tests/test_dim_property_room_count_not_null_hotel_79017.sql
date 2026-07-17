-- Singular test (E7): asserts dim_property.room_count is populated for the known hotel
-- with an existing hotel_config snapshot (hotel_id=79017, physical_room_count=49 confirmed
-- in FEASIBILITY VERDICT). A generic not_null column test is intentionally avoided because
-- it would fail for any hotel in stg_reservations lacking a hotel_config snapshot (AC5).
-- Singular test convention: passes when this query returns zero rows.
select
    hotel_id,
    room_count
from {{ ref('dim_property') }}
where hotel_id = '79017'
  and room_count is null
