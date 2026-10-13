"""TEST-ONLY synthetic failure tests for FIX 5/B (recover-and-continue,
narrowed policy - no step is ever skipped). Builds in-memory COPIES of
the baseline recording (never modifies the file on disk), runs each
through the REAL, unmodified run(), and asserts the reported per-step
results.

Scenario 1 (click/fill/check failure): step 7's locator is corrupted so
it can never resolve - expected: step 7 FAILED, step 8 (the very next
step, a Navigate) RECOVERED, steps 9+ continue normally, overall FAIL.

Scenario 2 (navigate failure - FIX B): step 3's own navigate target is
corrupted to an unreachable domain - expected: step 3 FAILED, and step 4
(the very next step) still EXECUTES normally (never marked "not
executed"/skipped) - a plain navigate failure must never trigger any
skip-ahead at all.

    venv/Scripts/python.exe tests/flowfix5_synthetic_test.py
"""
import copy
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from generator.script_generator import generate_script  # noqa: E402


def _run(test_case, label):
    scratch_dir = Path(tempfile.mkdtemp(prefix=f"flowfix5_synthetic_{label}_"))
    script_path = generate_script(test_case, out_name=f"flowfix5_synthetic_{label}_script.py", output_dir=scratch_dir)
    spec = importlib.util.spec_from_file_location(f"flowfix5_synthetic_{label}_script", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    output_json = scratch_dir / "report.json"
    screenshot_dir = scratch_dir / "screenshots"
    return module.run(
        test_case["start_url"], output_json_path=output_json,
        screenshot_dir=screenshot_dir, headless=False,
    )


def _print_and_save(result, label):
    print(f"\n===== PER-STEP RESULTS ({label}) =====")
    for s in result.get("steps", []):
        recovered = " [RECOVERED]" if s.get("recovered") else ""
        print(
            f"{s.get('index')} {s.get('action_type')} success={s.get('success')}{recovered} "
            f"{(s.get('error') or '')[:150]}"
        )
    print(f"\nSTATUS: {result.get('status')}")
    print(f"Recovered steps: {result.get('recovered_steps')}")

    out_path = BASE_DIR / "tests" / f"flowfix5_synthetic_result_{label}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"full result saved to {out_path}")


def scenario_click_failure(recording):
    actions = copy.deepcopy(recording["actions"][:12])
    sabotage_idx = 6  # 0-based -> step 7, "click Register Now"
    lp = actions[sabotage_idx]["locator_profile"]
    print(f"[click-failure] sabotaging step {sabotage_idx + 1} ({actions[sabotage_idx]['action_type']!r}, "
          f"was {lp.get('text')!r})")
    lp["id"] = None
    lp["text"] = "ZZZ_NONEXISTENT_TARGET_ZZZ"
    lp["element_text"] = "ZZZ_NONEXISTENT_TARGET_ZZZ"
    lp["accessible_name"] = "ZZZ_NONEXISTENT_TARGET_ZZZ"
    lp["css_path"] = "div#zzz-nonexistent-css-path-zzz"
    lp["xpath"] = "//div[@id='zzz-nonexistent-xpath-zzz']"
    lp["href"] = None
    lp["role"] = None
    actions[sabotage_idx]["bounding_box"] = {"x": 5, "y": 5, "width": 1, "height": 1}

    test_case = {
        "name": "flowfix5_synthetic_click",
        "start_url": recording["start_url"],
        "actions": actions,
        "viewport_width": recording.get("viewport_width"),
        "viewport_height": recording.get("viewport_height"),
    }
    result = _run(test_case, "click")
    _print_and_save(result, "click")

    steps = {s["index"]: s for s in result["steps"]}
    assert steps[7]["success"] is False, "step 7 (sabotaged click) must FAIL"
    assert steps[8]["success"] is True and steps[8].get("recovered") is True, (
        "step 8 (the next step, a Navigate) must succeed and be marked RECOVERED"
    )
    assert all(steps[idx]["success"] for idx in range(9, 13)), "steps 9-12 must all continue and pass"
    assert result["status"] == "FAIL", "overall status must still be FAIL"
    print("[click-failure] ALL ASSERTIONS PASSED")


def scenario_navigate_failure(recording):
    actions = copy.deepcopy(recording["actions"][:6])
    sabotage_idx = 2  # 0-based -> step 3, a "navigate" step
    assert actions[sabotage_idx]["action_type"] == "navigate", (
        f"expected step 3 to be a navigate, got {actions[sabotage_idx]['action_type']!r}"
    )
    print(f"[navigate-failure] sabotaging step {sabotage_idx + 1} (navigate) target to an unreachable domain")
    actions[sabotage_idx]["page_url"] = "https://this-domain-does-not-exist-zzz12345.invalid/"

    test_case = {
        "name": "flowfix5_synthetic_navigate",
        "start_url": recording["start_url"],
        "actions": actions,
        "viewport_width": recording.get("viewport_width"),
        "viewport_height": recording.get("viewport_height"),
    }
    result = _run(test_case, "navigate")
    _print_and_save(result, "navigate")

    steps = {s["index"]: s for s in result["steps"]}
    assert steps[3]["success"] is False, "step 3 (sabotaged navigate) must FAIL"
    assert steps[3]["error"] != "not executed - replay stopped before reaching this action"
    # FIX B: a failed navigate never triggers skip-ahead - step 4 must
    # actually run (whatever its own real outcome is), never be reported
    # as "not executed"
    assert steps[4]["error"] != "not executed - replay stopped before reaching this action", (
        "step 4 must have been ATTEMPTED, not skipped, after step 3's navigate failure"
    )
    assert result["status"] == "FAIL", "overall status must still be FAIL"
    print("[navigate-failure] ALL ASSERTIONS PASSED")


def main():
    recording_path = BASE_DIR / "storage" / "recordings" / "session_20260924_102031.json"
    with open(recording_path, "r", encoding="utf-8") as f:
        recording = json.load(f)

    scenario_click_failure(recording)
    scenario_navigate_failure(recording)
    print("\n===== ALL SCENARIOS PASSED =====")


if __name__ == "__main__":
    main()
