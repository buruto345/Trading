"""Causal morphology components, explicit sequence conventions, and separate markouts."""
import numpy as np
import pandas as pd


def geometry(frame, ulps=32):
    """Numerical tolerance is not a market tick size or an author's Doji threshold."""
    g = pd.DataFrame(index=frame.index)
    scale = frame[['ha_open', 'ha_high', 'ha_low', 'ha_close', 'ema100']].abs().max(axis=1)
    tol = ulps * np.finfo(float).eps * scale
    body = (frame.ha_close - frame.ha_open).abs()
    ranges = frame.ha_high - frame.ha_low
    upper = frame.ha_high - frame[['ha_open', 'ha_close']].max(axis=1)
    lower = frame[['ha_open', 'ha_close']].min(axis=1) - frame.ha_low
    g['timestamp'] = frame.timestamp
    g['available_at'] = frame.available_at
    g['partition'] = frame.partition
    g['ready'] = frame.indicator_ready
    g['segment_id'] = frame.segment_id
    g['tolerance'] = tol
    g['body'] = body
    g['range'] = ranges
    g['upper_wick'] = upper
    g['lower_wick'] = lower
    g['body_ratio'] = body.div(ranges.where(ranges > 0))
    for name in ['body', 'range', 'upper_wick', 'lower_wick']:
        g[name + '_bps'] = g[name].div(frame.ha_close) * 10000
    g['color'] = np.where(body <= tol, 0, np.sign(frame.ha_close - frame.ha_open)).astype('int8')
    g['ema_zone'] = np.select([frame.ha_low - frame.ema100 > tol,
                                frame.ema100 - frame.ha_high > tol], [1, -1], default=0).astype('int8')
    g['no_upper_wick'] = upper <= tol
    g['no_lower_wick'] = lower <= tol
    g['no_upper_exact'] = upper == 0
    g['no_lower_exact'] = lower == 0
    g['both_wicks'] = (upper > tol) & (lower > tol)
    g['clean_direction'] = np.select([
        g.ready & g.ema_zone.eq(1) & g.color.eq(-1) & g.no_upper_wick,
        g.ready & g.ema_zone.eq(-1) & g.color.eq(1) & g.no_lower_wick], [1, -1], default=0).astype('int8')
    g['same_color_two_wicks'] = g.ready & g.both_wicks & g.ema_zone.ne(0) & g.color.eq(g.ema_zone)
    return g


def sequences(g, symbol):
    """Maximal contiguous clean runs and their first subsequent two-wick candle.

    Terminal size is unrestricted: these rows are NOT original-method patterns.
    Record state only after information is available; forward results are separate.
    """
    columns = ['sequence_id', 'symbol', 'direction', 'start_index', 'end_index',
               'start_time', 'end_time', 'partition', 'impulse_count', 'pullback_count',
               'status', 'terminal_index', 'terminal_time', 'available_at',
               'intermediate_count', 'terminal_color_match', 'terminal_body_ratio']
    a = {name: g[name].to_numpy() for name in ['ready', 'segment_id', 'partition', 'color',
                                              'ema_zone', 'clean_direction', 'both_wicks', 'body_ratio']}
    times = g.timestamp.tolist()
    rows, active, pending = [], None, None
    streak, streak_direction = 0, 0

    def finish(row, status):
        if row is not None:
            row['status'] = status

    for i in range(len(g)):
        boundary = i == 0 or a['segment_id'][i] != a['segment_id'][i-1] or a['partition'][i] != a['partition'][i-1]
        if boundary or not a['ready'][i]:
            reason = 'censored_gap' if i and a['segment_id'][i] != a['segment_id'][i-1] else 'censored_split'
            if not a['ready'][i]: reason = 'censored_warmup'
            finish(active, reason)
            finish(pending, reason)
            active = pending = None
            streak = streak_direction = 0
        if not a['ready'][i]:
            continue
        clean, zone, color = int(a['clean_direction'][i]), int(a['ema_zone'][i]), int(a['color'][i])
        if active is not None:
            if clean == active['direction']:
                active['end_index'], active['end_time'] = i, times[i]
                active['pullback_count'] += 1
            else:
                pending, active = active, None
        if pending is not None:
            if zone != pending['direction']:
                finish(pending, 'censored_ema_zone_lost')
                pending = None
            elif clean:
                finish(pending, 'censored_replaced_by_clean_run')
                pending = None
            elif a['both_wicks'][i]:
                pending.update(status='observed_two_wick_terminal', terminal_index=i,
                               terminal_time=times[i], available_at=times[i] + pd.Timedelta(minutes=1),
                               intermediate_count=i - pending['end_index'] - 1,
                               terminal_color_match=color == pending['direction'],
                               terminal_body_ratio=float(a['body_ratio'][i]))
                pending = None
        if clean and active is None:
            active = dict(sequence_id=f'{symbol}_{i}', symbol=symbol, direction=clean,
                          start_index=i, end_index=i, start_time=times[i], end_time=times[i],
                          partition=a['partition'][i], impulse_count=streak if streak_direction == clean else 0,
                          pullback_count=1, status='pending', terminal_index=None, terminal_time=None,
                          available_at=None, intermediate_count=None, terminal_color_match=False,
                          terminal_body_ratio=None)
            rows.append(active)
        if zone and color == zone:
            streak = streak + 1 if streak_direction == zone else 1
            streak_direction = zone
        else:
            streak = streak_direction = 0
    finish(active, 'censored_data_end')
    finish(pending, 'censored_data_end')
    result = pd.DataFrame(rows, columns=columns)
    for col in ['terminal_index', 'intermediate_count']:
        result[col] = result[col].astype('Int64')
    for col in ['start_time', 'end_time', 'terminal_time', 'available_at']:
        result[col] = pd.to_datetime(result[col], utc=True)
    return result


def forward_behavior(frame, events, horizons):
    """Real OHLC markouts only. No entry assumption, risk levels, wins or losses."""
    cols = ['sequence_id', 'symbol', 'partition', 'terminal_time', 'horizon_minutes',
            'status', 'anchor_time', 'end_time', 'anchor_open', 'end_close',
            'directional_return_bps', 'favorable_excursion_bps', 'adverse_excursion_bps']
    rows = []
    cohort = events.loc[events.status.eq('observed_two_wick_terminal') & events.terminal_color_match & events.impulse_count.gt(0)]
    times, parts, segments = frame.timestamp.tolist(), frame.partition.to_numpy(), frame.segment_id.to_numpy()
    o, h, l, c = (frame[name].to_numpy() for name in ['open', 'high', 'low', 'close'])
    for event in cohort.itertuples(index=False):
        i, direction = int(event.terminal_index), event.direction
        for horizon in horizons:
            if not isinstance(horizon, int) or horizon < 1:
                raise ValueError('Positive integer horizon required')
            j, end = i + 1, i + horizon
            row = dict(sequence_id=event.sequence_id, symbol=event.symbol, partition=event.partition,
                       terminal_time=times[i], horizon_minutes=horizon, status='observed',
                       anchor_time=None, end_time=None, anchor_open=None, end_close=None,
                       directional_return_bps=None, favorable_excursion_bps=None, adverse_excursion_bps=None)
            if end >= len(frame): row['status'] = 'censored_data_end'
            elif segments[end] != segments[i]: row['status'] = 'censored_gap'
            elif parts[end] != parts[i]: row['status'] = 'censored_split'
            else:
                anchor = o[j]
                upper, lower = h[j:end+1].max(), l[j:end+1].min()
                row.update(anchor_time=times[j], end_time=times[end] + pd.Timedelta(minutes=1),
                           anchor_open=float(anchor), end_close=float(c[end]),
                           directional_return_bps=float(direction * (c[end] / anchor - 1) * 10000),
                           favorable_excursion_bps=float(((upper / anchor - 1) if direction == 1 else (1 - lower / anchor)) * 10000),
                           adverse_excursion_bps=float(((lower / anchor - 1) if direction == 1 else (1 - upper / anchor)) * 10000))
            rows.append(row)
    result = pd.DataFrame(rows, columns=cols)
    for col in ['terminal_time', 'anchor_time', 'end_time']:
        result[col] = pd.to_datetime(result[col], utc=True)
    return result


def distribution(values):
    v = pd.Series(values, dtype=float).dropna()
    v = v.loc[np.isfinite(v)]
    if v.empty:
        return dict(n=0, mean=None, min=None, max=None, p05=None, p25=None, median=None, p75=None, p95=None)
    return dict(n=len(v), mean=float(v.mean()), min=float(v.min()), max=float(v.max()),
                **{key: float(v.quantile(q)) for key, q in [('p05', .05), ('p25', .25), ('median', .5), ('p75', .75), ('p95', .95)]})


def candle_summary(g, bins):
    ready = g.loc[g.ready]
    flags = ['no_upper_wick', 'no_lower_wick', 'no_upper_exact', 'no_lower_exact', 'both_wicks', 'same_color_two_wicks']
    counts = {name: int(ready[name].sum()) for name in flags}
    counts.update(above_ema=int(ready.ema_zone.eq(1).sum()), below_ema=int(ready.ema_zone.eq(-1).sum()),
                  ema_touch_or_straddle=int(ready.ema_zone.eq(0).sum()),
                  bullish_clean_component=int(ready.clean_direction.eq(1).sum()),
                  bearish_clean_component=int(ready.clean_direction.eq(-1).sum()),
                  zero_range=int(ready.range.eq(0).sum()))
    histogram = np.histogram(ready.body_ratio.dropna(), bins=bins)[0].tolist()
    return dict(candles=len(g), ready_candles=len(ready), warmup_excluded=len(g)-len(ready),
                counts=counts, frequencies={k: v / len(ready) if len(ready) else None for k, v in counts.items()},
                distributions={name: distribution(ready[name]) for name in
                    ['body', 'body_bps', 'range', 'range_bps', 'upper_wick', 'upper_wick_bps',
                     'lower_wick', 'lower_wick_bps', 'body_ratio']},
                two_wick_body_ratio=distribution(ready.loc[ready.both_wicks, 'body_ratio']),
                same_color_two_wick_body_ratio=distribution(ready.loc[ready.same_color_two_wicks, 'body_ratio']),
                body_ratio_histogram=dict(edges=bins, counts=histogram, zero_range_excluded=counts['zero_range']))


def sequence_summary(events):
    observed = events.loc[events.status.eq('observed_two_wick_terminal')]
    return dict(clean_runs=len(events), statuses={str(k): int(v) for k, v in events.status.value_counts().items()},
                observed_terminals=len(observed), same_color_terminals=int(observed.terminal_color_match.sum()),
                with_impulse_same_color=int((observed.terminal_color_match & observed.impulse_count.gt(0)).sum()),
                pullback_length=distribution(events.pullback_count), impulse_count=distribution(events.impulse_count),
                intermediate_count=distribution(observed.intermediate_count),
                terminal_body_ratio=distribution(observed.terminal_body_ratio),
                exact_pattern_count=None, exact_pattern_count_reason='Doji and sequence definitions unresolved; runs are descriptive conventions')


def forward_summary(rows, horizons):
    return [dict(horizon_minutes=h, sample_size=len(group),
                 observed=int(group.status.eq('observed').sum()),
                 censored=int(group.status.ne('observed').sum()),
                 censor_reasons={str(k): int(v) for k, v in group.loc[group.status.ne('observed'), 'status'].value_counts().items()},
                 directional_return_bps=distribution(group.directional_return_bps),
                 favorable_excursion_bps=distribution(group.favorable_excursion_bps),
                 adverse_excursion_bps=distribution(group.adverse_excursion_bps),
                 independent_observations=None, independence_reason='Potential serial and overlapping-window dependence')
            for h in horizons for group in [rows.loc[rows.horizon_minutes.eq(h)]]]


def summaries(g, events, forward, config):
    def one(gg, ee, ff):
        return dict(candles=candle_summary(gg, config['body_ratio_bin_edges']), sequences=sequence_summary(ee),
                    forward=forward_summary(ff, config['forward_horizons_minutes']))
    overall = one(g, events, forward)
    parts = {p: one(g.loc[g.partition.eq(p)], events.loc[events.partition.eq(p)], forward.loc[forward.partition.eq(p)])
             for p in ['in_sample', 'validation', 'out_of_sample']}
    years = {str(y): one(g.loc[g.timestamp.dt.year.eq(y)], events.loc[events.start_time.dt.year.eq(y)],
                         forward.loc[forward.terminal_time.dt.year.eq(y)]) for y in sorted(g.timestamp.dt.year.unique())}
    return dict(overall=overall, partitions=parts, years=years,
                year_assignment='candles by candle open, sequences by run start, markouts by terminal time')
