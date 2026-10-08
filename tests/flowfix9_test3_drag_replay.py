"""FIX 3 (new "drag" action) - REPLAY side: takes the drag action captured
by flowfix9_test2_drag_capture.py's real recording pass and replays it
against a FRESH instance of the same fixture via the real, unmodified
generator.script_generator - confirms the generated script actually moves
the slider handle (mouse.move/down/move-along-path/up on the LIVE,
freshly-resolved bounding box) and that FIX 1's verification correctly
recognizes the resulting value/URL change as success.
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from phase4_test_helpers import run_test_case  # noqa: E402
from phase4_fixture_server import FixtureServer  # noqa: E402

CAPTURE_JS = (BASE_DIR / "recorder" / "action_capture.js").read_text(encoding="utf-8")


def capture_real_drag(base_url):
    recorded = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.expose_binding("recordAction", lambda source, raw: recorded.append(json.loads(raw)))
        context.add_init_script(CAPTURE_JS)
        page = context.new_page()
        page.goto(base_url)
        page.wait_for_timeout(200)
        handle_box = page.locator("#handle").bounding_box()
        start_x = handle_box["x"] + handle_box["width"] / 2
        start_y = handle_box["y"] + handle_box["height"] / 2
        page.mouse.move(start_x, start_y)
        page.mouse.down()
        page.mouse.move(start_x + 100, start_y, steps=8)
        page.mouse.up()
        page.wait_for_timeout(700)
        browser.close()
    assert len(recorded) == 1 and recorded[0]["action_type"] == "drag", recorded
    return recorded[0]


def main():
    with FixtureServer() as srv:
        base_url = srv.url("flowfix9_price_slider.html")
        drag_action = capture_real_drag(base_url)
        print("captured drag action value_before/after:", drag_action.get("value_before"), "->", drag_action.get("value_after"))

        test_case = {
            "name": "flowfix9_drag_replay",
            "start_url": base_url,
            "actions": [
                {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": base_url},
                drag_action,
            ],
        }
        result, captured = run_test_case(test_case, "flowfix9_drag_replay", headless=True)

    steps = result.get("steps", [])
    print("\n=== RESULT ===")
    for s in steps:
        print(s.get("index"), s.get("action_type"), s.get("success"), s.get("error"))

    drag_result = next((s for s in steps if s.get("action_type") == "drag"), None)
    assert drag_result is not None, "no drag step in result"
    assert drag_result.get("success") is True, f"expected success=True, got: {drag_result}"
    assert "[drag-verify]" in captured, "expected the new drag-verify log line"
    print("\nPASS: FIX 3 replay correctly performed the pointer drag and verified the resulting value change")


if __name__ == "__main__":
    main()
