---
title: Cashiering — Voucher code & discount amount extraction
date: 2026-07-16
type: backlog-note
feature: financials
---

## Context

VOUCHER rate plan reservations (`ratePlanCode = 'VOUCHER'`) check out with `rateAmount.amount = 0`.
The Reservation API does not carry voucher code, original rack rate, or discount amount.
As of 2026-07-16 there are ~77 such CheckedOut stays in the 90-day window.

These are currently excluded from ADR calculation (correct) but contribute $0 to revenue,
meaning the actual value of the stay (what the voucher was worth) is invisible in the warehouse.

## What's needed

- **Cashiering extractor** — `GET /csh/v1/hotels/{hotelId}/financialPostings`
  filtered by reservation ID, date range. Each voucher stay should have:
  - Posting: original room charge (positive amount = rack rate)
  - Posting: voucher credit (negative amount = discount)
  - Net = 0
- **`raw.cashiering_postings`** table — store line-item folio transactions
- **`stg_cashiering_postings.sql`** — extract transaction_code, amount, reservation_id
- **`dim_transaction_code`** — map transaction codes to categories (room, F&B, voucher, etc.)
- **`fct_folio_line.sql`** — fact table at folio-line grain

## What this unlocks

- `voucher_value` per reservation = absolute value of voucher credit posting
- True RevPAR: revenue including voucher value (management view) vs cash RevPAR (accounting view)
- Discount analysis: how much revenue is given away via vouchers per period

## Dependencies

- Cashiering API scope is under `financials` feature
- Reservation IDs already available in `raw.booking_core_reservations`
- No schema changes to existing tables needed
