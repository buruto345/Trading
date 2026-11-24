"""Independent count, interval, dependence and diagnostic calculations."""
from statistics import NormalDist
import numpy as np
import pandas as pd

SCENARIOS=['conservative','optimistic','excluded']


def bootstrap(e,scope='full',block=7,reps=2000,seed=20261124):
    if e.empty:return {s:(None,None,0) for s in SCENARIOS}
    day=pd.to_datetime(e.confirmation_time,utc=True).dt.floor('D')
    days=pd.date_range(day.min(),day.max(),freq='D')
    a=pd.crosstab(day,e[scope+'_outcome']).reindex(index=days,columns=['success','failure','ambiguous'],fill_value=0).fillna(0).to_numpy(float)
    n=len(a); b=min(n,block); k=(n+b-1)//b; tail=n-(k-1)*b
    prefix=np.vstack([np.zeros(3),np.cumsum(a,axis=0)])
    rng=np.random.default_rng(seed)
    starts=rng.integers(0,n-b+1,size=(reps,k))
    counts=(prefix[starts[:,:-1]+b]-prefix[starts[:,:-1]]).sum(axis=1)
    counts+=prefix[starts[:,-1]+tail]-prefix[starts[:,-1]]
    w,l,amb=counts.T;result={}
    for s in SCENARIOS:
        den=w+l if s=='excluded' else w+l+amb
        num=w+amb if s=='optimistic' else w
        v=num[den>0]/den[den>0]
        result[s]=(float(np.quantile(v,.025)),float(np.quantile(v,.975)),len(v)) if len(v) else (None,None,0)
    return result


def summary(e,scope='full',reps=0,**meta):
    counts=e[scope+'_outcome'].value_counts()
    w,l,a,u,invalid=[int(counts.get(k,0)) for k in ['success','failure','ambiguous','unresolved','invalid']]
    intervals=bootstrap(e,scope,reps=reps) if reps else {}
    span=0 if e.empty else (e.confirmation_time.max().floor('D')-e.confirmation_time.min().floor('D')).days+1
    rows=[]
    for s in SCENARIOS:
        den=w+l if s=='excluded' else w+l+a;num=w+a if s=='optimistic' else w
        p=num/den if den else None;z=NormalDist().inv_cdf(.975)
        if den:
            mid=(p+z*z/(2*den))/(1+z*z/den)
            half=z*np.sqrt(p*(1-p)/den+z*z/(4*den*den))/(1+z*z/den)
            wl,wh=mid-half,mid+half
        else:wl=wh=None
        low,high,valid=intervals.get(s,(None,None,0))
        rows.append(dict(meta,scenario=s,patterns=len(e),observed_successes=w,observed_failures=l,
            ambiguous=a,unresolved=u,invalid=invalid,denominator=den,scenario_successes=num,
            observed_proportion=p,ambiguity_rate=a/len(e) if len(e) else None,
            unresolved_rate=u/len(e) if len(e) else None,optimistic_conservative_gap=a/(w+l+a) if w+l+a else None,
            ci95_block_low=low,ci95_block_high=high,ci95_block_valid_repetitions=valid,
            ci95_wilson_iid_reference_low=wl,ci95_wilson_iid_reference_high=wh,
            sample_warning=len(e)<30 or span<56,calendar_span_days=span,
            interval_note='pointwise moving-block; stationarity assumed' if reps else 'block CI unavailable; IID Wilson reference only'))
    return rows


def descriptive(e,**meta):
    span=0 if e.empty else (e.confirmation_time.max()-e.confirmation_time.min()).total_seconds()/86400
    return summary(e,reps=500 if len(e)>=30 and span>=14 else 0,**meta)


def distribution(a):
    a=np.asarray(a,float);a=a[np.isfinite(a)]
    if not len(a):return dict(n=0)
    return dict(n=len(a),mean=float(a.mean()),median=float(np.median(a)),std=float(a.std(ddof=1)) if len(a)>1 else None,
        minimum=float(a.min()),p01=float(np.quantile(a,.01)),p05=float(np.quantile(a,.05)),p25=float(np.quantile(a,.25)),
        p75=float(np.quantile(a,.75)),p95=float(np.quantile(a,.95)),p99=float(np.quantile(a,.99)),maximum=float(a.max()))


def dependence(e):
    e=e.sort_values('doji_index');s=e.doji_index.to_numpy()+1;t=e.full_end_index.to_numpy()+1
    valid=t>s;s=s[valid];t=t[valid];n=len(s)
    previous=s<np.r_[-1,np.maximum.accumulate(t)[:-1]] if n else np.array([],bool)
    following=np.r_[s[1:]<t[:-1],False] if n else np.array([],bool)
    points=sorted([(int(x),1) for x in s]+[(int(x),-1) for x in t]);active=peak=0
    for _,delta in points:active+=delta;peak=max(peak,active)
    resolved=e[e.full_outcome.isin(['success','failure'])]
    y=resolved.full_outcome.eq('success').astype(float)
    lag={str(k):float(y.autocorr(k)) if len(y)>k+2 and y.std()>0 else None for k in [1,5,10,20]}
    daily=e.assign(day=e.confirmation_time.dt.floor('D')).groupby('day').size()
    if len(daily):daily=daily.reindex(pd.date_range(daily.index.min(),daily.index.max()),fill_value=0)
    r=resolved.assign(day=resolved.confirmation_time.dt.floor('D'),win=resolved.full_outcome.eq('success').astype(int))
    agg=r.groupby(['day','direction']).win.agg(['count','mean']).reset_index()
    wide=agg[agg['count']>=5].pivot(index='day',columns='direction',values='mean').dropna()
    corr=float(wide[1].corr(wide[-1])) if {-1,1}.issubset(wide.columns) and len(wide)>2 else None
    return dict(patterns=len(e),nonempty_intervals=n,overlapping_with_prior=int(previous.sum()),
        overlapping_any=int((previous|following).sum()),overlapping_any_fraction=float((previous|following).sum()/len(e)) if len(e) else None,
        maximum_concurrent=peak,independent_n=None,label_lag_correlations=lag,
        daily_count_distribution=distribution(daily),daily_count_variance_mean=float(daily.var()/daily.mean()) if len(daily)>1 and daily.mean()>0 else None,
        bull_bear_daily_rate_correlation=corr,bull_bear_days=len(wide),bull_bear_daily_minimum_resolved=5)


def conditions(f):
    trend=np.full(len(f),'unknown',object);vol=np.full(len(f),'unknown',object)
    for _,ids in f.groupby('segment_id',sort=False).groups.items():
        close=f.loc[ids,'close'];ret=np.log(close).diff();std=ret.rolling(60,min_periods=60).std()
        score=np.log(close/close.shift(60))/(std*np.sqrt(60))
        trend[ids]=np.where(score.notna(),np.where(score>1,'rising',np.where(score< -1,'falling','sideways')),'unknown')
        hist=std.shift(1).rolling(1440,min_periods=720)
        lo,hi=hist.quantile(1/3),hist.quantile(2/3)
        vol[ids]=np.where(lo.notna()&std.notna(),np.where(std<=lo,'low',np.where(std>hi,'high','medium')),'unknown')
    return trend,vol
