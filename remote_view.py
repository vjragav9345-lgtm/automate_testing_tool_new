"""REMOTE LIVE BROWSER (cloud server only).

On Render (the RENDER environment variable, set automatically by Render) the browser runs headless on the server.
This module lets the dashboard SEE the active page (Chromium DevTools screencast: Page.startScreencast, JPEG
frames, every frame acknowledged) and CONTROL it (mouse / keyboard sent back and applied with page.mouse /
page.keyboard - real, trusted input, so the existing recorder captures it exactly as on a local window).

Everywhere else (Windows / macOS / any machine without RENDER) REMOTE_MODE is False: no source is ever started,
the endpoints only answer {"remote": false}, and every existing code path runs exactly as before.

THREADING: Playwright sync objects are only touched by the thread that owns them. The owning thread (the recording
session, a Pick Element session) registers a Source and calls pump_for() in place of its own idle wait; pump()
starts / switches the screencast on the page that code already treats as active, acknowledges received frames and
applies queued input. Flask request threads only read the latest frame and put input events on a thread-safe
queue. A replay runs in its own process: its generated script writes its latest frame to live_view.json in its run
folder (same file hand-off the replay already uses for report.json), and this module only reads that file.

FAIL SAFE: any error is logged and turns off only the live view of that source - never a recording, Pick Element
session, replay or live log.
"""
import json
import logging
import os
import queue
import threading
import time
from pathlib import Path

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

REMOTE_MODE = os.environ.get("RENDER") is not None

_INPUT_QUEUE_MAX = 400          # pending input events per source (older mouse moves are dropped first)
_SOURCE_STALE_S = 5.0           # a source whose owner has not pumped for this long is not shown
_SCREENCAST_PARAMS = {"format": "jpeg", "quality": 60, "everyNthFrame": 1}
_MOUSE_BUTTONS = ("left", "right", "middle")

_LOCK = threading.Lock()
_SOURCES = []                   # registered in-process sources, newest last
_SEQ = [0]


class Source:
    """One live view: a kind ("recording", "pick"), a callable that returns the page the owning code treats as
    active, the latest frame and an input queue. Only the owning thread calls pump()/stop()."""

    def __init__(self, kind, get_active_page):
        self.kind = kind
        self.get_active_page = get_active_page
        self.id = f"{kind}-{int(time.time() * 1000)}"
        self.inputs = queue.Queue()
        self.frame = None             # {"seq", "data", "width", "height", "url"} - only the latest is kept
        self.url = None
        self.disabled = False
        self.stopped = False
        self.last_pump = time.monotonic()
        self._page = None
        self._cdp = None
        self._pending_acks = []
        self._acks_lock = threading.Lock()

    # ---- owning thread only ---------------------------------------------------------------------------------
    def _disable(self, why):
        if not self.disabled:
            logger.warning("remote live view (%s) turned off: %s - everything else continues normally", self.kind, why)
        self.disabled = True
        self._stop_screencast()

    def _stop_screencast(self):
        cdp, self._cdp, self._page = self._cdp, None, None
        if cdp is not None:
            try:
                cdp.send("Page.stopScreencast")
            except Exception:
                pass
            try:
                cdp.detach()
            except Exception:
                pass
        with self._acks_lock:
            self._pending_acks = []

    def _on_frame(self, params):
        # event callback: only remembers the frame (no Playwright call here - the ack is sent by pump())
        try:
            meta = params.get("metadata") or {}
            with _LOCK:
                _SEQ[0] += 1
                self.frame = {
                    "seq": _SEQ[0],
                    "data": params.get("data"),
                    "width": meta.get("deviceWidth"),
                    "height": meta.get("deviceHeight"),
                    "url": self.url,
                }
            with self._acks_lock:
                self._pending_acks.append(params.get("sessionId"))
        except Exception as e:
            logger.warning("remote live view: a frame could not be read (%s)", e)

    def _ensure_screencast(self):
        page = None
        try:
            page = self.get_active_page()
        except Exception:
            page = None
        if page is None:
            return None
        try:
            if page.is_closed():
                return None
        except Exception:
            return None
        if page is not self._page:
            # the active page changed (new tab / popup) or this is the first pump: (re)start on it
            self._stop_screencast()
            cdp = page.context.new_cdp_session(page)
            cdp.on("Page.screencastFrame", self._on_frame)
            cdp.send("Page.startScreencast", dict(_SCREENCAST_PARAMS))
            self._cdp, self._page = cdp, page
        try:
            self.url = page.url
        except Exception:
            pass
        return page

    def _ack_frames(self):
        with self._acks_lock:
            acks, self._pending_acks = self._pending_acks, []
        for sid in acks:
            if self._cdp is None or sid is None:
                break
            self._cdp.send("Page.screencastFrameAck", {"sessionId": sid})

    def _apply_input(self, page):
        handled = 0
        while handled < 200:
            try:
                ev = self.inputs.get_nowait()
            except queue.Empty:
                break
            handled += 1
            try:
                _apply_event(page, ev)
            except Exception as e:
                logger.warning("remote live view: an input event was not applied (%s)", e)

    def pump(self):
        """One round on the owning thread: screencast on the active page, frame acks, queued input."""
        self.last_pump = time.monotonic()
        if self.disabled or self.stopped:
            return
        try:
            page = self._ensure_screencast()
            if page is None:
                return
            self._ack_frames()
            self._apply_input(page)
        except Exception as e:
            self._disable(str(e) or e.__class__.__name__)

    def stop(self):
        self.stopped = True
        try:
            self._stop_screencast()
        except Exception:
            pass


def _num(v, default=0.0):
    try:
        f = float(v)
        return f if f == f else default
    except (TypeError, ValueError):
        return default


def _apply_event(page, ev):
    """Applies one dashboard input event as real input on the page (page.mouse / page.keyboard)."""
    t = ev.get("type")
    x, y = _num(ev.get("x")), _num(ev.get("y"))
    button = ev.get("button") if ev.get("button") in _MOUSE_BUTTONS else "left"
    clicks = max(1, min(3, int(_num(ev.get("clickCount"), 1) or 1)))
    if t == "move":
        page.mouse.move(x, y)
    elif t == "down":
        page.mouse.move(x, y)
        page.mouse.down(button=button, click_count=clicks)
    elif t == "up":
        page.mouse.move(x, y)
        page.mouse.up(button=button, click_count=clicks)
    elif t == "wheel":
        page.mouse.move(x, y)
        page.mouse.wheel(_num(ev.get("dx")), _num(ev.get("dy")))
    elif t in ("keydown", "keyup"):
        key = str(ev.get("key") or "")
        if not key or len(key) > 32:
            return
        if t == "keydown":
            page.keyboard.down(key)
        else:
            page.keyboard.up(key)
    elif t == "text":
        text = str(ev.get("text") or "")
        if text and len(text) <= 64:
            page.keyboard.type(text)


# ---- owning-thread API (called from small hooks in existing code, remote mode only) -------------------------------

def start_source(kind, get_active_page):
    """Registers a live view for the calling (owning) thread. None when remote mode is off or on any error."""
    if not REMOTE_MODE:
        return None
    try:
        src = Source(kind, get_active_page)
        with _LOCK:
            _SOURCES[:] = [s for s in _SOURCES if not s.stopped]
            _SOURCES.append(src)
        return src
    except Exception as e:
        logger.warning("remote live view not started (%s)", e)
        return None


def stop_source(src):
    """Stops a live view (owning thread). Never raises."""
    if src is None:
        return
    try:
        src.stop()
        with _LOCK:
            if src in _SOURCES:
                _SOURCES.remove(src)
    except Exception as e:
        logger.warning("remote live view: stop failed (%s)", e)


def pump_for(src, seconds, stop_event=None):
    """Used by the owning thread in place of its own idle wait of `seconds`: keeps the screencast and input going
    while waiting. Ends early when stop_event is set. Waits by Playwright's own wait (so page events are delivered
    exactly as during the existing waits); falls back to a plain sleep. Never raises."""
    deadline = time.monotonic() + max(0.0, float(seconds or 0))
    while True:
        if stop_event is not None and stop_event.is_set():
            return
        try:
            src.pump()
        except Exception as e:
            logger.warning("remote live view: pump failed (%s)", e)
        left = deadline - time.monotonic()
        if left <= 0:
            return
        step = min(left, 0.04)
        page = None
        try:
            page = src.get_active_page()
            if page is not None and page.is_closed():
                page = None
        except Exception:
            page = None
        try:
            if page is not None:
                page.wait_for_timeout(step * 1000)
            elif stop_event is not None:
                stop_event.wait(step)
            else:
                time.sleep(step)
        except Exception:
            if stop_event is not None:
                stop_event.wait(step)
            else:
                time.sleep(step)


# ---- what the dashboard reads -------------------------------------------------------------------------------

def _current_source():
    now = time.monotonic()
    with _LOCK:
        live = [s for s in _SOURCES if not s.stopped and not s.disabled and now - s.last_pump < _SOURCE_STALE_S]
    return live[-1] if live else None


def _replay_frame():
    """The latest frame a running replay (separate process) wrote into its run folder, or None."""
    try:
        from executor import run_execution as _rex
        with _rex._active_replays_lock:
            dirs = [e.get("run_dir") for e in _rex._active_replays.values() if not e.get("done") and e.get("run_dir")]
        for d in reversed(dirs):
            f = Path(d) / "live_view.json"
            if f.is_file():
                return json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        logger.debug("remote live view: replay frame not readable (%s)", e)
    return None


remote_view_bp = Blueprint("remote_view", __name__)


@remote_view_bp.route("/api/remote_view/status", methods=["GET"])
def api_remote_view_status():
    try:
        if not REMOTE_MODE:
            return jsonify({"success": True, "remote": False})
        src = _current_source()
        if src is not None:
            return jsonify({"success": True, "remote": True, "active": True, "source": src.kind, "input": True,
                            "url": src.url})
        fr = _replay_frame()
        if fr:
            return jsonify({"success": True, "remote": True, "active": True, "source": "replay", "input": False,
                            "url": fr.get("url")})
        return jsonify({"success": True, "remote": True, "active": False})
    except Exception as e:
        logger.warning("remote live view: status failed (%s)", e)
        return jsonify({"success": False, "remote": REMOTE_MODE, "active": False})


@remote_view_bp.route("/api/remote_view/frame", methods=["GET"])
def api_remote_view_frame():
    """?after=<seq>: the latest frame when it is newer than <seq> (else changed: false). JSON only."""
    try:
        if not REMOTE_MODE:
            return jsonify({"success": True, "remote": False})
        try:
            after = int(request.args.get("after") or 0)
        except (TypeError, ValueError):
            after = 0
        src = _current_source()
        if src is not None:
            with _LOCK:
                fr = dict(src.frame) if src.frame else None
            source, can_input, url = src.kind, True, src.url
        else:
            fr = _replay_frame()
            source, can_input, url = "replay", False, (fr or {}).get("url")
        if not fr:
            return jsonify({"success": True, "remote": True, "active": src is not None, "changed": False,
                            "source": source if src is not None else None})
        changed = fr.get("seq") != after
        out = {"success": True, "remote": True, "active": True, "changed": changed, "seq": fr.get("seq"),
               "source": source, "input": can_input, "url": url or fr.get("url"),
               "width": fr.get("width"), "height": fr.get("height")}
        if changed:
            out["data"] = fr.get("data")
        return jsonify(out)
    except Exception as e:
        logger.warning("remote live view: frame failed (%s)", e)
        return jsonify({"success": False, "remote": REMOTE_MODE, "changed": False})


@remote_view_bp.route("/api/remote_view/input", methods=["POST"])
def api_remote_view_input():
    """{"events": [{type, x, y, button, clickCount, dx, dy, key, text}, ...]} -> queued for the owning thread."""
    try:
        if not REMOTE_MODE:
            return jsonify({"success": False, "remote": False, "message": "Remote live browser is off."})
        src = _current_source()
        if src is None:
            return jsonify({"success": False, "remote": True, "message": "No live browser to control right now."})
        data = request.get_json(silent=True) or {}
        events = data.get("events") if isinstance(data.get("events"), list) else []
        accepted = 0
        for ev in events[:200]:
            if not isinstance(ev, dict) or ev.get("type") not in ("move", "down", "up", "wheel", "keydown", "keyup", "text"):
                continue
            if src.inputs.qsize() >= _INPUT_QUEUE_MAX:
                if ev.get("type") == "move":
                    continue                     # never flood: extra mouse moves are dropped
            src.inputs.put(ev)
            accepted += 1
        return jsonify({"success": True, "remote": True, "accepted": accepted})
    except Exception as e:
        logger.warning("remote live view: input failed (%s)", e)
        return jsonify({"success": False, "remote": REMOTE_MODE, "message": "Input could not be sent."})


def recorder_active_page(recorder):
    """The page the recorder itself treats as active (its _active_page_id), else any page it still has open."""
    try:
        p = (getattr(recorder, "_pages", None) or {}).get(getattr(recorder, "_active_page_id", 0))
        if p is not None and not p.is_closed():
            return p
    except Exception:
        pass
    try:
        return recorder.get_any_open_page()
    except Exception:
        return None


def first_open_page(preferred, context):
    """`preferred` while it is open, else the first open page of `context` (Pick Element's own page choice)."""
    try:
        if preferred is not None and not preferred.is_closed():
            return preferred
    except Exception:
        pass
    try:
        pages = [p for p in context.pages if not p.is_closed()]
        return pages[0] if pages else None
    except Exception:
        return None
