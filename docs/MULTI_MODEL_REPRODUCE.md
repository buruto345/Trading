# Chạy lại nghiên cứu đa mô hình

Từ thư mục dự án, PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts\run_multi_model.py
.\.venv\Scripts\python.exe scripts\audit_multi_model.py
.\.venv\Scripts\python.exe scripts\qa_multi_model.py
.\.venv\Scripts\python.exe -c "from pathlib import Path; from src.multi_model.report import generate; generate(Path.cwd())"
```

Pipeline không tải dữ liệu và chỉ ghi reports/multi_model cùng reports/ICT_Multi_Model_Comparison.html.
Đặc tả khóa trước thống kê ở MULTI_MODEL_PROTOCOL.md. Thư viện dùng môi trường .venv/requirements.lock.txt hiện có.
Mỗi lần chạy lưu checksum baseline, snapshot manifest, test XML/log, coverage dữ liệu, partitions,
formations/rejected/patterns/simulations Parquet, summary CSV/JSON, phân nhóm,
paired bootstrap contrasts và analysis từng model/track. HTML nhúng Plotly, không cần mạng.
Các hình desktop/mobile/candlestick và browser_qa.json là bằng chứng QA offline.
Không dùng scripts/run_pipeline.py cho nghiên cứu mới vì script gốc có thể ghi lại báo cáo gốc.
