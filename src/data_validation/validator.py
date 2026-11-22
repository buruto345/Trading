"""Conservative OHLCV validation without filling missing market observations."""
from __future__ import annotations

import numpy as np
import pandas as pd


def normalize_timestamp(values: pd.Series) -> pd.Series:
    """Normalize integer epoch seconds/ms/us or datetime values to UTC."""
    if pd.api.types.is_numeric_dtype(values):
        magnitude = values.dropna().abs().median()
        unit = "us" if magnitude >= 1e14 else "ms" if magnitude >= 1e11 else "s"
        return pd.to_datetime(values, unit=unit, utc=True, errors="coerce")
    return pd.to_datetime(values, utc=True, errors="coerce")


def validate_candles(frame: pd.DataFrame, interval_minutes: int = 5) -> tuple[pd.DataFrame, dict]:
    """Reject invalid rows, de-duplicate, expose gaps, and retain source timestamps."""
    df = frame.copy()
    raw_count = len(df)
    df["timestamp"] = normalize_timestamp(df["timestamp"])
    cols = ["open", "high", "low", "close", "volume"]
    for name in cols:
        df[name] = pd.to_numeric(df[name], errors="coerce")
    valid = df["timestamp"].notna() & np.isfinite(df[cols]).all(axis=1)
    valid &= (df[["open", "high", "low", "close"]] > 0).all(axis=1) & (df.volume >= 0)
    valid &= (df.high >= df[["open", "close", "low"]].max(axis=1))
    valid &= (df.low <= df[["open", "close", "high"]].min(axis=1))
    valid &= (df.timestamp.dt.minute % interval_minutes == 0) & (df.timestamp.dt.second == 0) & (df.timestamp.dt.microsecond == 0)
    invalid_count = int((~valid).sum())
    df = df.loc[valid].sort_values("timestamp", kind="stable")
    duplicates = int(df.duplicated("timestamp").sum())
    conflicts = int(df.groupby("timestamp")[cols].nunique().gt(1).any(axis=1).sum()) if duplicates else 0
    df = df.drop_duplicates("timestamp", keep="first").reset_index(drop=True)
    delta = df.timestamp.diff().dt.total_seconds().div(interval_minutes * 60)
    missing = int((delta.dropna() - 1).clip(lower=0).sum())
    gap_count = int((delta > 1).sum())
    df["segment_id"] = (delta > 1).cumsum().astype("int32")
    expected = len(df) + missing
    gap_ranges = [{"previous_candle": df.timestamp.iloc[i - 1].isoformat(),
                   "next_candle": df.timestamp.iloc[i].isoformat(),
                   "missing_intervals": int(delta.iloc[i] - 1)}
                  for i in np.flatnonzero((delta > 1).to_numpy())]
    metadata = {
        "raw_candles": raw_count, "validated_candles": len(df),
        "invalid_candles": invalid_count, "duplicate_candles": duplicates,
        "conflicting_duplicate_timestamps": conflicts, "missing_candles": missing,
        "gap_count": gap_count, "completeness": len(df) / expected if expected else None,
        "gap_ranges": gap_ranges,
        "earliest_timestamp": df.timestamp.min().isoformat() if len(df) else None,
        "latest_timestamp": df.timestamp.max().isoformat() if len(df) else None,
        "zero_volume_candles": int((df.volume == 0).sum()),
        "missing_policy": "No imputation. Segment id increments after every temporal gap.",
        "missing_definition": "Absent intervals on a continuous UTC grid between first and last candle; may include scheduled closures, not necessarily data defects.",
    }
    return df, metadata
