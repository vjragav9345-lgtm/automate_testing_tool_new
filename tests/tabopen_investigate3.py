"""TEST-ONLY: STEP 1 investigation, part 3. Builds a SYNTHETIC recording that exactly matches the
structural shape of the real bug report's JSON (navigate, click, tab_open[page_id=0],
tab_close[page_id=0], tab_close[page_id=0] - i.e. every step reusing the SAME page_id as the
opener, exactly as the editor's "Add Action" page_id-inheritance bug would produce), against a
REACHABLE test site (myntra.com is unreachable right now - confirmed separately, unrelated to
this task), to empirically observe what tab_open/tab_close actually do with this exact page_id
pattern - including whether the first tab_close really closes the only open page, and what
happens to the second tab_close afterward."""
import importlib.util
import json
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from generator.script_generator import generate_script

URL = "https://the-internet.herokuapp.com/windows"

tc = {
    "name": "tabopen_investigate3",
    "start_url": URL,
    "actions": [
        {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": URL, "page_id": 0},
        {"action_type": "click", "value": None, "page_url": URL, "page_id": 0,
         "locator_profile": {"id": None, "css_path": "a[target='_blank']", "xpath": "//a[@target='_blank']",
                              "text": "Click Here", "role": None, "tag": "a", "attributes": {}}},
        {"action_type": "tab_open", "value": None, "locator_profile": None, "bounding_box": None,
         "page_url": URL, "page_id": 0},
        {"action_type": "tab_close", "value": None, "locator_profile": None, "bounding_box": None,
         "page_url": URL, "page_id": 0},
        {"action_type": "tab_close", "value": None, "locator_profile": None, "bounding_box": None,
         "page_url": URL, "page_id": 0},
    ],
}

d = Path("tests/_probe_out/tabopen_investigate3")
d.mkdir(parents=True, exist_ok=True)
sp = generate_script(tc, out_name="tabopen_investigate3_script.py", output_dir=d)
spec = importlib.util.spec_from_file_location("tabopen_investigate3_mod", sp)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

t0 = time.monotonic()
res = mod.run(URL, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
dt = time.monotonic() - t0
print(f"\n=== total wall time {dt:.1f}s ===")
for s in res["steps"]:
    print(s["index"], s["action_type"], "success=" + str(s["success"]), "not_run=" + str(s.get("not_run")), repr(s.get("error"))[:200])
print("status:", res["status"], "|", res.get("message"))
