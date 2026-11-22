import numpy as np
import pandas as pd
import pytest
from src.multi_model.detectors import detect_models, displacement, silver_session, revisit
from src.multi_model.simulation import simulate_track
from src.simulation.engine import simulate_patterns

def example(mirror=False):
    # Quiet warmup, prior low, intervening up-close swing high, lower-low sweep,
    # displacement through breaker, FVG, revisit, then movement.
    rows=[[10,10.2,9.8,10]]*22+[[9.5,10,8,9],[9,10,9,9.8],
        [10,12,9,11],[11,11.5,9.5,10],[9,10,7,9.5],
        [9.5,14,9.2,13.5],[13,14,12.5,13.2],[13,13.5,11,12.8],[12.8,20,12,18]]
    df=pd.DataFrame(rows,columns=['open','high','low','close'])
    df['timestamp']=pd.date_range('2024-01-15 13:00',periods=len(df),freq='5min',tz='UTC')
    df['volume']=1.
    if mirror:
        old=df.copy();df['open']=30-old.open;df['close']=30-old.close;df['high']=30-old.low;df['low']=30-old.high
    return df

@pytest.mark.parametrize('mirror',[False,True])
def test_models_both_directions(mirror):
    d=example(mirror);p,r,f=detect_models(d,'TEST')
    # Baseline MSS occurs on displacement before gap => rejected by original convention.
    # Delay structure crossing until gap-confirmation to meet unchanged baseline rules.
    d.loc[27,'close']=11.8;d.loc[27,'open']=9.2
    p,r,f=detect_models(d,'TEST') if not mirror else detect_models(_mirror(example(False).assign()),'TEST')
    assert 3 in set(p.model)

def _mirror(df):
    df=df.copy();df.loc[27,'close']=11.8;df.loc[27,'open']=9.2
    old=df.copy();df['open']=30-old.open;df['close']=30-old.close;df['high']=30-old.low;df['low']=30-old.high
    return df

def complete(mirror=False):
    d=example();d.loc[27,['open','high','low','close']]=[9.2,12,9.2,11.9]
    # body/range >=.6 and >1.5 prior ATR; FVG at28, MSS at28.
    return _mirror_complete(d) if mirror else d

def _mirror_complete(d):
    r=d.copy();r['open']=30-d.open;r['close']=30-d.close;r['high']=30-d.low;r['low']=30-d.high;return r

@pytest.mark.parametrize('model',[0,1,3,4])
@pytest.mark.parametrize('mirror',[False,True])
def test_complete_models(model,mirror):
    p,r,f=detect_models(complete(mirror),'TEST')
    assert model in set(p.model), (p[['model','mss_idx']],r[['model','reason']])
    row=p[p.model==model].iloc[0]
    assert row.direction==('bearish' if mirror else 'bullish')
    assert row.confirmation_time==complete().timestamp.iloc[int(row.mss_idx)]+pd.Timedelta(minutes=5)
    if model in [1,4]:assert row.revisit_idx>row.formation_idx
    if model==4:assert row.overlap_upper>row.overlap_lower

@pytest.mark.parametrize('mirror',[False,True])
def test_silver_bullet(mirror):
    d=complete(mirror);d['timestamp']=pd.date_range('2024-01-15 12:50',periods=len(d),freq='5min',tz='UTC')
    p,_,_=detect_models(d,'TEST');assert 2 in set(p.model)
    assert set(p.loc[p.model==2,'session_sb'])=={'New York AM SB'}

@pytest.mark.parametrize('t,expected',[('2024-01-15T15:00Z',True),('2024-07-15T14:00Z',True),('2024-07-15T15:00Z',False),('2024-03-10T07:00Z',True),('2024-11-03T08:00Z',True)])
def test_dst(t,expected):assert bool(silver_session(t))==expected

def test_prefix_causality():
    d=complete();allp,_,_=detect_models(d,'TEST')
    for n in range(23,len(d)+1):
        p,_,_=detect_models(d.iloc[:n].copy(),'TEST')
        expected=set(allp.loc[allp.mss_idx<n,'pattern_id'])
        assert set(p.pattern_id)==expected if len(p) else not expected

def test_displacement_causal():
    d=complete();a=displacement(d);e=d.copy();e.loc[29:,'high']=1000
    b=displacement(e)
    assert np.array_equal(a[0][:29],b[0][:29])

def test_reject_and_no_revisit():
    d=complete().iloc[:29];p,r,f=detect_models(d,'TEST')
    assert not p.model.isin([1,4]).any()
    assert 'partition_end_before_revisit' in set(r.reason)

def test_gap_resets():
    d=complete();d.loc[26:,'timestamp']+=pd.Timedelta(minutes=5)
    p,_,_=detect_models(d,'TEST');assert p.empty or not p.model.isin([0,1,4]).any()

def test_revisit_invalidated_first():
    d=complete();d.loc[29,'low']=6
    p,r,_=detect_models(d,'TEST');assert 'stop_invalidated_before_revisit' in set(r.reason)
    assert not p.model.isin([1,4]).any()

def test_baseline_sim_unchanged():
    d=complete();p,_,_=detect_models(d,'TEST');p=p[p.model==0]
    pd.testing.assert_frame_equal(simulate_track(d,p),simulate_patterns(d,p))

def test_track_a_target():
    d=complete();p,_,_=detect_models(d,'TEST');p=p[p.model==1]
    s=simulate_track(d,p,track='A');assert s.target.iloc[0]==p.target_a.iloc[0]
    assert s.entry_time.iloc[0]>=p.confirmation_time.iloc[0]

def test_invalid_target():
    d=complete();p,_,_=detect_models(d,'TEST');p=p[p.model==1].copy();p['target_a']=1
    assert simulate_track(d,p,track='A').outcome.iloc[0]=='invalid'

def test_silver_prefix_causality():
    d=complete();d['timestamp']=pd.date_range('2024-01-15 12:50',periods=len(d),freq='5min',tz='UTC')
    full,_,_=detect_models(d,'TEST')
    for n in range(25,len(d)+1):
        p,_,_=detect_models(d.iloc[:n].copy(),'TEST')
        assert (set(p.pattern_id) if len(p) else set())==set(full.loc[full.mss_idx<n,'pattern_id'])

def test_gap_atr_warmup():
    d=pd.concat([complete(),complete()],ignore_index=True)
    d['timestamp']=pd.date_range('2024-01-01',periods=len(d),freq='5min',tz='UTC')
    d.loc[31:,'timestamp']+=pd.Timedelta(days=1)
    pos,neg=displacement(d)
    assert not pos[31:51].any() and not neg[31:51].any()

@pytest.mark.parametrize('track',['A','B'])
def test_simulation_ambiguous_and_minute_resolution(track):
    d=pd.DataFrame({'open':[10.,10.],'high':[10.5,13.],'low':[9.5,8.],'close':[10.,11.],
                    'timestamp':pd.date_range('2024-01-01',periods=2,freq='5min',tz='UTC')})
    p=pd.DataFrame([dict(pattern_id='x',symbol='TEST',direction='bullish',model=3,mss_idx=0,sweep_extreme=9.,target_a=12.)])
    assert simulate_track(d,p,track=track).outcome.iloc[0]=='ambiguous'
    minute=pd.DataFrame({'open':[10,10.5,12,11,10],'high':[11,13,12,11,11],'low':[9.5,10,10,8,9],'close':[10.5,12,11,10,11],
                        'timestamp':pd.date_range(d.timestamp.iloc[1],periods=5,freq='min')})
    s=simulate_track(d,p,track=track,minute_loader=lambda *_:minute)
    assert s.outcome.iloc[0]=='win' and s.resolution.iloc[0]=='M1'

@pytest.mark.parametrize('track',['A','B'])
def test_partition_censor(track):
    d=complete();p,_,_=detect_models(d,'TEST');p=p[p.model==1].copy();p['partition_end_idx']=p.mss_idx+1
    s=simulate_track(d,p,track=track)
    assert s.outcome.iloc[0]=='unresolved' and not s.traded.iloc[0]
