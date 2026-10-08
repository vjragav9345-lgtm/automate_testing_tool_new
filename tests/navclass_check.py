"""TEST-ONLY: checks 2 and 3 - a mid-sequence Navigate typed with https:// / as a relative path, ORIGINAL vs FIXED generator."""
import contextlib, importlib.machinery, importlib.util, io, sys, tempfile
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_fixture_server import FixtureServer
from phase4_test_helpers import step_lp

def load(path, name):
    l = importlib.machinery.SourceFileLoader(name, str(path)); s = importlib.util.spec_from_loader(name, l)
    m = importlib.util.module_from_spec(s); l.exec_module(m); return m

def run_case(gen, label, start, typed):
    acts = [
        {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": start},
        {"action_type": "navigate", "page_url": typed, "page_id": 0, "locator_profile": None, "bounding_box": None, "timestamp": "2026-09-28T15:51:45.835Z"},
        {"action_type": "click", "value": None, "page_url": start, "locator_profile": step_lp(id_="#back", text="back", css_path="#back", tag="a"), "bounding_box": {"x": 8, "y": 60, "width": 40, "height": 20}},
    ]
    tc = {"name": "navclass_" + label, "start_url": start, "actions": acts}
    d = Path(tempfile.mkdtemp())
    sp = gen.generate_script(tc, out_name=f"navclass_{label}.py", output_dir=d)
    spec = importlib.util.spec_from_file_location("nc_" + label, sp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        res = m.run(start, output_json_path=d / "r.json", screenshot_dir=d / "s", headless=True)
    logs = [l for l in buf.getvalue().splitlines() if "[nav-url-class]" in l]
    return [(s["success"], str(s.get("error") or "")[:90]) for s in res["steps"]], logs

old = load(BASE / Path(open(BASE / "tests/_probe_out/navclass_backup_dir.txt").read().strip()) / "generator" / "script_generator.py", "gen_old")
new = load(BASE / "generator" / "script_generator.py", "gen_new")
with FixtureServer() as srv:
    a = srv.url("task0_fill_fixture.html"); p2 = srv.url("task0_fill_page2.html")
    for label, typed in (("CHECK2 typed with http(s)://", p2), ("CHECK3 relative path /...", "/task0_fill_page2.html")):
        ro, _ = run_case(old, "o", a, typed); rn, logs = run_case(new, "n", a, typed)
        print(f"\n{label}: typed={typed!r}")
        print("  original steps:", [ok for ok, _ in ro]); print("  fixed    steps:", [ok for ok, _ in rn])
        print("  fixed log:", logs[-1] if logs else None)
        assert [ok for ok, _ in ro] == [ok for ok, _ in rn] == [True, True, True], (ro, rn)
print("\nPASS: identical, all steps pass (click resolved on the new page)")
