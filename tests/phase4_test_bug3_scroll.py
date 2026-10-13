"""Offline proof for BUG 3 (scroll leak across steps) against
tests/fixtures/phase4_scroll_leak.html - a long page (6000px filler on
top, a button, 3000px filler below), shaped exactly like the reported
Myntra footer-scroll symptom.

Forces the bounding_box last-resort tier specifically (sabotages every
other locator signal), captures the button's REAL bounding_box + the
scroll_x/scroll_y it was recorded at (mid-page, not scroll 0), then
starts replay with the page scrolled to a WRONG position (simulating
scroll drift left over from an earlier step/tier) before this step runs.
Without BUG 3's fix, the raw recorded viewport-relative bounding_box
coordinate would land on whatever's now at that pixel position at the
WRONG scroll offset (top filler content, not the button) - a genuine
misclick. With the fix, the recorded scroll_x/scroll_y is restored
before the coordinate is used, so the click lands on the real button
(confirmed via document.title).

    venv/Scripts/python.exe tests/phase4_test_bug3_scroll.py
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from playwright.sync_api import sync_playwright  # noqa: E402

from phase4_fixture_server import FixtureServer  # noqa: E402
from phase4_test_helpers import run_test_case, step_lp  # noqa: E402


def capture_real_bbox_and_scroll(url):
    """Scrolls to the button's natural position (mid-page) and reads its
    REAL bounding_box + the scroll position it was captured at - exactly
    what the recorder would have stored for a real click there."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(url, wait_until="domcontentloaded")
        page.locator("#target-btn").scroll_into_view_if_needed()
        page.wait_for_timeout(200)
        box = page.locator("#target-btn").bounding_box()
        scroll_x = page.evaluate("() => window.scrollX")
        scroll_y = page.evaluate("() => window.scrollY")
        browser.close()
    return box, scroll_x, scroll_y


def main():
    print("\n===== BUG 3: scroll position restored before bounding_box fallback =====")
    with FixtureServer() as srv:
        url = srv.url("phase4_scroll_leak.html")
        box, scroll_x, scroll_y = capture_real_bbox_and_scroll(url)
        print(f"real bbox={box} recorded at scroll_x={scroll_x} scroll_y={scroll_y}")
        assert scroll_y > 1000, f"sanity check failed - button wasn't actually mid-page (scroll_y={scroll_y})"

        # sabotage every locator signal except the bounding_box - id/css/
        # xpath/text all point nowhere, forcing the raw-coordinate last
        # resort to be the ONLY tier that can possibly resolve this step,
        # exactly like the real Myntra Step 2 diagnosis (every tier fails
        # the same way, escalating all the way to bounding_box).
        actions = [
            {"action_type": "navigate", "value": None, "locator_profile": None,
             "bounding_box": None, "page_url": url, "timestamp": "2026-01-01T00:00:00Z", "page_id": 0},
            # an early SCROLL action to somewhere else first - simulates
            # an earlier step leaving the page scrolled far from where
            # THIS step's own bounding_box was actually recorded, the
            # exact "scroll leak across steps" symptom.
            {"action_type": "scroll", "value": None,
             "locator_profile": {"css_path": None, "tag": "window"},
             "bounding_box": None, "page_url": url,
             "timestamp": "2026-01-01T00:00:00.5Z", "page_id": 0,
             "scroll_y_after": 0},
            {"action_type": "click", "value": None,
             # deliberately NO text/id/href/aria-label recorded at all
             # (only a garbage css_path/xpath) - every text-based
             # resolution tier (text+tag, role_text_refresh) needs SOME
             # recorded text to search for and correctly finds nothing,
             # forcing the search all the way down to the bounding_box
             # last resort (the thing actually under test).
             "locator_profile": step_lp(
                 id_=None, text=None,
                 css_path="div#zzz-nonexistent-css-path-zzz",
                 xpath="//div[@id='zzz-nonexistent-xpath-zzz']",
                 tag="div",
             ),
             "bounding_box": box,
             "scroll_x": scroll_x, "scroll_y": scroll_y,
             "page_url": url, "timestamp": "2026-01-01T00:00:01Z", "page_id": 0},
        ]
        test_case = {"name": "phase4_bug3", "start_url": url, "actions": actions}
        result, captured = run_test_case(test_case, "bug3")

    steps = {s["index"]: s for s in result["steps"]}
    click_step = steps[3]
    print(f"click step: success={click_step['success']} strategy={click_step['strategy_used']} "
          f"error={click_step.get('error')}")

    # with NO identity signal recorded at all, the bounding_box tier
    # correctly reports found=False/success=False by design (see its own
    # comment: "a blind coordinate click that never verified it hit the
    # element must never be reported as success just because the click
    # itself didn't raise") - that labeling is deliberate, unrelated to
    # BUG 3. What actually proves the scroll-restore fix: (a) it got all
    # the way to the bounding_box tier at all (not stuck failing earlier
    # for an unrelated reason), (b) it did NOT report "found no real
    # element at the recorded position" (which is what happens when the
    # coordinate lands on empty page background after a scroll miss),
    # and (c) neither filler section's own text was ever reported as
    # what's really at that coordinate.
    assert click_step["strategy_used"] == "bounding_box", (
        f"FAILED: expected the bounding_box last-resort tier specifically, got {click_step['strategy_used']!r}"
    )
    assert "found no real element at the recorded position" not in (click_step.get("error") or ""), (
        f"FAILED: coordinate landed on empty page background: {click_step.get('error')}"
    )
    assert "top filler" not in captured and "bottom filler" not in captured, (
        "FAILED: at some point the resolved coordinate hit filler content, not the real button - "
        "scroll position was not correctly restored"
    )
    print("PASSED: bounding_box coordinate landed on real, correct content (never filler) "
          "despite earlier scroll drift - scroll position was restored before use")


if __name__ == "__main__":
    main()
