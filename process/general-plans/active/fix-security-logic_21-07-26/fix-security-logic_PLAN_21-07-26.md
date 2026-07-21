# KẾ HOẠCH: Vá Lỗ Hổng Bảo Mật và Cải Thiện Logic

- **Ngày:** 21-07-26
- **Trạng thái:** Mới
- **Người thực hiện:** Claude Code

## Tóm tắt (TL;DR)

Kế hoạch này vạch ra các bước để khắc phục các lỗ hổng bảo mật (SQL injection, lộ bí mật, dependency cũ) và các vấn đề logic (dữ liệu trùng lặp, xử lý lỗi) đã được phát hiện trong quá trình review mã nguồn. Các nhiệm vụ được sắp xếp theo mức độ ưu tiên, bắt đầu từ các rủi ro cao nhất.

---

## 1. Khắc phục các lỗ hổng bảo mật

### 1.1. Sửa lỗi SQL Injection (Ưu tiên: **Cao**)

-   **Vấn đề:** Các tệp `extractor/probe_ar_invoices.py` và `extractor/probe_ar_invoices2.py` sử dụng f-string để xây dựng truy vấn SQL, tạo ra lỗ hổng SQL injection nghiêm trọng.
-   **Giải pháp:**
    1.  Đọc nội dung của `extractor/probe_ar_invoices.py` và `extractor/probe_ar_invoices2.py`.
    2.  Chỉnh sửa các tệp này để sử dụng truy vấn được tham số hóa (parameterized queries) của `psycopg2`. Thay vì chèn biến `tx_list` trực tiếp, sẽ sử dụng `IN %s` và truyền danh sách dưới dạng một tuple.
-   **Kiểm chứng:** Đảm bảo các script vẫn hoạt động sau khi thay đổi bằng cách chạy thử (nếu có thể) hoặc kiểm tra cú pháp.

### 1.2. Loại bỏ mật khẩu Hardcoded (Ưu tiên: **Trung bình**)

-   **Vấn đề:** Mật khẩu được ghi trực tiếp trong `query_db.py` và `eras_dbt/profiles.yml`.
-   **Giải pháp:**
    1.  **Đối với `query_db.py`:** Chỉnh sửa tệp để đọc thông tin kết nối CSDL từ các biến môi trường, tương tự như cách `extractor/src/config.py` đang làm.
    2.  **Đối với `eras_dbt/profiles.yml`:** Đây là tệp cấu hình mẫu. Chỉnh sửa tệp này để xóa mật khẩu và thêm một ghi chú rõ ràng hướng dẫn người dùng cấu hình mật khẩu trong tệp `.user.yml` (đã được `.gitignore` bỏ qua).
-   **Kiểm chứng:** Việc thay đổi này chủ yếu là để tăng cường bảo mật và thực hành tốt, không ảnh hưởng đến chức năng nếu biến môi trường được thiết lập đúng.

### 1.3. Nâng cấp các gói phụ thuộc có lỗ hổng (Ưu tiên: **Thấp**)

-   **Vấn đề:** `dashboard` và `dashboard_v2` sử dụng các phiên bản cũ của `streamlit`, `python-dotenv`, và `pillow` có chứa các lỗ hổng đã biết.
-   **Giải pháp:**
    1.  Đọc các tệp `dashboard/requirements.txt` và `dashboard_v2/requirements.txt`.
    2.  Chỉnh sửa các tệp này, nâng cấp phiên bản của các gói lên phiên bản an toàn được `pip-audit` đề xuất:
        *   `streamlit` -> `1.54.0` (hoặc mới hơn)
        *   `python-dotenv` -> `1.2.2` (hoặc mới hơn)
        *   Cập nhật `streamlit` có thể sẽ tự động kéo theo phiên bản `pillow` mới hơn.
    3.  Sau khi cập nhật, cần chạy lại dashboard để đảm bảo không có thay đổi nào gây lỗi (breaking changes).
-   **Kiểm chứng:** Chạy `pip-audit` lại trên các tệp `requirements.txt` đã cập nhật. Khởi động `dashboard` và `dashboard_v2` để kiểm tra giao diện và chức năng cơ bản.

---

## 2. Cải thiện Logic và Tính đúng đắn

### 2.1. Xử lý trùng lặp dữ liệu đặt phòng

-   **Vấn đề:** `extractor/src/main.py` lấy dữ liệu đặt phòng từ hai nguồn (`historical` và `active`) có thể bị trùng lặp, gây ra việc xử lý dữ liệu không hiệu quả.
-   **Giải pháp:**
    1.  Đọc `extractor/src/main.py`.
    2.  Áp dụng logic để loại bỏ các bản ghi trùng lặp trong bộ nhớ trước khi gửi đến CSDL. Sử dụng `set` của `confirmationId` từ danh sách `historical` để lọc danh sách `active`.
-   **Kiểm chứng:** Logic mới sẽ được kiểm tra bằng cách so sánh số lượng bản ghi trước và sau khi loại bỏ trùng lặp.

### 2.2. Cải thiện xử lý lỗi và tài nguyên

-   **Vấn đề:** Việc khởi tạo `Database` và `BaseOperaClient` trong `extractor/src/main.py` nằm ngoài khối `try...except` chính.
-   **Giải pháp:**
    1.  Đọc `extractor/src/main.py`.
    2.  Tái cấu trúc hàm `main` để đưa việc khởi tạo các đối tượng `db` và `client` vào bên trong khối `try...except`, đảm bảo mọi lỗi trong quá trình khởi tạo đều được bắt và xử lý một cách nhất quán.
-   **Kiểm chứng:** Việc thay đổi này giúp mã nguồn mạnh mẽ hơn, không có thay đổi về chức năng.

---

## Touchpoints

-   `extractor/src/main.py`
-   `extractor/probe_ar_invoices.py`
-   `extractor/probe_ar_invoices2.py`
-   `query_db.py`
-   `eras_dbt/profiles.yml`
-   `dashboard/requirements.txt`
-   `dashboard_v2/requirements.txt`

## Public Contracts

-   Không có thay đổi nào ảnh hưởng đến các hợp đồng công khai (API, etc.). Các thay đổi chủ yếu là nội bộ và để cải thiện bảo mật, chất lượng mã nguồn.

## Blast Radius

-   **Thấp.** Các thay đổi tập trung vào việc vá lỗi và cải thiện logic nội bộ. Việc nâng cấp `streamlit` có rủi ro thấp về breaking changes nhưng cần được kiểm tra thủ công.

## Verification Evidence

| Gate / Scenario | Strategy | Proves SPEC criterion |
|---|---|---|
| Chạy lại `pip-audit` trên các `requirements.txt` đã cập nhật. | Fully-Automated | Các lỗ hổng dependency đã được vá. |
| Chạy lại `grep` để tìm mật khẩu hardcoded. | Fully-Automated | Các bí mật đã được loại bỏ khỏi mã nguồn. |
| Khởi động `dashboard` và `dashboard_v2` và kiểm tra giao diện. | Manual | Nâng cấp `streamlit` không làm hỏng giao diện người dùng. |
| Chạy `extractor` sau khi sửa lỗi logic. | Manual | Extractor vẫn hoạt động chính xác và xử lý trùng lặp đúng. |
| Rà soát mã nguồn các file đã sửa SQLi. | Manual | Lỗi SQL Injection đã được khắc phục bằng parameterized queries. |

## Test Infra Improvement Notes

- (none identified yet)

## Resume and Execution Handoff

1.  **selected plan file path:** `process/general-plans/active/fix-security-logic_21-07-26/fix-security-logic_PLAN_21-07-26.md`
2.  **last completed phase or step:** PLAN (đang tạo kế hoạch)
3.  **validate-contract status:** pending
4.  **supporting context files loaded:** `process/context/all-context.md`, `process/development-protocols/all-development-protocols.md`
5.  **next step:** Sau khi kế hoạch được phê duyệt, chuyển sang chế độ VALIDATE, sau đó là EXECUTE để thực hiện các bước trong kế hoạch.

## Validate Contract

## Validate Contract

- **Ngày xác thực:** 21-07-26
- **Người xác thực:** vc-validate-agent (thông qua Claude Code)
- **Kết quả:** PASS

### Phân tích

Kế hoạch được cấu trúc tốt, giải quyết các vấn đề đã xác định theo thứ tự ưu tiên hợp lý. Rủi ro được đánh giá là thấp và các bước xác minh là đầy đủ.

- **Rủi ro nâng cấp Streamlit:** Đã kiểm tra ghi chú phát hành từ v1.38.0 đến v1.54.0. Không tìm thấy thay đổi lớn nào có khả năng gây lỗi cho các thành phần đang được sử dụng. Rủi ro chính là các thay đổi nhỏ về giao diện, sẽ được kiểm tra thủ công.
- **Các thay đổi khác:** Việc sửa lỗi SQL Injection và loại bỏ bí mật hardcoded là những thay đổi có mục tiêu rõ ràng và rủi ro thấp khi thực hiện đúng cách.

### Hợp đồng thực thi (Execute Contract)

Khi chuyển sang chế độ EXECUTE, người thực thi phải tuân thủ các cổng kiểm tra sau:

**Gate 1: Security Fixes Verification (Tự động)**
-   Chạy lại `pip-audit -r dashboard/requirements.txt` và `pip-audit -r dashboard_v2/requirements.txt`. **Kỳ vọng:** Không tìm thấy lỗ hổng nào cho các gói đã nâng cấp.
-   Chạy `grep -r "password" query_db.py eras_dbt/profiles.yml`. **Kỳ vọng:** Không có kết quả.

**Gate 2: Logic & Functionality Verification (Thủ công & Bán tự động)**
-   Chạy `python extractor/src/main.py` (với các biến môi trường phù hợp). **Kỳ vọng:** Script chạy thành công, log cho thấy logic loại bỏ trùng lặp hoạt động.
-   Chạy `streamlit run dashboard/app.py` và `streamlit run dashboard_v2/app.py`. **Kỳ vọng:** Cả hai ứng dụng khởi động thành công.
-   **Kiểm tra giao diện thủ công:** Mở trình duyệt và xác minh rằng:
    -   Bố cục không bị vỡ.
    -   Các tab (Revenue, Trends, etc.) hiển thị đúng.
    -   Các biểu đồ và bộ lọc hoạt động như trước khi nâng cấp.

**Trạng thái:** Kế hoạch đã sẵn sàng để chuyển sang chế độ `EXECUTE` sau khi được phê duyệt.

