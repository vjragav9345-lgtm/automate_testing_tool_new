"""TEST-ONLY, investigation only: isolates JUST the validate_checked step's own duration (not browser launch/script
generation), by timestamping print() lines, for the permanently-not-a-checkbox case."""
import builtins, importlib.util, sys, tempfile, time
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_fixture_server import FixtureServer
from phase4_test_helpers import step_lp
from generator.script_generator import generate_script

with FixtureServer() as srv:
    url = srv.url("checkbox_state_fixture.html")
    tc = {"name": "timing0b", "start_url": url, "actions": [
        {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": url},
        {"action_type": "validate_checked", "value": None, "page_url": url, "expected_state": "checked",
         "locator_profile": step_lp(id_=None, text=None, css_path=None, tag="button", xpath="//button[@id='plain-button']")},
    ]}
    d = Path(tempfile.mkdtemp())
    sp = generate_script(tc, out_name="timing0b.py", output_dir=d)

    timestamps = []
    _orig_print = builtins.print
    def _timed_print(*args, **kwargs):
        timestamps.append((time.monotonic(), " ".join(str(a) for a in args)))
        _orig_print(*args, **kwargs)
    builtins.print = _timed_print

    spec = importlib.util.spec_from_file_location("timing0b_mod", sp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    t_before_run = time.monotonic()
    res = mod.run(url, output_json_path=d / "r.json", screenshot_dir=d / "s", headless=True)
    builtins.print = _orig_print

    start_i = next(i for i, (_, l) in enumerate(timestamps) if l == "ACTION: validate_checked")
    print(f"\ntime from run() call to 'ACTION: validate_checked': {timestamps[start_i][0] - t_before_run:.3f}s (browser launch + navigate)")
    for t, l in timestamps[start_i:start_i+20]:
        print(f"  +{t - timestamps[start_i][0]:.3f}s  {l}")
    print("\nresult:", res["steps"][1].get("success"), res["steps"][1].get("error"))
