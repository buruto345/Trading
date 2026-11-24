"""Collect all available original M1 archives; preserve every existing M5 artifact."""
import argparse
import json
import logging
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.ha_research.data import collect_symbol, digest, save_json


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'config/ha_ema_research.json')
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8'))
    out = ROOT / 'reports/ha_ema'
    out.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
                        handlers=[logging.StreamHandler(), logging.FileHandler(out / 'collection.log', encoding='utf-8')])
    before = out / 'preservation_before.json'
    if not before.exists():
        paths = list((ROOT / 'data/processed').rglob('*.parquet'))
        paths += [p for p in (ROOT / 'reports').rglob('*') if p.is_file() and out not in p.parents]
        paths += [p for p in (ROOT / 'data/manifests').rglob('*.json') if 'ha_m1' not in p.parts]
        save_json(before, {p.relative_to(ROOT).as_posix(): digest(p) for p in paths if 'ha_m1' not in p.parts})
    results = []
    for symbol in config['symbols']:
        logging.info('Collecting original M1: %s', symbol)
        try:
            meta = collect_symbol(ROOT, symbol, config)
            results.append({'symbol': symbol, 'status': 'collected', 'candles': meta['quality']['validated_candles']})
        except Exception as exc:
            logging.exception('%s unavailable', symbol)
            results.append({'symbol': symbol, 'status': 'unavailable', 'error': str(exc)})
        save_json(out / 'collection_status.json', results)
    if any(x['status'] != 'collected' for x in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
