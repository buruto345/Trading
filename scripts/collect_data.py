"""Reproduce authentic historical collection with resumable cached ZIP archives."""
import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data_collection.collector import collect_all

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cutoff", default="2026-11-20")
    args = parser.parse_args()
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(ROOT / "logs/data_collection.log", encoding="utf-8")])
    manifest = collect_all(ROOT, args.cutoff)
    for item in manifest["instruments"]:
        print(item["symbol"], item.get("status"), item.get("validated_candles"), item.get("earliest_timestamp"), item.get("latest_timestamp"))
