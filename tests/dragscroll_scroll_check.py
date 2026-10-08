"""TEST-ONLY: Task B behaviours on a local fixture (tests/fixtures/dragscroll_scroll_pages.html), ORIGINAL vs FIXED
generator, with mouse.wheel calls counted in-process.

  case 1  ordinary scroll 0 -> 400                      PASS in both, hops replayed (wheel events > 0)
  case 2  scroll whose target the page cannot reach     FAILED in both ("did not reach target position") - the
          (html overflow hidden)                        fix must not turn a real failure into a pass
  case 3  a click makes the SITE scroll to 300 by     PASS in both; ORIGINAL then replays the recorded scroll's
          itself, then a recorded scroll to 300         delta on top (wheel events), FIXED skips the duplicate
                                                        movement (0 wheel) and still ends exactly at 300
  case 4  click whose target text drifted (recorded     FAILED in both (content mismatch is still a failure);
          "Buy now (15730)", live "(15731)") at the     ORIGINAL runs the scroll-and-recheck search (wheel events),
          recorded scroll position                      FIXED does not scroll at all
"""
import importlib.machinery
import importlib.util
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from playwright.sync_api import Mouse  # noqa: E402
from phase4_fixture_server import FixtureServer  # noqa: E402
from phase4_test_helpers import step_lp  # noqa: E402

WHEELS = []
_orig_wheel = Mouse.wheel


def _counting_wheel(self, dx, dy):
    WHEELS.append((dx, dy))
    return _orig_wheel(self, dx, dy)


Mouse.wheel = _counting_wheel


def load_gen(path, name):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    return m


def run_case(gen_module, label, actions, start_url):
    tc = {"name": f"scrollcheck_{label}", "start_url": start_url, "actions": actions}
    scratch = Path(tempfile.mkdtemp(prefix=f"scrollcheck_{label}_"))
    script = gen_module.generate_script(tc, out_name=f"scrollcheck_{label}.py", output_dir=scratch)
    spec = importlib.util.spec_from_file_location(f"scrollcheck_{label}_script", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    WHEELS.clear()
    res = mod.run(start_url, output_json_path=scratch / "report.json", screenshot_dir=scratch / "shots", headless=True)
    steps = res["steps"]
    return steps, len(WHEELS)


def main():
    bk = (BASE_DIR / "tests" / "_probe_out" / "backup_dir.txt").read_text().strip()
    old = load_gen(BASE_DIR / bk / "generator" / "script_generator.py", "gen_old")
    new = load_gen(BASE_DIR / "generator" / "script_generator.py", "gen_new")
    results = {}
    with FixtureServer() as srv:
        base = srv.url("dragscroll_scroll_pages.html")

        def nav(u):
            return {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": u}

        def scroll(u, dy, after):
            return {"action_type": "scroll", "value": None, "locator_profile": None, "page_url": u,
                    "delta_x": 0, "delta_y": dy, "scroll_y_before": 0, "scroll_y_after": after}

        cases = {
            "1 ordinary scroll": (base, [nav(base), scroll(base, 400, 400)]),
            "2 unreachable scroll": (base + "?mode=locked", [nav(base + "?mode=locked"), scroll(base + "?mode=locked", 500, 500)]),
            "3 site already scrolled": (base + "?mode=preset", [nav(base + "?mode=preset"), {
                "action_type": "click", "value": None, "page_url": base + "?mode=preset", "scroll_y": 0,
                "locator_profile": step_lp(id_="#go", text="Go", css_path="#go", tag="button"),
                "bounding_box": {"x": 10, "y": 10, "width": 50, "height": 34}},
                scroll(base + "?mode=preset", 300, 300)]),
            "4 drifted target": (base, [nav(base), {
                "action_type": "click", "value": None, "page_url": base, "scroll_y": 0,
                "locator_profile": step_lp(id_="#buy", text="Buy now (15730)", css_path="#buy", tag="button"),
                "bounding_box": {"x": 40, "y": 200, "width": 120, "height": 40}}]),
        }
        for name, (url, acts) in cases.items():
            for gen_name, gen in (("original", old), ("fixed", new)):
                steps, wheels = run_case(gen, f"{name[0]}_{gen_name}", acts, url)
                last = steps[-1]
                results[(name, gen_name)] = (last["success"], wheels, (last["error"] or "")[:90])

    print("\n%-26s %-9s %-8s %-8s %s" % ("case", "code", "result", "wheels", "error"))
    for (name, gen_name), (ok, wheels, err) in results.items():
        print("%-26s %-9s %-8s %-8d %s" % (name, gen_name, "PASS" if ok else "FAILED", wheels, err))

    r = results
    assert r[("1 ordinary scroll", "fixed")][0] and r[("1 ordinary scroll", "fixed")][1] > 0
    assert not r[("2 unreachable scroll", "original")][0] and not r[("2 unreachable scroll", "fixed")][0], "a real scroll failure must stay FAILED"
    assert "did not reach target position" in r[("2 unreachable scroll", "fixed")][2]
    assert r[("3 site already scrolled", "original")][0] and r[("3 site already scrolled", "fixed")][0]
    assert r[("3 site already scrolled", "original")][1] > 0 and r[("3 site already scrolled", "fixed")][1] == 0
    assert not r[("4 drifted target", "original")][0] and not r[("4 drifted target", "fixed")][0], "content-mismatch must stay FAILED"
    assert r[("4 drifted target", "fixed")][1] == 0
    print("\nPASS: real scroll failures stay FAILED; duplicate/unwanted scrolling is gone; outcomes otherwise unchanged")


if __name__ == "__main__":
    main()
