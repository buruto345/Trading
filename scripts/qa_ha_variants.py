"""Reconcile H1 label counts/rates and independently inspect true first passages."""
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import duckdb
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.ha_research.data import digest,save_json


def main():
    out=ROOT/'reports/ha_doji_variants'
    summary=json.loads((out/'summary.json').read_text(encoding='utf-8'))
    con=duckdb.connect();checks=[]
    for symbol in summary['config']['symbols']:
        path=out/f'{symbol}_observations.parquet'
        con.read_parquet(str(path)).create_view('obs',replace=True)
        for row in summary['full_history']+summary['partitioned']:
            if row['symbol']!=symbol:continue
            scope=row['scope'];where=f"variant='{row['variant']}'"
            if scope=='partition':where+=f" AND partition='{row['partition']}'"
            n,bull,bear,w,l,a,u,invalid=con.execute(f'''SELECT count(*),count(*) FILTER(WHERE direction=1),count(*) FILTER(WHERE direction=-1),
                count(*) FILTER(WHERE {scope}_outcome='success'),count(*) FILTER(WHERE {scope}_outcome='failure'),
                count(*) FILTER(WHERE {scope}_outcome='ambiguous'),count(*) FILTER(WHERE {scope}_outcome='unresolved'),
                count(*) FILTER(WHERE {scope}_outcome='invalid') FROM obs WHERE {where}''').fetchall()[0]
            assert [n,bull,bear,w,l,a,u,invalid]==[row[k] for k in ['patterns','bullish','bearish','observed_successes','observed_failures','ambiguous','unresolved','invalid']]
            den=w+l if row['scenario']=='excluded' else w+l+a
            num=w+a if row['scenario']=='optimistic' else w
            assert den==row['denominator'] and num==row['scenario_successes']
            assert row['observed_proportion']==(num/den if den else None)
        # Deterministic sample, covering each outcome type and variant; brute-force full slice.
        e=pd.read_parquet(path)
        f=pd.read_parquet(ROOT/f'data/processed/ha_m1/{symbol}_features.parquet',columns=['timestamp','open','high','low','ha_close','ha_high','ha_low'])
        g=pd.read_parquet(ROOT/f'reports/ha_descriptive/{symbol}_geometry.parquet',
                         columns=['ready','ema_zone','color','clean_direction','both_wicks','body_ratio','range','tolerance'])
        selected=e.groupby(['variant','full_outcome'],group_keys=False).head(12)
        audited=0
        for event in selected.itertuples(index=False):
            i=int(event.doji_index);end=int(event.full_end_index)
            assert event.confirmation_time==f.timestamp.iloc[i]+pd.Timedelta(minutes=1)
            assert event.pullback_count>=2 and event.body_ratio<=event.threshold
            assert event.reference==f.ha_close.iloc[i]
            start,end_pullback=int(event.pullback_start_index),int(event.pullback_end_index)
            assert end_pullback-start+1==event.pullback_count
            assert g.clean_direction.iloc[start:end_pullback+1].eq(event.direction).all()
            assert g.ema_zone.iloc[start:i+1].eq(event.direction).all()
            assert g.ready.iloc[start:i+1].all()
            assert g.color.iloc[end_pullback+1:i].eq(-event.direction).all()
            assert g.color.iloc[i]==event.direction and g.both_wicks.iloc[i]
            assert g.range.iloc[i]>min(g.range.iloc[i-1],g.range.iloc[i-2])+g.tolerance.iloc[i]
            if event.full_outcome=='invalid':continue
            lower,upper=min(event.adverse,event.favorable),max(event.adverse,event.favorable)
            window=f.iloc[i+1:end+1]
            hits=np.flatnonzero((window.high.to_numpy()>=upper)|(window.low.to_numpy()<=lower))
            if event.full_outcome=='unresolved':assert len(hits)==0
            else:
                assert len(hits) and int(hits[0])+i+1==end
                candle=f.iloc[end]
                if candle.open>=upper:expected='success' if event.direction==1 else 'failure'
                elif candle.open<=lower:expected='success' if event.direction==-1 else 'failure'
                elif candle.high>=upper and candle.low<=lower:expected='ambiguous'
                else:expected='success' if (candle.high>=upper)==(event.direction==1) else 'failure'
                assert expected==event.full_outcome
            audited+=1
        checks.append(dict(symbol=symbol,counts='passed',first_passages_and_morphology_audited=audited))
    original=json.loads((out/'preservation_before.json').read_text(encoding='utf-8'))
    changed=[p for p,sha in original.items() if not (ROOT/p).exists() or digest(ROOT/p)!=sha]
    assert not changed,changed
    save_json(out/'preservation_verified.json',dict(status='passed',checked_files=len(original),changed=changed))
    save_json(out/'audit.json',dict(status='passed',checks=checks,full_history_rows=len(summary['full_history'])))
    save_json(out/'browser_qa.json',dict(status='running'))
    errors=[];remote=[];views=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='chrome',headless=True)
        context=browser.new_context(offline=True)
        for name in summary['config']['symbols']+['comparison']:
            page=context.new_page()
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('request',lambda r:remote.append(r.url) if r.url.startswith(('http:','https:')) else None)
            page.goto((out/f'{name}.html').as_uri())
            assert 'Giả thuyết H1' in page.locator('#interpretation').inner_text()
            for scenario in summary['config']['scenarios']:
                assert page.locator(f'#{scenario} tbody tr').count()==(15 if name=='comparison' else 5)
            for width,height in [(1440,900),(390,844)]:
                page.set_viewport_size(dict(width=width,height=height))
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                page.screenshot(path=str(out/f'{name}_{width}.png'),full_page=True)
                views.append(dict(report=name,width=width,overflow=False))
            page.close()
        browser.close()
    assert not errors and not remote
    save_json(out/'browser_qa.json',dict(status='passed',offline=True,views=views,errors=errors,remote_requests=remote))
    print(json.dumps(dict(audit='passed',preserved_files=len(original),browser='passed')))


if __name__=='__main__':main()
