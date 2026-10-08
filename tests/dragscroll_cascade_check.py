"""TEST-ONLY: proves the failure cascade is unchanged by the drag/scroll fixes.

A local fixture recording with ONE deliberately-broken locator in the middle
(step 3) is replayed twice - through the ORIGINAL generator (backups/
drag_scroll_fix_*/generator/script_generator.py) and through the CURRENT one -
and the per-step (success, not_run, error) tuples are compared. Both must
show: steps before the broken one PASS, the broken step FAILED, every later
step "NOT RUN (stopped after step N failed)" - identical in both.

    venv/Scripts/python.exe tests/dragscroll_cascade_check.py
"""
import importlib.machinery
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from phase4_fixture_server import FixtureServer  # noqa: E402
from phase4_test_helpers import step_lp  # noqa: E402


def load_gen(path, name):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    return m


def build(base_url):
    def click(id_, text):
        return {"action_type": "click", "value": None, "page_url": base_url,
                "locator_profile": step_lp(id_=id_, text=text, css_path=id_, tag="button")}
    return {
        "name": "cascade_check", "start_url": base_url,
        "actions": [
            {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": base_url},
            click("#step1btn", "Step 1 Button"),
            click("#step2btn_missing", "Step 2 Button (missing)"),   # deliberately broken locator
            click("#step3btn", "Step 3 Button"),
            click("#step4btn", "Step 4 Button"),
        ],
    }


def run_with(gen_path, label, base_url):
    gm = load_gen(gen_path, f"gen_{label}")
    tc = build(base_url)
    scratch = Path(tempfile.mkdtemp(prefix=f"cascade_{label}_"))
    script = gm.generate_script(tc, out_name=f"cascade_{label}.py", output_dir=scratch)
    spec = importlib.util.spec_from_file_location(f"cascade_{label}_script", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    res = mod.run(base_url, output_json_path=scratch / "report.json", screenshot_dir=scratch / "shots", headless=True)
    return [(s["index"], s["action_type"], bool(s["success"]), bool(s.get("not_run")),
             (s.get("error") or "")[:36] if s.get("not_run") else ("<real failure>" if not s["success"] else None))
            for s in res["steps"]]


def main():
    bk = (BASE_DIR / "tests" / "_probe_out" / "backup_dir.txt").read_text().strip()
    old_path = BASE_DIR / bk / "generator" / "script_generator.py"
    new_path = BASE_DIR / "generator" / "script_generator.py"
    with FixtureServer() as srv:
        url = srv.url("flowfix9_multistep.html")
        before = run_with(old_path, "before", url)
        after = run_with(new_path, "after", url)
    print("BEFORE (original code):")
    for r in before: print("  ", r)
    print("AFTER (fixed code):")
    for r in after: print("  ", r)
    assert before == after, "cascade behaviour differs between original and fixed code!"
    assert any(r[3] for r in after), "expected NOT RUN steps"
    assert [r[2] for r in after][:2] == [True, True] and after[2][2] is False
    print("\nPASS: identical per-step outcomes; step 3 FAILED, later steps 'NOT RUN (stopped after step 3 failed)'")


if __name__ == "__main__":
    main()
