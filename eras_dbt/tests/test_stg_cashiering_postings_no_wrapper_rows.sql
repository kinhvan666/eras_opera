-- Singular test (AC-2): asserts zero Wrapper/folio-header rows survive into the staging model.
-- Any row with transaction_code LIKE '9%' must be excluded by the WHERE clause in
-- stg_cashiering_postings.sql. Passes when this query returns zero rows.
select
    transaction_no,
    transaction_code
from {{ ref('stg_cashiering_postings') }}
where transaction_code like '9%'
