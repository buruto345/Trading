"""Reproducible descriptive historical research; --skip-collection is fully offline."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import logging
from pathlib import Path
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.ha_research.data import digest, save_json
from src.ha_research.indicators import indicators, partitions
from src.ha_research.report import summarize, render
from src.ha_research.statistics import UNRESOLVED


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--skip-collection', action='store_true')
    parser.add_argument('--config', type=Path, default=ROOT / 'config/ha_ema_research.json')
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8'))
    if config['ema_span'] != 100:
        raise ValueError('Confirmed EMA span must be 100')
    out = ROOT / 'reports/ha_ema'
    out.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
                        handlers=[logging.StreamHandler(), logging.FileHandler(out / 'pipeline.log', encoding='utf-8')])
    if not args.skip_collection:
        subprocess.run([sys.executable, str(ROOT / 'scripts/collect_ha_m1.py'), '--config', str(args.config)], check=True, cwd=ROOT)
    with (out / 'tests.log').open('w', encoding='utf-8') as log:
        subprocess.run([sys.executable, '-m', 'pytest', '-q',
                        '--basetemp=' + str(ROOT / 'tests/data/synthetic/.ha_pytest'),
                        '--junitxml=' + str(out / 'tests.xml')],
                       cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    suites = ET.parse(out / 'tests.xml').getroot().findall('testsuite')
    test_counts = {field: sum(int(suite.get(field, '0')) for suite in suites)
                   for field in ['tests', 'failures', 'errors', 'skipped']}
    save_json(out / 'frozen_config.json', config)
    result = dict(config=config, tests=test_counts, markets=[], total_validated_candles=0,
                  outcome_statistics=dict(status='blocked_by_missing_definitions', sample_size=None,
                                          independent_observations=None, observed_proportion=None,
                                          confidence_interval=None, p_value=None),
                  missing_definitions={key: None for key in UNRESOLVED})
    manifest_snapshot = []
    for symbol in config['symbols']:
        logging.info('Validating cached snapshot and calculating indicators: %s', symbol)
        meta = json.loads((ROOT / f'data/manifests/ha_m1/{symbol}.json').read_text(encoding='utf-8'))
        path = ROOT / meta['processed_path']
        if digest(path) != meta['processed_sha256']:
            raise ValueError(f'Processed checksum mismatch: {symbol}')
        if meta['cutoff_exclusive'] != config['cutoff_exclusive']:
            raise ValueError('Cached manifest cutoff differs from configuration; recollect explicitly')
        for archive in meta['files']:
            if digest(ROOT / archive['relative_path']) != archive['sha256']:
                raise ValueError('Raw archive checksum mismatch')
        raw = pd.read_parquet(path)
        if len(raw) != meta['quality']['validated_candles'] or raw.empty:
            raise ValueError('Manifest candle count mismatch or empty dataset')
        research_start = config['research_start_by_symbol'].get(symbol)
        research = raw.loc[raw.timestamp.ge(pd.Timestamp(research_start))].copy() if research_start else raw
        excluded = len(raw) - len(research)
        features = indicators(research, config['ema_span'], config['warmup_bars'])
        features['partition'] = partitions(features.timestamp, config)
        feature_path = ROOT / f'data/processed/ha_m1/{symbol}_features.parquet'
        features.to_parquet(feature_path, index=False, compression='zstd')
        tail = max(0, int((pd.Timestamp(config['cutoff_exclusive']) - raw.timestamp.max()) / pd.Timedelta(minutes=1)) - 1)
        item = dict(symbol=symbol, quality=meta['quality'], failures=meta['failures'],
                    trailing_missing_minutes=tail, pre_research_excluded=excluded,
                    feature_path=feature_path.relative_to(ROOT).as_posix(), feature_sha256=digest(feature_path),
                    descriptive=summarize(features, symbol), limitations=meta['limitations'])
        result['markets'].append(item)
        result['total_validated_candles'] += len(raw)
        manifest_snapshot.append(meta)
        save_json(out / f'{symbol}_quality.json', meta['quality'])
        del features, research, raw
    save_json(out / 'summary.json', result)
    save_json(out / 'manifest_snapshot.json', manifest_snapshot)
    source_paths = list((ROOT / 'src/ha_research').glob('*.py')) + list((ROOT / 'scripts').glob('*ha*.py'))
    source_paths += list((ROOT / 'tests').glob('test_ha*.py')) + list((ROOT / 'docs').glob('HA_*.md'))
    source_paths += [ROOT / 'src/data_collection/collector.py', ROOT / 'src/data_validation/validator.py',
                     ROOT / 'src/statistics/analysis.py', args.config]
    save_json(out / 'execution.json', dict(completed_at=datetime.now(timezone.utc).isoformat(),
              python=platform.python_version(), platform=platform.platform(),
              dependencies={name: importlib.metadata.version(name) for name in ['numpy', 'pandas', 'pyarrow', 'scipy', 'pytest', 'playwright']},
              command=sys.argv, source_sha256={str(p.relative_to(ROOT)): digest(p) for p in source_paths},
              config_sha256=digest(args.config), network_collection=not args.skip_collection))
    render(ROOT, result)
    subprocess.run([sys.executable, str(ROOT / 'scripts/qa_ha_research.py')], cwd=ROOT, check=True)
    logging.info('Complete: %s validated original M1 candles; no outcomes inferred', result['total_validated_candles'])


if __name__ == '__main__':
    main()
