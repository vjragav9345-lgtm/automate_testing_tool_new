"""TEST-ONLY: the bounded corrective nudge, on a snapping slider (tests/fixtures/dragscroll_snap_slider.html).

The handle starts at value 100 (300px). The recording says the user dragged it to value 20 (snap point at 60px).
The recorded end_delta is deliberately a hair short (lands on 32px -> value 10), so the replay's first
attempt is WRONG while the button is still held, and the nudge has to fix it:

  case A: recorded before/after differ (100 -> 20)  => slope known from the recording, 1 nudge expected
  case B: recorded before == after (20 -> 20)       => no slope; the stalled probes must ESCALATE until
                                                       the next snap point is crossed
  case C: control - recorded end_delta exact        => 0 nudges

Also checks the failure path: an unreachable recorded value (55, no snap point) must still end as FAILED
after at most DRAG_NUDGE_MAX_ATTEMPTS nudges (a near-miss is never silently accepted).
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from phase4_fixture_server import FixtureServer  # noqa: E402
from phase4_test_helpers import run_test_case, step_lp  # noqa: E402


def drag_step(base_url, before, after, dx):
    lp = step_lp(id_="#handle", css_path="div#handle", xpath="//*[@id='handle']", tag="div",
                 attributes={"role": "slider"}, role="slider")
    return {
        "action_type": "drag", "value": None, "page_url": base_url, "locator_profile": lp,
        "source_target": lp, "html5": False,
        "start_offset": {"x": 10, "y": 10}, "end_delta": {"dx": dx, "dy": 0}, "path": [],
        "value_before": {"kind": "aria_value", "value": str(before), "text": None},
        "value_after": {"kind": "aria_value", "value": str(after), "text": None},
        "bounding_box": {"x": 330, "y": 90, "width": 20, "height": 20},
    }


def run_case(label, before, after, dx, url):
    tc = {
        "name": f"dragscroll_nudge_{label}", "start_url": url,
        "actions": [
            {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": url},
            drag_step(url, before, after, dx),
        ],
    }
    result, captured = run_test_case(tc, f"dragscroll_nudge_{label}", headless=True)
    step = next(s for s in result["steps"] if s["action_type"] == "drag")
    nudges = captured.count("[drag] nudge ")
    return step, nudges, captured


def main():
    with FixtureServer() as srv:
        url = srv.url("dragscroll_snap_slider.html")
        a, na, _ = run_case("A", 100, 20, -268, url)
        b, nb, _ = run_case("B", 20, 20, -268, url)
        c, nc, _ = run_case("C", 100, 20, -240, url)
        d, nd, _ = run_case("D", 100, 55, -268, url)   # 55 is not a snap value -> unreachable
    print("\ncase A (slope known):     success=%s nudges=%s" % (a["success"], na))
    print("case B (slope unknown):   success=%s nudges=%s" % (b["success"], nb))
    print("case C (exact, control):  success=%s nudges=%s" % (c["success"], nc))
    print("case D (unreachable):     success=%s nudges=%s error=%s" % (d["success"], nd, (d["error"] or "")[:110]))
    assert a["success"] and na == 1, (a, na)
    assert b["success"] and 2 <= nb <= 4, (b, nb)
    assert c["success"] and nc == 0, (c, nc)
    assert (not d["success"]) and nd <= 4 and "did not reach its recorded final value" in (d["error"] or ""), (d, nd)
    print("\nPASS: nudge corrects near-misses (known and unknown slope), leaves exact drags alone, "
          "and an unreachable value still FAILS after a bounded number of nudges")


if __name__ == "__main__":
    main()
