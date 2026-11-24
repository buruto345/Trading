"""Original M1 archives using the existing public downloader and UTC validator."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import shutil

import numpy as np
import pandas as pd

from src.data_collection.collector import list_keys, download_archive, read_archive
from src.data_validation.validator import normalize_timestamp, validate_candles

LOG = logging.getLogger(__name__)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.part')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                    allow_nan=False, default=str), encoding='utf-8')
    temporary.replace(path)


def validate_m1(frame):
    """Volume is optional. Quarantine all conflicting timestamps, never pick a price."""
    df = frame.copy()
    df['timestamp'] = normalize_timestamp(df.timestamp)
    ordering = bool(df.timestamp.dropna().is_monotonic_increasing)
    cols = ['open', 'high', 'low', 'close']
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    if 'volume' not in df:
        df['volume'] = np.nan
    df['volume'] = pd.to_numeric(df.volume, errors='coerce')
    missing_volume = int(df.volume.isna().sum())
    duplicate_rows = int(df.duplicated('timestamp').sum())
    duplicated = df[df.duplicated('timestamp', keep=False)]
    conflicts = duplicated.groupby('timestamp')[cols + ['volume']].nunique(dropna=False).gt(1).any(axis=1)
    bad_times = conflicts.index[conflicts]
    quarantine = df.timestamp.isin(bad_times)
    conflict_rows = int(quarantine.sum())
    df = df.loc[~quarantine].copy()
    absent_volume_times = set(df.loc[df.volume.isna(), 'timestamp'])
    df['volume'] = df.volume.fillna(0)  # Validator adapter only; restore missing values below.
    # Existing validator checks microseconds; also reject sub-microsecond timestamps.
    submicro = df.timestamp.dt.nanosecond.ne(0)
    submicro_rows = int(submicro.sum())
    df = df.loc[~submicro]
    clean, quality = validate_candles(df, 1)
    clean.loc[clean.timestamp.isin(absent_volume_times), 'volume'] = np.nan
    quality.update(raw_candles=len(frame), input_monotonic=ordering,
                   source_duplicate_rows=duplicate_rows,
                   conflicting_duplicate_timestamps=len(bad_times),
                   quarantined_conflict_rows=conflict_rows,
                   invalid_candles=quality['invalid_candles'] + submicro_rows,
                   missing_volume_rows=missing_volume,
                   zero_volume_candles=int(clean.volume.eq(0).sum()),
                   timezone='UTC', timestamp_role='candle open; indicators available one minute later',
                   closure_policy='No inferred closure calendar. All gaps remain unclassified; no imputation.',
                   volume_policy='Optional, missing retained as null; never a pattern filter')
    return clean, quality


def select_keys(monthly, daily, cutoff):
    """Prefer completed months, then uncovered days, with an exclusive UTC cutoff."""
    cutoff = pd.Timestamp(cutoff)
    keys = [k for k in monthly if k.endswith('.zip') and
            pd.Timestamp(Path(k).stem[-7:] + '-01', tz='UTC') + pd.offsets.MonthBegin(1) <= cutoff]
    months = {Path(k).stem[-7:] for k in keys}
    keys += [k for k in daily if k.endswith('.zip') and Path(k).stem[-10:-3] not in months
             and pd.Timestamp(Path(k).stem[-10:], tz='UTC') + pd.Timedelta(days=1) <= cutoff]
    return sorted(keys)


def collect_symbol(root, symbol, config):
    prefix = f'data/futures/um/{{}}/klines/{symbol}/1m/'
    monthly = list_keys(prefix.format('monthly'))
    daily = list_keys(prefix.format('daily'))
    keys = select_keys(monthly, daily, config['cutoff_exclusive'])
    frames, files, failures = [], [], []

    def task(key):
        if shutil.disk_usage(root).free < config['minimum_free_disk_gb'] * 1e9:
            raise RuntimeError('Disk reserve reached; archive not downloaded')
        path, meta = download_archive(key, root)
        frame = read_archive(path, symbol)
        meta.update(raw_candles=len(frame), input_monotonic=bool(frame.timestamp.is_monotonic_increasing))
        return frame, meta

    def collect(selected):
        # Ordered consumption makes duplicate handling and provenance deterministic.
        with ThreadPoolExecutor(max_workers=config['workers']) as pool:
            futures = [(key, pool.submit(task, key)) for key in selected]
            for i, (key, future) in enumerate(futures, 1):
                try:
                    frame, meta = future.result()
                    frames.append(frame)
                    files.append(meta)
                except Exception as exc:
                    failures.append({'key': key, 'error': str(exc)})
                if i % 10 == 0 or i == len(selected):
                    LOG.info('%s: %d/%d archives', symbol, i, len(selected))

    collect(keys)
    if not frames:
        raise RuntimeError(f'No M1 archives available for {symbol}: {failures}')
    joined = pd.concat(frames, ignore_index=True)
    clean, quality = validate_m1(joined)
    # Repair only observed gaps from source-listed daily archives, not guessed URLs.
    repair_days = set()
    for gap in quality['gap_ranges']:
        first = pd.Timestamp(gap['previous_candle']) + pd.Timedelta(minutes=1)
        last = pd.Timestamp(gap['next_candle']) - pd.Timedelta(minutes=1)
        repair_days.update(d.strftime('%Y-%m-%d') for d in pd.date_range(first.floor('D'), last.floor('D'), freq='D'))
    repairs = [k for k in daily if k.endswith('.zip') and k not in keys
               and Path(k).stem[-10:] in repair_days
               and pd.Timestamp(Path(k).stem[-10:], tz='UTC') < pd.Timestamp(config['cutoff_exclusive'])]
    if repairs:
        collect(sorted(repairs))
        joined = pd.concat(frames, ignore_index=True)
        clean, quality = validate_m1(joined)
    clean = clean.loc[clean.timestamp < pd.Timestamp(config['cutoff_exclusive'])].reset_index(drop=True)
    out = root / f'data/processed/ha_m1/{symbol}_1m.parquet'
    out.parent.mkdir(parents=True, exist_ok=True)
    clean.to_parquet(out, index=False, compression='zstd')
    metadata = dict(symbol=symbol, timeframe='1m', provider='Binance Public Data',
                    market='USD-M perpetual futures',
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                    cutoff_exclusive=config['cutoff_exclusive'],
                    requested_coverage='all source-listed history before cutoff',
                    available_archives=len(keys), repair_archives=len(repairs),
                    downloaded_archives=len(files), failures=failures, files=files,
                    quality=quality, processed_path=out.relative_to(root).as_posix(),
                    processed_sha256=digest(out),
                    provider_documentation='https://github.com/binance/binance-public-data',
                    terms='https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md',
                    limitations=['Single venue; no Forex or physical/spot gold.',
                                 'Archive availability is not proof of full listing-to-cutoff coverage.',
                                 'OHLC does not identify bid/ask, fees, funding, or intrabar path.',
                                 'Scheduled closures and outages are not distinguishable without a verified calendar.'])
    save_json(root / f'data/manifests/ha_m1/{symbol}.json', metadata)
    return metadata
