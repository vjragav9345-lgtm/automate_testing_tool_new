"""TEST-ONLY: Phase A verification for the two new tab_close guards.
Case 1: a single-page recording whose only step (besides navigate) is tab_close on page_id=0 ->
must FAIL "Cannot close the last tab", and must NOT actually close the browser.
Case 2: a real popup opened and closed once (page_id=1), then a SECOND tab_close also targeting
page_id=1 (already closed) -> must FAIL with an "already closed" reason, not silently PASS."""
import importlib.util
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from generator.script_generator import generate_script

URL = "https://the-internet.herokuapp.com/windows"


def replay(tc, label):
    d = Path(f"tests/_probe_out/tabclose_guards_{label}")
    d.mkdir(parents=True, exist_ok=True)
    sp = generate_script(tc, out_name=f"tabclose_guards_{label}_script.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(f"tabclose_guards_{label}_mod", sp)
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


# Case 1: last-tab guard
tc1 = {
    "name": "case1_last_tab", "start_url": URL,
    "actions": [
        {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": URL, "page_id": 0},
        {"action_type": "tab_close", "value": None, "locator_profile": None, "bounding_box": None,
         "page_url": URL, "page_id": 0},
    ],
}
res1 = replay(tc1, "case1_last_tab")
assert res1["steps"][1]["success"] is False and "Cannot close the last tab" in (res1["steps"][1].get("error") or ""), \
    "expected step 2 to FAIL with 'Cannot close the last tab'"
print("PASS: last-tab guard correctly failed instead of closing the browser")

# Case 2: already-closed guard
tc2 = {
    "name": "case2_already_closed", "start_url": URL,
    "actions": [
        {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": URL, "page_id": 0},
        {"action_type": "click", "value": None, "page_url": URL, "page_id": 0,
         "locator_profile": {"id": None, "css_path": "a[target='_blank']", "xpath": "//a[@target='_blank']",
                              "text": "Click Here", "role": None, "tag": "a", "attributes": {}}},
        {"action_type": "tab_open", "value": None, "locator_profile": None, "bounding_box": None,
         "page_url": URL, "page_id": 1},
        {"action_type": "tab_close", "value": None, "locator_profile": None, "bounding_box": None,
         "page_url": URL, "page_id": 1, "remaining_page_id": 0},
        {"action_type": "tab_close", "value": None, "locator_profile": None, "bounding_box": None,
         "page_url": URL, "page_id": 1, "remaining_page_id": 0},
    ],
}
res2 = replay(tc2, "case2_already_closed")
assert res2["steps"][3]["success"] is True, "expected the FIRST tab_close (real tab) to PASS"
assert res2["steps"][4]["success"] is False and "already closed" in (res2["steps"][4].get("error") or ""), \
    "expected the SECOND tab_close (already-closed page_id=1) to FAIL with an 'already closed' reason"
print("PASS: already-closed guard correctly failed the second, redundant tab_close instead of silently passing")
