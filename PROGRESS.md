# Tiến độ

- [x] Phase 1: Thư mục project, Git và Python 3.14.4 virtual environment; dependencies đã cài; requirements.lock.txt lưu phiên bản chính xác.
- [x] Phase 2: Tách quy tắc xác nhận và quy ước nghiên cứu; kế hoạch cố định trước kết quả.
- [x] Phase 3–4: Raw ZIP + SHA256, validated Parquet và manifest; daily repair ZEC hoàn tất.
- [x] Phase 5–6: Engine, statistics, reporting; 96 tests đã chạy thành công ở các suite (full-suite evidence cập nhật cuối pipeline).
- [x] Phase 7–9: 1.530.912 M5 candles research, 10.275 patterns; simulations, statistics, sensitivity, DuckDB và Polars reconciliation hoàn tất.
- [x] Phase 10–11: HTML tự chứa 18 phần, 41 charts; Chrome offline QA đạt ở 1440/1280/768/390px, filters khớp Parquet, không HTTP requests hoặc page errors.

Pipeline có raw-file cache; các artifact trung gian được lưu Parquet/JSON để tiếp tục sau gián đoạn.

## Kết quả cuối đã xác minh

96/96 unit/integration tests passed, coverage83.26%. 9.987 resolved, 3.295 wins, 6.692 losses, 286 unresolved, 2 ambiguous. Win Rate32.9929%; Wilson95%32.0774–33.9214%. Gross expectancy−0.01021R; cost-adjusted−0.22408R (10bps round-trip giả định). OOS net expectancy−0.26941R; bootstrap95%[−0.33598,−0.20246]R. Không có bằng chứng lợi thế sau phí cho cấu hình đang thử.

Source snapshot: BTC và XAU qua19/11/2026; ZEC qua20/11/2026 do daily archive mới có tại lần kiểm tra bổ sung. Raw/validated1.538.015 nến; loại7.103 XAU trước public-listing cutoff. Daily repair ZEC bổ sung1.440 interval thiếu trong monthly từ5 daily archive thật; thêm ngày20/11 có288 nến. Sau repair không có duplicate/invalid/gap nội bộ trong ba dataset. Không nội suy.

QA visual: đổi heading sang Cambria để hiển thị dấu tiếng Việt liền chữ; đã quan sát screenshot desktop/mobile và candlestick. Báo cáo chứa kết quả QA; toàn bộ artifact được lưu dưới project.

- 2026-11-21T20:17:46.494339+07:00: Phase 6: 92 tests passed, 0 failed.

- 2026-11-21T20:17:46.511382+07:00: Phase 3–4: Source collection and validated Parquet available; manifest records individual source failures.

- 2026-11-21T20:17:59.086317+07:00: Phase 7 checkpoint XAUUSDT: 91872 candles, 564 patterns; source-boundary exclusions 7103.

- 2026-11-21T20:19:29.946073+07:00: Phase 7 checkpoint BTCUSDT: 724608 candles, 5609 patterns; source-boundary exclusions 0.

- 2026-11-21T20:22:26.369688+07:00: Phase 7 checkpoint ZECUSDT: 714432 candles, 4102 patterns; source-boundary exclusions 0.

- 2026-11-21T20:24:06.518655+07:00: Phase 8–9: Statistics and predeclared sensitivity computed; SQL reconciliation and temporal invariants passed.

- 2026-11-21T20:24:29.654523+07:00: Phase 6: 96 tests passed, 0 failed.

- 2026-11-21T20:24:34.205925+07:00: Phase 10: Self-contained report generated; pipeline elapsed 446.6s. Browser QA remains separate.
