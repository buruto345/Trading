"""Synthetic geometry and sequence fixtures, never historical outcome evidence."""
import numpy as np
import pandas as pd
import pytest

from src.ha_research.descriptive import geometry, sequences, forward_behavior, summaries


def features():
    t = pd.date_range('2023-01-01', periods=3, freq='min', tz='UTC')
    return pd.DataFrame(dict(timestamp=t, available_at=t + pd.Timedelta(minutes=1),
         partition='in_sample', indicator_ready=True, segment_id=0,
         ha_open=[12., 15., 7.], ha_close=[14., 13., 9.],
         ha_high=[16., 15., 11.], ha_low=[11., 12., 7.], ema100=[10., 10., 12.]))


def test_geometry_manual_body_wicks_ratio_ema_position():
    g = geometry(features())
    np.testing.assert_allclose(g.body, [2, 2, 2])
    np.testing.assert_allclose(g.range, [5, 3, 4])
    np.testing.assert_allclose(g.upper_wick, [2, 0, 2])
    np.testing.assert_allclose(g.lower_wick, [1, 1, 0])
    np.testing.assert_allclose(g.body_ratio, [.4, 2/3, .5])
    assert g.ema_zone.tolist() == [1, 1, -1]
    assert g.clean_direction.tolist() == [0, 1, -1]
    assert g.same_color_two_wicks.tolist() == [True, False, False]


def test_ema_touch_is_not_above_or_below():
    f = features()
    f['ema100'] = [11., 15., 7.]
    assert geometry(f).ema_zone.eq(0).all()


def test_zero_range_is_null_not_doji():
    f = features()
    f[['ha_open', 'ha_high', 'ha_low', 'ha_close']] = 100.
    g = geometry(f)
    assert g.body_ratio.isna().all() and g.color.eq(0).all()
    assert not g.both_wicks.any() and not g.clean_direction.any()


def test_float_noise_and_strict_touch_tolerance():
    f = features().iloc[[1]].copy()
    f['ha_high'] = f.ha_open + np.spacing(15.)
    f['ema100'] = f.ha_low - np.spacing(12.)
    g = geometry(f)
    assert bool(g.no_upper_wick.iloc[0])
    assert not bool(g.no_upper_exact.iloc[0])
    assert g.ema_zone.iloc[0] == 0


def test_zero_body_color_is_neutral_even_when_two_wicks():
    f = features().iloc[[0]].copy()
    f['ha_close'] = f.ha_open
    g = geometry(f)
    assert g.color.iloc[0] == 0 and g.both_wicks.iloc[0]
    assert not g.same_color_two_wicks.iloc[0]


def synthetic_g(items):
    """Tuple(zone,color,clean-direction,both-wicks) directly tests state machine."""
    t = pd.date_range('2023-01-01', periods=len(items), freq='min', tz='UTC')
    g = pd.DataFrame(items, columns=['ema_zone','color','clean_direction','both_wicks'])
    g['timestamp'], g['available_at'] = t, t + pd.Timedelta(minutes=1)
    g['ready'], g['segment_id'], g['partition'], g['body_ratio'] = True, 0, 'in_sample', .1
    return g


def test_clean_run_intermediate_terminal_no_body_threshold():
    g = synthetic_g([(1,1,0,False), (1,-1,1,False), (1,-1,1,False),
                     (1,1,0,False), (1,1,0,True)])
    g.loc[4, 'body_ratio'] = .9
    e = sequences(g, 'TEST').iloc[0]
    assert e.pullback_count == 2 and e.impulse_count == 1
    assert e.intermediate_count == 1 and e.terminal_index == 4 and e.terminal_color_match
    assert e.terminal_body_ratio == .9  # Large body retained, never called a Doji.
    assert e.available_at == g.available_at.iloc[4]


def test_bearish_symmetry():
    bullish = synthetic_g([(1,1,0,False), (1,-1,1,False), (1,1,0,True)])
    bearish = bullish.copy()
    for col in ['ema_zone', 'color', 'clean_direction']: bearish[col] *= -1
    a, b = sequences(bullish, 'TEST').iloc[0], sequences(bearish, 'TEST').iloc[0]
    assert a.direction == -b.direction
    assert a.pullback_count == b.pullback_count and a.intermediate_count == b.intermediate_count
    assert a.terminal_color_match and b.terminal_color_match


def test_wrong_color_terminal_kept_and_flagged():
    e = sequences(synthetic_g([(1,1,0,False), (1,-1,1,False), (1,-1,0,True)]), 'TEST').iloc[0]
    assert e.status == 'observed_two_wick_terminal' and not e.terminal_color_match


@pytest.mark.parametrize('kind,expected', [('zone', 'censored_ema_zone_lost'), ('gap','censored_gap'),
                                          ('split','censored_split'), ('warmup','censored_warmup')])
def test_censor_boundaries(kind, expected):
    g = synthetic_g([(1,1,0,False), (1,-1,1,False), (1,1,0,True)])
    if kind == 'zone': g.loc[2, 'ema_zone'] = 0
    if kind == 'gap': g.loc[2, 'segment_id'] = 1
    if kind == 'split': g.loc[2, 'partition'] = 'validation'
    if kind == 'warmup': g.loc[2, 'ready'] = False
    assert sequences(g, 'TEST').status.iloc[0] == expected


def test_replacement_and_dataset_end():
    g = synthetic_g([(1,-1,1,False), (1,1,0,False), (1,-1,1,False)])
    e = sequences(g, 'TEST')
    assert e.status.tolist() == ['censored_replaced_by_clean_run', 'censored_data_end']
    assert e.impulse_count.tolist() == [0, 1]


def test_no_maximum_pullback_length():
    g = synthetic_g([(1,1,0,False)] + [(1,-1,1,False)]*1000 + [(1,1,0,True)])
    assert sequences(g, 'TEST').pullback_count.iloc[0] == 1000


def test_sequence_prefix_invariance():
    g = synthetic_g([(1,1,0,False), (1,-1,1,False), (1,1,0,True),
                     (1,-1,1,False), (1,1,0,True)])
    full, prefix = sequences(g, 'TEST'), sequences(g.iloc[:3], 'TEST')
    pd.testing.assert_frame_equal(full.loc[full.terminal_index.lt(3)].reset_index(drop=True), prefix)


def forward_fixture():
    g = synthetic_g([(1,1,0,False), (1,-1,1,False), (1,1,0,True), (1,1,0,False), (1,1,0,False)])
    f = g[['timestamp','partition','segment_id']].copy()
    f['open'], f['high'], f['low'], f['close'] = 100., 110., 90., 105.
    f['ha_close'] = 999999.  # Never a price anchor or return input.
    return f, sequences(g, 'TEST')


def test_forward_real_ohlc_math_no_synthetic_execution():
    f, events = forward_fixture()
    row = forward_behavior(f, events, [1]).iloc[0]
    assert row.anchor_open == 100 and row.end_close == 105
    assert row.directional_return_bps == pytest.approx(500)
    assert row.favorable_excursion_bps == pytest.approx(1000)
    assert row.adverse_excursion_bps == pytest.approx(-1000)
    assert row.end_time == f.timestamp.iloc[3] + pd.Timedelta(minutes=1)
    events['direction'] = -1
    assert forward_behavior(f, events, [1]).directional_return_bps.iloc[0] == pytest.approx(-500)


@pytest.mark.parametrize('kind', ['gap','split','data_end'])
def test_forward_censor_not_loss(kind):
    f, events = forward_fixture()
    horizon = 5 if kind == 'data_end' else 1
    if kind == 'gap': f.loc[3:, 'segment_id'] = 1
    if kind == 'split': f.loc[3:, 'partition'] = 'validation'
    row = forward_behavior(f, events, [horizon]).iloc[0]
    assert row.status == 'censored_' + kind and pd.isna(row.directional_return_bps)


def test_no_impulse_not_in_forward_cohort():
    f, events = forward_fixture()
    events['impulse_count'] = 0
    assert forward_behavior(f, events, [1]).empty


def test_summary_empty_partitions_and_null_metrics():
    g = geometry(features())
    events = sequences(g, 'TEST')
    f = features().rename(columns={'ha_open':'open', 'ha_high':'high', 'ha_low':'low', 'ha_close':'close'})
    forward = forward_behavior(f, events, [1])
    result = summaries(g, events, forward, dict(body_ratio_bin_edges=[0,.5,1], forward_horizons_minutes=[1]))
    assert result['overall']['candles']['body_ratio_histogram']['counts'] == [1,2]
    assert result['partitions']['out_of_sample']['candles']['ready_candles'] == 0
    assert result['partitions']['out_of_sample']['candles']['distributions']['body']['mean'] is None
    assert result['overall']['sequences']['exact_pattern_count'] is None
