-- eras_dbt/models/marts/kpi_daily_snapshot.sql
-- Daily grain KPIs per property: one row per property per business_date
-- Grain: (business_date, hotel_id)
-- All financial KPIs flagged as ESTIMATED in dashboard (room_count from dim_property is manual for V1)
--
-- Operational KPIs (reservations, room_nights, revenue, adr, occupancy, revpar, avg_lead_time)
-- exclude Cancelled and NoShow so they reflect actual stayed business only.
--
-- Cancellation rate is calculated on reservation-grain (not night-grain) to avoid
-- over-counting multi-night cancelled stays: cancelled_reservations / total_reservations.

with operational as (
    -- Stayed nights only: CheckedOut (and any future In-House status)
    select
        f.business_date,
        f.hotel_id,
        p.room_count,
        count(distinct case when f.business_date = f.arrival_date then f.reservation_id end) as reservations,
        count(*)                                                                    as room_nights,
        sum(f.night_amount)                                                         as total_revenue,
        -- ADR excludes complimentary/voucher ($0) nights from both numerator and
        -- denominator — standard revenue management practice so ADR reflects
        -- actual paid rate, not average diluted by free stays.
        sum(f.night_amount) filter (where f.night_amount > 0)
            / nullif(count(*) filter (where f.night_amount > 0), 0)                as adr,
        count(*) filter (where f.night_amount > 0)::numeric / nullif(p.room_count * 1.0, 0)                          as occupancy,
        sum(f.night_amount) / nullif(p.room_count * 1.0, 0)                        as revpar,
        avg((f.arrival_date - f.booking_date))                                      as avg_lead_time
    from {{ ref('fct_reservation_night') }} f
    join {{ ref('dim_property') }} p on f.hotel_id = p.hotel_id
    where f.reservation_status not in ('Cancelled', 'NoShow')
    group by 1, 2, 3
),

cancellation as (
    -- Cancellation rate on reservation-grain per business_date:
    -- a reservation is attributed to each night of its original stay window,
    -- then deduplicated so one reservation counts once per day.
    -- Rate = distinct cancelled reservations / distinct total reservations.
    select
        f.business_date,
        f.hotel_id,
        count(distinct f.reservation_id)                                                as total_reservations,
        count(distinct f.reservation_id) filter (where f.reservation_status in ('Cancelled', 'NoShow')) as cancelled_reservations,
        count(distinct f.reservation_id) filter (where f.reservation_status in ('Cancelled', 'NoShow'))::numeric
            / nullif(count(distinct f.reservation_id), 0)                              as cancellation_rate
    from {{ ref('fct_reservation_night') }} f
    group by 1, 2
)

select
    o.business_date,
    o.hotel_id,
    o.room_count,
    o.reservations,
    o.room_nights,
    o.total_revenue,
    coalesce(o.adr, 0) as adr,
    o.occupancy,
    o.revpar,
    o.avg_lead_time,
    coalesce(c.cancellation_rate, 0) as cancellation_rate
from operational o
left join cancellation c
    on o.business_date = c.business_date
    and o.hotel_id = c.hotel_id