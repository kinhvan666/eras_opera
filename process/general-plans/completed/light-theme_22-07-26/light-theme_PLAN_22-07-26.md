---
name: plan:light-theme
description: "Light theme for dashboard_v2: official dual [theme.light]/[theme.dark] config + one-click header toggle via st._config.set_option workaround; Streamlit settings menu stays hidden."
date: 22-07-26
feature: light-theme
phase: "complete"
status: "completed"
depends_on: process/general-plans/active/trends-tab-redesign_22-07-26/trends-tab-redesign_PLAN_22-07-26.md
---

# Plan: Light theme + nút toggle 1-chạm cho dashboard_v2

**Complexity:** SIMPLE-MEDIUM

## ⚠️ THỨ TỰ BẮT BUỘC

Plan này sửa `ui/tabs/trends.py` — file cũng bị plan `trends-tab-redesign_22-07-26` sửa.
**CHỈ thực thi SAU KHI trends-tab-redesign xong.** Gate tiên quyết G0:
`grep -c "rolling(7" dashboard_v2/ui/tabs/trends.py` ≥ 1. Không đạt → DỪNG,
báo `BLOCKED: depends on trends-tab-redesign`.

## 1. Overview

Thêm light theme với **nút toggle ☀️/🌙 một chạm trong cụm nút header** (cạnh EN/VI/↻/⎋).
Menu Settings của Streamlit **tiếp tục ẩn** (yêu cầu user 22-07-26).

Kiến trúc (đã research tài liệu Streamlit 2025, xem Decision Summary):
- **Widget gốc Streamlit**: khai báo song song `[theme.light]` + `[theme.dark]` trong
  `.streamlit/config.toml` (tính năng chính thức) — Streamlit tự render dropdown/date
  picker/tabs… đúng theo theme đang active, KHÔNG cần đè CSS baseweb thủ công.
- **Toggle 1-chạm**: workaround cộng đồng `st._config.set_option("theme.base", ...)` +
  `st.rerun()` (API riêng tư — đã chấp nhận rủi ro, xem Accepted Concerns).
- **Thành phần tự vẽ** (kpi-card, header, login) đã dùng CSS vars → chỉ cần 1 khối
  override vars khi light.
- **Chart Altair** (SVG không đọc CSS var): palette Python tập trung ở `ui/theme.py`.

## 2. Decision Summary (INNOVATE — user chốt 22-07-26 sau research)

| Quyết định | Chọn | Phương án bị loại + lý do |
|---|---|---|
| Nền tảng theme widget gốc | **Dual `[theme.light]`/`[theme.dark]` chính thức** | ~~Đè CSS baseweb thủ công~~ (bản plan đầu — nặng, dễ vỡ, research cho thấy không cần); ~~ghim 1 theme~~ |
| Cách toggle | **A: nút 1-chạm** dùng `st._config.set_option` + rerun (user chốt: không muốn lộ menu Settings) | ~~B: mở lại menu Settings Streamlit~~ (chính thống, 0 rủi ro nhưng 2 chạm + lộ menu — user bác) |
| Giá trị khởi tạo | Theo OS (`st.context.theme.type`), fallback dark | ~~Cứng dark~~ |
| Lưu lựa chọn | Query param `?theme=` + session | ~~Chỉ session~~ (mất khi F5) |
| Màu chart | Module `ui/theme.py::chart_colors()` | ~~if/else 27 chỗ~~ |
| `executive/` | Không làm — backlog | |

**Rủi ro đã chấp nhận khi chọn A** (user đã được nêu rõ 22-07-26): `st._config` là API
riêng tư — có thể vỡ khi nâng version Streamlit (khi đó fallback về phương án B);
config theme là biến toàn tiến trình — nhiều người online đồng thời khác theme có thể
thấy nháy theme 1 nhịp rerun (dashboard nội bộ ít user đồng thời, chấp nhận).

## 3. Scope

### In Scope

| File | Việc |
|---|---|
| `.streamlit/config.toml` | Chuyển `[theme]` đơn → `[theme.light]` + `[theme.dark]` đầy đủ màu thương hiệu |
| `app.py` | Khởi tạo theme (query param → OS → dark) + cơ chế re-assert mỗi rerun (chống race đa user) + nút toggle trong `hdr_btns` + nạp CSS override khi light |
| `styles/theme.css` | Giữ nguyên bộ dark (mặc định); rà hex viết thẳng → var |
| `styles/theme-light.css` (MỚI, NHỎ) | CHỈ override ~13 CSS vars của thành phần tự vẽ — KHÔNG đè widget Streamlit |
| `ui/theme.py` (MỚI) | `current_theme()` + `chart_colors()` |
| `ui/tabs/{trends,revenue,segments,pacing}.py` | 27 hex hardcode → `chart_colors()` |
| `ui/components.py`, `auth/session.py` | 4 hex còn sót → CSS var |
| `ui/i18n.py` | key `header.theme_title` ×2 ngôn ngữ |

### Out of Scope

- KHÔNG mở lại menu/Settings/toolbar Streamlit (CSS ẩn giữ nguyên).
- `executive/`, `dashboard/` cũ (backlog).
- Đổi bố cục/logic/encode chart — chỉ nguồn màu + toggle.

## 4. Blast Radius

9 file (2 mới), 1 package. Thuần trình bày; rollback = revert. Rủi ro chính: hành vi
`st._config.set_option` với dual-theme config là tổ hợp CHƯA kiểm chứng → Bước 0 probe
bắt buộc trước khi triển khai đại trà.

## 5. Implementation Checklist

### Bước 0 — PROBE khả thi (BẮT BUỘC làm trước, ~10 phút)

Tạo file tạm `probe_theme.py` cạnh app.py:

```python
import streamlit as st
st.write("context theme:", st.context.theme.type)
if st.button("toggle"):
    cur = st.context.theme.type or "dark"
    st.config.set_option("theme.base", "light" if cur == "dark" else "dark")
    st.rerun()
st.selectbox("probe", ["a", "b"])  # widget gốc để quan sát đổi theme
st.date_input("date probe")
```

Với config.toml Bước 1 đã áp, chạy `streamlit run probe_theme.py` (cổng bất kỳ), bấm
toggle và xác nhận: (a) widget gốc đổi light/dark ngay sau rerun; (b) `st.context.theme.type`
phản ánh đúng theme mới.
- Nếu `st.config.set_option` không tồn tại → dùng `st._config.set_option` (bản cũ hơn).
- Nếu set `theme.base` KHÔNG flip được khi có `[theme.light]/[theme.dark]` → fallback
  đã duyệt: giữ config.toml TỐI GIẢN (không dual section) và set TOÀN BỘ key màu qua
  `set_option` cho từng theme (danh sách key = 2 bảng màu ở Bước 1).
- Ghi kết quả probe (đường nào chạy) vào báo cáo. Xoá `probe_theme.py` sau khi xong.

### Bước 1 — `.streamlit/config.toml`

Thay khối `[theme]` hiện tại bằng:

```toml
[theme.dark]
primaryColor = "#3B82F6"
backgroundColor = "#020617"
secondaryBackgroundColor = "#0E1223"
textColor = "#F8FAFC"
font = "sans serif"

[theme.light]
primaryColor = "#2563EB"
backgroundColor = "#F8FAFC"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#0F172A"
font = "sans serif"
```

GIỮ nguyên các section `[browser]`, `[client]`, `[server]`. (Nếu probe Bước 0 rẽ nhánh
fallback thì áp cấu hình theo nhánh đó.)

### Bước 2 — `ui/theme.py` (MỚI)

```python
import streamlit as st

_DARK = {
    "primary": "#1D4ED8", "accent": "#3B82F6", "warn": "#F59E0B",
    "gray": "#ADB5BD", "text_label": "#E2E8F0", "band": "#334155",
    "positive": "#34D399", "negative": "#F87171",
}
_LIGHT = {
    "primary": "#2563EB", "accent": "#3B82F6", "warn": "#D97706",
    "gray": "#94A3B8", "text_label": "#334155", "band": "#CBD5E1",
    "positive": "#059669", "negative": "#DC2626",
}

def current_theme() -> str:
    return st.session_state.get("ui_theme", "dark")

def chart_colors() -> dict:
    return _LIGHT if current_theme() == "light" else _DARK
```

### Bước 3 — `app.py`

1. **Khởi tạo + re-assert** (sau login, TRƯỚC khi nạp CSS):

```python
from ui.theme import current_theme

def _apply_theme(mode: str):
    # probe Bước 0 quyết định set_option nào; mặc định:
    st.config.set_option("theme.base", mode)

if "ui_theme" not in st.session_state:
    qp = st.query_params.get("theme")
    if qp in ("light", "dark"):
        st.session_state["ui_theme"] = qp
    else:
        try:
            st.session_state["ui_theme"] = st.context.theme.type or "dark"
        except Exception:
            st.session_state["ui_theme"] = "dark"

# Re-assert mỗi rerun (chống race đa user), tối đa 1 lần rerun sửa lệch mỗi phiên
try:
    _rendered = st.context.theme.type
except Exception:
    _rendered = None
if _rendered and _rendered != st.session_state["ui_theme"] \
        and not st.session_state.get("_theme_rerun_once"):
    st.session_state["_theme_rerun_once"] = True
    _apply_theme(st.session_state["ui_theme"])
    st.rerun()
st.session_state.pop("_theme_rerun_once", None)
```

2. **Nạp CSS** (thay khối dòng ~55-56):

```python
css = (Path(__file__).parent / "styles" / "theme.css").read_text()
if st.session_state["ui_theme"] == "light":
    css += (Path(__file__).parent / "styles" / "theme-light.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
```

3. **Nút toggle** trong container `hdr_btns` (sau nút ⎋):

```python
_icon = "☀️" if st.session_state["ui_theme"] == "dark" else "🌙"
if st.button(_icon, key="hdr_theme", type="secondary", help=t("header.theme_title")):
    new = "light" if st.session_state["ui_theme"] == "dark" else "dark"
    st.session_state["ui_theme"] = new
    st.query_params["theme"] = new
    _apply_theme(new)
    st.rerun()
```

### Bước 4 — `styles/theme-light.css` (MỚI — chỉ override vars, KHÔNG selector baseweb)

```css
:root {
  --bg-primary: #F8FAFC;  --bg-card: #FFFFFF;
  --text-primary: #0F172A; --text-secondary: #475569;
  --accent-blue: #2563EB;
  --kpi-positive: #059669; --kpi-negative: #DC2626; --kpi-neutral: #64748B;
  --badge-estimated-bg: #D97706; --badge-estimated-text: #FFFFFF;
  --border: #E2E8F0;
  --title-gradient-from: #0F172A; --title-gradient-to: #2563EB;
}
```

(+ `--title-gradient-from/to` bản dark thêm vào theme.css; nếu soát theme.css thấy rule
dùng hex thẳng cho nền/chữ thì bổ sung override tương ứng vào đây)

### Bước 5 — 4 file tab + components + auth + i18n

- 4 tab: `from ui.theme import chart_colors`; `C = chart_colors()` đầu `draw()`; thay
  hằng `BLUE`/`AMBER`/`GRAY`/hex nhãn/dải cuối tuần → `C[...]`; xoá hằng không dùng.
  KHÔNG đổi encode/logic.
- `ui/components.py`: 2 hex delta → `var(--kpi-positive)/var(--kpi-negative)`.
- `auth/session.py`: 2 hex → var (login trước login-session: theme theo OS do Streamlit
  tự xử lý — chấp nhận).
- `ui/i18n.py`: `"header.theme_title"` → "Toggle light/dark theme" / "Đổi giao diện sáng/tối"
  (cả `en` lẫn `vi`).

### Bước 6 — Restart + tự kiểm

Restart `erasopera-dashboard_v2-1`; toggle qua lại nhiều lần; soát 4 tab + login ở cả
2 theme; F5 giữ theme.

## 6. Resume and Execution Handoff

- **Plan path:** `process/general-plans/active/light-theme_22-07-26/light-theme_PLAN_22-07-26.md`
- **Executor:** AI-Agent ngoài. Tiên quyết G0 (trends-tab-redesign xong).
- **Reviewer:** orchestrator (Claude) — probe P1–P5 bằng browser, bấm toggle thật.
- **Open decisions:** không — mọi nhánh rẽ đều có fallback đã duyệt (Bước 0).

## 7. Validate Contract

generated-by: outer-pvl
date: 2026-07-22
Date: 22-07-2026
Gate: PASS

### Khẳng định đã kiểm chứng (orchestrator, 22-07-26)

| # | Khẳng định | Bằng chứng |
|---|---|---|
| 1 | Streamlit hỗ trợ dual `[theme.light]`/`[theme.dark]` chính thức | docs.streamlit.io/develop/concepts/configuration/theming (research 22-07-26) |
| 2 | Chưa có API chính thức đổi theme runtime; workaround set_option+rerun được cộng đồng dùng rộng | GitHub issue #14172 (open); discuss.streamlit.io #56842, #83937 |
| 3 | Tổ hợp set_option × dual-theme CHƯA kiểm chứng → Bước 0 probe bắt buộc + fallback | ghi nhận rủi ro có kiểm soát |
| 4 | 27 hex trong 4 tab; 1 app.py; 2 components.py; 2 auth/session.py | grep 22-07-26 |
| 5 | Container `hdr_btns` tồn tại; `st.context.theme.type`, `st.query_params` khả dụng (1.54) | app.py + API 1.46+/1.30+ |
| 6 | Chart SVG không đọc CSS var → palette Python | hạn chế Vega-Lite |

### Ràng buộc cho agent thực thi (KHÔNG deviation)

1. Bước 0 probe BẮT BUỘC chạy trước Bước 2-6; kết quả probe (nhánh nào) phải có trong báo cáo.
2. CHỈ sửa/tạo file trong §3 In-Scope. Menu/toolbar Streamlit tiếp tục ẨN.
3. Dark mode giữ NGUYÊN diện mạo hiện tại (mọi hex dark như cũ).
4. KHÔNG đổi logic/encode/data chart. KHÔNG đụng `executive/`, `dashboard/` cũ.
5. KHÔNG commit; chỉ restart container dev `erasopera-dashboard_v2-1`. Xoá `probe_theme.py` trước khi báo xong.

### Test Gates

| Gate | Lệnh (từ repo root) | Đạt khi |
|---|---|---|
| G0 Tiên quyết | `grep -c "rolling(7" dashboard_v2/ui/tabs/trends.py` | ≥ 1 |
| G1 Syntax | `python -m py_compile` cho 9 file Python touched | exit 0 |
| G2 Hết hex trong tabs | `grep -rn '#[0-9A-Fa-f]\{6\}' dashboard_v2/ui/tabs/ --include='*.py'` | 0 match |
| G3 Palette + toggle | `grep -c "chart_colors" dashboard_v2/ui/theme.py` ≥ 2; mỗi tab ≥ 1; `grep -c "hdr_theme" dashboard_v2/app.py` = 1 | đúng |
| G4 Dual theme config | `grep -c "theme.light\|theme.dark" dashboard_v2/.streamlit/config.toml` | ≥ 2 (hoặc nhánh fallback: ghi rõ trong báo cáo) |
| G5 Light CSS chỉ vars | `grep -c "baseweb" dashboard_v2/styles/theme-light.css` | 0 |
| G6 Key i18n | `grep -c '"header.theme_title"' dashboard_v2/ui/i18n.py` | 2 |
| G7 Probe file đã xoá | `ls dashboard_v2/probe_theme.py` | not found |
| G8 App chạy sạch | restart + `curl -s http://localhost:8511/_stcore/health` | `ok` |

### Agent-Probe Gates (deferred — orchestrator review sau EXECUTE)

| Gate | Đạt khi |
|---|---|
| P1 | Dark: giống hệt trước plan (so screenshot) |
| P2 | Bấm ☀️ → light: widget gốc (dropdown, date picker, tabs, radio) VÀ kpi-card/chart đều sáng đồng bộ |
| P3 | Light: 4 tab chart palette light, nhãn đọc được; popup date picker sáng |
| P4 | Toggle qua lại nhiều lần ổn; F5 giữ theme (query param) |
| P5 | Menu Settings/toolbar Streamlit vẫn ẩn ở cả 2 theme |

### Accepted Concerns (known-gaps)

- `st.config.set_option`/`st._config` là API riêng tư: nâng version Streamlit có thể vỡ —
  khi đó chuyển phương án B (mở menu Settings) đã được thảo luận. Ghi chú này nằm luôn
  trong code comment tại `_apply_theme`.
- Config theme toàn tiến trình: nhiều user đồng thời khác theme có thể thấy nháy 1 nhịp
  rerun khi load — chấp nhận (nội bộ, ít user; cơ chế re-assert giới hạn 1 rerun/phiên).
- Login page theo OS (chưa có toggle trước đăng nhập) — chấp nhận.
- `executive/` dark-only — backlog.
