"""TEST-ONLY: VERIFY item 5 - a deliberately-nonexistent locator must FAIL with a clear reason, no crash."""
import importlib.util, sys, tempfile
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from generator.script_generator import generate_script
from phase4_fixture_server import FixtureServer
from phase4_test_helpers import step_lp

with FixtureServer() as srv:
    url = srv.url("bug1_wait_fixture.html")
    tc = {"name": "deliberate_fail", "start_url": url, "actions": [
        {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": url},
        {"action_type": "click", "value": None, "page_url": url,
         "locator_profile": step_lp(id_="#does-not-exist-at-all", text="Nonexistent Button", css_path="#does-not-exist-at-all", tag="button"),
         "bounding_box": None},
        {"action_type": "click", "value": None, "page_url": url,
         "locator_profile": step_lp(id_="#ready", text=None, css_path="#ready", tag="input"),
         "bounding_box": None},
    ]}
    d = Path(tempfile.mkdtemp())
    sp = generate_script(tc, out_name="deliberate_fail.py", output_dir=d)
    spec = importlib.util.spec_from_file_location("deliberate_fail_mod", sp)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        res = mod.run(url, output_json_path=d / "r.json", screenshot_dir=d / "s", headless=True)
        crashed = False
    except Exception as e:
        res = None
        crashed = True
        crash_err = e
print("crashed:", crashed)
assert not crashed, f"replay must never raise an unhandled exception, got: {crash_err if crashed else None}"
for s in res["steps"]:
    print(s.get("step"), s.get("action_type"), "PASS" if s.get("success") else "FAIL", (s.get("error") or "")[:150])
assert res["steps"][1]["success"] is False
assert res["steps"][1]["error"] and res["steps"][1]["error"].strip()
assert "NOT RUN" in str(res["steps"][2].get("error"))
print("\nPASS: a genuinely-missing locator fails clearly (no blank reason) and does not crash the app/replay engine")
