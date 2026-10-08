"""TEST-ONLY: point 4 - a pre-replay step that can't run is reported by step number, and the editor turns it into a clear message."""
import sys, threading
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
import app as appmod
import recorder.pick_element as pe
from phase4_fixture_server import FixtureServer
from phase4_test_helpers import step_lp
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

with FixtureServer() as fx:
    start = fx.url("task0_fill_fixture.html")
    steps = [
        {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": start},
        {"action_type": "click", "value": None, "page_url": start, "locator_profile": step_lp(id_="#does-not-exist", text="nothing here", css_path="#does-not-exist", tag="button"),
         "bounding_box": {"x": 5, "y": 5, "width": 40, "height": 20}},
        {"action_type": "click", "value": None, "page_url": start, "locator_profile": step_lp(id_="#lnk", text="plain link", css_path="#lnk", tag="a"), "bounding_box": {"x": 8, "y": 40, "width": 90, "height": 20}},
    ]
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True); ctx = br.new_context(); pg = ctx.new_page()
        raa = pe._load_resolve_and_act(start, "failure_check")
        final, ws = pe._replay_preceding_actions(pg, ctx, start, steps, raa)
        print("walk finished on:", final.url)
        print("replay_failures:", ws["replay_failures"])
        br.close()
    failures = ws["replay_failures"]
    assert [f["step_index"] for f in failures] == [2], failures

srv = make_server("127.0.0.1", 5001, appmod.app, threaded=True)
threading.Thread(target=srv.serve_forever, daemon=True).start()
with sync_playwright() as p:
    b = p.chromium.launch(headless=True); pg = b.new_page()
    pg.goto("http://127.0.0.1:5001/recording/edit?path=storage/recordings/session_20260928_224136.json"); pg.wait_for_selector("#actionsList > *")
    msg = pg.evaluate("f => replayFailuresSuffix({replay_failures: f})", failures)
    print("editor message:", msg)
    assert "step 2 (click)" in msg and "didn't run cleanly" in msg
    assert pg.evaluate("replayFailuresSuffix({replay_failures: []})") == ""
    b.close()
print("PASS")
import os; os._exit(0)
