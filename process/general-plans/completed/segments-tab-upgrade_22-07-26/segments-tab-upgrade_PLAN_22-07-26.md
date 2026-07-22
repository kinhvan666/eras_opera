---
name: plan:segments-tab-upgrade
description: "Upgrade dashboard_v2 Segments tab: business-friendly labels via existing t_code maps, drop rate-plan chart, executive-grade charts (metric toggle, % share, horizontal bars)."
date: 22-07-26
feature: segments-tab-upgrade
phase: "plan"
supersedes: process/general-plans/backlog/dashboard-v2-segment-refactor_22-07-26/dashboard-v2-segment-refactor_PLAN_22-07-26.md
---

# Plan: Segments Tab Upgrade (dashboard_v2)

**Complexity:** SIMPLE

## 1. Overview

Nâng cấp tab "Phân khúc" của **dashboard_v2** (bản đang chạy production, port 8502 qua
`docker-compose.prod.yml`) theo góc nhìn lãnh đạo tập đoàn:

1. Hiển thị **tên nghiệp vụ** thay cho mã OPERA thô (TAF, DIG, EML…) trên trục biểu đồ —
   tái dùng `MAPS` + `t_code()` sẵn có trong `dashboard_v2/ui/i18n.py` (song ngữ VI/EN),
   KHÔNG tạo dbt dimension mới.
2. **Bỏ biểu đồ "theo gói giá"** (rate plan) — ~40 mã đuôi dài, giá trị thấp với lãnh đạo.
3. Nâng chất lượng chart: chuyển hết sang **thanh ngang**, sắp giảm dần, nhãn **% share**
   trên thanh, highlight thanh dẫn đầu, giảm gridline. Metric duy nhất: **Đêm lưu trú**
   (quyết định user 22-07-26 — phương án 2: không thêm doanh thu vào tab này để tránh
   trùng/lệch số với tab Doanh thu vốn dùng doanh thu thực từ folio).

Plan này **thay thế** plan `dashboard-v2-segment-refactor_22-07-26` (đã bỏ — nhắm sai
thư mục `dashboard/` cũ và dùng mã mapping không tồn tại trong dữ liệu).

## 2. Goals

- Lãnh đạo đọc được tab Phân khúc không cần biết mã OPERA.
- Tab gọn còn 3 chart có thứ bậc thông tin rõ ràng, metric duy nhất là Đêm lưu trú.
- Giữ nguyên tính năng song ngữ EN/VI.

## 3. Scope

### In Scope

- `dashboard_v2/ui/i18n.py` — bổ sung mã thiếu vào MAPS + key i18n mới.
- `dashboard_v2/ui/tabs/segments.py` — viết lại 4 chart → 3 chart theo spec dưới.
- Không file nào khác.

### Out of Scope

- KHÔNG đụng dbt / warehouse (khác plan cũ).
- KHÔNG đụng dashboard cũ (`dashboard/`).
- KHÔNG đổi `fetch_kpi_daily_segmented`.
- KHÔNG thêm doanh thu vào tab Phân khúc (phương án 2 — user chốt 22-07-26): tránh hiển thị
  doanh thu ước tính cạnh doanh thu thực của tab Doanh thu. Doanh thu theo phân khúc (cần
  gắn market_code vào pipeline folio) → backlog.
- Các tab khác (Doanh thu, Xu hướng, Pace).

## 4. Touchpoints

| File | Thay đổi |
|---|---|
| `dashboard_v2/ui/i18n.py` | Thêm ~7 mã vào MAPS (VI+EN); thêm ~6 key i18n mới; sửa `DNK`→`DMK` |
| `dashboard_v2/ui/tabs/segments.py` | Viết lại `draw()` — 3 chart ngang, metric toggle, % share |

## 5. Public Contracts

Không có. Thuần presentation layer.

## 6. Blast Radius

- **Files:** 2 (cùng package `dashboard_v2`).
- **Risk:** Thấp. Không đổi schema/query/auth. Rollback = revert 2 file.
- **Không giao cắt** với các sửa đổi gần đây (header, KPI delta, i18n room-nights đã commit).

## 7. Implementation Checklist

### Bước 1 — Bổ sung MAPS trong `dashboard_v2/ui/i18n.py`

Mã có trong dữ liệu (đã query `analytics.fct_reservation_night` 22-07-26) nhưng thiếu trong MAPS:

| Category | Mã thiếu | Tên CHỐT (EN / VI) — user xác nhận 22-07-26 |
|---|---|---|
| market_code | `CCG` | Corporate Contracted Group / Khách đoàn công ty |
| market_code | `CMP` | Complimentary / Phòng Comp |
| market_code | `HSU` | House Use / Phòng nội bộ |
| market_code | `INM` | Internet Member / Khách hội viên trực tuyến |
| market_code | `WEB` | Website / Khách đặt qua Website trực tiếp |
| market_code | `WIG` | Wholesale Internet Group / Khách đoàn B2B Online |
| room_type | `DMK` | Deluxe King / Phòng Deluxe giường King (MAPS đang ghi nhầm `DNK` — đổi key thành `DMK`) |

- `source_of_business`: đã đủ 100% (11/11 mã), không sửa.
- Fallback `t_code()` trả về mã thô nếu gặp mã mới — giữ nguyên hành vi.

### Bước 2 — Key i18n mới (cả `vi` và `en`)

```
"seg.other"             → "Khác" / "Other"
"chart.seg_by_market"   → "Đêm lưu trú theo phân khúc thị trường" / "Room Nights by Market Segment"
"chart.seg_by_source"   → "Đêm lưu trú theo kênh đặt phòng" / "Room Nights by Booking Channel"
"chart.seg_by_roomtype" → "Đêm lưu trú theo loại phòng" / "Room Nights by Room Type"
```

(Key cũ `chart.roomnights_by_*`, `msg.no_rateplan` giữ nguyên — dashboard cũ còn dùng chung pattern; chỉ dashboard_v2 trỏ key mới.)

### Bước 3 — Viết lại `dashboard_v2/ui/tabs/segments.py`

1. **Bỏ hẳn** fetch + chart `rate_plan_code` (dòng 14 và block `col3` 68–89 hiện tại).
2. **3 chart đều thanh ngang**, metric duy nhất `room_nights` (`y` = tên phân khúc sort
   giảm dần, `x` = đêm lưu trú):
   - Market (trái trên) — **top 8 + gom "Khác"** (19 mã là quá nhiều).
   - Source (phải trên) — giữ nguyên toàn bộ (11 mã).
   - Room type (hàng dưới, full-width hoặc trái) — 6 mã, giữ nguyên.
3. **Nhãn trục = tên nghiệp vụ**: dùng cột `_desc` (đã có sẵn logic `t_code`) làm trục `y`;
   mã thô chuyển vào tooltip. Tên dài → cắt 28 ký tự + "…" trên trục, tên đầy đủ trong tooltip.
4. **% share**: `mark_text` cuối thanh — `"{room_nights:,} ({share:.0%})"`; share tính trên
   tổng đêm lưu trú của khoảng đã chọn.
5. **Màu**: thanh #1 giữ `#1D4ED8` đậm, các thanh còn lại `#1D4ED8` opacity 0.55 (điều kiện
   `alt.condition` theo rank); bỏ gridline dọc dày: `alt.Axis(grid=True, tickCount=5,
   gridOpacity=0.15)`.
6. Empty-state: giữ `st.info(msg.no_*)` như cũ.

### Bước 4 — Kiểm tra song ngữ + restart

- Chạy syntax check 2 file; restart container dev `erasopera-dashboard_v2-1`; probe tab ở
  cả VI và EN.

## 8. Verification Evidence

| Gate / Scenario | Strategy | Proves |
|---|---|---|
| `python -m py_compile` 2 file sửa | Fully-Automated | Không lỗi cú pháp |
| Mọi mã trong fact table có tên trong MAPS | Fully-Automated | Script đối chiếu `SELECT DISTINCT` 3 cột vs keys trong MAPS — 0 mã lọt |
| Tab Phân khúc còn đúng 3 chart, không còn chart gói giá | Agent-Probe | Đếm chart qua read_page sau login |
| Trục hiển thị tên nghiệp vụ, không phải mã thô | Agent-Probe | Screenshot/read_page thấy "Travel Agent FIT…" thay vì "TAF" |
| Đổi EN ↔ VI nhãn đổi theo | Agent-Probe | Click EN, xác nhận tên tiếng Anh |
| Khoảng ngày không dữ liệu → empty-state | Hybrid | Chọn range 2025, thấy msg.no_* |

## 9. Test Infra Improvement Notes

- Backlog: doanh thu THỰC theo phân khúc cần thêm market_code vào pipeline folio
  (extractor/dbt) — việc riêng, không thuộc plan này.
- Backlog: mapping tên nên chuyển về warehouse (dbt seed) nếu sau này có BI tool thứ hai
  đọc chung — khi đó cân nhắc lại bài toán song ngữ.

## 10. Resume and Execution Handoff

- **Selected Plan File Path:** `process/general-plans/active/segments-tab-upgrade_22-07-26/segments-tab-upgrade_PLAN_22-07-26.md`
- **Last Completed Phase:** PLAN
- **Validate Contract Status:** Pending — chạy VALIDATE trước EXECUTE.
- **Open decisions:** không còn — 7 tên mã đã được user chốt 22-07-26 (bảng Bước 1).
- **Supporting context:** `dashboard_v2/ui/tabs/segments.py`, `dashboard_v2/ui/i18n.py`
  (MAPS dòng 218+), `dashboard_v2/data/repository.py` (`fetch_kpi_daily_segmented` dòng 144 —
  đã trả `total_revenue`, không cần sửa), phân bố mã thực tế đã query 22-07-26.

## 11. Validate Contract

generated-by: outer-pvl
date: 2026-07-22
Date: 22-07-2026
Gate: PASS

### V1–V3 Findings (đã kiểm chứng 22-07-26 trên working tree + DB thực)

| # | Khẳng định trong plan | Kết quả kiểm chứng |
|---|---|---|
| 1 | `segments.py:14` fetch rate_df; block col3 dòng 68–89 là chart gói giá | ✅ Khớp |
| 2 | Key `seg.other`, `chart.seg_by_*` chưa tồn tại trong i18n.py | ✅ Chưa có — thêm mới an toàn |
| 3 | `DNK` xuất hiện đúng 2 chỗ: i18n.py:242 (vi), :290 (en) | ✅ Đổi cả 2 thành `DMK` |
| 4 | Sau bổ sung 6 mã market: phủ 19/19 mã thực tế trong fct_reservation_night | ✅ (DB query 22-07-26) |
| 5 | Source 11/11, room-type 6/6 sau sửa DMK | ✅ |
| 6 | `fetch_kpi_daily_segmented` không cần sửa | ✅ Đã trả room_nights + total_revenue |
| 7 | `msg.no_market/no_source/no_roomtype` tồn tại cả vi+en | ✅ |
| 8 | Altair 5.3.0 hỗ trợ layer bar+text và alt.condition theo rank | ✅ (requirements.txt) |

### Ràng buộc cho agent thực thi (KHÔNG deviation)

1. CHỈ sửa 2 file: `dashboard_v2/ui/i18n.py`, `dashboard_v2/ui/tabs/segments.py`.
2. KHÔNG xoá `rate_plan_code` khỏi `dashboard_v2/data/repository.py` — đó là tầng SQL
   dùng chung, ngoài scope. Chỉ gỡ 2 usage trong segments.py (dòng 14 + block col3).
3. KHÔNG xoá key i18n cũ (`chart.roomnights_by_*`, `msg.no_rateplan`, MAPS
   `rate_plan_code` nếu có) — chỉ THÊM key mới và đổi `DNK`→`DMK`.
4. Tên 7 mã mới phải dùng ĐÚNG NGUYÊN VĂN bảng "Tên CHỐT" ở Bước 1 (user đã duyệt).
5. Metric duy nhất: `room_nights`. KHÔNG thêm toggle doanh thu (quyết định user 22-07-26).
6. Thêm key mới vào CẢ HAI dict `vi` và `en`; mã "Khác"/"Other" dùng key `seg.other`.
7. Sau khi sửa xong: KHÔNG commit, KHÔNG restart container prod — chỉ restart container
   dev `erasopera-dashboard_v2-1` để chạy gate G6.

### Test Gates (chạy từ repo root `D:/ErasProjects/ErasOpera`)

| Gate | Lệnh | Đạt khi |
|---|---|---|
| G1 Syntax | `python -m py_compile dashboard_v2/ui/i18n.py dashboard_v2/ui/tabs/segments.py` | exit 0 |
| G2 Rate chart gỡ sạch | `grep -c "rate_plan_code" dashboard_v2/ui/tabs/segments.py` | output `0` |
| G3 DNK đã đổi | `grep -c '"DNK"' dashboard_v2/ui/i18n.py` | output `0` |
| G4 DMK đủ 2 dict | `grep -c '"DMK"' dashboard_v2/ui/i18n.py` | output `2` |
| G5 Key mới đủ vi+en | `grep -c '"seg.other"' dashboard_v2/ui/i18n.py` và `grep -c '"chart.seg_by_market"' dashboard_v2/ui/i18n.py` (tương tự cho seg_by_source, seg_by_roomtype) | mỗi key output `2` |
| G6 App khởi động sạch | `docker restart erasopera-dashboard_v2-1 && sleep 8 && curl -s http://localhost:8511/_stcore/health` | output `ok` |
| G7 Mapping phủ 100% | `docker exec erasopera-dashboard_v2-1 python -c "import sys; sys.path.insert(0,'/app'); import re; src=open('/app/ui/i18n.py',encoding='utf-8').read(); import psycopg2; conn=psycopg2.connect('postgresql://user:password@postgres:5432/erg_opera_data'); cur=conn.cursor(); [print(cat,[c for c in [r[0] for r in (cur.execute(f'SELECT DISTINCT {col} FROM analytics.fct_reservation_night WHERE {col} IS NOT NULL'), cur.fetchall())[1]] if f'\"{c}\"' not in src] or 'OK') for cat,col in [('market','market_code'),('source','source_of_business'),('room','room_type')]]"` | 3 dòng đều `OK` |

### Agent-Probe Gates (deferred — orchestrator kiểm tra sau EXECUTE, cần đăng nhập UI)

| Gate | Cách kiểm | Đạt khi |
|---|---|---|
| P1 | Mở tab Phân khúc | Đúng 3 chart, không còn chart gói giá |
| P2 | Đọc trục y các chart | Tên nghiệp vụ ("Travel Agent FIT…"), không phải mã thô |
| P3 | Đọc nhãn cuối thanh | Có số đêm + % share, tổng share market ≈ 100% |
| P4 | Bấm EN rồi VI | Nhãn trục + tiêu đề đổi ngôn ngữ theo |
| P5 | Chọn khoảng ngày 2025 (không dữ liệu) | Hiện msg.no_* , không crash |

### Accepted Concerns (known-gaps, không chặn EXECUTE)

- Thanh "Khác" (gom ngoài top-8 market) xếp theo giá trị tự nhiên, không ghim cuối — chấp nhận.
- Tên trục cắt 28 ký tự có thể trùng nhau về mặt hiển thị giữa 2 mã hiếm — tooltip vẫn phân biệt.
- G7 nối DB bằng DATABASE_URL mặc định trong container dev — nếu container dùng .env khác, thay chuỗi kết nối tương ứng.

### Handoff

- Executor: AI-Agent ngoài (không có ngữ cảnh hội thoại) — mọi thông tin cần thiết nằm trong
  file plan này. Bắt đầu từ §7 Implementation Checklist, tuân thủ §11 Ràng buộc, chạy đủ
  G1–G7, báo kết quả từng gate.
- Reviewer sau EXECUTE: orchestrator (Claude) chạy P1–P5 + đối chiếu diff với §7.
