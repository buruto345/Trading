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
