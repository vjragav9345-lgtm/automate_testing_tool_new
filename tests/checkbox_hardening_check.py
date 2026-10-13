"""TEST-ONLY: item 3's hardening - a SINGLE not_a_checkbox reading during a page re-render must NOT stop the poll
early; the SAME structural result on 2 CONSECUTIVE polls must."""
import importlib.util, sys, tempfile
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_fixture_server import FixtureServer
from phase4_test_helpers import step_lp
from generator.script_generator import generate_script

def run_validate(url, xpath, expected_state, label, tag="div"):
    tc = {"name": "hard_" + label, "start_url": url, "actions": [
        {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": url},
        {"action_type": "validate_checked", "value": None, "page_url": url, "expected_state": expected_state,
         "locator_profile": step_lp(id_=None, text=None, css_path=None, tag=tag, xpath=xpath)},
    ]}
    d = Path(tempfile.mkdtemp())
    sp = generate_script(tc, out_name=f"hard_{label}.py", output_dir=d)
    spec = importlib.util.spec_from_file_location("hard_" + label, sp)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    res = mod.run(url, output_json_path=d / "r.json", screenshot_dir=d / "s", headless=True)
    return res["steps"][1].get("success"), res["steps"][1].get("error")

with FixtureServer() as srv:
    url = srv.url("checkbox_reredner_fixture.html")
    ok, err = run_validate(url, "//div[@id='target']", "checked", "case1")
    print(f"transient not_a_checkbox during re-render, real checkbox appears at ~350ms: ok={ok} err={err!r}")
    assert ok, "a single not_a_checkbox reading during a re-render must NOT stop the poll early"

import time
with FixtureServer() as srv2:
    # a page that is genuinely, permanently not a checkbox (no re-render at
    # all - the SAME structural result every single poll) must still stop
    # early, well before the full STEP_TIME_BUDGET_S timeout, once that
    # result repeats on 2 consecutive polls - the hardening must not turn
    # this into an unbounded wait.
    url2 = srv2.url("checkbox_state_fixture.html")
    t0 = time.monotonic()
    ok2, err2 = run_validate(url2, "//button[@id='plain-button']", "checked", "case2", tag="button")
    dt = time.monotonic() - t0
    print(f"permanently not-a-checkbox target: ok={ok2} err={err2!r} took={dt:.1f}s (must be well under the full step timeout)")
    assert not ok2 and "not a checkbox" in (err2 or "")
    # dt includes _resolve_with_timeout's own existing, untouched per-attempt
    # retry overhead (up to ~3s when a tier initially finds nothing) on top
    # of poll_until_expected's own 200ms polling interval - the meaningful
    # comparison is against STEP_TIME_BUDGET_S (this action's full poll
    # deadline, ~15s): stopping after 2 consecutive identical readings
    # instead of waiting that whole budget out is what's being confirmed.
    assert dt < 14.0, "a genuinely-permanent not_a_checkbox result must still stop early, not wait out the full timeout"

print("\nPASS: single transient not_a_checkbox during re-render is tolerated; the real checkbox is still found and validated")
