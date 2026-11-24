# Yêu cầu làm rõ hợp nhất trước đánh giá win rate từng sản phẩm

**Lưu lịch sử:** yêu cầu mới nhất đã cung cấp đầy đủ lại đặc tả xác nhận;
không cần trả lời lại các quy tắc đã nêu. Phần tin nhắn bị cắt ở cuối tài liệu
này chỉ mô tả yêu cầu trước đó, không còn là yêu cầu gửi bổ sung hiện hành.
Đặc tả hiện hành nằm tại `HA_ORIGINAL_METHOD.md`; các mục chưa xác định được
giữ unresolved theo chỉ dẫn người dùng, không tự điền giả định.

Rà soát ngày 24/11/2026. Không sửa quy tắc đã xác nhận, không tải lại dữ liệu,
không tính lại HA/EMA và không tự nhận các đề xuất hội thoại là quy tắc gốc.

## Những gì repository đã có

- Ba M1 datasets tại `data/processed/ha_m1/{BTCUSDT,ZECUSDT,XAUUSDT}_1m.parquet`.
- HA/EMA, warm-up, timestamp và partitions trong `src/ha_research/indicators.py`.
- Quy tắc xác nhận tại `docs/HA_ORIGINAL_METHOD.md`: M1, EMA100(HA Close),
  toàn nến cùng phía EMA, pullback sạch không wick theo hướng đối xứng,
  Doji đúng màu/hai wick/thân nhỏ, RR 1:1; không session hoặc volume filter.
- Geometry, clean runs và real-price markouts trong `src/ha_research/descriptive.py`.
- Báo cáo riêng từng mã, theo năm/partition tại `reports/ha_descriptive/`.
- Wilson IID reference, counts, censor bounds và schema nhóm market/period/partition
  trong `src/ha_research/statistics.py`. Không có nhãn thắng/thua HA để cấp vào.

Không tìm thấy định nghĩa gốc bổ sung trong README, config, docs hoặc scripts HA.
Entry/SL/horizon ở `docs/ENGINE_CONVENTIONS.md` và engine mô phỏng cũ thuộc
ICT M5 RR 1:2; không phải định nghĩa của phương pháp HA M1 RR 1:1.

## Một lần làm rõ các định nghĩa còn thiếu

Vui lòng cung cấp câu trả lời và đánh dấu nguồn: **quy tắc tác giả có nguồn**,
**quy tắc người dùng chọn cho thí nghiệm**, hoặc **chưa biết**. Nếu có đường
dẫn/trích đoạn gốc, kèm nguồn để đối chiếu. Các lựa chọn thí nghiệm được lưu
trong protocol riêng, không ghi đè phương pháp gốc.

| Mục | Câu hỏi cần trả lời |
|---|---|
| Minimum impulse | Tối thiểu bao nhiêu nến, bắt đầu/kết thúc impulse ở đâu? |
| Minimum pullback | Tối thiểu bao nhiêu nến sạch? |
| Pullback continuity | Các nến pullback có phải liên tiếp cùng màu? Nến chen giữa xử lý thế nào? |
| Doji body/range | Body/Range tối đa bao nhiêu? Thân đúng bằng 0 có được tính, và gán màu thế nào? |
| Doji wick ratio | Có ràng buộc tỷ lệ hai wick hay chỉ cần cả hai wick dương? |
| Intermediate characteristics | Cho phép màu/thân/wick nào; khi có nhiều Doji hoặc pullback mới thì chọn hoặc hủy setup thế nào? |
| Maximum intermediate | Tối đa bao nhiêu nến hoặc xác nhận không giới hạn? |
| Entry | Giá/thời điểm cụ thể trên OHLC thật; market/limit và điều kiện không khớp? |
| Stop-loss | Cực trị nến/đoạn nào, dùng OHLC thật hay mức chỉ báo làm tham chiếu, có buffer không? |
| Outcome labeling | Thắng/thua trước hay sau chi phí, phí bao nhiêu; cho phép các quan sát/lệnh chồng lấn không; gặp gap xử lý thế nào? |
| Observation period | Tối đa bao nhiêu phút/nến; hết hạn chưa chạm mức thì unresolved hay đóng theo giá thị trường? |
| Intrabar ambiguity | Cùng nến chạm TP và SL: giữ ambiguous, giả định thứ tự, hay cần dữ liệu chi tiết hơn? |

RR 1:1 giữ nguyên; TP chỉ tính được sau khi xác định entry và risk/SL.
Không đặt giới hạn pullback tối đa vì đặc tả gốc không quy định giới hạn đó.
Số quan sát độc lập không tự bằng số tín hiệu; cần phương pháp xử lý phụ thuộc
trước khi dùng CI/kiểm định 75% để kết luận.

Đề xuất trước đây (Doji <=10%, entry next-open, SL cực trị pullback, horizon
60 phút) **chưa được xác nhận** và **chưa được chạy như mô hình giao dịch**.

## Phần có thể tính ngay từ kết quả hiện có

Đã kiểm tra lại SHA-256 ba M1 Parquet và ba markout Parquet. Đối chiếu SQL
sample size, số cửa sổ đo được và mean với báo cáo trước. Không thay dataset.
`reports/ha_win_rate_review/supported_metrics.json` lưu count, censored, mean,
median và sample standard deviation theo từng symbol/partition/horizon.
Đây là độ phân tán mô tả mẫu, không CI hoặc bằng chứng các mẫu độc lập.

| Sản phẩm | Quan sát hình thái trong cohort | Mean biến động có dấu sau 15 phút (bps) | Win rate gốc |
|---|---:|---:|---|
| BTCUSDT | 36.564 | -0,39444 | Chưa xác định |
| ZECUSDT | 37.200 | -1,08065 | Chưa xác định |
| XAUUSDT | 4.394 | +0,27417 | Chưa xác định |

Cohort là terminal hai wick cùng màu vùng EMA sau clean run có impulse mô tả,
chưa áp tiêu chuẩn Doji. Biến động từ Open thật nến kế tiếp tới Close thật
sau 15 nến, có dấu theo hướng xu hướng; 1 bps=0,01%. Đây không phải return
của giao dịch đã định nghĩa, không phải expectancy R và không suy ra win rate.
Các cửa sổ có thể overlap, chi phí chưa mô hình hóa. XAU không có IS/validation
trong split calendar hiện tại; không tạo giả kết quả cho nhóm rỗng.

## Phạm vi yêu cầu mới chưa đầy đủ

Tin nhắn kết thúc giữa câu: “For each instrument, calculate all statistically
valid metrics supported by”. Vui lòng gửi phần còn lại nếu còn các chỉ số,
điều kiện hoặc deliverable chưa được truyền tới. Phần này không được suy đoán.
