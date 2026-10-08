"""Runs a generated Playwright script (see generator/script_generator.py)
against a QA URL as a separate process, then layers content/screenshot/
UI-element/product validation on top of the structured result it writes out.

This used to have its own in-process copy of the click/fill/select replay
logic, separate from what the generated script did. That meant "the script
you can inspect" and "what actually runs" could drift apart, which is
exactly what generated-script users don't want. Now there's exactly one
replay implementation - the generated script - and this module just runs
it and interprets the result.

Product validation runs INSIDE that same script/subprocess too, on the same
page the recorded workflow just produced - not a separate session. This
module only passes the requested product name through as a CLI arg and
reads back whatever the script already found; it never opens the site a
second time.
"""
import json
import logging
import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

from storage.repository import BASE_DIR
from utils import normalize_url
from validation import compare

logger = logging.getLogger(__name__)

SCRIPT_TIMEOUT_SEC = 120

# Dynamic per-run timeout: a fixed ceiling only ever fits SOME session
# lengths - a 10-action session wastes most of it as dead air if
# something actually hangs, while a genuinely long, 50+ action session
# can get killed mid-way through legitimate work. Both constants below
# are pulled from timeouts this project ALREADY uses elsewhere, not
# invented:
#   - BASELINE_OVERHEAD_SEC mirrors the exact "page load timeout + 10s
#     buffer" pattern app.py's own recording-launch readiness wait
#     already uses (PAGE_LOAD_TIMEOUT/1000 + 10) - the same real-world
#     cost this replay subprocess pays once, up front, for the browser
#     to launch and its first page to load.
#   - SECONDS_PER_STEP matches generator/script_generator.py's own
#     page.goto(..., timeout=30000) - the single slowest per-operation
#     timeout already used anywhere in the generated script, i.e. the
#     worst-case cost a single recorded step (a navigation) can
#     legitimately take. Most steps (a click, a fill) finish in a
#     fraction of this; it's a ceiling per step, not an expected
#     average, so real runs finish well under the total budget.
BASELINE_OVERHEAD_SEC = 40
SECONDS_PER_STEP = 30
# Sane outer ceiling so a truly hung process still terminates instead
# of blocking forever. 30 minutes comfortably covers a session of ~55
# actions even if EVERY single one hit the worst-case per-step cost
# above (55 * 30s + 40s overhead ~= 1750s) - realistically far more
# steps than that finish inside this window, since most steps cost a
# small fraction of the per-step ceiling.
MAX_TIMEOUT_SEC = 1800


# how much extra subprocess-timeout headroom an OTP-shaped recording
# gets on top of its normal per-step budget - must stay >= the generated
# script's own OTP_WAIT_TIMEOUT_S (generator/script_generator.py), or a
# replay that's genuinely just waiting on a human to submit a live OTP
# would get killed by THIS timeout before that wait ever finishes.
# Recordings with no OTP-shaped step (has_otp_step=False, the default)
# are completely unaffected - this is only ever added on top.
OTP_WAIT_TIMEOUT_BUFFER_SEC = 200


def _compute_script_timeout(action_count, has_otp_step=False):
    """Derives the subprocess timeout from the session's own real
    action count instead of sharing one fixed ceiling across every
    session length. Never returns LESS than the original fixed
    SCRIPT_TIMEOUT_SEC, so a short session's timeout budget can only
    ever grow relative to before this change, never shrink - existing
    short-session behavior/speed is unaffected, only long sessions get
    the extra headroom they actually need. Falls back to the original
    fixed constant entirely when no action count is available (an
    unmodified/legacy call site), rather than guessing.

    has_otp_step (default False - every existing caller is unaffected)
    adds OTP_WAIT_TIMEOUT_BUFFER_SEC on top of the normal per-step
    budget, so a recording that pauses replay waiting for a live OTP
    (see generator/script_generator.py's own OTP-step handling) isn't
    killed by this subprocess timeout while genuinely just waiting on a
    human, not hung.
    """
    otp_buffer = OTP_WAIT_TIMEOUT_BUFFER_SEC if has_otp_step else 0
    if not action_count or action_count <= 0:
        return SCRIPT_TIMEOUT_SEC + otp_buffer
    scaled = BASELINE_OVERHEAD_SEC + SECONDS_PER_STEP * action_count + otp_buffer
    return min(MAX_TIMEOUT_SEC, max(SCRIPT_TIMEOUT_SEC, scaled))


def _slug(text, max_len=40):
    """Sanitizes a recording name into a short, filesystem-safe fragment
    for a run folder name - same idea as the generated script's own
    _slug() helper, kept as a tiny local copy here since this module
    doesn't import the generated-script template's internals."""
    if not text:
        return ""
    safe = "".join(c if c.isalnum() else "_" for c in text.strip().lower())
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe.strip("_")[:max_len]


def _fail_result(qa_url, run_id, message, run_dir=None):
    return {
        "status": "FAIL",
        "message": message,
        "diagnostic": None,
        "qa_url": qa_url,
        "steps": [],
        "step_counts": {"passed": 0, "warnings": 0, "failed": 0, "not_run": 0, "manual_input": 0},
        "ui_elements": [],
        "ui_elements_status": "FAIL",
        "content_check": None,
        "screenshot_diff": None,
        "product_validation": None,
        "final_screenshot": None,
        "run_id": run_id,
        "run_dir": _to_repo_relative(str(run_dir)) if run_dir else None,
    }


def _to_repo_relative(path_str):
    """Screenshots come back as absolute paths from the subprocess - store
    them relative to BASE_DIR like the rest of the app does, so the report
    generator's base64 embedding can find them the same way either way."""
    if not path_str:
        return None
    try:
        return str(Path(path_str).resolve().relative_to(BASE_DIR)).replace("\\", "/")
    except ValueError:
        return path_str


def _build_ui_elements(steps):
    """UI element validation reuses the found/not-found outcome the script
    already determined while resolving each step - nothing gets located a
    second time, we're just reporting that outcome as its own section.

    FIX 4 (report/live-log correctness): a step never reached because
    stop_on_failure halted replay earlier (script_generator.py's own
    `not_run` flag) or a manual-input/OTP step (`otp_role`) must never be
    reported here as a real "UI element missing" FAIL - CONFIRMED REAL BUG
    this fixes, against an actual Myntra recording (session_
    20260924_213410.json): 48 steps that were never even attempted were
    shown as red FAILED and listed under "UI elements missing" once the
    first real failure stopped the run. Both get their own NOT_RUN/
    MANUAL_INPUT status instead, distinct from PASS/FAIL, so overall PASS/
    FAIL and "UI elements missing" both only ever reflect genuine
    failures - a manual-input step is only ever "not a failure" when it
    didn't itself also fail for a real reason (an OTP step that genuinely
    couldn't resolve its own phone-number field, say, still reports FAIL).
    """
    ui_elements = []
    for s in steps:
        if s.get("action_type") in ("navigate", "scroll"):
            continue  # nothing to "find" for a navigation or scroll step
        found = bool(s.get("element_found"))
        strategy = s.get("strategy_used")
        not_run = bool(s.get("not_run"))
        is_manual_input = bool(s.get("otp_role")) and s.get("success") is not False
        if not_run:
            status = "NOT_RUN"
            message = "Step was never executed - replay stopped before reaching it"
        elif is_manual_input:
            status = "MANUAL_INPUT"
            message = "Manual input step (OTP/CAPTCHA) - not counted as a UI element failure"
        elif not found:
            status = "FAIL"
            message = "Expected UI element was not found"
        else:
            status = "PASS"
            message = None
        ui_elements.append({
            "index": s["index"],
            "action_type": s.get("action_type"),
            "element_found": found,
            "locator_used": strategy if strategy != "bounding_box" else None,
            "status": status,
            "message": message,
        })
    return ui_elements


def _prepare_run(script_path, recording_name):
    """Shared by execute_test() and the async start_replay() below: picks
    the one dedicated output folder for a run (see the docstring that used
    to live here - still exactly the same generated_scripts/screenshoots/
    <name>_<timestamp>/ convention, same parent the generated script's own
    run() falls back to when executed directly) and the report.json path
    inside it. No behavior here - just the naming/folder decision both
    call sites need identically.
    """
    run_id = f"{_slug(recording_name or script_path.stem) or 'run'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir = BASE_DIR / "generated_scripts" / "screenshoots" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    output_json = run_dir / "report.json"
    return run_id, run_dir, output_json


def _build_command(script_path, qa_url, output_json, run_dir, product_to_verify):
    # "0" = headed (visible) - dashboard-triggered Replay should open a
    # real browser window so the user can watch it run, matching how a
    # manually-run script behaves by default. The optional 5th arg is the
    # product name - the script validates it on whatever page the recorded
    # actions ended on, in this SAME process, not a second session here.
    venv_python = BASE_DIR / "venv" / "Scripts" / "python.exe"
    python_executable = str(venv_python) if venv_python.exists() else sys.executable
    return [python_executable, str(script_path), qa_url, str(output_json), str(run_dir), "0", product_to_verify or ""]


_INTERNAL_ERROR_MSG = (
    "Failed: The replay stopped because of an internal error in the tool while doing this step "
    "(not a website problem). Details are below."
)


def _complete_steps(steps, raw, total, returncode, stderr):
    """A replay process that ended before every recorded step had a result (a crash, a killed process, a
    closed browser) must never read as a pass. The step that was running is FAILED (plain reason, the
    technical text under Details); every step after it is NOT RUN, in the existing "NOT RUN (stopped
    after step N failed)" wording. Returns (steps, number of steps that had no result)."""
    try:
        total = int(total or 0)
    except (TypeError, ValueError):
        total = 0
    have = {s.get("index") for s in steps}
    missing = [i for i in range(1, total + 1) if i not in have]
    if not missing:
        return steps, 0
    cur = raw.get("current_step") if isinstance(raw.get("current_step"), dict) else {}
    crashed = cur.get("index") if cur.get("index") in missing else None
    types = raw.get("recorded_action_types") if isinstance(raw.get("recorded_action_types"), list) else []
    names = raw.get("recorded_names") if isinstance(raw.get("recorded_names"), list) else []

    def _entry(i, **kw):
        base = {
            "index": i,
            "action_type": types[i - 1] if i - 1 < len(types) else None,
            "name": names[i - 1] if i - 1 < len(names) else None,
            "origin": None, "count_summary_rows": None, "value_range_rows": None, "page_mismatch_info": None,
            "strategy_used": None, "element_found": False, "success": False, "warning": None,
            "effect_verified": None, "large_bbox_flag": False, "screenshot": None, "url_before": None,
            "url_after": None, "duration": 0, "locator_report": None, "expected": None, "actual": None,
            "candidate_diagnostics": None, "otp_role": None, "technical": None,
        }
        base.update(kw)
        return base

    detail = (stderr or "").strip()[-2000:] or f"the replay process ended before finishing (exit code {returncode})"
    out = list(steps)
    stopped_after = None
    if crashed is not None:
        out.append(_entry(crashed, error=_INTERNAL_ERROR_MSG, not_run=False, technical=detail))
        stopped_after = crashed
    for i in missing:
        if i == crashed:
            continue
        if stopped_after is not None:
            msg = f"NOT RUN (stopped after step {stopped_after} failed): {_INTERNAL_ERROR_MSG}"
        else:
            msg = "not executed - replay stopped before reaching this action"
        out.append(_entry(i, error=msg, not_run=True, technical=None if stopped_after is not None else detail))
    out.sort(key=lambda s: s.get("index") or 0)
    return out, len(missing)


def _finalize_result(qa_url, run_id, run_dir, output_json, expected_content, expected_screenshot, product_to_verify, proc_returncode=None, proc_stderr="", screenshot_options=None, action_count=None):
    """Everything execute_test() used to do AFTER the subprocess finished -
    read back the generated script's raw report.json and layer content/
    screenshot/UI-element/product validation on top of it. Shared as-is by
    both execute_test() (blocking) and the async start_replay()/
    poll_replay() pair below, so there is exactly one place that
    interprets a finished run's report.json, same as there's exactly one
    replay implementation.

    screenshot_options is an optional dict forwarded as keyword args to
    compare.compare_screenshots() - threshold/ignored_regions/strict (see
    that module for what each does). None (the default) means "use that
    module's own defaults", same behavior as before these existed.
    """
    if not output_json.exists():
        logger.error("generated script produced no result (exit %s): %s", proc_returncode, (proc_stderr or "")[-2000:])
        return _fail_result(qa_url, run_id, "the test script didn't complete - couldn't reach the QA URL or it crashed", run_dir)

    try:
        raw = json.loads(output_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.error("couldn't read execution result: %s", e)
        return _fail_result(qa_url, run_id, "couldn't read the test run's result file", run_dir)

    steps = raw.get("steps", [])
    # steps that never got a result (the process died before finishing): FAILED / NOT RUN, never a pass
    incomplete = 0
    if steps:
        try:
            steps, incomplete = _complete_steps(steps, raw, raw.get("recorded_steps") or action_count, proc_returncode, proc_stderr)
        except Exception as e:
            logger.warning("couldn't complete the step list of an unfinished run: %s", e)
    for s in steps:
        s["screenshot"] = _to_repo_relative(s.get("screenshot"))
        s["fragile"] = s.get("strategy_used") in ("text+tag", "bounding_box")

    ui_elements = _build_ui_elements(steps)
    # FIX 4: only a genuine FAIL counts against overall UI-element status -
    # NOT_RUN (stop_on_failure halted before reaching it) and MANUAL_INPUT
    # (OTP/CAPTCHA) are both real, distinct outcomes, never silently
    # folded into "FAIL" just because they aren't "PASS" either.
    ui_status = "FAIL" if any(e["status"] == "FAIL" for e in ui_elements) else "PASS"

    content_ok = None
    if expected_content and expected_content.strip():
        final_text = " ".join((raw.get("final_text") or "").split())
        content_ok = expected_content.strip().lower() in final_text.lower()

    final_screenshot_rel = _to_repo_relative(raw.get("final_screenshot"))
    diff_result = compare.compare_screenshots(expected_screenshot, final_screenshot_rel, **(screenshot_options or {}))

    # the script already validated the product (if one was requested) on
    # the same page its recorded actions left it on - just read that back
    product_result = raw.get("product_validation")
    if product_result and product_result.get("screenshot"):
        product_result["screenshot"] = _to_repo_relative(product_result["screenshot"])

    # FIX 4: a step backfilled as not_run (stop_on_failure halted before
    # reaching it) or a manual-input/OTP step that didn't itself fail must
    # never count against overall success - only a step that was actually
    # attempted and genuinely failed does. The step that DID trigger the
    # stop is untouched (not_run=False, success=False there) and still
    # correctly fails the run.
    def _step_counts_as_failure(s):
        if s.get("not_run"):
            return False
        if s.get("otp_role") and s.get("success") is not False:
            return False
        return not s["success"]

    steps_ok = not any(_step_counts_as_failure(s) for s in steps)

    # A script that failed before ever attempting a step (couldn't launch
    # the browser, or couldn't reach the QA URL) reports FAIL with an
    # EMPTY steps list. Left alone, every check above trivially passes on
    # an empty list ("nothing failed" reads as "nothing to report"),
    # which would misreport a run that never even started as a full PASS
    # - exactly backwards. A real recording with zero recorded actions
    # also produces an empty steps list, but the script itself reports
    # THAT as PASS (there was genuinely nothing to fail), so this only
    # fires when the script's own raw status disagrees.
    setup_failed = not steps and raw.get("status") == "FAIL"

    overall_pass = (
        steps_ok
        and not incomplete
        and ui_status == "PASS"
        and content_ok is not False
        and not (diff_result and diff_result.get("match") is False)
        and (product_result is None or product_result.get("found") is True)
        and not setup_failed
    )

    message_parts = []
    if setup_failed:
        # already a clean, user-facing sentence (see run()'s own
        # "Couldn't start the browser..."/"Couldn't reach {qa_url}..."
        # messages) - the raw technical detail lives in raw["diagnostic"]
        # instead, carried into final_result below for advanced
        # diagnostics rather than shown here.
        message_parts.append(raw.get("message") or "the test couldn't get started")
    if not steps_ok:
        # FIX 4: only genuine failures (never a not_run backfill entry or
        # an OTP step that didn't itself fail) are listed here - and the
        # summary names the FIRST one specifically, with its own recorded
        # reason, per the explicit "names the first failed step and its
        # reason" requirement, not just a bare list of indexes.
        failed_steps = [s for s in steps if _step_counts_as_failure(s)]
        failed = [s["index"] for s in failed_steps]
        message_parts.append(f"steps failed: {failed}")
        if failed_steps:
            _first = failed_steps[0]
            message_parts.append(
                f"first failure at step {_first['index']} "
                f"({_first.get('name') or _first.get('action_type')}): "
                f"{_first.get('error') or 'the tool did not record a reason (tool error)'}"
            )
    if incomplete and steps_ok:
        message_parts.append(f"replay stopped early - {incomplete} step(s) never ran")
    if ui_status == "FAIL":
        missing = [e["index"] for e in ui_elements if e["status"] == "FAIL"]
        message_parts.append(f"UI elements missing at steps: {missing}")
    if content_ok is False:
        message_parts.append("expected content not found on final page")
    if diff_result and diff_result.get("match") is False:
        message_parts.append("screenshot did not match baseline")
    if product_result is not None and not product_result.get("found"):
        message_parts.append(f"product not found: {product_to_verify.strip()}")
    if not message_parts:
        message_parts.append("all steps resolved and validations passed")

    # FIX 4: Passed/Failed/Not run/Manual-input as separate counts, so the
    # dashboard/report can show them side by side instead of a single
    # pass/fail-only tally that has no way to represent "not run at all".
    step_counts = {"passed": 0, "warnings": 0, "failed": 0, "not_run": 0, "manual_input": 0}
    for s in steps:
        if s.get("not_run"):
            step_counts["not_run"] += 1
        elif s.get("otp_role") and s.get("success") is not False:
            step_counts["manual_input"] += 1
        elif s["success"] and s.get("warning"):
            # WARNING: succeeded, but with a non-fatal note - its own count,
            # not folded into "passed" (see app.py's _summarize_steps)
            step_counts["warnings"] += 1
        elif s["success"]:
            step_counts["passed"] += 1
        else:
            step_counts["failed"] += 1

    final_result = {
        "status": "PASS" if overall_pass else "FAIL",
        "message": "; ".join(message_parts),
        "diagnostic": raw.get("diagnostic"),
        "qa_url": qa_url,
        "steps": steps,
        "step_counts": step_counts,
        "ui_elements": ui_elements,
        "ui_elements_status": ui_status,
        "content_check": content_ok,
        "screenshot_diff": diff_result,
        "product_validation": product_result,
        "final_screenshot": final_screenshot_rel,
        "run_id": run_id,
        "run_dir": _to_repo_relative(str(run_dir)),
        # OTP-STEP HANDLING / HOVER-REVEAL: carried forward from the raw
        # report so it survives this consolidation overwrite - CONFIRMED
        # REAL BUG this fixes: the script's own incremental writes (see
        # generator/script_generator.py's _hover_reveal_log/_otp_flow_log)
        # correctly wrote it to report.json throughout the run, but this
        # function's own final write below replaces the whole file with
        # `final_result`, which never included it, silently discarding
        # every line the moment the run finished - the dashboard's Live
        # Log view was never affected (it reads report.json WHILE the
        # run is still in progress, via poll_replay(), before this
        # consolidation ever happens), but a report re-opened afterward
        # showed no trace of them. None/empty for any run with neither
        # (the overwhelmingly common case), same as raw.get() elsewhere
        # on this exact object already returns.
        "live_log": raw.get("live_log"),
    }

    # report.json currently holds the RAW result the script itself wrote
    # (screenshot paths as absolute strings, no ui_elements/content_check/
    # product-validation enrichment) - overwrite it with the final,
    # enriched result so this one file, in this one run folder, is the
    # complete report for the run. Best-effort: a write failure here
    # shouldn't fail the run itself, since the caller still gets the
    # result back directly.
    try:
        output_json.write_text(json.dumps(final_result, indent=2), encoding="utf-8")
    except OSError as e:
        logger.warning("couldn't write consolidated report.json: %s", e)

    try:
        for child in sorted(run_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if child.is_dir() and not any(child.iterdir()):
                try:
                    child.rmdir()
                except OSError:
                    pass
    except OSError:
        pass

    return final_result


def execute_test(qa_url, script_path, expected_content=None, expected_screenshot=None, product_to_verify=None, recording_name=None, action_count=None, screenshot_options=None, has_otp_step=False):
    qa_url = normalize_url(qa_url)
    script_path = Path(script_path)
    script_timeout_sec = _compute_script_timeout(action_count, has_otp_step=has_otp_step)
    run_id, run_dir, output_json = _prepare_run(script_path, recording_name)
    cmd = _build_command(script_path, qa_url, output_json, run_dir, product_to_verify)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=script_timeout_sec)
        _console_rel = _save_console_output(run_dir, output_json, proc.stdout, proc.stderr)
    except subprocess.TimeoutExpired:
        logger.error("generated script timed out after %ds", script_timeout_sec)
        return _fail_result(qa_url, run_id, "test run took too long and was stopped", run_dir)

    _res = _finalize_result(
        qa_url, run_id, run_dir, output_json,
        expected_content, expected_screenshot, product_to_verify,
        proc_returncode=proc.returncode, proc_stderr=proc.stderr,
        screenshot_options=screenshot_options, action_count=action_count,
    )
    try:
        if isinstance(_res, dict) and _console_rel:
            _res["console_log"] = _console_rel          # DIAGNOSTIC: shown in the report
    except Exception:
        pass
    return _res


# ============================================================
# ASYNC REPLAY - same engine, same _finalize_result() as execute_test()
# above; the only difference is HOW the subprocess is waited on. This
# exists purely to power the dashboard's Live Replay Progress (see
# app.py's /api/test/run/start and /api/test/run/progress): a blocking
# call can't report "step 3 of 12" while it's still blocked. Popen here
# instead of subprocess.run so the calling thread can return immediately;
# a dedicated watcher thread per run then waits for it to exit and calls
# the exact same _finalize_result() execute_test() already uses - no
# second interpretation of a report.json, no second replay engine.
#
# The generated script itself already writes its own report.json
# incrementally, once per completed step (see run()'s per-step
# _write_result() calls in generator/script_generator.py) - this registry
# doesn't need to track step-by-step progress itself, it only needs to
# know WHERE that file is and whether the process has finished yet;
# poll_replay() just reads whatever the script has written so far.
# ============================================================

_active_replays = {}
_active_replays_lock = threading.Lock()


def _save_console_output(run_dir, output_json, stdout, stderr):
    """DIAGNOSTIC (logging only): the replay script's full console output (every locator method's verdict, every
    wait) saved as replay_console.txt in the run folder, and its path written into report.json as
    "console_log". Returns the repo-relative path or None. Never raises."""
    try:
        path = Path(run_dir) / "replay_console.txt"
        text = (stdout or "")
        if stderr:
            text += chr(10) + chr(10) + "===== stderr =====" + chr(10) + stderr
        path.write_text(text, encoding="utf-8", errors="replace")
        rel = _to_repo_relative(str(path))
        try:
            oj = Path(output_json)
            if oj.exists():
                data = json.loads(oj.read_text(encoding="utf-8"))
                data["console_log"] = rel
                oj.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("console log path not added to report.json: %s", e)
        return rel
    except Exception as e:
        logger.warning("replay console output not saved: %s", e)
        return None


def _watch_replay(run_id, proc, script_timeout_sec, qa_url, run_dir, output_json, expected_content, expected_screenshot, product_to_verify, screenshot_options=None):
    try:
        _stdout, stderr = proc.communicate(timeout=script_timeout_sec)
        _console_rel = _save_console_output(run_dir, output_json, _stdout, stderr)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
            _o, _e = proc.communicate()
            _save_console_output(run_dir, output_json, _o, _e)
        except Exception:
            pass
        logger.error("generated script timed out after %ds", script_timeout_sec)
        result = _fail_result(qa_url, run_id, "test run took too long and was stopped", run_dir)
        with _active_replays_lock:
            entry = _active_replays.get(run_id)
            if entry is not None:
                entry["done"] = True
                entry["result"] = result
        return

    result = _finalize_result(
        qa_url, run_id, run_dir, output_json,
        expected_content, expected_screenshot, product_to_verify,
        proc_returncode=proc.returncode, proc_stderr=stderr,
        screenshot_options=screenshot_options, action_count=action_count,
    )

    try:
        if isinstance(result, dict) and _console_rel:
            result["console_log"] = _console_rel        # DIAGNOSTIC: shown in the report
    except Exception:
        pass

    with _active_replays_lock:
        entry = _active_replays.get(run_id)
        if entry is not None:
            entry["done"] = True
            entry["result"] = result


def start_replay(qa_url, script_path, expected_content=None, expected_screenshot=None, product_to_verify=None, recording_name=None, action_count=None, screenshot_options=None, has_otp_step=False):
    """Starts a replay the same way execute_test() does, but returns as
    soon as the subprocess is launched instead of blocking until it
    finishes. Returns (run_id, run_dir_repo_relative, total_steps_hint)
    - total_steps_hint is None until the script itself writes it into
    report.json (see run()'s own `result["total_steps"] = total_steps`),
    which poll_replay() picks up from there.
    """
    qa_url = normalize_url(qa_url)
    script_path = Path(script_path)
    script_timeout_sec = _compute_script_timeout(action_count, has_otp_step=has_otp_step)
    run_id, run_dir, output_json = _prepare_run(script_path, recording_name)
    cmd = _build_command(script_path, qa_url, output_json, run_dir, product_to_verify)

    # the live log acknowledges each step's "Running" line before the browser
    # acts on it (see generator/script_generator.py's _wait_live_ack)
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
        env={**os.environ, "AUTOFLOW_LIVE_ACK": "1"},
    )

    with _active_replays_lock:
        _active_replays[run_id] = {"done": False, "result": None, "run_dir": run_dir, "output_json": output_json}

    watcher = threading.Thread(
        target=_watch_replay,
        args=(run_id, proc, script_timeout_sec, qa_url, run_dir, output_json, expected_content, expected_screenshot, product_to_verify),
        kwargs={"screenshot_options": screenshot_options},
        daemon=True,
    )
    watcher.start()

    return run_id, _to_repo_relative(str(run_dir))


def poll_replay(run_id):
    """Read-only: reports how far a start_replay() run has gotten. While
    still running, reads report.json directly (best-effort - the file may
    not exist yet, or be mid-write) for the step list the script has
    written so far; once the watcher thread has finalized the run, returns
    the exact same enriched result execute_test() would have returned.

    Returns None if run_id is unknown (never started, or this process
    restarted since - in-memory only, same lifetime tradeoff the existing
    recording-session state in app.py already accepts).
    """
    with _active_replays_lock:
        entry = _active_replays.get(run_id)

    if entry is None:
        return None

    if entry["done"]:
        return {"done": True, "result": entry["result"]}

    steps = []
    total_steps = None
    awaiting_otp = None
    live_log = []
    current_step = None
    try:
        raw = json.loads(entry["output_json"].read_text(encoding="utf-8"))
        steps = raw.get("steps", [])
        total_steps = raw.get("total_steps")
        # LIVE LOG SYNC: what the step that's running RIGHT NOW is doing
        # (index/phase/started_at) - written by the generated script the
        # moment each step starts and at each sub-phase (see its
        # _live_phase); None between steps and for an older script that
        # predates it, in which case the stream falls back to inferring
        # the running step from the finished-step count, as before.
        current_step = raw.get("current_step")
        # OTP-STEP HANDLING: both are None/empty for the overwhelmingly
        # common case of a recording with no OTP-shaped step (see
        # generator/script_generator.py's own _detect_otp_flow_roles) -
        # only present at all once that script actually starts writing
        # them, which only ever happens for a recognized OTP flow.
        awaiting_otp = raw.get("awaiting_otp")
        live_log = raw.get("live_log") or []
    except (OSError, json.JSONDecodeError):
        # not written yet, or caught mid-write (a partial JSON parse
        # failure here just means "nothing new to report this poll" -
        # the next poll a moment later reads the completed write)
        pass

    return {
        "done": False,
        "output_json": str(entry["output_json"]),
        "steps": steps,
        "total_steps": total_steps,
        "awaiting_otp": awaiting_otp,
        "live_log": live_log,
        "current_step": current_step,
    }
