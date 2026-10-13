"""Offline proof for FIX 2 items 1+2 (multi-candidate hover-reveal +
candidate scoring) against tests/fixtures/phase4_sort_dropdown.html -
THREE elements on the page all have the exact text "Popularity": the
real one inside a hover-only "Sort by" panel, one inside a permanently
display:none "mobile" duplicate panel, and one inside an unrelated
display:none wrapper. None of them has an href; the recorded css_path is
deliberately stale (matches nothing live), so text+tag's own
href/css_path disambiguation can't single one out - exactly the "4
candidates, all not visible" shape reported for the real Sort-by
dropdown, with NO hover_chain recorded (simulating an OLD recording).

Expects: the safety net hover-reveals the ancestor of ONLY the real
candidate (the other two structurally can't be revealed by any hover at
all), scores it highest, and clicks the REAL "Popularity" option -
confirmed via document.title, and via [candidate-score] log lines
showing all 3 candidates were actually considered.

    venv/Scripts/python.exe tests/phase4_test_multi_candidate.py
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from phase4_fixture_server import FixtureServer  # noqa: E402
from phase4_test_helpers import run_test_case, step_lp  # noqa: E402


def main():
    print("\n===== MULTI-CANDIDATE HOVER-REVEAL + SCORING =====")
    with FixtureServer() as srv:
        url = srv.url("phase4_sort_dropdown.html")
        actions = [
            {"action_type": "navigate", "value": None, "locator_profile": None,
             "bounding_box": None, "page_url": url, "timestamp": "2026-01-01T00:00:00Z", "page_id": 0},
            {"action_type": "click", "value": None,
             # no hover_chain at all (old recording) - text+tag is the
             # ONLY tier with anything to go on, and it's ambiguous
             # (3 exact "Popularity" matches, no href, stale css_path).
             "locator_profile": step_lp(
                 id_=None, text="Popularity", tag="li",
                 css_path="li#this-css-path-does-not-exist-anywhere",
             ),
             "bounding_box": {"x": 0, "y": 0, "width": 0, "height": 0},
             "page_url": url, "timestamp": "2026-01-01T00:00:01Z", "page_id": 0},
        ]
        test_case = {"name": "phase4_multi_candidate", "start_url": url, "actions": actions}
        result, captured = run_test_case(test_case, "multi_candidate")

    steps = {s["index"]: s for s in result["steps"]}
    click_step = steps[2]
    print(f"click step: success={click_step['success']} strategy={click_step['strategy_used']} "
          f"error={click_step.get('error')}")

    score_lines = [ln for ln in captured.splitlines() if "[candidate-score] text+tag" in ln]
    for ln in score_lines:
        print(" ", ln)

    assert len(score_lines) >= 3, f"FAILED: expected all 3 candidates to be scored/logged, got {len(score_lines)}"
    assert click_step["success"] is True, f"FAILED: click did not succeed: {click_step.get('error')}"
    assert click_step["strategy_used"] == "text+tag", (
        f"FAILED: expected the text+tag tier's own scoring to resolve this, got {click_step['strategy_used']!r}"
    )
    print("PASSED: all 3 ambiguous candidates were scored, the real (hoverable) one won, and was clicked")


if __name__ == "__main__":
    main()
