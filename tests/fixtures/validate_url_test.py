"""
Auto-generated from recording: validate_url_test
Generated at: 2026-09-20T18:12:06.405380
Original recorded (production) URL: http://127.0.0.1:8899/page1.html

Resolution order per step: data-testid -> data-test -> data-cy -> id -> name
-> aria-label -> placeholder -> role -> css_path -> xpath -> text+tag ->
bounding box click. Dropdowns use page.select_option(), form submits use
form.requestSubmit(), meaningful keypresses (Enter/Tab/Escape) use el.press(),
double/right clicks use el.dblclick()/el.click(button="right"), scrolling
uses page.mouse.wheel().

Prints simple progress/result messages only - no internal strategy/step
logs. Set AUTOFLOW_DEBUG=1 to also see which locator strategy was used for
every step.

Run directly with: python validate_url_test.py [qa_url] [output_json_path] [screenshot_dir] [headless] [product_name]
qa_url defaults to the recorded starting URL if omitted. Running the file
directly launches a VISIBLE (headed) browser so you can watch the replay;
pass "1" as the 4th argument to run headless instead. An optional 5th
argument validates that a product appears on whatever page the recorded
actions end on - no separate search, no re-opening the site.
"""
import os
import re
import io
import sys
import json
import time
import inspect
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, urljoin

from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops

# quiet unless AUTOFLOW_DEBUG=1 - this is a replay script, not a report, so
# by default it should just perform the recorded actions and stay silent
# unless something actually fails
_DEBUG = os.environ.get("AUTOFLOW_DEBUG") == "1"
logging.basicConfig(level=logging.DEBUG if _DEBUG else logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# recorded element text can contain characters a terminal's codec can't
# encode (icon-font glyphs, emoji, non-Latin scripts) - on Windows this is
# cp1252/cp437 by default, and an unencodable character reaching a bare
# print() raises UnicodeEncodeError right out of the replay loop, aborting
# every action after it. Reconfiguring stdout/stderr to UTF-8 with a
# replace fallback means a print can never crash the run over encoding.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

STEPS = [   {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': '#route-btn',
                               'css_path': 'button#route-btn',
                               'xpath': "//*[@id='route-btn']",
                               'tag': 'button',
                               'text': 'Go to /route2 (pushState)'},
        'bounding_box': {},
        'click_strategy': None,
        'wait_for_stable_state': None,
        'wait_for_stable_state_timeout_ms': None,
        'click_selector': None,
        'confirmation_selector': None,
        'confirmation_text': None,
        'next_action_selector': None,
        'next_action_text': None,
        'verification_selector': None,
        'verification_text': None,
        'max_retries': None,
        'confirmation_timeout_ms': None,
        'verification_timeout_ms': None,
        'page_url': 'http://127.0.0.1:8899/page1.html',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': None,
        'delay_before_ms': None,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None,
        'remaining_page_id': None,
        'check_mode': None,
        'target': None,
        'label': None,
        'take_screenshot': None,
        'screenshot': None,
        'screenshot_path': None,
        'capture_screenshot': None,
        'save_screenshot': None,
        'file_path': None,
        'target_path': None,
        'capture_as': None,
        'compare_to': None,
        'count_as': None,
        'expected_count': None,
        'count_a': None,
        'count_b': None,
        'operator': None,
        'labels': None,
        'check': None,
        'expected_state': None,
        'min_value': None,
        'max_value': None,
        'detect_by': None,
        'attribute_name': None,
        'match_mode': None},
    {   'action_type': 'validate_url',
        'value': '/route2',
        'locator_profile': {},
        'bounding_box': {},
        'click_strategy': None,
        'wait_for_stable_state': None,
        'wait_for_stable_state_timeout_ms': None,
        'click_selector': None,
        'confirmation_selector': None,
        'confirmation_text': None,
        'next_action_selector': None,
        'next_action_text': None,
        'verification_selector': None,
        'verification_text': None,
        'max_retries': None,
        'confirmation_timeout_ms': None,
        'verification_timeout_ms': None,
        'page_url': 'http://127.0.0.1:8899/page1.html',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': None,
        'delay_before_ms': None,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None,
        'remaining_page_id': None,
        'check_mode': None,
        'target': None,
        'label': None,
        'take_screenshot': None,
        'screenshot': None,
        'screenshot_path': None,
        'capture_screenshot': None,
        'save_screenshot': None,
        'file_path': None,
        'target_path': None,
        'capture_as': None,
        'compare_to': None,
        'count_as': None,
        'expected_count': None,
        'count_a': None,
        'count_b': None,
        'operator': None,
        'labels': None,
        'check': None,
        'expected_state': None,
        'min_value': None,
        'max_value': None,
        'detect_by': None,
        'attribute_name': None,
        'match_mode': 'contains'},
    {   'action_type': 'validate_url',
        'value': '/this-does-not-exist',
        'locator_profile': {},
        'bounding_box': {},
        'click_strategy': None,
        'wait_for_stable_state': None,
        'wait_for_stable_state_timeout_ms': None,
        'click_selector': None,
        'confirmation_selector': None,
        'confirmation_text': None,
        'next_action_selector': None,
        'next_action_text': None,
        'verification_selector': None,
        'verification_text': None,
        'max_retries': None,
        'confirmation_timeout_ms': None,
        'verification_timeout_ms': None,
        'page_url': 'http://127.0.0.1:8899/page1.html',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': None,
        'delay_before_ms': None,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None,
        'remaining_page_id': None,
        'check_mode': None,
        'target': None,
        'label': None,
        'take_screenshot': None,
        'screenshot': None,
        'screenshot_path': None,
        'capture_screenshot': None,
        'save_screenshot': None,
        'file_path': None,
        'target_path': None,
        'capture_as': None,
        'compare_to': None,
        'count_as': None,
        'expected_count': None,
        'count_a': None,
        'count_b': None,
        'operator': None,
        'labels': None,
        'check': None,
        'expected_state': None,
        'min_value': None,
        'max_value': None,
        'detect_by': None,
        'attribute_name': None,
        'match_mode': 'contains'}]
PROD_URL = "http://127.0.0.1:8899/page1.html"
SOURCE_NAME = "validate_url_test"
SOURCE_TYPE = "ORIGINAL"

# how long (seconds) to keep the browser open, fully idle, after the last
# action/screenshot/report data is captured - purely so a human watching a
# headed run gets to actually see the final page before it vanishes. Does
# not affect action timing/order, only the moment right before close().
DEFAULT_CLOSE_DELAY = 5

# replay waits BETWEEN actions to roughly match how the actions were
# originally paced when recorded, instead of firing every Playwright call
# back-to-back - a recording is a real user's workflow, and a replay that
# teleports through it isn't a believable rehearsal of that workflow.
# Capped both ways: never less than MIN (even if two actions were
# recorded milliseconds apart) and never more than MAX (a user reading
# the page for 30 seconds mid-recording shouldn't make every replay of
# this test take 30 seconds too).
REPLAY_TIMING_ENABLED = True
MIN_ACTION_DELAY = 0
MAX_ACTION_DELAY = 4

# named, tunable defaults for the newer state/portal-waiting helpers below
# (smart_click, wait_for_stable_state, wait_for_portal_ready) - centralized
# here as named constants, not buried as bare literals inside each
# function, so they can be tuned later for real network conditions without
# touching any of those functions' own logic. Each function still accepts
# its own timeout as a parameter too, so a single call can override these
# defaults without a code change at all.
SMART_CLICK_FALLBACK_TIMEOUT_MS = 3000
WAIT_FOR_STABLE_STATE_TIMEOUT_MS = 10000
WAIT_FOR_PORTAL_READY_TIMEOUT_MS = 10000
# how long a visible target's computed opacity must hold the same value,
# sampled twice this far apart, before it's considered "done transitioning"
# rather than "still mid CSS-transition/animation"
VISIBILITY_STABLE_SAMPLE_MS = 120
# defaults for add_to_cart_and_verify() below - a client-side confirmation
# state (a button swapping to "added"/checkmark) and a server-side add-to-
# cart request are two different things with two different timing
# profiles, so each gets its own tunable timeout rather than sharing one
ADD_TO_CART_CONFIRMATION_TIMEOUT_MS = 10000
ADD_TO_CART_VERIFICATION_TIMEOUT_MS = 10000
ADD_TO_CART_MAX_RETRIES = 3
# how long a click that the RECORDING shows was immediately followed by
# a navigate to a different URL gets to actually reach that URL before
# its step is reported as failed - see the effect-verification block in
# the main loop below. A locator resolving and a click executing
# without a Playwright exception is not proof the click's real, recorded
# effect (a modal opening, a route changing) actually happened.
EFFECT_VERIFY_TIMEOUT_S = 5.0
# scroll-reached-target verification (see the "scroll" branch in the main
# loop) - how close (px) counts as "reached", how long to wait/poll for
# it, and how many times to re-attempt the scroll itself before giving up
SCROLL_TARGET_TOLERANCE_PX = 20
SCROLL_VERIFY_TIMEOUT_S = 3.0
SCROLL_VERIFY_POLL_INTERVAL_S = 0.2
SCROLL_MAX_RETRIES = 4
# centralized locator-resolution timing for the NEW element-level
# validation actions (validate_text/validate_visible/count_elements/etc -
# see their handlers further down) - a short, bounded poll of the exact
# same _resolve_element() 12-level fallback used everywhere else, not a
# separate resolver. Deliberately NOT applied retroactively to the
# existing click/fill/select resolution path (resolve_and_act /
# _resolve_and_act_with_retry) - those already have their own
# extensively-tuned, already-proven timing (the fill/select retry budget,
# settle-and-recheck windows, etc.) and changing any of it is explicitly
# out of scope here.
LOCATOR_TIMEOUT_MS = 3000
LOCATOR_POLL_INTERVAL_MS = 200
# lazy-load/infinite-scroll probing (see _ensure_scroll_content_ready) -
# how many "scroll to current max, wait, recheck" rounds to try before
# giving up on the page ever growing tall enough, and how long to wait
# after each one for new content to mount
SCROLL_LAZY_LOAD_MAX_PROBES = 5
SCROLL_LAZY_LOAD_PROBE_WAIT_MS = 500
# a recorded click bounding box wider AND taller than this (px) covers
# more area than a single, deliberately-targeted interactive element
# plausibly would - a strong sign the RECORDING itself captured a broad/
# accidental click (an entire section, several sub-controls at once)
# rather than a precise one. Flagged for human review only - see the
# large-bbox check in the main replay loop - never auto-"fixed", since
# there's no way to know which specific sub-element was actually meant.
LARGE_BBOX_WIDTH_PX = 150
LARGE_BBOX_HEIGHT_PX = 150
# DOM quiet-window used before a click that immediately follows a
# recorded scroll (see resolve_and_act) - reuses _wait_for_page_settle's
# own MutationObserver mechanism, just with a shorter quiet window than
# its screenshot-timing default, matching "no further layout shifts for
# ~200-300ms" rather than a full page-load settle
POST_SCROLL_SETTLE_TIMEOUT_S = 4.0
POST_SCROLL_QUIET_WINDOW_MS = 250
# dynamic option-list stability (search/typeahead suggestions, dropdown
# options) before clicking one of them - see
# _wait_for_option_list_stable
OPTION_LIST_STABLE_INTERVAL_MS = 250
OPTION_LIST_STABLE_MAX_ATTEMPTS = 3


def _parse_timestamp(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _replay_delay(prev_ts, cur_ts):
    """Seconds to wait before replaying cur_ts's action, based on how far
    apart the two actions were actually recorded - not a fixed sleep."""
    if not REPLAY_TIMING_ENABLED:
        return 0
    prev = _parse_timestamp(prev_ts)
    cur = _parse_timestamp(cur_ts)
    if prev is None or cur is None:
        return 0
    delta = (cur - prev).total_seconds()
    if delta <= 0:
        return 0
    return max(MIN_ACTION_DELAY, min(MAX_ACTION_DELAY, delta))


def _step_delay(step, prev_ts, cur_ts):
    """Prefers the recorder's own delay_before_ms (the user's actual
    pacing between normalized actions, captured once at recording time)
    when present, falling back to a timestamp diff for older recordings
    made before that field existed. Either way this is purely recorded
    HUMAN pacing - it's layered on top of, never a substitute for, the
    Playwright waits (_settle, scroll_into_view_if_needed, etc.) that
    handle actual page/element readiness elsewhere in this loop."""
    if not REPLAY_TIMING_ENABLED:
        return 0
    delay_ms = step.get("delay_before_ms")
    if delay_ms is not None:
        return max(MIN_ACTION_DELAY, min(MAX_ACTION_DELAY, delay_ms / 1000))
    return _replay_delay(prev_ts, cur_ts)


def _slug(text, max_len=20):
    """Sanitizes recorded element text into a short, filesystem-safe
    fragment for screenshot filenames, e.g. "Add to Cart" -> "add_to_cart".
    Returns "" when there's nothing usable (caller falls back to just the
    action type)."""
    if not text:
        return ""
    safe = "".join(c if c.isalnum() else "_" for c in text.strip().lower())
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe.strip("_")[:max_len]


def _derive_stage_name(page, url, fallback_index):
    """Generic, site-agnostic name for the screenshot STAGE a page
    belongs to - tries the given url's own last non-empty path segment
    first (fast, deterministic, no live-page dependency), then the
    page's own title (only reached if the URL yielded nothing usable -
    e.g. the destination is just "/" or a bare query string), then the
    url's hostname, then a numbered fallback. url=None means "use
    page.url" - the caller passes an explicit url for the very first
    stage (before any navigate has happened) and None afterwards, once
    there's a live page whose OWN current location/title should decide
    the name rather than a possibly-stale recorded target.
    """
    if url is None:
        try:
            url = page.url if page is not None else ""
        except Exception:
            url = ""
    name = ""
    try:
        segments = [s for s in urlsplit(url or "").path.split("/") if s]
        if segments:
            name = _slug(segments[-1], max_len=30)
    except Exception:
        name = ""
    if not name and page is not None:
        try:
            name = _slug((page.title() or "").strip(), max_len=30)
        except Exception:
            name = ""
    if not name:
        try:
            name = _slug(urlsplit(url or "").netloc, max_len=30)
        except Exception:
            name = ""
    return name or f"stage_{fallback_index}"


def _is_explicit_screenshot_step(step):
    """Returns True if this step/event explicitly requests or defines a screenshot."""
    if not isinstance(step, dict):
        return False
    if step.get("action_type") == "screenshot":
        return True
    for key in ("take_screenshot", "screenshot", "screenshot_path", "capture_screenshot", "save_screenshot"):
        val = step.get(key)
        if val is True or val == 1 or str(val).lower() in ("true", "1", "yes"):
            return True
        if val and not isinstance(val, bool) and not isinstance(val, (int, float)):
            return True
    return False


def _get_step_target_shot_path(step, shot_dir, counter=None, default_name=None):
    """Determines the target file path for saving a step's screenshot.
    If the step specifies an existing target file path (screenshot_path, file_path,
    target_path, existing_file, or string screenshot), it uses that target path directly.
    Otherwise, if default_name is provided, it uses shot_dir/default_name.
    Otherwise, it uses _next_shot_path(shot_dir, counter).
    """
    if isinstance(step, dict):
        target = (
            step.get("screenshot_path")
            or step.get("file_path")
            or step.get("target_path")
            or step.get("existing_file")
        )
        if not target and isinstance(step.get("screenshot"), str):
            target = step.get("screenshot")

        if target and isinstance(target, str) and target.strip():
            p = Path(target.strip())
            if not p.is_absolute():
                p = Path(shot_dir) / p
            return p

    if default_name:
        return Path(shot_dir) / default_name
    if counter is not None:
        return _next_shot_path(shot_dir, counter)
    return Path(shot_dir) / "screenshot.png"


def _should_take_step_screenshot(step, ok, action_type, url_changed, has_explicit_screenshots):
    """Decides if a screenshot should be taken for this step."""
    is_explicit = _is_explicit_screenshot_step(step)
    if has_explicit_screenshots:
        return is_explicit
    else:
        if is_explicit or not ok:
            return True
        if action_type in (
            "navigate", "validate", "click_if_exists", "screenshot",
            "capture_value", "compare_value",
            "validate_element", "count_elements", "compare_counts",
            "count_summary", "check_checked", "validate_value_range",
            "detect_duplicates", "check",
            "capture_list", "compare_list_overlap",
            "__validate_xpath__",
            # a successful "fill"/"select" had no screenshot of its own
            # before this - only the step BEFORE it (pre-fill) and
            # whatever step happens to come after (often a navigate,
            # once Enter/submit is pressed) ever got captured, so the
            # typed/selected value never appeared in the report or the
            # replay video at all: it visually "jumped" straight from
            # empty to whatever the next screenshotted step showed, even
            # though _do_fill had already verified the real, correct
            # value was genuinely sitting in the field the whole time.
            # Generic - every fill/select action in any recording now
            # gets its own evidence frame, the same as every other
            # action type already does.
            "fill", "select",
        ):
            return True
        if action_type in ("click", "dblclick", "right_click", "submit", "press") and url_changed:
            return True
        return False


def _next_shot_path(shot_dir, counter):
    """Returns the path for the NEXT screenshot in this run's sequence -
    img1.png, img2.png, ... - advancing the shared counter every call so
    every screenshot the whole run takes (initial load, per-step,
    final, product validation) lands in one strictly ordered series."""
    counter[0] += 1
    return Path(shot_dir) / f"img{counter[0]}.png"


def _get_stage_dir(page, run_dir, stage_counter, default_shot_dir=None):
    """Derives the stage subfolder dynamically from the page's current URL."""
    if not run_dir:
        return Path(default_shot_dir) if default_shot_dir else None
    try:
        url = page.url if page is not None else ""
    except Exception:
        url = ""
    if not url or url.lower() in ("about:blank", "data:"):
        return Path(default_shot_dir) if default_shot_dir else Path(run_dir)
    stage_name = _derive_stage_name(page, url, stage_counter[0] if stage_counter else 1)
    return Path(run_dir) / stage_name


def _capture_screenshot_when_settled(page, shot_dir, img_counter, label=None, step=None, run_dir=None, stage_counter=None):
    """Manual, settle-aware screenshot capture for explicit screenshot events. Saves to target file if provided."""
    try:
        _wait_for_page_settle(page)
    except Exception:
        pass

    effective_shot_dir = _get_stage_dir(page, run_dir, stage_counter, shot_dir)

    if step:
        shot_path = _get_step_target_shot_path(step, effective_shot_dir, counter=img_counter, default_name=f"{_slug(label, max_len=100)}.png" if label else None)
    elif label:
        safe_name = _slug(label, max_len=100) or "screenshot"
        shot_path = Path(effective_shot_dir) / f"{safe_name}.png"
    else:
        shot_path = _next_shot_path(effective_shot_dir, img_counter)

    try:
        shot_path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(shot_path))
    except Exception:
        return None

    return str(shot_path)


def _page_state_key(page):
    """A cheap, generic fingerprint of the page's CURRENT rendered state -
    URL, a hash of the full DOM markup (not just visible text, so a
    purely visual/structural change - a button gaining disabled/aria-
    busy, a class toggling on for a spinner, an error banner being
    inserted - still counts as a real change even when no visible text
    changed), plus every input/textarea/select's current VALUE. That
    last part matters generically on any site: page.content() serializes
    static HTML attributes only - typing into a field changes its live
    DOM property, not its HTML attribute, so content() alone never
    reflects what a user actually typed/selected. Returns None if the
    page can't be read right now (e.g. mid-navigation, closed) - callers
    should treat that as "can't compare, don't suppress."
    """
    try:
        content = page.content()
    except Exception:
        return None
    try:
        url = page.url
    except Exception:
        url = ""
    try:
        field_values = page.eval_on_selector_all(
            "input, textarea, select",
            "els => els.map(el => el.value).join('\u0001')",
        )
    except Exception:
        field_values = ""
    fingerprint = f"{content} {field_values}"
    return url + "|" + hashlib.md5(fingerprint.encode("utf-8", "ignore")).hexdigest()


def _is_duplicate_screenshot(candidate_bytes, prev_bytes, threshold=0.02):
    """Generic, content-based check for whether a candidate screenshot is
    a near-duplicate of the immediately previous one actually saved this
    run - the same simple histogram-based pixel-diff-ratio technique
    validation/compare.py already uses for baseline comparison,
    reimplemented standalone here since this generated script is meant
    to run with no dependency on the rest of that project. Fails OPEN
    (treats as "not a duplicate") on any error or size mismatch, so a
    comparison problem can never suppress a screenshot that should have
    been kept.
    """
    if prev_bytes is None:
        return False
    try:
        img_a = Image.open(io.BytesIO(prev_bytes)).convert("RGB")
        img_b = Image.open(io.BytesIO(candidate_bytes)).convert("RGB")
    except Exception:
        return False
    if img_a.size != img_b.size or img_a.size[0] == 0 or img_a.size[1] == 0:
        return False
    diff = ImageChops.difference(img_a, img_b)
    hist = diff.histogram()
    total_channel_values = img_a.size[0] * img_a.size[1] * 3
    diff_sum = sum(i * count for i, count in enumerate(hist))
    diff_ratio = diff_sum / (total_channel_values * 255)
    return diff_ratio <= threshold


def _capture_screenshot(page, shot_dir, img_counter, last_state, last_shot_bytes, full_page=False, step=None, target_path=None, run_dir=None, stage_counter=None):
    """Takes the next screenshot in this run's sequence, but SKIPS saving
    it if the page's current state is a near-duplicate of the last screenshot actually saved this run.
    Saves directly to specified target_path or step's target file if provided.
    Best-effort throughout: a failure to take or write the screenshot is skipped,
    never failing the action flow.
    """
    state_key = _page_state_key(page)
    if state_key is not None and state_key == last_state[0]:
        return None
    try:
        candidate_bytes = page.screenshot(full_page=full_page)
    except Exception:
        return None

    if _is_duplicate_screenshot(candidate_bytes, last_shot_bytes[0]):
        if state_key is not None:
            last_state[0] = state_key
        return None

    effective_shot_dir = _get_stage_dir(page, run_dir, stage_counter, shot_dir)

    try:
        if target_path:
            shot_path = Path(target_path)
            if not shot_path.is_absolute():
                shot_path = Path(effective_shot_dir) / shot_path
        elif step:
            shot_path = _get_step_target_shot_path(step, effective_shot_dir, counter=img_counter)
        else:
            shot_path = _next_shot_path(effective_shot_dir, img_counter)

        shot_path.parent.mkdir(parents=True, exist_ok=True)
        with open(shot_path, "wb") as f:
            f.write(candidate_bytes)
    except Exception:
        return None

    if state_key is not None:
        last_state[0] = state_key
    last_shot_bytes[0] = candidate_bytes
    return str(shot_path)


def _describe_step(step):
    """Best-effort human label + locator string for the per-action
    terminal log - mirrors the recorder's own [RECORDED] line style so
    replay output reads like a continuation of the recording's."""
    lp = step.get("locator_profile") or {}
    attrs = lp.get("attributes") or {}
    text = (lp.get("element_text") or lp.get("text") or "").strip()
    value = step.get("value")
    # a click-type action with no recorded locator text falls back to
    # Value as its target text at replay time too (see resolve_and_act's
    # tier 11b) - describe it the same way here for an accurate log
    value_as_text = (
        value
        if step.get("action_type") in ("click", "dblclick", "right_click") and value
        else None
    )
    label = (
        text
        or value_as_text
        or lp.get("accessible_name")
        or lp.get("aria_label") or attrs.get("aria-label")
        or lp.get("placeholder") or attrs.get("placeholder")
        or lp.get("id")
        or lp.get("tag")
        or "(element)"
    )
    locator_display = (
        lp.get("id")
        or (f'a[href="{lp["href"]}"]' if lp.get("href") else None)
        or lp.get("css_path")
        or lp.get("xpath")
        or "(no stable locator found - will fall back to screen position)"
    )
    return label, locator_display


def _locator_attempts(step):
    """Numbered list of every locator tier resolve_and_act() would try for
    this step, in the same priority order, for failure diagnostics - shows
    what was actually available to try, not just the one that "won"."""
    lp = step.get("locator_profile") or {}
    attrs = lp.get("attributes") or {}
    action_type = step.get("action_type")
    value = step.get("value")
    tiers = [
        ("data-testid", attrs.get("data-testid")),
        ("data-test", attrs.get("data-test")),
        ("data-cy", attrs.get("data-cy")),
        ("id", lp.get("id")),
        ("name", attrs.get("name") or lp.get("name")),
        ("aria-label", attrs.get("aria-label") or lp.get("aria_label")),
        ("placeholder", attrs.get("placeholder") or lp.get("placeholder")),
        ("title", attrs.get("title") or lp.get("title")),
        ("role", attrs.get("role") or lp.get("role")),
        ("href", lp.get("href")),
        ("text", lp.get("element_text") or lp.get("text")),
        ("css_path", lp.get("css_path")),
        ("xpath", lp.get("xpath")),
    ]
    if action_type in ("click", "dblclick", "right_click") and not lp.get("text") and value:
        tiers.append(("text (from value)", value))
    box = step.get("bounding_box")
    if action_type in ("click", "dblclick", "right_click") and box and box.get("width") and box.get("height"):
        tiers.append(("bounding_box", f"x={box.get('x')}, y={box.get('y')}"))

    present = [(k, v) for k, v in tiers if v]
    if not present:
        return ["(no locator information recorded for this action)"]
    return [f"{i}. {k}={v}" for i, (k, v) in enumerate(present, start=1)]


def _print_step_header(i, total, step):
    action_type = step.get("action_type")
    page_id = step.get("page_id", 0)
    print("=" * 50)
    if action_type == "validate":
        # a validate step is easy to miss scrolling past a long terminal
        # log otherwise - this one extra marker line is the only visual
        # difference from every other action's header, everything below
        # (the [i/total], ACTION, STATUS/Done lines) stays identical
        print("[VALIDATION]")
    print(f"[{i}/{total}]")
    print(f"ACTION: {action_type}")
    if page_id:
        print(f"PAGE: {page_id}")
    if action_type == "navigate":
        print(f"URL: {step.get('page_url')}")
        if step.get("new_tab"):
            print("(new tab/page - replay switches to it for subsequent actions)")
    elif action_type == "scroll":
        print(f"Delta: ({step.get('delta_x')}, {step.get('delta_y')})")
    elif action_type == "press":
        print(f"Key: {step.get('value')}")
    elif action_type == "tab_switch":
        print(f"Switch: page {step.get('from_page_id')} -> page {step.get('to_page_id')}")
    elif action_type == "tab_open":
        print(f"URL: {step.get('page_url')}")
        print(f"(new tab/page opened from page {step.get('from_page_id')} - replay switches to it for subsequent actions)")
    elif action_type == "tab_close":
        print(f"Closing page {step.get('page_id')} -> remaining page {step.get('remaining_page_id')}")
    elif action_type == "validate":
        print(f'Expected: "{step.get("value")}"')
    elif action_type == "capture_value":
        label, locator_display = _describe_step(step)
        print(f"Element: {label}")
        print(f"Locator: {locator_display}")
        print(f"Capture As: {step.get('capture_as')}")
    elif action_type == "compare_value":
        print(f"Compare To: {step.get('compare_to')}")
    elif action_type == "validate_element":
        label, locator_display = _describe_step(step)
        print(f"Element: {label}")
        print(f"Locator: {locator_display}")
        print(f"Check: {step.get('check', 'disabled')}")
    elif action_type == "validate_text":
        label, locator_display = _describe_step(step)
        print(f"Element: {label}")
        print(f"Locator: {locator_display}")
        print(f"Expected text: {step.get('value')!r}")
        print(f"Match mode: {step.get('match_mode', 'contains')}")
    elif action_type == "validate_attribute":
        label, locator_display = _describe_step(step)
        print(f"Element: {label}")
        print(f"Locator: {locator_display}")
        print(f"Attribute: {step.get('attribute_name')}")
        print(f"Expected value: {step.get('value')!r}")
    elif action_type == "validate_visible":
        label, locator_display = _describe_step(step)
        print(f"Element: {label}")
        print(f"Locator: {locator_display}")
        print(f"Expected: {step.get('expected_state', 'visible')}")
    elif action_type == "validate_url":
        # no element/locator at all - this checks the CURRENT page URL,
        # same shape as the "navigate" print block above (also locator-
        # free), not the element-based validate_* blocks around it
        print(f"Expected URL {step.get('match_mode', 'contains')}: {step.get('value')!r}")
    elif action_type == "validate_value":
        label, locator_display = _describe_step(step)
        print(f"Element: {label}")
        print(f"Locator: {locator_display}")
        print(f"Expected value: {step.get('value')!r}")
        print(f"Match mode: {step.get('match_mode', 'exact')}")
    elif action_type == "validate_enabled":
        label, locator_display = _describe_step(step)
        print(f"Element: {label}")
        print(f"Locator: {locator_display}")
        print(f"Expected: {step.get('expected_state', 'enabled')}")
    elif action_type == "count_elements":
        label, locator_display = _describe_step(step)
        print(f"Selector: {locator_display}")
        print(f"Count As: {step.get('count_as')}")
        if step.get("expected_count") is not None:
            print(f"Expected Count: {step.get('expected_count')}")
    elif action_type == "compare_counts":
        print(f"Count A: {step.get('count_a')}")
        print(f"Count B: {step.get('count_b')}")
        print(f"Operator: {step.get('operator', 'eq')}")
    elif action_type == "count_summary":
        labels = step.get("labels") or []
        print(f"Summary Labels: {labels}")
    elif action_type == "check_checked":
        label, locator_display = _describe_step(step)
        print(f"Element: {label}")
        print(f"Locator: {locator_display}")
        print(f"Expected State: {step.get('expected_state', 'checked')}")
    elif action_type == "validate_value_range":
        label, locator_display = _describe_step(step)
        print(f"Element: {label}")
        print(f"Locator: {locator_display}")
        if step.get("min_value") is not None:
            print(f"Min: {step.get('min_value')}")
        if step.get("max_value") is not None:
            print(f"Max: {step.get('max_value')}")
    elif action_type == "detect_duplicates":
        label, locator_display = _describe_step(step)
        print(f"Selector: {locator_display}")
        print(f"Detect By: {step.get('detect_by', 'text')}")
    elif action_type == "add_to_cart_and_verify":
        print(f"Click selector: {step.get('click_selector')}")
        if step.get("confirmation_selector"):
            print(f"Confirmation selector: {step.get('confirmation_selector')}")
        if step.get("confirmation_text"):
            print(f"Confirmation text: {step.get('confirmation_text')!r}")
        if step.get("next_action_selector"):
            print(f"Next-action selector: {step.get('next_action_selector')}")
            if step.get("next_action_text"):
                print(f"Next-action ready text: {step.get('next_action_text')!r}")
        if step.get("verification_selector"):
            print(f"Verification selector: {step.get('verification_selector')}")
        if step.get("verification_text"):
            print(f"Verification text: {step.get('verification_text')!r}")
        print(f"Max retries: {step.get('max_retries') or ADD_TO_CART_MAX_RETRIES}")
    elif action_type in ("click", "dblclick", "right_click", "submit", "fill", "select", "check"):
        label, locator_display = _describe_step(step)
        print(f"Element: {label}")
        print(f"Locator: {locator_display}")
        if action_type in ("fill", "select"):
            print(f"Value: {step.get('value')}")
        elif action_type == "check":
            print(f"Expected State: {step.get('expected_state')}")
    print()


def to_qa_url(recorded_url, qa_base):
    """Map a URL recorded against production onto the QA host, keeping the
    path/query intact. Relative URLs and third-party domains pass through
    mostly unchanged - only the domain we actually recorded against gets
    swapped for the QA one.
    """
    if not recorded_url:
        return qa_base
    qa = urlsplit(qa_base)
    rec = urlsplit(recorded_url)
    if not rec.netloc:
        # already a relative/path-only URL - just point it at the QA host
        return urlunsplit((qa.scheme, qa.netloc, rec.path, rec.query, rec.fragment))
    prod = urlsplit(PROD_URL) if PROD_URL else None
    if prod and rec.netloc == prod.netloc:
        return urlunsplit((qa.scheme, qa.netloc, rec.path, rec.query, rec.fragment))
    # different domain than what we recorded against (e.g. a third-party
    # link) - leave it alone rather than guessing
    return recorded_url


def _by_attr(page, attr, value):
    """Locate by a raw HTML attribute value, e.g. [data-testid="submit"]."""
    if not value:
        return None
    try:
        safe = value.replace('"', '\"')
        c = page.locator(f'[{attr}="{safe}"]')
        if c.count() > 0:
            return c.first
    except Exception:
        pass
    return None


def _find_by_id(page, lp):
    if not lp.get("id"):
        return None
    try:
        c = page.locator(lp["id"])
        return c.first if c.count() > 0 else None
    except Exception:
        return None


def _find_by_role(page, lp, attrs):
    role = attrs.get("role") or lp.get("role")
    if not role:
        return None
    try:
        name = lp.get("accessible_name") or lp.get("text") or None
        c = page.get_by_role(role, name=name)
        return c.first if c.count() > 0 else None
    except Exception:
        return None


# standard, generic HTML-to-implicit-ARIA-role mappings (no site-specific
# knowledge at all - this is ordinary HTML semantics) used by
# _resolve_via_role_or_text below to infer a role for _find_by_role's own
# tier above to try even when the RECORDING never captured an explicit
# role="..." attribute - the overwhelmingly common case for a plain
# native <button>/<a>/<select>, which never needs one to already BE a
# button/link/combobox accessibility-wise.
_IMPLICIT_ARIA_ROLE_BY_TAG = {
    "button": "button",
    "a": "link",
    "summary": "button",
    "select": "combobox",
    "textarea": "textbox",
    "option": "option",
}
_IMPLICIT_ARIA_ROLE_BY_INPUT_TYPE = {
    "button": "button",
    "submit": "button",
    "reset": "button",
    "checkbox": "checkbox",
    "radio": "radio",
    "range": "slider",
    "text": "textbox",
    "search": "searchbox",
    "email": "textbox",
    "tel": "textbox",
    "url": "textbox",
    "password": "textbox",
    "number": "spinbutton",
}


def _infer_implicit_role(lp, attrs):
    """An explicitly recorded role always wins; otherwise infers the
    standard implicit ARIA role from the recorded tag (and, for <input>,
    its type) - generic HTML/ARIA semantics, never a site-specific guess.
    Returns None when nothing recorded gives enough information to infer
    anything (an unfamiliar/custom tag with no recorded role).
    """
    explicit = attrs.get("role") or lp.get("role")
    if explicit:
        return explicit
    tag = (lp.get("tag") or "").lower()
    if tag == "input":
        input_type = (attrs.get("type") or lp.get("type") or "text").lower()
        return _IMPLICIT_ARIA_ROLE_BY_INPUT_TYPE.get(input_type)
    return _IMPLICIT_ARIA_ROLE_BY_TAG.get(tag)


def _resolve_via_role_or_text(page, lp, attrs):
    """Last-chance, identity-based re-resolution tried right before the
    raw-coordinate bounding_box fallback (see resolve_and_act) - for a
    click whose EVERY earlier tier came up empty (most commonly because
    the recording only captured an implicit ARIA role, which
    _find_by_role's own tier above does not infer on its own), a stale
    recorded (x, y) is exactly what a layout-shifting preceding action
    (a checkbox reveal, an expand/collapse, any reflow) breaks - the
    element's role and accessible name/text haven't changed at all,
    wherever it moved to, so re-resolving fresh via Playwright's OWN
    accessibility-tree-aware get_by_role()/get_by_text() locators finds
    the REAL current element instead of clicking whatever now happens to
    sit at the stale coordinate. Only trusted when exactly ONE match
    exists - an ambiguous result here is no more trustworthy than
    guessing, so this returns None (falls through to the coordinate
    fallback) rather than risk a confident but wrong pick. Returns the
    resolved Locator, or None. Never raises.
    """
    accessible_name = (
        lp.get("accessible_name") or lp.get("aria_label")
        or lp.get("text") or lp.get("element_text") or None
    )
    if not accessible_name:
        return None

    role = _infer_implicit_role(lp, attrs)
    if role:
        try:
            c = page.get_by_role(role, name=accessible_name)
            if c.count() == 1:
                return c.first
        except Exception:
            pass

    try:
        c = page.get_by_text(accessible_name, exact=True)
        if c.count() == 1:
            return c.first
    except Exception:
        pass
    return None


def _normalize_href_for_match(href, base_url, keep_query):
    """Resolves href to a comparable (scheme, host, path[, query]) key for
    deciding whether it points at the SAME target as another href - not a
    fuzzy/similarity match, an equivalence check: two hrefs that represent
    the same resource (one absolute, one relative; with/without a
    trailing slash; differing only in tracking-style query params) must
    normalize to the same key, but any genuine path difference still
    means "different target", full stop.

    keep_query is decided ONCE by the caller from the RECORDED href alone
    (see _find_by_href) and applied identically to both sides being
    compared - a live element's .href is always a fully-resolved absolute
    URL and so always has a path, so deciding "keep the query" per-href
    independently would make the two sides permanently disagree whenever
    the recorded reference itself was query-only.
    """
    if not href:
        return None
    try:
        parts = urlsplit(urljoin(base_url, href))
    except Exception:
        return None
    path = parts.path
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return (parts.scheme, parts.netloc, path, parts.query if keep_query else "")


def _find_by_href(page, lp):
    if not lp.get("href"):
        return None
    recorded_href = lp["href"]
    # a recorded reference with no path component of its own (a query-
    # only or fragment-only reference like "?tab=reviews") means the
    # query IS what distinguishes the target - otherwise the query
    # string/fragment are ignored (tracking params, session ids, etc.
    # commonly vary without representing a different target)
    try:
        keep_query = not urlsplit(recorded_href).path
    except Exception:
        keep_query = False
    recorded_key = _normalize_href_for_match(recorded_href, page.url, keep_query)
    if recorded_key is None:
        return None
    try:
        anchors = page.locator("a[href]")
        live_hrefs = anchors.evaluate_all("els => els.map(el => el.href)")
    except Exception:
        return None
    for i, live_href in enumerate(live_hrefs):
        if _normalize_href_for_match(live_href, page.url, keep_query) == recorded_key:
            try:
                return anchors.nth(i)
            except Exception:
                return None
    return None


def _find_by_text_tag(page, lp):
    # exact, whole-trimmed-text match against each candidate's own text -
    # Playwright's has_text (substring match anywhere in the subtree) is
    # too permissive for short/generic labels ("8", "1", "OK") common to
    # pagination, quantity/size pickers, star ratings, etc. on any site,
    # and can silently grab the wrong element that merely CONTAINS the
    # recorded text rather than the one that IS that text.
    if not (lp.get("text") and lp.get("tag")):
        return None
    text = lp["text"].strip()
    if not text:
        return None
    try:
        loc = page.locator(lp["tag"])
        texts = loc.all_inner_texts()
    except Exception:
        return None

    exact_idx = [i for i, t in enumerate(texts) if t.strip() == text]
    if not exact_idx:
        lowered = text.lower()
        exact_idx = [i for i, t in enumerate(texts) if t.strip().lower() == lowered]
    if not exact_idx:
        return None

    # very short or purely numeric text is an inherently weak signal on
    # any site (it's exactly the kind of label pagination/size/quantity/
    # rating controls use) - only trust it when it's genuinely
    # unambiguous on this page; with multiple exact matches there's no
    # reliable way to know which one the user meant, so this tier is
    # skipped entirely (falls through to css_path/xpath) rather than
    # blindly taking the first match
    is_weak_text = len(text) <= 2 or text.isdigit()
    if is_weak_text and len(exact_idx) != 1:
        return None

    if len(exact_idx) == 1:
        try:
            return loc.nth(exact_idx[0])
        except Exception:
            return None

    # longer, non-weak text isn't immune to the same ambiguity - a label
    # repeated identically across many like items on any site (a
    # "Register Now"/"Add to Cart"/"View Details" button on every card in
    # a listing is the common real-world case) is just as ambiguous as a
    # short one once there's more than one exact match, and .first here
    # would silently click whichever candidate happens to come first in
    # DOM order - only "correct" by coincidence, and confidently wrong
    # the moment the recorded item's card isn't first anymore (removed,
    # reordered, or simply not the one at that position any more).
    # Disambiguate using whatever OTHER signal was actually recorded for
    # THIS click, the same way a person would tell the candidates apart -
    # an href identifies one specific link among several identically-
    # labeled ones; the exact recorded css_path identifies one specific
    # structural position. Only trust a match found this way; if neither
    # signal exists or neither resolves to one of these candidates, admit
    # this tier can't tell them apart rather than guess, and let the
    # search continue to css_path/xpath below instead of reporting a
    # confident but potentially wrong success.
    candidate = _disambiguate_exact_text_matches(page, loc, exact_idx, lp)
    return candidate


def _disambiguate_exact_text_matches(page, loc, exact_idx, lp):
    """Among several elements that all exactly match the recorded text,
    picks the one that also matches a stronger recorded signal - href
    first (identifies a specific link regardless of which of several
    identically-labeled links it is), then the exact recorded css_path
    (identifies a specific structural position). Returns None, never a
    guess, when neither signal is available or neither actually points at
    one of these candidates - a caller treating None as "this tier found
    nothing" is exactly the right fallback here, since a low-confidence
    pick would be worse than admitting this tier can't tell them apart.
    """
    href = lp.get("href")
    if href:
        try:
            for i in exact_idx:
                cand = loc.nth(i)
                is_match = cand.evaluate(
                    "(el, targetHref) => { "
                    "let node = el; "
                    "while (node) { "
                    "if (node.tagName === 'A' && node.getAttribute('href') === targetHref) return true; "
                    "node = node.parentElement; "
                    "} "
                    "return false; }",
                    href,
                )
                if is_match:
                    return cand
        except Exception:
            pass

    css_path = lp.get("css_path")
    if css_path:
        try:
            recorded_loc = page.locator(css_path)
            if recorded_loc.count() == 1:
                recorded_handle = recorded_loc.element_handle(timeout=1000)
                if recorded_handle is not None:
                    for i in exact_idx:
                        cand_handle = loc.nth(i).element_handle(timeout=1000)
                        if cand_handle is not None and cand_handle.evaluate("(a, b) => a === b", recorded_handle):
                            return loc.nth(i)
        except Exception:
            pass

    return None


def _find_by_value_text(page, lp, value, action_type):
    # a click-type action with no recorded locator text at all (e.g.
    # manually added in the Recording Editor) still has its Value, which
    # for a click is normally the visible text of the link/button to
    # click - never treated as the ONLY locator source when real
    # locator_profile.text exists (that's tried first, above)
    if lp.get("text") or not value or action_type not in ("click", "dblclick", "right_click"):
        return None
    try:
        c = page.get_by_text(value, exact=True)
        if c.count() == 0:
            c = page.get_by_text(value)
        return c.first if c.count() > 0 else None
    except Exception:
        return None


def _structural_match_conflicts_with_recorded_href(candidate, page, recorded_href):
    """Generic safety net for css_path/xpath - the two WEAKEST, PURELY
    STRUCTURAL tiers in the resolution order, tried only after every
    stronger, identity-based signal (data-testid/id/name/aria-label/
    href-exact/text-exact) has already failed to find the recorded
    element. A structural path can still resolve to SOMETHING even when
    the actual recorded element is long gone - the live DOM just happens
    to have a different element occupying that same tree position now
    (a rotating promotional banner/carousel slot is the confirmed real
    case: same "9th top-level section's own anchor" shape, completely
    different destination, because the promotion itself changed between
    record and replay time). Structurally-coincidental, not the same
    link - and for a click that NAVIGATES, confidently clicking the
    wrong one is a much worse failure mode (an unrelated page, a
    cascade of confused subsequent steps) than a clean "target not
    found".

    Only ever REJECTS a structural match, never confirms one - a
    candidate with no href at all (a button, a styled div) is exactly as
    trusted as before; this purely closes the specific gap where BOTH
    sides have a real href to compare and they point at genuinely
    different places. Reuses _normalize_href_for_match exactly as
    _find_by_href already does, so "same page, different tracking
    params" still counts as a match, not a conflict. Never raises;
    inconclusive (evaluate failure, no anchor found) means "don't
    reject" - this is a safety net, not a new way to fail closed on
    something ambiguous.
    """
    if not recorded_href:
        return False
    try:
        live_href = candidate.evaluate(
            "el => { const a = el.closest('a'); return a ? a.href : null; }"
        )
    except Exception:
        return False
    if not live_href:
        return False
    try:
        keep_query = not urlsplit(recorded_href).path
        recorded_key = _normalize_href_for_match(recorded_href, page.url, keep_query)
        live_key = _normalize_href_for_match(live_href, page.url, keep_query)
    except Exception:
        return False
    return recorded_key is not None and live_key is not None and recorded_key != live_key


def _find_by_css(page, lp):
    if not lp.get("css_path"):
        return None
    try:
        c = page.locator(lp["css_path"])
        if c.count() == 0:
            return None
        candidate = c.first
        if _structural_match_conflicts_with_recorded_href(candidate, page, lp.get("href")):
            return None
        return candidate
    except Exception:
        return None


def _find_by_xpath(page, lp):
    if not lp.get("xpath"):
        return None
    try:
        c = page.locator("xpath=" + lp["xpath"])
        if c.count() == 0:
            return None
        candidate = c.first
        if _structural_match_conflicts_with_recorded_href(candidate, page, lp.get("href")):
            return None
        return candidate
    except Exception:
        return None


def _parse_nth_of_type(segment):
    """Returns (tag, position) if this single css_path segment carries an
    explicit :nth-of-type(N) suffix (exactly how cssPath() in
    action_capture.js writes a non-unique sibling), else None. Plain
    string parsing, not regex - the format is simple and fixed enough
    that a dependency isn't worth adding for it.
    """
    marker = ":nth-of-type("
    idx = segment.find(marker)
    if idx == -1 or not segment.endswith(")"):
        return None
    tag = segment[:idx]
    num_str = segment[idx + len(marker):-1]
    if not (tag and num_str.isdigit()):
        return None
    return tag, int(num_str)


def _find_by_position(page, lp, info=None):
    """Fallback for when the recorded href/text no longer identifies an
    element anywhere on the page - the underlying content genuinely
    changed since recording (a different item now occupies that slot in
    a product grid, article feed, search results list, etc, on any
    site, static or dynamic). Re-derives "the Nth <tag> among its
    siblings under this container" from the recorded css_path's own
    :nth-of-type segment (css_path already encodes this - no new
    recorded field needed) and finds whatever CURRENTLY occupies that
    same structural position in the live DOM, rather than trying to
    relocate the specific recorded item by content.

    This is deliberately looser than the css_path tier itself, which
    applies the whole recorded path fairly literally and is fragile to
    any structural drift above the repeating element - here, only the
    repeating element's own tag and position among its immediate
    siblings matters, wherever its container now is. Position among
    structurally-similar siblings is the ONLY signal used - no text/
    content similarity, no scoring, nothing fuzzy.

    info, when given a dict, is populated with the position/tag actually
    used so the caller can report that a position fallback (not an exact
    match) is what resolved this step.

    Returns the resolved element, or None if the recorded css_path has
    no positional information to fall back on, or nothing currently
    occupies that position.
    """
    css_path = lp.get("css_path")
    if not css_path:
        return None

    segments = [s.strip() for s in css_path.split(">")]

    repeat_idx = None
    tag = None
    position = None
    for i in range(len(segments) - 1, -1, -1):
        parsed = _parse_nth_of_type(segments[i])
        if parsed:
            repeat_idx = i
            tag, position = parsed
            break

    if repeat_idx is None:
        return None

    container_selector = " > ".join(segments[:repeat_idx])
    remainder_selector = " > ".join(segments[repeat_idx + 1:])

    try:
        siblings = page.locator(f"{container_selector} > {tag}") if container_selector else page.locator(tag)
        if siblings.count() < position:
            return None
        target = siblings.nth(position - 1)
        if remainder_selector:
            descendant = target.locator(remainder_selector)
            if descendant.count() == 0:
                return None
            target = descendant.first
        if info is not None:
            info["tag"] = tag
            info["position"] = position
        return target
    except Exception:
        return None


def _try_dismiss_overlay(page):
    """Best-effort, generic recovery from an unexpected overlay/modal/
    dialog blocking a click - Escape, then a generically-matched close
    button (aria-label containing "close", anywhere, optionally inside a
    role=dialog element). No assumptions about any particular site's
    modal/lightbox/gallery markup; failures here are swallowed since this
    is purely a recovery attempt, not the action itself.
    """
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    try:
        close_btn = page.locator(
            '[role="dialog"] [aria-label*="close" i], [aria-label*="close" i]'
        ).first
        if close_btn.count() > 0:
            # close buttons are commonly icon-only, zero-size-box wrapper
            # elements themselves - exactly smart_click()'s own case.
            # standard_timeout preserves this call's original 1000ms (a
            # deliberately quick, best-effort recovery attempt, already
            # wrapped in try/except above) instead of smart_click's own
            # longer 5000ms default for the ordinary case.
            smart_click(page, close_btn, standard_timeout=1000)
    except Exception:
        pass


def _capture_dom_change_fingerprint(el):
    """Generic, content-agnostic snapshot of DOM state used to detect
    whether a click produced ANY observable effect at all - never any
    site-specific text/class/id check, so this works identically for a
    "size" click, a "quantity" click, or anything else. Signals used
    together:

    - total element count under body (catches new content mounting
      ANYWHERE on the page, not just near the click);
    - the count of elements under body that currently occupy real,
      non-zero layout space (width and height both > 0) - this is what
      actually catches a modal appearing, REGARDLESS of how it's
      styled: a fixed/absolute overlay is one common case, but plenty
      of real modals are just an ordinary in-flow element whose
      display flips from none to block/flex - that transition changes
      NOTHING about element count or position, only about whether it
      now occupies visual space at all, which this direct geometry
      check catches on any element anywhere, not just body's direct
      children;
    - the clicked element's own class/aria-expanded/inline-style
      together with its immediate parent's (catches an in-place state
      change - an expanded class, an aria-expanded flip - that doesn't
      add or reveal any element at all).

    None on failure - never blocks anything.
    """
    try:
        return el.evaluate(
            "e => { "
            "const all = document.body ? document.body.getElementsByTagName('*') : []; "
            "let visibleCount = 0; "
            "for (const node of all) { "
            "  const r = node.getBoundingClientRect(); "
            "  if (r.width > 0 && r.height > 0) visibleCount += 1; "
            "} "
            "const parent = e.parentElement; "
            "return { "
            "elementCount: all.length, "
            "visibleElementCount: visibleCount, "
            "selfSnapshot: (e.className || '') + '|' + (e.getAttribute('aria-expanded') || '') + '|' + (e.getAttribute('style') || ''), "
            "parentSnapshot: parent ? ((parent.className || '') + '|' + (parent.getAttribute('style') || '')) : null "
            "}; "
            "}"
        )
    except Exception:
        return None


def _find_alternate_clickable(el):
    """When a click on `el` produced no observable effect (see
    _capture_dom_change_fingerprint), finds the nearest REAL clickable
    hit-area near it - a descendant or ancestor carrying role="button",
    an inline onclick handler, or a computed cursor:pointer style - the
    generic, structural signature of "this is actually interactive" that
    a recording can miss when it captured a plain wrapper/text node
    instead of the element that really owns the click behavior (a
    "Qty: 1" text div wrapping the real button, say, or a clickable icon
    nested a level or two inside a recorded container). Descendants are
    checked first - structurally closer to what was actually recorded,
    and the more common real case - then ancestors, up to a few levels.
    Never a text/class/id-based guess. Returns an ElementHandle, or None
    if nothing plausible is found nearby. Never raises.
    """
    try:
        handle = el.evaluate_handle(
            "e => { "
            "const isClickable = (node) => { "
            "  if (!node || node.nodeType !== 1) return false; "
            "  if (node.getAttribute('role') === 'button') return true; "
            "  if (node.hasAttribute('onclick')) return true; "
            "  try { return getComputedStyle(node).cursor === 'pointer'; } catch (err) { return false; } "
            "}; "
            "const descendants = e.querySelectorAll('*'); "
            "for (const child of descendants) { "
            "  if (child !== e && isClickable(child)) return child; "
            "} "
            "let node = e.parentElement; "
            "let depth = 0; "
            "while (node && depth < 6) { "
            "  if (isClickable(node)) return node; "
            "  node = node.parentElement; "
            "  depth += 1; "
            "} "
            "return null; "
            "}"
        )
        as_el = handle.as_element()
        return as_el
    except Exception:
        return None


# see _do_fill's own docstring - how many verify-then-retry rounds to
# attempt before giving up, and how long to wait after each attempt
# before reading the input's displayed value back to check it
FILL_VERIFY_MAX_ATTEMPTS = 3
FILL_VERIFY_POLL_MS = 200


def _do_fill(page, el, value, turbo=False):
    """Fill el using real keystroke simulation as the PRIMARY method -
    press_sequentially dispatches actual keydown/input/keyup events per
    character, which is what makes a controlled input's visible on-
    screen state update (and is what auto-advancing multi-box PIN/OTP
    inputs and input masks require to accept the value at all). A direct
    value-set (el.fill()) can make the underlying form value land
    without ever triggering that visible re-render - functionally
    correct, but nothing appears on screen, which is indistinguishable
    from a real bug to anyone watching a replay. Falls back to a direct
    value-set only if the keystroke simulation itself doesn't stick,
    verified the same way as before, so a fill still succeeds on a field
    that genuinely doesn't respond to real typing. Generic for ANY fill,
    not specific to any particular kind of field.

    Wrapped in a bounded verify-and-retry loop on top of that: reads the
    input's own DISPLAYED value back from the DOM immediately after each
    attempt (input_value() reflects exactly what's rendered for a native
    input/textarea, not some separate internal-only state), and only
    returns once it genuinely matches what was supposed to be typed - a
    confirmed real gap otherwise, not hypothetical: a fill that "worked"
    by every signal available at the moment it ran (no exception, a
    value read back correctly) can still end up NOT visible a moment
    later if the page's own controlled-input re-render (common in
    React/Vue-style forms) resets or overwrites it on its next tick,
    something a single one-shot check right after the type can't catch
    but a follow-up re-verify, one settle-wait later, does. Never an
    unbounded wait - gives up after FILL_VERIFY_MAX_ATTEMPTS rounds and
    returns whatever the last attempt actually left in the field.

    turbo=True skips press_sequentially entirely (see resolve_and_act's
    own docstring for why) and goes straight to the el.fill() fallback
    below - Playwright's own native, single-call value-set, which still
    fires the input/change events a controlled input needs to notice the
    change, just without dispatching one real keydown/input/keyup per
    character purely so a human watching a normal Replay sees the field
    visibly fill in. The verify-and-retry loop and its settle wait are
    UNCHANGED in both modes - they exist to catch a framework re-render
    overwriting the value a moment later, a real correctness concern
    turbo mode never weakens.
    """
    def _read_current_value():
        try:
            return el.input_value(timeout=1000)
        except Exception:
            return None

    for attempt in range(1, FILL_VERIFY_MAX_ATTEMPTS + 1):
        try:
            el.clear(timeout=2000)
        except Exception:
            pass
        typed_ok = False
        if not turbo:
            try:
                el.press_sequentially(value, timeout=5000)
                typed_ok = _read_current_value() == value
            except Exception:
                typed_ok = False
        if not typed_ok:
            try:
                el.fill(value, timeout=5000)
            except Exception:
                pass
        # a settle wait before the REAL check - the same "give the
        # page's own re-render a real chance to catch up first" idea
        # already used elsewhere in this file, not a new pattern
        try:
            page.wait_for_timeout(FILL_VERIFY_POLL_MS)
        except Exception:
            pass
        if _read_current_value() == value:
            if attempt > 1:
                print(
                    f"[fill-verify] input value confirmed correct on "
                    f"retry attempt {attempt}/{FILL_VERIFY_MAX_ATTEMPTS}"
                )
            return
        print(
            f"[fill-verify] WARNING: input's displayed value did not match "
            f"what was set (attempt {attempt}/{FILL_VERIFY_MAX_ATTEMPTS}) "
            f"- retrying with real keystroke simulation"
        )
    print(
        f"[fill-verify] WARNING: input's displayed value still did not "
        f"match after {FILL_VERIFY_MAX_ATTEMPTS} attempts - proceeding "
        f"anyway with whatever the last attempt left in the field"
    )


# how many ancestor levels _reveal_via_ancestor_hover will try hovering,
# nearest first, before giving up - bounds the worst case for a target
# nested unusually deep inside a menu/panel structure
HOVER_REVEAL_MAX_ANCESTOR_DEPTH = 6
# per-ancestor hover timeout and the settle pause after each one, before
# re-checking whether the target became visible
HOVER_REVEAL_HOVER_TIMEOUT_MS = 2000
HOVER_REVEAL_SETTLE_MS = 150
# bounding-box stability check before a click - how many consecutive
# matching reads are required, how far apart, and how many total
# attempts before giving up and proceeding anyway (never an unbounded
# wait - Playwright's own actionability check still applies regardless)
BOUNDING_BOX_STABLE_SAMPLE_MS = 200
BOUNDING_BOX_STABLE_MAX_ATTEMPTS = 5
# how long to wait after a click before checking whether it produced any
# observable effect at all (see _capture_dom_change_fingerprint /
# _find_alternate_clickable) - long enough for an ordinary synchronous
# UI reaction (a modal opening, a class toggling) to land, short enough
# that this never meaningfully slows down a normal replay
CLICK_NO_EFFECT_WAIT_MS = 400
# see _wait_for_modal_target_visible's own stability requirement - how
# long after a first visible+confirmed check to wait before re-checking
# the SAME target is still open, to tell a genuinely stable modal apart
# from one that flashed open and closed again almost immediately
STABILITY_RECHECK_MS = 200
# HISTORY (do not repeat the mistake of assuming a tall value is needed
# for screenshots): originally 2000px, "so a tall page needed less
# scrolling for screenshots". That reasoning was never actually true -
# _capture_screenshot's only full-page capture uses page.screenshot(
# full_page=True), which Chromium/Playwright captures via CDP's
# captureBeyondViewport, independent of the configured context viewport
# size entirely (confirmed by reading _capture_screenshot itself - no
# manual stitching/resizing of ours involved). A first attempt at
# lowering this (to 1400, to fix a DIFFERENT bug - see below) was
# reverted after a live run showed it broke the previously-working
# Select Size modal (rendered shifted off-center, stuck unresponsive for
# 28s) - that regression is real and this value's own history, not
# erased here, but note it was never actually explained WHY 1400
# specifically broke it; it may be that ANY change to this constant
# risks some CSS/JS on a given site keying off window.innerHeight in a
# way that's only discoverable by testing, not something guessable in
# advance from the number chosen.
#
# Lowered again, this time to exactly REALISTIC_VIEWPORT_HEIGHT_PX
# (900), based on a DIFFERENT, more direct finding: a live comparison of
# the working "Select Size" dialog (y=400-750 of a 2000px screenshot)
# against the broken "Select Quantity" one (y=1000-1294, content itself
# only ~294px tall) showed the quantity dialog centers itself relative
# to the FULL configured viewport height (align-items:center or
# equivalent) - it was never too TALL to fit a real window, it was only
# ever pushed below a realistic fold by OUR OWN inflated 2000px replay
# viewport. Matching the real browser viewport to the realistic
# threshold removes the mismatch at its source instead of working around
# it after the fact (scroll-retry, force-interact) - if this holds up
# under a live re-run (required before trusting this), a whole class of
# viewport-relative-centering false "out-of-viewport" results goes away
# for any site, not just this one.
REPLAY_VIEWPORT_HEIGHT_PX = 900
# ground truth for "would a REAL user's browser show this" (900px,
# matching the 720-900px range already seen in this project's own
# recorded viewport_height values) - used by _MODAL_CONTENT_PAINTED_JS/
# _is_modal_content_painted's own viewport-bounds check. Deliberately
# kept as its OWN constant, separate from REPLAY_VIEWPORT_HEIGHT_PX
# above, even now that both happen to equal 900 - they answer two
# different questions (this replay's actual browser viewport vs. the
# ground truth the paint-check validates against) that could diverge
# again if either one needs to change for its own, independent reason in
# the future.
REALISTIC_VIEWPORT_HEIGHT_PX = 900


def _is_genuinely_interactable(el):
    """Playwright's own el.is_visible() is necessary but NOT sufficient
    here: it only checks for a non-empty box and the absence of
    display:none/visibility:hidden - a dropdown/submenu item hidden via
    opacity:0 (a very common technique, since it also enables a CSS
    fade-in transition) still reports is_visible()=True, and Playwright
    itself will happily click() it with no error and no force needed,
    exactly the "resolves and clicks without exception, yet the real
    menu was never actually open" gap this whole check exists to close.

    Adds three more generic, purely computed-style/geometry signals on
    top:

    - pointer-events:none, and near-zero EFFECTIVE opacity. Effective,
      not just the element's own opacity, matters: opacity is a
      compositing property, not a normally-inherited one - a menu
      framework commonly sets opacity:0 on the dropdown PANEL (the
      container), not on each item inside it, so an item's own
      getComputedStyle().opacity reads '1' even while it's rendered
      fully transparent because an ancestor is at 0. This walks up to
      document.body multiplying every level's own opacity together, the
      same way the browser's own compositing does, to get the REAL
      rendered opacity. pointer-events, unlike opacity, genuinely is an
      inherited CSS property, so the element's own computed value
      already reflects any ancestor that set it - no walk needed there.
    - clipped-by-an-ancestor's-own-overflow:hidden - an EQUALLY common,
      DIFFERENT collapse technique from opacity: an accordion-style
      dropdown that animates open via max-height (0 -> some real value)
      on a wrapper with overflow:hidden, rather than fading in. The
      collapsed wrapper's OWN getBoundingClientRect() genuinely shrinks
      to near-zero height while collapsed, but a menu ITEM further
      inside it can still report its own, unrelated (non-zero, "as if
      already expanded") bounding box - is_visible() alone has no way
      to know the ancestor is clipping it out of view. This walks every
      ancestor up to body; whenever one has overflow/overflowX/overflowY
      set to hidden or clip, it checks whether the target's own box
      still genuinely overlaps that ancestor's CURRENT (possibly
      collapsed-to-near-zero) rendered box - if it doesn't, the target
      is effectively invisible regardless of its own geometry.

    Never a class/id/text check - reads the same generic computed-style/
    geometry signals on any element, on any site.
    """
    try:
        if not el.is_visible():
            return False
    except Exception:
        return False
    try:
        style = el.evaluate(
            "e => { "
            "const s = getComputedStyle(e); "
            "let effectiveOpacity = 1; "
            "let node = e; "
            "while (node && node.nodeType === 1) { "
            "  effectiveOpacity *= parseFloat(getComputedStyle(node).opacity); "
            "  node = node.parentElement; "
            "} "
            "const rect = e.getBoundingClientRect(); "
            "let clippedByAncestor = false; "
            "let ancestor = e.parentElement; "
            "while (ancestor && ancestor !== document.body) { "
            "  const as = getComputedStyle(ancestor); "
            "  if (as.overflow === 'hidden' || as.overflowX === 'hidden' || as.overflowY === 'hidden' "
            "      || as.overflow === 'clip' || as.overflowX === 'clip' || as.overflowY === 'clip') { "
            "    const ar = ancestor.getBoundingClientRect(); "
            "    const overlapW = Math.min(rect.right, ar.right) - Math.max(rect.left, ar.left); "
            "    const overlapH = Math.min(rect.bottom, ar.bottom) - Math.max(rect.top, ar.top); "
            "    if (overlapW <= 0 || overlapH <= 0) { clippedByAncestor = true; break; } "
            "  } "
            "  ancestor = ancestor.parentElement; "
            "} "
            "return { "
            "effectiveOpacity: effectiveOpacity, pointerEvents: s.pointerEvents, "
            "clippedByAncestor: clippedByAncestor "
            "}; "
            "}"
        )
        if style.get("effectiveOpacity") is not None and style["effectiveOpacity"] < 0.05:
            return False
        if style.get("pointerEvents") == "none":
            return False
        if style.get("clippedByAncestor"):
            return False
    except Exception:
        # couldn't read computed style - trust is_visible() alone rather
        # than blocking a click over an inconclusive check
        pass
    return True


def _reveal_via_ancestor_hover(page, el, max_depth=HOVER_REVEAL_MAX_ANCESTOR_DEPTH):
    """If `el` isn't currently GENUINELY interactable (see
    _is_genuinely_interactable), tries hovering successive DOM ancestors
    of el - the NEAREST parent first, walking up - a generic proxy for
    "this target lives inside a dropdown/submenu/mega-menu that needs
    its trigger hovered before it renders", inferred purely from el's
    own LIVE ancestor chain at the moment of replay. Never any recorded/
    hardcoded structure, tag name, class, or text - the same chain would
    be walked for any hidden target on any site, whatever its actual
    HTML looks like.

    A no-op (immediately returns True) when el is already genuinely
    interactable - so calling this unconditionally before every click
    costs nothing extra for the ordinary, ready-to-click case. Stops
    hovering as soon as el becomes interactable, or after max_depth
    ancestors have been tried, and always leaves el in whatever state it
    ends up in - the caller's own stability check and Playwright's own
    actionability check still apply on top of this regardless.
    """
    if _is_genuinely_interactable(el):
        return True

    try:
        ancestors = el.locator("xpath=ancestor::*")
        ancestor_count = ancestors.count()
    except Exception:
        return False

    for depth in range(1, min(max_depth, ancestor_count) + 1):
        try:
            # ancestors is in document order (root first); the nearest
            # parent is the LAST entry, so depth counts backward from it
            ancestor = ancestors.nth(ancestor_count - depth)
            ancestor.hover(timeout=HOVER_REVEAL_HOVER_TIMEOUT_MS)
        except Exception:
            continue
        try:
            page.wait_for_timeout(HOVER_REVEAL_SETTLE_MS)
            if _is_genuinely_interactable(el):
                logger.debug(
                    "hover-reveal: target became interactable after "
                    "hovering ancestor at depth %d", depth,
                )
                return True
        except Exception:
            pass

    return _is_genuinely_interactable(el)


# how long to hold the mouse at the target before pressing down (lets a
# real mouseenter/hover-triggered handler settle first) and how long to
# hold the button down before releasing (mimics a genuine human click
# rather than an instantaneous down-up pair some debounced/threshold
# JS logic could otherwise treat differently) - matches natural human
# movement/press timing (~50-100ms), short enough to never meaningfully
# slow down a normal replay, long enough to be a real, observable gap in
# event timing
TRUSTED_CLICK_HOVER_PAUSE_MS = 80
TRUSTED_CLICK_DOWN_UP_PAUSE_MS = 80


def _trusted_mouse_click(page, el):
    """Dispatches a real, OS-level mouse sequence (move -> brief pause ->
    down -> brief pause -> up) via Playwright's low-level page.mouse API,
    computed fresh against el's own CURRENT bounding box - the fallback
    mechanism for a click already confirmed (by the caller) to have
    produced no observable effect via the ordinary el.click()/smart_
    click() path, or for the first real click on a target that only
    just became interactable via an ancestor hover-reveal (a dropdown/
    mega-menu item, say). Deliberately generic - takes only a resolved
    element, never any recorded text/site-specific value, so it applies
    identically to any click on any site.

    Never replaces the PRIMARY, already-working click path for an
    ordinary target - only used where the caller has already established
    a specific reason to prefer real mouse-hardware-level events over
    el.click()'s own internal dispatch (see the two call sites: the
    hover-reveal case, and the no-observable-effect retry case).

    Returns True once the full sequence was dispatched, False if el has
    no measurable bounding box (a genuinely zero-size element - the
    caller should fall back to smart_click()'s own force-click handling
    for that case rather than this) or the sequence itself raised. Never
    raises.
    """
    try:
        box = el.bounding_box()
    except Exception:
        box = None
    if not box or not box.get("width") or not box.get("height"):
        return False
    x = box["x"] + box["width"] / 2
    y = box["y"] + box["height"] / 2
    try:
        page.mouse.move(x, y)
        page.wait_for_timeout(TRUSTED_CLICK_HOVER_PAUSE_MS)
        page.mouse.down()
        page.wait_for_timeout(TRUSTED_CLICK_DOWN_UP_PAUSE_MS)
        page.mouse.up()
        return True
    except Exception:
        return False


# finds the smallest genuinely-interactive DESCENDANT of a matched click
# container, if one exists - the generic version of "a 'label + chevron'
# control's real hit-target is often the small icon, not the label text
# next to it" (confirmed real: a working Size-edit click resolved, via
# fallback, to a 6x3px chevron SVG, not the visible text container a
# same-shaped Qty-edit click was landing on instead). Never matches the
# container itself, and never a descendant that's the SAME SIZE OR
# LARGER than the container (that's not "more specific", just a
# same-or-bigger wrapper) - only a genuinely smaller, nested control.
# Every signal checked here is purely structural/generic (tag, role,
# computed cursor style, or a native onclick) - never any recorded/
# hardcoded text, site, or shape, and never anything requiring a CDP
# session or framework-internal (React or otherwise) properties - see
# the SAFETY FIX note right below for why.
# SAFETY FIX (regression found and reproduced after the initial version
# of this check shipped): the React-fiber/__reactProps-based handler
# detection has been REMOVED entirely - not because it was ever shown to
# be the actual cause of a real crash (it never used a CDP session,
# contrary to an initial suspicion - grep confirms zero CDP/
# getEventListeners usage anywhere in this file), but as a deliberate,
# requested safety measure: it reads framework-internal properties that
# are unnecessary complexity for what this check needs.
#
# The REAL bug, found by actually reproducing a failure rather than
# guessing: this logic previously applied to ANY matched container
# regardless of size, and simply preferred whatever smaller interactive
# descendant it could find, with no check that the descendant was
# actually RELEVANT to the click. Reproduced concretely with nothing
# more exotic than a plain <svg cursor:pointer> - a 600x150px banner
# containing an unrelated 8x8px dismiss icon got its click silently
# redirected to that icon instead of the banner's own real link,
# landing on a completely wrong destination. On a real page, a misclick
# like that landing on the wrong control (a close/remove/share icon,
# say) is exactly the kind of thing that can cascade into an
# unrecoverable "page/context/browser has been closed" - a
# fundamentally different, more serious problem than "which specific
# pixel gets clicked" alone suggested.
#
# Fixed by gating this whole check to only ever apply to a container
# that's already COMPACT - roughly the size of a single inline control
# (a size/quantity selector, a dropdown trigger), the actual "label +
# small affordance icon" pattern this exists for - never a banner,
# card, section, or any other large clickable region, where "some
# smaller clickable thing exists somewhere inside" is true of almost
# every container and therefore not a meaningful signal at all. A large
# container simply skips this check entirely and clicks its own center
# exactly as it always did before this feature existed.
_MORE_SPECIFIC_DESCENDANT_MAX_WIDTH = 300
_MORE_SPECIFIC_DESCENDANT_MAX_HEIGHT = 100

_MORE_SPECIFIC_DESCENDANT_JS = (
    "(container) => { "
    "  const cRect = container.getBoundingClientRect(); "
    "  const cArea = cRect.width * cRect.height; "
    "  if (cArea <= 0) return null; "
    f"  if (cRect.width > {_MORE_SPECIFIC_DESCENDANT_MAX_WIDTH} || cRect.height > {_MORE_SPECIFIC_DESCENDANT_MAX_HEIGHT}) return null; "
    "  function isCandidate(node) { "
    "    const tag = node.tagName ? node.tagName.toLowerCase() : ''; "
    "    if (tag === 'svg') return true; "
    "    const role = node.getAttribute ? node.getAttribute('role') : null; "
    "    if (role === 'button') return true; "
    "    if (node.hasAttribute && node.hasAttribute('onclick')) return true; "
    "    if (node.onclick) return true; "
    "    try { "
    "      return getComputedStyle(node).cursor === 'pointer'; "
    "    } catch (e) { return false; } "
    "  } "
    "  const descendants = container.querySelectorAll('*'); "
    "  let best = null; "
    "  let bestArea = Infinity; "
    "  for (const node of descendants) { "
    "    if (!isCandidate(node)) continue; "
    "    const r = node.getBoundingClientRect(); "
    "    const area = r.width * r.height; "
    "    if (area <= 0 || area >= cArea) continue; "
    "    if (area < bestArea) { bestArea = area; best = node; } "
    "  } "
    "  return best; "
    "}"
)


def _find_more_specific_clickable_descendant(el):
    """See _MORE_SPECIFIC_DESCENDANT_JS. Returns an ElementHandle for the
    smallest genuinely-interactive descendant found within el's own
    bounding box, or None if el has no such descendant (the ordinary
    case - a ready-to-click button/link with no nested icon-affordance
    at all) or the check itself couldn't run. Never raises.
    """
    try:
        handle = el.evaluate_handle(_MORE_SPECIFIC_DESCENDANT_JS)
    except Exception:
        return None
    try:
        descendant_el = handle.as_element()
    except Exception:
        descendant_el = None
    if descendant_el is None:
        try:
            handle.dispose()
        except Exception:
            pass
        return None
    return descendant_el


def _describe_element_for_log(el):
    """Tag/class/data-testid/role, the same shape CLICK-DIAG already logs
    elsewhere in this file - reused here for the container-vs-descendant
    click-resolution log. Returns None on any error, never raises."""
    try:
        return el.evaluate(
            "e => ({ "
            "tag: e.tagName ? e.tagName.toLowerCase() : null, "
            "cls: e.className ? String(e.className) : '', "
            "testid: e.getAttribute ? e.getAttribute('data-testid') : null, "
            "role: e.getAttribute ? e.getAttribute('role') : null "
            "})"
        )
    except Exception:
        return None


# TEMPORARY, UNCONDITIONAL diagnostic (not gated behind a flag, not
# tied to any recorded text/testid - runs the same way for every click,
# so it works regardless of which specific element/site produced a
# silent no-reaction click): document.elementsFromPoint (PLURAL)
# returns the FULL stack of elements at a viewport point, topmost
# first - not just the single element document.elementFromPoint alone
# would report (what the existing CLICK-DIAG block already checks). An
# invisible overlay silently absorbing a click sits ABOVE the real
# target in this same stack, at the exact coordinate about to be
# clicked. Includes each entry's own computed z-index/opacity/pointer-
# events (a click can be silently absorbed OR silently pass through
# depending on which), and flags which stack entry IS the element
# Playwright actually resolved via a strict DOM identity (===) check -
# run in the SAME evaluate call as the elementsFromPoint read itself,
# never a separate comparison that could race against the DOM changing
# in between. Called twice per click (see the two call sites) - once
# immediately before the click fires, once immediately after - so even
# a click that opens no dialog at all can be checked for ANY reaction
# whatsoever (a hover/active class, anything) at the exact point
# clicked.
_ELEMENTS_FROM_POINT_JS = (
    "(node0, [px, py]) => { "
    "  const els = document.elementsFromPoint(px, py) || []; "
    "  return els.map(e => { "
    "    const s = getComputedStyle(e); "
    "    return { "
    "      tag: e.tagName ? e.tagName.toLowerCase() : null, "
    "      cls: e.className ? String(e.className) : '', "
    "      testid: e.getAttribute ? e.getAttribute('data-testid') : null, "
    "      zIndex: s.zIndex, "
    "      opacity: s.opacity, "
    "      pointerEvents: s.pointerEvents, "
    "      isResolvedElement: (e === node0) "
    "    }; "
    "  }); "
    "}"
)


def _log_elements_from_point_stack(el, x, y, label=""):
    """See _ELEMENTS_FROM_POINT_JS. el is the element Playwright actually
    resolved/is about to click (or just clicked) - evaluate() is called
    ON el specifically so the JS side receives it as node0 for the
    identity comparison, rather than a separate, potentially-stale
    reference. label distinguishes BEFORE/AFTER in the printed output
    when this is called twice for the same click. Never raises; logs
    nothing on failure (still cheap and safe to call unconditionally).
    """
    try:
        stack = el.evaluate(_ELEMENTS_FROM_POINT_JS, [x, y])
    except Exception:
        stack = None
    if not stack:
        return
    prefix = f"[elements-from-point{(' ' + label) if label else ''}]"
    print(f"{prefix} stack at ({x:.0f}, {y:.0f}), topmost first:")
    for idx, entry in enumerate(stack):
        marker = " <-- RESOLVED ELEMENT" if entry.get("isResolvedElement") else ""
        print(
            f"{prefix}   [{idx}] tag={entry.get('tag')!r} "
            f"class={entry.get('cls')!r} testid={entry.get('testid')!r} "
            f"z-index={entry.get('zIndex')!r} opacity={entry.get('opacity')!r} "
            f"pointer-events={entry.get('pointerEvents')!r}{marker}"
        )
    top = stack[0]
    print(f"{prefix} TOP ELEMENT pointer-events={top.get('pointerEvents')!r}")
    if top.get("pointerEvents") == "none":
        print(
            f"{prefix} WARNING: topmost element has pointer-events:none - "
            f"clicks pass THROUGH it to whatever's beneath (index [1] onward)"
        )


def _wait_for_bounding_box_stable(page, el, max_attempts=BOUNDING_BOX_STABLE_MAX_ATTEMPTS):
    """Two consecutive bounding-box reads a short interval apart, tried
    up to max_attempts times - confirms el is not still mid CSS
    transition/animation (a dropdown/panel still expanding, say) before
    a click is attempted against it. Bounded, never an unbounded wait:
    gives up and returns False (caller proceeds with the click anyway -
    this is an extra confidence signal, not a hard gate) after
    max_attempts inconclusive tries.
    """
    def _read_box():
        try:
            return el.bounding_box()
        except Exception:
            return None

    prev = _read_box()
    for _ in range(max_attempts):
        page.wait_for_timeout(BOUNDING_BOX_STABLE_SAMPLE_MS)
        cur = _read_box()
        if prev and cur and (
            abs(prev.get("x", 0) - cur.get("x", 0)) < 1
            and abs(prev.get("y", 0) - cur.get("y", 0)) < 1
            and abs(prev.get("width", 0) - cur.get("width", 0)) < 1
            and abs(prev.get("height", 0) - cur.get("height", 0)) < 1
        ):
            return True
        prev = cur
    return False


def _warn_if_resolved_identity_mismatched(el, lp, action_type):
    """Generic sanity check: does the element a locator tier actually
    resolved to still look like the RECORDING's own description of it -
    same visible text, same aria-label, same href (only when one was
    recorded for each)? A tier can find SOME element that technically
    satisfies its own narrow matching signal (an exact href match, say)
    while a page's dynamic content means it isn't genuinely the intended
    element - a duplicate href living elsewhere in the DOM, a different
    entry in a search/typeahead list that happened to match first,
    unrelated to the real one. Never blocks the click or changes
    strategy/found/success - purely an immediate, visible console
    warning, so a "misclick due to dynamic content" surfaces right away
    instead of only showing up later via a failed navigation/effect
    check. Compares loosely (case-insensitive substring, either
    direction, for text/aria-label) since minor recorded-vs-live
    wording differences are normal and not evidence of anything wrong;
    href is compared exactly, since a genuinely different destination is
    exactly what this exists to catch.
    """
    if action_type not in ("click", "dblclick", "right_click"):
        return
    recorded_text = (lp.get("text") or lp.get("element_text") or "").strip()
    recorded_aria = (lp.get("aria_label") or "").strip()
    recorded_href = (lp.get("href") or "").strip()
    if not recorded_text and not recorded_aria and not recorded_href:
        return

    try:
        live_text = (el.inner_text(timeout=1000) or "").strip()
    except Exception:
        live_text = ""
    try:
        live_aria = (el.get_attribute("aria-label", timeout=1000) or "").strip()
    except Exception:
        live_aria = ""
    try:
        live_href = (el.get_attribute("href", timeout=1000) or "").strip()
    except Exception:
        live_href = ""

    def _loose_mismatch(recorded, live):
        r, l = recorded.lower(), live.lower()
        return r not in l and l not in r

    mismatches = []
    if recorded_text and live_text and _loose_mismatch(recorded_text, live_text):
        mismatches.append(f"text: recorded {recorded_text!r} vs actual {live_text!r}")
    if recorded_aria and live_aria and _loose_mismatch(recorded_aria, live_aria):
        mismatches.append(f"aria-label: recorded {recorded_aria!r} vs actual {live_aria!r}")
    if recorded_href and live_href and recorded_href != live_href:
        mismatches.append(f"href: recorded {recorded_href!r} vs actual {live_href!r}")

    if mismatches:
        print(
            f"[misclick-check] WARNING: the element resolved for this "
            f"{action_type} may not match the recording - {'; '.join(mismatches)} "
            f"- possible misclick due to dynamic page content"
        )


def _verify_click_target_hit_test(page, el, lp):
    """Harder than _warn_if_resolved_identity_mismatched above: that one
    checks whether the LOCATOR resolve_and_act's tier search found looks
    right; this checks whether the COORDINATE Playwright is actually
    about to click lands on that same element at all, using
    document.elementFromPoint() - the same generic hit-test signal the
    bounding_box fallback tier already uses elsewhere in this file. A
    tier can resolve the CORRECT element by selector while the real
    on-screen click point still lands on a different, overlapping/
    adjacent interactive element (two adjacent buttons/links sharing
    near-identical geometry) - Playwright's own click() has no way to
    know that's wrong, since IT dispatches at that same coordinate
    regardless of what visually renders there.

    Returns (ok, reason). ok=False means the caller should NOT click -
    fail this tier fast (falling through to the next one, exactly like
    any other tier-level failure) rather than silently clicking
    whatever's really there. A genuinely different DOM node at that
    point is not automatically treated as wrong: if it's el itself, an
    ancestor/descendant of el (an icon inside a button, say), or its own
    identity loosely matches the recorded text/href anyway, this passes
    - only an UNRELATED element with a DIFFERENT identity fails it.
    Never raises; anything inconclusive (no box, evaluate failure) is
    treated as passing, since this check's whole job is catching a
    CONFIRMED mismatch, not second-guessing an ordinary click.
    """
    try:
        box = el.bounding_box()
    except Exception:
        return True, None
    if not box or not box.get("width") or not box.get("height"):
        return True, None

    x = box["x"] + box["width"] / 2
    y = box["y"] + box["height"] / 2

    try:
        is_related = el.evaluate(
            "(e, [px, py]) => { "
            "const hitEl = document.elementFromPoint(px, py); "
            "return !!hitEl && (e === hitEl || e.contains(hitEl) || hitEl.contains(e)); "
            "}",
            [x, y],
        )
    except Exception:
        return True, None
    if is_related:
        return True, None

    try:
        hit_info = page.evaluate(
            "([px, py]) => { "
            "const hitEl = document.elementFromPoint(px, py); "
            "if (!hitEl) return null; "
            "const link = hitEl.closest('a'); "
            "return { "
            "text: (hitEl.innerText || '').trim().slice(0, 80), "
            "href: link ? link.getAttribute('href') : null, "
            "ariaLabel: hitEl.getAttribute('aria-label') "
            "}; "
            "}",
            [x, y],
        )
    except Exception:
        return True, None
    if not hit_info:
        return True, None

    return _identity_hit_matches(lp, hit_info, "click coordinate")


def _identity_hit_matches(lp, hit_info, where):
    """Shared comparison used by _verify_click_target_hit_test above (a
    tier-resolved element's own bounding-box center) and the raw-
    coordinate bounding_box last-resort tier further down in
    resolve_and_act (which has no resolved Locator at all, only whatever
    document.elementFromPoint() reports at the recorded x/y) - same
    generic, content-based identity check either way: recorded text/
    aria-label/href from the ORIGINAL recording's locator_profile against
    whatever is really rendered at that point right now. `where` only
    changes the wording of a failure reason, never the logic. Returns
    (ok, reason) exactly like _verify_click_target_hit_test - ok=False
    only for a CONFIRMED mismatch (recorded identity present and none of
    it matches); nothing recorded to compare against is inconclusive,
    not a failure.
    """
    recorded_text = (lp.get("text") or lp.get("element_text") or "").strip().lower()
    recorded_aria = (lp.get("aria_label") or "").strip().lower()
    recorded_href = (lp.get("href") or "").strip()
    hit_text = (hit_info.get("text") or "").strip().lower()
    hit_aria = (hit_info.get("ariaLabel") or "").strip().lower()
    hit_href = (hit_info.get("href") or "").strip()

    def _loose_match(a, b):
        return bool(a) and bool(b) and (a in b or b in a)

    if _loose_match(recorded_text, hit_text) or _loose_match(recorded_aria, hit_aria):
        return True, None
    if recorded_href and hit_href and recorded_href == hit_href:
        return True, None
    if not recorded_text and not recorded_aria and not recorded_href:
        # nothing recorded to compare against at all - inconclusive, not a confirmed mismatch
        return True, None

    hit_label = hit_info.get("text") or hit_info.get("ariaLabel") or hit_info.get("href") or "(unlabeled element)"
    recorded_label = lp.get("text") or lp.get("element_text") or lp.get("aria_label") or lp.get("href") or "(unrecorded)"
    return False, (
        f"a different element is actually at the {where} - "
        f"recorded target was {recorded_label!r}, but {hit_label!r} is really there"
    )


def _verify_post_click_identity(page, lp):
    """Every identity check elsewhere in this file (_warn_if_resolved_
    identity_mismatched, _verify_click_target_hit_test, the bounding_box
    last resort's own check) runs BEFORE the click fires, against
    whatever's resolved/rendered at that moment - none of them can catch
    a click that started out square on the right element and still ended
    up somewhere else, e.g. a mousedown-time reflow that swaps visible
    content out from under a screen coordinate the click is already
    committed to. This runs immediately AFTER the click, reading
    document.activeElement - the browser's own, generic record of
    "what actually just received the interaction" - and compares its
    text/aria-label/href against the recording's own description of the
    intended target, via the same _identity_hit_matches comparison used
    above.

    Deliberately conservative: nothing recorded to compare against,
    nothing actually focused (activeElement is body/html - the common,
    unremarkable case for a plain styled <div>/<span> click target that
    was never going to take focus at all), or a focused element that
    exposes none of the compared signals are all treated as inconclusive,
    never a failure - requiring a focus-based match universally would
    misflag huge numbers of perfectly ordinary clicks. Only a genuine,
    confirmed mismatch (something WAS recorded, something IS focused, and
    neither matches) is reported. Returns (ok, reason); never raises.
    """
    recorded_testid = (lp.get("attributes") or {}).get("data-testid")
    if not (lp.get("text") or lp.get("element_text") or lp.get("aria_label") or lp.get("href")):
        logger.debug(
            "click-diagnostic: after click - recorded data-testid=%r, but "
            "nothing recorded to compare against (no text/aria-label/href) - "
            "post-click identity check inconclusive",
            recorded_testid,
        )
        return True, None
    try:
        active = page.evaluate(
            "() => { "
            "const e = document.activeElement; "
            "if (!e || e === document.body || e === document.documentElement) return null; "
            "const link = e.closest('a'); "
            "return { "
            "text: (e.innerText || e.textContent || '').trim().slice(0, 80), "
            "href: link ? link.getAttribute('href') : e.getAttribute('href'), "
            "ariaLabel: e.getAttribute('aria-label'), "
            "testid: e.getAttribute('data-testid'), "
            "tag: e.tagName.toLowerCase() "
            "}; "
            "}"
        )
    except Exception:
        active = None
    logger.debug(
        "click-diagnostic: after click - recorded data-testid=%r text=%r | "
        "actually focused: %s",
        recorded_testid, lp.get("text") or lp.get("element_text"), active,
    )
    if not active or not (active.get("text") or active.get("ariaLabel") or active.get("href")):
        return True, None
    return _identity_hit_matches(lp, active, "post-click focus target")


def _is_zero_size_element(el):
    """True when el currently occupies NO layout space at all (bounding
    box missing, or width and height both 0) - the generic, content-
    agnostic signature of a display:none element, or one nested inside a
    display:none ancestor (a modal/dialog/drawer container that was
    recorded as opening but never actually did). Deliberately different
    from a merely opacity:0/visibility:hidden toggle - a technique real
    sites commonly use for custom checkbox/radio widgets while keeping
    the native input laid out at its normal size and position - which
    still reports a real, non-zero bounding box here. That distinction
    is exactly what lets the force=True fallbacks below stay safe for
    the legitimate hidden-toggle case while refusing to silently
    "succeed" by dispatching a click/check at a target that was never
    actually rendered on the page. Never raises; a bounding_box() that
    itself fails is treated as zero-size (the safer default - refuse the
    force fallback rather than risk a false success).
    """
    try:
        box = el.bounding_box()
    except Exception:
        return True
    if not box:
        return True
    return box.get("width", 0) <= 0 and box.get("height", 0) <= 0


def _wait_for_option_list_stable(
    page, el,
    interval_ms=OPTION_LIST_STABLE_INTERVAL_MS,
    max_attempts=OPTION_LIST_STABLE_MAX_ATTEMPTS,
):
    """If el's parent has multiple sibling children - the generic,
    structural shape of "one option among several in a list" (a search/
    typeahead suggestion, a dropdown's options, a filter list) - waits
    for that set of siblings' visible text to read the SAME on two
    consecutive checks before returning, a proxy for "this list has
    finished populating/re-rendering" without needing to detect exactly
    when the container was added or changed. A no-op (returns
    immediately, True) when el's parent doesn't look like a list at all
    (fewer than 2 children) - so this costs nothing for an ordinary,
    non-list click target. Bounded: gives up after max_attempts
    inconclusive checks and returns False, never an open-ended wait -
    the caller proceeds with the click regardless of the outcome, this
    is a best-effort settle, not a hard gate.
    """
    def _snapshot():
        try:
            return el.evaluate(
                "e => { "
                "const p = e.parentElement; "
                "if (!p || p.children.length < 2) return null; "
                "return Array.from(p.children).map(c => (c.innerText || '').trim()).join('|'); "
                "}"
            )
        except Exception:
            return None

    prev = _snapshot()
    if prev is None:
        return True

    for _ in range(max_attempts):
        page.wait_for_timeout(interval_ms)
        cur = _snapshot()
        if cur == prev:
            return True
        prev = cur
    logger.debug("option-list-stable: gave up after %d attempts, still changing", max_attempts)
    return False


def smart_click(page, selector_or_locator, fallback_coords=None, standard_timeout=5000):
    """Click something that may report a ZERO-SIZE bounding box even
    though it's real and visually clickable - an icon-wrapper div with no
    explicit width/height, an absolutely-positioned inner element whose
    parent collapses to 0x0, or a clickable target rendered entirely via
    a ::before/::after pseudo-element. Playwright's own actionability
    wait (and even a plain force=True click) still needs SOME coordinate
    to click at; a genuinely 0x0 box has none, so both keep failing no
    matter how long they're given - the standard measurement-based retry
    loop can burn minutes discovering that before ever giving up. This
    checks the CURRENT bounding_box() up front and, only for the
    zero-size case, skips straight to strategies that don't depend on a
    measured box at all.

    selector_or_locator may be a CSS selector string or an
    already-resolved Locator. fallback_coords, if given, is a
    {"x": ..., "y": ...} viewport point (typically the recorded
    bounding_box's center) to click as a last resort. standard_timeout
    lets a caller preserve its own pre-existing timeout for the ordinary,
    non-zero-size case (5000ms matches this file's own long-standing
    convention for a plain click elsewhere) - only ever affects the
    "standard" branch below, never the bounded fallback timeouts.

    Returns the strategy that succeeded: "standard", "force",
    "js_click", or "coordinate". Raises the last exception if every
    applicable strategy fails.
    """
    target = (
        page.locator(selector_or_locator)
        if isinstance(selector_or_locator, str)
        else selector_or_locator
    )

    try:
        box = target.bounding_box()
    except Exception:
        box = None

    if box and box.get("width") and box.get("height"):
        # measurable, normal-sized element - existing standard behavior,
        # completely unchanged
        target.click(timeout=standard_timeout)
        return "standard"

    # zero-size (or unmeasurable) - the standard retry loop is skipped
    # entirely here, not just shortened, since nothing it does can ever
    # succeed against a box with no real area. Each fallback gets its
    # own short, bounded timeout so a genuine failure still fails fast
    # instead of reintroducing the multi-minute delay this exists to fix.
    last_err = None

    try:
        target.click(timeout=SMART_CLICK_FALLBACK_TIMEOUT_MS, force=True)
        return "force"
    except Exception as e:
        last_err = e

    try:
        target.evaluate("el => el.click()", timeout=SMART_CLICK_FALLBACK_TIMEOUT_MS)
        return "js_click"
    except Exception as e:
        last_err = e

    if fallback_coords and fallback_coords.get("x") is not None and fallback_coords.get("y") is not None:
        try:
            # mouse.click() has no timeout parameter of its own (it's a
            # direct, immediate input dispatch, not an actionability-
            # waiting call) - it either completes right away or raises
            page.mouse.click(fallback_coords["x"], fallback_coords["y"])
            return "coordinate"
        except Exception as e:
            last_err = e

    raise last_err or RuntimeError("smart_click: zero-size element and no fallback strategy succeeded")


def _find_in_iframes(page, lp):
    """Generic same-origin iframe fallback for fill/select: page.locator()
    never searches inside an iframe's own document (a separate document
    entirely) - only frame_locator() does, and only when explicitly
    pointed at that specific iframe. Tries the same stable signals
    resolve_and_act already prioritizes at the top level - test-
    automation attributes, id, name, aria-label, placeholder, then the
    recorded css_path/xpath - inside every iframe on the page, in the
    same priority order, stopping at the first unique match. No
    knowledge of what site or field this is; purely "the top document
    had nothing, check same-origin iframes before giving up," which
    applies to any framework that renders a form (or part of one) inside
    an iframe, on any site.
    """
    attrs = lp.get("attributes") or {}
    try:
        iframe_count = page.locator("iframe").count()
    except Exception:
        return None
    if not iframe_count:
        return None

    attr_candidates = (
        ("data-testid", attrs.get("data-testid")),
        ("data-test", attrs.get("data-test")),
        ("data-cy", attrs.get("data-cy")),
        ("id", lp.get("id")),
        ("name", attrs.get("name") or lp.get("name")),
        ("aria-label", attrs.get("aria-label") or lp.get("aria_label")),
        ("placeholder", attrs.get("placeholder") or lp.get("placeholder")),
    )

    for i in range(iframe_count):
        try:
            fl = page.frame_locator(f"iframe >> nth={i}")
        except Exception:
            continue
        for attr, value in attr_candidates:
            if not value:
                continue
            try:
                loc = fl.locator(f'[{attr}="{value}"]')
                if loc.count() == 1:
                    return loc.first
            except Exception:
                continue
        css_path = lp.get("css_path")
        if css_path:
            try:
                loc = fl.locator(css_path)
                if loc.count() == 1:
                    return loc.first
            except Exception:
                pass
        xpath = lp.get("xpath")
        if xpath:
            try:
                loc = fl.locator(f"xpath={xpath}")
                if loc.count() == 1:
                    return loc.first
            except Exception:
                pass
    return None


def _locator_findable(page, lp):
    """Just the SEARCH half of resolve_and_act's tier list below (plus
    the iframe fallback) - no action attempted, purely "does anything on
    the page match this locator profile right now." Same finder
    functions, same priority order, minus position_fallback (that tier
    is about accepting a DIFFERENT element once the real one is
    confirmed gone - not relevant to "has the real recorded target
    appeared yet") and minus the value-as-text tier (needs an action's
    own value to mean anything). Used by the navigate lookahead below to
    confirm a destination page is actually usable, not just that its URL
    or network activity settled.
    """
    attrs = lp.get("attributes") or {}
    finders = (
        lambda: _by_attr(page, "data-testid", attrs.get("data-testid")),
        lambda: _by_attr(page, "data-test", attrs.get("data-test")),
        lambda: _by_attr(page, "data-cy", attrs.get("data-cy")),
        lambda: _find_by_id(page, lp),
        lambda: _by_attr(page, "name", attrs.get("name")),
        lambda: _by_attr(page, "aria-label", attrs.get("aria-label")),
        lambda: _by_attr(page, "placeholder", attrs.get("placeholder")),
        lambda: _by_attr(page, "title", attrs.get("title")),
        lambda: _find_by_role(page, lp, attrs),
        lambda: _find_by_href(page, lp),
        lambda: _find_by_text_tag(page, lp),
        lambda: _find_by_css(page, lp),
        lambda: _find_by_xpath(page, lp),
    )
    for finder in finders:
        try:
            if finder() is not None:
                return True
        except Exception:
            continue
    try:
        return _find_in_iframes(page, lp) is not None
    except Exception:
        return False


def _hover_recorded_ancestor_if_not_findable(page, lp, max_hops=HOVER_REVEAL_MAX_ANCESTOR_DEPTH):
    """Pre-resolution reveal for a click target that doesn't exist in the
    DOM AT ALL yet, not merely one that's present-but-hidden -
    _reveal_via_ancestor_hover further up handles the latter (it walks a
    LIVE resolved element's own ancestors), but a tier can only resolve
    something to walk from in the first place. Many real dropdown/
    submenu/mega-menu implementations don't just CSS-hide their nested
    items until a trigger is hovered - they don't render them into the
    DOM at all, so every locator tier reports "not found" simultaneously,
    identical to genuinely-missing content, unless something hovers the
    right ancestor FIRST.

    Generic and structural, exactly like _find_by_position's own
    approach: derives candidate ancestor selectors purely by trimming
    trailing segments off the RECORDED css_path (never live DOM
    inspection, since there may be nothing live to inspect yet), tries
    progressively higher ancestors (nearest parent first) as CSS
    selectors, hovers each candidate that actually exists, and stops as
    soon as the real target becomes findable via _locator_findable.
    Gated on the target genuinely not being findable already - an
    ordinary, already-visible nested click (a footer link three divs
    deep, say) costs nothing extra, since this returns immediately.
    Never blocks or fails the step on its own: if no ancestor prefix ever
    reveals it, resolution proceeds to the normal tier loop exactly as
    before, which then fails on its own merits.
    """
    css_path = lp.get("css_path")
    if not css_path:
        return
    if _locator_findable(page, lp):
        return

    segments = [s.strip() for s in css_path.split(">") if s.strip()]
    if len(segments) < 2:
        return

    for hops in range(1, min(max_hops, len(segments) - 1) + 1):
        prefix = " > ".join(segments[:-hops])
        if not prefix:
            break
        try:
            ancestor = page.locator(prefix).first
            if ancestor.count() == 0:
                continue
            ancestor.hover(timeout=HOVER_REVEAL_HOVER_TIMEOUT_MS)
        except Exception:
            continue
        try:
            page.wait_for_timeout(HOVER_REVEAL_SETTLE_MS)
        except Exception:
            pass
        if _locator_findable(page, lp):
            logger.debug(
                "recorded-ancestor hover-reveal: target became findable "
                "after hovering recorded ancestor prefix %r (%d hop(s) up)",
                prefix, hops,
            )
            return


def _resolve_element(page, lp):
    """Finds and returns the Playwright Locator for lp using the same finder tier list."""
    if not isinstance(lp, dict):
        return None
    attrs = lp.get("attributes") or {}
    finders = (
        lambda: _by_attr(page, "data-testid", attrs.get("data-testid")),
        lambda: _by_attr(page, "data-test", attrs.get("data-test")),
        lambda: _by_attr(page, "data-cy", attrs.get("data-cy")),
        lambda: _find_by_id(page, lp),
        lambda: _by_attr(page, "name", attrs.get("name") or lp.get("name")),
        lambda: _by_attr(page, "aria-label", attrs.get("aria-label") or lp.get("aria_label")),
        lambda: _by_attr(page, "placeholder", attrs.get("placeholder") or lp.get("placeholder")),
        lambda: _by_attr(page, "title", attrs.get("title") or lp.get("title")),
        lambda: _find_by_role(page, lp, attrs),
        lambda: _find_by_href(page, lp),
        lambda: _find_by_text_tag(page, lp),
        lambda: _find_by_css(page, lp),
        lambda: _find_by_xpath(page, lp),
    )
    for finder in finders:
        try:
            loc = finder()
            if loc is not None:
                return loc
        except Exception:
            continue
    try:
        return _find_in_iframes(page, lp)
    except Exception:
        return None


def _resolve_element_with_strategy(page, lp):
    """Same finder list, same order, same behavior as _resolve_element()
    above - NOT a second locator engine, just a version that also reports
    WHICH tier matched. Needed because _resolve_element() itself only
    ever returns the Locator, discarding which finder actually hit; the
    new validate_text/validate_attribute/validate_visible/validate_value/
    validate_enabled actions (see their handlers further down) need the
    strategy name for their locator_report (see
    _describe_locator_resolution). Kept in sync with _resolve_element() by
    construction: both call the exact same finder functions, in the exact
    same order - a change to one's tier list without the other would be
    an easy regression to introduce, so if _resolve_element() ever gains/
    reorders a tier, this must be updated identically.
    """
    if not isinstance(lp, dict):
        return None, None
    attrs = lp.get("attributes") or {}
    finders = (
        ("data-testid", lambda: _by_attr(page, "data-testid", attrs.get("data-testid"))),
        ("data-test", lambda: _by_attr(page, "data-test", attrs.get("data-test"))),
        ("data-cy", lambda: _by_attr(page, "data-cy", attrs.get("data-cy"))),
        ("id", lambda: _find_by_id(page, lp)),
        ("name", lambda: _by_attr(page, "name", attrs.get("name") or lp.get("name"))),
        ("aria-label", lambda: _by_attr(page, "aria-label", attrs.get("aria-label") or lp.get("aria_label"))),
        ("placeholder", lambda: _by_attr(page, "placeholder", attrs.get("placeholder") or lp.get("placeholder"))),
        ("title", lambda: _by_attr(page, "title", attrs.get("title") or lp.get("title"))),
        ("role", lambda: _find_by_role(page, lp, attrs)),
        ("href", lambda: _find_by_href(page, lp)),
        ("text+tag", lambda: _find_by_text_tag(page, lp)),
        ("css_path", lambda: _find_by_css(page, lp)),
        ("xpath", lambda: _find_by_xpath(page, lp)),
    )
    for strategy, finder in finders:
        try:
            loc = finder()
            if loc is not None:
                return loc, strategy
        except Exception:
            continue
    try:
        loc = _find_in_iframes(page, lp)
        if loc is not None:
            return loc, "xpath"
    except Exception:
        pass
    return None, None


def _resolve_with_timeout(page, lp, timeout_ms=None, poll_ms=None):
    """Bounded poll of _resolve_element_with_strategy(): stop immediately
    once found, otherwise keep re-trying the SAME 12-level chain until
    timeout_ms elapses, then give up - no infinite retries. Uses the
    centralized LOCATOR_TIMEOUT_MS/LOCATOR_POLL_INTERVAL_MS by default.
    Only used by the new validate_* actions below; the existing click/
    fill/select resolution path (resolve_and_act) is untouched and keeps
    its own, separately-tuned retry behavior.

    Returns (locator_or_None, strategy_or_None, attempt_count).
    """
    timeout_ms = LOCATOR_TIMEOUT_MS if timeout_ms is None else timeout_ms
    poll_ms = LOCATOR_POLL_INTERVAL_MS if poll_ms is None else poll_ms
    deadline = time.monotonic() + (timeout_ms / 1000.0)
    attempt = 0
    while True:
        attempt += 1
        loc, strategy = _resolve_element_with_strategy(page, lp)
        if loc is not None:
            return loc, strategy, attempt
        if time.monotonic() >= deadline:
            return None, None, attempt
        try:
            page.wait_for_timeout(poll_ms)
        except Exception:
            return None, None, attempt


# ============================================================
# LOCATOR RESOLUTION REPORTING - a read-only reporting layer over the
# EXISTING 12-level fallback chain (_resolve_element above, and
# resolve_and_act's own near-identical tier list further down). This
# never changes which tier is tried, in what order, or with what retry
# behavior - it only turns whichever strategy string a resolution attempt
# already reports (strategy_used, already collected in every step result)
# into a plain-English label and a numeric fallback level, so the
# dashboard/report can say "found using Role + accessible name" instead
# of a raw internal string. Reused by both the ordinary per-step report
# (see the per-step result dicts below) and the new validation actions'
# own results (see validate_text/count_elements/etc.), so there's exactly
# one place that translates a strategy string into user-facing text.
# ============================================================

# (numeric fallback level, human label) per strategy string this file's
# resolvers can report - level 1 is the strongest/most stable signal,
# higher numbers are progressively more generic/fragile fallbacks. Order
# mirrors _resolve_element's own finder order (the canonical, simpler
# 12-level chain used by validation/count actions); resolve_and_act's
# click/fill chain uses the same names plus "position_fallback" and,
# as an absolute last resort elsewhere in this file, "bounding_box".
_LOCATOR_STRATEGY_INFO = {
    "data-testid": (1, "Test ID"),
    "data-test": (2, "Test ID"),
    "data-cy": (3, "Test ID"),
    "id": (4, "Element ID"),
    "name": (5, "Name attribute"),
    "aria-label": (6, "Accessible name"),
    "placeholder": (7, "Placeholder"),
    "title": (8, "Title attribute"),
    "role": (9, "Role + accessible name"),
    "href": (10, "Link URL"),
    "text+tag": (11, "Text + Tag fallback"),
    "position_fallback": (12, "Position fallback"),
    "css_path": (13, "CSS path"),
    "xpath": (14, "XPath"),
    "bounding_box": (15, "Bounding Box fallback"),
}

# strategies weak enough that a step succeeding through them is still
# worth flagging for re-recording - the two loosest, most structural
# fallbacks (position/coordinates, not content or attributes)
_WEAK_LOCATOR_STRATEGIES = ("position_fallback", "bounding_box")


def _describe_locator_resolution(element_label, strategy_used, element_found, success, resolution_ms=None):
    """Builds the human-readable {strategy, strategy_label, fallback_level,
    resolved, weak, resolution_ms, message} block every step result (and
    every new validation-action result) carries as "locator_report".
    element_label is whatever short, human name the caller already has for
    the target (recorded element_text/aria-label/id/tag, or the action
    type itself as a last resort) - this never re-derives it, to avoid a
    second, possibly-inconsistent notion of "the element's name".
    """
    if not strategy_used or strategy_used not in _LOCATOR_STRATEGY_INFO:
        if not element_found:
            return {
                "strategy": None,
                "strategy_label": None,
                "fallback_level": None,
                "resolved": False,
                "weak": False,
                "resolution_ms": None,
                "message": f"{element_label} could not be resolved using any stored locator.",
            }
        # element_found True with an unrecognized/blank strategy string
        # shouldn't happen with today's resolvers, but a stale/foreign
        # strategy value must never crash reporting - describe it plainly
        # rather than guessing a fallback level for it
        return {
            "strategy": strategy_used,
            "strategy_label": strategy_used or "unknown",
            "fallback_level": None,
            "resolved": True,
            "weak": False,
            "resolution_ms": resolution_ms,
            "message": f"{element_label} found using {strategy_used or 'an unrecognized strategy'}.",
        }

    level, label = _LOCATOR_STRATEGY_INFO[strategy_used]
    weak = strategy_used in _WEAK_LOCATOR_STRATEGIES

    if not element_found:
        message = f"{element_label} could not be resolved using any stored locator."
    elif weak:
        message = (
            f"{element_label} found using {label}. "
            f"Consider re-recording this step."
        )
    else:
        message = f"{element_label} found using {label}."

    if element_found and resolution_ms is not None:
        message += f" (resolved in {resolution_ms}ms)"

    return {
        "strategy": strategy_used,
        "strategy_label": label,
        "fallback_level": level,
        "resolved": bool(element_found),
        "weak": weak,
        "resolution_ms": resolution_ms,
        "message": message,
    }


def _element_report_label(step):
    """Short, human name for a step's target, for locator-report messages
    - same field priority _describe_step (the Trim screen's own summarizer
    - see app.py's _describe_action_for_trim, kept deliberately in step
    with it) already uses: recorded element text/value first, then
    accessible name/aria-label/placeholder/id, then the tag, then a
    generic fallback naming the action itself.
    """
    lp = step.get("locator_profile") or {}
    attrs = lp.get("attributes") or {}
    text = (lp.get("element_text") or lp.get("text") or "").strip()
    value = step.get("value")
    action_type = step.get("action_type")
    value_as_text = value if action_type in ("click", "dblclick", "right_click") and value else None
    label = (
        text
        or value_as_text
        or lp.get("accessible_name")
        or lp.get("aria_label") or attrs.get("aria-label")
        or lp.get("placeholder") or attrs.get("placeholder")
        or lp.get("id")
        or lp.get("tag")
    )
    if label:
        return str(label).strip()[:60]
    return {
        "click": "Click target", "dblclick": "Double-click target", "right_click": "Right-click target",
        "fill": "Input field", "select": "Dropdown", "submit": "Submit control", "press": "Key target",
        "check": "Checkbox",
    }.get(action_type, "Element")


def _extract_element_value(el):
    """Reads an element's current text or value."""
    if el is None:
        return None
    try:
        val = el.input_value(timeout=1000)
        if val is not None:
            return str(val).strip()
    except Exception:
        pass
    try:
        val = el.get_attribute("value")
        if val is not None:
            return str(val).strip()
    except Exception:
        pass
    try:
        txt = el.inner_text(timeout=1000)
        if txt is not None:
            return " ".join(txt.split()).strip()
    except Exception:
        pass
    try:
        txt = el.text_content(timeout=1000)
        if txt is not None:
            return " ".join(txt.split()).strip()
    except Exception:
        pass
    return ""


def _wait_for_next_step_ready(page, next_step, timeout_s=9.0, interval_s=0.3):
    """Ties a navigate step's completion to something concrete: is the
    page actually usable for whatever comes next, rather than a generic
    signal (URL match, networkidle, content-diffing) that a client-side-
    rendered SPA can satisfy while still showing the previous view. If
    the next recorded step has a real target, polls for it to become
    findable (via _locator_findable above) for a bounded window. No
    locator profile on the next step (a scroll, another navigate, a
    tab_* action) means there's nothing meaningful to look ahead for, so
    this is trivially satisfied. Returns True if ready (or nothing to
    check), False if the window elapsed without the target appearing -
    callers decide what to do with that, this never raises.
    """
    if not next_step:
        return True
    lp = next_step.get("locator_profile") or {}
    has_identifying_signal = (
        any(lp.get(k) for k in ("id", "css_path", "xpath", "href", "element_text", "text"))
        or bool(lp.get("attributes"))
    )
    if not has_identifying_signal:
        return True
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            if _locator_findable(page, lp):
                return True
        except Exception:
            return True
        page.wait_for_timeout(int(interval_s * 1000))
    return False


def _element_has_modal_ancestor(el):
    """Generic, structural check for "is this element actually inside a
    container that looks like an active modal/dialog right now" - never
    any class/id/text/site-specific check, so it applies identically to
    a "size" modal, a "quantity" modal, or anything else shaped the same
    way. Walks el's own live ancestor chain (stopping at body) looking
    for either signal a real modal implementation commonly gives:

    - the ARIA-correct signal: role="dialog"/"alertdialog", or
      aria-modal="true", on any ancestor - what an accessibility-correct
      implementation (or a native <dialog> opened via showModal()) sets
      automatically;
    - the purely-CSS signal, for sites that skip ARIA entirely: an
      ancestor taken OUT of normal document flow (position: fixed or
      absolute) that covers a substantial share of the viewport - the
      same generic "this is a floating overlay, not normal in-flow
      content" signature this file's own overlay-blocking guard already
      uses elsewhere (see the portal/overlay pre-checks in
      resolve_and_act), just walked from the INSIDE (starting at a
      specific target) rather than scanned from body's direct children.

    A element merely being visible is NOT enough on its own to prove a
    real modal opened - a generic numeric id like "#9" can coincidentally
    match some other, already-visible, perfectly ordinary page element
    that has nothing to do with any dialog. This is what distinguishes
    that coincidental match from the real thing. Returns False (never
    raises) on any error - inconclusive is treated as "not confirmed",
    consistent with this being the STRICTER of the two signals this
    file's modal verification now requires together.
    """
    try:
        return el.evaluate(
            "e => { "
            "const vw = window.innerWidth, vh = window.innerHeight; "
            "const viewportArea = vw * vh; "
            "let node = e; "
            "while (node && node.nodeType === 1 && node !== document.body) { "
            "  const role = (node.getAttribute('role') || '').toLowerCase(); "
            "  if (role === 'dialog' || role === 'alertdialog') return true; "
            "  if ((node.getAttribute('aria-modal') || '').toLowerCase() === 'true') return true; "
            "  const style = getComputedStyle(node); "
            "  if (style.position === 'fixed' || style.position === 'absolute') { "
            "    const r = node.getBoundingClientRect(); "
            "    const area = r.width * r.height; "
            "    if (viewportArea > 0 && (area / viewportArea) >= 0.15) return true; "
            "  } "
            "  node = node.parentElement; "
            "} "
            "return false; "
            "}"
        )
    except Exception:
        return False


def _element_is_in_aria_dialog(el):
    """STRICT modal signal only - role="dialog"/"alertdialog" or
    aria-modal="true" on an ancestor. Deliberately narrower than
    _element_has_modal_ancestor just above, which ALSO accepts a purely
    generic "large fixed/absolute overlay" heuristic - a signature an
    ordinary, perfectly normal in-page element (a PDP's sticky "ADD TO
    BAG" bar pinned to the bottom of the viewport, say) can satisfy just
    as well as a real dialog, without being one.

    Exists specifically to gate _is_modal_content_painted's stricter
    paint check (opacity/elementFromPoint - see its own docstring): that
    check is safe to apply once we KNOW we're looking at real dialog
    content, but applying it to a merely fixed-position, already-working,
    non-modal element is exactly what caused a real regression - the PDP
    size button (position: fixed CTA bar nearby, no dialog anywhere in
    its ancestry) started failing this stricter check for reasons that
    have nothing to do with a modal never rendering, e.g. an unrelated
    neighboring element (a badge, a sticky header) overlapping its exact
    center pixel. Never raises; inconclusive reads as "not a dialog".
    """
    try:
        return bool(el.evaluate(
            "e => { "
            "let node = e; "
            "while (node && node.nodeType === 1 && node !== document.body) { "
            "  const role = (node.getAttribute('role') || '').toLowerCase(); "
            "  if (role === 'dialog' || role === 'alertdialog') return true; "
            "  if ((node.getAttribute('aria-modal') || '').toLowerCase() === 'true') return true; "
            "  node = node.parentElement; "
            "} "
            "return false; "
            "}"
        ))
    except Exception:
        return False


# CROSS-CONTAMINATION FIX (modal-open verification false positives): a
# click that's supposed to open modal B, fired immediately after modal A
# just closed, can pass _element_has_modal_ancestor's purely-structural
# "is SOMETHING dialog-shaped present" check even when B's own handler
# never ran at all - A and B commonly share the exact same reusable
# dialog/bottom-sheet CONTAINER on a real site (one generic role="dialog"
# element whose CONTENT gets swapped), so the container can still
# structurally look like an open modal purely as a leftover from A's own
# close animation/teardown, with nothing about B ever having happened.
# was_visible_before helps but is itself racy against that same close
# animation (see _wait_for_modal_target_visible's own docstring) - a
# purely STRUCTURAL/visibility check can never, on its own, distinguish
# "this modal is here because of the click I'm verifying" from "this
# modal is here because the PREVIOUS action left it mid-teardown".
#
# _arm_modal_mutation_tracker marks the exact moment (in the PAGE's own
# performance.now() clock, not this process's) right before a click that
# might open a modal fires, and installs (idempotently - safe to call
# before every such click) a MutationObserver that timestamps the most
# recent real DOM change anywhere under body. _wait_for_modal_target_
# visible's own _confirmed() check then requires that timestamp to be AT
# OR AFTER the armed moment before trusting a structural modal match -
# genuinely fresh activity, not a stale reference to whatever the
# PRECEDING action already left on the page. Falls back to the prior,
# unconditional behavior whenever no marker is present at all (an older
# recording/flow that never reached an arming point, or state a real
# hard-navigation wiped) rather than ever failing a check purely for
# missing instrumentation.
_MODAL_MUTATION_ARM_JS = (
    "() => { "
    "  if (!window.__afqaModalMutObserver && document.body) { "
    "    window.__afqaLastMutationTs = 0; "
    "    const obs = new MutationObserver(() => { "
    "      window.__afqaLastMutationTs = performance.now(); "
    "    }); "
    "    obs.observe(document.body, { attributes: true, childList: true, subtree: true }); "
    "    window.__afqaModalMutObserver = obs; "
    "  } "
    "  window.__afqaModalArmedAt = performance.now(); "
    "  return window.__afqaModalArmedAt; "
    "}"
)

_MODAL_FRESHNESS_CHECK_JS = (
    "() => ({ "
    "  lastMutationTs: (typeof window.__afqaLastMutationTs === 'number') ? window.__afqaLastMutationTs : null, "
    "  armedAt: (typeof window.__afqaModalArmedAt === 'number') ? window.__afqaModalArmedAt : null "
    "})"
)


def _arm_modal_mutation_tracker(page):
    """Call immediately before any click that might open a modal - see
    the _MODAL_MUTATION_ARM_JS comment above for why. Returns the armed
    timestamp (page-clock performance.now(), for logging) or None if the
    page wasn't in a state to accept it (mid-navigation, etc) - never
    raises, and a None result just means the later freshness check has
    nothing to compare against and is skipped, not that anything fails.
    """
    try:
        return page.evaluate(_MODAL_MUTATION_ARM_JS)
    except Exception:
        return None


# MODAL-OPEN DIAGNOSTICS: when the paint check below times out, "the
# click never triggered anything" and "the click worked but the app's
# own JS/network broke while rendering the result" look IDENTICAL from
# the DOM/paint check alone - both end up with an empty backdrop.
# Console errors and network activity happening in that SAME window
# are the only generic, site-agnostic signal that tells those two
# apart, so every page this replay ever touches (the initial page and
# any later tab - see _on_replay_new_page) gets a rolling event buffer
# attached the moment it's created, and _wait_for_modal_target_visible's
# own timeout path prints whatever fell inside its own polling window.
# Purely diagnostic: never affects ok/pass-fail, only what gets printed
# once a modal-open check has already failed for its own, independent
# reasons.
_MODAL_DIAG_EVENTS = {}
_MODAL_DIAG_REQ_STARTS = {}


def _install_modal_diagnostics(page):
    """Idempotent - safe to call once per page, wherever that page is
    created (the initial page, or any tab _on_replay_new_page picks
    up). Every handler is wrapped so a logging failure here can never
    take down the actual replay.
    """
    key = id(page)
    if key in _MODAL_DIAG_EVENTS:
        return
    events = []
    _MODAL_DIAG_EVENTS[key] = events

    def _console_handler(msg):
        try:
            events.append({"t": time.monotonic(), "kind": "console", "level": msg.type, "text": msg.text})
        except Exception:
            pass

    def _pageerror_handler(exc):
        try:
            events.append({"t": time.monotonic(), "kind": "pageerror", "text": str(exc)})
        except Exception:
            pass

    def _request_handler(req):
        try:
            _MODAL_DIAG_REQ_STARTS[id(req)] = time.monotonic()
        except Exception:
            pass

    def _requestfinished_handler(req):
        try:
            started = _MODAL_DIAG_REQ_STARTS.pop(id(req), None)
            now = time.monotonic()
            resp = req.response()
            events.append({
                "t": now, "kind": "network", "url": req.url, "method": req.method,
                "status": resp.status if resp else None,
                "duration_ms": (now - started) * 1000 if started is not None else None,
                "failure": None,
            })
        except Exception:
            pass

    def _requestfailed_handler(req):
        try:
            started = _MODAL_DIAG_REQ_STARTS.pop(id(req), None)
            now = time.monotonic()
            failure = req.failure
            failure_text = failure.get("errorText") if isinstance(failure, dict) else (failure or "failed")
            events.append({
                "t": now, "kind": "network", "url": req.url, "method": req.method,
                "status": None,
                "duration_ms": (now - started) * 1000 if started is not None else None,
                "failure": failure_text,
            })
        except Exception:
            pass

    try:
        page.on("console", _console_handler)
        page.on("pageerror", _pageerror_handler)
        page.on("request", _request_handler)
        page.on("requestfinished", _requestfinished_handler)
        page.on("requestfailed", _requestfailed_handler)
    except Exception:
        pass


def _print_modal_diag_window(page, start_t, end_t, label):
    """Prints whatever console/network activity landed inside
    [start_t, end_t] (both time.monotonic(), the same clock every
    event above is timestamped with) - called from
    _wait_for_modal_target_visible's own timeout path, right where a
    modal-open failure is about to be reported, so the two show up
    together instead of requiring a separate trawl through the full
    run log. Never raises, never affects the caller's own result.
    """
    try:
        events = _MODAL_DIAG_EVENTS.get(id(page), [])
        window = [e for e in events if start_t <= e["t"] <= end_t]
        if not window:
            print(f"[modal-diagnostics] {label}: no console/network activity observed in this window")
            return
        print(f"[modal-diagnostics] {label}: {len(window)} event(s) observed in this window -")
        for e in window:
            offset_ms = (e["t"] - start_t) * 1000
            if e["kind"] == "console":
                print(f"[modal-diagnostics]   +{offset_ms:.0f}ms console.{e['level']}: {e['text']}")
            elif e["kind"] == "pageerror":
                print(f"[modal-diagnostics]   +{offset_ms:.0f}ms UNCAUGHT EXCEPTION: {e['text']}")
            elif e["kind"] == "network":
                dur = f"{e['duration_ms']:.0f}ms" if e["duration_ms"] is not None else "?ms"
                if e["failure"]:
                    print(f"[modal-diagnostics]   +{offset_ms:.0f}ms NETWORK FAILED {e['method']} {e['url']} - {e['failure']} ({dur})")
                else:
                    slow_tag = " SLOW" if (e["duration_ms"] or 0) > 1000 else ""
                    print(f"[modal-diagnostics]   +{offset_ms:.0f}ms{slow_tag} {e['method']} {e['url']} -> {e['status']} ({dur})")
    except Exception:
        pass


# MODAL-INTERACTION TIMING: the fourth timestamp requested alongside
# click-dispatch/dom-appears/content-painted - when replay actually
# INTERACTS with whatever the modal was supposed to contain (the size/
# quantity option itself). That happens in a LATER, separate iteration
# of the main replay loop than the click-then-navigate verification
# above (it's the next recorded step, executed through the same generic
# _resolve_and_act_with_retry every ordinary step goes through) - so
# _wait_for_modal_target_visible arms this the moment its own
# verification SUCCEEDS (see its two "return True, None" points), and
# the generic per-step dispatch point (right before
# _resolve_and_act_with_retry runs, in run() below) checks whether the
# step it's about to run is the exact one this was armed for. Keyed by
# id(page) so multiple pages/tabs never cross-contaminate each other's
# pending timing; keyed by id(step) (the recorded step dict itself,
# never copied elsewhere in this file) so only that SAME step consumes
# it, not a coincidentally-similar later one.
_MODAL_INTERACTION_TIMING = {}


def _arm_modal_interaction_timing(page, t0, step):
    if not step:
        return
    try:
        _MODAL_INTERACTION_TIMING[id(page)] = {"t0": t0, "step_id": id(step)}
    except Exception:
        pass


def _maybe_log_modal_interaction_timing(page, step):
    try:
        ctx = _MODAL_INTERACTION_TIMING.get(id(page))
        if not ctx or ctx.get("step_id") != id(step):
            return
        del _MODAL_INTERACTION_TIMING[id(page)]
        lp = (step.get("locator_profile") or {})
        desc = lp.get("element_text") or lp.get("text") or lp.get("id") or "target"
        offset_ms = (time.monotonic() - ctx["t0"]) * 1000
        print(
            f"[modal-timing-detail] interaction with {desc!r} dispatched "
            f"at +{offset_ms:.0f}ms from click dispatch"
        )
    except Exception:
        pass


# FORCE-INTERACT registry - a target confirmed unreachable by every scroll
# mechanism tried (Playwright's scroll_into_view_if_needed(), then native
# JS scrollIntoView() - see _sample_with_scroll_retry) gets a native JS
# click dispatched directly on it, as a last resort, right inside
# _wait_for_modal_target_visible's own final timeout path (see the
# force-interact block there). That happens ONE recorded step early -
# on the CHECK step's own locator, verified as the upcoming target,
# not yet reached by the main replay loop - so the loop must NOT then
# click it AGAIN, normally, once it actually reaches that same recorded
# step: for a non-native, single-select "checkbox" (a quantity/size
# option div, not a real <input> - see _resolve_and_act_with_retry's own
# "check-vs-click" comment on why it never trusts is_checked for these
# and always clicks), a second click would very plausibly TOGGLE the
# selection back OFF, silently undoing the interaction just forced.
# Keyed the same way as _MODAL_INTERACTION_TIMING above (id(page) ->
# id(step), the recorded step dict itself, never copied elsewhere in
# this file) for the same reason: only that SAME step consumes its own
# marker, and multiple pages/tabs never cross-contaminate each other's.
_MODAL_FORCE_INTERACTED_STEPS = {}


def _mark_force_interacted(page, step):
    if not step:
        return
    try:
        _MODAL_FORCE_INTERACTED_STEPS[id(page)] = id(step)
    except Exception:
        pass


def _consume_force_interacted(page, step):
    """True (and clears the marker) only when `step` is the EXACT recorded
    step _wait_for_modal_target_visible's own force-interact fallback just
    force-clicked - never a coincidentally-similar later step, and never
    stale across pages, for the same identity-keying reasons as
    _maybe_log_modal_interaction_timing above.
    """
    try:
        marked_id = _MODAL_FORCE_INTERACTED_STEPS.get(id(page))
        if marked_id is None or marked_id != id(step):
            return False
        del _MODAL_FORCE_INTERACTED_STEPS[id(page)]
        return True
    except Exception:
        return False


# el.is_visible() (used by _wait_for_modal_target_visible's _confirmed())
# only proves a non-empty layout box with display!='none'/visibility!=
# 'hidden' - it does NOT check computed opacity, whether the box actually
# falls inside the viewport, or whether something else is painted on top
# of it. A panel mid fade-in/slide-in transition (opacity building from 0,
# or translated in from outside the viewport) commonly satisfies all of
# is_visible()'s own conditions well before a human - or a screenshot -
# would call it "on screen": getBoundingClientRect() already reports the
# element's POST-transform geometry and a non-empty box the instant it's
# laid out, regardless of current opacity or where that box currently
# sits relative to the viewport. This is exactly the gap that let replay
# "confirm" the quantity modal's content and click/check it while the
# backdrop was still visually empty - the checkbox existed, had a real
# layout box, and structurally sat inside a role=dialog ancestor, all
# before the panel had actually painted anything a viewer could see.
# Checks, on the actual target element and every ancestor up to <body>:
#   - connected to the live DOM
#   - non-empty getBoundingClientRect()
#   - that box's center falls inside the current viewport
#   - cumulative (multiplied, not just the target's own) computed opacity
#     is above a small floor - a 0%-opacity ancestor two levels up still
#     makes the target itself invisible even if the target's OWN opacity
#     reads 1
#   - no display:none/visibility:hidden ancestor
#   - document.elementFromPoint() at that box's center actually hits this
#     element (or an ancestor/descendant of it) - catches a target that's
#     technically laid out and "visible" by every check above but is
#     currently painted UNDER something else (a loading skeleton, the
#     backdrop itself, a clip-path hiding it) sitting on top of it


# SCROLL-BLOCKER DIAGNOSTIC: backs _is_modal_content_painted's scroll-into-
# view retry (see _sample_with_scroll_retry) - when scroll_into_view_if_
# needed() runs but the element's own bounding box doesn't move at all
# afterward, that's a real, distinct failure mode from "the scroll just
# hasn't settled yet": Playwright's scroll only ever moves the NEAREST
# scrollable ancestor (the page itself, or a container with overflow:auto/
# scroll and real overflow content) - it has nothing to do if there is no
# such ancestor between the target and <body>, which is exactly what
# happens when the dialog container is position:fixed and sized via a
# viewport-relative unit (100vh, say) rather than actual document flow: a
# fixed element that's already as tall as (or taller than) the viewport
# has no overflow FOR THE PAGE to scroll past, regardless of how far down
# inside it the target visually sits. Reports three independent, generic
# signals (never hardcoded to any one site's own class names) so a human
# can tell "nothing to scroll" apart from "scroll ran but hasn't taken
# effect yet" apart from "there's a genuinely scrollable ancestor, but the
# element still didn't reach it":
#   - the nearest ancestor (if any) that's both overflow-y:auto/scroll AND
#     actually has more content than it can show (scrollHeight >
#     clientHeight) - the one thing Playwright's own scroll could act on
#   - the nearest ancestor (if any) with overflow-y:hidden - content past
#     its edge is clipped, not reachable by scrolling anything
#   - whatever role=dialog/alertdialog/aria-modal ancestor contains the
#     target, with its own position/overflow-y/bounding box/scrollHeight -
#     specifically flatting whether that container's OWN height already
#     exceeds the realistic viewport passed in, which is exactly the
#     "fixed dialog sized via 100vh against this replay's own inflated
#     viewport" shape this whole investigation suspects
_MODAL_SCROLL_BLOCKER_DIAGNOSTIC_JS = (
    "(el, realisticVh) => { "
    "  const result = { "
    "    scrollable_ancestor: null, overflow_hidden_ancestor: null, "
    "    dialog_container: null, "
    "    document_scroll_height: document.documentElement.scrollHeight, "
    "    window_scroll_y: window.scrollY, "
    "    page_has_scrollable_overflow: document.documentElement.scrollHeight > window.innerHeight, "
    "  }; "
    "  const describe = (node) => ({ "
    "    tag: node.tagName, id: node.id || null, "
    "    className: node.className ? String(node.className) : null, "
    "  }); "
    "  let node = el ? el.parentElement : null; "
    "  while (node && node !== document.documentElement) { "
    "    const s = getComputedStyle(node); "
    "    if (!result.overflow_hidden_ancestor && s.overflowY === 'hidden') { "
    "      result.overflow_hidden_ancestor = describe(node); "
    "    } "
    "    if (!result.scrollable_ancestor && (s.overflowY === 'auto' || s.overflowY === 'scroll') "
    "        && node.scrollHeight > node.clientHeight + 1) { "
    "      result.scrollable_ancestor = Object.assign(describe(node), { "
    "        scrollHeight: node.scrollHeight, clientHeight: node.clientHeight, "
    "      }); "
    "    } "
    "    node = node.parentElement; "
    "  } "
    "  let dnode = el; "
    "  let dialog = null; "
    "  while (dnode && dnode !== document.body) { "
    "    if (dnode.getAttribute && (dnode.getAttribute('role') === 'dialog' "
    "        || dnode.getAttribute('role') === 'alertdialog' "
    "        || dnode.getAttribute('aria-modal') === 'true')) { dialog = dnode; break; } "
    "    dnode = dnode.parentElement; "
    "  } "
    "  if (dialog) { "
    "    const r = dialog.getBoundingClientRect(); "
    "    const s = getComputedStyle(dialog); "
    "    result.dialog_container = Object.assign(describe(dialog), { "
    "      position: s.position, overflowY: s.overflowY, "
    "      bbox: { x: r.left, y: r.top, w: r.width, h: r.height }, "
    "      scrollHeight: dialog.scrollHeight, clientHeight: dialog.clientHeight, "
    "      exceeds_realistic_viewport: (typeof realisticVh === 'number') ? (r.height > realisticVh) : null, "
    "    }); "
    "  } "
    "  return result; "
    "}"
)


_MODAL_CONTENT_PAINTED_JS = (
    "(el, realisticVh) => { "
    "  const result = { painted: false, reason: 'unknown', x: 0, y: 0, w: 0, h: 0, vw: 0, vh: 0 }; "
    "  if (!el || !el.isConnected) { result.reason = 'detached'; return result; } "
    "  const r = el.getBoundingClientRect(); "
    "  result.x = r.left; result.y = r.top; result.w = r.width; result.h = r.height; "
    "  if (r.width <= 0 || r.height <= 0) { result.reason = 'zero-size'; return result; } "
    "  const vw = window.innerWidth; "
    # REALISTIC-VIEWPORT FIX: this replay's own browser context is
    # configured with a taller-than-realistic viewport (REPLAY_VIEWPORT_
    # HEIGHT_PX, see run() below - 2000px, confirmed NOT safe to lower,
    # see that constant's own comment) for unrelated screenshot reasons -
    # real users and screen recordings never get anywhere near that much
    # vertical space. Using window.innerHeight directly here would
    # validate "is this inside REPLAY_VIEWPORT_HEIGHT_PX of space", not
    # "would a real user actually
    # see this" - confirmed via a live debug dump to be exactly how a
    # genuinely off-screen element (y=1120, well below any real ~900px
    # browser window) passed against the original 2000px number. min()
    # with the realistic override - never used to relax the check BEYOND
    # whatever the actual viewport happens to be, only ever to tighten it
    # toward a real-world height when the actual one is taller.
    "  const vh = (typeof realisticVh === 'number' && realisticVh > 0) "
    "    ? Math.min(window.innerHeight, realisticVh) : window.innerHeight; "
    "  result.vw = vw; result.vh = vh; "
    # OUT-OF-VIEWPORT FIX: this used to only bounds-check the box's
    # CENTER point (cx/cy) against the viewport - a real bug, confirmed
    # via a live debug dump, that let a genuinely off-screen element
    # (an interactive option positioned far down inside a tall dialog
    # container, well past the fold) pass: its center point still fell
    # inside SOME finite viewport number even though no real user (or
    # screen recording) would ever see it without scrolling. Checking
    # every edge of the FULL box against every viewport edge is what
    # actually enforces "entirely on screen", not just "center happens
    # to land inside some number".
    "  if (r.top < 0 || r.left < 0 || r.bottom > vh || r.right > vw) { result.reason = 'out-of-viewport'; return result; } "
    "  let node = el, opacity = 1; "
    "  while (node && node.nodeType === 1) { "
    "    const s = getComputedStyle(node); "
    "    if (s.visibility === 'hidden' || s.display === 'none') { result.reason = 'hidden-ancestor'; return result; } "
    "    const o = parseFloat(s.opacity); "
    "    opacity *= Number.isFinite(o) ? o : 1; "
    "    node = node.parentElement; "
    "  } "
    "  if (opacity <= 0.05) { result.reason = 'zero-opacity'; return result; } "
    "  const cx = r.left + r.width / 2, cy = r.top + r.height / 2; "
    "  const top = document.elementFromPoint(cx, cy); "
    "  if (!top || (top !== el && !el.contains(top) && !top.contains(el))) { result.reason = 'occluded'; return result; } "
    "  result.painted = true; result.reason = 'ok'; "
    "  return result; "
    "}"
)


def _double_raf(page):
    """Waits for two consecutive requestAnimationFrame callbacks - a
    style/class change (opening a modal, starting its enter transition)
    doesn't necessarily get reflected in the next getComputedStyle/
    getBoundingClientRect read synchronously; a real paint needs at least
    one frame, and two guards against reading a value the browser is
    mid-way through updating for the current frame. Best-effort: a page
    mid-navigation can reject this, which just means the caller's next
    read happens without this extra settle time rather than raising.
    """
    try:
        page.evaluate(
            "() => new Promise(resolve => "
            "requestAnimationFrame(() => requestAnimationFrame(resolve)))"
        )
    except Exception:
        pass


def _is_modal_content_painted(candidate_el):
    """Stronger replacement for trusting is_visible() alone (see
    _MODAL_CONTENT_PAINTED_JS above for what it actually checks) - and
    not just a single instantaneous read, either: samples it twice, each
    behind its own _double_raf settle, and requires the SAME non-empty,
    in-viewport bounding box both times. A single passing sample can
    still land mid CSS transition (a panel sliding/fading in tends to be
    genuinely "painted" - opacity>0, on top, in viewport - for most of
    that transition, not just its final frame); requiring the box to be
    stable across two frame-separated samples is what actually tells
    "settled" apart from "still moving/fading but happened to pass this
    instant". Also scrolls a target that's out of the current viewport
    into view and re-samples once before giving up on that sample (see
    _sample_with_scroll_retry below) - a real, open dialog whose specific
    option is rendered far down inside a tall container is a scroll away
    from being genuinely visible, not a false positive. Never raises;
    any evaluate failure (detached element, navigation mid-check) reads
    as not-painted. Returns (painted, last_reason) - see the comment
    right above the final return below for what last_reason is for.
    """
    def _sample():
        try:
            # REALISTIC-VIEWPORT FIX: passes REALISTIC_VIEWPORT_HEIGHT_PX
            # as the bounds-check reference instead of letting the JS side
            # default to this replay's own (deliberately tall, screenshot-
            # oriented) window.innerHeight - see both constants' own
            # comments for why.
            return candidate_el.evaluate(_MODAL_CONTENT_PAINTED_JS, REALISTIC_VIEWPORT_HEIGHT_PX)
        except Exception:
            return None

    def _sample_with_scroll_retry():
        # OUT-OF-VIEWPORT FIX: a target that's otherwise genuinely open
        # (correct opacity/visibility, not occluded) but currently sits
        # outside the viewport - the exact case _MODAL_CONTENT_PAINTED_JS's
        # own reason='out-of-viewport' now catches - is often just one
        # scroll away from being real, visible content rather than a
        # false positive to reject outright: a tall dialog container
        # whose actual interactive option is rendered far down inside it,
        # past what's currently in view.
        #
        # NOT via Playwright's scroll_into_view_if_needed() - confirmed,
        # via the scroll-blocker diagnostic below, to be a no-op on this
        # exact shape: a position:fixed dialog whose scrollHeight ==
        # clientHeight (no overflow at all) and no scrollable ancestor
        # anywhere between the target and <body>. Playwright's own method
        # only ever acts on a genuinely scrollable ancestor - with none to
        # act on, it silently does nothing, which is exactly what 10
        # identical retries with an unchanged y-position confirmed live.
        # REPLAY_VIEWPORT_HEIGHT_PX was tried as a workaround (making the
        # actual browser viewport shorter, matching REALISTIC_VIEWPORT_
        # HEIGHT_PX more closely, so this kind of vh-relative layout would
        # naturally place content in reach) - reverted after confirming it
        # broke Select Size (this SAME site calculates other modals' own
        # positioning from that real viewport height too - not something
        # safe to change globally, see that constant's own comment).
        #
        # Native el.scrollIntoView() instead: bypasses Playwright's own
        # "is there a scrollable ancestor" heuristic entirely and asks the
        # browser itself to do whatever it would do for this element -
        # which, for a genuinely fixed/non-scrollable panel, may still be
        # nothing (some fixed layouts have no scroll mechanism for
        # ANYTHING to invoke), but is worth trying since it's a strictly
        # different code path than what's already confirmed not to work,
        # and costs nothing extra to attempt. A single attempt (not a
        # loop) here, since this whole function already gets re-invoked on
        # every outer poll iteration - a genuinely unreachable target keeps
        # failing every time, not just once.
        r = _sample()
        if r and r.get("reason") == "out-of-viewport":
            _y_before, _h_before = r.get("y", 0), r.get("h", 0)
            print(
                f"[modal-content-check] target is outside the viewport "
                f"(box y={_y_before:.0f}..{_y_before + _h_before:.0f}, "
                f"viewport height={r.get('vh')}) - trying native scrollIntoView() and re-checking"
            )
            # SCROLL-BLOCKER DIAGNOSTIC - see _MODAL_SCROLL_BLOCKER_
            # DIAGNOSTIC_JS's own comment. Queried BEFORE the scroll
            # attempt (the DOM structure this reports on doesn't change
            # because of the scroll itself) so a human can immediately see
            # WHY the scroll below is or isn't expected to do anything,
            # without waiting for the after-bbox comparison to imply it.
            try:
                _blockers = candidate_el.evaluate(
                    _MODAL_SCROLL_BLOCKER_DIAGNOSTIC_JS, REALISTIC_VIEWPORT_HEIGHT_PX
                )
            except Exception as _e_blockers:
                _blockers = {"error": str(_e_blockers)}
            print("[modal-scroll-blocker] " + json.dumps(_blockers))
            try:
                # native JS scrollIntoView(), not Playwright's own
                # scroll_into_view_if_needed() - see this function's own
                # docstring above for why
                candidate_el.evaluate(
                    "(el) => { el.scrollIntoView({ block: 'center', inline: 'nearest' }); }"
                )
            except Exception as _e_scroll:
                print(f"[modal-scroll-blocker] native scrollIntoView() raised: {_e_scroll}")
            _double_raf(candidate_el.page)
            r = _sample()
            # confirms whether the scroll command actually moved anything
            # at all, independent of whether the move was enough to pass
            # the viewport-bounds check - "still out-of-viewport but moved
            # partway" and "zero effect, identical box" are very different
            # findings and this is the only place that distinguishes them
            if r:
                _y_after = r.get("y", 0)
                _moved = abs(_y_after - _y_before) > 1.0
                print(
                    f"[modal-content-check] after native scrollIntoView(): "
                    f"box y={_y_after:.0f}..{_y_after + r.get('h', 0):.0f} "
                    f"({'moved' if _moved else 'UNCHANGED'} from y={_y_before:.0f}), "
                    f"reason={r.get('reason')}"
                )
                if not _moved:
                    print(
                        "[modal-scroll-blocker] native scrollIntoView() ALSO had zero effect - "
                        "this target is not reachable by any scroll mechanism tried so far"
                    )
        return r

    # returns (painted, last_reason) - last_reason (see _MODAL_CONTENT_
    # PAINTED_JS's own reason values) is exposed so a caller polling this
    # repeatedly over a whole verification window (see _wait_for_modal_
    # target_visible) can tell, once that window finally times out,
    # whether the LAST thing standing in the way was specifically an
    # already-scroll-retried 'out-of-viewport' - the one case that whole
    # window's own force-interact fallback cares about - versus some
    # other reason (hidden, occluded, zero-opacity) that fallback should
    # never fire for.
    _double_raf(candidate_el.page)
    r1 = _sample_with_scroll_retry()
    if not r1 or not r1.get("painted"):
        return False, (r1.get("reason") if r1 else "evaluate-failed")
    _double_raf(candidate_el.page)
    r2 = _sample_with_scroll_retry()
    if not r2 or not r2.get("painted"):
        return False, (r2.get("reason") if r2 else "evaluate-failed")

    def _close(a, b, eps=1.0):
        return abs(a - b) <= eps

    _stable = (
        _close(r1["x"], r2["x"]) and _close(r1["y"], r2["y"])
        and _close(r1["w"], r2["w"]) and _close(r1["h"], r2["h"])
    )
    return _stable, ("ok" if _stable else "unstable")


def _save_modal_debug_screenshot(page, shot_dir, label):
    """Full-page screenshot taken at the exact moment replay judges a
    modal's content ready (or gives up waiting) - saved under shot_dir/
    debug/ regardless of whether the step's own normal per-step capture
    runs, so a human can see exactly what was on screen at that instant
    without having to reproduce the failure live. Best-effort: shot_dir
    being unavailable (a call site that has no run folder in scope) or
    the screenshot call itself failing (page mid-navigation/closed) just
    means no debug image this time, never a replay failure.
    """
    if shot_dir is None:
        return None
    try:
        debug_dir = Path(shot_dir) / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        path = debug_dir / f"modal-{label}-{int(time.time() * 1000)}.png"
        page.screenshot(path=str(path))
        print(f"[modal-debug] saved screenshot at moment of '{label}': {path}")
        return str(path)
    except Exception:
        return None


_MODAL_DETECT_JS = (
    "() => { "
    "  const vw = window.innerWidth, vh = window.innerHeight; "
    # unquoted attribute values (dialog/alertdialog/true are all plain
    # identifiers, valid unquoted in a CSS attribute selector)
    # deliberately avoids a three-way quote-nesting problem otherwise
    # unavoidable here: this JS source is itself a Python string literal
    # INSIDE script_generator.py's own outer triple-quoted SCRIPT_
    # TEMPLATE, so any " written here gets unescaped once when script_
    # generator.py itself loads - stripping the backslash BEFORE it ever
    # reaches the generated output file, which then fails to parse as
    # valid Python. Confirmed real, not hypothetical: this exact mistake
    # produced a SyntaxError in the generated script the first time this
    # line was written with escaped quotes.
    "  const candidates = document.querySelectorAll("
    '    "[role=dialog], [role=alertdialog], [aria-modal=true]"'
    "  ); "
    "  for (const c of candidates) { "
    "    const s = getComputedStyle(c); "
    "    if (s.display === 'none' || s.visibility === 'hidden') continue; "
    "    const r = c.getBoundingClientRect(); "
    "    if (r.width > 0 && r.height > 0) return true; "
    "  } "
    "  if (!document.body) return false; "
    "  for (const el of document.body.children) { "
    "    const s = getComputedStyle(el); "
    "    if (s.display === 'none' || s.visibility === 'hidden') continue; "
    "    if (s.position !== 'fixed' && s.position !== 'absolute') continue; "
    "    const r = el.getBoundingClientRect(); "
    "    if (vw * vh > 0 && (r.width * r.height) / (vw * vh) >= 0.15) return true; "
    "  } "
    "  return false; "
    "}"
)


# TEMPORARY DEBUG - the two JS snippets below back the "CONFIRMED stable"
# debug dump (see _debug_pause_if_quantity in _wait_for_modal_target_visible):
# one describes the exact element the paint-check just validated, the other
# independently lists every role=dialog/aria-modal candidate actually in the
# DOM at that same moment, so the two can be compared directly - is the
# paint-check's own target the same element as the real dialog container, a
# descendant of it, or something else entirely with no relation to it at
# all. Remove alongside the rest of the debug-pause wiring once no longer
# needed.
_ELEMENT_DEBUG_INFO_JS = (
    "(el) => { "
    "  const r = el.getBoundingClientRect(); "
    "  const s = getComputedStyle(el); "
    "  return { "
    "    tag: el.tagName, "
    "    id: el.id || null, "
    "    className: (el.className && el.className.toString) ? el.className.toString() : null, "
    "    bbox: { x: r.left, y: r.top, w: r.width, h: r.height }, "
    "    opacity: s.opacity, visibility: s.visibility, display: s.display, "
    "    zIndex: s.zIndex, position: s.position, "
    "    outerHTML: (el.outerHTML || '').slice(0, 500), "
    "  }; "
    "}"
)

_MODAL_DIALOG_CONTAINER_DEBUG_JS = (
    "() => { "
    "  const sel = "
    '    "[role=dialog], [role=alertdialog], [aria-modal=true]"; '
    "  return Array.from(document.querySelectorAll(sel)).map(c => { "
    "    const r = c.getBoundingClientRect(); "
    "    const s = getComputedStyle(c); "
    "    return { "
    "      tag: c.tagName, "
    "      id: c.id || null, "
    "      className: (c.className && c.className.toString) ? c.className.toString() : null, "
    "      bbox: { x: r.left, y: r.top, w: r.width, h: r.height }, "
    "      opacity: s.opacity, visibility: s.visibility, display: s.display, "
    "      zIndex: s.zIndex, position: s.position, "
    "      outerHTML: (c.outerHTML || '').slice(0, 300), "
    "    }; "
    "  }); "
    "}"
)


def _diagnose_modal_open_sequence(page, shot_dir=None):
    """Diagnostic (and only diagnostic - no pass/fail decision here) for
    a click that's supposed to open a modal: takes three checkpoints at
    0ms, 300ms, and 800ms after this call starts, each checking whether
    ANY element on the page structurally looks like a visible, open
    dialog (_MODAL_DETECT_JS above - the same generic role="dialog"/
    aria-modal/fixed-large-overlay signature _element_has_modal_ancestor
    already uses, just scanned across the whole page rather than walked
    up from one specific target, since at diagnostic time there may be
    no resolved "inner target" element to walk up from at all) AND takes
    a real screenshot at each one, when shot_dir is given - a boolean
    "was a dialog detected" is useful, but a human being asked for
    "definitive proof one way or the other" needs to actually SEE what
    replay saw at each moment, not just take this check's word for it.
    Simultaneously collects every DOM mutation anywhere under body
    during that same window (capped at 200 records, via a
    MutationObserver installed once and read back at the end), so a
    click whose dialog is NEVER observed at any checkpoint - despite the
    underlying state change still landing - still leaves a trace of what
    actually happened, instead of nothing to investigate at all.

    Deliberately Python-driven (three separate round-trips, not one
    combined async page.evaluate like an earlier version of this
    function) - taking a screenshot is only possible from the Python
    side, so once that's a requirement, splitting the timing across
    real page.wait_for_timeout() calls is what actually lets a
    screenshot land at each checkpoint; the small added IPC latency
    between calls is an acceptable tradeoff for that.

    Returns {"checkpoints": {"0ms": bool, "300ms": bool, "800ms": bool},
    "screenshots": {"0ms": path_or_None, ...}, "mutations": [...]}, or
    None on failure. Never raises, never blocks anything - purely
    observational.
    """
    def _detect():
        try:
            return page.evaluate(_MODAL_DETECT_JS)
        except Exception:
            return None

    def _shoot(label):
        if not shot_dir:
            return None
        try:
            path = Path(shot_dir) / f"modal-diagnostic-{label}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(path))
            return str(path)
        except Exception:
            return None

    try:
        page.evaluate(
            "() => { "
            "window.__modalDiagMutations = []; "
            "if (window.__modalDiagObserver) { "
            "  try { window.__modalDiagObserver.disconnect(); } catch (e) {} "
            "} "
            "if (!document.body) return; "
            "const observer = new MutationObserver((records) => { "
            "  for (const r of records) { "
            "    if (window.__modalDiagMutations.length >= 200) break; "
            "    window.__modalDiagMutations.push({ "
            "      type: r.type, "
            "      target: (r.target && r.target.tagName) ? r.target.tagName.toLowerCase() : 'text', "
            "      attr: r.attributeName || null, "
            "      added: r.addedNodes.length, "
            "      removed: r.removedNodes.length "
            "    }); "
            "  } "
            "}); "
            "observer.observe(document.body, { attributes: true, childList: true, subtree: true }); "
            "window.__modalDiagObserver = observer; "
            "}"
        )
    except Exception:
        pass

    checkpoints = {}
    screenshots = {}

    checkpoints["0ms"] = _detect()
    screenshots["0ms"] = _shoot("0ms")

    try:
        page.wait_for_timeout(300)
    except Exception:
        pass
    checkpoints["300ms"] = _detect()
    screenshots["300ms"] = _shoot("300ms")

    try:
        page.wait_for_timeout(500)
    except Exception:
        pass
    checkpoints["800ms"] = _detect()
    screenshots["800ms"] = _shoot("800ms")

    try:
        mutations = page.evaluate(
            "() => { "
            "if (window.__modalDiagObserver) { "
            "  try { window.__modalDiagObserver.disconnect(); } catch (e) {} "
            "} "
            "return window.__modalDiagMutations || []; "
            "}"
        )
    except Exception:
        mutations = []

    return {"checkpoints": checkpoints, "screenshots": screenshots, "mutations": mutations}


def _wait_for_modal_target_visible(
    page, target_step, timeout_s=6.0, interval_s=0.3, was_visible_before=None,
    shot_dir=None, click_dispatched_at=None, _debug_pause_if_quantity=False,
):
    """Stricter than _wait_for_next_step_ready above, and deliberately so:
    that one (and the _locator_findable it's built on) only proves the
    target exists SOMEWHERE in the DOM - which a hidden, never-actually-
    opened modal's content still does, since an id/css_path/xpath
    selector matches a display:none element exactly as readily as a
    rendered one. A click-then-navigate-to-a-modal-URL sequence whose
    "effect" is checked only by URL can pass even when the real dialog
    never mounted at all (no backdrop, no content, page pixel-identical
    to before the click) - forced/hash-only navigation reaches the URL
    regardless of whether the click's own handler ever ran. This polls
    for the SAME target (whatever the next recorded action's own
    locator_profile already names - never a hardcoded "modal"/"qty"/
    site-specific check) to become genuinely VISIBLE (Playwright's own
    is_visible(): a real, non-empty layout box, not visibility:hidden -
    already the right, established distinction elsewhere in this file
    between a merely-styled-hidden toggle and something that was truly
    never rendered) - visible alone is not enough on its own, though,
    since a generic id like "#9" can coincidentally match some unrelated,
    ALREADY-visible element elsewhere on the page that has nothing to do
    with any dialog. is_visible() alone is also not the same thing as
    genuinely PAINTED on screen: it only checks a non-empty layout box
    and display/visibility, not computed opacity, not whether that box
    currently falls inside the viewport, and not whether something else
    is painted on top of it - a panel mid fade-in/slide-in transition (a
    real, observed cause of an empty-looking modal whose recorded target
    still gets found and clicked/checked successfully under this weaker
    check) satisfies is_visible() well before it's actually visible to a
    human or a screenshot. _is_modal_content_painted() closes that gap -
    see its own docstring - and is required in addition to is_visible()
    below. Two independent, generic signals can each confirm the
    STRUCTURAL "is this really a dialog" half of the check on their own:

    - was_visible_before, when explicitly False: the target genuinely
      TRANSITIONED from invisible/absent to visible as a direct result
      of THIS interaction (captured by the caller right before the click
      fired) - strong, temporal, site-agnostic evidence regardless of
      how the modal is styled, and the only signal that catches a real
      modal built with neither ARIA nor fixed/absolute positioning (a
      plain in-flow div toggled via display, say);
    - _element_has_modal_ancestor(el): the STRUCTURAL fallback for when
      no reliable "before" snapshot exists (was_visible_before is None -
      an older recording, or this target wasn't resolvable pre-click
      either) or when the target was, unhelpfully, ALREADY visible
      before the click too (was_visible_before=True) - in which case
      "still visible now" is weak evidence on its own, and the
      structural role="dialog"/aria-modal/fixed-overlay check is what's
      actually needed to tell "a real modal was already open" apart from
      "an unrelated, ordinary page element happened to already be there".

    Applies uniformly to every click-then-navigate-to-modal sequence,
    whatever the target actually is - never a special case for one kind
    of modal versus another. Generic across any action type - check/
    fill/click/select all carry a locator_profile the same way. No
    locator on the target step (a scroll, another navigate, a tab_*
    action) means nothing to verify, so this is trivially satisfied.

    Confirmation requires STABILITY, not just a single instantaneous
    match: once visible+confirmed, the SAME check is repeated once more
    STABILITY_RECHECK_MS later, and only a target that's still visible
    and confirmed then counts as genuinely open. A dialog that flashes
    open and gets dismissed again almost immediately (a real race
    between the click's own handler and something that closes it right
    back, confirmed via video against one real recording) can otherwise
    satisfy a single-instant check for one animation frame and nothing
    more, reading as "verified" even though a human watching the replay
    never actually sees it. Applies the same way to every modal this
    function verifies, not a special case for one over another.

    click_dispatched_at (a time.monotonic() reading, taken by the caller
    at the exact moment the click this modal is supposed to be a result
    of actually fired) is purely diagnostic: every [modal-timing-detail]
    line below is printed as an offset from it, so the real millisecond
    gaps between "click fired" / "target DOM node first appears" /
    "content genuinely painted" / "confirmed stable" are visible
    directly in the log for ANY flow (comparing one recorded trigger
    against another - e.g. two structurally-identical click-then-
    navigate-to-modal sequences on the same page - is exactly what this
    is for). Falls back to this function's own start time when the
    caller has no real dispatch moment to hand over (an older call site,
    or a verification that isn't paired with a click this function
    itself observed) - never fabricated, just a slightly later reference
    point, and clearly distinguishable in the log's own timing since
    every offset in that case starts essentially at 0ms.

    Returns (ok, reason) - reason is None when ok, or a clear message
    for the caller to report when the window elapses without either
    signal confirming it stably. Never raises.
    """
    if not target_step:
        return True, None
    lp = target_step.get("locator_profile") or {}
    has_identifying_signal = (
        any(lp.get(k) for k in ("id", "css_path", "xpath", "href", "element_text", "text"))
        or bool(lp.get("attributes"))
    )
    if not has_identifying_signal:
        return True, None

    _t0 = click_dispatched_at if click_dispatched_at is not None else time.monotonic()
    _target_desc = lp.get("element_text") or lp.get("text") or lp.get("id") or lp.get("css_path") or "target"
    _dom_appeared_logged = False
    _painted_logged = False
    # see _is_modal_content_painted's own return-value comment - tracks
    # the LAST reason seen across every poll iteration in this whole
    # verification window, so the force-interact fallback (right before
    # this function's own final timeout return, further down) can tell
    # whether scroll-retry was actually exhausted against a genuinely
    # unreachable target, specifically, rather than firing for some other
    # failure reason it was never meant to cover
    _last_paint_reason = None

    def _log_timing(phase):
        print(
            f"[modal-timing-detail] {phase} - target={_target_desc!r} "
            f"at +{(time.monotonic() - _t0) * 1000:.0f}ms from click dispatch"
        )

    def _confirmed(candidate_el):
        nonlocal _painted_logged, _last_paint_reason
        try:
            if candidate_el is None or not candidate_el.is_visible():
                return False
            if not (was_visible_before is False or _element_has_modal_ancestor(candidate_el)):
                return False
            # is_visible() only proves a real layout box, not that it's
            # actually painted where a viewer would see it right now
            # (see _MODAL_CONTENT_PAINTED_JS / _is_modal_content_painted
            # docstrings) - required in addition to, not instead of, the
            # structural checks above. STRICTLY scoped to real dialogs
            # (_element_is_in_aria_dialog, the role=dialog/aria-modal
            # signal only) rather than every candidate that reached this
            # point: _element_has_modal_ancestor's own looser fixed-
            # overlay heuristic just above can also match an ordinary,
            # already-working in-page element (a sticky CTA bar) that
            # has nothing to do with a modal - the paint check's own
            # opacity/elementFromPoint requirements are only meaningful
            # (and only safe to fail a step over) once we KNOW we're
            # actually looking at dialog content.
            if _element_is_in_aria_dialog(candidate_el):
                _painted_now, _last_paint_reason = _is_modal_content_painted(candidate_el)
                if _painted_now and not _painted_logged:
                    _painted_logged = True
                    _log_timing("content genuinely PAINTED (_is_modal_content_painted=True)")
                if not _painted_now:
                    return False
        except Exception:
            return False

        # was_visible_before=True means the caller already confirmed (via
        # its OWN pre-click snapshot, taken before this click fired at
        # all) that this exact target was already visible - i.e. this
        # click was never going to be the one that freshly opens
        # anything; it's an ordinary follow-up interaction inside a
        # dialog some EARLIER step in this same sequence already opened
        # (e.g. clicking a field to focus it before typing into it). The
        # freshness check right below exists to tell a genuinely-just-
        # opened dialog apart from a stale leftover from a PRECEDING,
        # unrelated action - it was never meant to demand fresh DOM
        # activity from a click that both the structural
        # (_element_has_modal_ancestor, checked above) AND temporal
        # (was_visible_before) evidence already agree opened nothing new.
        # Skipping it here is what the "ALREADY visible before" case
        # described in this function's own docstring calls for; without
        # this, an ordinary already-open-dialog interaction and a truly
        # stale leftover were indistinguishable (both show no fresh
        # mutation), incorrectly failing the former.
        if was_visible_before is True:
            return True

        # freshness check (see _arm_modal_mutation_tracker) - a visible,
        # structurally-modal-looking element is still not proof THIS
        # click opened it: it could be a stale leftover the PRECEDING
        # action's own modal left mid-teardown, especially when both
        # share the same reusable dialog container. Requires real DOM
        # activity to have happened AT OR AFTER the moment this specific
        # click was armed - read live from the page each time (never
        # threaded through as a parameter) since whichever click most
        # recently armed the tracker (the original, or a retry) is
        # always the right one to check against.
        try:
            _fresh = page.evaluate(_MODAL_FRESHNESS_CHECK_JS)
        except Exception:
            _fresh = None
        armed_at = _fresh.get("armedAt") if _fresh else None
        last_mut = _fresh.get("lastMutationTs") if _fresh else None
        if armed_at is None:
            # no marker was ever armed for this click (an older code
            # path that doesn't reach an arming point yet, or a hard
            # navigation wiped all page-side state) - nothing to check
            # freshness against, so this falls back to the prior
            # behavior rather than failing purely for missing
            # instrumentation
            return True
        last_mut_display = f"{last_mut:.1f}ms" if last_mut is not None else "(none observed since page load)"
        print(
            f"[modal-timing] click armed at {armed_at:.1f}ms (page clock) - "
            f"last DOM mutation observed at {last_mut_display}"
        )
        if last_mut is None:
            return False
        is_fresh = last_mut >= armed_at
        if not is_fresh:
            print(
                f"[modal-timing] STALE - last mutation ({last_mut:.1f}ms) "
                f"predates this click's own armed timestamp "
                f"({armed_at:.1f}ms) - this modal-looking element is "
                f"almost certainly a leftover from a PRECEDING action, "
                f"not a fresh result of this click"
            )
        return is_fresh

    _log_timing("click dispatched (verification loop starting)")
    _diag_window_start = time.monotonic()
    _install_modal_diagnostics(page)
    deadline = time.monotonic() + timeout_s
    found_but_not_confirmed = False
    while time.monotonic() < deadline:
        try:
            el = _resolve_element(page, lp)
            if el is not None:
                if not _dom_appeared_logged:
                    _dom_appeared_logged = True
                    _log_timing("target DOM node first appears (not yet confirmed visible/painted)")
                if _confirmed(el):
                    page.wait_for_timeout(STABILITY_RECHECK_MS)
                    _final_confirm_el = _resolve_element(page, lp)
                    if _confirmed(_final_confirm_el):
                        _save_modal_debug_screenshot(page, shot_dir, "confirmed-ready-to-interact")
                        _log_timing("CONFIRMED stable - ready to interact")
                        if _debug_pause_if_quantity:
                            # ================================================
                            # TEMPORARY DEBUG DUMP + PAUSE - one-off,
                            # requested to see exactly WHICH element the
                            # paint-check validated, and to independently
                            # check whether a real role=dialog/aria-modal
                            # container exists in the DOM at all at this
                            # moment (and if so, its own opacity/visibility/
                            # bbox) - since terminal logs already say
                            # painted=True and the value does change, but the
                            # 5s visual pause showed NOTHING on screen at
                            # all, not even a darkened overlay. Scoped to
                            # ONLY this one call (every other
                            # _wait_for_modal_target_visible call site passes
                            # the default _debug_pause_if_quantity=False, so
                            # no other step in the replay is slowed down or
                            # dumps anything). DELETE this whole `if` block,
                            # _ELEMENT_DEBUG_INFO_JS/_MODAL_DIALOG_CONTAINER_
                            # DEBUG_JS above, the _debug_pause_if_quantity
                            # parameter, and its call-site wiring once you've
                            # confirmed what you needed to see.
                            # ================================================
                            try:
                                _el_info = (
                                    _final_confirm_el.evaluate(_ELEMENT_DEBUG_INFO_JS)
                                    if _final_confirm_el is not None else None
                                )
                            except Exception as _e_dump:
                                _el_info = {"error": str(_e_dump)}
                            print(
                                "[DEBUG-DUMP] element the paint-check just validated as painted:\n"
                                + json.dumps(_el_info, indent=2)
                            )
                            try:
                                _dialog_candidates = page.evaluate(_MODAL_DIALOG_CONTAINER_DEBUG_JS)
                            except Exception as _e_dump2:
                                _dialog_candidates = {"error": str(_e_dump2)}
                            print(
                                "[DEBUG-DUMP] role=dialog/aria-modal candidate(s) in the DOM right now "
                                f"({len(_dialog_candidates) if isinstance(_dialog_candidates, list) else '?'} found):\n"
                                + json.dumps(_dialog_candidates, indent=2)
                            )
                            print("[DEBUG-PAUSE] quantity modal confirmed stable - pausing 5s for visual inspection")
                            try:
                                page.wait_for_timeout(5000)
                            except Exception:
                                pass
                        _arm_modal_interaction_timing(page, _t0, target_step)
                        return True, None
                    logger.debug(
                        "modal-stability-check: target was visible+confirmed once "
                        "but not %dms later - likely a flash/race, not a "
                        "genuinely stable open; continuing to poll",
                        STABILITY_RECHECK_MS,
                    )
                found_but_not_confirmed = True
        except Exception:
            pass
        page.wait_for_timeout(int(interval_s * 1000))
    _diag_window_end = time.monotonic()
    _log_timing(
        f"TIMEOUT after {timeout_s:.1f}s - dom_appeared={_dom_appeared_logged}, "
        f"content_painted={_painted_logged}, confirmed_stable=False"
    )

    # FORCE-INTERACT FALLBACK - last resort, ONLY after every scroll
    # mechanism has had the full window to work and the LAST thing
    # actually observed was still specifically 'out-of-viewport' (never
    # for 'hidden-ancestor'/'zero-opacity'/'occluded'/'unstable' - those
    # mean something else is genuinely wrong, not "real content that's
    # just unreachable by scroll", and force-clicking through THOSE would
    # be interacting with content that may not even be the right thing).
    # Confirmed live (both Playwright's scroll_into_view_if_needed() and
    # native JS scrollIntoView() had zero effect across the WHOLE 6s
    # window - see _sample_with_scroll_retry) that this exact target sits
    # inside a fixed-position dialog with no scrollable ancestor at all,
    # so no further scroll attempt here would do anything new; dispatches
    # a native JS click directly on the DOM node instead, bypassing
    # Playwright's coordinate-based input entirely. This deliberately
    # trades the "verified visually painted" guarantee this whole
    # function exists to provide for "the recorded interaction still
    # happens and its real effect gets checked afterward" - an explicit,
    # accepted tradeoff for a target confirmed unreachable any other way,
    # not a silent weakening of the check for anything that just timed
    # out for an ordinary reason.
    if _last_paint_reason == "out-of-viewport" and has_identifying_signal:
        print(
            "[force-interact] scroll exhausted, dispatching native JS "
            "interaction on unreachable element"
        )
        try:
            _fi_el = _resolve_element(page, lp)
        except Exception:
            _fi_el = None
        if _fi_el is not None:
            # SELF-DOCUMENTING SIGNAL: reuses _MODAL_SCROLL_BLOCKER_
            # DIAGNOSTIC_JS (same call _sample_with_scroll_retry already
            # makes - no new JS/logic added here) one more time, right at
            # the moment force-interact actually fires, so THIS specific
            # log line alone tells a human (on any site, not just the one
            # that first surfaced this) whether the pattern is "dialog
            # container is genuinely taller than a realistic viewport,
            # with no scrollable ancestor" - the confirmed Myntra/Sportzia
            # shape - without needing a fresh multi-turn investigation
            # each time it recurs.
            try:
                _fi_blockers = _fi_el.evaluate(
                    _MODAL_SCROLL_BLOCKER_DIAGNOSTIC_JS, REALISTIC_VIEWPORT_HEIGHT_PX
                )
                _fi_dialog = (_fi_blockers or {}).get("dialog_container")
                if _fi_dialog:
                    _fi_sh = _fi_dialog.get("scrollHeight")
                    _fi_over = (
                        (_fi_sh - REALISTIC_VIEWPORT_HEIGHT_PX)
                        if isinstance(_fi_sh, (int, float)) else None
                    )
                    print(
                        f"[force-interact] dialog container scrollHeight={_fi_sh} vs "
                        f"realistic viewport={REALISTIC_VIEWPORT_HEIGHT_PX} - "
                        + (
                            f"exceeds by {_fi_over:.0f}px, no scroll mechanism "
                            f"available (scrollable_ancestor="
                            f"{_fi_blockers.get('scrollable_ancestor')})"
                            if isinstance(_fi_over, (int, float)) and _fi_over > 0
                            else "does not exceed the realistic viewport - "
                            "out-of-viewport was likely due to POSITION "
                            "(e.g. a viewport-relative centering offset), "
                            "not container height"
                        )
                    )
                else:
                    print(
                        "[force-interact] no role=dialog/aria-modal ancestor found "
                        "on this target - scrollHeight-vs-viewport comparison not applicable"
                    )
            except Exception as _e_fi_diag:
                print(f"[force-interact] scroll-blocker re-check raised: {_e_fi_diag}")
            try:
                _fi_el.evaluate(
                    "(el) => { "
                    "  el.click(); "
                    "  el.dispatchEvent(new Event('change', { bubbles: true })); "
                    "  el.dispatchEvent(new Event('input', { bubbles: true })); "
                    "}"
                )
                _double_raf(page)
                page.wait_for_timeout(int(interval_s * 1000))
                _save_modal_debug_screenshot(page, shot_dir, "force-interact-after-click")
                # marks THIS recorded step (target_step - the check/click
                # step whose own target we just force-clicked) as already
                # handled, so the main replay loop's normal per-step
                # dispatch skips re-clicking it when it reaches this same
                # step next - see _MODAL_FORCE_INTERACTED_STEPS's own
                # comment for why a second click here is actively harmful,
                # not just redundant
                _mark_force_interacted(page, target_step)
                _arm_modal_interaction_timing(page, _t0, target_step)
                _log_timing(
                    "FORCE-INTERACT dispatched native click on unreachable "
                    "target - NOT visually confirmed painted; the recorded "
                    "flow's own final-value check (if any) is what actually "
                    "verifies this worked, not this function"
                )
                return True, None
            except Exception as _e_force:
                print(f"[force-interact] native JS interaction raised: {_e_force}")
        else:
            print("[force-interact] could not re-resolve the target element - falling through to normal failure")

    if found_but_not_confirmed:
        _save_modal_debug_screenshot(page, shot_dir, "timeout-found-not-confirmed")
        _print_modal_diag_window(page, _diag_window_start, _diag_window_end, "modal-open timeout (found, not confirmed)")
        return False, (
            "target element found in DOM but not visible/painted, or not "
            "inside an active modal - likely a stale or coincidental ID "
            "match, a real modal did not open, or its content is still "
            "mid-transition/never finished rendering"
        )
    _save_modal_debug_screenshot(page, shot_dir, "timeout-not-found")
    _print_modal_diag_window(page, _diag_window_start, _diag_window_end, "modal-open timeout (never found)")
    return False, (
        "navigated to modal URL but expected modal content did not render "
        "- click likely did not trigger the real UI handler"
    )


def _verify_modal_opened_or_retry(page, STEPS, i, url_before, target, shot_dir=None):
    """Shared by every navigate-step code path that can land on a
    fragment-only URL representing a modal-like sub-state (".../cart" ->
    ".../cart#modal") - there are multiple such paths in this file
    (a natural client-side transition already having arrived there
    before this navigate even runs, and the forced hard-navigation
    fallback when it hasn't), and this same verify-then-retry needs to
    apply identically to all of them, not just one. Never site-specific:
    "entering a modal substate" is detected purely from whether the
    navigate's own recorded fragment was newly ADDED relative to the
    page's fragment just before this step (never removed/unchanged - see
    the callers' own comments for why that direction is excluded).

    Verifies via _wait_for_modal_target_visible (the SAME stability-
    requiring check the click step's own lookahead already uses) that
    whatever the NEXT recorded action targets is genuinely, stably
    visible. If not, retries the ORIGINAL recorded click (the step
    immediately before this navigate) once, targeting the nearest
    genuinely-interactive ancestor/descendant of it (role="button"/
    onclick/cursor:pointer - see _find_alternate_clickable) rather than
    assuming the recorded element itself is the real clickable hit-area.

    Returns (ok, reason, retried) - ok=True with reason=None whenever
    there's nothing to verify (not entering a substate, or verification/
    retry succeeded); ok=False with a clear reason when the modal never
    became stably visible even after the retry. retried is True whenever
    a retry was actually attempted, purely for the caller's own logging.
    Never raises.
    """
    try:
        before_fragment = urlsplit(url_before).fragment
        target_fragment = urlsplit(target).fragment
    except Exception:
        before_fragment, target_fragment = None, None
    entering_substate = bool(target_fragment) and target_fragment != before_fragment
    inner_target_step = STEPS[i] if i < len(STEPS) else None
    if not (entering_substate and inner_target_step):
        return True, None, False

    modal_ok, modal_reason = _wait_for_modal_target_visible(page, inner_target_step, shot_dir=shot_dir)
    if modal_ok:
        return True, None, False

    print(f"[modal-content-check] FAILED: {modal_reason}")

    # the dialog container itself can genuinely be open (backdrop, role=
    # dialog, DONE button all present) while the SPECIFIC content this
    # function was waiting for (a quantity/size option) just hasn't
    # rendered yet - an async fetch triggered by the click that hasn't
    # resolved within the wait window above, not a click that failed to
    # do anything. Re-clicking the ORIGINAL trigger in that case is
    # actively harmful: it's almost always a toggle, so a second click
    # on it closes the already-open dialog (restarting its async load
    # from scratch, right back to the empty state) instead of giving the
    # in-flight fetch more time - this is what previously produced an
    # empty-looking modal that never recovered. Only worth retrying the
    # click when NOTHING modal-like is on the page at all, i.e. the
    # click genuinely had no observable effect.
    try:
        _dialog_already_open = bool(page.evaluate(_MODAL_DETECT_JS))
    except Exception:
        _dialog_already_open = False
    if _dialog_already_open:
        return False, (
            f"{modal_reason} - a dialog is already open on the page, so "
            "this is content that never finished rendering inside it, "
            "not a click that failed to open anything; not retrying the "
            "click since that would only toggle the dialog closed"
        ), False

    orig_click_step = STEPS[i - 2] if i >= 2 else None
    # same action types NAV_CAUSING_ACTIONS (defined inside run(), not
    # reachable from this module-level function) names elsewhere in this
    # file - inlined here rather than referencing that local
    _nav_causing_action_types = ("click", "dblclick", "right_click", "submit", "press")
    if not (orig_click_step and orig_click_step.get("action_type") in _nav_causing_action_types):
        return False, modal_reason, False

    orig_click_lp = orig_click_step.get("locator_profile") or {}
    orig_click_el = _resolve_element(page, orig_click_lp)
    if orig_click_el is None:
        return False, modal_reason, False

    alt_el = _find_alternate_clickable(orig_click_el)
    retry_el = alt_el or orig_click_el
    print(
        "[modal-retry] modal did not stably open after the recorded click "
        "- retrying once on "
        + ("an alternate ancestor/descendant element" if alt_el is not None else "the same recorded element")
    )
    try:
        _arm_modal_mutation_tracker(page)
        _retry_click_t0 = time.monotonic()
        # trusted mouse move/down/up rather than el.click() - a click
        # that was supposed to open a modal and didn't is exactly the
        # "verified no observable effect" case the trusted-event retry
        # exists for (see _trusted_mouse_click). Falls back to an
        # ordinary click only if the target has no measurable bounding
        # box for the low-level sequence to run against at all.
        if _trusted_mouse_click(page, retry_el):
            print("[click-mechanism] TRUSTED MOUSE SEQUENCE used for this modal-retry click")
        else:
            retry_el.click(timeout=3000)
            print("[click-mechanism] standard click used for this modal-retry click (no measurable bounding box)")
        retry_ok, _ = _wait_for_modal_target_visible(
            page, inner_target_step, shot_dir=shot_dir, click_dispatched_at=_retry_click_t0,
        )
    except Exception:
        retry_ok = False

    if retry_ok:
        print("[modal-retry] retry succeeded - dialog is now stably visible, proceeding normally")
        return True, None, True

    print(
        "[modal-retry] retry did not open the modal either - marking this "
        "step FAILED rather than silently continuing to later steps"
    )
    return False, modal_reason, True


def _urls_same_target(url, target):
    """Like the navigate step's own _same_route (see the "navigate"
    branch further down) - but deliberately INCLUDES the URL fragment
    (#...) in the comparison, where that one leaves it out.

    _same_route's job is "has the SPA already gotten roughly to this
    route" for deciding whether a full reload is needed - a fragment-
    only difference genuinely doesn't warrant one there. This function's
    job is the opposite: verifying that a CLICK's own recorded effect
    actually happened, and on a real site a client-side modal/panel
    opening is frequently encoded purely as a fragment change
    (".../cart" -> ".../cart#modal") with nothing else about the URL
    moving at all. Ignoring the fragment here would make this check
    silently pass for a click that changed nothing whatsoever - exactly
    the false-PASS this exists to catch.
    """
    try:
        cu, tu = urlsplit(url), urlsplit(target)
    except Exception:
        return url == target
    return (
        cu.scheme, cu.netloc, cu.path.rstrip("/") or "/", cu.query, cu.fragment
    ) == (
        tu.scheme, tu.netloc, tu.path.rstrip("/") or "/", tu.query, tu.fragment
    )


def _wait_for_effect_url(page, target_url, timeout_s=EFFECT_VERIFY_TIMEOUT_S, interval_s=0.3):
    """Polls page.url for up to timeout_s, waiting for it to reach
    target_url (fragment-inclusive - see _urls_same_target above).
    Never raises; returns a plain True/False.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            if _urls_same_target(page.url, target_url):
                return True
        except Exception:
            return False
        page.wait_for_timeout(int(interval_s * 1000))
    try:
        return _urls_same_target(page.url, target_url)
    except Exception:
        return False


def _find_modal_check_value(steps, start_index, close_url):
    """Scans the RECORDING forward from start_index (0-based - the step
    right after a navigate-to-modal-style-URL) looking for a "check"
    step's own recorded value - generically, whatever it is (a
    quantity, a size, a color, ...), never a hardcoded concept. Stops as
    soon as either:
      - a "check" step with a non-empty recorded text is found (returns
        that text), or
      - a "navigate" step whose own page_url already matches close_url
        is reached first (the sequence closed with no check in it - not
        this pattern, returns None).
    Purely structural: driven entirely by action_type and recorded
    fields already in the JSON, never any element/site-specific detail.
    """
    for j in range(start_index, len(steps)):
        s_type = steps[j].get("action_type")
        if s_type == "navigate" and steps[j].get("page_url") == close_url:
            return None
        if s_type == "check":
            lp = steps[j].get("locator_profile") or {}
            # element_text (the element's own rendered/innerText content)
            # is the authoritative "what was actually selected" signal -
            # PREFERRED over text (which is often accessible_name/aria-
            # label under the hood, see buildProfile() in action_capture.
            # js: text = accessible_name || element_text). These two can
            # genuinely disagree on a real site (confirmed: a quantity
            # option recorded with accessible_name="1" and its own
            # visible/selected text="7" - reading accessible_name here
            # reports the WRONG value as "what was selected", even when
            # the surrounding pass/fail verdict is otherwise correct).
            # Logged whenever they differ so a mismatch like this is
            # visible in the terminal/report going forward, not silently
            # picked one way or the other.
            _element_text_val = (lp.get("element_text") or "").strip()
            _accessible_text_val = (lp.get("text") or "").strip()
            if _element_text_val and _accessible_text_val and _element_text_val.lower() != _accessible_text_val.lower():
                print(
                    f"[modal-check-value] NOTE: recorded accessible_name/text "
                    f"{_accessible_text_val!r} differs from the element's own "
                    f"rendered element_text {_element_text_val!r} for this "
                    f"'check' step - using element_text {_element_text_val!r} "
                    f"as the actual selected value, not accessible_name"
                )
            val = (_element_text_val or _accessible_text_val).strip()
            if val:
                return val
    return None


def _wait_for_visible_and_stable(page, selector, timeout_ms=WAIT_FOR_PORTAL_READY_TIMEOUT_MS):
    """Waits for `selector` to reach Playwright's own 'visible' state (not
    just attached/present in the DOM), then waits briefly for its computed
    opacity to stop changing between two samples - covers a CSS-only
    reveal that's technically "visible" the instant a transition/animation
    *starts*, not once it's actually settled (a fade-in, an expand). Always
    re-queries `selector` fresh via page.locator() rather than working off
    a handle resolved earlier, so this behaves the same whether the target
    already existed hidden, or was only just mounted into a different part
    of the DOM entirely (a portal/overlay appended elsewhere). Never
    raises; returns True once visible (whether or not opacity fully
    settled within the remaining time - visibility is the real, load-
    bearing signal), False only if it never became visible at all within
    timeout_ms.
    """
    deadline = time.monotonic() + (timeout_ms / 1000.0)
    try:
        page.wait_for_selector(selector, state="visible", timeout=timeout_ms)
    except Exception:
        return False

    try:
        prev_opacity = page.locator(selector).first.evaluate("el => getComputedStyle(el).opacity")
    except Exception:
        return True

    remaining_ms = max(0, int((deadline - time.monotonic()) * 1000))
    while remaining_ms > 0:
        page.wait_for_timeout(min(VISIBILITY_STABLE_SAMPLE_MS, remaining_ms))
        try:
            cur_opacity = page.locator(selector).first.evaluate("el => getComputedStyle(el).opacity")
        except Exception:
            return True
        if cur_opacity == prev_opacity:
            return True
        prev_opacity = cur_opacity
        remaining_ms = max(0, int((deadline - time.monotonic()) * 1000))

    logger.debug(
        "_wait_for_visible_and_stable: %r became visible but opacity was "
        "still changing when the window ran out - proceeding anyway",
        selector,
    )
    return True


def wait_for_stable_state(page, selector, expected_text=None, must_be_enabled=True, timeout=WAIT_FOR_STABLE_STATE_TIMEOUT_MS):
    """Waits for `selector` to reach its FINAL state after a prior action
    likely to trigger a UI transition (a disabled "SELECT SIZE" button
    swapping into an enabled "ADD TO BAG" once a size is picked, a toggle
    flipping, a field validating) - not just present, but actually
    visible, optionally enabled, and optionally showing expected_text.
    A locator match alone doesn't mean any of that: the same DOM node can
    still be sitting there disabled, showing its PRE-transition text, for
    a brief real window while the site's own JS finishes reacting - every
    strategy correctly reports "not found" (by the recorded, post-
    transition profile) purely because that state hasn't happened yet,
    not because the locator is wrong.

    Every condition is polled via Playwright's own condition-waiting
    primitives (wait_for_selector / wait_for_function) - never a fixed
    sleep(). Non-fatal: returns True once every requested condition
    holds, False if `timeout` (ms) elapses first, but never raises -
    callers proceed either way, since Playwright's own per-call
    actionability wait still applies on top of this regardless. This
    exists purely to give a real, in-flight transition a dedicated,
    text-aware chance to finish BEFORE the normal resolution/retry logic
    even starts, instead of only discovering "not found yet" the slow way
    through repeated failed tier attempts.
    """
    deadline = time.monotonic() + (timeout / 1000.0)

    try:
        page.wait_for_selector(selector, state="attached", timeout=timeout)
    except Exception:
        return False

    # CSS-hidden check (display/visibility only), deliberately NOT
    # Playwright's own state="visible" - that also requires a non-zero
    # rendered area, which a genuinely zero-size element (an icon-wrapper
    # button - exactly smart_click()'s own case, and plausibly the SAME
    # real button this function is waiting on) can never satisfy no
    # matter how long this waits. This still correctly waits out a real
    # display:none/visibility:hidden toggle, just without accidentally
    # excluding the zero-area case smart_click() is designed to click
    # anyway once this function hands off to the normal resolution flow.
    remaining_ms = max(500, int((deadline - time.monotonic()) * 1000))
    try:
        page.wait_for_function(
            "(sel) => { "
            "const el = document.querySelector(sel); "
            "if (!el) return false; "
            "const s = getComputedStyle(el); "
            "return s.display !== 'none' && s.visibility !== 'hidden'; "
            "}",
            arg=selector,
            timeout=remaining_ms,
        )
    except Exception:
        return False

    if must_be_enabled:
        remaining_ms = max(500, int((deadline - time.monotonic()) * 1000))
        try:
            page.wait_for_function(
                "(sel) => { "
                "const el = document.querySelector(sel); "
                "return !!el && !el.disabled && el.getAttribute('aria-disabled') !== 'true'; "
                "}",
                arg=selector,
                timeout=remaining_ms,
            )
        except Exception:
            return False

    if expected_text:
        remaining_ms = max(500, int((deadline - time.monotonic()) * 1000))
        try:
            page.wait_for_function(
                # innerText/value covers ordinary text content; aria-label
                # is checked too since an icon-only button (exactly the
                # kind this whole fix exists for) commonly has no visible
                # text at all - its "ADD TO BAG"-style label only exists
                # as an accessible name, same priority accessibleName()
                # already uses at record time
                "([sel, txt]) => { "
                "const el = document.querySelector(sel); "
                "if (!el) return false; "
                "const t = (el.innerText || el.value || el.getAttribute('aria-label') || '').trim(); "
                "return t.includes(txt); "
                "}",
                arg=[selector, expected_text],
                timeout=remaining_ms,
            )
        except Exception:
            return False

    return True


def wait_for_portal_ready(page, trigger_selector, target_selector, timeout=WAIT_FOR_PORTAL_READY_TIMEOUT_MS):
    """Clicks/activates `trigger_selector`, then waits for `target_selector`
    to become genuinely visible and settled - the general-purpose, callable
    version of the CSS-only-toggle/portal-mount problem: content already IN
    the DOM but not yet "visible" per Playwright's own actionability
    definition (a display:none/height:0 section mid-expand), or content
    that only gets mounted into a different part of the DOM entirely (a
    modal/overlay appended to <body>) once the trigger fires. Always
    re-queries target_selector fresh (via _wait_for_visible_and_stable,
    never a handle resolved before the trigger click), since a portal-
    mounted target may not exist as a node at all until after that click.
    """
    # the trigger itself is often exactly the kind of icon-only control
    # smart_click() exists for (an expand/toggle chevron, a "view
    # details" icon button), so it gets the same zero-size protection as
    # every other click in this file rather than a bare .click()
    smart_click(page, trigger_selector, standard_timeout=timeout)
    return _wait_for_visible_and_stable(page, target_selector, timeout_ms=timeout)


def _wait_for_selector_or_text(page, selector=None, text=None, text_target_selector=None, timeout=8000, must_be_enabled=False):
    """Shared "selector OR text" wait used by add_to_cart_and_verify()'s
    confirmation/verification/next-action-ready checks below - each of
    those is either "a distinct element becomes visible" (selector, via
    Playwright's own wait_for_selector(state="visible")) or "the already-
    clicked control's own text changes in place" (text, checked against
    text_target_selector via wait_for_stable_state - state="attached" +
    a display/visibility check, not Playwright's state="visible", since
    that also requires non-zero area and would never resolve for a
    zero-size icon-wrapper control). text with no text_target_selector
    searches for that text anywhere on the page instead (page.get_by_text)
    - the right shape for a verification string with no known stable
    selector. Callers supply whichever actually matches their site's
    behavior; this never raises, always returns True/False. Nothing
    matched at all (both selector and text are None) is trivially
    satisfied - not every check applies to every step.
    """
    if selector:
        try:
            page.wait_for_selector(selector, state="visible", timeout=timeout)
            return True
        except Exception:
            return False
    if text:
        if text_target_selector:
            return wait_for_stable_state(
                page, text_target_selector,
                expected_text=text, must_be_enabled=must_be_enabled, timeout=timeout,
            )
        try:
            page.get_by_text(text).first.wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return False
    return True


def add_to_cart_and_verify(
    page,
    click_selector,
    confirmation_selector=None,
    confirmation_text=None,
    next_action_selector=None,
    next_action_text=None,
    verification_selector=None,
    verification_text=None,
    max_retries=ADD_TO_CART_MAX_RETRIES,
    confirmation_timeout=ADD_TO_CART_CONFIRMATION_TIMEOUT_MS,
    verification_timeout=ADD_TO_CART_VERIFICATION_TIMEOUT_MS,
):
    """Generic click -> wait-for-confirmation -> next-click -> verify ->
    retry-if-failed sequence for an "add to cart"-style flow whose real
    success can only be confirmed by watching the UI transition through a
    confirmation state, then checking what the destination it leads to
    actually shows - not by the initial click alone completing without
    error. Confirmed root cause on a real site: the click itself never
    raises, but the underlying server-side request it triggers can still
    be in flight when the very next step (navigating onward) fires - so
    the destination genuinely shows an empty/incomplete result even
    though nothing "failed" from Playwright's own point of view. A
    locator that resolves and clicks cleanly is not the same thing as the
    action it was supposed to trigger having actually finished.

    Every string here is a caller-supplied PARAMETER - no "add to cart"/
    "add to bag"/site-specific wording is hardcoded inside this function,
    and it is never invoked automatically by pattern-matching recorded
    button text anywhere in this file. A step opts into it explicitly via
    the "add_to_cart_and_verify" action_type below, filled in with
    whatever selectors/text a specific recording actually observed - the
    engine itself stays blind to what any of it means.

    confirmation_selector/confirmation_text and verification_selector/
    verification_text are each an EITHER/OR pair (see
    _wait_for_selector_or_text): a distinct element appearing (a
    checkmark icon, a toast) vs. the clicked control's own text changing
    in place, or a page's visible text with no known stable selector.
    Pass whichever shape actually matches what a given site does.

    Unlike this function's original reference sketch, a confirmation
    timeout or a verification failure both retry the WHOLE sequence from
    a freshly reloaded copy of the page this call started on - page.
    click(click_selector) alone on a bare retry would silently do nothing
    useful once the first attempt has already navigated away from that
    page (click_selector no longer exists there), which would make retry
    a no-op exactly when it's needed most.

    next_action_text matters specifically when next_action_selector is
    the SAME element as click_selector - a real, common pattern where one
    control cycles through several states in place ("ADD TO BAG" ->
    "Added to Bag" -> "GO TO BAG"). Clicking that element again the
    instant confirmation appears can land WHILE it's still showing the
    confirmation state, not yet its final "ready for the next step" text
    - Playwright's own actionability wait has no way to know the SAME
    clickable element's click handler behaves differently depending on
    its current text, so it happily clicks too early and re-triggers the
    first click's own effect instead of advancing. Giving next_action_text
    makes this function wait for THAT specific text first, closing the
    race by construction instead of guessing at a settle delay. Leave it
    None when next_action_selector is a genuinely separate, always-
    present control with no in-place text transition to wait out.

    Returns (ok, message, attempts_made) rather than raising, matching
    this file's existing action-result convention (the caller already
    wraps every action_type's execution in its own try/except and reports
    ok/err through the shared per-step result, not a propagated
    exception).
    """
    # captured up front so a retry can return to a genuinely FRESH copy
    # of the starting page - page.go_back() alone risks the browser's own
    # back/forward cache restoring the page with the click target's
    # mutated post-click state (text/handler already swapped from the
    # previous attempt) still intact rather than a clean reload, which
    # would silently turn "retry the click" into "re-trigger whatever the
    # control now does instead", on any site whose control similarly
    # mutates itself in place
    try:
        start_url = page.url
    except Exception:
        start_url = None

    def _reload_for_retry(attempt):
        if not start_url:
            return False, "could not retry - the starting page's own URL was never captured"
        print(f"[add-to-cart] retrying - reloading {start_url!r} fresh before attempt {attempt + 1}")
        try:
            # a fresh goto(), not go_back() - see the note on start_url
            # above for why
            page.goto(start_url, wait_until="domcontentloaded", timeout=confirmation_timeout)
            return True, None
        except Exception as e:
            return False, f"could not reload the starting page to retry: {e}"

    last_message = "never attempted"
    for attempt in range(1, max_retries + 1):
        print(f"[add-to-cart] attempt {attempt}/{max_retries}: clicking {click_selector!r}")
        try:
            smart_click(page, click_selector)
            logger.debug("[add-to-cart] click fired (attempt %d)", attempt)
        except Exception as e:
            last_message = f"click failed: {e}"
            print(f"[add-to-cart] attempt {attempt}: {last_message}")
            if attempt >= max_retries:
                break
            reloaded, reload_err = _reload_for_retry(attempt)
            if not reloaded:
                last_message = reload_err
                print(f"[add-to-cart] {last_message}")
                break
            continue

        confirmed = _wait_for_selector_or_text(
            page, selector=confirmation_selector, text=confirmation_text,
            text_target_selector=click_selector, timeout=confirmation_timeout,
        )
        if not confirmed:
            last_message = "confirmation not seen"
            print(f"[add-to-cart] attempt {attempt}: {last_message}, retrying")
            if attempt >= max_retries:
                break
            reloaded, reload_err = _reload_for_retry(attempt)
            if not reloaded:
                last_message = reload_err
                print(f"[add-to-cart] {last_message}")
                break
            continue
        print(f"[add-to-cart] attempt {attempt}: confirmation seen")

        if next_action_selector:
            if next_action_text:
                ready = _wait_for_selector_or_text(
                    page, text=next_action_text, text_target_selector=next_action_selector,
                    timeout=confirmation_timeout, must_be_enabled=True,
                )
                print(
                    f"[add-to-cart] attempt {attempt}: next-action ready state "
                    f"{next_action_text!r} {'seen' if ready else 'NOT seen - clicking anyway'}"
                )
            try:
                smart_click(page, next_action_selector)
                print(f"[add-to-cart] attempt {attempt}: clicked next-action control {next_action_selector!r}")
            except Exception as e:
                last_message = f"next-action click failed: {e}"
                print(f"[add-to-cart] attempt {attempt}: {last_message}")
                if attempt >= max_retries:
                    break
                reloaded, reload_err = _reload_for_retry(attempt)
                if not reloaded:
                    last_message = reload_err
                    print(f"[add-to-cart] {last_message}")
                    break
                continue

        verified = _wait_for_selector_or_text(
            page, selector=verification_selector, text=verification_text,
            timeout=verification_timeout,
        )
        if verified:
            print(f"[add-to-cart] attempt {attempt}: verified successfully")
            return True, "verified", attempt

        last_message = "verification failed"
        print(f"[add-to-cart] attempt {attempt}: {last_message}, retrying")
        if attempt >= max_retries:
            break
        reloaded, reload_err = _reload_for_retry(attempt)
        if not reloaded:
            last_message = reload_err
            print(f"[add-to-cart] {last_message}")
            break

    print(f"[add-to-cart] giving up after {max_retries} attempt(s): {last_message}")
    return False, last_message, max_retries


def _wait_for_page_settle(page, timeout_s=6.0, quiet_window_ms=500):
    """Waits for the CURRENT page to be genuinely, fully loaded - not
    still showing a loading skeleton/spinner/placeholder state - using
    two generic signals together, network-idle then DOM-mutation-quiet.
    Used by the "screenshot" action type (see _capture_screenshot_when_
    settled) - fully generic, no site-specific selectors or hardcoded
    wait times.

    1. Network idle first, reusing the existing _settle() - a bounded,
       best-effort wait on its own, so a page with constant background
       network activity can't consume this whole function's budget by
       itself.
    2. Then watches the page's visible DOM via a MutationObserver,
       resolving once mutations have gone quiet for quiet_window_ms.
       Critically, that quiet window only ever starts counting once a
       mutation has actually happened at least once - a page that never
       mutates during this call (either genuinely static, or one whose
       loading skeleton hasn't even started being replaced yet) is NOT
       treated as "already settled" just because nothing has happened
       YET; it only resolves via the overall timeout below instead,
       which is exactly what correctly covers a genuinely static/
       already-final page too.

    The whole wait is bounded by timeout_s overall - once that elapses,
    this simply returns and the caller proceeds with whatever state
    exists at that point (a page with constant polling/animation can
    never hang the replay). Best-effort throughout: any error here is
    swallowed, never a reason to fail the action this is attached to.
    """
    deadline = time.monotonic() + timeout_s

    _settle(page)

    remaining_ms = max(500, int((deadline - time.monotonic()) * 1000))

    try:
        page.evaluate(
            """
            ([timeoutMs, quietMs]) => {
                return new Promise((resolve) => {
                    let quietTimer = null;
                    let overallTimer = null;

                    function finish() {
                        if (quietTimer) clearTimeout(quietTimer);
                        if (overallTimer) clearTimeout(overallTimer);
                        observer.disconnect();
                        resolve();
                    }

                    const observer = new MutationObserver(() => {
                        // (re)start the quiet window only once something
                        // has actually mutated - never resolve just
                        // because nothing has happened YET
                        if (quietTimer) clearTimeout(quietTimer);
                        quietTimer = setTimeout(finish, quietMs);
                    });

                    observer.observe(document.body, {
                        childList: true,
                        subtree: true,
                        attributes: true,
                        characterData: true,
                    });

                    // the only thing that can resolve this before any
                    // mutation has ever happened - covers a genuinely
                    // static/already-final page, and bounds the wait
                    // overall for a page with constant activity
                    overallTimer = setTimeout(finish, timeoutMs);
                });
            }
            """,
            [remaining_ms, quiet_window_ms],
        )
    except Exception:
        pass


def resolve_and_act(page, step, prev_action_type=None, fast_fail=False, turbo=False):
    """Try each locator strategy in priority order, then perform the step's
    action. Strongest/most stable signals first (test-automation attributes,
    id, other stable attributes), generic/fragile ones last.

    prev_action_type is the action_type of the immediately preceding
    RECORDED step (or None for the first step / when unknown) - used only
    for the pre-click state-fingerprint check below, never for locating
    anything.

    fast_fail, when True, means the navigate that led to this step already
    signaled its destination target never became findable - this step
    still gets one normal-speed resolution attempt, it just skips the
    settle-and-recheck and scroll-and-recheck escalation tiers if that
    attempt fails, so it reports failure quickly instead of repeating the
    full expensive retry cycle for a step whose page likely never loaded.

    turbo, when True, skips ONLY the purely cosmetic character-by-
    character typing simulation a "fill" action normally does (see
    _do_fill's own docstring) in favor of a single instant el.fill() -
    every wait that exists for actual correctness (settle/networkidle
    waits, the fill verify-and-retry loop, hover-reveal detection, the
    no-observable-effect click retry) runs exactly the same either way.
    Real Replay (run()'s own step loop) never passes this - it's False
    by default and only ever set True by the Pick Element picker's own
    best-effort preceding-actions walk (recorder/pick_element.py), whose
    entire purpose is reaching the right page state as fast as possible
    for a human to click something, not demonstrating realistic pacing.

    Unlike a simple "first tier that finds anything wins" search, EVERY
    tier that finds an element gets an actual attempt at the action before
    moving on - a tier can locate the right element in the DOM while that
    element is temporarily not visible/actionable (mid-animation, behind
    an overlay, hidden at the current viewport), and only the interaction
    itself reveals that. Falling through to the next tier in that case
    (rather than declaring the step failed) is what "use fallback locators
    if the primary locator fails" means in practice, not just "if the
    primary locator finds nothing."

    Returns (strategy_used, element_found, success, error_message).
    element_found is True for any real locator hit (everything except the
    bounding-box fallback, which still lets the step succeed but does NOT
    count as "found" for UI element validation purposes.
    """
    lp = step.get("locator_profile") or {}
    attrs = lp.get("attributes") or {}
    action_type = step.get("action_type")
    value = step.get("value")

    # an action type this executor has no handler for must never be
    # silently treated as a no-op success just because a locator happened
    # to resolve - fail it outright, clearly labeled, before spending any
    # time searching for an element to act on
    SUPPORTED_ACTIONS = ("click", "dblclick", "right_click", "fill", "select", "submit", "press", "check")
    if action_type not in SUPPORTED_ACTIONS:
        return None, False, False, f"UNSUPPORTED action_type: {action_type!r}"

    # portal-readiness pre-check: a recorded css_path starting with
    # "body > " (rather than the main app root) is a generic, structural
    # signal that this target lives inside a portal/overlay element
    # (modal, popup, bottom-sheet, dropdown-suggestions) appended
    # directly to <body> outside the main app container - never a
    # site-specific string/class/element check, works identically on
    # any site. These elements provably don't exist in the DOM yet at
    # the moment a scripted replay reaches them, even though a human's
    # natural pace lets them render first - confirmed by two separate
    # real failures (a suggestion dropdown, a size-selection popup)
    # where every resolution strategy reported found=False
    # simultaneously, which only happens when the element genuinely
    # isn't there yet. This runs BEFORE any resolution strategy is
    # attempted (not after they've already failed), giving them a fair
    # chance to find something that has actually rendered by the time
    # they run. Purely additive: every existing strategy, the
    # scroll-and-recheck tier, and the bounding_box fallback all still
    # run exactly as already fixed, completely unaffected for the
    # ordinary (non-portal) case.
    if (lp.get("css_path") or "").startswith("body > "):
        try:
            baseline_body_children = page.evaluate("document.body.children.length")
        except Exception:
            baseline_body_children = None

        if baseline_body_children is not None:
            try:
                # native Playwright polling primitive - waits until the
                # condition is true or the timeout elapses, whichever
                # first. 9000ms matches the SAME readiness-wait
                # convention _wait_for_next_step_ready already uses
                # elsewhere in this file (timeout_s=9.0) for exactly
                # this kind of "give the page a real chance to finish
                # rendering" check - not a newly-invented duration.
                page.wait_for_function(
                    "(baseline) => document.body.children.length > baseline",
                    arg=baseline_body_children,
                    timeout=9000,
                )
                logger.debug(
                    "portal-readiness wait: a new body-level element appeared "
                    "(body.children.length grew past %d) before resolving this step",
                    baseline_body_children,
                )
                # a mounted DOM node isn't necessarily a VISIBLE one yet -
                # a portal that appends its container before its own
                # CSS-driven reveal (fade/expand) finishes is "attached"
                # right away but not actually "visible" per Playwright's
                # own actionability definition for a little longer.
                # Reuses the same shared helper wait_for_portal_ready()
                # below is built on, so this doesn't duplicate that
                # visibility/opacity-stability logic - just applies it
                # here too, for the portal case this check already
                # detects. css_path is guaranteed non-empty inside this
                # branch (the "body > " check above requires it).
                _wait_for_visible_and_stable(page, lp["css_path"], timeout_ms=9000)
            except Exception:
                logger.debug(
                    "portal-readiness wait: timed out waiting for a new "
                    "body-level element to appear (baseline was %d children) "
                    "- proceeding with resolution anyway",
                    baseline_body_children,
                )

    # generic overlay-blocking guard: before ANY resolution strategy is
    # attempted, check whether some OTHER body-level element (the same
    # structural portal signal as above - appended directly to <body>,
    # outside the main app root) currently covers this step's own
    # recorded target position (or a large share of the viewport) and
    # would therefore swallow/block a genuine interaction with the real
    # target underneath it (a leftover loading overlay, a modal from a
    # previous step that hasn't closed yet, a toast/backdrop). Purely
    # structural - bounding-box overlap plus body-level DOM position -
    # no class name, id, or text is ever inspected, so this works
    # identically on any site. Skipped entirely when THIS step's own
    # target IS itself a body-level element: the portal-readiness check
    # above already handles that case, and waiting for an "overlay" to
    # disappear that is actually this step's own target would deadlock.
    if not (lp.get("css_path") or "").startswith("body > "):
        target_box = step.get("bounding_box") or {}
        # candidates are restricted to elements taken OUT of normal
        # document flow (position: fixed/absolute) - a purely structural,
        # computed-style signal (never a class/id/text check) that
        # reliably distinguishes a real overlay/modal/backdrop (which has
        # to be fixed/absolute to visually float above the rest of the
        # page in the first place) from the page's own normal in-flow
        # content wrapper. Without this, the site's own main content root
        # (itself a body-level element whose box always contains whatever
        # it wraps) would match its OWN normal content as "blocking" it -
        # a false positive on literally every ordinary step, not just
        # portal/overlay cases.
        _OVERLAY_CHECK_JS = """([tb]) => {
            const vw = window.innerWidth, vh = window.innerHeight;
            const viewportArea = vw * vh;
            for (const el of document.body.children) {
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden') continue;
                if (style.position !== 'fixed' && style.position !== 'absolute') continue;
                const r = el.getBoundingClientRect();
                if (r.width <= 0 || r.height <= 0) continue;
                const elArea = r.width * r.height;
                let overlaps = viewportArea > 0 && (elArea / viewportArea) >= 0.6;
                if (!overlaps && tb && tb.width && tb.height) {
                    const ix = Math.max(0, Math.min(r.right, tb.x + tb.width) - Math.max(r.left, tb.x));
                    const iy = Math.max(0, Math.min(r.bottom, tb.y + tb.height) - Math.max(r.top, tb.y));
                    const interArea = ix * iy;
                    const targetArea = tb.width * tb.height;
                    overlaps = targetArea > 0 && (interArea / targetArea) >= 0.6;
                }
                if (overlaps) return true;
            }
            return false;
        }"""
        try:
            overlay_blocking = page.evaluate(_OVERLAY_CHECK_JS, [target_box])
        except Exception:
            overlay_blocking = False

        if overlay_blocking:
            # an unexpected overlay this recorded sequence never accounts
            # for (a promotional popup, say) commonly does NOT auto-
            # dismiss on its own within any reasonable wait - it just sits
            # there until something closes it, unlike a transient loading
            # spinner. Actively attempting to dismiss it FIRST (the same
            # generic Escape-then-close-button recovery _try_dismiss_
            # overlay already uses reactively elsewhere in this file, run
            # here proactively instead) is what actually clears the
            # common real case; the wait-for-removal loop below remains
            # as a fallback for the kind of overlay that genuinely does
            # go away on its own (nothing to click, just needs time).
            logger.debug(
                "overlay-blocking guard: a body-level element currently "
                "covers this step's target area - attempting to dismiss it"
            )
            _try_dismiss_overlay(page)
            try:
                overlay_blocking = page.evaluate(_OVERLAY_CHECK_JS, [target_box])
            except Exception:
                overlay_blocking = False

        if overlay_blocking:
            logger.debug(
                "overlay-blocking guard: still blocked after dismissal "
                "attempt - waiting (up to 9.0s) for it to be removed "
                "before resolving"
            )
            try:
                page.wait_for_function(
                    "(args) => !(" + _OVERLAY_CHECK_JS + ")(args)",
                    arg=[target_box],
                    timeout=9000,
                )
                logger.debug("overlay-blocking guard: blocking overlay removed - proceeding")
            except Exception:
                logger.debug(
                    "overlay-blocking guard: timed out waiting for the "
                    "blocking overlay to be removed - proceeding with "
                    "resolution anyway"
                )

    # post-scroll DOM stabilization: a click immediately preceded (in the
    # RECORDING) by a scroll action is exactly the case where the page
    # may still be settling right as replay reaches it - lazy-loaded
    # images/sections finishing their own layout shift a moment after
    # the scroll step's own target-position verification above already
    # landed it correctly. Reuses _wait_for_page_settle's existing
    # MutationObserver-based "DOM mutations have gone quiet" signal
    # (already used elsewhere in this file for screenshot timing) rather
    # than a new mechanism - just with a short quiet window matching "no
    # further layout shifts for ~200-300ms", bounded overall, never an
    # open-ended wait. Generic: keyed purely on the PRECEDING recorded
    # action_type, never any element/site detail.
    if action_type in ("click", "dblclick", "right_click", "check") and prev_action_type == "scroll":
        _wait_for_page_settle(page, timeout_s=POST_SCROLL_SETTLE_TIMEOUT_S, quiet_window_ms=POST_SCROLL_QUIET_WINDOW_MS)

    # state-dependent target readiness: a prior interaction (a size
    # pick, a toggle) can trigger the site's OWN JS to swap this step's
    # target from one state into another (a disabled "SELECT SIZE"
    # button becoming an enabled "ADD TO BAG", say) - the recorded
    # locator_profile reflects the POST-transition state, so if that
    # transition hasn't finished yet, resolution correctly reports "not
    # found"/"not enabled" purely because that state hasn't happened
    # YET, not because anything about the locator is wrong.
    # wait_for_stable_state() gives that real, in-flight transition a
    # bounded, condition-based (never a fixed sleep) chance to actually
    # finish before the tier search below even starts, instead of only
    # discovering "not ready yet" the slow way through repeated failed
    # attempts.
    #
    # Auto-inference is deliberately narrower than the pre-click state-
    # fingerprint check further below (which reuses "immediately
    # preceded by a click/check/select/fill" - fine there, since that
    # check is cheap and purely informational). Here it's ALSO gated on
    # the target looking like a genuine state-carrying control (button/
    # link, or an explicit interactive role) - a click on an ordinary
    # <input>/<textarea>/<select> that simply happens to follow a fill
    # (clicking the next field in a form, the everyday case) is not a
    # state-dependent trigger at all, and this function's own
    # expected_text check would be comparing against the WRONG thing for
    # one anyway (an input's recorded "text" is its placeholder-derived
    # accessible name, never what wait_for_stable_state should expect
    # its live value/innerText to equal) - without this, an ordinary
    # click could burn wait_for_stable_state's full timeout for nothing.
    # Still available for anything else via the explicit per-step
    # wait_for_stable_state flag. Needs a plain CSS selector to poll (id
    # or css_path); skipped entirely when neither was recorded, same as
    # every other best-effort signal in this function - never raises,
    # never blocks the tier search below from still running normally
    # regardless of the outcome here.
    if action_type in ("click", "check"):
        _explicit_stable_wait = bool(step.get("wait_for_stable_state"))
        _tag = (lp.get("tag") or "").lower()
        _role = (attrs.get("role") or "").lower()
        _looks_state_carrying = _tag in ("button", "a") or _role in (
            "button", "switch", "tab", "menuitem", "checkbox", "radio",
        )
        _auto_infer_stable_wait = _looks_state_carrying and prev_action_type in (
            "click", "check", "select", "fill",
        )
        _stable_selector = lp.get("id") or lp.get("css_path")
        if (_explicit_stable_wait or _auto_infer_stable_wait) and _stable_selector:
            _stable_timeout = step.get("wait_for_stable_state_timeout_ms") or WAIT_FOR_STABLE_STATE_TIMEOUT_MS
            # expected_text only makes sense for the state-carrying case
            # above (a label that changes) - never derived for a plain
            # input/textarea/select even under an explicit opt-in flag,
            # since the mismatch described above is about what the
            # recorded "text" field MEANS for that tag, not about how
            # this wait got triggered
            _expected_text = (lp.get("text") or lp.get("element_text") or None) if _looks_state_carrying else None
            _became_stable = wait_for_stable_state(
                page,
                _stable_selector,
                expected_text=_expected_text,
                must_be_enabled=True,
                timeout=_stable_timeout,
            )
            logger.debug(
                "wait_for_stable_state(%r) -> %s (prior action was %r)",
                _stable_selector, _became_stable, prev_action_type,
            )

    # dropdown/submenu pre-reveal: a click target that's nested under a
    # collapsed menu/submenu commonly isn't even IN the DOM yet, not just
    # hidden - every tier below would report "not found" identically to
    # genuinely-missing content, since there's nothing yet to fall back
    # to (_reveal_via_ancestor_hover further down needs an already-
    # resolved element to walk ancestors FROM, which doesn't help here).
    # Runs before any tier is attempted, purely so a real ancestor
    # hover-reveal gets a fair chance first; a no-op whenever the target
    # is already findable, so this costs nothing for the ordinary case.
    if action_type in ("click", "dblclick", "right_click"):
        _hover_recorded_ancestor_if_not_findable(page, lp)

    # same priority as before: test-automation attributes, id, other
    # stable/human-meaningful attributes, role+accessible-name, href,
    # visible text, value-as-text, then the positional/structural
    # fallbacks - just tried as attempt-then-fall-through instead of
    # find-then-commit
    tiers = [
        ("data-testid", lambda: _by_attr(page, "data-testid", attrs.get("data-testid"))),
        ("data-test", lambda: _by_attr(page, "data-test", attrs.get("data-test"))),
        ("data-cy", lambda: _by_attr(page, "data-cy", attrs.get("data-cy"))),
        ("id", lambda: _find_by_id(page, lp)),
        ("name", lambda: _by_attr(page, "name", attrs.get("name"))),
        ("aria-label", lambda: _by_attr(page, "aria-label", attrs.get("aria-label"))),
        ("placeholder", lambda: _by_attr(page, "placeholder", attrs.get("placeholder"))),
        ("title", lambda: _find_by_title(page, lp, attrs)),
        ("role", lambda: _find_by_role(page, lp, attrs)),
        ("href", lambda: _find_by_href(page, lp)),
        ("text+tag", lambda: _find_by_text_tag(page, lp)),
        ("text+tag", lambda: _find_by_value_text(page, lp, value, action_type)),
        # only reached once every exact-content signal above (href, text)
        # has found NOTHING at all - the recorded item's identity can no
        # longer be verified on the live page (content genuinely changed
        # since recording, on any site). Position among structurally-
        # similar siblings, derived from the recorded css_path itself, is
        # the sole fallback signal - never text/content similarity.
        # Placed before css_path/xpath since those apply the recorded
        # path fairly literally (fragile to any structural drift above
        # the repeating element) while this is deliberately looser.
        ("position_fallback", lambda: _find_by_position(page, lp, position_fallback_info)),
        ("css_path", lambda: _find_by_css(page, lp)),
        ("xpath", lambda: _find_by_xpath(page, lp)),
    ]

    element_found = False
    last_err = None
    position_fallback_info = {}

    # the tier loop itself is unchanged (same strategies, same priority
    # order, same per-tier overlay-recovery retry) - it's just wrapped in
    # a function now so it can be run a second time, after a settle wait,
    # before giving up and falling to the bounding_box last resort below.
    # See the settle-and-retry call site right after this definition.
    def _attempt_tiers():
        nonlocal element_found, last_err

        def _post_click_check():
            # only click-type actions have the text/href identity
            # _verify_post_click_identity compares - fill/select/submit/
            # press/check all skip it trivially (inconclusive, never a
            # failure), same as every other click-only identity check in
            # this function
            if action_type not in ("click", "dblclick", "right_click"):
                return True, None
            return _verify_post_click_identity(page, lp)

        for strategy, finder in tiers:
            try:
                el = finder()
            except Exception:
                el = None
            if el is None:
                continue
            element_found = True
            # position_fallback means the recorded item's identity couldn't
            # be verified at all (content genuinely changed since recording)
            # - a successful click here is still a real success, but it must
            # never look indistinguishable from an exact-content match in
            # the step's own result, or a silently-wrong-item click could
            # pass as if nothing were amiss
            success_note = None
            if strategy == "position_fallback":
                success_note = (
                    f"recorded target not found - used same position "
                    f"(#{position_fallback_info.get('position')}) instead, "
                    f"content may differ from recording"
                )

            # numeric-id reliability check: a purely numeric id (e.g.
            # id="7") is a strong signal of a REUSED, non-semantic,
            # framework-internal identifier rather than a real, stable
            # author-written id - confirmed real, not hypothetical: the
            # same small numeric id has been observed attached to a
            # completely unrelated element (a donate checkbox) elsewhere
            # in the same recording session. The id/css_path/xpath tiers
            # above all ultimately resolve via that same recorded id when
            # one is present (css_path and xpath both short-circuit to
            # an id-based selector the moment the target has one - see
            # cssPath()/xPath() in action_capture.js), so this applies
            # regardless of which of those three tiers actually matched.
            # Re-verifies the LIVE element's own visible text against
            # element_text (the element's own rendered content - NOT
            # accessible_name/text, which can legitimately differ; see
            # the intended-value fix in _find_modal_check_value) before
            # ever clicking/checking it. A mismatch means the id was
            # coincidentally reused for a different element after a
            # re-render - this tier fails and falls through to the next
            # one, the same "never silently act on a misresolved target"
            # pattern the hit-test gate further below already uses for a
            # related kind of misclick risk. Never site-specific: purely
            # a shape check on the recorded id's own characters plus a
            # generic live-text comparison.
            if (
                strategy in ("id", "css_path", "xpath")
                and action_type in ("click", "dblclick", "right_click", "check")
            ):
                _recorded_id_raw = (lp.get("id") or "").lstrip("#").strip()
                if _recorded_id_raw.isdigit():
                    _recorded_numeric_text = (lp.get("element_text") or lp.get("text") or "").strip()
                    if _recorded_numeric_text:
                        try:
                            _live_numeric_text = " ".join((el.inner_text(timeout=1000) or "").split()).strip()
                        except Exception:
                            _live_numeric_text = None
                        if _live_numeric_text is not None and _live_numeric_text.lower() != _recorded_numeric_text.lower():
                            print(
                                f"[numeric-id-check] FAILED FAST: resolved via "
                                f"reused/non-semantic numeric id={_recorded_id_raw!r} "
                                f"(strategy={strategy}) but its live text "
                                f"{_live_numeric_text!r} does not match the recorded "
                                f"{_recorded_numeric_text!r} - the id likely got "
                                f"reused for a different element after a re-render"
                            )
                            last_err = (
                                f"numeric id={_recorded_id_raw!r} resolved to a "
                                f"different element (live text {_live_numeric_text!r} "
                                f"!= recorded {_recorded_numeric_text!r})"
                            )
                            continue

            # pre-click state-fingerprint check: this step's target may be
            # a direct reactive consequence of the immediately preceding
            # RECORDED interaction (e.g. an "add to bag"-style button that
            # only flips from disabled to enabled, or whose label text
            # updates, once the page's own JS finishes reacting to a prior
            # click/check/select/fill) - even though that reaction had
            # already finished by the time a human naturally paused during
            # recording. A generic fingerprint (disabled state + trimmed
            # visible text - never any specific expected value) is read
            # now and, only when the preceding step was itself an
            # interaction, re-read once after a single brief settle wait
            # (reusing _settle - the same settle utility already used
            # elsewhere in this file, not a new polling loop). Whether or
            # not it actually changed, resolution proceeds either way -
            # Playwright's own actionability check still runs as normal
            # at click/check time below regardless, so this can never
            # mask or replace that check, only give a genuine reaction a
            # brief chance to land first.
            if action_type in ("click", "check") and prev_action_type in (
                "click", "check", "select", "fill",
            ):
                def _state_fingerprint():
                    try:
                        return el.evaluate(
                            "e => ({ "
                            "disabled: 'disabled' in e ? !!e.disabled : null, "
                            "text: (e.innerText || '').trim() || null "
                            "})"
                        )
                    except Exception:
                        return None

                fp_before = _state_fingerprint()
                if fp_before is not None:
                    _settle(page)
                    fp_after = _state_fingerprint()
                    if fp_after != fp_before:
                        logger.debug(
                            "state-fingerprint changed after preceding %s "
                            "(before=%s, after=%s) - target's reactive "
                            "update landed",
                            prev_action_type, fp_before, fp_after,
                        )
                    else:
                        logger.debug(
                            "state-fingerprint unchanged after preceding %s "
                            "(fp=%s) - proceeding anyway, Playwright's own "
                            "actionability check still applies",
                            prev_action_type, fp_before,
                        )

            # hover-reveal + stability + identity sanity-check: a target
            # that a tier just resolved to (by id/css_path/href/whatever
            # signal that tier searches on) can still be genuinely hidden
            # right now - the common real-world cause being a dropdown/
            # submenu/mega-menu whose trigger hasn't been hovered yet, so
            # the item a person would see and click simply isn't
            # rendered/interactable at this instant. Clicking through
            # anyway (Playwright's actionability wait, or this file's own
            # force=True fallback) can still "succeed" while landing on
            # the wrong thing entirely if a page's own JS handles a click
            # on a not-really-open menu item differently than a genuine
            # one - exactly the kind of silent misclick this exists to
            # catch. Every check here is purely structural/generic (live
            # DOM ancestor walk, geometry, loose text/href comparison) -
            # never any recorded or hardcoded site-specific string - and
            # none of it blocks the click below: it only gives a hidden
            # target a real chance to become genuinely visible and
            # settled first, and warns immediately if what got resolved
            # doesn't look like the recording's own description of it.
            if action_type in ("click", "dblclick", "right_click"):
                # captured BEFORE _reveal_via_ancestor_hover runs (it's a
                # no-op when el is already interactable) - if a genuine
                # ancestor hover was actually needed to reveal el (the
                # dropdown/mega-menu-item case), the plain click below
                # switches to the trusted, low-level mouse sequence
                # instead of el.click()/smart_click(): a real mouseenter
                # already had to be simulated to get here, and a React
                # (or similar) component that needed that same real-
                # event treatment to reveal itself is exactly the kind
                # of component whose click handler may need it too,
                # rather than a synthetic dispatch through Playwright's
                # own internal click().
                _click_needed_hover_reveal = (
                    action_type == "click" and not _is_genuinely_interactable(el)
                )
                _reveal_via_ancestor_hover(page, el)
                # dynamic option list (search/typeahead suggestions, a
                # dropdown's options) still repopulating right as this
                # step reaches it - waits for the sibling set to stop
                # changing before treating el as ready to click, purely
                # structural (sibling count/text), a no-op for any
                # target that isn't part of a list at all
                _wait_for_option_list_stable(page, el)
                _wait_for_bounding_box_stable(page, el)
                _warn_if_resolved_identity_mismatched(el, lp, action_type)
                # click-diagnostic logging (AUTOFLOW_DEBUG only): always
                # logs recorded vs live identity for every click, whether
                # or not anything looks wrong - purely so two similar
                # steps (a working one and a failing one, say) can be
                # compared side by side in the same run's own debug
                # output to see whether THIS specific click is even
                # landing on the element the recording describes. Never
                # blocks anything or changes behavior on its own -
                # _warn_if_resolved_identity_mismatched/hit-test above
                # already own that job; this only makes the comparison
                # visible.
                try:
                    _live_identity = el.evaluate(
                        "e => ({ "
                        "testid: e.getAttribute('data-testid'), "
                        "text: (e.innerText || e.textContent || '').trim().slice(0, 80), "
                        "tag: e.tagName.toLowerCase() "
                        "})"
                    )
                except Exception:
                    _live_identity = None
                logger.debug(
                    "click-diagnostic: about to click (strategy=%s) - recorded "
                    "data-testid=%r text=%r tag=%r | resolved live element: %s",
                    strategy, attrs.get("data-testid"),
                    lp.get("text") or lp.get("element_text"), lp.get("tag"),
                    _live_identity,
                )
                # ==========================================================
                # TEMPORARY, UNCONDITIONAL diagnostic - NOT gated behind
                # AUTOFLOW_DEBUG or any other flag, deliberately, for a
                # specific live investigation: does a click's resolved
                # element actually match whatever document.elementFromPoint
                # reports is REALLY sitting at the coordinate Playwright is
                # about to click? Prints for EVERY click, match or not, so
                # two steps (a working one, a failing one) can be compared
                # side by side in the same run's raw terminal output with
                # no extra flags needed. Purely observational - never
                # changes what gets clicked or how; the existing hit-test
                # gate right below still owns the actual pass/fail
                # decision. Safe to delete this whole block once this
                # investigation is done.
                # ==========================================================
                if action_type in ("click", "dblclick", "right_click"):
                    try:
                        _diag_box = el.bounding_box()
                    except Exception:
                        _diag_box = None
                    if _diag_box and _diag_box.get("width") and _diag_box.get("height"):
                        _diag_x = _diag_box["x"] + _diag_box["width"] / 2
                        _diag_y = _diag_box["y"] + _diag_box["height"] / 2
                        try:
                            _diag_resolved = el.evaluate(
                                "e => ({ "
                                "tag: e.tagName.toLowerCase(), "
                                "cls: e.className ? String(e.className) : '', "
                                "testid: e.getAttribute('data-testid') "
                                "})"
                            )
                        except Exception:
                            _diag_resolved = None
                        try:
                            _diag_at_point = page.evaluate(
                                "([px, py]) => { "
                                "const h = document.elementFromPoint(px, py); "
                                "if (!h) return null; "
                                "return { "
                                "tag: h.tagName.toLowerCase(), "
                                "cls: h.className ? String(h.className) : '', "
                                "testid: h.getAttribute('data-testid') "
                                "}; "
                                "}",
                                [_diag_x, _diag_y],
                            )
                        except Exception:
                            _diag_at_point = None
                        _diag_match = (
                            _diag_resolved is not None and _diag_at_point is not None
                            and _diag_resolved.get("tag") == _diag_at_point.get("tag")
                            and _diag_resolved.get("cls") == _diag_at_point.get("cls")
                            and _diag_resolved.get("testid") == _diag_at_point.get("testid")
                        )
                        _diag_label = lp.get("text") or lp.get("element_text") or attrs.get("data-testid") or "(unlabeled)"
                        print(f"[CLICK-DIAG] === {action_type} on recorded target {_diag_label!r} (strategy={strategy}) ===")
                        print(
                            f"[CLICK-DIAG] resolved-to-click : tag={(_diag_resolved or {}).get('tag')!r} "
                            f"class={(_diag_resolved or {}).get('cls')!r} "
                            f"data-testid={(_diag_resolved or {}).get('testid')!r}"
                        )
                        print(
                            f"[CLICK-DIAG] at-click-coordinate: tag={(_diag_at_point or {}).get('tag')!r} "
                            f"class={(_diag_at_point or {}).get('cls')!r} "
                            f"data-testid={(_diag_at_point or {}).get('testid')!r}"
                        )
                        print(f"[CLICK-DIAG] MATCH={_diag_match}")
                # ==========================================================
                # end of temporary diagnostic block
                # ==========================================================

                # HARD gate, unlike the warning above: if a genuinely
                # DIFFERENT, unrelated element sits at the exact
                # coordinate Playwright is actually about to click (two
                # adjacent links/buttons sharing near-identical
                # geometry, say), fail THIS TIER now rather than
                # silently clicking whatever's really there - the same
                # "fall through to the next tier" behavior every other
                # per-tier failure in this loop already uses below, not
                # a new failure mode.
                hit_ok, hit_reason = _verify_click_target_hit_test(page, el, lp)
                if not hit_ok:
                    logger.debug("resolved via %s but hit-test failed: %s", strategy, hit_reason)
                    print(f"[misclick-check] FAILED FAST: {hit_reason} (strategy={strategy})")
                    last_err = hit_reason
                    continue

            # click-target resolution: prefer a smaller, more specific
            # interactive DESCENDANT of the matched container over the
            # container's own geometric center, when one exists (see
            # _find_more_specific_clickable_descendant) - the generic
            # "label + chevron" fix. _click_dispatch_el is what actually
            # gets scrolled-into-view and clicked below; el itself (and
            # every identity/hit-test check above and post-click below)
            # is completely unchanged, still the recorded container -
            # this only changes WHICH PIXEL within it gets clicked.
            _click_dispatch_el = el
            if action_type in ("click", "dblclick", "right_click"):
                _container_desc = _describe_element_for_log(el)
                _descendant_el = _find_more_specific_clickable_descendant(el)
                if _descendant_el is not None:
                    _descendant_desc = _describe_element_for_log(_descendant_el)
                    print(
                        f"[click-target-resolution] container matched: {_container_desc} "
                        f"- found a more specific interactive descendant: "
                        f"{_descendant_desc} - clicking the DESCENDANT instead "
                        f"of the container's own center"
                    )
                    _click_dispatch_el = _descendant_el
                else:
                    print(
                        f"[click-target-resolution] container matched: {_container_desc} "
                        f"- no more specific interactive descendant found - "
                        f"clicking the container as before"
                    )
            try:
                _click_dispatch_el.scroll_into_view_if_needed(timeout=5000)
                # secondary/parallel diagnostic (see
                # _log_elements_from_point_stack): the FULL element stack
                # at the exact point about to be clicked, not just the
                # single topmost element CLICK-DIAG below already checks
                # - reveals an invisible overlay silently absorbing the
                # click even when the descendant hypothesis above isn't
                # the real explanation for a given failure. Computed AFTER
                # scroll_into_view_if_needed (not before) so the logged
                # coordinate is the element's REAL final on-screen
                # position, not a pre-scroll one the click itself would
                # never actually land at. _efp_x/_efp_y are reused for the
                # AFTER-click reading further below, at the exact same
                # point.
                _efp_x = _efp_y = None
                if action_type in ("click", "dblclick", "right_click"):
                    try:
                        _dispatch_box = _click_dispatch_el.bounding_box()
                    except Exception:
                        _dispatch_box = None
                    if _dispatch_box and _dispatch_box.get("width") and _dispatch_box.get("height"):
                        _efp_x = _dispatch_box["x"] + _dispatch_box["width"] / 2
                        _efp_y = _dispatch_box["y"] + _dispatch_box["height"] / 2
                        _log_elements_from_point_stack(
                            _click_dispatch_el, _efp_x, _efp_y, label="BEFORE CLICK",
                        )
                # captured BEFORE the click fires - see the no-effect
                # retry right after smart_click() below for what this
                # is used for. Only for plain "click": dblclick/right_
                # click/fill/etc are all either far rarer misclick
                # candidates in practice or have their own success
                # criteria already (a fill's own typed-value check, a
                # check action's is_checked comparison) that make this
                # generic DOM-diff redundant for them.
                _dom_fp_before = _capture_dom_change_fingerprint(el) if action_type == "click" else None
                try:
                    _url_before_click = page.url if action_type == "click" else None
                except Exception:
                    _url_before_click = None
                # a click that opens a NEW tab/page (target="_blank", a
                # window.open() call) is a completely real, deliberate
                # effect - just one that's invisible to every signal
                # above, since the new content lands in a SEPARATE page
                # object, not this one's DOM or URL at all. Without this,
                # exactly that case would misread as "no effect" and
                # trigger the retry below, which would then click AGAIN
                # and open a SECOND tab - confirmed real, not
                # hypothetical: this exact bug produced two tabs from one
                # recorded product-card click before this check existed.
                try:
                    _page_count_before_click = len(page.context.pages) if action_type == "click" else None
                except Exception:
                    _page_count_before_click = None
                if action_type == "click":
                    # smart_click() handles the zero-size-bounding-box
                    # case (icon-wrapper divs, absolutely-positioned
                    # inner content, ::before/::after-rendered targets)
                    # itself - for every normal, measurable element this
                    # is identical to the plain el.click(timeout=5000)
                    # it replaces
                    _click_box = step.get("bounding_box") or {}
                    _click_fallback_coords = None
                    if _click_box.get("x") is not None and _click_box.get("y") is not None:
                        _click_fallback_coords = {
                            "x": _click_box["x"] + (_click_box.get("width") or 0) / 2,
                            "y": _click_box["y"] + (_click_box.get("height") or 0) / 2,
                        }
                    if _click_needed_hover_reveal and _trusted_mouse_click(page, _click_dispatch_el):
                        click_strategy_used = "standard"
                        print(
                            "[click-mechanism] TRUSTED MOUSE SEQUENCE used "
                            "(move -> pause -> down -> pause -> up) - target "
                            "required an ancestor hover-reveal to become "
                            "interactable"
                        )
                    else:
                        click_strategy_used = smart_click(page, _click_dispatch_el, fallback_coords=_click_fallback_coords)
                        print(
                            f"[click-mechanism] standard click used "
                            f"(strategy={strategy})"
                        )
                    # AFTER-click reading, same coordinate as the BEFORE
                    # one above (see _log_elements_from_point_stack) -
                    # immediately after the click fires, before anything
                    # else runs, so even a click that opens no dialog at
                    # all can be checked for ANY reaction whatsoever (a
                    # hover/active class, anything) at the exact point
                    # clicked. Purely diagnostic (the function itself
                    # never raises, even against a now-detached handle) -
                    # never affects ok/err/strategy below.
                    if _efp_x is not None and _efp_y is not None:
                        _log_elements_from_point_stack(
                            _click_dispatch_el, _efp_x, _efp_y, label="AFTER CLICK",
                        )
                    # generic self-correcting retry: a click that
                    # produces literally NO observable effect (no
                    # navigation, no new/changed content anywhere in
                    # body, no modal-shaped overlay, no attribute change
                    # on the clicked element or its immediate parent) is
                    # exactly what a recorded locator resolving to a
                    # plain wrapper/text node instead of the real
                    # clickable hit-area looks like - the recorded
                    # element technically "clicks" without error, but
                    # nothing was actually listening there. Rather than
                    # just reporting success on a click that visibly did
                    # nothing, this looks for a genuinely interactive
                    # element nearby (role="button"/onclick/cursor:
                    # pointer - see _find_alternate_clickable) and
                    # retries ONCE. Never site-specific, never gated on
                    # any recorded text - applies to any click, on any
                    # site, that produces zero detectable effect.
                    if _dom_fp_before is not None:
                        try:
                            page.wait_for_timeout(CLICK_NO_EFFECT_WAIT_MS)
                        except Exception:
                            pass
                        try:
                            _url_after_click = page.url
                        except Exception:
                            _url_after_click = None
                        try:
                            _page_count_after_click = len(page.context.pages)
                        except Exception:
                            _page_count_after_click = None
                        _opened_new_page = (
                            _page_count_before_click is not None
                            and _page_count_after_click is not None
                            and _page_count_after_click > _page_count_before_click
                        )
                        _dom_fp_after = _capture_dom_change_fingerprint(el)
                        _no_observable_effect = (
                            not _opened_new_page
                            and _url_after_click is not None
                            and _url_after_click == _url_before_click
                            and _dom_fp_after is not None
                            and _dom_fp_after == _dom_fp_before
                        )
                        if _no_observable_effect:
                            print(
                                f"[click-no-effect] WARNING: click on recorded target "
                                f"produced no detectable DOM change (strategy={strategy}) "
                                f"- looking for the real clickable hit-area nearby and "
                                f"retrying once"
                            )
                            _alt_el = _find_alternate_clickable(el)
                            # trusted mouse events (move -> pause -> down
                            # -> pause -> up) are the retry MECHANISM here
                            # - a real, OS-level input sequence rather
                            # than el.click()'s own internal dispatch -
                            # applied regardless of whether a different
                            # (alt_el) or the SAME (el) element ends up
                            # being retried, since "where to click" and
                            # "how to click" are independent fixes for
                            # independent failure causes. Falls back to
                            # an ordinary .click() only if the trusted
                            # sequence itself couldn't run at all (no
                            # measurable bounding box), never silently
                            # skips the retry.
                            _retry_el = _alt_el if _alt_el is not None else el
                            _retry_desc = (
                                "an alternate ancestor/descendant element"
                                if _alt_el is not None else "the same recorded element"
                            )
                            try:
                                if _trusted_mouse_click(page, _retry_el):
                                    print(
                                        f"[click-mechanism] TRUSTED MOUSE SEQUENCE used for "
                                        f"the retry on {_retry_desc} (standard click's first "
                                        f"attempt produced no observable effect)"
                                    )
                                else:
                                    _retry_el.click(timeout=3000)
                                    print(
                                        f"[click-mechanism] standard click used for the retry "
                                        f"on {_retry_desc} (target had no measurable bounding "
                                        f"box for a trusted mouse sequence)"
                                    )
                                logger.debug(
                                    "click-no-effect: retry fired on %s (strategy=%s)",
                                    _retry_desc, strategy,
                                )
                            except Exception as e_alt:
                                print(f"[click-no-effect] retry click failed: {e_alt}")
                                logger.debug(
                                    "click-no-effect: retry click failed (strategy=%s): %s",
                                    strategy, e_alt,
                                )
                    if click_strategy_used != "standard":
                        logger.debug(
                            "smart_click used fallback strategy=%s (zero-size "
                            "bounding box on this element)",
                            click_strategy_used,
                        )
                elif action_type == "dblclick":
                    _click_dispatch_el.dblclick(timeout=5000)
                elif action_type == "right_click":
                    _click_dispatch_el.click(timeout=5000, button="right")
                elif action_type == "fill" and value is not None:
                    _do_fill(page, el, value, turbo=turbo)
                elif action_type == "select" and value is not None:
                    el.select_option(value, timeout=5000)
                elif action_type == "submit":
                    el.evaluate("f => f.requestSubmit ? f.requestSubmit() : f.submit()")
                elif action_type == "press" and value:
                    el.press(value, timeout=5000)
                elif action_type == "check":
                    expected_state = step.get("expected_state")
                    if expected_state is None:
                        expected_state = True
                    elif isinstance(expected_state, str):
                        expected_state = expected_state.lower() in ("true", "1", "checked")
                    else:
                        expected_state = bool(expected_state)

                    is_checked = False
                    try:
                        if el.evaluate("e => e.tagName === 'INPUT'"):
                            is_checked = el.is_checked()
                        else:
                            child_in = el.locator("input").first
                            if child_in and child_in.count() > 0:
                                is_checked = child_in.is_checked()
                            else:
                                try:
                                    is_checked = el.is_checked()
                                except Exception:
                                    is_checked = False
                    except Exception:
                        is_checked = False

                    if not is_checked:
                        try:
                            is_checked = el.evaluate("""e => {
                                if (e.getAttribute('aria-checked') === 'true') return true;
                                if (e.getAttribute('aria-checked') === 'false') return false;
                                const cls = (e.className || '').toString().toLowerCase();
                                if (cls.includes('checked') || cls.includes('active') || cls.includes('selected')) return true;
                                if (e.querySelector('svg, i[class*="check"], [class*="check"], [class*="tick"]')) return true;
                                return false;
                            }""")
                        except Exception:
                            is_checked = False

                    # NATIVE vs NON-NATIVE split (confirmed real, not
                    # hypothetical - traced against an actual recorded
                    # session): a genuine native <input type="checkbox">
                    # has well-defined browser semantics for "checked" -
                    # el.is_checked()/.check()/.uncheck() are authoritative
                    # and genuinely idempotent there, so skipping the
                    # interaction when is_checked already equals
                    # expected_state is correct.
                    #
                    # A NON-native "checkbox" (any other tag with
                    # role="checkbox"/role="radio", or one of the class-
                    # name/icon heuristics above - a plain <div> or <svg>
                    # the recorder classified this way) has no such
                    # guarantee: the is_checked heuristics above are
                    # BEST-EFFORT signals, not ground truth, and for a
                    # single-select "pick a value from a list" control
                    # (a quantity/size/radio-style option row, say -
                    # genuinely NOT an independent on/off toggle despite
                    # being recorded as one) they can easily read as
                    # already matching expected_state even though the
                    # user's real, recorded click never actually fired
                    # anything - a real recorded session showed exactly
                    # this: a quantity option resolved via a bare-numeric
                    # id, recorded with expected_state=False, which this
                    # code's OLD unconditional "skip if already matching"
                    # gate would have (and did) turn into a complete
                    # no-op - no click at all, the exact "quantity click
                    # executes with no error but nothing changes" symptom.
                    # A "check" action only ever exists because a REAL
                    # user click was recorded, so a non-native target
                    # always gets that click on replay too - the is_checked
                    # comparison genuinely cannot be trusted to decide
                    # whether it's needed.
                    try:
                        is_native_input = bool(el.evaluate("e => e.tagName === 'INPUT'"))
                    except Exception:
                        is_native_input = False

                    should_interact = (is_checked != expected_state) if is_native_input else True
                    if not is_native_input:
                        print(
                            f"[check-vs-click] non-native checkbox-styled element "
                            f"(tag != INPUT) - always clicking regardless of the "
                            f"is_checked={is_checked!r}/expected_state={expected_state!r} "
                            f"comparison, since that comparison isn't reliable for a "
                            f"single-select/radio-style control recorded as 'check'"
                        )

                    if should_interact:
                        # force=True below deliberately bypasses Playwright's
                        # own actionability/visibility wait - necessary for
                        # the real, legitimate case of a native checkbox
                        # hidden via opacity/visibility for a custom-styled
                        # toggle, which is still genuinely present in its
                        # normal layout position. It is NOT safe for a
                        # target whose enclosing modal/dialog never actually
                        # opened (a recorded "navigate to #modal" that force-
                        # corrected the URL without the real UI ever
                        # mounting, say) - that element has zero layout size
                        # rather than merely being invisible, and force=True
                        # would dispatch the check/click at nothing while
                        # still reporting success. Guarding on that generic,
                        # structural signal here is what turns that into a
                        # real, visible failure instead.
                        if _is_zero_size_element(el):
                            raise RuntimeError(
                                "target has zero layout size (display:none or "
                                "inside a display:none ancestor) - its container "
                                "likely never actually opened/mounted"
                            )
                        if is_native_input:
                            try:
                                if expected_state:
                                    el.check(timeout=5000, force=True)
                                else:
                                    el.uncheck(timeout=5000, force=True)
                            except Exception:
                                el.click(timeout=5000, force=True)
                        else:
                            # non-native target - a plain, direct click is
                            # both the correct AND the only well-defined
                            # interaction here (there is no browser-level
                            # "uncheck" semantic for an arbitrary styled
                            # element); see the NOTE above for why this
                            # always runs rather than being gated on
                            # is_checked/expected_state
                            el.click(timeout=5000, force=True)
                # post-click identity check: the click just fired for
                # real - if what actually ended up focused doesn't match
                # what was recorded, this is a confirmed misclick, and
                # the step fails right here rather than waiting for a
                # downstream navigate/effect check to eventually notice
                post_ok, post_reason = _post_click_check()
                if not post_ok:
                    print(f"[misclick-check] FAILED (post-click): {post_reason}")
                    return strategy, element_found, False, post_reason
                # which tier actually won - only visible with AUTOFLOW_DEBUG=1
                # (same gate as the failure logging below), useful for
                # diagnosing a future "resolved to the wrong element" report
                # on any site the same way this one was diagnosed
                logger.debug("step resolved via strategy=%s", strategy)
                if success_note:
                    print(success_note)
                return strategy, element_found, True, success_note
            except Exception as e:
                # a resolved element whose scroll_into_view_if_needed()
                # timed out specifically because it's "not visible" is a
                # different, identifiable failure from "element not
                # found" or "covered by something else" - Playwright's
                # own timeout message says so directly. This is the
                # signature of an intentionally-hidden-but-functional
                # native input (a checkbox/radio used as a pure CSS
                # toggle - opacity:0 or equivalent) that's still
                # perfectly clickable. force=True is Playwright's own
                # documented mechanism for exactly this: it bypasses the
                # visibility/actionability check (including the implicit
                # scroll-into-view step that just failed) and interacts
                # with the element directly. Tried ONCE, immediately,
                # right here - not after burning through every remaining
                # tier's own full 5s retry cycle on the same doomed
                # visibility check. Scoped to click/check only, and only
                # for this specific message - a genuine "not found"
                # never reaches this except block at all (el already
                # exists by this point), and any OTHER failure reason
                # (covered by an overlay, not stable, outside viewport)
                # falls through to the existing handling below unchanged.
                # Same zero-size guard as the check-action force=True above:
                # a display:none (or display:none-ancestor) element has no
                # real layout box at all, unlike the opacity:0 toggle this
                # fallback exists for - forcing a click there would be a
                # false success, most commonly a click/check inside a modal
                # whose container never actually opened.
                if (
                    action_type in ("click", "check")
                    and "not visible" in str(e).lower()
                    and not _is_zero_size_element(el)
                ):
                    try:
                        if action_type == "click":
                            el.click(timeout=5000, force=True)
                        else:
                            expected_state = step.get("expected_state")
                            if expected_state is None:
                                expected_state = True
                            elif isinstance(expected_state, str):
                                expected_state = expected_state.lower() in ("true", "1", "checked")
                            else:
                                expected_state = bool(expected_state)
                            try:
                                if expected_state:
                                    el.check(timeout=5000, force=True)
                                else:
                                    el.uncheck(timeout=5000, force=True)
                            except Exception:
                                el.click(timeout=5000, force=True)
                        post_ok, post_reason = _post_click_check()
                        if not post_ok:
                            print(f"[misclick-check] FAILED (post-click): {post_reason}")
                            return strategy, element_found, False, post_reason
                        logger.debug(
                            "element found but not visible; retrying with force=True (strategy=%s)",
                            strategy,
                        )
                        if success_note:
                            print(success_note)
                        return strategy, element_found, True, success_note
                    except Exception as e_force:
                        logger.debug(
                            "force=True retry also failed for strategy=%s: %s",
                            strategy, e_force,
                        )
                        e = e_force
                elif (
                    action_type in ("click", "check")
                    and "not visible" in str(e).lower()
                ):
                    logger.debug(
                        "resolved via %s but element has zero layout size - "
                        "not attempting force=True, its container likely "
                        "never actually opened/mounted",
                        strategy,
                    )
                    print(
                        f"[modal-target-check] target has zero layout size "
                        f"(strategy={strategy}) - not forcing the interaction, "
                        f"its container likely never actually opened"
                    )

                # this tier found a real element but the interaction itself
                # failed (not visible/not stable/obscured, most commonly).
                # For click-type actions specifically, this is also exactly
                # what an unexpected overlay/modal/dialog blocking the real
                # target looks like - one generic, site-agnostic recovery
                # attempt (Escape / a generically-matched close button) plus
                # a single retry on this SAME element before giving up on
                # this tier, since the recovery may well have been all that
                # was needed.
                if action_type in ("click", "dblclick", "right_click"):
                    _try_dismiss_overlay(page)
                    try:
                        if action_type == "click":
                            smart_click(page, el, fallback_coords=_click_fallback_coords, standard_timeout=3000)
                        elif action_type == "dblclick":
                            el.dblclick(timeout=3000)
                        else:
                            el.click(timeout=3000, button="right")
                        post_ok, post_reason = _post_click_check()
                        if not post_ok:
                            print(f"[misclick-check] FAILED (post-click): {post_reason}")
                            return strategy, element_found, False, post_reason
                        logger.debug("step resolved via strategy=%s (after overlay recovery)", strategy)
                        if success_note:
                            print(success_note)
                        return strategy, element_found, True, success_note
                    except Exception as e2:
                        e = e2
                # a DIFFERENT tier might resolve to a different, actually-
                # interactable element (or the same one in a different
                # state by the time it's tried), so keep going rather than
                # give up here - Playwright's own exception text includes a
                # full multi-line retry trace that's only useful for
                # debugging, not for a "did my replay work" run
                logger.debug("resolved via %s but action failed: %s", strategy, e)
                last_err = str(e)
                continue
        return None

    first_attempt = _attempt_tiers()
    if first_attempt is not None:
        return first_attempt

    if not fast_fail:
        # one genuine readiness wait before falling all the way to the
        # scroll-and-recheck tier (and ultimately the bounding_box last
        # resort) - covers an autocomplete suggestion or portal-rendered
        # overlay that genuinely hasn't finished appearing yet at the moment
        # of the first attempt, AND a target whose own text/enabled/visible
        # state changes as a direct, reactive consequence of the
        # immediately preceding action (e.g. an "ADD TO BAG" button that
        # only becomes clickable once the page's own JS finishes updating
        # it after a size selection) - even though it had already rendered/
        # updated by the time a human naturally paused during recording.
        # Reuses _wait_for_next_step_ready exactly as-is - the same
        # mechanism already used for post-navigation readiness checks
        # elsewhere in this file - just pointed at THIS step's own target
        # (passing `step` itself) instead of the next recorded step, since
        # that's all the function actually needs: a dict with a
        # locator_profile to poll for. A single, one-time recheck of every
        # standard strategy (_attempt_tiers() runs the full tier list again)
        # - not a repeated loop - and it composes with the force=True
        # "resolved but not visible" fix for free: _attempt_tiers() is the
        # SAME shared function used everywhere in this resolution flow, so
        # that fix already applies here too, automatically.
        logger.debug(
            "element not found on first attempt, rechecking after brief settle"
        )
        _wait_for_next_step_ready(page, step)
        retry_attempt = _attempt_tiers()
        if retry_attempt is not None:
            logger.debug(
                "step resolved via settle-and-recheck (strategy=%s)",
                retry_attempt[0],
            )
            return retry_attempt

        # scroll-and-recheck: covers infinite-scroll/lazy-loaded content that
        # genuinely doesn't exist in the DOM yet, no matter how long the
        # settle wait above lasted - the site only renders it once the page
        # is actually scrolled near its position. One small, incremental
        # scroll at a time (reusing _replay_scroll exactly as the scroll
        # action itself already does - not one big jump), then a settle wait
        # before rechecking. This reuses _settle() rather than
        # _wait_for_next_step_ready() (already used once, above, for the
        # single one-time wait before this loop): _settle() is the SAME
        # settle utility used for post-navigation readiness throughout this
        # file, and its own docstring is this exact scenario - "domcontent
        # fires before JS-heavy sites finish rendering the elements a step
        # is about to look for". _wait_for_next_step_ready() polls for up to
        # 9s per call, which is appropriate for the single one-time wait
        # above, but multiplying that across several scroll iterations is
        # exactly the "stuck for dozens of seconds" symptom this fix exists
        # to eliminate, not reproduce. Every standard strategy is tried
        # again after each settle. Bounded entirely by the page's OWN real
        # state, never a fixed count: it stops the moment a scroll genuinely
        # produces no further movement AND no further document growth, i.e.
        # the page has actually reached the end of what it has to offer -
        # there's nothing further down that scrolling could ever reveal past
        # that point.
        try:
            prev_scroll_height = page.evaluate("document.body.scrollHeight")
            prev_scroll_y = page.evaluate("window.scrollY")
        except Exception:
            prev_scroll_height = None
            prev_scroll_y = None

        scroll_increment_count = 0
        while prev_scroll_height is not None:
            try:
                viewport_height = page.evaluate("window.innerHeight") or 600
            except Exception:
                viewport_height = 600
            # a fraction of the viewport per hop - a real user scrolling to
            # find something moves the page a bit at a time, not a full jump
            increment = max(1, int(viewport_height * 0.6))

            logger.debug(
                "scroll-and-recheck: attempt %d, scrolling %dpx to look for the target",
                scroll_increment_count + 1, increment,
            )
            try:
                _replay_scroll(page, 0, increment)
            except Exception:
                break
            scroll_increment_count += 1

            _settle(page)

            retry_after_scroll = _attempt_tiers()
            if retry_after_scroll is not None:
                logger.debug(
                    "step resolved via scroll-and-recheck after %d increment(s)",
                    scroll_increment_count,
                )
                return retry_after_scroll

            try:
                new_scroll_height = page.evaluate("document.body.scrollHeight")
                new_scroll_y = page.evaluate("window.scrollY")
            except Exception:
                new_scroll_height, new_scroll_y = None, None

            if new_scroll_height == prev_scroll_height and new_scroll_y == prev_scroll_y:
                logger.debug(
                    "scroll-and-recheck: stopping after %d increment(s) - "
                    "reached the end of the page's scrollable content",
                    scroll_increment_count,
                )
                break

            prev_scroll_height = new_scroll_height
            prev_scroll_y = new_scroll_y

    else:
        logger.debug(
            "fast-fail: skipping settle-and-recheck and "
            "scroll-and-recheck escalation tiers for this step - "
            "the previous navigate already signaled its destination "
            "target never became findable, so this reports failure "
            "quickly instead of repeating the full retry cycle"
        )

    if not element_found:
        last_err = "none of the locator strategies (data-testid/data-test/data-cy/id/name/aria-label/placeholder/title/role/href/text+tag/css_path/xpath) matched an element"

        # last resort for fill/select ONLY, and only once every named
        # locator has come up completely empty: some frameworks swap or
        # restructure an input's DOM the moment it receives focus
        # (floating-label / animated fields - the unfocused node the
        # recorder saw no longer exists once focused), so a fresh locator
        # query for the ORIGINAL attributes can genuinely match nothing
        # even though the right field is right there, already focused, by
        # the immediately-preceding click. Whatever the page currently has
        # focused is a reliable, framework-agnostic signal of intent for
        # exactly this click-then-type pattern - not a guess about page
        # content, since it only fires once every real locator has failed.
        if action_type in ("fill", "select") and value is not None:
            try:
                focused_tag = page.evaluate(
                    "document.activeElement && document.activeElement.tagName"
                )
            except Exception:
                focused_tag = None
            if focused_tag in ("INPUT", "TEXTAREA", "SELECT"):
                try:
                    el = page.locator(":focus")
                    el.scroll_into_view_if_needed(timeout=5000)
                    if action_type == "fill":
                        _do_fill(page, el, value, turbo=turbo)
                    else:
                        el.select_option(value, timeout=5000)
                    logger.debug("step resolved via strategy=focused_element_fallback")
                    return "focused_element_fallback", True, True, None
                except Exception as e:
                    last_err = str(e)

            # also last resort, fill/select only: page.locator() never
            # searches inside an iframe's own document - only
            # frame_locator() does, and only when explicitly pointed at
            # that iframe - so a target genuinely rendered inside an
            # iframe matches NOTHING above no matter how long the retry
            # window is, on any site that happens to render a form (or
            # part of one) that way. Tries the same stable signals
            # already used at the top level, in the same priority order,
            # inside every iframe on the page - no assumption about which
            # site/field this is.
            try:
                iframe_el = _find_in_iframes(page, lp)
            except Exception:
                iframe_el = None
            if iframe_el is not None:
                try:
                    iframe_el.scroll_into_view_if_needed(timeout=5000)
                    if action_type == "fill":
                        _do_fill(page, iframe_el, value, turbo=turbo)
                    else:
                        iframe_el.select_option(value, timeout=5000)
                    logger.debug("step resolved via strategy=iframe_fallback")
                    return "iframe_fallback", True, True, None
                except Exception as e:
                    last_err = str(e)

        # same last resort, click-type actions: a click target genuinely
        # rendered inside an iframe (third-party payment/checkout
        # overlays are a common real-world case) matches nothing in the
        # top-level document no matter how long anything waits, on any
        # site. Tried before falling all the way to a blind coordinate
        # click below, since a real element actually found inside an
        # iframe is always better evidence than a raw pixel position.
        if action_type in ("click", "dblclick", "right_click"):
            try:
                iframe_el = _find_in_iframes(page, lp)
            except Exception:
                iframe_el = None
            if iframe_el is not None:
                try:
                    iframe_el.scroll_into_view_if_needed(timeout=5000)
                    if action_type == "click":
                        # no fallback_coords here deliberately - the
                        # recorded bounding_box is relative to the TOP
                        # page's viewport, not this iframe's own internal
                        # coordinate space, so a coordinate click here
                        # would risk clicking the wrong spot on the outer
                        # page. force/js_click (Playwright's own
                        # locator-based dispatch) are still fully
                        # iframe-aware without that risk.
                        smart_click(page, iframe_el)
                    elif action_type == "dblclick":
                        iframe_el.dblclick(timeout=5000)
                    else:
                        iframe_el.click(timeout=5000, button="right")
                    logger.debug("step resolved via strategy=iframe_fallback")
                    return "iframe_fallback", True, True, None
                except Exception as e:
                    last_err = str(e)

    # generic role/accessible-name/text re-resolution: one more identity-
    # based attempt before EVER falling back to a raw, potentially-stale
    # coordinate click - deliberately OUTSIDE the "if not element_found"
    # block above, so this still runs even when some earlier tier DID
    # locate an element (setting element_found) that then failed the
    # actual interaction (a stale-position hit-test mismatch, most
    # commonly): a layout-shifting preceding action (a checkbox reveal,
    # an expand/collapse, any reflow) can move a target away from its
    # recorded (x, y) AND, separately, away from where its recorded
    # css_path/xpath structurally expected it (inserting/removing a
    # sibling anywhere in the ancestor chain shifts every :nth-of-type
    # index below it) - while the element's role and accessible name/
    # text never change at all. _find_by_role's own tier further up
    # only trusts an EXPLICITLY recorded role="..." attribute, which an
    # ordinary native <button>/<a> never needs to already BE a button/
    # link accessibility-wise - this uses Playwright's own accessibility-
    # tree-aware get_by_role()/get_by_text() instead, inferring the
    # standard implicit role from the recorded tag when none was
    # explicitly captured. See _resolve_via_role_or_text's own docstring
    # for the full reasoning; only trusted on an UNAMBIGUOUS single
    # match, exactly like every other identity tier in this function.
    if action_type in ("click", "dblclick", "right_click"):
        role_text_el = _resolve_via_role_or_text(page, lp, attrs)
        if role_text_el is not None:
            try:
                role_text_el.scroll_into_view_if_needed(timeout=5000)
                if action_type == "click":
                    smart_click(page, role_text_el)
                elif action_type == "dblclick":
                    role_text_el.dblclick(timeout=5000)
                else:
                    role_text_el.click(timeout=5000, button="right")
                post_ok, post_reason = _verify_post_click_identity(page, lp)
                if not post_ok:
                    print(f"[misclick-check] FAILED (post-click): {post_reason}")
                    return "role_text_refresh", True, False, post_reason
                logger.debug("step resolved via strategy=role_text_refresh")
                note = (
                    "recorded click position was stale (or every other "
                    "locator signal failed) - re-resolved the target live "
                    "via role/accessible-name/text instead of the "
                    "recorded coordinate"
                )
                print(f"[role-text-refresh] {note}")
                return "role_text_refresh", True, True, note
            except Exception as e:
                last_err = str(e)

    # bounding box is a last resort for click-type actions only - selects/
    # submits/keypresses need a real element to act on, a blind coordinate
    # click would just do the wrong thing. Only one dimension needs to be
    # non-zero, not both: some real, genuinely-clickable elements report
    # zero WIDTH (or height) in their own computed box (icon/badge header
    # links using overflow-visible children are a common real-world case)
    # - Playwright's own el.click() already refused these as "not visible"
    # above, but a raw pixel click doesn't require that same check and can
    # still land on real rendered content at that coordinate. A box where
    # BOTH dimensions are zero occupies no space at all and is skipped.
    box = step.get("bounding_box")
    if action_type in ("click", "dblclick", "right_click") and box and (box.get("width") or box.get("height")):
        try:
            x = box["x"] + box["width"] / 2
            y = box["y"] + box["height"] / 2
            # a blind coordinate click is only real evidence of an
            # interaction if something is actually rendered there right
            # now - on a stale/wrong/not-yet-loaded page this coordinate
            # can just be empty page background, and clicking it would
            # silently "succeed" while doing nothing real, masking
            # exactly the kind of navigation-timing problem this tier
            # exists to be a last resort for, not a cover for. Checking
            # what's really at (x, y) first means this fallback can never
            # manufacture false confidence that a page is ready when it
            # isn't - on any site, for any click-type action.
            real_target = page.evaluate(
                "([px, py]) => { "
                "const el = document.elementFromPoint(px, py); "
                "if (!el) return null; "
                "const link = el.closest('a'); "
                "return { "
                "isPageBackground: el === document.body || el === document.documentElement, "
                "text: (el.innerText || '').trim().slice(0, 80), "
                "href: link ? link.getAttribute('href') : null, "
                "ariaLabel: el.getAttribute('aria-label') "
                "}; "
                "}",
                [x, y],
            )
            if not real_target or real_target.get("isPageBackground"):
                return "bounding_box", element_found, False, (
                    "bounding box fallback found no real element at the recorded position"
                )
            # same hard identity gate the tier loop's own hit-test already
            # applies (_verify_click_target_hit_test / _identity_hit_matches)
            # - this raw coordinate click has no resolved Locator to run that
            # check against directly, but the recorded locator_profile's own
            # text/aria-label/href is exactly the same signal, compared
            # against whatever elementFromPoint() reports is really at this
            # position. Without this, a click that every tier above already
            # refused (because the recorded target is confirmed to be
            # somewhere else - an adjacent overlapping link, say) would still
            # reach here and dispatch a raw click at the wrong element,
            # silently reported as success whenever an earlier tier had at
            # least LOCATED the recorded element by selector (element_found).
            hit_ok, hit_reason = _identity_hit_matches(lp, real_target, "recorded click position")
            if not hit_ok:
                print(f"[misclick-check] FAILED FAST: {hit_reason} (strategy=bounding_box)")
                return "bounding_box", element_found, False, hit_reason
            if action_type == "dblclick":
                page.mouse.dblclick(x, y)
            elif action_type == "right_click":
                page.mouse.click(x, y, button="right")
            else:
                page.mouse.click(x, y)
            # element_found reflects whether any EARLIER tier ever
            # actually located the recorded, intended element - a blind
            # coordinate click that never verified it hit that element
            # (element_found is False here in the common case: nothing
            # above found anything at all) must never be reported as a
            # success just because the click itself didn't raise. When
            # an earlier tier DID find the real element but couldn't
            # interact with it through normal means, this mirrors that
            # genuine finding instead.
            return "bounding_box", element_found, element_found, None
        except Exception as e:
            return "bounding_box", element_found, False, f"coordinate click failed: {e}"

    return None, element_found, False, last_err


def _resolve_and_act_with_retry(
    page, step, retry_budget_s=4.5, retry_interval_s=0.35,
    prev_action_type=None, fast_fail=False,
):
    """fill/select actions are the ones exposed to a different failure mode
    than click-type actions: the target can genuinely not exist in the DOM
    yet at the single instant resolve_and_act tries it - an async page
    transition still loading (a form submit that triggers a backend call
    before the next screen renders), or a framework that rebuilds an
    input's DOM node on focus and hasn't settled yet. In both cases every
    locator tier - including the focused-element fallback, since nothing
    may be focused/existing yet either - correctly finds nothing, because
    there is genuinely nothing there YET, not because the wrong thing was
    searched for.

    This is a different problem from what Playwright's own per-element
    actionability retrying already covers (that only helps once a locator
    has found *a* matching element and is waiting for it to become
    interactable) - here nothing matches at all, so the fix is to retry
    the entire search-and-act attempt, fresh, for a bounded window, not to
    wait longer on a single found element.

    Click/dblclick/right_click/submit/press are unaffected - only
    fill/select get this treatment, and only because they're the ones
    actually exposed to this timing gap.
    """
    if step.get("action_type") not in ("fill", "select"):
        return resolve_and_act(page, step, prev_action_type=prev_action_type, fast_fail=fast_fail)

    # CRITICAL - DO NOT REMOVE OR SHORTEN THIS RETRY LOOP. This fixes a
    # bug that has already broken and been re-fixed multiple times:
    # fill/select actions failing on real sites because the field isn't
    # ready yet. Any future change to this file must not touch this.
    #
    # The print() below is ALWAYS ON (not gated by AUTOFLOW_DEBUG or any
    # other flag) and deliberately so: this exact retry loop has been
    # silently lost/shortened before without anyone noticing until real
    # runs failed again. A plain, unconditional line on every attempt
    # means a future regression (or a stale/frozen generated script that
    # never picked up this fix at all) is visible directly in the
    # terminal output of any run, not something that has to be
    # rediscovered by re-reading this file.
    lp = step.get("locator_profile") or {}
    target_desc = (
        lp.get("id") or lp.get("placeholder") or lp.get("aria_label")
        or lp.get("css_path") or lp.get("tag") or "(unnamed field)"
    )
    start = time.monotonic()
    deadline = start + retry_budget_s
    attempt = 1
    print(f"[fill-retry] attempt {attempt} for {target_desc!r} at t=0.0s")
    result = resolve_and_act(page, step, prev_action_type=prev_action_type, fast_fail=fast_fail)
    while not result[2] and time.monotonic() < deadline:
        page.wait_for_timeout(int(retry_interval_s * 1000))
        attempt += 1
        print(f"[fill-retry] attempt {attempt} for {target_desc!r} at t={time.monotonic() - start:.1f}s")
        result = resolve_and_act(page, step, prev_action_type=prev_action_type, fast_fail=fast_fail)

    if not result[2]:
        _diagnose_fill_select_failure(page, target_desc)

    return result


def _diagnose_fill_select_failure(page, target_desc):
    """One-time diagnostic for a fill/select that exhausted the full
    retry window above without ever finding its target (including the
    iframe fallback resolve_and_act itself already tried) - captures what
    genuinely exists on the page at that moment (a screenshot, plus every
    real <input> element's outerHTML) so a real DOM-structure mismatch
    (the target living somewhere page.locator() can't see at all, e.g.
    inside an iframe) is visible directly, instead of looking identical
    to "just needed more time" in the terminal output. ALWAYS ON, not
    gated behind AUTOFLOW_DEBUG or any other flag - a gated diagnostic is
    a diagnostic that silently doesn't run the moment someone forgets the
    flag, which is exactly what happened before this. Best-effort
    throughout - a diagnostic that itself fails must never mask or
    replace the real failure result it's attached to.
    """
    print(f"[fill-select-diagnostic] {target_desc!r} not found after full retry window - capturing DOM state")
    try:
        diag_dir = Path(__file__).resolve().parent / "fill_diagnostics"
        diag_dir.mkdir(parents=True, exist_ok=True)
        shot_path = diag_dir / f"{_slug(str(target_desc)) or 'field'}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
        page.screenshot(path=str(shot_path))
        print(f"[fill-select-diagnostic] screenshot: {shot_path}")
    except Exception as e:
        print(f"[fill-select-diagnostic] couldn't capture screenshot: {e}")
    try:
        inputs = page.evaluate(
            "Array.from(document.querySelectorAll('input')).map(el => ({outerHTML: el.outerHTML.slice(0,200)}))"
        )
        print(f"[fill-select-diagnostic] top-document <input> count: {len(inputs)}")
        for i, entry in enumerate(inputs):
            print(f"[fill-select-diagnostic]   input[{i}]: {entry.get('outerHTML')}")
        iframe_count = page.locator("iframe").count()
        print(f"[fill-select-diagnostic] <iframe> count on page: {iframe_count}")
    except Exception as e:
        print(f"[fill-select-diagnostic] couldn't read DOM state: {e}")


def _verify_fill_select_retry_intact():
    """Startup safety check for the CRITICAL retry loop inside
    _resolve_and_act_with_retry above - this exact bug (fill/select
    actions failing because a field isn't rendered/rebuilt yet on a real
    site) has already been silently reintroduced once before by some
    later edit trimming or removing that loop, and nobody noticed until
    real runs started failing again. Rather than rely on someone
    remembering to check, verify at the very start of every run that the
    retry loop's actual source still looks like a real bounded retry - a
    while loop tied to a multi-second deadline - and print a loud
    warning immediately if it doesn't, so a future regression is obvious
    from the first line of output instead of requiring someone to dig
    through failed steps to find it. Best-effort: if the check itself
    can't run for some reason, that's treated as suspicious too.
    """
    try:
        src = inspect.getsource(_resolve_and_act_with_retry)
        has_retry_while_loop = "while not result[2]" in src and "deadline" in src
        budget_match = re.search(r"retry_budget_s\s*=\s*([\d.]+)", src)
        budget_ok = bool(budget_match) and float(budget_match.group(1)) >= 2.0
        intact = has_retry_while_loop and budget_ok
    except Exception:
        intact = False
    if not intact:
        print("CORE FIX MISSING: fill/select retry logic not found - results from this run cannot be trusted.")


def _dismiss_dialog(dialog):
    logger.debug("dialog appeared (%s): %s - dismissing", dialog.type, dialog.message)
    dialog.dismiss()


def _get_valid_open_page(pages, preferred=None):
    """Returns any still-open Page from the runtime registry, or None if
    every page has closed. `preferred` (typically the loop's last-used
    page) is tried first - after a recorded tab_close, that variable can
    be pointing at an already-closed Page, and calling ANY Playwright
    method on a closed Page raises TargetClosedError, so nothing past the
    main action loop (final state capture, the close-delay pause) may
    touch a page without going through this first.
    """
    candidates = ([preferred] if preferred is not None else []) + list(pages.values())
    for pg in candidates:
        if pg is None:
            continue
        try:
            if not pg.is_closed():
                return pg
        except Exception:
            continue
    return None


def _resolve_target_page(pages, target_page_id, anchor_page, fallback_url=None, wait_seconds=5):
    """Returns (page_or_None, reason) for the page a step with this
    page_id should execute against. reason is None on success, or a
    concrete explanation of why resolution failed - callers must surface
    it rather than let a page-mismatch fail silently with no clue why.

    The common case (page already known - almost always page_id 0)
    returns immediately with no waiting at all. A page_id that hasn't
    appeared yet is given a short window to show up via the context's
    "page" event (it's usually mid-flight from the click that immediately
    preceded this step) before falling back to opening it directly at the
    recorded URL, so a popup that doesn't fire identically on this run
    still doesn't stall or silently misdirect the action to the wrong page.
    """
    if target_page_id in pages:
        existing = pages[target_page_id]
        try:
            closed = existing.is_closed()
        except Exception:
            closed = True
        if not closed:
            return existing, None
        return None, (
            f"page_id={target_page_id} was already closed (a recorded tab_close closed "
            f"it earlier in this replay) and cannot be used for this action"
        )

    # anchor_page (typically the loop's last-used page) may itself already
    # be closed here - e.g. the immediately preceding step was a
    # tab_close on exactly this page, and this step needs a page_id that
    # hasn't appeared yet. Any Playwright call on a closed Page raises
    # TargetClosedError, so the poll below (and the fallback context
    # access further down) must use a genuinely open page, not
    # necessarily anchor_page itself.
    safe_anchor = _get_valid_open_page(pages, preferred=anchor_page)
    if safe_anchor is None:
        return None, (
            f"page_id={target_page_id} has not appeared and no open page remains "
            f"to wait on or open a fallback page from (every registered page is closed)"
        )

    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if target_page_id in pages:
            return pages[target_page_id], None
        safe_anchor.wait_for_timeout(100)

    if not fallback_url:
        return None, (
            f"waited {wait_seconds}s for page_id={target_page_id} to appear as a new "
            f"tab/page (context 'page' event) but it never did, and this step has no "
            f"recorded URL to fall back to opening it directly"
        )

    try:
        new_page = safe_anchor.context.new_page()
        new_page.set_default_timeout(8000)
        new_page.on("dialog", _dismiss_dialog)
        new_page.goto(fallback_url, wait_until="domcontentloaded", timeout=30000)
        pages[target_page_id] = new_page
        return new_page, None
    except Exception as e:
        return None, (
            f"waited {wait_seconds}s for page_id={target_page_id} to appear as a new "
            f"tab/page but it never did; fallback attempt to open {fallback_url!r} "
            f"directly also failed: {e}"
        )


def _settle(page):
    """domcontentloaded fires before JS-heavy sites (Amazon's search box,
    for one) finish rendering the elements a step is about to look for -
    without this, the very next action can find nothing there yet and skip.
    Best-effort only: sites that never go network-idle just get the full
    timeout and move on rather than hanging the replay.
    """
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass


def _replay_scroll(page, dx, dy, scroll_y_after=None, element=None):
    """Replay a recorded scroll gradually instead of one instant jump - a
    single page.mouse.wheel(dx, dy) call for a large accumulated delta
    would teleport the page instead of scrolling it the way the original
    action looked. Breaking it into smaller hops with brief pauses gets
    much closer to the real thing without needing to match its timing
    exactly.

    scroll_y_after is the absolute vertical position the page actually
    ended up at when this action was recorded. The incremental hops above
    still provide the visual motion, but afterwards the vertical position
    is snapped to that exact recorded value - the live page's document
    height can differ slightly from record time (ads, lazy-loaded
    content, a different viewport), so replaying the recorded delta alone
    can drift short of or past where the user actually ended up. There's
    no recorded absolute value for horizontal movement, so delta_x is
    always replayed as-is. Older recordings made before scroll_y_after
    existed simply omit it, leaving this as pure delta replay like before.

    element, when provided, is the resolved locator for the SPECIFIC
    scrollable container this action was recorded on (a nested panel, not
    the window) - scrolling happens on that element directly via
    scrollLeft/scrollTop rather than page.mouse.wheel(), since replay
    can't rely on the mouse already being positioned over that container
    the way it naturally was when the action was recorded. When element
    is None (plain window scrolling, or an older recording with no
    container locator), behavior is exactly as before this parameter
    existed: page.mouse.wheel() + window.scrollTo().
    """
    total = max(abs(dx), abs(dy))
    steps = max(1, min(20, int(total / 120)))
    step_dx = dx / steps
    step_dy = dy / steps

    if element is not None:
        for _ in range(steps):
            try:
                element.evaluate(
                    "(el, d) => { el.scrollLeft += d[0]; el.scrollTop += d[1]; }",
                    [step_dx, step_dy],
                )
            except Exception:
                pass
            page.wait_for_timeout(40)
        if scroll_y_after is not None:
            try:
                element.evaluate("(el, y) => { el.scrollTop = y; }", scroll_y_after)
                # confirmed real race, not hypothetical: the incremental
                # scrollLeft/scrollTop nudges above can still be settling
                # (the browser's own scroll-input handling doesn't
                # necessarily apply each nudge synchronously) right as
                # this snap fires, letting a moment of residual motion
                # partially overwrite it a frame later. A brief wait plus
                # a second, corrective snap closes that race without
                # turning this into an open-ended wait.
                page.wait_for_timeout(120)
                element.evaluate("(el, y) => { el.scrollTop = y; }", scroll_y_after)
            except Exception:
                pass
        return

    for _ in range(steps):
        page.mouse.wheel(step_dx, step_dy)
        page.wait_for_timeout(40)
    if scroll_y_after is not None:
        try:
            # the options-object form only changes what's actually
            # specified - omitting "left" leaves whatever horizontal
            # position the delta_x hops above already produced alone,
            # only snapping the vertical position to the recorded value.
            # behavior: 'instant' is load-bearing, not redundant: the
            # options-object form of scrollTo() (unlike the legacy
            # scrollTo(x, y) form) honors the page's own CSS
            # `scroll-behavior: smooth` when present - a common real-site
            # choice for anchor-link UX - which would otherwise turn this
            # "snap to the recorded position" call into a multi-frame
            # ANIMATION that's very likely still mid-flight the instant
            # this function returns, landing short of the recorded target
            # exactly like the wheel-momentum race below, but for an
            # entirely different reason (CSS, not input-event timing).
            # Forcing instant here means this call always lands exactly
            # on scroll_y_after synchronously, on any site, regardless of
            # what that site's own CSS specifies.
            page.evaluate("y => window.scrollTo({top: y, behavior: 'instant'})", scroll_y_after)
            # confirmed real race, not hypothetical: Chromium's own
            # wheel-driven scroll input can still be mid-animation
            # (momentum/inertia resolving over several frames) right as
            # this snap fires - a subsequent animation frame from that
            # SAME wheel gesture can then partially override the snap a
            # moment later, landing short of the recorded target even
            # though the snap call itself raised no error. A brief wait
            # (long enough for that residual motion to finish) plus a
            # second, corrective snap closes that race - bounded, not an
            # open-ended wait, and a no-op in the common case where
            # nothing was actually still moving.
            page.wait_for_timeout(120)
            page.evaluate("y => window.scrollTo({top: y, behavior: 'instant'})", scroll_y_after)
        except Exception:
            pass


def _read_scroll_position(page, element=None):
    """Current vertical scroll position - el.scrollTop for a recorded
    container, window.scrollY for the page itself. None on failure.
    """
    try:
        if element is not None:
            return element.evaluate("el => el.scrollTop")
        return page.evaluate("() => window.scrollY")
    except Exception:
        return None


def _reset_scroll_position(page):
    """Explicitly snaps window scroll back to (0, 0) right after a fresh,
    real page load (page.goto()) - never after a client-side SPA route
    change, which manages its own scroll position and shouldn't be
    second-guessed here. Exists because a genuinely fresh navigation can
    still land already scrolled: Chromium's own scroll-anchoring/history
    restoration can carry over a PRIOR visit's scroll position for the
    same URL within one browser context (revisiting a "home" URL later
    in a flow is a common real case), which would otherwise look
    indistinguishable from an actual, but entirely unrecorded, scroll
    action happening during replay - the recording's own JSON has none,
    yet the page still isn't at the top when the next step runs. Forcing
    a clean instant snap here means replay always starts a fresh page
    exactly where a real fresh page load would - at the very top -
    regardless of whatever the browser might otherwise have restored.
    Best-effort only; failures are swallowed since this is a safety net,
    not the action itself.
    """
    try:
        page.evaluate("() => window.scrollTo({top: 0, left: 0, behavior: 'instant'})")
    except Exception:
        pass


def _verify_scroll_reached(
    page, target_y, element=None,
    tolerance_px=SCROLL_TARGET_TOLERANCE_PX,
    timeout_s=SCROLL_VERIFY_TIMEOUT_S,
    interval_s=SCROLL_VERIFY_POLL_INTERVAL_S,
):
    """Polls the current scroll position (see _read_scroll_position)
    until it's within tolerance_px of target_y, or timeout_s elapses.
    Returns (reached: bool, last_position). Never raises - a position
    that can't be read at all counts as not reached, not an error.
    """
    deadline = time.monotonic() + timeout_s
    last_pos = _read_scroll_position(page, element)
    while True:
        if last_pos is not None and abs(last_pos - target_y) <= tolerance_px:
            return True, last_pos
        if time.monotonic() >= deadline:
            return False, last_pos
        page.wait_for_timeout(int(interval_s * 1000))
        last_pos = _read_scroll_position(page, element)


def _read_scroll_extent(page, element=None):
    """Current (scrollHeight, viewportHeight) for the recorded scroll
    container, or the page itself when element is None - the two
    numbers that determine how far scrolling can ACTUALLY reach right
    now (max reachable position = scrollHeight - viewportHeight). None
    on failure.
    """
    try:
        if element is not None:
            return element.evaluate("el => [el.scrollHeight, el.clientHeight]")
        return page.evaluate(
            "() => { "
            "const se = document.scrollingElement || document.documentElement; "
            "return [se.scrollHeight, window.innerHeight]; "
            "}"
        )
    except Exception:
        return None


def _ensure_scroll_content_ready(
    page, target_y, element=None,
    max_probe_rounds=SCROLL_LAZY_LOAD_MAX_PROBES,
    probe_wait_ms=SCROLL_LAZY_LOAD_PROBE_WAIT_MS,
):
    """Before ever attempting the recorded absolute scroll_y_after jump,
    checks whether the CURRENT page/container is even tall enough to
    reach it yet. Many real pages (infinite-scroll listings, lazy-
    loaded sections/cards) only render further content once scrolling
    actually gets close to the bottom of what's currently mounted, so a
    scrollHeight recorded at the moment the ORIGINAL scroll finished can
    legitimately be much taller than what's rendered the instant replay
    reaches this step - jumping straight to the recorded target then
    just clamps short, no matter how many times the same jump is
    retried (which is exactly what a plain retry loop alone, with no
    concept of the page's own content still growing, would keep doing).

    Instead, this scrolls to whatever the CURRENT maximum reachable
    position is - the generic, site-agnostic way to trigger a scroll-
    position-based lazy-load/infinite-scroll mechanism, on any site,
    without any special knowledge of how that site implements it - and
    waits briefly after each nudge for new content to mount, repeating
    until either the target becomes reachable or scrollHeight stops
    growing across two consecutive checks (the page has genuinely
    finished loading everything it's going to, and further probing
    would just be spinning). Bounded by max_probe_rounds, never open-
    ended. The caller still does its own real scroll + verification
    afterward exactly as before - this only gives that a fair, content-
    aware chance to succeed first, instead of repeating a doomed jump.

    Returns (reachable, scroll_height, stabilized) - reachable is
    whether the target position is now within scrollHeight -
    viewportHeight; stabilized is True once scrollHeight was observed to
    stop growing, letting the caller distinguish "still loading, worth
    another real attempt" from "genuinely done growing, this is as tall
    as the page will ever get" for its own failure message. Never
    raises - inconclusive (extent unreadable) reports reachable=True so
    it never blocks the normal attempt that follows.
    """
    extent = _read_scroll_extent(page, element)
    if extent is None:
        return True, None, False
    scroll_height, viewport_height = extent
    max_reachable = max(0, scroll_height - viewport_height)
    if max_reachable >= target_y:
        return True, scroll_height, False

    prev_height = scroll_height
    stabilized = False
    for _ in range(max_probe_rounds):
        try:
            if element is not None:
                element.evaluate("(el, y) => { el.scrollTop = y; }", max_reachable)
            else:
                page.evaluate("y => window.scrollTo({top: y, behavior: 'instant'})", max_reachable)
        except Exception:
            break
        try:
            page.wait_for_timeout(probe_wait_ms)
        except Exception:
            pass
        extent = _read_scroll_extent(page, element)
        if extent is None:
            break
        scroll_height, viewport_height = extent
        max_reachable = max(0, scroll_height - viewport_height)
        if max_reachable >= target_y:
            return True, scroll_height, False
        if scroll_height <= prev_height:
            # scrollHeight didn't grow from this probe - the page has
            # stopped loading further content on its own, no point
            # probing further
            stabilized = True
            break
        prev_height = scroll_height

    return max_reachable >= target_y, scroll_height, stabilized


# --- Product search validation (optional Phase 6 addition) --------------
# Runs against the SAME page the recorded workflow already produced -
# never re-opens the site or re-runs a search of its own. Whatever page
# the recorded/replayed actions ended up on is what gets scanned. Generic
# on purpose: just scans <a> elements for plausible product-title-length
# text, no site-specific selectors, so it works the same on Amazon,
# Flipkart, or anywhere else.
PRODUCT_MIN_TITLE_LEN = 15
PRODUCT_MAX_TITLE_LEN = 300
PRODUCT_MAX_SCROLLS = 15
PRODUCT_SCROLL_STEP_PX = 1800


# how many result "blocks" a real results/listing page could plausibly
# have on one first page - well above what a normal grid/list shows, but
# far below what a mis-detection at the wrong (too-fine) DOM level would
# produce (which tends to land in the hundreds). Used purely as a sanity
# check on the detection itself, not a real limit on anything - see
# _detect_result_blocks.
VALIDATE_BLOCK_COUNT_CAP = 50

# Generic, site-agnostic "repeating listing block" detector, run via
# page.evaluate(). Starting point is the same idea _find_by_position()
# already relies on - siblings of the same tag under a common container
# are a repeating structure - generalized here to DISCOVER such groups
# fresh (no recorded css_path to anchor on, since validate never
# recorded a locator for this). Deliberately coarse: a candidate item is
# only accepted once it holds substantial, varied content (an image, or
# more than one distinct piece of text) - a single bare span/div with
# just one short text node is NOT a block on its own; such a candidate
# walks up to its nearest ancestor that actually groups several such
# pieces together instead. This is exactly the distinction the earlier,
# reverted per-<a>-element approach was missing (it treated every single
# link as its own "block", regardless of how little it held).
_VALIDATE_BLOCK_DETECTION_JS = """
() => {
    const MIN_GROUP_SIZE = 3;
    const MIN_BLOCK_TEXT_LEN = 20;
    const MAX_WALK_UP = 4;
    const HARD_CAP = 300;
    // how far an item's text length may drift from its siblings' median
    // and still count as part of the SAME repeating group. Real listing
    // items generated from one template land close together; a page's
    // structural sections (header/results/footer) sharing a tag by
    // coincidence do not, so this is what tells the two apart generically
    const SIZE_RATIO = 4;

    function ownText(el) {
        // innerText (not textContent) deliberately - it's rendering-aware,
        // so it naturally skips <script>/<style> content and anything
        // hidden via CSS, without ever naming those tags directly. A
        // detached/never-laid-out element falls back to textContent so it
        // isn't silently treated as empty.
        const t = (typeof el.innerText === 'string') ? el.innerText : (el.textContent || '');
        return t.trim().replace(/\s+/g, ' ');
    }

    // excludes non-rendering elements (script/style/template/etc.) and
    // anything hidden via CSS or zero-size layout, generically - no tag
    // name is ever named directly, so this works the same regardless of
    // what markup a given site happens to use
    function isVisible(el) {
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    }

    function isSubstantial(el) {
        if (el.querySelector('img')) return true;
        const pieces = new Set();
        const kids = el.querySelectorAll('*');
        for (let i = 0; i < kids.length; i++) {
            const child = kids[i];
            if (child.children.length > 0) continue;
            const t = ownText(child);
            if (t.length >= 3) pieces.add(t);
            if (pieces.size >= 2) return true;
        }
        return false;
    }

    function median(nums) {
        const s = [...nums].sort((a, b) => a - b);
        const mid = Math.floor(s.length / 2);
        return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
    }

    // find containers with enough same-tag direct children to look like
    // a repeating list/grid, AND whose items are actually similar in
    // size to each other - a same-tag-sibling count alone also matches
    // a page's structural skeleton (e.g. 3 unrelated <div> sections for
    // header/results/footer), which isn't a real repeating list
    const groups = [];
    const allEls = document.body.querySelectorAll('*');
    for (let i = 0; i < allEls.length; i++) {
        const container = allEls[i];
        const children = Array.from(container.children).filter(isVisible);
        if (children.length < MIN_GROUP_SIZE) continue;
        const counts = {};
        for (const c of children) {
            counts[c.tagName] = (counts[c.tagName] || 0) + 1;
        }
        let bestTag = null, bestCount = 0;
        for (const tag in counts) {
            if (counts[tag] > bestCount) { bestTag = tag; bestCount = counts[tag]; }
        }
        if (!bestTag || bestCount < MIN_GROUP_SIZE) continue;

        const sameTagChildren = children.filter(c => c.tagName === bestTag);
        const lens = sameTagChildren.map(c => ownText(c).length || 1);
        const med = median(lens);
        if (med < 5) continue;
        const similar = sameTagChildren.filter((c, idx) => lens[idx] >= med / SIZE_RATIO && lens[idx] <= med * SIZE_RATIO);
        if (similar.length < MIN_GROUP_SIZE) continue;

        groups.push({ container, tag: bestTag, items: similar });
    }

    // resolve each repeating child into a real "block" - substantial
    // content, walking up when the raw item is too thin
    const blocks = [];
    const seen = new Set();
    outer:
    for (const { items } of groups) {
        for (let item of items) {
            let candidate = item;
            let depth = 0;
            while (
                candidate &&
                depth < MAX_WALK_UP &&
                !isSubstantial(candidate) &&
                ownText(candidate).length < MIN_BLOCK_TEXT_LEN
            ) {
                candidate = candidate.parentElement;
                depth++;
            }
            if (!candidate || candidate === document.body) continue;
            const text = ownText(candidate);
            if (text.length < MIN_BLOCK_TEXT_LEN) continue;
            if (seen.has(candidate)) continue;
            seen.add(candidate);
            blocks.push(candidate);
            if (blocks.length >= HARD_CAP) break outer;
        }
    }

    // deduplicate nested matches - if one block fully contains another,
    // keep only the outer one, so the same listing entry is never
    // counted or reported twice
    const finalBlocks = blocks.filter(
        b => !blocks.some(other => other !== b && other.contains(b))
    );

    const results = [];
    finalBlocks.forEach((b, idx) => {
        b.setAttribute('data-afqa-block-idx', String(idx));
        results.push({ index: idx, text: ownText(b) });
    });
    return results;
}
"""


def _detect_result_blocks(page):
    """Runs the block-detection JS above and returns (blocks, usable).
    usable is False - meaning the caller should NOT trust this data and
    should fall back to a plain whole-page text search instead - when
    the detection throws, or when it finds an implausibly large number
    of "blocks" (VALIDATE_BLOCK_COUNT_CAP), the clearest sign the
    detection landed at too fine a DOM level (the exact failure mode of
    the earlier, reverted per-<a>-element approach) rather than at the
    coarse, real "listing item" level this is meant to find.
    """
    try:
        blocks = page.evaluate(_VALIDATE_BLOCK_DETECTION_JS)
    except Exception:
        return [], False
    if not isinstance(blocks, list) or len(blocks) > VALIDATE_BLOCK_COUNT_CAP:
        return [], False
    return blocks, True


# temporary marker attribute the click_if_exists JS below tags its
# chosen element with, so the Python side can grab a real Playwright
# locator for it afterward - cleared before every scan and again after a
# successful click, so it never lingers in the page's DOM
_CLICK_IF_EXISTS_MARKER = "data-autoflow-cie-target"

_CLICK_IF_EXISTS_CLEAR_JS = """
(marker) => {
    document.querySelectorAll('[' + marker + '="1"]').forEach(el => el.removeAttribute(marker));
}
"""

# generic, site-agnostic "does this exact text exist as a clickable
# element" scan for the click_if_exists action - deliberately EXACT
# equality after whitespace-normalizing/lowercasing, never a substring
# check, so a near-miss (e.g. "Regis Nov" against a target of
# "Register Now") never counts as a match.
_CLICK_IF_EXISTS_JS = """
(targetText) => {
    function normalize(s) {
        return (s || '').replace(/\s+/g, ' ').trim().toLowerCase();
    }

    const target = normalize(targetText);
    if (!target) {
        return { status: 'not_found', reason: 'no target text was given' };
    }

    function ownText(el) {
        return (typeof el.innerText === 'string') ? el.innerText : (el.textContent || '');
    }

    function isVisible(el) {
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    }

    const candidates = [];
    const elements = document.querySelectorAll("a, button, [role='button'], div, span");
    for (const el of elements) {
        if (!isVisible(el)) continue;
        if (normalize(ownText(el)) === target) {
            candidates.push(el);
        }
    }

    if (candidates.length === 0) {
        return {
            status: 'not_found',
            reason: 'no clickable element with text exactly matching "' + targetText + '" was found on the page',
        };
    }

    // among exact matches, prefer the smallest/most specific element -
    // fewest descendant elements - so a large wrapper that merely
    // CONTAINS the real target (whose own innerText also normalizes to
    // the same string, since text bubbles up through ancestors) never
    // wins over the actual target itself
    candidates.sort((a, b) => a.querySelectorAll('*').length - b.querySelectorAll('*').length);
    const el = candidates[0];

    function isDisabled(element) {
        if (element.disabled) return true;
        if (element.hasAttribute && element.hasAttribute('disabled')) return true;
        const ariaDisabled = element.getAttribute && element.getAttribute('aria-disabled');
        return ariaDisabled === 'true';
    }

    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || style.pointerEvents === 'none') {
        return {
            status: 'not_clickable',
            reason: 'element with text "' + targetText + '" is present but hidden (display/visibility/pointer-events) and cannot be clicked',
        };
    }

    if (isDisabled(el)) {
        return {
            status: 'not_clickable',
            reason: 'element with text "' + targetText + '" is present but disabled',
        };
    }

    const rect = el.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const hit = document.elementFromPoint(cx, cy);
    if (!hit || !(hit === el || el.contains(hit) || hit.contains(el))) {
        return {
            status: 'not_clickable',
            reason: 'element with text "' + targetText + '" is present but covered by another element and cannot be clicked',
        };
    }

    el.setAttribute('data-autoflow-cie-target', '1');
    return { status: 'found' };
}
"""


def _resolve_click_if_exists(page, target_text, timeout_s=8.0):
    """Looks for a clickable element on the CURRENT page whose text
    EXACTLY matches target_text (case-insensitive, whitespace-
    normalized - never a substring/fuzzy match - see
    _CLICK_IF_EXISTS_JS) and clicks it if found and genuinely clickable
    (visible, not disabled, not covered by another element).

    Never raises - every failure path returns {"ok": False, "reason":
    ...} instead of an exception, including a Playwright click failure
    (e.g. an actionability timeout), so a caller can always trust the
    return value rather than needing its own try/except around this.
    """
    try:
        page.evaluate(_CLICK_IF_EXISTS_CLEAR_JS, _CLICK_IF_EXISTS_MARKER)
    except Exception:
        pass

    try:
        result = page.evaluate(_CLICK_IF_EXISTS_JS, target_text)
    except Exception as e:
        return {"ok": False, "reason": f"could not scan the page for a matching element: {e}"}

    if not isinstance(result, dict) or result.get("status") != "found":
        reason = result.get("reason") if isinstance(result, dict) else None
        return {
            "ok": False,
            "reason": reason or f'no clickable element with text exactly matching "{target_text}" was found',
        }

    try:
        locator = page.locator(f"[{_CLICK_IF_EXISTS_MARKER}='1']").first
        locator.scroll_into_view_if_needed(timeout=timeout_s * 1000)
        smart_click(page, locator, standard_timeout=timeout_s * 1000)
    except Exception as e:
        return {"ok": False, "reason": f"found a matching element but the click failed: {e}"}

    try:
        page.evaluate(_CLICK_IF_EXISTS_CLEAR_JS, _CLICK_IF_EXISTS_MARKER)
    except Exception:
        pass

    return {"ok": True, "reason": None}


class _StopReplay(Exception):
    """Internal control-flow signal only - never a real crash. Raised
    from the click_if_exists dispatch branch in run()'s main loop when
    it fails to find/click its target, to halt the rest of the replay
    immediately. Caught by that same loop's per-step try/except
    specifically (ahead of the generic Exception handler, since a more
    specific except clause must come first) - the catch just breaks out
    of the loop; the existing not-executed backfill immediately after
    the loop already marks every remaining action, exactly as it does
    for any other early stop, so nothing else needs to change for that.
    """
    pass


def _scroll_reveal_full_page(page):
    """Scrolls down the CURRENT page, revealing whatever lazy-loaded
    content it has, until the page stops growing for two rounds in a row
    - bounded by PRODUCT_MAX_SCROLLS so this can never loop forever on an
    endless feed. Same bounded, generic approach _validate_product
    already uses for exactly this reason (a below-the-fold result isn't
    missed), reused here rather than invented fresh, so a validate check
    sees the full first page of results - not just the initial viewport
    - before deciding the expected text is genuinely absent. No
    assumption about pagination or what kind of content is on the page;
    this never navigates to a next page, only reveals more of the
    current one. Best-effort throughout: a failure partway through just
    means the reveal stops early, never a reason to fail the step this
    is attached to.
    """
    stable_rounds = 0
    last_height = None
    for _ in range(PRODUCT_MAX_SCROLLS):
        try:
            height_before = page.evaluate("document.body.scrollHeight")
        except Exception:
            height_before = last_height
        try:
            # NOT page.mouse.wheel() - that dispatches a real wheel event
            # at wherever the mouse cursor was last left by an EARLIER
            # step (a filter checkbox just clicked, a product card just
            # hovered) rather than moving it there deliberately. A wheel
            # event itself doesn't click anything, but resting it exactly
            # over a hover-sensitive element (a mega-menu trigger, an
            # image-zoom overlay) for this loop's full duration is an
            # avoidable risk for a routine whose only job is "move the
            # page", not "interact with whatever the mouse happens to be
            # over". window.scrollBy() via evaluate() moves the page
            # identically without touching the mouse at all.
            page.evaluate("(px) => window.scrollBy(0, px)", PRODUCT_SCROLL_STEP_PX)
        except Exception:
            break
        page.wait_for_timeout(700)
        try:
            page.wait_for_load_state("networkidle", timeout=3000)
        except Exception:
            pass
        try:
            height_after = page.evaluate("document.body.scrollHeight")
        except Exception:
            height_after = height_before
        if height_before is not None and height_after is not None and height_after <= height_before:
            stable_rounds += 1
            if stable_rounds >= 2:
                break
        else:
            stable_rounds = 0
        last_height = height_after


def _diagnose_validate_failure(page, expected_text):
    """One-time diagnostic for a validate step that didn't find its
    expected text after the full scroll-reveal + poll window - dumps a
    short excerpt of the page's actual visible text at that moment, so
    it's visible directly whether the text is genuinely absent or
    whether this ran before the page finished settling. A screenshot is
    already captured for every failed step by the shared per-step
    capture below (same as any other action type) - this adds the text
    dump specifically, the piece that capture doesn't provide. ALWAYS ON
    for a validate failure (not gated behind any flag), same reasoning as
    the existing fill/select failure diagnostic: a diagnostic that only
    sometimes runs is one that's silently missing exactly when it's
    needed. Best-effort only - a failure to read the page here must
    never mask the real validate failure it's attached to.
    """
    print(f"[validate-diagnostic] expected text {expected_text!r} not found - capturing page state")
    try:
        body_text = " ".join((page.inner_text("body") or "").split())
        print(f"[validate-diagnostic] visible page text (first 500 chars): {body_text[:500]!r}")
    except Exception as e:
        print(f"[validate-diagnostic] couldn't read page text: {e}")


def _normalize_product_text(text):
    return " ".join((text or "").split()).strip().lower()


def _scan_product_candidates(page, target_norm, seen, position, similar_matches):
    """One pass over the currently-rendered links. Mutates seen/similar_matches
    in place, returns (exact_match_or_None, updated_position). position only
    advances for genuinely new (not-yet-seen) candidates, so a result that's
    already on screen from a previous scroll pass never gets counted twice.
    """
    try:
        links = page.locator("a")
        count = links.count()
    except Exception:
        return None, position

    for i in range(count):
        el = links.nth(i)
        try:
            text = (el.inner_text(timeout=1000) or "").strip()
        except Exception:
            continue

        if len(text) < PRODUCT_MIN_TITLE_LEN or len(text) > PRODUCT_MAX_TITLE_LEN:
            continue
        norm = _normalize_product_text(text)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        position += 1

        if norm == target_norm:
            href = None
            try:
                href = el.get_attribute("href")
            except Exception:
                pass
            return {"position": position, "title": text, "url": href}, position

        if len(similar_matches) < 5 and (target_norm in norm or norm in target_norm):
            similar_matches.append({"position": position, "title": text})

    return None, position


def _validate_product(page, product_name, shot_dir, img_counter, last_state, last_shot_bytes):
    """Scans the CURRENT page - wherever replay left it - for an exact
    match of product_name, scrolling to reveal more results as needed.
    Stops once the page stops growing for two rounds in a row (reached the
    end of the results) so it can't loop forever on an endless feed.
    """
    target_norm = _normalize_product_text(product_name)
    seen = set()
    similar_matches = []
    position = 0

    match, position = _scan_product_candidates(page, target_norm, seen, position, similar_matches)

    if not match:
        stable_rounds = 0
        last_height = None
        for _ in range(PRODUCT_MAX_SCROLLS):
            try:
                height_before = page.evaluate("document.body.scrollHeight")
            except Exception:
                height_before = last_height
            try:
                # see _scroll_reveal_full_page's own comment on why
                # window.scrollBy() replaces page.mouse.wheel() here too -
                # same reasoning, same identical scroll mechanics, just
                # not tied to wherever the mouse cursor happens to be
                page.evaluate("(px) => window.scrollBy(0, px)", PRODUCT_SCROLL_STEP_PX)
            except Exception:
                break
            page.wait_for_timeout(700)
            try:
                page.wait_for_load_state("networkidle", timeout=3000)
            except Exception:
                pass

            match, position = _scan_product_candidates(page, target_norm, seen, position, similar_matches)
            if match:
                break

            try:
                height_after = page.evaluate("document.body.scrollHeight")
            except Exception:
                height_after = height_before
            if height_before is not None and height_after is not None and height_after <= height_before:
                stable_rounds += 1
                if stable_rounds >= 2:
                    break
            else:
                stable_rounds = 0
            last_height = height_after

    screenshot = _capture_screenshot(page, shot_dir, img_counter, last_state, last_shot_bytes)

    try:
        current_url = page.url
    except Exception:
        current_url = None

    if match:
        return {
            "status": "PASS",
            "product": product_name,
            "found": True,
            "match_type": "exact",
            "position": match["position"],
            "page": 1,
            "title": match["title"],
            "url": match["url"],
            "screenshot": screenshot,
            "reason": None,
            "checked_count": position,
            "search_url": current_url,
        }

    if similar_matches:
        best = similar_matches[0]
        reason = (
            "Exact product not found after checking all available results - "
            f'a similar result was seen at position #{best["position"]}: "{best["title"]}"'
        )
        match_type = "similar"
    else:
        reason = "Product not found after checking all available results"
        match_type = None

    return {
        "status": "FAIL",
        "product": product_name,
        "found": False,
        "match_type": match_type,
        "position": None,
        "page": 1,
        "title": None,
        "url": None,
        "screenshot": screenshot,
        "reason": reason,
        "checked_count": position,
        "search_url": current_url,
    }


def run(qa_url, output_json_path=None, screenshot_dir=None, headless=True, product_name=None):
    _verify_fill_select_retry_intact()
    print("Starting replay...")
    # wall-clock time for the WHOLE run, start to finish - printed and
    # stored alongside the existing per-step "duration" (see `duration =
    # time.monotonic() - step_start` further down, already computed and
    # reported per step) so a run's total time is visible without having
    # to sum every step by hand
    replay_start = time.monotonic()
    result = {
        "status": "FAIL",
        "message": "",
        "qa_url": qa_url,
        "steps": [],
        "final_url": None,
        "final_screenshot": None,
        "final_text": None,
        "product_validation": None,
        "total_duration_s": None,
    }

    # an explicit screenshot_dir (the dashboard flows always pass one -
    # see execute_test in executor/run_execution.py) is already a fresh,
    # unique-per-run folder, used as-is. The fallback here only kicks in
    # when the script is run directly with no screenshot_dir arg -
    # without a per-run subfolder of its own, every such run would write
    # into the SAME shared "screenshots" folder and different runs'
    # same-numbered images would collide/interleave with no way to tell
    # which run a given file came from.
    if screenshot_dir:
        run_dir = Path(screenshot_dir)
    else:
        run_id = f"{_slug(SOURCE_NAME) or 'run'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        run_dir = Path(__file__).resolve().parent / "screenshoots" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # screenshots are grouped into named STAGE subfolders of run_dir - one
    # per navigate action's destination (see _derive_stage_name), instead
    # of one flat sequence - so a run covering several pages can be
    # browsed page-by-page later. shot_dir always points at the CURRENT
    # stage's folder and gets reassigned whenever a "navigate" step
    # actually lands somewhere new; run_dir itself never changes and is
    # where report.json always lives, regardless of how many stages a
    # given run has.
    stage_counter = [1]
    shot_dir = run_dir / _derive_stage_name(None, qa_url, stage_counter[0])

    # one shared, run-wide counter so EVERY screenshot this run takes -
    # the initial load, every per-step capture, the final state, and any
    # product-validation capture - lands in one strictly sequential
    # img1.png, img2.png, ... series, in the exact order they were
    # actually taken. A single-element list so _validate_product (a
    # separate function, called later) can advance the SAME sequence
    # rather than starting its own.
    img_counter = [0]
    # tracks the state fingerprint of the last screenshot actually SAVED
    # this run (see _capture_screenshot/_page_state_key) - also a single-
    # element list so it's shared/mutable across every capture call site,
    # including _validate_product's own.
    last_state = [None]
    # raw PNG bytes of the last screenshot actually SAVED this run - a
    # separate tracker from last_state (see _capture_screenshot for why),
    # used for the genuine pixel-level duplicate check
    last_shot_bytes = [None]
    captured_values = {}
    captured_lists = {}  # stores lists from capture_list steps
    counted_values = {}  # stores counts from count_elements steps
    count_summary_data = {}  # accumulates labeled counts for count_summary

    # same consolidation as screenshots above: an explicit
    # output_json_path (the dashboard flow always passes one, pointed at
    # this same run's folder) is used as-is; direct execution with no
    # path given writes the report into that SAME per-run folder too,
    # rather than not writing one at all
    if not output_json_path:
        output_json_path = str(run_dir / "report.json")

    with sync_playwright() as p:
        try:
            # fixed top-left window position/size for a HEADED launch only
            # (headless has no real window to position at all) - lets the
            # dashboard's live log popup (see static/js/script.js's
            # runRecording()) reliably open in the top-right corner
            # without the two ever overlapping on a normal single-monitor
            # setup, since this window's position/size no longer depends
            # on wherever the OS/window manager happened to place it by
            # default. Purely a window-chrome placement hint to Chromium
            # itself - has no effect on the page's own viewport (still set
            # via new_context() below) or anything replay actually does.
            launch_kwargs = {"headless": headless}
            if not headless:
                launch_kwargs["args"] = ["--window-position=0,0", "--window-size=1280,900"]
            browser = p.chromium.launch(**launch_kwargs)
        except Exception as e:
            # a headed launch can fail on a machine with no display (e.g. a
            # bare server) - headless still lets the replay actually run
            if not headless:
                logger.warning("headed launch failed (%s), falling back to headless", e)
                browser = p.chromium.launch(headless=True)
            else:
                raise
        print("Browser launched.")
        # an explicit context (not the browser.new_page() shorthand) -
        # that shorthand creates a context that only ever supports the one
        # page it made, and raises "Please use browser.new_context()" the
        # moment anything (like the multi-page fallback below) tries to
        # open a second page on it. An explicit context matches how
        # recording already works (see app.py) and actually supports the
        # multi-page workflows recordings can contain.
        try:
            context = browser.new_context(viewport={"width": 1280, "height": REPLAY_VIEWPORT_HEIGHT_PX})
            # A recorded click on a page's Share control invokes the real
            # navigator.share() browser API - during replay that opens a
            # genuine, native, OS-level share dialog, not a page element,
            # which no browser-automation tool can see or close since it
            # lives outside the page's DOM entirely. Once open it blocks
            # the browser window for the rest of the run, so every later
            # action loses any reliable way to reach the page underneath.
            # Registered on the CONTEXT (not just this first page) and
            # before context.new_page() below, so it's already in place
            # for every page this replay ever creates - the initial page,
            # and any later tab_open - not just the one open right now.
            # Generic: touches only navigator.share, on any site, and
            # does nothing but resolve immediately - a real recorded
            # click on a Share button still fires and completes, it just
            # can no longer summon a real OS dialog to get stuck behind.
            context.add_init_script(
                "Object.defineProperty(navigator, 'share', {"
                " value: function () { return Promise.resolve(); },"
                " writable: true, configurable: true });"
            )
            page = context.new_page()
            page.set_default_timeout(8000)
            # cookie banners/alerts shouldn't be able to hang an unattended run
            page.on("dialog", _dismiss_dialog)
        except Exception as e:
            # a crash/disconnect this early (browser died right after
            # launch, resource exhaustion, etc.) previously propagated
            # straight out of run() uncaught - unwinding the
            # sync_playwright() context manager as a side effect, which
            # force-closes the browser with no FAILED status, no message,
            # and no report ever written. That's exactly what "the
            # browser closes unexpectedly" looks like from the outside:
            # not a crash IN a step, but one before any step ever got a
            # chance to run at all.
            print(f"Replay failed - could not set up the browser page:\n{e}")
            # result["message"] is what the dashboard shows as its main
            # summary line - the raw exception (a Playwright internal
            # error string) goes in result["diagnostic"] instead, kept
            # out of the user-facing message but still available in
            # report.json/report.html for anyone who needs it (see
            # generate_report()'s advanced-diagnostics section).
            result["message"] = "Couldn't start the browser for this test run."
            result["diagnostic"] = f"could not set up the browser page: {e}"
            try:
                browser.close()
            except Exception:
                pass
            _write_result(result, output_json_path)
            return result

        try:
            page.goto(qa_url, wait_until="domcontentloaded", timeout=30000)
            _settle(page)
            # a fresh page load should always start at the very top - see
            # _reset_scroll_position's own docstring for why this isn't
            # redundant with the browser's own default behavior
            _reset_scroll_position(page)
        except Exception as e:
            print(f"Replay failed - could not open {qa_url}:\n{e}")
            result["message"] = f"Couldn't reach {qa_url} - check the URL is correct and the site is reachable."
            result["diagnostic"] = f"could not open QA URL: {e}"
            browser.close()
            _write_result(result, output_json_path)
            return result

        # same standard as every other navigate action below: don't treat
        # the initial page load as genuinely ready just because
        # domcontentloaded/networkidle fired - confirm action #1's own
        # target can actually be found first, using the exact same
        # lookahead used for every subsequent navigate action, so the
        # homepage is truly rendered (not just loaded) before anything
        # is clicked on it
        first_step = STEPS[0] if STEPS else None
        first_lp = (first_step or {}).get("locator_profile") or {}
        if first_lp:
            print("[navigate-ready] waiting for step 1's target to become findable (up to 9.0s)...")
            ready_start = time.monotonic()
            if _wait_for_next_step_ready(page, first_step):
                print(f"[navigate-ready] found at t={time.monotonic() - ready_start:.1f}s - initial page is ready")
            else:
                print("[navigate-ready] step 1's target never appeared within the wait window")

        has_explicit_screenshots = any(_is_explicit_screenshot_step(s) for s in STEPS)

        # img1: the settled result of the very first page load if no explicit screenshot steps
        if not has_explicit_screenshots:
            _capture_screenshot(page, shot_dir, img_counter, last_state, last_shot_bytes, step=STEPS[0] if STEPS else None)

        print("REPLAY SOURCE:", SOURCE_NAME)
        print("ACTION COUNT:", len(STEPS))
        print("SOURCE TYPE:", SOURCE_TYPE)
        print()

        # page_id 0 is always the page we just opened above. Recorded
        # actions on any tab/page that opened DURING recording carry a
        # higher page_id (1, 2, ...), assigned in the order those pages
        # appeared - context.on("page") mirrors that same assignment here
        # so a click that (like it did when recording) pops open a new
        # tab gets that tab registered under the matching id automatically.
        # Actions without a page_id (recordings made before this existed)
        # default to 0 via step.get("page_id", 0) below, so single-page
        # recordings replay exactly as before.
        pages = {0: page}
        _next_replay_page_id = [1]

        # the highest page_id this recording ever references - a genuine
        # extra tab/page appearing during replay (one recorded product-
        # selection click somehow opening two tabs, say) shows up here as
        # a NEWLY-assigned pid exceeding this ceiling, which the recording
        # itself never anticipated. Purely diagnostic: this never closes
        # or otherwise touches the extra page, just makes it impossible to
        # miss in the log instead of silently proceeding with more open
        # tabs than the recording expects.
        try:
            _max_recorded_page_id = max(
                (int(s.get("page_id", 0)) for s in STEPS if s.get("page_id") is not None),
                default=0,
            )
        except Exception:
            _max_recorded_page_id = 0

        def _on_replay_new_page(new_page):
            pid = _next_replay_page_id[0]
            _next_replay_page_id[0] += 1
            pages[pid] = new_page
            try:
                new_page.set_default_timeout(8000)
                new_page.on("dialog", _dismiss_dialog)
            except Exception:
                pass
            print(f"(new page/tab appeared during replay - assigned page_id={pid}, url={new_page.url})")
            if pid > _max_recorded_page_id:
                print(
                    f"[extra-tab-check] WARNING: page_id={pid} just opened, but this "
                    f"recording's own actions never reference a page_id beyond "
                    f"{_max_recorded_page_id} - more tabs are open than the recording "
                    f"expects (url={new_page.url})"
                )
                logger.debug(
                    "extra-tab-check: unexpected extra page_id=%d opened "
                    "(recording's own max page_id=%d, url=%r)",
                    pid, _max_recorded_page_id, new_page.url,
                )

        page.context.on("page", _on_replay_new_page)

        print("Executing recorded actions...")
        print()

        total_steps = len(STEPS)
        # published up front (before any step has run) so a dashboard
        # polling output_json_path mid-run always knows the denominator
        # for "step X of Y" - result["steps"] itself only grows one entry
        # at a time as _write_result is called incrementally below.
        result["total_steps"] = total_steps
        prev_timestamp = None
        # these are the action types that can plausibly trigger real
        # navigation (a link, a submit button, Enter in a form) - after
        # one of these succeeds, give any resulting page load a moment to
        # settle before the screenshot/next action, so both see the
        # RESULTING page rather than a mid-navigation snapshot. A click
        # that didn't navigate is already idle, so this resolves almost
        # immediately and doesn't add a meaningful delay to those.
        NAV_CAUSING_ACTIONS = ("click", "dblclick", "right_click", "submit", "press")

        # tracks whether any step since the last successful "navigate" has
        # failed - a navigate is often recorded because an earlier action
        # (form submit, payment step, etc.) succeeded and the app itself
        # redirected there. If what came before it this run actually
        # failed, blindly loading that same URL can LOOK like progress
        # while replaying to a destination that never really earned it.
        failed_since_last_navigate = False

        # set by the navigate-ready check below when a destination's own
        # target never became findable within the wait window - consumed
        # by exactly the ONE step immediately following, then cleared,
        # never carried further (mirrors failed_since_last_navigate's
        # persist-until-consumed pattern above, but for a single step
        # instead of the rest of the session)
        fast_fail_next_step = False

        # set by the click-then-navigate effect-verification block below
        # when it detects a full click -> navigate-to-modal -> ... ->
        # check(value) -> ... -> navigate-back sequence in the recording
        # - carries the trigger element's own locator_profile and the
        # intended value forward until the LATER step that actually
        # returns to the URL this sequence started from, whenever that
        # is, then gets consumed and cleared there (see the modal-
        # sequence final-state check further down the loop)
        pending_modal_verification = None

        # set when a click -> navigate(#fragment) sequence's modal never
        # genuinely opened (see the fragment-target branch below, and
        # the "already there" branch's own _modal_ok check) - rather
        # than forcing the URL and letting subsequent steps (a quantity/
        # size selection, a DONE click, ...) attempt to act against a
        # page that only LOOKS like it has a modal open (the site's own
        # URL-based CSS dimming, with none of the real component state
        # that would actually populate it), every step is explicitly
        # marked SKIPPED - prior modal-open failure until the recording
        # reaches its own next "navigate" (whatever that turns out to
        # be - never assumed to be a specific "return to base" URL,
        # since a recording's own flow might genuinely go somewhere
        # else next). Generic: applies to any modal-opening sequence,
        # never anything quantity/size-specific.
        _skip_deps_until_url = None

        for i, step in enumerate(STEPS, start=1):
            action_type = step.get("action_type")
            cur_timestamp = step.get("timestamp")
            nav_warning = None
            if action_type == "navigate" and failed_since_last_navigate:
                nav_warning = (
                    "prior step(s) since the last successful navigation "
                    "failed - this navigate may be replaying to a URL that "
                    "depended on their success, so the destination may not "
                    "reflect a real transaction"
                )

            # large-bbox recording-quality flag: purely diagnostic, never
            # blocks or changes how this step is resolved/clicked - a
            # recorded bounding box this large (wider AND taller than
            # LARGE_BBOX_WIDTH_PX/LARGE_BBOX_HEIGHT_PX) covers far more
            # area than one specific, deliberately-clicked control
            # plausibly would (a whole "coupons/gifting/..." section, a
            # full card, an entire sidebar), on any site - most likely a
            # broad/accidental click captured during recording rather
            # than a precise one. Surfaced for human review (see
            # large_bbox_flag in the report) so a re-recording decision
            # can be made deliberately, never "fixed" automatically here,
            # since there's no way to know which specific sub-element
            # inside that area was actually meant.
            large_bbox_flag = False
            if action_type in ("click", "dblclick", "right_click"):
                _lbf_box = step.get("bounding_box") or {}
                _lbf_w = _lbf_box.get("width") or 0
                _lbf_h = _lbf_box.get("height") or 0
                if _lbf_w > LARGE_BBOX_WIDTH_PX and _lbf_h > LARGE_BBOX_HEIGHT_PX:
                    large_bbox_flag = True
                    _lbf_note = (
                        f"recorded click target has an unusually large bounding "
                        f"box ({_lbf_w:.0f}x{_lbf_h:.0f}px) covering more area "
                        f"than a single, precisely-targeted element plausibly "
                        f"would - possible recording artifact (a broad/"
                        f"accidental click rather than a deliberate one); "
                        f"consider re-recording this step more precisely"
                    )
                    nav_warning = f"{nav_warning}; {_lbf_note}" if nav_warning else _lbf_note

            # consumed here, immediately, so it can only ever apply to
            # THIS one step - every later step in the loop sees it as
            # False again regardless of what this step's own outcome is
            this_step_fast_fail = fast_fail_next_step
            fast_fail_next_step = False
            prev_action_type = STEPS[i - 2].get("action_type") if i >= 2 else None

            # a PRIOR click -> navigate(#fragment) sequence's modal
            # never genuinely opened (see _skip_deps_until_url's own
            # definition above) - this step depends on that modal being
            # open (it's INSIDE the same sequence, before the recording's
            # own next navigate), so it is never attempted against that
            # broken page state at all; marked SKIPPED explicitly in the
            # report instead of getting its own, unrelated-looking
            # failure reason (a "zero layout size"/"no element at this
            # position" error that doesn't explain the REAL cause).
            if _skip_deps_until_url is not None:
                if action_type == "navigate":
                    # the recording itself is moving on (whether or not
                    # this happens to be the exact URL the failed
                    # sequence started from) - stop skipping and let
                    # this navigate, and everything after it, be
                    # attempted normally again
                    _skip_deps_until_url = None
                else:
                    _print_step_header(i, total_steps, step)
                    print("STATUS: SKIPPED")
                    _skip_reason = (
                        "skipped - an earlier click in this modal-opening "
                        "sequence never produced a genuine modal/dialog "
                        "(no forced URL fallback was used, to avoid "
                        "masking that with a misleading half-open state), "
                        "so this step - which depends on that modal being "
                        "open - was never attempted against a non-"
                        "functional page"
                    )
                    print(f"Reason: {_skip_reason}")
                    print()
                    result["steps"].append({
                        "index": i,
                        "action_type": action_type,
                        "strategy_used": None,
                        "element_found": False,
                        "success": False,
                        "error": _skip_reason,
                        "warning": None,
                        "effect_verified": False,
                        "large_bbox_flag": False,
                        "screenshot": None,
                        "url_before": None,
                        "url_after": None,
                        "duration": 0,
                        "locator_report": None,
                        "expected": None,
                        "actual": None,
                    })
                    # incremental write - see the matching comment at the
                    # main per-step append below for why this is safe to
                    # do on every step rather than only at the very end
                    _write_result(result, output_json_path)
                    continue

            # Everything for this one step lives inside this try/except.
            # Every individual action type already catches its OWN
            # execution errors below (a normal "element not found" keeps
            # the loop going, as before) - this outer layer is a safety
            # net for anything else that could throw (the page dying
            # mid-replay, the pacing wait itself failing, etc.) so THAT
            # can never silently truncate the remaining actions without a
            # trace. If it fires, this step is recorded as failed and the
            # loop stops - the backfill after the loop then explicitly
            # marks every action that never got a chance to run, so the
            # result can never look like a complete run when it wasn't.
            try:
                _print_step_header(i, total_steps, step)
                print("STATUS: STARTED")

                # recorded delay_before_ms is history/diagnostic data
                # about how the user actually paced the recording - it is
                # deliberately NOT replayed as a sleep. Replay waits only
                # for real technical conditions (element/page readiness,
                # popups, navigation) via the Playwright waits already
                # used throughout this loop (_settle, scroll_into_view,
                # the popup wait in _resolve_target_page, etc.), so replay
                # stays materially faster than the original recording.
                prev_timestamp = cur_timestamp

                # every recorded action names which page/tab it belongs to
                # (page_id 0 = the original page; higher ids = tabs that
                # opened during recording) - resolve that page BEFORE
                # acting, since a page that opened mid-recording may not
                # exist yet on this run at exactly the same moment. The
                # fallback URL comes from THIS step's own recorded
                # page_url (not just steps flagged new_tab) so that once
                # the first action for a page_id is recovered, it's
                # registered in `pages` and every later action on that
                # same page_id hits the instant fast-path above instead
                # of repeating the wait.
                target_page_id = step.get("page_id", 0)
                if target_page_id not in pages:
                    fallback_url = to_qa_url(step.get("page_url"), qa_url) if step.get("page_url") else None
                    resolved_page, resolve_err = _resolve_target_page(pages, target_page_id, page, fallback_url=fallback_url)
                else:
                    resolved_page, resolve_err = pages[target_page_id], None

                print("Executing...")

                # set by the "validate" branch below when it captures a
                # screenshot of just the matching block - takes priority
                # over the shared per-step capture further down so the
                # step's reported screenshot is that crop, not a
                # redundant full-page image taken a moment later
                validate_shot_override = None

                # populated only by the validate_text/validate_attribute/
                # validate_visible/validate_value/validate_enabled
                # handlers below - None ("not applicable") for every other
                # action type, same convention as effect_verified above
                expected_value = None
                actual_value = None

                # set by the "click_if_exists" branch below when it
                # fails to find/click its target - checked once, after
                # this step's own STATUS/Reason/screenshot has already
                # been handled the normal way, to halt the whole replay
                stop_replay_after_step = False

                # None ("not applicable") unless this step is a
                # click-type action the RECORDING itself shows was
                # immediately followed by a navigate to a different URL
                # - see the effect-verification block below. True/False
                # once that check actually runs.
                effect_verified = None
                # set (True/False) only when this step is a click-type
                # action about to be checked for a fragment-adding
                # navigate right after it - see the pre-click visibility
                # snapshot further down and _wait_for_modal_target_visible
                pre_click_inner_target_visible = None

                if resolved_page is None:
                    strategy, found, ok, err = None, False, False, (
                        f"page_id={target_page_id} could not be resolved - {resolve_err}"
                    )
                    step_start = time.monotonic()
                    try:
                        url_before = page.url
                    except Exception:
                        url_before = None
                else:
                    page = resolved_page

                    try:
                        url_before = page.url
                    except Exception:
                        url_before = None

                    step_start = time.monotonic()

                    if action_type == "navigate":
                        target = to_qa_url(step.get("page_url"), qa_url)

                        def _same_route(url, _target=target):
                            try:
                                cu, tu = urlsplit(url), urlsplit(_target)
                            except Exception:
                                return url == _target
                            return (
                                cu.scheme, cu.netloc, cu.path.rstrip("/") or "/", cu.query
                            ) == (
                                tu.scheme, tu.netloc, tu.path.rstrip("/") or "/", tu.query
                            )

                        try:
                            if _same_route(page.url):
                                # a preceding action (already executed above,
                                # this step's own click/submit/etc.) already
                                # triggered the app's own client-side
                                # transition to this exact URL - this
                                # recorded navigate is just confirming where
                                # that landed. Nothing to do: forcing a
                                # reload here would discard whatever
                                # client-side state (cart, form progress,
                                # session data) the app built up getting
                                # here for real.
                                _settle(page)
                                strategy, found, ok, err = None, True, True, None
                                # _same_route deliberately excludes the URL
                                # fragment (see its own definition above),
                                # so THIS branch is what actually runs for a
                                # fragment-only navigate (".../cart" ->
                                # ".../cart#modal") whenever the base route
                                # already matches - the common case for a
                                # click-then-navigate-to-modal pair, since
                                # nothing about the PATH changes, only the
                                # fragment. That means the click's own
                                # handler may never have touched the
                                # fragment at all (never mind whether the
                                # real dialog it's supposed to open ever
                                # rendered) and this would still read as
                                # "already there, nothing to do" without
                                # this check. See _verify_modal_opened_or_
                                # retry's own docstring for the full
                                # reasoning - identical logic to the forced-
                                # fallback branch below, shared rather than
                                # duplicated, so it verifies/retries the
                                # same way regardless of which of these
                                # branches actually ran.
                                _modal_ok, _modal_reason, _modal_retried = _verify_modal_opened_or_retry(
                                    page, STEPS, i, url_before, target, shot_dir=shot_dir,
                                )
                                if not _modal_ok:
                                    ok = False
                                    err = _modal_reason
                                    effect_verified = False
                                    # see _skip_deps_until_url's own
                                    # definition - subsequent steps that
                                    # depend on this modal being open are
                                    # never attempted against a page that
                                    # never actually got it
                                    _skip_deps_until_url = url_before
                                elif _modal_retried:
                                    effect_verified = True
                            else:
                                # give the app a short window to arrive here
                                # on its own first - covers the common SPA
                                # case where the PRECEDING step is what
                                # actually triggers a client-side route
                                # change, and this navigate only confirms
                                # the destination rather than something that
                                # should force a fresh document load
                                try:
                                    page.wait_for_url(_same_route, timeout=3500)
                                    _settle(page)
                                    strategy, found, ok, err = None, True, True, None
                                except Exception:
                                    # the natural client-side transition never
                                    # reached the recorded target. Before
                                    # forcing the stale recorded URL, check
                                    # whether the page ALREADY navigated
                                    # somewhere else for real, driven by a
                                    # preceding fill/select whose value could
                                    # plausibly have been hand-edited (a
                                    # search box, a filter dropdown, ...) -
                                    # editing that value naturally produces a
                                    # DIFFERENT, correct destination than what
                                    # was originally recorded (e.g. the old
                                    # search term baked into this navigate's
                                    # page_url). Forcing the stale URL in
                                    # that case would silently discard the
                                    # correct, edited-flow navigation the app
                                    # itself already performed.
                                    #
                                    # The comparison baseline is deliberately
                                    # NOT url_before (this step's own
                                    # starting URL) - a live-search-style
                                    # input often updates the URL
                                    # SYNCHRONOUSLY the moment the preceding
                                    # fill/select runs, one full step before
                                    # this navigate even starts, so url_before
                                    # would already equal the post-edit URL
                                    # and a same-value comparison would never
                                    # see a difference. Instead this looks up
                                    # the PRECEDING step's own recorded
                                    # url_before (from result["steps"], which
                                    # already has that step's entry by now) -
                                    # the URL from before ANY effect of that
                                    # input occurred at all. Gated on "the
                                    # URL genuinely changed away from THAT"
                                    # specifically so the far more common
                                    # case - the preceding action simply
                                    # never triggered any transition at all -
                                    # still gets the exact same forced
                                    # recovery as before; only a page that
                                    # demonstrably WENT somewhere (during the
                                    # fill/select itself, or during this
                                    # step's own wait) skips it.
                                    try:
                                        _current_url_after_wait = page.url
                                    except Exception:
                                        _current_url_after_wait = None
                                    _prev_step = STEPS[i - 2] if i >= 2 else None
                                    _prev_drives_nav = bool(
                                        _prev_step
                                        and _prev_step.get("action_type") in ("fill", "select")
                                        and _prev_step.get("page_id", 0) == step.get("page_id", 0)
                                    )
                                    _prev_result = None
                                    if _prev_drives_nav:
                                        for _s in reversed(result["steps"]):
                                            if _s.get("index") == i - 1:
                                                _prev_result = _s
                                                break
                                    _baseline_url = _prev_result.get("url_before") if _prev_result else None
                                    _follow_edited_destination = bool(
                                        _prev_drives_nav
                                        and _current_url_after_wait
                                        and _baseline_url
                                        and _current_url_after_wait != _baseline_url
                                        and not _same_route(_current_url_after_wait)
                                    )

                                    # BUG 1 diagnostic: logs the EXACT URL
                                    # this fallback was instructed to reach
                                    # (target - computed straight from THIS
                                    # step's own recorded page_url via
                                    # to_qa_url, never a generic/guessed
                                    # URL) against where the browser
                                    # actually ends up after the goto
                                    # settles, so a real mismatch (a site-
                                    # side redirect, a canonical-URL
                                    # rewrite, or a genuine bug in this
                                    # fallback) is directly visible rather
                                    # than silently assumed to be correct
                                    # just because ok=True gets set below.
                                    if _follow_edited_destination:
                                        print(
                                            f"[navigate-edited-input] recorded target was {target!r}, but "
                                            f"the page already navigated to {_current_url_after_wait!r} "
                                            f"after the preceding {_prev_step.get('action_type')} step - "
                                            f"following that real destination instead of forcing the stale "
                                            f"recorded URL"
                                        )
                                    else:
                                        print(f"[navigate-fallback] instructed to navigate to: {target!r}")
                                        page.goto(target, wait_until="domcontentloaded", timeout=30000)
                                    _settle(page)
                                    _reset_scroll_position(page)
                                    try:
                                        _actual_landed_url = page.url
                                    except Exception:
                                        _actual_landed_url = None
                                    print(f"[navigate-fallback] browser actually landed on: {_actual_landed_url!r}")
                                    if (
                                        not _follow_edited_destination
                                        and _actual_landed_url
                                        and not _urls_same_target(_actual_landed_url, target)
                                    ):
                                        print(
                                            "[navigate-fallback] MISMATCH - the instructed URL and the "
                                            "actual landing URL differ (path/query, not just fragment) - "
                                            "this fallback DID navigate to the exact recorded page_url; "
                                            "the divergence happened AFTER that, most likely a site-side "
                                            "redirect/canonical-URL rewrite on the destination itself, "
                                            "not a bug in what URL this fallback requested"
                                        )
                                    strategy, found, ok, err = None, True, True, None
                                    if _follow_edited_destination:
                                        fallback_note = (
                                            f"navigated to {_actual_landed_url!r} instead of the recorded "
                                            f"{target!r} - the preceding fill/select step's value looks "
                                            f"like it was edited, so the edited flow's real destination was "
                                            f"followed instead of the stale recorded one"
                                        )
                                        # a REAL client-side transition did
                                        # happen here (the app itself
                                        # navigated, unlike the forced-
                                        # fallback case below) - reported as
                                        # verified, not as an unresolved
                                        # recovery
                                        effect_verified = True
                                    else:
                                        fallback_note = (
                                            "forced hard-navigation fallback - preceding action "
                                            "may not have triggered the app's own client-side "
                                            "transition, destination page may be missing state "
                                            "it would normally have"
                                        )
                                    nav_warning = f"{nav_warning}; {fallback_note}" if nav_warning else fallback_note
                                    # everything below is specifically about
                                    # diagnosing/verifying a FORCED-fallback
                                    # navigation (a click that may not have
                                    # really worked, recovered from only by
                                    # hard-navigating to the recorded URL) -
                                    # none of it applies when
                                    # _follow_edited_destination is True,
                                    # since that path never force-navigated
                                    # at all: the page already reached its
                                    # real, legitimately-edited destination
                                    # on its own, and effect_verified was
                                    # already set True for it above.
                                    if not _follow_edited_destination:
                                        # reuses the SAME effect_verified signal
                                        # every other click-then-navigate check in
                                        # this file already reports through - the
                                        # URL was reached here ONLY because this
                                        # branch forced it directly, not because
                                        # the preceding action's own natural
                                        # effect (a click genuinely landing on its
                                        # intended target, a real client-side
                                        # route change) ever happened. Reporting
                                        # this the same way as any other
                                        # unverified effect means a human
                                        # scanning the report sees the SAME "No"
                                        # signal here as for a click that visibly
                                        # failed to reach its target - not a
                                        # clean, unqualified "passed" that hides
                                        # exactly the ambiguity this exists to
                                        # surface: the preceding step's own click
                                        # may have landed on the wrong element
                                        # entirely, recovered from only because
                                        # this navigate happened to be recorded
                                        # and could force the URL directly.
                                        effect_verified = False
                                        print(
                                            "[navigate-fallback] WARNING: click did not produce "
                                            "expected navigation, force-navigated as fallback - "
                                            "original click target uncertain"
                                        )
                                        # same shared verify-then-retry as the
                                        # _same_route "already there" branch
                                        # above - see _verify_modal_opened_or_
                                        # retry's own docstring. Covers the
                                        # other half of the same real gap: a
                                        # click whose handler never touches the
                                        # URL at all, relying entirely on THIS
                                        # forced fallback to reach the fragment.
                                        _modal_ok, _modal_reason, _modal_retried = _verify_modal_opened_or_retry(
                                            page, STEPS, i, url_before, target, shot_dir=shot_dir,
                                        )
                                        if not _modal_ok:
                                            ok = False
                                            err = _modal_reason
                                            effect_verified = False
                                            # see _skip_deps_until_url's own
                                            # definition - subsequent steps that
                                            # depend on this modal being open are
                                            # never attempted against a page that
                                            # never actually got it
                                            _skip_deps_until_url = url_before
                                        elif _modal_retried:
                                            effect_verified = True
                                        elif not urlsplit(target).fragment:
                                            # _verify_modal_opened_or_retry only
                                            # ever checks a FRAGMENT-based modal
                                            # sub-state (see its own docstring/
                                            # entering_substate check) - a plain
                                            # full-page target with no fragment
                                            # at all means it had nothing to
                                            # verify and returned ok=True
                                            # unconditionally, which used to
                                            # leave this whole forced-fallback
                                            # (the preceding click's own
                                            # navigation never arrived on its
                                            # own - effect_verified is already
                                            # False above) reported as a plain
                                            # step PASS with no real
                                            # confirmation the landed page is
                                            # even the right one. Confirmed via
                                            # a real repro: forcing navigation
                                            # to a client-side-only pushState
                                            # route with no server-side page
                                            # behind it landed on a 404 and
                                            # still reported STATUS: SUCCESS /
                                            # RESULT: PASS. Failing it here
                                            # instead surfaces that as a real
                                            # failure rather than a silent
                                            # wrong-page pass.
                                            ok = False
                                            err = (
                                                "forced hard-navigation fallback: the preceding "
                                                "click did not produce the recorded navigation on "
                                                "its own, and the destination page could not be "
                                                "verified - treating as failed rather than a "
                                                "silent, unconfirmed pass"
                                            )
                        except Exception as e:
                            strategy, found, ok, err = None, True, False, str(e)

                        if ok:
                            # the URL and networkidle checks above can both
                            # be satisfied while the SPA is still rendering
                            # the previous view underneath - the strongest,
                            # most directly relevant signal that the
                            # destination is actually usable is whether the
                            # NEXT recorded step's own target can be found
                            # there, so check that directly instead of a
                            # generic content-diff/timing heuristic.
                            next_step = STEPS[i] if i < len(STEPS) else None
                            next_lp = (next_step or {}).get("locator_profile") or {}
                            if next_lp:
                                print(f"[navigate-ready] waiting for next step's target to become findable (up to 9.0s)...")
                                ready_start = time.monotonic()
                                if _wait_for_next_step_ready(page, next_step):
                                    print(f"[navigate-ready] found at t={time.monotonic() - ready_start:.1f}s - destination page is ready")
                                else:
                                    print(f"[navigate-ready] next step's target never appeared within the wait window")
                                    readiness_note = (
                                        "next recorded step's target never appeared on this "
                                        "page within the wait window - destination may not have "
                                        "actually finished loading/rendering"
                                    )
                                    nav_warning = f"{nav_warning}; {readiness_note}" if nav_warning else readiness_note
                                    # give the very next step a single normal-speed
                                    # resolution attempt, but let it fail fast
                                    # (skip the settle/scroll escalation tiers)
                                    # instead of burning the full expensive retry
                                    # cycle on a target whose page likely never
                                    # loaded - cleared automatically after that
                                    # one step, win or lose
                                    fast_fail_next_step = True

                        # regroup screenshots from here on under a new
                        # STAGE subfolder, named for wherever this
                        # navigate actually left the page - checked AFTER
                        # the attempt above (not from the recorded target
                        # URL) so a same-route no-op or a failed navigate
                        # that never actually left the current page
                        # naturally reproduces the SAME stage name (no new
                        # folder), while a real transition (success or the
                        # forced hard-navigation fallback) gets its own.
                        # run_dir itself - where report.json lives - never
                        # changes; only shot_dir, the CURRENT stage's
                        # folder, does.
                        try:
                            stage_counter[0] += 1
                            new_stage = _derive_stage_name(page, None, stage_counter[0])
                            shot_dir = run_dir / new_stage
                        except Exception as e:
                            logger.warning("couldn't set up stage folder for this navigate: %s", e)
                    elif action_type == "scroll":
                        # a scroll recorded against a nested scrollable
                        # container (not the window) carries a css_path
                        # and/or xpath locator for it - resolved here via
                        # the same _find_by_css/_find_by_xpath tiers
                        # resolve_and_act itself uses (css_path first,
                        # xpath as a fallback when css_path is absent or
                        # doesn't resolve), so that container gets
                        # scrolled directly instead of the page as a
                        # whole. No locator at all (the common case, or
                        # an older recording predating this field) means
                        # plain window scrolling, unchanged. scroll_y_after
                        # (absolute recorded position) is passed through
                        # when present so the final position gets
                        # corrected for any drift.
                        try:
                            scroll_lp = step.get("locator_profile") or {}
                            # SCOPED FIX: was _find_by_css then _find_by_xpath
                            # only - a narrower, scroll-specific two-tier
                            # lookup instead of _resolve_element(), the SAME
                            # full-priority resolver every other action type
                            # (click/fill/check) already goes through. Reuses
                            # it here unchanged - no new resolution logic, no
                            # change to _replay_scroll's own scroll mechanism
                            # (still element.scrollLeft/scrollTop via
                            # evaluate() for a resolved container, still
                            # page.mouse.wheel() for window-level scrolling
                            # when locator_profile is null/absent, exactly as
                            # before).
                            scroll_el = _resolve_element(page, scroll_lp) if scroll_lp else None
                            # driven ENTIRELY by whether this recorded step
                            # carries a locator_profile at all - never a
                            # site/URL/class-name check - so the exact same
                            # code path handles a whole-page-scroll site
                            # (locator_profile null) and an inner-div-scroll
                            # site (locator_profile present) identically
                            if scroll_el is not None:
                                print(f"[scroll] element-level scroll on {scroll_lp.get('css_path') or scroll_lp.get('xpath') or '(resolved element)'}")
                            elif not scroll_lp:
                                print("[scroll] window-level scroll (no locator_profile recorded)")
                            if scroll_el is None and scroll_lp:
                                # a container WAS recorded for this scroll
                                # but nothing resolved it on the live page -
                                # falling back to window-level scrolling from
                                # here is silent and looks identical to a
                                # genuinely successful container scroll
                                # otherwise, so flag it via the same
                                # nav_warning mechanism this loop already
                                # uses elsewhere, rather than let it
                                # disappear into an indistinguishable
                                # "success"
                                nav_warning = (
                                    "scroll target container not found - "
                                    "fell back to window-level scroll"
                                )
                                print(
                                    f"[scroll] target container not found "
                                    f"({scroll_lp.get('css_path') or scroll_lp.get('xpath')!r}) - "
                                    f"falling back to window-level scroll"
                                )

                            # lazy-load/infinite-scroll priming: only
                            # meaningful when an absolute target was
                            # actually recorded - see
                            # _ensure_scroll_content_ready's own
                            # docstring for the full reasoning. Runs
                            # BEFORE the real scroll attempt below, so a
                            # page whose further content only mounts once
                            # scrolling gets close to it has a real
                            # chance to grow first, rather than a
                            # doomed jump straight to a position that
                            # simply doesn't exist yet.
                            content_stabilized = False
                            _scroll_target_peek = step.get("scroll_y_after")
                            if _scroll_target_peek is not None:
                                _reachable, _sh, content_stabilized = _ensure_scroll_content_ready(
                                    page, _scroll_target_peek, scroll_el,
                                )
                                if not _reachable:
                                    logger.debug(
                                        "scroll-lazy-load: target %s still not reachable "
                                        "after probing (scrollHeight=%s, stabilized=%s)",
                                        _scroll_target_peek, _sh, content_stabilized,
                                    )

                            _replay_scroll(
                                page,
                                step.get("delta_x") or 0,
                                step.get("delta_y") or 0,
                                step.get("scroll_y_after"),
                                scroll_el,
                            )
                            strategy, found, ok, err = None, True, True, None

                            # verify the scroll actually reached its
                            # recorded target - _replay_scroll's own
                            # window.scrollTo()/el.scrollTop snap is a
                            # single fire-and-forget call with no
                            # confirmation it landed: the page's
                            # scrollHeight can be shorter than expected
                            # (content still loading) and clamp the
                            # scroll short, or smooth-scroll CSS can make
                            # it animate rather than land instantly, and
                            # either way the very next action would then
                            # fire against a page that never actually
                            # reached where the recording shows it did.
                            # Only meaningful when an absolute target was
                            # actually recorded (scroll_y_after) - older
                            # recordings with delta-only scrolls have no
                            # target to verify against, same as every
                            # other best-effort signal in this file.
                            scroll_target_y = step.get("scroll_y_after")
                            if scroll_target_y is not None:
                                reached, last_pos = _verify_scroll_reached(page, scroll_target_y, scroll_el)
                                # a genuine retry LOOP, not a single fixed
                                # retry - a page whose content is still
                                # growing (lazy-loaded/infinite-scroll
                                # sections that only mount once scrolling
                                # gets near them) can easily still be short
                                # of the recorded target after one re-
                                # attempt, needing several more before its
                                # scrollHeight is actually tall enough to
                                # reach it at all. Bounded by
                                # SCROLL_MAX_RETRIES, never open-ended -
                                # each iteration re-does the full
                                # _replay_scroll (incremental hops +
                                # absolute snap) so a still-loading page
                                # gets a fresh real chance to grow between
                                # attempts, not just a repeated snap to the
                                # same (possibly still-clamped) value.
                                retry_count = 0
                                while not reached and retry_count < SCROLL_MAX_RETRIES and not content_stabilized:
                                    retry_count += 1
                                    print(
                                        f"[scroll-verify] WARNING: scroll did not reach target "
                                        f"position (target={scroll_target_y}, at={last_pos}) - "
                                        f"retrying ({retry_count}/{SCROLL_MAX_RETRIES})"
                                    )
                                    # re-probe content-readiness on every
                                    # retry too, not just before the first
                                    # attempt - a page can still be
                                    # actively loading further content
                                    # across several of these iterations,
                                    # and this is what lets the loop
                                    # notice once scrollHeight has
                                    # genuinely stopped growing, ending
                                    # the retries early instead of
                                    # burning the full budget on a jump
                                    # that will never land
                                    _reachable, _sh, content_stabilized = _ensure_scroll_content_ready(
                                        page, scroll_target_y, scroll_el,
                                    )
                                    _replay_scroll(
                                        page,
                                        step.get("delta_x") or 0,
                                        step.get("delta_y") or 0,
                                        scroll_target_y,
                                        scroll_el,
                                    )
                                    reached, last_pos = _verify_scroll_reached(page, scroll_target_y, scroll_el)
                                if not reached:
                                    if content_stabilized:
                                        print(
                                            f"[scroll-verify] WARNING: page content has stabilized "
                                            f"(scrollHeight stopped growing) and the target position "
                                            f"is still unreachable (target={scroll_target_y}, "
                                            f"at={last_pos}) - genuine failure, not a loading delay"
                                        )
                                    else:
                                        print(
                                            f"[scroll-verify] WARNING: scroll still did not reach "
                                            f"target position after {retry_count} retries "
                                            f"(target={scroll_target_y}, at={last_pos})"
                                        )
                                effect_verified = reached
                                if not reached:
                                    ok = False
                                    if content_stabilized:
                                        err = (
                                            f"scroll did not reach target position {scroll_target_y} "
                                            f"(ended at {last_pos}) - page content has genuinely "
                                            f"stabilized (scrollHeight stopped growing), target is "
                                            f"not reachable"
                                        )
                                    else:
                                        err = (
                                            f"scroll did not reach target position {scroll_target_y} "
                                            f"(ended at {last_pos}) after {retry_count} retries"
                                        )
                        except Exception as e:
                            strategy, found, ok, err = None, True, False, str(e)
                    elif action_type == "tab_switch":
                        # the page-resolution step above already switched
                        # `page` to the recorded to_page_id (every step
                        # resolves its target page before acting, tab_switch
                        # is no different) - bring_to_front() just makes
                        # that switch visually real in a headed run too,
                        # matching what the user actually did
                        try:
                            page.bring_to_front()
                            strategy, found, ok, err = None, True, True, None
                        except Exception as e:
                            strategy, found, ok, err = None, True, False, str(e)
                    elif action_type == "tab_open":
                        # the page-resolution step above already found (a
                        # real popup, if one happened) or created (the
                        # fallback in _resolve_target_page) the runtime
                        # page for this recorded page_id - no separate
                        # goto here: the page is already at the right URL,
                        # and re-navigating an already-loaded new tab
                        # could re-trigger side effects the original
                        # tab-open never had. Just let it settle.
                        try:
                            _settle(page)
                            strategy, found, ok, err = None, True, True, None
                        except Exception as e:
                            strategy, found, ok, err = None, True, False, str(e)
                    elif action_type == "tab_close":
                        # closes the runtime page for the recorded page_id
                        # this step names (already resolved to `page`
                        # above) - later steps resolve their OWN page_id
                        # fresh via the same mechanism, so this doesn't
                        # need to do anything beyond the close itself
                        try:
                            if not page.is_closed():
                                page.close()
                            strategy, found, ok, err = None, True, True, None
                        except Exception as e:
                            strategy, found, ok, err = None, True, False, str(e)
                    elif action_type == "validate":
                        if step.get("check_mode") == "field_presence":
                            # a DIFFERENT validate shape from the search
                            # case below: one submitted FORM FIELD's
                            # typed value (name/email/phone/etc - never
                            # password/sensitive fields, see
                            # recorder/record_session.py's
                            # _maybe_auto_insert_field_presence_validate),
                            # checked as plain text presence on whatever
                            # page results (e.g. a profile page). Not a
                            # repeating list of results, so the block-wise
                            # logic below doesn't apply here - this reuses
                            # only the original, always-safe whole-page
                            # substring check.
                            expected_text = (step.get("value") or "").strip()
                            _settle(page)
                            _scroll_reveal_full_page(page)

                            deadline = time.monotonic() + 9.0
                            text_found = False
                            while True:
                                try:
                                    body_text = " ".join((page.inner_text("body") or "").split())
                                except Exception:
                                    body_text = ""
                                text_found = bool(expected_text) and expected_text.lower() in body_text.lower()
                                if text_found or time.monotonic() >= deadline:
                                    break
                                page.wait_for_timeout(300)

                            if text_found:
                                strategy, found, ok, err = None, True, True, None
                            else:
                                _diagnose_validate_failure(page, expected_text)
                                reason = f'Expected field value "{expected_text}" not found on page.'
                                strategy, found, ok, err = None, False, False, reason
                        else:
                            # read-only: confirms the searched-for text (added
                            # automatically at record time right after a
                            # search-type fill was submitted - see
                            # recorder/record_session.py's
                            # _maybe_auto_insert_validate) shows up on
                            # whatever page that search produced. Preferred
                            # check: does any individual result/listing BLOCK
                            # (see _detect_result_blocks) CONTAIN the expected
                            # text - substring, case-insensitive, never exact
                            # equality, since a real listing's title is
                            # normally longer than a short recorded search
                            # term. Falls back to the plain whole-page text
                            # search (the original, always-safe check) when
                            # block detection isn't usable for this page -
                            # throws, or finds an implausible number of
                            # "blocks" - so a bad detection can never turn
                            # into a bad validate result.
                            expected_text = (step.get("value") or "").strip()
                            _settle(page)
                            # reveal the full first page of results (lazy-
                            # loaded content below the fold) before checking -
                            # otherwise a genuinely-present result that hasn't
                            # scrolled into view yet would be reported as
                            # missing
                            _scroll_reveal_full_page(page)

                            use_blocks = expected_text != ""
                            blocks, total_blocks = [], 0
                            match = None
                            text_found = False
                            # bounded poll for async-rendered results, the
                            # same shape as the navigate-readiness wait
                            # elsewhere in this file (a time.monotonic
                            # deadline + page.wait_for_timeout between
                            # checks) - a search results page commonly
                            # finishes its own data fetch a moment after the
                            # network itself already went quiet. One single
                            # bounded window covers whichever check
                            # (block-wise or the plain fallback) ends up
                            # being used - never two separate windows back
                            # to back.
                            deadline = time.monotonic() + 9.0
                            while True:
                                if use_blocks:
                                    blocks, use_blocks = _detect_result_blocks(page)
                                    if use_blocks:
                                        total_blocks = len(blocks)
                                        match = next(
                                            (b for b in blocks if expected_text.lower() in (b.get("text") or "").lower()),
                                            None,
                                        )
                                # always also run the plain whole-page check,
                                # even when block detection is usable - the
                                # expected text can legitimately appear in
                                # page furniture that isn't part of any
                                # listing block (e.g. a "results for '<query>'"
                                # header), and a page that used to pass under
                                # the old whole-page-only check must keep
                                # passing here
                                try:
                                    body_text = " ".join((page.inner_text("body") or "").split())
                                except Exception:
                                    body_text = ""
                                text_found = bool(expected_text) and expected_text.lower() in body_text.lower()
                                if match or text_found or time.monotonic() >= deadline:
                                    break
                                page.wait_for_timeout(300)

                            if match:
                                strategy, found, ok, err = None, True, True, None
                                print(f"[validate] matched result #{match['index'] + 1} of {total_blocks}")
                                # screenshot of just the matching block, in
                                # the SAME per-run screenshoots folder and
                                # sequential imgN.png naming as every other
                                # screenshot this run takes - no separate
                                # folder, no new naming scheme
                                try:
                                    block_locator = page.locator(f'[data-afqa-block-idx="{match["index"]}"]')
                                    shot_path = _next_shot_path(shot_dir, img_counter)
                                    block_locator.screenshot(path=str(shot_path))
                                    validate_shot_override = str(shot_path)
                                    # the page itself didn't change from this
                                    # (read-only) capture - recording its
                                    # fingerprint now means the shared per-
                                    # step capture right below correctly sees
                                    # "already captured" and skips a redundant
                                    # full-page duplicate, rather than this
                                    # crop being silently superseded by one
                                    new_state = _page_state_key(page)
                                    if new_state is not None:
                                        last_state[0] = new_state
                                except Exception as e:
                                    logger.warning("couldn't capture matching-block screenshot: %s", e)
                            elif text_found:
                                strategy, found, ok, err = None, True, True, None
                            else:
                                _diagnose_validate_failure(page, expected_text)
                                if total_blocks:
                                    reason = (
                                        f'Expected text "{expected_text}" not found among '
                                        f'{total_blocks} result(s) on this page.'
                                    )
                                else:
                                    reason = f'Expected text "{expected_text}" not found on page.'
                                strategy, found, ok, err = None, False, False, reason
                    elif action_type == "click_if_exists":
                        # generic "click this if it's there" step - unlike
                        # every other action type, there's no recorded
                        # locator_profile to resolve at all: the target
                        # is a plain exact-match text string, resolved
                        # fresh on THIS page at replay time (see
                        # _resolve_click_if_exists). Any failure to
                        # find/click it halts the whole replay right
                        # here - see the stop_replay_after_step check
                        # further below, after this step's own
                        # STATUS/Reason/screenshot has already been
                        # handled the same way as every other action.
                        target_text = (step.get("target") or "").strip()
                        print(f'Target: "{target_text}"')
                        click_result = _resolve_click_if_exists(page, target_text)
                        strategy, found = None, click_result["ok"]
                        ok, err = click_result["ok"], click_result["reason"]
                        if not ok:
                            stop_replay_after_step = True
                    elif action_type == "add_to_cart_and_verify":
                        # opt-in composite action for an "add to cart"-
                        # style flow whose real success can only be
                        # confirmed by watching a UI confirmation state
                        # and then verifying the destination it leads to
                        # - never auto-triggered by recognizing button
                        # text, only ever run when a step was explicitly
                        # recorded/edited with this action_type and its
                        # own selectors/text. See add_to_cart_and_verify()
                        # for the full behavior; every parameter here
                        # comes straight from this step's own recorded
                        # fields, nothing hardcoded in this file itself.
                        _atc_click = step.get("click_selector")
                        _atc_confirmation_selector = step.get("confirmation_selector")
                        _atc_confirmation_text = step.get("confirmation_text")
                        _atc_verification_selector = step.get("verification_selector")
                        _atc_verification_text = step.get("verification_text")
                        if (
                            not _atc_click
                            or not (_atc_confirmation_selector or _atc_confirmation_text)
                            or not (_atc_verification_selector or _atc_verification_text)
                        ):
                            strategy, found, ok, err = None, False, False, (
                                "add_to_cart_and_verify step is missing one or more "
                                "required fields (click_selector, and either "
                                "confirmation_selector or confirmation_text, and either "
                                "verification_selector or verification_text)"
                            )
                        else:
                            _atc_ok, _atc_message, _atc_attempts = add_to_cart_and_verify(
                                page,
                                _atc_click,
                                confirmation_selector=_atc_confirmation_selector,
                                confirmation_text=_atc_confirmation_text,
                                next_action_selector=step.get("next_action_selector"),
                                next_action_text=step.get("next_action_text"),
                                verification_selector=_atc_verification_selector,
                                verification_text=_atc_verification_text,
                                max_retries=step.get("max_retries") or ADD_TO_CART_MAX_RETRIES,
                                confirmation_timeout=step.get("confirmation_timeout_ms") or ADD_TO_CART_CONFIRMATION_TIMEOUT_MS,
                                verification_timeout=step.get("verification_timeout_ms") or ADD_TO_CART_VERIFICATION_TIMEOUT_MS,
                            )
                            strategy = f"attempts={_atc_attempts}"
                            found = True
                            ok, err = _atc_ok, (None if _atc_ok else _atc_message)
                    elif action_type == "capture_value":
                        label_name = (step.get("capture_as") or "").strip()
                        lp = step.get("locator_profile") or {}
                        el = _resolve_element(page, lp)
                        if el is not None:
                            val = _extract_element_value(el)
                            if val is not None:
                                captured_values[label_name] = val
                                print(f'Captured value under "{label_name}": {val!r}')
                                strategy, found, ok, err = None, True, True, None
                            else:
                                captured_values[label_name] = ""
                                print(f'Captured empty value under "{label_name}"')
                                strategy, found, ok, err = None, True, True, None
                        else:
                            strategy, found, ok, err = None, False, False, f"Could not locate element to capture value for label '{label_name}'"
                    elif action_type == "compare_value":
                        label_name = (step.get("compare_to") or "").strip()
                        if label_name not in captured_values:
                            reason = f"no value was captured under label '{label_name}'"
                            strategy, found, ok, err = None, False, False, reason
                        else:
                            expected_text = str(captured_values[label_name]).strip()
                            _settle(page)
                            _scroll_reveal_full_page(page)

                            deadline = time.monotonic() + 9.0
                            text_found = False
                            while True:
                                try:
                                    body_text = " ".join((page.inner_text("body") or "").split())
                                except Exception:
                                    body_text = ""
                                text_found = bool(expected_text) and expected_text.lower() in body_text.lower()
                                if text_found or time.monotonic() >= deadline:
                                    break
                                page.wait_for_timeout(300)

                            if text_found:
                                strategy, found, ok, err = None, True, True, None
                                print(f'Compare matched captured value "{expected_text}" (label: {label_name}) on page')
                            else:
                                _diagnose_validate_failure(page, expected_text)
                                reason = f'Captured value "{expected_text}" (label: {label_name}) not found on page.'
                                strategy, found, ok, err = None, False, False, reason
                    elif action_type == "screenshot":
                        # manual, settle-aware capture - unlike every
                        # other action type, this one doesn't click,
                        # fill, or navigate anything at all; it just
                        # waits for the CURRENT page to be genuinely,
                        # fully loaded (see _wait_for_page_settle) and
                        # takes exactly one screenshot. A failure here
                        # (e.g. the screenshot write itself failing)
                        # marks just this one step FAILED and continues
                        # - unlike click_if_exists, it never halts the
                        # replay, since it's a passive capture nothing
                        # later depends on.
                        label = (step.get("label") or "").strip() or None
                        print(f'Label: "{label}"' if label else "Label: (none - sequential naming)")
                        shot_path = _capture_screenshot_when_settled(page, shot_dir, img_counter, label=label, step=step, run_dir=run_dir, stage_counter=stage_counter)
                        ok = shot_path is not None
                        strategy, found = None, ok
                        if ok:
                            err = None
                            # this step's own capture already IS its
                            # real evidence - report that path instead
                            # of whatever the shared per-step capture
                            # further below does
                            validate_shot_override = shot_path
                            # _capture_screenshot_when_settled deliberately
                            # doesn't touch last_state/last_shot_bytes (see
                            # its own signature) - recording this capture's
                            # fingerprint and bytes here means the shared
                            # per-step capture right below correctly sees
                            # "already captured" and skips a redundant
                            # duplicate, the same pattern the validate
                            # branch above already uses for its own crop
                            new_state = _page_state_key(page)
                            if new_state is not None:
                                last_state[0] = new_state
                            try:
                                last_shot_bytes[0] = Path(shot_path).read_bytes()
                            except Exception:
                                pass
                        else:
                            err = "screenshot capture failed - could not write the image file"

                    # ── NEW ACTION TYPES ─────────────────────────────────

                    elif action_type == "validate_element":
                        # Checks whether a specific element on the page
                        # is disabled (check: "disabled") or enabled
                        # (check: "enabled"). Does NOT alter the page.
                        # success=True when the check matches reality.
                        lp = step.get("locator_profile") or {}
                        check_mode = (step.get("check") or "disabled").strip().lower()
                        _settle(page)
                        try:
                            # try all available locator hints in priority order
                            el = None
                            for selector_fn in [
                                lambda: page.get_by_text(lp["text"], exact=False).first if lp.get("text") else None,
                                lambda: page.get_by_role(lp["role"]).first if lp.get("role") else None,
                                lambda: page.locator(lp["css_path"]).first if lp.get("css_path") else None,
                                lambda: page.locator(lp["xpath"]).first if lp.get("xpath") else None,
                            ]:
                                try:
                                    candidate = selector_fn()
                                    if candidate and candidate.count() > 0:
                                        el = candidate
                                        break
                                except Exception:
                                    pass

                            if el is None:
                                strategy, found, ok, err = None, False, False, "Element not found for validate_element"
                            else:
                                is_disabled = el.is_disabled()
                                if check_mode == "disabled":
                                    ok = is_disabled
                                    result_msg = "disabled" if is_disabled else "enabled (expected disabled)"
                                elif check_mode == "enabled":
                                    ok = not is_disabled
                                    result_msg = "enabled" if not is_disabled else "disabled (expected enabled)"
                                else:
                                    ok, result_msg = False, f"unknown check mode: {check_mode!r}"
                                print(f"[validate_element] Element is {'disabled' if is_disabled else 'enabled'} → check '{check_mode}': {'PASS' if ok else 'FAIL'} ({result_msg})")
                                strategy, found = None, True
                                if not ok:
                                    err = f"validate_element failed: element is {result_msg}"
                                else:
                                    err = None
                        except Exception as ve:
                            strategy, found, ok, err = None, False, False, str(ve)

                    # ── ELEMENT-LEVEL VALIDATION ACTIONS ────────────────
                    # validate_text/validate_attribute/validate_visible/
                    # validate_value/validate_enabled all follow the exact
                    # same shape: resolve the target through the SAME
                    # 12-level fallback chain everything else uses
                    # (_resolve_element_with_strategy - the identical
                    # finder list as _resolve_element, just also reporting
                    # which tier matched), bounded-poll for it using the
                    # centralized LOCATOR_TIMEOUT_MS/LOCATOR_POLL_INTERVAL_MS
                    # (stop immediately once found, fail after the
                    # timeout - no infinite retries), then check ONE
                    # condition and record expected/actual for the report.
                    # No separate validation locator engine - this is the
                    # existing resolver, wrapped for reporting.
                    elif action_type == "validate_text":
                        lp = step.get("locator_profile") or {}
                        expected_value = step.get("value") or ""
                        match_mode = (step.get("match_mode") or "contains").strip().lower()
                        el, strategy, _attempt = _resolve_with_timeout(page, lp)
                        if el is None:
                            found, ok, err = False, False, "validate_text: element not found"
                        else:
                            found = True
                            try:
                                actual_value = _extract_element_value(el) or ""
                                if not actual_value:
                                    actual_value = " ".join((el.inner_text(timeout=1000) or "").split())
                            except Exception:
                                actual_value = ""
                            if match_mode == "exact":
                                ok = actual_value.strip() == expected_value.strip()
                            else:
                                ok = expected_value.strip().lower() in actual_value.lower()
                            err = None if ok else (
                                f"validate_text: expected {'exactly ' if match_mode == 'exact' else ''}"
                                f"{expected_value!r}, got {actual_value!r}"
                            )
                            print(f"[validate_text] expected={expected_value!r} actual={actual_value!r} mode={match_mode}: {'PASS' if ok else 'FAIL'}")

                    elif action_type == "validate_attribute":
                        lp = step.get("locator_profile") or {}
                        attribute_name = (step.get("attribute_name") or "").strip()
                        expected_value = step.get("value") or ""
                        el, strategy, _attempt = _resolve_with_timeout(page, lp)
                        if el is None:
                            found, ok, err = False, False, "validate_attribute: element not found"
                        elif not attribute_name:
                            found, ok, err = True, False, "validate_attribute: no attribute name given"
                        else:
                            found = True
                            try:
                                actual_value = el.get_attribute(attribute_name)
                            except Exception:
                                actual_value = None
                            ok = (actual_value or "") == expected_value
                            err = None if ok else (
                                f"validate_attribute: {attribute_name!r} expected {expected_value!r}, "
                                f"got {actual_value!r}"
                            )
                            print(f"[validate_attribute] {attribute_name}: expected={expected_value!r} actual={actual_value!r}: {'PASS' if ok else 'FAIL'}")

                    elif action_type == "validate_visible":
                        lp = step.get("locator_profile") or {}
                        expected_state = (step.get("expected_state") or "visible").strip().lower()
                        expected_value = expected_state
                        # a step validating "hidden" must not fail just
                        # because the element hasn't rendered YET - a
                        # short bounded poll either way, same centralized
                        # timeout as every other new validation action
                        el, strategy, _attempt = _resolve_with_timeout(page, lp)
                        if el is None:
                            is_visible = False
                            found = False
                        else:
                            found = True
                            try:
                                is_visible = el.is_visible()
                            except Exception:
                                is_visible = False
                        actual_value = "visible" if is_visible else "hidden"
                        if expected_state == "hidden":
                            ok = not is_visible
                        else:
                            ok = is_visible
                        err = None if ok else f"validate_visible: element is {actual_value}, expected {expected_state}"
                        print(f"[validate_visible] expected={expected_state} actual={actual_value}: {'PASS' if ok else 'FAIL'}")

                    elif action_type == "validate_url":
                        # no element/locator involved at all - checks the
                        # CURRENT page URL, same locator-free shape as the
                        # base "validate" (content-check) action type
                        # above, not the element-based validate_* blocks
                        # around it
                        expected_value = step.get("value") or ""
                        match_mode = (step.get("match_mode") or "contains").strip().lower()
                        try:
                            actual_value = page.url
                        except Exception:
                            actual_value = ""
                        if match_mode == "exact":
                            ok = actual_value == expected_value
                        else:
                            ok = expected_value.lower() in actual_value.lower()
                        strategy, found = None, True
                        err = None if ok else f"validate_url: expected URL to {match_mode} {expected_value!r}, actual URL is {actual_value!r}"
                        print(f"[validate_url] expected({match_mode})={expected_value!r} actual={actual_value!r}: {'PASS' if ok else 'FAIL'}")

                    elif action_type == "validate_value":
                        lp = step.get("locator_profile") or {}
                        expected_value = step.get("value") or ""
                        match_mode = (step.get("match_mode") or "exact").strip().lower()
                        el, strategy, _attempt = _resolve_with_timeout(page, lp)
                        if el is None:
                            found, ok, err = False, False, "validate_value: element not found"
                        else:
                            found = True
                            try:
                                actual_value = _extract_element_value(el) or ""
                            except Exception:
                                actual_value = ""
                            if match_mode == "contains":
                                ok = expected_value.strip().lower() in actual_value.lower()
                            else:
                                ok = actual_value.strip() == expected_value.strip()
                            err = None if ok else f"validate_value: expected {expected_value!r}, got {actual_value!r}"
                            print(f"[validate_value] expected={expected_value!r} actual={actual_value!r} mode={match_mode}: {'PASS' if ok else 'FAIL'}")

                    elif action_type == "validate_enabled":
                        lp = step.get("locator_profile") or {}
                        expected_state = (step.get("expected_state") or "enabled").strip().lower()
                        expected_value = expected_state
                        el, strategy, _attempt = _resolve_with_timeout(page, lp)
                        if el is None:
                            found, ok, err = False, False, "validate_enabled: element not found"
                        else:
                            found = True
                            try:
                                is_disabled = el.is_disabled()
                            except Exception:
                                is_disabled = False
                            actual_value = "disabled" if is_disabled else "enabled"
                            ok = (actual_value == expected_state)
                            err = None if ok else f"validate_enabled: element is {actual_value}, expected {expected_state}"
                            print(f"[validate_enabled] expected={expected_state} actual={actual_value}: {'PASS' if ok else 'FAIL'}")

                    elif action_type == "count_elements":
                        # Counts how many matching elements exist on the
                        # current page and stores the count under
                        # `count_as` for later use by compare_counts or
                        # count_summary. Optionally validates the count
                        # equals `expected_count`.
                        lp = step.get("locator_profile") or {}
                        count_label = (step.get("count_as") or "").strip()
                        expected_count = step.get("expected_count")  # None = don't validate count
                        _settle(page)
                        _scroll_reveal_full_page(page)
                        try:
                            count = 0
                            # resolve selector using available locator hints
                            if lp.get("css_path"):
                                count = page.locator(lp["css_path"]).count()
                            elif lp.get("xpath"):
                                count = page.locator(lp["xpath"]).count()
                            elif lp.get("text"):
                                count = page.get_by_text(lp["text"], exact=False).count()
                            elif lp.get("role"):
                                count = page.get_by_role(lp["role"]).count()
                            else:
                                count = 0

                            print(f"[count_elements] Found {count} element(s) matching selector")
                            if count_label:
                                counted_values[count_label] = count
                                count_summary_data[count_label] = count
                                print(f"  → stored as '{count_label}'")

                            if expected_count is not None:
                                ok = (count == int(expected_count))
                                if ok:
                                    print(f"  → count matches expected ({expected_count}) ✓")
                                else:
                                    print(f"  → count mismatch: expected {expected_count}, got {count} ✗")
                                err = None if ok else f"count_elements: expected {expected_count} elements, found {count}"
                            else:
                                ok = True
                                err = None
                            strategy, found = None, True
                        except Exception as ce:
                            strategy, found, ok, err = None, False, False, str(ce)

                    elif action_type == "compare_counts":
                        # Compares two previously stored counts.
                        # operator: "eq" (==), "lt" (<), "gt" (>),
                        #           "lte" (<=), "gte" (>=), "ne" (!=)
                        count_a_label = (step.get("count_a") or "").strip()
                        count_b_label = (step.get("count_b") or "").strip()
                        operator = (step.get("operator") or "eq").strip().lower()
                        try:
                            if count_a_label not in counted_values:
                                strategy, found, ok, err = None, False, False, f"compare_counts: no count stored under '{count_a_label}'"
                            elif count_b_label not in counted_values:
                                strategy, found, ok, err = None, False, False, f"compare_counts: no count stored under '{count_b_label}'"
                            else:
                                a = counted_values[count_a_label]
                                b = counted_values[count_b_label]
                                ops = {
                                    "eq":  a == b,
                                    "lt":  a <  b,
                                    "gt":  a >  b,
                                    "lte": a <= b,
                                    "gte": a >= b,
                                    "ne":  a != b,
                                }
                                ok = ops.get(operator, False)
                                print(f"[compare_counts] {count_a_label}={a} {operator} {count_b_label}={b} → {'PASS' if ok else 'FAIL'}")
                                strategy, found = None, True
                                err = None if ok else f"compare_counts: {a} {operator} {b} is False"
                        except Exception as cce:
                            strategy, found, ok, err = None, False, False, str(cce)

                    elif action_type == "count_summary":
                        # Prints a formatted summary of all counts
                        # collected so far. Optionally filters to only
                        # the labels listed in `labels`; if empty/absent,
                        # prints ALL stored counts. Always succeeds.
                        summary_labels = step.get("labels") or []
                        try:
                            to_show = (
                                {k: count_summary_data[k] for k in summary_labels if k in count_summary_data}
                                if summary_labels
                                else dict(count_summary_data)
                            )
                            print("=" * 40)
                            print("=== COUNT SUMMARY ===")
                            if to_show:
                                for lbl, cnt in to_show.items():
                                    print(f"  {lbl:<30}: {cnt}")
                            else:
                                print("  (no counts recorded yet)")
                            print("=" * 40)
                            strategy, found, ok, err = None, True, True, None
                        except Exception as se:
                            strategy, found, ok, err = None, False, False, str(se)

                    elif action_type == "check_checked":
                        # Verifies whether a checkbox or radio button (native or custom <div>/<span>) is
                        # currently checked or unchecked.
                        # expected_state: "checked" (default) or "unchecked"
                        lp = step.get("locator_profile") or {}
                        attrs = lp.get("attributes") or {}
                        expected_state = (step.get("expected_state") or "checked").strip().lower()
                        _settle(page)
                        try:
                            el = None
                            for selector_fn in [
                                lambda: page.locator(f"#{lp['id']}").first if lp.get("id") else None,
                                lambda: page.locator(f"[name='{attrs.get('name')}']").first if attrs.get("name") else None,
                                lambda: page.get_by_label(lp["text"]).first if lp.get("text") else None,
                                lambda: page.get_by_text(lp["text"]).first if lp.get("text") else None,
                                lambda: page.locator(f"text={lp['text']}").first if lp.get("text") else None,
                                lambda: page.locator(lp["css_path"]).first if lp.get("css_path") else None,
                                lambda: page.locator(lp["xpath"]).first if lp.get("xpath") else None,
                                lambda: page.get_by_role("checkbox").first if lp.get("role") == "checkbox" else None,
                                lambda: page.get_by_role("radio").first if lp.get("role") == "radio" else None,
                            ]:
                                try:
                                    candidate = selector_fn()
                                    if candidate and candidate.count() > 0:
                                        el = candidate
                                        break
                                except Exception:
                                    pass

                            if el is None:
                                strategy, found, ok, err = None, False, False, "check_checked: element not found"
                            else:
                                is_checked = False
                                # Try native input detection first (child, parent, or self)
                                try:
                                    if el.evaluate("e => e.tagName === 'INPUT'"):
                                        is_checked = el.is_checked()
                                    else:
                                        child_in = el.locator("input").first
                                        if child_in and child_in.count() > 0:
                                            is_checked = child_in.is_checked()
                                        else:
                                            try:
                                                is_checked = el.is_checked()
                                            except Exception:
                                                is_checked = False
                                except Exception:
                                    is_checked = False

                                if not is_checked:
                                    # Custom visual element (<div> / <span>) detection
                                    try:
                                        is_checked = el.evaluate("""e => {
                                            if (e.getAttribute('aria-checked') === 'true' || e.getAttribute('data-checked') === 'true') return true;
                                            if (e.getAttribute('aria-checked') === 'false' || e.getAttribute('data-checked') === 'false') return false;
                                            const cls = (e.className || '').toString().toLowerCase();
                                            if (cls.includes('checked') || cls.includes('active') || cls.includes('selected')) return true;
                                            if (e.querySelector('svg, i[class*="check"], [class*="check"], [class*="tick"], [class*="active"]')) return true;
                                            if (e.querySelector('[style*="ionicons"]')) return true;
                                            if (e.children.length > 0) return true;
                                            return false;
                                        }""")
                                    except Exception:
                                        is_checked = False

                                if expected_state == "checked":
                                    ok = is_checked
                                elif expected_state == "unchecked":
                                    ok = not is_checked
                                else:
                                    ok = False
                                print(f"[check_checked] Element is {'checked' if is_checked else 'unchecked'} → expected '{expected_state}': {'PASS' if ok else 'FAIL'}")
                                strategy, found = None, True
                                err = None if ok else f"check_checked: element is {'checked' if is_checked else 'unchecked'}, expected {expected_state}"
                        except Exception as cke:
                            strategy, found, ok, err = None, False, False, str(cke)

                    elif action_type == "validate_value_range":
                        # Reads a numeric value from an element and
                        # checks it is within [min_value, max_value].
                        # Either bound is optional (omit to skip that
                        # side of the check). Strips non-numeric chars
                        # (currency symbols, commas) before parsing.
                        lp = step.get("locator_profile") or {}
                        min_value = step.get("min_value")  # None = no lower bound
                        max_value = step.get("max_value")  # None = no upper bound
                        _settle(page)
                        try:
                            el = None
                            for selector_fn in [
                                lambda: page.locator(lp["css_path"]).first if lp.get("css_path") else None,
                                lambda: page.locator(lp["xpath"]).first if lp.get("xpath") else None,
                                lambda: page.get_by_text(lp["text"], exact=False).first if lp.get("text") else None,
                            ]:
                                try:
                                    candidate = selector_fn()
                                    if candidate and candidate.count() > 0:
                                        el = candidate
                                        break
                                except Exception:
                                    pass

                            if el is None:
                                strategy, found, ok, err = None, False, False, "validate_value_range: element not found"
                            else:
                                raw_text = (el.inner_text() or "").strip()
                                # strip currency symbols, commas, spaces
                                import re as _re
                                numeric_str = _re.sub(r"[^\d.\-]", "", raw_text)
                                if not numeric_str:
                                    strategy, found, ok, err = None, True, False, f"validate_value_range: could not parse numeric value from {raw_text!r}"
                                else:
                                    numeric_val = float(numeric_str)
                                    in_range = True
                                    if min_value is not None and numeric_val < float(min_value):
                                        in_range = False
                                    if max_value is not None and numeric_val > float(max_value):
                                        in_range = False
                                    bounds = f"[{min_value if min_value is not None else '-∞'}, {max_value if max_value is not None else '+∞'}]"
                                    print(f"[validate_value_range] Value={numeric_val}, Range={bounds} → {'PASS' if in_range else 'FAIL'}")
                                    strategy, found, ok = None, True, in_range
                                    err = None if in_range else f"validate_value_range: {numeric_val} not in range {bounds}"
                        except Exception as vre:
                            strategy, found, ok, err = None, False, False, str(vre)

                    elif action_type == "detect_duplicates":
                        # Collects the text (or attribute) of all matching
                        # elements and checks for duplicates.
                        # detect_by: "text" (default) or an attribute name.
                        # success=True when NO duplicates are found.
                        lp = step.get("locator_profile") or {}
                        detect_by = (step.get("detect_by") or "text").strip().lower()
                        _settle(page)
                        _scroll_reveal_full_page(page)
                        try:
                            els = None
                            if lp.get("css_path"):
                                els = page.locator(lp["css_path"])
                            elif lp.get("xpath"):
                                els = page.locator(lp["xpath"])
                            elif lp.get("role"):
                                els = page.get_by_role(lp["role"])
                            else:
                                strategy, found, ok, err = None, False, False, "detect_duplicates: no usable selector in locator_profile"
                                els = None

                            if els is not None:
                                total = els.count()
                                values = []
                                for idx in range(total):
                                    try:
                                        el = els.nth(idx)
                                        if detect_by == "text":
                                            val = (el.inner_text() or "").strip()
                                        else:
                                            val = (el.get_attribute(detect_by) or "").strip()
                                        if val:
                                            values.append(val)
                                    except Exception:
                                        pass

                                seen = set()
                                duplicates = []
                                for v in values:
                                    if v in seen:
                                        duplicates.append(v)
                                    seen.add(v)

                                print(f"[detect_duplicates] Scanned {total} element(s), {len(duplicates)} duplicate(s) found")
                                if duplicates:
                                    for dup in duplicates:
                                        print(f"  DUPLICATE: {dup!r}")
                                ok = len(duplicates) == 0
                                strategy, found = None, True
                                err = None if ok else f"detect_duplicates: found {len(duplicates)} duplicate(s): {duplicates}"
                        except Exception as dde:
                            strategy, found, ok, err = None, False, False, str(dde)

                    elif action_type == "capture_list":
                        # Collects the text (or attribute) of ALL matching
                        # elements into a list and stores it under
                        # `capture_as` for later use by
                        # compare_list_overlap. detect_by: "text" (default)
                        # or an attribute name - same convention as
                        # detect_duplicates.
                        lp = step.get("locator_profile") or {}
                        label_name = (step.get("capture_as") or "").strip()
                        detect_by = (step.get("detect_by") or "text").strip().lower()
                        _settle(page)
                        _scroll_reveal_full_page(page)
                        try:
                            els = None
                            if lp.get("css_path"):
                                els = page.locator(lp["css_path"])
                            elif lp.get("xpath"):
                                els = page.locator(lp["xpath"])
                            elif lp.get("role"):
                                els = page.get_by_role(lp["role"])
                            else:
                                strategy, found, ok, err = None, False, False, "capture_list: no usable selector in locator_profile"
                                els = None

                            if els is not None:
                                total = els.count()
                                values = []
                                for idx in range(total):
                                    try:
                                        el = els.nth(idx)
                                        if detect_by == "text":
                                            val = (el.inner_text() or "").strip()
                                        else:
                                            val = (el.get_attribute(detect_by) or "").strip()
                                        if val:
                                            values.append(val)
                                    except Exception:
                                        pass

                                print(f"[capture_list] Captured {len(values)} value(s) under '{label_name}'")
                                if label_name:
                                    captured_lists[label_name] = values
                                ok = True
                                strategy, found = None, True
                                err = None
                        except Exception as cle:
                            strategy, found, ok, err = None, False, False, str(cle)

                    elif action_type == "compare_list_overlap":
                        # Captures a fresh ("after") list the same way
                        # capture_list does, then compares it against a
                        # previously captured ("before") list stored under
                        # `compare_to`, storing the overlap count under
                        # `count_as` in counted_values/count_summary_data -
                        # the same dicts count_elements already writes to,
                        # so compare_counts/count_summary can use it too.
                        lp = step.get("locator_profile") or {}
                        compare_to_label = (step.get("compare_to") or "").strip()
                        count_label = (step.get("count_as") or "").strip()
                        detect_by = (step.get("detect_by") or "text").strip().lower()
                        _settle(page)
                        _scroll_reveal_full_page(page)
                        try:
                            if compare_to_label not in captured_lists:
                                strategy, found, ok, err = None, False, False, f"compare_list_overlap: no list captured under '{compare_to_label}'"
                            else:
                                els = None
                                if lp.get("css_path"):
                                    els = page.locator(lp["css_path"])
                                elif lp.get("xpath"):
                                    els = page.locator(lp["xpath"])
                                elif lp.get("role"):
                                    els = page.get_by_role(lp["role"])
                                else:
                                    strategy, found, ok, err = None, False, False, "compare_list_overlap: no usable selector in locator_profile"
                                    els = None

                                if els is not None:
                                    total = els.count()
                                    after_list = []
                                    for idx in range(total):
                                        try:
                                            el = els.nth(idx)
                                            if detect_by == "text":
                                                val = (el.inner_text() or "").strip()
                                            else:
                                                val = (el.get_attribute(detect_by) or "").strip()
                                            if val:
                                                after_list.append(val)
                                        except Exception:
                                            pass

                                    before_list = captured_lists[compare_to_label]
                                    overlap_count = sum(1 for item in after_list if item in before_list)

                                    print(f"[compare_list_overlap] {overlap_count} of {len(after_list)} item(s) matched the '{compare_to_label}' list")
                                    if count_label:
                                        counted_values[count_label] = overlap_count
                                        count_summary_data[count_label] = overlap_count
                                        print(f"  → stored as '{count_label}'")

                                    ok = True
                                    strategy, found = None, True
                                    err = None
                        except Exception as cloe:
                            strategy, found, ok, err = None, False, False, str(cloe)

                    elif action_type == "__validate_xpath__":
                        # Internal-only probe used by the Recording Editor's
                        # Add Action dialog (see app.py's validate_locator) to
                        # check a candidate xpath against the REAL page state
                        # a replay would actually produce up to this point -
                        # never a real recorded action, never shown to users,
                        # never persisted into any real recording. Always
                        # succeeds (it's a probe, not an assertion) - the
                        # caller only cares about the match count.
                        #
                        # document.evaluate(...) directly, via page.evaluate()
                        # - the same method DevTools' console xpath helper
                        # uses - rather than Playwright's own locator/XPath
                        # abstraction, so a
                        # candidate independently confirmed "1 of 1" in
                        # DevTools can never disagree with this check due to
                        # an evaluation-method mismatch.
                        lp = step.get("locator_profile") or {}
                        probe_xpath = lp.get("xpath") or ""
                        _settle(page)
                        try:
                            match_count = page.evaluate(
                                """(xp) => {
                                    try {
                                        return document.evaluate(
                                            xp, document, null,
                                            XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null
                                        ).snapshotLength;
                                    } catch (e) {
                                        return -1;
                                    }
                                }""",
                                probe_xpath,
                            )
                        except Exception:
                            match_count = -1
                        if match_count < 0:
                            match_count = 0

                        # same storage pattern count_elements already uses
                        # for its own count - kept for consistency with how
                        # every other counting action type in this file
                        # works, though nothing else in THIS run reads it
                        # back (see strategy_used below for how the caller
                        # actually gets the count)
                        counted_values["__validate_xpath__"] = match_count
                        count_summary_data["__validate_xpath__"] = match_count
                        print(f"[__validate_xpath__] {match_count} element(s) matched")

                        # strategy_used is repurposed here to carry the match
                        # count back out through this step's own, already-
                        # serialized report entry - this internal action has
                        # no natural "strategy" of its own, and no existing
                        # per-step report field holds a count, so this is the
                        # narrowest way to expose it without changing the
                        # shared step-record shape every other action type
                        # also writes into
                        strategy = str(match_count)
                        found = match_count >= 1
                        ok = True
                        err = None

                    else:
                        # pre-click visibility snapshot: for a click the
                        # RECORDING shows is immediately followed by a
                        # navigate INTO a modal-like sub-state (a fragment
                        # being added), captures whether the modal-interior
                        # target (the step after that navigate) is ALREADY
                        # visible right now, BEFORE this click fires - a
                        # real, working modal transitions its content from
                        # invisible/absent to visible as a DIRECT result of
                        # THIS specific interaction, while a stale/
                        # coincidental id match (an unrelated, ordinary page
                        # element that just happens to share that id) is
                        # already sitting there regardless of whether this
                        # click does anything at all. Purely a snapshot here
                        # - see the effect-verification block further down
                        # for how it's actually used, alongside (not instead
                        # of) the structural role/dialog check, so neither
                        # signal alone has to carry every real-world case.
                        pre_click_inner_target_visible = None
                        # companion snapshot for the NO-recorded-navigate
                        # safety net further down (the "modal-no-navigate-
                        # check" block, see its own comment) - same idea as
                        # pre_click_inner_target_visible just above, but for
                        # whatever the VERY NEXT recorded step's own target
                        # is (not the step after an intervening navigate,
                        # since there isn't one on this path). Without this,
                        # that safety net always had to treat "already open,
                        # unchanged by this click" the same as "stale
                        # leftover from a preceding action" (both show no
                        # fresh DOM mutation after this click - see
                        # _confirmed()'s freshness gate) - wrongly failing
                        # an ordinary follow-up interaction (e.g. clicking a
                        # field that's already visible inside a dialog THIS
                        # SAME click sequence already opened one or more
                        # steps ago, just to focus it before typing) exactly
                        # as if the dialog had never opened at all.
                        pre_click_no_nav_target_visible = None
                        # set only when this step's own click is actually
                        # about to be armed/dispatched below - stays None
                        # otherwise (not a NAV_CAUSING_ACTIONS step, no
                        # entering-substate navigate right after it, or no
                        # locator on whatever that navigate's own next step
                        # targets), so _wait_for_modal_target_visible's own
                        # click_dispatched_at falls back to its internal
                        # "verification started" reference point instead of
                        # a fabricated dispatch time
                        _original_click_t0 = None
                        # TEMPORARY DEBUG - default so the _debug_pause_if_
                        # quantity kwarg at both _wait_for_modal_target_
                        # visible call sites below never NameErrors when
                        # arming didn't run this step; remove alongside the
                        # rest of the temporary debug-pause wiring
                        _click_target_desc = None
                        if action_type in NAV_CAUSING_ACTIONS:
                            _next_step_peek = STEPS[i] if i < len(STEPS) else None
                            if _next_step_peek and _next_step_peek.get("action_type") == "navigate":
                                _peek_target_url = to_qa_url(_next_step_peek.get("page_url"), qa_url)
                                try:
                                    _before_frag_peek = urlsplit(url_before or "").fragment
                                    _target_frag_peek = urlsplit(_peek_target_url or "").fragment
                                    _entering_peek = (
                                        bool(_peek_target_url)
                                        and not _urls_same_target(url_before, _peek_target_url)
                                        and bool(_target_frag_peek)
                                        and _target_frag_peek != _before_frag_peek
                                    )
                                except Exception:
                                    _entering_peek = False
                                if _entering_peek:
                                    _inner_peek = STEPS[i + 1] if (i + 1) < len(STEPS) else None
                                    _inner_peek_lp = (_inner_peek or {}).get("locator_profile") or {}
                                    if _inner_peek_lp:
                                        try:
                                            _peek_el = _resolve_element(page, _inner_peek_lp)
                                            pre_click_inner_target_visible = bool(
                                                _peek_el is not None and _peek_el.is_visible()
                                            )
                                        except Exception:
                                            pre_click_inner_target_visible = None

                            # arms the modal-timing freshness marker (see
                            # _arm_modal_mutation_tracker) right before THIS
                            # click fires below, whenever the very next
                            # recorded step carries a locator at all - not
                            # only when the recording ALSO shows an
                            # intervening navigate (the _entering_peek case
                            # above). A modal-opening click's own navigate can
                            # go missing from the recording for reasons that
                            # have nothing to do with whether a modal
                            # actually opened (see the no-recorded-navigate
                            # safety net further down this function, and
                            # recorder/record_session.py's
                            # _commit_pending_navigate) - arming here
                            # unconditionally means that safety net's own
                            # _wait_for_modal_target_visible call still gets a
                            # real click-dispatch reference and a real
                            # freshness marker to check against, exactly like
                            # the recorded-navigate case does. Cheap
                            # (one JS evaluate) and side-effect-free for any
                            # step that turns out to have nothing to do with
                            # a modal - _wait_for_modal_target_visible is
                            # only ever actually invoked once something
                            # AFTER the click structurally looks like a
                            # dialog.
                            # BUGFIX: the actual verification TARGET is
                            # STEPS[i+1] when the next step is a recorded
                            # navigate (the navigate itself always carries
                            # locator_profile=null - it's not clickable, it's
                            # a page transition), and _next_step_peek itself
                            # otherwise (the no-recorded-navigate safety-net
                            # case, where _next_step_peek IS the check/click
                            # step to be verified). Checking _next_step_peek's
                            # own locator_profile unconditionally (as an
                            # earlier version of this block did) meant this
                            # never armed at all for the ordinary recorded-
                            # navigate path, since that locator_profile is
                            # always null - silently dropping the click-
                            # dispatch reference/freshness-marker for exactly
                            # the common case.
                            _arm_target_lp = {}
                            if _next_step_peek:
                                if _next_step_peek.get("action_type") == "navigate":
                                    _peek_after_nav = STEPS[i + 1] if (i + 1) < len(STEPS) else None
                                    _arm_target_lp = (_peek_after_nav or {}).get("locator_profile") or {}
                                else:
                                    _arm_target_lp = _next_step_peek.get("locator_profile") or {}
                                    # snapshot BEFORE this click fires - see
                                    # pre_click_no_nav_target_visible's own
                                    # comment above for why this is needed
                                    if _arm_target_lp:
                                        try:
                                            _no_nav_peek_el = _resolve_element(page, _arm_target_lp)
                                            pre_click_no_nav_target_visible = bool(
                                                _no_nav_peek_el is not None and _no_nav_peek_el.is_visible()
                                            )
                                        except Exception:
                                            pre_click_no_nav_target_visible = None
                            if _arm_target_lp:
                                _armed_at = _arm_modal_mutation_tracker(page)
                                _original_click_t0 = time.monotonic()
                                if _armed_at is not None:
                                    print(f"[modal-timing] armed modal-open tracker at {_armed_at:.1f}ms (page clock) before this click")
                                _click_target_desc = (
                                    step.get("locator_profile") or {}
                                ).get("element_text") or (step.get("locator_profile") or {}).get("text") or "target"
                                print(f"[modal-timing-detail] click dispatched on {_click_target_desc!r} at t=0ms (reference point for this flow)")

                        # see _arm_modal_interaction_timing's own docstring -
                        # this is the generic per-step dispatch point every
                        # non-navigate action goes through, so it's also
                        # where a PRIOR successful modal-open verification's
                        # own timing context (if this happens to be the exact
                        # step it was armed for) gets consumed and logged
                        _maybe_log_modal_interaction_timing(page, step)
                        if _consume_force_interacted(page, step):
                            # see _MODAL_FORCE_INTERACTED_STEPS's own
                            # comment: _wait_for_modal_target_visible's own
                            # force-interact fallback already dispatched a
                            # native JS click on THIS exact step's target
                            # while it was still verifying the modal one
                            # step early - clicking it again here via the
                            # normal path would risk toggling a non-native,
                            # single-select control back off (see _resolve_
                            # and_act_with_retry's own check-vs-click
                            # comment on why "check" steps always click
                            # regardless of apparent current state), undoing
                            # what was already done. Reported as a real,
                            # distinct strategy (not silently merged into an
                            # ordinary "click"/"check" result) so anyone
                            # reading the report can see this step's success
                            # came from the force-interact fallback, not a
                            # normal, visually-confirmed interaction.
                            strategy, found, ok, err = "force-interact (already dispatched)", True, True, None
                            print(
                                "[force-interact] this step's target was already force-clicked "
                                "during the preceding modal-open verification - not re-clicking it"
                            )
                        else:
                            try:
                                strategy, found, ok, err = _resolve_and_act_with_retry(
                                    page, step,
                                    prev_action_type=prev_action_type,
                                    fast_fail=this_step_fast_fail,
                                )
                                if this_step_fast_fail and not ok:
                                    print(
                                        "[fast-fail] previous navigate's destination "
                                        "target never appeared - this step failed fast "
                                        "without the settle/scroll retry escalation"
                                    )
                            except Exception as e:
                                # one bad step shouldn't blank out the rest of the run
                                strategy, found, ok, err = None, False, False, str(e)
                                logger.error("step %d raised unexpectedly: %s", i, e)

                        if ok and action_type in NAV_CAUSING_ACTIONS:
                            # TEMPORARY DEBUG PRINT - confirms this code path
                            # (and therefore the current template) is
                            # actually the one executing during replay.
                            # Safe/easy to delete once confirmed - unrelated
                            # to the verification logic itself, which starts
                            # right below.
                            print(f"EFFECT VERIFICATION CODE RUNNING (step {i}, action_type={action_type!r})")
                            # effect verification: a locator resolving and a
                            # click executing without a Playwright exception
                            # is NOT the same thing as the click having
                            # actually produced its real, recorded effect -
                            # an element can be "found" and "clicked" (via a
                            # weak fallback tier, say) while the genuine
                            # target was obscured, mid-transition, or simply
                            # the wrong one, and Playwright's own click()
                            # still reports success regardless. Generic,
                            # reusing only what the RECORDING itself already
                            # shows: if this exact action was immediately
                            # followed, when it was recorded, by a "navigate"
                            # to a different URL, that recorded pairing is
                            # real evidence the ORIGINAL action genuinely
                            # caused that URL to be reached - so replay
                            # should too. Never a hardcoded text/site check;
                            # works for any click-then-navigate pair, on any
                            # site. Bounded, not open-ended: this either
                            # confirms or fails within EFFECT_VERIFY_TIMEOUT_S,
                            # it never introduces an unbounded wait.
                            next_step_for_effect = STEPS[i] if i < len(STEPS) else None
                            if next_step_for_effect and next_step_for_effect.get("action_type") == "navigate":
                                expected_effect_url = to_qa_url(next_step_for_effect.get("page_url"), qa_url)
                                if expected_effect_url and not _urls_same_target(url_before, expected_effect_url):
                                    # TEMPORARY DEBUG PRINT - confirms the
                                    # click-then-navigate pairing was
                                    # actually detected for this step and the
                                    # URL-reached check is about to run
                                    print(f"EFFECT VERIFICATION CODE RUNNING - checking for {expected_effect_url!r}")
                                    # entering_substate/inner_target_step
                                    # describe what the RECORDING itself
                                    # shows (a fragment being added on the
                                    # expected navigate target) - that is
                                    # known up front, independent of whether
                                    # the click actually achieves it during
                                    # replay, so it is computed here, before
                                    # the URL-reached wait below, rather than
                                    # only inside the "URL was reached"
                                    # branch.
                                    try:
                                        _before_fragment = urlsplit(url_before).fragment
                                        _target_fragment = urlsplit(expected_effect_url).fragment
                                    except Exception:
                                        _before_fragment, _target_fragment = None, None
                                    entering_substate = bool(_target_fragment) and _target_fragment != _before_fragment
                                    inner_target_step = STEPS[i + 1] if (i + 1) < len(STEPS) else None
                                    # ==================================
                                    # UNCONDITIONAL diagnostic - runs for
                                    # EVERY click entering a modal-like
                                    # sub-state, generically, not just
                                    # "quantity", and regardless of whether
                                    # the URL-reached check just below ends
                                    # up passing or failing - a click that
                                    # produces literally no reaction at all
                                    # (no URL change either, e.g. a
                                    # "black screen" no-op) must be captured
                                    # here too, not only successful ones, so
                                    # this call is placed BEFORE
                                    # _wait_for_effect_url rather than
                                    # inside its "succeeded" branch. Three
                                    # checkpoints at 0/300/800ms right after
                                    # the click, checking whether ANY
                                    # element on the page structurally looks
                                    # like an open dialog (see
                                    # _diagnose_modal_open_sequence), plus a
                                    # real screenshot and every DOM mutation
                                    # under body during that same window.
                                    # Purely additive - never affects
                                    # modal_ok/effect_verified below, which
                                    # still comes entirely from
                                    # _wait_for_effect_url and
                                    # _wait_for_modal_target_visible's own,
                                    # separate checks.
                                    if entering_substate and inner_target_step:
                                        _diag = _diagnose_modal_open_sequence(page, shot_dir=shot_dir)
                                        if _diag is not None:
                                            _cps = _diag.get("checkpoints") or {}
                                            _shots = _diag.get("screenshots") or {}
                                            print(
                                                f"[modal-open-diagnostic] checkpoints for this "
                                                f"click: 0ms={_cps.get('0ms')} "
                                                f"300ms={_cps.get('300ms')} "
                                                f"800ms={_cps.get('800ms')}"
                                            )
                                            print(
                                                f"[modal-open-diagnostic] screenshots: "
                                                f"0ms={_shots.get('0ms')} "
                                                f"300ms={_shots.get('300ms')} "
                                                f"800ms={_shots.get('800ms')}"
                                            )
                                            _present_vals = [v for v in _cps.values() if v is not None]
                                            if any(_present_vals) and not all(_present_vals):
                                                print(
                                                    "[modal-open-diagnostic] FLASH DETECTED - "
                                                    "the dialog was present at some checkpoints "
                                                    "but not others; the stability-recheck fix "
                                                    "below is what actually guards against this"
                                                )
                                            elif not any(_present_vals):
                                                _muts = _diag.get("mutations") or []
                                                print(
                                                    f"[modal-open-diagnostic] dialog never "
                                                    f"detected at any checkpoint - "
                                                    f"{len(_muts)} DOM mutation(s) under body "
                                                    f"in that window:"
                                                )
                                                for _m in _muts:
                                                    print(f"[modal-open-diagnostic]   {_m}")
                                    # ==================================
                                    # end of unconditional diagnostic block
                                    # ==================================
                                    effect_verified = _wait_for_effect_url(page, expected_effect_url)
                                    if effect_verified:
                                        logger.debug(
                                            "effect verified: reached %r after this %s",
                                            expected_effect_url, action_type,
                                        )
                                        # URL-reached is necessary but not
                                        # sufficient - a forced/hash-only
                                        # navigate lands on the right URL
                                        # regardless of whether the click's
                                        # own handler ever actually ran, so
                                        # a modal whose content never
                                        # mounted at all (no backdrop, page
                                        # pixel-identical to before the
                                        # click) would otherwise still read
                                        # as "verified". Generically checks
                                        # whatever the NEXT recorded action
                                        # after this navigate itself targets
                                        # (its own locator_profile - never a
                                        # hardcoded "modal"/"qty" check) is
                                        # genuinely visible on the live page
                                        # within a short, bounded window -
                                        # see _wait_for_modal_target_visible.
                                        # only meaningful when this navigate is
                                        # actually ENTERING a modal-like sub-
                                        # state, not leaving one - a fragment
                                        # being ADDED (".../cart" -> ".../cart
                                        # #modal") is the generic, structural
                                        # signal of "opening a sub-view", while
                                        # one being REMOVED or unchanged (a
                                        # modal's own "DONE"/close navigating
                                        # back to the base URL) means whatever
                                        # the NEXT recorded action targets is
                                        # just the next ordinary step in the
                                        # overall flow - not necessarily inside
                                        # any modal at all, so requiring it to
                                        # be would misfire on a perfectly normal
                                        # continuation (a completely unrelated
                                        # click on the main page, say).
                                        modal_ok, modal_reason = (
                                            _wait_for_modal_target_visible(
                                                page, inner_target_step,
                                                was_visible_before=pre_click_inner_target_visible,
                                                shot_dir=shot_dir,
                                                click_dispatched_at=_original_click_t0,
                                                # TEMPORARY DEBUG - see the
                                                # matching block inside
                                                # _wait_for_modal_target_visible
                                                # itself; remove this kwarg too
                                                # once that block is removed
                                                _debug_pause_if_quantity=("qty" in (_click_target_desc or "").lower()),
                                            )
                                            if entering_substate and inner_target_step else (True, None)
                                        )
                                        if not modal_ok:
                                            # generic retry: the click that
                                            # was SUPPOSED to open this modal
                                            # already fired once, but the
                                            # dialog never stably appeared -
                                            # rather than silently accepting
                                            # that and letting replay
                                            # continue on to later steps as
                                            # if the interaction succeeded,
                                            # one more attempt is made here,
                                            # re-resolving that SAME
                                            # recorded click's own element
                                            # fresh and looking for a
                                            # genuinely interactive
                                            # ancestor/descendant near it
                                            # (role="button"/onclick/
                                            # cursor:pointer - the same
                                            # _find_alternate_clickable
                                            # already used for the no-effect
                                            # click retry above) - the real
                                            # clickable hit-area is often a
                                            # different DOM node than the
                                            # one whose text got recorded.
                                            # Never site-specific: applies
                                            # to any click that was supposed
                                            # to open a modal and didn't,
                                            # whatever the target is.
                                            _retry_modal_ok, _retry_modal_reason = False, None
                                            # see _verify_modal_opened_or_retry's identical
                                            # check for why: a dialog that's already open
                                            # (backdrop/DONE button present, just the
                                            # specific content still loading async) must
                                            # NOT get its trigger re-clicked - that's almost
                                            # always a toggle, so the retry click below
                                            # would close the dialog instead of giving its
                                            # in-flight fetch more time, producing exactly
                                            # the empty-modal symptom this guard exists to
                                            # avoid.
                                            try:
                                                _dialog_already_open = bool(page.evaluate(_MODAL_DETECT_JS))
                                            except Exception:
                                                _dialog_already_open = False
                                            _orig_click_step = STEPS[i - 2] if i >= 2 else None
                                            if (
                                                not _dialog_already_open
                                                and _orig_click_step
                                                and _orig_click_step.get("action_type") in NAV_CAUSING_ACTIONS
                                            ):
                                                _orig_click_lp = _orig_click_step.get("locator_profile") or {}
                                                _orig_click_el = _resolve_element(page, _orig_click_lp)
                                                if _orig_click_el is not None:
                                                    _alt_modal_el = _find_alternate_clickable(_orig_click_el)
                                                    _retry_target_el = _alt_modal_el or _orig_click_el
                                                    print(
                                                        "[modal-retry] modal did not stably open after "
                                                        "the recorded click - retrying once on "
                                                        + ("an alternate ancestor/descendant element"
                                                           if _alt_modal_el is not None
                                                           else "the same recorded element")
                                                    )
                                                    try:
                                                        _arm_modal_mutation_tracker(page)
                                                        _retry_click_t0 = time.monotonic()
                                                        # trusted mouse move/down/up - see
                                                        # _trusted_mouse_click; falls back to
                                                        # an ordinary click only when no
                                                        # measurable bounding box exists
                                                        if _trusted_mouse_click(page, _retry_target_el):
                                                            print("[click-mechanism] TRUSTED MOUSE SEQUENCE used for this modal-retry click")
                                                        else:
                                                            _retry_target_el.click(timeout=3000)
                                                            print("[click-mechanism] standard click used for this modal-retry click (no measurable bounding box)")
                                                        _retry_modal_ok, _retry_modal_reason = _wait_for_modal_target_visible(
                                                            page, inner_target_step, shot_dir=shot_dir,
                                                            click_dispatched_at=_retry_click_t0,
                                                        )
                                                    except Exception as e_modal_retry:
                                                        _retry_modal_ok = False
                                                        _retry_modal_reason = str(e_modal_retry)
                                            if _retry_modal_ok:
                                                modal_ok = True
                                                effect_verified = True
                                                ok = True
                                                err = None
                                                print(
                                                    "[modal-retry] retry succeeded - dialog is now "
                                                    "stably visible, proceeding normally"
                                                )
                                                logger.debug(
                                                    "modal-content-check: retry succeeded after "
                                                    "initial click failed to open the modal"
                                                )
                                            else:
                                                effect_verified = False
                                                ok = False
                                                if _dialog_already_open:
                                                    err = (
                                                        f"{modal_reason} - a dialog is already open on "
                                                        "the page, so this is content that never "
                                                        "finished rendering inside it, not a click that "
                                                        "failed to open anything; not retrying the click "
                                                        "since that would only toggle the dialog closed"
                                                    )
                                                else:
                                                    err = modal_reason
                                                logger.debug(
                                                    "modal-content-check: URL %r reached but %s "
                                                    "(retry also failed: %s)",
                                                    expected_effect_url, modal_reason, _retry_modal_reason,
                                                )
                                                print(f"[modal-content-check] FAILED: {err}")
                                                # see _skip_deps_until_url's own
                                                # definition - subsequent steps that
                                                # depend on this modal being open are
                                                # never attempted against a page that
                                                # never actually got it
                                                _skip_deps_until_url = url_before
                                                if _orig_click_step and not _dialog_already_open:
                                                    print(
                                                        "[modal-retry] retry did not open the modal "
                                                        "either - marking this step FAILED rather than "
                                                        "silently continuing to later steps"
                                                    )
                                        else:
                                            # extends the check above from "did
                                            # we reach the modal" to "did the
                                            # whole modal interaction actually
                                            # stick" - scans forward past the
                                            # navigate step already found for a
                                            # recorded "check" step's own value,
                                            # stopping at whichever comes first:
                                            # that check, or a navigate step
                                            # that already closes the sequence
                                            # back to url_before with no check
                                            # in it (not this pattern). Only
                                            # queued up when a genuine value was
                                            # found - the final-state check
                                            # itself runs later, on whichever
                                            # step actually returns to
                                            # url_before (see further down the
                                            # loop).
                                            modal_check_value = _find_modal_check_value(STEPS, i, url_before)
                                            if modal_check_value:
                                                pending_modal_verification = {
                                                    "trigger_lp": step.get("locator_profile") or {},
                                                    "intended_value": modal_check_value,
                                                    "close_url": url_before,
                                                }
                                                logger.debug(
                                                    "modal-sequence-verify: queued - expecting %r "
                                                    "once the sequence returns to %r",
                                                    modal_check_value, url_before,
                                                )
                                    else:
                                        ok = False
                                        err = (
                                            f"click executed but its expected effect was not "
                                            f"observed - the recording shows this step "
                                            f"immediately followed by a navigate to "
                                            f"{expected_effect_url!r}, but the page never "
                                            f"reached it within {EFFECT_VERIFY_TIMEOUT_S:.0f}s "
                                            f"(still at {page.url!r})"
                                        )
                                        logger.debug(
                                            "effect NOT verified: expected %r, still at %r",
                                            expected_effect_url, page.url,
                                        )
                            elif next_step_for_effect:
                                # SAFETY NET: the recording did NOT capture a
                                # navigate step between this click and the
                                # very next recorded action - normally the
                                # signal this file uses to know a click opened
                                # a fragment-based modal sub-state (see the
                                # navigate branch just above). That signal can
                                # go missing even for a click that genuinely
                                # DOES open a modal: the recorder's own click-
                                # caused-this-navigate dedup (see recorder/
                                # record_session.py's _commit_pending_navigate)
                                # decides whether to KEEP that navigate based
                                # on wall-clock timing of an unrelated LATER
                                # event, not on whether a modal actually
                                # opened - so the exact same click, recorded
                                # twice, can end up with or without its
                                # navigate purely by scheduling luck. Relying
                                # SOLELY on "the recording has a navigate
                                # here" would then silently skip paint-
                                # verification for a modal that genuinely
                                # opened, letting the very next step (a size/
                                # quantity/etc. selection) interact with
                                # content nobody ever saw rendered - the exact
                                # silent-wrong-value bug this whole file
                                # exists to prevent for the case where the
                                # navigate WAS recorded.
                                #
                                # Structural, not timing-based, so it never
                                # fires for an ordinary click-then-click
                                # sequence that has nothing to do with any
                                # modal (the common case): after the click
                                # already fired above, check whether the very
                                # next recorded step's own target resolves to
                                # an element sitting inside something that
                                # structurally looks like an open dialog
                                # (_element_has_modal_ancestor - role=
                                # "dialog"/aria-modal/fixed-overlay, the SAME
                                # generic signal _wait_for_modal_target_
                                # visible's own _confirmed() already falls
                                # back to). A plain, already-on-page element
                                # with no such ancestor makes this a fast,
                                # cheap no-op; only a target that's actually
                                # inside a dialog-shaped container triggers
                                # the real (bounded, 6s) paint-verification
                                # wait. No retry-click here (unlike the
                                # navigate branch above) - the click already
                                # executed without error, so re-clicking would
                                # risk toggling an already-open dialog closed
                                # rather than giving it more time to render.
                                _no_nav_next_lp = next_step_for_effect.get("locator_profile") or {}
                                if _no_nav_next_lp:
                                    try:
                                        _no_nav_next_el = _resolve_element(page, _no_nav_next_lp)
                                        _no_nav_next_in_modal = bool(
                                            _no_nav_next_el is not None
                                            and _element_has_modal_ancestor(_no_nav_next_el)
                                        )
                                    except Exception:
                                        _no_nav_next_in_modal = False
                                    if _no_nav_next_in_modal:
                                        print(
                                            "[modal-no-navigate-check] next step's own target sits "
                                            "inside a dialog-like container even though no navigate "
                                            "was recorded between this click and it - verifying the "
                                            "modal genuinely painted before letting that step run"
                                        )
                                        _no_nav_modal_ok, _no_nav_modal_reason = _wait_for_modal_target_visible(
                                            page, next_step_for_effect,
                                            was_visible_before=pre_click_no_nav_target_visible,
                                            shot_dir=shot_dir,
                                            click_dispatched_at=_original_click_t0,
                                            # TEMPORARY DEBUG - see the
                                            # matching block inside
                                            # _wait_for_modal_target_visible
                                            # itself; remove this kwarg too
                                            # once that block is removed
                                            _debug_pause_if_quantity=("qty" in (_click_target_desc or "").lower()),
                                        )
                                        if not _no_nav_modal_ok:
                                            effect_verified = False
                                            ok = False
                                            err = _no_nav_modal_reason
                                            print(f"[modal-no-navigate-check] FAILED: {err}")
                                            # same generic skip-guard the
                                            # recorded-navigate path uses -
                                            # the very next step (the one
                                            # just checked) depends on this
                                            # modal being open and must not
                                            # run against a page that never
                                            # genuinely got it
                                            _skip_deps_until_url = url_before
                                        else:
                                            effect_verified = True

                            # captured BEFORE settling, so a visible
                            # transitional state (a submit button going
                            # into a loading/disabled state, etc.) has a
                            # chance to be caught in its own image - the
                            # dedup check in _capture_screenshot means a
                            # transition too fast to render anything
                            # different here just gets skipped, and the
                            # step's own post-settle screenshot below
                            # ends up being the only (and correct) one
                            if not has_explicit_screenshots:
                                _capture_screenshot(page, shot_dir, img_counter, last_state, last_shot_bytes, step=step)
                            _settle(page)
                            # _settle() only waits for network activity to
                            # quiet down - a result the app renders purely
                            # client-side (a validation/error message, a
                            # success state) with no accompanying network
                            # request wouldn't be waited for at all
                            # otherwise, so the step's screenshot below
                            # could still catch a pre-result frame. Same
                            # short, generic wait used elsewhere in this
                            # file for exactly this kind of DOM-settling
                            # purpose (see _validate_product's scroll
                            # loop) - not tied to any specific site or
                            # outcome.
                            try:
                                page.wait_for_timeout(300)
                            except Exception:
                                pass

                            # networkidle+300ms is a generic timing proxy,
                            # not proof the destination actually finished
                            # rendering - an SPA route change this click
                            # triggered can still be waiting on its own
                            # data fetch (an events listing, a form
                            # template) well after the network itself goes
                            # quiet. This does NOT affect the click's own
                            # success/failure (ok/strategy/err above are
                            # already decided) - it only delays the
                            # milestone screenshot below until the next
                            # recorded step's target is actually findable,
                            # the same readiness signal the navigate branch
                            # already relies on, so a milestone image never
                            # captures a still-loading page just because
                            # this wasn't a recorded "navigate" step.
                            #
                            # Gated on the URL actually having changed:
                            # most clicks in a real flow (a checkbox, an
                            # expanding dropdown, a size/gender picker)
                            # interact with the SAME page and never
                            # navigate anywhere - for those the "next
                            # step's target" often isn't meant to appear
                            # from THIS click at all (it may need a
                            # further click first), so waiting the full
                            # window here would just burn up to 9s per
                            # such click for no benefit. A real navigation
                            # is cheaply, generically detectable first: a
                            # different URL after settling.
                            try:
                                url_changed = page.url != url_before
                            except Exception:
                                url_changed = False
                            if url_changed:
                                next_step_for_shot = STEPS[i] if i < len(STEPS) else None
                                next_lp_for_shot = (next_step_for_shot or {}).get("locator_profile") or {}
                                if next_lp_for_shot:
                                    _wait_for_next_step_ready(page, next_step_for_shot)

                # modal-sequence final-state verification: the click-then-
                # navigate effect check above only confirms the FIRST
                # transition (reaching the modal URL) - it says nothing
                # about whether whatever happened INSIDE the modal
                # (a "check" step selecting some value) actually stuck
                # once the sequence closes back to where it started. Set
                # by that same effect-verification block, below, when it
                # detects this exact recorded shape (click -> navigate to
                # a modal-like URL -> ... -> a "check" step with a
                # recorded value -> ... -> navigate BACK to the original
                # URL) - consumed here, on whichever LATER step is the
                # navigate that actually returns to that original URL,
                # regardless of how many steps are in between. Re-
                # resolves the ORIGINAL trigger element (its own recorded
                # locator_profile - the same one the "click" step itself
                # used) and compares its CURRENT displayed value against
                # the value that was selected inside the modal - the
                # real, final-state check this exists for, not just "did
                # navigation happen". Never hardcodes what the value
                # means (quantity, size, color, ...) - it's read straight
                # from whatever the recording's own "check" step
                # captured.
                if pending_modal_verification and action_type == "navigate" and ok:
                    pmv = pending_modal_verification
                    try:
                        sequence_closed = _urls_same_target(page.url, pmv["close_url"])
                    except Exception:
                        sequence_closed = False
                    if sequence_closed:
                        trigger_el = _resolve_element(page, pmv["trigger_lp"])
                        final_value = _extract_element_value(trigger_el) if trigger_el is not None else None
                        intended = pmv["intended_value"]
                        if final_value and intended and intended.lower() in final_value.lower():
                            effect_verified = True
                            logger.debug(
                                "modal-sequence-verify: confirmed - final value %r "
                                "reflects selected %r", final_value, intended,
                            )
                        else:
                            effect_verified = False
                            ok = False
                            err = (
                                f"modal sequence completed (navigated back to "
                                f"{pmv['close_url']!r}) but the on-page value does not "
                                f"reflect the selected {intended!r} - currently "
                                f"{final_value!r}"
                            )
                            print(f"[modal-sequence-verify] WARNING: {err}")
                        pending_modal_verification = None

                duration = time.monotonic() - step_start

                if action_type == "navigate":
                    failed_since_last_navigate = not ok
                elif not ok:
                    failed_since_last_navigate = True

                try:
                    url_after = page.url
                except Exception:
                    url_after = None

                # every recorded action still gets its own screenshot
                # ATTEMPT here, no exceptions, positioned after any
                # settling the action-type-specific handling above did -
                # _capture_screenshot skips the SAVE (leaving shot_str
                # None, same as a failed capture) only when this state is
                # a near-duplicate of the last screenshot actually saved,
                # e.g. a fill whose value didn't visibly change from the
                # prior step's already-typed state, or a click whose
                # transitional capture above already caught this same
                # settled state
                url_changed = (url_after != url_before) if (url_after and url_before) else False
                if validate_shot_override:
                    shot_str = validate_shot_override
                elif _should_take_step_screenshot(step, ok, action_type, url_changed, has_explicit_screenshots):
                    shot_str = _capture_screenshot(page, shot_dir, img_counter, last_state, last_shot_bytes, step=step, run_dir=run_dir, stage_counter=stage_counter)
                else:
                    shot_str = None

                logger.debug("step %d (%s): strategy=%s found=%s success=%s", i, action_type, strategy, found, ok)

                # locator_report is purely a human-readable translation of
                # strategy/found/duration (all already computed above by
                # this step's own existing handling, whatever action type
                # it is) - see _describe_locator_resolution's own
                # docstring. None for a step with no recorded target at
                # all (a window-level scroll, a navigate, tab_* actions) -
                # there's nothing to report a resolution for. Computed
                # here (before the print block below) so the same plain-
                # English message can be printed to the terminal too, not
                # just stored in the report.
                if step.get("locator_profile"):
                    locator_report = _describe_locator_resolution(
                        _element_report_label(step), strategy, found, ok,
                        resolution_ms=round(duration * 1000) if found else None,
                    )
                else:
                    locator_report = None

                if ok:
                    print("STATUS: SUCCESS")
                    print(f"Done ({duration:.2f}s).")
                    if locator_report:
                        print(locator_report["message"])
                else:
                    # the plain print() is the real user-facing failure
                    # message (see AUTOFLOW_DEBUG for the fuller
                    # strategy/step trace)
                    logger.debug("step %d (%s) failed: %s", i, action_type, err)
                    print("STATUS: FAILED")
                    print(f"Reason: {err}")
                    print(f"Current URL: {url_after or url_before}")
                    if locator_report:
                        print(locator_report["message"])
                    if action_type not in ("navigate", "scroll", "validate"):
                        print("Locator attempts:")
                        for line in _locator_attempts(step):
                            print(f"  {line}")
                    if shot_str:
                        print(f"Screenshot: {shot_str}")
                if action_type == "validate":
                    # closes the distinct [VALIDATION] block opened in
                    # _print_step_header, so the whole thing - header
                    # through STATUS/Done - is visually bracketed and
                    # easy to spot scrolling past a long terminal log
                    print("=" * 50)
                if nav_warning:
                    print(f"WARNING: {nav_warning}")
                print()

                result["steps"].append({
                    "index": i,
                    "action_type": action_type,
                    "strategy_used": strategy,
                    "element_found": found,
                    "success": ok,
                    "error": err,
                    "warning": nav_warning,
                    "effect_verified": effect_verified,
                    "large_bbox_flag": large_bbox_flag,
                    "screenshot": shot_str,
                    "url_before": url_before,
                    "url_after": url_after,
                    "duration": round(duration, 3),
                    "locator_report": locator_report,
                    "expected": expected_value,
                    "actual": actual_value,
                })

                # incremental persistence: writes result (with its steps
                # list so far, and total_steps set up front) to
                # output_json_path after EVERY step, not just at the end -
                # a dashboard polling that same path mid-run (see Live
                # Replay Progress) can then show real step-by-step
                # progress. Cheap (report.json is small) and safe: this is
                # the exact same _write_result() the end-of-run/error
                # paths already call, just called more often, and nothing
                # downstream cares whether report.json was written once or
                # many times - only its final content once the run ends.
                _write_result(result, output_json_path)

                if stop_replay_after_step:
                    print(
                        "Halting replay - click_if_exists did not find/click "
                        "its target; no further actions will run."
                    )
                    print()
                    raise _StopReplay()

            except _StopReplay:
                break

            except Exception as fatal_e:
                logger.error("step %d crashed the replay loop: %s", i, fatal_e)
                print("STATUS: FAILED")
                print(f"Reason: replay could not continue - {fatal_e}")
                print()
                result["steps"].append({
                    "index": i,
                    "action_type": action_type,
                    "strategy_used": None,
                    "element_found": False,
                    "success": False,
                    "error": f"replay could not continue: {fatal_e}",
                    "warning": None,
                    "effect_verified": None,
                    "large_bbox_flag": False,
                    "screenshot": None,
                    "url_before": None,
                    "url_after": None,
                    "duration": 0,
                    "locator_report": None,
                    "expected": None,
                    "actual": None,
                })
                _write_result(result, output_json_path)
                # an unhandled crash IN ONE STEP's own handling doesn't
                # necessarily mean the browser/page itself is unusable -
                # only stop the whole replay when nothing further could
                # possibly succeed. Reused, not reinvented: the exact same
                # browser.is_connected() check used elsewhere in this file
                # (see the final browser.close() below), and the exact
                # same _get_valid_open_page() helper already used right
                # after this loop to find any still-open tab - it already
                # checks every registered page, not just whichever one
                # this step happened to be on, so a step that crashed
                # because ITS tab closed while another tab is still open
                # correctly continues too.
                try:
                    browser_alive = browser.is_connected()
                except Exception:
                    browser_alive = False
                if browser_alive and _get_valid_open_page(pages, preferred=page) is not None:
                    continue
                break

        # guarantee exactly one result entry per recorded action - if the
        # loop above broke early (the page/browser died), every action
        # after that point is explicitly recorded as NOT EXECUTED rather
        # than just missing, so a truncated run can never be mistaken for
        # a complete one just because everything THAT DID RUN succeeded
        executed_indexes = {s["index"] for s in result["steps"]}
        for i, step in enumerate(STEPS, start=1):
            if i not in executed_indexes:
                result["steps"].append({
                    "index": i,
                    "action_type": step.get("action_type"),
                    "strategy_used": None,
                    "element_found": False,
                    "success": False,
                    "error": "not executed - replay stopped before reaching this action",
                    "warning": None,
                    "effect_verified": None,
                    "large_bbox_flag": False,
                    "screenshot": None,
                    "url_before": None,
                    "url_after": None,
                    "duration": 0,
                    "locator_report": None,
                    "expected": None,
                    "actual": None,
                })
        result["steps"].sort(key=lambda s: s["index"])

        # the loop's own `page` variable can be pointing at an already-
        # closed Page here (e.g. the last recorded action was a tab_close
        # that closed exactly that page) - resolve a genuinely open page
        # from the runtime registry before touching anything else, rather
        # than assume `page` is still usable
        final_page = _get_valid_open_page(pages, preferred=page)

        if final_page is not None:
            try:
                result["final_url"] = final_page.url
                result["final_text"] = final_page.inner_text("body")
            except Exception as e:
                logger.warning("couldn't read final page state: %s", e)

            final_shot = _capture_screenshot(final_page, shot_dir, img_counter, last_state, last_shot_bytes, full_page=True)
            if final_shot:
                result["final_screenshot"] = final_shot
        else:
            logger.info("no open page remained at replay end - skipping final URL/screenshot capture")

        page = final_page

        if product_name and product_name.strip() and page is not None:
            pname = product_name.strip()
            # SCOPED FIX: "Product to Verify" is a dashboard input field,
            # completely independent of what the RECORDING itself
            # contains - filling it used to run _validate_product's own
            # scroll-and-scan unconditionally, even for a recording with
            # no validate/compare_value/count_elements/detect_duplicates/
            # capture_list/compare_list_overlap action anywhere in it, at
            # which point a manual user would never scroll at all. Gating
            # on whether the recording actually contains one of those six
            # action types makes replay match manual browsing for a
            # recording that doesn't use this feature, while leaving it
            # running exactly as before for one that does - never based
            # on any site-specific detail, purely the recorded action_type
            # values already in STEPS.
            _validation_family_action_types = {
                "validate", "compare_value", "count_elements",
                "detect_duplicates", "capture_list", "compare_list_overlap",
            }
            _recording_has_validation_action = any(
                s.get("action_type") in _validation_family_action_types for s in STEPS
            )
            if not _recording_has_validation_action:
                print(
                    '[product-validation] "Product to Verify" was set but this '
                    "recording contains no validation-family action (validate/"
                    "compare_value/count_elements/detect_duplicates/capture_list/"
                    "compare_list_overlap) - skipping the end-of-run product-search "
                    "scroll/scan; manual browsing of this recorded flow never does "
                    "this either"
                )
            else:
                print("PRODUCT SEARCH VALIDATION")
                print("")
                print("Requested Product:")
                print(pname)
                print("")
                try:
                    pv = _validate_product(page, pname, shot_dir, img_counter, last_state, last_shot_bytes)
                except Exception as e:
                    logger.error("product validation crashed: %s", e)
                    try:
                        cur_url = page.url
                    except Exception:
                        cur_url = None
                    pv = {
                        "status": "FAIL", "product": pname, "found": False,
                        "match_type": None, "position": None, "page": 1,
                        "title": None, "url": None, "screenshot": None,
                        "reason": f"product validation crashed: {e}",
                        "checked_count": 0, "search_url": cur_url,
                    }
                result["product_validation"] = pv
                if pv.get("found"):
                    print("PASS")
                    print("Product is found")
                    print(f"Position: Result {pv.get('position')}")
                else:
                    print("FAIL")
                    print("Product is not found")
                    print("Checked complete available results")
        elif product_name and product_name.strip():
            result["product_validation"] = {
                "status": "FAIL", "product": product_name.strip(), "found": False,
                "match_type": None, "position": None, "page": None,
                "title": None, "url": None, "screenshot": None,
                "reason": "no open page remained at replay end - could not validate",
                "checked_count": 0, "search_url": None,
            }

        # status/message/report are all finalized and written BEFORE the
        # close delay and browser.close() below - nothing about the
        # result depends on the browser still being open past this point.
        # result["steps"] is guaranteed (by the backfill above) to have
        # exactly one entry per recorded action, so these counts can never
        # under-report a run that was cut short.
        NOT_EXECUTED_MSG = "not executed - replay stopped before reaching this action"
        recorded_count = total_steps
        not_executed_steps = [s for s in result["steps"] if s["error"] == NOT_EXECUTED_MSG]
        attempted_count = recorded_count - len(not_executed_steps)
        successful_actions = sum(1 for s in result["steps"] if s["success"])
        failed_actions = attempted_count - successful_actions
        not_executed_count = len(not_executed_steps)

        # PASS requires every single recorded action to have both been
        # attempted AND succeeded - a truncated run (anything left
        # NOT EXECUTED) or any individual failure both force FAIL
        steps_ok = not_executed_count == 0 and failed_actions == 0
        result["status"] = "PASS" if steps_ok else "FAIL"
        if not_executed_count:
            result["message"] = f"replay stopped early - {not_executed_count} action(s) never executed"
        elif failed_actions:
            result["message"] = "one or more steps failed"
        else:
            result["message"] = "all steps resolved"

        total_duration_s = time.monotonic() - replay_start
        result["total_duration_s"] = round(total_duration_s, 3)

        _write_result(result, output_json_path)

        print("=" * 50)
        print("REPLAY COMPLETED")
        print("=" * 50)
        print()
        print(f"Recorded: {recorded_count}")
        print(f"JSON: {recorded_count}")
        print(f"Generated: {recorded_count}")
        print(f"Executed: {attempted_count}")
        print(f"Successful: {successful_actions}")
        print(f"Failed: {failed_actions}")
        print(f"Total replay time: {total_duration_s:.2f}s")
        if not_executed_count:
            first_missed = not_executed_steps[0]["index"]
            last_missed = not_executed_steps[-1]["index"]
            print(f"Not executed: {first_missed}-{last_missed} ({not_executed_count} action(s))")
        else:
            print("Not executed: 0")
        print()
        print(f"RESULT: {result['status']}")
        print()
        print("Final URL:")
        print(result.get("final_url"))
        print()
        print("Screenshots:")
        print(str(run_dir))
        print()
        print("Generated Script:")
        print(str(Path(__file__).resolve()))
        print()
        # everything that needs the page/browser (final_url, final
        # screenshot, product validation, report) is already captured and
        # written above - this is purely a "let it sit on screen for a
        # moment" pause before the ONE close() call below, not a
        # per-action delay. `page` may already be closed at this point (a
        # recorded tab_close, possibly the very last action, can close
        # exactly the page this variable was last pointing at) - calling
        # wait_for_timeout (or anything else) on a closed Page raises
        # TargetClosedError, so re-check for a genuinely open page rather
        # than trust `page`/`final_page` are still valid this much later.
        close_delay_page = _get_valid_open_page(pages, preferred=page)

        if close_delay_page is not None:
            print(f"Browser will remain open for {DEFAULT_CLOSE_DELAY} seconds...")
            try:
                close_delay_page.wait_for_timeout(DEFAULT_CLOSE_DELAY * 1000)
            except Exception as e:
                logger.info("close-delay wait skipped - page became unavailable: %s", e)
        else:
            print("No open page remained - skipping the close delay.")

        try:
            if browser.is_connected():
                browser.close()
                print("Browser closed successfully.")
            else:
                print("Browser was already closed.")
        except Exception as e:
            logger.info("browser.close() raised (already closing/closed): %s", e)
            print("Browser was already closed.")
        print("=" * 50)

        try:
            for child in sorted(run_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
                if child.is_dir() and not any(child.iterdir()):
                    try:
                        child.rmdir()
                    except Exception:
                        pass
        except Exception:
            pass

    return result


def _write_result(result, output_json_path):
    if output_json_path:
        Path(output_json_path).write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else PROD_URL
    if target and not target.startswith(("http://", "https://")):
        target = "https://" + target
    out_json = sys.argv[2] if len(sys.argv) > 2 else None
    out_shots = sys.argv[3] if len(sys.argv) > 3 else None
    # headed (visible) by default when you run this file yourself, so you
    # can actually watch the replay - pass "1" as a 4th argument to run it
    # headless instead (that's what the dashboard's automated QA runs use)
    headless_arg = sys.argv[4] if len(sys.argv) > 4 else "0"
    product_arg = sys.argv[5] if len(sys.argv) > 5 else ""
    run(target, out_json, out_shots, headless=(headless_arg == "1"), product_name=product_arg)
