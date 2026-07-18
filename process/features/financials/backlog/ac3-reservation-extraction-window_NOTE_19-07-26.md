---
name: backlog:financials-ac3-reservation-extraction-window
description: "Expand stg_reservations extraction to cover 2026 date range so AC-3 FK match rate test passes"
date: 19-07-26
metadata:
  node_type: memory
  type: backlog
  feature: financials
  priority: HIGH
---

# Backlog: AC-3 Reservation FK Match Rate — Extend Extraction Window

**Priority:** HIGH (blocks AC-3 SPEC criterion; affects Phase 4 aggregation accuracy)
**Source:** Phase 3 closeout (2026-07-19) — known-gap

## Problem

`test_ac3_reservation_fk_match_rate.sql` currently fails with 35.59% match rate (8,299 / 12,885 non-null reservation_id rows unmatched).

The 95% threshold is correct and the model is structurally correct — this is a data scope gap:
- Cashiering postings were extracted covering 2026 check-ins (reservation IDs ~16xxx range)
- `stg_reservations` currently covers reservations from an earlier extraction window (~11xxx range)

## Fix Options

1. **Re-extract reservations for 2026-01-01 onward** — run `ReservationExtractor` for the 2026 date range so `raw.booking_core_reservations` covers the same stay dates as the cashiering postings. Rebuild `stg_reservations`. After re-extraction, AC-3 should pass.

2. **Set AC-3 test severity to `warn` (interim)** — add `config(severity='warn')` to `test_ac3_reservation_fk_match_rate.sql` to prevent it from blocking `dbt build` until fix option 1 is complete.

## Recommendation

Do option 2 first (quick, unblocks Phase 4 dbt build in CI), then option 1 before Phase 5 (dashboard) to ensure revenue attribution is accurate for 2026 reservations.

## When to Resolve

Before or during Phase 4 research (re-extraction can be done as a pre-Phase-4 prerequisite).
A standalone quick-fix task for option 2 can be done immediately without a full phase plan.
