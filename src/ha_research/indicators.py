"""Causal HA and EMA features on validated, strictly ordered original M1 bars."""
import numpy as np
import pandas as pd


def indicators(frame, span=100, warmup=500):
    if not isinstance(span, int) or span < 1 or not isinstance(warmup, int) or warmup < span:
        raise ValueError('Require integer span >= 1 and warmup >= span')
    df = frame.copy().reset_index(drop=True)
    t = pd.to_datetime(df.timestamp, utc=True)
    if t.isna().any() or t.duplicated().any() or not t.is_monotonic_increasing:
        raise ValueError('Indicators require unique ordered valid timestamps')
    prices = df[['open', 'high', 'low', 'close']].to_numpy(dtype=float)
    if not np.isfinite(prices).all() or (prices <= 0).any():
        raise ValueError('Indicators require finite positive OHLC')
    if len(df) and ((prices[:, 1] < prices.max(axis=1)).any() or (prices[:, 2] > prices.min(axis=1)).any()):
        raise ValueError('Invalid OHLC geometry')
    if (t.dt.second.ne(0) | t.dt.microsecond.ne(0) | t.dt.nanosecond.ne(0)).any():
        raise ValueError('Require minute-aligned timestamps')
    n = len(df)
    hc = prices.mean(axis=1)
    ho, ema = np.empty(n), np.empty(n)
    age = np.empty(n, dtype=np.int32)
    reset = t.diff().ne(pd.Timedelta(minutes=1)).to_numpy()
    alpha = 2.0 / (span + 1)
    for i in range(n):
        if reset[i]:
            ho[i] = (prices[i, 0] + prices[i, 3]) / 2
            ema[i] = hc[i]
            age[i] = 1
        else:
            ho[i] = (ho[i - 1] + hc[i - 1]) / 2
            ema[i] = alpha * hc[i] + (1 - alpha) * ema[i - 1]
            age[i] = age[i - 1] + 1
    hh = np.maximum.reduce([prices[:, 1], ho, hc])
    hl = np.minimum.reduce([prices[:, 2], ho, hc])
    ranges = hh - hl
    body = np.abs(hc - ho)
    df['timestamp'] = t
    df['available_at'] = t + pd.Timedelta(minutes=1)
    df['segment_id'] = np.cumsum(reset).astype('int32') - 1
    df['segment_age'] = age
    df['ha_open'], df['ha_high'], df['ha_low'], df['ha_close'] = ho, hh, hl, hc
    df['ema100' if span == 100 else 'ema'] = ema
    df['indicator_ready'] = age >= warmup
    df['ha_body_ratio'] = np.divide(body, ranges, out=np.full(n, np.nan), where=ranges > 0)
    df['ha_upper_wick'] = hh - np.maximum(ho, hc)
    df['ha_lower_wick'] = np.minimum(ho, hc) - hl
    df['ha_color'] = np.sign(hc - ho).astype('int8')
    # These are descriptive geometry only, not classified Dojis or patterns.
    df['both_wicks'] = (df.ha_upper_wick > 0) & (df.ha_lower_wick > 0)
    return df


def partitions(timestamps, config):
    t = pd.to_datetime(timestamps, utc=True)
    a, b = pd.Timestamp(config['train_end_exclusive']), pd.Timestamp(config['validation_end_exclusive'])
    if a >= b or b >= pd.Timestamp(config['cutoff_exclusive']):
        raise ValueError('Chronological boundaries must strictly increase')
    return np.where(t < a, 'in_sample', np.where(t < b, 'validation', 'out_of_sample'))
