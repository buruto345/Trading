# Quy ước thực nghiệm của bộ máy

Các quy ước dưới đây phục vụ mô phỏng, không phải yêu cầu ICT đã được xác nhận.

- Swing wick nghiêm ngặt ba nến; chỉ dùng từ open nến i+2, khi nến i+1 đã đóng. High/Low bằng nhau không tạo swing.
- Liquidity level: swing gần nhất còn chưa bị wick xuyên qua, được xác nhận trước open nến sweep. Wick xuyên level tiêu thụ swing kể cả candle sai màu/đóng sai phía; không tái sử dụng.
- Structure level: swing đối diện được xác nhận gần nhất trước open sweep. Level này được cố định trong setup; không thay bằng swing tương lai. Không yêu cầu level còn nguyên vẹn ở sweep (đây là giới hạn cần sensitivity study).
- Một setup chờ mỗi hướng. Sweep mới thay setup cùng hướng; hai hướng có thể đồng thời tồn tại. Ghi nguyên nhân thay thế. Pattern ID duy nhất theo symbol/hướng/sweep timestamp.
- MSS chỉ xảy ra ở nến sau sweep, bằng close nghiêm ngặt vượt structure level. Chờ tối đa 24 nến M5 mặc định. Wick vượt sweep extreme trước MSS làm vô hiệu setup, kể cả nến đó cũng MSS.
- FVG bullish: Low[k] > High[k-2]; bearish: High[k] < Low[k-2]. Cả ba nến phải nằm trong [sweep,MSS]. Thời điểm hình thành là close nến thứ ba. Một FVG trước MSS vẫn hợp lệ dù đã được giá đi qua lại. Không thêm bộ lọc màu FVG.
- fvg_size là tổng kích thước các FVG; fvg_lower/upper là FVG cuối. fvg_details giữ timestamp và bounds của tất cả FVG.
- Gaps dữ liệu reset toàn bộ trạng thái, không lấp nến. Overlapping mô tả cửa sổ sweep–MSS giao với pattern đã xác nhận trước đó. Mô phỏng cho phép nhiều quan sát đồng thời; không phải portfolio có giới hạn vốn.
- Entry open nến sau MSS; stop tại wick extreme sweep, target cách entry 2 lần khoảng risk dương. Risk <=0 là invalid, không giao dịch. Không dùng giá trong nến MSS làm entry.
- Quan sát tối đa 288 nến (=24 giờ khi dữ liệu liên tục). partition_end_idx là biên loại trừ: không dùng candle trong partition tiếp theo. Không có entry, hết dữ liệu, gap hoặc hết horizon đều giữ unresolved; không gán flat return.
- Stop bị gap qua fill tại open xấu hơn; TP bị gap qua vẫn cap tại TP. M5 cùng chạm SL/TP dùng toàn bộ 5 nến M1 liên tục nếu có; vẫn ambiguous nếu cùng nến M1 chạm cả hai. Không đoán thứ tự intrabar.
- Chi phí giả định 10 bps round-trip trên notional entry (fee + slippage gộp), đổi sang R = 0.001*entry/risk; không bao gồm funding, không phải mức phí của sàn đã kiểm chứng.
- MFE/MAE lấy high/low toàn nến đến và gồm nến exit: **upper bound** do không biết intrabar path, không phải excursion thực tế trước exit. Không dùng nến sau exit. Horizon-censored excursions có quan sát đầy đủ đến close cuối.
- Kết quả R là từng quan sát với 1R bằng risk-distance, không đại diện lợi nhuận tài khoản hoặc sizing khả thi. Không có hòa vốn ở quy tắc exit này.
