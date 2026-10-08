"""TEST-ONLY: click followed by a navigate - recorder-captured (caused_by_timestamp/delay_before_ms present) vs hand-added
(absent), ORIGINAL vs FIXED generator, on a local fixture."""
import contextlib, importlib.machinery, importlib.util, io, sys, tempfile
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_fixture_server import FixtureServer
from phase4_test_helpers import step_lp

def load(path, name):
    l = importlib.machinery.SourceFileLoader(name, str(path)); s = importlib.util.spec_from_loader(name, l)
    m = importlib.util.module_from_spec(s); l.exec_module(m); return m

T1 = "2026-09-28T16:00:00.100Z"
def run_case(gen, tag, start, p2, click_lp, recorder_nav):
    click = {"action_type": "click", "value": None, "page_url": start, "timestamp": T1, "locator_profile": click_lp,
             "bounding_box": {"x": 8, "y": 40, "width": 90, "height": 20}}
    nav = {"action_type": "navigate", "page_url": p2, "page_id": 0, "locator_profile": None, "bounding_box": None, "timestamp": "2026-09-28T16:00:00.900Z"}
    if recorder_nav:
        nav.update({"caused_by_timestamp": T1, "delay_before_ms": 300})
    acts = [{"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": start}, click, nav]
    tc = {"name": "pairing_" + tag, "start_url": start, "actions": acts}
    d = Path(tempfile.mkdtemp())
    sp = gen.generate_script(tc, out_name=f"pairing_{tag}.py", output_dir=d)
    spec = importlib.util.spec_from_file_location("pc_" + tag, sp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        res = m.run(start, output_json_path=d / "r.json", screenshot_dir=d / "s", headless=True)
    out = [("PASS" if s["success"] else ("NOT RUN" if "NOT RUN" in str(s.get("error")) else "FAIL")) for s in res["steps"]]
    err = next((str(s.get("error"))[:110] for s in res["steps"] if not s["success"] and "NOT RUN" not in str(s.get("error"))), "")
    return out, err

old = load(BASE / Path(open(BASE / "tests/_probe_out/pairing_backup_dir.txt").read().strip()) / "generator" / "script_generator.py", "gen_old")
new = load(BASE / "generator" / "script_generator.py", "gen_new")
LINK = step_lp(id_="#lnk", text="plain link", css_path="#lnk", tag="a")
INPUT = step_lp(id_="#other", text=None, css_path="#other", tag="input")
with FixtureServer() as srv:
    a = srv.url("task0_fill_fixture.html"); p2 = srv.url("task0_fill_page2.html")
    cases = [
        ("A recorder pair, click really navigates", LINK, True),
        ("B recorder pair, navigate genuinely never happens", INPUT, True),
        ("C hand-added navigate after a non-navigating click", INPUT, False),
    ]
    res = {}
    for label, lp, rec in cases:
        res[label] = (run_case(old, "o", a, p2, lp, rec), run_case(new, "n", a, p2, lp, rec))
        (o, oe), (n, ne) = res[label]
        print(f"\n{label}\n  original: {o} {oe}\n  fixed   : {n} {ne}")
A, B, C = (res[c[0]] for c in cases)
assert A[0][0] == A[1][0] == ["PASS", "PASS", "PASS"]
assert B[0][0] == B[1][0] == ["PASS", "FAIL", "NOT RUN"] and "expected effect was not observed" in B[1][1]
assert C[0][0][1] == "FAIL" and C[1][0] == ["PASS", "PASS", "PASS"]
print("\nPASS: recorder-captured pairing unchanged (works, and still fails + cascades when the navigate never happens); hand-added navigate no longer fails the step before it")
