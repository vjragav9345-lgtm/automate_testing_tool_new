"""TEST-ONLY: VERIFY items 5 and 6 - plain regression re-replay of two previously-working recordings
after this task's validator changes (validate_element/enabled/visible/text/value now use
poll_until_expected). No code changes, no recording changes - just replay and report pass/fail counts."""
import importlib.util
import json
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from generator.script_generator import generate_script


def replay_recording(rec_path, label):
    tc = json.loads(Path(rec_path).read_text(encoding="utf-8"))
    d = Path(f"tests/_probe_out/verify56_{label}")
    d.mkdir(parents=True, exist_ok=True)
    sp = generate_script(tc, out_name=f"verify56_{label}_script.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(f"verify56_{label}_mod", sp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    start_url = tc.get("start_url") or (tc["actions"][0].get("page_url") if tc.get("actions") else None)
    t0 = time.monotonic()
    res = mod.run(start_url, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    dt = time.monotonic() - t0
    n = len(res["steps"])
    passed = sum(1 for s in res["steps"] if s.get("success"))
    print(f"\n=== {label} (total wall time {dt:.1f}s) ===")
    for s in res["steps"]:
        print(s["index"], s["action_type"], "success=" + str(s["success"]), "not_run=" + str(s.get("not_run")), repr(s.get("error"))[:100])
    print(f"status: {res['status']} | {passed}/{n} PASS")
    return res


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("both", "5"):
        replay_recording("storage/recordings/edited/session_20260929_105345_edited.json", "item5_myntra")
    if which in ("both", "6"):
        replay_recording("storage/recordings/edited/session_20260928_171139_edited.json", "item6_blinkit")
