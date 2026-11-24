# Danh sách thay đổi HA/EMA M1

## File hiện có được sửa

- `README.md`: nối thêm hướng dẫn nhánh M1, lệnh tái lập, nguồn và giới hạn.

Không sửa các engine ICT, confluence, cấu hình cũ, dataset M5 hoặc báo cáo cũ.
Các thay đổi PROGRESS.md và nội dung confluence đã có trước nhiệm vụ này được giữ nguyên.

## File nguồn mới

- `config/ha_ema_research.json`: phạm vi dữ liệu, cutoff, warm-up và split cố định.
- `src/ha_research/__init__.py`: package độc lập.
- `src/ha_research/data.py`: collection M1, validation adapter, provenance và hash.
- `src/ha_research/indicators.py`: HA/EMA nhân quả, thời điểm sẵn sàng, partition.
- `src/ha_research/statistics.py`: chặn định nghĩa thiếu và thống kê outcome tương lai.
- `src/ha_research/report.py`: thống kê mô tả và báo cáo HTML/Markdown.
- `scripts/collect_ha_m1.py`: thu thập/checkpoint và snapshot preservation.
- `scripts/run_ha_research.py`: tests, pipeline offline, báo cáo và QA.
- `scripts/qa_ha_research.py`: DuckDB reconciliation, preservation và Chrome offline.
- `tests/test_ha_research.py`: unit/integration trên dữ liệu test tổng hợp riêng.
- `tests/data/synthetic/.gitignore`: bỏ qua fixture tạm của pytest trong vùng synthetic.
- `docs/HA_ORIGINAL_METHOD.md`: các quy tắc được người dùng xác nhận.
- `docs/HA_UNRESOLVED_METHOD.md`: định nghĩa còn thiếu và cổng replication.
- `docs/HA_RESEARCH_PROTOCOL.md`: protocol, architecture, nguồn/điều khoản/giới hạn.
- `docs/HA_CHANGE_SUMMARY.md`: danh sách này.

## Artifact dữ liệu và báo cáo mới

- `data/raw/futures/um/{monthly,daily}/klines/{symbol}/1m/`: ZIP/checksum gốc mới,
  tái sử dụng cache có sẵn nếu trùng file và checksum hợp lệ.
- `data/processed/ha_m1/{symbol}_1m.parquet`: OHLCV thật, UTC, không nội suy.
- `data/processed/ha_m1/{symbol}_features.parquet`: OHLC thật cùng HA/EMA, ready, partition.
- `data/manifests/ha_m1/{symbol}.json`: checksum, nguồn, coverage và quality.
- `reports/HA_EMA_M1_Research_Report.html`: báo cáo độc lập mở offline.
- `reports/ha_ema/FINAL_RESEARCH_REPORT.md`: kết luận xác minh và phần chưa xác minh.
- `reports/ha_ema/{symbol}_quality.json`: missing/duplicate/invalid/order/timezone.
- `reports/ha_ema/summary.json`: số liệu mô tả theo thị trường/năm/partition.
- `reports/ha_ema/frozen_config.json`, `execution.json`, `manifest_snapshot.json`: tái lập.
- `reports/ha_ema/collection_status.json`, `collection.log`, `pipeline.log`: dấu vết chạy.
- `reports/ha_ema/tests.log`, `tests.xml`: toàn bộ pytest.
- `reports/ha_ema/audit.json`: đối chiếu độc lập bằng DuckDB.
- `reports/ha_ema/preservation_before.json`, `preservation_verified.json`: hash bảo toàn file cũ.
- `reports/ha_ema/browser_qa.json`, `report_{1440,768,390}.png`: QA Chrome offline.

Không thêm dependency. Tái sử dụng public archive downloader, validator UTC,
Wilson interval và môi trường thư viện hiện có. Không commit hoặc push.
