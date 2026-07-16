-- eras_dbt/models/marts/kpi_pacing.sql
-- Pacing comparison: current year vs prior year by property
-- Grain: (date, hotel_id) — one row per property per date in current year
-- Prior year data may be NULL (first year of data) — handle gracefully

with current_year as (
    select
        business_date,
        hotel_id,
        occupancy,
        adr,
        revpar,
        total_revenue,
        reservations,
        room_nights
    from {{ ref('kpi_daily_snapshot') }}
),
prior_year as (
    select
        (business_date + interval '1 year')::date as business_date,
        hotel_id,
        occupancy as prior_occupancy,
        adr as prior_adr,
        revpar as prior_revpar,
        total_revenue as prior_revenue,
        reservations as prior_reservations,
        room_nights as prior_room_nights
    from {{ ref('kpi_daily_snapshot') }}
)
select
    c.business_date,
    c.hotel_id,
    c.occupancy as current_occupancy,
    p.prior_occupancy,
    case
        when p.prior_occupancy is null then null
        when p.prior_occupancy = 0 then null
        else round((c.occupancy - p.prior_occupancy) / nullif(p.prior_occupancy, 0) * 100, 2)
    end as occupancy_pace_pct,
    c.adr as current_adr,
    p.prior_adr,
    case
        when p.prior_adr is null then null
        when p.prior_adr = 0 then null
        else round((c.adr - p.prior_adr) / nullif(p.prior_adr, 0) * 100, 2)
    end as adr_pace_pct,
    c.revpar as current_revpar,
    p.prior_revpar,
    case
        when p.prior_revpar is null then null
        when p.prior_revpar = 0 then null
        else round((c.revpar - p.prior_revpar) / nullif(p.prior_revpar, 0) * 100, 2)
    end as revpar_pace_pct,
    c.total_revenue as current_revenue,
    p.prior_revenue,
    case
        when p.prior_revenue is null then null
        when p.prior_revenue = 0 then null
        else round((c.total_revenue - p.prior_revenue) / nullif(p.prior_revenue, 0) * 100, 2)
    end as revenue_pace_pct,
    c.reservations as current_reservations,
    p.prior_reservations,
    c.room_nights as current_room_nights,
    p.prior_room_nights
from current_year c
left join prior_year p
    on c.hotel_id = p.hotel_id
   and c.business_date = p.business_date