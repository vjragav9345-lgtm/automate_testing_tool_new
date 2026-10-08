"""FIX 3 (new "drag" action) - RECORDER side: reproduces the exact real
bug from session_20260925_103118.json steps 13/14 (a price-range slider
drag captured as two separate, meaningless clicks - "Click - #rootRail"
then "Click - PRICE Rs300 - Rs3,800" - because action_capture.js had no
movement-threshold/gesture tracking at all before this fix, so a drag's
own mouseup was captured as a plain click on whatever text happened to be
under the pointer at release).

Loads the REAL, unmodified recorder/action_capture.js into a page (same
context.expose_binding("recordAction", ...) + add_init_script(...) wiring
record_session.py itself uses), performs a real mouse drag on the slider
handle via Playwright's own mouse API (dispatches trusted input events),
and asserts exactly ONE action was recorded, with action_type == "drag" -
no click actions for this gesture at all.
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import sync_playwright  # noqa: E402
from tests.phase4_fixture_server import FixtureServer  # noqa: E402

CAPTURE_JS = (BASE_DIR / "recorder" / "action_capture.js").read_text(encoding="utf-8")


def main():
    recorded = []

    with FixtureServer() as srv, sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        def on_action(raw):
            recorded.append(json.loads(raw))

        context.expose_binding("recordAction", lambda source, raw: on_action(raw))
        context.add_init_script(CAPTURE_JS)

        page = context.new_page()
        page.goto(srv.url("flowfix9_price_slider.html"))
        page.wait_for_timeout(200)

        handle_box = page.locator("#handle").bounding_box()
        start_x = handle_box["x"] + handle_box["width"] / 2
        start_y = handle_box["y"] + handle_box["height"] / 2

        page.mouse.move(start_x, start_y)
        page.mouse.down()
        # real drag: move well past the 5px threshold, along a path with
        # several intermediate points, ending up away from the rail
        # (mirrors the real recording's own release point landing over
        # the price label, not back on the rail/handle itself)
        page.mouse.move(start_x + 40, start_y - 5, steps=5)
        page.mouse.move(start_x + 90, start_y - 25, steps=5)
        page.mouse.move(start_x + 120, start_y - 40, steps=5)
        page.mouse.up()
        page.wait_for_timeout(700)  # let the bounded value-settle poll finish

        browser.close()

    print("=== RECORDED ACTIONS ===")
    for a in recorded:
        print(a.get("action_type"), "-", {k: a.get(k) for k in ("value_before", "value_after", "html5")})

    assert len(recorded) == 1, f"expected exactly 1 action, got {len(recorded)}: {recorded}"
    action = recorded[0]
    assert action.get("action_type") == "drag", f"expected a 'drag' action, got: {action}"
    assert action.get("value_before") is not None, "expected a detected slider/nearby-text value_before"
    assert action.get("value_after") is not None, "expected a detected slider/nearby-text value_after"
    assert action["value_before"] != action["value_after"], "value should have changed after the drag"
    assert action.get("path"), "expected sampled path points"
    assert len(action["path"]) <= 20, "path must be capped at ~20 points"

    print("\nPASS: FIX 3 recorder correctly captured ONE drag action "
          "(not two spurious clicks) with before/after value snapshots")


if __name__ == "__main__":
    main()
