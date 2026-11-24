# Thay đổi của nghiên cứu mô tả theo từng sản phẩm (v2)

## File hiện có được sửa trong lần này

- `README.md`: hướng dẫn pipeline offline và liên kết bốn báo cáo.
- `docs/HA_ORIGINAL_METHOD.md`: thêm quy tắc toàn nến so EMA, clean wick và Doji sai màu theo đặc tả bổ sung.
- `docs/HA_UNRESOLVED_METHOD.md`: cập nhật điểm đã giải quyết, hợp nhất 12 định nghĩa còn thiếu.
- `src/ha_research/statistics.py`: bổ sung maximum_observation_period và ambiguous_intrabar_handling vào cổng định nghĩa.

Không sửa collector, indicator, engine ICT/M5, confluence, dataset hoặc báo cáo cũ.
Các thay đổi có sẵn từ nhiệm vụ trước không được tính là thay đổi mới của v2.

## File nguồn mới

- `config/ha_descriptive.json`: protocol mô tả cố định, không network.
- `src/ha_research/descriptive.py`: geometry, chuỗi nhân quả, markout giá thật tách riêng, summaries.
- `src/ha_research/descriptive_report.py`: ba HTML riêng và comparison, báo cáo Markdown.
- `scripts/run_ha_descriptive.py`: revalidation, full pytest, phân tích ba mã, provenance và QA.
- `scripts/qa_ha_descriptive.py`: đối chiếu SQL độc lập và kiểm tra bốn HTML offline.
- `tests/test_ha_descriptive.py`: kiểm thử hình học, float, chuỗi, causal prefix, censor và giá thật.
- `docs/HA_DESCRIPTIVE_PROTOCOL.md`: convention đếm và giới hạn, không thay quy tắc gốc.
- `docs/HA_DESCRIPTIVE_CHANGES.md`: danh sách này.

## Artifact mới — tất cả tại `reports/ha_descriptive/`

- `BTCUSDT.html`, `ZECUSDT.html`, `XAUUSDT.html`, `comparison.html`.
- `BTCUSDT.json`, `ZECUSDT.json`, `XAUUSDT.json`, `summary.json`, `FINAL_REPORT.md`.
- `{symbol}_geometry.parquet`, `{symbol}_sequences.parquet`, `{symbol}_forward.parquet` cho ba sản phẩm.
- `frozen_config.json`, `frozen_base_config.json`, `execution.json` (hash code, dữ liệu và version thư viện).
- `tests.log`, `tests.xml`, `pipeline.log`.
- `audit.json`, `preservation_before.json`, `preservation_verified.json`, `browser_qa.json`.
- `{BTCUSDT,ZECUSDT,XAUUSDT,comparison}_{1440,390}.png`: bằng chứng browser QA.

Không thêm dependency, không tải lại dữ liệu, không tạo giả định entry/SL/outcome,
không giao dịch thật, không commit/push. Pipeline xuất lỗi thay vì âm thầm thay
dataset nếu checksum hoặc validation không khớp snapshot.
