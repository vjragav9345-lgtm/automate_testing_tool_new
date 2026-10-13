"""TEST-ONLY, investigation only (no product code changes): times EACH finder tier inside
_resolve_element_with_strategy for a single resolve attempt against the permanently-not-a-checkbox target,
by monkeypatching a LOADED COPY of the generated script's own module (never touches the real product file)."""
import importlib.util, sys, tempfile, time, types
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_fixture_server import FixtureServer
from phase4_test_helpers import step_lp
from generator.script_generator import generate_script

with FixtureServer() as srv:
    url = srv.url("checkbox_state_fixture.html")
    tc = {"name": "timing0", "start_url": url, "actions": [
        {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": url},
        {"action_type": "validate_checked", "value": None, "page_url": url, "expected_state": "checked",
         "locator_profile": step_lp(id_=None, text=None, css_path=None, tag="button", xpath="//button[@id='plain-button']")},
    ]}
    d = Path(tempfile.mkdtemp())
    sp = generate_script(tc, out_name="timing0.py", output_dir=d)
    spec = importlib.util.spec_from_file_location("timing0_mod", sp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # instrument a COPY of _resolve_element_with_strategy's own finder list logic
    # by wrapping each finder function this module already has, timing each call
    orig = mod._resolve_element_with_strategy
    finder_names = ["_by_attr", "_find_by_id", "_find_by_role", "_find_by_href",
                    "_find_by_text_tag", "_find_by_css", "_find_by_xpath", "_find_in_iframes"]
    timings = []
    originals = {}
    for name in finder_names:
        fn = getattr(mod, name)
        originals[name] = fn
        def make_wrapper(n, f):
            def wrapper(*a, **kw):
                t0 = time.monotonic()
                try:
                    return f(*a, **kw)
                finally:
                    timings.append((n, time.monotonic() - t0))
            return wrapper
        setattr(mod, name, make_wrapper(name, fn))

    res = mod.run(url, output_json_path=d / "r.json", screenshot_dir=d / "s", headless=True)
    print("=== per-finder-call timings (validate_checked's own resolve attempts) ===")
    for n, t in timings:
        print(f"  {n}: {t:.3f}s")
    print("\ntotal finder time:", sum(t for _, t in timings))
    print("\nstep 2 result:", res["steps"][1].get("success"), res["steps"][1].get("error"))
