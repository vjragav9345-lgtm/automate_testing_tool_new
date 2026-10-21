"""Single point of truth for reading/writing JSON records.

Everything is flat files for now. Keeping all the I/O behind these
functions means if this ever moves to a real DB, only this file changes.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
RECORDINGS_DIR = BASE_DIR / "storage" / "recordings"
EDITED_RECORDINGS_DIR = RECORDINGS_DIR / "edited"
TRIMMED_RECORDINGS_DIR = RECORDINGS_DIR / "trimmed"
EXECUTIONS_DIR = BASE_DIR / "storage" / "executions"
SEARCHES_DIR = BASE_DIR / "storage" / "searches"
SNAPSHOTS_DIR = BASE_DIR / "storage" / "snapshots"

for d in (RECORDINGS_DIR, EDITED_RECORDINGS_DIR, TRIMMED_RECORDINGS_DIR, EXECUTIONS_DIR, SEARCHES_DIR, SNAPSHOTS_DIR):
    d.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + f".tmp{os.getpid()}")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False, default=str)
    os.replace(tmp_path, path)


def _read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_recording(test_case: dict) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = test_case.get("name") or f"session_{ts}"
    path = RECORDINGS_DIR / f"{name}.json"
    test_case["name"] = name
    test_case["saved_at"] = datetime.now().isoformat()
    _write_json(path, test_case)
    logger.info("saved recording to %s", path)
    return path


def save_edited_recording(test_case: dict) -> Path:
    """Same as save_recording(), but writes into storage/recordings/edited/
    so a saved edit never overwrites, or even sits alongside, the original
    recording it was derived from."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = test_case.get("name") or f"session_{ts}"
    path = EDITED_RECORDINGS_DIR / f"{name}.json"
    test_case["name"] = name
    test_case["saved_at"] = datetime.now().isoformat()
    _write_json(path, test_case)
    logger.info("saved edited recording to %s", path)
    return path


def set_display_name(path: str, display_name: str) -> Path:
    """PHASE 2: sets (or, given an empty/whitespace-only string, clears)
    the recording's own display_name field IN PLACE - never touches the
    filename, "name", or anything else already in the file, so every
    existing path/link/report that references this recording keeps
    working exactly as before. Used by both the "Name this test" modal
    (right after a recording finishes) and the Rename action on the
    dashboard card / editor header.
    """
    p = Path(path)
    if not p.is_absolute():
        candidate = BASE_DIR / "storage" / p
        p = candidate if candidate.exists() else BASE_DIR / p
    data = _read_json(p)
    cleaned = (display_name or "").strip()
    data["display_name"] = cleaned or None
    _write_json(p, data)
    logger.info("set display_name for %s to %r", p, cleaned or None)
    return p


def is_auto_created_validation(action: dict) -> bool:
    """True for a validation step the RECORDER created on its own (never the
    user). The only such step the recorder ever produced in this codebase is
    the "expect field value" step for a value the PAGE put in a text box
    (validate_value + value_source == "page"). A step the user added in the
    editor carries origin == "added" / added_by == "user" and is never
    matched. Any other validation step in an old recording cannot be told
    apart reliably and is left untouched."""
    return (
        isinstance(action, dict)
        and action.get("action_type") == "validate_value"
        and action.get("value_source") == "page"
        and action.get("origin") != "added"
        and action.get("added_by") != "user"
    )


def strip_auto_created_validations(test_case: dict) -> dict:
    """In-memory only (nothing on disk is rewritten here): drops every
    recorder-created validation step (see is_auto_created_validation) and
    marks each validation step the user added with added_by="user", so the
    editor and replay only ever see real recorded actions plus the user's
    own validations. Returns test_case; the number dropped is stored in
    test_case["auto_validations_skipped"] only when it is non-zero."""
    actions = test_case.get("actions")
    if not isinstance(actions, list):
        return test_case
    kept, dropped = [], 0
    for a in actions:
        if is_auto_created_validation(a):
            dropped += 1
            continue
        if isinstance(a, dict) and str(a.get("action_type") or "").startswith("validate") and a.get("origin") == "added":
            a.setdefault("added_by", "user")
        kept.append(a)
    if dropped:
        test_case["actions"] = kept
        test_case["auto_validations_skipped"] = dropped
        logger.info("skipped %d recorder-created validation step(s) in %s", dropped, test_case.get("name"))
    return test_case


_URL_ACTIONS = ("click", "dblclick", "right_click", "check", "press", "submit", "select")


def _navigate_is_history_like(actions, j) -> bool:
    """actions[j] is a Navigate that is (most likely) a Back / Forward press, not the effect of the
    action before it: the recorder marked it (history), or its page is one the recording already
    visited earlier (the page of any earlier step, or where an earlier action led). A change of only
    the fragment of the page the previous action was on is that action's own effect, never a press."""
    from urllib.parse import urlsplit
    nav = actions[j]
    if nav.get("history"):
        return True
    url = nav.get("page_url")
    if not url:
        return False
    try:
        nu = urlsplit(url)
        if j > 0 and isinstance(actions[j - 1], dict) and actions[j - 1].get("page_url"):
            pu = urlsplit(actions[j - 1]["page_url"])
            if (nu.scheme, nu.netloc, nu.path, nu.query) == (pu.scheme, pu.netloc, pu.path, pu.query) and nu.fragment != pu.fragment:
                return False
    except Exception:
        pass
    key = _norm_cmp_url(url)
    for k in range(0, j):
        st = actions[k]
        if not isinstance(st, dict):
            continue
        for u in (st.get("page_url"), st.get("expected_url")):
            if u and _norm_cmp_url(u) == key:
                return True
    return False


def migrate_expected_urls(test_case: dict) -> dict:
    """I1-d (in memory, idempotent, nothing on disk is rewritten): folds a
    Navigate step that IMMEDIATELY follows a user action (before the next
    user action) into that action as its expected_url - where the action
    LEADS - with every URL of the redirect run as expected_url_chain. The
    Navigate step itself stays in the list (the original fields are kept for
    audit and step numbering does not shift), marked induced_by_prev=True and
    given caused_by_timestamp = the action's timestamp, so replay treats it
    as already satisfied by the action's own navigation (the existing
    verify-only look-ahead) instead of re-navigating. An action's own
    page_url is never its expectation. Older recordings therefore replay
    unchanged; nothing requires re-recording."""
    actions = test_case.get("actions")
    if not isinstance(actions, list):
        return test_case
    n = len(actions)
    for i, a in enumerate(actions):
        if not isinstance(a, dict) or a.get("action_type") not in _URL_ACTIONS or a.get("expected_url"):
            continue
        run = []
        j = i + 1
        while (
            j < n and isinstance(actions[j], dict) and actions[j].get("action_type") == "navigate"
            # only a navigation the RECORDER produced as the action's effect
            # (it carries caused_by_timestamp and/or delay_before_ms) - never
            # one added by hand in the editor, which is its own step
            and (actions[j].get("caused_by_timestamp") or actions[j].get("delay_before_ms") is not None)
            and actions[j].get("origin") != "added"
            # a Back / Forward press is its own step: where it landed is never where the action led
            and not _navigate_is_history_like(actions, j)
        ):
            run.append(actions[j])
            j += 1
        urls = [r.get("page_url") for r in run if r.get("page_url")]
        if not urls:
            continue
        a["expected_url"] = urls[0]
        a["expected_url_chain"] = urls
        a["migrated_expected_url"] = True
        for r in run:
            r["induced_by_prev"] = True
            if not r.get("caused_by_timestamp") and a.get("timestamp"):
                r["caused_by_timestamp"] = a.get("timestamp")
    return test_case


def _norm_cmp_url(u):
    """URL used only to COMPARE two recorded URLs: no fragment, no trailing
    slash, www == non-www, tracking params dropped, query sorted."""
    from urllib.parse import urlsplit, parse_qsl
    try:
        sp = urlsplit(u or "")
    except Exception:
        return u or ""
    host = (sp.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    q = sorted(
        (k, v) for k, v in parse_qsl(sp.query, keep_blank_values=True)
        if not (k.lower().startswith("utm_") or k.lower() in ("gclid", "fbclid", "msclkid", "_ga", "_gl"))
    )
    return f"{host}{sp.path.rstrip('/')}?{q}"


def repair_misattached_expected_urls(test_case: dict) -> dict:
    """In memory, idempotent. Older recordings attached a navigation to the
    LATEST click when the navigation event was finally handled, not to the
    click that caused it. Such an action carries an expected_url whose first
    hop is the very page the action itself was already recorded on (it could
    not have caused arriving there). That first hop is moved to the
    preceding click-type action when that one was made on a different page;
    otherwise it is dropped (a wrong expectation is worse than none).
    Recordings made after the recorder fix never match this."""
    actions = test_case.get("actions")
    if not isinstance(actions, list):
        return test_case
    for i, a in enumerate(actions):
        if not isinstance(a, dict) or a.get("migrated_expected_url") or a.get("expected_url_repaired"):
            continue
        chain = a.get("expected_url_chain")
        if not a.get("expected_url") or not isinstance(chain, list) or not chain:
            continue
        if not a.get("page_url") or _norm_cmp_url(chain[0]) != _norm_cmp_url(a.get("page_url")):
            continue
        prev = actions[i - 1] if i > 0 else None
        if (
            isinstance(prev, dict) and prev.get("action_type") in ("click", "dblclick", "right_click", "check", "press", "submit")
            and _norm_cmp_url(prev.get("page_url")) != _norm_cmp_url(chain[0])
        ):
            if not prev.get("expected_url"):
                prev["expected_url"] = chain[0]
                prev["expected_url_chain"] = [chain[0]]
            prev["expected_url_repaired"] = True
        a["original_expected_url_chain"] = list(chain)
        rest = chain[1:]
        a["expected_url_chain"] = rest or None
        a["expected_url"] = rest[0] if rest else None
        a["expected_url_repaired"] = True
    return test_case


_INTERACTIVE_TAGS = ("a", "button", "summary", "input", "select", "textarea", "label", "option")
_INTERACTIVE_ROLES = ("menuitem", "button", "tab", "link", "menuitemcheckbox", "option", "switch")


def _lp_is_container(lp, bbox) -> bool:
    """A recorded hover target that is a big non-interactive container whose
    label is its children's text concatenated - never a real trigger."""
    if not isinstance(lp, dict):
        return False
    attrs = lp.get("attributes") if isinstance(lp.get("attributes"), dict) else {}
    tag = (lp.get("tag") or "").lower()
    if tag in _INTERACTIVE_TAGS or (lp.get("role") or attrs.get("role")) in _INTERACTIVE_ROLES:
        return False
    if any(k in attrs for k in ("aria-haspopup", "aria-expanded", "tabindex", "onclick")):
        return False
    text = (lp.get("text") or lp.get("element_text") or "")
    area = 0
    if isinstance(bbox, dict):
        area = (bbox.get("width") or 0) * (bbox.get("height") or 0)
    return "\n" in text.strip() or area > 40000 or len(text) > 80


def normalize_reveal_steps(test_case: dict) -> dict:
    """In memory, idempotent; nothing on disk is rewritten.
    A hover recorded on a big non-interactive container (the revealed PANEL,
    labelled with its children's concatenated text) is not a real step: it is
    kept for audit, flagged reveal_only_container, and replay lets the NEXT
    step's own reveal logic find the real trigger. The same containers are
    removed from the next click's hover_chain. A real click is NEVER changed
    into a hover or dropped. Original fields are always kept."""
    actions = test_case.get("actions")
    if not isinstance(actions, list):
        return test_case
    for k, a in enumerate(actions):
        if not isinstance(a, dict):
            continue
        if a.get("action_type") == "hover" and not a.get("reveal_only_container"):
            if k + 1 < len(actions) and _lp_is_container(a.get("locator_profile"), a.get("bounding_box")):
                a["reveal_only_container"] = True
        if a.get("hover_chain") and not a.get("hover_chain_filtered"):
            keep = [h for h in a["hover_chain"] if not _lp_is_container(h, None)]
            if len(keep) != len(a["hover_chain"]):
                a["original_hover_chain"] = a["hover_chain"]
                a["hover_chain"] = keep or None
            a["hover_chain_filtered"] = True
    return test_case


def migrate_recording(test_case: dict) -> dict:
    """Every load-time, in-memory migration, in order (all idempotent)."""
    test_case = strip_auto_created_validations(test_case)
    test_case = repair_misattached_expected_urls(test_case)
    test_case = migrate_expected_urls(test_case)
    return normalize_reveal_steps(test_case)


def load_recording(path: str) -> dict:
    p = Path(path)
    if not p.is_absolute():
        # allow both "recordings/foo.json" and "foo.json"
        candidate = BASE_DIR / "storage" / p
        p = candidate if candidate.exists() else BASE_DIR / p
    return migrate_recording(_read_json(p))


def list_recordings() -> list:
    """Lists BOTH original recordings and their edited versions (if any),
    each as its own entry - list_recordings() re-reads every file from
    disk on every call, so whatever was most recently saved (original or
    edited) is always what gets returned here. There's no in-memory cache
    to go stale: the Dashboard just needs to call this again (which it
    already does on every page load) to see the latest edit.
    """
    out = []
    for directory, rel_prefix in (
        (RECORDINGS_DIR, "storage/recordings"),
        (EDITED_RECORDINGS_DIR, "storage/recordings/edited"),
        (TRIMMED_RECORDINGS_DIR, "storage/recordings/trimmed"),
    ):
        for f in directory.glob("*.json"):
            try:
                data = _read_json(f)
                out.append({
                    "name": data.get("name", f.stem),
                    "timestamp": data.get("saved_at", ""),
                    "step_count": len(data.get("actions", [])),
                    "path": f"{rel_prefix}/{f.name}",
                    # PHASE 2: absent (None) on any recording saved before
                    # this existed - the dashboard/editor fall back to
                    # showing "name" exactly as they always have whenever
                    # this is None, so an old recording looks unchanged.
                    "display_name": data.get("display_name"),
                })
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("skipping unreadable recording %s: %s", f, e)

    out.sort(key=lambda r: r["timestamp"], reverse=True)
    return out


def save_execution(result: dict) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = EXECUTIONS_DIR / f"execution_{ts}.json"
    _write_json(path, result)
    return path


def save_search(result: dict) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = SEARCHES_DIR / f"search_{ts}.json"
    _write_json(path, result)
    return path


def recover_orphaned_drafts() -> list:
    """FIX 5/FIX 6 (crash recovery): a recording session's append-only
    JSONL sidecar (recorder/record_session.py's Recorder._flush_draft)
    has every action captured, one per line, the instant it happens -
    including ones a crash prevented the periodic full-JSON consolidation
    from ever writing, and even a session that crashed before its FIRST
    consolidation, which leaves a sidecar with no matching .json at all.
    Normally that sidecar is deleted the moment a recording finishes and
    saves successfully (see app.py's _finish_recording) - one still
    sitting here means the process that owned it never reached that
    point (killed, crashed, power loss), and everything it captured would
    otherwise be silently lost.

    Called at app startup and again right before a NEW recording session
    starts (see Recorder.start()) - either one is "the next launch" this
    exists for. Reconciles every orphaned sidecar it finds into a
    complete, saved recording (tagged recovered=True so it's obviously
    distinguishable from a normally-finished one) and only removes the
    sidecar once that save has actually succeeded - a save failure here
    leaves the sidecar in place so the NEXT launch/call gets another
    chance at it rather than losing the only remaining copy.

    Only ever safe to call when nothing is actively recording (both call
    sites satisfy this: app startup has no session yet, and this runs
    before the new session's own sidecar is created) - a sidecar
    belonging to a still-running recording would otherwise race with that
    session's own in-progress appends.

    Returns the list of recovered recording paths (empty when there was
    nothing to recover).
    """
    recovered_paths = []
    for jsonl_path in sorted(RECORDINGS_DIR.glob("*.draft.jsonl")):
        name = jsonl_path.name[: -len(".draft.jsonl")]
        actions = []
        try:
            raw = jsonl_path.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning("couldn't read orphaned draft sidecar %s: %s", jsonl_path, e)
            continue
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                actions.append(json.loads(line))
            except json.JSONDecodeError:
                # a crash mid-write can only ever truncate the LAST line -
                # every earlier line was already a complete, flushed
                # append (each write is one line + immediate close) - skip
                # just that one rather than losing the whole recovery
                continue

        if not actions:
            # nothing was ever captured before the crash - nothing to
            # recover, just clean up the empty/unusable sidecar
            try:
                jsonl_path.unlink()
            except OSError:
                pass
            continue

        first_action = actions[0]
        start_url = first_action.get("page_url") if first_action.get("action_type") == "navigate" else None
        test_case = {
            "name": name,
            "start_url": start_url,
            "actions": actions,
            "recovered": True,
            "recovered_note": (
                f"Recovered after an interrupted recording session - "
                f"{len(actions)} action(s) captured before it stopped."
            ),
        }
        try:
            path = save_recording(test_case)
        except OSError as e:
            logger.error("couldn't save recovered recording %r: %s", name, e)
            continue
        try:
            jsonl_path.unlink()
        except OSError:
            pass
        logger.warning(
            "recovered %d action(s) from an interrupted recording session: %s",
            len(actions), path,
        )
        recovered_paths.append(path)
    return recovered_paths
