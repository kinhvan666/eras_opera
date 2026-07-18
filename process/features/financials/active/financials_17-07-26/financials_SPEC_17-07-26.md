---
name: spec:financials-v1
description: "Requirements for extracting real posted revenue from OPERA Cashiering and replacing estimated KPIs in the dimensional model and dashboard"
date: 17-07-26
feature: financials
phase: SPEC
---

# Financials Feature — SPEC

**Date:** 2026-07-17
**Feature:** financials
**Status:** Draft — awaiting INNOVATE

---

## Summary

Today, the ErasOpera dashboard shows Revenue, ADR, and RevPAR figures that are **estimates** — calculated by dividing a reservation's total rate-plan amount across its stay nights (`fct_reservation_night.night_amount`). This misses actual F&B charges, service charges, tax, and room adjustments that OPERA posts to folios in real time.

This SPEC covers extracting **real posted revenue** from the Oracle OPERA Cloud Cashiering API (`/financialPostings`), loading it into the warehouse as a new folio-line layer, and wiring it to the dashboard so Revenue, ADR, and RevPAR reflect what guests actually paid — broken down by Room, F&B, Service Charge, and Tax.

---

## User Stories / Jobs To Be Done

**Revenue Manager**
- When I look at the ADR and RevPAR dashboard, I want the figures to be based on what OPERA actually posted — not what the rate plan said — so I can report accurate performance to ownership and make correct pricing decisions.

**General Manager**
- When I open the Revenue tab, I want to see total revenue split into Room / F&B / Service Charge / Tax categories, so I can see the hotel's revenue mix at a glance without running a separate OPERA report.

**Data Analyst**
- When I query the warehouse, I want posting-level data joined to reservations and dated to the revenue business date, so I can build segment, rate-plan, and room-type revenue reports.

**Finance Team**
- When voucher-rate guests check out, I want the warehouse to record the original rack charge and the voucher credit separately, so I can calculate true voucher value and discount exposure — not just see $0 revenue.

---

## What The User Wants (Behavioral Outcomes)

1. **Accurate top-line KPIs.** Revenue, ADR, and RevPAR on the dashboard are sourced from actual OPERA folio postings. The label "(estimated)" is removed. Values match what a hotel controller would see in an OPERA revenue report for the same period.

2. **Revenue breakdown by category.** The dashboard displays a category split for the selected date range: Room / F&B / Service Charge / Tax. Adjustment codes (9xxx) are excluded from all totals.

3. **Voucher stay handling.** Voucher-rate reservations (rate plan = VOUCHER) show both the gross room charge and the voucher credit offset in the warehouse. A `voucher_value` measure becomes available for future reports, though V1 does not require it to appear on the dashboard.

4. **Data currency.** Posted revenue data refreshes on the same cadence as the existing extractor (on-demand / scheduled batch). The extractor fetches postings in 7-day windows to stay within OPERA API limits and automatically pages through all results.

5. **Revenue is attributed to the business date.** Posting amounts are attributed to `revenueDate` (the business date), not `postingDate`, consistent with hotel accounting practice.

6. **Currency: VND throughout.** No conversion. All amounts stored and displayed in Vietnamese Dong.

---

## Flow / State Diagram

```
OPERA Cloud Cashiering API
  GET /csh/v1/hotels/{hotelId}/financialPostings
    filter: transactionType = Revenue
    params: startDate, endDate (7-day windows), limit, offset
    auth: OAuth client_credentials + x-app-key + x-hotelid
            |
            | one posting line per charge
            v
+---------------------------+
|  raw.cashiering_postings  |  (new raw table)
|  one row per posting line |
|  grain: transactionNo     |
+---------------------------+
            |
            v
+-----------------------------+
|  stg_cashiering_postings    |  (new dbt staging model)
|  - type: posted_amount,     |
|    revenue_date, hotel_id,  |
|    transaction_code,        |
|    reservation_id (FK)      |
|  - derive: revenue_category |
|    (Room/F&B/Tax/SvcCharge) |
|  - exclude: 9xxx adjustments|
+-----------------------------+
            |
            +----------------------------+
            |                            |
            v                            v
+----------------------+    +------------------------------+
|  fct_folio_line      |    |  dim_transaction_code        |
|  (new fact table)    |    |  (new or existing dimension) |
|  grain: posting line |    |  code → category mapping     |
|  (transactionNo)     |    +------------------------------+
+----------------------+
            |
            | aggregate by reservation + business_date
            v
+-------------------------------+
|  fct_reservation_night        |  (existing — add new columns)
|  + revenue_actual (total)     |
|  + revenue_room               |
|  + revenue_fnb                |
|  + revenue_tax                |
|  + revenue_svc                |
|  night_amount stays for       |
|  backward compatibility       |
+-------------------------------+
            |
            v
+-----------------------------+
|  Dashboard — Revenue Tab    |
|  Revenue KPI = revenue_room |
|    + revenue_fnb            |
|    + revenue_tax            |
|    + revenue_svc            |
|  ADR = Revenue / room nights|
|  RevPAR = Revenue / avail   |
|  Category bar chart         |
+-----------------------------+
```

**Happy path:** extractor fetches 7-day windows → inserts raw rows → dbt staging assigns category → folio-line fact is built → reservation-night fact gains actual revenue columns → dashboard reads from actual columns.

**Key branch — posting with no reservation match:** postings where `guestInfo.reservationId` is absent or does not match a known `reservation_id` are stored in `raw` and `stg` but excluded from `fct_reservation_night` joins. They are still visible in `fct_folio_line` for reconciliation.

**Key branch — VOUCHER stays:** positive room charge posting + negative voucher credit posting both land in `fct_folio_line`. Net = 0 for accounting. Gross room charge is preserved for voucher value reporting.

---

## Acceptance Criteria (Testable Outcomes)

**AC-1 — Raw postings table is populated**
After running the extractor for any 7-day date range, `raw.cashiering_postings` contains at least one row per Revenue-type posting returned by the API, with `transactionNo` as the unique identifier and `hotel_id`, `revenue_date`, `transaction_code`, `posted_amount` all non-null.
- `proven by:` pytest integration test — run extractor against mock API fixture built from live probe response (1,359 postings / 7-day window); assert row count and non-null fields
- `strategy:` Fully-Automated

**AC-2 — Category assignment is correct**
Each row in `stg_cashiering_postings` has `revenue_category` set to one of: `Room`, `FnB`, `Tax`, `ServiceCharge`. Transaction codes in the 9xxx range produce no rows in the staging model (excluded at source).
- `proven by:` dbt `accepted_values` test on `revenue_category`; dbt singular test asserting zero rows where `transaction_code LIKE '9%'`
- `strategy:` Fully-Automated

**AC-3 — Posting-to-reservation join integrity**
For postings where `guestInfo.reservationId.id` is present, the `reservation_id` foreign key in `stg_cashiering_postings` matches a known `reservation_id` in `stg_reservations` for at least 95% of rows (allows for reservations not yet loaded into the warehouse).
- `proven by:` dbt data test asserting unmatched-FK rate < 5% of Revenue postings with a non-null `guestInfo.reservationId`
- `strategy:` Fully-Automated

**AC-4 — Folio-line fact table grain**
`fct_folio_line` has one row per posting line (`transactionNo`). No duplicate `transactionNo` values exist.
- `proven by:` dbt `unique` + `not_null` tests on `transaction_no` in `fct_folio_line`
- `strategy:` Fully-Automated

**AC-5 — Reservation-night fact carries actual revenue**
`fct_reservation_night` gains columns `revenue_actual`, `revenue_room`, `revenue_fnb`, `revenue_tax`, `revenue_svc`. For a reservation with known postings, `revenue_actual` = sum of all non-9xxx Revenue postings attributed to that reservation on the matching `revenue_date`. The existing `night_amount` column is unchanged.
- `proven by:` dbt singular test comparing `revenue_actual` for a known reservation against manually confirmed OPERA folio total for that stay
- `strategy:` Hybrid

**AC-6 — Dashboard KPIs source from actual postings**
Revenue, ADR, and RevPAR on the dashboard use `revenue_actual` (or the derived `revenue_room + revenue_fnb + ...`), not `night_amount`. For a selected date range with known postings, the dashboard values differ from the previous estimated values and match an OPERA revenue report for the same period.
- `proven by:` Manual spot-check — run dashboard for a known week; compare Revenue/ADR/RevPAR against OPERA standard revenue report for same hotel and date range
- `strategy:` Hybrid

**AC-7 — Category breakdown visible on dashboard**
The dashboard Revenue tab shows a breakdown of actual revenue by category (Room / F&B / Service Charge / Tax) for the selected property and date range. Category totals sum to total revenue (within rounding).
- `proven by:` Manual review of the Revenue tab after data load; assert category totals + zero-category rows sum to the headline Revenue KPI
- `strategy:` Hybrid

**AC-8 — Voucher postings are stored with gross and credit**
For VOUCHER-rate reservations, both the positive room charge posting and the negative voucher credit posting appear in `fct_folio_line` with their original amounts. Net sum of these postings is zero or near-zero.
- `proven by:` dbt singular test — select reservations where `rate_plan_code = 'VOUCHER'`; assert at least one has both a positive and negative `transaction_code LIKE '1%'` posting
- `strategy:` Fully-Automated

**AC-9 — 7-day window chunking works without errors**
The extractor automatically splits any requested date range into non-overlapping 7-day windows and fetches each without receiving a 400 error from the API.
- `proven by:` pytest unit test with mocked HTTP — assert a 30-day request produces exactly 5 (or 5+) non-overlapping windows; assert each window call returns 200 in the mock; assert the 400-on-wide-range error (confirmed in live probe) is never triggered
- `strategy:` Fully-Automated

**AC-10 — Pagination handles multi-page results**
When a 7-day window returns `hasMore = true`, the extractor continues fetching subsequent pages until `hasMore = false`, collecting all posting rows.
- `proven by:` pytest unit test with mocked HTTP fixture returning two pages (hasMore=true then hasMore=false); assert all rows from both pages land in the raw table
- `strategy:` Fully-Automated

---

## Out Of Scope

- **AR (Accounts Receivable) API** — post-checkout invoice management and aged receivables. Not in-stay revenue. Deferred.
- **Payment postings** (`transactionType = Payment`) — cash, card, transfer postings. Not revenue. Deferred.
- **Wrapper postings** (`transactionType = Wrapper`) — OPERA grouping entries. Not revenue. Deferred.
- **9xxx Adjustment codes** — included in raw extract but excluded from all revenue totals and dashboard KPIs. No further analysis in V1.
- **MICROS POS `/transactionCodes` lookup** — POS codes (1000, 2100, 7100, etc.) are not registered in the OPERA transaction code master; category is derived by numeric prefix, not a code lookup join.
- **Historical backfill automation** — V1 covers incremental extraction from a configured start date. Bulk historical backfill tooling is a separate concern.
- **Multi-currency conversion** — all data is VND. No FX conversion layer in V1.
- **Revenue forecasting or budgeting** — this SPEC covers actual posted revenue only, not forward-looking models.
- **Operations feature integration** — RevPAR denominator (total available room-nights) currently uses `dim_property.room_count` from the existing hotel config extractor. Full accurate denominator from the operations feature is a separate phase.
- **Real-time extraction** — batch/on-demand only. No webhook or streaming ingestion.

---

## Constraints

- OPERA Cashiering API date range limit: **7 days per request**. Extractor must chunk any wider range automatically.
- Auth pattern: same OAuth client_credentials + `x-app-key` + `x-hotelid` headers as the existing extractor. No new credential type.
- All amounts in VND. No currency conversion needed.
- `revenueDate` is the attribution date (business date), not `postingDate`.
- Revenue category is determined by transaction code numeric prefix (`1xxx`, `2xxx/3xxx/6xxx`, `7xxx`, `8xxx`). Code 9xxx = excluded.
- Technology stack: Python (extractor), PostgreSQL (raw + warehouse), dbt (staging + dimensional). No new runtimes.
- Kimball discipline: new fact tables must declare grain explicitly; dimensions must be conformed where possible (`dim_transaction_code` should be reusable across features).
- Existing `fct_reservation_night` columns (`night_amount`, etc.) must not be removed — only new columns added — to avoid breaking existing dashboard queries.
- `transactionNo` is the unique identifier for a posting line (deduplication key).
- Join key from postings to reservations: `guestInfo.reservationId.id` (nested object in API response) = `reservation_id` in warehouse.
- **Initial backfill window: 2026-01-01 to present (year-to-date).** First extraction run fetches ~37 7-day windows. Subsequent incremental runs fetch only the latest window(s).

---

## Open Questions

None — all questions resolved.

> **Resolved 2026-07-17:** Initial backfill window = **2026-01-01 to present (year-to-date)**. Matches the date range of existing reservation data already in the warehouse. The extractor will chunk this into ~37 non-overlapping 7-day windows (~37 API calls) on first run.

---

## Background / Research Findings

**Confirmed via live API probe (2026-07-17):**

- Primary endpoint: `GET /csh/v1/hotels/{hotelId}/financialPostings`
- Params: `startDate`, `endDate`, `limit`, `offset` (pagination via `hasMore`)
- 7-day date range limit confirmed — 90-day call returns HTTP 400
- Auth: identical to existing extractor (OAuth + x-app-key + x-hotelid)
- Total postings available in one 7-day probe: 1,359 lines
- `transactionType` values: `Revenue`, `Payment`, `Wrapper` — filter to `Revenue` only
- Revenue attribution field: `revenueDate` (not `postingDate`)
- Reservation FK: `guestInfo.reservationId.id` (nested object `{type, idContext, id}`)
- Unique identifier: `transactionNo`
- Currency: VND (`currencyCode = VND`, `postedAmount.amount`)

**Transaction code categories (confirmed from live data):**
- `1xxx` → Room (1000 = daily room charge, 1050 = extra bed)
- `2xxx`, `3xxx`, `6xxx` → F&B (restaurant, minibar, misc F&B)
- `7xxx` → Tax
- `8xxx` → Service Charge
- `9xxx` → Adjustment (AMEX settlements, etc.) — excluded from revenue totals
- MICROS POS codes (1000, 2100, 7100, 8100...) are NOT in `/transactionCodes` lookup — they are POS-generated and pushed into OPERA automatically; all data is in `/financialPostings`

**Current "estimated" revenue (what we are replacing):**
- `fct_reservation_night.night_amount` = `total_amount / night_count` where `total_amount` comes from the Reservation API rate plan field
- Does NOT include F&B, service charge, tax, or actual charges
- Dashboard Revenue / ADR / RevPAR all currently show this estimate

**Voucher stay context (from backlog note `cashiering-voucher-discount_NOTE_16-07-26.md`):**
- ~77 VOUCHER-rate stays in the 90-day window; `rateAmount.amount = 0` in Reservation API
- Cashiering should carry: positive posting (rack rate) + negative posting (voucher credit) = net 0
- These are currently excluded from ADR (correct) but contribute $0 revenue (incorrect for management reporting)

**booking-core SPEC Phase 2 reference:**
- Phase 2 explicitly calls for the financials feature to replace estimated KPIs with actual folio-level transactions (ref: `booking-core_SPEC_13-07-26.md` §Development Roadmap Phase 2)

**Relationship structure:** one reservation → multiple folio windows → multiple posting lines (1:many:many). Join via `guestInfo.reservationId.id` = `reservation_id`.
