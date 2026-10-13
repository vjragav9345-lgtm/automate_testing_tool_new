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
import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_CAPTURE_JS = (Path(__file__).parent / "action_capture.js").read_text(encoding="utf-8")


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
NAV_DEDUP_WINDOW = 1.5

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
    else:
        print(f"\n[RECORDED] {str(action_type).upper()}{page_tag}", flush=True)


class _PageState:
    """Per-page navigation-debounce state. Each open page/tab tracks its
    own pending redirect chain independently - two tabs mid-navigation at
    the same moment must not be able to cancel or overwrite each other's
    timers."""
    __slots__ = ("nav_timer", "pending_nav_url", "pending_nav_ts", "last_nav_url", "nav_chain_click_ts", "last_click_ts", "closed")

    def __init__(self, initial_url):
        self.nav_timer = None
        self.pending_nav_url = None
        self.pending_nav_ts = None
        self.last_nav_url = initial_url
        self.nav_chain_click_ts = None
        self.last_click_ts = 0.0
        self.closed = False


class Recorder:
    def __init__(self, page):
        self.page = page
        self.actions = []
        self.start_url = None
        self.session_id = None
        self.recording = False
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

    def _record(self, action):
        self.actions.append(action)
        lp = action.get("locator_profile") or {}
        logger.info("captured %s on %s (page_id=%s)", action.get("action_type"), lp.get("tag"), action.get("page_id"))
        _print_action_line(action)

    def _on_action(self, page_id, raw):
        if not self.recording:
            return
        try:
            action = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("dropped malformed action payload from page_id=%s", page_id)
            return

        if action.get("action_type") == "__page_visible__":
            # internal signal, not a real user action - never appended to
            # self.actions directly, only used to decide whether a
            # tab_switch action should be recorded (see _ensure_active)
            self._ensure_active(page_id, action.get("timestamp"))
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
        self._record(action)

        if state is not None and action.get("action_type") in ("click", "dblclick", "right_click"):
            state.last_click_ts = time.time()

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

        if self.recording:
            self._record({
                "action_type": "tab_close",
                "value": None,
                "locator_profile": None,
                "bounding_box": None,
                "page_id": page_id,
                "page_url": last_known_url,
                "remaining_page_id": remaining_id,
                "timestamp": _utc_timestamp(),
            })

        if was_active and remaining_id is not None:
            self._active_page_id = remaining_id
            self._pages_ever_focused.add(remaining_id)

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
            # already mid-chain (a redirect that followed an earlier one
            # within the settle window) - just update which URL/timestamp
            # we'll eventually commit (this later hop is the real moment
            # the FINAL url below became current), don't snapshot the
            # click time again
            state.nav_timer.cancel()
        else:
            # first hop of a possible chain - remember whether a click/
            # submit just happened, checked once the chain finally settles
            state.nav_chain_click_ts = state.last_click_ts

        state.pending_nav_url = url
        state.pending_nav_ts = ts
        state.nav_timer = threading.Timer(NAV_SETTLE_WINDOW, self._commit_pending_navigate, args=(page_id,))
        state.nav_timer.daemon = True
        state.nav_timer.start()

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
        state.pending_nav_url = None
        state.pending_nav_ts = None
        if not self.recording or not url or url == state.last_nav_url:
            return
        state.last_nav_url = url

        if state.nav_chain_click_ts is not None and time.time() - state.nav_chain_click_ts < NAV_DEDUP_WINDOW:
            # the whole redirect chain was caused by the click/submit step
            # already recorded - nothing new to add
            return

        self._record({
            "action_type": "navigate",
            "value": None,
            "locator_profile": None,
            "bounding_box": None,
            "page_url": url,
            # the true event-time timestamp captured in _on_navigate above,
            # not _utc_timestamp() called fresh here at commit-time - the
            # whole point of this fix. Falls back to "now" only if that
            # somehow wasn't set, which should never happen in practice.
            "timestamp": ts or _utc_timestamp(),
            "page_id": page_id,
        })

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
        # distinct page_id exactly once
        page.expose_function("recordAction", lambda raw, pid=page_id: self._on_action(pid, raw))
        page.add_init_script(_CAPTURE_JS)
        page.on("framenavigated", lambda frame, pid=page_id: self._on_navigate(pid, frame))
        page.on("close", lambda closed_page, pid=page_id: self._on_page_closed(pid))

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

    def start(self):
        self.actions = []
        self.start_url = self.page.url
        self.session_id = uuid.uuid4().hex
        self.recording = True
        self._page_ids = {}
        self._page_states = {}
        self._pages = {}
        self._next_page_id = 0
        self._active_page_id = 0
        self._pages_ever_focused = {0}

        self.attach_page(self.page, is_initial=True)

        logger.info("recording started at %s", self.start_url)
        print(
            "\n" + "=" * 50 +
            "\nRECORDING STARTED\n\nBrowser:\n" + self.start_url +
            "\n\nPerform your actions in the browser.\n\n"
            "Press ENTER in this terminal to stop recording.\n" +
            "=" * 50 + "\n",
            flush=True,
        )

    def stop(self, name=None, stop_reason="terminal_enter"):
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

        test_case = {
            "name": name,
            "session_id": self.session_id,
            "start_url": self.start_url,
            "recorded_at": datetime.now().isoformat(),
            "stop_reason": stop_reason,
            "total_actions": len(ordered_actions),
            "page_count": len(self._page_states),
            "actions": ordered_actions,
        }
        logger.info(
            "recording stopped (%s), %d actions captured across %d page(s)",
            stop_reason, len(ordered_actions), len(self._page_states),
        )
        return test_case
