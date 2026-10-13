"""TEST-ONLY: Bug 2 point 1 (picker element-selection) + a second/third site sanity check via Pick Element,
run through the REAL pick_element.py session (fresh path) against local fixtures."""
import sys, time
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
import recorder.pick_element as pe
from phase4_fixture_server import FixtureServer

with FixtureServer() as srv:
    url = srv.url("bug1_wait_fixture.html")
    pick_id = pe.start_pick_session(url, [])
    out = {}

    def drive(browser, context):
        p = context.pages[0]
        box = p.locator("#ready").bounding_box()
        cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        # simulate a real hover-then-click: mousemove first (feeds
        # __afqaPickLastHovered), THEN click at the same point
        p.mouse.move(cx, cy)
        p.wait_for_timeout(80)
        p.mouse.click(cx, cy)
        p.wait_for_timeout(400)
        out["profile"] = p.evaluate("() => window.__afqaLastPickedProfileForTest || null")
        browser.close()

    pe._TEST_DRIVE_QUEUE.put(drive)
    t0 = time.time()
    while "profile" not in out and time.time() - t0 < 60:
        time.sleep(0.3)
    time.sleep(0.5)
    status = pe._PICK_RESULTS.get(pick_id) or {}
    print("pick status keys:", list(status.keys()))
    print("picked xpath:", status.get("xpath"))
    print("picked tag:", status.get("tag"))
    assert status.get("tag") == "input" and status.get("xpath") and "#ready" in status.get("xpath") or status.get("xpath") == "//*[@id='ready']"
print("PASS: pick resolved the actual leaf element (#ready input), not an ancestor")
