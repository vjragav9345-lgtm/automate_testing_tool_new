"""TEST-ONLY diagnostic harness for the intermittent Sportzia OTP-flow
failure - NOT wired into app.py, the replay engine, or any route. Never
imported by anything else in this project; run directly:

    venv/Scripts/python.exe tests/otp_race_harness.py --delay-ms 1200

Purpose: reproduce the suspected root cause (the "click-no-effect" 400ms
retry in generator/script_generator.py firing a real second click while
a real async response is merely slow, not absent) under CONTROLLED,
repeatable network latency, since normal-speed runs are not reliable
enough to reproduce it on demand (see the Phase 0 report - 11 normal
runs against the real site did not fail).

Reuses the exact same resolve_and_act every real replay uses -
recorder/pick_element.py's own _load_resolve_and_act() dynamically loads
it from a real, completely unmodified generate_script() output (see that
module's own docstring for why this is the only valid way to get a real,
callable resolve_and_act at all). This harness never modifies, patches,
or monkeys with that function - it only controls the SURROUNDING network
conditions via Playwright's page.route(), then calls the real function
and reports what actually happened, exactly as a real replay would see
it.

Delays are applied only to xhr/fetch requests (the resource types a
real backend API call - a phone-validation/OTP-send call - actually
uses), and only for a bounded window bracketing each targeted click, so
this never turns into a blanket "make everything slow" throttle that
would prove nothing specific about the click-no-effect race.
"""
import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import sync_playwright  # noqa: E402

from generator.script_generator import generate_script  # noqa: E402
from recorder.pick_element import _load_resolve_and_act, _replay_preceding_actions  # noqa: E402


_PROBE_MODULE_CACHE = {"module": None}


def _load_probe_module(start_url, pick_id):
    """TEST-ONLY: same technique recorder/pick_element.py's own
    _load_resolve_and_act() uses (generate a real, unmodified throwaway
    script via generate_script() and import it), but returns the whole
    module instead of just resolve_and_act, so this harness can also
    reach _is_genuinely_interactable/_resolve_element - the same
    OTP-send readiness gate the real run() loop uses (see run()'s
    _otp_role == "send_otp" branch) - for isolating that ONE difference
    without touching product code at all.
    """
    if _PROBE_MODULE_CACHE["module"] is not None:
        return _PROBE_MODULE_CACHE["module"]
    scratch_dir = Path(tempfile.mkdtemp(prefix="otp_harness_probe_"))
    try:
        probe_name = f"otp_harness_probe_{pick_id}"
        test_case = {"name": probe_name, "start_url": start_url, "actions": []}
        script_path = generate_script(test_case, out_name=f"{probe_name}_script.py", output_dir=scratch_dir)
        spec = importlib.util.spec_from_file_location(probe_name, script_path)
        probe_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe_module)
        _PROBE_MODULE_CACHE["module"] = probe_module
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)
    return _PROBE_MODULE_CACHE["module"]


def make_delay_route_handler(delay_ms, label):
    def handler(route):
        request = route.request
        if request.resource_type in ("xhr", "fetch"):
            print(f"[harness] delaying {request.resource_type} request to {request.url!r} "
                  f"by {delay_ms}ms ({label})", flush=True)
            time.sleep(delay_ms / 1000)
        try:
            route.continue_()
        except Exception as e:
            print(f"[harness] route.continue_() failed (request likely already handled): {e}", flush=True)
    return handler


def run_one(recording, delay_ms, run_label, real_fill=False, otp_gate=False):
    print(f"\n===== {run_label} (delay={delay_ms}ms, real_fill={real_fill}, otp_gate={otp_gate}) =====", flush=True)

    actions = recording["actions"]
    start_url = recording["start_url"]

    # 1-based indices, matching report.json's own numbering:
    #   17 = click "Continue"  (opens the Sign In modal)
    #   18 = click phone input
    #   19 = fill phone number
    #   20 = check "Send OTP" (opens the Verify OTP modal)
    idx_phone_fill = 19
    idx_send_otp = 20
    preceding_before_phone_fill = actions[: idx_phone_fill - 1]  # steps 1..18
    step_phone_fill = actions[idx_phone_fill - 1]
    preceding_before_send_otp = actions[: idx_send_otp - 1]  # steps 1..19
    step_send_otp = actions[idx_send_otp - 1]

    resolve_and_act = _load_resolve_and_act(start_url, f"harness_{run_label}")
    _is_genuinely_interactable = None
    _resolve_element = None
    if otp_gate:
        _probe_module = _load_probe_module(start_url, f"harness_{run_label}")
        _is_genuinely_interactable = _probe_module._is_genuinely_interactable
        _resolve_element = _probe_module._resolve_element

    findings = {
        "run_label": run_label,
        "delay_ms": delay_ms,
        "send_otp_no_effect_fired": False,
        "send_otp_result": None,
        "flow_broken": False,
        "notes": [],
    }

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(15000)
        page.goto(start_url, wait_until="domcontentloaded")

        # dismiss the cookie-consent banner if present - NOT recorded in
        # the source recording at all (the real user dismissed it before
        # recording started, or it simply didn't reappear for them), so
        # _replay_preceding_actions' own best-effort walk has no step for
        # it and later steps can misresolve onto its own text. This
        # harness-only accommodation exists purely to reach a clean,
        # repeatable starting point before the step actually under test;
        # it changes nothing about how Send OTP itself is resolved or
        # clicked.
        try:
            page.get_by_text("Accept", exact=True).click(timeout=3000)
            print("[harness] dismissed cookie-consent banner")
        except Exception:
            print("[harness] no cookie-consent banner found (already dismissed or not shown)")

        # items 2c/2d: log every xhr/fetch request+response (URL, method,
        # status) and every console message from here through the end of
        # the Send OTP dispatch, in BOTH paths (real_fill and default) -
        # so the two paths' network/console behavior can be diff'ed.
        net_log = []
        console_log = []

        def _on_request(req):
            if req.resource_type in ("xhr", "fetch"):
                net_log.append({"event": "request", "method": req.method, "url": req.url})

        def _on_response(res):
            if res.request.resource_type in ("xhr", "fetch"):
                net_log.append({"event": "response", "status": res.status, "url": res.url})

        def _on_console(msg):
            if msg.type in ("error", "warning"):
                console_log.append({"type": msg.type, "text": msg.text})

        page.on("request", _on_request)
        page.on("response", _on_response)
        page.on("console", _on_console)

        if real_fill:
            # ONE-DIFFERENCE-AT-A-TIME isolation test (user item #2a):
            # fast-forward through everything EXCEPT the phone fill via
            # the fast-forward walk (turbo=True, hardcoded inside
            # _replay_preceding_actions - harmless for non-fill steps),
            # then dispatch the phone fill itself exactly as real run()
            # does: a direct resolve_and_act(..., turbo=False) call, so
            # it goes through _do_fill's real press_sequentially path
            # (genuine per-character keydown/input/keyup events) instead
            # of turbo's single native el.fill() value-set.
            final_page, _walk_state = _replay_preceding_actions(
                page, context, start_url, preceding_before_phone_fill, resolve_and_act
            )
            page = final_page
            strategy_f, found_f, ok_f, err_f = resolve_and_act(page, step_phone_fill, turbo=False)
            print(f"[harness] real_fill phone-fill dispatch: ok={ok_f} err={err_f}")
            findings["phone_fill_result"] = {"strategy": strategy_f, "found": found_f, "ok": ok_f, "err": err_f}
        else:
            # fast-forward through everything up to and including the phone
            # fill, in one unified walk - uses the SAME real, unmodified
            # resolve_and_act throughout (turbo only skips fill's own
            # cosmetic character-by-character PACING, not the real keydown/
            # input/keyup events themselves, so the site's own live
            # validation still sees genuine keystrokes)
            final_page, _walk_state = _replay_preceding_actions(
                page, context, start_url, preceding_before_send_otp, resolve_and_act
            )
            page = final_page

        if otp_gate:
            # ONE-DIFFERENCE-AT-A-TIME isolation test (user item #2b):
            # replicate run()'s own _otp_role == "send_otp" pre-click
            # readiness gate (generator/script_generator.py, the
            # _otp_send_enabled poll loop right before the normal
            # dispatch) - waits up to 5s, polling every 200ms, for the
            # Send OTP button to become "genuinely interactable"
            # (_is_genuinely_interactable: visible + effective opacity +
            # pointer-events + not clipped by an ancestor) before ever
            # dispatching the click below. The harness's default path
            # skips this entirely and clicks immediately.
            try:
                _otp_send_el = _resolve_element(page, step_send_otp.get("locator_profile") or {})
            except Exception:
                _otp_send_el = None
            _otp_send_enabled = None
            _gate_start = time.monotonic()
            if _otp_send_el is not None:
                _gate_deadline = time.monotonic() + 5.0
                while time.monotonic() < _gate_deadline:
                    _otp_send_enabled = _is_genuinely_interactable(_otp_send_el)
                    if _otp_send_enabled:
                        break
                    page.wait_for_timeout(200)
            _gate_elapsed = time.monotonic() - _gate_start
            print(f"[harness] otp_gate: send_otp_enabled={_otp_send_enabled} after {_gate_elapsed:.2f}s wait")
            findings["otp_gate_result"] = {"enabled": _otp_send_enabled, "wait_s": round(_gate_elapsed, 2)}

        # ---- Send OTP click, with delayed xhr/fetch around it ----
        page.route("**/*", make_delay_route_handler(delay_ms, "Send OTP click"))
        _capture_lines = []
        _orig_print = print
        import builtins
        def _spy_print(*args, **kwargs):
            text = " ".join(str(a) for a in args)
            _capture_lines.append(text)
            _orig_print(*args, **kwargs)
        builtins.print = _spy_print
        try:
            strategy, found, ok, err = resolve_and_act(page, step_send_otp, turbo=False)
        finally:
            builtins.print = _orig_print
        page.unroute("**/*")
        page.remove_listener("request", _on_request)
        page.remove_listener("response", _on_response)
        page.remove_listener("console", _on_console)

        findings["net_log"] = net_log
        findings["console_log"] = console_log
        findings["send_otp_result"] = {"strategy": strategy, "found": found, "ok": ok, "err": err}
        no_effect_lines = [l for l in _capture_lines if "click-no-effect" in l]
        if no_effect_lines:
            findings["send_otp_no_effect_fired"] = True
            findings["notes"].extend(no_effect_lines)
        print(f"[harness] Send OTP result: ok={ok} err={err}")
        try:
            page.screenshot(path=str(BASE_DIR / "tests" / f"harness_{run_label}_after_send_otp.png"))
        except Exception:
            pass

        if not ok:
            findings["flow_broken"] = True

        # check what's actually on screen now - did a spurious second
        # click land on "Verify & Continue" (which would mean the OTP
        # modal is now showing an error, or the flow silently skipped
        # ahead) instead of leaving the OTP-entry field ready?
        try:
            body_text = page.evaluate("() => document.body.innerText")
            findings["body_text_snippet"] = body_text[:300]
            if "Verify OTP" not in body_text and "One-Time Password" not in body_text:
                findings["flow_broken"] = True
                findings["notes"].append(
                    "OTP entry screen not showing after Send OTP - flow likely skipped ahead "
                    "or landed somewhere unexpected"
                )
        except Exception as e:
            findings["notes"].append(f"couldn't read body text: {e}")

        browser.close()

    return findings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay-ms", type=int, default=1200)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument(
        "--recording",
        default=str(BASE_DIR / "storage" / "recordings" / "session_20260923_140957.json"),
    )
    parser.add_argument(
        "--real-fill",
        action="store_true",
        help="Dispatch the phone-number fill with turbo=False (real per-character "
             "keystroke events), isolating it as the single difference from the "
             "default harness path (which uses turbo=True for it via the fast-"
             "forward walk).",
    )
    parser.add_argument(
        "--otp-gate",
        action="store_true",
        help="Replicate run()'s own OTP-send readiness gate (wait up to 5s for "
             "the Send OTP button to become genuinely interactable) before "
             "dispatching the click - isolating that ONE difference from the "
             "default harness path, which clicks immediately with no such wait.",
    )
    args = parser.parse_args()

    with open(args.recording, "r", encoding="utf-8") as f:
        recording = json.load(f)

    all_findings = []
    for i in range(1, args.runs + 1):
        f = run_one(
            recording, args.delay_ms, f"delay{args.delay_ms}_run{i}",
            real_fill=args.real_fill, otp_gate=args.otp_gate,
        )
        all_findings.append(f)

    print("\n\n===== HARNESS SUMMARY =====")
    for f in all_findings:
        print(json.dumps(f, indent=2))

    out_path = BASE_DIR / "tests" / f"harness_results_delay{args.delay_ms}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_findings, f, indent=2)
    print(f"\nresults saved to {out_path}")


if __name__ == "__main__":
    main()
