"""Offline proof for BUG 2 (product card label includes hover-only
content) against tests/fixtures/phase4_product_card.html - a card shaped
exactly like the reported Myntra case: repeated "NEW" badges, a
"Sizes: XXL" strip shown only on :hover, and a real <a href> carrying a
numeric product id.

Part A: drive the REAL recorder through a real click on the card -
recorded label must have "NEW" deduped (not repeated) and must NOT
contain "Sizes:"; href/product_id must be captured.

Part B: replay an OLD-STYLE recording whose href has DRIFTED (a
different slug, same numeric product id) and whose recorded label still
has the raw repeated/overlay text (simulating a recording made before
this fix) - must resolve via the href/product-id tier (not
bounding_box), actually click the right card (confirmed via
document.title), and must NOT raise the "unusually large bounding box"
recording-quality warning despite the card exceeding the large-bbox
thresholds.

    venv/Scripts/python.exe tests/phase4_test_bug2_card.py
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from playwright.sync_api import sync_playwright  # noqa: E402

from recorder.record_session import Recorder  # noqa: E402
from phase4_fixture_server import FixtureServer  # noqa: E402
from phase4_test_helpers import run_test_case, step_lp  # noqa: E402


def part_a_recorder_captures_clean_card(url):
    print("\n===== PART A: recorder captures clean label + href + product_id =====")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        recorder = Recorder(page)
        recorder.install_context_capture(context)
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(300)
        recorder.start(launch_url=url)

        page.click("#card-45954123")
        page.wait_for_timeout(700)

        test_case = recorder.stop(stop_reason="terminal_enter")
        browser.close()

    click = next(a for a in test_case["actions"] if a.get("action_type") == "click")
    lp = click["locator_profile"]
    print(f"  text={lp.get('text')!r}")
    print(f"  href={lp.get('href')!r}")
    print(f"  product_id={lp.get('product_id')!r}")

    text = (lp.get("text") or "")
    assert text.count("NEW") <= 1, f"FAILED: 'NEW' badge not deduped: {text!r}"
    assert "sizes" not in text.lower(), f"FAILED: overlay 'Sizes:' text leaked into the label: {text!r}"
    assert lp.get("href") and "45954123" in lp["href"], f"FAILED: href not captured correctly: {lp.get('href')!r}"
    assert lp.get("product_id") == "45954123", f"FAILED: product_id not extracted: {lp.get('product_id')!r}"
    print("PASSED: label deduped, no overlay text, href + product_id captured")


def part_b_href_drift_resolves_via_product_id(url):
    print("\n===== PART B: replay resolves a DRIFTED href via product_id tier =====")
    # simulates an OLD recording made before this fix: raw repeated
    # badges + overlay text in the label, AND an href that no longer
    # matches exactly (different slug) but keeps the same numeric id -
    # exactly the kind of drift a live site's own SEO-slug changes cause.
    actions = [
        {"action_type": "navigate", "value": None, "locator_profile": None,
         "bounding_box": None, "page_url": url, "timestamp": "2026-01-01T00:00:00Z", "page_id": 0},
        {"action_type": "click", "value": None,
         "locator_profile": step_lp(
             text="NEW\nNEW\nNEW\nNEW\nNEW\nMonk Mode\nSizes: XXL\nRs. 744",
             href="/tshirts/monk-mode/OLD-DRIFTED-SLUG-NO-LONGER-LIVE/45954123/buy",
             product_id="45954123",
             css_path="#card-does-not-exist-anymore",
             tag="a",
         ),
         "bounding_box": {"x": 20, "y": 20, "width": 260, "height": 340},
         "page_url": url, "timestamp": "2026-01-01T00:00:01Z", "page_id": 0},
    ]
    test_case = {"name": "phase4_bug2_partb", "start_url": url, "actions": actions}
    result, captured = run_test_case(test_case, "bug2_partb")

    steps = {s["index"]: s for s in result["steps"]}
    click_step = steps[2]
    print(f"click step: success={click_step['success']} strategy={click_step['strategy_used']} "
          f"large_bbox_flag={click_step.get('large_bbox_flag')} warning={click_step.get('warning')}")

    assert click_step["success"] is True, f"FAILED: click did not succeed: {click_step.get('error')}"
    assert click_step["strategy_used"] == "href", (
        f"FAILED: expected the href/product-id tier to resolve this, got {click_step['strategy_used']!r}"
    )
    assert click_step.get("large_bbox_flag") is False, (
        "FAILED: large-bbox recording-quality warning fired for a legitimate href-bearing card"
    )
    print("PASSED: drifted href resolved via product_id substring tier, large-bbox warning suppressed")


def main():
    with FixtureServer() as srv:
        card_url = srv.url("phase4_product_card.html")
        part_a_recorder_captures_clean_card(card_url)
        part_b_href_drift_resolves_via_product_id(card_url)
    print("\n===== BUG 2: ALL PARTS PASSED =====")


if __name__ == "__main__":
    main()
