-- eras_dbt/models/dimensional/dim_property.sql
-- Property dimension - one row per distinct hotel_id observed in stg_reservations
-- Minimal for now; future phase should enrich from Enterprise Configuration API
select
    hotel_id,
    null::text as hotel_name  -- placeholder: no property master-data API extracted in Phase 1
from (
    select distinct hotel_id
    from {{ ref('stg_reservations') }}
    where hotel_id is not null
) p