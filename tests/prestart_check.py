"""TEST-ONLY: ISSUE 2 - actions made BEFORE Recorder.start() (the page is usable as soon as it loads)
are saved, in order, right after the initial Navigate, which is always step 1.
  python tests/prestart_check.py            (fixture)
  python tests/prestart_check.py <url> <trigger css> <item css>   (any live site)"""
import sys
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
from recorder.record_session import Recorder

def center(pg, sel):
    bb = pg.locator(sel).first.bounding_box(); return bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2

def run(url, trig, item, when):
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True); ctx = b.new_context(viewport={"width": 1280, "height": 800}); pg = ctx.new_page()
        rec = Recorder(pg); rec.install_context_capture(ctx)
        pg.goto(url, wait_until="domcontentloaded")
        try: pg.wait_for_load_state("networkidle", timeout=8000)
        except Exception: pass
        x, y = center(pg, trig)
        if when == "before":
            pg.mouse.move(x, y, steps=6); pg.wait_for_timeout(200); pg.mouse.click(x, y); pg.wait_for_timeout(400)
        pg.wait_for_timeout(800)                      # the dashboard's screenshot / settle time
        rec.start(launch_url=url)
        if when == "after":
            pg.mouse.move(x, y, steps=6); pg.wait_for_timeout(200); pg.mouse.click(x, y); pg.wait_for_timeout(400)
        a, c = center(pg, item); pg.mouse.move(a, c, steps=10); pg.wait_for_timeout(300); pg.mouse.click(a, c)
        pg.wait_for_timeout(3000)
        tc = rec.stop(name="_prestart", stop_reason="terminal_enter")
        for d in (rec._draft_path, rec._draft_jsonl_path):
            if d: Path(d).unlink(missing_ok=True)
        b.close()
    return [(a["action_type"], ((a.get("locator_profile") or {}).get("text") or "")[:14]) for a in tc["actions"]]

fails = []
if len(sys.argv) >= 4:
    jobs = [(sys.argv[1], sys.argv[2], sys.argv[3])]
    cleanup = None
else:
    from phase4_fixture_server import FixtureServer
    fx = FixtureServer().__enter__(); jobs = [(fx.url("rv_mega_hover.html"), "#feat", "#pa")]
for url, trig, item in jobs:
    for when in ("before", "after"):
        steps = run(url, trig, item, when)
        print(when, steps)
        ok = len(steps) == 3 and steps[0][0] == "navigate" and steps[1][0] == "click" and steps[2][0] == "click"
        if not ok: fails.append((when, steps))
print("PRESTART CHECK", "PASS" if not fails else f"FAIL {fails}")
sys.exit(1 if fails else 0)
