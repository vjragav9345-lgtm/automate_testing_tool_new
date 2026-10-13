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
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from storage.repository import BASE_DIR
from utils import normalize_url
from validation import compare

logger = logging.getLogger(__name__)

SCRIPT_TIMEOUT_SEC = 120


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
        "qa_url": qa_url,
        "steps": [],
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
    second time, we're just reporting that outcome as its own section."""
    ui_elements = []
    for s in steps:
        if s.get("action_type") in ("navigate", "scroll"):
            continue  # nothing to "find" for a navigation or scroll step
        found = bool(s.get("element_found"))
        strategy = s.get("strategy_used")
        not_executed = (s.get("error") or "").startswith("not executed")
        if not_executed:
            message = "Step was never executed - replay stopped before reaching it"
        elif not found:
            message = "Expected UI element was not found"
        else:
            message = None
        ui_elements.append({
            "index": s["index"],
            "action_type": s.get("action_type"),
            "element_found": found,
            "locator_used": strategy if strategy != "bounding_box" else None,
            "status": "PASS" if found else "FAIL",
            "message": message,
        })
    return ui_elements


def execute_test(qa_url, script_path, expected_content=None, expected_screenshot=None, product_to_verify=None, recording_name=None):
    qa_url = normalize_url(qa_url)
    script_path = Path(script_path)
    # one dedicated folder for EVERYTHING this run produces - the
    # sequential img1.png, img2.png, ... screenshots (including product-
    # validation's own capture) and the report data below - instead of
    # each kind of output picking its own top-level location. Single
    # top-level screenshots/<name>_<timestamp>/ folder at the project
    # root, same naming convention the generated script's own run() uses
    # for its script-relative fallback when executed directly.
    run_id = f"{_slug(recording_name or script_path.stem) or 'run'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir = BASE_DIR / "screenshots" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    output_json = run_dir / "report.json"

    # "1" = headless - this is an unattended dashboard-triggered run, not
    # someone watching a terminal, so no visible browser should pop up.
    # (Running the generated script by hand defaults to headed instead -
    # see the script's own __main__ block.) The optional 5th arg is the
    # product name - the script validates it on whatever page the recorded
    # actions ended on, in this SAME process, not a second session here.
    cmd = [sys.executable, str(script_path), qa_url, str(output_json), str(run_dir), "1", product_to_verify or ""]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=SCRIPT_TIMEOUT_SEC)
    except subprocess.TimeoutExpired:
        logger.error("generated script timed out after %ds", SCRIPT_TIMEOUT_SEC)
        return _fail_result(qa_url, run_id, "test run took too long and was stopped", run_dir)

    if not output_json.exists():
        logger.error("generated script produced no result (exit %s): %s", proc.returncode, proc.stderr[-2000:])
        return _fail_result(qa_url, run_id, "the test script didn't complete - couldn't reach the QA URL or it crashed", run_dir)

    try:
        raw = json.loads(output_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.error("couldn't read execution result: %s", e)
        return _fail_result(qa_url, run_id, "couldn't read the test run's result file", run_dir)

    steps = raw.get("steps", [])
    for s in steps:
        s["screenshot"] = _to_repo_relative(s.get("screenshot"))
        s["fragile"] = s.get("strategy_used") in ("text+tag", "bounding_box")

    ui_elements = _build_ui_elements(steps)
    ui_status = "PASS" if all(e["status"] == "PASS" for e in ui_elements) else "FAIL"

    content_ok = None
    if expected_content and expected_content.strip():
        final_text = " ".join((raw.get("final_text") or "").split())
        content_ok = expected_content.strip().lower() in final_text.lower()

    final_screenshot_rel = _to_repo_relative(raw.get("final_screenshot"))
    diff_result = compare.compare_screenshots(expected_screenshot, final_screenshot_rel)

    # the script already validated the product (if one was requested) on
    # the same page its recorded actions left it on - just read that back
    product_result = raw.get("product_validation")
    if product_result and product_result.get("screenshot"):
        product_result["screenshot"] = _to_repo_relative(product_result["screenshot"])

    steps_ok = all(s["success"] for s in steps) if steps else True
    overall_pass = (
        steps_ok
        and ui_status == "PASS"
        and content_ok is not False
        and not (diff_result and diff_result.get("match") is False)
        and (product_result is None or product_result.get("found") is True)
    )

    message_parts = []
    if not steps_ok:
        failed = [s["index"] for s in steps if not s["success"]]
        message_parts.append(f"steps failed: {failed}")
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

    final_result = {
        "status": "PASS" if overall_pass else "FAIL",
        "message": "; ".join(message_parts),
        "qa_url": qa_url,
        "steps": steps,
        "ui_elements": ui_elements,
        "ui_elements_status": ui_status,
        "content_check": content_ok,
        "screenshot_diff": diff_result,
        "product_validation": product_result,
        "final_screenshot": final_screenshot_rel,
        "run_id": run_id,
        "run_dir": _to_repo_relative(str(run_dir)),
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

    return final_result
