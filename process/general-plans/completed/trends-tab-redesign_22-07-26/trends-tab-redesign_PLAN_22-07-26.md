---
name: plan:trends-tab-redesign
description: "Redesign dashboard_v2 Trends tab daily view: lines + 7-day moving average, weekend bands, weekly cancel rate. Monthly view unchanged."
date: 22-07-26
feature: trends-tab-redesign
phase: "complete"
status: "completed"
---

# Plan: Thiết kế lại tab Xu hướng (bản Theo ngày) — dashboard_v2

**Complexity:** SIMPLE

## 1. Overview

Bản "Theo ngày" của tab Xu hướng hiện vẽ ~90 cột/chart (Doanh thu, ADR) và đường răng cưa
không có trung bình trượt (OCC), cùng Cancel Rate theo ngày nhiễu vô nghĩa (mẫu vài
booking/ngày nhảy 0%→80%). Tên tab là "Xu hướng" nhưng không chart nào cho thấy xu hướng.

Thiết kế lại bản NGÀY theo nguyên tắc dataviz (form theo câu hỏi, một trục, nhiễu mờ —
tín hiệu đậm). **Bản THÁNG giữ nguyên 100%** (đã tốt: line + point + nhãn, ADR trọng số).

## 2. Decision Summary (INNOVATE — chốt 22-07-26)

| Quyết định | Chọn | Phương án bị loại + lý do |
|---|---|---|
| Dạng chart ngày cho Doanh thu/ADR | Đường ngày mờ + **đường MA-7 đậm** | ~~Giữ cột ngày~~ (90 cột = rừng gai, không đọc được xu hướng); ~~chỉ MA không có ngày~~ (mất khả năng soi ngày đột biến) |
| OCC ngày | Giữ vùng+đường, thêm MA-7 đậm + **dải cuối tuần** | ~~Chỉ thêm MA~~ (dải cuối tuần giải thích ngay chu kỳ răng cưa cho lãnh đạo — đáng giá) |
| Cancel Rate ngày | **Gộp theo tuần** (cột thưa ~13 cột) | ~~Giữ theo ngày~~ (tỷ lệ trên mẫu nhỏ = nhiễu vô nghĩa); ~~bỏ hẳn khỏi bản ngày~~ (mất thông tin không cần thiết — bản tuần vẫn hữu ích) |
| Chart "OCC theo thứ trong tuần" | **KHÔNG làm đợt này** | Để backlog — user chưa duyệt, tránh phình scope |
| Badge EST cho ADR ngày (nguồn ước tính) | **KHÔNG làm đợt này** | Số ước tính đã sửa đúng (plan dbt-revenue-fix 22-07-26); đồng bộ nguồn ADR là backlog riêng |
| Dual-axis (OCC + ADR chung chart) | **Không bao giờ** | Vi phạm nguyên tắc một trục |

## 3. Scope

### In Scope

- `dashboard_v2/ui/tabs/trends.py` — CHỈ nhánh `else` (daily) của 4 chart + helper mới.
- `dashboard_v2/ui/i18n.py` — thêm ~4 key mới (cả `vi` và `en`).

### Out of Scope — KHÔNG đụng

- Nhánh `by_month` (monthly) của cả 4 chart — giữ nguyên từng dòng.
- `data/repository.py`, mọi tab khác, dbt.
- Chart OCC-theo-thứ, badge EST (backlog — xem Decision Summary).

## 4. Touchpoints

| File | Thay đổi |
|---|---|
| `dashboard_v2/ui/tabs/trends.py` | Helper `_with_ma7`, `_weekend_bands`, `_weekly`; viết lại 4 nhánh daily |
| `dashboard_v2/ui/i18n.py` | 4 key mới ×2 ngôn ngữ |

## 5. Blast Radius

2 file, 1 package. Risk thấp — thuần presentation, monthly view không đổi, rollback = revert.

## 6. Implementation Checklist

### Bước 1 — Key i18n mới (thêm cả dict `en` LẪN `vi`)

```
"trend.ma7"             → "7-day average"        / "Trung bình 7 ngày"
"trend.daily"           → "Daily"                / "Theo ngày"
"chart.cancel_by_week"  → "Cancel Rate by week"  / "Tỷ lệ hủy phòng (Cancel Rate) theo tuần"
"trend.weekend_note"    → "Shaded = weekend"     / "Vùng mờ = cuối tuần"
```

### Bước 2 — Helpers trong `trends.py` (đặt trên hàm `draw`)

```python
def _with_ma7(df, col):
    """Thêm cột {col}_ma7 = trung bình trượt 7 ngày (min_periods=1)."""
    out = df.sort_values("business_date").copy()
    out[f"{col}_ma7"] = out[col].rolling(7, min_periods=1).mean()
    return out

def _weekend_bands(df):
    """DataFrame các ngày T7/CN để vẽ dải mờ: cột band_start, band_end (ngày +1)."""
    d = pd.to_datetime(df["business_date"])
    wk = df.loc[d.dt.dayofweek >= 5, ["business_date"]].copy()
    wk["band_start"] = pd.to_datetime(wk["business_date"])
    wk["band_end"] = wk["band_start"] + pd.Timedelta(days=1)
    return wk

def _weekly_cancel(df):
    """Gộp cancellation_rate theo tuần (nhãn = thứ Hai đầu tuần), mean."""
    d = df.copy()
    d["week"] = pd.to_datetime(d["business_date"]).dt.to_period("W-SUN").dt.start_time
    return d.groupby("week", as_index=False)["cancellation_rate"].mean()
```

### Bước 3 — 4 nhánh daily (nhánh `else`, monthly GIỮ NGUYÊN)

**Chung cho chart 1–3 (Doanh thu, OCC, ADR):**
- Lớp 1 (nếu có bands): `mark_rect` dải cuối tuần — `x="band_start:T", x2="band_end:T"`,
  `color="#334155", opacity=0.18`, không tooltip.
- Lớp 2: đường ngày — màu cũ của chart, `strokeWidth=1.5, opacity=0.35`, tooltip ngày+giá trị.
- Lớp 3: đường MA-7 — cùng hue, `strokeWidth=2.5, opacity=1.0`, tooltip ngày+MA.
- Ghi chú dưới chart: `st.caption(t("trend.weekend_note") + " · " + t("trend.ma7") + " = đường đậm")`
  (một dòng caption chung, đặt sau chart OCC là đủ — không lặp 3 lần).

**Chart 1 — Doanh thu ngày** (`rev_src`): bỏ `mark_bar` → 3 lớp trên với `total_revenue`
(+ `_with_ma7(rev_src, "total_revenue")`). Trục y giữ `VND_LABEL_EXPR`.

**Chart 2 — OCC ngày** (`src`): giữ `mark_area opacity=0.15` làm nền, thêm lớp MA-7 đậm
+ dải cuối tuần. Đường ngày hiện có hạ `opacity` 0.35.

**Chart 3 — ADR ngày** (`src`): bỏ `mark_bar` → 3 lớp với `adr`. Ngày `adr=0`
(ngày toàn phòng comp, do coalesce trong kpi_daily_snapshot): thay 0 → NaN trước khi vẽ
(`src["adr"] = src["adr"].replace(0, float("nan"))` TRONG NHÁNH DAILY, trên bản copy —
tránh đường tụt về 0 giả; MA-7 dùng `rolling(...).mean()` mặc định skip NaN).

**Chart 4 — Cancel Rate tuần**: tiêu đề đổi sang `t("chart.cancel_by_week")`;
`_weekly_cancel(src)` → `mark_bar` AMBER như cũ, `x=alt.X("week:T", ...)`, giữ format `%`.

### Bước 4 — Restart + kiểm tra

`docker restart erasopera-dashboard_v2-1` → health `ok`.

## 7. Verification Evidence

Gate G1–G6 trong §9 Validate Contract.

## 8. Resume and Execution Handoff

- **Selected Plan File Path:** `process/general-plans/active/trends-tab-redesign_22-07-26/trends-tab-redesign_PLAN_22-07-26.md`
- **Executor:** AI-Agent ngoài — plan tự chứa, không cần ngữ cảnh hội thoại.
- **Reviewer sau EXECUTE:** orchestrator (Claude) — diff so checklist + probe P1–P4.
- **Open decisions:** không.

## 9. Validate Contract

generated-by: outer-pvl
date: 2026-07-22
Date: 22-07-2026
Gate: PASS

### Khẳng định đã kiểm chứng (orchestrator, 22-07-26)

| # | Khẳng định | Bằng chứng |
|---|---|---|
| 1 | 4 key i18n mới chưa tồn tại | grep 22-07-26 = 0 match |
| 2 | `rolling` chưa dùng trong trends.py | grep = 0 |
| 3 | Chart Doanh thu daily dùng ACTUAL folio (không phải ước tính) | trends.py dòng 53-63 |
| 4 | ADR daily nguồn kpi_daily_snapshot — có ngày adr=0 (8 ngày all-comp, coalesce) | DB query 22-07-26 |
| 5 | Nhánh monthly tách biệt rõ bằng `if by_month:` — sửa nhánh else không chạm monthly | trends.py cấu trúc 70-96, 120-207 |
| 6 | Altair 5.3.0 hỗ trợ mark_rect x/x2 + layer nhiều lớp | requirements.txt |

### Ràng buộc cho agent thực thi (KHÔNG deviation)

1. CHỈ sửa `dashboard_v2/ui/tabs/trends.py` và `dashboard_v2/ui/i18n.py`.
2. Nhánh `by_month` (monthly) của cả 4 chart: KHÔNG đổi một dòng nào.
3. Key i18n thêm vào CẢ HAI dict `en` và `vi`. KHÔNG xoá key cũ (`chart.cancel_by_day`
   giữ lại — dashboard cũ dùng chung pattern).
4. Không thêm dual-axis, không thêm chart mới ngoài danh sách.
5. `replace(0, nan)` cho ADR chỉ áp trong nhánh daily trên bản copy — không đổi df gốc.
6. KHÔNG commit; restart CHỈ container dev `erasopera-dashboard_v2-1`.

### Test Gates (chạy từ repo root)

| Gate | Lệnh | Đạt khi |
|---|---|---|
| G1 Syntax | `python -m py_compile dashboard_v2/ui/tabs/trends.py dashboard_v2/ui/i18n.py` | exit 0 |
| G2 MA-7 có mặt | `grep -c "rolling(7" dashboard_v2/ui/tabs/trends.py` | ≥ 1 |
| G3 Key mới đủ 2 ngôn ngữ | `grep -c '"trend.ma7"' dashboard_v2/ui/i18n.py` (tương tự 3 key còn lại) | mỗi key = 2 |
| G4 Cancel tuần | `grep -c "cancel_by_week" dashboard_v2/ui/tabs/trends.py` | ≥ 1 |
| G5 Monthly nguyên vẹn | `git diff dashboard_v2/ui/tabs/trends.py` — vùng `if by_month:` (các dòng 70-86, 120-133, 153-166, 182-196 bản gốc) không có dòng `-` nào | đúng |
| G6 App chạy sạch | `docker restart erasopera-dashboard_v2-1 && sleep 8 && curl -s http://localhost:8511/_stcore/health` | `ok` |

### Agent-Probe Gates (deferred — orchestrator review sau EXECUTE)

| Gate | Đạt khi |
|---|---|
| P1 | Bản ngày: Doanh thu + ADR là đường (mờ) + MA-7 (đậm), không còn cột |
| P2 | OCC có dải mờ cuối tuần đúng vị trí T7/CN; caption chú thích hiện |
| P3 | Chart 4 tiêu đề "theo tuần", ~13 cột thay vì ~90 |
| P4 | Bản tháng: giống hệt trước (so screenshot) |

### Accepted Concerns (known-gaps)

- ADR daily vẫn từ nguồn ước tính trong khi Doanh thu daily là số thực — đồng bộ nguồn là
  backlog riêng (không chặn).
- MA-7 tuần đầu tiên tính trên <7 ngày (`min_periods=1`) — dốc đầu chuỗi hơi nhạy, chấp nhận.
- Chart OCC-theo-thứ: backlog, chờ user duyệt.
