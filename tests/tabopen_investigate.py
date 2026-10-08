"""TEST-ONLY: STEP 1 investigation for the tab_open/tab_close task. Replays the EXACT reported
recording (session_20260929_112139_edited) with the REAL, unmodified generator, instrumenting
len(context.pages) and each step's own resolved-page identity before/after, to see empirically
what tab_open/tab_close actually do (or don't do) given this recording's page_id values."""
import importlib.util
import json
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from generator.script_generator import generate_script

REC = "storage/recordings/edited/session_20260929_112139_edited.json"

tc = json.loads(Path(REC).read_text(encoding="utf-8"))
d = Path("tests/_probe_out/tabopen_investigate")
d.mkdir(parents=True, exist_ok=True)
sp = generate_script(tc, out_name="tabopen_investigate_script.py", output_dir=d)
print("generated:", sp)

spec = importlib.util.spec_from_file_location("tabopen_investigate_mod", sp)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

start_url = tc.get("start_url")
t0 = time.monotonic()
res = mod.run(start_url, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
dt = time.monotonic() - t0
print(f"\n=== total wall time {dt:.1f}s ===")
for s in res["steps"]:
    print(s["index"], s["action_type"], "success=" + str(s["success"]), "not_run=" + str(s.get("not_run")), repr(s.get("error"))[:160])
print("status:", res["status"], "|", res.get("message"))
