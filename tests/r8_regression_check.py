"""TEST-ONLY: re-run of R8 (plain fill+click regression) for the hover
follow-up task. No production code was changed in that task, so this is a
confirmation that the baseline plain fill+click flow is unaffected -
using the same tests/fixtures/r8_regression_local.html fixture as the
original Phase 7 check."""
import importlib.util
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
from phase4_fixture_server import FixtureServer
from recorder.record_session import Recorder
from generator.script_generator import generate_script

FIXTURE = "r8_regression_local.html"

with FixtureServer() as srv:
    url = srv.url(FIXTURE)

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        pg = ctx.new_page()
        rec = Recorder(pg)
        rec.install_context_capture(ctx)
        pg.goto(url, wait_until="domcontentloaded")
        pg.wait_for_timeout(300)
        rec.start(launch_url=pg.url)
        pg.fill("#searchBox", "shoes")
        pg.click("#searchBtn")
        pg.wait_for_timeout(300)
        tc = rec.stop(name="r8_regression", stop_reason="terminal_enter")
        drafts = (rec._draft_path, rec._draft_jsonl_path)
        b.close()
    for d in drafts:
        if d:
            Path(d).unlink(missing_ok=True)

    d = Path("tests/_probe_out/r8_regression_rerun")
    d.mkdir(parents=True, exist_ok=True)
    sp = generate_script(tc, out_name="r8_regression_rerun_script.py", output_dir=d)
    spec = importlib.util.spec_from_file_location("r8_regression_rerun_mod", sp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    res = mod.run(url, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)

    print("=== R8 rerun ===")
    for s in res["steps"]:
        print(s["index"], s["action_type"], "success=" + str(s["success"]), "warning=" + repr(s.get("warning")))
    print("status:", res["status"])
    assert res["status"] == "PASS" and all(s["success"] for s in res["steps"])
    assert not any(s.get("warning") for s in res["steps"])
    print("R8 RE-RUN: PASS, no warnings - CONFIRMED")
