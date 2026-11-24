# HA–EMA100: đặc tả cập nhật và nghiên cứu D01–D05

Ngày 24/11/2026. Nguồn: đặc tả người dùng mới nhất; không tự xác minh video.
Tài liệu này là đặc tả hiện hành cho run mới. Các báo cáo/config trước đó là
snapshot nghiên cứu lịch sử, không sửa lại kết quả cũ.

## Quy tắc gốc đã được xác nhận bổ sung

M1, HA; EMA100 trên HA Close, không slope, volume/session/đa khung hoặc
xác nhận cấu trúc/nến bổ sung. Hai chiều đối xứng. Không yêu cầu minimum
impulse; impulse được có wick. RR công bố 1:1, 75% chưa kiểm chứng.

Bullish: toàn nến HA (thân và wick) trên EMA. Pullback có ít nhất **hai nến
bearish liên tiếp không wick trên**, toàn bộ trên EMA, không giới hạn độ dài.
Intermediate được có wick, phải bearish, toàn bộ trên EMA, không giới hạn số
nến. Doji bullish, thân nhỏ, có hai wick, toàn nến trên EMA; range HA của Doji
**lớn hơn ít nhất một trong hai range HA ngay trước**. Không cần nến xác nhận.
Chạm/cắt EMA làm mẫu không hợp lệ.

Bearish: toàn nến dưới EMA; pullback ít nhất hai nến bullish liên tiếp không
wick dưới; intermediate bullish được có wick; Doji bearish hai wick và cùng
điều kiện range. Không giới hạn pullback/intermediate/thời hạn quan sát.

Công thức HA và geometry không đổi: C_HA=(O+H+L+C)/4;
O_HA[t]=(O_HA[t-1]+C_HA[t-1])/2; H_HA=max(H,O_HA,C_HA);
L_HA=min(L,O_HA,C_HA). EMA100(C_HA). Body=abs(C_HA−O_HA),
Range=H_HA−L_HA; upper=H_HA−max(O_HA,C_HA); lower=min(O_HA,C_HA)−L_HA;
Body_Ratio=Body/Range, null khi range=0.
Tái sử dụng feature/geometry đã kiểm thử và hash; không tái tính hoặc tải lại.
Giữ warm-up500, seed/reset-gap và tolerance32eps theo protocol hiện có.

## Tham số nghiên cứu do người dùng chọn, không phải của tác giả

D01<=5%, D02<=10%, D03<=20%, D04<=30%, D05<=40% Body/Range.
Chạy tất cả, không xếp hạng/chọn ngưỡng tốt nhất. Không yêu cầu tỷ lệ hai wick,
ngoài cả hai wick lớn hơn dung sai; đây là cách xử lý khi không có tỷ lệ được
công bố. Body nằm trong dung sai có màu neutral, không đủ điều kiện Doji màu.

State machine nhân quả: bắt đầu tại run clean; đủ hai nến thì armed. Kéo dài
run clean đến nến không clean đầu tiên; sau đó cho phép intermediate ngược
màu xu hướng với wick tùy ý. Một setup được dùng tối đa một lần. Nến cùng màu
xu hướng đầu tiên phải là Doji đạt threshold/range, nếu không thì hủy setup;
neutral, mất vùng EMA hoặc gap cũng hủy. Các clean candle sau intermediate vẫn
là intermediate; không tạo nhiều setup trùng từ mọi cặp nến của cùng một run.

Đặc tả trước đó nói Doji sai màu làm mẫu không hợp lệ, trong khi đặc tả mới
cho phép intermediate ngược màu có wick. Chọn rõ precedence để giữ điều kiện
đã xác nhận: nến ngược màu thỏa toàn bộ định nghĩa Doji của variant (threshold,
hai wick, range expansion) hủy setup trước khi được nhận là intermediate.
Đây là convention giải quyết tình huống giao nhau, chưa được video xác minh;
ghi số lần loại `opposite_doji`. Không âm thầm coi mọi nến ngược màu là Doji.

## Phát biểu outcome được cung cấp và diễn giải H1

Phát biểu được cung cấp: quan sát bắt đầu khi Doji đóng, biên tham chiếu tại
wick tương ứng của Doji, RR1:1, không buffer, tác giả dùng biểu đồ HA trong video.
Chưa rõ chính xác mốc giá close, wick đối hướng, dùng HA hay giá thật để xác
định chạm biên. Vì thế **tái lập outcome gốc vẫn chưa xác định**.

Để có phép đo lịch sử định lượng có thể kiểm tra, chạy riêng **H1 — giả thuyết
biên tham chiếu HA, đường giá thật**:

- Bullish: R=HA Close−HA Low của Doji; biên bất lợi=HA Low;
  biên thuận=HA Close+R.
- Bearish: R=HA High−HA Close; biên bất lợi=HA High;
  biên thuận=HA Close−R.
- Không buffer, không giả định fill ở HA Close. Đây là mức chỉ báo và phép đo
  chạm biên, không phải giá giao dịch thực thi, P&L hoặc expectancy.
- Dùng OHLC **thị trường thật** từ nến kế tiếp, không dùng high/low của chính
  Doji vì chúng xảy ra trước thời điểm quan sát. Nếu open nến kế tiếp/đang xét
  đã nằm ngoài một biên, biên đó được ghi chạm trước tại open; không coi gap là
  fill tại biên. Nếu open nằm giữa hai biên và high/low chạm cả hai: ambiguous.
- Không horizon nhân tạo. Đo tới lần chạm đầu hoặc cuối dữ liệu/gap. Giữ mọi
  quan sát overlap; không giới hạn một vị thế vì không phải portfolio simulator.
- Full history không cắt tại split; đánh giá IS/validation/OOS riêng cắt outcome
  tại boundary để tránh dùng tương lai partition kế tiếp. Cả hai scope được lưu.
  Partition gán bằng giờ Doji đóng; formation có thể dùng lịch sử trước split.
- Giá đóng thị trường của Doji có thể khác HA Close. Ghi chênh lệch và số lần
  close thật đã ở ngoài biên H1 để bộc lộ tính không thực thi của giả thuyết.

## Ambiguity, censoring và thống kê

W=chạm biên thuận trước; L=biên bất lợi trước; A=ambiguous; U=unresolved.
Resolved=W+L. Conservative: W/(W+L+A); Optimistic: (W+A)/(W+L+A);
Excluded: W/(W+L). U luôn báo riêng, không tự gán thất bại; bounds bao gồm U
được lưu để thấy giới hạn censoring. Invalid risk nếu có được báo riêng.
45 hàng full-history = 3 mã × 5 thresholds × 3 ambiguity scenarios.
Các bảng partition/year là phân tích bổ sung, không trộn các instrument.

CI95 Wilson chỉ là tham chiếu IID. CI95 chính cho H1 dùng moving calendar-block
bootstrap 7 ngày, 2000 lần, seed20261124, trên ngày xác nhận; gồm ngày không có
quan sát. Lưu status khi denominator bootstrap bằng 0. CI bootstrap vẫn phụ
thuộc giả định stationarity/block length, không chứng minh độc lập. Báo count
observations có interval overlap và maximum concurrent; independent n=null.
Các interval được căn theo nến: end_time là giờ đóng nến chứa lần chạm,
kể cả khi reason cho biết biên đã vượt tại open. Overlap/concurrency vì thế
là số đo bảo thủ theo bar, không phải thời điểm fill hoặc số vị thế thực tế.
Không gộp variant thành trial độc lập. CI là pointwise, không simultaneous;
không kiểm định significance hay chọn tham số để đạt 75%. 45 cách báo cáo không
phải 45 thí nghiệm độc lập. Reused OOS là hồi cứu, không holdout mới.

## Dữ liệu, artifacts và giới hạn

BTCUSDT/ZECUSDT/XAUUSDT perpetual Binance từ snapshot M1. Dữ liệu đến
22/11/2026 23:59 UTC; thiếu ngày 23/11 tới cutoff, không tải bù. XAU trước
05/01/2026 giữ nguồn nhưng loại nghiên cứu. Lịch đóng cửa chưa xác minh; không
thay thế bằng Forex/spot gold. Selection/survivorship, costs/funding/spread,
đường giá intrabar và phương pháp tác giả vẫn là giới hạn.

Kết quả mới riêng tại `reports/ha_doji_variants/`; không sửa báo cáo cũ.
Source/config/docs hashes, input hashes, preservation, CSV/JSON/Parquet,
unit test XML, audit và browser QA được lưu. Không thêm dependency/network.
