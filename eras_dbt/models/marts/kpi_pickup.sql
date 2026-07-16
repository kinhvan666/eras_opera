-- eras_dbt/models/marts/kpi_pickup.sql
-- Pickup analysis: 7/30/90 day forward-looking pickup per property
-- Grain: (hotel_id, window_days) — one row per property per pickup window
-- Based on reservations with arrival_date in future relative to snapshot date

with snapshot_date as (
    -- Use the latest business_date in the fact table as the "today" reference
    select max(business_date)::date as snap_date
    from {{ ref('fct_reservation_night') }}
),
future_reservations as (
    select
        f.hotel_id,
        f.reservation_id,
        f.arrival_date,
        f.night_amount,
        f.booking_date,
        s.snap_date,
        (f.arrival_date - s.snap_date)::int as days_until_arrival
    from {{ ref('fct_reservation_night') }} f
    cross join snapshot_date s
    where f.arrival_date > s.snap_date
      and f.reservation_status != 'Cancelled'
),
pickup_windows as (
    select
        hotel_id,
        sum(case when days_until_arrival <= 7 then 1 else 0 end) as pickup_7d_rooms,
        sum(case when days_until_arrival <= 7 then night_amount else 0 end) as pickup_7d_revenue,
        sum(case when days_until_arrival <= 30 then 1 else 0 end) as pickup_30d_rooms,
        sum(case when days_until_arrival <= 30 then night_amount else 0 end) as pickup_30d_revenue,
        sum(case when days_until_arrival <= 90 then 1 else 0 end) as pickup_90d_rooms,
        sum(case when days_until_arrival <= 90 then night_amount else 0 end) as pickup_90d_revenue
    from future_reservations
    group by 1
)
select
    hotel_id,
    7 as window_days,
    pickup_7d_rooms as pickup_rooms,
    pickup_7d_revenue as pickup_revenue
from pickup_windows
union all
select
    hotel_id,
    30 as window_days,
    pickup_30d_rooms as pickup_rooms,
    pickup_30d_revenue as pickup_revenue
from pickup_windows
union all
select
    hotel_id,
    90 as window_days,
    pickup_90d_rooms as pickup_rooms,
    pickup_90d_revenue as pickup_revenue
from pickup_windows