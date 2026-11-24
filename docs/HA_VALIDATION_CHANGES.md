# Phase 2 — file và cách tái lập

Chạy trong root repository, dùng snapshot M1/features/geometry có sẵn:

```powershell
.\.venv\Scripts\python.exe scripts\run_ha_validation.py
.\.venv\Scripts\python.exe scripts\report_ha_validation.py
```

Pipeline phân tích không gọi collector. Reference tính độc lập chỉ báo trong bộ
nhớ để audit, không xây lại/thay thế components hoặc cache Phase1. Report script
kiểm tra thêm saved fields, normalization, xuất Markdown/HTML và browser QA.

- `src/ha_validation/reference.py`: lfilter/EWM, suffix-search và first-passage.
- `src/ha_validation/statistics.py`: independent bootstrap/counts/CI/dependence.
- `scripts/run_ha_validation.py`: T01–T13, kiểm thử, reconciliation/preservation.
- `scripts/supplement_ha_validation.py`: đối chiếu giá/geometry và normalization.
- `scripts/report_ha_validation.py`: T14, 17 sections, 22 charts, offline QA.
- `tests/test_ha_validation.py`: 19 tests mới; fixtures chỉ trong memory của test.
- `docs/HA_VALIDATION_PROTOCOL.md`: diagnostic conventions định trước và holdout.
- `reports/ha_model_validation/`: baseline, outputs và bằng chứng hoàn chỉnh.

Baseline được tạo trước khi thêm audit: commit
`fed1f51df2781990795339e69509b31bc701bad3`, 338 file đã có. File baseline là dấu
vết lịch sử không được tạo lại khi rerun. Nếu bắt đầu nghiên cứu mới với input
khác, dùng thư mục output khác và baseline mới, không ghi đè snapshot này.

Không sửa README/PROGRESS hoặc công việc confluence đang dở; không sửa kết quả
Phase1. Exact Phase1 dependency versions không được ghi trực tiếp trong
execution.json: đó là giới hạn, không tự điền versions hiện tại thành lịch sử.

Tỷ lệ H1 không phải win rate thực thi, không chứng minh profitability hoặc
tái lập outcome tác giả. Không có download, account, order hoặc live execution.
