# Mô hình đã xác nhận

M5, ICT Reversal, hai chiều; Liquidity Sweep + MSS + FVG là ba điều kiện bắt buộc của cùng một mô hình. Không lọc phiên hay Daily Bias.

Swing High tại i: High[i] > High[i-1] và High[i] > High[i+1]. Swing Low đối xứng với <. Dùng wick, không dùng màu nến, loại bằng nhau. Chỉ xác nhận khi nến i+1 đóng.

Bearish sweep: có Swing High được xác nhận trước đó; high vượt swing; close dưới swing; close < open. Bullish: low dưới Swing Low; close trên swing; close > open.

Bearish MSS: nến sau sweep đóng dưới Swing Low liên quan. Bullish MSS: đóng trên Swing High liên quan. FVG đúng hướng phải xuất hiện trong chuyển động sweep đến MSS; không bắt buộc MSS tạo FVG.

Quy ước wick FVG ba nến: bullish khi Low[k] > High[k-2], biên [High[k-2], Low[k]]; bearish khi High[k] < Low[k-2], biên [High[k], Low[k-2]]. Xác nhận khi k đóng; equality không tạo gap.

RR mô phỏng 1:2. Chọn swing, thời hạn, entry, stop, overlap chưa được người dùng xác nhận: xem RESEARCH_ASSUMPTIONS.md. Không có Intermediate/Long-Term Swing.

