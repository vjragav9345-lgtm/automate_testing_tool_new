"""TEST-ONLY: Phase B verification. myntra.com is unreachable in this environment (confirmed
separately, ERR_HTTP2_PROTOCOL_ERROR - the same pre-existing external issue seen throughout this
session, unrelated to this change), so this exercises the EXACT JSON SHAPE the editor's Add Action
would now produce for a manual tab_open/tab_close (manual: true, from_page_id, remaining_page_id,
the "Open Tab (tab N) - URL" name) against a reachable substitute site, proving the replay-side
mechanism end to end.

Test 1: Navigate -> Click -> Open Tab (manual, https://www.google.com) -> Close Tab -> all PASS.
Test 2: same, plus one more Close Tab at the end -> that last step FAILS "Cannot close the last tab".
"""
import importlib.util
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from generator.script_generator import generate_script

URL = "https://the-internet.herokuapp.com/checkboxes"


def replay(tc, label):
    d = Path(f"tests/_probe_out/phaseB_{label}")
    d.mkdir(parents=True, exist_ok=True)
    sp = generate_script(tc, out_name=f"phaseB_{label}_script.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(f"phaseB_{label}_mod", sp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    t0 = time.monotonic()
    res = mod.run(URL, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    dt = time.monotonic() - t0
    print(f"\n=== {label} (total wall time {dt:.1f}s) ===")
    for s in res["steps"]:
        print(s["index"], s["action_type"], "success=" + str(s["success"]), "not_run=" + str(s.get("not_run")), repr(s.get("error"))[:160])
    print("status:", res["status"], "|", res.get("message"))
    return res


CLICK_LP = {"id": None, "css_path": "#checkboxes input[type='checkbox']",
            "xpath": "(//input[@type='checkbox'])[1]",
            "text": None, "role": None, "tag": "input", "attributes": {}}

BASE_ACTIONS = [
    {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": URL, "page_id": 0},
    {"action_type": "click", "value": None, "page_url": URL, "page_id": 0, "locator_profile": CLICK_LP},
    # exactly what the editor's Add Action now produces for a manual tab_open
    {"action_type": "tab_open", "value": None, "locator_profile": None, "bounding_box": None,
     "page_url": "https://www.google.com", "page_id": 1, "manual": True, "from_page_id": 0,
     "name": "Open Tab (tab 1) - https://www.google.com"},
    # exactly what the editor's Add Action now produces for a Close Tab right after it
    {"action_type": "tab_close", "value": None, "locator_profile": None, "bounding_box": None,
     "page_url": "https://www.google.com", "page_id": 1, "remaining_page_id": 0},
]

# Test 1
tc1 = {"name": "phaseB_test1", "start_url": URL, "actions": [dict(a) for a in BASE_ACTIONS]}
res1 = replay(tc1, "test1_open_close")
assert all(s["success"] for s in res1["steps"]), "expected ALL steps to PASS in test 1"
print("PASS: test 1 - Open Tab (manual, google.com) then Close Tab both succeeded, Myntra/original page unaffected")

# Test 2: same plus one more Close Tab at the end (editor would default its page_id to 0,
# the remaining/original page, per the "after a Close Tab, defaults back to the tab still open" rule)
tc2_actions = [dict(a) for a in BASE_ACTIONS]
tc2_actions.append({"action_type": "tab_close", "value": None, "locator_profile": None, "bounding_box": None,
                     "page_url": URL, "page_id": 0})
tc2 = {"name": "phaseB_test2", "start_url": URL, "actions": tc2_actions}
res2 = replay(tc2, "test2_extra_close")
assert all(s["success"] for s in res2["steps"][:-1]), "expected the first 4 steps to PASS in test 2"
last = res2["steps"][-1]
assert last["success"] is False and last.get("error") == "Cannot close the last tab", \
    f"expected the last step to FAIL with 'Cannot close the last tab', got: {last.get('error')!r}"
print("PASS: test 2 - the extra Close Tab correctly FAILED with 'Cannot close the last tab'")
