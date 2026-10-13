"""TEST-ONLY: replay saved recording(s) through the REAL dashboard and READ the REAL live log page:
one line per step, Running -> result in place, no sub-lines, no repeats.   python tests/livelog_replay.py name [name ...]"""
import json, subprocess, sys, time, urllib.request
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
from playwright.sync_api import sync_playwright
PORT = 5082
srv = subprocess.Popen([sys.executable, "-c", f"import app; app.app.run(host='127.0.0.1', port={PORT}, threaded=True)"], cwd=BASE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
bad = []
try:
    for _ in range(60):
        try: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/recordings", timeout=3); break
        except Exception: time.sleep(0.5)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        for name in sys.argv[1:]:
            rel = f"storage/recordings/{name}.json"
            if not (BASE / rel).is_file(): rel = f"storage/recordings/edited/{name}.json"
            rec = json.load(open(BASE / rel, encoding="utf-8")); n = len(rec["actions"])
            req = urllib.request.Request(f"http://127.0.0.1:{PORT}/api/test/run/start", json.dumps({"qa_url": rec["start_url"], "recording_path": rel}).encode(), {"Content-Type": "application/json"})
            st = json.load(urllib.request.urlopen(req, timeout=60))
            pg = b.new_page(viewport={"width": 1100, "height": 900}); t0 = time.time()
            pg.goto(f"http://127.0.0.1:{PORT}/logs?run_id={st['run_id']}")
            pg.wait_for_function("() => { const s = document.getElementById('summaryBanner'); return s && s.style.display === 'block'; }", timeout=600000)
            pg.wait_for_timeout(500)
            lines = pg.eval_on_selector_all("#logLines .log-line", "els => els.map(e => e.innerText.trim())")
            extras = pg.eval_on_selector_all("#logLines > div:not(.log-line)", "els => els.map(e => e.innerText.trim().slice(0, 130))")
            summ = pg.inner_text("#summaryBanner").replace("\n", " ")[:200]
            order = [int(l.split("Step ")[1].split(":")[0]) for l in lines if "Step " in l]
            ok = len(lines) == n and order == list(range(1, n + 1)) and len(set(lines)) == len(lines) and not any("↳" in x for x in lines + extras) and not any("Running" in l for l in lines)
            print(f"=== {name}: {len(lines)}/{n} step lines, {len(extras)} reason lines, {time.time()-t0:.0f}s -> {'OK' if ok else 'PROBLEM'}")
            for l in lines: print("   ", l[:140].replace("\n", " "))
            for e in extras: print("    +", e.replace("\n", " "))
            print("   SUMMARY:", summ)
            if not ok: bad.append(name)
            pg.close()
        b.close()
finally:
    srv.terminate()
print("LIVELOG REPLAY", "ALL OK" if not bad else f"PROBLEMS {bad}")
