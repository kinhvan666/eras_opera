---
name: backlog:dashboard-kpi-actual-tiles
description: "Follow-up: update Revenue/ADR/RevPAR KPI tiles to use actual fct_folio_line data instead of estimated night_amount"
date: 19-07-26
metadata:
  node_type: memory
  type: backlog
  feature: financials
---

# Backlog: Dashboard KPI Tile Actual Revenue Update

**Added:** 2026-07-19 (Phase 5 verify session — KPI understatement discovered)
**Priority:** HIGH — Revenue KPI tile understates by ~2.4x (₫3.41B EST vs ₫8.24B ACT)
**Prerequisite:** Phase 5 VERIFIED (fct_folio_line → Revenue tab section) — DONE

---

## Problem

Revenue, ADR, and RevPAR KPI tiles currently use estimated `night_amount` from `fct_reservation_night`.
True actual revenue from `fct_folio_line` is ~2.4x larger. CEO-visible metric is wrong.

Revenue definition confirmed in Phase 5 verify: Room + FnB + ServiceCharge + Other — EXCLUDE Tax (VAT).

| Category | 90-day actual |
|---|---|
| FnB | ₫4,498,320,159 |
| Room | ₫3,456,538,207 |
| ServiceCharge | ₫241,276,639 |
| Other | ₫39,653,564 |
| **Revenue actual (excl Tax)** | **₫8,235,788,569** |
| Tax | ₫139,753,346 |
| **Gross incl Tax** | **₫8,375,541,915** |

---

## Planned Sub-Plans (priority order)

- **Plan A — Revenue tile:** Replace night_amount sum with fct_folio_line SUM(posted_amount excl Tax). Blast radius: repository.py + KPI component. Remove "EST" badge.
- **Plan B+C — ADR + RevPAR tiles (together):** ADR = Room revenue / room nights; RevPAR = Room revenue / available rooms. Blast radius: repository.py + KPI component. Room revenue ONLY (hospitality standard).
- **Plan D+E — TRevPAR + TRevPOR (new metrics):** TRevPAR = total actual revenue / available rooms; TRevPOR = total actual revenue / occupied rooms. Need available rooms count from dim_property.

Full detail (SQL, research questions, ordering): `process/features/financials/active/financials_17-07-26/dashboard-kpi-actual_HANDOUT_19-07-26.md`

---

## Entry Context for New Session

- fct_folio_line columns: `fact_sk, transaction_no, hotel_id, revenue_date, reservation_id, posted_amount, revenue_category, cashier_id, reference`
- 12,956 total rows (post-Phase 5 backfill)
- Negative postings (516 rows, -₫3.27B total) = OPERA correction postings — NET is correct behavior
- DB: localhost:5434, `erg_opera_data` db; dashboard settings.py patches hostname for container vs local
