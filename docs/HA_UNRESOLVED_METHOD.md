# Những định nghĩa chưa xác định

## Trạng thái hiện hành sau đặc tả D01–D05

Đã xác nhận: không minimum impulse, pullback tối thiểu hai clean candles liên
tiếp, intermediate ngược màu xu hướng được có wick, không giới hạn số nến
pullback/intermediate hoặc observation period; range Doji > ít nhất một trong
hai range trước. Không hỏi lại các mục đã xác nhận này.

Chưa xác định chính xác: body/range **của tác giả** (5 thresholds là nghiên cứu),
tỷ lệ wick nếu có, mốc close/biên wick cụ thể và đường giá HA hay market dùng
để chấm outcome trong video. Tình huống intermediate ngược màu cũng có hình
Doji cần precedence được ghi rõ; H1 dùng invalidation trước theo quy tắc cũ.
Không xác minh fills/chi phí/independence của tác giả.

Run mới H1 là giả thuyết tường minh tại `HA_DOJI_VARIANTS_PROTOCOL.md`: mốc HA
Close, wick HA đối hướng làm biên bất lợi, favorable 1R đối xứng, chạm biên trên
OHLC thật sau Doji. Không coi giá HA là fill. Ba ambiguity scenarios là cách
báo cáo được người dùng yêu cầu; unresolved cuối dữ liệu giữ riêng.

## Lịch sử các mục unresolved của nghiên cứu v1/v2

Danh sách dưới và schema legacy `statistics.UNRESOLVED` phục vụ snapshot cũ;
không phải danh sách các mục còn thiếu cho run D01–D05 hiện hành.

Tất cả mục dưới đây có trạng thái **unresolved**; không có giá trị mặc định để
nhận diện mô hình hay tính win rate.

| Mục | Thông tin cần bổ sung |
|---|---|
| minimum_pullback_candles | Số nến pullback tối thiểu |
| minimum_impulse_candles | Số nến impulse tối thiểu |
| pullback_color_continuity | Có bắt buộc liên tục cùng màu không |
| maximum_doji_body_ratio | Ngưỡng thân/range và xử lý range bằng không |
| doji_wick_ratio | Tỷ lệ wick trên/dưới hoặc xác nhận không có điều kiện tỷ lệ |
| intermediate_characteristics | Màu, vị trí, kích thước nến trung gian |
| maximum_intermediate_candles | Số tối đa hoặc xác nhận không giới hạn |
| entry_price | Giá và thời điểm entry trên OHLC thị trường thật |
| stop_loss | Vị trí SL, mức rủi ro, xử lý gap |
| outcome_labeling | Horizon, TP/SL cùng nến, censoring, overlap, chi phí và thắng/thua |
| maximum_observation_period | Thời hạn theo dõi kết quả lịch sử |
| ambiguous_intrabar_handling | Quy tắc khi cùng một nến thật chạm nhiều mức giá |

Đặc tả mới đã xác nhận xét **toàn nến kể cả wick** khi so EMA và wick bị cấm
trong pullback sạch. Cần làm rõ thêm thời điểm bắt đầu impulse, nến HA thân
đúng bằng không có màu nào, và dung sai tick.
Những câu hỏi triển khai này không thay đổi các quy tắc định tính đã xác nhận.

Pipeline tạo đặc trưng, thống kê mô tả và các đoạn cấu trúc quan sát được, không tạo trade/outcome.
Không diễn giải số nến có hai wick thành số Doji hoặc số tín hiệu.
`require_definitions` chặn báo cáo outcome khi thiếu một trong mười hai định nghĩa.
Việc điền chuỗi mô tả chỉ là cổng kiểm tra schema, không phải xác minh nội dung
phương pháp. Chưa triển khai detector hoặc simulator HA vì chưa đủ định nghĩa.

Muốn tiếp tục: lấy định nghĩa có nguồn, đóng băng protocol trước khi xem kết quả,
thêm bộ nhận diện nhân quả và mô phỏng giá thật, xác định censoring và dependence,
kiểm thử rồi mới đánh giá tuyên bố. Không chọn giả định nhằm đạt 75%.
