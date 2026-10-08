"""TEST-ONLY: per-phase regression. Records a simple flow (navigate, click, type, select, scroll)
with the REAL Recorder, then drives the REAL dashboard (own Flask process): replay + live-log
stream, last result (View Last Log), HTML report, Rename, Delete. Prints PASS/FAIL per item."""
import json, subprocess, sys, time, urllib.request
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
from phase4_fixture_server import FixtureServer
from recorder.record_session import Recorder
from storage import repository

PORT = 5077
fails = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name, extra); 
    if not ok: fails.append(name)

def post(path, body):
    r = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(r, timeout=60))
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}")
def get(path):
    return json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=60))

srv = subprocess.Popen([sys.executable, "-c", f"import app; app.app.run(host='127.0.0.1', port={PORT}, threaded=True)"],
                       cwd=BASE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(60):
        try: get("/api/recordings"); break
        except Exception: time.sleep(0.5)
    with FixtureServer() as fx:
        url = fx.url("reg_form.html")
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True); ctx = b.new_context(viewport={"width": 1000, "height": 700}); pg = ctx.new_page()
            rec = Recorder(pg); rec.install_context_capture(ctx)
            pg.goto(url); rec.start(launch_url=url)
            pg.locator("#go").click(); pg.wait_for_timeout(300)
            pg.locator("#name").click(); pg.keyboard.type("Alice"); pg.keyboard.press("Tab"); pg.wait_for_timeout(300)
            pg.locator("#sel").focus(); pg.keyboard.press("ArrowDown"); pg.keyboard.press("ArrowDown"); pg.keyboard.press("Tab"); pg.wait_for_timeout(300)
            pg.mouse.move(300, 400); pg.mouse.wheel(0, 900); pg.wait_for_timeout(800)
            tc = rec.stop(name="regr_simple_flow", stop_reason="terminal_enter")
            for d in (rec._draft_path, rec._draft_jsonl_path):
                if d: Path(d).unlink(missing_ok=True)
            b.close()
        kinds = [a["action_type"] for a in tc["actions"]]
        print("recorded:", kinds)
        check("record: navigate/click/fill/select/scroll captured", all(k in kinds for k in ("navigate", "click", "select", "scroll")) and any(k in kinds for k in ("fill", "type")))
        path = repository.save_recording(tc)
        rel = f"storage/recordings/{path.name}"
        st = post("/api/test/run/start", {"qa_url": url, "recording_path": rel})
        rid = st.get("run_id"); check("replay started", bool(rid), str(st)[:100])
        events = []; ev = None; t0 = time.monotonic()
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/test/run/stream?run_id={rid}", timeout=300) as resp:
            for raw in resp:
                line = raw.decode("utf-8", "replace").rstrip("\n")
                if line.startswith("event:"): ev = line[6:].strip(); continue
                if line.startswith("data:"):
                    d = json.loads(line[5:]); events.append((round(time.monotonic() - t0, 1), ev, d))
                    if ev in ("summary", "stream_error"): break
        run_t = {}; step_t = {}
        for tt, e, d in events:
            if e == "running": run_t.setdefault(d["index"], tt)
            if e == "step": step_t.setdefault(d["index"], tt)
        check("live log: every step had a Running line before its result",
              all(i in run_t and run_t[i] <= step_t[i] for i in step_t), f"running={sorted(run_t)} steps={sorted(step_t)}")
        check("live log: Running only after the script reported a step",
              all(d.get("started_at") for _, e, d in events if e == "running"))
        steps = [d for _, e, d in events if e == "step"]
        if len(steps) != len(tc["actions"]): print("STEP EVENT ORDER:", [(tt, d["index"]) for tt, e, d in events if e == "step"])
        summ = [d for _, e, d in events if e == "summary"]
        check("live log: every step line arrived", len(steps) == len(tc["actions"]), f"{len(steps)}/{len(tc['actions'])}")
        check("replay: all steps pass", all(s["status"] in ("pass", "warning") for s in steps), str([s["status"] for s in steps]))
        check("summary: PASS", bool(summ) and summ[0].get("status") in ("PASS", "pass"), str(summ[0].get("status") if summ else None))
        lr = get("/api/recordings/last_result?path=" + rel)
        check("View Last Log: last result served", bool(lr) and lr.get("success", True) is not False, str(list(lr)[:6]))
        run_dir = st.get("run_dir")
        rd = (BASE / run_dir) if run_dir and not Path(run_dir).is_absolute() else Path(run_dir or "")
        check("HTML report generated", (rd / "report.html").is_file(), str(rd))
        nm = post("/api/recordings/set_display_name", {"path": rel, "display_name": "Regression flow renamed"})
        check("Rename", nm.get("success") is True and nm.get("display_name") == "Regression flow renamed", str(nm))
        dl = post("/api/recordings/delete", {"path": rel})
        check("Delete", dl.get("success") is True and not path.exists(), str(dl)[:100])
finally:
    srv.terminate()
    Path(BASE / "storage/recordings/regr_simple_flow.json").unlink(missing_ok=True)
print("\nREGRESSION:", "ALL PASS" if not fails else f"FAILED {fails}")
sys.exit(1 if fails else 0)
