"""AutoFlow QA dashboard - Flask app tying the frontend to the Playwright
automation engine.

Recording is no longer a separate UI step. Clicking Launch Browser opens
the user-supplied URL and immediately starts the Recorder on it; the
terminal becomes the recording control - actions print live as they
happen, and pressing ENTER in the terminal stops and saves the session.

That whole lifecycle (launch, record, wait for ENTER, stop, save) runs on
one dedicated background thread per session, not on Flask's request
thread. Two reasons:
  - Playwright's sync API is tied to the OS thread that created it, so
    whatever thread launches the browser has to be the one used for the
    rest of that session's calls.
  - Waiting for a terminal ENTER can take an arbitrary amount of time,
    and Flask needs to stay responsive (status checks, QA replay runs)
    while that's happening.
Everything else (QA replay, product validation, report) is unaffected by
this - /api/test/run already runs the generated script (which also does
product validation, if requested) as its own subprocess, so it never
touches this thread's Playwright objects.
"""

import json
import logging
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PWTimeoutError,
    Error as PWError,
)

from storage import repository
from storage.repository import BASE_DIR
from utils import normalize_url, attach_dialog_handler
from recorder.record_session import Recorder
from generator.script_generator import generate_script, EDITED_OUTPUT_DIR
from executor.run_execution import execute_test
from validation.report_generator import generate_report


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

app = Flask(__name__)

PAGE_LOAD_TIMEOUT = 30000


# Thread-safe recording status.
session_state = {
    "active": False,
    "recording": False,
    "current_url": None,
}

state_lock = threading.Lock()


def _finish_recording(
    recorder,
    stop_reason="terminal_enter",
    closed_note=None,
):
    """Stops recorder, saves JSON and generates the normal script."""

    name = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    test_case = recorder.stop(
        name=name,
        stop_reason=stop_reason,
    )

    captured_count = len(test_case["actions"])
    saved_count = None

    path = repository.save_recording(test_case)

    # Validate saved JSON, and confirm what actually landed on disk matches
    # what was captured in memory - a silent drop here would mean the
    # generated script (and every later replay) is missing actions without
    # any visible sign of it.
    try:
        with open(path, encoding="utf-8") as f:
            saved_data = json.load(f)

        saved_count = len(saved_data.get("actions", []))
        if saved_count != captured_count:
            print(
                f"\nWARNING: action count mismatch - "
                f"captured {captured_count} but JSON has {saved_count}\n",
                flush=True,
            )

    except (OSError, json.JSONDecodeError) as e:
        logger.error(
            "saved recording failed validation: %s",
            e,
        )

        print(
            f"\nWARNING: saved JSON failed to validate: {e}\n",
            flush=True,
        )

    if closed_note:
        print(
            f"\n{'=' * 50}\n"
            f"{closed_note}\n\n"
            f"Actions captured: {len(test_case['actions'])}\n"
            f"{'=' * 50}",
            flush=True,
        )

    # Existing script generation remains unchanged.
    try:
        script_path = generate_script(test_case)

        script_line = (
            f"\nPython script generated:\n"
            f"{script_path}\n"
        )

    except Exception as e:
        logger.error(
            "script generation failed: %s",
            e,
        )

        script_line = (
            f"\nPython script generation FAILED:\n"
            f"{e}\n"
        )

    print(
        "\n"
        + "=" * 50
        + f"\nRECORDING COMPLETED\n\n"
        f"Total actions captured: {captured_count}\n"
        f"JSON actions saved: {saved_count}\n"
        f"Stop reason: {stop_reason}\n\n"
        f"JSON saved:\n"
        f"{path}\n"
        f"{script_line}"
        + "=" * 50
        + "\n",
        flush=True,
    )

    with state_lock:
        session_state["recording"] = False

    return path


def _run_recording_session(
    url,
    ready_event,
    ready_result,
):
    """Runs the browser recording session on its own thread."""

    pw = None
    browser = None
    recorder = None

    try:
        pw = sync_playwright().start()

        try:
            browser = pw.chromium.launch(
                headless=False
            )

        except Exception as e:
            logger.warning(
                "headed browser launch failed (%s), "
                "falling back to headless",
                e,
            )

            browser = pw.chromium.launch(
                headless=True
            )

        context = browser.new_context()

        page = context.new_page()

        page.set_default_timeout(8000)

        attach_dialog_handler(page)

        try:
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=PAGE_LOAD_TIMEOUT,
            )

            try:
                page.wait_for_load_state(
                    "networkidle",
                    timeout=8000,
                )

            except PWTimeoutError:
                pass

            title = page.title()

            # img1 for this launch: its own screenshots/<timestamp>/
            # folder, the same per-run convention the replay side uses -
            # best-effort only, a screenshot failure here must never
            # block the browser launch itself
            try:
                launch_shot_dir = (
                    BASE_DIR / "screenshots" /
                    datetime.now().strftime("%Y%m%d_%H%M%S")
                )
                launch_shot_dir.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(launch_shot_dir / "img1.png"))
            except Exception as e:
                logger.warning("couldn't capture initial-load screenshot: %s", e)

            ready_result.update(
                {
                    "success": True,
                    "message": (
                        "page loaded, recording started "
                        "automatically"
                    ),
                    "url": page.url,
                    "page_title": title,
                }
            )

        except PWTimeoutError:

            logger.warning(
                "timed out loading %s",
                url,
            )

            ready_result.update(
                {
                    "success": False,
                    "message": (
                        "page took too long to respond"
                    ),
                    "url": url,
                    "page_title": None,
                }
            )

            ready_event.set()
            return

        except PWError as e:

            logger.error(
                "couldn't launch/navigate to %s: %s",
                url,
                e,
            )

            ready_result.update(
                {
                    "success": False,
                    "message": (
                        "Couldn't reach that URL - "
                        "check it's correct and try again."
                    ),
                    "url": url,
                    "page_title": None,
                }
            )

            ready_event.set()
            return

        with state_lock:
            session_state["active"] = True
            session_state["recording"] = True
            session_state["current_url"] = page.url

        recorder = Recorder(page)

        recorder.start()

        def _on_new_page(new_page):

            try:
                new_page.wait_for_load_state(
                    "domcontentloaded",
                    timeout=10000,
                )

            except Exception:
                pass

            try:
                new_page.set_default_timeout(8000)
                attach_dialog_handler(new_page)
            except Exception:
                pass

            # attaches the same capture mechanism used on the original
            # page, so actions performed on this new tab/window keep being
            # recorded instead of disappearing once the user's focus moves
            # to it (see Recorder.record_new_tab/attach_page)
            recorder.record_new_tab(
                new_page
            )

        context.on(
            "page",
            _on_new_page,
        )

        ready_event.set()

        enter_pressed = threading.Event()

        def _wait_for_enter():

            try:
                input()

            except EOFError:

                logger.warning(
                    "no terminal input available - "
                    "stopping recording immediately"
                )

            enter_pressed.set()

        threading.Thread(
            target=_wait_for_enter,
            daemon=True,
        ).start()

        stop_reason = "terminal_enter"
        closed_note = None

        consecutive_failures = 0

        while not enter_pressed.is_set():

            # polls whichever registered page is still open, not always
            # the original one - closing the original tab while a child
            # tab remains open must NOT be mistaken for the whole browser
            # closing (see Recorder.get_any_open_page)
            if not browser.is_connected():

                stop_reason = "browser_closed"

                closed_note = (
                    "BROWSER CLOSED UNEXPECTEDLY"
                )

                break

            probe_page = recorder.get_any_open_page()

            if probe_page is None:

                stop_reason = "browser_closed"

                closed_note = (
                    "BROWSER CLOSED UNEXPECTEDLY"
                )

                break

            try:
                probe_page.evaluate("1")

                consecutive_failures = 0

            except Exception:

                # that specific page may have just closed between the
                # checks above and this call - only a real problem if the
                # browser itself is gone or truly nothing remains open
                if (
                    not browser.is_connected()
                    or recorder.get_any_open_page() is None
                ):

                    stop_reason = "browser_closed"

                    closed_note = (
                        "BROWSER CLOSED UNEXPECTEDLY"
                    )

                    break

                consecutive_failures += 1

                if consecutive_failures >= 10:

                    stop_reason = "navigation_error"

                    closed_note = (
                        "RECORDING STOPPED - page got stuck "
                        "after a navigation error"
                    )

                    break

            enter_pressed.wait(0.5)

        _finish_recording(
            recorder,
            stop_reason=stop_reason,
            closed_note=closed_note,
        )

    except Exception as e:

        logger.error(
            "recording session crashed: %s",
            e,
        )

        if not ready_event.is_set():

            ready_result.update(
                {
                    "success": False,
                    "message": (
                        "Couldn't launch the browser."
                    ),
                    "url": url,
                    "page_title": None,
                }
            )

            ready_event.set()

        elif (
            recorder is not None
            and recorder.recording
        ):

            try:

                _finish_recording(
                    recorder,
                    stop_reason="application_error",
                    closed_note=(
                        f"APPLICATION ERROR - {e}"
                    ),
                )

            except Exception as save_err:

                logger.error(
                    "couldn't save recording "
                    "after crash: %s",
                    save_err,
                )

    finally:

        with state_lock:
            session_state["active"] = False
            session_state["recording"] = False

        try:

            if browser is not None:
                browser.close()

        except Exception:
            pass

        try:

            if pw is not None:
                pw.stop()

        except Exception:
            pass


@app.route("/")
def index():
    return render_template(
        "index.html"
    )


# ============================================================
# STEP 1 - DASHBOARD JSON LIST
# ============================================================

@app.route("/api/recordings")
def api_recordings():
    """
    Step 1 only.

    Lists existing JSON recordings from storage/recordings
    for the Dashboard's Recorded Tests panel. Reuses the
    existing repository.list_recordings() - no new storage
    logic here.
    """

    try:
        recordings = repository.list_recordings()

    except OSError as e:

        logger.error(
            "couldn't list recordings: %s",
            e,
        )

        return jsonify(
            {
                "success": False,
                "message": "Couldn't read the recordings folder.",
                "recordings": [],
            }
        )

    return jsonify(
        {
            "success": True,
            "recordings": recordings,
        }
    )


# ============================================================
# STEP 2 - JSON RECORDING VIEW / EDITOR SCREEN
# ============================================================

def _resolve_recording_file(recording_path):
    """Resolves a recording path as the frontend sends it - a bare
    filename, "storage/recordings/x.json", or
    "storage/recordings/edited/x.json" (now that edited recordings show
    up in the Dashboard too) - to a real file under storage/recordings/,
    including its edited/ subfolder. Returns None if the result would
    land outside storage/recordings/ entirely (no path escaping).
    """
    raw = (recording_path or "").strip()

    if not raw:
        return None

    parts = Path(raw).parts

    if "recordings" in parts:
        idx = parts.index("recordings")
        rel = (
            Path(*parts[idx + 1:])
            if len(parts) > idx + 1
            else Path(Path(raw).name)
        )
    else:
        rel = Path(Path(raw).name)

    candidate = (repository.RECORDINGS_DIR / rel).resolve()

    try:
        candidate.relative_to(repository.RECORDINGS_DIR.resolve())
    except ValueError:
        return None

    return candidate


@app.route("/recording/edit")
def recording_editor():
    """
    Step 2 only.

    Opens an existing JSON recording and displays its
    contents in the Recording Editor screen.

    IMPORTANT:
    No modify/delete/add/reorder/save logic is included here.
    Those belong to later steps.
    """

    recording_path = request.args.get(
        "path",
        ""
    ).strip()

    if not recording_path:

        return (
            "Recording path is required.",
            400,
        )

    # Allow JSON recordings from storage/recordings, including its
    # edited/ subfolder.
    recording_file = _resolve_recording_file(
        recording_path
    )

    if (
        recording_file is None
        or recording_file.suffix.lower() != ".json"
    ):

        return (
            "Only JSON recordings can be opened.",
            400,
        )

    try:

        recording = repository.load_recording(
            str(recording_file)
        )

    except FileNotFoundError:

        return (
            f"Recording not found: {recording_path}",
            404,
        )

    except (
        OSError,
        json.JSONDecodeError,
    ) as e:

        logger.error(
            "couldn't read recording %s: %s",
            recording_path,
            e,
        )

        return (
            "The selected recording could not be read.",
            400,
        )

    display_path = (
        str(
            recording_file.relative_to(
                BASE_DIR
            )
        )
        .replace("\\", "/")
    )

    return render_template(
        "recording_editor.html",
        recording=recording,
        recording_path=display_path,
    )


@app.route("/api/recordings/view")
def api_recordings_view():
    """
    Step 2 only.

    Returns the full JSON of one existing recording (metadata
    + every action, in order) for the Recording Editor screen
    to render. Reuses repository.load_recording() - no new
    storage logic. View only - this never writes anything.
    """

    recording_path = request.args.get(
        "path",
        ""
    ).strip()

    if not recording_path:

        return jsonify(
            {
                "success": False,
                "message": "Recording path is required.",
                "recording": None,
            }
        )

    # Allow JSON recordings from storage/recordings, including its
    # edited/ subfolder - same resolution the /recording/edit page
    # route uses.
    recording_file = _resolve_recording_file(
        recording_path
    )

    if (
        recording_file is None
        or recording_file.suffix.lower() != ".json"
    ):

        return jsonify(
            {
                "success": False,
                "message": "Only JSON recordings can be opened.",
                "recording": None,
            }
        )

    try:

        recording = repository.load_recording(
            str(recording_file)
        )

    except FileNotFoundError:

        return jsonify(
            {
                "success": False,
                "message": f"Recording not found: {recording_path}",
                "recording": None,
            }
        )

    except (
        OSError,
        json.JSONDecodeError,
    ) as e:

        logger.error(
            "couldn't read recording %s: %s",
            recording_path,
            e,
        )

        return jsonify(
            {
                "success": False,
                "message": "The selected recording could not be read.",
                "recording": None,
            }
        )

    # if this IS an edited recording, also hand back its untouched
    # original so the editor can show both - "session_X_edited" always
    # derives from "session_X" (the stable-naming convention Save Edited
    # JSON uses), so the original's path is just that suffix stripped
    original = None

    if recording_file.parent == repository.EDITED_RECORDINGS_DIR:

        original_name = (
            recording.get("name")
            or recording_file.stem
        )

        if original_name.endswith("_edited"):

            original_name = original_name[
                : -len("_edited")
            ]

            original_file = (
                repository.RECORDINGS_DIR
                / f"{original_name}.json"
            )

            if original_file.exists():

                try:
                    original = repository.load_recording(
                        str(original_file)
                    )
                except (
                    OSError,
                    json.JSONDecodeError,
                ) as e:
                    logger.warning(
                        "couldn't load original %s for comparison: %s",
                        original_file,
                        e,
                    )

    return jsonify(
        {
            "success": True,
            "recording": recording,
            "original": original,
        }
    )


# ============================================================
# STEP 7 - SAVE EDITED JSON
# ============================================================

@app.route(
    "/api/recordings/save",
    methods=["POST"]
)
def api_recordings_save():
    """
    Saves the edited recording (from the Recording Editor
    screen) into storage/recordings/edited/ - the original
    recording is never touched. One original recording maps
    to exactly ONE stable edited filename (no timestamp): every
    Save Edited JSON click for the same original overwrites
    that same file (and its matching generated script) with the
    latest edited state, rather than piling up a new dated copy
    each time.
    """

    body = request.get_json(
        force=True,
        silent=True
    ) or {}

    recording = body.get(
        "recording"
    ) or {}

    actions = recording.get(
        "actions",
        []
    )

    if not isinstance(actions, list):

        return jsonify(
            {
                "success": False,
                "message": "Edited actions are invalid.",
                "path": None,
                "name": None,
            }
        )

    original_name = (
        recording.get("name")
        or "recording"
    )

    # one stable name per original recording - re-saving an edit of
    # "session_X" (or of "session_X_edited" itself, if it's ever reopened)
    # always converges on the same "session_X_edited" target, instead of
    # a new "_edited_<timestamp>" file every time Save is clicked
    new_name = (
        original_name
        if original_name.endswith("_edited")
        else f"{original_name}_edited"
    )

    # the edited JSON is the source of truth: if the first action now
    # points at a different page (e.g. its navigate/page_url was edited),
    # start_url must follow it rather than staying on whatever the
    # ORIGINAL recording started on
    if (
        actions
        and isinstance(actions[0], dict)
        and actions[0].get("page_url")
    ):
        start_url = actions[0]["page_url"]
    else:
        start_url = recording.get(
            "start_url",
            ""
        )

    test_case = {
        "name": new_name,
        "start_url": start_url,
        "actions": actions,
    }

    try:

        path = repository.save_edited_recording(
            test_case
        )

    except OSError as e:

        logger.error(
            "couldn't save edited recording: %s",
            e,
        )

        return jsonify(
            {
                "success": False,
                "message": "Couldn't save the edited recording.",
                "path": None,
                "name": None,
            }
        )

    # Existing script generator, reused as-is - just pointed at the
    # edited-scripts folder so it never mixes with a script generated
    # from the original recording. The user never has to trigger this
    # by hand; it happens automatically as part of Save Edited JSON.
    #
    # Re-read the file we just wrote, rather than reusing the in-memory
    # test_case dict, so the script is provably generated from the SAVED
    # JSON on disk - the single source of truth - not just from whatever
    # was in memory a moment earlier.
    try:

        saved_test_case = repository.load_recording(
            str(path)
        )

        generate_script(
            saved_test_case,
            output_dir=EDITED_OUTPUT_DIR,
        )

    except Exception as e:

        logger.error(
            "script generation failed for edited recording: %s",
            e,
        )

    display_path = (
        str(
            path.relative_to(
                BASE_DIR
            )
        )
        .replace("\\", "/")
    )

    return jsonify(
        {
            "success": True,
            "message": "Edited recording saved.",
            "path": display_path,
            "name": new_name,
        }
    )


@app.route(
    "/api/browser/launch",
    methods=["POST"]
)
def api_browser_launch():

    body = request.get_json(
        force=True,
        silent=True
    ) or {}

    url = normalize_url(
        body.get("url", "")
    )

    if not url:

        return jsonify(
            {
                "success": False,
                "message": "please enter a URL",
                "url": url,
                "page_title": None,
            }
        )

    with state_lock:

        if session_state["active"]:

            return jsonify(
                {
                    "success": False,
                    "message": (
                        "A recording is already "
                        "in progress - press ENTER "
                        "in the terminal to stop it "
                        "before launching another."
                    ),
                    "url": url,
                    "page_title": None,
                }
            )

        session_state["active"] = True

    ready_event = threading.Event()

    ready_result = {}

    thread = threading.Thread(
        target=_run_recording_session,
        args=(
            url,
            ready_event,
            ready_result,
        ),
        daemon=True,
    )

    thread.start()

    if not ready_event.wait(
        timeout=PAGE_LOAD_TIMEOUT / 1000 + 10
    ):

        return jsonify(
            {
                "success": False,
                "message": (
                    "browser launch is taking "
                    "too long"
                ),
                "url": url,
                "page_title": None,
            }
        )

    return jsonify(
        ready_result
    )


@app.route(
    "/api/database/connect"
)
def api_database_connect():

    return jsonify(
        {
            "success": False,
            "configured": False,
            "message": (
                "Database integration is "
                "not configured yet."
            ),
        }
    )


@app.route("/status")
def status():

    with state_lock:

        return jsonify(
            {
                "flask": "ok",
                "playwright_installed": True,
                "browser_active": (
                    session_state["active"]
                ),
                "recording": (
                    session_state["recording"]
                ),
                "current_url": (
                    session_state["current_url"]
                ),
            }
        )


@app.route(
    "/api/test/run",
    methods=["POST"]
)
def api_test_run():

    body = request.get_json(
        force=True,
        silent=True
    ) or {}

    qa_url = body.get(
        "qa_url",
        ""
    )

    recording_path = body.get(
        "recording_path",
        ""
    )

    expected_content = body.get(
        "expected_content",
        ""
    )

    expected_screenshot = body.get(
        "expected_screenshot",
        ""
    )

    product_to_verify = body.get(
        "product_to_verify",
        ""
    )

    if not qa_url.strip():

        return jsonify(
            {
                "status": "FAIL",
                "message": (
                    "QA website URL is required"
                ),
                "html_report": None,
                "json_report": None,
            }
        )

    test_case = {
        "name": (
            f"adhoc_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ),
        "start_url": qa_url,
        "actions": [],
    }

    if recording_path.strip():

        try:

            test_case = (
                repository.load_recording(
                    recording_path
                )
            )

        except (
            FileNotFoundError,
            OSError,
        ) as e:

            logger.error(
                "couldn't load recording %s: %s",
                recording_path,
                e,
            )

            return jsonify(
                {
                    "status": "FAIL",
                    "message": (
                        f"couldn't find recording "
                        f"at {recording_path}"
                    ),
                    "html_report": None,
                    "json_report": None,
                }
            )

    # Existing script generation.
    script_path = generate_script(
        test_case
    )

    # recording_name is what execute_test uses to name this run's output
    # folder (screenshots/<name>_<timestamp>/) - every kind of output for
    # this run (the sequential img1.png, img2.png, ... screenshots,
    # product-validation's own capture, and the report data written back
    # into report.json) ends up in that one folder, computed once inside
    # execute_test.
    result = execute_test(
        qa_url,
        script_path,
        expected_content,
        expected_screenshot,
        product_to_verify,
        test_case.get("name"),
    )

    # execute_test already wrote the full result to report.json inside
    # the run's own folder - no separate storage/executions/ copy needed.
    run_dir = (
        BASE_DIR / result["run_dir"]
        if result.get("run_dir") else None
    )

    html_report_path = generate_report(
        result,
        output_dir=run_dir,
    )

    return jsonify(
        {
            "status": result["status"],
            "message": result["message"],
            "html_report": (
                str(
                    html_report_path.relative_to(
                        BASE_DIR
                    )
                ).replace("\\", "/")
            ),
            "json_report": (
                result["run_dir"] + "/report.json"
                if result.get("run_dir") else None
            ),
        }
    )


if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        threaded=True,
    )