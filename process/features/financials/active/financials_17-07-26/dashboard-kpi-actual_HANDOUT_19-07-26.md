# Dashboard KPI Actual — Handout Session Mới

**Date:** 2026-07-19
**Prerequisite hoàn thành:** Phase 5 (fct_folio_line → Revenue tab section) — DONE + EVL PASS + visual verified
**Feature folder:** process/features/financials/active/financials_17-07-26/

---

## Context đã verify trong session này

- `analytics.fct_folio_line` có đủ data, verified chính xác
- Date range 90 ngày (2026-04-20 → 2026-07-19): tổng ₫8,375,541,915
- **Định nghĩa Revenue đã thống nhất:** Room + FnB + ServiceCharge + Other — KHÔNG bao gồm Tax (VAT nộp nhà nước)
- ServiceCharge = phí dịch vụ → IS revenue (không phải tip)
- FnB ₫4.5B verified hợp lệ — phần lớn từ MICE/event (ví dụ META EVENT TRAVEL, 564 covers/₫282M)
- Revenue tile EST hiện tại (₫3.41B) understate ~2.4x so với actual

### Breakdown 90 ngày gần nhất từ DB:
| Category | Amount | Tính Revenue? |
|---|---|---|
| FnB | ₫4,498,320,159 | Có |
| Room | ₫3,456,538,207 | Có |
| ServiceCharge | ₫241,276,639 | Có |
| Tax | ₫139,753,346 | **Không** |
| Other | ₫39,653,564 | Có |
| **Revenue thực** | **₫8,235,788,569** | |
| **Gross (incl Tax)** | **₫8,375,541,915** | |

---

## Kế hoạch cập nhật KPI tiles — theo thứ tự ưu tiên

### Plan A — Revenue tile (ưu tiên cao nhất)

**Scope:** Thay `night_amount`-based bằng query từ `fct_folio_line`
**Impact:** ₫3.41B EST → ₫8.24B ACT — thay đổi lớn nhất, ý nghĩa nhất với CEO
**Blast radius:** 2 files
- `dashboard/data/repository.py` — thêm `REVENUE_ACTUAL_KPI_SQL` (GROUP BY ngày, aggregate cho KPI tile)
- `dashboard/ui/components.py` (hoặc file chứa KPI tiles) — thay data source, bỏ badge EST

**SQL cần viết:**
```sql
SELECT SUM(posted_amount) AS revenue
FROM analytics.fct_folio_line
WHERE revenue_date BETWEEN %(start_date)s AND %(end_date)s
  AND (%(hotel_id)s::text IS NULL OR hotel_id = %(hotel_id)s)
  AND revenue_category != 'Tax'
```

**Cần research trước EXECUTE:**
- Tìm file và function đang render Revenue KPI tile hiện tại
- Xác nhận badge "EST" được render như thế nào để biết cách bỏ/đổi thành "ACT"
- Xác nhận delta % (so sánh kỳ này vs kỳ trước) có cần query thêm không

---

### Plan B — ADR tile (ưu tiên trung bình)

**Scope:** Thay estimated ADR bằng actual Room revenue / room nights
**Impact:** ₫2.9M EST → ~₫2.56M ACT (Room actual ₫3.46B / 1,350 nights)
**Note:** ADR = Room Revenue ONLY (không tính FnB/SC/Other) — đây là chuẩn hospitality
**Blast radius:** 1-2 files (repository.py + KPI tile component)

**SQL:**
```sql
SELECT SUM(posted_amount) AS room_revenue
FROM analytics.fct_folio_line
WHERE revenue_date BETWEEN %(start_date)s AND %(end_date)s
  AND revenue_category = 'Room'
  AND (%(hotel_id)s::text IS NULL OR hotel_id = %(hotel_id)s)
```
Chia cho room nights từ `fct_reservation_night` (giữ nguyên denominator hiện tại).

**Cần research:** Denominator room nights hiện đang lấy từ đâu (fct_reservation_night hay dim_date join?)

---

### Plan C — RevPAR tile (ưu tiên trung bình, làm cùng Plan B)

**Scope:** Thay estimated RevPAR bằng actual Room revenue / available rooms
**Impact:** ₫781K EST → actual (cùng Room revenue như ADR, denominator là available rooms)
**Note:** RevPAR = Room Revenue ONLY / Available Rooms — chuẩn hospitality
**Blast radius:** Cùng file với Plan B, làm chung 1 plan

**Cần research:** Available rooms per day hiện lấy từ đâu (dim_property.room_count?)

---

### Plan D — TRevPAR (metric mới, ưu tiên thấp hơn)

**Scope:** Thêm tile mới — Total Revenue Per Available Room
**Định nghĩa:** SUM(posted_amount excl Tax) / available rooms per day
**Tại sao quan trọng:** CEO hospitality dùng TRevPAR để so sánh với industry benchmark
**Giá trị ước tính:** ₫8,235,788,569 / (available rooms × 90 ngày)

**Cần research trước:**
- Số available rooms của hotel 79017 là bao nhiêu? (từ dim_property hoặc raw.enterprise_hotel_config)
- Kiểm tra xem RevPAR hiện tại dùng denominator như thế nào để follow pattern

---

### Plan E — TRevPOR (metric mới, ưu tiên thấp hơn)

**Scope:** Thêm tile mới — Total Revenue Per Occupied Room
**Định nghĩa:** SUM(posted_amount excl Tax) / occupied room nights
**Giá trị ước tính:** ₫8,235,788,569 / 1,350 = ~₫6.1M per occupied room
**Tại sao quan trọng:** Cho thấy mỗi phòng có khách generate bao nhiêu tổng doanh thu (room + FnB + event)

---

## Thứ tự đề xuất cho session mới

```
Plan A (Revenue tile) → RESEARCH → PLAN → VALIDATE → EXECUTE
Plan B+C (ADR + RevPAR cùng lúc) → RESEARCH → PLAN → VALIDATE → EXECUTE
Plan D+E (TRevPAR + TRevPOR cùng lúc, sau khi biết available rooms) → RESEARCH → PLAN → VALIDATE → EXECUTE
```

**Lưu ý cho session mới:**
- Chạy `find process/context/ -type f` và `find process/features/financials/ -type f` trước khi làm
- Read `process/context/all-context.md` và `process/context/database/all-database.md`
- fct_folio_line columns: `fact_sk, transaction_no, hotel_id, revenue_date, reservation_id, posted_amount, revenue_category, cashier_id, reference`
- DB connection: localhost:5434, database erg_opera_data (dashboard/config/settings.py tự patch hostname)
- Negative postings (516 rows, -₫3.27B toàn bộ data) là OPERA corrections — tính NET trong SUM là đúng

---

## Files quan trọng để đọc khi bắt đầu session mới

- `dashboard/data/repository.py` — xem pattern fetch functions hiện tại
- `dashboard/ui/components.py` hoặc file render KPI tiles — xác định chỗ thay badge EST
- `eras_dbt/models/dimensional/fct_folio_line.sql` — confirm columns
- `process/features/financials/active/financials_17-07-26/financials-postings-umbrella_PLAN_17-07-26.md`
