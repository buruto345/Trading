"""Independent vector/suffix implementation; no imports from ha_research."""
import numpy as np
import pandas as pd
from scipy.signal import lfilter


def features(raw):
    f = raw.reset_index(drop=True).copy()
    n = len(f)
    reset = f.timestamp.diff().ne(pd.Timedelta(minutes=1)).to_numpy()
    starts = np.flatnonzero(reset)
    hc = f[['open','high','low','close']].to_numpy(float).sum(axis=1)/4
    ho, ema, age = np.empty(n), np.empty(n), np.empty(n, dtype=int)
    for a,b in zip(starts, np.r_[starts[1:], n]):
        seed = (f.open.iloc[a]+f.close.iloc[a])/2
        ho[a:b] = lfilter([.5], [1.,-.5], np.r_[0.,hc[a:b-1]], zi=[seed])[0]
        ema[a:b] = pd.Series(hc[a:b]).ewm(span=100, adjust=False).mean().to_numpy()
        age[a:b] = np.arange(1,b-a+1)
    f['ha_close'], f['ha_open'], f['ema100'] = hc,ho,ema
    f['ha_high'] = np.maximum(np.maximum(f.high.to_numpy(),ho),hc)
    f['ha_low'] = np.minimum(np.minimum(f.low.to_numpy(),ho),hc)
    f['segment_id'] = np.cumsum(reset)-1
    f['indicator_ready'] = age >= 500
    f['available_at'] = f.timestamp+pd.Timedelta(minutes=1)
    return f


def geometry(f):
    o,h,l,c,e = (f[k].to_numpy() for k in ['ha_open','ha_high','ha_low','ha_close','ema100'])
    tol = 32*np.finfo(float).eps*np.max(np.abs(np.array([o,h,l,c,e])),axis=0)
    body, ran = abs(c-o), h-l
    upper,lower = h-np.maximum(c,o), np.minimum(c,o)-l
    color = np.where(body<=tol,0,np.sign(c-o)).astype(int)
    zone = np.where(l-e>tol,1,np.where(e-h>tol,-1,0))
    ready = f.indicator_ready.to_numpy()
    clean = np.where(ready & (zone==1)&(color==-1)&(upper<=tol),1,
                     np.where(ready & (zone==-1)&(color==1)&(lower<=tol),-1,0))
    return pd.DataFrame(dict(ready=ready,segment_id=f.segment_id,ema_zone=zone,color=color,
        clean_direction=clean,both_wicks=(upper>tol)&(lower>tol),
        body_ratio=np.divide(body,ran,out=np.full(len(f),np.nan),where=ran>0),range=ran,tolerance=tol))


def detect(g, threshold):
    """Search qualifying suffixes and earliest clean pair, not a state machine."""
    n=len(g); idx=np.arange(n); seg=g.segment_id.to_numpy()
    col,z,ready,cl,ran,tol,ratio,both=(g[k].to_numpy() for k in
        ['color','ema_zone','ready','clean_direction','range','tolerance','body_ratio','both_wicks'])
    expand=np.zeros(n,bool)
    if n>2: expand[2:]=ran[2:]>np.minimum(ran[1:-1],ran[:-2])+tol[2:]
    shape=both & (ratio<=threshold) & np.isfinite(ratio) & expand
    reset=np.r_[True,seg[1:]!=seg[:-1]]
    rows=[]
    for d in [1,-1]:
        opposite=ready & (z==d)&(col==-d)
        # Any invalid candle or wrong-color Doji ends a permissible suffix.
        barrier=(~opposite)|shape
        last_barrier=np.maximum.accumulate(np.where(barrier,idx,-1))
        segment_start=np.maximum.accumulate(np.where(reset,idx,0))
        pairs=np.flatnonzero((cl[:-1]==d)&(cl[1:]==d)&(~reset[1:]))
        # End of each initial clean run, by suffix minimum of non-clean indices.
        stop=np.minimum.accumulate(np.where(cl!=d,idx,n)[::-1])[::-1]
        segment_end=np.minimum.accumulate(np.where(np.r_[reset[1:],True],idx+1,n)[::-1])[::-1]
        candidates=np.flatnonzero(ready&(z==d)&(col==d)&shape)
        for i in candidates:
            if i<2 or reset[i]: continue
            lower=max(last_barrier[i-1]+1,segment_start[i])
            # A reset candle can itself start a run (warmup normally prevents it).
            p=np.searchsorted(pairs,lower)
            if p==len(pairs) or pairs[p]+1>=i: continue
            a=int(pairs[p]); b=int(min(stop[a],segment_end[a]))-1
            rows.append((int(i),d,a,b,b-a+1,int(i-b-1)))
    return pd.DataFrame(rows,columns=['doji_index','direction','pullback_start_index',
        'pullback_end_index','pullback_count','intermediate_count']).sort_values('doji_index').reset_index(drop=True)


def partition(t):
    t=pd.to_datetime(t,utc=True)
    return np.where(t<pd.Timestamp('2024-01-01',tz='UTC'),'in_sample',
        np.where(t<pd.Timestamp('2025-01-01',tz='UTC'),'validation','out_of_sample'))


def passage(o,h,l,start,stop,lo,hi,d):
    for j in range(start,stop):
        if o[j]>=hi: return ('success' if d==1 else 'failure'),j,'open_at_or_above_upper'
        if o[j]<=lo: return ('success' if d==-1 else 'failure'),j,'open_at_or_below_lower'
        up,down=h[j]>=hi,l[j]<=lo
        if up and down: return 'ambiguous',j,'both_boundaries_intrabar'
        if up:return ('success' if d==1 else 'failure'),j,'upper_only'
        if down:return ('success' if d==-1 else 'failure'),j,'lower_only'
    return 'unresolved',max(start-1,stop-1),'domain_end'


def outcomes(f, events):
    n=len(f); o,h,l=(f[k].to_numpy() for k in ['open','high','low'])
    seg=f.segment_id.to_numpy(); part=partition(f.timestamp); idx=np.arange(n)
    last=np.r_[seg[:-1]!=seg[1:],True]
    ends=np.minimum.accumulate(np.where(last,idx+1,n)[::-1])[::-1]
    last_part=last|np.r_[part[:-1]!=part[1:],True]
    pe=np.minimum.accumulate(np.where(last_part,idx+1,n)[::-1])[::-1]
    result=[]
    for v in events.itertuples():
        i=int(v.doji_index);d=int(v.direction);ref=f.ha_close.iloc[i]
        adverse=f.ha_low.iloc[i] if d==1 else f.ha_high.iloc[i]
        risk=d*(ref-adverse);fav=ref+d*risk;lo,hi=sorted([adverse,fav]);row={}
        for scope,stop in [('full',ends[i]),('partition',min(ends[i],pe[i+1] if i+1<n else n))]:
            if risk<=0 or not np.isfinite(risk) or lo<=0: s,j,r='invalid',i,'nonpositive_risk_or_boundary'
            else: s,j,r=passage(o,h,l,i+1,int(stop),lo,hi,d)
            if s=='unresolved':r='dataset_end' if stop==n else 'gap' if stop==ends[i] else 'partition_boundary'
            row.update({scope+'_outcome':s,scope+'_end_index':j,scope+'_reason':r})
        result.append(row)
    return pd.DataFrame(result,index=events.index)
