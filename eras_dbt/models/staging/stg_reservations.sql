-- eras_dbt/models/staging/stg_reservations.sql
with source as (
    select * from {{ source('raw', 'booking_core_reservations') }}
),

staged as (
    select
        raw_data->'reservationIdList'->0->>'id' as reservation_id,
        raw_data->'externalReferences'->0->>'id' as confirmation_no,
        (raw_data->'roomStay'->'originalTimeSpan'->>'startDate')::date as arrival_date,
        (raw_data->'roomStay'->'originalTimeSpan'->>'endDate')::date as departure_date,
        (raw_data->>'createDateTime')::timestamp as created_at,
        (raw_data->>'lastModifyDateTime')::timestamp as updated_at,
        raw_data->'reservationGuest'->>'id' as profile_id,
        raw_data->'reservationGuest'->>'givenName' as guest_first_name,
        raw_data->'reservationGuest'->>'surname' as guest_last_name,
        raw_data->'roomStay'->>'roomType' as room_type,
        raw_data->'roomStay'->'rateAmount'->>'amount' as total_amount,
        raw_data->>'hotelId' as hotel_id,
        raw_data->'reservationGuest'->'address'->>'cityName' as guest_city,
        raw_data->'reservationGuest'->'address'->>'postalCode' as guest_postal_code,
        raw_data->'reservationGuest'->'address'->>'state' as guest_state,
        raw_data->'reservationGuest'->'address'->'country'->>'code' as guest_country_code,
        raw_data->'roomStay'->>'ratePlanCode' as rate_plan_code,
        raw_data->'roomStay'->>'marketCode' as market_code,
        raw_data->'roomStay'->>'sourceOfBusiness' as source_of_business
    from source
)

select * from staged
