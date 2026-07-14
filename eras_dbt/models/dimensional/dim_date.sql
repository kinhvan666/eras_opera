-- eras_dbt/models/dimensional/dim_date.sql
-- Calendar dimension generated via generate_series over the observed date range in stg_reservations
with date_bounds as (
    select
        min(arrival_date) as min_date,
        max(departure_date) as max_date
    from {{ ref('stg_reservations') }}
),
date_series as (
    select
        generate_series(
            (select min_date from date_bounds) - interval '1 year',
            (select max_date from date_bounds) + interval '1 year',
            interval '1 day'
        )::date as date_day
)
select
    date_day,
    extract(year from date_day)::int as year,
    extract(quarter from date_day)::int as quarter,
    extract(month from date_day)::int as month,
    to_char(date_day, 'Month') as month_name,
    extract(dow from date_day)::int as day_of_week,  -- 0=Sunday, 6=Saturday
    to_char(date_day, 'Day') as day_name,
    (extract(dow from date_day) in (0, 6)) as is_weekend
from date_series