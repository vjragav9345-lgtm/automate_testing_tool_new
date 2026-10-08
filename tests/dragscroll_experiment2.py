"""TEST-ONLY: what happens AFTER mouseup? logs label + URL rf param over time."""
import json, sys, time
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl
from playwright.sync_api import sync_playwright

rec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
act = rec["actions"][int(sys.argv[2]) - 1]
url = act["page_url"]; sel = act["source_target"]["id"]; so = act["start_offset"]; path = act["path"]; delta = act["end_delta"]

def label(page):
    return page.evaluate("""(sel) => { const t = document.querySelector(sel); if(!t) return 'THUMB-GONE'; let n = t; for (let i=0;i<6&&n;i++){ const s=(n.innerText||'').trim(); if (s && /\d/.test(s) && s.length<120) return s; n=n.parentElement;} return null; }""", sel)
def rf(page):
    return dict(parse_qsl(urlsplit(page.url).query)).get("rf")

with sync_playwright() as p:
    b = p.chromium.launch(headless=False)
    page = b.new_context(viewport={"width":1280,"height":720}).new_page()
    page.goto(url, wait_until="domcontentloaded"); page.wait_for_selector(sel, timeout=30000); page.wait_for_timeout(2500)
    box = page.locator(sel).bounding_box(); sx, sy = box["x"]+so["x"], box["y"]+so["y"]
    print("before", label(page), "rf=", rf(page))
    page.mouse.move(sx, sy); page.mouse.down()
    for pt in path: page.mouse.move(box["x"]+pt["dx"], box["y"]+pt["dy"], steps=1)
    page.mouse.move(sx+delta["dx"], sy+delta["dy"], steps=1)
    print("mouse still down:", label(page), "rf=", rf(page))
    page.mouse.up(); t0 = time.time()
    for ms in (0, 50, 100, 200, 350, 500, 800, 1200, 2000, 4000):
        while (time.time()-t0)*1000 < ms: time.sleep(0.005)
        print(f"+{ms:5d}ms after mouseup: label={label(page)!r:20} rf={rf(page)!r}")
    b.close()
