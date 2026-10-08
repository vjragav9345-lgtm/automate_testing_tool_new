"""TEST-ONLY: the live log window shows ONE line per step (Running -> result, in place), no "sub-lines", no
repeated lines, reason lines under WARNING / FAILED / NOT RUN; the sub-line information is in the step Details.
Drives the REAL dashboard (own Flask process) and READS THE REAL PAGE (templates/live_log.html) in a browser."""
import json, subprocess, sys, time, urllib.request
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
from phase4_fixture_server import FixtureServer
from storage import repository

PORT = 5079
fails = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name, extra)
    if not ok: fails.append(name)
def post(path, body):
    r = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=60))
def lp(**kw):
    b = {"id": None, "tag": None, "text": "", "element_text": "", "aria_label": None, "accessible_name": "", "attributes": {}}
    b.update(kw); return b

srv = subprocess.Popen([sys.executable, "-c", f"import app; app.app.run(host='127.0.0.1', port={PORT}, threaded=True)"],
                       cwd=BASE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
made = []
try:
    for _ in range(60):
        try: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/recordings", timeout=3); break
        except Exception: time.sleep(0.5)
    with FixtureServer() as fx:
        def nav(u): return {"action_type": "navigate", "page_url": u, "locator_profile": {}, "value": None}
        scenarios = {}
        u = fx.url("rv_mega_hover.html")
        scenarios["pass"] = (u, [nav(u),
            {"action_type": "hover", "page_url": u, "value": None, "locator_profile": lp(id="feat", tag="a", text="Features", element_text="Features", attributes={"id": "feat", "href": "#"})},
            {"action_type": "click", "page_url": u, "value": None, "locator_profile": lp(id="pa", tag="a", text="Pro Analytics", element_text="Pro Analytics", attributes={"id": "pa"})}])
        u2 = fx.url("gap_page.html")
        scenarios["fail"] = (u2, [nav(u2),
            {"action_type": "click", "page_url": u2, "value": None, "locator_profile": lp(id="nope-1", tag="button", text="Missing thing", element_text="Missing thing", accessible_name="Missing thing", attributes={"id": "nope-1"})},
            {"action_type": "click", "page_url": u2, "value": None, "locator_profile": lp(id="nope-2", tag="button", text="Also missing", element_text="Also missing", attributes={"id": "nope-2"})}])
        u3 = fx.url("pop_closed_cookie.html")
        FP = {"kind": "dialog", "tag": "div", "id": "pop", "role": "dialog", "aria_label": "Video", "css_path": "div#pop", "text_hint": "Video player"}
        scenarios["warn"] = (u3, [nav(u3),
            {"action_type": "click", "page_url": u3, "value": None, "popup_container": FP, "locator_profile": lp(id="x", tag="button", title="Close", attributes={"title": "Close"})}])
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            for name, (start, actions) in scenarios.items():
                tc = {"name": f"lld_{name}", "start_url": start, "actions": actions}
                path = repository.save_recording(tc); made.append(path)
                st = post("/api/test/run/start", {"qa_url": start, "recording_path": f"storage/recordings/{path.name}"})
                pg = b.new_page(viewport={"width": 1100, "height": 800})
                pg.goto(f"http://127.0.0.1:{PORT}/logs?run_id={st['run_id']}")
                pg.wait_for_selector("#summaryBanner", state="visible", timeout=180000) if pg.locator("#summaryBanner").count() else pg.wait_for_timeout(1000)
                pg.wait_for_function("() => { const s = document.getElementById('summaryBanner'); return s && s.style.display === 'block'; }", timeout=180000)
                pg.wait_for_timeout(600)
                lines = pg.eval_on_selector_all("#logLines .log-line", "els => els.map(e => e.innerText.trim())")
                extras = pg.eval_on_selector_all("#logLines > div:not(.log-line)", "els => els.map(e => e.innerText.trim().slice(0, 160))")
                print(f"--- {name}: {len(lines)} step lines, {len(extras)} reason/extra lines")
                for l in lines: print("    ", l[:150].replace("\n", " "))
                for e in extras: print("     +", e.replace("\n", " "))
                n = len(actions)
                check(f"{name}: exactly one line per step", len(lines) == n, f"{len(lines)}/{n}")
                check(f"{name}: no sub-lines", not any("↳" in l for l in lines + extras) and not any(l.startswith("[") and "Clicking" in l for l in lines))
                check(f"{name}: no repeated lines", len(set(lines)) == len(lines))
                check(f"{name}: steps in order, none left Running",
                      [int(l.split("Step ")[1].split(":")[0]) for l in lines if "Step " in l] == list(range(1, n + 1)) and not any("Running" in l for l in lines))
                if name == "pass": check("pass: every step PASS", all("PASS" in l for l in lines))
                if name == "fail":
                    check("fail: step 2 FAILED with a reason line, step 3 NOT RUN with a reason line",
                          "FAILED" in lines[1] and "NOT RUN" in lines[2] and len(extras) >= 2 and all(len(e) > 15 for e in extras[:2]))
                if name == "warn":
                    check("warn: WARNING with its reason line", "WARNING" in lines[1] and any("already closed" in e for e in extras))
                # the step Details (report) keep what AutoFlow did
                rd = BASE / st["run_dir"]
                for _ in range(40):
                    if (rd / "report.html").is_file(): break
                    time.sleep(0.25)
                html = (rd / "report.html").read_text(encoding="utf-8") if (rd / "report.html").is_file() else ""
                if name == "warn":
                    check("warn: report Details keep the sub-line information", "What AutoFlow did" in html, "")
                if name == "pass":
                    rj = json.loads((rd / "report.json").read_text(encoding="utf-8"))
                    check("pass: report.json steps (View Last Log) keep the sub-line information",
                          any("What AutoFlow did" in (s.get("technical") or "") for s in rj["steps"]))
                pg.close()
            b.close()
finally:
    srv.terminate()
    for pth in made: Path(pth).unlink(missing_ok=True)
print("\nLIVE LOG DISPLAY:", "ALL PASS" if not fails else f"FAILED {fails}")
sys.exit(1 if fails else 0)
