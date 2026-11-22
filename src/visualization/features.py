"""Features measured at sweep time, never fitted using future candles."""
from __future__ import annotations
import numpy as np
import pandas as pd


def add_market_features(candles: pd.DataFrame, patterns: pd.DataFrame) -> pd.DataFrame:
    if patterns.empty:
        return patterns.copy()
    out = patterns.copy()
    close = candles['close'].astype(float)
    returns = close.pct_change(fill_method=None)
    volatility = returns.rolling(288, min_periods=288).std()
    trend = close / close.shift(288) - 1
    day = pd.to_datetime(candles['timestamp'], utc=True).dt.floor('D')
    daily = candles.assign(day=day).groupby('day', sort=True).agg(open=('open','first'),close=('close','last'))
    bias = np.sign(daily['close'] - daily['open']).shift(1)
    indices = out['sweep_idx'].astype(int).to_numpy()
    out['volatility'] = volatility.iloc[indices].to_numpy()
    out['volume'] = candles['volume'].iloc[indices].to_numpy()
    out['regime'] = np.where(trend.iloc[indices].isna(),'warmup',np.where(trend.iloc[indices]>=0,'up_24h','down_24h'))
    previous = day.map(bias).iloc[indices].to_numpy()
    direction = np.where(out['direction'].eq('bullish'),1,-1)
    out['daily_bias'] = np.where(np.isnan(previous),'unavailable',np.where(previous==0,'neutral',np.where(previous==direction,'aligned','opposed')))
    out['fvg_relative'] = out['fvg_size'].to_numpy()/close.iloc[indices].to_numpy()
    out['sweep_relative'] = out['sweep_size'].to_numpy()/close.iloc[indices].to_numpy()
    return out

