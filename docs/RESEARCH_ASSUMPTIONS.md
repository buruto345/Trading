# Các giả định thí nghiệm — không phải quy tắc đã xác nhận

Các giá trị dưới đây được ấn định trước khi chạy thống kê, không tối ưu theo Win Rate.

- Liquidity swing: swing gần nhất còn chưa bị xuyên wick, được xác nhận trước khi nến sweep mở. Một swing chỉ được sử dụng một lần; wick xuyên nhưng không đạt điều kiện sweep vẫn tiêu thụ mức liquidity.
- Structure: swing đối hướng gần nhất được xác nhận trước sweep. Không yêu cầu mức structure còn nguyên; đây là giới hạn của cách diễn giải đang thử nghiệm.
- Một pending setup mỗi hướng; sweep mới thay setup cũ. MSS phải ở nến sau sweep; tối đa24 nến. Wick vượt extreme của sweep trước MSS vô hiệu setup.
- FVG: cả ba nến phải nằm trong [sweep,MSS], hướng gap khớp mô hình. Ghi mọi FVG. Không yêu cầu FVG còn chưa mitigation tại MSS.
- Overlap được giữ như những quan sát nghiên cứu khác nhau, không tương đương một portfolio có giới hạn vốn. Bootstrap theo lịch để xét phụ thuộc. Không đếm lại cùng sweep.
- Entry giả định: open nến ngay sau MSS; stop extreme sweep; target cách entry2 lần risk. Risk không dương được ghi invalid. Không giả định limit entry tại FVG.
- Horizon288 nến M5 (24giờ); quan sát chưa chạm boundary được censored/unresolved, không ép đóng lệnh thành win/loss. End-of-data, missing candles và ranh giới partition cũng censor.
- Nếu open đã vượt stop: fill tại open (lỗ có thể >1R). Nếu vượt target: bảo thủ fill target. Nếu cùng nến có stop và target: dùng M1 authentic; nếu M1 vẫn không biết thứ tự thì ambiguous.
- Cost round-trip10bps trên entry notional, cost_R=entry×0.001/risk; sensitivity0/5/10/20bps. Đây là giả định minh họa, không phải phí sàn được báo giá. Chưa mô hình funding, spread, queue hay độ trượt ngoài gap.
- MFE/MAE đo bằng wick nến đến lúc kết thúc; khi không biết intrabar, extreme của nến kết thúc chỉ là upper bound, không khẳng định đã xảy ra trước exit.
- Partition theo chỉ số nến từng instrument: 60% /20% /20%. Chạy detector riêng mỗi đoạn; setup không băng ranh giới, outcomes censor ở cuối đoạn. Mỗi đoạn cần warmup swing tự nhiên. Mốc thời gian khác nhau giữa instrument; không coi OOS gộp là một đoạn lịch chung.
- Volatility: rolling standard deviation close-return288 nến, chỉ tới sweep. Volume tại sweep; regime: dấu return288 nến; daily bias: dấu nến ngày UTC đã đóng trước sweep, chỉ là đặc trưng quan sát.
- Session mô tả: Tokyo09–18, London08–17, New York08–17 theo múi giờ địa phương; DST bằng IANA tzdata. Các bit phiên tạo nhãn overlap, không dùng làm bộ lọc nhận diện.
- Nhóm exploratory chỉ dùng development (in-sample+validation); OOS chỉ bảng tổng hợp định trước. Các ranh giới quantile fit trên in-sample. Multiple testing BH được trình bày như exploratory, không tạo recommendation.
- Wilson dựa trên Bernoulli độc lập chỉ là tham chiếu. Bootstrap block ngày chung các instrument có thể tăng/giảm CI; ESS là ước lượng heuristic qua tỷ số variance, không số lượng giao dịch độc lập đã chứng minh.
- Combined weighting: mỗi quan sát trọng số1; instrument có nhiều mẫu chiếm tỷ trọng lớn hơn. Không phải equal-capital portfolio.
- Break-even33.33% chỉ đúng mô hình payoff+2/-1 trước phí và không gap. Kết luận cost-adjusted dựa vào outcome thực tế thay vì ngưỡng lý tưởng này.

Sensitivity: max Sweep→MSS12/48 trên development. Kết quả sensitivity chỉ dùng đánh giá độ nhạy, không chọn cấu hình tốt nhất.

XAU archive có nến trước ngày public listing05/01/2026. Giữ nguyên trong raw/validated nhưng loại khỏi nghiên cứu trước 00:00 UTC05/01/2026; đây là cutoff theo ngày do thông báo không xác định giờ. Số gap đo trên lưới24/7, không tự động coi mọi khoảng nghỉ là lỗi: lịch giao dịch vàng có thể có phiên đóng.
