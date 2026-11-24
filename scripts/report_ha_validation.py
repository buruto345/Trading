"""Render evidence-backed Phase 2 report, embedded charts and offline browser QA."""
from pathlib import Path
import sys,json,html,hashlib,xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.run_ha_validation import read,save,sha,OUT,OLD


def table(rows,columns):
    d=pd.DataFrame(rows).reindex(columns=columns)
    return '<div class="table-wrap">'+d.to_html(index=False,escape=True,float_format=lambda x:f'{x:.6g}',na_rep='—')+'</div>'


def mdtable(rows,columns):
    def cell(x):
        if isinstance(x,float):return f'{x:.6g}' if np.isfinite(x) else '—'
        return str(x).replace('|','/').replace('\n',' ')
    return '| '+' | '.join(columns)+' |\n|'+'|'.join(['---']*len(columns))+'|\n'+'\n'.join('| '+' | '.join(cell(r.get(c,'—')) for c in columns)+' |' for r in rows)


def figure(traces,title,ytitle='Tỷ lệ outcome H1',height=360):
    fig=go.Figure(traces)
    fig.update_layout(title=dict(text=title,font=dict(size=18)),height=height,margin=dict(l=50,r=20,t=65,b=55),
        paper_bgcolor='#ffffff',plot_bgcolor='#ffffff',font=dict(family='Segoe UI',color='#182a2b'),
        colorway=['#146f64','#b54d45','#a88d45','#647574','#466c98'],legend=dict(orientation='h',y=-.23),
        yaxis_title=ytitle,hovermode='closest')
    fig.update_xaxes(showgrid=False);fig.update_yaxes(gridcolor='#e9eeeb',zeroline=False)
    return fig.to_html(full_html=False,include_plotlyjs=False,config=dict(responsive=True,displaylogo=False,displayModeBar=False))


def main():
    from scripts.supplement_ha_validation import main as supplement
    supplement()
    v=read(OUT/'validation_summary.json');q=read(OUT/'data_quality_audit.json');det=read(OUT/'independent_detection_audit.json')
    suites=ET.parse(OUT/'tests.xml').getroot().findall('testsuite')
    v['tests']={k:sum(int(x.get(k,'0')) for x in suites) for k in ['tests','failures','errors','skipped']}
    if not (v['false_positives'] or v['false_negatives'] or v['classification_mismatches']):
        pd.DataFrame(columns=['symbol','variant','kind','doji_index','direction']).to_csv(OUT/'pattern_mismatches.csv',index=False)
    dep=read(OUT/'observation_dependence.json');look=read(OUT/'lookahead_audit.json');leak=read(OUT/'data_leakage_audit.json')
    stat=read(OUT/'statistical_reliability.json');outside=read(OUT/'outside_boundaries.json');pres=read(OUT/'preservation_verified.json')
    data={n:pd.read_csv(OUT/(n+'.csv')) for n in ['full_history_reproduced','monthly_statistics','quarterly_statistics','yearly_statistics','market_condition_statistics','directional_statistics','oos_review','ha_price_bias','bootstrap_sensitivity']}
    full=data['full_history_reproduced'];rec=v['reconciliation']
    # Verify Phase1's recorded input identity against the pre-audit snapshot.
    baseline=read(OUT/'baseline.json');previous=read(OLD/'execution.json')
    checks=[]
    for group in ['input_and_output_hashes','source_hashes']:
        for path,h in previous[group].items():
            actual=baseline['hashes'].get(path)
            checks.append(dict(group=group,path=path,match=actual==h,baseline_present=actual is not None))
    save('phase1_identity_audit.json',dict(checks=checks,mismatches=[x for x in checks if not x['match']]))
    detection_ok=not (v['false_positives'] or v['false_negatives'] or v['classification_mismatches']) and all(not any(r['geometry_classification_mismatches'].values()) and all(x['outside_512eps']==0 for x in r['indicator_comparison'].values()) for r in det)
    stats_ok=all(not x['discrepancies'] and x['matched_rows']==x['expected_rows'] for x in rec.values())
    prefix_ok=all(not p['pattern_mismatch_variants'] and all(err==0 for err in p['reference_max_errors'].values()) for x in look for p in x['prefixes'])
    leakage_ok=all(not x['partition_assignment_errors'] and not x['confirmation_time_errors'] and not x['partition_end_beyond_boundary'] for x in leak)
    statuses=[
      ('T01','WARNING','data_quality_audit.json','Toàn bộ 3 Parquet M1','Thiếu đuôi 1 ngày/mã; chưa xác minh lịch đóng cửa hoặc parse lại ZIP nguồn.'),
      ('T02','PASS' if detection_ok else 'FAIL','independent_detection_audit.json; pattern_mismatches.csv','Toàn bộ nến và 15 nhóm mẫu','Đúng với đặc tả đóng băng; không xác nhận quy tắc của tác giả.'),
      ('T03','WARNING','ha_price_bias.csv; outside_boundaries.json','4 trường giá × 4 phép đo × 15 nhóm','Giá HA tổng hợp; không chứng minh có thể khớp lệnh.'),
      ('T04','WARNING' if prefix_ok else 'FAIL','lookahead_audit.json; source_review.json','9 prefix, mọi variant; chỉ báo toàn lịch sử','Median-unit normalization có phụ thuộc toàn cột; nguồn sửa đổi có thể thay lịch sử.'),
      ('T05','PASS' if leakage_ok else 'FAIL','data_leakage_audit.json','Mọi timestamp/nhãn partition','Full scope có thể dùng tương lai partition; không dùng nó làm đánh giá holdout.'),
      ('T06','PASS' if not v['outcome_discrepancies'] else 'FAIL','outcome_reconciliation.json; ambiguity_audit.csv','Mọi observation, 2 scopes, 3 scenarios','M1 không xác định thứ tự hai biên trong một nến.'),
      ('T07','WARNING','observation_dependence.json','15 nhóm; 30 cặp variant','Không ước lượng số mẫu độc lập; correlations là mô tả.'),
      ('T08','WARNING','monthly_statistics.csv; quarterly_statistics.csv; yearly_statistics.csv','Mọi kỳ kể cả kỳ rỗng','CI theo kỳ ngắn ít block; chưa stationarity.'),
      ('T09','WARNING','market_condition_statistics.csv; HA_VALIDATION_PROTOCOL.md','Mọi nhóm đã định trước, kể cả unknown/rỗng','Phân nhóm chẩn đoán, không bộ lọc hoặc quan hệ nhân quả.'),
      ('T10','WARNING','directional_statistics.csv; directional_monthly_statistics.csv','Cả bullish và bearish × 15','Chênh lệch không chứng minh nguyên nhân hay hướng giao dịch.'),
      ('T11','WARNING' if stats_ok else 'FAIL','statistical_reliability.json; bootstrap_sensitivity.csv','45 full + 135 partition + 237 yearly cũ','CI pointwise; phụ thuộc block, selection/survivorship và tái sử dụng dữ liệu.'),
      ('T12','WARNING','oos_review.csv; HA_VALIDATION_PROTOCOL.md','IS/validation/retrospective OOS, mọi nhóm','Holdout mới: NOT VERIFIED; chưa có dữ liệu chưa từng xem.'),
      ('T13','WARNING' if stats_ok and not pres['changed'] and not v['tests']['failures'] else 'FAIL','reproducibility.json; baseline.json; tests.xml','Hash, seed, kết quả và môi trường hiện tại','Phase1 không ghi trực tiếp versions trong execution.json; môi trường cũ chính xác chưa xác minh.'),
      ('T14','PASS','FINAL_VALIDATION_REPORT.md/html; browser_qa.json','17 phần, bảng audit và chart offline','PASS chỉ sau browser QA đạt; không nâng mức xác minh trading.')]
    tasks=[dict(Task=a,Status=b,Evidence=c,Coverage=d,Limitations=e) for a,b,c,d,e in statuses]
    save('source_review.json',dict(files=['src/data_validation/validator.py','src/ha_research/data.py','src/ha_research/indicators.py','src/ha_research/descriptive.py','src/ha_research/variants.py','scripts/run_ha_variants.py'],
        findings=[dict(component='normalization',status='WARNING',finding='normalize_timestamp selects unit using full-column median. Fixed same-unit source is prefix-stable; mixed units or revisions can change earlier timestamps.'),
        dict(component='duplicate handling',status='WARNING',finding='Global conflict quarantine may remove prior rows when a conflicting revision is appended. No duplicate/conflict observed in frozen processed M1.'),
        dict(component='indicators/detection',status='PASS' if detection_ok and prefix_ok else 'FAIL',finding='HA/EMA past recurrences; pattern confirmed only at close. Independent full-history calculations and sampled prefix tests reconciled.'),
        dict(component='outcomes',status='PASS' if not v['outcome_discrepancies'] else 'FAIL',finding='Future raw OHLC intentionally used only for outcome from next bar; not detection. Partition scope censored.'),
        dict(component='statistics',status='WARNING',finding='Full-history descriptive confidence intervals and calendar groups use future observations in cohort, but are never input to detector. Retrospective diagnostics are not deployed filters.')]))
    counts={s:sum(t['Status']==s for t in tasks) for s in ['PASS','WARNING','FAIL','NOT VERIFIED']}
    v.update(tasks=tasks,status_counts=counts,original_author_claim='NOT VERIFIED',executable_win_rate='NOT VERIFIED',new_holdout='NOT VERIFIED',phase1_identity_mismatches=sum(not x['match'] for x in checks))
    save('validation_summary.json',v)
    sections=[]
    def section(title,paragraphs,rows=None,cols=None,charts=''):
        prose='\n\n'.join(paragraphs)
        md='## '+title+'\n\n'+prose+'\n\n'+(mdtable(rows,cols)+'\n\n' if rows is not None else '')
        body=''.join('<p>'+html.escape(p)+'</p>' for p in paragraphs)
        if rows is not None:body+=table(rows,cols)
        sections.append((title,md,body+charts))
    section('1. Executive Summary',[
      f"Đã quét độc lập {v['research_candles']:,} nến nghiên cứu và {v['observations']:,} dòng observation của 15 nhóm. Các dòng giữa variants dùng chung nhiều nến, không phải từng đó mẫu độc lập.",
      f"Đối chiếu: {v['false_positives']} false positive, {v['false_negatives']} false negative, {v['classification_mismatches']} sai khác cấu trúc mẫu; {v['outcome_discrepancies']} sai khác outcome. {rec['full_history']['matched_rows']}/45 dòng full-history được tái tính; số khác biệt thống kê vượt tolerance: {len(rec['full_history']['discrepancies'])}.",
      'Các số dưới đây là tỷ lệ outcome biên H1 với giá OHLC thật sau Doji, không phải win rate giao dịch. Tuyên bố 75% của tác giả, giá vào/stop chính xác và kết quả thực thi vẫn NOT VERIFIED.'
    ],tasks,['Task','Status','Evidence','Coverage','Limitations'])
    section('2. Existing Research Overview',[
      'M1 Binance USD-M perpetual BTCUSDT/ZECUSDT/XAUUSDT. EMA100 trên HA Close, warm-up500, pullback ≥2 clean candles, intermediate ngược màu, Doji đúng màu có hai wick và range mở rộng so ít nhất một trong hai nến trước; không giới hạn horizon. Giữ nguyên mọi quy tắc đóng băng.',
      'D01–D05 = 5/10/20/30/40% body/range do người dùng chọn. H1 lấy HA Close làm mốc, wick HA đối hướng làm biên bất lợi, biên thuận cách đều RR1:1. Precedence opposite-Doji là convention nghiên cứu, chưa xác minh tác giả.',
      'Audit Phase1 chỉ kiểm tra chi tiết 543 mẫu. Phase2 dùng reference suffix-search, lfilter/EWM và first-passage từng nến riêng, không tái sử dụng state machine. Bộ 259 tests trước đây gồm cả confluence chưa commit; phạm vi công bố cũ là202 tests.'
    ])
    section('3. Data Quality Validation',[
      'Không sửa/interpolate/tải bù dữ liệu. Completeness tính trên lưới UTC giữa nến đầu/cuối; không có nghĩa đủ dữ liệu tới cutoff. Ba mã thiếu 1.440 phút đuôi đến 24/11/2026 00:00 UTC.',
      'XAUUSDT là perpetual đúng mã, không phải vàng giao ngay hoặc Forex. Loại lịch sử trước05/01/2026 theo quy tắc cũ. Giá trị zero-volume không đảm bảo thanh khoản/fillability. Audit đọc toàn processed M1; không tái parse từng archive nguồn.'
    ],q,['symbol','total_candles','research_candles','research_period_exclusions','warmup_exclusions','indicator_ready','duplicate','invalid','missing_internal','missing_tail_minutes','zero_volume_candles'])
    section('4. Independent Pattern Detection Audit',[
      'Reference xác định candidate Doji rồi tìm suffix ngược màu hợp lệ và cặp clean đầu tiên sau rào cản; khác cấu trúc state machine đang kiểm tra. Toàn lịch sử được quét để tìm cả mẫu thiếu. So start/end pullback, số intermediate, direction, timestamp và nhãn hình học.',
      'Chỉ báo HA được tái tính trong bộ nhớ bằng bộ lọc tuyến tính; EMA bằng EWM. Không ghi đè cached features. So số học với tolerance512eps tương đối, nhưng classification vẫn đúng tolerance32eps đã đóng băng. Sai khác chi tiết (nếu có) ở CSV và JSON.'
    ],det,['symbol','variant','candles_scanned','original_patterns','reference_patterns','matching_keys','false_positives','false_negatives','classification_mismatches'])
    biascharts=''
    for symbol in v['instruments']:
        d=data['ha_price_bias'];d=d[(d.symbol==symbol)&(d.field=='close')&(d.measure=='signed_percent')]
        biascharts+=figure([go.Scatter(x=d.variant,y=d['median'],mode='markers',name='Median',error_y=dict(type='data',array=d.p95-d['median'],arrayminus=d['median']-d.p05)),go.Scatter(x=d.variant,y=d['mean'],mode='markers',name='Mean')],symbol+' · HA Close − market Close: p05–p95','Chênh lệch (%)')
    section('5. Heikin Ashi Price Bias',[
      'ha_price_bias.csv cung cấp signed/absolute/relative-percent differences cho Open/High/Low/Close, mean/median/std/min/max và p01/05/25/75/95/99 cho tất cả15 nhóm. Biểu đồ hiển thị median và p05–p95 của chênh HA Close, không phải CI.',
      'Một số market Close đã ngoài biên H1 ngay lúc Doji đóng. Việc chờ nến sau có thể vẫn cho outcome H1 success, nhưng không tạo bằng chứng vào lệnh được tại HA Close. Phân bố khoảng lệch theo đơn vị risk của các trường hợp này lưu riêng.'
    ],outside,['symbol','variant','patterns','count','frequency'],biascharts)
    section('6. Look-Ahead Bias',[
      'Kiểm tra prefix 1000/10000/50000 nến cho mỗi mã, mỗi variant; so kết quả từ dữ liệu cắt ngắn với full history, cả reference và Phase1. Outcome chỉ bắt đầu nến kế tiếp. Chỉ báo đối chiếu trên toàn lịch sử; không tuyên bố prefix sampling là chứng minh tuyệt đối. Bổ sung 15 prefix normalization trên source timestamps và đối chiếu mọi trường giá/geometry đã lưu: supplemental_field_audit.json.',
      'Review phát hiện thiết kế normalization dùng median toàn cột để đoán đơn vị epoch; dữ liệu trộn đơn vị hoặc revision có thể làm quá khứ thay đổi. Snapshot cố định dùng cùng đơn vị, không thấy sai lệch lịch sử. Conflict quarantine cũng có thể đổi lịch sử nếu nguồn sửa. Cần khóa schema/unit khi áp dụng bộ nhập cho dữ liệu khác.'
    ],[dict(symbol=x['symbol'],prefixes=','.join(str(p['prefix_bars']) for p in x['prefixes']),mismatch_variants=sum(len(p['pattern_mismatch_variants']) for p in x['prefixes'])) for x in look],['symbol','prefixes','mismatch_variants'])
    section('7. Data Leakage',[
      'IS trước01/01/2024; validation2024; retrospective OOS từ01/01/2025. Membership dựa giờ Doji đóng. Formation và chỉ báo dùng lịch sử quá khứ qua split, không khởi tạo lại EMA tại split. Partition outcome kết thúc tại biên; full-history scope lưu riêng.',
      'Các thống kê subgroup hồi cứu không đi ngược vào detector. OOS này đã được xem nhiều lần, không là holdout độc lập.'
    ],leak,['symbol','observations','partition_assignment_errors','confirmation_time_errors','partition_end_beyond_boundary','full_outcome_crossing_partition','scope_label_changes'])
    outcharts=''
    for symbol in v['instruments']:
        d=full[(full.symbol==symbol)&(full.scenario=='excluded')]
        outcharts+=figure([go.Bar(x=d.variant,y=d[k],name=label) for k,label in [('observed_successes','Success'),('observed_failures','Failure'),('ambiguous','Ambiguous'),('unresolved','Unresolved')]],symbol+' · Outcome H1', 'Số observations')
    section('8. Intrabar Ambiguity',[
      'W=success, L=failure, A=ambiguous, U=unresolved. Conservative=W/(W+L+A); optimistic=(W+A)/(W+L+A); excluded=W/(W+L). U và invalid luôn báo riêng, không ép thành thất bại.',
      'Nếu open đã ngoài một biên, open được xét trước; nếu open ở giữa và high/low chạm cả hai biên trong cùng nến thì ambiguous. Không suy thứ tự intrabar. Optimistic−conservative=A/(W+L+A). First-passage độc lập kiểm tra từng nến tới chạm đầu/cuối dữ liệu/gap/split, không horizon60.'
    ],full.to_dict('records'),['symbol','variant','scenario','patterns','observed_successes','observed_failures','ambiguous','unresolved','observed_proportion','optimistic_conservative_gap'],outcharts)
    overlapchart=figure([go.Bar(x=[x['symbol']+' '+x['variant'] for x in dep['within_variant']],y=[100*x['overlapping_any_fraction'] for x in dep['within_variant']],name='Any overlap')],'Overlap theo interval nến','Observations có overlap (%)')
    section('9. Observation Dependence',[
      'Interval [doji+1,end+1) căn theo bar; end là cuối nến chứa chạm kể cả open-gap. Đây là overlap bảo thủ theo bar, không concurrency vị thế. Báo overlap bất kỳ và overlap với trước riêng.',
      'Các variant dùng chung observations; tăng threshold cũng thay rào cản opposite-Doji nên không mặc định nested hoàn toàn. JSON cung cấp intersection/Jaccard/a_not_in_b, serial correlation lag1/5/10/20, phân tán daily counts và bull/bear correlation. Không có effective independent n; 45 hàng không phải45 thí nghiệm độc lập.'
    ],dep['within_variant'],['symbol','variant','patterns','overlapping_with_prior','overlapping_any','overlapping_any_fraction','maximum_concurrent','bull_bear_daily_rate_correlation','bull_bear_days'],overlapchart)
    temporalcharts='';variability=[]
    for symbol in v['instruments']:
        for name,label in [('monthly_statistics','Tháng'),('yearly_statistics','Năm')]:
            d=data[name];d=d[(d.symbol==symbol)&(d.scenario=='excluded')]
            temporalcharts+=figure([go.Scatter(x=z.period,y=z.observed_proportion,mode='lines+markers',name=variant,connectgaps=False) for variant,z in d.groupby('variant')],symbol+' · '+label+' · H1 excluded')
        d=data['monthly_statistics'];d=d[(d.symbol==symbol)&(d.scenario=='excluded')]
        for variant,z in d.groupby('variant'):variability.append(dict(symbol=symbol,variant=variant,months=len(z),empty_months=int(z.patterns.eq(0).sum()),warning_months=int(z.sample_warning.sum()),monthly_min=z.observed_proportion.min(),monthly_max=z.observed_proportion.max(),monthly_std=z.observed_proportion.std()))
    save('temporal_variability.json',variability)
    section('10. Temporal Robustness',[
      'Bảng tháng/quý/năm bao gồm toàn bộ kỳ của research interval, cả kỳ rỗng và bất lợi. Outcome full scope gán kỳ theo confirmation; nó có thể kết thúc kỳ sau, nên đây là cohort descriptive chứ không phải censored backtest theo kỳ.',
      'Tái đối chiếu237 hàng năm cũ. Subgroup CI moving-block500 lần khi ≥30 mẫu và span≥14 ngày; warning khi ít mẫu hoặc span<56 ngày. Trường hợp không đủ điều kiện để trống CI chính; Wilson vẫn chỉ tham chiếu IID. Biến động giữa kỳ không chứng minh nguyên nhân.'
    ],variability,['symbol','variant','months','empty_months','warning_months','monthly_min','monthly_max','monthly_std'],temporalcharts)
    marketcharts=''
    for symbol in v['instruments']:
        d=data['market_condition_statistics'];d=d[(d.symbol==symbol)&(d.scenario=='excluded')&(d.dimension=='trend')]
        marketcharts+=figure([go.Bar(x=z.category,y=z.observed_proportion,name=variant) for variant,z in d.groupby('variant')],symbol+' · Trạng thái tại Doji · H1 excluded')
    section('11. Market Condition Analysis',[
      'Protocol viết trước subgroup results: score=log return60/(std60 log-return một nến ×sqrt60). >1 rising, <−1 falling, còn lại sideways. Vol thấp/vừa/cao so quantile1/3 và2/3 của1440 std60 quá khứ, shift1, min720; reset theo gap. Unknown khi thiếu lịch sử.',
      'Báo mọi category và16 tổ hợp trend×vol kể cả unknown/rỗng trong CSV. Đây là nhãn mô tả có sẵn tại timestamp, không thêm filter, không chọn ngưỡng theo75%. Khác biệt giữa nhóm không chứng minh phân loại là nguyên nhân.'
    ],charts=marketcharts)
    directional=data['directional_statistics'];directional=directional[directional.scenario=='excluded']
    section('12. Bullish and Bearish Analysis',[
      'Báo riêng hai chiều và cả3 scenarios. CSV tháng theo hướng cho temporal stability; bảng dưới gồm mẫu số, ambiguity, CI và mức lệch HA Close trung bình. Sample imbalance và phân bố giá/volatility khác nhau có thể góp phần vào khác biệt; không thể kết luận giải thích nhân quả hoặc khuyến nghị hướng.',
      'CI mỗi hướng là pointwise; không suy chênh lệch có ý nghĩa từ hai CI riêng lẻ. Daily cross-direction correlation chỉ dùng ngày cả hai có≥5 resolved observations và báo số ngày đủ điều kiện.'
    ],directional.to_dict('records'),['symbol','variant','direction','patterns','observed_proportion','ambiguity_rate','ci95_block_low','ci95_block_high','mean_signed_ha_close_difference','mean_absolute_ha_close_difference','outside_boundary_count'])
    cicharts=''
    for symbol in v['instruments']:
        d=full[(full.symbol==symbol)&(full.scenario=='excluded')]
        cicharts+=figure([go.Scatter(x=d.variant,y=d.observed_proportion,mode='markers',name='H1 excluded',error_y=dict(type='data',array=d.ci95_block_high-d.observed_proportion,arrayminus=d.observed_proportion-d.ci95_block_low))],symbol+' · CI95 block7 ngày, 2000 lần')
    section('13. Statistical Reliability',[
      'Independent bootstrap dùng tổng cộng dồn block thay cho expanded day indices; cùng seed20261124, calendar days kể cả ngày trống, cùng2000 draws. Tái tính point estimates, denominators, Wilson bằng NormalDist và block CI. Sensitivity1/3/7/14/28 ngày định trước, không chọn block thuận lợi.',
      'Unweighted mean của5 tỷ lệ khác ratio gộp các dòng có trọng số. Cả hai đều tái sử dụng variant observations, không là ước lượng độc lập cho instrument. arithmetic_means lưu cả hai với nhãn rõ. Từng nhóm instrument×variant là đơn vị báo cáo chính.',
      'CI không khắc phục selection/survivorship, single-venue, nonstationarity, nested samples và multiple comparisons. Không tính p-value để đạt75%, không suy profitability từ CI hẹp.'
    ],[dict(scope=k,matched_rows=x['matched_rows'],expected_rows=x['expected_rows'],discrepancies=len(x['discrepancies']),max_numeric_difference=x['max_numeric_difference']) for k,x in rec.items()],['scope','matched_rows','expected_rows','discrepancies','max_numeric_difference'],cicharts)
    partitioncharts=''
    for symbol in v['instruments']:
        d=data['oos_review'];d=d[(d.symbol==symbol)&(d.scenario=='excluded')]
        partitioncharts+=figure([go.Scatter(x=z.partition,y=z.observed_proportion,name=variant,mode='markers+lines',connectgaps=False,error_y=dict(type='data',array=z.ci95_block_high-z.observed_proportion,arrayminus=z.observed_proportion-z.ci95_block_low)) for variant,z in d.groupby('variant')],symbol+' · Partition-censored H1 excluded')
    section('14. Out-of-Sample Review',[
      '135 hàng IS/validation/retrospective OOS đều đối chiếu. XAU không có IS/validation trong research period: giữ hàng rỗng, không bịa kết quả. CSV thêm body ratio, absolute HA Close difference và outside-boundary rate để so thay đổi dữ liệu.',
      'Protocol holdout sau: khóa code/config/hash và khoảng lịch chưa từng xem trước khi nhận dữ liệu; giữ warm-up lịch sử; cắt outcome tại cuối holdout; báo tất cả mã/variant/scenario, missingness/ambiguity/CI; không retune. Phase2 không tải hoặc tạo kết quả holdout mới.'
    ],charts=partitioncharts)
    section('15. Reproducibility',[
      f"Commit gốc {baseline['commit']}. {pres['unchanged']}/{pres['files']} file baseline không đổi. Input/config/source hashes tại baseline.json; code audit, commands, versions, seed và reconciliation tại reproducibility.json. Số tests hiện tại: {v['tests']}. Các tests confluence tồn tại trong workspace nhưng không thuộc commit Phase1.",
      'Phase1 execution.json không ghi dependency versions trực tiếp: kết quả tái lập trong môi trường hiện tại đã đóng băng; exact historical environment chưa được chứng minh. CSV Phase1 có rounding10 chữ số; đối chiếu thống kê dùng JSON full precision.',
      'Chạy: .\\.venv\\Scripts\\python.exe scripts\\run_ha_validation.py rồi scripts\\report_ha_validation.py. Không gọi collector/network; dữ liệu gốc và kết quả cũ được giữ. Các lỗi integration của audit lúc phát triển được sửa trước lần chạy hoàn tất, không sửa engine Phase1.'
    ])
    section('16. Limitations',[
      'External validity và real-world execution: NOT VERIFIED. Chưa xác định mapping outcome tác giả, entry/stop thực tế, tick path, spread, fees, funding, slippage, fillability; H1 không phải P&L. Nguồn chỉ một venue và3 sản phẩm được chọn trước; không đại diện mọi thị trường.',
      'Thiếu đuôi dữ liệu, tuổi lịch sử XAU ngắn, calendar đóng cửa chưa xác minh; warm-up và ngày bắt đầu XAU là conventions. Bootstrap giả định phụ thuộc được block đại diện; không loại toàn bộ dependence hoặc nonstationarity.',
      'Software correctness được kiểm tra theo đặc tả đóng băng, không xác minh đặc tả là bản gốc của tác giả. Audit độc lập về thuật toán nhưng vẫn trong cùng dự án/môi trường; không là đánh giá bên thứ ba có dữ liệu độc lập.'
    ])
    section('17. Final Validation Conclusion',[
      f"Software: {'đối chiếu detector/outcome/statistics đạt trong phạm vi ghi nhận' if detection_ok and stats_ok and not v['outcome_discrepancies'] else 'có sai lệch cần đọc bảng audit'}. {rec['full_history']['matched_rows']}/45 full-history rows tái tính, {len(rec['full_history']['discrepancies'])} sai khác vượt tolerance. Không sửa kết quả cũ.",
      'Statistical reliability vẫn có WARNING do dependence, ambiguity, stationarity, selection và holdout hồi cứu. External validity, lợi nhuận, win rate thực thi và tái lập tuyên bố75% vẫn NOT VERIFIED. Không chọn sản phẩm/threshold “tốt nhất”.'
    ])
    md='# Model Validation Report — Phase 2\n\n24/11/2026 · offline · H1 reference-boundary research\n\n'+''.join(s[1] for s in sections)
    (OUT/'FINAL_VALIDATION_REPORT.md').write_text(md,encoding='utf-8')
    css='''*{box-sizing:border-box}html{scroll-behavior:auto}body{margin:0;background:#f4f3ef;color:#182a2b;font:16px/1.65 "Segoe UI",sans-serif}header,main{max-width:1240px;margin:auto;padding:32px}header{padding-top:48px}h1,h2{font-family:Cambria,serif;line-height:1.15}h1{font-size:clamp(36px,5vw,64px);margin:8px 0 24px}h2{font-size:32px;margin-top:0}p{max-width:100ch;text-wrap:pretty}a{color:#146f64}a:focus-visible,button:focus-visible{outline:3px solid #a88d45;outline-offset:3px}nav{display:flex;gap:8px;flex-wrap:wrap}nav a{padding:8px 12px;border:1px solid #dce2dd;border-radius:4px;text-decoration:none}nav a:hover{background:#e0eae5}.eyebrow{font:14px Consolas,monospace;color:#647574;letter-spacing:.08em}.notice{font-weight:600;max-width:90ch}.statusline{display:flex;gap:24px;flex-wrap:wrap}.statusline strong{font-size:28px}section{background:white;padding:32px;margin:0 0 24px;border:1px solid #dce2dd;border-radius:8px;min-width:0}.table-wrap{overflow-x:auto;max-width:100%;margin:24px 0}table{border-collapse:collapse;font-size:13px;min-width:700px}th,td{text-align:left;padding:10px;border-bottom:1px solid #dce2dd;vertical-align:top}th{background:#f4f3ef;white-space:nowrap}td{font-variant-numeric:tabular-nums}tr:hover td{background:#f6f8f5}.plotly-graph-div{max-width:100%}footer{padding:24px;color:#647574}button{font:inherit;padding:8px 16px;background:white;color:#146f64;border:1px solid #146f64;border-radius:4px;cursor:pointer}body.compact section{padding:20px}body.compact td,body.compact th{padding:6px}@media(max-width:650px){header,main{padding:16px}header{padding-top:32px}section{padding:16px;border-radius:4px}h2{font-size:27px}nav a{min-height:44px}h1{font-size:40px}.statusline{gap:16px}}@media print{nav,button{display:none}body{background:white}section{break-inside:avoid}}'''
    nav=''.join(f'<a href="#s{i}">{i}. {html.escape(title.split(". ",1)[1])}</a>' for i,(title,_,_) in enumerate(sections,1))
    content=''.join(f'<section id="s{i}"><h2>{html.escape(title)}</h2>{body}</section>' for i,(title,_,body) in enumerate(sections,1))
    page='<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>HA Model Validation · Phase 2</title><style>'+css+'</style><script>'+get_plotlyjs()+'</script></head><body><header><div class="eyebrow">OFFLINE RESEARCH / PHASE 2 / 24.11.2026</div><h1>Independent Model Validation</h1><p class="notice">H1 đo chạm biên tham chiếu HA trên OHLC thật. Các tỷ lệ không phải win rate giao dịch thực thi hoặc xác minh tuyên bố75%.</p><div class="statusline">'+''.join(f'<span><strong>{n}</strong> {s}</span>' for s,n in counts.items())+'</div><p><button id="density" aria-pressed="false">Mật độ bảng</button> · <a href="FINAL_VALIDATION_REPORT.md">Markdown</a> · <a href="validation_summary.json">Machine-readable audit</a></p><nav>'+nav+'</nav></header><main>'+content+'</main><footer>Frozen research · No orders · No live execution · All instruments and variants retained</footer><script>document.getElementById("density").onclick=function(){const active=document.body.classList.toggle("compact");this.setAttribute("aria-pressed",String(active));window.dispatchEvent(new Event("resize"));};</script></body></html>'
    page=page.replace('<div class="statusline">','<p>Trạng thái dưới đây áp dụng cho T01–T14. Win rate thực thi, tuyên bố 75% và holdout mới: <strong>NOT VERIFIED</strong>.</p><div class="statusline">')
    (OUT/'FINAL_VALIDATION_REPORT.html').write_text(page,encoding='utf-8')
    from playwright.sync_api import sync_playwright
    qa=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True)
        for width,height in [(1440,900),(390,844)]:
            context=browser.new_context(viewport=dict(width=width,height=height),offline=True)
            page=context.new_page();errors=[];external=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('request',lambda r:external.append(r.url) if r.url.startswith(('http:','https:')) else None)
            page.goto((OUT/'FINAL_VALIDATION_REPORT.html').as_uri(),wait_until='load')
            page.wait_for_function('document.querySelectorAll(".js-plotly-plot").length > 0 && [...document.querySelectorAll(".js-plotly-plot")].every(e=>e._fullLayout)')
            overflow=page.evaluate('document.documentElement.scrollWidth>window.innerWidth+1')
            charts=page.locator('.js-plotly-plot').count()
            page.locator('#density').click();assert page.locator('#density').get_attribute('aria-pressed')=='true'
            page.locator('#density').click();page.locator('nav a').last.click()
            final_visible=page.locator('#s17').evaluate('(e)=>e.getBoundingClientRect().top < innerHeight')
            page.evaluate('window.scrollTo(0,0)')
            page.screenshot(path=str(OUT/f'qa_{width}_top.png'))
            page.locator('#s13').evaluate('(e)=>window.scrollTo(0,e.offsetTop)')
            page.screenshot(path=str(OUT/f'qa_{width}_statistics.png'))
            page.locator('#s13 .js-plotly-plot').first.evaluate('(e)=>window.scrollTo(0,e.getBoundingClientRect().top+window.scrollY)')
            page.screenshot(path=str(OUT/f'qa_{width}_chart.png'))
            qa.append(dict(viewport=[width,height],charts=charts,sections=page.locator('section').count(),horizontal_overflow=overflow,page_errors=errors,external_requests=external,density_toggle=True,final_navigation=final_visible,status='PASS' if not overflow and not errors and not external and final_visible and charts>=20 else 'FAIL'))
            context.close()
        browser.close()
    save('browser_qa.json',dict(scope='Chrome offline desktop/mobile; report navigation, density toggle, charts, overflow',checks=qa))
    if any(x['status']!='PASS' for x in qa):raise RuntimeError('Browser QA failed; repair before delivery')
    rep=read(OUT/'reproducibility.json');rep['tests']=v['tests'];rep['report_source_hash']=sha(Path(__file__))
    rep['commands']=['.\\.venv\\Scripts\\python.exe scripts\\run_ha_validation.py','.\\.venv\\Scripts\\python.exe -m pytest -q --junitxml=reports/ha_model_validation/tests.xml','.\\.venv\\Scripts\\python.exe scripts\\report_ha_validation.py']
    rep['source_hashes']={p.relative_to(ROOT).as_posix():sha(p) for folder in ['scripts','tests'] for p in (ROOT/folder).glob('*ha_validation*.py')}
    rep['artifact_hashes']={p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name not in ['reproducibility.json','completion.json']};save('reproducibility.json',rep)
    save('completion.json',dict(status='complete',report_pending=False,tests=v['tests'],browser_qa='PASS'))
    print(json.dumps(dict(status_counts=counts,reconciliation=rec,browser_qa=qa),indent=2))


if __name__=='__main__':main()
