"""Offline proof for BUG 1 (hover-revealed menu not recorded / replay
safety net) against tests/fixtures/phase4_hover_menu.html - a mega-menu
shaped exactly like the reported Myntra MEN -> Casual Shirts case
(display:none submenu revealed only on :hover of its trigger).

Part A: drive the REAL Recorder (recorder/record_session.py) through a
hover-then-click, exactly like a human would - the recorded JSON must
contain an explicit 'hover' step (targeting #men-trigger) BEFORE the
click step (targeting #casual-shirts-link).

Part B: replay an OLD-STYLE synthetic recording (no hover step at all,
just a bare click on the hidden #casual-shirts-link) - the safety net
inside _verify_resolved_target (_reveal_via_ancestor_hover, ancestors +
siblings) must reveal it, log "[hover-reveal]", click the REAL link
(confirmed via document.title), report success WITH a warning, and never
fall into the scroll-search/bounding_box path (no [CLICK-DIAG] bounding-
box misclick, and no multi-second scroll toward the footer).

Part C (regression): an ordinary, always-visible link click must NOT
record any hover step.

    venv/Scripts/python.exe tests/phase4_test_bug1_hover.py
"""
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from playwright.sync_api import sync_playwright  # noqa: E402

from recorder.record_session import Recorder  # noqa: E402
from phase4_fixture_server import FixtureServer  # noqa: E402
from phase4_test_helpers import run_test_case, step_lp  # noqa: E402


def part_a_recorder_emits_hover(url):
    print("\n===== PART A: recorder emits hover step before click =====")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        recorder = Recorder(page)
        recorder.install_context_capture(context)
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(300)
        recorder.start(launch_url=url)

        # Playwright's page.hover()/click() jump the pointer straight to
        # the target in one synthetic mousemove - real human movement (what
        # the recorder is actually built for) generates many intermediate
        # mousemove events as the cursor visibly glides there, which is
        # exactly what the recorder's pre-hover ambient snapshot relies on
        # (see action_capture.js's own comment on why a fresh, in-mouseover
        # read is always too late). mouse.move(..., steps=N) interpolates
        # like a real drag, so this drives it the same way an actual
        # recording session would see it.
        # start well away from the navbar entirely (the navbar sits at
        # the page's own top-left corner) - starting too close/inside it
        # would make the "before hover" ambient baseline already reflect
        # a partially-hovered state.
        page.mouse.move(700, 700)
        page.wait_for_timeout(200)
        trigger_box = page.locator("#men-trigger").bounding_box()
        trigger_cx = trigger_box["x"] + trigger_box["width"] / 2
        trigger_cy = trigger_box["y"] + trigger_box["height"] / 2
        page.mouse.move(trigger_cx, trigger_cy, steps=25)
        page.wait_for_timeout(400)
        link_box = page.locator("#casual-shirts-link").bounding_box()
        link_cy = link_box["y"] + link_box["height"] / 2
        # straight vertical descent at the TRIGGER's own x - the submenu
        # shares the trigger's left edge (left:0 in CSS) and is wider than
        # it, so this x stays inside the trigger while y is still in its
        # range, then inside the submenu once y crosses into its range -
        # never exits the hoverable region along the way (real hardware
        # mouse movement toward a mega-menu item behaves the same way).
        page.mouse.move(trigger_cx, link_cy, steps=15)
        page.wait_for_timeout(300)
        link_box = page.locator("#casual-shirts-link").bounding_box()
        page.mouse.move(
            link_box["x"] + link_box["width"] / 2,
            link_box["y"] + link_box["height"] / 2,
            steps=5,
        )
        page.wait_for_timeout(200)
        page.mouse.down()
        page.mouse.up()
        page.wait_for_timeout(700)

        test_case = recorder.stop(stop_reason="terminal_enter")
        browser.close()

    actions = test_case["actions"]
    for a in actions:
        print(f"  action_type={a.get('action_type'):10s} text={(a.get('locator_profile') or {}).get('text')!r}")

    click_idx = next((i for i, a in enumerate(actions) if a.get("action_type") == "click"), None)
    assert click_idx is not None, "no click action was recorded at all"
    hover_idx = next((i for i, a in enumerate(actions) if a.get("action_type") == "hover"), None)
    assert hover_idx is not None, "FAILED: no 'hover' action was recorded at all"
    assert hover_idx < click_idx, "FAILED: hover action was not recorded BEFORE the click"
    print(f"PASSED: hover recorded at index {hover_idx}, click at index {click_idx}")
    return test_case


def part_c_no_hover_for_ordinary_click(url):
    print("\n===== PART C (regression): ordinary click records NO hover =====")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        recorder = Recorder(page)
        recorder.install_context_capture(context)
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(300)
        recorder.start(launch_url=url)

        page.click("#ordinary-link")
        page.wait_for_timeout(700)

        test_case = recorder.stop(stop_reason="terminal_enter")
        browser.close()

    hover_count = sum(1 for a in test_case["actions"] if a.get("action_type") == "hover")
    assert hover_count == 0, f"FAILED: expected 0 hover actions for an ordinary click, got {hover_count}"
    print("PASSED: no hover action recorded for an ordinary, always-visible link click")


def part_d_modal_close_does_not_attribute_hover_to_covered_sibling(url):
    print("\n===== PART D: modal close does not create a hover on a covered sibling =====")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        recorder = Recorder(page)
        recorder.install_context_capture(context)
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(300)
        recorder.start(launch_url=url)

        page.click("#open-control")
        page.wait_for_timeout(250)
        page.click("#close-control")
        page.wait_for_timeout(100)
        page.click("#covered-link")
        page.wait_for_timeout(500)

        test_case = recorder.stop(stop_reason="terminal_enter")
        browser.close()

    actions = [a for a in test_case["actions"] if not a.get("action_type", "").startswith("__")]
    labels = [((a.get("locator_profile") or {}).get("text") or
               (a.get("locator_profile") or {}).get("accessible_name") or "").strip()
              for a in actions]
    types = [a.get("action_type") for a in actions]
    print("recorded:", list(zip(types, labels)))
    assert types == ["click", "click", "click"], f"unexpected modal sequence: {list(zip(types, labels))}"
    assert labels[0] == "Open overlay", f"open action was not recorded: {labels}"
    assert labels[1] == "", f"close control should remain an ordinary unnamed click: {labels}"
    assert labels[2] == "Behind the overlay", f"post-close target was not recorded last: {labels}"
    test_case = {"name": "phase4_modal_hover_attribution", "start_url": url, "actions": actions}
    result, captured = run_test_case(test_case, "modal_hover_attribution")
    replay_steps = [s for s in result["steps"] if s.get("action_type") != "navigate"]
    assert len(replay_steps) == 3, f"unexpected replay sequence: {replay_steps}"
    assert all(s.get("success") for s in replay_steps), (
        "FAILED: replay did not complete modal open/close/underlying click: " +
        repr([s.get("error") for s in replay_steps]) + "\n" + captured[-2000:]
    )
    print("PASSED: recording and replay preserve modal open, close, then post-close click")


def part_b_safety_net_reveals_and_clicks(url):
    print("\n===== PART B: replay safety net reveals + clicks an OLD-STYLE recording =====")
    actions = [
        {"action_type": "navigate", "value": None, "locator_profile": None,
         "bounding_box": None, "page_url": url, "timestamp": "2026-01-01T00:00:00Z", "page_id": 0},
        {"action_type": "click", "value": None,
         "locator_profile": step_lp(
             id_=None, text="Casual Shirts", href="/men-casual-shirts",
             css_path="#casual-shirts-link", tag="a",
         ),
         "bounding_box": {"x": 0, "y": 0, "width": 0, "height": 0},
         "page_url": url, "timestamp": "2026-01-01T00:00:01Z", "page_id": 0},
    ]
    test_case = {"name": "phase4_bug1_partB", "start_url": url, "actions": actions}

    t0 = time.monotonic()
    result, captured = run_test_case(test_case, "bug1_partb")
    elapsed = time.monotonic() - t0

    steps = {s["index"]: s for s in result["steps"]}
    click_step = steps[2]
    print(f"click step result: success={click_step['success']} strategy={click_step['strategy_used']} "
          f"warning={click_step.get('warning')} error={click_step.get('error')} elapsed={elapsed:.1f}s")

    assert "[hover-reveal]" in captured, "FAILED: no [hover-reveal] log line was printed"
    assert click_step["success"] is True, f"FAILED: click step did not succeed: {click_step.get('error')}"
    assert click_step["strategy_used"] != "bounding_box", (
        f"FAILED: resolved via bounding_box fallback, not the safety net: {click_step['strategy_used']}"
    )
    assert "hover-reveal" in (click_step.get("error") or ""), (
        "FAILED: step succeeded but no PASS-with-warning note was attached"
    )
    assert elapsed < 20, f"FAILED: took {elapsed:.1f}s - scroll-search likely ran despite the found-but-hidden gate"
    print("PASSED: safety net revealed the hidden link, clicked it, reported PASS-with-warning, no scroll-search")


def main():
    with FixtureServer() as srv:
        menu_url = srv.url("phase4_hover_menu.html")
        modal_url = srv.url("phase4_modal_hover_attribution.html")
        part_a_recorder_emits_hover(menu_url)
        part_c_no_hover_for_ordinary_click(menu_url)
        part_d_modal_close_does_not_attribute_hover_to_covered_sibling(modal_url)
        part_b_safety_net_reveals_and_clicks(menu_url)
    print("\n===== BUG 1: ALL PARTS PASSED =====")


if __name__ == "__main__":
    main()
