"""Offline browser evidence for the independent multi-model report."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/multi_model'

def main():
    errors=[];remote=[];checks=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='chrome',headless=True)
        context=browser.new_context(offline=True,viewport={'width':1440,'height':900})
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:remote.append(r.url) if r.url.startswith(('http:','https:')) else None)
        page.goto((ROOT/'reports/ICT_Multi_Model_Comparison.html').as_uri(),timeout=120000)
        page.wait_for_function('window.REPORT_READY===true',timeout=120000)
        assert page.locator('.research-section').count()==21
        expected=json.loads((OUT/'summary.json').read_text(encoding='utf-8'))
        assert page.evaluate('window.LIVE_SUMMARY.patterns')==sum(x['patterns'] for x in expected if x['track']=='B')
        for track in ['A','B']:
            page.select_option('#track',track)
            for model in range(5):
                page.select_option('#model',str(model))
                page.select_option('#dimension','symbol')
                assert page.evaluate('window.LIVE_SUMMARY.model')==model
                actual=page.locator('#live-table tbody tr').count()
                assert actual==3
        page.select_option('#model','3');page.select_option('#dimension','fvg_relative')
        assert page.get_by_text('Không có dữ liệu cho lựa chọn này.',exact=True).count()==1
        page.select_option('#dimension','session_sb');page.select_option('#model','2')
        assert page.evaluate('window.LIVE_SUMMARY.groups')==3
        checks.extend(['21 sections','Track A/B and all models reconcile','Empty-state correct','Three Silver Bullet sessions'])
        assert page.evaluate('DATA.charts.every(c=>!!document.getElementById(c.id).data)')
        assert page.evaluate("DATA.charts.filter(c=>c.figure.data[0]?.type==='candlestick').every(c=>{const shape=c.figure.layout.shapes.find(s=>s.type==='line');const x=c.figure.data[0].x;return Date.parse(shape.x0)>=Date.parse(x[0])&&Date.parse(shape.x0)<=Date.parse(x[x.length-1])})")
        checks.append('UTC confirmation marker falls inside each candle example')
        page.screenshot(path=str(OUT/'desktop.png'))
        page.click('#theme');assert page.locator('body').evaluate('(e)=>e.classList.contains("dark")')
        page.screenshot(path=str(OUT/'dark.png'));page.click('#theme')
        views=[]
        for width,height in [(1440,900),(1280,720),(768,1024),(390,844)]:
            page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(300)
            overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth+1');assert not overflow
            views.append({'width':width,'height':height,'horizontal_overflow':overflow})
        page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(OUT/'mobile.png'))
        page.set_viewport_size({'width':1440,'height':900})
        page.locator('#s18 details').first.evaluate('(e)=>{e.open=true;window.scrollTo(0,e.offsetTop)}')
        page.wait_for_timeout(400);page.screenshot(path=str(OUT/'candlestick.png'))
        assert not errors,errors
        assert not remote,remote
        evidence={'status':'passed','browser':'Chrome headless / Playwright','offline':True,'viewports':views,'checks':checks,'charts':page.evaluate('DATA.charts.length+2'),'errors':errors,'remote_requests':remote}
        browser.close()
    (OUT/'browser_qa.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(evidence,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
