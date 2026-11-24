# Protocol nghiên cứu HA/EMA M1

Đóng băng cấu hình trong `config/ha_ema_research.json` trước thống kê mô tả.
Không thêm thư viện: dùng pandas/numpy/scipy/pyarrow/pytest/Playwright sẵn có.
Chỉ tải lịch sử công khai; không tài khoản, credentials, orders hay live feed.

## Nguồn và phạm vi

Binance Vision USD-M perpetual BTCUSDT, ZECUSDT, XAUUSDT. Tải toàn bộ monthly
M1 đã hoàn tất, bổ sung daily cho các tháng chưa được monthly bao phủ đến trước
24/11/2026 00:00 UTC. Chọn giới hạn ngày hoàn tất, không sử dụng nến trong ngày.
Nguồn: https://github.com/binance/binance-public-data ; schema futures kline
và checksum được kiểm tra ngày 24/11/2026. Dữ liệu gốc không suy từ M5.
Quyền sử dụng: https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md
(bản được đọc: 1.0, 26/08/2026). Phạm vi này là nghiên cứu cá nhân offline,
phi sản xuất, phi thương mại. Ghi công Binance Vision; dữ liệu/phân tích phái sinh
thuộc CC BY-NC-SA 4.0 theo điều khoản nguồn; không thay đổi license code cũ.
Không công bố hoặc tải dữ liệu lên dịch vụ bên ngoài trong nhiệm vụ này.

Ưu tiên archive monthly để giảm request; tối đa 4 worker, retry theo downloader
hiện có, giữ lại ít nhất 3 GB dung lượng trước mỗi download. SHA-256 của ZIP,
checksum provider và Parquet được lưu. Cache checksum cố định phiên bản đã tải;
không tuyên bố cache là revision mới nhất trên server. Manifest ghi lỗi tải.
Nếu pipeline chạy lại với collection thì snapshot có thể thay đổi khi archive
mới xuất hiện; dùng `--skip-collection` để phân tích chính xác snapshot đã lưu.

Đây không phải toàn bộ Forex/Gold/Crypto. Không có Forex; không đổi XAUUSDT
thành XAUUSD. Giữ archive XAU trước 05/01/2026 cho provenance nhưng loại khỏi
nghiên cứu theo convention của repository (ngày mở công khai được lưu trong
manifest M5 cũ). Không tái xác minh giờ mở intraday trong nghiên cứu này.

## Kiểm định và chỉ báo

Kiểm tra OHLC dương hữu hạn, high/low hợp lệ, UTC, minute alignment, thứ tự,
trùng và giá xung đột. Trùng giống nhau giữ một; xung đột cách ly toàn timestamp.
Volume thiếu giữ null và không ảnh hưởng đủ điều kiện; volume âm/vô hạn bị loại.
Các khoảng trống là số phút thiếu trên lưới UTC 24/7 giữa nến đầu/cuối. Không
khẳng định đó là lỗi: XAU có thể có đóng cửa theo lịch; chưa xác minh calendar
lịch sử nên **không** trừ cuối tuần một cách suy đoán. Report liệt kê khoảng
trống, phần thiếu ở đuôi tới cutoff và archive thất bại. Completeness nội bộ
không phải completeness từ ngày listing. Không lấp dữ liệu thiếu.

`input_monotonic` của toàn bộ batch được ghi trước khi sort; thứ tự ghép daily
và monthly có thể không theo thời gian. Mỗi archive cũng có cờ thứ tự riêng
trong manifest để phân biệt lỗi nguồn với thứ tự ghép. Sau validation dữ liệu
được sắp tăng, không trùng. Fixture pytest được lưu dưới
`tests/data/synthetic/.ha_pytest`, tách khỏi dữ liệu lịch sử.

HA Close=(O+H+L+C)/4; HA Open đầu segment=(O+C)/2;
HA Open[t]=(HA Open[t-1]+HA Close[t-1])/2;
HA High=max(H,HA Open,HA Close); HA Low=min(L,HA Open,HA Close).
EMA dùng alpha=2/101, seed HA Close đầu segment, đệ quy adjust=False.
Đây là convention khởi tạo nghiên cứu, chưa biết có khớp platform tác giả không.
Reset cả HA và EMA sau bất kỳ khoảng trống; warm-up 500 nến trong mỗi segment,
ready tại nến thứ 500. Trọng số seed EMA khi đó là (99/101)^499 (~0,00463%).
Không dùng EMA slope. Không làm tròn giá tính toán float64. Thân bằng không
có màu 0; chỉ mô tả, không tự gán bullish/bearish. So sánh wick >0 là thống kê
hình học, chưa phải tiêu chuẩn tick hay ngưỡng Doji.

Ví dụ thủ công trong unit test: ba nến OHLC lần lượt (10,14,8,12),
(12,16,10,14), (14,18,12,16) cho HA Close [11,13,15], HA Open [11,11,12].
EMA span=3 (alpha=0,5, chỉ dùng trong test) cho [11,12,13,5]. Test span=100
đối chiếu độc lập pandas EWM, kiểm tra warm-up thứ 500 và prefix invariance.

Timestamp là giờ mở; OHLC/HA/EMA nến t chỉ sẵn sàng tại t+1 phút. Synthetic
HA chỉ là chỉ báo, tuyệt đối không là giá thực thi. Không feature tương lai.
Không có nhãn outcome nên chưa có mô phỏng RR hoặc entry/SL giả định.

## Chia thời gian và thống kê

Biên calendar cố định chung cho các thị trường: IS trước 01/01/2024,
validation năm 2024, OOS từ 01/01/2025. Gắn partition theo giờ mở nến;
available_at chỉ được sử dụng khi đã đóng. Không reset indicator tại split:
quá khứ IS được phép làm warm-up cho tương lai. XAU không có IS/validation;
báo rõ ô rỗng, không ép chia riêng để tạo dữ liệu huấn luyện.
OOS này là nhãn hồi cứu; dữ liệu thời kỳ tương ứng từng có trong nghiên cứu
M5 nên không gọi là holdout chưa từng xem. Không điều chỉnh tham số theo OOS.

Report mô tả phân bố body/range, wick, màu, vị trí với EMA, warm-up, theo
market/năm/partition. Đây không phải win rate. Cỡ mẫu tín hiệu, independent n,
observed win proportion, CI và kiểm định 75% hiện đều null.

Interface thống kê tương lai nhận nhãn từ bên ngoài và yêu cầu định nghĩa rõ;
giữ ambiguous/unresolved ngoài denominator resolved đồng thời báo bounds trên
toàn mẫu. Wilson là khoảng tham chiếu IID, không tự coi dữ liệu là độc lập.
Số trial độc lập chưa xác định nếu chưa có bằng chứng; không đồng nhất cluster
count hoặc non-overlap với độc lập. Binomial H0 p=0,75 hai phía chỉ được tính
khi có independence rationale tường minh, vẫn cần review bên ngoài.
Trước kết luận phải chọn calendar-block/cluster bootstrap, family kiểm định và
điều chỉnh multiple-testing trong protocol mới. Không suy lợi nhuận từ ý nghĩa
thống kê. Cần xử lý selection bias, phụ thuộc chéo thị trường, look-ahead,
overfitting, chi phí/funding/slippage và censoring xuyên biên split.

## Kiến trúc bổ sung

`src/ha_research/data.py` tái sử dụng downloader và validator, bổ sung volume
optional/quarantine; `indicators.py` chỉ báo và partition; `statistics.py` cổng
định nghĩa và schema outcome; `report.py` báo cáo mô tả độc lập.
`scripts/collect_ha_m1.py` thu thập; `scripts/run_ha_research.py` pipeline offline;
`scripts/qa_ha_research.py` đối chiếu Parquet/JSON và kiểm tra browser offline.
Data: `data/raw/futures/um/*/klines/*/1m`, `data/processed/ha_m1`,
`data/manifests/ha_m1`. Kết quả: `reports/ha_ema`, HTML riêng.
Không sửa các engine ICT hoặc báo cáo cũ. Hash preservation trước/sau kiểm tra
dữ liệu và báo cáo có sẵn. README được nối thêm hướng dẫn, giữ nội dung trước đó.
