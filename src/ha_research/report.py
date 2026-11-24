"""Descriptive reports only; no inferred pattern definitions or historical wins."""
from html import escape
import json

import pandas as pd

from src.ha_research.statistics import UNRESOLVED


def describe(frame):
    ready = frame.loc[frame.indicator_ready]
    ratios = ready.ha_body_ratio.dropna()
    quantiles = {str(q): float(ratios.quantile(q)) if len(ratios) else None
                 for q in [.05, .25, .5, .75, .95]}
    return dict(candles=len(frame), indicator_ready=len(ready), warmup_excluded=len(frame) - len(ready),
                first=frame.timestamp.min().isoformat() if len(frame) else None,
                last=frame.timestamp.max().isoformat() if len(frame) else None,
                body_ratio_quantiles=quantiles,
                both_wicks=int(ready.both_wicks.sum()),
                bullish=int(ready.ha_color.eq(1).sum()), bearish=int(ready.ha_color.eq(-1).sum()),
                neutral=int(ready.ha_color.eq(0).sum()),
                ha_close_above_ema=int(ready.ha_close.gt(ready.ema100).sum()),
                ha_close_below_ema=int(ready.ha_close.lt(ready.ema100).sum()),
                zero_range=int(ready.ha_high.eq(ready.ha_low).sum()),
                upper_wick_mean=float(ready.ha_upper_wick.mean()) if len(ready) else None,
                lower_wick_mean=float(ready.ha_lower_wick.mean()) if len(ready) else None)


def summarize(frame, symbol):
    rows = []
    years = frame.timestamp.dt.year
    for (year, partition), group in frame.groupby([years, 'partition'], sort=True):
        rows.append(dict(symbol=symbol, year=int(year), partition=partition, **describe(group)))
    return dict(symbol=symbol, overall=describe(frame), groups=rows,
                partitions={part: describe(frame.loc[frame.partition.eq(part)])
                            for part in ['in_sample', 'validation', 'out_of_sample']})


def render(root, result):
    totals = []
    for item in result['markets']:
        q, s = item['quality'], item['descriptive']['overall']
        totals.append({'Thị trường': item['symbol'], 'Nến hợp lệ': q['validated_candles'],
                       'Nến nghiên cứu': s['candles'], 'Đủ warm-up': s['indicator_ready'],
                       'Phút thiếu nội bộ': q['missing_candles'],
                       'Completeness nội bộ': q['completeness'],
                       'Đầu UTC': q['earliest_timestamp'], 'Cuối UTC': q['latest_timestamp'],
                       'Phút thiếu đến cutoff': item['trailing_missing_minutes']})
    table = pd.DataFrame(totals).to_html(index=False, escape=True, border=0)
    groups = [dict(symbol=m['symbol'], partition=p, **{k: s[k] for k in ['candles', 'indicator_ready', 'both_wicks', 'bullish', 'bearish', 'neutral']})
              for m in result['markets'] for p, s in m['descriptive']['partitions'].items()]
    split_table = pd.DataFrame(groups).to_html(index=False, escape=True, border=0)
    tests = result.get('tests', {})
    test_text = f"{tests.get('tests', '—')} tests; {tests.get('failures', '—')} failures; {tests.get('errors', '—')} errors."
    unresolved = ''.join('<li>' + escape(key) + ': unresolved</li>' for key in UNRESOLVED)
    payload = escape(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    html = f'''<!doctype html><html lang="vi"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nghiên cứu HA – EMA 100 M1</title>
<style>body{{font:16px/1.6 system-ui,sans-serif;margin:0;color:#172b3a;background:#f5f7f9}}
main{{max-width:1200px;margin:auto;padding:24px}}h1{{line-height:1.2}}section{{background:white;padding:20px;margin:20px 0;border-radius:8px}}
.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #ccd5df}}
.status{{border-left:5px solid #b07816;padding:14px;background:#fff4d9}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}}li{{overflow-wrap:anywhere}}
@media(max-width:500px){{main{{padding:12px}}section{{padding:12px}}h1{{font-size:27px}}}}</style>
<main><h1>Heikin Ashi · EMA 100 · M1</h1>
<p>Nghiên cứu lịch sử offline — cutoff trước 24/11/2026 00:00 UTC.</p>
<p class="status" id="status">Chưa thể kiểm chứng win rate 75%. Định nghĩa mô hình và outcome chưa đầy đủ.
Không có số tín hiệu, nhãn thắng/thua, win rate hoặc CI thực nghiệm.</p>
<section><h2>Dữ liệu đã kiểm định</h2><p id="total">Tổng {result['total_validated_candles']:,} nến M1 hợp lệ.</p>
<div class="scroll">{table}</div><p>Phút thiếu theo lưới 24/7 gồm cả khả năng đóng cửa thị trường; chưa có calendar xác minh.
Không nội suy M1 từ M5. XAU trước 05/01/2026 được giữ trong dữ liệu nguồn nhưng loại khỏi nghiên cứu.</p></section>
<section><h2>Phân chia thời gian và thống kê mô tả</h2><div class="scroll">{split_table}</div>
<p>IS trước 2024; validation năm 2024; OOS từ 2025. OOS hồi cứu, không phải mẫu chưa từng xem.
Các số hình học chỉ tính trên nến đủ 500 nến warm-up. Hai wick không đồng nghĩa Doji hay tín hiệu.</p></section>
<section><h2>Đã xác minh và giới hạn</h2><p>Archive checksum SHA-256, OHLC, timestamp UTC,
trùng lặp, khoảng trống; công thức HA/EMA có kiểm thử thủ công, reset sau gap và prefix invariance.
HA là giá tổng hợp của chỉ báo, không phải giá khớp lệnh.</p>
<p>Chỉ có Binance USD-M perpetual BTCUSDT/ZECUSDT/XAUUSDT; chưa có Forex hoặc vàng giao ngay.
Chưa xác minh nguồn công bố 75%, cỡ mẫu, thời kỳ, chi phí hoặc independence.
Selection bias, look-ahead, multiple testing và overfitting phải được xử lý trước kiểm định kết luận.</p></section>
<section><h2>Định nghĩa còn thiếu</h2><ul>{unresolved}</ul></section>
<section><h2>Dấu vết tái lập</h2><p>{test_text}</p><p>Config, hash dữ liệu/code, manifest, tests.xml, audit và browser_qa.json
được lưu tại reports/ha_ema. Các trường thống kê outcome không xác định giữ null.</p>
<details><summary>JSON chi tiết: quality, phân bố, partitions và limitations</summary><pre>{payload}</pre></details></section>
<p>Nguồn: <a href="https://github.com/binance/binance-public-data">Binance Vision</a>.
Dữ liệu và phân tích phái sinh: CC BY-NC-SA 4.0 theo điều khoản nguồn. Không có giao dịch thật.</p></main></html>'''
    (root / 'reports/HA_EMA_M1_Research_Report.html').write_text(html, encoding='utf-8')
    lines = ['# Kết quả nghiên cứu HA–EMA M1', '',
             'Chưa thể kiểm chứng tuyên bố 75%; chưa có định nghĩa đủ để nhận diện và gán outcome.', '',
             f"Tổng nến M1 hợp lệ: {result['total_validated_candles']:,}.", '']
    for row in totals:
        lines.append('- ' + '; '.join(f'{key}: {value}' for key, value in row.items()))
    lines += ['', 'Đã kiểm định OHLC/UTC/duplicate/gap và checksum; đã triển khai HA/EMA nhân quả.',
              test_text,
              'Kết quả unit/integration tests, audit và browser QA nằm cạnh báo cáo này.',
              'Không có Forex; XAUUSDT perpetual không đại diện vàng giao ngay. Calendar đóng cửa chưa xác minh.',
              'Cỡ mẫu tín hiệu, số quan sát độc lập, observed win proportion, CI và p-value: chưa xác định.',
              'Các định nghĩa còn thiếu: ' + ', '.join(UNRESOLVED) + '.',
              'Không tối ưu tham số để khớp 75%. Không dùng HA làm giá thực thi; không có lệnh thật.',
              'Cần protocol outcome và dependence đầy đủ trước nghiên cứu thắng/thua tiếp theo.',
              'Nguồn dữ liệu: Binance Vision; dữ liệu/phân tích phái sinh theo CC BY-NC-SA 4.0.']
    (root / 'reports/ha_ema/FINAL_RESEARCH_REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
