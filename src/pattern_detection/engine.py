"""Chronological ICT detection. Experimental conventions live in ENGINE_CONVENTIONS.md."""
from __future__ import annotations

import json
from typing import Any
import numpy as np
import pandas as pd

FIVE_MINUTES = pd.Timedelta(minutes=5)
PATTERN_COLUMNS = ['pattern_id','symbol','direction','sweep_idx','mss_idx','swing_idx',
    'structure_idx','sweep_time','detection_time','confirmation_time','swing_price',
    'structure_price','sweep_extreme','fvg_count','fvg_lower','fvg_upper','fvg_size',
    'fvg_details','sweep_size','body_size','wick_size','delay_bars','overlapping']


def swing_flags(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Centered strict wick pivots; flags are descriptive, available at next close."""
    h, l = df.high.to_numpy(), df.low.to_numpy()
    sh, sl = np.zeros(len(df), bool), np.zeros(len(df), bool)
    if len(df) > 2:
        t = pd.to_datetime(df.timestamp, utc=True)
        contiguous = (t.diff().iloc[1:-1].to_numpy() == FIVE_MINUTES) & (t.diff().iloc[2:].to_numpy() == FIVE_MINUTES)
        sh[1:-1] = (h[1:-1] > h[:-2]) & (h[1:-1] > h[2:]) & contiguous
        sl[1:-1] = (l[1:-1] < l[:-2]) & (l[1:-1] < l[2:]) & contiguous
    return sh, sl


def fvg_flags(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Three-candle wick gaps, indexed by third candle (confirmation at its close)."""
    h, l = df.high.to_numpy(), df.low.to_numpy()
    bull, bear = np.zeros(len(df), bool), np.zeros(len(df), bool)
    if len(df) > 2:
        t = pd.to_datetime(df.timestamp, utc=True)
        contiguous = (t.diff().iloc[1:-1].to_numpy() == FIVE_MINUTES) & (t.diff().iloc[2:].to_numpy() == FIVE_MINUTES)
        bull[2:] = (l[2:] > h[:-2]) & contiguous
        bear[2:] = (h[2:] < l[:-2]) & contiguous
    return bull, bear


def detect_patterns(df: pd.DataFrame, symbol: str, max_sweep_mss: int = 24
                    ) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    """Return accepted observations, rejected setups, and independently labelled counts.

    Data must be sorted, validated UTC M5 bars. No precomputed swing becomes
    accessible before its next candle closes. Pending state never crosses gaps.
    """
    if max_sweep_mss < 1:
        raise ValueError('max_sweep_mss must be positive')
    timestamps = pd.to_datetime(df.timestamp, utc=True).reset_index(drop=True)
    if not timestamps.is_monotonic_increasing or timestamps.duplicated().any():
        raise ValueError('OHLCV timestamps must be unique and sorted')
    contiguous_steps=timestamps.diff().eq(FIVE_MINUTES).to_numpy()
    o,h,l,c = (df[k].to_numpy(dtype=float) for k in ('open','high','low','close'))
    sh,sl = swing_flags(df)
    bull_fvg,bear_fvg = fvg_flags(df)
    highs: list[int] = []
    lows: list[int] = []
    latest_high = latest_low = None
    pending: dict[str, dict[str, Any]] = {}
    patterns, rejected = [], []
    counters = dict(candles=len(df), swing_highs=int(sh.sum()), swing_lows=int(sl.sum()),
                    bullish_sweeps=0,bearish_sweeps=0,mss_events=0,
                    bullish_fvgs=int(bull_fvg.sum()),bearish_fvgs=int(bear_fvg.sum()),
                    valid_patterns=0)
    previous_confirmation = -1

    def reject(p: dict, reason: str, at: int) -> None:
        rejected.append(dict(symbol=symbol,direction=p['direction'],sweep_idx=p['sweep_idx'],
                             swing_idx=p['swing_idx'],structure_idx=p.get('structure_idx'),
                             rejected_idx=at,sweep_time=timestamps.iloc[p['sweep_idx']],
                             rejected_time=timestamps.iloc[at]+FIVE_MINUTES,
                             reason=reason,fvg_count=len(p.get('fvgs',[]))))

    for j in range(len(df)):
        if j and not contiguous_steps[j]:
            for p in pending.values():
                reject(p,'data_gap',j)
            pending.clear(); highs.clear(); lows.clear()
            latest_high=latest_low=None
        # Center j-2 was confirmed by j-1 close, now available at j open.
        center = j-2
        contiguous_prior = j >= 3 and contiguous_steps[j]
        if contiguous_prior:
            if sh[center]:
                highs.append(center); latest_high=center
            if sl[center]:
                lows.append(center); latest_low=center

        for direction,p in list(pending.items()):
            s=p['sweep_idx']; is_bull=direction=='bullish'
            reason=None
            if j-s > max_sweep_mss:
                reason='setup_expired'
            elif (is_bull and l[j] < p['sweep_extreme']) or (not is_bull and h[j] > p['sweep_extreme']):
                reason='sweep_extreme_invalidated'
            if reason:
                reject(p,reason,j); del pending[direction]; continue
            gap_flag=bull_fvg[j] if is_bull else bear_fvg[j]
            if gap_flag and j-2>=s:
                lower,upper=(h[j-2],l[j]) if is_bull else (h[j],l[j-2])
                p['fvgs'].append(dict(formation_idx=j,formation_time=(timestamps.iloc[j]+FIVE_MINUTES).isoformat(),
                                      lower=float(lower),upper=float(upper),size=float(upper-lower)))
            mss=c[j]>p['structure_price'] if is_bull else c[j]<p['structure_price']
            if mss:
                counters['mss_events']+=1
                if not p['fvgs']:
                    reject(p,'mss_without_fvg',j)
                else:
                    fvgs=p.pop('fvgs')
                    p.update(pattern_id=f'{symbol}:{direction}:{timestamps.iloc[s].isoformat()}',
                             symbol=symbol,mss_idx=j,sweep_time=timestamps.iloc[s],
                             detection_time=timestamps.iloc[s]+FIVE_MINUTES,
                             confirmation_time=timestamps.iloc[j]+FIVE_MINUTES,
                             fvg_count=len(fvgs),fvg_lower=fvgs[-1]['lower'],fvg_upper=fvgs[-1]['upper'],
                             fvg_size=sum(g['size'] for g in fvgs),fvg_details=json.dumps(fvgs),
                             delay_bars=j-s,overlapping=s<=previous_confirmation)
                    patterns.append(p.copy()); previous_confirmation=j
                del pending[direction]

        # Select the most recent unbroken pivot before applying this candle's breach.
        for direction, pivots, structure in [('bearish',highs,latest_low),('bullish',lows,latest_high)]:
            if not pivots:
                continue
            si=pivots[-1]; is_bull=direction=='bullish'; price=l[si] if is_bull else h[si]
            valid=(l[j]<price and c[j]>price and c[j]>o[j]) if is_bull else (h[j]>price and c[j]<price and c[j]<o[j])
            if not valid:
                continue
            counters[f'{direction}_sweeps']+=1
            p=dict(direction=direction,sweep_idx=j,swing_idx=si,structure_idx=structure,
                   swing_price=float(price),sweep_extreme=float(l[j] if is_bull else h[j]),
                   sweep_size=float(price-l[j] if is_bull else h[j]-price),
                   body_size=float(abs(c[j]-o[j])),wick_size=float(min(o[j],c[j])-l[j] if is_bull else h[j]-max(o[j],c[j])),fvgs=[])
            if structure is None:
                reject(p,'no_confirmed_structure',j); continue
            p['structure_price']=float(h[structure] if is_bull else l[structure])
            if direction in pending:
                reject(pending[direction],'replaced_by_new_sweep',j)
            pending[direction]=p
        # Breached pivots are permanently consumed, even with wrong colour/close.
        while highs and h[j]>h[highs[-1]]:
            highs.pop()
        while lows and l[j]<l[lows[-1]]:
            lows.pop()

    for p in pending.values():
        reject(p,'end_of_data_before_mss',len(df)-1)
    result=pd.DataFrame(patterns,columns=PATTERN_COLUMNS)
    counters['valid_patterns']=len(result)
    counters['detected_swings']=counters['swing_highs']+counters['swing_lows']
    counters['detected_sweeps']=counters['bullish_sweeps']+counters['bearish_sweeps']
    counters['detected_fvgs']=counters['bullish_fvgs']+counters['bearish_fvgs']
    counters['rejected_setups']=len(rejected)
    return result,pd.DataFrame(rejected,columns=['symbol','direction','sweep_idx','swing_idx','structure_idx','rejected_idx','sweep_time','rejected_time','reason','fvg_count']),counters
