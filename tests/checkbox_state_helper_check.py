"""TEST-ONLY bounded checks for _resolve_checkbox_state / validate_checked, run through the real generated script
(generate_script + run) against a local fixture with every case the task lists."""
import importlib.util, sys, tempfile
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_fixture_server import FixtureServer
from phase4_test_helpers import step_lp
from generator.script_generator import generate_script

def run_validate(url, xpath, expected_state, tag_hint="div", label="check"):
    tc = {"name": "vc_" + label, "start_url": url, "actions": [
        {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": url},
        {"action_type": "validate_checked", "value": None, "page_url": url, "expected_state": expected_state,
         "locator_profile": step_lp(id_=None, text=None, css_path=None, tag=tag_hint, xpath=xpath)},
    ]}
    d = Path(tempfile.mkdtemp())
    sp = generate_script(tc, out_name=f"vc_{label}.py", output_dir=d)
    spec = importlib.util.spec_from_file_location("vc_" + label, sp)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    res = mod.run(url, output_json_path=d / "r.json", screenshot_dir=d / "s", headless=True)
    step = res["steps"][1]
    return step.get("success"), step.get("error")

with FixtureServer() as srv:
    url = srv.url("checkbox_state_fixture.html")
    cases = [
        ("custom checkbox, picked DIV, expect checked -> PASS", "//div[@class='tick' and ../@id='custom-checked']", "checked", True),
        ("custom checkbox, picked LABEL, expect checked -> PASS", "//*[@id='custom-checked']", "checked", True),
        ("custom checkbox, picked DIV, expect unchecked -> PASS (unchecked one)", "//div[@class='tick' and ../@id='custom-unchecked']", "unchecked", True),
        ("custom checkbox, picked DIV, WRONG expectation -> FAIL", "//div[@class='tick' and ../@id='custom-checked']", "unchecked", False),
        ("native checked -> PASS", "//*[@id='native-checked']", "checked", True),
        ("native unchecked -> PASS", "//*[@id='native-unchecked']", "unchecked", True),
        ("aria checked -> PASS", "//*[@id='aria-checked']", "checked", True),
        ("aria unchecked -> PASS", "//*[@id='aria-unchecked']", "unchecked", True),
        ("ambiguous group -> FAIL", "//*[@id='ambiguous-group']", "checked", False),
        ("plain button, no checkbox -> FAIL", "//*[@id='plain-button']", "checked", False),
    ]
    for label, xpath, expected, want_ok in cases:
        ok, err = run_validate(url, xpath, expected, label="c%d" % cases.index((label, xpath, expected, want_ok)))
        print(f"{'OK ' if ok == want_ok else 'BAD'} {label}: got ok={ok} err={err!r}")
        assert ok == want_ok, (label, ok, err)
    print("\nPASS: all checkbox-state cases behave as specified")
