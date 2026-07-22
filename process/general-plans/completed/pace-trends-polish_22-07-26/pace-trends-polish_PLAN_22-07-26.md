---
name: plan:pace-trends-polish
description: "Polish dashboard_v2 Trends monthly view (partial-month marker, ADR label precision, MoM%) and Pace tab (daily-pickup chart replaces empty pace panel, incremental pickup buckets, table/label fixes)."
date: 22-07-26
feature: pace-trends-polish
phase: "complete"
status: "completed"
---

# Plan: Hoàn thiện tab Xu hướng (tháng) + tab Pace — dashboard_v2

**Complexity:** SIMPLE

## 1. Overview

6 cải tiến đã duyệt 22-07-26 (review executive):

| # | Vấn đề | Mức |
|---|---|---|
| 1 | Tháng cụt (2026-04 thiếu đầu, 2026-07 chưa hết) trông như tháng tốt/kém nhất — gây hiểu sai | 🔴 |
| 2 | Nhãn ADR tháng "4M 4M 4M 4M" — làm tròn quá thô | 🟡 |
| 3 | Cột doanh thu tháng thiếu % so tháng trước | 🟢 |
| 4 | Panel "Pace % vs năm trước" trống đến 2027 — nửa màn hình chết | 🔴 |
| 5 | Pickup 7/30/90 là cửa sổ LỒNG NHAU vẽ như 3 mục độc lập; bảng: cột "Phòng" đặt tên sai, cột hotel_id thừa | 🟠 |
| 6 | Trục y chart pickup bị cắt chữ (nhãn mới dài) | 🟡 |

## 2. Decision Summary (INNOVATE — chốt 22-07-26)

| Quyết định | Chọn | Bị loại + lý do |
|---|---|---|
| Đánh dấu tháng cụt | Cột nhạt (opacity 0.45) + hậu tố `*` trên nhãn + 1 caption chung | ~~Bỏ tháng cụt khỏi chart~~ (mất thông tin mới nhất); ~~kẻ sọc~~ (Altair vẽ pattern phức tạp không đáng) |
| Panel Pace % trống | Thay tạm bằng **chart "Lượng đặt mới theo ngày (30 ngày qua)"** (bookings mới/ngày từ `booking_date`); TỰ ĐỘNG đổi về Pace % khi có dữ liệu năm trước (logic `has_prior` sẵn có giữ nguyên) | ~~Giữ thông báo trống~~ (nửa màn hình chết 1 năm); ~~bỏ panel~~ (mất chỗ cho Pace % sau này) |
| Pickup lồng nhau | Chuyển thành **khoảng tăng thêm**: 0–7 / 8–30 / 31–90 (tính từ số luỹ kế sẵn có, không đổi dbt) | ~~Sửa mart kpi_pickup~~ (đổi dbt không cần thiết — UI trừ được); ~~chỉ ghi chú "luỹ kế"~~ (vẫn dễ cộng nhầm) |
| Cột hotel_id trong bảng | Bỏ luôn (đã có filter cơ sở phía trên) | ~~Giữ~~ (nhiễu) |

## 3. Scope

### In Scope

| File | Việc |
|---|---|
| `dashboard_v2/ui/tabs/trends.py` | Mục 1, 2, 3 — CHỈ nhánh `by_month` |
| `dashboard_v2/ui/tabs/pacing.py` | Mục 4, 5, 6 |
| `dashboard_v2/data/repository.py` | THÊM 1 hàm mới `fetch_pickup_daily` (không sửa hàm nào khác) |
| `dashboard_v2/ui/i18n.py` | ~5 key mới + sửa 2 value (cả `en` lẫn `vi`) |

### Out of Scope

- dbt/mart (`kpi_pickup` giữ nguyên — bucket tính ở UI).
- Nhánh daily của Xu hướng (vừa redesign xong), tab Doanh thu/Phân khúc, `executive/`, dashboard cũ.
- Logic Pace % khi CÓ dữ liệu năm trước — giữ nguyên (sẽ tự kích hoạt 2027).

## 4. Blast Radius

4 file, 1 package. Risk thấp; rollback = revert. Không đụng warehouse.

## 5. Implementation Checklist

### Mục 1 — Tháng cụt (`trends.py`, nhánh `by_month`)

1. Trong `_monthly(df)`: thêm cột `days_in_month_data = groupby.count(business_date)` và
   `is_partial = days_in_month_data < số ngày lịch của tháng đó`
   (`pd.Period(month).days_in_month`).
2. Chart doanh thu tháng: `opacity=alt.condition(datum.is_partial, 0.45, 0.8)`;
   nhãn cột: thêm `*` khi partial (`_rev_label = fmt + ("*" nếu partial)`).
   LƯU Ý: revenue dùng `rev_src` (từ folio, groupby month riêng) — join cờ `is_partial`
   từ mdf vào rev_src theo month trước khi vẽ.
3. Caption chung dưới chart doanh thu: key `trend.partial_month_note`
   ("\* Tháng chưa đủ ngày dữ liệu — số liệu chưa trọn tháng").
4. OCC/ADR/Cancel tháng: thêm `*` vào nhãn điểm (mark_text) của tháng partial — không
   đổi màu đường.

### Mục 2 — Độ mịn nhãn ADR (`trends.py`)

`_fmt`: nhánh `>= 1e6` đổi `.0f` → `.1f` (VD "4.3M"). (Nhánh B giữ `.2f`, K giữ `.0f`.)

### Mục 3 — % MoM trên nhãn doanh thu tháng (`trends.py`)

Trong rev_src (sau groupby month, sort theo month): `_mom = total_revenue.pct_change()`;
nhãn thành `"3.88B (+45%)"` (tháng đầu không có % — chỉ số tiền). Partial → vẫn hiện %,
kèm `*` từ Mục 1.

### Mục 4 — Panel phải tab Pace (`pacing.py` + `repository.py`)

1. `repository.py` — hàm MỚI (đặt cạnh `fetch_kpi_pickup`):

```python
@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_pickup_daily(hotel_id=None, days=30):
    """Số đêm đặt MỚI theo ngày đặt (booking_date) trong N ngày qua — gồm cả booking đã hủy sau đó thì loại."""
    sql = """
        select booking_date, count(*) as room_nights, sum(night_amount) as est_revenue
        from analytics.fct_reservation_night
        where booking_date >= current_date - %(days)s::int
          and reservation_status not in ('Cancelled', 'NoShow')
          and (%(hotel_id)s::text is null or hotel_id = %(hotel_id)s)
        group by booking_date
        order by booking_date
    """
    with psycopg2.connect(DATABASE_URL) as conn:
        return pd.read_sql(sql, conn, params={"hotel_id": hotel_id, "days": days})
```

2. `pacing.py` col2: giữ nguyên toàn bộ logic `has_prior` — CHỈ thay nhánh
   `st.info(t("msg.prior_year_na_long"))` bằng:
   - tiêu đề wrapper đổi sang `t("chart.pickup_daily")`
   - chart cột: `x=booking_date:T`, `y=room_nights:Q` màu `C["primary"]`, tooltip
     ngày + số đêm + doanh thu ước tính; height ~320
   - caption: `t("msg.prior_year_na_long")` chuyển xuống thành caption nhỏ dưới chart
     (giữ thông tin "Pace % sẽ có khi đủ dữ liệu năm trước")
   - `fetch_pickup_daily` trống → giữ st.info như cũ.

### Mục 5 — Pickup bucket tăng thêm + bảng (`pacing.py`)

1. Từ pickup_df luỹ kế (7/30/90) tính bucket:

```python
w = pickup_df.set_index("window_days")
buckets = pd.DataFrame({
    "bucket": [t("pacing.bucket_0_7"), t("pacing.bucket_8_30"), t("pacing.bucket_31_90")],
    "room_nights": [w.loc[7,"pickup_rooms"], w.loc[30,"pickup_rooms"]-w.loc[7,"pickup_rooms"], w.loc[90,"pickup_rooms"]-w.loc[30,"pickup_rooms"]],
    "est_revenue": [tương tự với pickup_revenue],
})
```

   (thiếu window nào trong df → bucket đó bỏ qua, không crash; sort thứ tự cố định 0–7, 8–30, 31–90 bằng `alt.X(sort=None)`)
2. Chart: cột theo bucket (`:N`, sort=None), y = room_nights.
3. Bảng: dùng buckets (KHÔNG còn hotel_id); đổi cột "Phòng" → key `pacing.rooms` sửa
   value thành "Số đêm" / "Room nights"; thêm dòng tổng (Total = giá trị 90 ngày luỹ kế)
   để không mất thông tin tổng.
4. Tiêu đề section `chart.pickup` sửa value: "... (cộng dồn 90 ngày, chia khoảng)" /
   "(incremental buckets over 90 days)".

### Mục 6 — Trục y bị cắt (`i18n.py`)

`pacing.room_nights_axis`: "Số đêm đặt phòng (Room Nights)" → "Số đêm đặt phòng" (vi);
"Rooms Picked Up" → "Room Nights" (en).

### Key i18n mới (cả `en` LẪN `vi`)

```
"chart.pickup_daily"    → "New room nights by booking day (last 30 days)" / "Lượng đặt mới theo ngày (30 ngày qua)"
"trend.partial_month_note" → "* Month with incomplete data" / "* Tháng chưa đủ ngày dữ liệu"
"pacing.bucket_0_7"     → "0–7 days" / "0–7 ngày"
"pacing.bucket_8_30"    → "8–30 days" / "8–30 ngày"
"pacing.bucket_31_90"   → "31–90 days" / "31–90 ngày"
"pacing.total"          → "Total (90 days)" / "Tổng (90 ngày)"
```

Sửa value 2 key sẵn có: `pacing.rooms`, `pacing.room_nights_axis` (trên); KHÔNG xoá key nào.

## 6. Resume and Execution Handoff

- **Plan path:** `process/general-plans/active/pace-trends-polish_22-07-26/pace-trends-polish_PLAN_22-07-26.md`
- **Executor:** AI-Agent ngoài — plan tự chứa.
- **Reviewer:** orchestrator (Claude) — gates + probe screenshot với user.
- Không phụ thuộc plan nào đang mở (trends-redesign + light-theme đã completed/uncommitted-clean… agent xác nhận working tree các file mục tiêu không có thay đổi dở dang trước khi bắt đầu).

## 7. Validate Contract

generated-by: outer-pvl
date: 2026-07-22
Date: 22-07-2026
Gate: PASS

### Khẳng định đã kiểm chứng (orchestrator, 22-07-26)

| # | Khẳng định | Bằng chứng |
|---|---|---|
| 1 | `kpi_pickup` trả hotel_id/window_days/pickup_rooms/pickup_revenue (luỹ kế 7/30/90) | repository.py:287-297 + screenshot |
| 2 | `fct_reservation_night.booking_date` tồn tại (nguồn cho pickup daily) | schema warehouse 22-07-26 |
| 3 | Nhánh `has_prior`/`msg.prior_year_na_long` ở pacing.py:82-85 — thay đúng chỗ | đọc code 22-07-26 |
| 4 | `_monthly` groupby month ở trends.py; rev_src groupby riêng từ folio | đọc code 22-07-26 |
| 5 | Key i18n mới chưa tồn tại | grep 22-07-26 |

### Ràng buộc cho agent thực thi (KHÔNG deviation)

1. CHỈ sửa 4 file §3. `repository.py`: CHỈ THÊM `fetch_pickup_daily`, cấm sửa hàm khác.
2. Nhánh daily tab Xu hướng + logic Pace-%-khi-có-dữ-liệu: KHÔNG đổi.
3. Màu qua `chart_colors()` (module ui/theme.py sẵn có) — cấm hex hardcode mới (gate G4).
4. Key i18n thêm cả 2 ngôn ngữ; không xoá key.
5. KHÔNG commit; restart CHỈ container dev `erasopera-dashboard_v2-1`.

### Test Gates

| Gate | Lệnh (repo root) | Đạt khi |
|---|---|---|
| G1 Syntax | `python -m py_compile` 4 file touched | exit 0 |
| G2 Hàm mới đúng chỗ | `grep -c "fetch_pickup_daily" dashboard_v2/data/repository.py` ≥ 1 và `grep -c "fetch_pickup_daily" dashboard_v2/ui/tabs/pacing.py` ≥ 1 | đúng |
| G3 Bucket tăng thêm | `grep -c "bucket_8_30" dashboard_v2/ui/tabs/pacing.py` | ≥ 1 |
| G4 Không hex mới trong tabs | `grep -rn '#[0-9A-Fa-f]\{6\}' dashboard_v2/ui/tabs/ --include='*.py'` | 0 match |
| G5 Key i18n đủ 2 ngôn ngữ | `grep -c '"chart.pickup_daily"'` = 2, tương tự 5 key còn lại | đúng |
| G6 Partial-month marker | `grep -c "is_partial" dashboard_v2/ui/tabs/trends.py` | ≥ 2 |
| G7 App chạy sạch | restart + health | `ok` |

### Agent-Probe Gates (deferred — orchestrator + user screenshot)

| Gate | Đạt khi |
|---|---|
| P1 | Tháng 2026-04 và 2026-07 (range mẫu 23/04–22/07): cột nhạt + nhãn có `*` + caption |
| P2 | Nhãn ADR tháng hiện 1 số lẻ (4.3M ≠ 3.5M) |
| P3 | Nhãn doanh thu tháng có (+x%) từ tháng thứ 2 |
| P4 | Panel phải Pace = chart đặt-mới-theo-ngày (~30 cột) + caption về Pace % |
| P5 | Pickup: 3 cột 0–7/8–30/31–90 KHÔNG lồng nhau (tổng 3 cột = giá trị 90 cũ); bảng hết hotel_id, cột "Số đêm", có dòng Tổng |
| P6 | Trục y pickup không còn bị cắt chữ |

### Accepted Concerns (known-gaps)

- Pickup daily loại booking đã hủy → con số là "net mới còn hiệu lực", không phải gross
  bookings tại thời điểm đặt. Chấp nhận cho V1; gross cần snapshot lịch sử (backlog).
- % MoM trên tháng partial so với tháng trọn là so lệch — đã có dấu `*` cảnh báo; chấp nhận.
- Doanh thu pickup là ước tính (night_amount) — nhất quán với hiện trạng tab Pace.
