"""Captures user actions on an already-open Playwright page.

We don't spawn a second browser for recording - it rides on the same
page the user launched from the dashboard. The injected JS always
forwards click/change/submit/keydown events to Python; whether they
actually get kept is gated by self.recording here, not by any flag in
page JS. That matters because page JS resets on every navigation - if
the on/off switch lived there, a "stopped" recorder could start
capturing again the moment the user navigates (add_init_script re-runs
the capture script on every new page load). Keeping the switch on the
Python side avoids that.

Navigation itself isn't something page JS can reliably report (the page
is usually about to unload), so that's watched from the Python side via
Playwright's framenavigated event instead.
"""
import gzip
import hashlib
import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# reuses the SAME atomic (temp-file + os.replace) write helper and target
# directory the finished-recording save path already uses (storage/
# repository.py) - FIX 1's incremental per-action flush writes through
# the exact same primitive, rather than a second, separately-maintained
# write routine.
from storage.repository import RECORDINGS_DIR, SNAPSHOTS_DIR, _write_json, recover_orphaned_drafts

logger = logging.getLogger(__name__)

# TEMPORARY diagnostic instrumentation switch - see the matching block in
# action_capture.js (search RECORDER_DEBUG there) for what this actually
# turns on: raw pointer/mouse/click event logging plus a log line at every
# existing dedup/discard point, all gated behind this one flag so it's a
# no-op (same behavior, same output) for every normal recording. Off by
# default; set DEBUG_RECORDER=1 (or true/yes/on, case-insensitive) in the
# environment to turn it on for one recording session. Accepts more than
# a bare "1" - a strict "1"-only check (this file's own AUTOFLOW_DEBUG-
# style precedent elsewhere in this project) silently stayed off for a
# real user who reasonably set DEBUG_RECORDER=true instead, with no error
# of any kind to indicate why - not a mistake worth letting happen twice.
_RECORDER_DEBUG = os.environ.get("DEBUG_RECORDER", "").strip().lower() in ("1", "true", "yes", "on")

# window.__RECORDER_DEBUG__ is how the flag actually reaches page JS - set
# via a one-line prefix on the SAME script already injected on every page
# load, rather than a second add_init_script call (expose_function/
# add_init_script each raise if called twice on the same page - see
# attach_page below - so this piggybacks on the existing single call
# instead of needing its own guard).
# [DIAG-REC] field-session log lines (see action_capture.js, afqaRecLog): on with AUTOFLOW_DEBUG=1 (or DEBUG_RECORDER)
_REC_FIELD_DIAG = os.environ.get("AUTOFLOW_DEBUG", "").strip() == "1" or _RECORDER_DEBUG

_CAPTURE_JS = (
    f"window.__RECORDER_DEBUG__ = {'true' if _RECORDER_DEBUG else 'false'};\n"
    f"window.__AFQA_REC_DIAG__ = {'true' if _REC_FIELD_DIAG else 'false'};\n"
    + (Path(__file__).parent / "action_capture.js").read_text(encoding="utf-8")
)


def _utc_timestamp():
    """Matches the format/timezone of JS's Date().toISOString() exactly
    (UTC, milliseconds, trailing Z) - actions recorded here (navigate, new
    tab) get sorted together with actions timestamped in the browser, and
    that only produces the right order if both sides use the same clock.
    Using local time here while JS uses UTC would silently break sorting
    on any machine not already set to UTC.
    """
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _parse_ts(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


# FIX 5 (scale): caps for the RC4 DOM-snapshot mechanism below - a
# recording with 200+ navigate-shaped actions must not turn into hundreds
# of megabytes of near-duplicate full-page HTML. Per-snapshot cap keeps
# one unusually large page from blowing the budget by itself; the session
# cap is the actual backstop for a long recording overall.
SNAPSHOT_MAX_BYTES_PER_FILE = 2 * 1024 * 1024
SNAPSHOT_MAX_BYTES_PER_SESSION = 100 * 1024 * 1024


def _is_hard_navigation(page):
    """True only for a genuine full document load (new/reload/back-
    forward), never a client-side pushState/replaceState URL change - the
    PerformanceNavigationTiming entry list the browser itself maintains
    only ever grows on a real navigation, so comparing its length across
    calls is a reliable, purely-generic signal (no site-specific
    detection of "is this an SPA filter change" needed). Best-effort: an
    evaluate() failure (page mid-navigation, closing, cross-origin during
    the check) is treated as "not a hard navigation" - the caller's own
    existing hard-navigation-specific paths simply see one fewer snapshot
    in the rare case this misfires, never a crash.
    """
    try:
        return bool(page.evaluate(
            "() => performance.getEntriesByType('navigation').length > (window.__afqaNavCount || 0)"
        ))
    except Exception:
        return False


def _mark_navigation_counted(page):
    try:
        page.evaluate(
            "() => { window.__afqaNavCount = performance.getEntriesByType('navigation').length; }"
        )
    except Exception:
        pass


class _SnapshotBudget:
    """Per-session state for the dedup/cap logic below - lives on the
    Recorder instance (one per recording session), reset at start()."""

    def __init__(self):
        self.total_bytes = 0
        self.last_content_hash = None
        self.quota_warned = False


def _capture_dom_snapshot(page, session_id, ts, budget):
    """RC4 (real DOM evidence for the future): saves a full-page HTML
    snapshot at the moment of a navigate, under
    storage/snapshots/<session_id>/<sanitized_timestamp>.html.gz - later
    consumed by tests/fixture_from_snapshot.py to rebuild a local fixture
    from what the real site actually looked like, or by a human debugging
    a stale-locator replay failure. Keyed by timestamp rather than a step
    index: the final step numbering only exists after stop() sorts every
    action chronologically, long after this navigate is captured, but the
    timestamp recorded here is the same one _record() stores on the
    navigate action itself, so any later consumer can still match this
    file back to its exact step. page.content() (not CDP MHTML) is used
    deliberately - it's a single Playwright call that works identically
    on every browser engine this tool supports, not just Chromium.

    FIX 5 (scale): gzip-compressed, capped per-file and per-session (see
    the module constants above), and skipped outright when the content is
    byte-identical to the immediately preceding snapshot in this same
    session (a pushState-driven filter change that happens to leave the
    markup unchanged, or two hard navigations landing on the same
    template) - all to keep a long recording's snapshot footprint from
    growing unbounded. Best-effort throughout: any failure here (page
    already navigating away, closed, etc) must never break the recording
    itself.
    """
    if not session_id:
        return None
    try:
        html = page.content()
    except Exception:
        return None

    raw_bytes = html.encode("utf-8", errors="replace")
    content_hash = hashlib.sha1(raw_bytes).hexdigest()
    if budget.last_content_hash == content_hash:
        return None  # identical to the previous snapshot - nothing new to save
    budget.last_content_hash = content_hash

    if budget.total_bytes >= SNAPSHOT_MAX_BYTES_PER_SESSION:
        if not budget.quota_warned:
            logger.warning(
                "session %s reached the %dMB DOM-snapshot budget - "
                "further navigate steps still record normally, just "
                "without a full-page snapshot", session_id,
                SNAPSHOT_MAX_BYTES_PER_SESSION // (1024 * 1024),
            )
            budget.quota_warned = True
        return None

    safe_ts = (ts or "").replace(":", "-").replace(".", "-")
    if not safe_ts:
        return None
    session_dir = SNAPSHOTS_DIR / session_id
    try:
        session_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = session_dir / f"{safe_ts}.html.gz"
        compressed = gzip.compress(raw_bytes, compresslevel=6)
        if len(compressed) > SNAPSHOT_MAX_BYTES_PER_FILE:
            # last-resort truncation for a genuinely huge page - still
            # useful for locator/DOM-shape debugging even if incomplete;
            # far better than either skipping it entirely or blowing the
            # per-file cap
            raw_bytes = raw_bytes[: SNAPSHOT_MAX_BYTES_PER_FILE * 4]
            compressed = gzip.compress(raw_bytes, compresslevel=6)[:SNAPSHOT_MAX_BYTES_PER_FILE]
        snapshot_path.write_bytes(compressed)
        budget.total_bytes += len(compressed)
    except Exception:
        return None
    return str(snapshot_path.relative_to(SNAPSHOTS_DIR.parent.parent))


def _add_delays(ordered_actions):
    """Stamps delay_before_ms on the FINAL normalized/chronological action
    list - current action timestamp minus the previous action's, in
    milliseconds. Computed once here (after dedup/ordering), not from raw
    low-level events, and not confused with page-load/readiness time -
    this is purely the user's own pacing between one meaningful action and
    the next."""
    prev_dt = None
    for action in ordered_actions:
        dt = _parse_ts(action.get("timestamp"))
        if prev_dt is not None and dt is not None:
            delay_ms = (dt - prev_dt).total_seconds() * 1000
            action["delay_before_ms"] = max(0, round(delay_ms))
        else:
            action["delay_before_ms"] = 0
        if dt is not None:
            prev_dt = dt
    return ordered_actions

# a link click or a submit-button click almost always causes the page change
# that follows it - these windows suppress the resulting duplicate
# navigate/submit record, since the click already represents the same step

SUBMIT_DEDUP_WINDOW = 0.6
# how long after a tab closes it is confirmed as a real "Close Tab" step: closing the whole browser closes
# every tab within milliseconds, so within this time all pages are gone (not a step)
TAB_CLOSE_CONFIRM_S = 1.5
NAV_DEDUP_WINDOW = 1.5

# how long after a click a committed navigation still counts as that click's own
# effect (seconds) - the post-click URL is captured only once it has committed
POST_CLICK_NAV_WINDOW_S = 12.0

# real navigations are often a CHAIN of redirects (tracking/ref URLs,
# consent interstitials, etc) that fire several framenavigated events in
# quick succession for what the user experiences as ONE action. Waiting
# this long after the last one before committing avoids recording each
# intermediate hop as its own separate (duplicate) navigate action.
# Measured live against Amazon: the hop from the /s/ref=nb_sb_noss redirect
# to the final /s?k=... results URL landed anywhere from ~2.5s to >3s after
# the first hop across different loads - real redirect timing is genuinely
# variable, not a fixed interval. 4.5s gives real-world chains enough room
# to fully settle in the common case; this remains a best-effort heuristic,
# not a guarantee, since no fixed timeout can bound an arbitrarily slow chain.
NAV_SETTLE_WINDOW = 4.5

# same priority order resolve_and_act uses at replay time (see
# generator/script_generator.py) - kept here just for the human-readable
# terminal display, not for actually finding elements
_LOCATOR_ATTR_ORDER = ("data-testid", "data-test", "data-cy", "name", "aria-label", "placeholder", "role")


def _describe_element(locator_profile):
    """Best-effort human label for a [RECORDED] line - prefer visible text/
    accessible name, fall back to attributes a user would recognize, then
    id/tag."""
    lp = locator_profile or {}
    text = (lp.get("element_text") or lp.get("text") or "").strip()
    if text:
        return text
    accessible_name = (lp.get("accessible_name") or "").strip()
    if accessible_name:
        return accessible_name
    attrs = lp.get("attributes") or {}
    for key in ("aria-label", "placeholder", "title", "name"):
        if lp.get(key.replace("-", "_")) or attrs.get(key):
            return lp.get(key.replace("-", "_")) or attrs.get(key)
    if lp.get("id"):
        return lp["id"]
    return lp.get("tag") or "(unknown element)"


def _locator_display(locator_profile):
    """What selector would actually be used to find this element again -
    shown on the Locator: line so a fragile capture (no id, no attributes,
    just a tag) is obvious right away instead of hiding behind "Element: img".
    """
    lp = locator_profile or {}
    if lp.get("id"):
        return lp["id"]
    if lp.get("href"):
        return f'a[href="{lp["href"]}"]'
    attrs = lp.get("attributes") or {}
    for attr in _LOCATOR_ATTR_ORDER:
        if attrs.get(attr):
            return f'[{attr}="{attrs[attr]}"]'
    if lp.get("css_path"):
        return lp["css_path"]
    if lp.get("xpath"):
        return lp["xpath"]
    return "(no stable locator found - will fall back to screen position)"


def _print_action_line(action):
    """The live terminal feedback the user watches while recording - this
    is deliberately plain print(), not the logging module, since it's
    meant to be read by a person in real time, not parsed as a log."""
    action_type = action.get("action_type")
    lp = action.get("locator_profile")
    # only shown once a second tab/page exists - keeps single-tab recording
    # output identical to before this ever mattered
    page_tag = f" (page {action['page_id']})" if action.get("page_id") else ""

    if action_type == "click":
        print(f"\n[RECORDED] CLICK{page_tag}\nElement: {_describe_element(lp)}\nLocator: {_locator_display(lp)}", flush=True)
    elif action_type == "dblclick":
        print(f"\n[RECORDED] DOUBLE CLICK{page_tag}\nElement: {_describe_element(lp)}\nLocator: {_locator_display(lp)}", flush=True)
    elif action_type == "right_click":
        print(f"\n[RECORDED] RIGHT CLICK{page_tag}\nElement: {_describe_element(lp)}\nLocator: {_locator_display(lp)}", flush=True)
    elif action_type == "fill":
        print(f"\n[RECORDED] FILL{page_tag}\nElement: {_describe_element(lp)}\nLocator: {_locator_display(lp)}\nValue: {action.get('value')}", flush=True)
    elif action_type == "select":
        print(f"\n[RECORDED] SELECT{page_tag}\nElement: {_describe_element(lp)}\nLocator: {_locator_display(lp)}\nValue: {action.get('value')}", flush=True)
    elif action_type == "submit":
        print(f"\n[RECORDED] SUBMIT{page_tag}\nElement: {_describe_element(lp)}\nLocator: {_locator_display(lp)}", flush=True)
    elif action_type == "navigate":
        print(f"\n[RECORDED] NAVIGATE{page_tag}\nURL: {action.get('page_url')}", flush=True)
    elif action_type == "press":
        print(f"\n[RECORDED] PRESS{page_tag}\nElement: {_describe_element(lp)}\nKey: {action.get('value')}\nLocator: {_locator_display(lp)}", flush=True)
    elif action_type == "scroll":
        print(f"\n[RECORDED] SCROLL{page_tag}\nDelta: ({action.get('delta_x', 0)}, {action.get('delta_y', 0)})", flush=True)
    elif action_type == "tab_switch":
        print(f"\n[RECORDED] TAB SWITCH\n{action.get('from_page_id')} -> {action.get('to_page_id')}", flush=True)
    elif action_type == "tab_open":
        print(f"\n[RECORDED] TAB OPEN\npage_id={action.get('page_id')} (from page {action.get('from_page_id')})\nURL: {action.get('page_url')}", flush=True)
    elif action_type == "tab_close":
        print(f"\n[RECORDED] TAB CLOSE\npage_id={action.get('page_id')} -> remaining page {action.get('remaining_page_id')}", flush=True)
    elif action_type == "validate":
        print(f"\n[RECORDED] VALIDATE (auto-added){page_tag}\nExpected text: {action.get('value')}", flush=True)
    else:
        print(f"\n[RECORDED] {str(action_type).upper()}{page_tag}", flush=True)


class _PageState:
    """Per-page navigation-debounce state. Each open page/tab tracks its
    own pending redirect chain independently - two tabs mid-navigation at
    the same moment must not be able to cancel or overwrite each other's
    timers."""
    __slots__ = (
        "nav_timer", "pending_nav_url", "pending_nav_ts", "last_nav_url", "nav_chain_click_ts",
        "last_click_ts", "closed", "last_click_action_ts", "nav_chain_click_action_ts",
        "pending_nav_snapshot_path", "pending_nav_chain", "_chain_open",
        "history_expect", "last_history", "titles", "pending_nav_chain_start",
    )

    def __init__(self, initial_url):
        self.nav_timer = None
        self.pending_nav_url = None
        self.pending_nav_ts = None
        self.pending_nav_snapshot_path = None
        self.pending_nav_chain = []
        self._chain_open = False
        # when the pending chain's FIRST page change happened: a click can only have caused a navigation it
        # came before (see _click_that_caused)
        self.pending_nav_chain_start = None
        # Back / Forward presses the page reported whose own navigation event has not arrived yet:
        # [(landed url, time)] - that event must not become a second step (see _record_history)
        self.history_expect = []
        self.last_history = None
        self.titles = {}
        self.last_nav_url = initial_url
        self.nav_chain_click_ts = None
        self.last_click_ts = 0.0
        self.closed = False
        # RC3: the causing click's own RECORDED timestamp (a string, the
        # same field _record() stores on every action) - not last_click_ts
        # (a bare time.time() float, only ever used for the elapsed-time
        # comparison). This is what lets a navigate step point back at
        # the specific action that caused it (caused_by_timestamp) so
        # replay can resolve it to a real step index later, after
        # stop()'s own final chronological sort.
        self.last_click_action_ts = None
        self.nav_chain_click_action_ts = None


class Recorder:
    def __init__(self, page):
        self.page = page
        self.actions = []
        self.start_url = None
        self.session_id = None
        self.recording = False
        # ISSUE 2: the page is usable (and the user may already click) from the
        # moment it loads, before start() is called. The initial Navigate is
        # stamped with the moment this Recorder was created (before the page was
        # loaded), and anything the user does before start() is held here and
        # saved, in order, right after that Navigate - never dropped or sorted
        # in front of it.
        self._created_ts = _utc_timestamp()
        self._prestart_buffer = []
        self._accept_prestart = True
        # set by install_context_capture() (FIX 1 - recorder attaches too
        # late): once a context-level expose_binding/add_init_script pair
        # is installed, attach_page() must NOT also register a page-level
        # one for the SAME name - Playwright raises if "recordAction" is
        # registered twice on the same context. Callers that never call
        # install_context_capture() (any existing caller) see no behavior
        # change at all - attach_page() falls back to its original,
        # unchanged per-page registration exactly as before.
        self._context_capture_installed = False
        # set fresh by start() - the stable filename this session's
        # incremental draft is written to (see _flush_draft). Fixed once
        # at start(), never recomputed per-flush, so every incremental
        # write lands on the SAME file instead of a new one each time.
        self._draft_path = None
        # FIX 5 (scale): the append-only sidecar _flush_draft() writes
        # every action to in O(1) time (see its own docstring for why the
        # old "rewrite the whole JSON every action" approach doesn't scale
        # to a long recording) - same stem as _draft_path, set alongside
        # it in start().
        self._draft_jsonl_path = None
        self._draft_actions_since_consolidate = 0
        self._draft_last_consolidate_at = 0.0
        self._snapshot_budget = _SnapshotBudget()
        # FIX 2 (locator stability) - keyed by target_timestamp; a patch
        # that arrives before its own target action has been appended yet
        # (CONFIRMED to actually happen: Playwright's expose_binding
        # delivery order across two independent, differently-timed send()
        # calls from the page is not guaranteed to match the order those
        # calls were made in) is held here and applied the moment that
        # action DOES get appended (see _record()), instead of being
        # silently dropped.
        self._pending_locator_patches = {}
        self._pending_post_click = {}
        self._last_click_ref = None
        self._last_click_wall = 0.0
        # id(page) -> sequential page_id, assigned in the order pages are
        # attached (0 = the original page, 1/2/... = tabs opened during
        # recording, in the order they appeared) - this is what lets the
        # executor later know which page/tab each action belongs to
        self._page_ids = {}
        self._page_states = {}  # page_id -> _PageState
        self._pages = {}  # page_id -> Page object (kept even after close, for historical lookup)
        self._next_page_id = 0
        # which page_id the user is currently on, and which page_ids have
        # ever been the active one before - used to tell a genuine "user
        # switched back to an already-open tab" (tab_switch) apart from a
        # page's own first activation (initial load, or a just-opened new
        # tab autofocusing itself) - see _handle_visibility
        self._active_page_id = 0
        self._pages_ever_focused = set()

    def get_any_open_page(self):
        """Returns a still-open Page object, or None if every registered
        page has closed. Used by the recording session's own liveness
        loop (see app.py) so that closing the ORIGINAL page while another
        page/tab remains open doesn't get mistaken for the whole browser
        having closed - the loop needs some open page to poll, and it
        should not be hardcoded to whichever one happened to be first.
        """
        for page_id, state in self._page_states.items():
            if not state.closed:
                page = self._pages.get(page_id)
                if page is not None:
                    return page
        return None

    def _page_id_for(self, page):
        key = id(page)
        if key not in self._page_ids:
            self._page_ids[key] = self._next_page_id
            self._next_page_id += 1
        return self._page_ids[key]

    def _apply_post_click_patch(self, patch):
        """Merges a click's post-click result into the click action itself
        (found by timestamp, newest first); held until that action arrives
        when the patch outruns it - same pattern as the locator-stability
        patch below."""
        target_ts = patch.get("target_timestamp")
        post_click = patch.get("post_click")
        if not target_ts or not isinstance(post_click, dict):
            return
        for action in reversed(self.actions):
            if action.get("timestamp") == target_ts:
                self._merge_post_click(action, post_click)
                return
        self._pending_post_click[target_ts] = post_click

    def _apply_reply_patch(self, patch):
        """The chatbot's reply (the text new on the page after a send, saved once it finished) is attached to the
        step that sent the prompt (found by timestamp, newest first); held until that step arrives if it outruns it."""
        target_ts = patch.get("target_timestamp")
        text = patch.get("reply_text")
        # FACTS observed for this send (see action_capture.js): the typed text showed up as a new entry on the
        # page, and the message box was still there afterwards - kept even when there is no reply text
        facts = {k: bool(patch.get(k)) for k in ("message_echoed", "input_kept") if k in patch}
        has_text = isinstance(text, str) and bool(text.strip())
        if not target_ts or (not has_text and not facts):
            return
        for action in reversed(self.actions):
            if action.get("timestamp") == target_ts:
                if has_text:
                    action["reply_text"] = text
                action.update(facts)
                return
        if has_text:
            self.__dict__.setdefault("_pending_reply", {})[target_ts] = text
        if facts:
            self.__dict__.setdefault("_pending_reply_facts", {})[target_ts] = facts

    @staticmethod
    def _merge_post_click(action, post_click):
        """Merge the page-side post-click result into the click step. The
        page-side URL is read before a navigation the click started has
        committed (the old page is all it can see), so it never replaces a
        URL already recorded AFTER such a navigation (post_click["navigated"])."""
        existing = action.setdefault("post_click", {})
        incoming = dict(post_click)
        if existing.get("navigated"):
            incoming.pop("url_path_after", None)
        existing.update(incoming)

    def _apply_locator_stability_patch(self, patch):
        """FIX 2 (locator stability, additive only): merges an async
        match_count/disambiguation report (see action_capture.js's
        _scheduleLocatorStabilityCheck) into the action it belongs to,
        found by matching timestamp - the same unique-per-action key
        caused_by_timestamp already relies on elsewhere in this file.
        Searched in reverse (most recent actions first) since the patch
        always arrives shortly after its target action, never before an
        equally-timestamped OLDER one could exist (timestamps come from
        Date.now(), effectively unique in practice).

        Deliberately does NOT touch the JSONL sidecar (_flush_draft) -
        that would either require re-appending the whole patched action
        (breaking the append-only, one-line-per-action invariant a crash-
        recovery read depends on) or a second file format entirely, for a
        signal that's purely an extra scoring hint, never load-bearing
        for correctness. The periodic full-JSON consolidation naturally
        picks up the patched value the next time it runs regardless, and
        the FINAL save (stop() -> save_recording()) always reflects it
        immediately since this mutates self.actions in place, in memory -
        the only real exposure is a crash between the patch landing and
        the next consolidation, which loses nothing but this one nice-to-
        have hint on whichever action was mid-flight.

        A target action that's already been trimmed/edited via some other
        path is a genuine no-op (nothing left to patch). A target
        timestamp that doesn't match anything YET is held in
        self._pending_locator_patches and applied the moment a matching
        action is recorded (see _record()) - CONFIRMED necessary, not
        theoretical: this patch can and does arrive before its own target
        action's expose_binding call is delivered/processed, even though
        the target was sent to the page's own recordAction bridge first.
        """
        target_ts = patch.get("target_timestamp")
        if not target_ts:
            return
        for action in reversed(self.actions):
            if action.get("timestamp") == target_ts:
                self._merge_locator_patch_into(action, patch)
                return
        self._pending_locator_patches[target_ts] = patch

    @staticmethod
    def _merge_locator_patch_into(action, patch):
        # locator_profile and act_target are the SAME object by reference
        # in the JS payload (see buildProfile's own "act_target:
        # locatorProfile"), but JSON serialization over the recordAction
        # bridge does not preserve that identity - they land here as two
        # separate dict copies, so both need patching explicitly for
        # generate_script()'s whitelist (which reads them as two distinct
        # fields) to see this on either one.
        for key in ("locator_profile", "act_target"):
            lp = action.get(key)
            if isinstance(lp, dict):
                lp["match_count"] = patch.get("match_count")
                if patch.get("disambiguation"):
                    lp["disambiguation"] = patch.get("disambiguation")

    def _record(self, action):
        self.actions.append(action)
        # FIX 2 (locator stability): a patch for THIS action's own
        # timestamp may have already arrived and be waiting (see
        # _apply_locator_stability_patch's own docstring for why this
        # ordering genuinely happens) - apply it now rather than never.
        pending_patch = self._pending_locator_patches.pop(action.get("timestamp"), None)
        if pending_patch is not None:
            self._merge_locator_patch_into(action, pending_patch)
        _pending_reply = self.__dict__.get("_pending_reply", {}).pop(action.get("timestamp"), None)
        if _pending_reply:
            action["reply_text"] = _pending_reply
        _pending_facts = self.__dict__.get("_pending_reply_facts", {}).pop(action.get("timestamp"), None)
        if _pending_facts:
            action.update(_pending_facts)
        pending_pc = self._pending_post_click.pop(action.get("timestamp"), None)
        if pending_pc is not None:
            self._merge_post_click(action, pending_pc)
        if action.get("action_type") in ("click", "dblclick", "right_click", "check", "press", "submit", "select"):
            self._last_click_ref = action
            self._last_click_wall = time.time()
            # the new tab this click opened was announced before the click itself arrived
            if time.time() - getattr(self, "_last_tab_open_wall", 0.0) < 1.5 and action.get("action_type") in ("click", "dblclick", "press", "submit"):
                action.setdefault("post_click", {})["new_tab"] = True
        lp = action.get("locator_profile") or {}
        logger.info("captured %s on %s (page_id=%s)", action.get("action_type"), lp.get("tag"), action.get("page_id"))
        _print_action_line(action)
        self._flush_draft()

    # FIX 5 (scale): a full-JSON rewrite is only paid this often, not on
    # every single action - CONFIRMED REAL COST this fixes: the old
    # unconditional rewrite-the-whole-file-every-action approach made each
    # action's own save cost proportional to EVERY action recorded so far
    # (dom_context/html-chain data included), an O(N^2) total write cost
    # across a long recording. 20 actions is small enough that a crash
    # between consolidations only ever loses a short, recent stretch - the
    # append-only JSONL sidecar below already has every action as it
    # happens regardless, this cadence only controls how often the
    # human-readable/recovery .json snapshot itself gets refreshed.
    DRAFT_CONSOLIDATE_EVERY_N_ACTIONS = 20
    DRAFT_CONSOLIDATE_MIN_INTERVAL_S = 10.0

    def _flush_draft(self):
        """Incremental per-action persistence (FIX 1, refined by FIX 5):
        every action is appended to self._draft_jsonl_path (one JSON
        object per line, opened in append mode) - O(1) per call,
        regardless of how many actions came before it - so closing the
        browser manually, or a genuine crash, loses nothing beyond
        whatever hasn't happened yet. The full, human-readable/recovery
        self._draft_path JSON is still refreshed periodically (see the
        cadence constants above), never on every single action, so a long
        recording's per-action save cost stays flat instead of growing
        with everything recorded so far. Best-effort only throughout: a
        write failure here must never interrupt recording itself, only
        get logged.
        """
        if not self._draft_path:
            return
        action = self.actions[-1] if self.actions else None
        if action is not None and self._draft_jsonl_path:
            try:
                with open(self._draft_jsonl_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(action, ensure_ascii=False, default=str) + "\n")
            except Exception as e:
                logger.warning("incremental draft JSONL append failed (%s): %s", self._draft_jsonl_path, e)

        self._draft_actions_since_consolidate += 1
        now = time.monotonic()
        due = (
            self._draft_actions_since_consolidate >= self.DRAFT_CONSOLIDATE_EVERY_N_ACTIONS
            or (now - self._draft_last_consolidate_at) >= self.DRAFT_CONSOLIDATE_MIN_INTERVAL_S
        )
        if not due:
            return
        self._consolidate_draft()

    def _consolidate_draft(self):
        """Full rewrite of self._draft_path from self.actions - same
        primitive/shape _flush_draft always used before FIX 5, just no
        longer called on every single action. Also called once, straight
        away, whenever the JSONL append itself couldn't be used at all
        (self._draft_jsonl_path unset - shouldn't happen for a normally-
        started session, but keeps a session with no sidecar at all
        exactly as safe as before this change instead of silently losing
        crash-recovery coverage)."""
        if not self._draft_path:
            return
        try:
            _write_json(self._draft_path, {
                "name": self._draft_path.stem,
                "start_url": self.start_url,
                "actions": self.actions,
            })
            self._draft_actions_since_consolidate = 0
            self._draft_last_consolidate_at = time.monotonic()
        except Exception as e:
            logger.warning("incremental draft flush failed (%s): %s", self._draft_path, e)

    def _on_action(self, page_id, raw, frame_info=None):
        if not self.recording:
            if self._accept_prestart and len(self._prestart_buffer) < 500:
                self._prestart_buffer.append((page_id, raw, frame_info))
            return
        try:
            action = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("dropped malformed action payload from page_id=%s", page_id)
            return
        action.pop("frame_hint", None)

        if action.get("action_type") == "__page_visible__":
            # internal signal, not a real user action - never appended to
            # self.actions directly, only used to decide whether a
            # tab_switch action should be recorded (see _ensure_active)
            self._ensure_active(page_id, action.get("timestamp"))
            return

        if action.get("action_type") == "__locator_stability__":
            # FIX 2 (locator stability, additive only) - see
            # action_capture.js's own _scheduleLocatorStabilityCheck: a
            # ~300ms-delayed report of how many live elements the
            # already-recorded action's primary locators actually match,
            # arriving as its own message rather than folded into the
            # original synchronous payload (counting DOM matches is real,
            # if small, cost that must never add latency to the capture-
            # click path). Patches the matching action in place; never a
            # new action of its own.
            self._apply_locator_stability_patch(action)
            return

        if action.get("action_type") == "__reply__":
            self._apply_reply_patch(action)
            return

        if action.get("action_type") == "__reply_stop__":
            # a reply went quiet right after a real mouse press made while it was being written: the click step
            # of that press is what stopped it (replay must stop the reply there too) - metadata, never a step
            try:
                _at = _parse_ts(action.get("at"))
                if _at is not None:
                    for _a in reversed(self.actions):
                        if _a.get("action_type") not in ("click", "dblclick", "right_click"):
                            continue
                        _cdt = _parse_ts(_a.get("timestamp"))
                        if _cdt is not None and -0.3 <= (_cdt - _at).total_seconds() <= 1.5:
                            _a["stops_reply"] = True
                            break
            except Exception as e:
                logger.warning("reply-stop note could not be applied: %s", e)
            return

        if action.get("action_type") == "__history__":
            self._record_history(page_id, action)
            return

        if action.get("action_type") == "__title__":
            self._apply_title(page_id, action)
            return

        if action.get("action_type") == "__post_click__":
            # what the page did in response to a click, captured after it
            # settled (see action_capture.js's _schedulePostClickObservation):
            # merged into that click step as metadata - never a step of its own
            self._apply_post_click_patch(action)
            return

        if action.get("action_type") == "__consistency_warning__":
            # diagnostic-only signal from the recorder's own JS-side
            # badge/counter consistency check (see checkForMissedClick in
            # action_capture.js) - printed straight to the terminal so
            # whoever is recording notices it live, never appended to
            # self.actions (it isn't a user action, and never changes
            # what actually gets recorded)
            print(
                f"\nWarning: {action.get('message')} (page_id={page_id})\n",
                flush=True,
            )
            logger.warning("consistency check: %s (page_id=%s)", action.get("message"), page_id)
            return

        # a real action arriving on a page we didn't think was active is
        # itself proof the user is now on it - a real action can only
        # happen on the page the user is actually looking at. This is a
        # deliberate second, independent signal alongside visibilitychange
        # (see _ensure_active): visibilitychange depends on the browser's
        # own window-focus tracking, which isn't available/reliable in
        # every environment a recording might run in, so this guarantees
        # a genuine switch still gets recorded even when that signal never
        # fires, without ever fabricating one when it isn't warranted.
        self._ensure_active(page_id, action.get("timestamp"))

        state = self._page_states.get(page_id)
        last_click_ts = state.last_click_ts if state else 0.0

        if action.get("action_type") == "submit" and time.time() - last_click_ts < SUBMIT_DEDUP_WINDOW:
            # the submit button click just recorded already represents this
            logger.info("skipped submit - already represented by the click just recorded")
            return

        action["page_id"] = page_id
        # FIX 6 (iframe/frame tracking - e.g. Razorpay's checkout, a
        # cross-origin iframe): only ever set for an action that genuinely
        # came from a non-main frame (see _describe_frame/_on_action_
        # binding) - every existing caller of _on_action (attach_page's
        # own per-page expose_function path) never passes frame_info at
        # all, so this key is simply absent for every action exactly as
        # before, on any recording made without context-level capture.
        if frame_info is not None:
            action["frame"] = frame_info
        self._record(action)

        if state is not None and action.get("action_type") in ("click", "dblclick", "right_click", "check"):
            state.last_click_ts = time.time()
            # RC3: this action's own recorded timestamp - see
            # _PageState's own docstring for exactly what this is used
            # for (a navigate's caused_by_timestamp).
            state.last_click_action_ts = action.get("timestamp")

        # recording captures ONLY what the user did: nothing here ever adds an
        # action (validation/assert included) on its own - a validation step
        # exists only if the user adds it deliberately through the editor's
        # "Add Action"

    def _ensure_active(self, page_id, ts):
        """Makes page_id the active page, recording a tab_switch action
        only when this is a genuine change away from a page that was
        already known/active before - never for a page's own first
        activation (initial load, or a just-opened new tab autofocusing
        itself - see record_new_tab), and never when _on_page_closed
        already accounted for the same transition internally (a tab
        closing and focus automatically returning to another one is a
        lifecycle consequence of the close, not a separate user action).
        """
        if not self.recording or page_id not in self._page_states:
            return
        if self._page_states[page_id].closed:
            return

        if page_id not in self._pages_ever_focused:
            self._pages_ever_focused.add(page_id)
            self._active_page_id = page_id
            return

        if page_id == self._active_page_id:
            return

        from_page_id = self._active_page_id
        from_state = self._page_states.get(from_page_id)
        to_state = self._page_states.get(page_id)
        self._active_page_id = page_id

        self._record({
            "action_type": "tab_switch",
            "value": None,
            "locator_profile": None,
            "bounding_box": None,
            "from_page_id": from_page_id,
            "to_page_id": page_id,
            "from_url": from_state.last_nav_url if from_state else None,
            "to_url": to_state.last_nav_url if to_state else None,
            "page_url": to_state.last_nav_url if to_state else None,
            "timestamp": ts or _utc_timestamp(),
            "page_id": page_id,
        })

    def _on_page_closed(self, page_id):
        """A page/tab was closed - by the user via the browser's own tab
        close button, or programmatically. Persisted as a real tab_close
        action (not a fake DOM click - there's no element to attribute it
        to) so the saved JSON matches what the terminal reports at
        runtime. Order matters here, matching exactly what's required:
        capture the closing page's last known URL and figure out which
        page remains active BEFORE appending the action (so the action
        itself can correctly say what page replay/inspection should
        expect to be current afterward), THEN update internal active-page
        tracking - that ordering is what lets _ensure_active recognize
        the next real action on the remaining page as a continuation
        rather than fabricate a tab_switch for what was really just the
        close's own side effect.
        """
        state = self._page_states.get(page_id)
        if state is None or state.closed:
            return

        last_known_url = state.last_nav_url
        was_active = self.recording and self._active_page_id == page_id
        remaining_id = self._pick_fallback_active_page(exclude=page_id) if was_active else self._active_page_id

        state.closed = True
        if state.nav_timer is not None:
            state.nav_timer.cancel()
            state.nav_timer = None

        logger.info("page_id=%d closed", page_id)
        print(f"\n[RECORDER] TAB/PAGE CLOSED (page_id={page_id})\n", flush=True)

        # CONFIRMED REAL BUG this fixes: this handler has no way to tell
        # "the user closed one of several open tabs" (a real test step)
        # apart from "the user closed the browser window to STOP
        # recording" (stop_reason="browser_closed" isn't known until
        # AFTER this event already fired) - both look identical from
        # here alone. The one thing that DOES distinguish them: closing
        # the whole browser leaves NO other page open afterward, while a
        # genuine mid-test tab close always leaves at least the original
        # tab (or another one) still open. Checked fresh here (not via
        # was_active/remaining_id above, which are only ever None in the
        # narrower was_active-and-no-fallback case) so this catches it
        # regardless of which page happened to be active.
        any_other_open = any(
            pid != page_id and not st.closed for pid, st in self._page_states.items()
        )

        if self.recording and any_other_open:
            # closing the whole BROWSER closes its tabs one after another - the first ones still see the
            # others open. So a tab close is only kept when, a moment later, the recording is still running
            # and another page is still open (the user closed ONE tab); its own timestamp keeps its place.
            _close_action = {
                "action_type": "tab_close",
                "value": None,
                "locator_profile": None,
                "bounding_box": None,
                "page_id": page_id,
                "page_url": last_known_url,
                "remaining_page_id": remaining_id,
                "timestamp": _utc_timestamp(),
            }
            try:
                _t = threading.Timer(TAB_CLOSE_CONFIRM_S, self._commit_tab_close, args=(_close_action,))
                _t.daemon = True
                self.__dict__.setdefault("_pending_tab_closes", {})[id(_close_action)] = (_t, _close_action)
                _t.start()
            except Exception as e:
                logger.warning("tab close confirmation could not be scheduled (%s) - recorded at once", e)
                self._record(_close_action)

        if was_active and remaining_id is not None:
            self._active_page_id = remaining_id
            self._pages_ever_focused.add(remaining_id)

    def _commit_tab_close(self, action, force=None):
        """Timer callback (plain Python state only, like _commit_pending_navigate): keep the tab close when the
        recording is still running and another page is still open - else it was part of closing the browser and
        is not a step. force=True/False decides directly (used by stop()). Never raises."""
        try:
            pending = self.__dict__.get("_pending_tab_closes", {})
            if pending.pop(id(action), None) is None:
                return                                   # already decided
            if force is None:
                keep = (self.recording and not self.__dict__.get("_browser_closing", False)
                        and any(not st.closed for st in self._page_states.values()))
            else:
                keep = bool(force)
            if keep:
                self._record(action)
            else:
                logger.info("tab close (page_id=%s) not recorded: it came from closing the browser", action.get("page_id"))
                print("\n[RECORDER] tab close ignored - it was part of closing the browser\n", flush=True)
        except Exception as e:
            logger.warning("tab close confirmation failed: %s", e)

    def _pick_fallback_active_page(self, exclude):
        # the original page is almost always where the user ends up after
        # closing a tab they opened from it - fall back to whatever else
        # is still open if that's not available (e.g. page 0 itself is
        # the one that closed)
        if exclude != 0 and 0 in self._page_states and not self._page_states[0].closed:
            return 0
        for pid, state in self._page_states.items():
            if pid != exclude and not state.closed:
                return pid
        return None

    def _on_navigate(self, page_id, frame):
        if not self.recording or frame != frame.page.main_frame:
            return
        url = frame.url
        if not url.startswith(("http://", "https://")):
            return
        state = self._page_states.get(page_id)
        if state is None:
            return

        # the hop of a Back / Forward press the page already reported (see _record_history): the
        # press is its own step, and it must neither start a redirect chain nor swallow the
        # navigation of the action before it
        if state.history_expect:
            _now_h = time.time()
            state.history_expect[:] = [e for e in state.history_expect if _now_h - e[1] < 6.0]
            for _e in list(state.history_expect):
                if _e[0] == url:
                    state.history_expect.remove(_e)
                    state.last_nav_url = url
                    return

        # a page-change event that lands on the page the recorder already knows it is on (a second event of a
        # Back / Forward press, a restore from the browser cache) is no navigation: it never starts a chain that
        # a later click's own navigation would then be folded into
        if state.nav_timer is None and url == state.last_nav_url:
            return

        # captured HERE, synchronously, on the real framenavigated event -
        # not when the settle timer below eventually fires. The commit is
        # deliberately delayed (to dedupe a redirect chain into one
        # action), but the delay must never leak into the RECORDED
        # timestamp: other actions the user performs during that delay
        # get their own timestamps immediately, and stop() later sorts
        # every action by timestamp to restore true chronological order.
        # A timestamp taken at commit-time instead of event-time would be
        # stamped up to NAV_SETTLE_WINDOW seconds late, which is long
        # enough for several later, real actions to end up sorted BEFORE
        # a navigate that actually happened before all of them - this is
        # what actually causes a misordered navigate, on any site, any
        # time a navigation is followed by other actions within that
        # window, not something specific to any one recording.
        ts = _utc_timestamp()

        if state.nav_timer is not None:
            # a hop arriving on the heels of the previous one (well within
            # NAV_DEDUP_WINDOW - the same threshold already used elsewhere
            # in this file to tell "just happened" apart from "unrelated")
            # is a genuine technical redirect chain still unwinding -
            # collapse it as before. A hop arriving after a REAL gap is
            # different: the user actually did something on the page the
            # previous hop landed on for a meaningful stretch of time (any
            # site: scrolled a product page, read an article, filled part
            # of a form) before navigating again - even if this new hop
            # happens to land back on the exact same URL the chain started
            # from, that intermediate page was a real, distinct state the
            # user genuinely visited, not a transient redirect artifact.
            # Committing the pending hop right now, instead of letting it
            # keep getting silently overwritten, is what stops "went to a
            # product page, looked at it, came back" from vanishing
            # entirely just because the round trip ends up at its own
            # starting URL - the exact same-URL check in
            # _commit_pending_navigate below is only meant to catch a
            # chain that never really went anywhere, not a real visit
            # that happened to return.
            prev_ts = _parse_ts(state.pending_nav_ts)
            now_dt = _parse_ts(ts)
            gap = (now_dt - prev_ts).total_seconds() if (prev_ts and now_dt) else 0.0
            # (or the user clicked something AFTER the pending hop: that next navigation is the
            # click's own - never folded into the previous action's redirect chain)
            _acted_since = bool(
                prev_ts is not None and state.last_click_ts is not None
                and state.last_click_ts > prev_ts.timestamp()
            )
            if gap > NAV_DEDUP_WINDOW or _acted_since:
                state.nav_timer.cancel()
                state.nav_timer = None
                self._commit_pending_navigate(page_id)
            else:
                # already mid-chain (a redirect that followed an earlier
                # one within the settle window) - just update which URL/
                # timestamp we'll eventually commit (this later hop is the
                # real moment the FINAL url below became current), don't
                # snapshot the click time again
                state.nav_timer.cancel()

        if state.nav_timer is None:
            # first hop of a possible chain (either genuinely the first
            # navigation on this page, or the fresh start right after
            # committing an earlier, genuinely-separate pending hop above)
            # - remember whether a click/submit just happened, checked
            # once THIS chain finally settles
            state.nav_chain_click_ts = state.last_click_ts
            state.nav_chain_click_action_ts = state.last_click_action_ts
            state.pending_nav_chain_start = ts

        # every hop of the (possibly redirecting) navigation, in order - the
        # click that started it gets the whole chain as expected_url_chain
        if not hasattr(state, "pending_nav_chain") or getattr(state, "_chain_open", False) is False:
            state.pending_nav_chain = []
        state._chain_open = True
        if not state.pending_nav_chain or state.pending_nav_chain[-1] != url:
            state.pending_nav_chain.append(url)
        state.pending_nav_url = url
        state.pending_nav_ts = ts
        # RC4: captured synchronously here, on the real framenavigated
        # event, while `frame`'s page is guaranteed to be on this exact
        # URL - waiting until _commit_pending_navigate (which runs on a
        # background Timer thread, unsafe to touch the Playwright page
        # from at all) would be both too late (a later hop in the same
        # chain may have already navigated further) and unsafe.
        #
        # FIX 5 (scale): a full-page snapshot is only ever worth taking
        # for a REAL document load - a client-side filter/sort/pagination
        # change (pushState, no actual reload) fires this exact same
        # framenavigated event but leaves the page's own markup almost
        # entirely intact, so snapshotting it too is pure duplicate cost
        # (CONFIRMED against a real Myntra recording: 16 full ~1.2MB
        # snapshots for 57 actions, most of them near-identical filter-
        # panel states). The navigate ACTION itself is still recorded
        # exactly as before either way - only the snapshot capture is
        # skipped for a soft/pushState hop.
        _hard_nav = _is_hard_navigation(frame.page)
        _mark_navigation_counted(frame.page)
        if _hard_nav:
            state.pending_nav_snapshot_path = _capture_dom_snapshot(
                frame.page, self.session_id, ts, self._snapshot_budget,
            )
        else:
            state.pending_nav_snapshot_path = None
        state.nav_timer = threading.Timer(NAV_SETTLE_WINDOW, self._commit_pending_navigate, args=(page_id,))
        state.nav_timer.daemon = True
        state.nav_timer.start()

    def _click_that_caused(self, page_id, url, nav_ts):
        """The recorded click-type action that caused a navigation to `url`:
        the latest one on this page whose own recorded page_url differs from
        `url` (a click made once the page had already reached `url` cannot
        have caused it), within POST_CLICK_NAV_WINDOW_S of the navigation.
        None when there is no such click (a typed URL, back/forward)."""
        _nav_dt = _parse_ts(nav_ts)
        try:
            _ordered = sorted(self.actions, key=lambda a: a.get("timestamp") or "", reverse=True)
        except Exception:
            _ordered = list(reversed(self.actions))
        for _a in _ordered:
            _cdt0 = _parse_ts(_a.get("timestamp"))
            # made after the navigation began: it cannot have caused it
            if _nav_dt is not None and _cdt0 is not None and _cdt0 > _nav_dt:
                continue
            if _a.get("action_type") not in ("click", "dblclick", "right_click", "check", "press", "submit", "select"):
                # another real action of the user (Back / Forward, a typed address, typing, a tab switch ...)
                # came between the last click and this navigation: the navigation is not that click's result.
                # Scrolling and hovering never cause a navigation and are passed over.
                if _a.get("action_type") not in ("scroll", "hover") and not str(_a.get("action_type") or "").startswith("__"):
                    return None
                continue
            if _a.get("page_id") != page_id:
                continue
            if (_a.get("page_url") or "") == url:
                continue
            _cdt = _parse_ts(_a.get("timestamp"))
            if _nav_dt is not None and _cdt is not None and (_nav_dt - _cdt).total_seconds() > POST_CLICK_NAV_WINDOW_S:
                return None
            return _a
        return None

    def _commit_pending_navigate(self, page_id):
        # runs on the Timer's own thread - only touches plain Python state
        # here (list append, attribute writes), never the Playwright page,
        # so this is safe despite not being the thread that owns the browser
        state = self._page_states.get(page_id)
        if state is None:
            return
        state.nav_timer = None
        url = state.pending_nav_url
        ts = state.pending_nav_ts
        _chain_start_ts = getattr(state, "pending_nav_chain_start", None) or ts
        state.pending_nav_chain_start = None
        snapshot_path = state.pending_nav_snapshot_path
        state.pending_nav_url = None
        state.pending_nav_ts = None
        state.pending_nav_snapshot_path = None
        if not self.recording or not url or url == state.last_nav_url:
            return
        state.last_nav_url = url

        # BUG: "was this navigate caused by the click" must be judged
        # against the ACTUAL event-time gap between the click and the
        # navigate (ts, captured synchronously in _on_navigate above) -
        # not time.time() read fresh here, at COMMIT time. Commit is
        # deliberately delayed (the NAV_SETTLE_WINDOW timer, so a redirect
        # chain can unwind first - see _on_navigate's own docstring), and
        # can also fire EARLY the moment a later, genuinely-separate hop
        # arrives (the gap > NAV_DEDUP_WINDOW branch above). Either way,
        # how much wall-clock time has passed by the moment this function
        # happens to run is scheduling jitter, not a signal about the
        # user's real actions - yet it was the ONLY thing this comparison
        # looked at. A click that opens a fragment-only modal (".../cart"
        # -> ".../cart#modal") 26-130ms later is exactly the kind of
        # navigate downstream replay depends on seeing recorded (see
        # generator/script_generator.py's whole click-then-navigate-to-
        # modal verification path) - the SAME click-then-hash-navigate
        # pattern was silently, non-deterministically dropped from a
        # recording purely because this happened to run a bit sooner or
        # later than another otherwise-unrelated recorded action, never
        # because the navigate itself arrived any differently. Comparing
        # against the navigate's own recorded timestamp instead makes the
        # decision depend only on the real gap between the click and the
        # navigate - deterministic, and independent of when Python
        # happens to get around to committing it.
        _nav_dt = _parse_ts(ts)
        _elapsed_since_click = (
            _nav_dt.timestamp() - state.nav_chain_click_ts if _nav_dt is not None
            else time.time() - state.nav_chain_click_ts
        )
        # RC3 (inconsistent navigate recording - CONFIRMED REAL BUG via a
        # live Myntra recording: a filter click's own resulting URL
        # change was recorded as its own navigate step for SOME filter
        # clicks but silently DROPPED for others, purely because of how
        # fast the SPA's own route update happened to settle relative to
        # this exact window, not because of anything different about the
        # click itself). This used to return here instead of recording
        # anything at all whenever the navigate followed a click/check
        # within NAV_DEDUP_WINDOW, on the theory that "the click already
        # represents this, nothing new to add" - but the resulting URL
        # IS real, meaningful state a filter/sort click's own recorded
        # page_url never otherwise captures, and replay depends on
        # seeing it to verify the click's own effect. Every URL change
        # is now recorded unconditionally (still deduped against the
        # immediately preceding URL by the check above) - the ONLY thing
        # this timing comparison still decides is whether to tag this
        # navigate with caused_by_timestamp, so replay can tell "this
        # was a direct effect of the preceding action" (verify-only, see
        # generator/script_generator.py's own navigate handling) apart
        # from a navigate with no specific preceding cause.
        _caused_by_ts = (
            state.nav_chain_click_action_ts
            if (state.nav_chain_click_ts is not None and _elapsed_since_click < NAV_DEDUP_WINDOW)
            else None
        )

        # the action this navigation really belongs to (an Enter press counts, not only a click)
        _real_cause = self._click_that_caused(page_id, url, _chain_start_ts)
        if _caused_by_ts and _real_cause is not None and _real_cause.get("timestamp") != _caused_by_ts:
            _caused_by_ts_for_post = None
        else:
            _caused_by_ts_for_post = _caused_by_ts
        if _caused_by_ts_for_post:
            for _a in reversed(self.actions):
                if _a.get("timestamp") == _caused_by_ts_for_post:
                    try:
                        from urllib.parse import urlsplit as _us
                        _u = _us(url)
                        _a.setdefault("post_click", {})["url_path_after"] = f"{_u.scheme}://{_u.netloc}{_u.path}"
                    except Exception:
                        pass
                    break

        # the page the click was on has now navigated: this committed URL is the
        # click's post-click URL. Never the pre-click URL - the page-side
        # observation can only ever have seen that one, because it ran before
        # the navigation committed. Bounded window; a later redirect hop
        # updates it, so the FINAL committed URL wins.
        # FIX 3 (attribution): the click that CAUSED this navigation - not
        # simply the latest click. Playwright's sync API delivers the
        # framenavigated event only when the recorder thread next yields, so
        # by the time it is handled the user may already have clicked again
        # (that later click was made ON the new page). The causing click is
        # the latest one made on a page other than the one just reached.
        _click = self._click_that_caused(page_id, url, _chain_start_ts)
        if _click is not None:
            try:
                from urllib.parse import urlsplit as _us2
                _nu = _us2(url)
                _pc = _click.setdefault("post_click", {})
                _before = _us2(_pc.get("url_path_before") or _click.get("page_url") or "")
                _pc.setdefault("url_path_before", f"{_before.scheme}://{_before.netloc}{_before.path}" if _before.netloc else None)
                if (_nu.netloc, _nu.path.rstrip("/")) != (_before.netloc, _before.path.rstrip("/")):
                    _pc["url_path_after"] = f"{_nu.scheme}://{_nu.netloc}{_nu.path}"
                    _pc["navigated"] = True
            except Exception:
                pass

        _chain = list(getattr(state, "pending_nav_chain", None) or [url])
        state._chain_open = False
        state.pending_nav_chain = []
        if _click is not None:
            # I1-c: this navigation is the EFFECT of the user's action. It is
            # attached to that action as where it leads (expected_url) with the
            # redirect chain it went through, instead of being saved as a
            # standalone Navigate step. Only a navigation with no action
            # behind it (a typed URL, back/forward, reload) stays a Navigate.
            # The one exception: a navigation that only ADDS a fragment to the
            # page (a modal / sub-state opened by the click) is still kept as a
            # step - replay's modal verification keys off it - but is marked
            # induced so it is never re-navigated.
            if not _click.get("expected_url"):
                _click["expected_url"] = _chain[0]
            _ch = _click.setdefault("expected_url_chain", [])
            for _u in _chain:
                if _u not in _ch:
                    _ch.append(_u)
            try:
                from urllib.parse import urlsplit as _us3
                _a3, _b3 = _us3(url), _us3(_click.get("page_url") or "")
                _fragment_only = (
                    (_a3.scheme, _a3.netloc, _a3.path, _a3.query) == (_b3.scheme, _b3.netloc, _b3.path, _b3.query)
                    and _a3.fragment != _b3.fragment
                )
            except Exception:
                _fragment_only = False
            if not _fragment_only:
                logger.info("navigation to %s attached to the %s that caused it (expected_url)", url, _click.get("action_type"))
                return
            _induced_by_action = True
        else:
            _induced_by_action = False

        self._record({
            "action_type": "navigate",
            "value": None,
            "locator_profile": None,
            "bounding_box": None,
            "page_url": url,
            "induced_by_prev": True if _induced_by_action else None,
            # the true event-time timestamp captured in _on_navigate above,
            # not _utc_timestamp() called fresh here at commit-time - the
            # whole point of this fix. Falls back to "now" only if that
            # somehow wasn't set, which should never happen in practice.
            "timestamp": ts or _utc_timestamp(),
            "page_id": page_id,
            "caused_by_timestamp": _caused_by_ts,
            "dom_snapshot_path": snapshot_path,
            "page_title": state.titles.get(url),
        })

    def _record_history(self, page_id, msg):
        """A Back / Forward press, reported by the page (action_capture.js): recorded as its OWN step -
        never merged with another press (even a second one a moment later, or one that lands on a
        page seen before), never a plain Navigate. Whatever navigation was still pending belongs to the
        action BEFORE the press and is finished first, so that action keeps its own expected result."""
        state = self._page_states.get(page_id)
        url = (msg.get("url") or "")
        if state is None or not url.startswith(("http://", "https://")):
            return
        now = time.time()
        if state.last_history and state.last_history[0] == url and now - state.last_history[1] < 0.5:
            return                                        # the same press reported twice (cache restore + entry change)
        state.last_history = (url, now)
        if state.nav_timer is not None and state.pending_nav_url == url:
            # this press's own navigation event arrived first: take it back out of the pending chain
            chain = list(state.pending_nav_chain or [])
            if len(chain) >= 2 and chain[-1] == url:
                chain.pop()
                state.pending_nav_chain = chain
                state.pending_nav_url = chain[-1]
            else:
                state.nav_timer.cancel()
                state.nav_timer = None
                state.pending_nav_url = None
                state.pending_nav_ts = None
                state.pending_nav_snapshot_path = None
                state.pending_nav_chain = []
                state._chain_open = False
        else:
            state.history_expect.append((url, now))
        if state.nav_timer is not None:
            state.nav_timer.cancel()
            state.nav_timer = None
            self._commit_pending_navigate(page_id)
        state.last_nav_url = url
        direction = msg.get("direction") if msg.get("direction") in ("back", "forward") else "back"
        title = msg.get("title") or state.titles.get(url)
        self._record({
            "action_type": "navigate",
            "history": direction,
            "value": None,
            "locator_profile": None,
            "bounding_box": None,
            "page_url": url,
            "expected_url": url,
            "page_title": title,
            "induced_by_prev": None,
            "timestamp": msg.get("timestamp") or _utc_timestamp(),
            "page_id": page_id,
            "caused_by_timestamp": None,
            "dom_snapshot_path": None,
        })

    def _apply_title(self, page_id, msg):
        """The page title for a navigation step, reported by the page once it has loaded."""
        state = self._page_states.get(page_id)
        url, title = msg.get("url"), msg.get("title")
        if state is None or not url or not title:
            return
        state.titles[url] = title
        for a in reversed(self.actions):
            if a.get("action_type") == "navigate" and a.get("page_id") == page_id and a.get("page_url") == url:
                if not a.get("page_title"):
                    a["page_title"] = title
                break

    def install_context_capture(self, context):
        """FIX 1 (recorder attaches too late): registers the recordAction
        bridge and the capture script at the CONTEXT level, before any
        page exists - call this immediately after browser.new_context(),
        before context.new_page()/page.goto(). Playwright applies a
        context-level add_init_script to every page the context ever
        creates, including that page's very FIRST navigation (unlike a
        per-page add_init_script registered after page.goto() has already
        started, which only covers navigations AFTER it was registered) -
        this is what actually closes the gap where an early cookie-accept
        or nav-menu click during the initial load was previously never
        observed at all (nothing was listening yet).

        expose_binding (not expose_function) is used specifically so the
        callback receives `source` (source.page / source.frame) - the
        SAME mechanism FIX 6 (iframe/frame tracking) needs to know which
        frame an action actually came from, without a second, separate
        injection mechanism.

        Must be called at most once per context (Playwright raises if
        "recordAction" is registered twice) - attach_page() checks
        self._context_capture_installed and skips its own, otherwise-
        identical per-page registration once this has run, so the two
        can never conflict.
        """
        context.expose_binding("recordAction", self._on_action_binding)
        context.add_init_script(_CAPTURE_JS)
        self._context_capture_installed = True

    def _on_action_binding(self, source, raw):
        """expose_binding callback (see install_context_capture) - source
        is Playwright's own dict-like BindingCall source info (keys:
        "context", "page", "frame" - NOT attribute access, unlike the
        equivalent JS-side API), carrying which page/frame this call
        actually came from. Resolves that to the same page_id scheme
        _page_id_for/attach_page already use, then defers to the
        existing _on_action(page_id, raw, frame_info) for every bit of
        real handling - this is purely an adapter, not a second code path.
        """
        try:
            page_id = self._page_id_for(source["page"])
        except Exception:
            logger.warning("recordAction binding fired with no resolvable page - dropped")
            return
        frame_info = None
        try:
            _hint = json.loads(raw).get("frame_hint")
        except Exception:
            _hint = None
        try:
            frame_info = self._describe_frame(source["frame"], _hint)
        except Exception:
            pass
        self._on_action(page_id, raw, frame_info=frame_info)

    def _describe_frame(self, frame, hint=None):
        """FIX 6 (iframe/frame tracking - Razorpay's checkout is a cross-
        origin iframe, and page_url/page_id alone can never express "this
        action happened inside a nested frame"). Returns None for the
        main frame (nothing extra to record - the overwhelming majority
        of actions), or a small dict describing a nested frame: its own
        URL, and its owning <iframe> element's src/name/id as seen from
        the PARENT frame - enough for replay to re-find the same frame
        later via frame_locator (matched by iframe src host), without
        needing a second, frame-scoped injection mechanism.

        Wrapped in one outer try/except (on top of the inner, per-field
        ones already here for partial-info cases): a detached/mid-
        navigation frame, or anything else going wrong while describing
        it, must never propagate - the caller (_on_action_binding) always
        records the action itself regardless of what this returns, and
        losing the frame annotation is far better than losing the action.
        """
        try:
            try:
                if frame == frame.page.main_frame:
                    return None
            except Exception:
                pass
            info = {"frame_url": None, "parent_iframe_src": None, "parent_iframe_name": None}
            try:
                info["frame_url"] = frame.url
            except Exception:
                pass
            # NOT frame.frame_element(): a blocking Playwright call inside this binding callback
            # never returns and froze the whole recording; the page side sent what it knows
            if isinstance(hint, dict):
                info["parent_iframe_src"] = hint.get("src")
                info["parent_iframe_name"] = hint.get("name") or hint.get("title")
            try:
                info["frame_name"] = frame.name or None
            except Exception:
                pass
        except Exception:
            logger.debug("_describe_frame failed entirely (detached frame?) - action still recorded")
            return None
        return info

    def attach_page(self, page, is_initial=False):
        """Wires the SAME action-capture mechanism (recordAction bridge,
        injected JS, navigation tracking) onto a page - the original
        recording page, or a new tab/window that opened during recording.
        Every page a user might act on while recording gets this, so
        actions performed on any of them keep being captured instead of
        disappearing the moment focus moves to a new tab. Safe to call more
        than once for the same page object (a no-op after the first time).
        """
        page_id = self._page_id_for(page)
        if page_id in self._page_states:
            return page_id

        self._page_states[page_id] = _PageState(page.url)
        self._pages[page_id] = page

        # expose_function/add_init_script each raise if called twice on the
        # SAME page object - the guard above (page_id in self._page_states)
        # already prevents that, since every distinct page object gets a
        # distinct page_id exactly once. Skipped entirely when
        # install_context_capture() already registered the SAME
        # "recordAction" name at the context level (FIX 1) - registering
        # it again here, per-page, would raise; every page created from
        # that context is already covered by the context-level init
        # script regardless. Callers that never call
        # install_context_capture() are completely unaffected - this
        # branch is unchanged from before.
        if not self._context_capture_installed:
            page.expose_function("recordAction", lambda raw, pid=page_id: self._on_action(pid, raw))
            page.add_init_script(_CAPTURE_JS)
        page.on("framenavigated", lambda frame, pid=page_id: self._on_navigate(pid, frame))
        page.on("close", lambda closed_page, pid=page_id: self._on_page_closed(pid))

        # TEMPORARY diagnostic relay (see _RECORDER_DEBUG above) - the
        # page-side instrumentation logs via console.log with a
        # distinctive "[recorder-debug]" prefix specifically so this can
        # forward ONLY those lines to the terminal, not a busy site's own
        # unrelated console noise. A no-op registration when the flag is
        # off, so this never affects a normal recording either way.
        if _RECORDER_DEBUG or _REC_FIELD_DIAG:
            def _relay_debug_console(msg, pid=page_id):
                try:
                    text = msg.text
                except Exception:
                    return
                if text.startswith("[DIAG-REC]") or (_RECORDER_DEBUG and text.startswith("[recorder-debug]")):
                    print(text, flush=True)
            page.on("console", _relay_debug_console)

        try:
            page.evaluate(_CAPTURE_JS)
        except Exception:
            # page may be mid-navigation right when this attaches - the
            # init script above still covers it on the next load
            pass

        logger.info("recorder attached to page_id=%d url=%s", page_id, page.url)
        if not is_initial:
            print(f"\n[RECORDER] New tab/page detected - now recording on it too\nURL: {page.url}\n", flush=True)
        return page_id

    def record_new_tab(self, new_page):
        """Called when the user's action opened a new browser tab/window
        (target="_blank" link, ctrl+click, window.open, etc). Attaches
        capture to the new page (so its own actions keep being recorded)
        and records a distinct tab_open action - not a navigate - so the
        JSON keeps the same distinction the terminal already makes between
        "a new page was created" and "this page navigated somewhere",
        tagged with the new page's page_id so replay knows to switch to it.
        """
        if not self.recording:
            return
        url = new_page.url
        if not url or not url.startswith(("http://", "https://")):
            return
        from_page_id = self._active_page_id
        self._last_tab_open_wall = time.time()
        if self._last_click_ref is not None and time.time() - self._last_click_wall < 6.0:
            self._last_click_ref.setdefault("post_click", {})["new_tab"] = True
        page_id = self.attach_page(new_page, is_initial=False)
        self._record({
            "action_type": "tab_open",
            "value": None,
            "locator_profile": None,
            "bounding_box": None,
            "page_url": url,
            "timestamp": _utc_timestamp(),
            "new_tab": True,
            "page_id": page_id,
            "from_page_id": from_page_id,
        })

    def start(self, launch_url=None):
        """launch_url (FIX 1): when given, this is the literal URL the
        caller passed to page.goto() - used verbatim as start_url / Step
        1's own recorded navigate, instead of re-reading self.page.url
        (which, by the time start() runs, may already reflect a
        server-side or client-side redirect the user never asked for,
        silently recording the WRONG starting point). Omitted (the
        default, backward-compatible for any existing caller), this
        behaves exactly as before: self.page.url is used as-is.
        """
        # FIX 6 (crash recovery): before this NEW session creates its own
        # draft/sidecar, sweep up any leftover sidecar from a PREVIOUS
        # session that never reached a successful save (killed process,
        # crash, power loss) - safe here specifically because only one
        # recording is ever active at a time (see session_state["active"]
        # in app.py), so anything found at this exact point can only
        # belong to an already-ended session, never this one. Best-effort:
        # never lets a recovery hiccup block starting the new recording.
        try:
            recover_orphaned_drafts()
        except Exception as e:
            logger.warning("crash-recovery sweep failed (continuing to start recording anyway): %s", e)

        self.actions = []
        self.start_url = launch_url if launch_url else self.page.url
        self.session_id = uuid.uuid4().hex
        # the browser / its window going away (the user closing the browser to end the recording): tab closes
        # caused by that are not steps (see _commit_tab_close)
        self._browser_closing = False
        try:
            def _mark_browser_closing(*_a):
                self._browser_closing = True
            self.page.context.on("close", _mark_browser_closing)
            if self.page.context.browser is not None:
                self.page.context.browser.on("disconnected", _mark_browser_closing)
        except Exception as e:
            logger.warning("browser-close signal could not be registered (%s) - page counting alone is used", e)
        # stable for this whole session (see _flush_draft) - computed
        # once, here, never recomputed per-flush. Uses the SAME
        # "session_<timestamp>" shape save_recording() falls back to when
        # no explicit name was given, so a recording finished normally
        # and never explicitly renamed ends up at (effectively) this same
        # path - _finish_recording's own cleanup (see app.py) removes
        # this draft once the real, final save has succeeded.
        self._draft_path = RECORDINGS_DIR / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        # FIX 5: append-only sidecar - same cleanup as _draft_path itself
        # (see _finish_recording in app.py), never left behind after a
        # normal, successful save.
        self._draft_jsonl_path = self._draft_path.with_suffix(".draft.jsonl")
        self._draft_actions_since_consolidate = 0
        self._draft_last_consolidate_at = time.monotonic()
        self._snapshot_budget = _SnapshotBudget()
        self._pending_locator_patches = {}
        self._pending_post_click = {}
        self._last_click_ref = None
        self._last_click_wall = 0.0
        self.recording = True
        self._page_ids = {}
        self._page_states = {}
        self._pages = {}
        self._next_page_id = 0
        self._active_page_id = 0
        self._pages_ever_focused = {0}

        # ITEM 1: every recording's own actions list must always begin
        # with an explicit "navigate" action for the initial page load -
        # previously this was only ever captured in start_url (a
        # separate, top-level field), never as an action in its own
        # right, so actions[0] was normally whatever the user did FIRST
        # (a click, a fill, ...) with no explicit record of how replay
        # even got to that starting page at all. Recorded the exact same
        # shape _commit_pending_navigate already uses for every OTHER
        # navigate action, so nothing downstream (replay, the editor,
        # the report) needs to treat this one any differently from a
        # normal recorded navigate.
        self._record({
            "action_type": "navigate",
            "value": None,
            "locator_profile": None,
            "bounding_box": None,
            "page_url": self.start_url,
            "timestamp": self._created_ts,
            "page_id": 0,
        })

        self.attach_page(self.page, is_initial=True)

        # whatever the user did before start() ran, in the order it happened
        self._accept_prestart = False
        _held, self._prestart_buffer = self._prestart_buffer, []
        for _pid, _raw, _fi in _held:
            try:
                self._on_action(_pid, _raw, frame_info=_fi)
            except Exception as _e:
                logger.warning("could not replay an action captured before start(): %s", _e)

        # log the final (possibly redirected) URL separately from the
        # literal launch_url recorded as Step 1 above - visible in the
        # recorder's own log/terminal for diagnosis, never written into
        # the recording JSON (Step 1 must stay the literal requested URL)
        try:
            resolved_url = self.page.url
        except Exception:
            resolved_url = None
        logger.info("recording started - launch_url=%s resolved_url=%s", self.start_url, resolved_url)
        if resolved_url and resolved_url != self.start_url:
            print(
                f"[RECORDER] Note: page ended up at {resolved_url!r} "
                f"(redirected from the requested {self.start_url!r})",
                flush=True,
            )
        print(
            "\n" + "=" * 50 +
            "\nRECORDING STARTED\n\nBrowser:\n" + self.start_url +
            "\n\nPerform your actions in the browser.\n\n"
            "Press ENTER in this terminal to stop recording.\n" +
            "=" * 50 + "\n",
            flush=True,
        )

    def stop(self, name=None, stop_reason="terminal_enter"):
        # a value typed into a text field but never committed (no Enter, no
        # blur, no later action) must not be lost just because recording
        # ends now: ask every still-open page/frame to flush it as a final
        # Fill step (action_capture.js's window.__afqaFlushPendingFill) while
        # recording is still on, so _on_action still accepts it
        for _pid, _page in list(self._pages.items()):
            _pstate = self._page_states.get(_pid)
            if _pstate is None or _pstate.closed:
                continue
            _flushed = False
            try:
                for _frame in _page.frames:
                    try:
                        _flushed = bool(_frame.evaluate(
                            "() => !!(window.__afqaFlushPendingFill && window.__afqaFlushPendingFill('stop-recording'))"
                        )) or _flushed
                    except Exception:
                        pass
                if _flushed:
                    _page.wait_for_timeout(300)  # let the recordAction message arrive
            except Exception:
                pass

        # tab closes still waiting for confirmation: part of closing the browser -> not steps; a normal stop
        # while the browser stays open -> the user closed that tab, kept
        try:
            for _key, (_tmr, _act) in list(self.__dict__.get("_pending_tab_closes", {}).items()):
                try:
                    _tmr.cancel()
                except Exception:
                    pass
                self._commit_tab_close(_act, force=(False if stop_reason == "browser_closed" else None))
        except Exception as e:
            logger.warning("pending tab closes could not be settled: %s", e)

        # a navigation that was still mid-redirect-chain (debounce timer
        # pending) on any open page when the user stopped is still a real,
        # meaningful final action - flush it now instead of just
        # cancelling and losing it
        for page_id, state in list(self._page_states.items()):
            if state.nav_timer is not None:
                state.nav_timer.cancel()
                state.nav_timer = None
                self._commit_pending_navigate(page_id)

        self.recording = False
        self._accept_prestart = False

        # actions can arrive at Python slightly out of order relative to
        # when they truly happened - the double-click disambiguation in
        # action_capture.js briefly holds a click back to see if a second
        # one follows, so a fill/select committed a moment later (via a
        # blur it triggered) can arrive first even though the click came
        # first in real life. Each action's own timestamp is still captured
        # at the true moment it happened though, so sorting on that here
        # restores the real order for the saved JSON/replay regardless of
        # arrival order - across every page/tab that was recorded, not just
        # the original one.
        ordered_actions = sorted(self.actions, key=lambda a: a.get("timestamp") or "")
        _add_delays(ordered_actions)

        # the RESULT of each step, in one place (additive; replay judges a step by its result):
        # the page address after it, whether it navigated, whether a dialog was open, a new tab
        for _a in ordered_actions:
            _pc = _a.get("post_click") if isinstance(_a.get("post_click"), dict) else None
            if _pc is None:
                continue
            _chain = _a.get("expected_url_chain") or []
            _a["result"] = {
                "url_after": (_chain[-1] if _chain else None) or _pc.get("url_path_after"),
                "navigated": bool(_pc.get("navigated") or _a.get("expected_url")),
                "dialog_open": _pc.get("dialog_open"),
                "new_tab": bool(_pc.get("new_tab")),
            }

        # CONFIRMED REAL BUG this fixes: replay used to force a hardcoded
        # 900px-tall viewport regardless of what the recording actually
        # used - a scroll action's own recorded target (scroll_y_after)
        # is only ever reachable at replay time when the page's real
        # scrollable range (document_height - viewport_height) matches
        # what it was at record time. A live screen recording showed
        # genuinely-working scrolls on Sportzia reported as FAILED
        # ("scroll did not reach target position") purely because the
        # recorded viewport (608-640px tall, this specific machine's own
        # real browser window at record time) didn't match replay's
        # fixed 900px one - verified directly via page.viewport_size/
        # window.innerHeight on both a headed and a headless replay
        # launch, both reading 900 regardless of what was recorded.
        # Optional field - an old recording made before this existed
        # simply doesn't have it, and replay falls back to Playwright's
        # own default (1280x720) exactly as if this had never been
        # added; nothing about the old JSON schema changes.
        try:
            viewport = self.page.viewport_size
        except Exception:
            viewport = None

        # FIX 1.5 (recording environment): device scale factor, user
        # agent, locale, timezone and color scheme, alongside the
        # viewport above - a replay whose browser context doesn't match
        # any of these can render meaningfully different layouts (a
        # responsive breakpoint, a date/number format a text-match
        # depends on, a dark-mode-only control) than what was actually
        # recorded. Every one of these is read directly from the live
        # page (never guessed/hardcoded), so it reflects whatever this
        # specific recording session's own browser actually used. Purely
        # additive and optional throughout: a read that fails (or an
        # older recording made before this existed) just leaves that one
        # field None, and replay already falls back to its own current
        # defaults for any missing field - see generate_script().
        def _safe_env_eval(js, default=None):
            try:
                return self.page.evaluate(js)
            except Exception:
                return default

        test_case = {
            "name": name,
            "session_id": self.session_id,
            "start_url": self.start_url,
            "recorded_at": datetime.now().isoformat(),
            "stop_reason": stop_reason,
            "total_actions": len(ordered_actions),
            "page_count": len(self._page_states),
            "viewport_width": (viewport or {}).get("width"),
            "viewport_height": (viewport or {}).get("height"),
            "device_scale_factor": _safe_env_eval("() => window.devicePixelRatio"),
            "user_agent": _safe_env_eval("() => navigator.userAgent"),
            "locale": _safe_env_eval("() => navigator.language"),
            "timezone_id": _safe_env_eval(
                "() => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone; } "
                "catch (e) { return null; } }"
            ),
            "color_scheme": _safe_env_eval(
                "() => (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) "
                "? 'dark' : 'light'"
            ),
            "actions": ordered_actions,
        }
        logger.info(
            "recording stopped (%s), %d actions captured across %d page(s)",
            stop_reason, len(ordered_actions), len(self._page_states),
        )
        return test_case
