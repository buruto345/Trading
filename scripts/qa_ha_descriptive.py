"""Independent SQL reconciliation and offline browser QA of all four reports."""
import json
from pathlib import Path
import sys

import duckdb
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.ha_research.data import digest, save_json


def main():
    out = ROOT / 'reports/ha_descriptive'
    result = json.loads((out / 'summary.json').read_text(encoding='utf-8'))
    execution = json.loads((out / 'execution.json').read_text(encoding='utf-8'))
    for name, expected in execution['artifacts'].items():
        assert digest(ROOT / name) == expected
    con, evidence = duckdb.connect(), []
    for m in result['markets']:
        symbol = m['symbol']
        for view in ['geometry', 'sequences', 'forward']:
            con.read_parquet(str(out / f'{symbol}_{view}.parquet')).create_view(view, replace=True)
        for part, summary in [('all', m['descriptive']['overall']), *m['descriptive']['partitions'].items()]:
            predicate = 'TRUE' if part == 'all' else f"partition='{part}'"
            values = con.execute(f'''SELECT count(*), count(*) FILTER(WHERE ready),
                count(*) FILTER(WHERE ready AND no_upper_wick), count(*) FILTER(WHERE ready AND no_lower_wick),
                count(*) FILTER(WHERE clean_direction=1), count(*) FILTER(WHERE clean_direction=-1)
                FROM geometry WHERE {predicate}''').fetchall()[0]
            c = summary['candles']
            assert list(values) == [c['candles'], c['ready_candles'], c['counts']['no_upper_wick'], c['counts']['no_lower_wick'],
                                    c['counts']['bullish_clean_component'], c['counts']['bearish_clean_component']]
            count, lengths, matching, cohort = con.execute(f'''SELECT count(*), coalesce(sum(pullback_count),0),
                count(*) FILTER(WHERE terminal_color_match),
                count(*) FILTER(WHERE terminal_color_match AND impulse_count>0)
                FROM sequences WHERE {predicate}''').fetchall()[0]
            s = summary['sequences']
            assert count == s['clean_runs'] and matching == s['same_color_terminals'] and cohort == s['with_impulse_same_color']
            assert lengths == c['counts']['bullish_clean_component'] + c['counts']['bearish_clean_component']
            for f in summary['forward']:
                size, observed, mean = con.execute(f'''SELECT count(*), count(*) FILTER(WHERE status='observed'), avg(directional_return_bps)
                     FROM forward WHERE {predicate} AND horizon_minutes=?''', [f['horizon_minutes']]).fetchall()[0]
                assert size == f['sample_size'] == cohort
                assert observed == f['observed']
                if observed:
                    assert abs(mean - f['directional_return_bps']['mean']) < 1e-8
        bad = con.execute('''SELECT count(*) FROM sequences WHERE
            pullback_count != end_index-start_index+1 OR
            (status='observed_two_wick_terminal' AND
             (terminal_index<=end_index OR intermediate_count!=terminal_index-end_index-1 OR
              available_at!=terminal_time+INTERVAL 1 MINUTE))''').fetchall()[0][0]
        assert bad == 0
        evidence.append(dict(symbol=symbol, status='passed', checks=['partition counts', 'clean candle/run reconciliation', 'forward counts and means', 'causal timestamps']))
    original = json.loads((out / 'preservation_before.json').read_text(encoding='utf-8'))
    changed = [p for p, sha in original.items() if not (ROOT / p).exists() or digest(ROOT / p) != sha]
    assert not changed, changed
    save_json(out / 'preservation_verified.json', dict(status='passed', checked_files=len(original), changed=changed))
    save_json(out / 'audit.json', dict(status='passed', markets=evidence))
    save_json(out / 'browser_qa.json', dict(status='running', offline=True))
    errors, remote, views = [], [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome', headless=True)
        context = browser.new_context(offline=True)
        for name in [m['symbol'] for m in result['markets']] + ['comparison']:
            page = context.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('request', lambda r: remote.append(r.url) if r.url.startswith(('https:', 'http:')) else None)
            page.goto((out / f'{name}.html').as_uri())
            assert 'chưa thể kiểm chứng' in page.locator('#status').inner_text()
            if name != 'comparison':
                m = next(m for m in result['markets'] if m['symbol'] == name)
                assert f"{m['quality']['validated_candles']:,}" in page.locator('#valid-count').inner_text()
                assert f"{m['descriptive']['overall']['sequences']['clean_runs']:,}" in page.locator('#run-count').inner_text()
                page.locator('summary').click()
            for width, height in [(1440, 900), (390, 844)]:
                page.set_viewport_size(dict(width=width, height=height))
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                page.screenshot(path=str(out / f'{name}_{width}.png'), full_page=True)
                views.append(dict(report=name, width=width, overflow=False))
            for href in page.locator('a').evaluate_all('(els)=>els.map(e=>e.getAttribute("href"))'):
                assert (out / href).exists(), href
            page.close()
        browser.close()
    assert not errors and not remote
    save_json(out / 'browser_qa.json', dict(status='passed', offline=True, views=views, errors=errors, remote_requests=remote))
    print(json.dumps(dict(audit='passed', preservation_files=len(original), reports=4, browser='passed')))


if __name__ == '__main__':
    main()
