"""TEST-ONLY: root-cause check for VERIFY items 5/6 failures - replay the SAME two recordings
using the PRE-this-task backup generator (script_generator.py.bak4, saved before any of this
task's edits) to determine whether the failures seen with the current code are pre-existing
(site/network drift) or an actual regression introduced by this task's validator changes."""
import importlib.machinery
import importlib.util
import json
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))


def load_generate_script(path):
    loader = importlib.machinery.SourceFileLoader("gen_baseline", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod.generate_script


def replay_recording(generate_script, rec_path, label):
    tc = json.loads(Path(rec_path).read_text(encoding="utf-8"))
    d = Path(f"tests/_probe_out/verify56_baseline_{label}")
    d.mkdir(parents=True, exist_ok=True)
    sp = generate_script(tc, out_name=f"verify56_baseline_{label}_script.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(f"verify56_baseline_{label}_mod", sp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    start_url = tc.get("start_url") or (tc["actions"][0].get("page_url") if tc.get("actions") else None)
    t0 = time.monotonic()
    try:
        res = mod.run(start_url, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    except Exception as e:
        print(f"\n=== {label} (BASELINE/.bak4) raised: {e!r} ===")
        return None
    dt = time.monotonic() - t0
    n = len(res["steps"])
    passed = sum(1 for s in res["steps"] if s.get("success"))
    print(f"\n=== {label} (BASELINE/.bak4, total wall time {dt:.1f}s) ===")
    for s in res["steps"]:
        print(s["index"], s["action_type"], "success=" + str(s["success"]), "not_run=" + str(s.get("not_run")), repr(s.get("error"))[:100])
    print(f"status: {res['status']} | {passed}/{n} PASS")
    return res


if __name__ == "__main__":
    gen = load_generate_script(BASE / "generator" / "script_generator.py.bak4")
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("both", "5"):
        replay_recording(gen, "storage/recordings/edited/session_20260929_105345_edited.json", "item5_myntra")
    if which in ("both", "6"):
        replay_recording(gen, "storage/recordings/edited/session_20260928_171139_edited.json", "item6_blinkit")
