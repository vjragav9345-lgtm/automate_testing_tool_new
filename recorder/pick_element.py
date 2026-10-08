"""Pick Element - lets the Recording Editor's Add Action modal capture an
XPath by having the user click a real, live page element instead of typing
one by hand.

Runs a session on its own background thread (same reason Recorder does:
Playwright's sync API is tied to the OS thread that created it, and this
has to block waiting for a human click, which Flask's request thread
can't afford to do). app.py's /api/recordings/pick_element/* routes are
thin wrappers around prewarm_pick_session()/start_pick_session()/
get_pick_status() below - all the actual browser/replay/JS-injection
logic lives here, isolated from the rest of the app for easy review.

WARM SESSIONS (speed feature): getting the picker to the right page is
mostly spent replaying preceding_actions via a real, headed browser - a
brand new browser launch plus a full replay from step 1 every single
time a human clicks "Pick Element" is real, avoidable latency when nothing
about the preceding steps actually changed since the last time. A
_WarmPickSession keeps ONE browser/context/page alive, on its own
persistent thread, across multiple Add Action modal openings within the
same Recording Editor tab (identified by a client-minted warm_id - see
recording_editor.html): the modal calls prewarm_pick_session() the
moment it opens (before the user has even clicked Pick Element), and
start_pick_session() reuses whatever that warm session already got done
- continuing forward when the new insertion point is later than what's
already replayed, or falling back to a full re-navigate + replay when
it's earlier (see _WarmPickSession._advance_to). Passing no warm_id (or
one whose session turns out to need a full replay anyway) still works
exactly like the old one-shot behavior, just without the head start -
see _run_pick_session_fresh, which is also what a warm session's own
FIRST use goes through internally.

_run_pick_session_fresh()/_WarmPickSession need a real, callable
resolve_and_act() to replay whatever actions precede the insertion point
- but generator/script_generator.py is a TEMPLATE container, not a normal
module: resolve_and_act, _resolve_element, and the rest of the
12-strategy engine exist only as literal text inside SCRIPT_TEMPLATE,
becoming real, executable Python only once generate_script() substitutes
the template and writes an actual .py file (confirmed: `hasattr(generator.
script_generator, "resolve_and_act")` is False). So this reuses
generate_script() - the exact same mechanism api_recordings_
validate_locator() already uses for its own, different probe - to write
a throwaway script, then dynamically loads THAT file as a module to get
a real resolve_and_act reference. Every generated script guards its own
replay behind `if __name__ == "__main__":`, so loading it this way never
triggers a live replay of its own - only the function definitions run.

CACHED, NOT regenerated per call: resolve_and_act's own source is
completely generic replay-engine code - it takes page/step as plain
arguments and never closes over anything specific to the test_case that
happened to generate it (confirmed: this exact function is already
reused today across calls made with entirely different start_urls, by
both this module and validate_locator, with no wrong-site behavior ever
observed). Regenerating + writing + importlib-loading the ~10,000-line
template on every single Pick Element click or Validate call was pure,
measured overhead (about a third of a second per call) that bought
nothing - see _load_resolve_and_act.
"""
import importlib.util
import json
import logging
import queue
import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright, Error as PWError

from generator.script_generator import generate_script
from recorder.record_session import _CAPTURE_JS
from utils import attach_dialog_handler

logger = logging.getLogger(__name__)

PICK_TIMEOUT_S = 120
PICK_POLL_INTERVAL_S = 0.3
PAGE_LOAD_TIMEOUT_MS = 30000

# must match generator/script_generator.py's own _CONTENT_MISMATCH_MARKER
# exactly - resolve_and_act (loaded from a generated script, see
# _load_resolve_and_act below) prefixes an error with this whenever it
# hard-confirms the live page no longer matches what was recorded (a
# different element at the click coordinate, or an exact href mismatch),
# as opposed to an ordinary "not found yet" timing failure. Duplicated as
# a plain string, not imported, since resolve_and_act only ever exists
# as generated-file text (see this module's own docstring) - never a
# site-specific value, purely an internal signal both files agree on.
_CONTENT_MISMATCH_MARKER = "[content-mismatch]"

# how long a warm session's browser stays open with no prewarm/pick
# activity at all before it closes itself - an idle headed Chrome window
# left open forever (the user closed the Recording Editor tab without
# ever finishing a pick, say) would otherwise never get cleaned up. The
# background thread itself is cheap to leave blocked past this point
# (just a queue.get with a timeout) - only the browser gets torn down;
# the next prewarm/pick simply relaunches, same as this warm_id's very
# first use.
_WARM_SESSION_IDLE_TIMEOUT_S = 600

# action types resolve_and_act() actually handles - see its own
# SUPPORTED_ACTIONS constant inside the generated-script template.
# navigate/tab_open/tab_close are handled separately below (resolve_and_
# act doesn't cover them at all); scroll and every validation-family
# action type (validate/compare_value/count_elements/...) are skipped -
# getting the picker visually close enough to click is this feature's
# whole job, not a byte-perfect Replay.
_RESOLVE_AND_ACT_SUPPORTED = {
    "click", "dblclick", "right_click", "fill", "select", "submit", "press", "check",
}

_PICK_LOCK = threading.Lock()
_PICK_RESULTS = {}  # pick_id -> {"status": ..., ...}


def _store_result(pick_id, result):
    with _PICK_LOCK:
        _PICK_RESULTS[pick_id] = result


def start_pick_session(start_url, preceding_actions, warm_id=None, session_path=None):
    """Spawns (or reuses) a background thread and returns immediately
    with a pick_id the caller polls via get_pick_status(). Never blocks
    on the human actually clicking anything - that's the whole reason
    this is a background thread rather than handled inline in the Flask
    route.

    warm_id, when given, names a _WarmPickSession that a preceding
    prewarm_pick_session() call (from the Add Action modal opening) may
    already have gotten partway - or all the way - to the right page.
    The pick then runs ON that warm session's own persistent
    thread/browser instead of launching a fresh one. Omitting warm_id
    (or a session that needs a full replay anyway) falls back to
    exactly the old behavior via _run_pick_session_fresh.
    """
    pick_id = uuid.uuid4().hex
    _store_result(pick_id, {"status": "waiting"})

    if warm_id:
        session = _get_or_create_warm_session(warm_id)
        # CONFIRMED REAL BUG this fixes: a live repro showed a second
        # Pick Element click on the SAME warm session silently queue
        # behind a still-open (but abandoned) previous pick's wait
        # phase - the modal read "waiting" the whole time (that generic
        # status set two lines up, not real progress) with zero backend
        # activity for the full PICK_TIMEOUT_S. A new pick request means
        # the user is done with whatever was open before (they clicked
        # Pick Element again) - signal it to end and its browser to
        # close NOW, from this request thread, rather than let it run
        # out its own clock first.
        pending_cancel = session._active_pick_cancel
        if pending_cancel is not None:
            pending_cancel.set()
        session.submit("start_pick", pick_id, session_path, start_url, preceding_actions)
    else:
        thread = threading.Thread(
            target=_run_pick_session_fresh,
            args=(pick_id, start_url, preceding_actions),
            daemon=True,
        )
        thread.start()

    return pick_id


def prewarm_pick_session(warm_id, session_path, start_url, preceding_actions):
    """Fire-and-forget: called the instant the Add Action modal opens
    with a known insertion point, well before the user has clicked Pick
    Element at all - gets a background browser as close as possible to
    that point in the meantime, so the ACTUAL Pick Element click (see
    start_pick_session above) can often skip replay entirely. Never
    blocks the calling Flask request thread and never raises back to
    it - a failed/slow prewarm just means the next Pick Element click
    falls back to replaying live, exactly like today.
    """
    if not warm_id:
        return
    session = _get_or_create_warm_session(warm_id)
    session.submit("prewarm", session_path, start_url, preceding_actions)


def cancel_active_pick(warm_id):
    """Signals warm_id's currently in-progress pick (if any) to end and
    its browser to close right away, instead of lingering open until
    PICK_TIMEOUT_S elapses on its own. Called when the Add Action modal
    is cancelled, saved, or otherwise closed without the user having
    closed the picker browser themselves - see recording_editor.html's
    modalCancelBtn/modalSaveBtn handlers. Fire-and-forget, same as
    prewarm_pick_session: a missing/unknown warm_id, or no pick actually
    in progress, is simply a no-op, never an error.
    """
    if not warm_id:
        return
    with _WARM_SESSIONS_LOCK:
        session = _WARM_SESSIONS.get(warm_id)
    if session is None:
        return
    pending_cancel = session._active_pick_cancel
    if pending_cancel is not None:
        pending_cancel.set()


def get_pick_status(pick_id):
    """Returns the current status for pick_id, clearing it from the
    store once a TERMINAL status (done/timeout/error/cancelled) has been
    read once - the frontend only ever needs to see a given result a
    single time. An unknown pick_id (never started, or already consumed)
    reads as "waiting" rather than an error, since the frontend's own
    poll loop can't otherwise distinguish "not started yet" from "already
    delivered" - both are fine to just keep waiting on.
    """
    with _PICK_LOCK:
        result = _PICK_RESULTS.get(pick_id)
        if result is None:
            return {"status": "waiting"}
        if result.get("status") in ("done", "timeout", "error", "cancelled"):
            del _PICK_RESULTS[pick_id]
        return result


# ============================================================
# resolve_and_act - loaded once, cached forever (see module docstring)
# ============================================================

_RESOLVE_AND_ACT_CACHE_LOCK = threading.Lock()
_RESOLVE_AND_ACT_CACHE = {"fn": None}


def _load_resolve_and_act(start_url, pick_id):
    """Returns a real, callable resolve_and_act - generated (via
    generate_script(), completely unmodified) and dynamically loaded
    exactly once per process, then cached forever. start_url/pick_id are
    only ever used to name the ONE throwaway script this ever generates
    (on the very first call); every later call ignores them and returns
    the same cached function object. Safe because resolve_and_act's own
    source never depends on which test_case produced it - see this
    module's own docstring for the confirmation this rests on. Every
    generated script guards its own replay behind
    `if __name__ == "__main__":`, so loading it this way never triggers
    a live replay of its own - only the function definitions run.
    """
    with _RESOLVE_AND_ACT_CACHE_LOCK:
        if _RESOLVE_AND_ACT_CACHE["fn"] is not None:
            return _RESOLVE_AND_ACT_CACHE["fn"]

        scratch_dir = Path(tempfile.mkdtemp(prefix="pick_element_"))
        try:
            probe_name = f"pick_probe_{pick_id}"
            test_case = {"name": probe_name, "start_url": start_url, "actions": []}
            script_path = generate_script(
                test_case, out_name=f"{probe_name}_script.py", output_dir=scratch_dir
            )
            spec = importlib.util.spec_from_file_location(probe_name, script_path)
            probe_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(probe_module)
            _RESOLVE_AND_ACT_CACHE["fn"] = probe_module.resolve_and_act
        finally:
            # the module object already holds everything we need in memory -
            # the file on disk was only ever a means to that, never something
            # this feature's own output should accumulate
            shutil.rmtree(scratch_dir, ignore_errors=True)

        return _RESOLVE_AND_ACT_CACHE["fn"]


# ============================================================
# network blocking (Pick Element's own browser context only - never
# touches generator/script_generator.py's real Replay context, which
# opens its own, completely separate one)
# ============================================================

# substrings, not full domains - matched against the full request URL,
# lowercased, so both bare and subdomain'd hosts (static.doubleclick.net,
# www.google-analytics.com, ...) match without listing every variant.
# Deliberately narrow on facebook.com specifically (its own pixel/SDK
# paths only, not the bare domain) - a recorded flow's own "log in with
# Facebook" step, however rare, must not silently break.
_AD_TRACKER_BLOCK_SUBSTRINGS = (
    "doubleclick.net", "googlesyndication.com", "googletagmanager.com",
    "google-analytics.com", "googleadservices.com", "adnxs.com",
    "facebook.com/tr", "connect.facebook.net", "hotjar.com",
    "criteo.com", "criteo.net", "taboola.com", "outbrain.com",
    "scorecardresearch.com", "quantserve.com", "adsrvr.org",
    "moatads.com", "amazon-adsystem.com", "clarity.ms", "mouseflow.com",
    "fullstory.com", "segment.io", "mixpanel.com", "optimizely.com",
    "yieldmo.com", "pubmatic.com", "rubiconproject.com", "casalemedia.com",
    "openx.net", "indexexchange.com", "appnexus.com", "smartadserver.com",
    "media.net", "adform.net", "bidswitch.net", "bat.bing.com",
    "3lift.com", "spotxchange.com", "yieldlab.net", "adroll.com",
)


def _install_pick_network_blocking(context):
    """Blocks known ad/tracker/analytics requests and any video/audio
    media - the whole point of Pick Element is seeing/clicking real page
    content as fast as possible, and neither category is ever something
    a user picks or needs to see load. Product IMAGES are deliberately
    never touched (resource_type == "image" is never checked against
    anything here) - a huge fraction of real picks (a product card, a
    thumbnail) target exactly that content. Best-effort: a routing
    failure here just means this one request loads normally, same as if
    blocking had never been installed.
    """
    def _handle(route):
        request = route.request
        try:
            if request.resource_type == "media":
                route.abort()
                return
            url = request.url.lower()
            if any(s in url for s in _AD_TRACKER_BLOCK_SUBSTRINGS):
                route.abort()
                return
        except Exception:
            pass
        try:
            route.continue_()
        except Exception:
            pass

    try:
        context.route("**/*", _handle)
    except Exception:
        pass


# ============================================================
# preceding-actions replay walk
# ============================================================

def _replay_preceding_actions(page, context, start_url, preceding_actions, resolve_and_act,
                               _pages=None, _current_page_id=0, _new_pages_queue=None,
                               _step_offset=0, _total=None):
    """Best-effort walk through preceding_actions to land the picker on
    approximately the right page/tab - not a verified Replay (see this
    module's own docstring on _RESOLVE_AND_ACT_SUPPORTED for the scope
    decision). One step failing to resolve never aborts the walk; getting
    as close as possible for the user to finish manually (scroll, click
    around) beats stopping partway and leaving the picker on an earlier,
    less useful page.

    tab_open steps are matched against REAL new pages the browser itself
    creates in response to a preceding click (a target="_blank" link,
    say) - via context.on("page", ...), the same mechanism app.py's own
    recording session already uses for this - rather than fabricating a
    blank page ourselves, which a resolve_and_act() click's own href
    navigation already does more faithfully.

    The five underscore-prefixed params are optional and exist only for
    _WarmPickSession's continuation path: every existing caller
    (validate_locator, _run_pick_session_fresh) omits them and gets
    exactly the old single-shot-from-scratch behavior (preceding_actions
    is the FULL list, replayed step 1..N against a brand new page/
    context). A warm session instead passes in the pages/current_page_id/
    new_pages_queue state a PREVIOUS call already built up on this same
    page/context, plus _step_offset/_total so the printed step numbers
    stay correct - letting preceding_actions here be just the NEW, DELTA
    slice rather than the whole thing again.

    Returns (final_page, walk_state) - walk_state is
    {"pages", "current_page_id", "new_pages_queue"}, meant to be threaded
    straight into a later call's own _pages/_current_page_id/
    _new_pages_queue when there is one; every existing caller ignores it.
    """
    register_new_page_listener = _new_pages_queue is None
    new_pages_queue = _new_pages_queue if _new_pages_queue is not None else []

    # CONFIRMED REAL BUG, found via a live repro against myntra.com: this
    # used to wait_for_load_state() BEFORE appending to the queue below -
    # meaning the queue stayed EMPTY until the new tab's OWN page load
    # finished (up to 10s), while the tab_open step's own outer wait
    # below only waited 5s before giving up. On a real, ad/tracker-heavy
    # site, a genuinely-opened new tab easily takes longer than 5s to
    # reach domcontentloaded, so the outer wait expired FIRST, pages[
    # step_page_id] never got set, and every subsequent step silently
    # fell back to the ORIGINAL page object instead - explaining exactly
    # what the repro showed: clicks for "38"/"ADD TO BAG" landing on the
    # search-results page's own nav content, and the picker ending up
    # injected onto the wrong tab. The context "page" event itself fires
    # the instant the new tab is CREATED, before any navigation even
    # starts - appending immediately here means the tab_open step below
    # sees it right away regardless of how long that tab's own page load
    # takes; the actual load-wait now happens AFTER assignment, where a
    # slow load can never cause a wrong-page fallback.
    def _on_new_page(new_page):
        new_pages_queue.append(new_page)

    if register_new_page_listener:
        context.on("page", _on_new_page)

    pages = _pages if _pages is not None else {0: page}
    current_page_id = _current_page_id
    total = _total if _total is not None else len(preceding_actions)
    # set only when a step's resolve_and_act call hard-confirms the live
    # page no longer matches what was recorded (see _CONTENT_MISMATCH_
    # MARKER above) - unlike an ordinary "didn't resolve" failure (best-
    # effort, walk continues regardless - see this function's own
    # docstring), this is a CONFIRMED "recording and live site have
    # diverged" signal, not a timing fluke, so continuing the walk would
    # just be guessing at further steps against a page nobody actually
    # recorded. Stops the walk right here; surfaced to the caller via
    # walk_state so the picker can tell the user clearly instead of
    # silently landing on the wrong page.
    content_mismatch = None
    # every step of this walk that didn't run cleanly (the walk itself keeps
    # going past these - see the docstring): [{"step_index", "action_type",
    # "reason"}], surfaced to the user by the modal so a picker that isn't on
    # the expected page is never left unexplained
    replay_failures = []

    for i, step in enumerate(preceding_actions, start=1 + _step_offset):
        action_type = step.get("action_type")
        step_page_id = step.get("page_id", current_page_id)
        cur = pages.get(step_page_id) or pages.get(current_page_id) or page

        # REPLAY-BOUNDARY VERIFICATION: one line per preceding step this
        # loop actually processes, printed BEFORE it acts on the step -
        # since this loop only ever iterates over preceding_actions
        # itself (already sliced to end at insert_after_index by
        # _slice_preceding_actions, before this function ever sees it),
        # the last line printed here is structural proof of exactly where
        # replay stopped: nothing with a HIGHER index than what appears
        # in this file's own terminal output was ever touched.
        print(f"[pick] replaying step {i}/{total}: {action_type}")
        _step_t0 = time.monotonic()

        if action_type == "navigate":
            try:
                cur.goto(
                    step.get("page_url") or start_url,
                    wait_until="domcontentloaded",
                    timeout=15000,
                )
            except Exception as e:
                logger.debug("pick-element replay: navigate step failed (%s) - continuing", e)
                replay_failures.append({
                    "step_index": i, "action_type": action_type,
                    "reason": f"couldn't load {step.get('page_url') or start_url}",
                })

        elif action_type == "tab_open":
            # the click just replayed above may have triggered a real new
            # tab - give the browser a brief, bounded window for the new
            # PAGE OBJECT to appear (near-instant once the tab is
            # created, since _on_new_page appends immediately - see its
            # own comment above for why this used to be the actual bug)
            deadline = time.monotonic() + 5.0
            while not new_pages_queue and time.monotonic() < deadline:
                # a Playwright call, not a bare time.sleep: in the sync API
                # the context's "page" event (what fills new_pages_queue) is
                # only delivered while Playwright's own loop is running, so
                # sleeping here never lets the new tab reach the queue
                try:
                    cur.wait_for_timeout(100)
                except Exception:
                    time.sleep(0.1)
            if new_pages_queue:
                new_page = new_pages_queue.pop(0)
                pages[step_page_id] = new_page
                current_page_id = step_page_id
                # THIS wait can safely take as long as the page actually
                # needs - it no longer gates whether pages[step_page_id]
                # gets set at all, only whether replay pauses briefly for
                # it to be ready before the NEXT step tries to act on it
                try:
                    new_page.wait_for_load_state("domcontentloaded", timeout=15000)
                except Exception as e:
                    logger.debug("pick-element replay: new tab's own page load didn't settle in time (%s) - continuing", e)
            else:
                logger.debug(
                    "pick-element replay: tab_open step expected a new tab but none "
                    "appeared within 5s - subsequent steps for page_id=%s may act on "
                    "the wrong page", step_page_id,
                )
                current_page_id = step_page_id

        elif action_type == "tab_close":
            closing = pages.pop(step_page_id, None)
            if closing is not None:
                try:
                    closing.close()
                except Exception:
                    pass
            remaining = step.get("remaining_page_id")
            if remaining is not None:
                current_page_id = remaining

        elif action_type in _RESOLVE_AND_ACT_SUPPORTED:
            try:
                # turbo=True - this walk's only job is reaching the right
                # page state as fast as possible for a human to click
                # something, not demonstrating realistic pacing (see
                # resolve_and_act's own docstring for exactly what this
                # does and doesn't skip). Real Replay never passes this.
                _rr_strategy, _rr_found, _rr_ok, _rr_err = resolve_and_act(cur, step, turbo=True)
                if not _rr_ok and _rr_err and _CONTENT_MISMATCH_MARKER in _rr_err:
                    print(
                        f"[pick] step {i}/{total} ({action_type}) CONFIRMED content "
                        f"mismatch - stopping the walk here instead of guessing "
                        f"further: {_rr_err}",
                        flush=True,
                    )
                    content_mismatch = {
                        "step_index": i,
                        "action_type": action_type,
                        "reason": _rr_err,
                    }
                    break
                if not _rr_ok:
                    replay_failures.append({
                        "step_index": i, "action_type": action_type,
                        "reason": str(_rr_err or "its target could not be resolved")[:160],
                    })
            except Exception as e:
                logger.debug(
                    "pick-element replay: %s step failed (%s) - continuing", action_type, e
                )
                replay_failures.append({
                    "step_index": i, "action_type": action_type, "reason": str(e)[:160],
                })
        # else: scroll / validation-family / anything else - skipped by
        # design, see this function's own docstring
        print(f"[pick-speed] step {i}/{total} ({action_type}) took {time.monotonic() - _step_t0:.2f}s", flush=True)

    if content_mismatch is not None:
        print(f"[pick] replay stopped early at step {content_mismatch['step_index']}/{total} - content mismatch")
    else:
        print(f"[pick] replay stopped after step {total}, waiting for click")

    final_page = pages.get(current_page_id) or page
    walk_state = {
        "pages": pages,
        "current_page_id": current_page_id,
        "new_pages_queue": new_pages_queue,
        "content_mismatch": content_mismatch,
        "replay_failures": replay_failures,
    }
    return final_page, walk_state


# ============================================================
# shared "picker is now waiting for a click" phase - used by both the
# warm-session path and the plain one-shot fallback path below, so
# there's exactly one copy of the lock/release state machine and the
# [pick-timing] instrumentation regardless of which path landed the
# browser here. Caller owns pw/browser creation AND teardown (this
# function only ever READS browser.is_connected() - it never closes
# anything itself); see each caller's own finally block.
# ============================================================

# ============================================================
# TEST-ONLY DRIVING HOOK - never touched by any real production code
# path; empty in every real run, so this is purely additive. A UI-level
# test (one that drives the real Recording Editor page, not this
# module's own functions directly - see tests/ for why that distinction
# matters) can push a callable(browser, context) onto this queue; the
# wait loop in _run_pick_wait_phase below calls it once, on the SAME
# thread that owns this session's Playwright connection - the only
# thread allowed to touch it. This is what lets a test perform a real
# page.mouse.click(...) inside the picker's own browser reliably,
# instead of a second, independent Playwright connection - a genuine
# Playwright limitation already confirmed (a second CDP client's clicks
# don't reliably reach the ORIGINAL connection's exposed-function
# callback) rules that out for good.
# ============================================================
_TEST_DRIVE_QUEUE = queue.Queue()


def _normalize_url_for_compare(url):
    """Strips a trailing slash and any hash fragment so /events and
    /events/ (or /events#foo) compare equal - CONFIRMED FALSE ALARM this
    fixes: a live repro showed this exact pair
    ('.../events', '.../events/') flagged as a mismatch when nothing
    about the page actually differed. Never touches query strings or
    anything else - a real path difference still surfaces normally.
    """
    if not url:
        return url
    return url.split("#", 1)[0].rstrip("/")


def _run_pick_wait_phase(pick_id, browser, context, final_page, start_url, preceding_actions, cancel_event=None, content_mismatch=None, replay_failures=None):
    # content_mismatch (see _replay_preceding_actions' own field of the
    # same name): set only when the preceding-actions walk stopped EARLY
    # because resolve_and_act hard-confirmed the live page no longer
    # matches what was recorded - a stronger, more specific signal than
    # the page_url_check below (which only compares the FINAL landed URL
    # against what the last preceding step's own page_url happened to
    # record, and can't say WHICH step actually diverged or why). Merged
    # into every _store() call below exactly like page_url_check already
    # is, so the modal can tell a genuine "site content changed since
    # recording" apart from "still waiting for a human to click".
    #
    # SAFETY CHECK: if the live page's URL doesn't match what the
    # recording's own last preceding step expects at this exact
    # position, content has likely drifted (a redirect, an A/B variant,
    # a login wall, a site-side layout change) since the recording was
    # made - surfacing this explicitly beats a user picking an XPath
    # against a page that silently isn't the one their steps actually
    # recorded. Purely informational: never blocks picking, the modal
    # just shows it alongside whatever else is happening.
    expected_url = preceding_actions[-1].get("page_url") if preceding_actions else None
    if not expected_url:
        expected_url = start_url
    try:
        actual_url = final_page.url
    except Exception:
        actual_url = None
    url_mismatch = bool(
        expected_url and actual_url
        and _normalize_url_for_compare(expected_url) != _normalize_url_for_compare(actual_url)
    )
    url_check = {"expected_url": expected_url, "actual_url": actual_url, "mismatch": url_mismatch}
    if url_mismatch:
        print(f"[pick-url-check] {pick_id} MISMATCH expected={expected_url!r} actual={actual_url!r}", flush=True)

    def _store(result):
        merged = dict(result)
        merged["page_url_check"] = url_check
        merged["content_mismatch"] = content_mismatch
        merged["replay_failures"] = replay_failures or []
        _store_result(pick_id, merged)

    # PICK ELEMENT NEVER TOUCHES storage/recordings/<session>.json -
    # everything from here down only ever reads the live browser page and
    # writes to the in-memory _PICK_RESULTS store (see get_pick_status/
    # _store_result). The recording file is only ever modified by the
    # Recording Editor's own explicit Save button (a separate route
    # entirely), once a human has reviewed and confirmed the picked
    # xpath in the modal - this function has no import of, or reference
    # to, storage.repository at all.
    # STATE MACHINE for the lock/double-click-release cycle (see
    # action_capture.js's own pickLocked/lockPick/releasePick for the
    # JS-side half): a plain dict behind a lock, not threading.Event - an
    # Event is naturally one-shot (fine for the OLD "first click wins
    # forever" behavior), but re-lockable/releasable selection needs to
    # flip back and forth freely, which Event.clear() can do
    # mechanically but doesn't fit the "wait for any of: locked,
    # released, browser closed" shape nearly as cleanly as just polling
    # this dict does below.
    _pick_lock = threading.Lock()
    pick_state = {"locked": False, "profile": None}

    def _on_pick_result(raw_json):
        # LATENCY INSTRUMENTATION (always on, not gated - this is a
        # correctness-relevant timing, not a debug-only detail; see the
        # "why" this exists: a real screen recording showed a
        # 110-second gap between a real lock and the dashboard showing
        # it, and this is how that got root-caused). One line per stage,
        # all sharing the pick_id so a single run's whole timeline can
        # be reconstructed by grepping it.
        t_received = time.time()
        print(f"[pick-timing] {pick_id} binding_received t={t_received:.3f}", flush=True)
        try:
            profile = json.loads(raw_json)
        except Exception as e:
            logger.warning("pick-element: couldn't parse pick result JSON: %s", e)
            profile = {}

        # FIX 3's checkbox_state_info is deliberately NOT computed here: this
        # callback is invoked REENTRANTLY, from inside whatever Playwright
        # call is currently pumping this session's connection (see the wait
        # loop's own long comment on exactly this, a few screens down) -
        # calling another blocking Playwright method (.evaluate(), which
        # _resolve_checkbox_state needs) from in here deadlocks the
        # connection instead of raising a catchable exception (CONFIRMED via
        # a live repro: the pick never completed, the callback's own first
        # print line ran, nothing after it ever did). Computed instead in
        # the wait loop itself, a safe, non-reentrant context - see its own
        # comment for exactly where.
        with _pick_lock:
            pick_state["locked"] = True
            pick_state["profile"] = profile
        # LIVE UPDATE, sent immediately at lock time - not just once the
        # browser eventually closes (see this module's own docstring
        # point about capturing at lock time). Status "locked" is
        # deliberately NOT terminal (see get_pick_status below) - the
        # browser stays open, the user can still double-click to
        # release and pick something else, and each further lock
        # overwrites this same in-progress entry rather than being
        # treated as a second, separate pick.
        _store({
            "status": "locked",
            "xpath": profile.get("xpath"),
            "xpath_candidates": profile.get("xpath_candidates") or [profile.get("xpath")],
            "css_path": profile.get("css_path"),
            "id": profile.get("id"),
            "locator_profile": profile,
            "match_count": profile.get("match_count"),
            "checkbox_state_info": profile.get("checkbox_state_info"),
            "value_range_preview": profile.get("value_range_preview"),
        })
        t_stored = time.time()
        print(f"[pick-timing] {pick_id} status_written t={t_stored:.3f} (+{t_stored - t_received:.3f}s)", flush=True)

    def _on_pick_release():
        with _pick_lock:
            pick_state["locked"] = False
            pick_state["profile"] = None
        logger.info("pick-element: selection released, hover mode resumed")
        print(f"[pick-timing] {pick_id} release_received t={time.time():.3f}", flush=True)
        _store({"status": "waiting"})

    def _inject_pick_mode(target_page):
        """Injects the pick-mode overlay/capture script into target_page
        and exposes pickResult on it. Called for EVERY page currently
        open in the context below - not just final_page - because which
        tab a human is actually looking at in the headed browser isn't
        guaranteed to match whichever one this walk's own tab-tracking
        happened to call "final" (these recordings routinely open
        several tabs). Protecting every open tab makes that mismatch
        harmless instead of a real, unblocked click landing wherever the
        human happens to be - confirmed as a real cause of clicks
        reaching the live page during picking. Safe to call more than
        once on the same page - the JS side's own __afqaPickOverlay
        guard, and a failed re-expose on an already-exposed page, are
        both silently absorbed.
        """
        try:
            target_page.expose_function("pickResult", _on_pick_result)
        except Exception:
            pass  # already exposed on this page - fine
        try:
            target_page.expose_function("pickReleased", _on_pick_release)
        except Exception:
            pass  # already exposed on this page - fine
        pick_script = "window.__afqaPickMode = true;\n" + _CAPTURE_JS
        # add_init_script only affects FUTURE navigations of this page -
        # it's already loaded, so it also needs injecting into the
        # CURRENT document directly; add_init_script is still registered
        # too, in case the user reloads or navigates while the picker is
        # waiting
        try:
            target_page.add_init_script(pick_script)
        except Exception:
            pass
        try:
            target_page.evaluate(pick_script)
        except Exception as e:
            logger.warning("pick-element: couldn't inject pick-mode into a page (%s)", e)
            return
        # VERSION MARKER (terminal-side half - see action_capture.js's own
        # comment on __afqaCaptureVersion for why this exists at all):
        # reads the version string BACK from the page right after
        # injecting it, so this process's own stdout is unambiguous proof
        # of which action_capture.js content is actually live in this
        # browser - no guessing from symptoms, no console-only check the
        # terminal-side dev might miss.
        try:
            live_version = target_page.evaluate("window.__afqaCaptureVersion")
        except Exception:
            live_version = None
        print(f"[pick] injected pick-mode into {target_page.url!r} - action_capture.js version: {live_version!r}")

    for p in context.pages:
        _inject_pick_mode(p)

    # BRING TO FRONT (CONFIRMED GAP - no bring_to_front() call existed
    # anywhere in this codebase before this): the Recording Editor is
    # typically a maximised browser window of its own, and a headed
    # window launched from a background Python thread has no guaranteed
    # claim on OS foreground focus - Windows' own focus-stealing
    # prevention can leave a genuinely-launched, genuinely-ready picker
    # window sitting behind the editor, indistinguishable from "no
    # window appeared" to the user even though picking is fully live.
    # Best-effort: a failure here never blocks picking itself, it just
    # means the user has to alt-tab to find it, exactly like before this
    # fix.
    try:
        final_page.bring_to_front()
    except Exception as e:
        logger.debug("pick-element: bring_to_front failed (%s) - continuing", e)

    # SAFETY NET (defense in depth): even with every currently-open tab
    # protected above, if a real click somehow still gets through and
    # opens a genuinely NEW page during the wait below, this catches it -
    # protects it too (in case the human is now looking at it), and
    # closes it ONLY while a pick is still in progress (pick_event not
    # yet set); once a pick has already completed successfully there's
    # nothing to protect anymore and the whole browser is about to close
    # shortly after regardless, so touching a late-arriving page at that
    # point would be interference for no benefit. Replaces the
    # replay-phase's own tab-open listener, which only ever fed a queue
    # nothing reads anymore past this point.
    def _is_currently_locked():
        with _pick_lock:
            return pick_state["locked"]

    def _on_unexpected_new_page(new_page):
        try:
            _inject_pick_mode(new_page)
        except Exception:
            pass
        if _is_currently_locked():
            return
        logger.warning(
            "pick-element: an unexpected new page appeared during an "
            "active pick session - closing it"
        )
        try:
            new_page.wait_for_timeout(300)
            if not _is_currently_locked():
                new_page.close()
        except Exception:
            pass

    context.on("page", _on_unexpected_new_page)

    _store({"status": "waiting"})

    # Simply watches for the browser closing - the actual pick state
    # (locked/released/re-locked, as many times as the user likes) is
    # updated live, straight to _PICK_RESULTS, by _on_pick_result/
    # _on_pick_release above as it happens; this loop's only job is
    # deciding WHEN the session ends. Whatever is locked (or isn't) at
    # that moment is what finalizes below - true regardless of whether
    # the loop ends by timeout or by the browser actually closing, so a
    # user who's happy with their pick right as the timeout fires
    # doesn't lose it just for taking a while to get there.
    # CONFIRMED ROOT CAUSE (measured, not guessed - see the [pick-timing]
    # log lines this whole module prints): a plain time.sleep() here
    # starves Playwright's own message pump. The sync API's
    # exposed-function callback (_on_pick_result above) is only actually
    # INVOKED when the thread that owns this Playwright connection makes
    # its own call back into Playwright (each one processes any
    # callbacks queued up since the last one) - a bare time.sleep()
    # never does that, so a lock that happens while this loop is
    # "asleep" sits queued, invisible to _store_result, until whatever
    # ends the CURRENT sleep call finally lets a later loop iteration
    # make a real Playwright call again. In the wild that gap can be
    # enormous - a real screen recording showed 110+ seconds between a
    # genuine lock and the dashboard ever seeing it, entirely explained
    # by this. page.wait_for_timeout() is Playwright's OWN wait
    # primitive - it still elapses the same real time, but because it's
    # a genuine Playwright call, it keeps pumping the connection (and
    # therefore dispatching any pending exposed-function callback) for
    # the ENTIRE duration instead of only at its edges.
    # cancel_event (see _WarmPickSession._active_pick_cancel's own
    # comment): a NEWER pick on this SAME warm session showing up while
    # this loop is still waiting sets this - checked every iteration
    # (every PICK_POLL_INTERVAL_S), so it ends this session almost
    # immediately instead of running out its own PICK_TIMEOUT_S first.
    # None for the plain one-shot fallback path (_run_pick_session_fresh),
    # which has no warm session/shared state to be superseded by in the
    # first place - a bare truthiness check on None is just always False.
    deadline = time.monotonic() + PICK_TIMEOUT_S
    while (
        time.monotonic() < deadline
        and browser.is_connected()
        and not (cancel_event is not None and cancel_event.is_set())
    ):
        try:
            _poll_page = browser.contexts[0].pages[0]
            _poll_page.wait_for_timeout(PICK_POLL_INTERVAL_S * 1000)
        except Exception:
            # no page currently open (mid tab-close/tab-open) or the
            # browser just disconnected - a plain sleep is a safe
            # fallback for this one tick; the loop's own
            # browser.is_connected() check above still ends it promptly
            # once the browser is genuinely gone
            time.sleep(PICK_POLL_INTERVAL_S)
        # FIX 3 (Validate Checkbox State dialog): computed HERE, once per
        # newly-locked pick, not inside _on_pick_result itself - see that
        # function's own comment for why (a blocking Playwright call from
        # inside its exposed-function callback deadlocks the connection).
        # This loop already makes a real Playwright call every tick
        # (_poll_page.wait_for_timeout above), so it's a safe, non-reentrant
        # place to make one more. Reuses the SAME resolve_and_act already
        # cached for this process (generator/script_generator.py's
        # _resolve_checkbox_state, read off its module namespace) - never a
        # second copy of that JS. Purely informational: a failure here
        # leaves checkbox_state_info absent, never blocks the pick itself.
        with _pick_lock:
            _cb_locked, _cb_profile = pick_state["locked"], pick_state["profile"]
        if _cb_locked and _cb_profile and _cb_profile.get("xpath") and "checkbox_state_info" not in _cb_profile:
            _cb_info = None
            try:
                _resolve_fn = _RESOLVE_AND_ACT_CACHE.get("fn")
                if _resolve_fn is not None:
                    _resolve_checkbox_state = _resolve_fn.__globals__.get("_resolve_checkbox_state")
                    if _resolve_checkbox_state is not None:
                        _cb_info = _resolve_checkbox_state(
                            browser.contexts[0].pages[0].locator(f"xpath={_cb_profile['xpath']}").first
                        )
            except Exception as e:
                logger.debug("pick-element: checkbox_state_info computation failed (%s)", e)
            with _pick_lock:
                # only write back if this is STILL the same locked pick (the
                # user may have released/re-picked something else while the
                # evaluate() above was running)
                if pick_state["locked"] and pick_state["profile"] is _cb_profile:
                    _cb_profile["checkbox_state_info"] = _cb_info
                    _store({
                        "status": "locked",
                        "xpath": _cb_profile.get("xpath"),
                        "xpath_candidates": _cb_profile.get("xpath_candidates") or [_cb_profile.get("xpath")],
                        "css_path": _cb_profile.get("css_path"),
                        "id": _cb_profile.get("id"),
                        "locator_profile": _cb_profile,
                        "match_count": _cb_profile.get("match_count"),
                        "checkbox_state_info": _cb_info,
                    })

        # BUG 2 fix (f): same "computed once per newly-locked pick" pattern
        # as checkbox_state_info right above, reusing the exact same
        # generated-module resolver (_afqa_resolve_element_value) a real
        # replay's Validate Value Range step uses - lets the editor show
        # "Values found: ..." (or an ambiguity warning) before the step is
        # even saved. Capped, since a drag-pick's xpath can match many
        # elements; purely informational, never blocks the pick.
        with _pick_lock:
            _vr_locked, _vr_profile = pick_state["locked"], pick_state["profile"]
        if _vr_locked and _vr_profile and _vr_profile.get("xpath") and "value_range_preview" not in _vr_profile:
            _vr_preview = None
            try:
                _resolve_fn = _RESOLVE_AND_ACT_CACHE.get("fn")
                if _resolve_fn is not None:
                    _afqa_resolve_element_value = _resolve_fn.__globals__.get("_afqa_resolve_element_value")
                    if _afqa_resolve_element_value is not None:
                        _vr_locator = browser.contexts[0].pages[0].locator(f"xpath={_vr_profile['xpath']}")
                        _vr_cap = min(_vr_profile.get("match_count") or 1, 12)
                        _vr_preview = []
                        for _vr_idx in range(_vr_cap):
                            _v, _r, _d = _afqa_resolve_element_value(_vr_locator.nth(_vr_idx))
                            _vr_role = next(
                                (c["role"] for c in _d.get("candidates", []) if _v is not None and c["value"] == _v),
                                None,
                            )
                            _vr_preview.append({
                                "value": _v, "ambiguous_reason": _r, "role": _vr_role,
                                "candidates": _d.get("candidates", []),
                            })
            except Exception as e:
                logger.debug("pick-element: value_range_preview computation failed (%s)", e)
            with _pick_lock:
                if pick_state["locked"] and pick_state["profile"] is _vr_profile:
                    _vr_profile["value_range_preview"] = _vr_preview
                    _store({
                        "status": "locked",
                        "xpath": _vr_profile.get("xpath"),
                        "xpath_candidates": _vr_profile.get("xpath_candidates") or [_vr_profile.get("xpath")],
                        "css_path": _vr_profile.get("css_path"),
                        "id": _vr_profile.get("id"),
                        "locator_profile": _vr_profile,
                        "match_count": _vr_profile.get("match_count"),
                        "value_range_preview": _vr_preview,
                    })

        if not _TEST_DRIVE_QUEUE.empty():
            try:
                _drive_fn = _TEST_DRIVE_QUEUE.get_nowait()
                _drive_fn(browser, context)
            except Exception as e:
                print(f"[test-drive] hook failed: {e!r}", flush=True)

    t_loop_exit = time.time()
    print(f"[pick-timing] {pick_id} wait_loop_exit t={t_loop_exit:.3f} browser_connected={browser.is_connected()}", flush=True)

    with _pick_lock:
        final_locked = pick_state["locked"]
        final_profile = pick_state["profile"]

    if final_locked:
        profile = final_profile or {}
        # match_count was computed client-side, in the same click
        # handler that captured this profile (document.evaluate against
        # the live page, right when the xpath was still fresh) - see
        # action_capture.js's own pick-mode branch. Missing/None here
        # just means that evaluate() call itself failed (an unusual
        # xpath), not "zero matches" - the frontend treats either the
        # same way (not confidently 1:1).
        result = {
            "status": "done",
            "xpath": profile.get("xpath"),
            "xpath_candidates": profile.get("xpath_candidates") or [profile.get("xpath")],
            "css_path": profile.get("css_path"),
            "id": profile.get("id"),
            "locator_profile": profile,
            "match_count": profile.get("match_count"),
            "checkbox_state_info": profile.get("checkbox_state_info"),
            "value_range_preview": profile.get("value_range_preview"),
        }
    elif not browser.is_connected():
        result = {
            "status": "cancelled",
            "message": (
                "The picker browser window was closed before an element "
                "was picked (or the selection was released and nothing "
                "new was picked before it closed)."
            ),
        }
    elif cancel_event is not None and cancel_event.is_set():
        # superseded by a newer Pick Element click (or an explicit
        # Cancel/Save on the modal) on this same warm session, never a
        # real timeout - see cancel_event's own comment above. The
        # frontend's own generation-token guard already stopped polling
        # this pick_id the moment the newer one started, so nothing
        # actually reads this message in practice; it's set for anyone
        # reading the store/logs directly.
        result = {
            "status": "cancelled",
            "message": "This picker was closed because a newer Pick Element session started.",
        }
    else:
        result = {
            "status": "timeout",
            "message": "No element was picked within the time limit.",
        }

    _store(result)
    print(f"[pick-timing] {pick_id} finalized t={time.time():.3f} status={result['status']}", flush=True)


# ============================================================
# plain one-shot fallback path - no warm_id given, or this warm_id's
# session decided it needed a full replay anyway. Always launches its
# own fresh browser, exactly like Pick Element always used to.
# ============================================================

def _run_pick_session_fresh(pick_id, start_url, preceding_actions):
    pw = None
    browser = None

    try:
        pw = sync_playwright().start()

        try:
            browser = pw.chromium.launch(headless=False)
        except Exception as e:
            logger.warning("pick-element: headed launch failed (%s), falling back to headless", e)
            browser = pw.chromium.launch(headless=True)

        context = browser.new_context()
        _install_pick_network_blocking(context)
        page = context.new_page()
        page.set_default_timeout(8000)
        attach_dialog_handler(page)

        try:
            page.goto(start_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
        except PWError as e:
            _store_result(pick_id, {
                "status": "error",
                "message": f"Couldn't reach {start_url!r}: {e}",
            })
            return

        resolve_and_act = _load_resolve_and_act(start_url, pick_id)

        final_page, _walk_state = _replay_preceding_actions(
            page, context, start_url, preceding_actions, resolve_and_act
        )

        _run_pick_wait_phase(
            pick_id, browser, context, final_page, start_url, preceding_actions,
            content_mismatch=_walk_state.get("content_mismatch"),
            replay_failures=_walk_state.get("replay_failures"),
        )

    except Exception as e:
        # never let a raw Playwright error (TargetClosedError, an
        # expose_function failure on a closed page, etc.) reach the
        # modal as text a user can't act on - the real exception is
        # still logged server-side for debugging, just not surfaced
        logger.error("pick-element session %s crashed: %s", pick_id, e)
        _store_result(pick_id, {
            "status": "error",
            "message": "Something unexpected happened during picking - please try again.",
        })

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


# ============================================================
# warm sessions - see this module's own docstring
# ============================================================

_WARM_SESSIONS = {}
_WARM_SESSIONS_LOCK = threading.Lock()


def _get_or_create_warm_session(warm_id):
    with _WARM_SESSIONS_LOCK:
        session = _WARM_SESSIONS.get(warm_id)
        if session is None:
            session = _WarmPickSession(warm_id)
            _WARM_SESSIONS[warm_id] = session
        return session


class _WarmPickSession:
    """One persistent background thread owning (at most) one
    browser/context/page, identified by a client-minted warm_id (one per
    open Recording Editor tab - see recording_editor.html). Everything
    that touches self.pw/browser/context/page/resolve_and_act happens on
    this object's own thread (_run) - Playwright's sync API is tied to
    the OS thread that created it, exactly like every other long-lived
    Playwright session in this project (Recorder, the old one-shot Pick
    Element session this replaces).

    Jobs are submitted via .submit(kind, *args) and processed strictly
    one at a time, in order - a "prewarm" while a "start_pick" is still
    running its own wait phase simply waits in the queue, which matches
    how the UI actually behaves (the Add Action modal is one modal; a
    second one can't meaningfully open while the first's Pick Element
    browser is still up).
    """

    def __init__(self, warm_id):
        self.warm_id = warm_id
        self._queue = queue.Queue()

        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.resolve_and_act = None

        self.session_path = None
        self.start_url = None
        self.processed_actions = []

        self.walk_pages = None
        self.walk_current_page_id = 0
        self.walk_new_pages_queue = None
        # set by _advance_to whenever its own _replay_preceding_actions
        # call stopped early on a confirmed content mismatch - read by
        # _do_start_pick right after, exactly like the other walk_*
        # fields above (this session has no separate "did the walk finish
        # cleanly" signal otherwise)
        self.walk_content_mismatch = None
        # accumulated across every (delta) walk this warm browser has done
        # since its last reset - see _replay_preceding_actions' replay_failures
        self.walk_replay_failures = []

        # SINGLE-USE PREWARM tracking: a prewarm is only ever a valid
        # head-start for the ONE pick it was made for - the exact same
        # recording/start_url/preceding_actions (which encodes the exact
        # insertion position N, since preceding_actions is always
        # real_actions[:N+1]). _prewarm_consumed starts True (nothing
        # warmed yet); _do_prewarm sets it False and records what it
        # warmed to; _do_start_pick consumes it (flips it back to True)
        # only on an exact match, and otherwise discards it - closing the
        # window and launching a genuinely fresh one instead, never
        # silently reusing a DIFFERENT pick's leftover browser state.
        self._prewarm_consumed = True
        self._prewarm_session_path = None
        self._prewarm_start_url = None
        self._prewarm_actions = None

        # set for as long as a start_pick's own _run_pick_wait_phase is
        # actively blocked waiting for a human click - lets a NEWER pick
        # request on this SAME warm session (see start_pick_session)
        # signal that wait loop to end promptly instead of silently
        # queuing behind it for up to PICK_TIMEOUT_S (CONFIRMED REAL BUG:
        # a live repro showed a second Pick Element click sit at generic
        # "waiting" with zero backend activity - no window, no injection -
        # for the full 120s until the first, abandoned session finally
        # timed out on its own).
        self._active_pick_cancel = None

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def submit(self, kind, *args):
        self._queue.put((kind, args))

    def _run(self):
        while True:
            try:
                job = self._queue.get(timeout=_WARM_SESSION_IDLE_TIMEOUT_S)
            except queue.Empty:
                if self._browser_alive():
                    print(
                        f"[pick-warm] {self.warm_id} idle for "
                        f"{_WARM_SESSION_IDLE_TIMEOUT_S}s with no prewarm/pick "
                        f"activity - closing its browser",
                        flush=True,
                    )
                    self._teardown_browser()
                continue

            kind, args = job
            try:
                if kind == "shutdown":
                    self._teardown_browser()
                    return
                elif kind == "prewarm":
                    self._do_prewarm(*args)
                elif kind == "start_pick":
                    self._do_start_pick(*args)
            except Exception as e:
                logger.error("warm pick session %s: job %r crashed: %s", self.warm_id, kind, e)

    def _browser_alive(self):
        return self.browser is not None and self.browser.is_connected()

    def _launch(self, start_url):
        self.pw = sync_playwright().start()
        try:
            self.browser = self.pw.chromium.launch(headless=False)
        except Exception as e:
            logger.warning("warm pick session: headed launch failed (%s), falling back to headless", e)
            self.browser = self.pw.chromium.launch(headless=True)

        self.context = self.browser.new_context()
        _install_pick_network_blocking(self.context)
        self.page = self.context.new_page()
        self.page.set_default_timeout(8000)
        attach_dialog_handler(self.page)

        self.walk_pages = {0: self.page}
        self.walk_current_page_id = 0
        self.walk_new_pages_queue = []
        # tab_open steps in a replayed prefix adopt the REAL new tab the
        # preceding click opened, taken from this queue (see
        # _replay_preceding_actions). That function only registers its own
        # listener when it creates the queue itself - a warm session hands
        # it an already-existing one, so without this nothing ever fills it
        # and every tab_open times out, leaving the picker on the original
        # tab. Appends to whichever queue is current (a reset replaces it).
        def _queue_new_tab(new_page):
            if self.walk_new_pages_queue is not None:
                self.walk_new_pages_queue.append(new_page)
        self.context.on("page", _queue_new_tab)

        if self.resolve_and_act is None:
            self.resolve_and_act = _load_resolve_and_act(start_url, f"warm_{self.warm_id}")

        self.processed_actions = []

        # unlike a step-level replay failure further down (best-effort,
        # never aborts the walk - see _replay_preceding_actions' own
        # docstring), failing to even reach start_url at all means there
        # is nothing useful to prewarm or pick against - propagates up
        # so _do_start_pick can surface the same clear "Couldn't reach"
        # error the one-shot fallback path
        # (_run_pick_session_fresh) always has, instead of silently
        # leaving the picker sitting on a blank/error page.
        #
        # CONFIRMED REAL BUG, found by a UI-level test driving the real
        # dashboard against an unreachable start_url: letting this
        # exception propagate while self.browser/context/page stay set
        # left the warm session "half alive" - _browser_alive() then
        # read True on the NEXT call (the browser process itself launched
        # fine; only navigation failed), so _advance_to skipped
        # re-launching entirely and fell into its own "reset" branch
        # instead, which swallows a failed goto silently by design (see
        # its own comment) - silently hiding the exact same reachability
        # failure this is supposed to surface. Tearing down everything
        # this method just created before re-raising is what makes the
        # NEXT call see _browser_alive() == False and actually retry a
        # real launch, instead of quietly reusing a browser stuck on
        # about:blank.
        try:
            self.page.goto(start_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
        except Exception:
            self._teardown_browser()
            raise

    def _teardown_browser(self):
        try:
            if self.browser is not None and self.browser.is_connected():
                self.browser.close()
        except Exception:
            pass
        try:
            if self.pw is not None:
                self.pw.stop()
        except Exception:
            pass
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.processed_actions = []
        self.walk_pages = None
        self.walk_current_page_id = 0
        self.walk_new_pages_queue = None
        self.walk_content_mismatch = None
        self.walk_replay_failures = []
        # a torn-down browser invalidates whatever it was warmed to -
        # never let a later pick think a (now-closed) prewarm is still
        # usable
        self._prewarm_consumed = True
        self._prewarm_session_path = None
        self._prewarm_start_url = None
        self._prewarm_actions = None

    def _advance_to(self, session_path, start_url, preceding_actions):
        """Gets this warm session's browser to the state right after
        preceding_actions' last step, reusing already-completed work
        when possible:

        - browser not alive yet (first use, or a previous pick already
          closed it) -> launch fresh, replay everything.
        - same recording, same or later insertion point, and
          preceding_actions actually starts with everything already
          replayed -> CONTINUE: only replay the new, delta slice.
        - anything else (different recording, or an EARLIER insertion
          point, or the two lists diverge) -> RESET: re-navigate to
          start_url and replay preceding_actions in full - but in the
          SAME browser/context, never launching a second one, so at
          least the launch cost is still saved.

        Returns the page the walk ended on.
        """
        if not self._browser_alive():
            self._launch(start_url)

        same_recording = (self.session_path == session_path and self.start_url == start_url)
        is_continuation = (
            same_recording
            and len(preceding_actions) >= len(self.processed_actions)
            and preceding_actions[:len(self.processed_actions)] == self.processed_actions
        )

        if self.processed_actions and not is_continuation:
            print(
                f"[pick-warm] {self.warm_id} target moved backward or changed "
                f"recording - resetting to start_url and replaying from scratch",
                flush=True,
            )
            try:
                self.page.goto(start_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
            except Exception as e:
                logger.debug("warm pick session: reset navigate failed (%s) - continuing", e)
            self.processed_actions = []
            self.walk_pages = {0: self.page}
            self.walk_current_page_id = 0
            self.walk_new_pages_queue = []
            self.walk_content_mismatch = None
            self.walk_replay_failures = []

        self.session_path = session_path
        self.start_url = start_url

        delta = preceding_actions[len(self.processed_actions):]
        if delta:
            _final_page, walk_state = _replay_preceding_actions(
                self.page, self.context, start_url, delta, self.resolve_and_act,
                _pages=self.walk_pages,
                _current_page_id=self.walk_current_page_id,
                _new_pages_queue=self.walk_new_pages_queue,
                _step_offset=len(self.processed_actions),
                _total=len(preceding_actions),
            )
            self.walk_pages = walk_state["pages"]
            self.walk_current_page_id = walk_state["current_page_id"]
            self.walk_new_pages_queue = walk_state["new_pages_queue"]
            self.walk_content_mismatch = walk_state["content_mismatch"]
            self.walk_replay_failures.extend(walk_state.get("replay_failures") or [])
        else:
            print(
                f"[pick-warm] {self.warm_id} already at this exact position "
                f"({len(preceding_actions)} preceding steps) - nothing to replay",
                flush=True,
            )

        # when the walk broke early on a confirmed content mismatch,
        # only the steps genuinely completed before that point are
        # "processed" - marking the FULL requested list as processed
        # here (as if the walk had reached the end normally) would make
        # a LATER _advance_to call for a longer preceding_actions list
        # see this as a valid continuation and skip straight past the
        # very step that never actually succeeded, trusting a walk that
        # never got there
        if self.walk_content_mismatch is not None:
            self.processed_actions = preceding_actions[: self.walk_content_mismatch["step_index"] - 1]
        else:
            self.processed_actions = preceding_actions
        return self.walk_pages.get(self.walk_current_page_id) or self.page

    def _do_prewarm(self, session_path, start_url, preceding_actions):
        t0 = time.monotonic()
        try:
            self._advance_to(session_path, start_url, preceding_actions)
            # records EXACTLY what this prewarm reached, so
            # _do_start_pick can later verify a pick is asking for this
            # same spot before trusting this browser as a head start -
            # see _prewarm_consumed's own comment in __init__
            self._prewarm_consumed = False
            self._prewarm_session_path = session_path
            self._prewarm_start_url = start_url
            self._prewarm_actions = preceding_actions
            print(
                f"[pick-warm] {self.warm_id} prewarmed to position "
                f"({len(preceding_actions)} preceding steps) in "
                f"{time.monotonic() - t0:.2f}s",
                flush=True,
            )
        except Exception as e:
            logger.debug(
                "warm pick session %s: prewarm failed (%s) - the next Pick "
                "Element click will replay live instead", self.warm_id, e,
            )

    def _do_start_pick(self, pick_id, session_path, start_url, preceding_actions):
        t0 = time.monotonic()

        # SINGLE-USE PREWARM CONSUMPTION (see _prewarm_consumed's own
        # comment in __init__): only trust the currently-warm browser as
        # this pick's own head start when it was warmed for THIS exact
        # recording/start_url/preceding_actions (an exact list match
        # pins down the exact insertion position N too, since
        # preceding_actions is always real_actions[:N+1]) and hasn't
        # already been handed to an earlier pick. Anything else - no
        # prewarm, a different position, an already-consumed one, or a
        # browser that died since - discards it outright: tears down
        # whatever's there FIRST, so _advance_to below is guaranteed to
        # see _browser_alive() == False and launch a genuinely NEW
        # browser process, never silently continue an unrelated one.
        prewarm_matches = (
            not self._prewarm_consumed
            and self._browser_alive()
            and self._prewarm_session_path == session_path
            and self._prewarm_start_url == start_url
            and self._prewarm_actions == preceding_actions
        )
        if prewarm_matches:
            self._prewarm_consumed = True
            print(
                f"[pick-warm] {self.warm_id} pick {pick_id} consuming its "
                f"own matching prewarm (same recording/position)",
                flush=True,
            )
        else:
            if self._browser_alive():
                print(
                    f"[pick-warm] {self.warm_id} pick {pick_id} has no "
                    f"matching unused prewarm - closing the existing "
                    f"window and launching a fresh one",
                    flush=True,
                )
            self._teardown_browser()

        try:
            final_page = self._advance_to(session_path, start_url, preceding_actions)
        except PWError as e:
            logger.warning("warm pick session %s: couldn't reach %r: %s", self.warm_id, start_url, e)
            _store_result(pick_id, {
                "status": "error",
                "message": f"Couldn't reach {start_url!r}: {e}",
            })
            self._teardown_browser()
            return
        except Exception as e:
            logger.error("warm pick session %s: advance_to crashed for pick %s: %s", self.warm_id, pick_id, e)
            _store_result(pick_id, {
                "status": "error",
                "message": "Something unexpected happened during picking - please try again.",
            })
            self._teardown_browser()
            return

        print(
            f"[pick-speed] {pick_id} warm session {self.warm_id} reached the "
            f"pick point in {time.monotonic() - t0:.2f}s",
            flush=True,
        )

        # published so a NEWER pick request on this SAME warm session (see
        # start_pick_session below) can signal THIS wait phase to end
        # promptly instead of silently queuing behind it - see this
        # attribute's own comment in __init__ for the confirmed bug this
        # fixes.
        cancel_event = threading.Event()
        self._active_pick_cancel = cancel_event

        try:
            _run_pick_wait_phase(
                pick_id, self.browser, self.context, final_page, start_url, preceding_actions,
                cancel_event=cancel_event, content_mismatch=self.walk_content_mismatch,
                replay_failures=self.walk_replay_failures,
            )
        except Exception as e:
            logger.error("warm pick session %s: wait phase crashed for pick %s: %s", self.warm_id, pick_id, e)
            _store_result(pick_id, {
                "status": "error",
                "message": "Something unexpected happened during picking - please try again.",
            })
        finally:
            if self._active_pick_cancel is cancel_event:
                self._active_pick_cancel = None
            # a finished pick (done/timeout/error/cancelled) always ends
            # with the browser closed, same as the old one-shot session
            # always did - this warm session's slot is now empty; the
            # NEXT prewarm/pick relaunches fresh, same as this warm_id's
            # very first use
            self._teardown_browser()
