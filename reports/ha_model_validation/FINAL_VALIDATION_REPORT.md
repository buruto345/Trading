# Model Validation Report — Phase 2

24/11/2026 · offline · H1 reference-boundary research

## 1. Executive Summary

Đã quét độc lập 7,666,079 nến nghiên cứu và 225,458 dòng observation của 15 nhóm. Các dòng giữa variants dùng chung nhiều nến, không phải từng đó mẫu độc lập.

Đối chiếu: 0 false positive, 0 false negative, 0 sai khác cấu trúc mẫu; 0 sai khác outcome. 45/45 dòng full-history được tái tính; số khác biệt thống kê vượt tolerance: 0.

Các số dưới đây là tỷ lệ outcome biên H1 với giá OHLC thật sau Doji, không phải win rate giao dịch. Tuyên bố 75% của tác giả, giá vào/stop chính xác và kết quả thực thi vẫn NOT VERIFIED.

| Task | Status | Evidence | Coverage | Limitations |
|---|---|---|---|---|
| T01 | WARNING | data_quality_audit.json | Toàn bộ 3 Parquet M1 | Thiếu đuôi 1 ngày/mã; chưa xác minh lịch đóng cửa hoặc parse lại ZIP nguồn. |
| T02 | PASS | independent_detection_audit.json; pattern_mismatches.csv | Toàn bộ nến và 15 nhóm mẫu | Đúng với đặc tả đóng băng; không xác nhận quy tắc của tác giả. |
| T03 | WARNING | ha_price_bias.csv; outside_boundaries.json | 4 trường giá × 4 phép đo × 15 nhóm | Giá HA tổng hợp; không chứng minh có thể khớp lệnh. |
| T04 | WARNING | lookahead_audit.json; source_review.json | 9 prefix, mọi variant; chỉ báo toàn lịch sử | Median-unit normalization có phụ thuộc toàn cột; nguồn sửa đổi có thể thay lịch sử. |
| T05 | PASS | data_leakage_audit.json | Mọi timestamp/nhãn partition | Full scope có thể dùng tương lai partition; không dùng nó làm đánh giá holdout. |
| T06 | PASS | outcome_reconciliation.json; ambiguity_audit.csv | Mọi observation, 2 scopes, 3 scenarios | M1 không xác định thứ tự hai biên trong một nến. |
| T07 | WARNING | observation_dependence.json | 15 nhóm; 30 cặp variant | Không ước lượng số mẫu độc lập; correlations là mô tả. |
| T08 | WARNING | monthly_statistics.csv; quarterly_statistics.csv; yearly_statistics.csv | Mọi kỳ kể cả kỳ rỗng | CI theo kỳ ngắn ít block; chưa stationarity. |
| T09 | WARNING | market_condition_statistics.csv; HA_VALIDATION_PROTOCOL.md | Mọi nhóm đã định trước, kể cả unknown/rỗng | Phân nhóm chẩn đoán, không bộ lọc hoặc quan hệ nhân quả. |
| T10 | WARNING | directional_statistics.csv; directional_monthly_statistics.csv | Cả bullish và bearish × 15 | Chênh lệch không chứng minh nguyên nhân hay hướng giao dịch. |
| T11 | WARNING | statistical_reliability.json; bootstrap_sensitivity.csv | 45 full + 135 partition + 237 yearly cũ | CI pointwise; phụ thuộc block, selection/survivorship và tái sử dụng dữ liệu. |
| T12 | WARNING | oos_review.csv; HA_VALIDATION_PROTOCOL.md | IS/validation/retrospective OOS, mọi nhóm | Holdout mới: NOT VERIFIED; chưa có dữ liệu chưa từng xem. |
| T13 | WARNING | reproducibility.json; baseline.json; tests.xml | Hash, seed, kết quả và môi trường hiện tại | Phase1 không ghi trực tiếp versions trong execution.json; môi trường cũ chính xác chưa xác minh. |
| T14 | PASS | FINAL_VALIDATION_REPORT.md/html; browser_qa.json | 17 phần, bảng audit và chart offline | PASS chỉ sau browser QA đạt; không nâng mức xác minh trading. |

## 2. Existing Research Overview

M1 Binance USD-M perpetual BTCUSDT/ZECUSDT/XAUUSDT. EMA100 trên HA Close, warm-up500, pullback ≥2 clean candles, intermediate ngược màu, Doji đúng màu có hai wick và range mở rộng so ít nhất một trong hai nến trước; không giới hạn horizon. Giữ nguyên mọi quy tắc đóng băng.

D01–D05 = 5/10/20/30/40% body/range do người dùng chọn. H1 lấy HA Close làm mốc, wick HA đối hướng làm biên bất lợi, biên thuận cách đều RR1:1. Precedence opposite-Doji là convention nghiên cứu, chưa xác minh tác giả.

Audit Phase1 chỉ kiểm tra chi tiết 543 mẫu. Phase2 dùng reference suffix-search, lfilter/EWM và first-passage từng nến riêng, không tái sử dụng state machine. Bộ 259 tests trước đây gồm cả confluence chưa commit; phạm vi công bố cũ là202 tests.

## 3. Data Quality Validation

Không sửa/interpolate/tải bù dữ liệu. Completeness tính trên lưới UTC giữa nến đầu/cuối; không có nghĩa đủ dữ liệu tới cutoff. Ba mã thiếu 1.440 phút đuôi đến 24/11/2026 00:00 UTC.

XAUUSDT là perpetual đúng mã, không phải vàng giao ngay hoặc Forex. Loại lịch sử trước05/01/2026 theo quy tắc cũ. Giá trị zero-volume không đảm bảo thanh khoản/fillability. Audit đọc toàn processed M1; không tái parse từng archive nguồn.

| symbol | total_candles | research_candles | research_period_exclusions | warmup_exclusions | indicator_ready | duplicate | invalid | missing_internal | missing_tail_minutes | zero_volume_candles |
|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 3627360 | 3627360 | 0 | 499 | 3626861 | 0 | 0 | 0 | 1440 | 369 |
| ZECUSDT | 3575039 | 3575039 | 0 | 499 | 3574540 | 0 | 0 | 0 | 1440 | 20166 |
| XAUUSDT | 499195 | 463680 | 35515 | 499 | 463181 | 0 | 0 | 0 | 1440 | 11538 |

## 4. Independent Pattern Detection Audit

Reference xác định candidate Doji rồi tìm suffix ngược màu hợp lệ và cặp clean đầu tiên sau rào cản; khác cấu trúc state machine đang kiểm tra. Toàn lịch sử được quét để tìm cả mẫu thiếu. So start/end pullback, số intermediate, direction, timestamp và nhãn hình học.

Chỉ báo HA được tái tính trong bộ nhớ bằng bộ lọc tuyến tính; EMA bằng EWM. Không ghi đè cached features. So số học với tolerance512eps tương đối, nhưng classification vẫn đúng tolerance32eps đã đóng băng. Sai khác chi tiết (nếu có) ở CSV và JSON.

| symbol | variant | candles_scanned | original_patterns | reference_patterns | matching_keys | false_positives | false_negatives | classification_mismatches |
|---|---|---|---|---|---|---|---|---|
| BTCUSDT | D01 | 3627360 | 6009 | 6009 | 6009 | 0 | 0 | 0 |
| BTCUSDT | D02 | 3627360 | 11731 | 11731 | 11731 | 0 | 0 | 0 |
| BTCUSDT | D03 | 3627360 | 22776 | 22776 | 22776 | 0 | 0 | 0 |
| BTCUSDT | D04 | 3627360 | 32824 | 32824 | 32824 | 0 | 0 | 0 |
| BTCUSDT | D05 | 3627360 | 40912 | 40912 | 40912 | 0 | 0 | 0 |
| ZECUSDT | D01 | 3575039 | 5413 | 5413 | 5413 | 0 | 0 | 0 |
| ZECUSDT | D02 | 3575039 | 10603 | 10603 | 10603 | 0 | 0 | 0 |
| ZECUSDT | D03 | 3575039 | 19909 | 19909 | 19909 | 0 | 0 | 0 |
| ZECUSDT | D04 | 3575039 | 27874 | 27874 | 27874 | 0 | 0 | 0 |
| ZECUSDT | D05 | 3575039 | 33797 | 33797 | 33797 | 0 | 0 | 0 |
| XAUUSDT | D01 | 463680 | 669 | 669 | 669 | 0 | 0 | 0 |
| XAUUSDT | D02 | 463680 | 1333 | 1333 | 1333 | 0 | 0 | 0 |
| XAUUSDT | D03 | 463680 | 2632 | 2632 | 2632 | 0 | 0 | 0 |
| XAUUSDT | D04 | 463680 | 3904 | 3904 | 3904 | 0 | 0 | 0 |
| XAUUSDT | D05 | 463680 | 5072 | 5072 | 5072 | 0 | 0 | 0 |

## 5. Heikin Ashi Price Bias

ha_price_bias.csv cung cấp signed/absolute/relative-percent differences cho Open/High/Low/Close, mean/median/std/min/max và p01/05/25/75/95/99 cho tất cả15 nhóm. Biểu đồ hiển thị median và p05–p95 của chênh HA Close, không phải CI.

Một số market Close đã ngoài biên H1 ngay lúc Doji đóng. Việc chờ nến sau có thể vẫn cho outcome H1 success, nhưng không tạo bằng chứng vào lệnh được tại HA Close. Phân bố khoảng lệch theo đơn vị risk của các trường hợp này lưu riêng.

| symbol | variant | patterns | count | frequency |
|---|---|---|---|---|
| BTCUSDT | D01 | 6009 | 353 | 0.0587452 |
| BTCUSDT | D02 | 11731 | 666 | 0.0567727 |
| BTCUSDT | D03 | 22776 | 1271 | 0.0558044 |
| BTCUSDT | D04 | 32824 | 1848 | 0.0563003 |
| BTCUSDT | D05 | 40912 | 2458 | 0.0600802 |
| ZECUSDT | D01 | 5413 | 696 | 0.128579 |
| ZECUSDT | D02 | 10603 | 1416 | 0.133547 |
| ZECUSDT | D03 | 19909 | 2696 | 0.135416 |
| ZECUSDT | D04 | 27874 | 3861 | 0.138516 |
| ZECUSDT | D05 | 33797 | 4831 | 0.142942 |
| XAUUSDT | D01 | 669 | 52 | 0.077728 |
| XAUUSDT | D02 | 1333 | 108 | 0.0810203 |
| XAUUSDT | D03 | 2632 | 233 | 0.0885258 |
| XAUUSDT | D04 | 3904 | 356 | 0.0911885 |
| XAUUSDT | D05 | 5072 | 483 | 0.0952287 |

## 6. Look-Ahead Bias

Kiểm tra prefix 1000/10000/50000 nến cho mỗi mã, mỗi variant; so kết quả từ dữ liệu cắt ngắn với full history, cả reference và Phase1. Outcome chỉ bắt đầu nến kế tiếp. Chỉ báo đối chiếu trên toàn lịch sử; không tuyên bố prefix sampling là chứng minh tuyệt đối. Bổ sung 15 prefix normalization trên source timestamps và đối chiếu mọi trường giá/geometry đã lưu: supplemental_field_audit.json.

Review phát hiện thiết kế normalization dùng median toàn cột để đoán đơn vị epoch; dữ liệu trộn đơn vị hoặc revision có thể làm quá khứ thay đổi. Snapshot cố định dùng cùng đơn vị, không thấy sai lệch lịch sử. Conflict quarantine cũng có thể đổi lịch sử nếu nguồn sửa. Cần khóa schema/unit khi áp dụng bộ nhập cho dữ liệu khác.

| symbol | prefixes | mismatch_variants |
|---|---|---|
| BTCUSDT | 1000,10000,50000 | 0 |
| ZECUSDT | 1000,10000,50000 | 0 |
| XAUUSDT | 1000,10000,50000 | 0 |

## 7. Data Leakage

IS trước01/01/2024; validation2024; retrospective OOS từ01/01/2025. Membership dựa giờ Doji đóng. Formation và chỉ báo dùng lịch sử quá khứ qua split, không khởi tạo lại EMA tại split. Partition outcome kết thúc tại biên; full-history scope lưu riêng.

Các thống kê subgroup hồi cứu không đi ngược vào detector. OOS này đã được xem nhiều lần, không là holdout độc lập.

| symbol | observations | partition_assignment_errors | confirmation_time_errors | partition_end_beyond_boundary | full_outcome_crossing_partition | scope_label_changes |
|---|---|---|---|---|---|---|
| BTCUSDT | 114252 | 0 | 0 | 0 | 0 | 0 |
| ZECUSDT | 97596 | 0 | 0 | 0 | 0 | 0 |
| XAUUSDT | 13610 | 0 | 0 | 0 | 0 | 0 |

## 8. Intrabar Ambiguity

W=success, L=failure, A=ambiguous, U=unresolved. Conservative=W/(W+L+A); optimistic=(W+A)/(W+L+A); excluded=W/(W+L). U và invalid luôn báo riêng, không ép thành thất bại.

Nếu open đã ngoài một biên, open được xét trước; nếu open ở giữa và high/low chạm cả hai biên trong cùng nến thì ambiguous. Không suy thứ tự intrabar. Optimistic−conservative=A/(W+L+A). First-passage độc lập kiểm tra từng nến tới chạm đầu/cuối dữ liệu/gap/split, không horizon60.

| symbol | variant | scenario | patterns | observed_successes | observed_failures | ambiguous | unresolved | observed_proportion | optimistic_conservative_gap |
|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | D01 | conservative | 6009 | 3759 | 1933 | 317 | 0 | 0.625562 | 0.0527542 |
| BTCUSDT | D01 | optimistic | 6009 | 3759 | 1933 | 317 | 0 | 0.678316 | 0.0527542 |
| BTCUSDT | D01 | excluded | 6009 | 3759 | 1933 | 317 | 0 | 0.660401 | 0.0527542 |
| BTCUSDT | D02 | conservative | 11731 | 7515 | 3584 | 632 | 0 | 0.64061 | 0.0538744 |
| BTCUSDT | D02 | optimistic | 11731 | 7515 | 3584 | 632 | 0 | 0.694485 | 0.0538744 |
| BTCUSDT | D02 | excluded | 11731 | 7515 | 3584 | 632 | 0 | 0.677088 | 0.0538744 |
| BTCUSDT | D03 | conservative | 22776 | 15121 | 6484 | 1170 | 1 | 0.66393 | 0.0513721 |
| BTCUSDT | D03 | optimistic | 22776 | 15121 | 6484 | 1170 | 1 | 0.715302 | 0.0513721 |
| BTCUSDT | D03 | excluded | 22776 | 15121 | 6484 | 1170 | 1 | 0.699884 | 0.0513721 |
| BTCUSDT | D04 | conservative | 32824 | 22454 | 8685 | 1684 | 1 | 0.684093 | 0.0513055 |
| BTCUSDT | D04 | optimistic | 32824 | 22454 | 8685 | 1684 | 1 | 0.735399 | 0.0513055 |
| BTCUSDT | D04 | excluded | 32824 | 22454 | 8685 | 1684 | 1 | 0.721089 | 0.0513055 |
| BTCUSDT | D05 | conservative | 40912 | 28800 | 10051 | 2060 | 1 | 0.703967 | 0.0503532 |
| BTCUSDT | D05 | optimistic | 40912 | 28800 | 10051 | 2060 | 1 | 0.75432 | 0.0503532 |
| BTCUSDT | D05 | excluded | 40912 | 28800 | 10051 | 2060 | 1 | 0.741294 | 0.0503532 |
| ZECUSDT | D01 | conservative | 5413 | 3153 | 1916 | 344 | 0 | 0.582487 | 0.0635507 |
| ZECUSDT | D01 | optimistic | 5413 | 3153 | 1916 | 344 | 0 | 0.646037 | 0.0635507 |
| ZECUSDT | D01 | excluded | 5413 | 3153 | 1916 | 344 | 0 | 0.622016 | 0.0635507 |
| ZECUSDT | D02 | conservative | 10603 | 6339 | 3612 | 652 | 0 | 0.59785 | 0.061492 |
| ZECUSDT | D02 | optimistic | 10603 | 6339 | 3612 | 652 | 0 | 0.659342 | 0.061492 |
| ZECUSDT | D02 | excluded | 10603 | 6339 | 3612 | 652 | 0 | 0.637021 | 0.061492 |
| ZECUSDT | D03 | conservative | 19909 | 12344 | 6384 | 1181 | 0 | 0.620021 | 0.0593199 |
| ZECUSDT | D03 | optimistic | 19909 | 12344 | 6384 | 1181 | 0 | 0.679341 | 0.0593199 |
| ZECUSDT | D03 | excluded | 19909 | 12344 | 6384 | 1181 | 0 | 0.65912 | 0.0593199 |
| ZECUSDT | D04 | conservative | 27874 | 17867 | 8411 | 1596 | 0 | 0.640992 | 0.0572577 |
| ZECUSDT | D04 | optimistic | 27874 | 17867 | 8411 | 1596 | 0 | 0.698249 | 0.0572577 |
| ZECUSDT | D04 | excluded | 27874 | 17867 | 8411 | 1596 | 0 | 0.679922 | 0.0572577 |
| ZECUSDT | D05 | conservative | 33797 | 22302 | 9677 | 1818 | 0 | 0.659881 | 0.0537918 |
| ZECUSDT | D05 | optimistic | 33797 | 22302 | 9677 | 1818 | 0 | 0.713673 | 0.0537918 |
| ZECUSDT | D05 | excluded | 33797 | 22302 | 9677 | 1818 | 0 | 0.697395 | 0.0537918 |
| XAUUSDT | D01 | conservative | 669 | 427 | 198 | 44 | 0 | 0.638266 | 0.0657698 |
| XAUUSDT | D01 | optimistic | 669 | 427 | 198 | 44 | 0 | 0.704036 | 0.0657698 |
| XAUUSDT | D01 | excluded | 669 | 427 | 198 | 44 | 0 | 0.6832 | 0.0657698 |
| XAUUSDT | D02 | conservative | 1333 | 850 | 400 | 83 | 0 | 0.637659 | 0.0622656 |
| XAUUSDT | D02 | optimistic | 1333 | 850 | 400 | 83 | 0 | 0.699925 | 0.0622656 |
| XAUUSDT | D02 | excluded | 1333 | 850 | 400 | 83 | 0 | 0.68 | 0.0622656 |
| XAUUSDT | D03 | conservative | 2632 | 1724 | 747 | 161 | 0 | 0.655015 | 0.0611702 |
| XAUUSDT | D03 | optimistic | 2632 | 1724 | 747 | 161 | 0 | 0.716185 | 0.0611702 |
| XAUUSDT | D03 | excluded | 2632 | 1724 | 747 | 161 | 0 | 0.697693 | 0.0611702 |
| XAUUSDT | D04 | conservative | 3904 | 2640 | 1053 | 211 | 0 | 0.67623 | 0.0540471 |
| XAUUSDT | D04 | optimistic | 3904 | 2640 | 1053 | 211 | 0 | 0.730277 | 0.0540471 |
| XAUUSDT | D04 | excluded | 3904 | 2640 | 1053 | 211 | 0 | 0.714866 | 0.0540471 |
| XAUUSDT | D05 | conservative | 5072 | 3576 | 1247 | 249 | 0 | 0.705047 | 0.0490931 |
| XAUUSDT | D05 | optimistic | 5072 | 3576 | 1247 | 249 | 0 | 0.75414 | 0.0490931 |
| XAUUSDT | D05 | excluded | 5072 | 3576 | 1247 | 249 | 0 | 0.741447 | 0.0490931 |

## 9. Observation Dependence

Interval [doji+1,end+1) căn theo bar; end là cuối nến chứa chạm kể cả open-gap. Đây là overlap bảo thủ theo bar, không concurrency vị thế. Báo overlap bất kỳ và overlap với trước riêng.

Các variant dùng chung observations; tăng threshold cũng thay rào cản opposite-Doji nên không mặc định nested hoàn toàn. JSON cung cấp intersection/Jaccard/a_not_in_b, serial correlation lag1/5/10/20, phân tán daily counts và bull/bear correlation. Không có effective independent n; 45 hàng không phải45 thí nghiệm độc lập.

| symbol | variant | patterns | overlapping_with_prior | overlapping_any | overlapping_any_fraction | maximum_concurrent | bull_bear_daily_rate_correlation | bull_bear_days |
|---|---|---|---|---|---|---|---|---|
| BTCUSDT | D01 | 6009 | 1 | 2 | 0.000332834 | 2 | None | 0 |
| BTCUSDT | D02 | 11731 | 7 | 14 | 0.00119342 | 2 | 0.319046 | 17 |
| BTCUSDT | D03 | 22776 | 16 | 32 | 0.00140499 | 2 | -0.0539293 | 398 |
| BTCUSDT | D04 | 32824 | 48 | 95 | 0.00289422 | 2 | 0.0326582 | 1149 |
| BTCUSDT | D05 | 40912 | 85 | 168 | 0.00410637 | 2 | 0.0311306 | 1645 |
| ZECUSDT | D01 | 5413 | 2 | 4 | 0.000738962 | 2 | None | 0 |
| ZECUSDT | D02 | 10603 | 3 | 6 | 0.000565878 | 2 | -0.459738 | 8 |
| ZECUSDT | D03 | 19909 | 14 | 28 | 0.0014064 | 2 | 0.032902 | 214 |
| ZECUSDT | D04 | 27874 | 34 | 68 | 0.00243955 | 2 | 0.0200316 | 762 |
| ZECUSDT | D05 | 33797 | 68 | 129 | 0.00381691 | 2 | 0.044707 | 1167 |
| XAUUSDT | D01 | 669 | 0 | 0 | 0 | 1 | None | 0 |
| XAUUSDT | D02 | 1333 | 0 | 0 | 0 | 1 | None | 2 |
| XAUUSDT | D03 | 2632 | 3 | 6 | 0.00227964 | 2 | -0.0975516 | 39 |
| XAUUSDT | D04 | 3904 | 7 | 14 | 0.00358607 | 2 | -0.0129667 | 119 |
| XAUUSDT | D05 | 5072 | 26 | 47 | 0.00926656 | 2 | 0.00230897 | 192 |

## 10. Temporal Robustness

Bảng tháng/quý/năm bao gồm toàn bộ kỳ của research interval, cả kỳ rỗng và bất lợi. Outcome full scope gán kỳ theo confirmation; nó có thể kết thúc kỳ sau, nên đây là cohort descriptive chứ không phải censored backtest theo kỳ.

Tái đối chiếu237 hàng năm cũ. Subgroup CI moving-block500 lần khi ≥30 mẫu và span≥14 ngày; warning khi ít mẫu hoặc span<56 ngày. Trường hợp không đủ điều kiện để trống CI chính; Wilson vẫn chỉ tham chiếu IID. Biến động giữa kỳ không chứng minh nguyên nhân.

| symbol | variant | months | empty_months | warning_months | monthly_min | monthly_max | monthly_std |
|---|---|---|---|---|---|---|---|
| BTCUSDT | D01 | 84 | 1 | 84 | 0.5 | 0.816667 | 0.0646511 |
| BTCUSDT | D02 | 84 | 0 | 84 | 0.523077 | 0.793893 | 0.0469346 |
| BTCUSDT | D03 | 84 | 0 | 84 | 0.569507 | 0.833333 | 0.0368896 |
| BTCUSDT | D04 | 84 | 0 | 84 | 0.591549 | 0.833333 | 0.0361524 |
| BTCUSDT | D05 | 84 | 0 | 84 | 0.618462 | 0.875 | 0.0348011 |
| ZECUSDT | D01 | 82 | 0 | 82 | 0.433962 | 0.790698 | 0.0676566 |
| ZECUSDT | D02 | 82 | 0 | 82 | 0.525424 | 0.78 | 0.0552954 |
| ZECUSDT | D03 | 82 | 0 | 82 | 0.556522 | 0.768627 | 0.0503247 |
| ZECUSDT | D04 | 82 | 0 | 82 | 0.566766 | 0.765714 | 0.0448119 |
| ZECUSDT | D05 | 82 | 0 | 82 | 0.576659 | 0.78453 | 0.0432822 |
| XAUUSDT | D01 | 11 | 0 | 11 | 0.612245 | 0.757576 | 0.0472004 |
| XAUUSDT | D02 | 11 | 0 | 11 | 0.588785 | 0.761905 | 0.0552702 |
| XAUUSDT | D03 | 11 | 0 | 11 | 0.643979 | 0.766467 | 0.0349287 |
| XAUUSDT | D04 | 11 | 0 | 11 | 0.632653 | 0.797571 | 0.041107 |
| XAUUSDT | D05 | 11 | 0 | 11 | 0.671196 | 0.822823 | 0.0388108 |

## 11. Market Condition Analysis

Protocol viết trước subgroup results: score=log return60/(std60 log-return một nến ×sqrt60). >1 rising, <−1 falling, còn lại sideways. Vol thấp/vừa/cao so quantile1/3 và2/3 của1440 std60 quá khứ, shift1, min720; reset theo gap. Unknown khi thiếu lịch sử.

Báo mọi category và16 tổ hợp trend×vol kể cả unknown/rỗng trong CSV. Đây là nhãn mô tả có sẵn tại timestamp, không thêm filter, không chọn ngưỡng theo75%. Khác biệt giữa nhóm không chứng minh phân loại là nguyên nhân.

## 12. Bullish and Bearish Analysis

Báo riêng hai chiều và cả3 scenarios. CSV tháng theo hướng cho temporal stability; bảng dưới gồm mẫu số, ambiguity, CI và mức lệch HA Close trung bình. Sample imbalance và phân bố giá/volatility khác nhau có thể góp phần vào khác biệt; không thể kết luận giải thích nhân quả hoặc khuyến nghị hướng.

CI mỗi hướng là pointwise; không suy chênh lệch có ý nghĩa từ hai CI riêng lẻ. Daily cross-direction correlation chỉ dùng ngày cả hai có≥5 resolved observations và báo số ngày đủ điều kiện.

| symbol | variant | direction | patterns | observed_proportion | ambiguity_rate | ci95_block_low | ci95_block_high | mean_signed_ha_close_difference | mean_absolute_ha_close_difference | outside_boundary_count |
|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | D01 | -1 | 2930 | 0.672202 | 0.0546075 | 0.654825 | 0.689174 | 10.598 | 14.5613 | 159 |
| BTCUSDT | D01 | 1 | 3079 | 0.649213 | 0.0509906 | 0.631753 | 0.666686 | -9.62583 | 14.1015 | 194 |
| BTCUSDT | D02 | -1 | 5693 | 0.685192 | 0.0581416 | 0.672587 | 0.69632 | 11.6941 | 15.0379 | 313 |
| BTCUSDT | D02 | 1 | 6038 | 0.669514 | 0.0498509 | 0.656967 | 0.682068 | -10.6864 | 14.3262 | 353 |
| BTCUSDT | D03 | -1 | 10969 | 0.7051 | 0.0543349 | 0.696482 | 0.714288 | 13.564 | 15.9587 | 607 |
| BTCUSDT | D03 | 1 | 11807 | 0.695068 | 0.0486152 | 0.686836 | 0.703562 | -12.3732 | 14.8543 | 664 |
| BTCUSDT | D04 | -1 | 15921 | 0.72509 | 0.0532002 | 0.71745 | 0.732933 | 14.8079 | 16.6471 | 902 |
| BTCUSDT | D04 | 1 | 16903 | 0.717336 | 0.0495178 | 0.708941 | 0.724282 | -13.4223 | 15.3306 | 946 |
| BTCUSDT | D05 | -1 | 19878 | 0.743327 | 0.051967 | 0.736246 | 0.750774 | 15.7274 | 17.1544 | 1188 |
| BTCUSDT | D05 | 1 | 21034 | 0.739378 | 0.0488257 | 0.731541 | 0.745896 | -14.3674 | 15.8326 | 1270 |
| ZECUSDT | D01 | -1 | 2639 | 0.619451 | 0.061008 | 0.600116 | 0.640528 | 0.0873759 | 0.116021 | 332 |
| ZECUSDT | D01 | 1 | 2774 | 0.624469 | 0.0659697 | 0.605824 | 0.643814 | -0.0924333 | 0.123453 | 364 |
| ZECUSDT | D02 | -1 | 5241 | 0.629261 | 0.0597214 | 0.615579 | 0.643943 | 0.0877604 | 0.111029 | 709 |
| ZECUSDT | D02 | 1 | 5362 | 0.644635 | 0.0632227 | 0.630216 | 0.658719 | -0.0969065 | 0.122828 | 707 |
| ZECUSDT | D03 | -1 | 9944 | 0.656073 | 0.0570193 | 0.645249 | 0.66676 | 0.0997931 | 0.116794 | 1378 |
| ZECUSDT | D03 | 1 | 9965 | 0.662175 | 0.0616157 | 0.650954 | 0.672161 | -0.111521 | 0.13065 | 1318 |
| ZECUSDT | D04 | -1 | 13977 | 0.677788 | 0.0543035 | 0.668256 | 0.687167 | 0.108076 | 0.121473 | 2004 |
| ZECUSDT | D04 | 1 | 13897 | 0.682083 | 0.0602288 | 0.673537 | 0.69 | -0.120595 | 0.135493 | 1857 |
| ZECUSDT | D05 | -1 | 17045 | 0.698281 | 0.0511 | 0.689597 | 0.706891 | 0.116148 | 0.126808 | 2493 |
| ZECUSDT | D05 | 1 | 16752 | 0.696488 | 0.0565306 | 0.6892 | 0.70453 | -0.128503 | 0.140527 | 2338 |
| XAUUSDT | D01 | -1 | 337 | 0.670886 | 0.0623145 | 0.62604 | 0.713787 | 0.457337 | 0.65339 | 22 |
| XAUUSDT | D01 | 1 | 332 | 0.695793 | 0.0692771 | 0.655418 | 0.740318 | -0.55262 | 0.670934 | 30 |
| XAUUSDT | D02 | -1 | 679 | 0.687697 | 0.0662739 | 0.658706 | 0.71648 | 0.502703 | 0.694124 | 50 |
| XAUUSDT | D02 | 1 | 654 | 0.672078 | 0.058104 | 0.634143 | 0.704307 | -0.547813 | 0.654748 | 58 |
| XAUUSDT | D03 | -1 | 1330 | 0.702008 | 0.0639098 | 0.676336 | 0.725422 | 0.571436 | 0.721162 | 113 |
| XAUUSDT | D03 | 1 | 1302 | 0.693312 | 0.0583717 | 0.669105 | 0.712231 | -0.58773 | 0.680883 | 120 |
| XAUUSDT | D04 | -1 | 1958 | 0.72397 | 0.0582227 | 0.699295 | 0.745145 | 0.64234 | 0.750111 | 177 |
| XAUUSDT | D04 | 1 | 1946 | 0.705787 | 0.0498458 | 0.688317 | 0.720293 | -0.625948 | 0.693345 | 179 |
| XAUUSDT | D05 | -1 | 2547 | 0.749896 | 0.0518257 | 0.726757 | 0.768702 | 0.672759 | 0.749302 | 241 |
| XAUUSDT | D05 | 1 | 2525 | 0.732973 | 0.0463366 | 0.717748 | 0.746251 | -0.642911 | 0.694317 | 242 |

## 13. Statistical Reliability

Independent bootstrap dùng tổng cộng dồn block thay cho expanded day indices; cùng seed20261124, calendar days kể cả ngày trống, cùng2000 draws. Tái tính point estimates, denominators, Wilson bằng NormalDist và block CI. Sensitivity1/3/7/14/28 ngày định trước, không chọn block thuận lợi.

Unweighted mean của5 tỷ lệ khác ratio gộp các dòng có trọng số. Cả hai đều tái sử dụng variant observations, không là ước lượng độc lập cho instrument. arithmetic_means lưu cả hai với nhãn rõ. Từng nhóm instrument×variant là đơn vị báo cáo chính.

CI không khắc phục selection/survivorship, single-venue, nonstationarity, nested samples và multiple comparisons. Không tính p-value để đạt75%, không suy profitability từ CI hẹp.

| scope | matched_rows | expected_rows | discrepancies | max_numeric_difference |
|---|---|---|---|---|
| full_history | 45 | 45 | 0 | 1.11022e-16 |
| partitioned | 135 | 135 | 0 | 1.11022e-16 |
| yearly | 237 | 237 | 0 | 0 |

## 14. Out-of-Sample Review

135 hàng IS/validation/retrospective OOS đều đối chiếu. XAU không có IS/validation trong research period: giữ hàng rỗng, không bịa kết quả. CSV thêm body ratio, absolute HA Close difference và outside-boundary rate để so thay đổi dữ liệu.

Protocol holdout sau: khóa code/config/hash và khoảng lịch chưa từng xem trước khi nhận dữ liệu; giữ warm-up lịch sử; cắt outcome tại cuối holdout; báo tất cả mã/variant/scenario, missingness/ambiguity/CI; không retune. Phase2 không tải hoặc tạo kết quả holdout mới.

## 15. Reproducibility

Commit gốc fed1f51df2781990795339e69509b31bc701bad3. 338/338 file baseline không đổi. Input/config/source hashes tại baseline.json; code audit, commands, versions, seed và reconciliation tại reproducibility.json. Số tests hiện tại: {'tests': 278, 'failures': 0, 'errors': 0, 'skipped': 0}. Các tests confluence tồn tại trong workspace nhưng không thuộc commit Phase1.

Phase1 execution.json không ghi dependency versions trực tiếp: kết quả tái lập trong môi trường hiện tại đã đóng băng; exact historical environment chưa được chứng minh. CSV Phase1 có rounding10 chữ số; đối chiếu thống kê dùng JSON full precision.

Chạy: .\.venv\Scripts\python.exe scripts\run_ha_validation.py rồi scripts\report_ha_validation.py. Không gọi collector/network; dữ liệu gốc và kết quả cũ được giữ. Các lỗi integration của audit lúc phát triển được sửa trước lần chạy hoàn tất, không sửa engine Phase1.

## 16. Limitations

External validity và real-world execution: NOT VERIFIED. Chưa xác định mapping outcome tác giả, entry/stop thực tế, tick path, spread, fees, funding, slippage, fillability; H1 không phải P&L. Nguồn chỉ một venue và3 sản phẩm được chọn trước; không đại diện mọi thị trường.

Thiếu đuôi dữ liệu, tuổi lịch sử XAU ngắn, calendar đóng cửa chưa xác minh; warm-up và ngày bắt đầu XAU là conventions. Bootstrap giả định phụ thuộc được block đại diện; không loại toàn bộ dependence hoặc nonstationarity.

Software correctness được kiểm tra theo đặc tả đóng băng, không xác minh đặc tả là bản gốc của tác giả. Audit độc lập về thuật toán nhưng vẫn trong cùng dự án/môi trường; không là đánh giá bên thứ ba có dữ liệu độc lập.

## 17. Final Validation Conclusion

Software: đối chiếu detector/outcome/statistics đạt trong phạm vi ghi nhận. 45/45 full-history rows tái tính, 0 sai khác vượt tolerance. Không sửa kết quả cũ.

Statistical reliability vẫn có WARNING do dependence, ambiguity, stationarity, selection và holdout hồi cứu. External validity, lợi nhuận, win rate thực thi và tái lập tuyên bố75% vẫn NOT VERIFIED. Không chọn sản phẩm/threshold “tốt nhất”.

