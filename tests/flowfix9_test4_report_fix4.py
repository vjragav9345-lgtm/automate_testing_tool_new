"""FIX 4 (report/live-log correctness) - end-to-end: a 4-step recording
where step 2's target genuinely doesn't exist (so it fails and, with
stop_on_failure on by default, halts replay) must report steps 3-4 as
NOT_RUN (grey), never as red FAILED counted alongside step 2's real
failure - reproduces the exact real bug from a Myntra recording where 48
never-attempted steps were shown as red FAILED / "UI elements missing".

Runs through the REAL executor.run_execution.execute_test (real subprocess,
real report.json enrichment) and validation.report_generator.generate_report
(real HTML report), not just the raw generator output, since the bug this
fixes was in that enrichment layer, not in script_generator.py's own
report.json.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from generator.script_generator import generate_script  # noqa: E402
from executor import run_execution  # noqa: E402
from validation import report_generator  # noqa: E402
from tests.phase4_fixture_server import FixtureServer  # noqa: E402
from tests.phase4_test_helpers import step_lp  # noqa: E402


def build_test_case(base_url):
    return {
        "name": "flowfix9_report_fix4",
        "start_url": base_url,
        "actions": [
            {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": base_url},
            {"action_type": "click", "value": None, "locator_profile": step_lp(id_="#step1btn", text="Step 1 Button", css_path="#step1btn", tag="button"), "page_url": base_url},
            {"action_type": "click", "value": None, "locator_profile": step_lp(id_="#step2btn_missing", text="Step 2 Button (missing)", css_path="#step2btn_missing", tag="button"), "page_url": base_url},
            {"action_type": "click", "value": None, "locator_profile": step_lp(id_="#step3btn", text="Step 3 Button", css_path="#step3btn", tag="button"), "page_url": base_url},
            {"action_type": "click", "value": None, "locator_profile": step_lp(id_="#step4btn", text="Step 4 Button", css_path="#step4btn", tag="button"), "page_url": base_url},
        ],
    }


def main():
    import tempfile
    scratch_dir = Path(tempfile.mkdtemp(prefix="flowfix9_fix4_"))

    with FixtureServer() as srv:
        base_url = srv.url("flowfix9_multistep.html")
        test_case = build_test_case(base_url)
        script_path = generate_script(test_case, out_name="flowfix9_fix4_script.py", output_dir=scratch_dir)
        result = run_execution.execute_test(base_url, script_path, recording_name="flowfix9_fix4", action_count=5)

    print("=== step_counts ===", result.get("step_counts"))
    print("=== message ===", result.get("message"))
    print("=== ui_elements_status ===", result.get("ui_elements_status"))
    for s in result.get("steps", []):
        print(s["index"], s.get("action_type"), "success=", s.get("success"), "not_run=", s.get("not_run"))
    for e in result.get("ui_elements", []):
        print("ui_element", e["index"], e["status"], e.get("message"))

    counts = result.get("step_counts") or {}
    assert counts.get("passed") == 2, counts  # navigate isn't in ui_elements but IS a step; step1 + navigate both success
    assert counts.get("failed") == 1, counts
    assert counts.get("not_run") == 2, counts

    # index 1=navigate, 2=step1 (real), 3=step2 (fails - target missing),
    # 4/5=step3/step4 (never reached - not_run)
    steps_by_index = {s["index"]: s for s in result["steps"]}
    assert steps_by_index[3]["not_run"] is False and steps_by_index[3]["success"] is False
    assert steps_by_index[4]["not_run"] is True and steps_by_index[4]["success"] is False
    assert steps_by_index[5]["not_run"] is True and steps_by_index[5]["success"] is False
    assert steps_by_index[4]["error"].startswith("NOT RUN")

    ui_by_index = {e["index"]: e for e in result["ui_elements"]}
    assert ui_by_index[3]["status"] == "FAIL", ui_by_index[3]
    assert ui_by_index[4]["status"] == "NOT_RUN", ui_by_index[4]
    assert ui_by_index[5]["status"] == "NOT_RUN", ui_by_index[5]

    assert result["status"] == "FAIL"
    assert "first failure at step 3" in result["message"], result["message"]
    # NOT_RUN steps must never be listed as "missing" UI elements
    assert "UI elements missing at steps: [3]" in result["message"], result["message"]

    # report_generator must not crash and must classify the same way
    report_path = report_generator.generate_report(result, output_dir=scratch_dir)
    html = report_path.read_text(encoding="utf-8")
    assert "not-run-row" in html or "NOT RUN" in html, "expected NOT RUN styling/text in the HTML report"
    print(f"\nHTML report written to: {report_path}")

    print("\nPASS: FIX 4 correctly separates Passed/Failed/Not-run and only lists the real failure")


if __name__ == "__main__":
    main()
