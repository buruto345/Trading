"""Execute independent offline Phase 2; preserve all Phase 1 files."""
from pathlib import Path
import sys,json,hashlib,logging,gc,subprocess,xml.etree.ElementTree as ET
from datetime import datetime,timezone
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.ha_validation import reference as ref
from src.ha_validation import statistics as stats
OUT=ROOT/'reports/ha_model_validation';OLD=ROOT/'reports/ha_doji_variants'


def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple,np.ndarray)):return [clean(v) for v in x]
    if isinstance(x,(np.bool_,)):return bool(x)
    if isinstance(x,(np.integer,)):return int(x)
    if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
    if isinstance(x,(pd.Timestamp,datetime)):return x.isoformat()
    return x


def save(name,x):(OUT/name).write_text(json.dumps(clean(x),indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def csv(name,rows):pd.DataFrame(rows).to_csv(OUT/name,index=False)


def compare_rows(rows,old,keys,fields):
    lookup={tuple(str(x[k]) for k in keys):x for x in old};errors=[]
    matched=0;maxdiff=0.
    for r in rows:
        key=tuple(str(r[k]) for k in keys)
        if key not in lookup:continue
        o=lookup[key];matched+=1
        for f in fields:
            a,b=r.get(f),o.get(f)
            if isinstance(a,(float,int,np.number)) and isinstance(b,(float,int,np.number)):
                delta=abs(a-b);maxdiff=max(maxdiff,delta)
                if not np.isclose(a,b,rtol=1e-9,atol=1e-10,equal_nan=True):errors.append(dict(key=key,field=f,actual=a,old=b))
            elif a!=b and not (pd.isna(a) and pd.isna(b)):errors.append(dict(key=key,field=f,actual=a,old=b))
    return dict(matched_rows=matched,expected_rows=len(old),max_numeric_difference=maxdiff,discrepancies=errors)


def prefix_audit(raw,full,g,events):
    from src.ha_research.indicators import indicators
    from src.ha_research.descriptive import geometry
    from src.ha_research.variants import detect
    rows=[]
    for n in [1000,10000,50000]:
        if n>len(raw):continue
        a=ref.features(raw.iloc[:n]);ag=ref.geometry(a)
        old=indicators(raw.iloc[:n]);old['partition']=ref.partition(old.timestamp)
        og=geometry(old);old['research_partition']=ref.partition(old.available_at)
        errors={k:float(np.max(abs(a[k].to_numpy()-full[k].iloc[:n].to_numpy()))) for k in ['ha_open','ha_high','ha_low','ha_close','ema100']}
        original_errors={k:float(np.max(abs(old[k].to_numpy()-full[k].iloc[:n].to_numpy()))) for k in errors}
        mismatches=[]
        for variant,threshold in CONFIG['variants'].items():
            expected=events.loc[(events.variant==variant)&(events.doji_index<n),'doji_index'].tolist()
            r=ref.detect(ag,threshold).doji_index.tolist();o=detect(old,og,'TEST',variant,threshold)[0].doji_index.tolist()
            if r!=expected or o!=expected:mismatches.append(variant)
        rows.append(dict(prefix_bars=n,reference_max_errors=errors,original_max_errors=original_errors,
            pattern_mismatch_variants=mismatches,available_at_matches=bool((a.available_at==a.timestamp+pd.Timedelta(minutes=1)).all())))
    return rows


def main():
    global CONFIG
    OUT.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s',handlers=[logging.StreamHandler(),logging.FileHandler(OUT/'pipeline.log',encoding='utf-8')])
    baseline=read(OUT/'baseline.json');CONFIG=read(ROOT/'config/ha_doji_variants.json');base=read(ROOT/'config/ha_ema_research.json')
    save('frozen_config.json',dict(method=CONFIG,base=base,protocol_sha256=sha(ROOT/'docs/HA_VALIDATION_PROTOCOL.md'),
        audit=dict(block_lengths=[1,3,7,14,28],repetitions=2000,diagnostic_repetitions=500,seed=20261124)))
    save('completion.json',dict(status='running',started_at=datetime.now(timezone.utc)))
    old=read(OLD/'summary.json');quality=[];detection=[];mismatches=[];bias=[];look=[];leak=[];ambiguity=[];depend=[];cross=[]
    fullrows=[];partrows=[];months=[];quarters=[];years=[];market=[];directional=[];directional_monthly=[];sensitivity=[];outside=[];outcome_errors=[]
    fields=['patterns','observed_successes','observed_failures','ambiguous','unresolved','invalid','denominator','scenario_successes','observed_proportion']
    for symbol in CONFIG['symbols']:
        logging.info('%s independent data/indicator audit',symbol)
        raw=pd.read_parquet(ROOT/f'data/processed/ha_m1/{symbol}_1m.parquet')
        frozen=pd.read_parquet(ROOT/f'data/processed/ha_m1/{symbol}_features.parquet')
        prices=raw[['open','high','low','close']].to_numpy(float);t=raw.timestamp;delta=t.diff()/pd.Timedelta(minutes=1)
        invalid=(~np.isfinite(prices).all(axis=1))|(prices<=0).any(axis=1)|(prices[:,1]<prices.max(axis=1))|(prices[:,2]>prices.min(axis=1))
        excluded=0
        if symbol in base['research_start_by_symbol']:
            keep=t>=pd.Timestamp(base['research_start_by_symbol'][symbol]);excluded=int((~keep).sum());research=raw.loc[keep].reset_index(drop=True)
        else:research=raw.copy()
        q=dict(symbol=symbol,total_candles=len(raw),valid_candles=int((~invalid).sum()),research_candles=len(research),
            first=t.min(),last=t.max(),timezone=str(t.dt.tz),ordered=bool(t.is_monotonic_increasing),duplicate=int(t.duplicated().sum()),invalid=int(invalid.sum()),
            missing_internal=int(np.maximum(delta.fillna(1).to_numpy()-1,0).sum()),gap_count=int((delta>1).sum()),
            minute_alignment_errors=int((t.dt.second.ne(0)|t.dt.microsecond.ne(0)|t.dt.nanosecond.ne(0)).sum()),research_period_exclusions=excluded,
            completeness=len(t)/((t.max()-t.min())/pd.Timedelta(minutes=1)+1),
            missing_tail_minutes=int((pd.Timestamp(base['cutoff_exclusive'])-t.max())/pd.Timedelta(minutes=1)-1),
            zero_volume_candles=int(raw.volume.eq(0).sum()),coverage='all processed M1 rows; raw archive contents not re-parsed',closure_calendar='NOT VERIFIED')
        f=ref.features(research);g=ref.geometry(f)
        q['warmup_exclusions']=int((~f.indicator_ready).sum());q['indicator_ready']=int(f.indicator_ready.sum())
        previous=next(x for x in old['quality'] if x['symbol']==symbol)
        q['phase1_count_differences']={k:q[k]-previous[k] for k in ['total_candles','valid_candles','research_candles','duplicate','invalid','missing_internal','missing_tail_minutes','completeness']}
        q['source_alignment']=bool(f.timestamp.equals(frozen.timestamp) and np.array_equal(f[['open','high','low','close']],frozen[['open','high','low','close']]))
        quality.append(q)
        gi=pd.read_parquet(ROOT/f'reports/ha_descriptive/{symbol}_geometry.parquet')
        numeric={k:dict(max_abs=float(np.max(abs(f[k]-frozen[k]))),outside_512eps=int((abs(f[k]-frozen[k])>512*np.finfo(float).eps*np.maximum(abs(frozen[k]),1)).sum())) for k in ['ha_open','ha_close','ha_high','ha_low','ema100']}
        classes={k:int((g[k].to_numpy()!=gi[k].to_numpy()).sum()) for k in ['ready','segment_id','ema_zone','color','clean_direction','both_wicks']}
        events=pd.read_parquet(OLD/f'{symbol}_observations.parquet')
        logging.info('%s exhaustive suffix scan / first-passage verification: %d observation rows',symbol,len(events))
        prefix=prefix_audit(research,f,g,events)
        look.append(dict(symbol=symbol,prefixes=prefix,outcome_start='doji_index + 1',full_indicator_comparison=numeric,
            normalization_note='Frozen processed timestamps UTC; raw normalization infers epoch unit from whole-column median. Mixed-unit/revised inputs can change history; not observed in this fixed homogeneous snapshot.'))
        audited_labels=ref.outcomes(f,events)
        for col in audited_labels:
            bad=events[col].ne(audited_labels[col])
            for ix in events.index[bad]:outcome_errors.append(dict(symbol=symbol,observation_id=events.loc[ix,'observation_id'],field=col,original=events.loc[ix,col],reference=audited_labels.loc[ix,col]))
        for scope in ['full','partition']:
            actual=f.timestamp.iloc[audited_labels[scope+'_end_index'].to_numpy()].reset_index(drop=True)+pd.Timedelta(minutes=1)
            bad=actual.ne(events[scope+'_end_time'].reset_index(drop=True))
            if bad.any():outcome_errors.append(dict(symbol=symbol,field=scope+'_end_time',mismatch_count=int(bad.sum())))
        expected_part=ref.partition(events.confirmation_time)
        boundary=pd.to_datetime(np.where(events.partition=='in_sample','2024-01-01',np.where(events.partition=='validation','2025-01-01','2026-11-24')),utc=True)
        leaks=(events.partition_end_time.to_numpy()>boundary.to_numpy())
        leak.append(dict(symbol=symbol,observations=len(events),partition_assignment_errors=int((expected_part!=events.partition).sum()),
            confirmation_time_errors=int((events.confirmation_time.to_numpy()!=(f.timestamp.iloc[events.doji_index]+pd.Timedelta(minutes=1)).to_numpy()).sum()),
            partition_end_beyond_boundary=int(leaks.sum()),full_outcome_crossing_partition=int((events.full_end_time.to_numpy()>boundary.to_numpy()).sum()),
            scope_label_changes=int(events.full_outcome.ne(events.partition_outcome).sum()),
            indicators_reset_at_partition=False,indicator_evidence='independent continuous recurrence agrees across full history',holdout_status='retrospective reused OOS'))
        trend,vol=stats.conditions(f)
        e=events.copy();e['trend']=trend[e.doji_index];e['volatility']=vol[e.doji_index]
        for variant,threshold in CONFIG['variants'].items():
            logging.info('%s %s: reconcile, bias, dependence, calendar and diagnostic cohorts',symbol,variant)
            sub=e[e.variant==variant].copy();expected=ref.detect(g,threshold)
            expected_ids=set(zip(expected.doji_index,expected.direction));old_ids=set(zip(sub.doji_index,sub.direction))
            fp=old_ids-expected_ids;fn=expected_ids-old_ids
            for kind,ids in [('false_positive',fp),('false_negative',fn)]:
                for i,d in ids:mismatches.append(dict(symbol=symbol,variant=variant,kind=kind,doji_index=i,direction=d))
            merged=expected.merge(sub,on=['doji_index','direction'],suffixes=('_reference','_original'))
            detail=0
            for k in ['pullback_start_index','pullback_end_index','pullback_count','intermediate_count']:
                bad=merged[k+'_reference']!=merged[k+'_original'];detail+=int(bad.sum())
                for row in merged.loc[bad].to_dict('records'):mismatches.append(dict(symbol=symbol,variant=variant,kind=k,doji_index=row['doji_index'],reference=row[k+'_reference'],original=row[k+'_original']))
            detection.append(dict(symbol=symbol,variant=variant,candles_scanned=len(f),original_patterns=len(sub),reference_patterns=len(expected),
                matching_keys=len(old_ids&expected_ids),false_positives=len(fp),false_negatives=len(fn),classification_mismatches=detail,
                duplicate_keys=int(sub.duplicated(['doji_index','direction']).sum()),geometry_classification_mismatches=classes,indicator_comparison=numeric,
                coverage='exhaustive all research candles and all observations',root_cause=None if not (fp or fn or detail) else 'inspect pattern_mismatches.csv'))
            meta=dict(symbol=symbol,variant=variant)
            rows=stats.summary(sub,reps=2000,**meta);fullrows+=rows;ambiguity+=rows
            dep=stats.dependence(sub);depend.append(dict(meta,**dep))
            for b in [1,3,7,14,28]:
                intervals=stats.bootstrap(sub,block=b)
                for scenario,(lo,hi,nrep) in intervals.items():sensitivity.append(dict(meta,scenario=scenario,block_days=b,low=lo,high=hi,valid_repetitions=nrep))
            for part in ['in_sample','validation','out_of_sample']:
                p=sub[sub.partition==part]
                partrows+=stats.summary(p,'partition',reps=2000,**meta,partition=part,
                    mean_body_ratio=float(p.body_ratio.mean()) if len(p) else None,
                    mean_abs_ha_close_difference=float(p.reference_minus_market_close.abs().mean()) if len(p) else None,
                    outside_boundary_rate=float(p.market_close_outside_boundaries.mean()) if len(p) else None)
            for freq,target in [('M',months),('Q',quarters),('Y',years)]:
                times=sub.confirmation_time.dt.tz_localize(None).dt.to_period(freq)
                periods=pd.period_range(f.timestamp.iloc[0].tz_localize(None),f.available_at.iloc[-1].tz_localize(None),freq=freq)
                for period in periods:
                    cohort=sub.loc[times==period]
                    target+=stats.descriptive(cohort,**meta,period=str(period),year=int(period.year))
            for d in [-1,1]:
                cohort=sub[sub.direction==d]
                directional+=stats.descriptive(cohort,**meta,direction=d,
                    mean_signed_ha_close_difference=float(cohort.reference_minus_market_close.mean()) if len(cohort) else None,
                    mean_absolute_ha_close_difference=float(cohort.reference_minus_market_close.abs().mean()) if len(cohort) else None,
                    outside_boundary_count=int(cohort.market_close_outside_boundaries.sum()))
                times=cohort.confirmation_time.dt.tz_localize(None).dt.to_period('M')
                for period in pd.period_range(f.timestamp.iloc[0].tz_localize(None),f.available_at.iloc[-1].tz_localize(None),freq='M'):
                    directional_monthly+=stats.summary(cohort.loc[times==period],**meta,direction=d,period=str(period))
            for name,categories in [('trend',['rising','falling','sideways','unknown']),('volatility',['low','medium','high','unknown'])]:
                for category in categories:market+=stats.descriptive(sub[sub[name]==category],**meta,dimension=name,category=category)
            for tr in ['rising','falling','sideways','unknown']:
                for vo in ['low','medium','high','unknown']:market+=stats.descriptive(sub[(sub.trend==tr)&(sub.volatility==vo)],**meta,dimension='joint',category=tr+'/'+vo)
            ii=sub.doji_index.to_numpy()
            for field in ['close','open','high','low']:
                diff=f['ha_'+field].to_numpy()[ii]-f[field].to_numpy()[ii]
                for kind,values in [('signed',diff),('absolute',abs(diff)),('signed_percent',100*diff/f[field].to_numpy()[ii]),('absolute_percent',100*abs(diff)/f[field].to_numpy()[ii])]:
                    bias.append(dict(meta,field=field,measure=kind,**stats.distribution(values)))
            out=sub.market_close_outside_boundaries
            dist=stats.distribution(sub.loc[out,'reference_minus_market_close']/sub.loc[out,'risk'])
            outside.append(dict(meta,count=int(out.sum()),patterns=len(sub),frequency=float(out.mean()),signed_difference_in_risk_units=dist))
        sets={v:set(e.loc[e.variant==v,'doji_index']) for v in CONFIG['variants']}
        for ai,a in enumerate(sets):
            for b in list(sets)[ai+1:]:cross.append(dict(symbol=symbol,variant_a=a,variant_b=b,intersection=len(sets[a]&sets[b]),union=len(sets[a]|sets[b]),a_not_in_b=len(sets[a]-sets[b]),jaccard=len(sets[a]&sets[b])/len(sets[a]|sets[b])))
        save('data_quality_audit.json',quality);save('independent_detection_audit.json',detection)
        save('lookahead_audit.json',look);save('data_leakage_audit.json',leak)
        del raw,research,f,g,gi,frozen,events,e;gc.collect()
    if mismatches:csv('pattern_mismatches.csv',mismatches)
    else:pd.DataFrame(columns=['symbol','variant','kind','doji_index','direction']).to_csv(OUT/'pattern_mismatches.csv',index=False)
    save('outcome_reconciliation.json',dict(checked_observation_rows=sum(x['original_patterns'] for x in detection),scopes=['full','partition'],discrepancies=outcome_errors))
    for name,rows in [('ha_price_bias.csv',bias),('ambiguity_audit.csv',ambiguity),('full_history_reproduced.csv',fullrows),('oos_review.csv',partrows),
        ('monthly_statistics.csv',months),('quarterly_statistics.csv',quarters),('yearly_statistics.csv',years),('market_condition_statistics.csv',market),
        ('directional_statistics.csv',directional),('directional_monthly_statistics.csv',directional_monthly),('bootstrap_sensitivity.csv',sensitivity)]:csv(name,rows)
    save('outside_boundaries.json',outside);save('observation_dependence.json',dict(within_variant=depend,cross_variant=cross,independent_n=None))
    interval_fields=['ci95_block_low','ci95_block_high','ci95_block_valid_repetitions','ci95_wilson_iid_reference_low','ci95_wilson_iid_reference_high']
    # JSON keeps original full precision; CSV is deliberately rounded in Phase 1.
    oldfull=pd.json_normalize(old['full_history'],sep='_').to_dict('records');oldpart=pd.json_normalize(old['partitioned'],sep='_').to_dict('records')
    oldyear=pd.json_normalize(old['yearly'],sep='_').to_dict('records')
    reconciliation=dict(full_history=compare_rows(fullrows,oldfull,['symbol','variant','scenario'],fields+interval_fields),
        partitioned=compare_rows(partrows,oldpart,['symbol','variant','partition','scenario'],fields+interval_fields),
        yearly=compare_rows(years,oldyear,['symbol','variant','year','scenario'],fields))
    means=[]
    for symbol in CONFIG['symbols']:
        for scenario in stats.SCENARIOS:
            rs=[r for r in fullrows if r['symbol']==symbol and r['scenario']==scenario]
            means.append(dict(symbol=symbol,scenario=scenario,unweighted_mean=np.mean([r['observed_proportion'] for r in rs]),
                duplicated_variant_weighted_ratio=sum(r['scenario_successes'] for r in rs)/sum(r['denominator'] for r in rs),
                warning='Neither statistic is an independent pooled estimate; variants reuse candles and outcomes.'))
    save('statistical_reliability.json',dict(reconciliation=reconciliation,bootstrap_sensitivity=sensitivity,arithmetic_means=means,
        limitations=['pointwise not simultaneous CI','block-length and stationarity sensitivity','resolved label correlations omit ambiguous/unresolved',
        'three preselected surviving instruments, single venue; selection/survivorship not corrected','retrospective variants, no independent 45-experiment interpretation'],
        phase1_dependency_versions='not recorded directly in Phase1 execution.json; present environment frozen, exact historical environment NOT VERIFIED'))
    logging.info('Run complete test suite')
    with (OUT/'tests.log').open('w',encoding='utf-8') as stream:
        tested=subprocess.run([sys.executable,'-m','pytest','-q','--junitxml='+str(OUT/'tests.xml')],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
    suites=ET.parse(OUT/'tests.xml').getroot().findall('testsuite');tests={k:sum(int(x.get(k,'0')) for x in suites) for k in ['tests','failures','errors','skipped']}
    preserved={p:sha(ROOT/p)==h for p,h in baseline['hashes'].items()}
    save('preservation_verified.json',dict(files=len(preserved),unchanged=sum(preserved.values()),changed=[p for p,ok in preserved.items() if not ok]))
    repro=dict(commit=baseline['commit'],baseline='baseline.json',current_environment=baseline['versions'],python=baseline['python'],tests=tests,
        commands=['.\\.venv\\Scripts\\python.exe scripts\\run_ha_validation.py'],network_requests=0,
        source_hashes={p.relative_to(ROOT).as_posix():sha(p) for folder in ['src/ha_validation','scripts','tests'] for p in (ROOT/folder).glob('*ha_validation*.py')},
        reference_source_hashes={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'src/ha_validation').glob('*.py')},
        result_reconciliation=reconciliation,status='PASS' if tested.returncode==0 and all(preserved.values()) and not outcome_errors else 'FAIL')
    save('reproducibility.json',repro)
    summary=dict(instruments=CONFIG['symbols'],research_candles=sum(q['research_candles'] for q in quality),observations=sum(x['original_patterns'] for x in detection),
        false_positives=sum(x['false_positives'] for x in detection),false_negatives=sum(x['false_negatives'] for x in detection),
        classification_mismatches=sum(x['classification_mismatches'] for x in detection),outcome_discrepancies=len(outcome_errors),
        reconciliation=reconciliation,tests=tests,preservation=dict(files=len(preserved),unchanged=sum(preserved.values())))
    save('validation_summary.json',summary)
    save('completion.json',dict(status='analysis_complete',completed_at=datetime.now(timezone.utc),report_pending=True))
    logging.info('Analysis completed: %s',summary)


if __name__=='__main__':main()
