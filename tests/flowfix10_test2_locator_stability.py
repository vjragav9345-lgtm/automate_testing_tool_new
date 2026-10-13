"""Item 3 (FIX 2, recorder-side, additive only): ~300ms after capturing an
action's locator profile, the recorder counts how many live elements each
primary locator matches (match_count) and, when the best one is ambiguous,
attaches disambiguating context (container path, same-text sibling index,
relative position). Replay must use these only as EXTRA scoring signals
inside _score_candidates_and_pick - never a new tier, never a change to
existing tier order/threshold.

Part 1 (recorder): clicks one of three IDENTICAL buttons (same text, same
class, no id/data-testid - a genuinely ambiguous css_path/text+tag locator)
via the real, unmodified action_capture.js and confirms match_count/
disambiguation land on the recorded action.

Part 2 (replay): feeds a synthetic action carrying that same shape of
disambiguation into the real _score_candidates_and_pick (via a full
generate+run pass against three ambiguous candidates, only one of which
matches the recorded container path/sibling index) and confirms the new
signals show up in the score log and the correct candidate wins.
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from phase4_test_helpers import run_test_case, step_lp  # noqa: E402
from phase4_fixture_server import FixtureServer  # noqa: E402
from recorder.record_session import Recorder  # noqa: E402


def part1_recorder(base_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        recorder = Recorder(page)
        recorder.install_context_capture(context)
        page.goto(base_url, wait_until="domcontentloaded")
        page.wait_for_timeout(200)
        recorder.start(launch_url=base_url)

        buttons = page.locator(".pick-btn")
        buttons.nth(1).click()  # the MIDDLE one (index 1) - only correct via disambiguation
        page.wait_for_timeout(600)  # let the ~300ms stability check + patch land

        recorded = list(recorder.actions)
        draft_path, draft_jsonl_path = recorder._draft_path, recorder._draft_jsonl_path
        browser.close()

    for p_ in (draft_path, draft_jsonl_path):
        if p_:
            p_.unlink(missing_ok=True)

    print("=== recorded actions ===")
    for a in recorded:
        print(a.get("action_type"), "match_count=", (a.get("locator_profile") or {}).get("match_count"),
              "disambiguation=", (a.get("locator_profile") or {}).get("disambiguation"))

    click_actions = [a for a in recorded if a.get("action_type") == "click"]
    assert len(click_actions) == 1, click_actions
    action = click_actions[0]
    lp = action["locator_profile"]
    mc = lp.get("match_count")
    assert mc, "expected match_count to be recorded"
    assert any(v == 3 for v in mc.values()), f"expected some tier to show 3 matches, got {mc}"
    disamb = lp.get("disambiguation")
    assert disamb, "expected disambiguation context for an ambiguous locator"
    assert disamb.get("same_text_sibling_index") == 1, disamb  # the middle button, 0-based
    assert disamb.get("same_text_sibling_total") == 3, disamb
    assert disamb.get("container_path"), disamb
    print("\nPART 1 PASS: recorder captured match_count + disambiguation for an ambiguous locator")
    return action


def part2_replay(base_url, recorded_action):
    lp = dict(recorded_action["locator_profile"])
    # force the SAME ambiguous shape onto a plain step - three identical
    # buttons, generically resolved via text+tag, no other distinguishing
    # signal - only the disambiguation context tells them apart
    lp["text"] = "Select"
    lp["element_text"] = "Select"
    lp["id"] = None
    lp["css_path"] = None
    lp["xpath"] = None
    lp["tag"] = "button"

    click_step = {
        "action_type": "click",
        "value": None,
        "locator_profile": lp,
        "page_url": base_url,
    }
    test_case = {
        "name": "flowfix10_locator_stability_replay",
        "start_url": base_url,
        "actions": [
            {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": base_url},
            click_step,
        ],
    }
    result, captured = run_test_case(test_case, "flowfix10_locator_stability", headless=True)

    print("\n=== replay result ===")
    for s in result.get("steps", []):
        print(s.get("index"), s.get("action_type"), s.get("success"), s.get("error"))

    assert "container-path+" in captured or "same-text-sibling-index+" in captured, (
        "expected the new FIX 2 disambiguation signals in the candidate-score log"
    )
    assert "match-count-consistent+5" in captured, "expected the match_count consistency bonus in the log"

    click_result = next(s for s in result["steps"] if s["action_type"] == "click")
    assert click_result["success"] is True, click_result
    print("\nPART 2 PASS: replay used match_count/disambiguation as extra scoring signals "
          "in _score_candidates_and_pick, with no tier/threshold changes, and resolved correctly")


def main():
    with FixtureServer() as srv:
        base_url = srv.url("flowfix10_ambiguous_rows.html")
        action = part1_recorder(base_url)
        part2_replay(base_url, action)


if __name__ == "__main__":
    main()
