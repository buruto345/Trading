# Phase 2 — protocol kiểm định độc lập

Đóng băng trước phân tích: `reports/ha_model_validation/baseline.json` ghi commit,
338 hash file, trạng thái workspace và phiên bản thư viện. Không sửa Phase 1.
Quy tắc hiện hành giữ nguyên `HA_DOJI_VARIANTS_PROTOCOL.md`. D01–D05 là lựa chọn
nghiên cứu; H1 và precedence opposite-Doji chưa được tác giả xác minh.

Reference dùng bộ lọc tuyến tính cho HA Open, pandas EWM cho EMA; detector tìm
ngược đoạn ngược màu và cặp clean đầu tiên sau rào cản Doji sai màu. Không gọi
state machine Phase 1. Quét toàn lịch sử; so sánh mọi observation. Outcome kiểm
tra lần lượt từng nến OHLC thật sau Doji, cả full và partition scope.
Sai số chỉ báo cho phép 512 epsilon tương đối (float64); classification phải
khớp chính xác theo tolerance 32 epsilon của đặc tả, không nới ngưỡng detector.

Định trước T09, trước khi xem kết quả subgroup: log-return 60 nến chia cho
standard deviation của 60 log-return một nến (ddof=1) nhân sqrt(60). Score >1:
rising, <-1: falling, còn lại sideways. Volatility là std60; so với quantile
1/3 và 2/3 của 1440 giá trị std60 trước đó (shift1, tối thiểu720). Low <=q1,
high >q2, còn lại medium. Reset theo gap, không vượt qua gap; thiếu lịch sử
ghi unknown. Đây chỉ là nhãn chẩn đoán, không thêm chỉ báo/filter vào model.
Báo cả từng chiều phân loại và tất cả tổ hợp, kể cả nhóm rỗng.

T11 bootstrap độc lập dùng tổng cộng dồn block, cùng seed20261124, 2000 lần,
block7 ngày đối chiếu Phase1; sensitivity định trước1/3/7/14/28 ngày. Calendar
ngày trống nằm trong khoảng ngày xác nhận đầu/cuối của cohort. Ba scenarios
chia sẻ draws. Không tối ưu block hoặc threshold. CI pointwise, không simultaneous.
Subgroup/tháng/quý/năm dùng500 lần, block7 nếu >=30 mẫu và span>=14 ngày;
khác thì không cung cấp block CI. Cả trường hợp đủ ngưỡng vẫn có cảnh báo ít
block (<8) và stationarity. Wilson chỉ là tham chiếu IID, không CI chính.
Temporal tables bao gồm mọi kỳ trong research interval, kể cả kỳ không có mẫu.

Overlap đo interval theo bar [doji+1,end+1), không phải vị thế/fill. Đo cả
overlap với trước và overlap với bất kỳ mẫu khác. Serial correlation resolved
labels ở lag1/5/10/20; bỏ A/U chỉ là diagnostic. So bullish/bearish theo daily
rates trên ngày cả hai có >=5 resolved mẫu; không suy effective independent n.
Các variant có thể không nested hoàn toàn do precedence opposite Doji.

Prefix tests tại 1000/10000/50000 nến mỗi mã cho cả reference và Phase1;
toàn lịch sử được kiểm tra bằng reference độc lập. Ghi coverage, không gọi
sample prefix test là exhaustive proof. Historical normalization được review
riêng; thay đổi dữ liệu nguồn/revisions không phải tương lai hợp lệ cố định.

Holdout tương lai: khóa protocol/config/code/hash trước khi nhận dữ liệu mới;
chọn trước một khoảng lịch chưa từng xem, không sửa model sau xem; giữ warm-up
từ lịch sử trước điểm bắt đầu, không dùng outcome vượt cuối holdout; báo mọi
mã/variant/scenario, khoảng bất định và dữ liệu thiếu. Không có kết quả holdout
mới trong Phase2; không tải dữ liệu hoặc đặt lệnh.

Thiết kế là Extension theo `DESIGN.md`: giữ Cambria/Segoe UI/Consolas, nền
#f4f3ef, panel trắng, ink #182a2b, accent #146f64, negative #b54d45, spacing8px,
radius4/8px, không animation. Audience nghiên cứu, đọc laptop/mobile; variance3,
motion1,density8,assets1,fidelity8. Tập trung số liệu/uncertainty và tables có
scroll nội bộ. Mọi script/font/chart offline; theo ủy quyền thiết kế đã lưu.
