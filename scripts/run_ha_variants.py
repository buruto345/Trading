"""Run 15 D01-D05 combinations offline from verified existing indicators/geometry."""
from datetime import datetime, timezone
import gc
import json
import logging
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.ha_research.data import digest,save_json
from src.ha_research.indicators import partitions
from src.ha_research.variants import detect,label,summarize
from src.ha_research.variant_report import render
from src.statistics.analysis import clean_json


def main():
    out=ROOT/'reports/ha_doji_variants'
    out.mkdir(parents=True,exist_ok=True)
    config=json.loads((ROOT/'config/ha_doji_variants.json').read_text(encoding='utf-8'))
    base=json.loads((ROOT/'config/ha_ema_research.json').read_text(encoding='utf-8'))
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s',
        handlers=[logging.StreamHandler(),logging.FileHandler(out/'pipeline.log',encoding='utf-8')])
    if not (out/'preservation_before.json').exists():
        old=[p for folder in ['data/processed','data/manifests','reports'] for p in (ROOT/folder).rglob('*')
             if p.is_file() and out not in p.parents]
        save_json(out/'preservation_before.json',{p.relative_to(ROOT).as_posix():digest(p) for p in old})
    save_json(out/'completion.json',dict(status='running'))
    save_json(out/'frozen_config.json',config)
    save_json(out/'frozen_base_config.json',base)
    with (out/'tests.log').open('w',encoding='utf-8') as log:
        subprocess.run([sys.executable,'-m','pytest','-q','--basetemp='+str(ROOT/'tests/data/synthetic/.ha_pytest'),
                        '--junitxml='+str(out/'tests.xml')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    suites=ET.parse(out/'tests.xml').getroot().findall('testsuite')
    tests={k:sum(int(s.get(k,'0')) for s in suites) for k in ['tests','failures','errors','skipped']}
    result=dict(config=config,tests=tests,quality=[],full_history=[],partitioned=[],yearly=[],rejections=[])
    previous=json.loads((ROOT/'reports/ha_ema/summary.json').read_text(encoding='utf-8'))
    geometry_execution=json.loads((ROOT/'reports/ha_descriptive/execution.json').read_text(encoding='utf-8'))
    hashes={}
    for symbol in config['symbols']:
        logging.info('%s: verify existing dataset and cached features/geometry',symbol)
        meta_path=ROOT/f'data/manifests/ha_m1/{symbol}.json'
        meta=json.loads(meta_path.read_text(encoding='utf-8'))
        source=ROOT/meta['processed_path']
        if digest(source)!=meta['processed_sha256']:raise ValueError('M1 hash mismatch')
        cached=next(m for m in previous['markets'] if m['symbol']==symbol)
        features=ROOT/cached['feature_path']
        if digest(features)!=cached['feature_sha256']:raise ValueError('Feature hash mismatch')
        gp=ROOT/f'reports/ha_descriptive/{symbol}_geometry.parquet'
        if digest(gp)!=geometry_execution['artifacts'][gp.relative_to(ROOT).as_posix()]:raise ValueError('Geometry hash mismatch')
        for path in [source,features,gp,meta_path]:hashes[path.relative_to(ROOT).as_posix()]=digest(path)
        f=pd.read_parquet(features)
        g=pd.read_parquet(gp)
        if not f.timestamp.equals(g.timestamp) or set(f.symbol.unique())!={symbol}:raise ValueError('Dataset alignment failed')
        if not f.timestamp.is_monotonic_increasing or f.timestamp.duplicated().any():raise ValueError('Ordering failed')
        f['research_partition']=partitions(f.available_at,base)
        q=meta['quality']
        quality=dict(symbol=symbol,source='Binance Vision USD-M perpetual',first=q['earliest_timestamp'],last=q['latest_timestamp'],
            total_candles=q['raw_candles'],valid_candles=q['validated_candles'],research_candles=len(f),
            missing_internal=q['missing_candles'],duplicate=q['duplicate_candles'],invalid=q['invalid_candles'],
            completeness=q['completeness'],missing_tail_minutes=cached['trailing_missing_minutes'],timezone='UTC',
            warmup_bars=base['warmup_bars'],calendar='unverified',quality_provenance='existing validation, input SHA256 rechecked')
        result['quality'].append(quality)
        events=[]
        for variant,threshold in config['variants'].items():
            logging.info('%s %s: detect, label H1, bootstrap',symbol,variant)
            p,rejected=detect(f,g,symbol,variant,threshold)
            e=label(f,p)
            events.append(e)
            info=dict(symbol=symbol,variant=variant,threshold=threshold,total_candles=q['raw_candles'],
                valid_candles=q['validated_candles'],historical_start=q['earliest_timestamp'],historical_end=q['latest_timestamp'],
                outcome_interpretation=config['outcome_interpretation'],original_author_win_rate=None,
                market_close_outside_boundaries=int(e.market_close_outside_boundaries.sum()))
            result['full_history'] += [info|r for r in summarize(e,'full',config)]
            for part in ['in_sample','validation','out_of_sample']:
                subset=e.loc[e.partition.eq(part)]
                result['partitioned'] += [info|dict(partition=part)|r for r in summarize(subset,'partition',config)]
            years=pd.to_datetime(e.confirmation_time,utc=True).dt.year
            for year in sorted(years.unique()):
                subset=e.loc[years.eq(year)]
                result['yearly'] += [info|dict(year=int(year))|r for r in summarize(subset,'full',config,bootstrap=False)]
            result['rejections'].append(dict(symbol=symbol,variant=variant,counts=rejected))
        combined=pd.concat(events,ignore_index=True)
        path=out/f'{symbol}_observations.parquet'
        combined.to_parquet(path,index=False,compression='zstd')
        hashes[path.relative_to(ROOT).as_posix()]=digest(path)
        save_json(out/f'{symbol}.json',clean_json(dict(quality=quality,full_history=[r for r in result['full_history'] if r['symbol']==symbol],
            partitioned=[r for r in result['partitioned'] if r['symbol']==symbol],yearly=[r for r in result['yearly'] if r['symbol']==symbol])))
        save_json(out/'summary.json',clean_json(result))
        del f,g,p,e,events,combined
        gc.collect()
    assert len(result['full_history'])==45
    for name in ['full_history','partitioned','yearly']:
        pd.json_normalize(result[name],sep='_').to_csv(out/f'{name}.csv',index=False,float_format='%.10g')
    save_json(out/'data_quality.json',result['quality'])
    render(ROOT,result)
    paths=list((ROOT/'src/ha_research').glob('*.py'))+list((ROOT/'scripts').glob('*ha*.py'))
    paths+=list((ROOT/'tests').glob('test_ha*.py'))+list((ROOT/'docs').glob('HA_*.md'))
    paths += [ROOT/'config/ha_doji_variants.json',ROOT/'config/ha_ema_research.json']
    save_json(out/'execution.json',dict(completed_at=datetime.now(timezone.utc).isoformat(),network_requests=0,
        rebuilt_indicators=False,input_and_output_hashes=hashes,source_hashes={p.relative_to(ROOT).as_posix():digest(p) for p in paths}))
    subprocess.run([sys.executable,str(ROOT/'scripts/qa_ha_variants.py')],cwd=ROOT,check=True)
    save_json(out/'completion.json',dict(status='passed',combinations=15,scenarios=45,tests=tests))
    logging.info('Completed 15 combinations and 45 H1 reporting rows')


if __name__=='__main__':main()
