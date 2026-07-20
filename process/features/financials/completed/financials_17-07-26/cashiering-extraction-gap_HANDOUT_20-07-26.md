# Cashiering Extraction Gap — Handout (784 CheckedOut stays vắng mặt trong folio)

**Date:** 2026-07-20
**Author:** orchestrator (session verify độ chính xác KPI tiles)
**Feature folder:** process/features/financials/active/financials_17-07-26/
**Prerequisite đã có:** dashboard KPI tiles đã chuyển sang ACTUAL (Plan A–C đã EXECUTE, xem `dashboard-kpi-actual_HANDOUT_19-07-26.md`). Handout này là **finding mới** phát hiện SAU khi tiles đã actual — actual vẫn under-count.

---

## TL;DR (cho session tiếp theo)

Tile Revenue / ADR / RevPAR trên dashboard hiện là **ACTUAL** (từ `fct_folio_line`) — đã đúng hướng.
NHƯNG pipeline extract vẫn **bỏ sót ~784 stays đã CheckedOut** → số actual đang **thấp hơn thực tế**.
Nguyên nhân: **CashieringExtractor bỏ sót**, không phải staging filter, không phải booking tương lai, không phải sai JSON path.
Cần re-run extract + điều tra OPERA API response cho các missing reservations.

---

## Bằng chứng (query thực tế, Postgres container `erasopera-postgres-1:5434`, db `erg_opera_data`)

### 1. Coverage fact vs folio (tại ngày 2026-07-20)
```
fct_reservation_night  : 2,986 rows, 1 hotel (79017), business_date tới 2026-12-26 (có tương lai)
fct_folio_line          : 12,956 rows, MAX(revenue_date)=2026-07-18
dim_property.room_count : 49 (hotel 79017, manual V1)
```

### 2. Overlap reservation_id — past vs future
```
fact past reservations (business_date <= 2026-07-18, non-Cancelled/NoShow) : 1,450
  ├─ có folio Room posting                                          :   530  ✅
  └─ THIẾU folio Room posting                                       :   920  ❌
        ├─ reservation_status = 'CheckedOut' (bắt buộc có posting)  :   830
        │     ├─ có folio posting category khác (FnB/...)           :    46
        │     └─ HOÀN TOÀN KHÔNG CÓ raw postings nào                :   784  ← GAP
        └─ Reserved / Requested / InHouse (có thể chưa checkout)    :    90  (chấp nhận)
fact future reservations (sau 2026-07-18)                            :   159  (chưa tới, bỏ qua)
```

### 3. Xác nhận 784 stays vắng mặt ở TẤNG raw layer (không chỉ staging)
Path đúng: `raw_data->'guestInfo'->'reservationId'->>'id'`
```
raw.cashiering_postings                : 18,335 rows
  ├─ có guestInfo                       : 18,335 (100%)
  ├─ có reservationId hợp lệ            : 18,068
  └─ có guestInfo NHƯNG thiếu id        :    267  (mất join, không recover qua path này)
raw distinct reservation_id            :  1,184
fct_folio_line distinct reservation_id :  1,121
fct raw-orphans (có raw, không có fct) :     63  (do staging filter 9xxx / transactionType)
```
Cross-check: missing stay `reservation_id = 13743487` (4 nights, CheckedOut) →
`raw.cashiering_postings` query đúng path = **0 rows**. → 784 stays thực sự không được extract.

### 4. Phân bố gap rải đều mọi tháng (loại trừ "1 window lỗi")
```
arrival_month | missing CheckedOut stays
2026-01       | 169
2026-02       |  55
2026-03       |  69
2026-04       |  92
2026-05       | 104
2026-06       | 171
2026-07       | 124
```
→ Gap lan tỏa toàn timeline, không phải 1 batch lỗi cục bộ → mang màu sắc **extraction-level miss**
  (khả năng cao: OPERA API không trả postings cho một lớp transactions, hoặc extract chỉ chạy 1 lần
  và bỏ sót 1 phần do pagination/timeout không retry).

### 5. Thành phần Revenue actual (để hiểu tile Revenue hiện tại)
```
Category      | Amount (Jan–Jul, trừ Tax)
FnB           | ₫6.91B  (54%)
Room          | ₫5.53B  (43%)
ServiceCharge | ₫0.38B
Other         | ₫0.04B
TỔNG actual   | ₫12.86B
```
- Tile "Revenue" = TỔNG (gồm FnB) → dễ bị hiểu lầm là Room revenue. ADR/RevPAR thì đúng chỉ lấy Room.
- Gap ₫8.24B (actual) vs ₫3.41B (estimated night_amount) = **toàn bộ FnB + phụ phí** (fact booking chỉ đo Room).
  → breakdown bars (tab Revenue) lấy từ `fct_reservation_night.night_amount` = chỉ Room → KHÔNG reconcile được với tile.

---

## Tác động lên độ chính xác (cập nhật vs handout 19-07)

| Tile (main dashboard) | Nguồn | Đánh giá 20-07 |
|---|---|---|
| Revenue | `fct_folio_line` (trừ Tax) | ✅ ACTUAL nhưng **under-count ~784 stays** |
| ADR | Room folio ÷ room nights (fact) | ⚠️ ACTUAL, **pha loãng** (tử số thiếu 784 stays) |
| RevPAR | Room folio ÷ (room_count×days) | ⚠️ ACTUAL, **pha loãng** + mẫu số room_count manual |
| Occupancy | room_nights ÷ room_count | ⚠️ ESTIMATED, mẫu số room_count manual (49 rooms, 1 hotel) |
| Resv / Room Nights / Lead / Canc | `kpi_daily_snapshot` | ⚠️ ESTIMATED (booking-based, gồm tương lai) |
| Revenue breakdown bars | `fct_reservation_night.night_amount` | ❌ chỉ Room estimate, không so sánh được |
| **Executive dashboard** (all tiles) | `kpi_daily_snapshot` (night_amount) | ❌ ESTIMATED, **không khớp** main dashboard |

Note: `dashboard-kpi-actual-tiles_NOTE_19-07-26.md` (backlog) ghi "ADR/RevPAR/Revenue cần dùng actual"
→ **ĐÃ XONG** (Plan A–C). Finding này là lớp sâu hơn: actual vẫn thiếu do extract gap.

---

## Hướng sửa đề xuất (cần RESEARCH → PLAN → VALIDATE → EXECUTE)

### Bước 1 — Re-run CashieringExtractor full backfill
- `BACKFILL_START_DATE = 2026-01-01` (`extractor/src/extractors/cashiering.py:13`).
- Raw là append-only → re-run sẽ thêm rows, KHÔNG ghi đè. Cần xác nhận raw row count tăng
  (18,335 → cao hơn) và distinct reservation_id tăng (1,184 → gần 1,450+).
- **Cảnh báo:** re-run có thể tạo duplicate postings nếu OPERA trả lại rows cũ → cần dedupe check
  (PK `transaction_no`?). Verify trước khi chạm pipeline.

### Bước 2 — Nếu re-run vẫn thiếu → điều tra OPERA API
- Lấy mẫu 1–2 missing CheckedOut reservations (vd 13743487), gọi trực tiếp
  `GET /csh/v1/hotels/79017/financialPostings?reservationId=...&startDate=...&endDate=...`
  (hoặc filter theo date window chứa arrival của stay) → xem API có trả postings không.
- Khả năng: (a) cần param khác, (b) postings nằm ở endpoint khác (vd transaction-level vs journal-level),
  (c) lớp postings đó có `transactionType != 'Revenue'` nên staging loại — NHƯNG raw vẫn phải có.
  Vì raw đã thiếu → (c) không giải thích được → tập trung vào (a)/(b).

### Bước 3 — Recover 267 rows thiếu reservationId
- 267 raw rows có `guestInfo` nhưng `reservationId.id` null. Thử recover qua `reference` field
  (`stg_cashiering_postings.sql:27`) hoặc `cashierId`. Nếu không recover được → chấp nhận mất join
  (những rows này không ảnh hưởng room-night count nhưng ảnh hưởng Revenue total nhẹ).

### Bước 4 — Data-quality test (mới)
- Thêm singular dbt test / Python assert: mọi `CheckedOut` stay trong `fct_reservation_night`
  (past) MUST có ≥1 `fct_folio_line` row với `revenue_category='Room'`. Fail hiện tại (920 violations).
- Giúp phát hiện tái diễn sau mỗi extract run.

---

## Files cần đọc khi bắt đầu session sửa

- `extractor/src/extractors/cashiering.py` — logic fetch (chunk 30d, pagination hasMore + short-page stop)
- `eras_dbt/models/staging/stg_cashiering_postings.sql` — filter `transactionType='Revenue'`, loại `9xxx`, path `guestInfo.reservationId.id`
- `eras_dbt/models/dimensional/fct_folio_line.sql` — fact grain
- `extractor/src/client.py` — `fetch_one`, pagination, retry/timeout behavior (QUAN TRỌNG để chẩn đoán miss)
- `dashboard/data/repository.py` — fetch_revenue_actual_summary, fetch_adr_revpar_actual_summary (tile sources hiện tại)
- Handout 19-07: `dashboard-kpi-actual_HANDOUT_19-07-26.md` (context Plan A–E đã done)

## DB connection
- Container: `erasopera-postgres-1`, published port `5434`, db `erg_opera_data`, role `user`.
- Dashboard tự patch host (`dashboard/config/settings.py`): `@postgres:5432` → `@localhost:5434`.
- Chạy query: `docker exec erasopera-postgres-1 psql -U user -d erg_opera_data -c "..."`

## Câu hỏi mở (cho session sửa)
1. OPERA `/financialPostings` có trả đủ postings cho mọi CheckedOut stay không, hay có lớp bị thiếu?
2. Re-run extract có duplicate risk không (dedupe bằng transaction_no)?
3. 267 rows thiếu reservationId có recover được qua `reference` không?
