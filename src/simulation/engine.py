"""Offline first-passage simulation; unresolved and ambiguous observations retained."""
from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd

STEP=pd.Timedelta(minutes=5)
SIM_COLUMNS=['entry_idx','exit_idx','entry_time','exit_time','entry','stop','target','risk',
             'outcome','reason','gross_r','net_r','cost_r','duration_bars','duration_minutes',
             'mfe_r','mae_r','excursion_is_bound','resolution','traded','minute_data_error']


def _minute_outcome(minutes: pd.DataFrame, timestamp: pd.Timestamp, direction: str,
                    stop: float, target: float, expected_ohlc: tuple|None=None) -> tuple[str,float,pd.Timestamp] | None:
    """Resolve only a complete, consistent ordered five-minute segment."""
    if minutes is None or len(minutes)==0:
        return None
    t=pd.to_datetime(minutes.timestamp,utc=True)
    m=minutes.loc[(t>=timestamp)&(t<timestamp+STEP)].copy()
    m['timestamp']=pd.to_datetime(m.timestamp,utc=True)
    m=m.sort_values('timestamp')
    if len(m)!=5 or m.timestamp.duplicated().any() or not np.array_equal(m.timestamp.to_numpy(),pd.date_range(timestamp,periods=5,freq='min').to_numpy()):
        return None
    if expected_ohlc is not None:
        actual=(m.open.iloc[0],m.high.max(),m.low.min(),m.close.iloc[-1])
        if not np.allclose(actual,expected_ohlc,rtol=1e-9,atol=1e-8):
            return None
    bull=direction=='bullish'
    for bar in m.itertuples():
        if (bull and bar.open<=stop) or (not bull and bar.open>=stop):
            return 'loss',float(bar.open),bar.timestamp
        if (bull and bar.open>=target) or (not bull and bar.open<=target):
            return 'win',target,bar.timestamp
        sl=bar.low<=stop if bull else bar.high>=stop
        tp=bar.high>=target if bull else bar.low<=target
        if sl and tp:
            return 'ambiguous',float('nan'),bar.timestamp+pd.Timedelta(minutes=1)
        if sl or tp:
            return ('loss',stop,bar.timestamp+pd.Timedelta(minutes=1)) if sl else ('win',target,bar.timestamp+pd.Timedelta(minutes=1))
    return None


def simulate_patterns(df: pd.DataFrame, patterns: pd.DataFrame, horizon: int=288,
                      cost_bps: float=10, minute_loader: Callable|None=None) -> pd.DataFrame:
    """Next-open entry, sweep-extreme stop, 2R target; costs in round-trip notional bps.

    partition_end_idx is exclusive. Entry and every observed bar must precede it.
    Minute loader accepts (symbol, UTC 'YYYY-MM-DD') and returns OHLCV or None.
    """
    if horizon<1 or cost_bps<0:
        raise ValueError('horizon must be positive and cost_bps nonnegative')
    if 'pattern_id' in patterns and patterns.pattern_id.duplicated().any():
        raise ValueError('Duplicate pattern_id would double-count observations')
    ts=pd.to_datetime(df.timestamp,utc=True).reset_index(drop=True)
    o,h,l,c=(df[k].to_numpy(float) for k in ('open','high','low','close'))
    output=[]
    for p in patterns.to_dict('records'):
        entry_idx=int(p['mss_idx'])+1
        boundary=p.get('partition_end_idx',len(df))
        boundary=len(df) if pd.isna(boundary) else min(int(boundary),len(df))
        r={**p,'entry_idx':entry_idx,'exit_idx':None,'entry_time':pd.NaT,'exit_time':pd.NaT,
           'entry':np.nan,'stop':p['sweep_extreme'],'target':np.nan,'risk':np.nan,
           'outcome':'unresolved','reason':'end_of_data_or_partition','gross_r':np.nan,
           'net_r':np.nan,'cost_r':np.nan,'duration_bars':0,'duration_minutes':0.,'mfe_r':np.nan,'mae_r':np.nan,
           'excursion_is_bound':True,'resolution':'M5','traded':False,'minute_data_error':None}
        if entry_idx>=boundary:
            output.append(r);continue
        if ts.iloc[entry_idx]-ts.iloc[entry_idx-1] != STEP:
            r['reason']='gap_before_entry';output.append(r);continue
        entry=float(o[entry_idx]);bull=p['direction']=='bullish';sign=1 if bull else -1
        stop=float(p['sweep_extreme']);risk=(entry-stop)*sign
        r.update(entry=entry,entry_time=ts.iloc[entry_idx],risk=risk)
        if risk<=0 or not np.isfinite(risk):
            r.update(outcome='invalid',reason='nonpositive_risk');output.append(r);continue
        target=entry+sign*2*risk
        r.update(target=target,traded=True,cost_r=cost_bps/10000*entry/risk,mfe_r=0.,mae_r=0.)
        last=min(entry_idx+horizon,boundary)
        for j in range(entry_idx,last):
            if j>entry_idx and ts.iloc[j]-ts.iloc[j-1]!=STEP:
                r['reason']='data_gap';break
            r.update(exit_idx=j,exit_time=ts.iloc[j]+STEP,duration_bars=j-entry_idx+1)
            # These are whole-bar excursion upper bounds whenever an exit happens.
            fav=(h[j]-entry)/risk if bull else (entry-l[j])/risk
            adv=(entry-l[j])/risk if bull else (h[j]-entry)/risk
            r['mfe_r']=max(r['mfe_r'],fav);r['mae_r']=max(r['mae_r'],adv)
            outcome=None;fill=np.nan
            if (bull and o[j]<=stop) or (not bull and o[j]>=stop):
                outcome='loss';fill=float(o[j]);r['exit_time']=ts.iloc[j];r['reason']='stop_gap_open'
            elif (bull and o[j]>=target) or (not bull and o[j]<=target):
                outcome='win';fill=target;r['exit_time']=ts.iloc[j];r['reason']='target_gap_capped'
            else:
                sl=l[j]<=stop if bull else h[j]>=stop
                tp=h[j]>=target if bull else l[j]<=target
                if sl and tp:
                    outcome='ambiguous';r['reason']='both_levels_in_M5'
                    if minute_loader is not None:
                        try:
                            minutes=minute_loader(p['symbol'],ts.iloc[j].strftime('%Y-%m-%d'))
                            resolved=_minute_outcome(minutes,ts.iloc[j],p['direction'],stop,target,(o[j],h[j],l[j],c[j]))
                            if resolved:
                                outcome,fill,r['exit_time']=resolved
                                r['resolution']='M1';r['reason']='both_levels_in_M1' if outcome=='ambiguous' else 'ordered_M1_first_passage'
                        except Exception as exc:
                            r['minute_data_error']=f'{type(exc).__name__}: {exc}'
                elif sl:
                    outcome='loss';fill=stop;r['reason']='stop_hit'
                elif tp:
                    outcome='win';fill=target;r['reason']='target_hit'
            if outcome:
                r['outcome']=outcome
                if outcome in ('win','loss'):
                    r['gross_r']=sign*(fill-entry)/risk
                    r['net_r']=r['gross_r']-r['cost_r']
                break
        else:
            r['reason']='observation_horizon' if entry_idx+horizon<=boundary else 'end_of_data_or_partition'
            r['excursion_is_bound']=False
        if pd.notna(r['exit_time']):
            r['duration_minutes']=(r['exit_time']-r['entry_time']).total_seconds()/60
        output.append(r)
    return pd.DataFrame(output,columns=list(patterns.columns)+[k for k in SIM_COLUMNS if k not in patterns.columns])
