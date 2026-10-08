import json, subprocess, sys, time, urllib.request
from pathlib import Path
BASE = Path("E:/01-10-2026_1030_AM"); sys.path.insert(0, str(BASE)); sys.path.insert(0, str(BASE/"tests"))
from playwright.sync_api import sync_playwright
from phase4_fixture_server import FixtureServer
from storage import repository
mod = sys.argv[1]; PORT = 5081
code = f"""
import {mod} as a
import itertools
orig = a.poll_replay
c = itertools.count()
def bad(run_id):
    r = orig(run_id)
    if r and not r.get('done') and next(c) % 6 == 5:
        r = dict(r); r['steps'] = []; r['live_log'] = []; r['current_step'] = None
    return r
a.poll_replay = bad
a.app.run(host='127.0.0.1', port={PORT}, threaded=True)
"""
srv = subprocess.Popen([sys.executable, "-c", code], cwd=BASE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
made = []
try:
    for _ in range(60):
        try: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/recordings", timeout=3); break
        except Exception: time.sleep(0.5)
    with FixtureServer() as fx:
        u = fx.url("rv_mega_hover.html")
        lp = lambda **k: {**{"id": None, "tag": None, "text": "", "element_text": "", "aria_label": None, "accessible_name": "", "attributes": {}}, **k}
        acts = [{"action_type": "navigate", "page_url": u, "locator_profile": {}, "value": None},
                {"action_type": "hover", "page_url": u, "value": None, "locator_profile": lp(id="feat", tag="a", text="Features", element_text="Features", attributes={"id": "feat", "href": "#"})},
                {"action_type": "click", "page_url": u, "value": None, "locator_profile": lp(id="pa", tag="a", text="Pro Analytics", element_text="Pro Analytics", attributes={"id": "pa"})}] * 1
        acts = acts + [dict(acts[2]) for _ in range(3)]
        tc = {"name": "fault_x", "start_url": u, "actions": acts}
        path = repository.save_recording(tc); made.append(path)
        req = urllib.request.Request(f"http://127.0.0.1:{PORT}/api/test/run/start", json.dumps({"qa_url": u, "recording_path": f"storage/recordings/{path.name}"}).encode(), {"Content-Type": "application/json"})
        st = json.load(urllib.request.urlopen(req, timeout=60))
        n_log = 0; evs = []; ev = None
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/test/run/stream?run_id={st['run_id']}", timeout=300) as resp:
            for raw in resp:
                line = raw.decode("utf-8", "replace").rstrip()
                if line.startswith("event:"): ev = line[6:].strip(); continue
                if line.startswith("data:"):
                    d = json.loads(line[5:]); evs.append((ev, d))
                    if ev == "log": n_log += 1
                    if ev in ("summary", "stream_error"): break
        rj = json.load(open(BASE / st["run_dir"] / "report.json", encoding="utf-8"))
        steps = [d["index"] for e, d in evs if e == "step"]
        print(mod, "log events sent:", n_log, "| entries in the report:", len(rj.get("live_log", [])), "| step events:", len(steps), "unique:", len(set(steps)))
finally:
    srv.terminate()
    for m in made: Path(m).unlink(missing_ok=True)
