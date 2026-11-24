# Nghiên cứu hình thái M1 theo từng sản phẩm — protocol v2

Chỉ đọc ba M1 Parquet đã lưu và kiểm tra SHA-256 ZIP/Parquet. Không tải lại.
Giữ cutoff và split của cấu hình cũ; XAU trước 05/01/2026 vẫn ở dataset gốc
nhưng ngoài population nghiên cứu. Không thay báo cáo v1 hay mô hình ICT.
Đây là phân tích mô tả, không phải simulator giao dịch hoặc kiểm định win rate.

## Kiểm định và hình học

Revalidate toàn bộ dataset bằng `validate_m1`; xác minh chỉ có đúng symbol,
timestamp tăng, UTC, unique, OHLC dương hữu hạn, gap và completeness. So sánh
với manifest lưu trước đó. Thiếu ở đuôi cutoff được báo riêng; không tải bù
ngày 23/11 trong lần này để giữ snapshot. Lịch đóng cửa lịch sử chưa được xác
minh: không gọi khoảng trống là outage, không coi nến zero-volume là giá có
thể khớp. Không có lịch Forex hoặc vàng giao ngay trong dữ liệu này.

Tái tính HA/EMA bằng module đã kiểm thử, 500 nến warm-up sau đầu dữ liệu/gap.
Body=abs(HA Close−HA Open), range=HA High−HA Low. Range bằng 0 có ratio=null.
Đo cả đơn vị giá và bps so với HA Close để so sánh sản phẩm khác thang giá.

Dung sai số học = 32 × eps(float64) × max(abs(HA OHLC), abs(EMA)). Đây chỉ là
convention chống nhiễu float, không phải tick-size của tác giả. Wick <= tolerance
coi là không wick; wick > tolerance là có wick. Body trong tolerance có màu 0
và không đủ điều kiện màu. Toàn nến trên EMA khi HA Low−EMA > tolerance;
dưới EMA khi EMA−HA High > tolerance. Chạm/gần chạm không thuộc hai vùng.
Lưu cả số lượng wick bằng 0 chính xác để thấy ảnh hưởng dung sai.

Population phân bố: nến đủ warm-up. Phân bố body ratio có riêng cohort hai wick,
và cohort hai wick cùng màu vùng EMA. **Không gọi đây là phân bố Doji đã xác
định**; ngưỡng Doji chưa có. Histogram [0,.05,.1,.2,.3,.5,.75,1] là các bin mô
tả, không chọn ngưỡng tối ưu. Các bin là [a,b), bin cuối gồm 1.

## Chuỗi quan sát — quy ước đếm, không bổ sung quy tắc gốc

Bullish clean component: HA giảm, không wick trên, toàn nến trên EMA.
Bearish clean component: HA tăng, không wick dưới, toàn nến dưới EMA.
Đếm từng đoạn **liên tiếp tối đại** của cùng component, tối thiểu một nến để
định nghĩa một đoạn thống kê. Không khẳng định tác giả yêu cầu continuity/min=1.
Số impulse mô tả là số nến cùng màu xu hướng, cùng vùng EMA, liên tiếp ngay
trước đoạn. Có thể bằng 0; giữ nhóm này, không loại âm thầm. Không giới hạn
độ dài pullback. Segments không vượt gap hoặc split; ghi censoring.

Sau đoạn, tìm **nến đầu tiên có cả hai wick**, bất kể màu/kích thước, trong cùng
vùng EMA. Số nến ở giữa=end distance−1, không đặt max. Nếu đoạn clean mới bắt
đầu trước khi tìm thấy terminal thì đoạn cũ censored/replaced. Nếu chạm/cắt EMA,
gap, warm-up, biên partition hoặc hết dữ liệu thì censored với lý do. Terminal
sai màu được ghi mismatch, không gọi hợp lệ. Terminal thân to vẫn được giữ để
phân bố không bị ngưỡng giả định làm thiên lệch. Các quy tắc ghép/first terminal
là convention mô tả; chưa biết có khớp cách tác giả chọn intermediate không.
Thời điểm xác nhận terminal là sau khi terminal đóng; không dùng độ dài đoạn
hoàn tất như feature có sẵn ở đầu đoạn.

Do đó frequency của **pattern hoàn chỉnh**, phân bố độ dài pullback của pattern
gốc và phân bố intermediate của pattern gốc đều chưa xác định. Report cung cấp
frequency/length của các component/chuỗi theo convention trên, đặt nhãn rõ.

## Hành vi giá thật sau quan sát

Cohort: terminal hai wick đúng màu EMA, có ít nhất một nến impulse mô tả trước
đoạn. Đây là bộ lọc phân tích, chưa có ngưỡng Doji; không phải tín hiệu gốc.
Tại terminal i, neo giá là **Open thật i+1**, đo Close thật i+h sau 1/5/15/60 nến.
Return_bps = direction × (Close[i+h]/Open[i+1]−1) × 10000. Lưu cả return và
max/min excursion hướng xu hướng trên High/Low thật trong cửa sổ này.
Neo giá chỉ là mốc so sánh, không giả định khớp lệnh hoặc entry chính thức.

Chỉ đo khi toàn bộ cửa sổ đủ, không gap và cùng partition của observation;
giữ lý do thiếu/horizon_end/gap/split, không đổi thành thua. Đo tương lai chỉ
trong bảng kết quả sau sự kiện, không cấp cho bộ nhận diện; tests kiểm tra
prefix invariance và mutation future. Không tính tỷ lệ return dương là win rate.
Các cửa sổ có thể overlap; số quan sát độc lập chưa biết. Trung bình/quantile
là mô tả mẫu, không CI nhân quả hoặc kiểm định 75%. Không chọn horizon từ kết quả.

## Báo cáo và thiên lệch

Mỗi sản phẩm có HTML/JSON riêng; comparison giữ số liệu tách sản phẩm, không
gộp thành một win rate. Theo năm, IS/validation/OOS; các partition rỗng ghi 0
observations và metric=null, không coi là kết quả 0%. Không shuffle dữ liệu.
Đã biết dữ liệu OOS hồi cứu từ nghiên cứu trước: không phải holdout chưa xem.
Survivorship/selection bias: chỉ ba sản phẩm có sẵn, một sàn, không đại diện
Forex/Gold/Crypto của tác giả. Multiple horizons và nhiều phân bố chỉ exploratory,
không chọn cấu hình hoặc tuyên bố ý nghĩa thống kê. Costs/funding/spread/intrabar
chưa xác định; không dùng HA làm giá thực thi. Không thêm dependency.

Metrics outcome có schema sẵn cho từng market/năm/split, nhưng sample size
outcome, observed win proportion, CI, independent n, p-value đều null kèm lý do.
Các định nghĩa gốc còn thiếu được hợp nhất tại HA_UNRESOLVED_METHOD.md.
