# Các kết quả thống kê thực tế hiện có — ba sản phẩm M1

Ngày rà soát: 24/11/2026. Dùng lại artifact đã kiểm định; hash của ba M1 Parquet và chín Parquet nghiên cứu khớp snapshot. Không tải dữ liệu, không tính lại chỉ báo, không thay quy tắc.

## Dữ liệu và thống kê hình thái

| Sản phẩm | Bắt đầu UTC | Kết thúc UTC | M1 hợp lệ | Nến đủ warm-up | Clean runs | Mean độ dài run | Mean intermediate |
|---|---|---|---:|---:|---:|---:|---:|
| BTCUSDT | 2019-12-31T00:00:00+00:00 | 2026-11-22T23:59:00+00:00 | 3627360 | 3626861 | 325916 | 1.950101 | 0.107480 |
| ZECUSDT | 2020-02-05T08:01:00+00:00 | 2026-11-22T23:59:00+00:00 | 3575039 | 3574540 | 315826 | 1.860467 | 0.167765 |
| XAUUSDT | 2025-12-11T08:05:00+00:00 | 2026-11-22T23:59:00+00:00 | 499195 | 463181 | 37968 | 2.262089 | 0.134031 |

Cả ba snapshot: duplicate=0, invalid=0, missing nội bộ=0; completeness nội bộ=100%. Mỗi mã còn thiếu 1440 phút tới cutoff, lịch đóng cửa chưa xác minh. XAU loại 35515 nến trước 05/01/2026 khỏi nghiên cứu nhưng giữ trong nguồn.
Clean run = đoạn liên tiếp tối đại theo convention mô tả. Intermediate đếm tới terminal hai wick đầu tiên; không phải phân bố của pattern gốc đã xác định. Không quy đổi số đoạn thành số trade.

## Hình học trên nến đủ warm-up

| Sản phẩm | Median Body/Range | Không wick trên (%) | Không wick dưới (%) |
|---|---:|---:|---:|
| BTCUSDT | 0.502601 | 27.4880 | 27.9671 |
| ZECUSDT | 0.487132 | 28.0793 | 28.4016 |
| XAUUSDT | 0.533022 | 29.4839 | 29.7290 |

## Giá thật sau quan sát

Cohort: terminal có hai wick cùng màu vùng EMA, sau clean run có ít nhất một nến impulse mô tả; chưa áp ngưỡng Doji. Neo Open thật nến sau terminal, so với Close thật sau h nến. Return có dấu theo hướng xu hướng; đơn vị bps, 1 bps=0,01%. Không phải thực thi giao dịch hoặc expectancy sau phí.

| Sản phẩm | Phút | N có kết quả | Mean (bps) | Median (bps) | P05 (bps) | P95 (bps) | Censored |
|---|---:|---:|---:|---:|---:|---:|---:|
| BTCUSDT | 1 | 36564 | -0.013826 | 0.000000 | -10.176858 | 10.347097 | 0 |
| BTCUSDT | 5 | 36564 | -0.086037 | -0.604195 | -21.640743 | 23.032026 | 0 |
| BTCUSDT | 15 | 36564 | -0.394440 | -1.583615 | -36.355692 | 39.505445 | 0 |
| BTCUSDT | 60 | 36563 | -0.095025 | -2.782061 | -70.393704 | 81.406118 | 1 |
| ZECUSDT | 1 | 37200 | -0.270600 | 0.000000 | -20.435910 | 20.194616 | 0 |
| ZECUSDT | 5 | 37200 | -0.615486 | 0.000000 | -45.017810 | 45.882309 | 0 |
| ZECUSDT | 15 | 37200 | -1.080649 | -2.271955 | -77.505432 | 79.956950 | 0 |
| ZECUSDT | 60 | 37199 | -1.394941 | -3.963535 | -150.741705 | 159.745488 | 1 |
| XAUUSDT | 1 | 4394 | -0.001708 | 0.000000 | -4.769071 | 4.815792 | 0 |
| XAUUSDT | 5 | 4394 | 0.010151 | -0.042807 | -10.498574 | 10.860597 | 0 |
| XAUUSDT | 15 | 4394 | 0.274169 | -0.130981 | -18.129941 | 20.652092 | 0 |
| XAUUSDT | 60 | 4394 | -0.044305 | -0.757904 | -36.883117 | 38.335294 | 0 |

P05/P95 là phân vị mẫu, không phải khoảng tin cậy của mean hoặc win rate. Không chọn horizon từ kết quả.

## Phân chia thời gian: mean biến động 15 phút

| Sản phẩm | Partition | N | Mean (bps) |
|---|---|---:|---:|
| BTCUSDT | in_sample | 19770 | -0.340194 |
| BTCUSDT | validation | 4983 | -0.678153 |
| BTCUSDT | out_of_sample | 11811 | -0.365542 |
| ZECUSDT | in_sample | 22017 | -0.976745 |
| ZECUSDT | validation | 6234 | -0.842733 |
| ZECUSDT | out_of_sample | 8949 | -1.502018 |
| XAUUSDT | in_sample | 0 | Không có dữ liệu |
| XAUUSDT | validation | 0 | Không có dữ liệu |
| XAUUSDT | out_of_sample | 4394 | 0.274169 |

IS trước 2024; validation năm 2024; OOS từ 2025. OOS hồi cứu từng được dùng trước đây, không phải holdout mới. Các quan sát có thể phụ thuộc/overlap; independent n chưa xác định.

## Quan sát chưa hoàn tất và outcome mơ hồ

| Sản phẩm | Mất vùng EMA trước terminal | Bị thay bởi run mới | Run censored tại split | Markout 60 phút censored tại split |
|---|---:|---:|---:|---:|
| BTCUSDT | 60776 | 626 | 0 | 1 |
| ZECUSDT | 58343 | 3358 | 1 | 1 |
| XAUUSDT | 6957 | 145 | 0 | 0 |

Những trạng thái trên là dừng chuỗi/censoring, không phải trade thua hoặc ambiguity intrabar. Số trường hợp cùng nến chạm TP/SL: chưa xác định (null), không phải 0; chưa có entry/SL/TP cụ thể để kiểm tra. Không giả định đường giá intrabar.

## Kết luận và giới hạn tái lập 75%

Win rate, CI win rate và p-value đối với 75% cho cả ba mã đều chưa xác định. Còn thiếu ngưỡng Doji, entry gốc, SL gốc và outcome-labeling (horizon, intrabar, censoring/chi phí); minimum/continuity và intermediate cũng chưa được định nghĩa đầy đủ. RR 1:1 không tự xác định các đại lượng này.
Các quy tắc xác nhận và công thức được giữ tại docs/HA_ORIGINAL_METHOD.md; convention mô tả tách riêng trong docs/HA_DESCRIPTIVE_PROTOCOL.md. Không tự áp giả định để đạt 75%, không dùng HA làm giá thị trường, không giao dịch thật.
Chi tiết phân bố theo năm/partition nằm trong reports/ha_descriptive/{symbol}.json và HTML tương ứng. Bằng chứng từ pipeline hiện có: 233 tests passed, audit SQL và QA offline đạt. Lần này chỉ đối chiếu/reuse artifact, không tuyên bố chạy lại toàn pipeline.
