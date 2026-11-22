import io
import hashlib
import zipfile

import pandas as pd
import pytest

from src.data_validation.validator import normalize_timestamp, validate_candles
from src.data_collection.collector import read_archive
from src.data_collection import collector


def candles():
    return pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=4, freq="5min", tz="UTC"),
                         "open": [10.] * 4, "high": [12.] * 4, "low": [9.] * 4,
                         "close": [11.] * 4, "volume": [5.] * 4})


@pytest.mark.parametrize("epoch", [1704067200, 1704067200000, 1704067200000000])
def test_timestamp_normalization(epoch):
    assert normalize_timestamp(pd.Series([epoch]))[0] == pd.Timestamp("2024-01-01", tz="UTC")


def test_missing_candle_no_fill():
    df, stats = validate_candles(candles().drop(index=1))
    assert stats["missing_candles"] == 1
    assert len(df) == 3
    assert df.segment_id.tolist() == [0, 1, 1]


def test_duplicate_detection():
    original = candles()
    df, stats = validate_candles(pd.concat([original, original.iloc[[1]]]))
    assert len(df) == 4
    assert stats["duplicate_candles"] == 1
    assert stats["conflicting_duplicate_timestamps"] == 0


def test_duplicate_conflict_disclosed():
    original = candles()
    duplicate = original.iloc[[1]].copy()
    duplicate["volume"] = 99
    _, stats = validate_candles(pd.concat([original, duplicate]))
    assert stats["conflicting_duplicate_timestamps"] == 1


@pytest.mark.parametrize("column,value", [("open", -1), ("volume", -1), ("high", 8), ("low", 12), ("close", float("nan"))])
def test_invalid_ohlcv_rejected(column, value):
    frame = candles()
    frame.loc[1, column] = value
    valid, stats = validate_candles(frame)
    assert len(valid) == 3
    assert stats["invalid_candles"] == 1


def test_unsorted_input_sorted():
    valid, _ = validate_candles(candles().iloc[::-1])
    assert valid.timestamp.is_monotonic_increasing


@pytest.mark.parametrize("header", ["", "open_time,open,high,low,close,volume\n"])
def test_archive_header_formats(tmp_path, header):
    path = tmp_path / "sample.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("sample.csv", header + "1704067200000,10,12,9,11,5\n")
    frame = read_archive(path, "BTCUSDT")
    assert len(frame) == 1
    assert frame.iloc[0].source_timestamp == 1704067200000


def test_empty_dataset_supported():
    valid, stats = validate_candles(candles().iloc[:0])
    assert len(valid) == 0
    assert stats["completeness"] is None


def test_checksum_mismatch_rejected(tmp_path, monkeypatch):
    key = "data/futures/um/daily/klines/BTCUSDT/1m/test.zip"
    monkeypatch.setattr(collector, "_get", lambda url: b"0" * 64 + b" test.zip" if url.endswith("CHECKSUM") else b"invalid archive")
    with pytest.raises(ValueError, match="Checksum mismatch"):
        collector.download_archive(key, tmp_path)


def test_verified_cache_avoids_download(tmp_path, monkeypatch):
    key = "data/futures/um/daily/klines/BTCUSDT/1m/test.zip"
    payload = b"test original bytes"
    digest = hashlib.sha256(payload).hexdigest()
    requests = []
    def fake_get(url):
        requests.append(url)
        return (digest + " test.zip").encode() if url.endswith("CHECKSUM") else payload
    monkeypatch.setattr(collector, "_get", fake_get)
    path, first = collector.download_archive(key, tmp_path)
    path2, second = collector.download_archive(key, tmp_path)
    assert path == path2
    assert first["sha256"] == second["sha256"] == digest
    assert len(requests) == 2


def test_subminute_timestamp_rejected():
    frame = candles()
    frame.loc[1, "timestamp"] += pd.Timedelta(seconds=1)
    valid, stats = validate_candles(frame)
    assert len(valid) == 3
    assert stats["invalid_candles"] == 1
