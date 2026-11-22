# Protocol đa mô hình — khóa trước khi chạy thống kê

## Kế hoạch
1. Kiểm kê và SHA256 các kết quả cũ, mã nguồn gốc và Parquet; không tải dữ liệu.
2. Giữ detector/simulator/statistics gốc; thêm module độc lập, tái dùng swing, FVG, features, Wilson và calendar block bootstrap.
3. Kiểm thử bullish/bearish, prefix causality, DST, gaps, rejects và mô phỏng trước lịch sử.
4. Chạy từng partition 60/20/20 theo số nến từng mã như baseline; reset trạng thái ở biên.
5. Lưu observations/rejections/simulations/statistics mới; đối soát và HTML offline tiếng Việt, browser QA.

## Nguồn và mức xác nhận
- Baseline: docs/MODEL_SPECIFICATION.md và docs/ENGINE_CONVENTIONS.md của dự án, không sửa.
- ICT 2022: The Inner Circle Trader, 2022 Mentorship Episode 6: https://www.youtube.com/watch?v=Bkt8B3kLATQ . Metadata mô tả FVG và MSS.
- Silver Bullet: The Inner Circle Trader, 2023 ICT Mentorship — ICT Silver Bullet Time Based Trading Model: https://www.youtube.com/watch?v=tRq1hyGGtl4 . Ba khung giờ do người dùng chỉ định.
- Breaker: The Inner Circle Trader, Core Content Month 04 — ICT Breaker Block: https://www.youtube.com/watch?v=UrS-mtGHtAA .
- Turtle Soup: đặc tả false breakout do người dùng cung cấp và swing đã xác nhận của dự án.
- Unicorn: yêu cầu overlap breaker/FVG do người dùng cung cấp, tham khảo khái niệm breaker ở trên.
Đã kiểm tra tiêu đề/metadata nguồn; không có toàn bộ transcript đã xác thực. Không tuyên bố tái tạo chính thức ICT. Mọi ngưỡng, lựa chọn candle/entry/exit dưới đây là quy ước thực nghiệm, không trích thành quy tắc chính thức.

## Quy tắc chung
Nến UTC M5, swing 3 nến strict chỉ khả dụng từ open i+2. Không equality. Gaps reset detector và ATR. Một liquidity level bị xuyên wick chỉ dùng một lần. Màu rejection bullish close>open, bearish close<open. Không Daily Bias.
Displacement: body cùng hướng >= 1.5 * trung bình true range 20 nến trước (không chứa nến hiện tại), body/range >=0.6. Warmup 20 nến liên tục; không tối ưu ngưỡng sau kết quả.
FVG wick 3 nến của engine gốc, chỉ xác nhận lúc nến thứ ba đóng; displacement phải là nến giữa của FVG. FVG size là độ rộng zone được chọn, không tổng nhiều gap ở mô hình mới.
Retracement/revisit: nến SAU formation có high>=lower và low<=upper. Tối đa 24 nến. Nếu wick xuyên stop, gap hoặc hết partition trước revisit thì reject; ưu tiên invalidation khi cùng nến revisit. Confirmation tại CLOSE nến revisit, không giả định limit fill intrabar. Ghi formation, MSS và revisit riêng. Pattern cuối chỉ tính khi đủ confirmation; formation/rejects được thống kê riêng.

## M0 Existing ICT Baseline
Detector gốc không đổi: sweep có màu đúng, MSS sau sweep <=24 nến, FVG giữa sweep và MSS. Track B chạy lại riêng, next-open stop sweep và TP2R. Track A bằng quy ước gốc RR2. Đối soát kết quả với snapshot cũ.

## M1 ICT 2022 FVG Retracement (biến thể thực nghiệm)
Lấy chuỗi sweep/MSS đã xác nhận của detector gốc. Chọn FVG cuối có displacement nến giữa, trong sweep..MSS. FVG có thể xác nhận trước hoặc cùng MSS; đợi revisit SAU MSS, không nhận revisit trước confirmation. Stop sweep extreme. Mẫu đủ điều kiện sau revisit close.

## M2 ICT Silver Bullet (biến thể FVG/displacement)
FVG có displacement nến giữa, cả ba nến cùng cửa sổ New York local ngày đó: [03:00,04:00), [10:00,11:00), [14:00,15:00). Formation close và revisit close cũng phải nằm trong cùng cửa sổ; loại close đúng giờ kết thúc. Dùng tz_convert America/New_York cho DST, không UTC offset cố định. Không bắt buộc sweep/MSS; ghi flags có/không dựa trên baseline đã xác nhận trong 24 nến trước và cùng hướng. Stop extreme của 3 nến FVG. Revisit <=24 nến và phải trong phiên.

## M3 ICT Turtle Soup (biến thể có lọc màu)
Nearest unbroken confirmed swing được wick xuyên và close trở lại bên trong, đúng màu rejection. Không yêu cầu MSS/FVG. Xác nhận close rejection. Stop tại extreme rejection. Track A target swing đối diện đã xác nhận trước sweep (nếu không có target hợp lệ -> invalid). Ghi rejection wick-breach sai màu/không close lại.

## M4 ICT Unicorn (biến thể breaker một nến)
Từ sweep/MSS/FVG baseline: bắt buộc swing bị sweep < opposite structure swing < sweep theo chỉ số. Bullish: structure swing high candle là up-close; trước đó có swing low, sau đó bị sweep thấp hơn; close MSS vượt high của structure candle. Bearish đối xứng với down-close swing-low candle. Breaker là FULL WICK RANGE candle structure đó (không tự tìm candle thuận lợi khác). Breaker bị phá bằng close MSS; FVG displacement cùng hướng phải có overlap dương với breaker. Chọn FVG hợp lệ cuối; zone=intersection. Revisit sau MSS; stop sweep extreme. Không có higher timeframe narrative hay kill-zone filter: hạn chế rõ ràng.

## Hai track
Cùng population mẫu đủ confirmation, cùng next-open entry (không entry ngay candle xác nhận), horizon288 M5, censor tại gap/partition/end, phí10 bps round-trip entry/risk, không funding. Stop thống nhất extreme lưu trong pattern.
B: target2R mọi mô hình.
A: M0 giữ2R; M1/M2/M4 target extreme cùng hướng của chuyển động từ sweep (M2: candle đầu FVG) đến formation/MSS, biết TRƯỚC revisit. M3 target opposite confirmed swing trước rejection. Target không còn thuận hướng ở entry => invalid, không đổi sang target thuận lợi hơn. Vì exit khác nhau, không xếp hạng WR Track A như tương đương.
M5 chạm cả SL/TP dùng cache M1 nếu đủ5 nến liên tục, OHLC khớp; cùng M1 chạm hai mức vẫn ambiguous. Thiếu M1 giữ ambiguous. Không download. Gap SL fill open xấu hơn, gap TP cap target. MFE/MAE toàn nến exit là upper bound. R cộng dồn theo exit không phải portfolio/equity tiền thực.

## Thống kê và giới hạn
WR=wins/(wins+losses), n resolved luôn đi kèm; invalid/unresolved/ambiguous tách riêng. Wilson95 là tham chiếu iid; calendar circular block bootstrap7 ngày,1000 draws seed20261121 giữ các mã cùng ngày, ESS variance-ratio heuristic. Phân nhóm mô tả gồm OOS nhưng không tune; quantile bins chỉ fit in-sample. So sánh net expectancy từng mô hình với M0 bằng paired calendar blocks; CI Bonferroni98.75 cho4 contrasts, không giả định các event độc lập. Khác population nên không phải matched-trade causal estimate.
OOS cũ đã từng xem: đây là historical holdout tái sử dụng, KHÔNG prospective untouched. Coverage XAU ngắn hơn BTC/ZEC; bổ sung tổng hợp common calendar overlap. Tất cả chỉ mô phỏng giáo dục.

## Thiết kế báo cáo
Extension của docs/DESIGN.md: nền giấy #f4f3ef, ink #182a2b, accent #146f64, loss #b54d45; Cambria/Segoe UI/Consolas local, grid8px, radius4/8px, không animation. Variance3/motion1/density8/assets1/fidelity8. 21 mục, bảng cuộn ngang nội bộ, Plotly nhúng offline, chọn track và phân nhóm, theme sáng/tối. Ưu tiên mẫu số/CI và giới hạn, không trophy ranking.
