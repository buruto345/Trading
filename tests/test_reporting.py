"""Report reconciliation with synthetic outcomes, isolated from historical artifacts."""
import json
from pathlib import Path
import pandas as pd
import pytest
from src.reporting.report import number, pct, stats_table, generate_report
from src.statistics.analysis import analyze
from src.visualization.features import add_market_features


def test_number_handles_unavailable():
    assert number(None)=='—'
    assert number(float('nan'))=='—'
    assert pct(.25)=='25.00%'


def test_stats_table_escapes_labels_and_keeps_unknown_counts():
    s=analyze(pd.DataFrame({'symbol':['BTCUSDT']*3,'direction':['bullish']*3,'confirmation_time':pd.date_range('2024-01-01',periods=3,tz='UTC'),'exit_time':pd.date_range('2024-01-02',periods=3,tz='UTC'),'partition':['in_sample']*3,'outcome':['win','loss','unresolved'],'gross_r':[2.,-1.,None],'net_r':[1.9,-1.1,None]}),bootstrap_reps=20)['overall']
    result=stats_table({'<script>':s})
    assert '&lt;script&gt;' in result and '<script>' not in result
    assert '50.00%' in result and 'Wilson 95%' in result


def test_market_features_do_not_read_future():
    dates=pd.date_range('2024-01-01',periods=600,freq='5min',tz='UTC')
    candles=pd.DataFrame({'timestamp':dates,'open':range(100,700),'close':range(101,701),'high':range(102,702),'low':range(99,699),'volume':10.})
    patterns=pd.DataFrame({'sweep_idx':[300],'direction':['bullish'],'fvg_size':[1.],'sweep_size':[2.]})
    first=add_market_features(candles,patterns)
    changed=candles.copy();changed.loc[301:,'close']=99999.
    second=add_market_features(changed,patterns)
    pd.testing.assert_frame_equal(first,second)


def test_full_offline_html_generation_reconciles_synthetic_records(tmp_path):
    root=tmp_path;out=root/'reports/results';out.mkdir(parents=True)
    (root/'data/manifests').mkdir(parents=True);(root/'data/processed').mkdir();(root/'docs').mkdir()
    (root/'docs/RESEARCH_ASSUMPTIONS.md').write_text('Synthetic test only',encoding='utf-8')
    timestamps=pd.date_range('2024-01-01',periods=20,freq='5min',tz='UTC')
    candles=pd.DataFrame({'timestamp':timestamps,'open':100.,'high':103.,'low':98.,'close':101.,'volume':20.})
    candles.to_parquet(root/'data/processed/BTCUSDT_research_5m.parquet')
    rows=[]
    for i,outcome in enumerate(['win','loss','ambiguous','unresolved','win','loss']):
        rows.append(dict(pattern_id=f'test{i}',symbol='BTCUSDT',direction='bullish' if i%2==0 else 'bearish',sweep_idx=3,mss_idx=6,swing_idx=1,structure_idx=2,sweep_time=timestamps[3],confirmation_time=timestamps[7]+pd.Timedelta(days=i),entry_time=timestamps[7]+pd.Timedelta(days=i),exit_time=timestamps[8]+pd.Timedelta(days=i),fvg_details='[]',entry=101.,stop=98.,target=107.,risk=3.,fvg_size=1.,fvg_count=1,sweep_size=1.,body_size=1.,wick_size=1.,delay_bars=3,volatility=.1,volume=20.,regime='up_24h',daily_bias='aligned',fvg_relative=.01,partition=['in_sample','validation','out_of_sample'][i%3],outcome=outcome,gross_r=2. if outcome=='win' else -1. if outcome=='loss' else None,net_r=1.9 if outcome=='win' else -1.1 if outcome=='loss' else None,cost_r=.1,duration_bars=2,mfe_r=2.,mae_r=1.,reason='synthetic',traded=True))
    from src.statistics.analysis import add_calendar_features
    frame=add_calendar_features(pd.DataFrame(rows));frame.to_parquet(out/'simulations.parquet')
    pd.DataFrame([dict(symbol='BTCUSDT',swing_idx=1,structure_idx=2,sweep_idx=3,rejected_idx=5,rejected_time=timestamps[6],reason='mss_without_fvg')]).to_parquet(out/'rejected.parquet')
    stats=analyze(frame,bootstrap_reps=20)
    artifacts={'statistical_analysis.json':stats,'detection_counts.json':{'BTCUSDT':{'candles':20,'valid_patterns':6}},'test_results.json':{'tests':1,'passed':1,'failures':0,'errors':0,'skipped':0,'coverage_percent':0},'partition_boundaries.json':[{'symbol':'BTCUSDT','partition':'in_sample','start':str(timestamps[0]),'end':str(timestamps[-1]),'candles':20}],'sensitivity.json':[],'research_exclusions.json':{},'reconciliation.json':{'synthetic_only':True}}
    for name,value in artifacts.items():(out/name).write_text(json.dumps(value),encoding='utf-8')
    (root/'data/manifests/historical_data_manifest.json').write_text(json.dumps({'instruments':[{'symbol':'BTCUSDT','raw_candles':20}]}))
    destination=generate_report(root)
    page=destination.read_text(encoding='utf-8')
    assert '<html lang="vi">' in page
    assert 'window.RESEARCH_RECORDS=' in page
    assert '<script src=' not in page and '<link ' not in page
    assert 'id="s18"' in page and 'id="instrument"' in page
    exported=json.loads((out/'report_summary.json').read_text(encoding='utf-8'))
    assert exported['overall']['patterns']==6
    assert exported['overall']['wins']==2 and exported['overall']['unresolved']==1

