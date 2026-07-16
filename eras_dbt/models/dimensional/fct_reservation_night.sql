-- eras_dbt/models/dimensional/fct_reservation_night.sql
-- Fact table at reservation-night grain: one row per property per reservation per stay night
-- Night explosion via lateral join with generate_series
-- Composite surrogate key for grain uniqueness (md5 of hotel_id|reservation_id|business_date)
with reservation_nights as (
    select
        s.hotel_id,
        s.reservation_id,
        s.profile_id,
        s.rate_plan_code,
        s.market_code,
        s.source_of_business,
        s.room_type,
        s.total_amount,
        s.arrival_date,
        s.departure_date,
        s.created_at::date as booking_date,
        s.reservation_status,
        gs.date_day as business_date,
        -- Calculate night count for per-night revenue allocation
        (s.departure_date - s.arrival_date)::int as night_count
    from {{ ref('stg_reservations') }} s
    cross join lateral generate_series(
        s.arrival_date,
        s.departure_date - interval '1 day',
        interval '1 day'
    ) gs(date_day)
    where s.hotel_id is not null
      and s.reservation_id is not null
      and s.arrival_date is not null
      and s.departure_date is not null
      and s.departure_date > s.arrival_date
)
select
    md5(concat_ws('|', hotel_id, reservation_id, business_date)) as fact_sk,
    hotel_id,
    reservation_id,
    business_date,
    profile_id,
    rate_plan_code,
    market_code,
    source_of_business,
    room_type,
    (total_amount::numeric / night_count) as night_amount,
    arrival_date,
    booking_date,
    reservation_status
from reservation_nights