"""TEST-ONLY wrapper (Phase 1 item #5) - calls the REAL, completely
unmodified run() from a freshly generated script, in-process, under
controlled artificial network delay. Never imported by anything else in
this project; run directly:

    venv/Scripts/python.exe tests/otp_real_run_wrapper.py --delay-ms 1200

The production replay path (generator/script_generator.py's run(), and
every helper it calls) is never edited or monkeypatched itself - only
Playwright's own public Browser.new_context() is wrapped, purely inside
this process, so every context run() creates automatically gets a
page.route() delay handler attached before run() ever uses it. This is
strictly less invasive than patching run() or resolve_and_act directly:
the delay is applied at the Playwright API boundary, the exact same
boundary a real slow backend would show up at, and run()'s own code path
- including every settlement wait, retry, and the OTP-flow readiness gate
that tests/otp_race_harness.py's approximate fast-forward walk does not
replicate - runs completely untouched.

Only xhr/fetch requests are delayed (the resource types a real backend
API call actually uses), matching otp_race_harness.py's own convention,
so this never turns into a blanket "make everything slow" throttle.
"""
import argparse
import builtins
import importlib.util
import json
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import Browser  # noqa: E402

from generator.script_generator import generate_script  # noqa: E402


_STEP_HEADER_RE = re.compile(r"^\[(\d+)/\d+\]$")


def install_delay_patch(delay_ms, delay_state):
    """Wraps Browser.new_context so every context it creates has an
    xhr/fetch delay route attached before run() ever hands it a page to
    navigate. The route handler only actually sleeps while
    delay_state["enabled"] is True (see arm_step_gate below) - a step-
    scoped gate, not a whole-run blanket delay: delaying EVERY xhr/fetch
    for the whole replay was tried first and caused an unrelated, earlier
    failure (step 9, an events-list search click landing on the wrong
    card because the results list hadn't re-rendered yet under the
    slowed-down search API) that has nothing to do with the OTP flow
    this is actually investigating. Returns the original method so it
    can be restored.
    """
    orig_new_context = Browser.new_context

    def patched_new_context(self, *args, **kwargs):
        context = orig_new_context(self, *args, **kwargs)

        def handler(route):
            request = route.request
            if delay_state["enabled"] and request.resource_type in ("xhr", "fetch"):
                print(f"[wrapper] delaying {request.resource_type} request to {request.url!r} by {delay_ms}ms", flush=True)
                time.sleep(delay_ms / 1000)
            try:
                route.continue_()
            except Exception as e:
                print(f"[wrapper] route.continue_() failed (request likely already handled): {e}", flush=True)

        context.route("**/*", handler)
        return context

    Browser.new_context = patched_new_context
    return orig_new_context


def restore_patch(orig_new_context):
    Browser.new_context = orig_new_context


def arm_step_gate(delay_state, target_step):
    """Spies on print() (the same technique tests/otp_race_harness.py
    already uses to capture "[click-no-effect]" lines) to detect run()'s
    own per-step header line (_print_step_header's `print(f"[{i}/
    {total}]")` - a plain, generic step-boundary marker every step
    already prints, not something added for this) and flips
    delay_state["enabled"] on exactly for the duration of target_step,
    off again the moment the next step's header appears. Returns the
    original print() so it can be restored.
    """
    orig_print = builtins.print

    def spy_print(*args, **kwargs):
        if args:
            text = str(args[0])
            m = _STEP_HEADER_RE.match(text)
            if m:
                step_num = int(m.group(1))
                if step_num == target_step:
                    delay_state["enabled"] = True
                    orig_print(f"[wrapper] step {step_num} starting - delay armed", flush=True)
                elif delay_state["enabled"]:
                    delay_state["enabled"] = False
                    orig_print(f"[wrapper] step {step_num} starting - delay disarmed", flush=True)
        orig_print(*args, **kwargs)

    builtins.print = spy_print
    return orig_print


def disarm_step_gate(orig_print):
    builtins.print = orig_print


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay-ms", type=int, default=1200)
    parser.add_argument(
        "--recording",
        default=str(BASE_DIR / "storage" / "recordings" / "session_20260923_140957.json"),
    )
    parser.add_argument(
        "--through-step", type=int, default=20,
        help="1-based inclusive number of recorded actions to replay (default 20 = through Send OTP).",
    )
    parser.add_argument(
        "--delay-step", type=int, default=None,
        help="1-based step index to scope the delay to (only xhr/fetch requests firing while "
             "this exact step is executing are delayed). Defaults to --through-step (the last "
             "step replayed, e.g. Send OTP itself) - NOT the whole run, since blanket-delaying "
             "every request for the whole replay was found to cause an unrelated earlier failure.",
    )
    parser.add_argument(
        "--start-at-register", action="store_true",
        help="TEST-ONLY: skip recorded steps 1-9 (feed -> events list -> click the event "
             "card), which were found to be independently flaky right now (the events-"
             "list card locator intermittently resolves to the wrong event, unrelated to "
             "network delay - confirmed by it failing identically with the delay gate off). "
             "Replaces them with a single synthetic navigate straight to the event's "
             "/register URL (the same URL recorded step 10 already navigates to), then "
             "splices in the original steps 15 onward (scroll, the +5K counter, Continue, "
             "phone entry, Send OTP, ...) unmodified. Does not edit the recording file. "
             "With this flag, --through-step/--delay-step count from 1 = the synthetic "
             "navigate (so step 7 = Send OTP).",
    )
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    with open(args.recording, "r", encoding="utf-8") as f:
        recording = json.load(f)

    if args.start_at_register:
        register_url = recording["actions"][14]["page_url"]  # step 15's page_url
        synthetic_navigate = {"action_type": "navigate", "page_url": register_url, "page_id": 0}
        full_actions = [synthetic_navigate] + recording["actions"][14:22]  # original steps 15-22
    else:
        full_actions = recording["actions"]

    delay_step = args.delay_step if args.delay_step is not None else args.through_step
    sliced_actions = full_actions[: args.through_step]
    test_case = {
        "name": "otp_real_run_wrapper",
        # run()'s own initial page.goto(qa_url) happens BEFORE the per-step
        # loop starts (see generator/script_generator.py line ~8917) - for
        # the synthetic-navigate case this MUST already be register_url,
        # not the original recording's start_url, otherwise step 1's own
        # navigate finds itself NOT already on the target route, falls
        # into the forced-fallback recovery path (which exists to recover
        # from a PRECEDING CLICK not producing its recorded navigation),
        # and gets marked failed by logic that assumes a click drove it -
        # a wrapper artifact, not a real replay bug (confirmed via a real
        # run: the browser DID physically land on the correct URL either
        # way; only the false-failure verdict differed).
        "start_url": register_url if args.start_at_register else recording["start_url"],
        "actions": sliced_actions,
    }

    scratch_dir = Path(tempfile.mkdtemp(prefix="otp_real_run_"))
    try:
        script_path = generate_script(test_case, out_name="otp_real_run_script.py", output_dir=scratch_dir)
        spec = importlib.util.spec_from_file_location("otp_real_run_script", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        delay_state = {"enabled": False}
        orig_new_context = install_delay_patch(args.delay_ms, delay_state)
        orig_print = arm_step_gate(delay_state, delay_step)
        try:
            output_json = scratch_dir / "report.json"
            screenshot_dir = scratch_dir / "screenshots"
            result = module.run(
                test_case["start_url"],
                output_json_path=output_json,
                screenshot_dir=screenshot_dir,
                headless=args.headless,
            )
        finally:
            disarm_step_gate(orig_print)
            restore_patch(orig_new_context)

        print("\n===== RESULT =====")
        print("status:", result.get("status"))
        print("message:", result.get("message"))
        for s in result.get("steps", []):
            print(
                s.get("index"), s.get("action_type"),
                "success=", s.get("success"),
                (s.get("error") or "")[:150],
            )

        out_path = BASE_DIR / "tests" / f"real_run_wrapper_result_delay{args.delay_ms}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"\nfull result saved to {out_path}")
        print(f"screenshots saved under {screenshot_dir}")
    finally:
        # keep the screenshots for inspection - only drop the throwaway
        # generated script/module, not the run's own output
        pass


if __name__ == "__main__":
    main()
