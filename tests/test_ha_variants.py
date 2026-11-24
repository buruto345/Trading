"""Synthetic rule examples for updated method and H1 first passage."""
import numpy as np
import pandas as pd
import pytest

from src.ha_research.variants import detect, label, first_passage, summarize, overlap


def fixture():
    n=6
    t=pd.date_range('2023-01-01',periods=n,freq='min',tz='UTC')
    f=pd.DataFrame(dict(timestamp=t,partition='in_sample',research_partition='in_sample',segment_id=0,
        open=100.,high=101.,low=99.,close=100.,ha_close=100.,ha_low=98.,ha_high=102.))
    g=pd.DataFrame(dict(ready=True,segment_id=0,ema_zone=1,color=[-1,-1,1,1,1,1],
        clean_direction=[1,1,0,0,0,0],both_wicks=[False,False,True,False,False,False],
        body_ratio=[.8,.8,.1,.8,.8,.8],range=[2.,2.,3.,2.,2.,2.],tolerance=1e-12))
    return f,g


def test_two_clean_no_impulse_and_thresholds():
    f,g=fixture()
    assert detect(f,g,'TEST','D01',.05)[0].empty
    p,_=detect(f,g,'TEST','D02',.1)
    assert len(p)==1 and p.pullback_count.iloc[0]==2
    assert p.intermediate_count.iloc[0]==0 and p.reference.iloc[0]==100
    assert p.adverse.iloc[0]==98 and p.favorable.iloc[0]==102
    assert p.confirmation_time.iloc[0]==f.timestamp.iloc[3]


@pytest.mark.parametrize('change',['single','wick','touch','zero_color','small_range','gap'])
def test_confirmed_constraints(change):
    f,g=fixture()
    if change=='single': g.loc[0,'clean_direction']=0
    if change=='wick': g.loc[1,'clean_direction']=0
    if change=='touch': g.loc[1,'ema_zone']=0;g.loc[1,'clean_direction']=0
    if change=='zero_color': g.loc[2,'color']=0
    if change=='small_range': g.loc[2,'range']=2
    if change=='gap': g.loc[2:,'segment_id']=1
    assert detect(f,g,'TEST','D05',.4)[0].empty


def test_range_larger_than_only_one_preceding_is_enough():
    f,g=fixture();g.loc[0,'range']=9
    assert len(detect(f,g,'TEST','D02',.1)[0])==1


def test_bearish_symmetry():
    f,g=fixture()
    for k in ['ema_zone','color','clean_direction']: g[k]*=-1
    p,_=detect(f,g,'TEST','D02',.1)
    assert p.direction.iloc[0]==-1 and p.adverse.iloc[0]==102 and p.favorable.iloc[0]==98


def test_intermediate_color_and_opposite_doji_precedence():
    f,g=fixture()
    g.loc[2,['color','body_ratio']]=[-1,.8]
    g.loc[3,['color','both_wicks','body_ratio','range']]=[1,True,.1,4.]
    p,_=detect(f,g,'TEST','D02',.1)
    assert len(p)==1 and p.intermediate_count.iloc[0]==1
    g.loc[2,'body_ratio']=.1
    p,reject=detect(f,g,'TEST','D02',.1)
    assert p.empty and reject['opposite_doji']==1


def test_neutral_or_wrong_intermediate_cannot_be_skipped():
    f,g=fixture();g.loc[2,['color','body_ratio']]=[0,.8]
    g.loc[3,['both_wicks','body_ratio','range']]=[True,.1,4.]
    assert detect(f,g,'TEST','D02',.1)[0].empty


def test_prefix_and_future_mutation_do_not_change_detection():
    f,g=fixture()
    a=detect(f,g,'TEST','D02',.1)[0]
    b=detect(f.iloc[:3],g.iloc[:3],'TEST','D02',.1)[0]
    pd.testing.assert_frame_equal(a,b)
    f.loc[3:,['open','high','low','close']]=999.
    pd.testing.assert_frame_equal(a,detect(f,g,'TEST','D02',.1)[0])


@pytest.mark.parametrize('o,h,l,direction,expected',[
    (100,103,99,1,'success'),(100,101,97,1,'failure'),
    (100,103,97,1,'ambiguous'),(103,104,97,1,'success'),
    (97,103,96,1,'failure'),(100,103,99,-1,'failure'),
    (100,101,97,-1,'success')])
def test_intrabar_and_open_order(o,h,l,direction,expected):
    result=first_passage(np.array([o]),np.array([h]),np.array([l]),0,1,98,102,direction)
    assert result[0]==expected


def test_doji_own_range_never_used_as_future_and_ha_not_execution():
    f,g=fixture();p,_=detect(f,g,'TEST','D02',.1)
    f.loc[2,['high','low']]=[1000,1]
    out=label(f,p)
    assert out.full_outcome.iloc[0]=='unresolved'
    f.loc[3,'high']=103
    assert label(f,p).full_outcome.iloc[0]=='success'


def test_unlimited_horizon():
    n=10000
    o=np.full(n,100.);h=o+1;l=o-1;h[-1]=103
    result=first_passage(o,h,l,0,n,98,102,1)
    assert result[:2]==('success',n-1)


def test_full_history_vs_partition_censoring():
    f,g=fixture();p,_=detect(f,g,'TEST','D02',.1)
    f.loc[4:,'partition']='validation';f.loc[4,'high']=103
    out=label(f,p)
    assert out.full_outcome.iloc[0]=='success'
    assert out.partition_outcome.iloc[0]=='unresolved'
    assert out.partition_reason.iloc[0]=='partition_boundary'


def test_confirmation_at_boundary_belongs_to_next_partition():
    f,g=fixture();f.loc[3:,'partition']='validation';f.loc[2:,'research_partition']='validation'
    f.loc[3,'high']=103
    p,_=detect(f,g,'TEST','D02',.1)
    assert p.partition.iloc[0]=='validation'
    assert label(f,p).partition_outcome.iloc[0]=='success'


def test_gap_censors_no_imputation():
    f,g=fixture();p,_=detect(f,g,'TEST','D02',.1)
    f.loc[3:,'segment_id']=1;f.loc[3,'high']=103
    out=label(f,p)
    assert out.full_outcome.iloc[0]=='unresolved' and out.full_reason.iloc[0]=='gap'


def test_ambiguity_denominators_and_bootstrap_reproducibility():
    f,g=fixture();p,_=detect(f,g,'TEST','D02',.1)
    out=pd.concat([label(f,p)]*4,ignore_index=True)
    out['full_outcome']=['success','failure','ambiguous','unresolved']
    out['confirmation_time']=pd.date_range('2023-01-01',periods=4,freq='8D',tz='UTC')
    config=dict(scenarios=['conservative','optimistic','excluded'],bootstrap_block_days=7,bootstrap_repetitions=100,seed=1)
    rows=summarize(out,'full',config)
    assert [r['observed_proportion'] for r in rows]==[1/3,2/3,1/2]
    assert all(r['unresolved']==1 and r['resolved']==2 and r['ambiguous']==1 for r in rows)
    assert rows==summarize(out,'full',config)
    assert rows[0]['all_observation_bounds']==[.25,.75]


def test_overlap_count_is_not_independent_n():
    e=pd.DataFrame(dict(doji_index=[0,1,4],full_end_index=[3,2,5]))
    assert overlap(e,'full')==dict(overlapping_with_prior=1,maximum_concurrent=2,independent_observations=None)
