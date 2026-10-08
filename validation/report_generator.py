"""Builds the self-contained HTML report for a test run.

Screenshots get inlined as base64 data URIs so the report is a single
file someone can email around without also having to hand over the
screenshots folder.
"""
import base64
import logging
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from jinja2 import Environment, FileSystemLoader

from storage.repository import BASE_DIR

logger = logging.getLogger(__name__)

# PHASE 4a: turns one of the replay engine's own technical error/warning
# strings into ONE plain-English sentence a non-developer can read at a
# glance - the technical text itself is NEVER altered, only accompanied
# by this (see report.html's own "Details" disclosure, and static/js/
# script.js's _plainLanguageReason() for the same logic on the dashboard
# card/live log side - kept in sync if this policy ever changes). A
# standalone copy here (not imported from generator/script_generator.py)
# because that whole file is one large string.Template - none of its own
# functions are directly importable from another module.
_NOT_RUN_STEP_RE = re.compile(r"NOT RUN \(stopped after step (\d+) failed\)")
_VALUE_MISMATCH_RE = re.compile(
    r"expected(?:\s+exactly)?\s+['‘]([^'’]*)['’],?\s*(?:found|got)\s+['‘]([^'’]*)['’]",
    re.IGNORECASE,
)


def _url_path_label(url):
    if not url:
        return "(unknown page)"
    try:
        parts = urlsplit(url)
        return (parts.path or "/") + (("?" + parts.query) if parts.query else "")
    except Exception:
        return url


_PAGE_MISMATCH_RE = re.compile(r"expected to reach ['\"](.+?)['\"], but landed on ['\"](.+?)['\"] instead", re.DOTALL)
_PLAIN_PREFIXES = ("Warning:", "Note:", "Failed:")


def _path_only(url):
    """origin-less path of a URL (query/fragment dropped) for a headline;
    full URLs belong only in Details."""
    try:
        return (urlsplit(url).path or "/")
    except Exception:
        return str(url)


def strip_fail_wrapper(text):
    """'Failed: <reason> The replay stopped.' -> '<reason>' - used when a
    failure reason is embedded in a longer sentence ('Not run because ...')."""
    t = (text or "").strip()
    if t.startswith("Failed:"):
        t = t[len("Failed:"):].strip()
    for tail in (" The replay stopped.", " Continuing."):
        if t.endswith(tail):
            t = t[: -len(tail)]
    return t.rstrip(".")


_TECHNICAL_RE = re.compile(
    r"DOM|locator|xpath|css_path|selector|strateg|hit-test|bounding|Page\.|Mouse\.|Locator\.|Target page|"
    r"act_target|state_target|tier|evaluate|_|\[[a-z-]+\]|Traceback|Exception|Error:|timeout \d|Timeout \d",
    re.I)

# (pattern, plain sentence or function(label, match)) - checked in order
_PLAIN_TABLE = [
    (r"found in DOM but not visible/painted|never finished rendering",
     lambda lbl, m: f"Failed: '{lbl}' was on the page but never showed up on screen the way it should after the previous step. The replay stopped."),
    (r"navigated to modal URL but expected modal content did not render|click likely did not trigger",
     "Failed: A popup was expected to open after the click, but its content never appeared. The replay stopped."),
    (r"hover did not reveal its recorded target",
     lambda lbl, m: f"Failed: Hovering did not open the menu that holds '{lbl}'. The replay stopped."),
    (r"scroll did not reach target position",
     "Failed: The page could not be scrolled to the same place as in the recording because its content changed. The replay stopped."),
    (r"never appeared on this page within the wait window",
     "Warning: The next item took a long time to appear, so the page may not have finished loading. Continuing."),
    (r"click executed but its expected effect was not observed",
     lambda lbl, m: f"Failed: Clicked '{lbl}', but the page did not go where it went during recording. The replay stopped."),
    (r"Target page, context or browser has been closed|replay could not continue",
     "Failed: The browser window was closed while the replay was running. The replay stopped."),
    (r"count_elements: expected (\d+) elements?, found (\d+)",
     lambda lbl, m: f"Failed: Expected {m.group(1)} items on the page, but found {m.group(2)}. The replay stopped."),
    (r"validate_element failed: element is enabled \(expected disabled\)",
     lambda lbl, m: f"Failed: '{lbl}' is enabled, but it was expected to be disabled. The replay stopped."),
    (r"validate_element failed: element is disabled \(expected enabled\)",
     lambda lbl, m: f"Failed: '{lbl}' is disabled, but it was expected to be enabled. The replay stopped."),
    (r"could not convert string to float",
     "Failed: A value on the page could not be read as a number. The replay stopped."),
    (r"tab_close failed|Cannot close the last tab",
     "Failed: There was no other tab left to close. The replay stopped."),
    (r"validate_url: expected URL",
     "Failed: The page address is not the one that was expected. The replay stopped."),
    (r"No count saved as",
     "Failed: No saved count with that name exists yet. The replay stopped."),
    (r"act_target could not be resolved live",
     "Warning: The checkbox could not be found directly, so its visible label was clicked instead. The test continued."),
    (r"recorded target not found - used same position",
     "Warning: The recorded item could not be found by its details, so AutoFlow used its position on the page. The test continued."),
    (r"required an un-recorded hover-reveal",
     "Warning: The item was hidden, so AutoFlow hovered over its menu to show it. The test continued."),
    (r"recorded click position was stale",
     "Warning: The recorded click position no longer matched, so AutoFlow found the item by its name instead. The test continued."),
    (r"Text of this element changed on the site",
     "Warning: The text of this item changed since the recording. The test continued."),
    (r"Page\.\w+: |Mouse\.\w+: |Locator\.\w+: ",
     "Failed: The browser stopped responding at this step. The replay stopped."),
]


def plain_language_reason(element_label, error_text):
    """Returns a plain sentence for error_text, or None when error_text
    itself is empty/None. Falls back to returning error_text UNCHANGED
    when its shape isn't recognized, rather than inventing a sentence
    that might misdescribe an error this doesn't actually understand.

    Every FAIL/WARNING headline follows "<what was expected> / <what
    happened> / <what the replay did>": the replay engine already writes
    most of them in that form (a "Failed:" / "Warning:" / "Note:" text,
    passed through as is); the rest - older engine messages and
    recordings - are translated here. Technical text (selectors, full
    URLs, boxes) is never part of the headline."""
    if not error_text:
        return None
    e = str(error_text)

    m = _NOT_RUN_STEP_RE.search(e)
    if m:
        # "NOT RUN (stopped after step N failed): <reason of that failure>"
        tail = e[m.end():].lstrip(": ").strip()
        reason = plain_language_reason(element_label, tail) if tail else None
        reason = strip_fail_wrapper(reason) if reason else ""
        return f"Not run because step {m.group(1)} failed" + (f": {reason}." if reason else ".")

    if e.lstrip().startswith(_PLAIN_PREFIXES):
        return e  # already a plain-English headline from the replay engine

    if "Value changed on the site" in e:
        return e  # already a plain sentence - Phase 1a's own wording

    if "next recorded step's target never appeared" in e:
        # FOLLOW-UP FIX (Part 1d): the technical wording stays as the raw
        # "warning" text (shown under this same Details disclosure, via
        # the caller's own plain-vs-raw comparison), only ever attached
        # at all once the very next step's own outcome showed real
        # trouble - see script_generator.py's own per-step tail comment.
        return "Warning: The page took longer than usual to show the next item. Continuing."

    pm = _PAGE_MISMATCH_RE.search(e)
    if pm:
        return (
            f"Failed: Expected to open '{_path_only(pm.group(1))}' but the browser went to "
            f"'{_path_only(pm.group(2))}' instead. The replay stopped."
        )

    if "forced hard-navigation fallback" in e and "treating as failed" in e:
        return (
            "Failed: Expected the page to open after the click, but it only loaded when opened "
            "directly by its address, and it could not be confirmed to be the right page. The replay stopped."
        )

    if "forced hard-navigation fallback" in e:
        return "Note: The page was opened directly by its address because the click did not open it by itself."

    if "unusually large bounding box" in e:
        return (
            "Warning: The recorded click covered a large area of the page, so the replay may not "
            "click exactly the same spot. Continuing."
        )

    if "content-mismatch" in e or "a different element is actually at the recorded click position" in e:
        return (
            f"Failed: Wanted to click '{element_label}' but a different item is on the page now. "
            "The replay stopped."
        )

    if "not hit-testable" in e or "popup is covering" in e:
        return (
            f"Failed: Something on the page (a popup or menu) was covering '{element_label}'. "
            "The replay stopped."
        )

    m2 = _VALUE_MISMATCH_RE.search(e)
    if m2:
        return f"Failed: Expected {m2.group(1)!r}, found {m2.group(2)!r}. The replay stopped."

    if re.search(r"checked for \d+(\.\d+)?s\s*$", e) and ("timed out" in e.lower() or "timeout" in e.lower()):
        return "Failed: The page took too long to respond at this step. The replay stopped."

    if "could not be resolved" in e or "none of the locator strategies" in e or "could not uniquely resolve" in e:
        return f"Failed: Wanted to use '{element_label}' but it is not on the page now. The replay stopped."

    if e.startswith("drag produced no observable effect"):
        return "Failed: The drag did not change anything on the page. The replay stopped."

    # ---- older / low-level engine messages: always said in plain words (the raw text stays in Details)
    for rx, said in _PLAIN_TABLE:
        mm = re.search(rx, e, re.I | re.S)
        if mm:
            return said(element_label, mm) if callable(said) else said

    # a message that still reads technical is never shown as the headline
    if _TECHNICAL_RE.search(e):
        return "Failed: Something unexpected stopped this step. The replay stopped."

    return e


def step_headline(step, element_label):
    """The ONE plain-English headline for a step's WARNING / FAIL / NOT-RUN
    line, shared by the live log and the HTML report so they always agree.
    None for a clean pass. Guarantees the form: a FAIL starts with
    "Failed:" and says the replay stopped; a WARNING starts with
    "Warning:"/"Note:" and says it continued."""
    err, warn = step.get("error"), step.get("warning")
    label = element_label or step.get("name") or step.get("action_type") or "This step"
    if step.get("not_run"):
        return plain_language_reason(label, err)
    if step.get("success"):
        if not warn:
            return None
        text = plain_language_reason(label, warn)
        if text and not text.lstrip().startswith(_PLAIN_PREFIXES):
            text = f"Warning: {text} Continuing."
        return text
    text = plain_language_reason(label, err or warn)
    if text and not text.lstrip().startswith(_PLAIN_PREFIXES):
        text = f"Failed: {text} The replay stopped."
    return text


TEMPLATES_DIR = BASE_DIR / "templates"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

# same set the dashboard's own script.js (VALIDATION_ACTION_TYPES) uses to
# tell an assertion-style step (validate_*/check_checked/compare_*/...)
# apart from an interaction or a passive data capture - kept in sync with
# it by hand, since the two live in different files with no shared config
VALIDATION_ACTION_TYPES = {
    "validate", "validate_element", "validate_text", "validate_attribute",
    "validate_visible", "validate_url", "validate_value", "validate_enabled",
    "check_checked", "validate_value_range", "compare_value",
    "compare_counts", "count_summary", "detect_duplicates",
    "compare_list_overlap",
}


def _to_data_uri(rel_path):
    if not rel_path:
        return None
    full = BASE_DIR / rel_path
    if not full.exists():
        return None
    try:
        data = base64.b64encode(full.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{data}"
    except OSError as e:
        logger.warning("couldn't embed screenshot %s: %s", rel_path, e)
        return None


def _step_outcome(s):
    """FIX 4 (report/live-log correctness): a step the generator flagged
    not_run (stop_on_failure halted before reaching it) or otp_role (a
    manual-input/OTP step that didn't itself fail) is neither a pass nor a
    genuine failure - CONFIRMED REAL BUG this fixes, against an actual
    Myntra recording: the downloadable report counted 48 never-attempted
    steps as "failed" and listed the first of them as the failure reason.
    Kept in sync with static/js/script.js's own _stepOutcome() by
    construction (same fields, same precedence).

    FOLLOW-UP FIX 2: "warning" is its own outcome now too - a step that
    SUCCEEDED but carries a non-fatal note (e.g. Fix 1's "Value changed
    on the site..." note) - never indistinguishable from a clean pass.
    """
    if s.get("not_run"):
        return "not_run"
    if s.get("otp_role") and s.get("success") is not False:
        return "manual_input"
    if s.get("success") and s.get("warning"):
        return "warning"
    return "pass" if s.get("success") else "fail"


def honest_summary(steps, total):
    """Plain sentence for a run with no failed / not-run step. "Matched the
    recording: all N steps passed" only when every step did exactly the recorded
    action; a step that used a workaround (Escape, a fallback locator, ...) or
    carries a warning is named."""
    steps = steps or []
    work = [s.get("index") for s in steps if s.get("success") and s.get("workarounds")]
    warn = [s.get("index") for s in steps if s.get("success") and s.get("warning") and not s.get("workarounds")]

    def _see(idx):
        return "step " + ", ".join(str(i) for i in idx) if len(idx) == 1 else "steps " + ", ".join(str(i) for i in idx)

    # "all N steps passed" only when every one of the N steps really ran and passed
    _ran_ok = sum(1 for s in steps if s.get("success") is not False and not s.get("not_run"))
    if _ran_ok < total:
        return f"Replay finished: {_ran_ok}/{total} steps passed."
    if not work and not warn:
        return f"Replay matched the recording: all {total} steps passed."
    parts = []
    if work:
        parts.append(f"{total - len(work) - len(warn)} step{'s' if total - len(work) - len(warn) != 1 else ''} matched the recording, "
                     f"{len(work)} step{'s' if len(work) != 1 else ''} needed a workaround (see {_see(work)})")
    else:
        parts.append(f"{total - len(warn)} step{'s' if total - len(warn) != 1 else ''} matched the recording")
    if warn:
        parts.append(f"{len(warn)} step{'s' if len(warn) != 1 else ''} passed with a warning (see {_see(warn)})")
    return ", ".join(parts) + "."


def _plain_summary(steps, execution_summary):
    """PHASE 4c: one plain sentence on whether replay matched the
    recording overall - never changes pass/fail logic itself, purely a
    wording layer over execution_summary's own, already-computed counts.
    """
    total = execution_summary["total"]
    if total == 0:
        return "Replay finished with no steps to report."
    if execution_summary["failed"] == 0 and execution_summary["not_run"] == 0:
        return honest_summary(steps, total)
    first_failed = execution_summary.get("first_failed")
    if first_failed:
        reason = first_failed.get("plain_reason") or first_failed.get("error") or "an unknown error"
        return f"Replay stopped at step {first_failed.get('index')}: {reason}"
    return f"Replay finished: {execution_summary['passed'] + execution_summary['warnings']}/{total} steps passed."


def generate_report(execution_result: dict, output_dir: Path = None) -> Path:
    template = _env.get_template("report.html")

    # PHASE 4b: the ORIGINAL recorded actions, index-matched to
    # execution_result["steps"] by their shared 1-based "index" - the
    # exact same data app.py's own live-log SSE stream already threads
    # through for its per-step element label (_run_meta[run_id]
    # ["actions"], set from test_case.get("actions") when the run
    # starts - see api_test_run_start). Absent entirely for a run
    # started before this existed; the column then simply shows "-" for
    # every step, no re-run and no new capture logic anywhere.
    recorded_actions = execution_result.get("recorded_actions") or []

    steps = []
    for s in execution_result.get("steps", []):
        # PHASE 4a: element_label reuses this step's own name (the same
        # human-readable label the report/editor already show elsewhere -
        # see generator/script_generator.py's _derive_action_name) rather
        # than re-deriving a second one.
        element_label = s.get("name") or s.get("action_type") or "This step"
        # a step that SUCCEEDED explains its WARNING, not an informational
        # resolution note left in `error` (see app.py's _step_failure_reason)
        reason_source = (s.get("warning") or s.get("error")) if s.get("success") else (s.get("error") or s.get("warning"))
        idx = s.get("index")
        recorded_action = (
            recorded_actions[idx - 1] if isinstance(idx, int) and 0 < idx <= len(recorded_actions) else {}
        )
        recorded_lp = recorded_action.get("locator_profile") or {}
        # FIX 2: same screenshot_data pattern as the step's own main
        # screenshot above - Jinja can't call _to_data_uri directly, so
        # it's precomputed here, once, for the mismatch's own evidence
        # screenshot.
        _pm_info = s.get("page_mismatch_info")
        if _pm_info and _pm_info.get("screenshot"):
            _pm_info = {**_pm_info, "screenshot_data": _to_data_uri(_pm_info.get("screenshot"))}

        # FIX 4: a FAIL without a reason is itself a tool error - never an
        # empty reason in the report
        if _step_outcome(s) == "fail" and not (reason_source or "").strip():
            s = {**s, "error": (
                "The step failed but the tool did not record why - this is a tool error, "
                "not necessarily a problem with the site"
            )}
            reason_source = s["error"]
            logger.error("report: step %s is a FAIL with no recorded reason", s.get("index"))
        steps.append({
            **s,
            "screenshot_data": _to_data_uri(s.get("screenshot")),
            "page_mismatch_info": _pm_info,
            "outcome": _step_outcome(s),
            "plain_reason": step_headline(s, element_label),
            # PHASE 4b: "Recorded vs Replayed" - the recorded URL/element
            # text next to what replay actually found. "actual" (set only
            # for a validate_* step - see generator/script_generator.py's
            # own expected_value/actual_value) is the one existing field
            # that already captures "what replay found" as text; every
            # other action type shows "-" there rather than a guess, since
            # no per-step "live element text" is otherwise captured today.
            "recorded_url": recorded_action.get("page_url"),
            "recorded_text": recorded_lp.get("text") or recorded_lp.get("accessible_name"),
            "replayed_url": s.get("url_after") or s.get("url_before"),
            "replayed_text": s.get("actual"),
        })

    ui_elements = execution_result.get("ui_elements", [])
    execution_summary = {
        "total": len(steps),
        # WARNING is its own status next to PASS/FAIL: "passed" is CLEAN
        # passes only, "warnings" is the steps that succeeded with a
        # non-fatal note - so Passed + Warnings + Failed + Not run + Manual
        # input add up to the total, and a warning is never counted twice
        "passed": sum(1 for s in steps if s["outcome"] == "pass"),
        "warnings": sum(1 for s in steps if s["outcome"] == "warning"),
        "failed": sum(1 for s in steps if s["outcome"] == "fail"),
        "not_run": sum(1 for s in steps if s["outcome"] == "not_run"),
        "manual_input": sum(1 for s in steps if s["outcome"] == "manual_input"),
        "first_failed": next((s for s in steps if s["outcome"] == "fail"), None),
    }
    plain_summary = _plain_summary(steps, execution_summary)
    ui_summary = {
        "total": len(ui_elements),
        "found": sum(1 for e in ui_elements if e.get("status") == "PASS"),
        "missing": sum(1 for e in ui_elements if e.get("status") == "FAIL"),
        "status": execution_result.get("ui_elements_status"),
    }

    product_validation = execution_result.get("product_validation")
    if product_validation:
        product_validation = {**product_validation, "screenshot_data": _to_data_uri(product_validation.get("screenshot"))}

    # step-level validation breakdown for the report's own "Step
    # Validations" section - same distinction (and same numbers) the
    # dashboard's live validation panel already shows (see
    # VALIDATION_ACTION_TYPES in static/js/script.js), so the downloadable
    # report never disagrees with what was shown live.
    validation_steps = [s for s in steps if s.get("action_type") in VALIDATION_ACTION_TYPES]
    action_steps = [s for s in steps if s.get("action_type") not in VALIDATION_ACTION_TYPES]
    validation_summary = {
        "actions_passed": sum(1 for s in action_steps if s["outcome"] == "pass"),
        "actions_total": len(action_steps),
        "validations_passed": sum(1 for s in validation_steps if s["outcome"] == "pass"),
        "validations_total": len(validation_steps),
        "failed_total": sum(1 for s in steps if s["outcome"] == "fail"),
        "not_run_total": sum(1 for s in steps if s["outcome"] == "not_run"),
        "manual_input_total": sum(1 for s in steps if s["outcome"] == "manual_input"),
        "locator_warnings": sum(1 for s in steps if (s.get("locator_report") or {}).get("weak")),
    }

    html = template.render(
        result=execution_result,
        steps=steps,
        ui_elements=ui_elements,
        ui_summary=ui_summary,
        execution_summary=execution_summary,
        plain_summary=plain_summary,
        validation_steps=validation_steps,
        validation_summary=validation_summary,
        product_validation=product_validation,
        final_screenshot_data=_to_data_uri(execution_result.get("final_screenshot")),
        generated_at=datetime.now().isoformat(),
    )

    # a caller with a per-run output folder already (the dashboard's Run
    # Test flow - see execute_test in executor/run_execution.py) passes
    # it here so the HTML report lands alongside that same run's
    # screenshots and report.json instead of its own separate top-level
    # location. Falls back to the old shared REPORTS_DIR only for a
    # caller that doesn't have a per-run folder to give it.
    if output_dir:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / "report.html"
    else:
        run_id = execution_result.get("run_id") or datetime.now().strftime("%Y%m%d_%H%M%S")
        path = REPORTS_DIR / f"report_{run_id}.html"
    path.write_text(html, encoding="utf-8")
    logger.info("wrote report to %s", path)
    return path
