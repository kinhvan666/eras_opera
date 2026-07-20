---
phase: cashiering-backfill
date: 2026-07-20
status: COMPLETE_WITH_GAPS
feature: financials
plan: process/features/financials/active/financials_17-07-26/cashiering-backfill_PLAN_20-07-26.md
---

# Cashiering Backfill Re-run — Execute Report

## What Was Done

Thực thi đúng kế hoạch `cashiering-backfill_PLAN_20-07-26.md` (operational re-run, 0 file thay đổi):

1. **Baseline (Steps 1-3):** raw=18,791 rows / 18,791 distinct txn_no; distinct reservation_id (correct path `raw_data->'guestInfo'->'reservationId'->>'id'`)=1,202; gap_stays (CheckedOut, business_date<=2026-07-18, thiếu fct_folio_line)=784.
2. **Step 4 — Re-run CashieringExtractor:** chạy `poetry run python -m src` với `DATABASE_URL` override sang `localhost:5434` (extractor ngoài container không resolve được host `postgres`). Hoàn thành không exception. `Fetched 18816 cashiering postings`, upsert xong.
3. **Step 5 — Verify raw tăng:** raw 18,791 → **18,819** (+28); distinct txn_no 18,819 (no duplicate — PK upsert đúng); distinct reservation_id 1,202 → **1,203** (+1).
4. **Step 6 — dbt build:** toàn bộ staging + dimensional models rebuild thành công. `fct_folio_line`=13,297 rows (tăng từ 12,956 baseline), `fct_reservation_night`=2,993 rows.
5. **Step 7 — Gap sau rebuild:** **784** (không giảm).
6. **Step 8 — Gap report theo tháng:** 2026-01=169, 02=55, 03=69, 04=92, 05=116, 06=172, 07=124 (=784).

## What Was Skipped or Deferred

- **Handout Bước 2 (OPERA API investigation):** gap vẫn = 784 sau re-run xác nhận OPERA `/financialPostings` không trả postings cho 784 stays → cần plan mới gọi API trực tiếp điều tra.
- **Handout Bước 3 (recover 267 null reservationId rows):** ngoài scope plan này.
- **Handout Bước 4 (dbt data-quality test mới):** ngoài scope plan này.

## Test Gate Outcomes

| Gate | Kết quả |
|---|---|
| TC1 extractor no exception | ✅ PASS — "Extraction process finished." |
| TC2 raw rows after >= baseline | ✅ PASS — 18,819 >= 18,791, no duplicate txn_no |
| TC3 dbt build exits 0 (model errors) | ⚠️ MODEL BUILD OK; 2 data-test errors pre-existing/ngoài scope (see Deviations) |
| TC4 gap decreases | ❌ NO CHANGE — 784 → 784 (dự báo trước, xác nhận extraction-level miss) |
| TC5 distinct reservation_id increases/holds | ✅ PASS — 1,202 → 1,203 |

## Plan Deviations

1. **DATABASE_URL override:** plan ghi `cd extractor && poetry run python -m src` nhưng không note host. Chạy ngoài Docker network → host `postgres` không resolve. Đã override `$env:DATABASE_URL="postgresql://user:password@localhost:5434/erg_opera_data"`. Within-blast-radius (không đổi code), chỉ env runtime.
2. **dbt test errors (2):** `not_null_my_first_dbt_model_id` (example model) + `not_null_fct_reservation_night_rate_plan_code` (118 rows thiếu rate_plan_code). Cả 2 là pre-existing data-test failures, KHÔNG phải model build errors, nằm ngoài blast radius plan này (plan chỉ re-run extract + rebuild). Model `fct_folio_line` / `fct_reservation_night` build thành công.

## Test Infra Gaps Found

- Không có automated test phát hiện tái diễn gap (handout Bước 4 đề xuất nhưng chưa làm).
- 2 dbt tests fail pre-existing cần dọn (example model + rate_plan_code null) — nên tách thành backlog/cleanup plan riêng.

## Closeout Packet

- **Selected plan:** process/features/financials/active/financials_17-07-26/cashiering-backfill_PLAN_20-07-26.md
- **Finished:** re-run extract + dbt rebuild, xác nhận raw upsert idempotent, gap measurement chính xác.
- **Verified:** raw row count tăng, no dup, dbt models rebuild, gap = 784 (unchanged) với phân bố tháng.
- **Unverified:** nguyên nhân OPERA API miss (cần Bước 2).
- **Cleanup:** 2 dbt test failures pre-existing cần xử lý riêng.
- **Next valid state:** tạo plan mới cho handout Bước 2 — OPERA API investigation (gọi `/financialPostings?reservationId=...` cho mẫu missing stays vd 13743487).

## Forward Preview

- **Test Infra Found:** extractor cần DATABASE_URL override khi chạy local (host postgres→localhost:5434).
- **Blast Radius Changes:** none (0 files modified).
- **Commands to Stay Green:** `docker exec erasopera-postgres-1 psql -U user -d erg_opera_data -c "<gap query>"` để re-measure.
- **Dependency Changes:** none.

**Follow-up plan stub:** process/features/financials/active/financials_17-07-26/ (mới) — OPERA API financialPostings investigation cho 784 missing CheckedOut stays.
