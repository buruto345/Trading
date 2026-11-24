# Kết quả nghiên cứu HA–EMA M1

Chưa thể kiểm chứng tuyên bố 75%; chưa có định nghĩa đủ để nhận diện và gán outcome.

Tổng nến M1 hợp lệ: 7,701,594.

- Thị trường: BTCUSDT; Nến hợp lệ: 3627360; Nến nghiên cứu: 3627360; Đủ warm-up: 3626861; Phút thiếu nội bộ: 0; Completeness nội bộ: 1.0; Đầu UTC: 2019-12-31T00:00:00+00:00; Cuối UTC: 2026-11-22T23:59:00+00:00; Phút thiếu đến cutoff: 1440
- Thị trường: ZECUSDT; Nến hợp lệ: 3575039; Nến nghiên cứu: 3575039; Đủ warm-up: 3574540; Phút thiếu nội bộ: 0; Completeness nội bộ: 1.0; Đầu UTC: 2020-02-05T08:01:00+00:00; Cuối UTC: 2026-11-22T23:59:00+00:00; Phút thiếu đến cutoff: 1440
- Thị trường: XAUUSDT; Nến hợp lệ: 499195; Nến nghiên cứu: 463680; Đủ warm-up: 463181; Phút thiếu nội bộ: 0; Completeness nội bộ: 1.0; Đầu UTC: 2025-12-11T08:05:00+00:00; Cuối UTC: 2026-11-22T23:59:00+00:00; Phút thiếu đến cutoff: 1440

Đã kiểm định OHLC/UTC/duplicate/gap và checksum; đã triển khai HA/EMA nhân quả.
212 tests; 0 failures; 0 errors.
Kết quả unit/integration tests, audit và browser QA nằm cạnh báo cáo này.
Không có Forex; XAUUSDT perpetual không đại diện vàng giao ngay. Calendar đóng cửa chưa xác minh.
Cỡ mẫu tín hiệu, số quan sát độc lập, observed win proportion, CI và p-value: chưa xác định.
Các định nghĩa còn thiếu: minimum_pullback_candles, minimum_impulse_candles, pullback_color_continuity, maximum_doji_body_ratio, doji_wick_ratio, intermediate_characteristics, maximum_intermediate_candles, entry_price, stop_loss, outcome_labeling.
Không tối ưu tham số để khớp 75%. Không dùng HA làm giá thực thi; không có lệnh thật.
Cần protocol outcome và dependence đầy đủ trước nghiên cứu thắng/thua tiếp theo.
Nguồn dữ liệu: Binance Vision; dữ liệu/phân tích phái sinh theo CC BY-NC-SA 4.0.
