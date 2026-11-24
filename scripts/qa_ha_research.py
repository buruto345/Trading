"""Independent count reconciliation, preservation hashes and offline HTML QA."""
import json
from pathlib import Path
import sys

import duckdb
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.ha_research.data import digest, save_json


def main():
    out = ROOT / 'reports/ha_ema'
    result = json.loads((out / 'summary.json').read_text(encoding='utf-8'))
    audit = []
    con = duckdb.connect()
    for market in result['markets']:
        path = ROOT / market['feature_path']
        assert digest(path) == market['feature_sha256']
        con.read_parquet(str(path)).create_view('features', replace=True)
        groups = con.execute('''SELECT partition, count(*), count(*) FILTER (WHERE indicator_ready),
            count(*) FILTER (WHERE indicator_ready AND both_wicks),
            count(*) FILTER (WHERE indicator_ready AND ha_color=1),
            count(*) FILTER (WHERE indicator_ready AND ha_color=-1),
            count(*) FILTER (WHERE indicator_ready AND ha_color=0)
            FROM features GROUP BY partition''').fetchall()
        for part, count, ready, wicks, bull, bear, neutral in groups:
            expected = market['descriptive']['partitions'][part]
            assert [count, ready, wicks, bull, bear, neutral] == [expected[k] for k in
                    ['candles', 'indicator_ready', 'both_wicks', 'bullish', 'bearish', 'neutral']]
        count = con.execute('SELECT count(*) FROM features').fetchall()[0][0]
        assert count + market['pre_research_excluded'] == market['quality']['validated_candles']
        bad = con.execute('''SELECT count(*) FROM features WHERE
            available_at != timestamp + INTERVAL 1 MINUTE OR
            ha_high < greatest(ha_open,ha_close,high) OR ha_low > least(ha_open,ha_close,low) OR
            indicator_ready != (segment_age >= ?)''', [result['config']['warmup_bars']]).fetchall()[0][0]
        assert bad == 0
        audit.append(dict(symbol=market['symbol'], research_candles=count, partition_rows=len(groups), status='passed'))
    assert sum(m['quality']['validated_candles'] for m in result['markets']) == result['total_validated_candles']
    original = json.loads((out / 'preservation_before.json').read_text(encoding='utf-8'))
    changed = [name for name, expected in original.items() if not (ROOT / name).exists() or digest(ROOT / name) != expected]
    assert not changed, changed
    save_json(out / 'preservation_verified.json', dict(status='passed', checked_files=len(original), changed=changed))
    save_json(out / 'audit.json', dict(status='passed', markets=audit, total=result['total_validated_candles']))
    errors, requests, views = [], [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome', headless=True)
        context = browser.new_context(offline=True)
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('request', lambda r: requests.append(r.url) if r.url.startswith(('http:', 'https:')) else None)
        page.goto((ROOT / 'reports/HA_EMA_M1_Research_Report.html').as_uri())
        assert '75%' in page.locator('#status').inner_text()
        assert f"{result['total_validated_candles']:,}" in page.locator('#total').inner_text()
        assert page.locator('table').count() == 2
        assert page.locator('table').first.locator('tbody tr').count() == len(result['markets'])
        for width, height in [(1440, 900), (768, 1024), (390, 844)]:
            page.set_viewport_size(dict(width=width, height=height))
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
            page.screenshot(path=str(out / f'report_{width}.png'), full_page=True)
            views.append(dict(width=width, height=height, overflow=False))
        page.locator('summary').click()
        assert page.locator('details').get_attribute('open') is not None
        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
        browser.close()
    assert not errors and not requests, (errors, requests)
    save_json(out / 'browser_qa.json', dict(status='passed', offline=True, views=views,
              errors=errors, remote_requests=requests, checks=['total and market rows', 'unverified claim banner', 'detail disclosure']))
    print(json.dumps(dict(audit='passed', preservation_files=len(original), browser='passed')))


if __name__ == '__main__':
    main()
