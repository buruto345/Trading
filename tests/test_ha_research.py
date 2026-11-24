"""Hand-calculated indicators and hostile data cases; synthetic inputs only in tests."""
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd
import pytest

from src.ha_research.data import validate_m1, select_keys, collect_symbol, digest
from src.ha_research.indicators import indicators, partitions
from src.ha_research.statistics import UNRESOLVED, require_definitions, outcome_report
from src.ha_research.report import summarize, render


def bars():
    return pd.DataFrame(dict(timestamp=pd.date_range('2020-01-01', periods=3, freq='min', tz='UTC'),
                             open=[10., 12., 14.], high=[14., 16., 18.], low=[8., 10., 12.],
                             close=[12., 14., 16.], symbol='TEST'))


def test_hand_calculated_ha_and_ema():
    result = indicators(bars(), span=3, warmup=3)
    np.testing.assert_allclose(result.ha_close, [11, 13, 15], rtol=0, atol=1e-12)
    np.testing.assert_allclose(result.ha_open, [11, 11, 12], rtol=0, atol=1e-12)
    np.testing.assert_allclose(result.ema, [11, 12, 13.5], rtol=0, atol=1e-12)
    np.testing.assert_allclose(result.ha_high, [14, 16, 18])
    np.testing.assert_allclose(result.ha_low, [8, 10, 12])
    assert result.indicator_ready.tolist() == [False, False, True]
    assert (result.available_at - result.timestamp).eq(pd.Timedelta(minutes=1)).all()


def test_recursive_open_can_extend_beyond_actual_low():
    frame = bars()
    frame.loc[2, ['open', 'high', 'low', 'close']] = [100, 105, 99, 102]
    out = indicators(frame, 3, 3)
    assert out.ha_low.iloc[2] == 12
    assert out.low.iloc[2] == 99  # HA must never overwrite actual prices.


def test_gap_reset_and_warmup():
    frame = bars()
    frame.loc[2, 'timestamp'] += pd.Timedelta(minutes=1)
    out = indicators(frame, 2, 2)
    assert out.segment_age.tolist() == [1, 2, 1]
    assert out.ha_open.iloc[2] == 15
    assert out.ema.iloc[2] == 15
    assert out.indicator_ready.tolist() == [False, True, False]


def test_prefix_invariance_and_pandas_ema_reference():
    n = 600
    frame = pd.concat([bars().iloc[[0]]] * n, ignore_index=True)
    frame['timestamp'] = pd.date_range('2020-01-01', periods=n, freq='min', tz='UTC')
    for col in ['open', 'high', 'low', 'close']:
        frame[col] += np.arange(n) * .1
    full = indicators(frame)
    prefix = indicators(frame.iloc[:520])
    pd.testing.assert_frame_equal(prefix, full.iloc[:520].reset_index(drop=True))
    np.testing.assert_allclose(full.ema100, full.ha_close.ewm(span=100, adjust=False).mean(), atol=1e-12)
    assert not full.indicator_ready.iloc[498] and full.indicator_ready.iloc[499]


@pytest.mark.parametrize('mode', ['reverse', 'duplicate', 'nan', 'offgrid', 'bad_high'])
def test_indicator_rejects_invalid_inputs(mode):
    frame = bars()
    if mode == 'reverse': frame = frame.iloc[::-1]
    if mode == 'duplicate': frame.loc[1, 'timestamp'] = frame.timestamp.iloc[0]
    if mode == 'nan': frame.loc[1, 'open'] = np.nan
    if mode == 'offgrid': frame.loc[1, 'timestamp'] += pd.Timedelta(seconds=1)
    if mode == 'bad_high': frame.loc[1, 'high'] = 1
    with pytest.raises(ValueError): indicators(frame)


def test_empty_and_zero_range():
    assert indicators(bars().iloc[:0]).empty
    frame = bars()
    frame[['open', 'high', 'low', 'close']] = 10.
    result = indicators(frame, 1, 1)
    assert result.ha_body_ratio.isna().all()
    assert not result.both_wicks.any()
    assert result.ha_color.eq(0).all()


def test_optional_volume_and_timezone():
    frame = bars()
    frame['timestamp'] = frame.timestamp.dt.tz_convert('Asia/Ho_Chi_Minh')
    clean, q = validate_m1(frame)
    assert len(clean) == 3 and clean.volume.isna().all()
    assert str(clean.timestamp.dt.tz) == 'UTC'
    assert q['missing_volume_rows'] == 3 and q['zero_volume_candles'] == 0


@pytest.mark.parametrize('unit', ['s', 'ms', 'us'])
def test_epoch_units(unit):
    frame = bars()
    frame['timestamp'] = frame.timestamp.astype('int64') // {'s': 10**6, 'ms': 1000, 'us': 1}[unit] if frame.timestamp.dtype.unit == 'us' else frame.timestamp.astype('int64') // {'s': 10**9, 'ms': 10**6, 'us': 1000}[unit]
    clean, _ = validate_m1(frame)
    pd.testing.assert_series_equal(clean.timestamp, bars().timestamp, check_dtype=False)


def test_duplicate_conflict_quarantine_order_and_gap():
    frame = bars()
    conflict = frame.iloc[[1]].copy()
    conflict['close'] = 13
    frame = pd.concat([frame.iloc[::-1], frame.iloc[[0]], conflict], ignore_index=True)
    clean, q = validate_m1(frame)
    assert len(clean) == 2
    assert q['quarantined_conflict_rows'] == 2
    assert q['duplicate_candles'] == 1
    assert q['missing_candles'] == 1 and not q['input_monotonic']
    assert clean.segment_id.tolist() == [0, 1]
    assert q['raw_candles'] == len(clean) + q['quarantined_conflict_rows'] + q['duplicate_candles'] + q['invalid_candles']


@pytest.mark.parametrize('field,value', [('high', 1), ('low', 30), ('open', 0), ('close', np.inf), ('volume', -1)])
def test_invalid_ohlcv_rejected(field, value):
    frame = bars()
    frame['volume'] = 1.
    frame.loc[1, field] = value
    clean, q = validate_m1(frame)
    assert len(clean) == 2 and q['invalid_candles'] == 1 and q['missing_candles'] == 1


def test_key_selection_monthly_daily_exclusive_cutoff():
    monthly = ['x/TEST-1m-2020-01.zip', 'x/TEST-1m-2020-02.zip']
    daily = ['d/TEST-1m-2020-01-01.zip', 'd/TEST-1m-2020-02-01.zip', 'd/TEST-1m-2020-02-02.zip']
    assert select_keys(monthly, daily, '2020-02-02T00:00:00Z') == sorted([monthly[0], daily[1]])


def test_partitions_fixed_boundaries():
    config = dict(train_end_exclusive='2024-01-01T00:00:00Z', validation_end_exclusive='2025-01-01T00:00:00Z', cutoff_exclusive='2026-11-24T00:00:00Z')
    assert partitions(pd.Series(['2023-12-31T23:59Z', '2024-01-01T00:00Z', '2025-01-01T00:00Z']), config).tolist() == ['in_sample', 'validation', 'out_of_sample']


def test_unresolved_gate():
    with pytest.raises(ValueError, match='entry_price'):
        require_definitions({})
    with pytest.raises(ValueError): outcome_report(pd.DataFrame(), {})


def outcomes():
    return pd.DataFrame(dict(observation_id=list('abcd'), symbol='TEST', period='2020',
                             partition='in_sample', outcome=['win', 'loss', 'ambiguous', 'unresolved']))


def test_outcome_denominators_uncertainty_and_no_independence_invention():
    report = outcome_report(outcomes(), {k: 'Explicit test convention' for k in UNRESOLVED})
    total = report['overall']
    assert total['sample_size'] == 4 and total['resolved'] == 2
    assert total['observed_proportion'] == .5
    assert total['all_observations_bounds'] == [.25, .75]
    assert total['independent_observations'] is None and total['p_equal_075_iid'] is None
    ci = total['wilson95_iid_reference']
    assert ci['low'] == pytest.approx(.09453120573423074)
    assert ci['high'] == pytest.approx(.9054687942657693)


@pytest.mark.parametrize('bad', ['duplicate', 'null', 'unknown'])
def test_invalid_outcomes_rejected(bad):
    frame = outcomes()
    if bad == 'duplicate': frame.loc[1, 'observation_id'] = 'a'
    if bad == 'null': frame.loc[1, 'period'] = None
    if bad == 'unknown': frame.loc[1, 'outcome'] = 'profit'
    with pytest.raises(ValueError): outcome_report(frame, {k: 'test' for k in UNRESOLVED})


def test_collection_and_research_integration_offline(tmp_path, monkeypatch):
    import src.ha_research.data as module
    key = 'data/futures/um/monthly/klines/TEST/1m/TEST-1m-2020-01.zip'
    raw = tmp_path / 'source.zip'
    # A tiny clearly synthetic test ZIP, never written into historical dataset paths.
    csv = '\n'.join(f'{int(t.timestamp()*1000)},{o},{h},{l},{c},1' for t,o,h,l,c in bars()[['timestamp','open','high','low','close']].itertuples(index=False, name=None))
    with zipfile.ZipFile(raw, 'w') as archive: archive.writestr('test.csv', csv)
    monkeypatch.setattr(module, 'list_keys', lambda prefix: [key] if '/monthly/' in prefix else [])
    monkeypatch.setattr(module, 'download_archive', lambda k, root: (raw, dict(relative_path='source.zip', sha256=digest(raw), source_url='synthetic-test-only', checksum_verified=True)))
    config = dict(cutoff_exclusive='2020-02-01T00:00:00Z', workers=1, minimum_free_disk_gb=0)
    meta = collect_symbol(tmp_path, 'TEST', config)
    assert meta['quality']['validated_candles'] == 3 and not meta['failures']
    frame = pd.read_parquet(tmp_path / meta['processed_path'])
    frame = indicators(frame, 100, 100)
    frame['partition'] = 'in_sample'
    summary = summarize(frame, 'TEST')
    assert summary['overall']['candles'] == 3 and summary['overall']['indicator_ready'] == 0
    assert summary['partitions']['out_of_sample']['candles'] == 0
    (tmp_path / 'reports/ha_ema').mkdir(parents=True)
    result = dict(total_validated_candles=3, markets=[dict(symbol='TEST', quality=meta['quality'], descriptive=summary, trailing_missing_minutes=0)])
    render(tmp_path, result)
    html = (tmp_path / 'reports/HA_EMA_M1_Research_Report.html').read_text(encoding='utf-8')
    assert '75%' in html and 'unresolved' in html and 'https://cdn' not in html
