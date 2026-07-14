{% snapshot dim_guest_snapshot %}

{{
    config(
        target_schema='snapshots',
        strategy='check',
        unique_key='profile_id',
        check_cols=['guest_city', 'guest_postal_code', 'guest_state', 'guest_country_code'],
        updated_at='updated_at'
    )
}}

with guest_latest as (
    select
        profile_id,
        guest_first_name,
        guest_last_name,
        guest_city,
        guest_postal_code,
        guest_state,
        guest_country_code,
        max(updated_at) as updated_at
    from {{ ref('stg_reservations') }}
    where profile_id is not null
    group by
        profile_id,
        guest_first_name,
        guest_last_name,
        guest_city,
        guest_postal_code,
        guest_state,
        guest_country_code
)

select * from guest_latest

{% endsnapshot %}