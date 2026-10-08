"""TEST-ONLY: VERIFY item 3 (2nd site) - Pick Element on a page with buttons/links (task0_fill_fixture.html),
then build a tiny recording from the picked profile and REPLAY it end-to-end."""
import importlib.util, sys, time
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
import recorder.pick_element as pe
from phase4_fixture_server import FixtureServer
from generator.script_generator import generate_script

with FixtureServer() as srv:
    url = srv.url("task0_fill_fixture.html")
    pick_id = pe.start_pick_session(url, [])
    out = {}

    def drive(browser, context):
        p = context.pages[0]
        box = p.locator("#lnk").bounding_box()   # "plain link" <a id="lnk">
        cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        p.mouse.move(cx, cy)
        p.wait_for_timeout(80)
        p.mouse.click(cx, cy)
        p.wait_for_timeout(400)
        browser.close()

    pe._TEST_DRIVE_QUEUE.put(drive)
    t0 = time.time()
    status = {}
    while time.time() - t0 < 60:
        status = pe._PICK_RESULTS.get(pick_id) or {}
        if status.get("status") == "done":
            break
        time.sleep(0.3)
    time.sleep(0.3)
    print("picked xpath:", status.get("xpath"), "| tag:", (status.get("locator_profile") or {}).get("tag"))
    assert status.get("status") == "done" and status.get("xpath"), status

    tc = {"name": "site2_pick_replay", "start_url": url, "actions": [
        {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": url},
        {"action_type": "click", "value": None, "page_url": url,
         "locator_profile": {"xpath": status["xpath"], "css_path": status.get("css_path"), "id": status.get("id"), "tag": "a", "text": "plain link"},
         "bounding_box": None},
    ]}
    import tempfile
    d = Path(tempfile.mkdtemp())
    sp = generate_script(tc, out_name="site2_pick_replay.py", output_dir=d)
    spec = importlib.util.spec_from_file_location("site2_pick_replay_mod", sp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    res = mod.run(url, output_json_path=d / "r.json", screenshot_dir=d / "s", headless=True)
    for s in res["steps"]:
        print(s.get("step"), s.get("action_type"), "PASS" if s.get("success") else "FAIL", (s.get("error") or "")[:150])
    assert all(s["success"] for s in res["steps"])
print("\nPASS: Pick Element + Replay works end-to-end on a second site (buttons/links page)")
