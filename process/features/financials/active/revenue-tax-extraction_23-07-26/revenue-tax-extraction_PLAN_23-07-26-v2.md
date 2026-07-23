# Kế hoạch xử lý bóc tách Thuế & Phí phục vụ (CẬP NHẬT CUỐI)

**Kết luận nhanh**: KHÔNG CẦN CHỈNH SỬA LOGIC. Hệ thống hiện tại đã hoạt động chính xác đúng như yêu cầu của người dùng.

## Phân tích Dữ liệu thực tế & Yêu cầu của người dùng
1. **Dữ liệu Opera đã bóc tách sẵn**: Qua kiểm tra database, các giao dịch doanh thu gốc (Phòng, FnB...) từ Opera trả về **đã là số Net (chưa bao gồm Thuế/Phí)**. Thuế (VAT) và Phí phục vụ (SC) được Opera tự sinh ra thành các dòng giao dịch hoàn toàn tách biệt.
2. **Yêu cầu của người dùng**: Người dùng xác nhận **không muốn tự chia thuế (1.134)**, và **muốn giữ lại Service Charge trên Dashboard, chỉ loại bỏ Thuế (VAT)**.

## Đánh giá code Dashboard hiện tại
Tin vui là mã nguồn SQL hiện tại của Dashboard đang làm **chính xác 100%** điều này:
- Câu SQL `REVENUE_ACTUAL_KPI_SQL` (tính Tổng Doanh Thu) đang có sẵn điều kiện: `AND revenue_category NOT IN ('Tax')`.
- Câu SQL `REVENUE_BREAKDOWN_SQL` (phân bổ doanh thu) đang có sẵn điều kiện: `and revenue_category not in ('Tax')`.
- Code Python vẽ biểu đồ (donut chart và line chart) cũng đang có sẵn đoạn lọc: `df_chart = df_actual[~df_actual["revenue_category"].isin(["Tax"])]`.

**Kết quả**: Doanh thu đang hiển thị trên Dashboard chính là `Net Revenue + Service Charge`. Đây chuẩn xác là "Doanh thu không bao gồm thuế nhưng vẫn giữ lại phí phục vụ" theo đúng chuẩn ngành khách sạn và đúng ý muốn của người dùng.

## Quyết định (Decision)
- **Hủy bỏ hoàn toàn Hướng 1** (Tự chia 1.134) vì sai bản chất dữ liệu.
- **Không áp dụng Hướng 2** (Loại trừ thêm ServiceCharge) vì người dùng muốn giữ lại Service Charge.
- **Hành động**: Đóng kế hoạch này lại (Close out plan) mà không cần thực hiện bất kỳ thay đổi nào (Zero code changes required), hệ thống hiện tại đã chính xác.

## User Review Required
> [!IMPORTANT]
> **Xác nhận Đóng Kế hoạch:**
> Dựa trên xác nhận của bạn ("vẫn muốn giữ Service Charge, chỉ bỏ Thuế"), tôi xin báo cáo rằng **code hiện tại của Dashboard ĐÃ VÀ ĐANG LÀM CHÍNH XÁC ĐIỀU NÀY**.
> Toàn bộ các câu query SQL và code vẽ biểu đồ hiện tại đều đang chỉ loại trừ duy nhất hạng mục `Tax`, giữ nguyên `Room`, `FnB` (đã là số Net) và cộng thêm `ServiceCharge`.
> 
> Vì vậy, chúng ta **không cần phải sửa bất cứ dòng code SQL nào nữa**. Kế hoạch bóc tách thuế này có thể được xem là đã hoàn thành/không cần thiết.
> 
> Bạn có đồng ý **hủy/đóng** kế hoạch này và chuyển sang các công việc khác (như dò tìm dữ liệu Group Revenue bị thiếu) không? 
