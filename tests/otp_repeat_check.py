"""TEST-ONLY zero-cost repeat check (item 7) - runs the real flow through
phone-fill (stopping BEFORE Send OTP is ever dispatched, so this never
clicks it and costs nothing against that budget) N times, and each time
reports exactly what the FIXED resolver (_resolve_element_with_strategy,
which now includes the nested-duplicate collapse and css_path/xpath
ambiguity resolution) would resolve for the Send OTP step: strategy, tag,
text, bounding box. Must be the real button (tabindex="0", ~384x52 near
x=448,y=445) every time, never the icon.

    venv/Scripts/python.exe tests/otp_repeat_check.py --runs 5
"""
import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import Browser, BrowserContext  # noqa: E402

from generator.script_generator import generate_script  # noqa: E402


def install_capture_patch(capture_state):
    orig_new_context = Browser.new_context
    orig_new_page = BrowserContext.new_page

    def patched_new_context(self, *args, **kwargs):
        context = orig_new_context(self, *args, **kwargs)
        capture_state["context"] = context
        return context

    def patched_new_page(self, *args, **kwargs):
        page = orig_new_page(self, *args, **kwargs)
        capture_state["page"] = page
        return page

    Browser.new_context = patched_new_context
    BrowserContext.new_page = patched_new_page
    return orig_new_context, orig_new_page


def restore_capture_patch(orig_new_context, orig_new_page):
    Browser.new_context = orig_new_context
    BrowserContext.new_page = orig_new_page


def run_once(module, recording, run_label):
    register_url = recording["actions"][14]["page_url"]
    synthetic_navigate = {"action_type": "navigate", "page_url": register_url, "page_id": 0}
    full_actions = [synthetic_navigate] + recording["actions"][14:19]  # steps 1-6, phone fill last, Send OTP excluded
    lp = recording["actions"][19]["locator_profile"]  # original step 20 = Send OTP

    test_case = {"name": f"otp_repeat_check_{run_label}", "start_url": register_url, "actions": full_actions}
    scratch_dir = Path(tempfile.mkdtemp(prefix=f"otp_repeat_{run_label}_"))
    script_path = generate_script(test_case, out_name=f"otp_repeat_{run_label}_script.py", output_dir=scratch_dir)
    spec = importlib.util.spec_from_file_location(f"otp_repeat_{run_label}_script", script_path)
    real_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(real_module)

    capture_state = {}
    orig_new_context, orig_new_page = install_capture_patch(capture_state)

    import builtins
    orig_print = builtins.print
    probe = {}

    def spy_print(*args, **kwargs):
        if args and str(args[0]) == "REPLAY COMPLETED" and not capture_state.get("probed"):
            capture_state["probed"] = True
            page = capture_state.get("page")
            if page is not None:
                try:
                    el, strat = real_module._resolve_element_with_strategy(page, lp)
                except Exception as e:
                    el, strat = None, None
                    probe["error"] = str(e)
                if el is not None:
                    try:
                        probe["strategy"] = strat
                        probe["tag"] = el.evaluate("e => e.tagName")
                        probe["text"] = (el.inner_text() or "")[:60]
                        probe["bounding_box"] = el.bounding_box()
                    except Exception as e:
                        probe["read_error"] = str(e)
                else:
                    probe["strategy"] = None
                    probe["note"] = "no strategy resolved anything"
        orig_print(*args, **kwargs)

    builtins.print = spy_print
    try:
        output_json = scratch_dir / "report.json"
        screenshot_dir = scratch_dir / "screenshots"
        real_module.run(
            test_case["start_url"], output_json_path=output_json,
            screenshot_dir=screenshot_dir, headless=True,
        )
    finally:
        builtins.print = orig_print
        restore_capture_patch(orig_new_context, orig_new_page)

    return probe


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument(
        "--recording",
        default=str(BASE_DIR / "storage" / "recordings" / "session_20260923_140957.json"),
    )
    args = parser.parse_args()

    with open(args.recording, "r", encoding="utf-8") as f:
        recording = json.load(f)

    module = None  # each run generates and loads its own throwaway module
    all_results = []
    for i in range(1, args.runs + 1):
        print(f"\n===== repeat check run {i}/{args.runs} =====", flush=True)
        probe = run_once(module, recording, f"run{i}")
        print(json.dumps(probe, indent=2, default=str), flush=True)
        all_results.append(probe)

    print("\n\n===== SUMMARY =====")
    all_correct = True
    for i, p in enumerate(all_results, start=1):
        box = p.get("bounding_box") or {}
        is_button = (
            p.get("strategy") is not None
            and p.get("tag") == "DIV"
            and (p.get("text") or "").strip() == "Send OTP"
            and box.get("width", 0) > 300
        )
        print(f"run {i}: strategy={p.get('strategy')} tag={p.get('tag')} text={p.get('text')!r} "
              f"bbox={box} -> {'REAL BUTTON' if is_button else 'WRONG / NOT RESOLVED'}")
        if not is_button:
            all_correct = False

    out_path = BASE_DIR / "tests" / "otp_repeat_check_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nresults saved to {out_path}")
    print("ALL RUNS RESOLVED THE REAL BUTTON" if all_correct else "AT LEAST ONE RUN DID NOT RESOLVE THE REAL BUTTON")


if __name__ == "__main__":
    main()
