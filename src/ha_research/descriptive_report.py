"""Self-contained per-market and comparison HTML; no guessed win rates."""
from html import escape
import json
import pandas as pd

from src.ha_research.statistics import UNRESOLVED

STYLE = '''body{font:16px/1.6 system-ui,sans-serif;color:#193042;background:#f2f5f7;margin:0}
main{max-width:1180px;margin:auto;padding:24px}section{background:white;padding:20px;margin:20px 0;border-radius:8px}
h1{line-height:1.2}h2{line-height:1.3}a{color:#175c99}.notice{background:#fff2d3;border-left:5px solid #b37a10;padding:14px}
.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:10px;border-bottom:1px solid #d5dfe7}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}li{overflow-wrap:anywhere}.metric{font-size:26px;font-weight:700}
@media(max-width:500px){main{padding:12px}section{padding:12px}h1{font-size:27px}}'''


def table(rows):
    return '<div class="scroll">' + pd.DataFrame(rows).to_html(index=False, border=0, escape=True, na_rep='Chưa xác định') + '</div>'


def page(title, body):
    return f'''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title><style>{STYLE}</style><main><h1>{escape(title)}</h1>
<p class="notice" id="status">Win rate 75%: chưa thể kiểm chứng. Chưa có định nghĩa Doji, entry, SL và outcome đầy đủ.
Số chuỗi hình thái và biến động sau sự kiện không phải số lệnh hoặc tỷ lệ thắng.</p>{body}
<footer>Nguồn: Binance Vision USD-M perpetual, snapshot cục bộ. Dữ liệu/phân tích phái sinh theo CC BY-NC-SA 4.0.
Chỉ nghiên cứu lịch sử offline; không tài khoản hoặc đặt lệnh thật.</footer></main></html>'''


def comparison_rows(markets):
    rows = []
    for m in markets:
        c, s = m['descriptive']['overall']['candles'], m['descriptive']['overall']['sequences']
        rows.append({'Sản phẩm': m['symbol'], 'M1 hợp lệ': m['quality']['validated_candles'],
                     'Nến nghiên cứu': c['candles'], 'Đủ warm-up': c['ready_candles'],
                     'Clean runs (quy ước)': s['clean_runs'], 'Terminal cùng màu': s['same_color_terminals'],
                     'Có impulse + cùng màu': s['with_impulse_same_color'], 'Win rate gốc': 'Chưa xác định'})
    return rows


def render_reports(root, result):
    out = root / 'reports/ha_descriptive'
    missing = '<ul>' + ''.join(f'<li>{escape(key)}: chưa xác định</li>' for key in UNRESOLVED) + '</ul>'
    confirmed = '''M1, HA, EMA 100 trên HA Close; không bắt buộc EMA slope, volume, session hoặc đa khung.
Toàn nến kể cả wick phải trên EMA cho bullish, dưới EMA cho bearish. Bullish clean pullback là nến giảm không wick trên;
bearish là nến tăng không wick dưới. Impulse được có wick; không quy định pullback tối đa. Doji cùng màu xu hướng,
thân nhỏ/gần 0, hai wick, toàn nến cùng phía EMA. Được có intermediate, không cần nến xác nhận sau Doji.
Chạm/cắt EMA hoặc Doji sai màu làm mẫu không hợp lệ. RR công bố 1:1, win rate 75% chưa xác minh.'''
    limits = '''Không có Forex hoặc vàng giao ngay; chỉ ba perpetual còn trong mẫu hiện có nên có selection/survivorship bias.
Lịch đóng cửa chưa xác minh; zero-volume không đồng nghĩa thanh khoản thực thi. OOS hồi cứu từng được xem ở nghiên cứu trước.
Chuỗi có thể phụ thuộc và cửa sổ tương lai có thể overlap. Không shuffle hoặc tối ưu tham số/horizon theo kết quả.
Các phân bố nhiều chiều là exploratory, không phải kiểm định significance. Chi phí, spread, funding, slippage và
thứ tự intrabar chưa đủ để tính outcome. HA tổng hợp không dùng làm giá khớp lệnh.'''
    for m in result['markets']:
        symbol = m['symbol']
        q, overall = m['quality'], m['descriptive']['overall']
        c, s = overall['candles'], overall['sequences']
        quality = [{'Thuộc tính': k, 'Giá trị': v} for k, v in {
            'Nguồn': 'Binance Vision — USD-M perpetual', 'Đầu UTC': q['earliest_timestamp'], 'Cuối UTC': q['latest_timestamp'],
            'Tổng nến nguồn (manifest)': m['source_quality']['raw_candles'], 'Nến hợp lệ kiểm tra lại': q['validated_candles'],
            'Nến ngoài thời kỳ nghiên cứu': m['excluded_before_research'], 'Missing nội bộ': q['missing_candles'],
            'Trùng timestamp trong Parquet': q['source_duplicate_rows'], 'Invalid OHLC/timestamp/volume': q['invalid_candles'],
            'Completeness nội bộ': q['completeness'], 'Thiếu đuôi tới cutoff (phút)': m['trailing_missing_minutes'],
            'Thứ tự tăng': q['input_monotonic'], 'Timezone': q['timezone'],
            'Warm-up': f"{result['base_config']['warmup_bars']} nến mỗi segment", 'Lịch đóng cửa': 'Chưa xác minh',
            'Zero-volume': q['zero_volume_candles']}.items()]
        frequencies = [{'Đặc tính': k, 'Số nến': v, 'Tỷ lệ trên nến đủ warm-up (%)':
                        round(100*c['frequencies'][k], 4) if c['frequencies'][k] is not None else None}
                       for k, v in c['counts'].items()]
        distributions = [dict(measure=name, **values) for name, values in c['distributions'].items()]
        distributions += [dict(measure='body_ratio_two_wick_cohort_NOT_defined_Doji', **c['two_wick_body_ratio']),
                          dict(measure='body_ratio_same_color_two_wicks_NOT_defined_Doji', **c['same_color_two_wick_body_ratio'])]
        lengths = [dict(measure=name, **s[name]) for name in ['pullback_length', 'impulse_count', 'intermediate_count', 'terminal_body_ratio']]
        behavior = [{'Horizon (phút)': f['horizon_minutes'], 'Quan sát cohort': f['sample_size'],
                     'Đủ cửa sổ': f['observed'], 'Censored': f['censored'],
                     'Mean return (bps)': f['directional_return_bps']['mean'],
                     'Median return (bps)': f['directional_return_bps']['median'],
                     'P05 (bps)': f['directional_return_bps']['p05'], 'P95 (bps)': f['directional_return_bps']['p95']}
                    for f in overall['forward']]
        splitrows = [{'Partition': part, 'Nến đủ warm-up': v['candles']['ready_candles'],
                      'Clean runs': v['sequences']['clean_runs'], 'Cohort theo quy ước': v['sequences']['with_impulse_same_color'],
                      'Win rate': 'Chưa xác định'} for part, v in m['descriptive']['partitions'].items()]
        yearrows = [{'Năm': year, 'Nến đủ warm-up': v['candles']['ready_candles'], 'Clean runs theo năm bắt đầu': v['sequences']['clean_runs'],
                     'Terminal cùng màu của các run': v['sequences']['same_color_terminals']}
                    for year, v in m['descriptive']['years'].items()]
        body = f'''<p><a href="comparison.html">So sánh ba sản phẩm</a> · <a href="{symbol}.json">JSON đầy đủ</a></p>
<section><h2>Coverage và kiểm định</h2><p class="metric" id="valid-count">{q['validated_candles']:,} nến M1 hợp lệ</p>{table(quality)}
<p>Không tải lại dữ liệu. Hash nguồn/Parquet được xác minh trước phân tích. Completeness nội bộ chỉ tính giữa nến đầu và cuối,
không khẳng định đủ từ ngày listing hoặc tới cutoff. Các gap không được lấp.</p></section>
<section><h2>Thân nến, wick và EMA</h2>{table(frequencies)}{table(distributions)}
<p>Population: {c['ready_candles']:,} nến đủ warm-up. Body ratio có cohort hai wick để nghiên cứu ngưỡng còn thiếu;
chưa có phân bố Doji chính thức. Bps chuẩn hóa theo HA Close; số liệu giá gốc chỉ so trong cùng sản phẩm.</p></section>
<section><h2>Pullback và intermediate — quy ước mô tả</h2>
<p id="run-count">{s['clean_runs']:,} đoạn clean liên tiếp; {s['observed_terminals']:,} terminal hai wick;
{s['same_color_terminals']:,} terminal cùng màu, trong đó {s['with_impulse_same_color']:,} có impulse đứng trước.</p>
{table(lengths)}{table([{'Trạng thái': k, 'Số đoạn': v} for k,v in s['statuses'].items()])}
<p>Đếm run liên tiếp tối đại, không giới hạn số nến; lấy terminal hai wick đầu tiên cùng vùng EMA, chưa giới hạn thân.
Intermediate không giới hạn hình dạng/số lượng, censor khi mất vùng EMA, gap/split, run mới hoặc hết dữ liệu.
Đây là convention ghép chuỗi, không phải xác nhận continuity hoặc số tối thiểu của tác giả. Pattern hoàn chỉnh: chưa xác định.</p></section>
<section><h2>Giá thị trường thật sau quan sát</h2>{table(behavior)}
<p>Cohort = terminal hai wick đúng màu, sau clean run có impulse mô tả; chưa có tiêu chuẩn Doji.
Return có dấu theo hướng xu hướng, neo Open thật nến kế tiếp và Close thật sau h nến.
Các horizon 1/5/15/60 phút là cửa sổ mô tả cố định, không phải thời hạn trade của tác giả.
Loại khỏi phép đo nếu cửa sổ vượt gap/partition/cuối dữ liệu, giữ lý do censoring. Mean/quantile không phải CI hoặc win rate.</p></section>
<section><h2>Theo thời kỳ</h2>{table(splitrows)}{table(yearrows)}<p>Chi tiết phân bố và forward behavior cho từng năm/partition trong JSON.
Không gộp sản phẩm. Partition rỗng không phải tỷ lệ thắng 0%.</p></section>
<section><h2>Quy tắc đã xác nhận</h2><p>{confirmed}</p></section>
<section><h2>Định nghĩa còn thiếu và thống kê chưa khả dụng</h2>{missing}
<p>Sample size outcome, observed win proportion, CI win rate, số quan sát độc lập và p-value 75% đều chưa xác định.
Cỡ mẫu hình thái và số cửa sổ đo giá được báo riêng, không thay thế cỡ mẫu giao dịch.</p></section>
<section><h2>Giới hạn</h2><p>{limits}</p></section>
<section><h2>Bằng chứng tái lập</h2><p>{result['tests']['tests']} tests, {result['tests']['failures']} failures,
{result['tests']['errors']} errors. Xem audit.json, browser_qa.json và execution.json cạnh báo cáo.</p>
<details><summary>Snapshot cấu hình</summary><pre>{escape(json.dumps(result['config'], ensure_ascii=False, indent=2))}</pre></details></section>'''
        (out / f'{symbol}.html').write_text(page(f'{symbol} · HA / EMA 100 · M1', body), encoding='utf-8')
    rows = comparison_rows(result['markets'])
    links = ' · '.join(f'<a href="{m["symbol"]}.html">{m["symbol"]}</a>' for m in result['markets'])
    comparison = f'''<p>{links}</p><section><h2>So sánh trên snapshot hiện có</h2>{table(rows)}
<p>Clean runs là các đoạn theo convention mô tả. Không diễn giải số lượng đó là tín hiệu đã xác nhận hoặc số trade.</p></section>
<section><h2>Phạm vi và kết luận</h2><p>Ba sản phẩm đã được kiểm tra lại dữ liệu, tái tính HA/EMA và phân tích riêng.
Không tải lại; không có mô phỏng entry/SL/TP. Chưa thể chấp nhận hoặc bác bỏ win rate 75% của tác giả.</p>
<p>{limits}</p></section><section><h2>Những định nghĩa cần bổ sung</h2>{missing}</section>
<section><h2>Kiểm thử</h2><p>{result['tests']['tests']} tests passed nếu failures/errors bằng 0:
failures={result['tests']['failures']}, errors={result['tests']['errors']}.</p>
<p><a href="summary.json">JSON so sánh</a> · <a href="audit.json">Đối chiếu số liệu</a> · <a href="browser_qa.json">Browser QA</a></p></section>'''
    (out / 'comparison.html').write_text(page('So sánh ba sản phẩm · HA / EMA 100 · M1', comparison), encoding='utf-8')
    lines = ['# Kết quả mô tả HA/EMA theo từng sản phẩm', '',
             'Chưa đủ định nghĩa để tính win rate hoặc kiểm định tuyên bố 75%. Không tải lại dữ liệu.', '',
             f"Tests: {result['tests']}", '']
    for row in rows:
        lines.append('- ' + '; '.join(f'{k}: {v}' for k,v in row.items()))
    lines += ['', 'Đọc HTML riêng từng sản phẩm và comparison.html; JSON chứa phân bố, năm/partition và censoring.',
              'Không coi clean runs, terminal hai wick hoặc return dương là trade thắng.',
              'Định nghĩa còn thiếu: ' + ', '.join(UNRESOLVED),
              'Bằng chứng audit, preservation, browser QA và hash code/data được lưu cùng thư mục.']
    (out / 'FINAL_REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
