"""TEST-ONLY acceptance: record a manual flow on a live site with the REAL Recorder (the first click is made
BEFORE start(), like a person who acts as soon as the page shows), replay it through the REAL dashboard
(own Flask process) and print the saved steps + the live-log stream with arrival times.

  python tests/acceptance_live.py doc360
  python tests/acceptance_live.py github
Selectors below belong to this TEST only (they drive the browser like a person); the product has none."""
import os, json, re, subprocess, sys, time, urllib.request
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from playwright.sync_api import sync_playwright
from recorder.record_session import Recorder
from storage import repository

PORT = 5078
site = sys.argv[1]

def center(loc):
    bb = loc.bounding_box(); return bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2
def human_click(pg, loc, dwell=250, hover=True):
    if hover:
        try: loc.hover(timeout=5000); pg.wait_for_timeout(dwell)
        except Exception: pass
    loc.click(); pg.wait_for_timeout(700)
def human_hover(pg, loc, dwell=500):
    loc.hover(); pg.wait_for_timeout(dwell)

def two_more_links(pg, selector):
    """click up to two visible links (different targets) - what a person does after the main flow"""
    seen = set()
    for _ in range(2):
        links = pg.locator(selector)
        pick = None
        for i in range(min(links.count(), 12)):
            h = links.nth(i).get_attribute("href")
            from urllib.parse import urlsplit as _us
            if h and h not in seen and not h.startswith("#") and _us(h).path.rstrip("/") != _us(pg.url).path.rstrip("/"):
                pick = (i, h); break
        if not pick: return
        seen.add(pick[1]); human_click(pg, links.nth(pick[0])); pg.wait_for_timeout(3500)

def flow_doc360(pg, rec, url):
    # the person clicks the nav item as soon as the page is usable - BEFORE the recorder's start()
    human_click(pg, pg.locator("header a", has_text="Features").first)
    pg.wait_for_timeout(800)
    rec.start(launch_url=url)
    human_hover(pg, pg.locator("header a", has_text="Features").first, 300)
    human_click(pg, pg.locator("header").get_by_role("link", name="Pro Analytics").locator("visible=true").first)   # link inside the menu
    pg.wait_for_timeout(4000)
    pg.mouse.move(640, 400); pg.mouse.wheel(0, 500); pg.wait_for_timeout(800); pg.mouse.wheel(0, -500); pg.wait_for_timeout(800)   # scroll
    try: human_click(pg, pg.get_by_role("button", name="Allow All").first, 250)                                          # cookie banner
    except Exception: pass
    human_click(pg, pg.locator('a:has-text("Watch video"):visible').first, 150)                                          # popup
    human_click(pg, pg.locator('button[title="Close"]:visible').first, hover=False)                                       # its X
    pg.wait_for_timeout(500)
    human_click(pg, pg.locator('header a[href="#"]', has_text=re.compile(r"^\s*EN\s*$")).locator("visible=true").first)   # language dropdown
    human_click(pg, pg.locator('header a[href="https://document360.com/fr/"]:visible').first); pg.wait_for_timeout(4500)  # pick a language
    two_more_links(pg, 'header a[href^="/"]:visible')                                          # 2 more links

def flow_github(pg, rec, url):
    human_click(pg, pg.locator("header button:visible", has_text="Platform").first)   # nav menu, opened BEFORE start()
    pg.wait_for_timeout(800)
    rec.start(launch_url=url)
    human_click(pg, pg.locator('a[href$="/features/actions"]:visible').first); pg.wait_for_timeout(4500)   # link inside the menu
    pg.mouse.move(640, 400); pg.mouse.wheel(0, 600); pg.wait_for_timeout(800)                                 # scroll
    two_more_links(pg, 'main a[href^="/"]:visible, main a[href^="https://github.com/"]:visible')                # 2 more links

SITES = {"doc360": ("https://www.Document360.com", flow_doc360), "github": ("https://github.com", flow_github)}
url, flow = SITES[site]
with sync_playwright() as p:
    b = p.chromium.launch(headless=True); ctx = b.new_context(viewport={"width": 1280, "height": 800}); pg = ctx.new_page()
    rec = Recorder(pg); rec.install_context_capture(ctx)
    pg.goto(url, wait_until="domcontentloaded")
    try: pg.wait_for_load_state("networkidle", timeout=8000)
    except Exception: pass
    flow(pg, rec, url)
    name = f"acc_{site}"
    tc = rec.stop(name=name, stop_reason="terminal_enter")
    for d in (rec._draft_path, rec._draft_jsonl_path):
        if d: Path(d).unlink(missing_ok=True)
    b.close()
path = repository.save_recording(tc)
print("SAVED STEPS:")
for i, a in enumerate(tc["actions"], 1):
    lp = a.get("locator_profile") or {}
    print(f"  {i}. {a['action_type']:8s} {(lp.get('text') or lp.get('title') or lp.get('aria_label') or '')[:22]!r:26} {a.get('page_url')}")

srv = subprocess.Popen([sys.executable, "-c", f"import app; app.app.run(host='127.0.0.1', port={PORT}, threaded=True)"],
                       cwd=BASE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    def post(path_, body):
        r = urllib.request.Request(f"http://127.0.0.1:{PORT}{path_}", json.dumps(body).encode(), {"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(r, timeout=60))
    for _ in range(60):
        try: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/recordings", timeout=3); break
        except Exception: time.sleep(0.5)
    st = post("/api/test/run/start", {"qa_url": tc["start_url"], "recording_path": f"storage/recordings/{path.name}"})
    t0 = time.monotonic(); ev = None; last = None
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/test/run/stream?run_id={st['run_id']}", timeout=900) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").rstrip("\n")
            if line.startswith("event:"): ev = line[6:].strip(); continue
            if not line.startswith("data:"): continue
            d = json.loads(line[5:]); at = f"[+{time.monotonic()-t0:5.1f}s]"
            if os.environ.get("ACC_RAW"): print("   RAW", ev, str(d)[:90])
            if ev == "running":
                if d["index"] != last:
                    last = d["index"]; print(f"{at} Step {d['index']}: {d.get('element') or d.get('action_type')} - Running...")
            elif ev == "log": print(f"{at}     {d['message']}")
            elif ev == "step":
                from datetime import datetime as _dt
                try: lat = (_dt.now() - _dt.fromisoformat(d["ended_at"])).total_seconds()
                except Exception: lat = -1
                print(f"{at} Step {d['index']} {d['action_type']} - {d['status'].upper()} ({d.get('duration')}s) log_latency={lat:.2f}s")
                if d.get("workarounds"): print("      workarounds:", d["workarounds"])
                if (d.get('reason') or {}).get('plain'): print(f"{at}     {d['reason']['plain']}")
            elif ev == "summary":
                print(f"{at} SUMMARY TEXT: {d.get('plain_summary')}"); print(f"{at} SUMMARY {d.get('status')} total={d['total_steps']} passed={d['passed']} warnings={d['warnings']} failed={d['failed']} not_run={d['skipped']} {d['duration_s']}s"); break
            elif ev == "stream_error": print(at, "STREAM ERROR", d); break
finally:
    srv.terminate()
    import os
    if not os.environ.get('ACC_KEEP'): Path(path).unlink(missing_ok=True)
