"""Reproducible offline extension; never calls collection or overwrites baseline artifacts."""
import sys,json,hashlib,subprocess,time
from pathlib import Path
from functools import lru_cache
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.multi_model.detectors import detect_models,NAMES
from src.multi_model.simulation import simulate_track
from src.data_validation.validator import validate_candles
from src.visualization.features import add_market_features
from src.statistics.analysis import summary,analyze,clean_json,add_calendar_features
OUT=ROOT/'reports/multi_model'

def save(name,obj):
    (OUT/name).write_text(json.dumps(clean_json(obj),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def protected():
    files=list((ROOT/'reports/results').rglob('*'))+list((ROOT/'src').rglob('*.py'))+list((ROOT/'data/processed').rglob('*.parquet'))
    files += [ROOT/'reports/ICT_Quantitative_Research_Report.html',ROOT/'data/manifests/historical_data_manifest.json']
    return {str(p.relative_to(ROOT)):digest(p) for p in files if p.is_file() and 'multi_model' not in p.parts}

@lru_cache(maxsize=32)
def minutes(symbol,day):
    path=ROOT/f'data/processed/m1/{symbol}_{day}.parquet'
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()

def contrasts(sim,reps=1000):
    # Common calendar resampling preserves dependence across model and instrument.
    d=sim[sim.outcome.isin(['win','loss'])].copy();d['day']=pd.to_datetime(d.confirmation_time,utc=True).dt.floor('D')
    if d.empty:return []
    days=pd.date_range(d.day.min(),d.day.max(),freq='D');arrays=[]
    for model in range(5):
        a=d[d.model==model].groupby('day').agg(n=('net_r','size'),net=('net_r','sum')).reindex(days,fill_value=0).to_numpy(float)
        arrays.append(a)
    data=np.stack(arrays,axis=1);rng=np.random.default_rng(20261121);draws=[]
    block=min(7,len(days))
    for _ in range(reps):
        starts=rng.integers(len(days),size=int(np.ceil(len(days)/block)))
        ix=((starts[:,None]+np.arange(block))%len(days)).ravel()[:len(days)]
        sums=data[ix].sum(axis=0)
        means=np.divide(sums[:,1],sums[:,0],out=np.full(5,np.nan),where=sums[:,0]>0)
        draws.append(means-means[0])
    draws=np.asarray(draws);out=[]
    for model in range(1,5):
        finite=draws[:,model][np.isfinite(draws[:,model])]
        total=data.sum(axis=0);point=total[model,1]/total[model,0]-total[0,1]/total[0,0] if total[model,0] and total[0,0] else None
        ci=np.quantile(finite,[.00625,.99375]).tolist() if len(finite) else [None,None]
        out.append(dict(model=model,baseline=0,delta_net_expectancy=point,ci98_75_bonferroni=ci,valid_reps=len(finite),resolved_model=int(total[model,0]),resolved_baseline=int(total[0,0])))
    return out

def main():
    started=time.time();OUT.mkdir(parents=True,exist_ok=True)
    before=protected();save('preservation_before.json',before)
    test=subprocess.run([sys.executable,'-m','pytest','-q','--junitxml=reports/multi_model/tests.xml'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
    (OUT/'tests.log').write_text(test.stdout+'\n'+test.stderr,encoding='utf-8');print(test.stdout,flush=True)
    if test.returncode:raise RuntimeError('Tests failed')
    allp=[];allr=[];allf=[];alls=[];coverage=[];parts=[];data={}
    manifest=json.loads((ROOT/'data/manifests/historical_data_manifest.json').read_text(encoding='utf-8'))
    for symbol in ['XAUUSDT','BTCUSDT','ZECUSDT']:
        original=pd.read_parquet(ROOT/f'data/processed/{symbol}_5m.parquet')
        df,meta=validate_candles(original)
        assert meta['invalid_candles']==meta['duplicate_candles']==0
        df=df[df.timestamp<pd.Timestamp('2026-11-21T00:00Z')]
        if symbol=='XAUUSDT':df=df[df.timestamp>=pd.Timestamp('2026-01-05T00:00Z')]
        df=df.reset_index(drop=True);data[symbol]=df
        _,usedmeta=validate_candles(df);coverage.append({'symbol':symbol,**usedmeta,'raw_validated_rows':len(original)})
        print(symbol,len(df),'candles',flush=True)
        pp=[]
        bounds=[0,int(len(df)*.6),int(len(df)*.8),len(df)]
        for name,start,end in zip(['in_sample','validation','out_of_sample'],bounds[:-1],bounds[1:]):
            print(symbol,name,'detecting',flush=True)
            p,r,f=detect_models(df.iloc[start:end].reset_index(drop=True),symbol)
            for frame in [p,r,f]:
                for col in frame:
                    if col.endswith('_idx'):frame[col]=pd.to_numeric(frame[col],errors='coerce')+start
                if 'fvg_details' in frame:
                    def offset_details(value):
                        if not isinstance(value,str):return value
                        gaps=json.loads(value)
                        for gap in gaps:gap['formation_idx']+=start
                        return json.dumps(gaps)
                    frame['fvg_details']=frame.fvg_details.map(offset_details)
                frame['partition']=name;frame['partition_end_idx']=end
                if 'pattern_id' in frame:frame['pattern_id']=frame.pattern_id.astype(str)+':'+name
            p=add_market_features(df,p)
            pp.append(p);allr.append(r);allf.append(f)
            parts.append(dict(symbol=symbol,partition=name,start=str(df.timestamp.iloc[start]),end=str(df.timestamp.iloc[end-1]),candles=end-start))
        p=pd.concat(pp,ignore_index=True);allp.append(p)
        for track in ['A','B']:
            print(symbol,track,'simulating',p.model.value_counts().to_dict(),flush=True)
            s=simulate_track(df,p,horizon=288,cost_bps=10,minute_loader=minutes,track=track);s['track']=track
            alls.append(add_calendar_features(s))
    patterns=pd.concat(allp,ignore_index=True);sim=pd.concat(alls,ignore_index=True)
    rejects=pd.concat(allr,ignore_index=True);formations=pd.concat(allf,ignore_index=True)
    for name,frame in [('patterns',patterns),('simulations',sim),('rejected',rejects),('formations',formations)]:frame.to_parquet(OUT/f'{name}.parquet',index=False)
    save('coverage.json',coverage);save('partitions.json',parts);save('manifest_snapshot.json',manifest)
    rejects.groupby(['model','symbol','reason']).size().rename('count').to_csv(OUT/'rejection_counts.csv')
    assert not patterns.pattern_id.duplicated().any()
    assert len(sim)==2*len(patterns)
    traded=sim[sim.traded];resolved=sim[sim.outcome.isin(['win','loss'])]
    assert (traded.entry_time>=traded.confirmation_time).all()
    assert (traded.entry_idx<traded.partition_end_idx).all()
    assert (traded.exit_idx.fillna(-1)<traded.partition_end_idx).all()
    assert np.allclose(resolved.net_r,resolved.gross_r-resolved.cost_r)
    new=sim[(sim.model==0)&(sim.track=='B')].sort_values(['symbol','sweep_time']).reset_index(drop=True)
    old=pd.read_parquet(ROOT/'reports/results/simulations.parquet').sort_values(['symbol','sweep_time']).reset_index(drop=True)
    for col in ['outcome','gross_r','net_r','entry_time','exit_time']:
        pd.testing.assert_series_equal(new[col],old[col],check_names=False,check_dtype=False)
    totals=[];analyses={};groups=[]
    overlap_start=max(pd.Timestamp(c['earliest_timestamp']) for c in coverage)
    overlap_end=min(pd.Timestamp(c['latest_timestamp'])+pd.Timedelta(minutes=5) for c in coverage)
    for (track,model),g in sim.groupby(['track','model']):
        print('statistics',track,model,flush=True)
        analysis=analyze(g,bootstrap_reps=1000);analyses[f'{track}:{model}']=analysis
        # Track A variable targets invalidate the fixed-2R binomial null in reused module.
        if track=='A' and model!=0:
            def strip(obj):
                if isinstance(obj,dict):
                    for k in list(obj):
                        if k in ['binomial_p_greater_than_one_third','bh_q_value','bh_reject_05','break_even_win_rate_gross','risk_reward','dependence_test']:obj[k]=None
                        else:strip(obj[k])
                elif isinstance(obj,list):
                    for x in obj:strip(x)
            strip(analysis)
            analysis['cost_sensitivity']=[]
        save(f'analysis_{track}_{model}.json',analysis)
        s=analysis['overall'];s['track']=track;s['model']=int(model);s['name']=NAMES[model];totals.append(s)
        for dim in ['symbol','direction','session','session_sb','hour','weekday','month','year','partition']:
            for key,grp in g.groupby(dim,dropna=False):groups.append({'track':track,'model':int(model),'dimension':dim,'group':str(key),**summary(grp)})
        for dim in ['volatility','fvg_relative','sweep_relative']:
            vals=g.loc[g.partition=='in_sample',dim].dropna()
            if len(vals)<4:continue
            cuts=np.unique(vals.quantile([.25,.5,.75]).to_numpy());bins=pd.cut(g[dim],np.r_[-np.inf,cuts,np.inf])
            for key,grp in g.groupby(bins,observed=True,dropna=False):groups.append({'track':track,'model':int(model),'dimension':dim,'group':str(key),**summary(grp)})
        common=g[(g.confirmation_time>=overlap_start)&(g.confirmation_time<overlap_end)]
        groups.append({'track':track,'model':int(model),'dimension':'common_calendar','group':f'{overlap_start} .. {overlap_end}',**summary(common)})
    save('summary.json',totals);save('groups.json',groups)
    save('contrasts.json',{track:contrasts(sim[sim.track==track]) for track in ['A','B']})
    pd.json_normalize(totals).to_csv(OUT/'summary.csv',index=False)
    save('reconciliation.json',{'patterns':len(patterns),'simulation_rows':len(sim),'original_baseline_exact_match':True,'causal_entry':True,'partition_boundaries':True,'cost_identity':True,'unique_patterns':True,'counts':sim.groupby(['track','model','outcome']).size().rename('n').reset_index().to_dict('records')})
    after=protected();assert before==after,'Protected baseline or data changed'
    save('preservation_verified.json',{'all_unchanged':True,'files':len(before),'sha256':after})
    save('execution.json',{'seconds':time.time()-started,'python':sys.version,'completed_at':pd.Timestamp.now(tz='Asia/Ho_Chi_Minh').isoformat(),'bootstrap_seed':20261121,'protocol_sha256':digest(ROOT/'docs/MULTI_MODEL_PROTOCOL.md'),'downloads':0})
    from src.multi_model.report import generate
    generate(ROOT)
    from scripts.audit_multi_model import main as audit
    from scripts.qa_multi_model import main as browser_qa
    audit()
    browser_qa()
    generate(ROOT)
    print('COMPLETE',time.time()-started,flush=True)

if __name__=='__main__':main()
