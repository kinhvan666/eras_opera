-- Singular test (AC-3): asserts that >=95% of non-null reservation_id rows in
-- stg_cashiering_postings match a row in stg_reservations.
-- Fails (returns rows) if >5% of non-null reservation_id values have no match.
-- Uses ref() for both sources per project pattern (E6 in validate-contract).

select
    count(*) as unmatched_count
from (
    select p.reservation_id
    from {{ ref('stg_cashiering_postings') }} p
    where p.reservation_id is not null
      and not exists (
          select 1
          from {{ ref('stg_reservations') }} r
          where r.reservation_id = p.reservation_id
      )
) unmatched
having
    count(*) * 1.0 / nullif(
        (select count(*) from {{ ref('stg_cashiering_postings') }} where reservation_id is not null),
        0
    ) > 0.05
