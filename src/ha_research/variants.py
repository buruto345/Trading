"""D01-D05 causal detection and H1 indicator-boundary research, never execution."""
from collections import Counter
import numpy as np
import pandas as pd

from src.statistics.analysis import wilson


def detect(frame, geometry, symbol, variant, threshold):
    """One observation per qualifying setup; all rules use closed candles only."""
    g = geometry
    ready, segment, zone, color, clean, both, ratio, ranges, tol = (
        g[k].to_numpy() for k in ['ready','segment_id','ema_zone','color','clean_direction',
                                  'both_wicks','body_ratio','range','tolerance'])
    times = frame.timestamp.tolist()
    ha_close, ha_low, ha_high, close = (frame[k].to_numpy() for k in ['ha_close','ha_low','ha_high','close'])
    parts = frame.research_partition.to_numpy()
    records, rejected = [], Counter()
    direction = count = 0
    start = end = -1
    intermediate = False
    for i in range(len(frame)):
        if not ready[i] or (i and segment[i] != segment[i-1]):
            if count >= 2: rejected['gap_or_warmup'] += 1
            direction = count = 0
            intermediate = False
        if not ready[i]: continue
        z, col, cl = int(zone[i]), int(color[i]), int(clean[i])
        if direction and z != direction:
            if count >= 2: rejected['ema_zone_lost'] += 1
            direction = count = 0
            intermediate = False
        if direction:
            expansion = i >= 2 and ranges[i] > min(ranges[i-1], ranges[i-2]) + tol[i]
            doji_shape = both[i] and np.isfinite(ratio[i]) and ratio[i] <= threshold and expansion
            if count >= 2 and col == direction:
                if doji_shape:
                    reference = float(ha_close[i])
                    adverse = float(ha_low[i] if direction == 1 else ha_high[i])
                    risk = direction * (reference-adverse)
                    favorable = reference + direction*risk
                    records.append(dict(observation_id=f'{symbol}_{variant}_{i}', symbol=symbol,
                        variant=variant, threshold=threshold, direction=direction, doji_index=i,
                        pullback_start_index=start, pullback_end_index=end, pullback_count=count,
                        intermediate_count=i-end-1, confirmation_time=times[i]+pd.Timedelta(minutes=1),
                        partition=parts[i], body_ratio=float(ratio[i]), doji_range=float(ranges[i]),
                        reference=reference, adverse=adverse, favorable=favorable, risk=risk,
                        doji_market_close=float(close[i]),
                        reference_minus_market_close=reference-float(close[i]),
                        market_close_outside_boundaries=bool(close[i] <= min(adverse,favorable) or close[i] >= max(adverse,favorable))))
                else: rejected['trend_color_not_qualifying_doji'] += 1
                direction = count = 0
                intermediate = False
            elif count >= 2 and col == -direction:
                if doji_shape:
                    rejected['opposite_doji'] += 1
                    direction = count = 0
                    intermediate = False
                elif cl == direction and not intermediate:
                    count += 1
                    end = i
                else:
                    intermediate = True
            elif count == 1 and cl == direction:
                count = 2
                end = i
            else:
                if count >= 2: rejected['neutral_or_invalid_color'] += 1
                direction = count = 0
                intermediate = False
        # A candle consumed as a continuation must not start another setup.
        if not direction and cl:
            direction, count, start, end, intermediate = cl, 1, i, i, False
    if count >= 2: rejected['setup_at_data_end'] += 1
    cols = ['observation_id','symbol','variant','threshold','direction','doji_index',
            'pullback_start_index','pullback_end_index','pullback_count','intermediate_count',
            'confirmation_time','partition','body_ratio','doji_range','reference','adverse',
            'favorable','risk','doji_market_close','reference_minus_market_close','market_close_outside_boundaries']
    return pd.DataFrame(records, columns=cols), dict(rejected)


def domain_ends(frame):
    """Exclusive segment and timestamp-partition ends for every candle."""
    n = len(frame)
    segment = frame.segment_id.to_numpy()
    part = frame.partition.to_numpy()
    outputs = []
    for split in [False, True]:
        boundary = np.r_[True, (segment[1:] != segment[:-1]) | ((part[1:] != part[:-1]) if split else False)]
        starts = np.flatnonzero(boundary)
        ends = np.r_[starts[1:], n]
        result = np.empty(n, dtype=np.int64)
        for start, end in zip(starts, ends): result[start:end] = end
        outputs.append(result)
    return outputs


def first_passage(o, h, l, start, stop, lower, upper, direction):
    """Find first crossing with expanding vector blocks, without a time horizon."""
    cursor, chunk = start, 32
    while cursor < stop:
        end = min(stop, cursor+chunk)
        hit = np.flatnonzero((h[cursor:end] >= upper) | (l[cursor:end] <= lower))
        if len(hit):
            j = cursor+int(hit[0])
            # Open precedes the rest of this candle and can disambiguate a gap.
            if o[j] >= upper: side, rule = 1, 'open_at_or_above_upper'
            elif o[j] <= lower: side, rule = -1, 'open_at_or_below_lower'
            elif h[j] >= upper and l[j] <= lower: return 'ambiguous', j, 'both_boundaries_intrabar'
            elif h[j] >= upper: side, rule = 1, 'upper_only'
            else: side, rule = -1, 'lower_only'
            return ('success' if side == direction else 'failure'), j, rule
        cursor, chunk = end, min(chunk*2, 65536)
    return 'unresolved', max(start-1, stop-1), 'domain_end'


def label(frame, patterns):
    """H1 crossing labels; no synthetic price is treated as a fill."""
    out = patterns.copy()
    o,h,l = (frame[k].to_numpy() for k in ['open','high','low'])
    segment_ends, split_ends = domain_ends(frame)
    times, n = frame.timestamp.tolist(), len(frame)
    labels = []
    for event in patterns.itertuples(index=False):
        i, start = int(event.doji_index), int(event.doji_index)+1
        lower, upper = min(event.adverse,event.favorable), max(event.adverse,event.favorable)
        item = {}
        # Partition membership belongs to confirmation time, not Doji open time.
        partition_stop = split_ends[start] if start < n else n
        for scope, stop in [('full', int(segment_ends[i])), ('partition', int(min(segment_ends[i],partition_stop)))]:
            if not np.isfinite(event.risk) or event.risk <= 0 or lower <= 0:
                status, end, reason = 'invalid', i, 'nonpositive_risk_or_boundary'
            else:
                status,end,reason = first_passage(o,h,l,start,stop,lower,upper,event.direction)
                if status == 'unresolved':
                    reason = 'dataset_end' if stop == n else 'gap' if stop == segment_ends[i] else 'partition_boundary'
            item.update({f'{scope}_outcome':status, f'{scope}_end_index':end,
                         f'{scope}_reason':reason, f'{scope}_end_time':times[end]+pd.Timedelta(minutes=1)})
        labels.append(item)
    return pd.concat([out.reset_index(drop=True), pd.DataFrame(labels, columns=[f'{s}_{k}' for s in ['full','partition']
                           for k in ['outcome','end_index','reason','end_time']])], axis=1)


def overlap(events, scope):
    """Counts intervals intersecting earlier intervals; does not infer independence."""
    if events.empty: return dict(overlapping_with_prior=0, maximum_concurrent=0, independent_observations=None)
    starts = events.doji_index.to_numpy(dtype=int)+1
    ends = events[f'{scope}_end_index'].to_numpy(dtype=int)+1
    order = np.argsort(starts, kind='stable')
    latest, count = -1, 0
    for j in order:
        if starts[j] < latest: count += 1
        latest = max(latest, ends[j])
    valid = ends > starts
    points = [(int(s),1) for s in starts[valid]] + [(int(e),-1) for e in ends[valid]]
    active = peak = 0
    for _, delta in sorted(points):
        active += delta
        peak = max(peak, active)
    return dict(overlapping_with_prior=count, maximum_concurrent=peak, independent_observations=None)


def bootstrap_scenarios(events, scope, config):
    """Moving 7-calendar-day blocks; all scenarios share draws within this cohort."""
    empty = {s: dict(low=None, high=None, valid_repetitions=0) for s in config['scenarios']}
    if events.empty: return empty
    e = events.copy()
    e['day'] = pd.to_datetime(e.confirmation_time, utc=True).dt.floor('D')
    days = pd.date_range(e.day.min(), e.day.max(), freq='D')
    counts = pd.crosstab(e.day, e[f'{scope}_outcome']).reindex(index=days, columns=['success','failure','ambiguous'], fill_value=0).fillna(0).to_numpy(float)
    length = min(config['bootstrap_block_days'], len(counts))
    rng = np.random.default_rng(config['seed'])
    distributions = {s: [] for s in config['scenarios']}
    for _ in range(config['bootstrap_repetitions']):
        starts = rng.integers(0, len(counts)-length+1, size=int(np.ceil(len(counts)/length)))
        indices = (starts[:,None]+np.arange(length)).ravel()[:len(counts)]
        w,l,a = counts[indices].sum(axis=0)
        for scenario in distributions:
            den = w+l if scenario == 'excluded' else w+l+a
            num = w+a if scenario == 'optimistic' else w
            if den: distributions[scenario].append(num/den)
    return {s: dict(low=float(np.quantile(v,.025)) if v else None,
                    high=float(np.quantile(v,.975)) if v else None, valid_repetitions=len(v))
            for s,v in distributions.items()}


def summarize(events, scope, config, bootstrap=True):
    counts = events[f'{scope}_outcome'].value_counts().to_dict()
    w,l,a,u,invalid = (int(counts.get(k,0)) for k in ['success','failure','ambiguous','unresolved','invalid'])
    intervals = bootstrap_scenarios(events,scope,config) if bootstrap else {}
    rows = []
    for scenario in config['scenarios']:
        den = w+l if scenario=='excluded' else w+l+a
        num = w+a if scenario=='optimistic' else w
        ci = wilson(num,den)
        eligible = w+l+a+u
        rows.append(dict(scenario=scenario, scope=scope, patterns=len(events),
            bullish=int(events.direction.eq(1).sum()), bearish=int(events.direction.eq(-1).sum()),
            resolved=w+l, observed_successes=w, observed_failures=l, ambiguous=a, unresolved=u, invalid=invalid,
            scenario_successes=num, scenario_unsuccessful=den-num, denominator=den,
            observed_proportion=num/den if den else None,
            ci95_block=intervals.get(scenario,dict(low=None,high=None,valid_repetitions=0)),
            ci95_wilson_iid_reference=dict(low=ci['low'],high=ci['high']),
            all_observation_bounds=[w/eligible,(w+a+u)/eligible] if eligible else [None,None],
            unresolved_reasons={str(k):int(v) for k,v in events.loc[events[f'{scope}_outcome'].eq('unresolved'),f'{scope}_reason'].value_counts().items()},
            **overlap(events,scope)))
    return rows
