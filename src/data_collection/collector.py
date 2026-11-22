"""Download public Binance archives, verify checksums, and persist reproducible data."""
from __future__ import annotations

import hashlib
import io
import json
import logging
import time
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

if TYPE_CHECKING:
    import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://data.binance.vision/"
BUCKET = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
NS = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
LOG = logging.getLogger(__name__)


def _get(url: str, attempts: int = 3) -> bytes:
    for attempt in range(attempts):
        try:
            with urlopen(url, timeout=45) as response:
                return response.read()
        except HTTPError as exc:
            if exc.code in (403, 404) or attempt == attempts - 1:
                raise
        except Exception:
            if attempt == attempts - 1:
                raise
        time.sleep(2 ** attempt)
    raise RuntimeError("Download retries exhausted")


def list_keys(prefix: str) -> list[str]:
    """Enumerate the public provider bucket; no guessed missing archive requests."""
    keys, marker = [], ""
    while True:
        params = {"prefix": prefix, "max-keys": 1000, "marker": marker}
        root = ET.fromstring(_get(BUCKET + "?" + urlencode(params)))
        page = [node.text for node in root.findall("s:Contents/s:Key", NS)]
        keys.extend(page)
        if root.findtext("s:IsTruncated", "false", NS) != "true":
            return keys
        marker = page[-1]


def download_archive(key: str, root: Path = ROOT) -> tuple[Path, dict]:
    """Cache original ZIP and checksum, enforcing provider SHA256 integrity."""
    target = root / "data/raw" / key.removeprefix("data/")
    target.parent.mkdir(parents=True, exist_ok=True)
    checksum_path = Path(str(target) + ".CHECKSUM")
    if not checksum_path.exists():
        checksum_path.write_bytes(_get(BASE + key + ".CHECKSUM"))
    checksum = checksum_path.read_text().split()[0].lower()
    cached = target.exists()
    if cached and hashlib.sha256(target.read_bytes()).hexdigest() != checksum:
        cached = False
    if not cached:
        payload = _get(BASE + key)
        if hashlib.sha256(payload).hexdigest() != checksum:
            raise ValueError(f"Checksum mismatch: {key}")
        temporary = Path(str(target) + ".part")
        temporary.write_bytes(payload)
        temporary.replace(target)
    metadata = {
        "source_url": BASE + key, "checksum_url": BASE + key + ".CHECKSUM",
        "relative_path": str(target.relative_to(root)).replace("\\", "/"),
        "sha256": checksum, "checksum_verified": True, "bytes": target.stat().st_size,
        "download_date": datetime.fromtimestamp(target.stat().st_mtime, timezone.utc).isoformat(),
    }
    return target, metadata


def read_archive(path: Path, symbol: str) -> pd.DataFrame:
    """Read both historical headerless and newer header-bearing kline CSVs."""
    import pandas as pd
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"Expected one CSV in {path}")
        payload = archive.read(names[0])
    first_cell = payload.split(b",", 1)[0]
    skip = 0 if first_cell.isdigit() else 1
    frame = pd.read_csv(io.BytesIO(payload), header=None, skiprows=skip, usecols=range(6),
                        names=["source_timestamp", "open", "high", "low", "close", "volume"])
    frame["timestamp"] = frame.source_timestamp
    frame["symbol"] = symbol
    return frame


def collect_symbol(symbol: str, cutoff: str = "2026-11-20", root: Path = ROOT) -> tuple[dict, list[dict]]:
    import pandas as pd
    from src.data_validation.validator import validate_candles
    monthly = list_keys(f"data/futures/um/monthly/klines/{symbol}/5m/")
    cutoff_ts = pd.Timestamp(cutoff, tz="UTC")
    keys = [key for key in monthly if key.endswith(".zip")
            and pd.Timestamp(Path(key).stem[-7:] + "-01", tz="UTC") < cutoff_ts.replace(day=1)]
    # Daily archive listing also discovers early days absent from the monthly archive.
    daily = list_keys(f"data/futures/um/daily/klines/{symbol}/5m/")
    covered_months = {Path(key).stem[-7:] for key in keys}
    for key in daily:
        if not key.endswith(".zip"):
            continue
        date = Path(key).stem[-10:]
        if date[:7] not in covered_months and pd.Timestamp(date, tz="UTC") <= cutoff_ts:
            keys.append(key)
    keys = sorted(keys)
    files, frames, failures = [], [], []
    def task(key: str):
        path, meta = download_archive(key, root)
        frame = read_archive(path, symbol)
        meta.update(symbol=symbol, timeframe="5m", raw_candles=len(frame))
        return frame, meta
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(task, key): key for key in keys}
        for count, future in enumerate(as_completed(futures), 1):
            try:
                frame, meta = future.result()
                frames.append(frame)
                files.append(meta)
            except Exception as exc:
                failures.append({"url": BASE + futures[future], "error": str(exc)})
            if count % 20 == 0 or count == len(keys):
                LOG.info("%s: %s / %s archives processed", symbol, count, len(keys))
    metadata = {
        "symbol": symbol, "instrument": symbol, "provider": "Binance Public Data",
        "source_url": BASE + f"?prefix=data/futures/um/monthly/klines/{symbol}/5m/",
        "market_type": "USD-M perpetual futures", "timeframe": "5m", "timezone": "UTC",
        "downloaded_files": len(files), "available_files": len(keys), "download_failures": failures,
        "collection_cutoff": cutoff, "download_date": datetime.now(timezone.utc).isoformat(),
        "known_limitations": ["Single venue, perpetual futures rather than spot or physical underlying.",
                              "Trade-price OHLCV does not identify intrabar order, bid/ask, funding or executable fills.",
                              "Provider archives can be revised; local copies and SHA256 freeze this run.",
                              "M1 is fetched on demand for ambiguous M5 observations; M1 may remain ambiguous."],
    }
    if frames:
        joined = pd.concat(frames, ignore_index=True)
        validated, quality = validate_candles(joined, 5)
        # Monthly files occasionally omit complete days that exist in daily archives.
        # Fetch only documented source days intersecting observed internal gaps.
        missing_before = quality['missing_candles']
        repair_days = set()
        for gap in quality['gap_ranges']:
            first = pd.Timestamp(gap['previous_candle']) + pd.Timedelta(minutes=5)
            last = pd.Timestamp(gap['next_candle']) - pd.Timedelta(minutes=5)
            repair_days.update(day.strftime('%Y-%m-%d') for day in pd.date_range(first.floor('D'), last.floor('D'), freq='D'))
        repair_keys = [f'data/futures/um/daily/klines/{symbol}/5m/{symbol}-5m-{day}.zip' for day in sorted(repair_days)]
        daily_set = set(daily)
        repairs = []
        for key in repair_keys:
            if key not in daily_set or key in keys:
                continue
            try:
                frame, meta = task(key)
                frames.append(frame); files.append(meta); repairs.append(key)
            except Exception as exc:
                failures.append({'url': BASE + key, 'error': str(exc)})
        if repairs:
            joined = pd.concat(frames, ignore_index=True)
            validated, quality = validate_candles(joined, 5)
        metadata['monthly_gap_intervals_before_daily_repair'] = missing_before
        metadata['daily_gap_repair_files'] = repairs
        metadata['downloaded_files'] = len(files)
        metadata['available_files'] = len(keys) + len(repairs)
        metadata.update(quality)
        if symbol == "XAUUSDT":
            metadata["official_general_availability_date"] = "2026-01-05"
            metadata["launch_source_url"] = "https://www.binance.com/en/support/announcement/detail/ecf7318c0d434c339e80878588e700d0"
            metadata["archive_candles_before_general_availability"] = int((validated.timestamp < pd.Timestamp("2026-01-05", tz="UTC")).sum())
            metadata["known_limitations"].append("Archive contains dates before official 2026-01-05 general availability. Retained for provenance; exclude before this date in primary research. Intraday public launch time not established.")
            metadata["known_limitations"].append("Commodity contract trading-calendar changes and scheduled closures can contribute to absent 24/7-grid candles; absence is not automatically a data error.")
            metadata["trading_schedule_source_url"] = "https://www.binance.com/en-NG/square/post/09-15-2026-binance-to-move-commodity-based-tradfi-perpetual-contracts-to-24-5-trading-366786094157850"
        out = root / f"data/processed/{symbol}_5m.parquet"
        out.parent.mkdir(parents=True, exist_ok=True)
        validated.to_parquet(out, index=False, compression="zstd")
        metadata["processed_path"] = str(out.relative_to(root)).replace("\\", "/")
        metadata["status"] = "collected"
    else:
        metadata.update(status="unavailable", raw_candles=0, validated_candles=0)
    return metadata, sorted(files, key=lambda item: item["source_url"])


def collect_all(root: Path = ROOT, cutoff: str = "2026-11-20") -> dict:
    destination = root / "data/manifests/historical_data_manifest.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = {"provider_documentation": "https://github.com/binance/binance-public-data",
              "retrieved_at": datetime.now(timezone.utc).isoformat(), "instruments": [], "files": []}
    for symbol in ["BTCUSDT", "ZECUSDT", "XAUUSDT"]:
        LOG.info("Collecting %s", symbol)
        try:
            summary, files = collect_symbol(symbol, cutoff, root)
        except Exception as exc:
            LOG.exception("Collection failed for %s", symbol)
            summary, files = {"symbol": symbol, "status": "unavailable", "error": str(exc)}, []
        result["instruments"].append(summary)
        result["files"].extend(files)
        destination.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def fetch_minutes(symbol: str, day: str, root: Path | None = None) -> pd.DataFrame:
    """Fetch one UTC M1 day. Errors are surfaced; no synthetic fallback is allowed."""
    import pandas as pd
    from src.data_validation.validator import validate_candles
    root = ROOT if root is None else Path(root)
    day = str(pd.Timestamp(day).date())
    cache = root / f"data/processed/m1/{symbol}_{day}.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    key = f"data/futures/um/daily/klines/{symbol}/1m/{symbol}-1m-{day}.zip"
    path, metadata = download_archive(key, root)
    frame, quality = validate_candles(read_archive(path, symbol), 1)
    cache.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(cache, index=False, compression="zstd")
    metadata.update(quality, symbol=symbol, timeframe="1m")
    metadata_path = root / f"data/manifests/m1/{symbol}_{day}.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return frame
