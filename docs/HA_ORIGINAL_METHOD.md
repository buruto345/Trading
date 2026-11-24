# Heikin Ashi – EMA 100 – Clean Pullback – Doji: quy tắc được cung cấp

## Cập nhật hiện hành: D01–D05 (24/11/2026)

Đặc tả mới nhất đã giải quyết các mục trước đây chưa rõ: không minimum impulse;
pullback ít nhất **hai nến sạch liên tiếp**; intermediate phải ngược màu xu
hướng, được có wick; không giới hạn pullback/intermediate/observation period;
range Doji phải lớn hơn ít nhất một trong hai range ngay trước.

Phát biểu outcome được cung cấp: quan sát từ lúc Doji đóng, biên tham chiếu tại
wick Doji tương ứng, RR1:1, không buffer, tác giả dùng biểu đồ HA. Mốc giá và
đường giá chấm outcome vẫn chưa đủ rõ để khẳng định tái lập nguyên bản.

Năm ngưỡng body/range 5/10/20/30/40% là **biến thể nghiên cứu được người dùng
chọn**, không phải tham số gốc. Xem **`HA_DOJI_VARIANTS_PROTOCOL.md`** để đọc
đầy đủ đặc tả hiện hành, mapping hai chiều, công thức, convention ghép chuỗi,
giả thuyết H1, ba kịch bản ambiguity, CI và hạn chế. Cấu hình thực thi:
`config/ha_doji_variants.json`. Các phần dưới giữ lịch sử đặc tả trước cập nhật;
những mục đã giải quyết ở trên không còn được coi là unresolved.

## Lịch sử đặc tả trước cập nhật D01–D05

Nguồn phương pháp: đặc tả người dùng cung cấp ngày 24/11/2026. Chưa có đường dẫn
bài gốc hoặc dữ liệu giao dịch của tác giả để xác minh độc lập lời tuyên bố.
Tệp này tách biệt hoàn toàn với MODEL_SPECIFICATION.md của mô hình ICT M5.

| Thuộc tính | Đặc tả đã được người dùng xác nhận |
|---|---|
| Khung | M1 gốc |
| Nến | Heikin Ashi |
| Chỉ báo | EMA 100, nguồn HA Close |
| Độ dốc EMA | Không bắt buộc |
| Mô hình | Tiếp diễn xu hướng sau pullback |
| Wick nến impulse | Được phép |
| Số nến pullback tối đa | Không có giới hạn được quy định |
| Pullback chạm/cắt EMA | Không được phép |
| Vị trí EMA | Toàn bộ nến HA, gồm thân và wick, phải nằm trên EMA cho bullish; dưới EMA cho bearish |
| Pullback bullish sạch | Nến HA giảm, không có wick trên, toàn nến trên EMA |
| Pullback bearish sạch | Nến HA tăng, không có wick dưới, toàn nến dưới EMA |
| Thân Doji | Nhỏ hoặc gần bằng không |
| Wick Doji | Bắt buộc có cả wick trên và dưới |
| Màu Doji | Cùng chiều xu hướng chính |
| Nến trung gian | Được phép |
| Nến xác nhận sau Doji | Không bắt buộc |
| Volume filter | Không dùng |
| Session filter | Không dùng |
| Hai chiều | Bullish và bearish đối xứng |
| RR công bố | 1:1 |
| Win rate công bố | 75%, chưa kiểm chứng |

Tác giả được cho là đã gộp Forex, vàng và crypto. Cỡ mẫu, thời kỳ, chi phí và
quy trình xác minh chưa được cung cấp. RR 1:1 không xác định entry, stop,
thứ tự chạm mức hoặc định nghĩa nhãn thắng/thua.

Bổ sung theo đặc tả người dùng ngày 24/11/2026: toàn bộ Doji cùng phía EMA;
Doji sai màu xu hướng làm mẫu không hợp lệ. Không yêu cầu chỉ báo bổ sung hoặc
đa khung thời gian. Chưa có ngưỡng để phân loại một nến cụ thể là Doji.

## Đặc tả đầy đủ được tái xác nhận ngày 24/11/2026

Phần này lưu yêu cầu mới nhất của người dùng để các lần nghiên cứu sau không
yêu cầu cung cấp lại những điều đã xác nhận. Nguồn là đặc tả người dùng, chưa
phải bằng chứng xác minh độc lập bài công bố của tác giả.

### Cấu hình chung

- Chỉ M1, nến Heikin Ashi, EMA 100 tính trên HA Close.
- Không yêu cầu độ dốc EMA, volume, giới hạn phiên, đa khung thời gian hoặc
  chỉ báo bổ sung.
- RR công bố 1:1; win rate công bố 75% chưa được kiểm chứng.
- Hai chiều bullish/bearish hoàn toàn đối xứng.
- Nghiên cứu độc lập BTCUSDT, ZECUSDT, XAUUSDT từ M1 đã lưu; không tải lại,
  không tái xây dựng project, không live execution hoặc tiền thật.

### Bullish: impulse → clean pullback → bullish Doji

1. Xu hướng: toàn nến HA, gồm thân và cả hai wick, phải trên EMA 100.
   Không cần EMA slope hoặc xác nhận cấu trúc thị trường bổ sung.
2. Impulse: nến bullish được có cả wick trên và wick dưới. Không bắt buộc
   impulse sạch hoặc không có wick dưới.
3. Clean pullback: gồm nến HA bearish không có wick trên; toàn bộ các nến
   pullback vẫn trên EMA. Chạm hoặc cắt EMA làm mẫu không hợp lệ. Tác giả
   không quy định giới hạn độ dài pullback tối đa.
4. Doji: bullish, thân nhỏ hoặc gần bằng 0, có cả wick trên/dưới, toàn nến
   trên EMA. Được có nến trung gian giữa pullback và Doji. Không cần nến xác
   nhận sau Doji. Doji bearish làm mẫu bullish không hợp lệ.

### Bearish: impulse → clean pullback → bearish Doji

1. Xu hướng: toàn nến HA, gồm thân và cả hai wick, phải dưới EMA 100.
   Không yêu cầu EMA slope; áp dụng tính đối xứng với bullish.
2. Impulse: nến bearish được phép có wick.
3. Clean pullback: gồm nến HA bullish không có wick dưới; toàn bộ các nến
   pullback vẫn dưới EMA. Chạm hoặc cắt EMA làm mẫu không hợp lệ. Không có
   giới hạn độ dài pullback tối đa được tác giả quy định.
4. Doji: bearish, thân nhỏ hoặc gần bằng 0, có cả wick trên/dưới, toàn nến
   dưới EMA. Được có nến trung gian, không cần nến xác nhận bổ sung. Doji
   bullish làm mẫu bearish không hợp lệ.

### Công thức chỉ báo và hình học

```text
HA_Close[t] = (Open[t] + High[t] + Low[t] + Close[t]) / 4
HA_Open[t] = (HA_Open[t-1] + HA_Close[t-1]) / 2
HA_High[t] = max(High[t], HA_Open[t], HA_Close[t])
HA_Low[t] = min(Low[t], HA_Open[t], HA_Close[t])

EMA_Source[t] = HA_Close[t]
EMA_Period = 100

Body = abs(HA_Close - HA_Open)
Range = HA_High - HA_Low
Upper_Wick = HA_High - max(HA_Open, HA_Close)
Lower_Wick = min(HA_Open, HA_Close) - HA_Low
Body_Ratio = Body / Range
```

Range bằng 0 không có tỷ lệ xác định; không tự coi là Doji hợp lệ. Tính toán
phải xử lý khởi tạo, warm-up, dữ liệu thiếu và sai số số thực. HA là giá tổng
hợp chỉ báo, không phải giá khớp lệnh thị trường.

### Quy tắc chưa xác định của tác giả

Các mục sau vẫn **unresolved**, không có giá trị mặc định dùng để tính win rate:

1. Độ dài impulse tối thiểu.
2. Độ dài pullback tối thiểu.
3. Tính liên tục màu nến pullback.
4. Body/Range tối đa của Doji.
5. Tỷ lệ wick Doji.
6. Đặc điểm nến trung gian.
7. Số nến trung gian tối đa.
8. Giá/thời điểm entry gốc.
9. Vị trí stop-loss gốc.
10. Thời hạn quan sát outcome tối đa.
11. Cách giải quyết outcome intrabar mơ hồ.

RR 1:1 không tự xác định outcome thắng/thua. Schema nghiên cứu giữ thêm mục
`outcome_labeling` bao quát cách tính mẫu số, censoring, chi phí và overlap;
đó là lý do danh sách kỹ thuật hiện có 12 mục, không phải 12 quy tắc gốc.
Xem `HA_UNRESOLVED_METHOD.md` để đối chiếu tên trường.

### Phân biệt quy tắc gốc với triển khai nghiên cứu

HA Open seed=(O+C)/2, EMA seed=HA Close đầu segment, warm-up 500 nến và reset
sau gap là các convention tính toán đã kiểm thử, không tuyên bố là khởi tạo
platform của tác giả. Dung sai 32 eps theo thang giá thuộc convention số học.

Đếm clean run liên tiếp tối đại, ghép nến hai wick đầu tiên và đo giá thật sau
1/5/15/60 phút là nghiên cứu mô tả theo `HA_DESCRIPTIVE_PROTOCOL.md`. Những
convention đó không giải quyết Doji/entry/SL của tác giả. Đề xuất Doji <=10%,
entry next-open, SL cực trị đoạn và horizon 60 phút trong hội thoại trước
chưa được chấp nhận làm protocol giao dịch. Không tự nâng thành quy tắc gốc.
