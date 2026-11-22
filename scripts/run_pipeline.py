"""Reproducible end-to-end research, with cached source archives and report-only resume."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import json
import logging
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import yaml
import duckdb
from src.pattern_detection.engine import detect_patterns
from src.simulation.engine import simulate_patterns
from src.visualization.features import add_market_features
from src.statistics.analysis import run_analysis, summary
from src.data_collection.collector import collect_all, fetch_minutes

RESULTS=ROOT/'reports/results'
LOG=logging.getLogger('pipeline')

def save_json(path: Path, value) -> None:
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str,allow_nan=False),encoding='utf-8')

def progress(text: str) -> None:
    LOG.info(text)
    with (ROOT/'PROGRESS.md').open('a',encoding='utf-8') as stream:
        stream.write('\n- '+pd.Timestamp.now(tz='Asia/Ho_Chi_Minh').isoformat()+': '+text+'\n')

def run_tests() -> dict:
    result=subprocess.run([sys.executable,'-m','pytest','-q','--junitxml=reports/results/tests.xml','--cov=src','--cov-report=json:reports/results/coverage.json'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
    (ROOT/'logs/tests.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
    print(result.stdout,flush=True)
    root=ET.parse(RESULTS/'tests.xml').getroot()
    suites=list(root.iter('testsuite'))
    metrics={key:sum(int(s.get(key,0)) for s in suites) for key in ['tests','failures','errors','skipped']}
    metrics['passed']=metrics['tests']-metrics['failures']-metrics['errors']-metrics['skipped']
    metrics['coverage_percent']=json.loads((RESULTS/'coverage.json').read_text())['totals']['percent_covered']
    save_json(RESULTS/'test_results.json',metrics)
    if result.returncode: raise RuntimeError('Unit tests failed: see logs/tests.log')
    progress(f"Phase 6: {metrics['passed']} tests passed, {metrics['failures']} failed.")
    return metrics

def partition_patterns(df: pd.DataFrame,symbol: str,max_delay: int):
    boundaries=[0,int(len(df)*.6),int(len(df)*.8),len(df)]
    names=['in_sample','validation','out_of_sample']
    patterns=[];rejects=[];counts={};partitions=[]
    for name,start,end in zip(names,boundaries[:-1],boundaries[1:]):
        part=df.iloc[start:end].reset_index(drop=True)
        p,r,c=detect_patterns(part,symbol,max_sweep_mss=max_delay)
        for key in c: counts[key]=counts.get(key,0)+int(c[key])
        for frame in [p,r]:
            for key in ['sweep_idx','mss_idx','swing_idx','structure_idx','rejected_idx']:
                if key in frame: frame[key]=frame[key]+start
            frame['partition']=name
        if not p.empty:
            def adjust_gaps(value):
                gaps=json.loads(value)
                for gap in gaps: gap['formation_idx']+=start
                return json.dumps(gaps)
            p['fvg_details']=p.fvg_details.map(adjust_gaps)
        p['partition_end_idx']=end
        patterns.append(p);rejects.append(r)
        partitions.append(dict(symbol=symbol,partition=name,start=str(part.timestamp.iloc[0]),end=str(part.timestamp.iloc[-1]),candles=len(part)))
    return pd.concat(patterns,ignore_index=True),pd.concat(rejects,ignore_index=True),counts,partitions

def collect_minutes(preliminary: pd.DataFrame, candles: pd.DataFrame) -> dict:
    ambiguous=preliminary.loc[preliminary.outcome.eq('ambiguous')]
    tasks=sorted({(r.symbol,pd.Timestamp(candles.timestamp.iloc[int(r.exit_idx)]).strftime('%Y-%m-%d')) for r in ambiguous.itertuples()})
    failures=[]
    if tasks: LOG.info('M1 investigation: %s daily archives',len(tasks))
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs={pool.submit(fetch_minutes,symbol,day):(symbol,day) for symbol,day in tasks}
        for i,future in enumerate(as_completed(jobs),1):
            try: future.result()
            except Exception as exc: failures.append(dict(symbol=jobs[future][0],day=jobs[future][1],error=str(exc)))
            if i%25==0: LOG.info('M1 %s/%s',i,len(tasks))
    return dict(requested_days=len(tasks),failed_days=failures)

@lru_cache(maxsize=64)
def cached_minutes(symbol: str,day: str):
    path=ROOT/f'data/processed/m1/{symbol}_{day}.parquet'
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()

def validate_results(sim: pd.DataFrame,patterns: pd.DataFrame) -> dict:
    assert len(sim)==len(patterns)
    assert not patterns.pattern_id.duplicated().any()
    assert (patterns.mss_idx>patterns.sweep_idx).all()
    assert (patterns.confirmation_time>patterns.detection_time).all()
    traded=sim.loc[sim.traded]
    assert (traded.entry_time>=traded.confirmation_time).all()
    assert (traded.entry_idx<traded.partition_end_idx).all()
    assert (traded.exit_idx.fillna(-1)<traded.partition_end_idx).all()
    resolved=sim.loc[sim.outcome.isin(['win','loss'])]
    assert np.allclose(resolved.net_r,resolved.gross_r-resolved.cost_r)
    db=duckdb.connect()
    db.register('simulations',sim)
    sql_counts=db.execute('SELECT outcome, COUNT(*) n, SUM(gross_r) gross_r, SUM(net_r) net_r FROM simulations GROUP BY outcome ORDER BY outcome').fetchdf()
    sql_counts.to_csv(RESULTS/'independent_sql_reconciliation.csv',index=False)
    checks={'patterns_equal_simulation_rows':True,'unique_pattern_ids':True,'causal_timestamps':True,'no_partition_crossing':True,'cost_reconciliation':True,'sql_rows':int(sql_counts.n.sum()),'sql_resolved':len(resolved)}
    save_json(RESULTS/'reconciliation.json',checks)
    return checks

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--skip-collection',action='store_true')
    parser.add_argument('--report-only',action='store_true')
    args=parser.parse_args()
    RESULTS.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',handlers=[logging.StreamHandler(),logging.FileHandler(ROOT/'logs/research.log',encoding='utf-8')])
    if args.report_only:
        from src.reporting.report import generate_report
        generate_report(ROOT)
        return
    started=time.perf_counter()
    cfg=yaml.safe_load((ROOT/'config/research_config.yaml').read_text())
    run_tests()
    if not args.skip_collection: collect_all(ROOT)
    manifest=json.loads((ROOT/'data/manifests/historical_data_manifest.json').read_text(encoding='utf-8'))
    progress('Phase 3–4: Source collection and validated Parquet available; manifest records individual source failures.')
    observations=[];simulations=[];rejections=[];counters={};partition_table=[];minute_audit={};sensitivity=[];excluded={}
    for symbol in cfg['symbols']:
        path=ROOT/f'data/processed/{symbol}_5m.parquet'
        if not path.exists(): LOG.warning('%s unavailable',symbol);continue
        df=pd.read_parquet(path).sort_values('timestamp').reset_index(drop=True)
        # Public gold listing date is an ex ante market eligibility boundary, never inferred from returns.
        initial=len(df)
        df=df.loc[df.timestamp<pd.Timestamp(cfg['data_cutoff_exclusive'])].copy()
        if symbol=='XAUUSDT': df=df.loc[df.timestamp>=pd.Timestamp('2026-01-05T00:00:00Z')]
        df=df.reset_index(drop=True)
        excluded[symbol]=initial-len(df)
        LOG.info('%s processing %s M5 candles',symbol,len(df))
        p,r,c,parts=partition_patterns(df,symbol,cfg['max_sweep_mss'])
        p=add_market_features(df,p)
        observations.append(p);rejections.append(r);counters[symbol]=c;partition_table.extend(parts)
        first=simulate_patterns(df,p,horizon=cfg['observation_horizon'],cost_bps=cfg['round_trip_cost_bps'])
        minute_audit[symbol]=collect_minutes(first,df)
        sim=simulate_patterns(df,p,horizon=cfg['observation_horizon'],cost_bps=cfg['round_trip_cost_bps'],minute_loader=cached_minutes)
        simulations.append(sim)
        LOG.info('%s: %s patterns; %s',symbol,len(p),sim.outcome.value_counts().to_dict())
        df.to_parquet(ROOT/f'data/processed/{symbol}_research_5m.parquet',index=False)
        p.to_parquet(RESULTS/f'{symbol}_patterns.parquet',index=False)
        sim.to_parquet(RESULTS/f'{symbol}_simulations.parquet',index=False)
        progress(f'Phase 7 checkpoint {symbol}: {len(df)} candles, {len(p)} patterns; source-boundary exclusions {excluded[symbol]}.')
        # Two predeclared delays, development data only, no M1 downloading for sensitivity.
        dev=df.iloc[:int(len(df)*.8)].copy()
        for delay in cfg['sensitivity_sweep_mss']:
            LOG.info('%s sensitivity Sweep-MSS=%s, development only',symbol,delay)
            ps,_,_=detect_patterns(dev,symbol,max_sweep_mss=delay)
            ss=simulate_patterns(dev,ps,horizon=cfg['observation_horizon'],cost_bps=cfg['round_trip_cost_bps'],minute_loader=cached_minutes)
            sensitivity.append({'symbol':symbol,'max_sweep_mss':delay,'scope':'development only; cached M1 where available',**summary(ss)})
        # Horizon sensitivity holds the baseline pattern population fixed, excludes OOS.
        for horizon in [144,576]:
            LOG.info('%s sensitivity horizon=%s, development only',symbol,horizon)
            ps=p.loc[p.partition.ne('out_of_sample')]
            ss=simulate_patterns(df,ps,horizon=horizon,cost_bps=cfg['round_trip_cost_bps'],minute_loader=cached_minutes)
            sensitivity.append({'symbol':symbol,'horizon_bars':horizon,'scope':'development only; baseline patterns, cached M1',**summary(ss)})
    if not observations: raise RuntimeError('No authentic datasets collected; cannot fabricate research')
    p=pd.concat(observations,ignore_index=True);sim=pd.concat(simulations,ignore_index=True);rejected=pd.concat(rejections,ignore_index=True)
    from src.statistics.analysis import add_calendar_features
    sim=add_calendar_features(sim)
    p.to_parquet(RESULTS/'patterns.parquet',index=False);sim.to_parquet(RESULTS/'simulations.parquet',index=False);rejected.to_parquet(RESULTS/'rejected.parquet',index=False)
    rejected.groupby(['symbol','reason']).size().rename('count').to_csv(RESULTS/'rejection_counts.csv')
    save_json(RESULTS/'detection_counts.json',counters)
    save_json(RESULTS/'partition_boundaries.json',partition_table)
    save_json(RESULTS/'minute_audit.json',minute_audit)
    save_json(RESULTS/'sensitivity.json',sensitivity)
    save_json(RESULTS/'research_exclusions.json',excluded)
    validate_results(sim,p)
    run_analysis(sim,RESULTS)
    from scripts.audit_results import audit
    audit(ROOT)
    progress('Phase 8–9: Statistics and predeclared sensitivity computed; SQL reconciliation and temporal invariants passed.')
    run_tests()
    from src.reporting.report import generate_report
    generate_report(ROOT)
    from scripts.browser_qa import main as browser_qa
    browser_qa()
    generate_report(ROOT)  # Embed the completed acceptance evidence.
    elapsed=time.perf_counter()-started
    save_json(RESULTS/'execution.json',dict(completed_at=pd.Timestamp.now(tz='Asia/Ho_Chi_Minh').isoformat(),seconds=elapsed,python=sys.version,config=cfg))
    progress(f'Phase 10–11: Self-contained report generated and offline browser QA passed; pipeline elapsed {elapsed:.1f}s.')

if __name__=='__main__': main()
