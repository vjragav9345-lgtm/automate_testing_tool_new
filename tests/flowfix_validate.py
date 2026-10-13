"""TEST-ONLY validation runner for the recorder/replay flow fixes (FIX
1-6) - runs a recording through the REAL, unmodified run() and reports
per-step results. Deliberately truncates BEFORE any real Send OTP click
(step 13 in session_20260924_102031.json) to avoid spending that site's
real SMS budget during this validation pass - the full, untruncated
acceptance run (including OTP/Razorpay/sign-out) is a separate, later
step.

    venv/Scripts/python.exe tests/flowfix_validate.py --recording <path> [--through-step N] [--headless]
"""
import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from generator.script_generator import generate_script  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--recording", required=True)
    parser.add_argument("--through-step", type=int, default=None)
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    with open(args.recording, "r", encoding="utf-8") as f:
        recording = json.load(f)

    actions = recording["actions"]
    if args.through_step:
        actions = actions[: args.through_step]

    test_case = {
        "name": Path(args.recording).stem + "_flowfix_validate",
        "start_url": recording["start_url"],
        "actions": actions,
        "viewport_width": recording.get("viewport_width"),
        "viewport_height": recording.get("viewport_height"),
    }

    scratch_dir = Path(tempfile.mkdtemp(prefix="flowfix_validate_"))
    script_path = generate_script(test_case, out_name="flowfix_validate_script.py", output_dir=scratch_dir)
    spec = importlib.util.spec_from_file_location("flowfix_validate_script", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    output_json = scratch_dir / "report.json"
    screenshot_dir = scratch_dir / "screenshots"
    result = module.run(
        test_case["start_url"], output_json_path=output_json,
        screenshot_dir=screenshot_dir, headless=args.headless,
    )

    print("\n===== PER-STEP RESULTS =====")
    for s in result.get("steps", []):
        recovered = " [RECOVERED]" if s.get("recovered") else ""
        print(
            f"{s.get('index')} {s.get('action_type')} success={s.get('success')} "
            f"strategy={(s.get('locator_report') or {}).get('strategy')}{recovered} "
            f"{(s.get('error') or '')[:150]}"
        )
    print(f"\nSTATUS: {result.get('status')}")
    print(f"Recovered steps: {result.get('recovered_steps')}")
    print(f"Screenshots: {screenshot_dir}")

    out_path = BASE_DIR / "tests" / f"flowfix_validate_result_{Path(args.recording).stem}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"full result saved to {out_path}")


if __name__ == "__main__":
    main()
