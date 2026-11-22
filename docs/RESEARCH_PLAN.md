# Kế hoạch được cố định trước khi xem kết quả

1. Thu thập tất cả monthly M5 có sẵn trong kho Binance USD-M của đúng ba mã; mở rộng daily tới ngày đóng hoàn chỉnh trước 21/11/2026 UTC.
2. Kiểm tra timestamp, OHLCV, duplicate, missing; không nội suy giá. M1 theo ngày cần giải quyết intrabar.
3. Nhận diện tuần tự với max Sweep→MSS 24 nến và mô phỏng 288 nến, RR2, cost10bps round-trip.
4. Chia mỗi instrument theo thứ tự nến 60/20/20; không cho setup/outcome vượt ranh giới. Không shuffle.
5. Nhóm exploratory chỉ dùng in-sample + validation. OOS chỉ đánh giá tổng hợp đã xác định.
6. Wilson 90/95/99, bootstrap block calendar giữ đồng thời giữa instrument, kiểm tra H0 p=1/3 thô, FDR exploratory.
7. Sensitivity max Sweep→MSS 12/48 trên development, không lựa chọn tham số thắng. Cost0/5/10/20bps; không tối ưu để giao dịch.
8. Xuất dữ liệu, báo cáo offline 18 phần, test và kiểm tra trình duyệt.

