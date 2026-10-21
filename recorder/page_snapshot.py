"""PAGE SNAPSHOTS for Pick Element (separate from replay).

While recording, the page the user sees right before each step is saved as a single-file MHTML snapshot
(Chromium's own page capture, CDP Page.captureSnapshot {format: "mhtml"} through a Playwright CDP session), plus
a small JSON metadata file:

    storage/snapshots/<recording name>/<step reference>.mhtml   (the page)
    storage/snapshots/<recording name>/<step reference>.json    (url, viewport, scroll, time, step reference, file)
    storage/snapshots/<recording name>/final.mhtml / final.json  (the page when the recording stopped)

The step reference is the stable one used since Phase 1: the recorded step's own timestamp (else
"<index>:<action type>"), file-name safe. A page that did not change since the previous snapshot (same address,
same DOM signature) is not written again - its metadata points at the earlier file.

Password and OTP inputs never keep a value in a saved snapshot: the value attributes are removed from the SAVED
content (the live page is never touched).

Pick Element opens a snapshot with open_snapshot_page(): the archive's HTML is served at its original address
through Playwright request routing (route.fulfill), every resource from the archive itself, every other request
aborted - and every <script> in the archive is turned off (non-executable type), inline on* handlers renamed,
meta refreshes and javascript: frames disabled. So the website's own code never runs (no redirects, no network
calls, no popups, no sign-up), while the page is an ordinary document in which the existing Pick Element overlay
is injected exactly as on a live page.

Everything here is fail-safe: any error is logged as a warning and the caller falls back to its existing
behaviour. Snapshot contents are never logged.
"""
import base64
import json
import logging
import os
import quopri
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlsplit

from storage.repository import SNAPSHOTS_DIR

logger = logging.getLogger(__name__)

# a capture slower than this turns snapshot saving off for the rest of that recording / run (never slows it down)
SNAPSHOT_CAPTURE_SLOW_S = 8.0
# a snapshot larger than this is not kept (a warning), and a recording keeps at most this much in total
SNAPSHOT_MAX_BYTES_PER_FILE = 40 * 1024 * 1024
SNAPSHOT_MAX_BYTES_PER_RECORDING = 600 * 1024 * 1024
# after a recorded action, the page is watched this long for changes (each change is captured, the last one
# before the next action is the "before next step" snapshot); a page idle longer is not captured again
RECORD_SETTLE_WINDOW_S = 8.0
FINAL_REF = "final"

_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")

# a cheap DOM signature (address, element count, markup length, title) - read only
_SIG_JS = (
    "() => { try { var b = document.body; return [location.href, document.getElementsByTagName('*').length, "
    "b ? b.innerHTML.length : 0, document.title || '', document.readyState].join('|'); } catch (e) { return null; } }"
)
_STATE_JS = (
    "() => ({ w: window.innerWidth, h: window.innerHeight, x: window.scrollX, y: window.scrollY, "
    "url: location.href, ready: document.readyState })"
)


# ---------------------------------------------------------------------------------------------------------------
# names and references
# ---------------------------------------------------------------------------------------------------------------

def safe_name(value):
    """A file-name-safe form of a recording name or step reference (same on Windows and macOS). None if empty."""
    try:
        s = _SAFE_RE.sub("-", str(value or "")).strip("-.")
        return s[:150] or None
    except Exception:
        return None


def snapshot_dir(recording_name):
    """storage/snapshots/<recording name> (None for an unusable name)."""
    n = safe_name(recording_name)
    return (SNAPSHOTS_DIR / n) if n else None


def step_ref(action, index):
    """The stable step reference (Phase 1): the recorded timestamp, else "<index>:<action type>"."""
    try:
        if isinstance(action, dict):
            if action.get("timestamp"):
                return str(action["timestamp"])
            return f"{index}:{action.get('action_type') or ''}"
    except Exception:
        pass
    return None


def recording_names(recording, file_stem=None):
    """The names a recording's snapshots may be stored under: its own name, its file name, and - for a copy saved
    by the editor ("<name>_edited") - the original recording's name (the steps keep their timestamps)."""
    out = []
    for n in ((recording or {}).get("name"), file_stem):
        n = (n or "").strip() if isinstance(n, str) else ""
        if n and n not in out:
            out.append(n)
    for n in list(out):
        if n.endswith("_edited") and n[: -len("_edited")] and n[: -len("_edited")] not in out:
            out.append(n[: -len("_edited")])
    return out


def target_ref(actions, insert_after_index):
    """The snapshot Pick Element needs for an insertion point: the page right BEFORE step insert_after_index + 2
    (1-based) - i.e. the page the existing picker reaches after replaying steps 1..insert_after_index+1 - or the
    final page when that is past the last step. Returns (ref, step_number or None)."""
    acts = actions if isinstance(actions, list) else []
    k = max(0, int(insert_after_index) + 1)
    if k >= len(acts):
        return FINAL_REF, None
    return step_ref(acts[k], k + 1), k + 1


def find_snapshot(recording, file_stem, ref):
    """The saved snapshot for ref: its metadata plus "path" (the .mhtml file), or None. Never raises."""
    try:
        sref = safe_name(ref)
        if not sref:
            return None
        for name in recording_names(recording, file_stem):
            d = snapshot_dir(name)
            if d is None:
                continue
            meta_path = d / f"{sref}.json"
            if not meta_path.is_file():
                continue
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            f = d / str(meta.get("file") or "")
            if meta.get("file") and f.is_file():
                meta["path"] = str(f)
                return meta
    except Exception as e:
        logger.warning("snapshot lookup failed (%s) - using the existing Pick Element", e)
    return None


def has_snapshot(recording_name, ref):
    """True when a snapshot for ref is stored under recording_name. Never raises."""
    try:
        d = snapshot_dir(recording_name)
        sref = safe_name(ref)
        return bool(d and sref and (d / f"{sref}.json").is_file())
    except Exception:
        return False


def delete_snapshots(recording_name):
    """Removes storage/snapshots/<recording name> (all its snapshots). Returns the removed path or None."""
    import shutil
    d = snapshot_dir(recording_name)
    if d is not None and d.is_dir():
        shutil.rmtree(d)
        return d
    return None


# ---------------------------------------------------------------------------------------------------------------
# MHTML (MIME multipart) parts - a minimal reader that keeps every byte it does not change
# ---------------------------------------------------------------------------------------------------------------

def _split_header_body(blob):
    for sep in (b"\r\n\r\n", b"\n\n"):
        i = blob.find(sep)
        if i != -1:
            return blob[:i], blob[i + len(sep):], sep
    return blob, b"", b"\r\n\r\n"


def _headers(header_bytes):
    """{lower-case name: value} of a MIME header block (folded lines joined)."""
    out = {}
    text = header_bytes.decode("latin-1")
    text = re.sub(r"\r?\n[ \t]+", " ", text)
    for line in re.split(r"\r?\n", text):
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip().lower()] = v.strip()
    return out


def _parts(raw):
    """(boundary, [(start, end)]) - the byte span of each MIME part's content (headers + body), between the
    boundary lines. ([], ...) when this is not a multipart archive."""
    head, _body, _sep = _split_header_body(raw)
    m = re.search(rb'boundary="?([^";\r\n]+)"?', head, re.I)
    if not m:
        return None, []
    delim = b"--" + m.group(1)
    spans = []
    pos = raw.find(delim, len(head))
    while pos != -1:
        start = pos + len(delim)
        if raw[start:start + 2] == b"--":
            break                                    # the closing boundary
        # the part starts after the line break that ends the boundary line
        nl = raw.find(b"\n", start)
        if nl == -1:
            break
        start = nl + 1
        nxt = raw.find(b"\n" + delim, start)
        if nxt == -1:
            break
        end = nxt
        if end > start and raw[end - 1:end] == b"\r":
            end -= 1
        spans.append((start, end))
        pos = nxt + 1
    return m.group(1), spans


def _decode_body(headers, body):
    enc = (headers.get("content-transfer-encoding") or "").strip().lower()
    if enc == "quoted-printable":
        return quopri.decodestring(body)
    if enc == "base64":
        return base64.b64decode(re.sub(rb"\s+", b"", body) + b"===")
    return body


def _encode_base64_part(header_bytes, sep, data):
    """The part re-written with a base64 body (the only header changed: Content-Transfer-Encoding)."""
    hb = header_bytes
    if re.search(rb"(?im)^content-transfer-encoding:", hb):
        hb = re.sub(rb"(?im)^(content-transfer-encoding:)[^\r\n]*", rb"\1 base64", hb)
    else:
        hb = hb + b"\r\nContent-Transfer-Encoding: base64"
    b64 = base64.b64encode(data)
    lines = b"\r\n".join(b64[i:i + 76] for i in range(0, len(b64), 76))
    return hb + sep + lines


def _rewrite_html_parts(raw, fn):
    """Applies fn(html_bytes) -> (new_bytes, changes) to every HTML part of the archive; parts fn does not change
    keep their exact bytes. Returns (new_raw, total_changes)."""
    _b, spans = _parts(raw)
    if not spans:
        return raw, 0
    out, last, total = [], 0, 0
    for start, end in spans:
        content = raw[start:end]
        hb, body, sep = _split_header_body(content)
        h = _headers(hb)
        ctype = (h.get("content-type") or "").lower()
        if "text/html" in ctype or "application/xhtml" in ctype:
            try:
                html = _decode_body(h, body)
                new_html, n = fn(html)
                if n:
                    out.append(raw[last:start])
                    out.append(_encode_base64_part(hb, sep, new_html))
                    last = end
                    total += n
            except Exception as e:
                logger.warning("snapshot: an HTML part could not be processed (%s) - kept as it is", e)
    out.append(raw[last:])
    return b"".join(out), total


# ---------------------------------------------------------------------------------------------------------------
# masking (save time): password and OTP inputs keep no value
# ---------------------------------------------------------------------------------------------------------------

_INPUT_TAG_RE = re.compile(rb"<input\b[^>]*>", re.I)
_VALUE_ATTR_RE = re.compile(rb"""(\svalue\s*=\s*)("[^"]*"|'[^']*'|[^\s>]+)""", re.I)
_OTP_WORDS = {"otp", "otps", "passcode", "totp", "2fa", "mfa", "pin", "onetimecode"}
_OTP_PHRASES = ("one time", "verification code", "verify code", "security code", "auth code",
                "authentication code", "confirmation code", "sms code", "access code")
_TEXTISH = ("", "text", "tel", "number", "password", "search")


def _attr(tag, name):
    m = re.search(rb"\s" + name + rb"""\s*=\s*("([^"]*)"|'([^']*)'|([^\s>]+))""", tag, re.I)
    if not m:
        return None
    v = m.group(2) if m.group(2) is not None else (m.group(3) if m.group(3) is not None else m.group(4))
    return (v or b"").decode("latin-1").strip().lower()


def _is_sensitive_input(tag):
    """A password field or a one-time-code field (generic signals only)."""
    itype = _attr(tag, b"type") or ""
    if itype == "password":
        return True
    if itype not in _TEXTISH:
        return False
    ac = _attr(tag, b"autocomplete") or ""
    if "one-time-code" in ac:
        return True
    texts = " ".join(t for t in (_attr(tag, b"name"), _attr(tag, b"id"), _attr(tag, b"placeholder"),
                                 _attr(tag, b"aria-label"), ac) if t)
    words = [w for w in re.split(r"[^a-z0-9]+", texts) if w]
    if any(w in _OTP_WORDS for w in words):
        return True
    flat = " " + " ".join(words) + " "
    if any((" " + p + " ") in flat for p in _OTP_PHRASES):
        return True
    maxlen = _attr(tag, b"maxlength") or ""
    if maxlen == "1":
        return True                                  # one box of a split one-time code
    if (_attr(tag, b"inputmode") or "") == "numeric" and maxlen.isdigit() and 4 <= int(maxlen) <= 8:
        return True
    return False


def _mask_html(html):
    count = [0]

    def _tag(m):
        tag = m.group(0)
        if not _is_sensitive_input(tag):
            return tag
        new = _VALUE_ATTR_RE.sub(lambda v: v.group(1) + b'""', tag)
        if new != tag:
            count[0] += 1
        return new

    return _INPUT_TAG_RE.sub(_tag, html), count[0]


def mask_mhtml(raw):
    """The archive with every password / OTP input's value removed (the live page is never touched)."""
    return _rewrite_html_parts(raw, _mask_html)


# ---------------------------------------------------------------------------------------------------------------
# capture + store
# ---------------------------------------------------------------------------------------------------------------

def capture_page(page):
    """(masked MHTML bytes, page state) of the page as it is now - Chromium's own page snapshot through a CDP
    session (read only). Raises on failure (callers catch)."""
    state = page.evaluate(_STATE_JS) or {}
    cdp = page.context.new_cdp_session(page)
    try:
        res = cdp.send("Page.captureSnapshot", {"format": "mhtml"})
    finally:
        try:
            cdp.detach()
        except Exception:
            pass
    data = (res or {}).get("data")
    if not data:
        raise RuntimeError("the browser returned an empty page snapshot")
    raw = data.encode("utf-8", errors="surrogateescape")
    masked, _n = mask_mhtml(raw)
    return masked, state


def _atomic_write(path, data):
    tmp = path.with_name(path.name + ".tmp")
    if isinstance(data, str):
        tmp.write_text(data, encoding="utf-8")
    else:
        tmp.write_bytes(data)
    os.replace(tmp, path)


def write_meta(folder, ref, file_name, state, extra=None):
    meta = {
        "step_ref": ref,
        "file": file_name,
        "url": (state or {}).get("url"),
        "viewport": {"width": (state or {}).get("w"), "height": (state or {}).get("h")},
        "scroll": {"x": (state or {}).get("x"), "y": (state or {}).get("y")},
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }
    meta.update(extra or {})
    _atomic_write(folder / f"{safe_name(ref)}.json", json.dumps(meta, indent=2))
    return meta


def save_missing_step_snapshot(page, recording_name, ref, source):
    """Saves the snapshot for ref from `page` when that recording has none yet (Pick Element's replay fallback,
    a full replay). Same masking / storage rules as recording. Returns True when one was written. Never raises."""
    try:
        folder = snapshot_dir(recording_name)
        sref = safe_name(ref)
        if folder is None or not sref or (folder / f"{sref}.json").is_file():
            return False
        t0 = time.monotonic()
        data, state = capture_page(page)
        if len(data) > SNAPSHOT_MAX_BYTES_PER_FILE:
            logger.warning("snapshot for a step not saved - the page snapshot is too large")
            return False
        folder.mkdir(parents=True, exist_ok=True)
        _atomic_write(folder / f"{sref}.mhtml", data)
        write_meta(folder, ref, f"{sref}.mhtml", state, {"source": source})
        print(f"[snapshot] saved the missing page snapshot for step {ref} ({source}, {time.monotonic() - t0:.1f}s)",
              flush=True)
        return True
    except Exception as e:
        logger.warning("snapshot for step %s not saved (%s) - nothing else changes", ref, e)
        return False


def _parse_ts(ts):
    try:
        s = str(ts).strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        d = datetime.fromisoformat(s)
        return d.timestamp()
    except Exception:
        return None


class RecordingSnapshotter:
    """Saves page snapshots while recording. tick() is called from the recording session's own polling loop (the
    thread that owns the recording browser, never from a page callback), so it never runs inside a recorded
    action's handling and never changes what is recorded. After each recorded action the active page is watched
    for RECORD_SETTLE_WINDOW_S: every time its DOM signature changes it is captured again (only the latest capture
    of that quiet period is kept), so the last capture before the next action is the page as the user saw it right
    before that step. finalize() then assigns, by time, each step the latest capture taken completely before it.
    Any error, or a capture slower than SNAPSHOT_CAPTURE_SLOW_S, turns snapshots off for this recording (a
    warning) - recording itself is never affected."""

    def __init__(self, recorder, recording_name):
        self.recorder = recorder
        self.folder = snapshot_dir(recording_name)
        self.enabled = self.folder is not None
        self.captures = []          # {"file", "t0", "t1", "sig", "state", "page_id"}
        self._last_sig = None
        self._seen = -1
        self._last_change = time.monotonic()
        self._seq = 0
        self._bytes = 0
        self._warned = False

    def _off(self, why):
        if self.enabled:
            print(f"[snapshot] WARNING: page snapshots are off for the rest of this recording - {why}. "
                  f"Recording continues normally.", flush=True)
        self.enabled = False

    def _action_count(self):
        try:
            return len(self.recorder.actions) + len(getattr(self.recorder, "_prestart_buffer", None) or [])
        except Exception:
            return 0

    def _active_page(self):
        try:
            pid = getattr(self.recorder, "_active_page_id", 0)
            p = (getattr(self.recorder, "_pages", None) or {}).get(pid)
            if p is not None and not p.is_closed():
                return p, pid
        except Exception:
            pass
        try:
            p = self.recorder.get_any_open_page()
            return p, (self.recorder._page_id_for(p) if p is not None else None)
        except Exception:
            return None, None

    def tick(self, force=False):
        if not self.enabled:
            return
        try:
            n = self._action_count()
            if n != self._seen:
                self._seen = n
                self._last_change = time.monotonic()
                self._last_sig = None          # a new step: a new quiet period starts
            if not force and time.monotonic() - self._last_change > RECORD_SETTLE_WINDOW_S:
                return
            page, pid = self._active_page()
            if page is None:
                return
            sig = page.evaluate(_SIG_JS)
            if not sig or (sig.endswith("|loading") and not force):
                return
            if sig == self._last_sig and not force:
                return
            self._last_sig = sig
            base = sig.rsplit("|", 1)[0]       # address + DOM signature (without the load state)
            last = self.captures[-1] if self.captures else None
            if last is not None and last["sig_base"] == base:
                # the page did not change since the previous snapshot: reference that file, no new one
                now = time.time()
                if last["period"] == n and not force:
                    last["t1"] = now
                else:
                    self.captures.append(dict(last, t0=now, t1=now, period=n))
                return
            if self._bytes >= SNAPSHOT_MAX_BYTES_PER_RECORDING:
                self._off("the recording reached its snapshot disk budget")
                return
            t0 = time.time()
            m0 = time.monotonic()
            data, state = capture_page(page)
            took = time.monotonic() - m0
            t1 = time.time()
            if len(data) > SNAPSHOT_MAX_BYTES_PER_FILE:
                logger.warning("a page snapshot was skipped - too large")
                return
            self.folder.mkdir(parents=True, exist_ok=True)
            self._seq += 1
            name = f"_cap_{self._seq:05d}.mhtml"
            _atomic_write(self.folder / name, data)
            self._bytes += len(data)
            self.captures.append({"file": name, "t0": t0, "t1": t1, "sig_base": base, "state": state,
                                  "page_id": pid, "period": n, "size": len(data)})
            # the same quiet period (no new step in between): only its two latest captures are kept - the latest
            # is normally the "before next step" page; the one before it covers a step made in the instant
            # between that capture and Python learning about the step
            same = [c for c in self.captures if c["period"] == n]
            for old in same[:-2]:
                self.captures.remove(old)
                if not any(c["file"] == old["file"] for c in self.captures):
                    try:
                        (self.folder / old["file"]).unlink()
                        self._bytes -= int(old.get("size") or 0)
                    except Exception:
                        pass
            if took > SNAPSHOT_CAPTURE_SLOW_S:
                self._off(f"one page snapshot took {took:.1f}s")
        except Exception as e:
            if not self._warned:
                self._warned = True
                logger.warning("page snapshot not saved (%s) - recording continues normally", e)

    def capture_final(self):
        """The final page, right before the recording stops (when a page is still open)."""
        self.tick(force=True)

    def finalize(self, actions):
        """Assigns snapshots to the saved steps (by time) and writes their metadata; removes captures no step
        uses. Never raises."""
        if self.folder is None or not self.captures:
            return
        try:
            caps = sorted(self.captures, key=lambda c: c["t0"])
            used = {}

            def _assign(ref, cap):
                if cap["file"] not in used:
                    used[cap["file"]] = safe_name(ref)
                write_meta(self.folder, ref, cap["file"], cap["state"],
                           {"page_id": cap.get("page_id"), "captured_at": datetime.fromtimestamp(cap["t0"]).isoformat(timespec="seconds"),
                            "source": "recording"})

            prev_t = None
            acts = actions if isinstance(actions, list) else []
            for k, a in enumerate(acts, start=1):
                ref = step_ref(a, k)
                t = _parse_ts((a or {}).get("timestamp"))
                if t is None or not ref:
                    continue
                cands = [c for c in caps if c["t1"] <= t and (prev_t is None or c["t0"] >= prev_t)]
                if cands:
                    _assign(ref, cands[-1])
                prev_t = t
            last_t = prev_t
            finals = [c for c in caps if last_t is None or c["t0"] >= last_t]
            if finals:
                _assign(FINAL_REF, finals[-1])
            # each used capture is renamed to the first step that uses it; the others' metadata points at it
            renames = {}
            for f, ref_name in used.items():
                target = f"{ref_name}.mhtml"
                try:
                    os.replace(self.folder / f, self.folder / target)
                    renames[f] = target
                except Exception:
                    renames[f] = f
            for meta_path in self.folder.glob("*.json"):
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    if meta.get("file") in renames:
                        meta["file"] = renames[meta["file"]]
                        _atomic_write(meta_path, json.dumps(meta, indent=2))
                except Exception:
                    pass
            for c in caps:
                if c["file"] not in used:
                    try:
                        (self.folder / c["file"]).unlink()
                    except Exception:
                        pass
            print(f"[snapshot] {len(used)} page snapshot(s) saved for this recording "
                  f"({sum(1 for _ in self.folder.glob('*.json'))} step reference(s))", flush=True)
        except Exception as e:
            logger.warning("page snapshots could not be finalized (%s) - Pick Element will replay instead", e)


# ---------------------------------------------------------------------------------------------------------------
# opening a snapshot (Pick Element): served at its own address, the website's scripts off
# ---------------------------------------------------------------------------------------------------------------

_SCRIPT_OPEN_RE = re.compile(rb"<script\b", re.I)
_TAG_RE = re.compile(rb"<[A-Za-z][^>]*>")
_ON_ATTR_RE = re.compile(rb"(\s)(on[a-z]+\s*=)", re.I)
_REFRESH_RE = re.compile(rb"""\shttp-equiv\s*=\s*(["']?)refresh\1""", re.I)
_JS_SRC_RE = re.compile(rb"""(\s)(src\s*=\s*["']?\s*javascript:)""", re.I)
_CID_SRC_RE = re.compile(rb"""(\s(?:src|href)\s*=\s*["'])cid:([^"']+)(["'])""", re.I)
PART_PREFIX = "/__afqa_snapshot_part__/"


def _neutralize_html(html, origin):
    """The website's scripts turned off: every <script> becomes a non-executable type (the element itself stays,
    so the DOM structure and element positions are unchanged), inline on* handlers are renamed (data-afqa-on...),
    meta refreshes and javascript: frame sources disabled; cid: frame references point at the archive route."""
    html = _SCRIPT_OPEN_RE.sub(b'<script type="text/x-afqa-disabled"', html)

    def _tag(m):
        t = m.group(0)
        t = _ON_ATTR_RE.sub(rb"\1data-afqa-\2", t)
        t = _REFRESH_RE.sub(b' data-afqa-http-equiv="refresh"', t)
        t = _JS_SRC_RE.sub(rb"\1data-afqa-\2", t)
        return t

    html = _TAG_RE.sub(_tag, html)
    html = _CID_SRC_RE.sub(lambda m: m.group(1) + (origin + PART_PREFIX + quote(m.group(2).decode("latin-1"), safe="")).encode("latin-1") + m.group(3), html)
    return html


def load_archive(path):
    """{"main_url", "resources": {url: (content_type, bytes)}} from a saved snapshot; HTML parts neutralized."""
    raw = Path(path).read_bytes()
    head, _b, _s = _split_header_body(raw)
    top = _headers(head)
    _bnd, spans = _parts(raw)
    if not spans:
        raise RuntimeError("not a page snapshot archive")
    main_url = (top.get("snapshot-content-location") or "").strip()
    resources = {}
    first_html = None
    origin = None
    if main_url:
        u = urlsplit(main_url)
        origin = f"{u.scheme}://{u.netloc}"
    parsed = []
    for start, end in spans:
        hb, body, _sep = _split_header_body(raw[start:end])
        h = _headers(hb)
        parsed.append((h, body))
        if first_html is None and "text/html" in (h.get("content-type") or "").lower():
            first_html = h.get("content-location")
    if not main_url:
        main_url = first_html or ""
        u = urlsplit(main_url)
        origin = f"{u.scheme}://{u.netloc}"
    if not main_url.lower().startswith(("http://", "https://")):
        raise RuntimeError("the snapshot has no web address to open it at")
    for h, body in parsed:
        ctype = h.get("content-type") or "application/octet-stream"
        data = _decode_body(h, body)
        if "text/html" in ctype.lower() or "application/xhtml" in ctype.lower():
            data = _neutralize_html(data, origin)
        keys = []
        loc = (h.get("content-location") or "").strip()
        if loc:
            keys.append(loc.split("#", 1)[0])
        cid = (h.get("content-id") or "").strip().strip("<>")
        for c in [cid, loc[4:] if loc.lower().startswith("cid:") else ""]:
            if c:
                keys.append(origin + PART_PREFIX + quote(c, safe=""))
        for k in keys:
            resources.setdefault(k, (ctype, data))
    return {"main_url": main_url, "resources": resources}


def open_snapshot_page(context, archive, scroll=None, timeout_ms=15000):
    """Opens the archive in a new page of `context` (its own browser context): every request is answered from
    the archive or aborted (no network), website scripts are never fetched. Returns the page, ready for the
    existing Pick Element overlay. Raises on failure (the caller closes it and falls back)."""
    resources = archive["resources"]
    main_url = archive["main_url"]

    def _handle(route):
        try:
            req = route.request
            if req.resource_type == "script":
                route.abort()
                return
            hit = resources.get(req.url.split("#", 1)[0])
            if hit is None:
                route.abort()
                return
            route.fulfill(status=200, headers={"content-type": hit[0]}, body=hit[1])
        except Exception:
            try:
                route.abort()
            except Exception:
                pass

    context.route("**/*", _handle)
    page = context.new_page()
    page.set_default_timeout(8000)
    page.goto(main_url, wait_until="load", timeout=timeout_ms)
    try:
        page.evaluate("(s) => window.scrollTo(s.x || 0, s.y || 0)", {"x": (scroll or {}).get("x") or 0,
                                                                   "y": (scroll or {}).get("y") or 0})
    except Exception:
        pass
    # the page must be a working document the overlay can be injected into
    page.wait_for_function("() => !!(document.body || document.documentElement)", timeout=5000)
    return page
