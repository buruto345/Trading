"""Independent oracle checks using known and randomized synthetic fixtures."""
import numpy as np
import pandas as pd
import pytest
from src.ha_validation import reference as r
from src.ha_validation import statistics as s
from src.ha_research.variants import detect, bootstrap_scenarios
from src.ha_research.indicators import indicators
from src.ha_research.descriptive import geometry


def raw(n=1200):
    rng=np.random.default_rng(83);c=100+np.cumsum(rng.normal(0,.2,n));o=np.r_[100,c[:-1]]
    return pd.DataFrame(dict(timestamp=pd.date_range('2023-12-31',periods=n,freq='min',tz='UTC'),
        open=o,close=c,high=np.maximum(o,c)+.1,low=np.minimum(o,c)-.1))


def test_independent_indicators_gaps_zero_range_and_prefix():
    f=raw();f.loc[600:,'timestamp']+=pd.Timedelta(minutes=5)
    a=r.features(f);b=indicators(f)
    for k in ['ha_open','ha_close','ha_high','ha_low','ema100']:np.testing.assert_allclose(a[k],b[k],rtol=1e-14)
    pd.testing.assert_frame_equal(a.iloc[:700],r.features(f.iloc[:700]))
    assert not a.indicator_ready.iloc[600:1099].any()
    flat=raw(3);flat[['open','high','low','close']]=100
    assert r.geometry(r.features(flat)).body_ratio.isna().all()


@pytest.mark.parametrize('seed',range(8))
def test_suffix_oracle_matches_random_causal_state_machine(seed):
    rng=np.random.default_rng(seed);n=3000;f=raw(n);f=r.features(f)
    g=r.geometry(f)
    # Valid abstract candle classes, including reset, neutral and wrong-color Doji.
    z=rng.choice([-1,1],n);col=rng.choice([-1,0,1],n,p=[.48,.04,.48]);both=rng.random(n)<.35
    g['ema_zone']=z;g['color']=col;g['both_wicks']=both
    g['clean_direction']=np.where((col==-z)&~both,z,0)
    g['ready']=True;g['body_ratio']=rng.random(n);g['range']=rng.uniform(1,4,n)
    g['segment_id']=np.arange(n)//400;f['research_partition']='in_sample'
    for threshold in [.05,.1,.2,.3,.4]:
        a=r.detect(g,threshold);b=detect(f,g,'TEST','D',threshold)[0]
        pd.testing.assert_frame_equal(a,b[a.columns].reset_index(drop=True),check_dtype=False)


@pytest.mark.parametrize('o,h,l,d,expected',[(100,103,97,1,'ambiguous'),(103,104,97,1,'success'),
    (97,104,96,-1,'success'),(100,101,99,1,'unresolved'),(100,103,99,-1,'failure')])
def test_direct_first_passage(o,h,l,d,expected):
    assert r.passage([o],[h],[l],0,1,98,102,d)[0]==expected


def test_independent_block_sums_match_expanded_bootstrap():
    e=pd.DataFrame(dict(confirmation_time=pd.date_range('2020-01-01',periods=11,freq='3D',tz='UTC'),
        full_outcome=['success','ambiguous','failure','unresolved','success','failure','success','success','ambiguous','failure','success']))
    for b in [1,3,7,14,28]:
        a=s.bootstrap(e,block=b,reps=80)
        old=bootstrap_scenarios(e,'full',dict(scenarios=s.SCENARIOS,seed=20261124,bootstrap_block_days=b,bootstrap_repetitions=80))
        for key in a:assert a[key]==(old[key]['low'],old[key]['high'],old[key]['valid_repetitions'])


def test_causal_market_conditions():
    f=r.features(raw(2500));a=s.conditions(f);b=s.conditions(f.iloc[:1900])
    for x,y in zip(a,b):np.testing.assert_array_equal(x[:1900],y)


def test_denominators_preserve_unresolved():
    e=pd.DataFrame(dict(confirmation_time=pd.date_range('2020',periods=4,tz='UTC'),full_outcome=['success','failure','ambiguous','unresolved']))
    rows=s.summary(e)
    assert [x['observed_proportion'] for x in rows]==[1/3,2/3,.5]
    assert all(x['unresolved']==1 for x in rows)


def test_reference_outcomes_partition_gap_and_no_doji_bar():
    f=pd.DataFrame(dict(timestamp=pd.date_range('2023-12-31 23:57',periods=6,freq='min',tz='UTC'),
        segment_id=0,open=100.,high=101.,low=99.,ha_close=100.,ha_low=98.,ha_high=102.))
    e=pd.DataFrame(dict(doji_index=[0],direction=[1]))
    f.loc[0,['high','low']]=[110,90]
    assert r.outcomes(f,e).full_outcome.iloc[0]=='unresolved'
    f.loc[3,'high']=103
    out=r.outcomes(f,e)
    assert out.full_outcome.iloc[0]=='success'
    assert out.partition_outcome.iloc[0]=='unresolved'
    assert out.partition_reason.iloc[0]=='partition_boundary'
    f.loc[2:,'segment_id']=1
    assert r.outcomes(f,e).full_reason.iloc[0]=='gap'


def test_reference_confirmation_exactly_on_partition_boundary():
    f=pd.DataFrame(dict(timestamp=pd.date_range('2023-12-31 23:59',periods=3,freq='min',tz='UTC'),
        segment_id=0,open=100.,high=[101.,103.,101.],low=99.,ha_close=100.,ha_low=98.,ha_high=102.))
    e=pd.DataFrame(dict(doji_index=[0],direction=[1]))
    out=r.outcomes(f,e)
    assert out.partition_outcome.iloc[0]=='success'
    assert r.partition(f.timestamp+pd.Timedelta(minutes=1))[0]=='validation'
