"""Offline-only v2 research of the three existing M1 snapshots. No collector calls."""
from datetime import datetime, timezone
import gc
import importlib.metadata
import json
import logging
from pathlib import Path
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.ha_research.data import digest, save_json, validate_m1
from src.ha_research.indicators import indicators, partitions
from src.ha_research.descriptive import geometry, sequences, forward_behavior, summaries
from src.ha_research.descriptive_report import render_reports
from src.ha_research.statistics import UNRESOLVED


def main():
    config_path = ROOT / 'config/ha_descriptive.json'
    config = json.loads(config_path.read_text(encoding='utf-8'))
    base = json.loads((ROOT / config['base_config']).read_text(encoding='utf-8'))
    out = ROOT / 'reports/ha_descriptive'
    out.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
                        handlers=[logging.StreamHandler(), logging.FileHandler(out / 'pipeline.log', encoding='utf-8')])
    if not (out / 'preservation_before.json').exists():
        files = [p for folder in ['data/processed', 'data/manifests', 'reports'] for p in (ROOT / folder).rglob('*')
                 if p.is_file() and out not in p.parents and 'ha_descriptive' not in p.parts]
        save_json(out / 'preservation_before.json', {p.relative_to(ROOT).as_posix(): digest(p) for p in files})
    save_json(out / 'frozen_config.json', config)
    save_json(out / 'frozen_base_config.json', base)
    with (out / 'tests.log').open('w', encoding='utf-8') as log:
        subprocess.run([sys.executable, '-m', 'pytest', '-q',
                        '--basetemp=' + str(ROOT / 'tests/data/synthetic/.ha_pytest'),
                        '--junitxml=' + str(out / 'tests.xml')],
                       cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    suites = ET.parse(out / 'tests.xml').getroot().findall('testsuite')
    tests = {k: sum(int(s.get(k, '0')) for s in suites) for k in ['tests', 'failures', 'errors', 'skipped']}
    result = dict(config=config, base_config=base, tests=tests, markets=[])
    artifacts = {}
    for symbol in config['symbols']:
        logging.info('%s: verify existing raw/processed hashes and revalidate M1', symbol)
        meta_path = ROOT / f'data/manifests/ha_m1/{symbol}.json'
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        source = ROOT / meta['processed_path']
        if digest(source) != meta['processed_sha256']:
            raise ValueError(f'{symbol}: corrupted processed dataset; no automatic download')
        for archive in meta['files']:
            if digest(ROOT / archive['relative_path']) != archive['sha256']:
                raise ValueError(f'{symbol}: corrupted source archive; no automatic download')
        raw = pd.read_parquet(source)
        if set(raw.symbol.unique()) != {symbol}:
            raise ValueError('Mixed or incorrect instruments')
        clean, quality = validate_m1(raw)
        if not quality['input_monotonic'] or quality['invalid_candles'] or quality['source_duplicate_rows']:
            raise ValueError('Stored snapshot failed revalidation; investigate without silently replacing data')
        if len(clean) != meta['quality']['validated_candles'] or quality['missing_candles'] != meta['quality']['missing_candles']:
            raise ValueError('Coverage differs from source manifest')
        tail = max(0, int((pd.Timestamp(base['cutoff_exclusive']) - clean.timestamp.max()) / pd.Timedelta(minutes=1)) - 1)
        del raw
        start = base['research_start_by_symbol'].get(symbol)
        research = clean.loc[clean.timestamp.ge(pd.Timestamp(start))].copy() if start else clean
        excluded = len(clean) - len(research)
        logging.info('%s: recompute HA/EMA and geometry', symbol)
        frame = indicators(research, base['ema_span'], base['warmup_bars'])
        frame['partition'] = partitions(frame.timestamp, base)
        # Reconcile mathematical outputs with the preserved v1 indicator snapshot.
        cached = pd.read_parquet(ROOT / f'data/processed/ha_m1/{symbol}_features.parquet',
                                 columns=['timestamp', 'ha_open', 'ha_high', 'ha_low', 'ha_close', 'ema100'])
        if not frame.timestamp.equals(cached.timestamp):
            raise ValueError('v1 feature timestamp mismatch')
        for col in ['ha_open', 'ha_high', 'ha_low', 'ha_close', 'ema100']:
            np.testing.assert_allclose(frame[col], cached[col], rtol=0, atol=1e-10)
        del cached, clean, research
        g = geometry(frame, config['floating_point_ulps'])
        logging.info('%s: count causal clean runs and terminal observations', symbol)
        events = sequences(g, symbol)
        logging.info('%s: measure separate real-price markouts', symbol)
        forward = forward_behavior(frame, events, config['forward_horizons_minutes'])
        for name, df in [('geometry', g), ('sequences', events), ('forward', forward)]:
            path = out / f'{symbol}_{name}.parquet'
            df.to_parquet(path, index=False, compression='zstd')
            artifacts[path.relative_to(ROOT).as_posix()] = digest(path)
        logging.info('%s: distributions by year and chronological partition', symbol)
        report = dict(symbol=symbol, source='Binance Vision USD-M perpetual', source_manifest=meta_path.relative_to(ROOT).as_posix(),
                      source_sha256=meta['processed_sha256'], quality=quality, source_quality=meta['quality'],
                      trailing_missing_minutes=tail, excluded_before_research=excluded,
                      descriptive=summaries(g, events, forward, config),
                      unavailable_metrics={k: dict(value=None, reason='Original outcome/Doji definitions unresolved') for k in
                          ['original_pattern_count', 'outcome_sample_size', 'observed_win_proportion', 'win_rate_confidence_interval', 'independent_observations', 'p_value_075']},
                      unresolved_definitions={k: None for k in UNRESOLVED})
        save_json(out / f'{symbol}.json', report)
        result['markets'].append(report)
        del frame, g, events, forward
        gc.collect()
    save_json(out / 'summary.json', result)
    render_reports(ROOT, result)
    code = list((ROOT / 'src/ha_research').glob('*.py')) + list((ROOT / 'scripts').glob('*ha*.py'))
    code += list((ROOT / 'tests').glob('test_ha*.py')) + list((ROOT / 'docs').glob('HA_*.md'))
    code += [config_path, ROOT / config['base_config'], ROOT / 'src/data_validation/validator.py']
    save_json(out / 'execution.json', dict(completed_at=datetime.now(timezone.utc).isoformat(), network_requests=0,
               python=platform.python_version(), dependencies={k: importlib.metadata.version(k) for k in ['numpy','pandas','pyarrow','duckdb','pytest','playwright']},
               source_hashes={p.relative_to(ROOT).as_posix(): digest(p) for p in code}, artifacts=artifacts))
    subprocess.run([sys.executable, str(ROOT / 'scripts/qa_ha_descriptive.py')], cwd=ROOT, check=True)
    logging.info('Finished all three instruments; original-method win rates remain unavailable')


if __name__ == '__main__':
    main()
