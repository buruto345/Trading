"""Predeclared experimental ICT variants. See MULTI_MODEL_PROTOCOL.md."""
import json
import numpy as np
import pandas as pd
from src.pattern_detection.engine import detect_patterns, swing_flags, fvg_flags, FIVE_MINUTES

NAMES = {0:'Existing ICT Baseline',1:'ICT 2022 FVG Retracement',2:'ICT Silver Bullet',3:'ICT Turtle Soup',4:'ICT Unicorn'}

def displacement(df):
    prev=df.close.shift(1)
    tr=pd.concat([df.high-df.low,(df.high-prev).abs(),(df.low-prev).abs()],axis=1).max(axis=1)
    segment=pd.to_datetime(df.timestamp,utc=True).diff().ne(FIVE_MINUTES).cumsum()
    tr=tr.where(segment.eq(segment.shift(1)),df.high-df.low)
    atr=tr.groupby(segment).transform(lambda s:s.shift(1).rolling(20,min_periods=20).mean())
    body=df.close-df.open
    strong=body.abs().ge(1.5*atr)&body.abs().ge(.6*(df.high-df.low))
    return (strong & body.gt(0)).to_numpy(),(strong & body.lt(0)).to_numpy()

def silver_session(t):
    t=pd.Timestamp(t).tz_convert('America/New_York')
    name={3:'London SB',10:'New York AM SB',14:'New York PM SB'}.get(t.hour)
    return f'{t.date()} {name}' if name else None

def turtle(df,symbol):
    ts=pd.to_datetime(df.timestamp,utc=True).reset_index(drop=True)
    o,h,l,c=(df[k].to_numpy(float) for k in ['open','high','low','close'])
    sh,sl=swing_flags(df); highs=[];lows=[];lh=ll=None;rows=[];reject=[]
    for j in range(len(df)):
        if j and ts.iloc[j]-ts.iloc[j-1]!=FIVE_MINUTES:
            highs.clear();lows.clear();lh=ll=None
        elif j>=3:
            if sh[j-2]:highs.append(j-2);lh=j-2
            if sl[j-2]:lows.append(j-2);ll=j-2
        for bull,pivots,opposite in [(True,lows,lh),(False,highs,ll)]:
            if not pivots:continue
            si=pivots[-1];price=l[si] if bull else h[si]
            breached=l[j]<price if bull else h[j]>price
            if not breached:continue
            valid=(c[j]>price and c[j]>o[j]) if bull else (c[j]<price and c[j]<o[j])
            direction='bullish' if bull else 'bearish'
            if valid:
                rows.append(dict(pattern_id=f'{symbol}:3:{direction}:{j}',symbol=symbol,model=3,direction=direction,
                    sweep_idx=j,mss_idx=j,swing_idx=si,structure_idx=opposite,sweep_time=ts.iloc[j],
                    confirmation_time=ts.iloc[j]+FIVE_MINUTES,detection_time=ts.iloc[j]+FIVE_MINUTES,
                    formation_idx=j,formation_time=ts.iloc[j]+FIVE_MINUTES,revisit_idx=np.nan,
                    swing_price=price,sweep_extreme=l[j] if bull else h[j],
                    sweep_size=price-l[j] if bull else h[j]-price,
                    target_a=(h[opposite] if bull else l[opposite]) if opposite is not None else np.nan,
                    fvg_size=np.nan,fvg_lower=np.nan,fvg_upper=np.nan,fvg_count=0,body_size=abs(c[j]-o[j]),
                    wick_size=min(o[j],c[j])-l[j] if bull else h[j]-max(o[j],c[j]),delay_bars=0,session_sb='Not SB'))
            else:reject.append(dict(model=3,symbol=symbol,direction=direction,sweep_idx=j,rejected_idx=j,reason='breach_without_colored_rejection'))
        while highs and h[j]>h[highs[-1]]:highs.pop()
        while lows and l[j]<l[lows[-1]]:lows.pop()
    return rows,reject

def revisit(df,p,lower,upper,model):
    start=int(p['formation_idx']);ts=df.timestamp
    bull=p['direction']=='bullish';session=silver_session(ts.iloc[start]+FIVE_MINUTES)
    for j in range(start+1,min(start+25,len(df))):
        if ts.iloc[j]-ts.iloc[j-1]!=FIVE_MINUTES:return None,'revisit_data_gap',j
        if model==2 and silver_session(ts.iloc[j]+FIVE_MINUTES)!=session:return None,'session_ended_before_revisit',j
        if (df.low.iloc[j]<p['sweep_extreme'] if bull else df.high.iloc[j]>p['sweep_extreme']):
            return None,'stop_invalidated_before_revisit',j
        if df.high.iloc[j]>=lower and df.low.iloc[j]<=upper:
            return j,None,j
    j=min(start+24,len(df)-1)
    return None,'no_revisit_in_24_bars' if start+24<len(df) else 'partition_end_before_revisit',j

def detect_models(df,symbol):
    ts=pd.to_datetime(df.timestamp,utc=True)
    if not ts.is_monotonic_increasing or ts.duplicated().any():raise ValueError('Unique sorted timestamps required')
    base,base_reject,_=detect_patterns(df,symbol)
    dp,dn=displacement(df);bull_fvg,bear_fvg=fvg_flags(df)
    rows,rejected=turtle(df,symbol);formations=[]
    base=base.copy();base['model']=0;base['formation_idx']=base.mss_idx;base['formation_time']=base.confirmation_time
    base['target_a']=np.nan;base['session_sb']='Not SB';base['revisit_idx']=np.nan
    rows.extend(base.to_dict('records'))
    for p in base.to_dict('records'):
        bull=p['direction']=='bullish';gaps=json.loads(p['fvg_details'])
        qualifying=[g for g in gaps if (dp if bull else dn)[g['formation_idx']-1]]
        for model in [1,4]:
            q={**p,'model':model,'pattern_id':f'{model}:{p["pattern_id"]}','original_mss_idx':p['mss_idx']}
            if not qualifying:
                rejected.append({**q,'rejected_idx':p['mss_idx'],'reason':'no_displacement_fvg'});continue
            g=qualifying[-1];lower,upper=g['lower'],g['upper']
            if model==4:
                b=int(p['structure_idx']);s=int(p['sweep_idx']);si=int(p['swing_idx'])
                colored=df.close.iloc[b]>df.open.iloc[b] if bull else df.close.iloc[b]<df.open.iloc[b]
                if not(si<b<s and colored):
                    rejected.append({**q,'rejected_idx':p['mss_idx'],'reason':'breaker_geometry_or_color'});continue
                q.update(breaker_idx=b,breaker_lower=df.low.iloc[b],breaker_upper=df.high.iloc[b])
                overlap=[x for x in qualifying if min(x['upper'],df.high.iloc[b])>max(x['lower'],df.low.iloc[b])]
                if not overlap:
                    rejected.append({**q,'rejected_idx':p['mss_idx'],'reason':'no_positive_overlap'});continue
                g=overlap[-1];lower=max(g['lower'],df.low.iloc[b]);upper=min(g['upper'],df.high.iloc[b])
                q.update(overlap_lower=lower,overlap_upper=upper)
            q.update(fvg_lower=g['lower'],fvg_upper=g['upper'],fvg_size=g['upper']-g['lower'],
                     fvg_formation_idx=g['formation_idx'],fvg_count=1,zone_lower=lower,zone_upper=upper)
            q['fvg_details']=json.dumps([g])
            start=int(p['sweep_idx']);end=int(p['mss_idx'])
            q['target_a']=float(df.high.iloc[start:end+1].max() if bull else df.low.iloc[start:end+1].min())
            formations.append(q.copy())
            j,reason,at=revisit(df,q,lower,upper,model)
            if j is None:rejected.append({**q,'rejected_idx':at,'reason':reason})
            else:
                q.update(revisit_idx=j,revisit_time=ts.iloc[j]+FIVE_MINUTES,mss_idx=j,confirmation_time=ts.iloc[j]+FIVE_MINUTES)
                rows.append(q)
    # Session-specific FVG/displacement, with optional baseline context flags.
    for j in np.flatnonzero(bull_fvg|bear_fvg):
        bull=bool(bull_fvg[j]);session=silver_session(ts.iloc[j]+FIVE_MINUTES)
        if not session:continue
        q=dict(model=2,symbol=symbol,direction='bullish' if bull else 'bearish',sweep_idx=j-2,mss_idx=j,
            pattern_id=f'{symbol}:2:{j}',formation_idx=j,formation_time=ts.iloc[j]+FIVE_MINUTES,
            confirmation_time=ts.iloc[j]+FIVE_MINUTES,detection_time=ts.iloc[j]+FIVE_MINUTES,sweep_time=ts.iloc[j-2])
        if not all(silver_session(ts.iloc[k])==session for k in range(j-2,j+1)):
            rejected.append({**q,'rejected_idx':j,'reason':'fvg_crosses_session_boundary'});continue
        if not (dp if bull else dn)[j-1]:
            rejected.append({**q,'rejected_idx':j,'reason':'no_displacement_fvg'});continue
        lower,upper=(df.high.iloc[j-2],df.low.iloc[j]) if bull else (df.high.iloc[j],df.low.iloc[j-2])
        context=base[(base.direction==q['direction']) & base.mss_idx.le(j)&base.mss_idx.ge(j-24)]
        q.update(fvg_lower=lower,fvg_upper=upper,fvg_size=upper-lower,fvg_count=1,zone_lower=lower,zone_upper=upper,
            fvg_formation_idx=j,sweep_extreme=float(df.low.iloc[j-2:j+1].min() if bull else df.high.iloc[j-2:j+1].max()),
            target_a=float(df.high.iloc[j-2:j+1].max() if bull else df.low.iloc[j-2:j+1].min()),
            sweep_size=np.nan,body_size=abs(df.close.iloc[j-1]-df.open.iloc[j-1]),wick_size=np.nan,delay_bars=2,
            session_sb=session.split(' ',1)[1],context_sweep_mss=not context.empty)
        formations.append(q.copy());k,reason,at=revisit(df,q,lower,upper,2)
        if k is None:rejected.append({**q,'rejected_idx':at,'reason':reason})
        else:
            q.update(revisit_idx=k,revisit_time=ts.iloc[k]+FIVE_MINUTES,mss_idx=k,confirmation_time=ts.iloc[k]+FIVE_MINUTES)
            rows.append(q)
    for r in base_reject.to_dict('records'):rejected.append({**r,'model':0})
    return pd.DataFrame(rows),pd.DataFrame(rejected),pd.DataFrame(formations)

