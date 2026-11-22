"""Optional standard-library-only prefetch while analysis dependencies install."""
import logging
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data_collection.collector import list_keys, download_archive

if __name__ == "__main__":
    for symbol in ["BTCUSDT", "ZECUSDT", "XAUUSDT"]:
        monthly = [k for k in list_keys(f"data/futures/um/monthly/klines/{symbol}/5m/") if k.endswith(".zip") and Path(k).stem[-7:] < "2026-11"]
        covered = {Path(k).stem[-7:] for k in monthly}
        daily = [k for k in list_keys(f"data/futures/um/daily/klines/{symbol}/5m/") if k.endswith(".zip") and Path(k).stem[-10:] <= "2026-11-20" and Path(k).stem[-10:-3] not in covered]
        keys = monthly + daily
        print(symbol, len(keys), "archives", flush=True)
        def fetch(key):
            try:
                download_archive(key, ROOT)
                return True
            except Exception as exc:
                print(key, str(exc), flush=True)
                return False
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(fetch, keys))
        print(symbol, sum(results), "downloaded and verified", flush=True)
