---
name: plan:dbt-revenue-estimate-fix
description: "Fix estimated-revenue understatement in dbt: rateAmount is per-night (stop dividing by night_count) and use actual stay dates instead of originalTimeSpan."
date: 22-07-26
feature: dbt-revenue-estimate-fix
phase: "complete"
status: "completed"
---

# Plan: Sửa doanh thu ước tính trong dbt (F1 + F2)

**Complexity:** SIMPLE

## 1. Overview

Hai lỗi logic nghiệp vụ trong pipeline dbt làm SAI số liệu ước tính, phát hiện qua audit
đối chiếu spec OHIP (`docs/OPERA Cloud Reservation API (26.2.0.0).json`) và doanh thu folio
thực tế (22-07-26):

- **F1 (nghiêm trọng):** `roomStay.rateAmount.amount` là giá **MỖI ĐÊM**, nhưng
  `fct_reservation_night` đang chia thêm cho số đêm (`total_amount / night_count`) →
  doanh thu/ADR/RevPAR ước tính bị thiếu N lần cho khách ở N đêm.
- **F2 (trung bình):** `stg_reservations` lấy ngày ở từ `originalTimeSpan` (kỳ ở GỐC lúc
  đặt), trong khi OHIP spec ghi rõ originalTimeSpan không đổi khi kỳ ở thay đổi. Raw data
  có sẵn `roomStay.arrivalDate` / `roomStay.departureDate` (ngày THỰC TẾ). 67/4.808 booking
  (1,4%) đang lệch — chủ yếu khách về sớm, hệ thống vẫn đếm đêm không xảy ra.

### Bằng chứng F1 (đối chiếu folio thực, khách CheckedOut)

| Số đêm | DT Room thực (folio) | Ước tính hiện tại | rateAmount × số đêm |
|---|---|---|---|
| 1 | 5.09M | 4.56M ✓ | 4.56M ✓ |
| 2 | 10.88M | 5.64M ✗ | 11.28M ✓ |
| 3 | 13.93M | 4.83M ✗ | 14.48M ✓ |

→ Kết luận không thể chối cãi: rateAmount là giá/đêm. `night_amount` đúng phải =
`total_amount` (không chia).

## 2. Goals

- Doanh thu/ADR/RevPAR ước tính phản ánh đúng "doanh thu tiền phòng dự kiến".
- Đêm lưu trú tính theo kỳ ở THỰC TẾ (khách về sớm không bị đếm thừa đêm).

## 3. Scope

### In Scope

- `eras_dbt/models/staging/stg_reservations.sql` — đổi nguồn 2 cột ngày.
- `eras_dbt/models/dimensional/fct_reservation_night.sql` — bỏ phép chia night_count.
- `dbt build` toàn bộ (staging → dimensional → marts tự rebuild theo DAG).
- **F3 — ADR thẻ KPI loại đêm 0₫** (bổ sung 22-07-26): `dashboard_v2/data/repository.py`,
  DUY NHẤT khối `ROOM_NIGHTS_SQL` — thêm điều kiện `AND night_amount > 0` để mẫu số ADR
  loại phòng comp/house-use theo chuẩn STR/USALI (hiện 211/2.119 đêm 0₫ pha loãng ADR ~11%;
  bản ADR ước tính trong kpi_daily_snapshot đã loại đúng — fix này đồng bộ 2 phiên bản).
  PHẢI làm SAU Bước 3 (dbt build) vì night_amount vừa được rebuild.

### Out of Scope — TUYỆT ĐỐI KHÔNG ĐỤNG

- `fct_folio_line` / `stg_cashiering_postings` (doanh thu THỰC — đang đúng, PM revenue
  đã được tính đủ theo xác nhận nghiệp vụ 22-07-26).
- Mọi file trong `dashboard/` và `dashboard_v2/` — NGOẠI TRỪ duy nhất khối
  `ROOM_NIGHTS_SQL` trong `dashboard_v2/data/repository.py` (F3 ở In-Scope). Cấm đụng
  `ROOM_REVENUE_SQL`, `ROOM_COUNT_SQL`, `KPI_DAILY_SQL` và mọi hàm Python trong file đó.
- Cột `total_amount` trong staging: GIỮ TÊN (đổi tên là breaking change cho code khác
  đang select) — chỉ sửa comment giải thích ngữ nghĩa.
- Không sửa logic ADR/OCC/cancel trong `kpi_daily_snapshot` (đang đúng chuẩn).

## 4. Touchpoints

| File | Thay đổi |
|---|---|
| `eras_dbt/models/staging/stg_reservations.sql` | 2 dòng ngày + comment |
| `eras_dbt/models/dimensional/fct_reservation_night.sql` | 1 biểu thức night_amount + comment |
| `dashboard_v2/data/repository.py` | 1 dòng filter trong ROOM_NIGHTS_SQL (F3 — ADR) + comment |

Hạ nguồn rebuild tự động (không sửa tay): `kpi_daily_snapshot` (total_revenue/adr/revpar
tăng đúng), `kpi_pickup` (pickup_*_revenue tăng đúng), `kpi_pacing`, `dim_date`.

## 5. Public Contracts

Tên cột không đổi ở mọi model → dashboard không cần sửa. Chỉ GIÁ TRỊ các cột ước tính
thay đổi (tăng) — đây là chủ đích của fix.

## 6. Blast Radius

- **Files:** 2 file sửa; 4 model hạ nguồn rebuild.
- **Risk:** Trung bình-thấp. Thuần dbt, rollback = revert 2 file + dbt build lại.
  Số ước tính trên tab Xu hướng/Pace sẽ TĂNG rõ rệt (~2-3×) — là hành vi ĐÚNG mong đợi,
  không phải regression.

## 7. Implementation Checklist

### Bước 1 — `eras_dbt/models/staging/stg_reservations.sql`

Đổi 2 dòng lấy ngày (hiện tại dòng ~23-24):

```sql
-- TRƯỚC:
(raw_data->'roomStay'->'originalTimeSpan'->>'startDate')::date   as arrival_date,
(raw_data->'roomStay'->'originalTimeSpan'->>'endDate')::date     as departure_date,

-- SAU (kèm comment):
-- Ngày ở THỰC TẾ (roomStay.arrivalDate/departureDate) — KHÔNG dùng originalTimeSpan
-- vì OHIP spec: originalTimeSpan giữ nguyên khi kỳ ở bị đổi (đổi lịch/về sớm/no-show cuộn)
(raw_data->'roomStay'->>'arrivalDate')::date                     as arrival_date,
(raw_data->'roomStay'->>'departureDate')::date                   as departure_date,
```

Lưu ý: cả 2 key này tồn tại trong 100% rows raw hiện có (đã kiểm chứng 22-07-26 qua
`jsonb_object_keys`). Khách về sớm dạng arrival=departure sẽ tự bị loại bởi filter
`departure_date > arrival_date` sẵn có trong fct — hành vi đúng (0 đêm).

### Bước 2 — `eras_dbt/models/dimensional/fct_reservation_night.sql`

Đổi biểu thức night_amount (hiện tại dòng ~44):

```sql
-- TRƯỚC:
(total_amount::numeric / night_count) as night_amount,

-- SAU (kèm comment):
-- total_amount = roomStay.rateAmount = giá MỖI ĐÊM (per-night, xác nhận bằng đối chiếu
-- folio 22-07-26) → night_amount chính là rateAmount, KHÔNG chia cho night_count.
total_amount::numeric as night_amount,
```

Đồng thời xoá/không dùng biến `night_count` trong CTE nếu không còn chỗ nào tham chiếu
(kiểm tra bằng grep trước khi xoá; nếu còn dùng thì giữ).

### Bước 3 — Rebuild + test

```bash
cd eras_dbt && dbt build --profiles-dir .
```

- Profile: `eras_dbt/.user.yml` (đã tồn tại, gitignored). Nếu chạy ngoài Docker mà lỗi
  kết nối host `postgres`: dùng host `localhost` port `5434` (per
  `process/context/all-context.md` §Run extractor LOCALLY).
- `dbt build` bao gồm cả dbt tests — tất cả phải PASS.

### Bước 4 — `dashboard_v2/data/repository.py` — ADR loại đêm 0₫ (F3)

Sửa DUY NHẤT khối `ROOM_NIGHTS_SQL` (hiện tại dòng ~223):

```sql
-- TRƯỚC:
ROOM_NIGHTS_SQL = """
    SELECT COUNT(*) AS room_nights
    FROM analytics.fct_reservation_night
    WHERE business_date BETWEEN %(start_date)s AND %(end_date)s
      AND reservation_status NOT IN ('Cancelled', 'NoShow')
      AND (%(hotel_id)s::text IS NULL OR hotel_id = %(hotel_id)s)
"""

-- SAU:
ROOM_NIGHTS_SQL = """
    -- Mẫu số ADR: loại đêm 0đ (comp/house-use) theo chuẩn STR/USALI —
    -- đồng bộ với ADR ước tính trong kpi_daily_snapshot (đã loại sẵn).
    -- Thẻ KPI "Đêm lưu trú" KHÔNG dùng SQL này (lấy từ kpi_daily_snapshot) nên không đổi.
    SELECT COUNT(*) AS room_nights
    FROM analytics.fct_reservation_night
    WHERE business_date BETWEEN %(start_date)s AND %(end_date)s
      AND reservation_status NOT IN ('Cancelled', 'NoShow')
      AND night_amount > 0
      AND (%(hotel_id)s::text IS NULL OR hotel_id = %(hotel_id)s)
"""
```

Xác nhận trước khi sửa (agent PHẢI kiểm): `ROOM_NIGHTS_SQL` chỉ được dùng trong
`_fetch_adr_revpar_inputs` (mẫu số ADR) — RevPAR dùng `room_count × days`, thẻ Đêm lưu trú
dùng `kpi_daily_snapshot` → cả hai KHÔNG bị ảnh hưởng. Nếu grep thấy chỗ dùng khác → DỪNG, báo lại.

Sau khi sửa: `docker restart erasopera-dashboard_v2-1` (container dev, KHÔNG đụng prod).

### Bước 5 — Chạy gate xác minh số liệu (G1–G7 bên dưới)

## 8. Verification Evidence

Xem §10 Validate Contract — gate G1–G5 là danh sách bắt buộc.

## 9. Resume and Execution Handoff

- **Selected Plan File Path:** `process/general-plans/active/dbt-revenue-estimate-fix_22-07-26/dbt-revenue-estimate-fix_PLAN_22-07-26.md`
- **Executor:** AI-Agent ngoài — file plan này tự chứa toàn bộ ngữ cảnh cần thiết.
- **Reviewer sau EXECUTE:** orchestrator (Claude) đối chiếu diff + chạy lại G2–G5.
- **Open decisions:** không còn.

## 10. Validate Contract

generated-by: outer-pvl
date: 2026-07-22
Date: 22-07-2026
Gate: PASS

### Khẳng định đã kiểm chứng trước (orchestrator, 22-07-26)

| # | Khẳng định | Bằng chứng |
|---|---|---|
| 1 | rateAmount là giá/đêm | Bảng đối chiếu folio §1 (sai lệch đúng bội số đêm) |
| 2 | roomStay.arrivalDate/departureDate tồn tại trong raw | `jsonb_object_keys` trên toàn bộ 4.808 rows |
| 3 | 67/4.808 booking lệch original vs thực tế | SQL count 22-07-26 |
| 4 | Hạ nguồn dùng night_amount: kpi_daily_snapshot, kpi_pickup | grep toàn bộ eras_dbt/models |
| 5 | Không model nào ngoài 2 file cần sửa tay | grep + DAG dbt |
| 6 | `.user.yml` profile tồn tại | ls 22-07-26 |

### Ràng buộc cho agent thực thi (KHÔNG deviation)

1. CHỈ sửa 2 file nêu ở §4. Cấm đụng `fct_folio_line`, `stg_cashiering_postings`,
   `kpi_daily_snapshot`, mọi file dashboard.
2. GIỮ tên cột `total_amount` và `night_amount` — chỉ đổi giá trị biểu thức + comment.
3. Số ước tính TĂNG ~2-3× sau fix là ĐÚNG (mục tiêu của fix) — không được "sửa lại cho
   giống số cũ".
4. KHÔNG commit. Báo kết quả từng gate rồi dừng.

### Test Gates (chạy từ repo root)

| Gate | Lệnh | Đạt khi |
|---|---|---|
| G1 dbt build + tests | `cd eras_dbt && dbt build --profiles-dir .` | exit 0, mọi test PASS |
| G2 Hết phép chia | `grep -c "/ night_count" eras_dbt/models/dimensional/fct_reservation_night.sql` | output `0` |
| G3 Ngày thực tế | `grep -c "originalTimeSpan" eras_dbt/models/staging/stg_reservations.sql` | output `0` |
| G4 Ước tính ≈ thực (per-night) | SQL bên dưới | cột `ty_le` trong khoảng **0.75–1.15** cho mọi dòng |
| G5 Không mất grain | SQL: `SELECT COUNT(*) - COUNT(DISTINCT fact_sk) FROM analytics.fct_reservation_night;` (qua `docker exec erasopera-postgres-1 psql -U user -d erg_opera_data`) | output `0` |
| G6 ADR filter đúng chỗ | `grep -c "night_amount > 0" dashboard_v2/data/repository.py` | output `1` (chỉ trong ROOM_NIGHTS_SQL) |
| G7 App chạy sạch sau F3 | `docker restart erasopera-dashboard_v2-1 && sleep 8 && curl -s http://localhost:8511/_stcore/health` | output `ok` |

SQL cho G4 (chạy qua `docker exec erasopera-postgres-1 psql -U user -d erg_opera_data`):

```sql
WITH res AS (
  SELECT reservation_id, AVG(night_amount) est_per_night, COUNT(*) nights
  FROM analytics.fct_reservation_night WHERE reservation_status='CheckedOut' GROUP BY 1
), folio AS (
  SELECT reservation_id, SUM(posted_amount) room_rev
  FROM analytics.fct_folio_line WHERE revenue_category='Room' GROUP BY 1
)
SELECT r.nights, COUNT(*) n_res,
       ROUND(AVG(r.est_per_night) / NULLIF(AVG(f.room_rev / r.nights),0), 2) AS ty_le
FROM res r JOIN folio f USING (reservation_id)
WHERE r.nights BETWEEN 1 AND 3 GROUP BY 1 ORDER BY 1;
```

(Trước fix, ty_le ≈ 0.90 / 0.52 / 0.35 — sau fix cả 3 dòng phải về vùng ~0.9–1.0.)

### Accepted Concerns (known-gaps, không chặn)

- rateAmount là giá đêm HIỆN HÀNH của booking — kỳ ở đổi giá giữa chừng vẫn ước tính theo
  1 mức giá (sai số nhỏ, chấp nhận cho số "ước tính"; số thực đã có folio).
- Doanh thu ước tính không bao giờ gồm doanh thu PM/F&B (6,81 tỷ) — ĐÚNG bản chất
  "doanh thu tiền phòng dự kiến"; đã xác nhận với user 22-07-26.
- Sau fix, so sánh "vs kỳ trước" trên tab Xu hướng sẽ nhảy bậc tại thời điểm rebuild —
  hiện tượng một lần, không phải bug.
- ADR thẻ KPI sau F3 sẽ TĂNG ~11% (₫2,71M → ~₫3,01M cho YTD) — là hành vi đúng chuẩn
  STR, không phải regression.
- **Multi-room booking (known-gap — đã kiểm chứng là KHÔNG ảnh hưởng room nights):**
  12/4.808 reservation có `numberOfRooms` > 1, nhưng CẢ 12 đều `Cancelled` và chưa gán
  phòng (kiểm chứng 22-07-26). Nguyên nhân: OPERA tách booking nhiều phòng thành từng
  reservation 1-phòng khi nhận phòng — kỳ ở thật luôn là 1-phòng/reservation → room nights
  hiện KHÔNG thiếu. Ảnh hưởng còn lại duy nhất: cancellation_rate đếm đoàn huỷ N phòng là
  1 lượt (chấp nhận; nếu muốn đếm theo phòng: nhân `numberOfRooms` trong CTE cancellation —
  backlog, ngoài scope).
