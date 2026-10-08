"""TEST-ONLY: where do far-away mid-drag mousemove samples come from? Logs isTrusted etc."""
import random, sys, json
from playwright.sync_api import sync_playwright
random.seed(7)
JS = """
(() => {
  window.__mm = []; let last = null; let down = false;
  document.addEventListener('mousedown', e => { down = true; last = [e.clientX, e.clientY]; window.__mm.push(['DOWN', e.isTrusted, e.clientX, e.clientY, Math.round(performance.now())]); }, true);
  document.addEventListener('mouseup', e => { down = false; window.__mm.push(['UP', e.isTrusted, e.clientX, e.clientY, Math.round(performance.now())]); }, true);
  document.addEventListener('mousemove', e => {
    if (!down) return;
    const j = last ? Math.hypot(e.clientX-last[0], e.clientY-last[1]) : 0;
    if (j > 150) window.__mm.push(['JUMP', e.isTrusted, e.clientX, e.clientY, Math.round(performance.now()), Math.round(j), e.movementX, e.movementY, e.screenX, e.screenY]);
    last = [e.clientX, e.clientY];
  }, true);
})();
"""
with sync_playwright() as p:
    b = p.chromium.launch(headless=False)
    ctx = b.new_context(viewport={'width':1280,'height':720}); ctx.add_init_script(JS)
    pg = ctx.new_page(); pg.goto('https://refreshless.com/nouislider/examples/', wait_until='domcontentloaded'); pg.wait_for_timeout(2500)
    targets = pg.locator('.noUi-target'); total = targets.count(); jumps = []; ndrag = 0
    for k in range(60):
        s = targets.nth(k % total); hs = s.locator('.noUi-handle'); hc = hs.count()
        if not hc: continue
        h = hs.nth(random.randrange(hc))
        if not h.is_visible():
            continue
        for _ in range(10):
            box = h.bounding_box()
            if box and 120 < box['y'] < 560: break
            if not box: break
            pg.mouse.move(700, 360); pg.mouse.wheel(0, max(-900, min(900, int(box['y'] - 340)))); pg.wait_for_timeout(500)
        box = h.bounding_box()
        if not box: continue
        x0, y0 = box['x']+box['width']/2, box['y']+box['height']/2
        dx = random.choice([-1,1]) * random.randint(30, 90)
        pg.evaluate("window.__mm = []")
        pg.mouse.move(x0, y0, steps=8); pg.wait_for_timeout(150); pg.mouse.down(); pg.wait_for_timeout(180)
        for i in range(1, 15):
            pg.mouse.move(x0 + dx*i/14, y0 + random.uniform(-1.5, 1.5)); pg.wait_for_timeout(40)
        pg.mouse.up(); pg.wait_for_timeout(300); ndrag += 1
        for ev in pg.evaluate("window.__mm"):
            if ev[0] == 'JUMP': jumps.append((k, ev))
    print('drags performed', ndrag, ' jump events', len(jumps))
    for k, ev in jumps: print(' drag#', k, ev)
    b.close()
