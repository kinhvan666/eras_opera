with source as (
    select * from {{ source('opera_cloud', 'reservations') }}
)

select
    id as reservation_id,
    confirmation_number,
    guest_name,
    check_in_date,
    check_out_date,
    status
from source
