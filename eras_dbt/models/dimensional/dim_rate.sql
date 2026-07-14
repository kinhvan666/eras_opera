-- eras_dbt/models/dimensional/dim_rate.sql
-- Rate dimension - one row per unique (rate_plan_code, market_code, source_of_business) combination
-- Using md5-based surrogate key since dbt_utils.generate_surrogate_key is not available (no packages.yml)
with rate_combinations as (
    select distinct
        rate_plan_code,
        market_code,
        source_of_business
    from {{ ref('stg_reservations') }}
    where rate_plan_code is not null
)
select
    md5(concat_ws('|', rate_plan_code, market_code, source_of_business)) as rate_sk,
    rate_plan_code,
    market_code,
    source_of_business
from rate_combinations