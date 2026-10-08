"""TEST-ONLY: VERIFY items 3 and 4 - live sites (not local fixtures), via the real generated script."""
import importlib.util, sys, tempfile
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from generator.script_generator import generate_script
from phase4_test_helpers import step_lp

def run_validate(url, xpath, expected_state, label):
    tc = {"name": "vl_" + label, "start_url": url, "actions": [
        {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": url},
        {"action_type": "validate_checked", "value": None, "page_url": url, "expected_state": expected_state,
         "locator_profile": step_lp(id_=None, text=None, css_path=None, tag="input", xpath=xpath)},
    ]}
    d = Path(tempfile.mkdtemp())
    sp = generate_script(tc, out_name=f"vl_{label}.py", output_dir=d)
    spec = importlib.util.spec_from_file_location("vl_" + label, sp)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    res = mod.run(url, output_json_path=d / "r.json", screenshot_dir=d / "s", headless=True)
    step = res["steps"][1]
    return step.get("success"), step.get("error")

print("=== VERIFY item 3: native checkbox site ===")
url = "https://the-internet.herokuapp.com/checkboxes"
ok1, err1 = run_validate(url, "(//form[@id='checkboxes']//input)[1]", "unchecked", "c1")
print("checkbox 1 (unchecked):", "PASS" if ok1 else f"FAIL {err1}")
assert ok1
ok2, err2 = run_validate(url, "(//form[@id='checkboxes']//input)[2]", "checked", "c2")
print("checkbox 2 (checked):", "PASS" if ok2 else f"FAIL {err2}")
assert ok2

print("\n=== VERIFY item 4: another site with a custom/hidden-input checkbox ===")
url2 = "https://jqueryui.com/checkboxradio/"
ok3, err3 = run_validate(url2, "//label[@for='checkbox-1']", "unchecked", "jq1")
print("jQuery UI checkboxradio demo, label for hidden native input (unchecked):", "PASS" if ok3 else f"FAIL {err3}")
assert ok3
print("\nPASS: both live-site checks confirmed")
