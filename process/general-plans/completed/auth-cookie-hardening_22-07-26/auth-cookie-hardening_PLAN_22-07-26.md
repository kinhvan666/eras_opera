---
name: plan:auth-cookie-hardening
description: "Security & Auth Hardening: Remove session_token from URL, implement cookie-based persistence (extra-streamlit-components), add expired session cleanup, and update admin password."
date: 22-07-26
feature: auth-cookie-hardening
phase: "complete"
status: "completed"
---

# Plan: Củng cố Bảo mật Đăng nhập (Auth & Cookie Hardening) — dashboard_v2

**Complexity:** MEDIUM (High-Risk Class: Security & Authentication)

## 1. Overview

Rà soát cơ chế xác thực hiện tại cho thấy 2 rủi ro bảo mật quan trọng:
1. **Lộ Token trên URL (`?session_token=...`)**: Token phiên đăng nhập hiện nằm trên thanh địa chỉ trình duyệt nhằm duy trì trạng thái khi F5. Hậu quả: Dễ bị rò rỉ khi sếp/nhân viên copy link gửi cho nhau (người nhận vào thẳng bằng tài khoản người gửi mà không cần mật khẩu), bị lưu trong Lịch sử trình duyệt, Nginx access log, và rò rỉ khi họp online / chụp màn hình.
2. **Mật khẩu Admin mặc định chưa đổi**: Cần cung cấp công cụ đổi mật khẩu Admin an toàn và vô hiệu hóa tất cả phiên đăng nhập cũ khi đổi mật khẩu.

## 2. Decision Summary (INNOVATE — 22-07-26)

| Quyết định | Giải pháp | Lý do chọn |
|---|---|---|
| Lưu trữ Token phiên | **Cookie trình duyệt (`extra-streamlit-components`)** | Chuẩn ngành: Token nằm ẩn trong cookie, không hiện trên URL, không rò rỉ khi copy link hay xem lịch sử |
| Xóa Token khỏi URL | **Xóa ngay lập tức (`st.query_params.clear()`)** | Bảo vệ lập tức cả các link cũ còn tồn tại: vừa load xong token là xóa sạch query param trên thanh địa chỉ |
| Thời hạn phiên (TTL) | **Rút xuống 4 giờ** | Tăng tính an toàn tối đa cho hệ thống điều hành doanh nghiệp |
| Đổi mật khẩu Admin | **Thêm hàm CLI/admin reset password + thu hồi phiên** | Đảm bảo xóa sạch các session_token cũ khi mật khẩu bị thay đổi |

## 3. Scope

### In Scope

- `requirements.txt`: Bổ sung `extra-streamlit-components`.
- `dashboard_v2/auth/session.py`: Cập nhật logic `is_logged_in()`, `logout()`, `_attempt_login()` dùng CookieManager và xóa sạch query param `session_token`.
- `dashboard_v2/auth/db.py`: Bổ sung `cleanup_expired_sessions()`, `revoke_all_user_sessions()`, đổi TTL mặc định thành 3 ngày.
- `dashboard_v2/scripts/reset_admin_pass.py` (MỚI): Script CLI đổi mật khẩu Admin an toàn từ terminal.

### Out of Scope

- Không đổi giao diện form login (giữ nguyên trải nghiệm người dùng).
- Không ảnh hưởng đến các tab báo cáo hay dbt.

## 4. Blast Radius

4 file Python/text. Thuần túy lớp Auth & Session. Rủi ro High-Risk Class (Security) $\rightarrow$ Cần kiểm thử kỹ luồng Đăng nhập / F5 / Đăng xuất / Cookie.

## 5. Implementation Checklist

### Bước 1 — Bổ sung thư viện `extra-streamlit-components`

Thêm `extra-streamlit-components` vào `requirements.txt` và cài đặt vào môi trường Python.

### Bước 2 — Cập nhật `dashboard_v2/auth/db.py`

1. Đổi TTL tạo session từ `7 days` $\to$ `3 days` (72h).
2. Thêm hàm `cleanup_expired_sessions()` xóa các dòng `expires_at < NOW()`.
3. Thêm hàm `revoke_all_user_sessions(user_id)` xóa toàn bộ session trong DB của user khi đổi mật khẩu.

### Bước 3 — Cập nhật `dashboard_v2/auth/session.py` (Cookie Integration)

1. Tích hợp `CookieManager` từ `extra-streamlit-components`.
2. Khi đăng nhập thành công:
   - Lưu `session_token` vào cookie `erasopera_session` (với max_age 3 ngày).
   - Xóa ngay lập tức `session_token` khỏi `st.query_params` nếu có.
3. Khi kiểm tra trạng thái (`is_logged_in`):
   - Đọc `session_token` từ Cookie `erasopera_session` (hoặc fallback `st.session_state`).
   - Nếu còn tham số `session_token` trên URL (link cũ), đọc xong lập tức xóa khỏi URL và ghi sang Cookie.
4. Khi Đăng xuất (`logout`):
   - Xóa cookie `erasopera_session`.
   - Xóa session khỏi Database.
   - Clear toàn bộ query params.

### Bước 4 — Tạo script đổi mật khẩu Admin (`dashboard_v2/scripts/reset_admin_pass.py`)

Tạo script CLI cho phép đổi mật khẩu Admin trực tiếp trong terminal, tự động hash mật khẩu bằng bcrypt và thu hồi toàn bộ session cũ.

### Bước 5 — Restart + Kiểm thử toàn bộ luồng Auth

1. Restart container dev `erasopera-dashboard_v2-1`.
2. Kiểm tra F5 giữ đăng nhập không bị hiện token trên URL.
3. Kiểm tra nút Đăng xuất ⎋ hoạt động sạch sẽ.

## 6. Verification Evidence

Xem các Test Gates G1–G6 trong §7 Validate Contract.

## 7. Validate Contract

generated-by: outer-pvl
date: 2026-07-22
Date: 22-07-2026
Gate: PASS

### Ràng buộc thực thi

1. KHÔNG được để lại `?session_token=...` trên URL thanh địa chỉ trình duyệt sau khi đăng nhập/load trang.
2. Token lưu trong Cookie với cờ thời hạn 3 ngày.
3. Nút Đăng xuất bắt buộc xóa cả Cookie lẫn phiên trong Postgres Database.

### Test Gates

| Gate | Lệnh / Thao tác | Đạt khi |
|---|---|---|
| G1 Syntax | `python -m py_compile dashboard_v2/auth/session.py dashboard_v2/auth/db.py` | exit 0 |
| G2 Thư viện Cookie | `python -c "import extra_streamlit_components"` | exit 0 |
| G3 Không còn lưu token lên URL | `grep -c 'st.query_params\["session_token"\] = token' dashboard_v2/auth/session.py` | 0 |
| G4 Dọn session hết hạn | `grep -c "cleanup_expired_sessions" dashboard_v2/auth/db.py` | ≥ 1 |
| G5 Script đổi pass Admin | `python dashboard_v2/scripts/reset_admin_pass.py --help` hoặc syntax check | exit 0 |
| G6 App chạy sạch | Restart container + health check | `ok` |

### Accepted Concerns (known-gaps)

- Khi trình duyệt chặn hoàn toàn 3rd party cookies trong iframe (hiếm gặp): CookieManager sẽ fallback về `st.session_state` trong phiên làm việc.
