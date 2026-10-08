"""TEST-ONLY: what does the live DOM look like for the recorded 'Seekbuylove' checkbox target, before/after a click?"""
import json
from playwright.sync_api import sync_playwright
XP = "//label[normalize-space(text())='Seekbuylove']/div"
JS = """e => { const lab = e.closest('label'); const inp = lab && lab.querySelector('input');
  const chain=[]; let n=e; for (let i=0;i<4&&n;i++){ chain.push({tag:n.tagName, cls:(n.className||'').toString().slice(0,60), ariaChecked:n.getAttribute('aria-checked'), checked:('checked' in n)?n.checked:undefined}); n=n.parentElement; }
  return {label: lab ? lab.outerHTML.slice(0,400) : null, input: inp ? {type: inp.type, checked: inp.checked, ariaChecked: inp.getAttribute('aria-checked')} : null, chain}; }"""
with sync_playwright() as p:
    b = p.chromium.launch(headless=False); pg = b.new_context(viewport={"width": 1280, "height": 900}).new_page()
    pg.goto("https://www.myntra.com/men-tshirts", wait_until="domcontentloaded"); pg.wait_for_timeout(4000)
    loc = pg.locator("xpath=" + XP)
    print("matches:", loc.count())
    el = loc.first; el.scroll_into_view_if_needed()
    print("BEFORE", json.dumps(el.evaluate(JS), ensure_ascii=False)); print("url before:", pg.url)
    el.click(force=True)
    for t in (300, 700, 1500, 2500):
        pg.wait_for_timeout(t - (0 if t == 300 else 0))
        print(f"AFTER~{t}ms url:", pg.url, "| state:", json.dumps(el.evaluate(JS), ensure_ascii=False)[:600])
    b.close()
