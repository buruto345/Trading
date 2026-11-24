# Đánh giá HA–EMA 100 trên ba M1 datasets có sẵn

Ngày cập nhật: 24/11/2026. Dùng lại các artifact đã kiểm định, không tải lại
dữ liệu, không tính lại chỉ báo, không thay mô hình hoặc báo cáo lịch sử.
Đặc tả đầy đủ: `docs/HA_ORIGINAL_METHOD.md`.

## Kết quả riêng từng sản phẩm

| Sản phẩm | M1 hợp lệ đã lưu | Nến dùng nghiên cứu | Đoạn clean theo convention | Win rate gốc | CI win rate |
|---|---:|---:|---:|---|---|
| BTCUSDT | 3.627.360 | 3.627.360 | 325.916 | Chưa xác định | Chưa xác định |
| ZECUSDT | 3.575.039 | 3.575.039 | 315.826 | Chưa xác định | Chưa xác định |
| XAUUSDT | 499.195 | 463.680 | 37.968 | Chưa xác định | Chưa xác định |

Không có nhãn trade win/loss HA đã xác định nên không tồn tại mẫu số thắng/thua
hợp lệ để tính tỷ lệ hoặc CI. Không hiểu null là 0% hoặc 75%. Không thể chấp
nhận/bác bỏ tuyên bố 75% từ số nến, số đoạn clean hoặc giá tăng/giảm sau quan sát.

Đoạn clean liên tiếp và terminal hai wick là các convention mô tả đã công bố,
không phải số lần xuất hiện mẫu Doji gốc hoàn chỉnh. Báo cáo riêng đã có phân
bố body/range/wick, vị trí EMA, lengths, intermediate, năm và IS/validation/OOS.

## Kiểm định và nguồn kết quả được tái sử dụng

- `reports/ha_descriptive/summary.json`: số liệu tách riêng ba mã, không gộp win rate.
- `reports/ha_descriptive/{symbol}.html` và `comparison.html`: báo cáo chi tiết.
- `reports/ha_descriptive/tests.xml`: lần chạy trước 233 tests, 0 failures/errors.
- `reports/ha_descriptive/audit.json`: SQL reconciliation đạt cho ba mã.
- `reports/ha_descriptive/browser_qa.json`: bốn báo cáo kiểm tra offline đạt.
- `reports/ha_descriptive/preservation_verified.json`: 174 file cũ giữ nguyên.
- `supported_metrics.json`: lần rà soát trước kiểm tra hash và tính lại count,
  mean, median, sample standard deviation của markout theo mã/partition/horizon.

Đây là kết quả kiểm thử/phân tích đã có, không tuyên bố đã chạy lại toàn bộ
pipeline trong lần cập nhật tài liệu này. Module chỉ báo và mô phỏng cũ không sửa.

## Chất lượng dữ liệu và giới hạn

Cả ba Parquet kiểm tra trước đó đều không có timestamp trùng, OHLC không hợp
lệ hoặc missing nội bộ. Coverage kết thúc 22/11/2026 23:59 UTC; thiếu 1.440
phút mỗi mã tới cutoff 24/11/2026 00:00 UTC. Không tải bù. Lịch đóng cửa thị
trường chưa xác minh; không coi zero-volume là khả năng thực thi.
XAU trước 05/01/2026 giữ trong dataset gốc nhưng loại khỏi nghiên cứu.

Mẫu chỉ gồm Binance USD-M perpetual, không có Forex hoặc vàng giao ngay.
OOS là dữ liệu hồi cứu đã được dùng trước đây. Quan sát/cửa sổ có thể phụ thuộc;
independent sample size chưa xác định. Không diễn giải phân bố hoặc mean giá
sau quan sát thành hiệu quả giao dịch hay bằng chứng thống kê cho 75%.

## Vì sao chưa có win rate và việc đã hoàn thành

Ngưỡng Doji, minimum/continuity của impulse/pullback, đặc điểm/giới hạn
intermediate, entry, SL, thời hạn quan sát và intrabar vẫn unresolved theo
chính đặc tả mới. Không nhập convention ICT M5 RR 1:2 vào HA M1 RR 1:1.
Không áp bộ giả định đã từng đề xuất khi chưa có protocol thí nghiệm được chọn.

Đã lưu đầy đủ các quy tắc người dùng xác nhận, công thức và phân biệt rõ phần
unresolved. Không yêu cầu người dùng nhắc lại những quy tắc này. Phần đánh giá
định lượng thực hiện được đã có sẵn; kết quả win rate gốc chưa thể nhận dạng
từ phương pháp chưa xác định entry/SL/outcome, dù dữ liệu giá đầy đủ hơn.

## File thay đổi trong lần cập nhật này

- Sửa `docs/HA_ORIGINAL_METHOD.md`: lưu đầy đủ đặc tả mới nhất.
- Sửa `README.md`: dẫn tới đặc tả và kết luận hiện hành.
- Sửa `docs/HA_WIN_RATE_CLARIFICATION_REQUEST.md`: đánh dấu yêu cầu cũ là lịch sử.
- Tạo `reports/ha_win_rate_review/EVALUATION_STATUS.md`: tài liệu này.
