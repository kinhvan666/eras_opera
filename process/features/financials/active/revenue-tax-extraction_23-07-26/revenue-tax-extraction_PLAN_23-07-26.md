# Kế hoạch chi tiết xử lý bóc tách Thuế & Phí phục vụ (Hướng 2: Bài bản qua Data Warehouse/DBT)

**Mục tiêu**: Giữ nguyên kiến trúc Dashboard hiện tại (không hardcode hệ số thuế vào mã Dashboard). Thay vào đó, yêu cầu Data Team cập nhật logic tính toán trong DBT (Data Build Tool) để bóc tách Thuế và Phí phục vụ từ nguồn (Opera) ra thành các trường `net_amount`, `tax_amount`, `service_charge_amount` ngay từ tầng Staging và Mart. Qua đó, Dashboard sẽ tự động hiển thị Net Revenue mà không cần thay đổi bất cứ dòng code nào ở Frontend.

## Giả định hệ số (System Assumptions)
Theo tiêu chuẩn kế toán khách sạn tại Việt Nam hiện tại:
- **Phí phục vụ (SC)**: 5%
- **Thuế giá trị gia tăng (VAT)**: 8% (áp dụng từ tháng 7/2023 - 2024 đối với các dịch vụ lưu trú, ăn uống)
- **Công thức quy đổi**: `Net = Gross / 1.134`, `SC = Net * 0.05`, `VAT = Net * 0.08`

## Proposed Changes (Các thay đổi mã nguồn đề xuất)

### 1. File `eras_dbt/models/staging/stg_cashiering_postings.sql`
- **Thêm cột mới**: Bổ sung logic tính toán trực tiếp trong DBT cho 3 cột mới:
  - `net_amount`: Dùng câu lệnh `CASE WHEN revenue_category IN ('Room', 'FnB') THEN posted_amount / 1.134 ELSE posted_amount END`
  - `tax_amount`: Tính tương ứng từ `net_amount`.
  - `service_charge_amount`: Tính tương ứng từ `net_amount`.
- Giữ nguyên cột `posted_amount` như một cột ghi nhận Gross Revenue gốc từ Opera.

### 2. File `eras_dbt/models/marts/fct_...` (Các bảng Fact liên quan)
- Cập nhật các bảng Fact tổng hợp doanh thu (chẳng hạn `fct_reservation_night`, `fct_revenue_daily`) để hàm `SUM()` sử dụng cột `net_amount` thay vì `posted_amount`.
- Bổ sung `SUM(tax_amount)` và `SUM(service_charge_amount)` vào Fact table nếu cần thiết cho báo cáo tài chính chi tiết sau này.

### 3. File Code Dashboard (`dashboard_v2`)
- **[NO CHANGE]**: Dashboard sẽ giữ nguyên 100% logic Gross Revenue hiện tại. Tuy nhiên, do dữ liệu dưới Database đã được chuẩn hóa thành Net Revenue bởi DBT, Dashboard sẽ tự động hiển thị số đúng.

---

## Touchpoints
- `eras_dbt/models/staging/stg_cashiering_postings.sql`
- Các bảng Fact trong `eras_dbt/models/marts/`

## Public Contracts
- Lược đồ CSDL (Schema) của Data Warehouse sẽ có thêm các cột `net_amount`, `tax_amount`, `service_charge_amount`.

## Blast Radius
- Số lượng file ảnh hưởng: Các file model DBT (SQL).
- Rủi ro (Risk Class): Medium. Yêu cầu chạy lại toàn bộ pipeline dbt (`dbt run --full-refresh`) để áp dụng số liệu mới về quá khứ.

## Verification Evidence
| Gate / Scenario | Strategy | Proves SPEC criterion |
|---|---|---|
| Kiểm tra dbt build | Agent-Probe | Lệnh `dbt build` chạy thành công không có lỗi |
| Kiểm tra chênh lệch số tổng | Agent-Probe | Số liệu trong bảng Fact giảm từ Gross xuống Net |
| Đối chiếu với hệ thống Oracle | Manual | Số Net Revenue khớp với Manager Report trên Dashboard |

## Test Infra Improvement Notes
(none identified yet)

## Validate Contract

(placeholder — vc-validate-agent writes this section before EXECUTE)

## Resume and Execution Handoff
- **Selected plan file path**: `process/features/financials/active/revenue-tax-extraction_23-07-26/revenue-tax-extraction_PLAN_23-07-26.md`
- **Last completed phase or step**: PLAN (Plan written and handed off)
- **Validate-contract status**: pending
- **Supporting context files loaded**: `process/context/all-context.md`
- **Next step for a fresh agent**:
  1. Yêu cầu quyền truy cập sửa code trong thư mục `eras_dbt`.
  2. Xin lệnh `ENTER EXECUTE MODE` từ người dùng để bắt đầu chỉnh sửa.

## User Review Required
> [!IMPORTANT]
> **Câu hỏi cần chốt trước khi Execute:**
> 1. Tỷ lệ Thuế VAT và Phí SC (8% và 5%, hệ số chia 1.134) đã hoàn toàn đúng thực tế chưa?
> 2. Có cần phải viết cấu hình dbt seed / macro để thay đổi thuế VAT 8% -> 10% theo từng khoảng thời gian (Effective Dates) hay không? Hay chỉ cần hardcode tỷ lệ 8% cho toàn bộ dữ liệu lịch sử?
