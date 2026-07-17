-- eras_dbt/models/staging/stg_reservations.sql
-- Dedup raw rows: lấy extracted_at mới nhất cho mỗi reservation_id.
-- Loại bỏ pseudo rooms (phòng ảo hệ thống như NORA/PM) — không phải lưu trú thật.
with source as (
    select * from {{ source('raw', 'booking_core_reservations') }}
),

-- Lấy row mới nhất per reservation_id để loại bỏ duplicate từ lần extract trước
deduped as (
    select distinct on (raw_data->'reservationIdList'->0->>'id')
        *
    from source
    where raw_data->'reservationIdList'->0->>'id' is not null
    order by
        raw_data->'reservationIdList'->0->>'id',
        extracted_at desc
),

staged as (
    select
        raw_data->'reservationIdList'->0->>'id'                          as reservation_id,
        raw_data->'externalReferences'->0->>'id'                         as confirmation_no,
        (raw_data->'roomStay'->'originalTimeSpan'->>'startDate')::date   as arrival_date,
        (raw_data->'roomStay'->'originalTimeSpan'->>'endDate')::date     as departure_date,
        (raw_data->>'createDateTime')::timestamp                         as created_at,
        (raw_data->>'lastModifyDateTime')::timestamp                     as updated_at,
        raw_data->'reservationGuest'->>'id'                              as profile_id,
        raw_data->'reservationGuest'->>'givenName'                       as guest_first_name,
        raw_data->'reservationGuest'->>'surname'                         as guest_last_name,
        raw_data->'roomStay'->>'roomType'                                as room_type,
        (raw_data->'roomStay'->'rateAmount'->>'amount')::numeric         as total_amount,
        raw_data->>'hotelId'                                             as hotel_id,
        raw_data->'reservationGuest'->'address'->>'cityName'             as guest_city,
        raw_data->'reservationGuest'->'address'->>'postalCode'           as guest_postal_code,
        raw_data->'reservationGuest'->'address'->>'state'                as guest_state,
        raw_data->'reservationGuest'->'address'->'country'->>'code'      as guest_country_code,
        raw_data->'roomStay'->>'ratePlanCode'                            as rate_plan_code,
        raw_data->'roomStay'->>'marketCode'                              as market_code,
        -- sourceOfBusiness is unpopulated for this property; sourceCode carries the booking channel
        coalesce(
            nullif(raw_data->'roomStay'->>'sourceOfBusiness', ''),
            raw_data->'roomStay'->>'sourceCode'
        )                                                                as source_of_business,
        raw_data->>'reservationStatus'                                   as reservation_status,
        (raw_data->'roomStay'->>'pseudoRoom')::boolean                   as is_pseudo_room,
        (raw_data->'roomStay'->>'rateSuppressed')::boolean               as is_rate_suppressed
    from deduped
    -- Loại bỏ pseudo rooms: phòng ảo (NORA, PM, PF...) không phải lưu trú thật,
    -- không có revenue, làm sai occupancy và ADR nếu giữ lại.
    where (raw_data->'roomStay'->>'pseudoRoom')::boolean is not true
)

select * from staged
