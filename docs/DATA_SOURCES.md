# Nguồn dữ liệu và quy trình kiểm tra

Nguồn gốc: Binance Public Data, https://data.binance.vision/ . Tài liệu nhà cung cấp: https://github.com/binance/binance-public-data .

Sử dụng đúng BTCUSDT, ZECUSDT và XAUUSDT thuộc USD-M perpetual futures, không thay XAUUSDT bằng XAUUSD hoặc token vàng. Kho public S3 được liệt kê trước khi tải để tìm toàn bộ tháng hiện có. Các ngày chưa có tháng tương ứng được bổ sung bằng kho daily. Mốc cắt cố định 2026-11-20 UTC; không dùng nến của ngày chưa kết thúc.

CSV gốc được giữ trong ZIP, cùng CHECKSUM do nhà cung cấp công bố. Mỗi tệp phải khớp SHA256 trước khi được đọc. Tải lại tiếp tục từ cache đã xác minh. Manifest chứa URL, đường dẫn tương đối, SHA256, ngày tải và số nến từng tệp. Dữ liệu được chuẩn hóa về UTC nhưng vẫn giữ source_timestamp và symbol.

Validation loại giá không dương, volume âm, số không hữu hạn, timestamp sai và cấu trúc OHLC không hợp lệ. Timestamp trùng được giữ bản đầu, đồng thời đếm riêng số trùng và xung đột OHLCV. Dữ liệu thiếu không được nội suy; segment_id tăng sau mỗi khoảng trống. Completeness = số nến hợp lệ / (số nến hợp lệ + nến thiếu giữa đầu-cuối quan sát). Phần trước ngày niêm yết không được coi là thiếu.

M1 được tải theo ngày UTC khi cần điều tra nến M5 chạm cả hai mức. M1 có OHLC vẫn không cho biết thứ tự giá bên trong một phút; phải tiếp tục giữ ambiguous nếu không xác định được. Mỗi tệp M1 có manifest riêng tại data/manifests/m1/.

Hạn chế: một sàn, sản phẩm perpetual; volume không đồng nghĩa thanh khoản thực thi. Không có bid/ask, funding, hàng đợi lệnh hay ticks. Nhà cung cấp có thể sửa archive; SHA256 và bản gốc đóng băng dữ liệu của lần nghiên cứu này. Kho archive có thể bắt đầu sau ngày niêm yết thực tế; báo cáo dùng khoảng thời gian thực sự tải được.

XAUUSDT: archive chứa ngày trước mốc phổ biến cho toàn bộ thị trường đủ điều kiện 2026-01-05, được thông báo tại https://www.binance.com/en/support/announcement/detail/ecf7318c0d434c339e80878588e700d0 . Giữ dữ liệu trước mốc trong raw/processed để truy xuất nguồn nhưng loại khỏi nghiên cứu chính; 00:00 UTC là quy ước theo ngày vì chưa xác minh giờ chính xác.

Số `missing_candles` và completeness dùng lưới UTC 24/7, không tự động coi mọi khoảng trống là lỗi nhà cung cấp. Đặc biệt lịch giao dịch XAUUSDT có thể có kỳ nghỉ/giờ bảo trì. Thông báo Binance về thay đổi sang 24/5 từ 2026-09-15 21:00 UTC: https://www.binance.com/en-NG/square/post/09-15-2026-binance-to-move-commodity-based-tradfi-perpetual-contracts-to-24-5-trading-366786094157850 . Bộ kiểm tra hiện chưa tái dựng đầy đủ lịch phiên chính thức theo từng thời kỳ.
