"""Self-contained Vietnamese report; charts are built from stored computed records."""
from __future__ import annotations
import html
import json
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs
from plotly.utils import PlotlyJSONEncoder
from jinja2 import Environment, FileSystemLoader, select_autoescape
from src.statistics.analysis import summary, clean_json

GREEN='#146f64'; RED='#b54d45'; GOLD='#ab812f'; INK='#182a2b'

def number(value,decimals=2):
    if value is None or (isinstance(value,float) and not np.isfinite(value)): return '—'
    return f'{value:,.{decimals}f}' if decimals else f'{value:,.0f}'

def pct(value): return number(value*100,2)+'%' if value is not None else '—'
def ci(s):
    w=s.get('wilson',{}).get('95',{})
    return f"{pct(w.get('low'))} – {pct(w.get('high'))}"

def table(rows,columns):
    head=''.join('<th>'+html.escape(label)+'</th>' for key,label in columns)
    body=''.join('<tr>'+''.join('<td>'+html.escape(str(row.get(key,'—')))+'</td>' for key,_ in columns)+'</tr>' for row in rows)
    return f'<div class="table-scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'

def stats_table(groups):
    rows=[]
    items=groups.items() if isinstance(groups,dict) else [(row.get('group',''),row) for row in groups]
    for label,s in items:
        rows.append(dict(group=label,n=s['patterns'],trades=s['trades'],resolved=s['resolved'],wins=s['wins'],losses=s['losses'],unresolved=s['unresolved'],ambiguous=s['ambiguous'],no_entry=s.get('no_entry',0),wr=pct(s['win_rate']),ci=ci(s),exp=number(s['cost_adjusted']['expectancy_r']),pf=number(s['cost_adjusted']['profit_factor']),q=number(s.get('bh_q_value'),5)))
    return table(rows,[('group','Nhóm'),('n','Patterns'),('trades','Trades'),('resolved','Resolved'),('wins','W'),('losses','L'),('unresolved','U'),('ambiguous','A'),('no_entry','Chưa entry'),('wr','Win Rate'),('ci','Wilson 95%'),('exp','Net E[R]'),('pf','Net PF'),('q','BH q')])

def generate_report(root: Path) -> Path:
    root=Path(root);results=root/'reports/results'
    load=lambda name: json.loads((results/name).read_text(encoding='utf-8'))
    stats=load('statistical_analysis.json');counts=load('detection_counts.json')
    tests=load('test_results.json');manifest=json.loads((root/'data/manifests/historical_data_manifest.json').read_text(encoding='utf-8'))
    partitions=load('partition_boundaries.json');sensitivity=load('sensitivity.json');exclusions=load('research_exclusions.json')
    simulations=pd.read_parquet(results/'simulations.parquet')
    rejected=pd.read_parquet(results/'rejected.parquet')
    overall=stats['overall'];dev=simulations.loc[simulations.partition.ne('out_of_sample')]
    total_candles=sum(c.get('candles',0) for c in counts.values())
    total_raw=sum(m.get('raw_candles',0) for m in manifest['instruments'])
    charts=[]
    def chart(fig,title='',height=360):
        ident=f'chart-{len(charts)}'
        fig.update_layout(title=dict(text=title,font=dict(size=17)),height=height,margin=dict(l=55,r=25,t=65,b=55),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font=dict(family='Segoe UI',color=INK),colorway=[GREEN,RED,GOLD],legend=dict(orientation='h',y=1.12),hovermode='closest')
        fig.update_xaxes(gridcolor='#e1e6e2');fig.update_yaxes(gridcolor='#e1e6e2')
        charts.append(dict(id=ident,figure=fig.to_plotly_json()))
        return f'<div class="chart" id="{ident}" style="min-height:{height}px" aria-label="{html.escape(title)}"></div>'
    sections=[]
    def section(n,title,body,scope=''):
        sections.append(dict(id=f's{n}',number=f'{n:02d}',title=title,body=body,scope=scope))
    def group_chart(rows,title):
        labels=[r.get('group','') for r in rows];rates=[(r['win_rate'] or 0)*100 for r in rows]
        plus=[((r['wilson']['95']['high'] or 0)-(r['win_rate'] or 0))*100 for r in rows]
        minus=[((r['win_rate'] or 0)-(r['wilson']['95']['low'] or 0))*100 for r in rows]
        custom=[[r['patterns'],r['resolved'],r['wins'],r['losses'],r['unresolved'],r['ambiguous'],ci(r)] for r in rows]
        fig=go.Figure(go.Bar(x=labels,y=rates,marker_color=GREEN,error_y=dict(type='data',symmetric=False,array=plus,arrayminus=minus),customdata=custom,hovertemplate='%{x}<br>WR %{y:.2f}%<br>Patterns %{customdata[0]} / resolved %{customdata[1]}<br>W %{customdata[2]} L %{customdata[3]} U %{customdata[4]} A %{customdata[5]}<br>CI %{customdata[6]}<extra></extra>'))
        fig.add_hline(y=100/3,line_dash='dot',line_color=GOLD,annotation_text='BE gross lý tưởng 33.33%')
        fig.update_yaxes(title='Win Rate · %',rangemode='tozero')
        return chart(fig,title)
    def explore(dimension):return [r for r in stats['exploratory'] if r['dimension']==dimension]

    # Genuine examples selected deterministically by earliest confirmation, no profit cherry-picking.
    candles={s:pd.read_parquet(root/f'data/processed/{s}_research_5m.parquet') for s in counts}
    def case_figure(row,rejection=False):
        data=candles[row['symbol']]; end=int(row.get('rejected_idx',row.get('mss_idx',row['sweep_idx'])))
        swing=int(row['swing_idx']);struct=row.get('structure_idx')
        candidates=[swing,int(row['sweep_idx']),end]
        if struct is not None and not pd.isna(struct):candidates.append(int(struct))
        start=max(0,min(candidates)-5);stop=min(len(data),end+15)
        exit_index=row.get('exit_idx')
        if exit_index is not None and pd.notna(exit_index): stop=min(len(data),max(stop,int(exit_index)+5))
        d=data.iloc[start:stop]
        fig=go.Figure(go.Candlestick(x=d.timestamp.astype(str).tolist(),open=d.open.tolist(),high=d.high.tolist(),low=d.low.tolist(),close=d.close.tolist(),increasing_line_color=GREEN,decreasing_line_color=RED,name=row['symbol']))
        for idx,label in [(swing,'Swing'),(int(row['sweep_idx']),'Sweep'),(end,'Rejected' if rejection else 'MSS')]+([(int(struct),'Structure')] if struct is not None and not pd.isna(struct) else []):
            if idx>=start:
                fig.add_annotation(x=str(data.timestamp.iloc[idx]),y=float(data.high.iloc[idx]),text=label,showarrow=True,arrowhead=2,ay=-35,font=dict(size=11))
        if not rejection:
            if exit_index is not None and pd.notna(exit_index):
                ei=int(exit_index)
                fig.add_annotation(x=str(data.timestamp.iloc[ei]),y=float(data.high.iloc[ei]),text='Exit / censor',showarrow=True,arrowhead=2,ay=-55,font=dict(size=11))
            for gap in json.loads(row.get('fvg_details','[]')):
                fig.add_shape(type='rect',x0=str(data.timestamp.iloc[gap['formation_idx']]),x1=str(data.timestamp.iloc[min(end+5,len(data)-1)]),y0=gap['lower'],y1=gap['upper'],fillcolor='rgba(20,111,100,.14)',line_width=0)
            for key,color in [('entry',INK),('stop',RED),('target',GREEN)]:
                value=row.get(key)
                if value is not None and pd.notna(value):fig.add_hline(y=float(value),line_color=color,line_dash='dot',annotation_text=key)
        fig.update_layout(xaxis_rangeslider_visible=False)
        return fig
    case_charts=[];model_charts=[]
    ordered=simulations.sort_values(['confirmation_time','symbol'])
    for direction in ['bullish','bearish']:
        selected=ordered.loc[ordered.direction.eq(direction)]
        if len(selected):
            row=selected.iloc[0].to_dict()
            model_charts.append(chart(case_figure(row),f"{row['symbol']} · {direction} · mẫu lịch sử đầu tiên",420))
    for outcome in ['win','loss','ambiguous','unresolved']:
        selected=ordered.loc[ordered.outcome.eq(outcome)]
        if len(selected):
            row=selected.iloc[0].to_dict()
            case_charts.append(chart(case_figure(row),f"{row['symbol']} · {outcome} · {str(row['confirmation_time'])[:16]}",420)+f'<p class="note">{html.escape(str(row["pattern_id"]))} · {html.escape(str(row.get("reason","")))}. Khung nến quanh setup; entry/stop/target là giả định.</p>')
        else:case_charts.append(f'<p>Không có trường hợp {outcome} trong dữ liệu đã chạy.</p>')
    if len(rejected):
        row=rejected.sort_values(['rejected_time','symbol']).iloc[0].to_dict()
        case_charts.append(chart(case_figure(row,True),f"Rejected · {row['symbol']} · {row['reason']}",420))

    boot=overall.get('bootstrap',{});ess=boot.get('effective_sample_size')
    period=min(p['start'] for p in partitions)[:10]+' → '+max(p['end'] for p in partitions)[:10]
    kpis=[('Historical M5',number(total_candles,0),'nến dùng nghiên cứu'),('Valid patterns',number(overall['patterns'],0),'Sweep + MSS + FVG'),('Win Rate',pct(overall['win_rate']),f"{overall['wins']:,} W / {overall['resolved']:,} resolved"),('Wilson 95%',ci(overall),'tham chiếu IID'),('Net expectancy',number(overall['cost_adjusted']['expectancy_r'])+' R','resolved · cost10bps'),('Effective n',number(ess,0),'heuristic · block7 ngày')]
    extra=[dict(label='Trades thực sự entry',value=overall['trades']),dict(label='Wins / Losses',value=f"{overall['wins']:,} / {overall['losses']:,}"),dict(label='Unresolved / Ambiguous',value=f"{overall['unresolved']:,} / {overall['ambiguous']:,}"),dict(label='Break-even trades',value=overall['breakeven']),dict(label='Chưa entry / Invalid',value=f"{overall.get('no_entry',0)} / {overall['invalid']}"),dict(label='Break-even WR lý tưởng',value='33.33% trước phí'),dict(label='Net Profit Factor',value=number(overall['cost_adjusted']['profit_factor'])),dict(label='Max realized drawdown',value=number(overall['cost_adjusted']['maximum_drawdown_r'])+' R'),dict(label='Research period UTC',value=period)]
    section(1,'Tổng quan nghiên cứu',table(extra,[('label','Chỉ số'),('value','Kết quả')])+f'<p>Weight1 mỗi observation. Win Rate = W/(W+L+B); unresolved và ambiguous không nằm trong mẫu số đó, nhưng được giữ nguyên trong báo cáo. Khoảng tỷ lệ thắng trên toàn bộ trades nếu gán mọi kết quả chưa rõ là thua/thắng: <strong>{pct(overall["win_rate_all_trades_lower"])}–{pct(overall["win_rate_all_trades_upper"])}</strong>. Đây không phải equity của portfolio có vốn hoặc giới hạn vị thế.</p>','Toàn bộ dữ liệu · cấu hình cố định')
    model='''<div class="rule-grid"><div><h3>Swing → Sweep</h3><p>Swing High: Hᵢ &gt; Hᵢ₋₁ và Hᵢ &gt; Hᵢ₊₁; Swing Low dùng dấu &lt;. Xác nhận sau nến kế tiếp đóng. Bỏ equal high/low.</p><p>Bearish sweep vượt Swing High, đóng dưới mức đó và C&lt;O. Bullish sweep xuyên Swing Low, đóng trên mức đó và C&gt;O.</p></div><div><h3>MSS + FVG</h3><p>Bearish MSS đóng dưới Swing Low liên quan; bullish đóng trên Swing High. FVG cùng hướng phải hình thành trong đoạn sweep→MSS, không nhất thiết ngay nến MSS.</p><p>Bullish FVG: Lₖ&gt;Hₖ₋₂. Bearish FVG: Hₖ&lt;Lₖ₋₂. Chỉ biết gap khi nến thứ ba đóng.</p></div></div>'''
    assumptions=(root/'docs/RESEARCH_ASSUMPTIONS.md').read_text(encoding='utf-8')
    section(2,'Định nghĩa ICT & giả định',model+'<details><summary>Đọc toàn bộ giả định thí nghiệm</summary><pre class="prose">'+html.escape(assumptions)+'</pre></details>'+''.join(model_charts),'Quy tắc xác nhận tách biệt với quy ước thực nghiệm')
    data_rows=[]
    for m in manifest['instruments']:
        data_rows.append(dict(symbol=m['symbol'],market=m.get('market_type','unavailable'),period=str(m.get('earliest_timestamp','—'))[:16]+' → '+str(m.get('latest_timestamp','—'))[:16],raw=m.get('raw_candles',0),valid=m.get('validated_candles',0),missing=m.get('missing_candles',0),dup=m.get('duplicate_candles',0),files=m.get('downloaded_files',0),excluded=exclusions.get(m['symbol'],0)))
    data_table=table(data_rows,[('symbol','Instrument'),('market','Market'),('period','UTC archive'),('raw','Raw'),('valid','Validated'),('missing','Vắng trên lưới'),('dup','Duplicates'),('files','ZIP M5'),('excluded','Loại khỏi research')])
    m1files=list((root/'data/manifests/m1').glob('*.json'))
    m1rows=sum(json.loads(f.read_text(encoding='utf-8')).get('validated_candles',0) for f in m1files)
    data_table+=f'<p>M1: {len(m1files)} tệp ngày, {m1rows:,} nến validated. {int(simulations.get("resolution",pd.Series(dtype=str)).eq("M1").sum())} observation được điều tra bằng đoạn M1 đầy đủ và khớp OHLC; một số vẫn ambiguous. Manifest từng ngày lưu trong data/manifests/m1.</p>'
    sources=''.join(f'<li><a href="{html.escape(m.get("source_url","https://data.binance.vision/"))}">{html.escape(m["symbol"])} · Binance Public Data</a></li>' for m in manifest['instruments'])
    section(3,'Dữ liệu & nguồn gốc',data_table+f'<p>{total_raw:,} nến raw. File ZIP gốc, checksum và timestamp nguyên bản được lưu trong project. Không resample lấp giá hoặc dùng synthetic trong nghiên cứu.</p><p>XAUUSDT có archive trước ngày public listing05/01/2026; phần đó bị loại khỏi research theo cutoff00:00UTC của ngày listing. Vắng trên lưới24/7 có thể bao gồm nghỉ phiên, đặc biệt XAU; không đồng nhất với thất lạc download. M1 chỉ tải những ngày cần giải quyết ambiguous.</p><ul>{sources}<li><a href="https://github.com/binance/binance-public-data">Đặc tả Binance Public Data</a></li><li><a href="https://www.binance.com/en/support/announcement/detail/ecf7318c0d434c339e80878588e700d0">Công bố XAUUSDT</a></li></ul><details><summary>Manifest tổng hợp và chất lượng từng mã</summary><pre>'+html.escape(json.dumps(manifest['instruments'],ensure_ascii=False,indent=2))+'</pre></details>')
    countrows=[dict(symbol=s,**c) for s,c in counts.items()]
    overlap_count=int(simulations['overlapping'].sum()) if 'overlapping' in simulations else 0
    counttable=f'<p>{overlap_count:,} pattern có cửa sổ sweep–MSS chồng lên pattern đã xác nhận trước đó. Overlap giao dịch có thể lớn hơn; các quan sát không được coi là độc lập.</p>'+table(countrows,[('symbol','Mã'),('candles','Nến'),('detected_swings','Swings'),('detected_sweeps','Sweeps'),('mss_events','MSS sau sweep'),('detected_fvgs','FVG toàn bộ'),('valid_patterns','Combined'),('rejected_setups','Rejected')])
    intervals=[dict(level=level+'%',low=pct(w['low']),high=pct(w['high']),moe=pct(w['margin_of_error']),normal=pct(w['normal_margin_of_error'])) for level,w in overall['wilson'].items()]
    section(4,'Cỡ mẫu & độ chính xác',counttable+stats_table(stats['instrument_direction'])+table(intervals,[('level','Confidence'),('low','Lower'),('high','Upper'),('moe','Wilson half-width'),('normal','MOE xấp xỉ IID')])+f'<p>Mục tiêu5.000–15.000 là tham khảo, không quota. Không nhân bản hoặc nới điều kiện để đạt số mẫu. Resolved n={overall["resolved"]:,}; effective n≈{number(ess,0)} là heuristic từ variance bootstrap. Số MSS ở đây chỉ đếm MSS của các pending sweep, không phải mọi structure break trên thị trường.</p>')
    curves=stats['curves'];eq=go.Figure()
    for key,label,color in [('gross','Gross',GREEN),('cost_adjusted','Cost-adjusted',RED)]:eq.add_trace(go.Scatter(x=curves['timestamps'],y=curves[key]['equity'],name=label,line=dict(color=color,width=1.5)))
    dd=go.Figure(go.Scatter(x=curves['timestamps'],y=curves['cost_adjusted']['drawdown'],fill='tozeroy',line=dict(color=RED),name='Net drawdown'))
    performance=[]
    labels={'gross_profit_r':'Tổng R dương','gross_loss_r':'Tổng |R âm|','net_result_r':'Tổng kết quả R','expectancy_r':'Expectancy R','profit_factor':'Profit Factor','average_winning_outcome_r':'R dương trung bình','average_losing_outcome_r':'R âm trung bình','std':'Std R','median':'Median R','maximum_drawdown_r':'Max drawdown R','average_drawdown_r':'Average drawdown R'}
    for key,label in labels.items():performance.append(dict(metric=label,gross=number(overall['gross'].get(key)),net=number(overall['cost_adjusted'].get(key))))
    rates=[dict(metric=k,value=pct(overall[k])) for k in ['win_rate','loss_rate','unresolved_rate','ambiguous_rate','censored_rate']]
    section(5,'Kết quả mô phỏng tổng thể',table(rates,[('metric','Rate'),('value','Giá trị')])+table(performance,[('metric','Metric'),('gross','Gross'),('net','Sau cost10bps')])+chart(eq,'Cộng dồn realized R · thứ tự exit')+chart(dd,'Drawdown realized R · cost-adjusted')+'<details><summary>Công thức và mẫu số</summary><p>Win Rate=W/(W+L+B); loss=L/(W+L+B). Unresolved rate=unresolved đã entry/trades; ambiguous rate=A/trades. Expectancy=ΣR/n resolved hữu hạn; PF=ΣR dương/|ΣR âm|; std dùng ddof1; drawdown=max cumulative R trước đó−cumulative R hiện tại, đỉnh ban đầu0. Net R=gross R−entry×cost_bps/(10000×risk). Percentiles trên resolved. Chuỗi W/L theo exit_time; unknown ngắt chuỗi. Giá trị PF không xác định khi không có loss được để trống.</p></details>')
    section(6,'So sánh từng instrument',stats_table(stats['instruments'])+group_chart([dict(group=k,**v) for k,v in stats['instruments'].items()],'Win Rate theo mã · toàn bộ')+'<p>Instrument có lịch sử và độ dài OOS khác nhau. Không coi ba sản phẩm là một exposure đồng nhất; XAUUSDT là perpetual chứ không phải XAUUSD giao ngay.</p>')
    section(7,'Bullish và Bearish',stats_table(stats['directions'])+group_chart([dict(group=k,**v) for k,v in stats['directions'].items()],'Win Rate theo hướng · toàn bộ'))
    timebody=''
    for dimension,label in [('hour','Giờ UTC'),('weekday','Ngày trong tuần'),('month','Tháng'),('quarter','Quý'),('year','Năm')]:
        rows=explore(dimension)
        timebody+=group_chart(rows,label)+f'<details><summary>Bảng {label}: n, W/L/U/A và CI</summary>'+stats_table(rows)+'</details>'
    month_rows=explore('month')
    timebody+=chart(go.Figure(go.Bar(x=[r['group'] for r in month_rows],y=[r['patterns'] for r in month_rows],marker_color=GREEN)),'Số pattern mỗi tháng · development')
    section(8,'Thời gian',timebody,'Exploratory · chỉ in-sample + validation')
    section(9,'Phiên & khoảng giao nhau',group_chart(explore('session'),'Phiên theo giờ địa phương')+stats_table(explore('session'))+'<p>Asian09–18 Asia/Tokyo; London08–17 Europe/London; New York08–17 America/New_York. Múi giờ IANA xử lý DST theo từng ngày. Nhãn overlap loại trừ lẫn nhau. Cửa sổ này áp dụng mọi ngày, không phải lịch mở cửa/ngày lễ của sở giao dịch. Không lọc setup theo phiên.</p>','Exploratory · development')
    characteristics=''
    for col,label in [('fvg_relative','FVG / giá'),('fvg_count','Số FVG'),('sweep_size','Sweep size'),('body_size','Body size'),('wick_size','Wick size'),('delay_bars','Sweep→MSS bars'),('volatility','Volatility'),('volume','Volume')]:
        if col in dev:
            values=pd.to_numeric(dev[col],errors='coerce').dropna().tolist()
            characteristics+=chart(go.Figure(go.Histogram(x=values,nbinsx=45,marker_color=GREEN)),label)
        rows=explore(col+'_bin')
        if rows:characteristics+='<details><summary>Nhóm '+label+' · quantile fit in-sample</summary>'+stats_table(rows)+'</details>'
    scatter=dev.loc[dev.outcome.isin(['win','loss'])].sort_values('confirmation_time').iloc[::max(1,len(dev)//2500)]
    characteristics+=chart(go.Figure(go.Scattergl(x=scatter.delay_bars.tolist(),y=scatter.net_r.tolist(),mode='markers',marker=dict(size=4,opacity=.4,color=GREEN),text=scatter.symbol.tolist())),'Delay và net R · lấy đều theo thời gian, tối đa khoảng2500 điểm')
    characteristics+=stats_table(explore('regime'))+stats_table(explore('daily_bias'))
    section(10,'Đặc trưng pattern & thị trường',characteristics+'<p>Raw-price size/volume khác đơn vị giữa mã; pooled quantile chỉ mang tính mô tả. FVG relative giúp so sánh. Volatility dùng288 return M5 trước/tại sweep. Regime là dấu return24giờ; Daily Bias là hướng ngày UTC đã đóng trước sweep, không phải điều kiện bắt buộc.</p>','Exploratory · development; threshold fit chỉ in-sample')
    heatbody=''
    for dimension,label in [('instrument_direction','Instrument × Direction'),('instrument_session','Instrument × Session'),('weekday_hour','Weekday × Hour'),('year_month','Year × Month')]:
        rows=explore(dimension);xs=sorted({r['keys'][1] for r in rows});ys=sorted({r['keys'][0] for r in rows})
        lookup={tuple(r['keys']):r for r in rows};z=[];text=[]
        for y in ys:
            zr=[];tr=[]
            for x in xs:
                r=lookup.get((y,x))
                zr.append(r['win_rate']*100 if r and r['win_rate'] is not None else None)
                tr.append(f"n={r['resolved']} W={r['wins']} L={r['losses']} U={r['unresolved']} A={r['ambiguous']}<br>95% {ci(r)}"+(' · nhỏ n<30' if r['resolved']<30 else '') if r else 'Không có mẫu')
            z.append(zr);text.append(tr)
        heatbody+=chart(go.Figure(go.Heatmap(x=xs,y=ys,z=z,text=text,colorscale=[[0,'#f6e8dc'],[.5,'#b7d4c5'],[1,GREEN]],zmin=0,zmax=100,hovertemplate='%{y} / %{x}<br>WR %{z:.2f}%<br>%{text}<extra></extra>',colorbar=dict(title='%'))),label)
        heatbody+='<details><summary>Bảng mẫu số và CI · '+label+'</summary>'+stats_table(rows)+'</details>'
    section(11,'Win Rate heatmaps',heatbody,'Exploratory · development; hover để xem W/L/U/A và CI')
    bootrows=[]
    for block,b in stats['bootstrap_sensitivity'].items():
        bootrows.append(dict(days=block,ci=' – '.join(pct(x) for x in b.get('ci',{}).get('95',[None,None])),ess=number(b.get('effective_sample_size'),0),net=' – '.join(number(x) for x in b.get('net_expectancy_ci95',[None,None]))))
    reliability=table(bootrows,[('days','Block ngày'),('ci','Bootstrap WR95%'),('ess','ESS heuristic'),('net','Net expectancy95% R')])
    reliability+=chart(go.Figure(go.Histogram(x=[v*100 for v in boot.get('win_rate_distribution',[])],nbinsx=40,marker_color=GREEN)),'Bootstrap Win Rate · block7 ngày · 1000 lần')
    reliability+=f'<p>Exact binomial một phía H₀:p≤1/3: p={overall["binomial_p_greater_than_one_third"]:.5g}. Kiểm định này giả định IID và payoff gross+2/−1, nên không chứng minh expectancy sau phí hoặc gap. Bootstrap resample block ngày cùng lúc mọi instrument để giữ đồng biến theo lịch; ESS=min(n,p(1−p)/variance bootstrap), chỉ là heuristic. Lag1 active-day WR={number(boot.get("daily_win_rate_lag1_autocorrelation"),4)}.</p><p>{html.escape(stats["method"]["multiple_testing"])}</p>'
    reliability+='<details><summary>Độ nhạy giả định · không chọn cấu hình tốt nhất</summary>'+stats_table([dict(group=f"{r['symbol']} delay={r.get('max_sweep_mss','24')} horizon={r.get('horizon_bars','288')}",**r) for r in sensitivity])+'</details>'
    costrows=[dict(bps=r['round_trip_bps'],n=r['resolved'],exp=number(r['cost_adjusted']['expectancy_r']),pf=number(r['cost_adjusted']['profit_factor']),net=number(r['cost_adjusted']['net_result_r']),be=pct(r['break_even_rate_constant_2R_minus_1R_approx'])) for r in stats['cost_sensitivity']]
    reliability+=table(costrows,[('bps','Round-trip bps'),('n','Resolved'),('exp','Net E[R]'),('pf','Net PF'),('net','Σ Net R'),('be','BE WR xấp xỉ')])
    section(12,'Độ tin cậy thống kê',reliability,'Wilson, block bootstrap, kiểm định và sensitivity')
    outcome_counts=simulations.outcome.value_counts()
    distributions=chart(go.Figure(go.Bar(x=outcome_counts.index.tolist(),y=outcome_counts.tolist(),marker_color=[GREEN if x=='win' else RED if x=='loss' else GOLD for x in outcome_counts.index])),'Tần suất outcomes · toàn bộ')
    for col,label in [('gross_r','Gross R resolved'),('net_r','Net R resolved'),('duration_bars','Duration M5 bars'),('mfe_r','MFE R · exit-bar upper bound'),('mae_r','MAE R · exit-bar upper bound')]:
        distributions+=chart(go.Figure(go.Histogram(x=pd.to_numeric(simulations[col],errors='coerce').dropna().tolist(),nbinsx=50,marker_color=GREEN)),label)
    box=go.Figure()
    for symbol,g in simulations.groupby('symbol'):box.add_trace(go.Box(y=g.net_r.dropna().tolist(),name=symbol,boxpoints=False))
    distributions+=chart(box,'Net R resolved theo instrument · box plot')
    streaks=[]
    for target in ['win','loss']:
        runs=[];length=0
        for outcome in simulations.sort_values('exit_time').outcome:
            if outcome==target:length+=1
            else:
                if length:runs.append(length)
                length=0
        if length:runs.append(length)
        streaks.append(go.Histogram(x=runs,name=target,opacity=.65,xbins=dict(size=1)))
    distributions+=chart(go.Figure(streaks),'Độ dài chuỗi thắng/thua · unknown ngắt chuỗi')
    distributions+=f'<p>Max consecutive W/L: {overall["max_consecutive_wins"]}/{overall["max_consecutive_losses"]}. Average observation duration={number(overall["duration_bars"]["mean"])} M5 bars. Excursion của nến exit có thể xảy ra sau thời điểm chạm boundary: chỉ là upper bound, không suy diễn thành giá có thể thực thi.</p><details><summary>Percentiles gross/net và MFE/MAE</summary><pre>'+html.escape(json.dumps({k:overall[k] for k in ['gross','cost_adjusted','mfe_r','mae_r','duration_bars']},ensure_ascii=False,indent=2))+'</pre></details>'
    section(13,'Phân phối outcomes',distributions,'Toàn bộ · giữ unresolved và ambiguous')
    rejection_table=table(rejected.groupby(['symbol','reason']).size().rename('count').reset_index().to_dict('records'),[('symbol','Mã'),('reason','Lý do reject'),('count','Số lượng')]) if len(rejected) else '<p>Không có rejection.</p>'
    section(14,'Case studies từ giá thật',rejection_table+'<p>Chọn observation sớm nhất theo confirmation_time rồi symbol cho từng outcome; bullish/bearish đầu tiên ở phần02. Rejected chọn sớm nhất theo rejected_time. Không chọn theo lợi nhuận. Vùng xanh là FVG, mũi tên là swing/sweep/structure/MSS. Có thể zoom/pan và bật/tắt series.</p>'+''.join(case_charts))
    oos=stats['partitions'].get('out_of_sample',{})
    oosboot=oos.get('bootstrap',{})
    section(15,'Kiểm định Out-of-sample',stats_table(stats['partitions'])+group_chart([dict(group=k,**v) for k,v in stats['partitions'].items()],'Các partition cố định · 60/20/20')+table(partitions,[('symbol','Mã'),('partition','Partition'),('start','Bắt đầu UTC'),('end','Kết thúc UTC'),('candles','Nến')])+f'<p>Không shuffle; detector bắt đầu mới mỗi đoạn. Outcome bị censor ở ranh giới, không nhìn sang đoạn sau. Các mốc khác nhau theo instrument nên OOS gộp không phải một giai đoạn lịch chung. OOS không tham gia các bảng subgroup hoặc fit quantile. Bootstrap OOS WR95%: {" – ".join(pct(x) for x in oosboot.get("ci",{}).get("95",[None,None]))}. Net expectancy95%: {" – ".join(number(x) for x in oosboot.get("net_expectancy_ci95",[None,None]))} R.</p>','Đánh giá cuối theo protocol đã ấn định')
    limitations='''<ul><li>Một venue và ba mã đã được chọn trước: selection/survivorship bias chưa được loại trừ. Không đại diện universe có sản phẩm đã delist.</li><li>Kho lưu trữ không bảo đảm bao phủ từ ngày đầu giao dịch; tệp có thể được provider sửa. Checksum local đóng băng run này.</li><li>XAU lịch sử ngắn, có prelaunch archive và các khoảng nghỉ; phần trước listing bị loại. M1 vẫn không xác định được thứ tự bên trong một phút.</li><li>Quy tắc swing selection, entry/stop, horizon và overlap là thực nghiệm chưa được chủ mô hình xác nhận. Sensitivity không bao quát mọi cách diễn giải.</li><li>Trades chồng lấn không độc lập, không có hạn mức vốn. Equity/drawdown chỉ cộng realized R, không mark-to-market, funding hoặc liquidation.</li><li>Cost10bps là giả định; không phải phí hiện tại của sàn. Tight risk có thể tạo cost_R rất lớn. Chưa mô hình spread/queue/market impact.</li><li>Wilson/binomial IID có thể quá tự tin. Block bootstrap phụ thuộc độ dài block và tính ổn định theo thời gian. ESS không chứng minh độc lập.</li><li>OOS tách theo từng instrument, không theo cùng calendar date. Aggregate toàn bộ chứa OOS để báo tổng, nhưng exploratory chỉ development.</li><li>FDR của các nhóm chồng lấn và phụ thuộc vẫn chỉ mô tả. Không chuyển subgroup tốt thành khuyến nghị giao dịch.</li></ul>'''
    section(16,'Giới hạn nghiên cứu',limitations)
    qa=load('browser_qa.json') if (results/'browser_qa.json').exists() else {'status':'Chưa chạy tại thời điểm xuất HTML; xem browser_qa.json sau bước QA.'}
    testbody=table([tests],[('tests','Tests'),('passed','Passed'),('failures','Failed'),('errors','Errors'),('skipped','Skipped'),('coverage_percent','Coverage %')])
    testbody+='<p>Coverage là line coverage của suite Python, không phải chứng minh tính đúng của mô hình. Test synthetic nằm riêng với dữ liệu lịch sử. Đối chiếu độc lập DuckDB: pattern ID unique, causality, partition boundary và gross−cost=net.</p><details><summary>QA & reconciliation evidence</summary><pre>'+html.escape(json.dumps({'browser':qa,'reconciliation':load('reconciliation.json')},ensure_ascii=False,indent=2))+'</pre></details>'
    section(17,'Kiểm thử & kiểm tra số liệu',testbody)
    netci=oosboot.get('net_expectancy_ci95',[None,None])
    if netci[0] is None:verdict='OOS chưa đủ thông tin để kết luận expectancy sau phí.'
    elif netci[0]>0:verdict='OOS có khoảng bootstrap expectancy sau phí nằm trên0 dưới cấu hình giả định này; đây là bằng chứng lịch sử có điều kiện, chưa xác nhận khả năng sinh lời tương lai.'
    elif netci[1]<0:verdict='OOS có khoảng bootstrap expectancy sau phí nằm dưới0 dưới cấu hình giả định này; nghiên cứu không hỗ trợ lợi thế sau phí ở cấu hình đang thử.'
    else:verdict='Khoảng bootstrap expectancy sau phí của OOS chứa0; bằng chứng chưa đủ để xác nhận lợi thế sau phí.'
    section(18,'Kết luận từ dữ liệu',f'<p class="conclusion">{verdict}</p><p>Toàn bộ: {overall["patterns"]:,} patterns, {overall["resolved"]:,} resolved, Win Rate{pct(overall["win_rate"])} (Wilson95% {ci(overall)}), {overall["unresolved"]:,} unresolved và {overall["ambiguous"]:,} ambiguous. OOS: {oos.get("resolved",0):,} resolved, {oos.get("wins",0):,}W/{oos.get("losses",0):,}L, {oos.get("unresolved",0):,}U/{oos.get("ambiguous",0):,}A; WR{pct(oos.get("win_rate"))} (95% {ci(oos)}).</p><p>Các quan hệ theo phiên, giờ và đặc trưng là exploratory. Chưa biết kết quả sẽ giữ được trên venue khác, dữ liệu tương lai hoặc cách xác nhận model khác. Không có kết luận bảo đảm lợi nhuận.</p>')

    # Small record schema for live, explicitly separate exploration panel.
    columns=['symbol','direction','confirmation_time','session','partition','outcome','gross_r','net_r','traded']
    records=simulations[columns].copy()
    records['confirmation_time']=pd.to_datetime(records.confirmation_time,utc=True).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    record_json=records.to_json(orient='values',date_format='iso',double_precision=8)
    context=dict(sections=sections,kpis=kpis,period=period,total_candles=total_candles,patterns=overall['patterns'],report_date=pd.Timestamp.now(tz='Asia/Ho_Chi_Minh').strftime('%d/%m/%Y %H:%M UTC+7'),plotly_js=get_plotlyjs(),chart_json=json.dumps(charts,cls=PlotlyJSONEncoder,ensure_ascii=False).replace('</',r'<\/'),records_json=record_json.replace('</',r'<\/'),sessions=sorted(simulations.session.dropna().unique()),symbols=sorted(counts),css=(Path(__file__).parent/'report.css').read_text(encoding='utf-8'),js=(Path(__file__).parent/'report.js').read_text(encoding='utf-8'))
    env=Environment(loader=FileSystemLoader(Path(__file__).parent),autoescape=select_autoescape(['html']))
    destination=root/'reports/ICT_Quantitative_Research_Report.html'
    destination.write_text(env.get_template('template.html').render(**context),encoding='utf-8')
    (results/'report_summary.json').write_text(json.dumps(clean_json(dict(total_candles=total_candles,period=period,overall=overall,tests=tests,report=str(destination))),ensure_ascii=False,indent=2),encoding='utf-8')
    return destination
