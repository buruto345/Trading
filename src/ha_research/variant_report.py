"""Render all 45 H1 scenarios, never rank or select thresholds."""
from html import escape
import pandas as pd
from src.ha_research.descriptive_report import STYLE, table


def percentage(value):
    return 'Chưa xác định' if value is None else f'{100*value:.2f}%'


def compact(rows):
    result=[]
    for r in rows:
        ci=r['ci95_block']
        result.append({'Instrument':r['symbol'],'Doji':f"{r['variant']} ≤{r['threshold']*100:g}%",
            'M1 hợp lệ':r['valid_candles'],'Patterns':r['patterns'],'Bull':r['bullish'],'Bear':r['bearish'],
            'Resolved':r['resolved'],'Ambiguous':r['ambiguous'],'Unresolved':r['unresolved'],
            'H1 proportion':percentage(r['observed_proportion']),
            '95% block CI':f"{percentage(ci['low'])} – {percentage(ci['high'])}"})
    return result


def render(root, result):
    out=root/'reports/ha_doji_variants'
    labels={'conservative':'Conservative — ambiguous tính unsuccessful',
            'optimistic':'Optimistic — ambiguous tính successful',
            'excluded':'Excluded — loại ambiguous khỏi mẫu số, vẫn báo riêng'}
    for symbol in result['config']['symbols']+['comparison']:
        rows=[r for r in result['full_history'] if symbol=='comparison' or r['symbol']==symbol]
        title=f'{symbol} · D01–D05 · H1 boundary research'
        links=' · '.join(f'<a href="{s}.html">{s}</a>' for s in result['config']['symbols']+['comparison'] if s!=symbol)
        blocks=''
        for scenario in result['config']['scenarios']:
            selected=[r for r in rows if r['scenario']==scenario]
            blocks+=f'<section id="{scenario}"><h2>{labels[scenario]}</h2>{table(compact(selected))}</section>'
        per=[r for r in result['partitioned'] if (symbol=='comparison' or r['symbol']==symbol) and r['scenario']=='excluded']
        partition_rows=[dict(symbol=r['symbol'],variant=r['variant'],partition=r['partition'],n=r['patterns'],
                             resolved=r['resolved'],ambiguous=r['ambiguous'],unresolved=r['unresolved'],
                             proportion=percentage(r['observed_proportion']),
                             ci95=f"{percentage(r['ci95_block']['low'])} – {percentage(r['ci95_block']['high'])}") for r in per]
        dependency=[dict(symbol=r['symbol'],variant=r['variant'],overlapping_with_prior=r['overlapping_with_prior'],
                         maximum_concurrent=r['maximum_concurrent'],independent_n='Chưa xác định',
                         real_close_outside_H1=r['market_close_outside_boundaries']) for r in rows if r['scenario']=='excluded']
        selected_quality=[q for q in result['quality'] if symbol=='comparison' or q['symbol']==symbol]
        html=f'''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title><style>{STYLE}td:first-child{{max-width:180px;overflow-wrap:anywhere}}</style><main>
<h1>{escape(title)}</h1><p>{links}</p>
<p id="interpretation" class="notice"><b>Giả thuyết H1, không phải win rate thực thi hoặc tái lập xác nhận của tác giả.</b>
Mốc = HA Close Doji; biên bất lợi = wick HA đối hướng; biên thuận đối xứng 1R.
Kiểm tra bằng OHLC thị trường thật từ nến kế tiếp. Không giả định khớp tại giá HA.</p>
<section><h2>Điều kiện mẫu và phạm vi</h2><p>Không minimum impulse. Ít nhất hai clean candles liên tiếp, không giới hạn pullback;
intermediate ngược màu xu hướng, không giới hạn số lượng; toàn nến cùng phía EMA. Doji đúng màu, hai wick,
range lớn hơn ít nhất một trong hai range trước. Thresholds 5/10/20/30/40% là biến thể nghiên cứu, không phải tham số gốc.</p>
{table(selected_quality)}<p>Dữ liệu cũ giữ nguyên, không download. Không có Forex/spot gold; XAU pre-05/01/2026 loại nghiên cứu.
Lịch đóng cửa chưa xác minh. Completeness nội bộ không bao gồm phần thiếu từ cuối snapshot đến cutoff.</p></section>
{blocks}
<section><h2>Cách đọc outcome và uncertainty</h2><p>Resolved=W+L; conservative=W/(W+L+A), optimistic=(W+A)/(W+L+A),
excluded=W/(W+L). Unresolved không ép thành thất bại và không đưa vào ba mẫu số; CSV/JSON lưu bounds gồm censoring.
Open đã vượt biên giải quyết chạm đầu tại open; nếu open ở giữa và high/low chạm cả hai biên thì ambiguous.</p>
<p>CI95 hiển thị là moving calendar-block bootstrap 7 ngày, {result['config']['bootstrap_repetitions']} lần,
seed cố định. CI pointwise, không simultaneous cho 45 hàng. Wilson IID chỉ là tham chiếu trong JSON/CSV.
Dependence kéo dài hơn block vẫn có thể làm CI quá hẹp; không chứng minh independent n, không kiểm định significance để chọn ngưỡng.</p></section>
<section><h2>Overlap và mốc HA so với giá thật</h2>{table(dependency)}<p>Cho phép quan sát chồng lấn; không mô phỏng portfolio.
Các trường hợp Close thị trường đã ngoài biên H1 cho thấy H1 không thể được đọc như giao dịch entry tại HA Close.
Chi phí/spread/funding chưa áp dụng vì đây là crossing study, không P&amp;L.</p></section>
<section><h2>IS / validation / OOS — excluded scenario</h2>{table(partition_rows)}
<p>IS trước 2024, validation năm 2024, OOS từ 2025; gán theo thời điểm Doji đóng. Bảng này censor tại split;
ba bảng full history phía trên theo dõi tới chạm biên/gap/cuối dataset, không horizon nhân tạo.
OOS là hồi cứu đã dùng trước đây. CSV/JSON chứa đủ ba scenarios cho từng partition và kết quả theo năm.</p></section>
<section><h2>Điều chưa xác minh</h2><p>Chưa rõ tác giả dùng HA Close hay giá Close thị trường làm mốc, wick nào làm biên và
đường giá HA hay OHLC thật để chấm kết quả. Precedence Doji sai màu so với intermediate có wick là convention được công bố.
Vì vậy các tỷ lệ trên chỉ đúng với H1 và variant tương ứng; không xác nhận/bác bỏ trực tiếp tuyên bố 75% nguyên bản.</p></section>
<section><h2>Tái lập và kiểm tra</h2><p>{result['tests']['tests']} tests, {result['tests']['failures']} failures,
{result['tests']['errors']} errors. Xem <a href="full_history.csv">45 hàng CSV</a>, <a href="summary.json">JSON đầy đủ</a>,
<a href="audit.json">audit</a>, <a href="browser_qa.json">browser QA</a> và protocol trong repository.</p></section>
<footer>Binance Vision — dữ liệu/phân tích phái sinh theo CC BY-NC-SA 4.0. Offline, không giao dịch thật.</footer></main></html>'''
        (out/f'{symbol}.html').write_text(html,encoding='utf-8')
    md=['# Kết quả D01–D05 / H1', '',
        'H1 là giả thuyết biên HA với đường giá OHLC thật, không phải giá khớp lệnh hoặc tái lập xác nhận phương pháp gốc.', '']
    for scenario in result['config']['scenarios']:
        md += ['## '+labels[scenario], '', '| Instrument | Variant | Patterns | W | L | A | U | Proportion H1 | CI95 block |',
               '|---|---|---:|---:|---:|---:|---:|---|---|']
        for r in result['full_history']:
            if r['scenario']!=scenario:continue
            ci=r['ci95_block']
            md.append(f"| {r['symbol']} | {r['variant']} | {r['patterns']} | {r['observed_successes']} | {r['observed_failures']} | {r['ambiguous']} | {r['unresolved']} | {percentage(r['observed_proportion'])} | {percentage(ci['low'])}–{percentage(ci['high'])} |")
        md.append('')
    md += ['CI pointwise 7-day block bootstrap, không đảm bảo độc lập hoặc simultaneous coverage.',
           'Outcome gốc, executable win rate và profitability vẫn chưa được xác minh. Không lựa chọn threshold theo kết quả.',
           f"Tests: {result['tests']}. Audit/preservation/browser evidence trong cùng thư mục."]
    (out/'FINAL_REPORT.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
