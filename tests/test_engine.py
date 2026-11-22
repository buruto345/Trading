import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from src.pattern_detection.engine import detect_patterns,swing_flags,fvg_flags
from src.simulation.engine import simulate_patterns,_minute_outcome


def frame(rows):
    d=pd.DataFrame(rows,columns=['open','high','low','close'])
    d['timestamp']=pd.date_range('2020-01-01',periods=len(d),freq='5min',tz='UTC')
    d['volume']=1.
    return d


def bullish():
    # Manual: swing high=12 at 1, swing low=8 at 2, sweep low=7 at 4,
    # FVG [10,10.5] confirmed at 6 close, MSS close=12.5 > 12 at 6.
    return frame([[10,11,9,10],[10,12,10,11],[10,11,8,9],
                  [9,10.5,9,10],[8.5,10,7,9.5],[9.5,11,9,10.5],
                  [11,13,10.5,12.5]])


def mirrored(d):
    r=d.copy()
    r['open']=30-d.open;r['close']=30-d.close
    r['high']=30-d.low;r['low']=30-d.high
    return r


def simulation_case(bars):
    d=frame([[10,11,9,10]]+bars)
    p=pd.DataFrame([dict(pattern_id='unit',symbol='TEST',direction='bullish',mss_idx=0,sweep_extreme=9.)])
    return d,p


def test_swing_high_strict():
    h,l=swing_flags(bullish());assert h[1];assert not h[2]


def test_swing_low_strict():
    h,l=swing_flags(bullish());assert l[2];assert l[4]


def test_equal_high_rejected():
    d=bullish();d.loc[2,'high']=12
    assert not swing_flags(d)[0][1]


def test_equal_low_rejected():
    d=bullish();d.loc[3,'low']=8
    assert not swing_flags(d)[1][2]


def test_swing_needs_next_candle():
    assert not swing_flags(bullish().iloc[:2])[0][1]


def test_complete_bullish_pattern():
    p,r,c=detect_patterns(bullish(),'TEST')
    assert len(p)==1
    x=p.iloc[0];assert x.direction=='bullish';assert x.sweep_idx==4;assert x.mss_idx==6
    assert x.structure_idx==1;assert x.swing_idx==2
    assert x.fvg_count==1;assert x.fvg_lower==10;assert x.fvg_upper==10.5


def test_complete_bearish_pattern():
    p,r,c=detect_patterns(mirrored(bullish()),'TEST')
    assert len(p)==1;assert p.iloc[0].direction=='bearish'
    assert p.iloc[0].sweep_extreme==23


def test_bullish_sweep_color_mandatory():
    d=bullish();d.loc[4,'close']=8.4
    assert detect_patterns(d,'TEST')[2]['bullish_sweeps']==0


def test_bearish_sweep_color_mandatory():
    d=mirrored(bullish());d.loc[4,'close']=21.6
    assert detect_patterns(d,'TEST')[2]['bearish_sweeps']==0


def test_bullish_sweep_close_mandatory():
    d=bullish();d.loc[4,['open','close']]=[7.2,7.5]
    assert detect_patterns(d,'TEST')[2]['bullish_sweeps']==0


def test_bearish_sweep_close_mandatory():
    d=mirrored(bullish());d.loc[4,['open','close']]=[22.8,22.5]
    assert detect_patterns(d,'TEST')[2]['bearish_sweeps']==0


def test_sweep_equal_level_not_breach():
    d=bullish();d.loc[4,'low']=8
    assert detect_patterns(d,'TEST')[2]['bullish_sweeps']==0


def test_bullish_fvg():
    assert fvg_flags(bullish())[0][6]


def test_bearish_fvg():
    assert fvg_flags(mirrored(bullish()))[1][6]


def test_fvg_equal_boundaries_rejected():
    d=bullish();d.loc[6,'low']=10
    assert not fvg_flags(d)[0][6]


def test_confirmation_timing():
    d=bullish();p,_,_=detect_patterns(d,'TEST');x=p.iloc[0]
    assert x.confirmation_time==d.timestamp.iloc[6]+pd.Timedelta(minutes=5)
    assert x.detection_time==d.timestamp.iloc[4]+pd.Timedelta(minutes=5)
    assert json.loads(x.fvg_details)[0]['formation_time']==x.confirmation_time.isoformat()


def test_fvg_can_precede_mss():
    d=bullish();d.loc[6,'close']=11.5
    d=frame(d[['open','high','low','close']].values.tolist()+[[11.5,13,10,12.5]])
    p,_,_=detect_patterns(d,'TEST')
    assert len(p)==1;assert p.iloc[0].mss_idx==7
    assert json.loads(p.iloc[0].fvg_details)[0]['formation_idx']==6


def test_fvg_does_not_confirm_before_third_close():
    p,_,_=detect_patterns(bullish().iloc[:6],'TEST');assert p.empty


def test_no_fvg_rejected():
    d=bullish();d.loc[6,'low']=9.5
    p,r,_=detect_patterns(d,'TEST')
    assert p.empty;assert 'mss_without_fvg' in r.reason.tolist()


def test_no_sweep_no_pattern():
    d=bullish();d.loc[4,'low']=8.1
    assert detect_patterns(d,'TEST')[0].empty


def test_no_mss_no_pattern():
    d=bullish();d.loc[6,'close']=11.5
    p,r,_=detect_patterns(d,'TEST');assert p.empty
    assert 'end_of_data_before_mss' in r.reason.tolist()


def test_mss_equal_close_rejected():
    d=bullish();d.loc[6,'close']=12
    assert detect_patterns(d,'TEST')[0].empty


def test_duplicate_timestamp_rejected():
    d=bullish();d.loc[3,'timestamp']=d.timestamp.iloc[2]
    with pytest.raises(ValueError):detect_patterns(d,'TEST')


def test_pattern_not_duplicated_by_later_closes():
    d=frame(bullish()[['open','high','low','close']].values.tolist()+[[12.5,14,12,13],[13,15,12,14]])
    p,_,_=detect_patterns(d,'TEST');assert len(p)==1;assert p.pattern_id.is_unique


def test_missing_candle_resets_setup():
    d=bullish();d.loc[5:,'timestamp']+=pd.Timedelta(minutes=5)
    p,r,_=detect_patterns(d,'TEST');assert p.empty;assert 'data_gap' in r.reason.tolist()


def test_missing_candle_prevents_fvg():
    d=bullish();d.loc[6,'timestamp']+=pd.Timedelta(minutes=5)
    assert not fvg_flags(d)[0][6]


def test_prefix_invariance_no_lookahead():
    d=frame(bullish()[['open','high','low','close']].values.tolist()+[[12.5,14,12,13],[13,15,12,14]])
    full,_,_=detect_patterns(d,'TEST')
    for n in range(1,len(d)+1):
        p,_,_=detect_patterns(d.iloc[:n],'TEST')
        expected=full[full.mss_idx<n]
        assert p.pattern_id.tolist()==expected.pattern_id.tolist()


def test_setup_expiration():
    p,r,_=detect_patterns(bullish(),'TEST',max_sweep_mss=1)
    assert p.empty;assert 'setup_expired' in r.reason.tolist()


def test_extreme_invalidation():
    d=bullish();d.loc[5,'low']=6
    p,r,_=detect_patterns(d,'TEST');assert p.empty
    assert 'sweep_extreme_invalidated' in r.reason.tolist()


def test_next_open_entry_and_win():
    d,p=simulation_case([[10,12.1,9.5,11]])
    x=simulate_patterns(d,p).iloc[0]
    assert x.entry==10;assert x.stop==9;assert x.target==12
    assert x.outcome=='win';assert x.gross_r==2;assert x.net_r==pytest.approx(1.99)


def test_stop_loss():
    d,p=simulation_case([[10,10.5,8.9,9.5]])
    x=simulate_patterns(d,p).iloc[0];assert x.outcome=='loss';assert x.gross_r==-1


def test_bearish_simulation():
    d,p=simulation_case([[10,12.1,9.5,11]])
    d=mirrored(d);p['direction']='bearish';p['sweep_extreme']=21
    x=simulate_patterns(d,p).iloc[0];assert x.outcome=='win';assert x.gross_r==2


def test_ambiguous_m5_retained():
    d,p=simulation_case([[10,12.1,8.9,11]])
    x=simulate_patterns(d,p).iloc[0];assert x.outcome=='ambiguous';assert np.isnan(x.gross_r)


def test_no_future_candle_after_exit():
    d,p=simulation_case([[10,12.1,9.5,11],[11,100,0,11]])
    x=simulate_patterns(d,p).iloc[0];assert x.duration_bars==1
    assert x.mfe_r==pytest.approx(2.1);assert x.mae_r==pytest.approx(.5)


def test_unresolved_horizon():
    d,p=simulation_case([[10,11,9.5,10],[10,12.1,9.5,11]])
    x=simulate_patterns(d,p,horizon=1).iloc[0]
    assert x.outcome=='unresolved';assert x.reason=='observation_horizon'


def test_partition_censoring():
    d,p=simulation_case([[10,11,9.5,10],[10,12.1,9.5,11]])
    p['partition_end_idx']=2
    x=simulate_patterns(d,p).iloc[0]
    assert x.outcome=='unresolved';assert x.exit_idx==1


def test_partition_entry_not_allowed():
    d,p=simulation_case([[10,12.1,9.5,11]])
    p['partition_end_idx']=1
    x=simulate_patterns(d,p).iloc[0];assert not x.traded;assert x.outcome=='unresolved'


def test_gap_censors_simulation():
    d,p=simulation_case([[10,11,9.5,10],[10,12.1,9.5,11]])
    d.loc[2,'timestamp']+=pd.Timedelta(minutes=5)
    x=simulate_patterns(d,p).iloc[0];assert x.outcome=='unresolved';assert x.reason=='data_gap'


def test_stop_gap_worse_fill():
    d,p=simulation_case([[10,11,9.5,10],[8,10,7,9]])
    x=simulate_patterns(d,p).iloc[0];assert x.outcome=='loss';assert x.gross_r==-2


def test_invalid_risk_retained_not_traded():
    d,p=simulation_case([[8,10,7,9]])
    x=simulate_patterns(d,p).iloc[0];assert x.outcome=='invalid';assert not x.traded


def minutes_at(t,rows):
    m=frame(rows);m['timestamp']=pd.date_range(t,periods=len(m),freq='min')
    return m


def test_m1_resolves_win_first():
    d,p=simulation_case([[10,12.1,8.9,11]])
    m=minutes_at(d.timestamp.iloc[1],[[10,12.1,9.5,11],[11,11,8.9,10],[10,11,9.5,10],[10,11,9.5,10],[10,11,9.5,11]])
    x=simulate_patterns(d,p,minute_loader=lambda *_:m).iloc[0]
    assert x.outcome=='win';assert x.resolution=='M1'


def test_m1_still_ambiguous():
    d,p=simulation_case([[10,12.1,8.9,11]])
    m=minutes_at(d.timestamp.iloc[1],[[10,12.1,8.9,11]]*5)
    x=simulate_patterns(d,p,minute_loader=lambda *_:m).iloc[0]
    assert x.outcome=='ambiguous';assert x.resolution=='M1'


def test_incomplete_m1_does_not_guess():
    d,p=simulation_case([[10,12.1,8.9,11]])
    m=minutes_at(d.timestamp.iloc[1],[[10,12.1,9.5,11]])
    x=simulate_patterns(d,p,minute_loader=lambda *_:m).iloc[0]
    assert x.outcome=='ambiguous';assert x.resolution=='M5'


def test_minute_loader_failure_retained():
    d,p=simulation_case([[10,12.1,8.9,11]])
    def failure(*_):raise OSError('unavailable')
    x=simulate_patterns(d,p,minute_loader=failure).iloc[0]
    assert x.outcome=='ambiguous';assert 'OSError' in x.minute_data_error


def test_inconsistent_m1_does_not_resolve():
    d,p=simulation_case([[10,12.1,8.9,11]])
    m=minutes_at(d.timestamp.iloc[1],[[10,12.1,9.5,11]]*5)
    x=simulate_patterns(d,p,minute_loader=lambda *_:m).iloc[0]
    assert x.outcome=='ambiguous';assert x.resolution=='M5'


def test_duplicate_observations_rejected():
    d,p=simulation_case([[10,12.1,9.5,11]])
    with pytest.raises(ValueError,match='Duplicate'):
        simulate_patterns(d,pd.concat([p,p],ignore_index=True))


def test_overlapping_observations_retained_independently():
    d,p=simulation_case([[10,12.1,9.5,11]])
    two=pd.concat([p,p],ignore_index=True);two.loc[1,'pattern_id']='second'
    result=simulate_patterns(d,two)
    assert len(result)==2;assert (result.outcome=='win').all()


def test_duration_minutes_and_boundary():
    d,p=simulation_case([[10,11,9.5,10],[10,12.1,9.5,11]])
    x=simulate_patterns(d,p).iloc[0]
    assert x.duration_minutes==10;assert x.duration_bars==2


def test_empty_observations_have_schema():
    d=bullish().iloc[:2]
    p,_,_=detect_patterns(d,'TEST')
    result=simulate_patterns(d,p)
    assert result.empty;assert 'outcome' in result.columns


def test_save_synthetic_fixtures():
    path=Path('data/synthetic');path.mkdir(parents=True,exist_ok=True)
    bullish().to_csv(path/'manual_bullish.csv',index=False)
    mirrored(bullish()).to_csv(path/'manual_bearish.csv',index=False)
    assert (path/'manual_bullish.csv').exists()
