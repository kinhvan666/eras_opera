# OPERA API financialPostings Investigation — 784 Missing CheckedOut Stays

**Date:** 2026-07-20
**Feature:** financials
**Source:** cashiering-extraction-gap_HANDOUT_20-07-26.md (Bước 2) + cashiering-backfill_REPORT_20-07-26.md
**Status:** NEW PLAN REQUIRED

## Problem

After re-running CashieringExtractor full backfill (cashiering-backfill_PLAN_20-07-26.md, executed 2026-07-20),
`fct_folio_line` still has **784 CheckedOut stays** (business_date <= 2026-07-18) with zero folio rows.
Raw layer also missing these — re-run only added +28 rows / +1 reservation_id, confirming the gap is NOT a
staging filter or pagination miss in our code, but an **OPERA API extraction-level miss**.

Gap by month (post re-run): 2026-01=169, 02=55, 03=69, 04=92, 05=116, 06=172, 07=124.

## Root Cause Hypothesis

OPERA `/financialPostings` does not return postings for a layer of CheckedOut transactions, OR requires a
different parameter / endpoint (transaction-level vs journal-level).

## Fix Options

1. Call OPERA API directly for 1-2 sample missing stays (e.g. reservation_id=13743487, 4 nights CheckedOut):
   `GET /csh/v1/hotels/79017/financialPostings?reservationId=...&startDate=...&endDate=...`
   (or date-window filter containing the stay arrival) → check if API returns postings.
2. If API returns nothing → try alternate params / endpoint (transactionType, journal vs transaction level).
3. If API returns data our extractor missed → fix `extractor/src/extractors/cashiering.py` fetch logic.

## Priority

Medium — KPI tiles (Revenue/ADR/RevPAR) are ACTUAL but under-count ~784 stays. Dashboard usable but
revenue slightly low. Not blocking, but accuracy gap.

## Related

- `process/features/financials/active/financials_17-07-26/cashiering-backfill_PLAN_20-07-26.md`
- `process/features/financials/active/financials_17-07-26/cashiering-extraction-gap_HANDOUT_20-07-26.md`
