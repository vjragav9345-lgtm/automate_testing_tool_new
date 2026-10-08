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
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from flask import Flask, Response, jsonify, render_template, request, send_file
from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PWTimeoutError,
    Error as PWError,
)
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from storage import repository
from storage import session_files
from storage.repository import BASE_DIR
from storage.retention import run_cleanup, RETENTION_DAYS
from utils import normalize_url, attach_dialog_handler
from recorder.record_session import Recorder
import recorder.pick_element as pick_element
from recorder.pick_element import (
    start_pick_session, get_pick_status, prewarm_pick_session,
    _load_resolve_and_act, _replay_preceding_actions,
)
from generator.script_generator import generate_script, EDITED_OUTPUT_DIR, OUTPUT_DIR, test_case_has_otp_step
from executor.run_execution import execute_test, start_replay, poll_replay, SCRIPT_TIMEOUT_SEC, _compute_script_timeout
from validation.report_generator import generate_report, plain_language_reason, step_headline, strip_fail_wrapper, honest_summary


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

app = Flask(__name__)

PAGE_LOAD_TIMEOUT = 30000


# Thread-safe recording status.
#
# "phase" is the dashboard-facing lifecycle state - one of:
#   idle | launching | recording | stopping | completed | failed
# It's intentionally separate from the older "active"/"recording" booleans
# (kept as-is so nothing that already reads them breaks) - phase exists
# purely so a polling dashboard can render one clear state instead of
# reverse-engineering it from those two booleans.
session_state = {
    "active": False,
    "recording": False,
    "current_url": None,
    "phase": "idle",
    "last_message": None,
    "last_recording_path": None,
    "last_recording_name": None,
    "last_action_count": None,
    "last_stop_reason": None,
}

state_lock = threading.Lock()

# Populated with the live threading.Event a recording session is waiting
# on (the same one terminal ENTER already sets - see _wait_for_enter in
# _run_recording_session) once that session is far enough along to accept
# a stop request. The dashboard's Stop Recording button (see
# api_recording_stop) sets this exact same Event rather than duplicating
# any stop logic - it's just a second way to trigger the one existing
# stop mechanism. None whenever no session is in a stoppable state.
_recording_control = {"enter_pressed": None}


def _regenerate_script_after_save(test_case, output_dir=None):
    """Shared step every recording-JSON save path calls right after its
    write to disk completes, so the matching .py script is never stale -
    a hand-edited JSON (a changed value, a manually-added validate
    action, anything else) takes effect the moment it's saved, not
    deferred to the next Run. Regeneration failure is logged clearly but
    never blocks or rolls back the JSON save that already happened - the
    save itself must always succeed regardless of what happens here.
    Returns the generated script Path, or None if regeneration failed.
    """
    try:
        script_path = generate_script(test_case, output_dir=output_dir)
        logger.info(
            "regenerated script for %r: %s",
            test_case.get("name"),
            script_path,
        )
        return script_path
    except Exception as e:
        logger.error(
            "script regeneration failed for %r: %s",
            test_case.get("name"),
            e,
        )
        return None


# ============================================================
# RECORDING JSON WATCHER - a SECOND, independent trigger for
# _regenerate_script_after_save(), alongside the app-internal save
# routes above that already call it directly. This one exists for edits
# made OUTSIDE this tool entirely - a text editor, VS Code, any external
# process saving a recording's JSON file directly - which the app's own
# routes never see happen. Reuses the exact same shared function; no
# regeneration logic is duplicated here.
# ============================================================

# how long a watched file's events must stay quiet before this actually
# reads/regenerates it - an editor's save can fire several filesystem
# events in a burst, and can briefly leave the file only partially
# written; waiting this long after the LAST event before acting means
# only the final, complete write ever gets processed
RECORDINGS_WATCH_DEBOUNCE_SEC = 0.4


class _RecordingJsonWatchHandler(FileSystemEventHandler):
    """Watches storage/recordings/ (recursively, so the edited/ and
    trimmed/ subfolders are covered too - both are still storage/
    recordings/*.json, just one directory deeper) for *.json changes.

    Debounced per-file via one threading.Timer per path: each new event
    for a given file cancels that file's pending timer and starts a
    fresh one, so only a genuinely settled write is ever processed.
    Skips (rather than crashes on) a file that doesn't parse as valid
    JSON yet - the next save event picks it up.

    This handler only ever READS storage/recordings/ and calls
    generate_script() (via the shared helper), which only ever WRITES
    under generated_scripts/ - never back into storage/recordings/ - so
    a regeneration can never itself produce another event this same
    watcher would react to. No infinite loop is possible.

    Every entry point watchdog can call into (on_created/on_modified/
    on_moved, all synchronous on its own dispatcher thread) is wrapped
    against ever raising - see _safe_schedule for why that specifically
    matters here (an uncaught exception there kills the dispatcher
    thread permanently, not just the one event).
    """

    def __init__(self):
        self._timers = {}
        self._lock = threading.Lock()

    def _schedule(self, path_str):
        if not path_str or not path_str.lower().endswith(".json"):
            return
        with self._lock:
            existing = self._timers.get(path_str)
            if existing is not None:
                existing.cancel()
            timer = threading.Timer(
                RECORDINGS_WATCH_DEBOUNCE_SEC, self._process, args=(path_str,)
            )
            timer.daemon = True
            self._timers[path_str] = timer
            timer.start()

    def _process(self, path_str):
        with self._lock:
            self._timers.pop(path_str, None)

        try:
            path = Path(path_str)

            if not path.exists():
                # deleted, or moved away, before the debounce window
                # elapsed - nothing to regenerate from
                return

            try:
                with open(path, encoding="utf-8") as f:
                    test_case = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.info(
                    "recording watcher: %s not valid JSON yet (%s) - "
                    "will retry on the next save",
                    path,
                    e,
                )
                return

            if not isinstance(test_case, dict) or not isinstance(test_case.get("actions"), list):
                logger.warning(
                    "recording watcher: %s doesn't look like a recording "
                    "(no actions list) - skipped",
                    path,
                )
                return

            try:
                path.resolve().relative_to(repository.EDITED_RECORDINGS_DIR.resolve())
                output_dir = EDITED_OUTPUT_DIR
            except ValueError:
                output_dir = None

            print(
                f"\n[recording-watcher] detected external change to {path} "
                f"- regenerating script...",
                flush=True,
            )

            script_path = _regenerate_script_after_save(test_case, output_dir=output_dir)

            if script_path:
                print(f"[recording-watcher] regenerated: {script_path}\n", flush=True)
            else:
                print(
                    f"[recording-watcher] regeneration FAILED for {path} - "
                    f"see server log\n",
                    flush=True,
                )

        except Exception as e:
            # nothing that happens for one file's event should ever be
            # able to take down the watcher - it must keep watching for
            # every OTHER file's changes regardless
            logger.error("recording watcher: unexpected error handling %s: %s", path_str, e)

    def on_created(self, event):
        self._safe_schedule(event, event.src_path)

    def on_modified(self, event):
        self._safe_schedule(event, event.src_path)

    def on_moved(self, event):
        self._safe_schedule(event, event.dest_path)

    def _safe_schedule(self, event, path_str):
        # these three on_* methods run SYNCHRONOUSLY on watchdog's own
        # dispatcher thread (BaseObserver.run(), in
        # watchdog/observers/api.py) - that loop only ever catches
        # queue.Empty, nothing else, so ANY uncaught exception here
        # would propagate out of dispatch_events() and kill the
        # dispatcher thread for good: the watcher would stop reacting to
        # every future save, for every file, silently, with nothing ever
        # logged - exactly the "only the first save works" symptom this
        # guards against. _process (the debounced callback below) has
        # its own try/except because it runs on a separate Timer thread,
        # but that thread dying wouldn't take the Observer down with it
        # - THIS is the code that actually protects the Observer itself.
        try:
            if not event.is_directory:
                self._schedule(path_str)
        except Exception as e:
            logger.error(
                "recording watcher: unexpected error in event handler for %s: %s",
                path_str,
                e,
            )


_recordings_observer = None


def start_recordings_watcher():
    """Starts the background filesystem watcher over storage/recordings/
    - runs as a daemon thread for the lifetime of this process, starting
    automatically as part of the app launching (see the bottom of this
    file), no separate manual step required. Idempotent: calling it more
    than once just leaves the first observer running.
    """
    global _recordings_observer

    if _recordings_observer is not None:
        return _recordings_observer

    handler = _RecordingJsonWatchHandler()
    observer = Observer()
    observer.schedule(handler, str(repository.RECORDINGS_DIR), recursive=True)
    observer.daemon = True
    observer.start()

    _recordings_observer = observer
    logger.info("recording JSON watcher started on %s", repository.RECORDINGS_DIR)
    print(f"Watching {repository.RECORDINGS_DIR} for external JSON edits...", flush=True)

    return observer


def _finish_recording(
    recorder,
    stop_reason="terminal_enter",
    closed_note=None,
):
    """Stops recorder, saves JSON and generates the normal script."""

    # reuse the SAME name the incremental draft (FIX 1 - see Recorder.
    # start()/_flush_draft) has been writing to throughout the session,
    # when one exists - repository.save_recording() below then simply
    # overwrites that same file with the final, complete version instead
    # of leaving the draft behind as an orphaned duplicate under a
    # different timestamp.
    _draft_path = getattr(recorder, "_draft_path", None)
    name = _draft_path.stem if _draft_path else f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    test_case = recorder.stop(
        name=name,
        stop_reason=stop_reason,
    )

    captured_count = len(test_case["actions"])
    saved_count = None

    try:
        path = repository.save_recording(test_case)
        # FIX 5: the incremental append-only sidecar (see Recorder.
        # _flush_draft) has done its job the moment the real, complete
        # JSON is safely on disk - remove it rather than leaving it behind
        # as a stray file next to every finished recording.
        _draft_jsonl_path = getattr(recorder, "_draft_jsonl_path", None)
        if _draft_jsonl_path is not None:
            try:
                _draft_jsonl_path.unlink(missing_ok=True)
            except OSError:
                pass
    except OSError as e:
        # A save failure here must never look like a silent hang to the
        # dashboard - surface it as a clear "failed" phase rather than
        # letting the exception propagate uncaught (which would otherwise
        # be swallowed by _run_recording_session's own crash handler with
        # no user-facing explanation of what actually went wrong).
        logger.error("couldn't save recording %r: %s", name, e)
        print(f"\nRECORDING SAVE FAILED: {e}\n", flush=True)
        with state_lock:
            session_state["recording"] = False
            session_state["phase"] = "failed"
            session_state["last_message"] = (
                "Couldn't save the recording - please check available "
                "disk space and try again."
            )
            session_state["last_stop_reason"] = stop_reason
        return None

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

    script_path = _regenerate_script_after_save(test_case)

    if script_path:
        script_line = (
            f"\nPython script generated:\n"
            f"{script_path}\n"
        )
    else:
        script_line = (
            "\nPython script generation FAILED - see server log.\n"
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

    completion_message = f"Recording completed - {captured_count} action(s) captured."
    if closed_note:
        completion_message = f"{closed_note} - {captured_count} action(s) captured before it stopped."

    with state_lock:
        session_state["recording"] = False
        session_state["phase"] = "completed"
        session_state["last_message"] = completion_message
        session_state["last_recording_path"] = (
            str(path.relative_to(BASE_DIR)).replace("\\", "/")
        )
        session_state["last_recording_name"] = test_case.get("name")
        session_state["last_action_count"] = captured_count
        session_state["last_stop_reason"] = stop_reason

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

        # FIX 1 (recorder attaches too late): install the capture bridge
        # at the CONTEXT level, before page.goto() below ever runs, so
        # the injected script covers this page's very first navigation
        # too - not just navigations that happen after the old, later
        # attach_page() call. Constructing Recorder here (rather than
        # after goto, as before) only registers this binding/init-script
        # early; recorder.start() below (still called only after a
        # successful goto) is what actually turns capturing on.
        recorder = Recorder(page)
        recorder.install_context_capture(context)

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

            with state_lock:
                session_state["active"] = False
                session_state["phase"] = "failed"
                session_state["last_message"] = "Page took too long to respond."

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

            with state_lock:
                session_state["active"] = False
                session_state["phase"] = "failed"
                session_state["last_message"] = (
                    "Couldn't reach that URL - check it's correct and try again."
                )

            ready_event.set()
            return

        with state_lock:
            session_state["active"] = True
            session_state["recording"] = True
            session_state["current_url"] = page.url
            session_state["phase"] = "recording"
            session_state["last_message"] = None

        # recorder was already constructed (and install_context_capture()
        # already registered) right after context/page creation above -
        # not re-created here - so the context-level binding/init-script
        # stays the one and only registration for this session.
        recorder.start(launch_url=url)

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

        # registered here (not earlier) so a Stop Recording click can never
        # race ahead of the terminal-ENTER path actually being live - both
        # set the exact same Event, so whichever fires first is simply
        # "the" stop trigger for this session; the other is then a no-op.
        with state_lock:
            _recording_control["enter_pressed"] = enter_pressed

        def _wait_for_enter():

            try:
                input()

            except EOFError:

                # REAL BUG FIX: this used to call enter_pressed.set() here
                # too, which meant ANY environment without a live terminal
                # attached to stdin (VS Code's Run button, a task runner,
                # a debugger launch config, this app started from another
                # script) - not just piped/non-interactive execution -
                # immediately closed the browser within milliseconds of
                # opening it, before a human ever got a chance to do
                # anything. That "stop the instant EOF is hit" behavior
                # made sense when terminal ENTER was the ONLY way to stop
                # a recording; now that the dashboard's Stop Recording
                # button (see api_recording_stop) sets this exact same
                # Event through a completely different path, there's no
                # reason to auto-terminate here at all - just disable the
                # terminal path and let the session keep running normally
                # until Stop Recording is clicked (or the browser closes/
                # gets stuck, both already handled by the loop below).
                logger.warning(
                    "no terminal input available in this environment - "
                    "terminal ENTER will not work for this session; "
                    "use the dashboard's Stop Recording button instead"
                )

                with state_lock:
                    session_state["last_message"] = (
                        "Recording in progress - this environment has no "
                        "terminal input available, so use Stop Recording "
                        "(in the dashboard) to end this session."
                    )

                return

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

                # FIX 6 (recording stop wording): the browser disconnecting
                # is indistinguishable, from this polling loop alone,
                # between a user deliberately closing the window to end
                # the recording (the overwhelmingly common case) and a
                # genuine crash - so this is worded as the NORMAL stop it
                # almost always is. "unexpected"/crash language is
                # reserved for the navigation_error case below and for a
                # genuinely uncaught exception (see the except block
                # further down this function).
                closed_note = (
                    "Recording stopped (browser closed)"
                )

                break

            probe_page = recorder.get_any_open_page()

            if probe_page is None:

                stop_reason = "browser_closed"

                closed_note = (
                    "Recording stopped (browser closed)"
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
                        "Recording stopped (browser closed)"
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

            with state_lock:
                session_state["active"] = False
                session_state["phase"] = "failed"
                session_state["last_message"] = "Couldn't launch the browser."

            ready_event.set()

        elif (
            recorder is not None
            and recorder.recording
        ):

            try:

                _finish_recording(
                    recorder,
                    stop_reason="application_error",
                    # user-facing text only - the raw exception is
                    # already captured above via logger.error(), so
                    # nothing technical is lost by keeping this clean
                    closed_note=(
                        "RECORDING STOPPED - an unexpected "
                        "error interrupted the session"
                    ),
                )

            except Exception as save_err:

                logger.error(
                    "couldn't save recording "
                    "after crash: %s",
                    save_err,
                )

                with state_lock:
                    session_state["active"] = False
                    session_state["recording"] = False
                    session_state["phase"] = "failed"
                    session_state["last_message"] = (
                        "Recording crashed and couldn't be saved."
                    )

    finally:

        with state_lock:
            session_state["active"] = False
            session_state["recording"] = False
            _recording_control["enter_pressed"] = None

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


@app.route("/api/recordings/set_display_name", methods=["POST"])
def api_recordings_set_display_name():
    """PHASE 2: sets (or clears, given an empty string) a recording's own
    display_name - never renames the file, never touches anything else in
    it. Used by the "Name this test" modal right after a recording
    finishes, and by the Rename action on the dashboard card / editor
    header.
    """
    body = request.get_json(force=True, silent=True) or {}
    recording_file = _resolve_recording_file(body.get("path"))

    if (
        recording_file is None
        or recording_file.suffix.lower() != ".json"
        or not recording_file.is_file()
    ):
        return jsonify({"success": False, "message": "Recording not found."}), 404

    display_name = body.get("display_name")
    if display_name is not None and not isinstance(display_name, str):
        return jsonify({"success": False, "message": "display_name must be a string."}), 400

    try:
        repository.set_display_name(str(recording_file), display_name or "")
    except (OSError, json.JSONDecodeError) as e:
        logger.error("couldn't set display_name for %s: %s", recording_file, e)
        return jsonify({"success": False, "message": "Couldn't save the name."}), 500

    return jsonify({"success": True, "display_name": (display_name or "").strip() or None})


@app.route("/api/recordings/delete", methods=["POST"])
def api_recordings_delete():
    """Deletes ONE session: its recording JSON, generated scripts and
    replay run folders (screenshots + report.json/report.html) - exactly
    what storage/session_files.py maps that session to. The dashboard
    asks for confirmation before calling this."""
    body = request.get_json(force=True, silent=True) or {}
    recording_file = _resolve_recording_file(body.get("path"))

    if (
        recording_file is None
        or recording_file.suffix.lower() != ".json"
        or not recording_file.is_file()
    ):
        return jsonify({"success": False, "message": "Recording not found."}), 404

    names = {recording_file.stem}
    try:
        names.add((repository.load_recording(str(recording_file)).get("name") or "").strip())
    except (OSError, json.JSONDecodeError):
        pass
    names.discard("")

    # never pull a run folder out from under a replay that is still writing to it
    from storage.retention import _active_run_dirs
    active_runs = _active_run_dirs()
    for name in names:
        for run_dir in session_files.session_files(name)["run_dirs"]:
            if str(run_dir.resolve()) in active_runs:
                return jsonify({
                    "success": False,
                    "message": "A replay of this session is still running - wait for it to finish.",
                }), 409

    deleted = {"recordings": 0, "scripts": 0, "run_dirs": 0}
    errors = []
    for name in names:
        result = session_files.delete_session(name)
        for kind in deleted:
            deleted[kind] += len(result[kind])
        errors.extend(result["errors"])

    logger.info("deleted session %s: %s (errors: %s)", sorted(names), deleted, errors)

    if errors:
        return jsonify({
            "success": False,
            "message": "Some files of this session couldn't be deleted.",
            "deleted": deleted,
            "errors": errors,
        }), 500

    return jsonify({"success": True, "deleted": deleted})


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

    # ITEM 2 FIX: continue from a previously-saved edit if one exists,
    # instead of always re-opening the pristine original. /api/recordings/
    # save never touches the original (by design - see its own docstring),
    # writing to storage/recordings/edited/<name>_edited.json instead. Without
    # this, re-opening the SAME original path/link after an earlier
    # edit+save (delete a step, add one, ...) showed the untouched
    # original again, with every earlier change silently gone from
    # view - even though it really had been saved, just under a
    # different file. Only swaps when the requested file is an
    # ORIGINAL (lives directly in storage/recordings/, not already
    # inside its edited/ or trimmed/ subfolder) and a matching edited
    # copy actually exists.
    if recording_file.parent == repository.RECORDINGS_DIR:
        edited_candidate = (
            repository.EDITED_RECORDINGS_DIR / f"{recording_file.stem}_edited.json"
        )
        if edited_candidate.exists():
            recording_file = edited_candidate

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

    return jsonify(
        {
            "success": True,
            "recording": recording,
        }
    )


# ============================================================
# LAST VALIDATION RESULT - read-only lookup used by the dashboard's
# "View Last Log" button (see static/js/script.js) when nothing is
# cached in the browser (e.g. after a page reload). Does not modify
# api_recordings_view above or any other existing route.
# ============================================================

@app.route("/api/recordings/last_result")
def api_recordings_last_result():
    """Read-only: finds and returns the most recent replay result
    (report.json) for one recording, if any exists.

    There's no stored mapping from a recording to its past run
    folders, so this derives one the same way execute_test() already
    does: every run folder's name starts with a slug of the SAME
    recording name that was passed as recording_name for that replay
    (see run_id construction in executor/run_execution.py). Recording
    names in this project are already plain, filesystem-safe strings
    (e.g. "session_20260908_123157"), so a case-insensitive prefix
    match against that name reliably ties a run folder back to the
    recording it came from - the most recently modified match is
    treated as "the last run". Read-only throughout: only ever reads
    an existing report.json, never writes or triggers replay.
    """
    recording_path = request.args.get("path", "").strip()

    if not recording_path:
        return jsonify({"success": False, "found": False, "message": "path is required."})

    recording_file = _resolve_recording_file(recording_path)

    if recording_file is None or recording_file.suffix.lower() != ".json":
        return jsonify({"success": False, "found": False, "message": "Recording not found."})

    try:
        recording = repository.load_recording(str(recording_file))
    except (FileNotFoundError, OSError, json.JSONDecodeError) as e:
        logger.error("couldn't read recording %s: %s", recording_path, e)
        return jsonify({"success": False, "found": False, "message": "Couldn't read the recording."})

    recording_name = (recording.get("name") or recording_file.stem).strip().lower()

    if not recording_name:
        return jsonify({"success": False, "found": False, "message": "Recording has no name to match against."})

    best_dir = None
    best_mtime = None

    try:
        for entry in SCREENSHOTS_ROOT.iterdir():
            if not entry.is_dir():
                continue
            if not entry.name.lower().startswith(recording_name):
                continue
            report_path = entry / "report.json"
            if not report_path.is_file():
                continue
            mtime = entry.stat().st_mtime
            if best_mtime is None or mtime > best_mtime:
                best_mtime = mtime
                best_dir = entry
    except OSError as e:
        logger.error("couldn't scan screenshots folder for %s: %s", recording_path, e)
        return jsonify({"success": False, "found": False, "message": "Couldn't read the screenshots folder."})

    if best_dir is None:
        return jsonify({"success": True, "found": False, "message": "No replay has been run yet for this session."})

    try:
        with open(best_dir / "report.json", encoding="utf-8") as f:
            report = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.error("couldn't read report.json in %s: %s", best_dir, e)
        return jsonify({"success": False, "found": False, "message": "Couldn't read the last result file."})

    return jsonify({
        "success": True,
        "found": True,
        "status": report.get("status"),
        "message": report.get("message"),
        "steps": report.get("steps", []),
        "ui_elements": report.get("ui_elements", []),
        "json_report": str((best_dir / "report.json").relative_to(BASE_DIR)).replace("\\", "/"),
    })


# ============================================================
# VALIDATE LOCATOR - read-only check used by the Recording Editor's
# "Add Action" dialog (see templates/recording_editor.html) to confirm a
# manually-typed xpath actually resolves against the EXACT DOM state a
# real Replay would produce up to the insertion point - by actually
# replaying the session's real preceding steps through the project's
# existing, already-proven pipeline (generate_script(), then running the
# generated script the same way a real Replay does), rather than trying
# to approximate that page state through URL/timing heuristics. Never
# writes to the real session file, never triggers a real Replay, and
# never leaves anything behind in generated_scripts/ or
# storage/recordings/ - the whole probe lives in one per-call scratch
# directory outside both, removed in a finally block every time.
# ============================================================

# action types whose whole purpose is to operate on a SET of matching
# elements - for these, an xpath matching more than one element is a
# legitimate success, not an ambiguous locator. Every other locator-
# needing action type (click, fill, check_checked, ...) keeps requiring
# exactly one match, since a non-unique locator there would be genuinely
# ambiguous at replay time. Defined once, here - the dialog only needs
# to forward the action_type it already has, not duplicate this list.
MULTI_MATCH_ACTION_TYPES = {"count_elements", "detect_duplicates"}


def _slice_preceding_actions(session_path, insert_after_index):
    """Shared by validate_locator and pick_element/start - resolves a
    recording by session_path, loads it, and slices its own real,
    already-recorded actions down to (and including) insert_after_index.
    -1 (inserting before the very first step) correctly slices down to an
    empty list.

    Returns (start_url, preceding_actions, probe_page_id, error_message).
    error_message is None on success; on failure the first three are all
    None and error_message is a human-readable reason, for the caller to
    surface directly.
    """
    recording_file = _resolve_recording_file(session_path)
    if recording_file is None or recording_file.suffix.lower() != ".json":
        return None, None, None, "Recording not found."

    try:
        recording = repository.load_recording(str(recording_file))
    except (FileNotFoundError, OSError, json.JSONDecodeError) as e:
        logger.error("_slice_preceding_actions: couldn't read recording %s: %s", session_path, e)
        return None, None, None, "Couldn't read the recording."

    real_actions = recording.get("actions", [])
    if not isinstance(real_actions, list):
        real_actions = []

    start_url = recording.get("start_url", "")
    if not start_url:
        return None, None, None, "Recording has no start_url to replay against."

    slice_end = max(0, min(insert_after_index + 1, len(real_actions)))
    preceding_actions = real_actions[:slice_end]

    # the probe/picker targets whatever page/tab those preceding steps
    # actually left off on, so it inherits their own page_id - 0 (the
    # original page) when there is nothing preceding it
    probe_page_id = preceding_actions[-1].get("page_id", 0) if preceding_actions else 0

    return start_url, preceding_actions, probe_page_id, None


@app.route("/api/recordings/validate_locator", methods=["POST"])
def api_recordings_validate_locator():
    """Read-only: fast-forwards to session_path's own state at
    insert_after_index, then probes whether xpath resolves there.

    REWRITTEN (was: generate_script() + a full subprocess replay of
    every preceding step at NORMAL pace, then a separate __validate_xpath__
    step on top - confirmed the actual cause of "Validate replays the
    whole flow slowly, ~35s for a 3-step insertion point" a real screen
    recording showed). Now reuses recorder/pick_element.py's OWN
    _load_resolve_and_act()/_replay_preceding_actions() - the exact same
    turbo=True fast-forward Pick Element already relies on and this
    project has already exercised heavily - instead of a second, slower
    path to the same place. The actual check is Playwright's own native
    locator(f"xpath=...").count(), which needs no generated script or
    subprocess at all once the right page is already open. Same single
    replay ENGINE either way (resolve_and_act is dynamically loaded from
    a real generate_script() output, same as before) - only the invocation
    shape (in-process + turbo, vs. subprocess + normal pace) changed.
    Never writes anything to the real recording, never triggers a real
    Replay.
    """
    data = request.get_json(silent=True) or {}

    session_path = (data.get("session_path") or "").strip()
    xpath = (data.get("xpath") or "").strip()
    action_type = (data.get("action_type") or "").strip()
    # FIX 1: optional, only meaningful for validate_value_range - lets the
    # editor preview resolve the SAME way a saved value_hint would on replay
    value_hint = (data.get("value_hint") or "").strip() or None
    insert_after_index_raw = data.get("insert_after_index")

    if not session_path:
        return jsonify({"success": False, "message": "session_path is required."})

    if not xpath:
        return jsonify({"success": False, "message": "Enter an XPath to validate."})

    if insert_after_index_raw is None:
        return jsonify({"success": False, "message": "insert_after_index is required."})

    try:
        insert_after_index = int(insert_after_index_raw)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "insert_after_index must be a number."})

    start_url, preceding_actions, probe_page_id, error_message = _slice_preceding_actions(
        session_path, insert_after_index
    )
    if error_message is not None:
        return jsonify({"success": False, "message": error_message})

    probe_id = uuid.uuid4().hex
    pw = None
    browser = None
    try:
        # same dynamically-loaded resolve_and_act pick_element.py itself
        # uses - a real generate_script() output, loaded as a module
        # purely for its function definitions (see that module's own
        # docstring for why this is necessary at all)
        resolve_and_act = _load_resolve_and_act(start_url, probe_id)

        pw = sync_playwright().start()
        try:
            browser = pw.chromium.launch(headless=False)
        except Exception as e:
            # headless fallback only for a genuinely headless-incapable
            # environment (no display) - NOT the default, see the
            # anti-bot-detection note this replaces below for why headed
            # is deliberately preferred whenever it's actually available
            logger.warning("validate_locator: headed launch failed (%s), falling back to headless", e)
            browser = pw.chromium.launch(headless=True)

        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(8000)
        attach_dialog_handler(page)

        # HEADED BY DEFAULT - CONFIRMED REAL BUG this preserves the fix
        # for: a validation probe's own headless launch was the actual
        # cause of "validation probe didn't run" against a live site
        # (myntra.com) - page.goto() failed immediately with
        # net::ERR_HTTP2_PROTOCOL_ERROR under headless, while the
        # IDENTICAL request against the SAME URL succeeded immediately
        # headed. Sites that fingerprint/block headless Chromium at the
        # network level are common enough that this was never a
        # Myntra-specific fix - do not "optimize" this back to headless.
        try:
            page.goto(start_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
        except PWError as e:
            return jsonify({"success": False, "message": f"Couldn't reach {start_url!r}: {e}"})

        # THE SPEED FIX ITSELF: turbo=True fast-forward through the
        # preceding actions (same function, same flag, pick_element.py
        # already proved this works reliably) instead of a full,
        # normal-paced subprocess replay of the same steps.
        final_page, _walk_state = _replay_preceding_actions(
            page, context, start_url, preceding_actions, resolve_and_act
        )

        try:
            match_count = final_page.locator(f"xpath={xpath}").count()
        except Exception as e:
            return jsonify({"success": False, "message": f"That XPath isn't valid: {e}"})

        found = (match_count >= 1) if action_type in MULTI_MATCH_ACTION_TYPES else (match_count == 1)

        # FIX 3 (Validate Checkbox State dialog): the modal's own "Validate"
        # button must show the REAL checkbox state too, not just found/
        # match_count - reuses the exact same resolver a real replay uses
        # (generator/script_generator.py's _resolve_checkbox_state, read off
        # resolve_and_act's own module namespace - never a second copy of
        # that JS), only when this step is actually a checkbox validation
        # and the xpath is unique enough to test at all. Best-effort: never
        # raises, never affects found/match_count either way.
        checkbox_state_info = None
        if action_type == "validate_checked" and match_count == 1:
            try:
                _resolve_checkbox_state = resolve_and_act.__globals__.get("_resolve_checkbox_state")
                if _resolve_checkbox_state is not None:
                    checkbox_state_info = _resolve_checkbox_state(final_page.locator(f"xpath={xpath}").first)
            except Exception:
                checkbox_state_info = None

        # BUG 2 fix (f): preview the value(s) Validate Value Range WILL
        # check, using the exact same resolver a real replay uses (see
        # generator/script_generator.py's own _afqa_resolve_element_value,
        # read off resolve_and_act's module namespace - never a second
        # copy of that logic), so an ambiguous pick can be caught and
        # fixed in the editor before saving. Best-effort and capped
        # (matches this route's own "never raises, never affects found/
        # match_count" convention for the checkbox preview above it).
        value_range_preview = None
        if action_type == "validate_value_range" and match_count >= 1:
            try:
                _afqa_resolve_element_value = resolve_and_act.__globals__.get("_afqa_resolve_element_value")
                if _afqa_resolve_element_value is not None:
                    _vr_preview_rows = []
                    _vr_cap = min(match_count, 20)
                    _vr_locator = final_page.locator(f"xpath={xpath}")
                    for _vr_idx in range(_vr_cap):
                        _vr_val, _vr_reason, _vr_detail = _afqa_resolve_element_value(
                            _vr_locator.nth(_vr_idx), value_hint=value_hint
                        )
                        _vr_role = next(
                            (c["role"] for c in _vr_detail.get("candidates", []) if _vr_val is not None and c["value"] == _vr_val),
                            None,
                        )
                        _vr_preview_rows.append({
                            "value": _vr_val, "ambiguous_reason": _vr_reason, "role": _vr_role,
                            "candidates": _vr_detail.get("candidates", []),
                        })
                    value_range_preview = _vr_preview_rows
            except Exception:
                value_range_preview = None

        # same pink-highlight visual language as Pick Element and a real
        # replay's own validation steps (see generator/script_generator.py's
        # _draw_validation_highlight) - reimplemented here at the same
        # small scale as pick_element.py's own JS injections, rather than
        # importing script_generator.py's version, since this route isn't
        # part of a generated script and the two run in genuinely
        # different contexts. Best-effort: never raises, never affects
        # the returned result either way.
        if match_count >= 1:
            try:
                final_page.locator(f"xpath={xpath}").first.evaluate("""(node) => {
                    node.scrollIntoView({block: 'center'});
                    var r = node.getBoundingClientRect();
                    var box = document.createElement('div');
                    box.id = '__afqaValidationHighlight';
                    box.style.cssText = 'position:fixed;pointer-events:none;z-index:2147483647;' +
                        'border:3px solid #ff4081;background:rgba(255,64,129,0.15);box-sizing:border-box;' +
                        'left:' + r.left + 'px;top:' + r.top + 'px;width:' + r.width + 'px;height:' + r.height + 'px;';
                    document.body.appendChild(box);
                }""")
                final_page.wait_for_timeout(1200)
            except Exception:
                pass

        return jsonify({
            "success": True, "found": found, "match_count": match_count,
            "checkbox_state_info": checkbox_state_info,
            "value_range_preview": value_range_preview,
        })

    except Exception as e:
        logger.error("validate_locator failed: %s", e)
        return jsonify({"success": False, "message": "Couldn't validate that locator - please try again."})

    finally:
        try:
            if browser is not None and browser.is_connected():
                browser.close()
        except Exception:
            pass
        try:
            if pw is not None:
                pw.stop()
        except Exception:
            pass


@app.route("/api/recordings/test_navigate", methods=["POST"])
def api_recordings_test_navigate():
    """ITEM 3: lets a "navigate" step being added/edited in the Add
    Action modal actually be tried for real - previously a navigate
    step's Target URL field was just a plain text input with no way to
    confirm the URL is even reachable before saving it as inert JSON.

    One-shot and self-contained, same pattern api_recordings_validate_
    locator right above already uses: launches its OWN fresh headed
    browser (headed preferred for the same anti-bot-detection reasoning
    validate_locator's own comment documents), navigates to the given
    URL, reports whether it succeeded plus the page title/final URL,
    and closes that browser again before this request returns - it
    NEVER touches session_path/preceding_actions, the warm Pick Element
    session, or recordingData in any way, so it can't leave anything
    behind that would affect how a later Pick Element click (or a real
    Replay) resolves the recording's own, separate actions. Never
    writes to the recording file - same as Validate/Pick Element, only
    the user's own explicit Save does that.
    """
    data = request.get_json(silent=True) or {}
    raw_url = (data.get("url") or "").strip()

    if not raw_url:
        return jsonify({"success": False, "message": "Enter a URL first."})

    url = normalize_url(raw_url)

    pw = None
    browser = None
    try:
        pw = sync_playwright().start()
        try:
            browser = pw.chromium.launch(headless=False)
        except Exception as e:
            logger.warning("test_navigate: headed launch failed (%s), falling back to headless", e)
            browser = pw.chromium.launch(headless=True)

        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(8000)
        attach_dialog_handler(page)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
        except PWError as e:
            return jsonify({"success": False, "message": f"Couldn't reach {url!r}: {e}"})

        try:
            title = page.title()
        except Exception:
            title = None
        try:
            final_url = page.url
        except Exception:
            final_url = url

        return jsonify({
            "success": True,
            "message": f"Reached {final_url!r} - \"{title}\"" if title else f"Reached {final_url!r}",
            "url": final_url,
            "title": title,
        })

    except Exception as e:
        logger.error("test_navigate failed: %s", e)
        return jsonify({"success": False, "message": "Couldn't test that URL - please try again."})

    finally:
        # closes/returns immediately after confirming the URL, exactly
        # as required - this test browser is never left open for the
        # user to keep interacting with (unlike Pick Element's own,
        # deliberately-left-open browser), so it can never be mistaken
        # for, or interfere with, the page state any OTHER step in this
        # recording expects.
        try:
            if browser is not None and browser.is_connected():
                browser.close()
        except Exception:
            pass
        try:
            if pw is not None:
                pw.stop()
        except Exception:
            pass


@app.route("/api/recordings/pick_element/start", methods=["POST"])
def api_recordings_pick_element_start():
    """Kicks off a Pick Element session: replays session_path's own
    actions up to insert_after_index (same slicing validate_locator
    already uses - see _slice_preceding_actions), then hands off to a
    background thread (recorder/pick_element.py) that opens a real,
    headed browser and waits for the user to click something in it.
    Returns immediately with a pick_id - never blocks the request on a
    human actually clicking, see api_browser_launch's own docstring for
    why this project always puts a long-lived Playwright session on its
    own thread rather than the Flask request thread.

    warm_id, when the frontend sends one (see recording_editor.html's
    own pickWarmId, minted once per editor page load), names a
    background browser a preceding /pick_element/prewarm call for this
    SAME insertion point may already have gotten some or all of the way
    there - see recorder.pick_element.start_pick_session's own docstring
    for exactly how that's reused. Optional: omitting it still works
    exactly as before, just without the head start.
    """
    data = request.get_json(silent=True) or {}

    session_path = (data.get("session_path") or "").strip()
    insert_after_index_raw = data.get("insert_after_index")
    warm_id = (data.get("warm_id") or "").strip() or None

    if not session_path:
        return jsonify({"success": False, "message": "session_path is required."})

    if insert_after_index_raw is None:
        return jsonify({"success": False, "message": "insert_after_index is required."})

    try:
        insert_after_index = int(insert_after_index_raw)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "insert_after_index must be a number."})

    start_url, preceding_actions, _probe_page_id, error_message = _slice_preceding_actions(
        session_path, insert_after_index
    )
    if error_message is not None:
        return jsonify({"success": False, "message": error_message})

    pick_id = start_pick_session(
        start_url, preceding_actions, warm_id=warm_id, session_path=session_path
    )

    return jsonify({"success": True, "pick_id": pick_id})


@app.route("/api/recordings/pick_element/prewarm", methods=["POST"])
def api_recordings_pick_element_prewarm():
    """Fire-and-forget: called the instant the Add Action modal opens
    with a known insertion point (recording_editor.html's own
    openAddActionDialog), well before the user has clicked Pick Element
    at all - starts getting a background browser to that point in the
    meantime so the actual Pick Element click can often skip replay
    entirely. Always returns success immediately regardless of what
    happens in the background - a failed/slow prewarm just means the
    next Pick Element click falls back to replaying live, exactly like
    before this feature existed. See recorder.pick_element.
    prewarm_pick_session's own docstring.
    """
    data = request.get_json(silent=True) or {}

    session_path = (data.get("session_path") or "").strip()
    insert_after_index_raw = data.get("insert_after_index")
    warm_id = (data.get("warm_id") or "").strip()

    if not session_path or not warm_id or insert_after_index_raw is None:
        return jsonify({"success": True})  # nothing usable to prewarm - not an error

    try:
        insert_after_index = int(insert_after_index_raw)
    except (TypeError, ValueError):
        return jsonify({"success": True})

    start_url, preceding_actions, _probe_page_id, error_message = _slice_preceding_actions(
        session_path, insert_after_index
    )
    if error_message is not None:
        return jsonify({"success": True})

    prewarm_pick_session(warm_id, session_path, start_url, preceding_actions)

    return jsonify({"success": True})


@app.route("/api/recordings/pick_element/status", methods=["GET"])
def api_recordings_pick_element_status():
    """Polled by the Recording Editor while a Pick Element session is
    live. Just forwards recorder.pick_element.get_pick_status() as-is -
    {"status": "waiting"} while nothing's happened yet, {"status": "locked",
    xpath, css_path, id, locator_profile, match_count} while the browser is
    still open and something is currently locked (NOT terminal - the user
    can still release/re-lock; polling continues), {"status": "done", ...}
    once the browser has actually closed with a lock in place, or
    {"status": "timeout"|"error"|"cancelled", "message": ...} otherwise.
    """
    pick_id = (request.args.get("pick_id") or "").strip()

    if not pick_id:
        return jsonify({"status": "error", "message": "pick_id is required."})

    result = get_pick_status(pick_id)
    # LATENCY INSTRUMENTATION (always on - see recorder/pick_element.py's
    # matching [pick-timing] lines): every poll response is timestamped
    # server-side so a slow/stale dashboard can be diagnosed as "the
    # server had fresh data but something client-side didn't show it" vs
    # "the server itself didn't have fresh data yet" - two very
    # different bugs that look identical from the browser alone.
    print(f"[pick-timing] {pick_id} poll_served t={time.time():.3f} status={result.get('status')}", flush=True)
    return jsonify(result)


@app.route("/api/recordings/pick_element/cancel", methods=["POST"])
def api_recordings_pick_element_cancel():
    """Fire-and-forget, mirroring prewarm: called when the Add Action
    modal is cancelled, saved, or otherwise closed without the user
    having closed the picker browser window themselves (see
    recording_editor.html's modalCancelBtn/modalSaveBtn handlers) - ends
    that warm session's currently in-progress pick (if any) and closes
    its browser right away, instead of leaving it open until
    PICK_TIMEOUT_S elapses on its own. A missing/unknown warm_id, or no
    pick actually in progress, is simply a no-op, never an error - see
    recorder.pick_element.cancel_active_pick's own docstring.
    """
    data = request.get_json(silent=True) or {}
    warm_id = (data.get("warm_id") or "").strip()
    pick_element.cancel_active_pick(warm_id)
    return jsonify({"success": True})


# TEST-ONLY, off by default (AUTOFLOW_TEST_HOOKS=1 to enable): lets a
# UI-level test process that's driving the REAL Recording Editor page
# over HTTP (a separate process from this one - Playwright forbids two
# sync_playwright() sessions sharing a process) reach into the picker
# browser THIS process's own pick_element.py background thread owns,
# without a second, unreliable CDP connection (see recorder/
# pick_element.py's own docstring on why that's a dead end). Pushes onto
# _TEST_DRIVE_QUEUE, consumed by _run_pick_wait_phase's own wait loop on
# the one thread allowed to touch that browser. Never registered/usable
# unless the env var is set - a real deployment never has this route at
# all in any meaningful sense (it 404s... actually 403s, see below).
_TEST_HOOKS_ENABLED = os.environ.get("AUTOFLOW_TEST_HOOKS") == "1"


@app.route("/api/recordings/pick_element/_test_drive", methods=["POST"])
def api_recordings_pick_element_test_drive():
    if not _TEST_HOOKS_ENABLED:
        return jsonify({"success": False, "message": "test hooks disabled"}), 403

    data = request.get_json(silent=True) or {}
    action = (data.get("action") or "").strip()

    if action == "click_xpath":
        xpath = data.get("xpath") or ""

        def _drive(browser, context):
            p = context.pages[0]
            loc = p.locator(f"xpath={xpath}").first
            try:
                loc.scroll_into_view_if_needed(timeout=5000)
            except Exception:
                pass
            box = loc.bounding_box(timeout=5000)
            if box:
                cx = box["x"] + box["width"] / 2
                cy = box["y"] + box["height"] / 2
                p.mouse.click(cx, cy)

        pick_element._TEST_DRIVE_QUEUE.put(_drive)

    elif action == "drag_over_xpath":
        # FOLLOW-UP FIX (Part 4/V1/V8 verification): same test-drive
        # pattern as click_xpath above, for a real drag-select gesture
        # instead of a plain click - lets an automated test exercise the
        # picker's OWN real mousedown/mousemove/mouseup drag-select
        # handling (action_capture.js) inside the real, server-launched
        # picker browser, the same way a person dragging a box over a
        # product list would. Test-hooks-only, same gate as every other
        # action here.
        xpath = data.get("xpath") or ""

        def _drive(browser, context):
            p = context.pages[0]
            loc = p.locator(f"xpath={xpath}")
            count = loc.count()
            if count < 2:
                return
            first_box = loc.first.bounding_box(timeout=5000)
            last_box = loc.nth(count - 1).bounding_box(timeout=5000)
            if not first_box or not last_box:
                return
            x1 = first_box["x"] + 2
            y1 = first_box["y"] + 2
            x2 = last_box["x"] + last_box["width"] - 2
            y2 = last_box["y"] + last_box["height"] - 2
            p.mouse.move(x1, y1)
            p.mouse.down()
            p.mouse.move((x1 + x2) / 2, (y1 + y2) / 2, steps=5)
            p.mouse.move(x2, y2, steps=8)
            p.mouse.up()

        pick_element._TEST_DRIVE_QUEUE.put(_drive)

    elif action == "drag_hold_scroll":
        # FOLLOW-UP FIX (Part B verification, S2): same test-drive pattern
        # as the others above - drags from a starting element toward the
        # bottom edge of the viewport and HOLDS there, giving the picker's
        # own auto-scroll (a requestAnimationFrame loop keyed off the last
        # known mouse position, not fresh mousemove events) real wall-
        # clock time to actually scroll the page while the drag is still
        # active, the same way a person dragging past the bottom edge of
        # their screen would. Test-hooks-only, same gate as every other
        # action here.
        start_xpath = data.get("start_xpath") or ""
        hold_ms = int(data.get("hold_ms") or 2500)

        def _drive(browser, context):
            p = context.pages[0]
            loc = p.locator(f"xpath={start_xpath}").first
            box = loc.bounding_box(timeout=5000)
            if not box:
                return
            # a REAL drag-select covers some actual width, not a single
            # vertical line - a zero-width rectangle can never reach the
            # picker's own 60% area-overlap rule (the intersection width
            # is always 0), leaving only the content-box-center rule to
            # possibly match, which needs near-pixel-perfect horizontal
            # alignment with items whose own text width varies - CONFIRMED
            # REAL bug in this test drive (not the app) that made an
            # earlier version of this verification report "multi_none"
            # even though the picker's own candidate accumulation was
            # working correctly. Starts near the LEFT edge of the item,
            # ends near the RIGHT edge at the bottom.
            x1 = box["x"] + box["width"] * 0.15
            width_px = data.get("width_px")
            x2 = (x1 + float(width_px)) if width_px else (box["x"] + box["width"] * 0.85)
            y = box["y"] + box["height"] / 2
            viewport = p.viewport_size or {"width": 1280, "height": 720}
            edge_y = viewport["height"] - 20
            p.mouse.move(x1, y)
            p.mouse.down()
            p.mouse.move(x2, edge_y, steps=10)
            p.wait_for_timeout(hold_ms)
            p.mouse.up()

        pick_element._TEST_DRIVE_QUEUE.put(_drive)

    elif action == "close_browser":
        def _drive(browser, context):
            browser.close()

        pick_element._TEST_DRIVE_QUEUE.put(_drive)

    else:
        return jsonify({"success": False, "message": f"unknown action {action!r}"}), 400

    return jsonify({"success": True})


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

    # FOLLOW-UP FIX 4 (CONFIRMED REAL BUG): saving an edit never carried
    # the source recording's own display_name over at all - the frontend
    # already sends the full recordingData object (which includes
    # display_name, see recording_editor.html's own saveEditedBtn handler
    # and its use of recordingData.display_name elsewhere), this endpoint
    # just never read it. ".strip()" ensures re-editing an ALREADY-edited
    # copy (whose display_name is already "X (edited)") doesn't stack a
    # second "(edited)" suffix. A recording with no display_name at all
    # keeps today's behavior exactly - test_case simply gets no
    # display_name key, same as before this fix existed.
    source_display_name = (recording.get("display_name") or "").strip()
    if source_display_name:
        new_display_name = (
            source_display_name
            if source_display_name.endswith("(edited)")
            else f"{source_display_name} (edited)"
        )
    else:
        new_display_name = None

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
    if new_display_name:
        test_case["display_name"] = new_display_name  # FOLLOW-UP FIX 4

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

    # Shared regenerate-on-save step, pointed at the edited-scripts folder
    # so it never mixes with a script generated from the original
    # recording. The user never has to trigger this by hand; it happens
    # automatically as part of Save Edited JSON.
    #
    # Re-read the file we just wrote, rather than reusing the in-memory
    # test_case dict, so the script is provably generated from the SAVED
    # JSON on disk - the single source of truth - not just from whatever
    # was in memory a moment earlier.
    try:
        saved_test_case = repository.load_recording(str(path))
    except Exception as e:
        logger.error("couldn't re-read saved recording for script generation: %s", e)
        saved_test_case = None

    if saved_test_case is not None:
        _regenerate_script_after_save(saved_test_case, output_dir=EDITED_OUTPUT_DIR)

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


# ============================================================
# SCREENSHOT STAGES - read-only browsing of one run's screenshots,
# grouped into the named stages the replay engine already organizes them
# into on disk (see generator/script_generator.py's run()/
# _derive_stage_name - not duplicated here, just read back from disk).
# Nothing here can change how a replay runs.
# ============================================================

SCREENSHOTS_ROOT = OUTPUT_DIR / "screenshoots"

_IMG_NUM_RE = re.compile(r"(\d+)")


def _resolve_run_dir(run_dir_str):
    """Resolves a run's screenshot folder as the frontend sends it (a
    repo-relative or absolute path) to a real directory under
    generated_scripts/screenshoots/ - returns None if it would land
    outside that folder (no path escaping) or doesn't exist.
    """
    raw = (run_dir_str or "").strip()
    if not raw:
        return None
    p = Path(raw)
    candidate = p if p.is_absolute() else (BASE_DIR / raw)
    try:
        candidate = candidate.resolve()
        candidate.relative_to(SCREENSHOTS_ROOT.resolve())
    except (ValueError, OSError):
        return None
    if not candidate.is_dir():
        return None
    return candidate


def _resolve_screenshot_file(path_str):
    """Same containment rule as _resolve_run_dir, for a single screenshot
    file rather than a run's whole folder."""
    raw = (path_str or "").strip()
    if not raw:
        return None
    p = Path(raw)
    candidate = p if p.is_absolute() else (BASE_DIR / raw)
    try:
        candidate = candidate.resolve()
        candidate.relative_to(SCREENSHOTS_ROOT.resolve())
    except (ValueError, OSError):
        return None
    if not candidate.is_file():
        return None
    return candidate


def _resolve_stage_dir(session_dir, stage_name):
    """Resolves a stage subfolder name (e.g. "events") within an
    ALREADY-validated session directory - rejects anything that isn't a
    real, directly-contained subdirectory of it (blocks a stage name
    containing "..", a slash, or anything else that would escape the
    session folder).
    """
    raw = (stage_name or "").strip()
    if not raw:
        return None
    candidate = session_dir / raw
    try:
        candidate = candidate.resolve()
        candidate.relative_to(session_dir.resolve())
    except (ValueError, OSError):
        return None
    if candidate == session_dir.resolve() or not candidate.is_dir():
        return None
    return candidate


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def _get_image_files(folder: Path, recursive=False) -> list[Path]:
    """Finds all image files (.png, .jpg, .jpeg, .webp) in folder (or recursively)."""
    if not folder or not folder.exists() or not folder.is_dir():
        return []
    pattern = "**/*" if recursive else "*"
    images = []
    try:
        for f in folder.glob(pattern):
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS:
                images.append(f)
    except OSError:
        pass
    return images


def _image_sort_key(path: Path):
    """Sorts image files: if filename contains number (img1, img2), sorts by number, otherwise by modification time or name."""
    m = _IMG_NUM_RE.search(path.stem)
    if m:
        return (0, int(m.group(1)), path.name)
    try:
        return (1, path.stat().st_mtime, path.name)
    except Exception:
        return (2, 0, path.name)


def _cleanup_empty_dirs(root_dir: Path):
    """Recursively removes empty directories under root_dir."""
    if not root_dir or not root_dir.exists() or not root_dir.is_dir():
        return
    try:
        for child in sorted(root_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if child.is_dir():
                try:
                    if not any(child.iterdir()):
                        child.rmdir()
                except OSError:
                    pass
    except OSError:
        pass


def _image_number(path: Path):
    m = _IMG_NUM_RE.search(path.stem)
    return int(m.group(1)) if m else 0


@app.route("/run/stages")
def run_stages_page():
    """Opens the Screenshot Stages viewer for one run's folder. Read-only
    - just a display of what run() already wrote to disk.
    """
    run_dir = request.args.get("run_dir", "").strip()

    if not run_dir:
        return ("run_dir is required.", 400)

    resolved = _resolve_run_dir(run_dir)

    if resolved is None:
        return (f"Run folder not found: {run_dir}", 404)

    display_run_dir = str(resolved.relative_to(BASE_DIR)).replace("\\", "/")

    return render_template("run_stages.html", run_dir=display_run_dir)


@app.route("/api/runs/stages")
def api_runs_stages():
    """Read-only: lists the named stage subfolders under one run's
    screenshot folder, each with its screenshots, in the order the
    stages actually happened.
    """
    run_dir = request.args.get("run_dir", "").strip()

    if not run_dir:
        return jsonify({"success": False, "message": "run_dir is required.", "stages": []})

    resolved = _resolve_run_dir(run_dir)

    if resolved is None:
        return jsonify({
            "success": False,
            "message": f"Run folder not found: {run_dir}",
            "stages": [],
        })

    stages = []

    try:
        _cleanup_empty_dirs(resolved)
        for entry in resolved.iterdir():
            if not entry.is_dir():
                continue
            images = sorted(_get_image_files(entry, recursive=False), key=_image_sort_key)
            if not images:
                continue
            earliest_mtime = min(img.stat().st_mtime for img in images)
            stages.append({
                "name": entry.name,
                "earliest_mtime": earliest_mtime,
                "first_index": _image_sort_key(images[0]),
                "images": [
                    str(img.relative_to(BASE_DIR)).replace("\\", "/")
                    for img in images
                ],
            })
    except OSError as e:
        logger.error("couldn't list stages for %s: %s", run_dir, e)
        return jsonify({
            "success": False,
            "message": "Couldn't read this run's screenshot folder.",
            "stages": [],
        })

    stages.sort(key=lambda s: (s["earliest_mtime"], s["first_index"]))

    return jsonify({"success": True, "stages": stages})


@app.route("/screenshots/raw")
def screenshots_raw():
    """Read-only: serves one screenshot file's raw bytes, for the Stages
    viewer's <img> tags.
    """
    path_arg = request.args.get("path", "").strip()

    resolved = _resolve_screenshot_file(path_arg)

    if resolved is None:
        return ("Screenshot not found.", 404)

    return send_file(str(resolved), mimetype="image/png")


# ============================================================
# SCREENSHOTS VIEWER - a dashboard-level entry point listing EVERY past
# run's screenshot session (reverse chronological).
# ============================================================

@app.route("/screenshots")
def screenshots_viewer_page():
    return render_template("screenshots_viewer.html")


@app.route("/api/screenshots/sessions")
def api_screenshots_sessions():
    """Read-only: lists every session folder under
    generated_scripts/screenshoots/ that actually holds screenshots.
    """
    sessions = []

    # optional ?session=<recording name>: only that recording's own run
    # folders (see storage/session_files.py) - the dashboard's per-session
    # Screenshots button
    only_session = request.args.get("session", "").strip()

    try:
        _cleanup_empty_dirs(SCREENSHOTS_ROOT)
        for entry in SCREENSHOTS_ROOT.iterdir():
            if not entry.is_dir():
                continue
            if only_session and not session_files.is_run_folder_of(only_session, entry.name):
                continue
            images = _get_image_files(entry, recursive=True)
            image_count = len(images)
            if image_count == 0:
                continue
            sessions.append({
                "session_id": entry.name,
                "run_dir": str(entry.relative_to(BASE_DIR)).replace("\\", "/"),
                "image_count": image_count,
                "modified": entry.stat().st_mtime,
            })
    except OSError as e:
        logger.error("couldn't list screenshot sessions: %s", e)
        return jsonify({
            "success": False,
            "message": "Couldn't read the screenshots folder.",
            "sessions": [],
        })

    sessions.sort(key=lambda s: s["modified"], reverse=True)

    return jsonify({"success": True, "sessions": sessions})


@app.route("/api/screenshots/stages")
def api_screenshots_stages():
    """Read-only: lists the stage subfolders that actually exist inside
    ONE session's screenshot folder.
    """
    run_dir = request.args.get("run_dir", "").strip()

    if not run_dir:
        return jsonify({
            "success": False,
            "message": "run_dir is required.",
            "stages": [],
            "root_images": [],
        })

    session_dir = _resolve_run_dir(run_dir)

    if session_dir is None:
        return jsonify({
            "success": False,
            "message": f"Session folder not found: {run_dir}",
            "stages": [],
            "root_images": [],
        })

    stage_entries = []

    try:
        _cleanup_empty_dirs(session_dir)
        root_images = sorted(_get_image_files(session_dir, recursive=False), key=_image_sort_key)

        for entry in session_dir.iterdir():
            if not entry.is_dir():
                continue
            images_here = _get_image_files(entry, recursive=False)
            if not images_here:
                continue
            earliest_mtime = min(img.stat().st_mtime for img in images_here)
            stage_entries.append({
                "name": entry.name,
                "earliest_mtime": earliest_mtime,
                "first_index": min(_image_sort_key(f) for f in images_here),
            })
    except OSError as e:
        logger.error("couldn't list stages for %s: %s", run_dir, e)
        return jsonify({
            "success": False,
            "message": "Couldn't read this session's folder.",
            "stages": [],
            "root_images": [],
        })

    stage_entries.sort(key=lambda s: (s["earliest_mtime"], s["first_index"]))

    return jsonify({
        "success": True,
        "stages": [s["name"] for s in stage_entries],
        "root_images": [
            str(img.relative_to(BASE_DIR)).replace("\\", "/") for img in root_images
        ],
    })


@app.route("/api/screenshots/images")
def api_screenshots_images():
    """Read-only: lists the image files that actually exist inside
    ONE session's ONE stage subfolder.
    """
    run_dir = request.args.get("run_dir", "").strip()
    stage = request.args.get("stage", "").strip()

    if not run_dir or not stage:
        return jsonify({
            "success": False,
            "message": "run_dir and stage are required.",
            "images": [],
        })

    session_dir = _resolve_run_dir(run_dir)

    if session_dir is None:
        return jsonify({
            "success": False,
            "message": f"Session folder not found: {run_dir}",
            "images": [],
        })

    stage_dir = _resolve_stage_dir(session_dir, stage)

    if stage_dir is None:
        return jsonify({
            "success": False,
            "message": f"Stage folder not found: {stage}",
            "images": [],
        })

    try:
        images = sorted(_get_image_files(stage_dir, recursive=False), key=_image_sort_key)
    except OSError as e:
        logger.error("couldn't list images for %s/%s: %s", run_dir, stage, e)
        return jsonify({
            "success": False,
            "message": "Couldn't read this stage's folder.",
            "images": [],
        })

    return jsonify({
        "success": True,
        "images": [
            {
                "filename": img.name,
                "path": str(img.relative_to(BASE_DIR)).replace("\\", "/"),
            }
            for img in images
        ],
    })


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
                        "in the terminal, or use "
                        "Stop Recording, before "
                        "launching another."
                    ),
                    "url": url,
                    "page_title": None,
                }
            )

        session_state["active"] = True
        session_state["phase"] = "launching"
        session_state["last_message"] = None
        session_state["current_url"] = None

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


@app.route("/api/recording/stop", methods=["POST"])
def api_recording_stop():
    """Dashboard-driven equivalent of pressing ENTER in the terminal -
    reuses the exact same stop mechanism (the enter_pressed Event the
    recording session's own wait loop already watches - see
    _run_recording_session), it's just triggered from here instead of
    stdin. No second recorder/stop implementation exists.

    Idempotent: a second call while already stopping (or after the
    recording has already finished) is a safe no-op that reports the
    current phase rather than trying to stop anything twice.
    """
    with state_lock:
        phase = session_state["phase"]

        if not session_state["active"]:
            return jsonify({
                "success": False,
                "message": "No active recording to stop.",
                "phase": phase,
            })

        if phase == "stopping":
            return jsonify({
                "success": True,
                "message": "Already stopping this recording...",
                "phase": "stopping",
            })

        enter_pressed = _recording_control.get("enter_pressed")

        if enter_pressed is None:
            # "active" flips True the instant the launch thread starts,
            # before the browser/page/recorder exist yet - a stop request
            # landing in that brief window has nothing to signal yet.
            return jsonify({
                "success": False,
                "message": (
                    "Recording is still starting up - try Stop Recording "
                    "again in a moment."
                ),
                "phase": phase,
            })

        session_state["phase"] = "stopping"
        session_state["last_message"] = "Stopping recording..."

    # Set outside the lock - it's the recording thread's own Event, not
    # part of session_state, and nothing about setting it needs the lock.
    enter_pressed.set()

    return jsonify({
        "success": True,
        "message": "Stopping recording...",
        "phase": "stopping",
    })


@app.route("/api/recording/status")
def api_recording_status():
    """Polled by the dashboard while a recording is launching/active, so
    it can render Recording / Stopping... / Recording Completed /
    Recording Failed without the user ever needing the terminal. Purely
    read-only - never changes session_state itself.
    """
    with state_lock:
        return jsonify({
            "phase": session_state["phase"],
            "active": session_state["active"],
            "recording": session_state["recording"],
            "current_url": session_state["current_url"],
            "message": session_state["last_message"],
            "recording_path": session_state["last_recording_path"],
            "recording_name": session_state["last_recording_name"],
            "action_count": session_state["last_action_count"],
            "stop_reason": session_state["last_stop_reason"],
        })


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


def _load_test_case_for_run(body):
    """Shared by /api/test/run and /api/test/run/start: resolves the
    request body's qa_url/recording_path into the test_case to replay -
    either the recording named by recording_path, or (with none given) a
    bare ad-hoc case that just opens qa_url with no recorded actions.
    Returns (test_case, qa_url, error_response_or_None) - callers return
    error_response as-is the moment it's non-None.
    """
    qa_url = body.get("qa_url", "")
    recording_path = body.get("recording_path", "")

    if not qa_url.strip():
        return None, qa_url, jsonify({
            "status": "FAIL",
            "message": "QA website URL is required",
            "html_report": None,
            "json_report": None,
        })

    test_case = {
        "name": f"adhoc_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "start_url": qa_url,
        "actions": [],
    }

    if recording_path.strip():
        try:
            test_case = repository.load_recording(recording_path)
        except (FileNotFoundError, OSError) as e:
            logger.error("couldn't load recording %s: %s", recording_path, e)
            return None, qa_url, jsonify({
                "status": "FAIL",
                "message": f"couldn't find recording at {recording_path}",
                "html_report": None,
                "json_report": None,
            })

    return test_case, qa_url, None


def _screenshot_options_from_body(body):
    """Shared by /api/test/run and /api/test/run/start: pulls the
    optional screenshot-comparison overrides out of the request body -
    screenshot_threshold (float), screenshot_ignored_regions (a list of
    {x, y, width, height} dicts, in the baseline image's own pixel
    coordinates), screenshot_strict (bool) - straight into the dict shape
    validation.compare_screenshots() takes as keyword args. Returns None
    (not an empty dict) when nothing was given, so downstream code can
    just do `compare_screenshots(a, b, **(options or {}))` and get that
    function's own defaults untouched - same behavior as before these
    existed for every caller that doesn't pass them.
    """
    options = {}
    if body.get("screenshot_threshold") is not None:
        try:
            options["threshold"] = float(body["screenshot_threshold"])
        except (TypeError, ValueError):
            pass
    if body.get("screenshot_ignored_regions"):
        options["ignored_regions"] = body["screenshot_ignored_regions"]
    if body.get("screenshot_strict"):
        options["strict"] = True
    return options or None


def _json_on_error(plain):
    """Replay/run API routes always answer with JSON: an unexpected error becomes
    {"success": false, "error": <plain sentence>, "message": <same>} (HTTP 500) - the
    dashboard shows that sentence - and the full traceback goes to the terminal."""
    import functools
    import traceback

    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **k):
            try:
                return fn(*a, **k)
            except Exception:
                logger.error("%s failed: %s", fn.__name__, traceback.format_exc())
                print(traceback.format_exc(), flush=True)
                return jsonify({"success": False, "error": plain, "message": plain}), 500
        return wrapper
    return deco


@app.route(
    "/api/test/run",
    methods=["POST"]
)
@_json_on_error("The replay could not be run because of an unexpected problem in AutoFlow. Details are in the server terminal.")
def api_test_run():

    body = request.get_json(
        force=True,
        silent=True
    ) or {}

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

    test_case, qa_url, error_response = _load_test_case_for_run(body)
    if error_response is not None:
        return error_response

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
        # lets execute_test() scale its subprocess timeout to this
        # session's real length instead of one fixed ceiling shared by
        # every session - see _compute_script_timeout()
        action_count=len(test_case.get("actions", [])),
        screenshot_options=_screenshot_options_from_body(body),
        has_otp_step=test_case_has_otp_step(test_case),
    )

    # execute_test already wrote the full result to report.json inside
    # the run's own folder - no separate storage/executions/ copy needed.
    run_dir = (
        BASE_DIR / result["run_dir"]
        if result.get("run_dir") else None
    )

    # PHASE 2d: the report's own <title>/heading uses this when set (see
    # report.html) - test_case is this exact run's own recording, loaded
    # just above, so no separate lookup is needed here.
    result["test_name"] = test_case.get("name")
    result["display_name"] = test_case.get("display_name")
    # PHASE 4b: the report's own "Recorded vs Replayed" column uses this.
    result["recorded_actions"] = test_case.get("actions") or []

    _attach_sub_lines_to_steps(result)
    html_report_path = generate_report(
        result,
        output_dir=run_dir,
    )

    return jsonify(
        {
            "status": result["status"],
            "message": result["message"],
            "steps": result["steps"],
            "ui_elements": result["ui_elements"],
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


# ============================================================
# ASYNC REPLAY - Live Replay Progress. Same engine as /api/test/run above
# (same generate_script(), same executor) - the only difference is that
# starting a run and reading its result are two separate calls, so the
# dashboard can poll for progress instead of the request just hanging
# until the whole replay finishes. See executor/run_execution.py's
# start_replay()/poll_replay() for the actual async plumbing; this is
# just their HTTP-facing wrapper, including the same html_report
# generation step /api/test/run already did for a finished run.
# ============================================================

_run_meta = {}
_run_meta_lock = threading.Lock()


@app.route("/api/test/run/start", methods=["POST"])
@_json_on_error("The replay could not be started because of an unexpected problem in AutoFlow. Details are in the server terminal.")
def api_test_run_start():

    body = request.get_json(force=True, silent=True) or {}

    expected_content = body.get("expected_content", "")
    expected_screenshot = body.get("expected_screenshot", "")
    product_to_verify = body.get("product_to_verify", "")

    test_case, qa_url, error_response = _load_test_case_for_run(body)
    if error_response is not None:
        return error_response

    script_path = generate_script(test_case)
    action_count = len(test_case.get("actions", []))

    run_id, run_dir = start_replay(
        qa_url,
        script_path,
        expected_content,
        expected_screenshot,
        product_to_verify,
        test_case.get("name"),
        action_count=action_count,
        screenshot_options=_screenshot_options_from_body(body),
        has_otp_step=test_case_has_otp_step(test_case),
    )

    with _run_meta_lock:
        _run_meta[run_id] = {
            "test_name": test_case.get("name"),
            # PHASE 2d: absent (None) on any recording saved before
            # display_name existed - the live log/report fall back to
            # test_name exactly as they always have.
            "display_name": test_case.get("display_name"),
            "total_steps": action_count,
            "html_report": None,
            # the recorded actions themselves - only used so the live log
            # (see /api/test/run/stream) can show a human label like
            # "click - Add to Bag" per step; the run report's own
            # per-step results never carry the recorded locator_profile
            # back, only what replay resolved against
            "actions": test_case.get("actions", []),
        }

    return jsonify({
        "success": True,
        "run_id": run_id,
        "run_dir": run_dir,
        "test_name": test_case.get("name"),
        "total_steps": action_count,
    })


# ============================================================
# OTP-STEP HANDLING: the replay subprocess pauses and waits for a
# human-submitted OTP value (see generator/script_generator.py's own
# _wait_for_live_otp) via a plain marker file inside its own run_dir -
# this route is the other end of that hand-off. run_dir is a pure,
# deterministic function of run_id alone (the exact same computation
# _prepare_run() in executor/run_execution.py already uses), so this
# needs no lookup into that module's own in-memory _active_replays
# state - only used to decide, for a genuinely unknown run_id, whether
# to report a clear error instead of silently writing a file nothing
# will ever read.
# ============================================================

@app.route("/api/test/run/otp_submit", methods=["POST"])
@_json_on_error("The OTP could not be passed to the replay because of an unexpected problem in AutoFlow. Details are in the server terminal.")
def api_test_run_otp_submit():
    data = request.get_json(silent=True) or {}
    run_id = (data.get("run_id") or "").strip()
    value = (data.get("value") or "").strip()

    if not run_id:
        return jsonify({"success": False, "message": "run_id is required."})
    if not value:
        return jsonify({"success": False, "message": "Enter an OTP value first."})

    run_dir = BASE_DIR / "generated_scripts" / "screenshoots" / run_id
    if not run_dir.is_dir():
        return jsonify({"success": False, "message": "Unknown or already-finished run_id."})

    try:
        (run_dir / "otp_input.txt").write_text(value, encoding="utf-8")
    except Exception as e:
        logger.error("otp_submit: couldn't write OTP marker file for run %s: %s", run_id, e)
        return jsonify({"success": False, "message": "Couldn't submit the OTP - please try again."})

    return jsonify({"success": True})


def _summarize_steps(steps):
    """Shared pass/fail/warning tally for the progress panel.

    PHASE 6 BUG FIX: CONFIRMED REAL BUG - "failed" used to be every step
    with success != True, which counts a step stop_on_failure backfilled
    as not_run (never actually attempted) as a genuine failure too. Two of
    this function's three call sites (see api_test_run_stream's own
    "summary" SSE event) already worked around this by subtracting a
    separately-computed `skipped` count from the result - the THIRD
    (api_test_run_progress's "done" response) had no such correction and
    returned an inflated "failed" straight from here. Fixed at the
    source instead: "failed" now excludes not_run by construction, so
    every caller gets the correct number automatically, whether or not it
    happens to also compute skipped/not_run separately for its own
    display purposes.

    FOLLOW-UP FIX (Part 2, CONFIRMED REAL BUG): "warning" used to ALSO
    count a step whose strategy_used was text+tag/bounding_box (the two
    weakest locator tiers) - a completely separate "fragile, consider re-
    recording" concept ALREADY shown on its own, independently, via each
    step's own locator_report.weak (see report.html's "weak" pill and the
    dashboard's own "N locator warning(s)" line) - regardless of whether
    that step carried an actual visible warning note. This made the "N
    warnings" TOTAL bigger than the number of yellow WARNING items ever
    shown anywhere (report_generator.py's own _plain_summary, and every
    UI surface's own warning display, all key off step.warning being
    truthy - never strategy_used). One source now: a step counts as a
    warning here if and only if it actually carries a warning note, the
    exact same condition that makes it render as one anywhere else.
    """
    # WARNING is its own status next to PASS/FAIL/SKIPPED: "passed" counts
    # only CLEAN passes (a succeeded step with no warning note), so
    # Passed + Warnings + Failed (+ Skipped) adds up to the step total -
    # a warning step is counted once, under "warnings", never also here
    # a manual-input step (an OTP wait a human completes) is its own bucket
    # in the HTML report and the dashboard - counted here the same way so
    # every surface shows the same numbers
    def _is_manual(st):
        return bool(st.get("otp_role")) and st.get("success") is not False and not st.get("not_run")

    manual_input = sum(1 for s in steps if _is_manual(s))
    passed = sum(1 for s in steps if s.get("success") and not s.get("warning") and not _is_manual(s))
    failed = sum(1 for s in steps if not s.get("success") and not s.get("not_run"))
    warnings = sum(1 for s in steps if s.get("success") and s.get("warning") and not _is_manual(s))
    # FIX 2: a step's own page_mismatch_info is truthy only when its
    # effect-verification detected a genuine page mismatch - counted
    # separately from "warnings" (which page_mismatch's own nav_warning
    # note also contributes to today) so the dashboard can show a
    # dedicated "Page mismatches" figure.
    page_mismatches = sum(1 for s in steps if s.get("page_mismatch_info"))
    return {"passed": passed, "failed": failed, "warnings": warnings, "page_mismatches": page_mismatches, "manual_input": manual_input}


@app.route("/api/test/run/progress")
@_json_on_error("The replay progress could not be read because of an unexpected problem in AutoFlow. Details are in the server terminal.")
def api_test_run_progress():

    run_id = (request.args.get("run_id") or "").strip()

    if not run_id:
        return jsonify({"success": False, "message": "run_id is required."})

    progress = poll_replay(run_id)

    if progress is None:
        return jsonify({
            "success": False,
            "message": "Unknown run_id - it may have finished before this server was last restarted.",
        })

    with _run_meta_lock:
        meta = dict(_run_meta.get(run_id) or {})

    if not progress["done"]:
        steps = progress.get("steps") or []
        return jsonify({
            "success": True,
            "done": False,
            "test_name": meta.get("test_name"),
            "total_steps": progress.get("total_steps") or meta.get("total_steps"),
            "steps": steps,
            **_summarize_steps(steps),
        })

    result = progress["result"]
    # PHASE 2d: same as api_test_run_result's own synchronous copy of this -
    # meta was already loaded above for test_name; the report's own
    # <title>/heading uses this when set.
    result["test_name"] = meta.get("test_name")
    result["display_name"] = meta.get("display_name")
    result["recorded_actions"] = meta.get("actions") or []  # PHASE 4b

    # generate_report() is only ever run ONCE per run_id, the first poll
    # that observes it done - repeat polls afterward (the frontend keeps
    # polling briefly to display the final state) reuse the cached path
    # instead of regenerating the same HTML report on every request.
    with _run_meta_lock:
        cached_html_report = (_run_meta.get(run_id) or {}).get("html_report")

    if cached_html_report is None:
        run_dir = BASE_DIR / result["run_dir"] if result.get("run_dir") else None
        _attach_sub_lines_to_steps(result)
        html_report_path = generate_report(result, output_dir=run_dir)
        cached_html_report = str(html_report_path.relative_to(BASE_DIR)).replace("\\", "/")
        with _run_meta_lock:
            if run_id in _run_meta:
                _run_meta[run_id]["html_report"] = cached_html_report

    steps = result.get("steps") or []

    return jsonify({
        "success": True,
        "done": True,
        "test_name": meta.get("test_name"),
        "total_steps": meta.get("total_steps"),
        "status": result["status"],
        "message": result["message"],
        "steps": steps,
        "ui_elements": result["ui_elements"],
        "html_report": cached_html_report,
        "json_report": (
            result["run_dir"] + "/report.json"
            if result.get("run_dir") else None
        ),
        **_summarize_steps(steps),
    })


# ============================================================
# LIVE LOG (separate window) - a Server-Sent Events stream of the SAME
# poll_replay()/report.json data /api/test/run/progress already reads,
# reshaped into one event per NEWLY-completed step instead of the whole
# steps-so-far list on every poll. No second replay-tracking mechanism -
# this only ever reads what start_replay()'s watcher thread and the
# generated script's own incremental report.json writes already produce.
# See templates/live_log.html for the popup window that consumes this,
# and static/js/script.js's runRecording() for where that window gets
# opened.
# ============================================================

def _step_display_status(step):
    """running/pass/warning/fail/skipped for one finished step - "skipped"
    is a real, distinct outcome for a step never attempted (see
    _skip_deps_until_url and the post-loop not-executed backfill in
    script_generator.py's run()), not just another failure - both stamp a
    recognizable message prefix on `error` rather than their own boolean
    field, so that's what this reads instead of inventing a new one.

    FOLLOW-UP FIX 2: "warning" is a real, distinct outcome for a step that
    SUCCEEDED but carries a non-fatal note (e.g. Fix 1's "Value changed on
    the site..." note) - CONFIRMED REAL BUG this fixes: such a step used
    to be indistinguishable from an ordinary clean pass anywhere the live
    log/dashboard read this status, even though the replay engine had
    already computed the warning and stored it on the step.
    """
    if step.get("success"):
        return "warning" if step.get("warning") else "pass"
    err = (step.get("error") or "")
    # not_run is the explicit flag on every step stop_on_failure never
    # reached - its message reads "NOT RUN (stopped after step N failed)",
    # which the two lowercase prefixes below never matched, so such a step
    # showed as a FAILED line and the summary's Skipped count stayed 0
    if step.get("not_run") or err.startswith("skipped") or err.startswith("not executed") or err.startswith("NOT RUN"):
        return "skipped"
    return "fail"


def _step_failure_reason(step, element_label=None):
    """Plain-language WHY (or, for a passing-with-warning step, WHAT
    CHANGED) - built entirely from fields the replay engine already
    computes per step (see script_generator.py's own result["steps"].
    append() call sites) - no new data collection, just formatting what's
    already there into one readable block.

    PHASE 4a: "plain" is the one-sentence version (see
    validation/report_generator.py's own plain_language_reason, the same
    function the downloadable report uses) - "error"/"warning" below stay
    exactly as they were, for the live log's own "Details" disclosure.

    FOLLOW-UP FIX 2 (CONFIRMED REAL BUG): this used to return None
    outright for any successful step, which silently discarded a passing
    step's own "warning" field - the live log/dashboard had no way to
    show the "Value changed on the site..." note for a step that PASSED,
    only for one that failed. Now only returns None when there's
    genuinely nothing to show (success and no warning).
    """
    error = step.get("error")
    warning = step.get("warning")
    if step.get("success") and not warning:
        return None
    if step.get("not_run"):
        # a step that was never reached has no failure of its own to explain
        # beyond "not run because step N failed: <reason>"
        return {
            "error": None, "technical": None, "selector": None, "url": None,
            "screenshot": None, "warning": None,
            "plain": step_headline(step, element_label),
        }
    return {
        # REQ 5: "plain" is the one-sentence headline (what was expected /
        # what happened / what the replay did). Everything technical -
        # selectors, full URLs, boxes - is Details only: "technical" (the
        # replay engine's own explanation) plus the fields below
        "plain": step_headline(step, element_label),
        "technical": step.get("technical"),
        "error": error,
        "selector": step.get("strategy_used"),
        "url": step.get("url_after") or step.get("url_before"),
        "screenshot": step.get("screenshot"),
        "warning": warning,
    }


def _attach_sub_lines_to_steps(result):
    """The replay's sub-lines (what AutoFlow did around each step: waits, hovers, clicks, ...) are
    not shown in the live log; they are kept as the step's Details (the report's "Details" /
    Last Log) - each line under the step it happened in, by time. Idempotent. Never raises."""
    try:
        entries = [
            e for e in (result.get("live_log") or [])
            if e.get("level") == "note" or str(e.get("message") or "").startswith("↳")
        ]
        steps = result.get("steps") or []
        if not entries or not steps:
            return
        from datetime import datetime as _dt
        starts = []
        for s in steps:
            try:
                starts.append(_dt.fromisoformat(s["started_at"]).timestamp())
            except Exception:
                starts.append(None)
        per = {}
        for e in entries:
            t_ = e.get("t")
            idx = 0
            if isinstance(t_, (int, float)):
                for i, st in enumerate(starts):
                    if st is not None and st <= t_ + 0.05:
                        idx = i
            per.setdefault(idx, []).append(str(e.get("message") or "").lstrip("↳").strip())
        for i, msgs in per.items():
            s = steps[i]
            if s.get("_sub_lines_attached"):
                continue
            s["_sub_lines_attached"] = True
            s["technical"] = "; ".join(x for x in (s.get("technical"), "What AutoFlow did: " + " > ".join(m for m in msgs if m)) if x)
        # keep it in the saved report too (View Last Log reads report.json)
        if result.get("run_dir"):
            rp = BASE_DIR / result["run_dir"] / "report.json"
            if rp.is_file():
                saved = json.loads(rp.read_text(encoding="utf-8"))
                for i, s in enumerate(steps):
                    if s.get("_sub_lines_attached") and i < len(saved.get("steps", [])):
                        saved["steps"][i]["technical"] = s.get("technical")
                tmp = rp.with_name(rp.name + ".tmp")
                tmp.write_text(json.dumps(saved, indent=2), encoding="utf-8")
                os.replace(tmp, rp)
    except Exception:
        pass


def _href_human_name(lp):
    """A person's name for a link without text of its own: the words of the page it opens (the last part of
    its address that is a word - not a number or a generated code), e.g. "Beauty Page Appliances"; "... tile"
    when the link shows only an image. "" when there are no such words. Same rule as the replay script's
    _href_human_name. Never raises."""
    try:
        from urllib.parse import urlsplit as _us, unquote as _uq
        segs = [_uq(x) for x in _us((lp or {}).get("href") or "").path.split("/") if x]
        for seg in reversed(segs):
            has_d = any(c.isdigit() for c in seg)
            has_a = any(c.isalpha() for c in seg)
            # a number, or a long letters+digits token without separators (an id), is not a page name
            if not has_a or (has_d and len(seg) >= 8 and not re.search(r"[-_+]", seg)):
                continue
            for ext in (".html", ".htm", ".php", ".aspx", ".asp", ".jsp"):
                if seg.lower().endswith(ext):
                    seg = seg[: -len(ext)]
            words = [w for w in re.split(r"[-_+\s.]+", seg) if w]
            name = " ".join(w[:1].upper() + w[1:] for w in words)[:40].strip()
            if not name:
                continue
            img_only = ((lp.get("content_hint") or "").strip() == "image") or (lp.get("tag") or "").lower() == "img"
            return f"{name} tile" if img_only else name
    except Exception:
        pass
    return ""


def _step_element_label(recorded_actions, step):
    """The recorded step's own element text/name (e.g. "Add to Bag") -
    read from the ORIGINAL recording's locator_profile, since the run
    report's per-step result never echoes that back (see the "actions"
    comment in api_test_run_start above). None when unavailable (a
    scroll/navigate/tab_* step with no locator_profile at all, or an
    index this recording doesn't have).

    FOLLOW-UP FIX 5 (CONFIRMED REAL BUG): a step ADDED through the
    Recording Editor (count_elements, count_summary, compare_counts, ...)
    has no clicked-element text at all - the live log/dashboard showed
    only the generic action-type label ("Count Elements") for these,
    even though the editor already builds and saves a meaningful
    action.name ("Count product cards (50) -> product_counts", see
    buildAutoStepName in recording_editor.html) right onto this exact
    recorded_actions entry. An explicit name now wins here, same "an
    explicit action.name always wins" precedent recording_editor.html's
    own tab_open handling already documents - a RECORDED step with no
    name (the common case, unless it was manually renamed) falls straight
    through to the locator_profile-based label exactly as before.
    """
    index = step.get("index")
    if not index or not recorded_actions or index > len(recorded_actions):
        return None
    recorded_action = recorded_actions[index - 1] or {}
    explicit_name = (recorded_action.get("name") or "").strip()
    if explicit_name:
        return explicit_name
    if recorded_action.get("action_type") == "navigate":
        # "Open - <page title>" / "Go back - <page title>" (the page path when no title was recorded)
        _t = (recorded_action.get("page_title") or "").strip()[:60]
        if not _t:
            try:
                from urllib.parse import urlsplit as _us
                _segs = [x for x in _us(recorded_action.get("page_url") or "").path.split("/") if x]
                _t = (_segs[-1].replace("-", " ").replace("_", " ").title()) if _segs else "Home page"
            except Exception:
                _t = "page"
        _verb = {"back": "Go back", "forward": "Go forward"}.get(recorded_action.get("history"), "Open")
        return f"{_verb} \u2013 {_t}"
    lp = recorded_action.get("locator_profile") or {}
    attrs = lp.get("attributes") if isinstance(lp.get("attributes"), dict) else {}
    named = (
        lp.get("text") or lp.get("accessible_name") or lp.get("aria_label") or attrs.get("aria-label")
        or lp.get("title") or attrs.get("title") or attrs.get("alt")
        or (None if (lp.get("tag") or "").lower() in ("html", "body") else (lp.get("inner_label") or lp.get("near_text")))
        or lp.get("placeholder") or attrs.get("name")
    )
    if (named and (lp.get("content_hint") or "").strip() == "image" and (lp.get("tag") or "").lower() == "a"
            and not (lp.get("text") or lp.get("aria_label") or attrs.get("aria-label") or lp.get("title") or attrs.get("title"))
            and named in (lp.get("inner_label"), attrs.get("alt"), lp.get("accessible_name"))
            and recorded_action.get("action_type") in ("click", "dblclick", "right_click", "hover")):
        named = f"{str(named).strip()} tile"            # an image-only link named by its image: "Grooming tile"
    if not named and lp.get("href") and recorded_action.get("action_type") in ("click", "dblclick", "right_click", "hover"):
        named = _href_human_name(lp) or None
    if not named and lp.get("href") and recorded_action.get("action_type") in ("click", "dblclick", "right_click", "hover"):
        try:
            from urllib.parse import urlsplit as _us2, unquote as _uq
            _p = "/" + "/".join(_uq(x) for x in _us2(lp["href"]).path.split("/") if x)
            named = f"link to '{_p if len(_p) <= 56 else '...' + _p[-53:]}'"
        except Exception:
            pass
    if named or not lp or recorded_action.get("action_type") not in ("click", "dblclick", "right_click", "hover", "check", "fill", "select"):
        return named
    # nothing readable recorded: say what the element is or contains (never an id, never a bare tag)
    if (lp.get("tag") or "").lower() in ("html", "body"):
        return "page area"
    hint = (lp.get("content_hint") or "").strip()
    fr = recorded_action.get("frame") if isinstance(recorded_action.get("frame"), dict) else {}
    word = {"a": "link", "button": "button", "input": "field", "textarea": "field", "select": "dropdown",
            "img": "image"}.get((lp.get("tag") or "").lower()) or (lp.get("role") or "").lower() or "element"
    _sig_words = ""
    try:
        _toks = [x for x in str(lp.get("icon_signature") or "").split() if x]
        for _tk in _toks:
            if "-" in _tk and not _tk.startswith(("use=", "title=")):
                _first, _rest = _tk.split("-", 1)
                if _first and _first in _toks and _rest:
                    _sig_words = _rest.replace("-", " ").strip()[:30]
                    break
    except Exception:
        _sig_words = ""
    what = {"video": "video player", "audio": "audio player", "canvas": "drawing area", "image": "image",
            "icon": (_sig_words + " icon").strip(), "frame": "embedded content"}.get(hint)
    if isinstance(attrs, dict) and ("aria-haspopup" in attrs or "aria-expanded" in attrs):
        return f"{(lp.get('tag') or 'element').lower()} (menu button)"
    if hint.startswith("input:"):
        return hint.split(":", 1)[1] + " field"
    if what in ("icon", "image"):
        return f"{what} {word}" if word in ("button", "link") else what
    if what:
        return what
    if (fr.get("parent_iframe_name") or "").strip():
        return f"area in '{fr['parent_iframe_name']}'"
    pcn = recorded_action.get("popup_container") if isinstance(recorded_action.get("popup_container"), dict) else {}
    if pcn and word in ("control", "element", "item"):
        return f"area in '{pcn['aria_label']}'" if (pcn.get("aria_label") or "").strip() else "area in the popup"
    if word in ("control", "element", "item"):
        # a control with no name of its own (an icon drawn by an icon font, say): named by the label next to it
        try:
            _ctx = lp.get("nearby_label") or ""
            if not str(_ctx).strip():
                _ic = lp.get("item_context") if isinstance(lp.get("item_context"), dict) else {}
                _ctx = (_ic or {}).get("text") or ""
            if not str(_ctx).strip():
                # an older recording: the text of the nearest block around the control, from its saved HTML
                from html import unescape as _unesc
                _dc = recorded_action.get("dom_context") if isinstance(recorded_action.get("dom_context"), dict) else {}
                for _h in (_dc.get("act_target_html_chain") or [])[1:5]:
                    _t = re.sub(r"<[^>]*>", " ", str(_h or "").replace("...[truncated]", " "))
                    _t = re.sub(r"<[^>]*$", " ", _t)
                    _t = " ".join(_unesc("".join(ch for ch in _t if not (0xE000 <= ord(ch) <= 0xF8FF))).split())
                    if _t and len(_t) <= 40:
                        _ctx = _t
                        break
                    if len(_t) > 40:
                        break
            _ctx = " ".join(str(_ctx or "").split())
            return f"icon button next to '{_ctx[:30]}'" if _ctx else "icon button"
        except Exception:
            return "icon button"
    return word


def _step_name_is_full_sentence(recorded_actions, step):
    """FOLLOW-UP FIX (Part 4d, CONFIRMED REAL BUG): an ADDED step's own
    auto name (recording_editor.html's buildAutoStepName) always already
    reads as a full, verb-first sentence ("Select 'Girls' option") -
    prefixing the generic action-type label in front of that doubled the
    verb ("Click - Select 'Girls' option"). True only for an "added"-
    origin step that also has an explicit name (the exact case
    buildAutoStepName's output ends up in) - a RECORDED step's own name
    (even a manual rename via the per-row rename button) is NOT reliably
    verb-first, so it keeps the "TypeLabel - Name" display exactly as
    before. Mirrors recording_editor.html's own renderActions() check
    (action.origin === "added") so the editor and the live log never
    disagree about which steps get this treatment.
    """
    index = step.get("index")
    if not index or not recorded_actions or index > len(recorded_actions):
        return False
    recorded_action = recorded_actions[index - 1] or {}
    if recorded_action.get("action_type") == "navigate":
        return True                 # "Open - <page>" / "Go back - <page>" already read as a sentence
    return bool(recorded_action.get("origin") == "added" and (recorded_action.get("name") or "").strip())


@app.route("/api/test/run/stream")
def api_test_run_stream():
    """SSE stream: one 'step' event per newly-completed step, then one
    'summary' event once the run finishes, then the stream closes.
    Requires threaded=True on app.run() (already set) so this long-lived
    connection doesn't block any other request.
    """
    run_id = (request.args.get("run_id") or "").strip()

    def _sse(event, data):
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    def generate():
        if not run_id:
            yield _sse("stream_error", {"message": "run_id is required."})
            return

        with _run_meta_lock:
            meta = dict(_run_meta.get(run_id) or {})

        # PHASE 2d: sent once, right away - lets the live log page show
        # this run's own name (display_name when the recording has one,
        # else the auto test_name, exactly as before) instead of just the
        # generic "Live Replay Log" heading.
        yield _sse("meta", {
            "test_name": meta.get("test_name"),
            "display_name": meta.get("display_name"),
        })

        started_at = time.monotonic()
        sent_count = 0
        # OTP-STEP HANDLING: both stay at their initial value (0/False)
        # for the overwhelmingly common case of a run with no OTP-shaped
        # step at all - poll_replay()'s own awaiting_otp/live_log fields
        # are None/empty then, so neither branch below ever fires.
        sent_log_count = 0
        acked_step = None  # (index, started_at) whose "Running" line has been sent and acknowledged
        otp_prompt_active = False
        # LIVE LOG SYNC: each step's screenshot is captured AFTER its result
        # line has already been sent (see the generated script's own
        # "capturing screenshot" phase) - remembers which screenshot path
        # (and status) was last told to the client per step index, so a
        # later patch to that same step is sent once as a "step_update"
        # event instead of being silently missed.
        sent_step_shot = {}
        sent_note_key = None

        def _step_updates(steps_now):
            for _s in steps_now[:sent_count]:
                _idx = _s.get("index")
                _shot = _s.get("screenshot")
                _key = (_shot, _step_display_status(_s))
                if _idx is None:
                    continue
                _prev = sent_step_shot.get(_idx)
                if _prev is None:
                    # first time seen: its "step" event (sent in this same
                    # poll, from this same data) already carried this state
                    sent_step_shot[_idx] = _key
                elif _prev[1] != _key[1] or (_prev[0] is None and _shot):
                    # status changed (e.g. a late "page was still loading"
                    # warning) or the screenshot has just arrived. A mere
                    # change in HOW the same screenshot's path is spelled
                    # (absolute while running, repo-relative once the run is
                    # finalized) is not an update
                    sent_step_shot[_idx] = _key
                    yield _sse("step_update", {
                        "index": _idx,
                        "status": _key[1],
                        "screenshot": _shot,
                        "reason": _step_failure_reason(_s, _step_element_label(meta.get("actions"), _s)),
                    })
        # a run_id that's already finished by the time this connects
        # (a fast run, or a slow client opening the popup late) still
        # needs its full step history replayed once here, not just the
        # steps AFTER whatever poll_replay first returns
        while True:
            progress = poll_replay(run_id)
            if progress is None:
                yield _sse("stream_error", {
                    "message": "Unknown run_id - it may have finished before "
                                "this server was last restarted."
                })
                return

            if progress["done"]:
                result = progress["result"] or {}
                steps = result.get("steps") or []
                yield from _step_updates(steps)
                for step in steps[sent_count:]:
                    _element_label = _step_element_label(meta.get("actions"), step)
                    sent_step_shot[step.get("index")] = (step.get("screenshot"), _step_display_status(step))
                    yield _sse("step", {
                        "index": step.get("index"),
                        "action_type": step.get("action_type"),
                        "element": _element_label,
                        "status": _step_display_status(step),
                        "started_at": step.get("started_at"),  # LIVE LOG SYNC
                        "ended_at": step.get("ended_at"),
                        "duration": step.get("duration"),
                        "reason": _step_failure_reason(step, _element_label),
                        # FOLLOW-UP FIX 6: forwarded regardless of pass/fail/
                        # warning status (unlike "reason" above, which is
                        # only built when there's something wrong) - a
                        # count_elements/count_summary step's own numbers
                        # should show on an ordinary PASS too.
                        "count_summary_rows": step.get("count_summary_rows"),
                        "value_range_rows": step.get("value_range_rows"),  # BUG 2
                        "page_mismatch": step.get("page_mismatch_info"),  # FIX 2
                        # FOLLOW-UP FIX (Part 4d)
                        "name_is_full_sentence": _step_name_is_full_sentence(meta.get("actions"), step),
                    })
                sent_count = len(steps)
                tally = _summarize_steps(steps)
                skipped = sum(1 for s in steps if _step_display_status(s) == "skipped")

                # same generate-once-cache-after pattern as
                # api_test_run_progress() above - whichever of the two
                # routes reaches "done" first for this run_id generates
                # the report, the other just reads the cached path, so
                # opening ONLY the live log popup (never polling
                # /api/test/run/progress at all) still ends up with a
                # working report link instead of always None
                with _run_meta_lock:
                    cached_html_report = (_run_meta.get(run_id) or {}).get("html_report")
                if cached_html_report is None and result.get("run_dir"):
                    try:
                        # PHASE 2d: same field injection as the other two
                        # generate_report() call sites - the report's own
                        # <title>/heading uses this when set.
                        result["test_name"] = meta.get("test_name")
                        result["display_name"] = meta.get("display_name")
                        result["recorded_actions"] = meta.get("actions") or []  # PHASE 4b
                        run_dir_path = BASE_DIR / result["run_dir"]
                        _attach_sub_lines_to_steps(result)
                        html_report_path = generate_report(result, output_dir=run_dir_path)
                        cached_html_report = str(html_report_path.relative_to(BASE_DIR)).replace("\\", "/")
                        with _run_meta_lock:
                            if run_id in _run_meta:
                                _run_meta[run_id]["html_report"] = cached_html_report
                    except Exception:
                        cached_html_report = None

                # PHASE 4c: one plain sentence on whether replay matched
                # the recording overall - built from the exact same
                # passed/failed/skipped/warnings tally already computed
                # just above for the rest of this event; never changes
                # pass/fail logic itself.
                #
                # PHASE 6 BUG FIX: this used to subtract `skipped` from
                # tally["failed"] here because _summarize_steps() itself
                # used to count a not-run step as failed - now that
                # _summarize_steps() excludes not_run by construction (see
                # its own docstring), tally["failed"] is already correct
                # and subtracting skipped again would double-count it.
                _real_failed = tally["failed"]
                _total_for_summary = meta.get("total_steps") or len(steps)
                if _real_failed == 0 and skipped == 0:
                    plain_summary_text = honest_summary(steps, _total_for_summary)
                else:
                    _first_failed_step = next(
                        (s for s in steps if not s.get("success") and not s.get("not_run")), None
                    )
                    if _first_failed_step:
                        _el = _step_element_label(meta.get("actions"), _first_failed_step)
                        _reason = strip_fail_wrapper(step_headline(_first_failed_step, _el))
                        plain_summary_text = f"Replay stopped at step {_first_failed_step.get('index')}: {_reason}."
                    else:
                        plain_summary_text = f"Replay finished: {tally['passed'] + tally['warnings'] + tally['manual_input']}/{_total_for_summary} steps passed."

                yield _sse("summary", {
                    "status": result.get("status"),
                    "message": result.get("message"),
                    "total_steps": _total_for_summary,
                    "passed": tally["passed"],
                    "failed": _real_failed,
                    "skipped": skipped,
                    "warnings": tally["warnings"],  # FOLLOW-UP FIX 2
                    "manual_input": tally["manual_input"],
                    "page_mismatches": tally["page_mismatches"],  # FIX 2
                    "duration_s": round(time.monotonic() - started_at, 1),
                    "html_report": cached_html_report,
                    "plain_summary": plain_summary_text,
                })
                return

            steps = progress.get("steps") or []
            yield from _step_updates(steps)
            live_log = progress.get("live_log") or []

            # ONE clock and true chronological order: the new step results and the new log lines are merged by
            # the replay engine's own timestamps, so a line logged during a step comes before that step's result
            def _epoch_of(iso):
                try:
                    return datetime.fromisoformat(str(iso)).timestamp()
                except Exception:
                    return None

            _events = []
            for step in steps[sent_count:]:
                _ts = _epoch_of(step.get("ended_at"))
                _events.append((_ts if _ts is not None else float("inf"), 1, "step", step))
            for entry in live_log[sent_log_count:]:
                _msg = entry.get("message") or ""
                # the replay's sub-lines ("↳ ...", level "note") are not shown in the live
                # log - one line per step only; they live in the step's Details (report)
                if entry.get("level") == "note" or _msg.startswith("↳"):
                    continue
                _t = entry.get("t")
                _events.append((float(_t) if isinstance(_t, (int, float)) else float("-inf"), 0, "log", entry))
            _events.sort(key=lambda ev: (ev[0], ev[1]))
            for _when, _rank, _kind, _item in _events:
                if _kind == "log":
                    _t = _item.get("t")
                    _at = None
                    if isinstance(_t, (int, float)):
                        try:
                            _at = datetime.fromtimestamp(_t).isoformat(timespec="milliseconds")
                        except Exception:
                            _at = None
                    yield _sse("log", {"message": _item.get("message") or "", "at": _at, "step": _item.get("step")})
                    continue
                step = _item
                _element_label = _step_element_label(meta.get("actions"), step)
                sent_step_shot[step.get("index")] = (step.get("screenshot"), _step_display_status(step))
                yield _sse("step", {
                    "index": step.get("index"),
                    "action_type": step.get("action_type"),
                    "element": _element_label,
                    "status": _step_display_status(step),
                    "started_at": step.get("started_at"),  # LIVE LOG SYNC
                    "ended_at": step.get("ended_at"),
                    "duration": step.get("duration"),
                    "reason": _step_failure_reason(step, _element_label),
                    "count_summary_rows": step.get("count_summary_rows"),  # FOLLOW-UP FIX 6
                    "value_range_rows": step.get("value_range_rows"),  # BUG 2
                    "page_mismatch": step.get("page_mismatch_info"),  # FIX 2
                    "name_is_full_sentence": _step_name_is_full_sentence(meta.get("actions"), step),  # FOLLOW-UP FIX (Part 4d)
                })
            # never go backwards: a report read that failed mid-write comes back empty
            sent_count = max(sent_count, len(steps))
            # never go backwards: a report read that failed mid-write comes back with an empty
            # log, and resetting the offset to 0 made the next good read re-send every old line
            sent_log_count = max(sent_log_count, len(live_log))
            # tell the replay script how many log lines have been SENT, so a line
            # is on screen before the browser action it describes
            if progress.get("output_json") and live_log:
                try:
                    Path(str(progress["output_json"]) + ".logack").write_text(str(sent_log_count), encoding="utf-8")
                except OSError:
                    pass

            awaiting_otp = progress.get("awaiting_otp")
            if awaiting_otp and not otp_prompt_active:
                otp_prompt_active = True
                yield _sse("otp_needed", {
                    "run_id": run_id,
                    "step_index": awaiting_otp.get("step_index"),
                    "total_steps": awaiting_otp.get("total_steps"),
                    "message": awaiting_otp.get("message") or "Enter OTP to continue",
                })
            elif not awaiting_otp and otp_prompt_active:
                otp_prompt_active = False
                yield _sse("otp_resolved", {"run_id": run_id})

            total_steps = progress.get("total_steps") or meta.get("total_steps")
            recorded_actions = meta.get("actions") or []
            # the replay script reports which step is running (current_step);
            # the live log shows only "RUNNING Step N" - the sub-phase it is
            # in is deliberately not sent
            _cs = progress.get("current_step") or {}
            _cs_index = _cs.get("index")
            _cs_phase = None

            # the "Running" line starts only once the replay script has reported a
            # real step (never a guess made while the browser is still launching)
            if total_steps and _cs_index and _cs_index > sent_count:
                next_index = _cs_index
                next_lp = (
                    (recorded_actions[next_index - 1] or {}).get("locator_profile") or {}
                    if next_index <= len(recorded_actions) else {}
                )
                _next_action = recorded_actions[next_index - 1] if next_index <= len(recorded_actions) else {}
                _next_explicit_name = ((_next_action or {}).get("name") or "").strip()
                yield _sse("running", {
                    "index": next_index,
                    "action_type": (_next_action or {}).get("action_type"),
                    # FOLLOW-UP FIX 5/Part 4d: an added step's own explicit
                    # name wins here too, same preference as the "step"
                    # event's own _step_element_label - otherwise the
                    # "RUNNING" line showed the generic type label for the
                    # whole time a Count Elements/Count Summary step (no
                    # locator text of its own) was executing.
                    "element": _next_explicit_name or next_lp.get("text") or next_lp.get("accessible_name") or next_lp.get("id"),
                    "name_is_full_sentence": bool((_next_action or {}).get("origin") == "added" and _next_explicit_name),
                    "elapsed_s": round(time.monotonic() - started_at, 1),
                    # LIVE LOG SYNC: None for an older script that doesn't
                    # report these - the page then shows the plain RUNNING
                    # line exactly as before
                    "started_at": _cs.get("started_at") if _cs_index == next_index else None,
                })
                # tell the replay script this step's "Running" line has been sent,
                # so its browser action starts only after the log shows it
                # (generator/script_generator.py's _wait_live_ack)
                _ack_key = (_cs_index, _cs.get("started_at"))
                if _ack_key != acked_step and progress.get("output_json"):
                    acked_step = _ack_key
                    try:
                        Path(str(progress["output_json"]) + ".ack").write_text(
                            f"{_cs_index}:{_cs.get('started_at')}", encoding="utf-8")
                    except OSError:
                        pass
            # was 0.4s; the replay script now writes report.json at every
            # sub-phase, so poll faster to keep the log in step with it
            time.sleep(0.2)

    return Response(generate(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


@app.route("/logs")
def live_log_page():
    """Standalone live-log page, opened in its OWN popup window (see
    runRecording() in static/js/script.js) so it stays visible next to
    the replay's own Chromium window instead of being covered by it -
    reads run_id from the query string client-side and connects to
    /api/test/run/stream itself; nothing server-rendered is run-specific.
    """
    return render_template("live_log.html")


# ============================================================
# RETENTION / CLEANUP - see storage/retention.py for the actual sweep
# logic and its own safety rules. Triggered on demand only (no
# background scheduler) - dry_run defaults to True, so a GET/preview or
# an unconfirmed POST always shows what WOULD happen before anything is
# actually archived/deleted.
# ============================================================

@app.route("/api/maintenance/cleanup", methods=["GET", "POST"])
def api_maintenance_cleanup():
    """GET (or POST with no body) previews a cleanup sweep - nothing is
    ever touched. POST with {"dry_run": false} actually performs it.
    Optional body/query fields: retention_days (int, default
    storage.retention.RETENTION_DAYS), mode ("archive" default, or
    "delete").
    """
    if request.method == "POST":
        body = request.get_json(force=True, silent=True) or {}
    else:
        body = {}

    try:
        retention_days = int(body.get("retention_days", request.args.get("retention_days", RETENTION_DAYS)))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "retention_days must be a whole number of days."})

    if retention_days < 1:
        return jsonify({"success": False, "message": "retention_days must be at least 1."})

    mode = body.get("mode", request.args.get("mode", "archive"))
    if mode not in ("archive", "delete"):
        return jsonify({"success": False, "message": "mode must be 'archive' or 'delete'."})

    # GET is always a preview, regardless of any dry_run value someone
    # might pass as a query param - a read-only HTTP method must never be
    # able to trigger a real deletion
    dry_run = True if request.method == "GET" else bool(body.get("dry_run", True))

    try:
        result = run_cleanup(retention_days=retention_days, dry_run=dry_run, mode=mode)
    except Exception as e:
        logger.error("cleanup sweep failed: %s", e)
        return jsonify({"success": False, "message": "Cleanup sweep failed - see server log."})

    return jsonify({"success": True, **result})


if __name__ == "__main__":

    # FIX 6 (crash recovery): the other trigger point for
    # repository.recover_orphaned_drafts() (see its own docstring and
    # Recorder.start()'s matching call) - a session that crashed the last
    # time this server was running gets its leftover JSONL sidecar swept
    # up into a proper, saved recording before anything else happens.
    # Safe here unconditionally: no recording can possibly be active yet
    # at this point in startup.
    try:
        recovered = repository.recover_orphaned_drafts()
        if recovered:
            logger.warning("recovered %d interrupted recording(s) on startup: %s", len(recovered), recovered)
    except Exception as e:
        logger.error("startup crash-recovery sweep failed: %s", e)

    start_recordings_watcher()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        threaded=True,
    )