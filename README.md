# ICT Quantitative Research

Nghiên cứu lịch sử offline, M5, đúng mã XAUUSDT/BTCUSDT/ZECUSDT Binance USD-M perpetual.
Ba điều kiện kết hợp: Liquidity Sweep + MSS + FVG; RR giả định1:2. Không live trading.

## Chạy lại (PowerShell, từ thư mục project)

```powershell
.\.venv\Scripts\python.exe scripts\run_pipeline.py
```

Pipeline tải/cache dữ liệu công khai, chạy test, nhận diện và mô phỏng, thống kê rồi xuất `reports/ICT_Quantitative_Research_Report.html`.
Pipeline cuối cũng chạy browser QA bằng Chrome headless ở chế độ offline rồi nhúng kết quả kiểm tra vào HTML. Python dùng trong lần đã xác minh:3.14.4 trên Windows.
Tái lập trên snapshot dữ liệu đã xác minh bằng `--skip-collection`; xuất lại báo cáo từ kết quả bằng `--report-only`. Chạy không có cờ sẽ kiểm tra thêm archive công khai đến cutoff20/11/2026; tệp mới xuất bản muộn có thể thay đổi coverage, và manifest sẽ ghi lại.
Kiểm tra số liệu độc lập: `.\.venv\Scripts\python.exe scripts\audit_results.py`. Kiểm tra giao diện offline: `.\.venv\Scripts\python.exe scripts\browser_qa.py` (Google Chrome cài sẵn).
Để tạo môi trường mới: `python -m venv .venv`, rồi `.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt`.

## Tài liệu và bằng chứng

- `docs/MODEL_SPECIFICATION.md`: quy tắc đã xác nhận.
- `docs/RESEARCH_ASSUMPTIONS.md`: cách diễn giải thí nghiệm và giới hạn.
- `docs/RESEARCH_PLAN.md`: protocol định trước; `docs/ARCHITECTURE.md`: module.
- `data/manifests/historical_data_manifest.json`: provenance, integrity, missing/duplicate.
- `reports/results/`: patterns, simulations, rejected, statistics, test XML và browser evidence.
- `logs/`: log chạy; `PROGRESS.md`: checkpoint.

Mở HTML trực tiếp không cần Internet. Bộ lọc chỉ cập nhật vùng khám phá tương tác được đánh dấu; các bảng kiểm định cố định giữ đúng population ghi tại tiêu đề. Dữ liệu synthetic chỉ phục vụ test, không đưa vào thống kê lịch sử.
Tổng hợp weight1 mỗi observation. Win Rate trên resolved phải đọc cùng unresolved/ambiguous và CI; không suy ra hiệu quả giao dịch tương lai.

## Snapshot đã thực thi

1.530.912 nến M5 dùng nghiên cứu, 10.275 patterns, 9.987 resolved, WR32.99% (Wilson95%32.08–33.92%), 286 unresolved và2 ambiguous. 96 tests passed, coverage83.26%; 41 charts kiểm tra offline ở4 kích thước. Net expectancy−0.224R ở giả định10bps round-trip; OOS−0.269R. XAU chỉ từ05/01/2026, không thay bằng sản phẩm khác. Xem báo cáo để đọc giới hạn và khoảng bootstrap.

## Nghiên cứu Heikin Ashi – EMA 100 – Clean Pullback – Doji (M1)

Nhánh độc lập, chỉ nghiên cứu lịch sử offline. Không suy M1 từ M5 và không thay
đổi mô hình ICT. Tuyên bố 75% với RR 1:1 **chưa được kiểm chứng**: thiếu ngưỡng
Doji, entry, stop-loss và định nghĩa outcome. Pipeline hiện tính chỉ báo/thống kê
mô tả; không tự dựng quy tắc, tín hiệu hoặc giao dịch thắng/thua.

```powershell
# Tải toàn bộ archive M1 có sẵn trong phạm vi config, chạy tests, phân tích và QA
.\.venv\Scripts\python.exe scripts\run_ha_research.py
# Tái lập offline từ ZIP/Parquet/manifest đã lưu, không truy cập mạng
.\.venv\Scripts\python.exe scripts\run_ha_research.py --skip-collection
# Chỉ thu thập M1 hoặc chạy lại audit/browser QA
.\.venv\Scripts\python.exe scripts\collect_ha_m1.py
.\.venv\Scripts\python.exe scripts\qa_ha_research.py
```

- Cấu hình: `config/ha_ema_research.json`; không thêm dependency.
- Quy tắc gốc: `docs/HA_ORIGINAL_METHOD.md`; thiếu định nghĩa: `docs/HA_UNRESOLVED_METHOD.md`.
- Kiến trúc, công thức, warm-up, partitions, nguồn và giới hạn: `docs/HA_RESEARCH_PROTOCOL.md`.
- M1 gốc đã kiểm định: `data/processed/ha_m1/*_1m.parquet`; chỉ báo riêng: `*_features.parquet`.
- Provenance và SHA-256: `data/manifests/ha_m1/`; bản đóng băng trong `reports/ha_ema/manifest_snapshot.json`.
- Báo cáo: `reports/HA_EMA_M1_Research_Report.html`, `reports/ha_ema/FINAL_RESEARCH_REPORT.md`.
- Kết quả kiểm thử/đối chiếu: `reports/ha_ema/tests.xml`, `audit.json`, `browser_qa.json`, `preservation_verified.json`.
- Danh sách file bổ sung: `docs/HA_CHANGE_SUMMARY.md`.

Nguồn Binance Vision USD-M perpetual BTCUSDT/ZECUSDT/XAUUSDT, không có Forex
hoặc vàng giao ngay. Snapshot thu được đến 22/11/2026 23:59 UTC, thiếu ngày
23/11 so với cutoff; pipeline ghi phần thiếu ở đuôi, không gọi là đầy đủ tới
cutoff. Dữ liệu và phân tích phái sinh theo điều khoản Binance Vision
CC BY-NC-SA 4.0, dành cho nghiên cứu cá nhân phi thương mại trong phạm vi này.
M1 Parquet và ZIP nằm trong đường dẫn đã được `.gitignore`; cần giữ snapshot
cục bộ để tái lập offline. Không có upload/commit/push dữ liệu trong nhiệm vụ.

## Báo cáo HA/EMA M1 theo từng sản phẩm — đặc tả bổ sung

Chạy nghiên cứu mô tả mới hoàn toàn offline, **không tải lại dataset**:

```powershell
.\.venv\Scripts\python.exe scripts\run_ha_descriptive.py
```

Pipeline kiểm tra lại hash ZIP/Parquet, validation, tái tính HA/EMA; đo body,
wick, toàn nến so EMA; đếm các đoạn pullback sạch theo convention công khai;
đo biến động OHLC thật sau các quan sát ở 1/5/15/60 phút, tách khỏi detector.
Không tự định nghĩa Doji hoặc entry/SL; không tạo nhãn thắng/thua.

- `reports/ha_descriptive/comparison.html`: so sánh ba sản phẩm.
- `reports/ha_descriptive/BTCUSDT.html`, `ZECUSDT.html`, `XAUUSDT.html`: báo cáo riêng.
- JSON cùng tên: phân bố, thống kê theo năm/partition, censoring, metric chưa khả dụng.
- `*_geometry.parquet`, `*_sequences.parquet`, `*_forward.parquet`: dữ liệu đối chiếu.
- `tests.xml`, `audit.json`, `browser_qa.json`, `preservation_verified.json`: kiểm thử và bằng chứng.
- `docs/HA_DESCRIPTIVE_PROTOCOL.md`: quy ước đếm, dung sai float, markout và giới hạn.
- `docs/HA_DESCRIPTIVE_CHANGES.md`: toàn bộ file mới/sửa của lần bổ sung này.

Đếm clean run liên tiếp và ghép terminal hai wick đầu tiên là convention mô tả,
không phải quy tắc đã được tác giả xác nhận. Tần suất hình thái và return sau
quan sát không phải win rate. Mười hai định nghĩa còn thiếu được hợp nhất trong
`docs/HA_UNRESOLVED_METHOD.md`. Báo cáo v1 và các mô hình trước đó được bảo toàn.

Đặc tả đầy đủ mới nhất (hai chiều, công thức HA/geometry, quy tắc đã xác nhận
và danh sách chưa xác định) được lưu bền vững tại `docs/HA_ORIGINAL_METHOD.md`.
Kết luận đánh giá trên kết quả có sẵn: `reports/ha_win_rate_review/EVALUATION_STATUS.md`.

## D01–D05: 15 nhóm mẫu và 45 kịch bản H1

Đặc tả hiện hành: `docs/HA_DOJI_VARIANTS_PROTOCOL.md`. Đã xác nhận pullback
ít nhất hai clean candles liên tiếp, không minimum impulse, intermediate
ngược màu, range Doji > ít nhất một trong hai range trước; không giới hạn
pullback/intermediate/observation. Threshold 5/10/20/30/40% là biến thể nghiên cứu.

```powershell
.\.venv\Scripts\python.exe scripts\run_ha_variants.py
```

Lệnh chỉ đọc M1, indicators và geometry có sẵn, xác minh hash; không tải hoặc
tái tính chỉ báo. Kết quả riêng tại `reports/ha_doji_variants/`: `comparison.html`,
ba HTML/JSON theo symbol, `full_history.csv` (45 hàng), `partitioned.csv`,
`yearly.csv`, `*_observations.parquet`, quality, tests, audit và browser QA.

H1 đo chạm biên với mốc HA Close, wick HA đối hướng và RR1:1 trên OHLC thật
sau khi Doji đóng. **Không giả định fill tại HA Close**, không phải P&L hoặc
win rate thực thi. Mapping này là diễn giải nghiên cứu công khai, chưa xác
minh là outcome gốc của tác giả. Không dùng H1 để tuyên bố tái lập 75%.
Conservative/optimistic/excluded báo riêng; unresolved không ép thành thua.
CI95 calendar-block bootstrap 7 ngày và Wilson IID reference, overlap và
IS/OOS được lưu. Không chọn threshold theo kết quả. Báo cáo cũ giữ nguyên.
Danh sách thay đổi: `docs/HA_VARIANTS_CHANGES.md`.

### Phạm vi lưu trên GitHub

Commit nghiên cứu HA gồm code, đặc tả, manifest, báo cáo, kết quả tổng hợp và
Parquet observations/sequences/forward. ZIP gốc, M1/features đã xử lý và cache
`reports/ha_descriptive/*_geometry.parquet` giữ cục bộ theo `.gitignore`.
Để chạy offline cần có snapshot dữ liệu/cache tương ứng; hash nằm trong manifest
và execution.json. Geometry có thể tái tạo bằng pipeline mô tả từ M1 đã lưu.
Kết quả 259 tests trước đó thuộc toàn workspace có cả nghiên cứu confluence
chưa commit; `publication_tests.xml` ghi kiểm thử cho phạm vi commit HA này.
