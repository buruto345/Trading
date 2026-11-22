"""Executable offline Chrome acceptance; saves evidence and reconciles live filters."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd
from playwright.sync_api import sync_playwright


def main():
    destination=ROOT/'reports/ICT_Quantitative_Research_Report.html'
    results=ROOT/'reports/results'
    frame=pd.read_parquet(results/'simulations.parquet')
    expected=frame.loc[frame.partition.ne('out_of_sample')]
    errors=[];remote=[];checks=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='chrome',headless=True)
        context=browser.new_context(viewport={'width':1440,'height':1000},offline=True,device_scale_factor=1)
        page=context.new_page()
        page.on('pageerror',lambda error: errors.append(str(error)))
        page.on('request',lambda request: remote.append(request.url) if request.url.startswith(('http://','https://')) else None)
        page.goto(destination.as_uri(),wait_until='load',timeout=120000)
        page.wait_for_function('window.REPORT_READY === true',timeout=120000)
        page.wait_for_function("document.querySelector('#live-chart .main-svg') !== null")
        assert page.locator('.research-section').count()==18
        assert page.evaluate('window.LIVE_SUMMARY.n')==len(expected)
        assert page.evaluate('window.LIVE_SUMMARY.w')==int(expected.outcome.eq('win').sum())
        checks.append('Initial development counts match Parquet')
        page.screenshot(path=str(ROOT/'reports/figures/dashboard_desktop.png'),full_page=False)
        page.select_option('#instrument','BTCUSDT');page.select_option('#direction','bullish')
        filtered=expected.loc[expected.symbol.eq('BTCUSDT')&expected.direction.eq('bullish')]
        assert page.evaluate('window.LIVE_SUMMARY.n')==len(filtered)
        assert abs(page.evaluate('window.LIVE_SUMMARY.wr')-filtered.outcome.eq('win').sum()/filtered.outcome.isin(['win','loss']).sum())<1e-12
        checks.append('Instrument + direction filters reconcile')
        page.select_option('#partition','validation')
        filtered=filtered.loc[filtered.partition.eq('validation')]
        assert page.evaluate('window.LIVE_SUMMARY.n')==len(filtered)
        page.fill('#from-date','2099-01-01');page.locator('#from-date').dispatch_event('change')
        assert page.evaluate('window.LIVE_SUMMARY.n')==0
        assert page.evaluate('window.LIVE_SUMMARY.wr') is None
        checks.append('Partition + empty date filter has correct empty state')
        page.click('#reset');assert page.evaluate('window.LIVE_SUMMARY.n')==len(expected)
        page.click('#theme');assert page.locator('body').evaluate('(el)=>el.classList.contains("dark")')
        page.screenshot(path=str(ROOT/'reports/figures/dashboard_dark.png'),full_page=False)
        page.click('#theme')
        # Explicitly render all chart definitions, verify every Plotly container materializes.
        page.evaluate('window.renderAllCharts()')
        page.wait_for_function('window.RESEARCH_CHARTS.every(c=>document.getElementById(c.id).data)',timeout=120000)
        checks.append(f"All {page.evaluate('window.RESEARCH_CHARTS.length')} embedded charts render offline")
        page.locator('#s2').evaluate('(el)=>window.scrollTo(0,el.offsetTop)')
        page.screenshot(path=str(ROOT/'reports/figures/model_cases.png'),full_page=False)
        viewports=[]
        for width,height in [(1440,1000),(1280,720),(768,1024),(390,844)]:
            page.set_viewport_size({'width':width,'height':height})
            page.evaluate('window.dispatchEvent(new Event("resize"))')
            page.wait_for_timeout(350)
            overflow=page.evaluate('document.documentElement.scrollWidth>window.innerWidth+1')
            assert not overflow,f'Horizontal overflow at {width}'
            viewports.append({'width':width,'height':height,'horizontal_overflow':overflow})
        page.evaluate('window.scrollTo(0,0)')
        page.screenshot(path=str(ROOT/'reports/figures/dashboard_mobile.png'),full_page=False)
        assert not errors,errors
        assert not remote,remote
        browser.close()
    evidence={'status':'passed','url':destination.as_uri(),'network':'offline=True; no HTTP(S) requests','browser':'Chromium via installed Chrome','viewports':viewports,'checks':checks,'page_errors':errors,'remote_requests':remote,'screenshots':['dashboard_desktop.png','dashboard_dark.png','dashboard_mobile.png','model_cases.png']}
    (results/'browser_qa.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(evidence,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
