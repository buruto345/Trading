# Thay đổi cho run D01–D05/H1

File nguồn mới:

- `config/ha_doji_variants.json`: 5 thresholds, H1 mapping, bootstrap và ambiguity scenarios.
- `src/ha_research/variants.py`: state machine nhân quả, first-passage OHLC thật, censor/overlap/CI.
- `src/ha_research/variant_report.py`: bốn báo cáo HTML và Markdown kết quả.
- `scripts/run_ha_variants.py`: pipeline offline tái sử dụng feature/geometry, full pytest, audit.
- `scripts/qa_ha_variants.py`: SQL counts/proportions, brute-force samples, preservation và browser QA.
- `tests/test_ha_variants.py`: 26 unit cases cho rule updates và H1.
- `docs/HA_DOJI_VARIANTS_PROTOCOL.md`: đặc tả hiện hành, nguồn và giả thuyết tách biệt.
- `docs/HA_VARIANTS_CHANGES.md`: danh sách này.

File hiện có sửa: `README.md`, `docs/HA_ORIGINAL_METHOD.md`,
`docs/HA_UNRESOLVED_METHOD.md`. Không sửa các indicator, collector, model hoặc
report cũ; không thêm dependency hoặc live execution.

Artifacts mới tại `reports/ha_doji_variants/`:

- `BTCUSDT.html`, `ZECUSDT.html`, `XAUUSDT.html`, `comparison.html`, `FINAL_REPORT.md`.
- JSON riêng từng mã, `summary.json`, `full_history.csv`, `partitioned.csv`, `yearly.csv`.
- Ba `{symbol}_observations.parquet` có levels, labels, reasons, timestamps, partitions.
- `data_quality.json`, `frozen_config.json`, `frozen_base_config.json`, `execution.json`, `completion.json`.
- `tests.xml`, `tests.log`, `pipeline.log`, `audit.json`, `browser_qa.json`.
- `preservation_before.json`, `preservation_verified.json`; screenshots desktop/mobile bốn báo cáo.

CI là pointwise và H1 là diễn giải nghiên cứu. Kết quả phương pháp gốc/giá
khớp lệnh thật vẫn chưa được xác minh; không giả mạo metrics còn thiếu.
