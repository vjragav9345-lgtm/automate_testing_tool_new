"""
Auto-generated from recording: session_20260818_145158
Generated at: 2026-08-18T14:51:58.446232
Original recorded (production) URL: https://www.flipkart.com/

Resolution order per step: data-testid -> data-test -> data-cy -> id -> name
-> aria-label -> placeholder -> role -> css_path -> xpath -> text+tag ->
bounding box click. Dropdowns use page.select_option(), form submits use
form.requestSubmit(), meaningful keypresses (Enter/Tab/Escape) use el.press(),
double/right clicks use el.dblclick()/el.click(button="right"), scrolling
uses page.mouse.wheel().

Prints simple progress/result messages only - no internal strategy/step
logs. Set AUTOFLOW_DEBUG=1 to also see which locator strategy was used for
every step.

Run directly with: python session_20260818_145158_script.py [qa_url] [output_json_path] [screenshot_dir] [headless] [product_name]
qa_url defaults to the recorded starting URL if omitted. Running the file
directly launches a VISIBLE (headed) browser so you can watch the replay;
pass "1" as the 4th argument to run headless instead. An optional 5th
argument validates that a product appears on whatever page the recorded
actions end on - no separate search, no re-opening the site.
"""
import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from playwright.sync_api import sync_playwright

# quiet unless AUTOFLOW_DEBUG=1 - this is a replay script, not a report, so
# by default it should just perform the recorded actions and stay silent
# unless something actually fails
_DEBUG = os.environ.get("AUTOFLOW_DEBUG") == "1"
logging.basicConfig(level=logging.DEBUG if _DEBUG else logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

STEPS = [   {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'css_path': 'body > div:nth-of-type(5) > div > span',
                               'xpath': '/html[1]/body[1]/div[5]/div[1]/span[1]',
                               'text': '✕',
                               'tag': 'span',
                               'attributes': {'role': 'button'}},
        'bounding_box': {   'x': 988.8500366210938,
                            'y': 96,
                            'width': 26.149999618530273,
                            'height': 32},
        'page_url': 'https://www.flipkart.com/',
        'delta_x': None,
        'delta_y': None,
        'timestamp': '2026-08-18T09:20:53.627Z',
        'new_tab': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'css_path': 'div#container > div > div > div > div > div > div > '
                                           'div > div > div > div > div > div > div > div > '
                                           'div:nth-of-type(2) > div > div > div > div > div > '
                                           'header > div > div > form > div > div > input',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/header[1]/div[1]/div[1]/form[1]/div[1]/div[1]/input[1]',
                               'text': '',
                               'tag': 'input',
                               'attributes': {   'type': 'text',
                                                 'title': 'Search for Products, Brands and More',
                                                 'placeholder': 'Search for Products, Brands and '
                                                                'More',
                                                 'name': 'q'}},
        'bounding_box': {'x': 105.5999984741211, 'y': 78, 'width': 821.9625244140625, 'height': 40},
        'page_url': 'https://www.flipkart.com/',
        'delta_x': None,
        'delta_y': None,
        'timestamp': '2026-08-18T09:20:54.945Z',
        'new_tab': None},
    {   'action_type': 'fill',
        'value': 'vivo x300',
        'locator_profile': {   'id': None,
                               'css_path': 'div#container > div > div > div > div > div > div > '
                                           'div > div > div > div > div > div > div > div > '
                                           'div:nth-of-type(2) > div > div > div > div > div > '
                                           'header > div > div > form > div > div > input',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/header[1]/div[1]/div[1]/form[1]/div[1]/div[1]/input[1]',
                               'text': 'vivo x300',
                               'tag': 'input',
                               'attributes': {   'type': 'text',
                                                 'title': 'Search for Products, Brands and More',
                                                 'placeholder': 'Search for Products, Brands and '
                                                                'More',
                                                 'name': 'q'}},
        'bounding_box': {'x': 105.5999984741211, 'y': 78, 'width': 821.9625244140625, 'height': 40},
        'page_url': 'https://www.flipkart.com/',
        'delta_x': None,
        'delta_y': None,
        'timestamp': '2026-08-18T09:21:07.720Z',
        'new_tab': None},
    {   'action_type': 'press',
        'value': 'Enter',
        'locator_profile': {   'id': None,
                               'css_path': 'div#container > div > div > div > div > div > div > '
                                           'div > div > div > div > div > div > div > div > '
                                           'div:nth-of-type(2) > div > div > div > div > div > '
                                           'header > div > div > form > div > div > input',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/header[1]/div[1]/div[1]/form[1]/div[1]/div[1]/input[1]',
                               'text': 'vivo x300',
                               'tag': 'input',
                               'attributes': {   'type': 'text',
                                                 'title': 'Search for Products, Brands and More',
                                                 'placeholder': 'Search for Products, Brands and '
                                                                'More',
                                                 'name': 'q'}},
        'bounding_box': {'x': 105.5999984741211, 'y': 78, 'width': 821.9625244140625, 'height': 40},
        'page_url': 'https://www.flipkart.com/',
        'delta_x': None,
        'delta_y': None,
        'timestamp': '2026-08-18T09:21:07.721Z',
        'new_tab': None},
    {   'action_type': 'scroll',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.flipkart.com/search?q=vivo%20x300&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off',
        'delta_x': 0,
        'delta_y': 265,
        'timestamp': '2026-08-18T09:21:11.264Z',
        'new_tab': None},
    {   'action_type': 'scroll',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.flipkart.com/search?q=vivo%20x300&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off',
        'delta_x': 0,
        'delta_y': 549,
        'timestamp': '2026-08-18T09:21:12.293Z',
        'new_tab': None},
    {   'action_type': 'navigate',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.flipkart.com/search?q=vivo%20x300&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off',
        'delta_x': None,
        'delta_y': None,
        'timestamp': '2026-08-18T09:21:13.235Z',
        'new_tab': None},
    {   'action_type': 'scroll',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.flipkart.com/search?q=vivo%20x300&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off',
        'delta_x': 0,
        'delta_y': 197,
        'timestamp': '2026-08-18T09:21:13.989Z',
        'new_tab': None},
    {   'action_type': 'scroll',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.flipkart.com/search?q=vivo%20x300&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off',
        'delta_x': 0,
        'delta_y': -120,
        'timestamp': '2026-08-18T09:21:15.398Z',
        'new_tab': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'css_path': 'div#container > div > div:nth-of-type(3) > div > '
                                           'div:nth-of-type(2) > div:nth-of-type(4) > div > div > '
                                           'div > a > div:nth-of-type(2) > div > '
                                           'div:nth-of-type(3) > ul > li:nth-of-type(5)',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[3]/div[1]/div[2]/div[4]/div[1]/div[1]/div[1]/a[1]/div[2]/div[1]/div[3]/ul[1]/li[5]',
                               'text': 'Dimensity 9500 Processor',
                               'tag': 'li',
                               'attributes': {}},
        'bounding_box': {'x': 537, 'y': 225.4375, 'width': 418.9250183105469, 'height': 22},
        'page_url': 'https://www.flipkart.com/search?q=vivo%20x300&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off',
        'delta_x': None,
        'delta_y': None,
        'timestamp': '2026-08-18T09:21:17.148Z',
        'new_tab': None},
    {   'action_type': 'navigate',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.flipkart.com/vivo-x300-pro-dune-gold-512-gb/p/itmb73a83ccc00e3?pid=MOBHHZBCNHJVGGCD&lid=LSTMOBHHZBCNHJVGGCDPWXQCF&marketplace=FLIPKART&q=vivo+x300&store=tyy%2F4io&srno=s_1_3&otracker=search&otracker1=search&fm=organic&iid=45c9a908-651d-4be1-b93d-9d07308d0650.MOBHHZBCNHJVGGCD.SEARCH&ppt=None&ppn=None&ssid=e8p3b8wc2o0000001787044869128&qH=5448b696df0184c9&ov_redirect=true',
        'delta_x': None,
        'delta_y': None,
        'timestamp': '2026-08-18T09:21:18.790Z',
        'new_tab': True},
    {   'action_type': 'scroll',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.flipkart.com/search?q=vivo%20x300&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off',
        'delta_x': 0,
        'delta_y': 459,
        'timestamp': '2026-08-18T09:21:47.662Z',
        'new_tab': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'css_path': 'div#container > div > div:nth-of-type(3) > div > div > '
                                           'div > div > div > section:nth-of-type(19) > '
                                           'div:nth-of-type(2) > div > div > div > label',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[3]/div[1]/div[1]/div[1]/div[1]/div[1]/section[19]/div[2]/div[1]/div[1]/div[1]/label[1]',
                               'text': 'vivo',
                               'tag': 'label',
                               'attributes': {}},
        'bounding_box': {'x': 24, 'y': 405, 'width': 238, 'height': 25.600000381469727},
        'page_url': 'https://www.flipkart.com/search?q=vivo%20x300&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off',
        'delta_x': None,
        'delta_y': None,
        'timestamp': '2026-08-18T09:21:48.334Z',
        'new_tab': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'css_path': 'div#container > div > div:nth-of-type(3) > div > div > '
                                           'div > div > div > section:nth-of-type(3) > '
                                           'div:nth-of-type(2) > div > div > div > label > div',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[3]/div[1]/div[1]/div[1]/div[1]/div[1]/section[3]/div[2]/div[1]/div[1]/div[1]/label[1]/div[1]',
                               'text': '',
                               'tag': 'div',
                               'attributes': {}},
        'bounding_box': {'x': 24, 'y': 423.7749938964844, 'width': 14, 'height': 14},
        'page_url': 'https://www.flipkart.com/search?q=vivo+x300&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off&p%5B%5D=facets.brand%255B%255D%3Dvivo',
        'delta_x': None,
        'delta_y': None,
        'timestamp': '2026-08-18T09:21:50.177Z',
        'new_tab': None},
    {   'action_type': 'scroll',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.flipkart.com/search?q=vivo+x300&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off&p%5B%5D=facets.brand%255B%255D%3Dvivo&p%5B%5D=facets.ram%255B%255D%3D8%2BGB%2Band%2BAbove',
        'delta_x': 0,
        'delta_y': 210,
        'timestamp': '2026-08-18T09:21:54.315Z',
        'new_tab': None},
    {   'action_type': 'navigate',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.flipkart.com/search?q=vivo+x300&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off&p%5B%5D=facets.brand%255B%255D%3Dvivo&p%5B%5D=facets.ram%255B%255D%3D8%2BGB%2Band%2BAbove',
        'delta_x': None,
        'delta_y': None,
        'timestamp': '2026-08-18T09:21:55.172Z',
        'new_tab': None},
    {   'action_type': 'scroll',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.flipkart.com/search?q=vivo+x300&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off&p%5B%5D=facets.brand%255B%255D%3Dvivo&p%5B%5D=facets.ram%255B%255D%3D8%2BGB%2Band%2BAbove',
        'delta_x': 0,
        'delta_y': 372,
        'timestamp': '2026-08-18T09:21:55.497Z',
        'new_tab': None},
    {   'action_type': 'scroll',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.flipkart.com/search?q=vivo+x300&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off&p%5B%5D=facets.brand%255B%255D%3Dvivo&p%5B%5D=facets.ram%255B%255D%3D8%2BGB%2Band%2BAbove',
        'delta_x': 0,
        'delta_y': 1530,
        'timestamp': '2026-08-18T09:21:56.551Z',
        'new_tab': None}]
PROD_URL = "https://www.flipkart.com/"

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


def _describe_step(step):
    """Best-effort human label + locator string for the per-action
    terminal log - mirrors the recorder's own [RECORDED] line style so
    replay output reads like a continuation of the recording's."""
    lp = step.get("locator_profile") or {}
    attrs = lp.get("attributes") or {}
    text = (lp.get("text") or "").strip()
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
        or attrs.get("aria-label")
        or attrs.get("placeholder")
        or lp.get("id")
        or lp.get("tag")
        or "(element)"
    )
    locator_display = (
        lp.get("id")
        or lp.get("css_path")
        or lp.get("xpath")
        or "(no stable locator found - will fall back to screen position)"
    )
    return label, locator_display


def _print_step_header(i, total, step):
    action_type = step.get("action_type")
    print("=" * 50)
    print(f"[{i}/{total}]")
    print(f"ACTION: {action_type}")
    if action_type == "navigate":
        print(f"URL: {step.get('page_url')}")
        if step.get("new_tab"):
            print("(recorded as a new tab/window - replayed in this same page)")
    elif action_type == "scroll":
        print(f"Delta: ({step.get('delta_x')}, {step.get('delta_y')})")
    elif action_type == "press":
        print(f"Key: {step.get('value')}")
    elif action_type in ("click", "dblclick", "right_click", "submit", "fill", "select"):
        label, locator_display = _describe_step(step)
        print(f"Element: {label}")
        print(f"Locator: {locator_display}")
        if action_type in ("fill", "select"):
            print(f"Value: {step.get('value')}")
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


def resolve_and_act(page, step):
    """Try each locator strategy in priority order, then perform the step's
    action. Strongest/most stable signals first (test-automation attributes,
    id, other stable attributes), generic/fragile ones last.

    Returns (strategy_used, element_found, success, error_message).
    element_found is True for any real locator hit (everything except the
    bounding-box fallback, which still lets the step succeed but does NOT
    count as "found" for UI element validation purposes.
    """
    lp = step.get("locator_profile") or {}
    attrs = lp.get("attributes") or {}
    action_type = step.get("action_type")
    value = step.get("value")
    el = None
    strategy = None

    # 1-3: test-automation attributes - purpose-built to be stable locators
    for attr in ("data-testid", "data-test", "data-cy"):
        if el is None:
            el = _by_attr(page, attr, attrs.get(attr))
            if el is not None:
                strategy = attr

    # 4: unique id
    if el is None and lp.get("id"):
        try:
            c = page.locator(lp["id"])
            if c.count() > 0:
                el, strategy = c.first, "id"
        except Exception:
            pass

    # 5-7: other attributes that are usually stable and human-meaningful
    for attr in ("name", "aria-label", "placeholder"):
        if el is None:
            el = _by_attr(page, attr, attrs.get(attr))
            if el is not None:
                strategy = attr

    # 8: accessibility role + accessible name
    if el is None and attrs.get("role"):
        try:
            c = page.get_by_role(attrs["role"], name=lp.get("text") or None)
            if c.count() > 0:
                el, strategy = c.first, "role"
        except Exception:
            pass

    # 9: generic stable css path (id/nth-of-type chain from when recorded)
    if el is None and lp.get("css_path"):
        try:
            c = page.locator(lp["css_path"])
            if c.count() > 0:
                el, strategy = c.first, "css_path"
        except Exception:
            pass

    # 10: xpath
    if el is None and lp.get("xpath"):
        try:
            c = page.locator("xpath=" + lp["xpath"])
            if c.count() > 0:
                el, strategy = c.first, "xpath"
        except Exception:
            pass

    # 11: visible text + tag
    if el is None and lp.get("text") and lp.get("tag"):
        try:
            c = page.locator(lp["tag"], has_text=lp["text"])
            if c.count() > 0:
                el, strategy = c.first, "text+tag"
        except Exception:
            pass

    # 11b: text only, no tag - a click-type action that has no recorded/
    # edited locator_profile at all (e.g. manually added in the Recording
    # Editor, or edited without touching Locator) still has its Value,
    # which for a click is normally the visible text of the link/button to
    # click. Value is never treated as the ONLY locator source when a real
    # locator_profile.text exists (that's tried first, above) - this only
    # kicks in when there's nothing else to go on.
    if (
        el is None
        and not lp.get("text")
        and value
        and action_type in ("click", "dblclick", "right_click")
    ):
        try:
            c = page.get_by_text(value, exact=True)
            if c.count() == 0:
                c = page.get_by_text(value)
            if c.count() > 0:
                el, strategy = c.first, "text+tag"
        except Exception:
            pass

    element_found = el is not None
    last_err = None

    if el is not None:
        try:
            el.scroll_into_view_if_needed(timeout=5000)
            if action_type == "click":
                el.click(timeout=5000)
            elif action_type == "dblclick":
                el.dblclick(timeout=5000)
            elif action_type == "right_click":
                el.click(timeout=5000, button="right")
            elif action_type == "fill" and value is not None:
                el.fill(value, timeout=5000)
            elif action_type == "select" and value is not None:
                el.select_option(value, timeout=5000)
            elif action_type == "submit":
                el.evaluate("f => f.requestSubmit ? f.requestSubmit() : f.submit()")
            elif action_type == "press" and value:
                el.press(value, timeout=5000)
            return strategy, element_found, True, None
        except Exception as e:
            # a recoverable hiccup, not a final failure yet - the bounding
            # box fallback below still gets a chance, and Playwright's own
            # exception text includes a full multi-line retry trace that's
            # only useful for debugging, not for a "did my replay work" run
            logger.debug("resolved via %s but action failed: %s", strategy, e)
            last_err = str(e)
    else:
        last_err = "none of the locator strategies (data-testid/data-test/data-cy/id/name/aria-label/placeholder/role/css_path/xpath/text+tag) matched an element"

    # bounding box is a last resort for click-type actions only - selects/
    # submits/keypresses need a real element to act on, a blind coordinate
    # click would just do the wrong thing
    box = step.get("bounding_box")
    if action_type in ("click", "dblclick", "right_click") and box and box.get("width") and box.get("height"):
        try:
            x = box["x"] + box["width"] / 2
            y = box["y"] + box["height"] / 2
            if action_type == "dblclick":
                page.mouse.dblclick(x, y)
            elif action_type == "right_click":
                page.mouse.click(x, y, button="right")
            else:
                page.mouse.click(x, y)
            return "bounding_box", element_found, True, None
        except Exception as e:
            return "bounding_box", element_found, False, f"coordinate click failed: {e}"

    return strategy, element_found, False, last_err


def _dismiss_dialog(dialog):
    logger.debug("dialog appeared (%s): %s - dismissing", dialog.type, dialog.message)
    dialog.dismiss()


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


def _replay_scroll(page, dx, dy):
    """Replay a recorded scroll gradually instead of one instant jump - a
    single page.mouse.wheel(dx, dy) call for a large accumulated delta
    would teleport the page instead of scrolling it the way the original
    action looked. Breaking it into smaller hops with brief pauses gets
    much closer to the real thing without needing to match its timing
    exactly.
    """
    total = max(abs(dx), abs(dy))
    steps = max(1, min(20, int(total / 120)))
    step_dx = dx / steps
    step_dy = dy / steps
    for _ in range(steps):
        page.mouse.wheel(step_dx, step_dy)
        page.wait_for_timeout(40)


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


def _validate_product(page, product_name, shot_dir):
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
                page.mouse.wheel(0, PRODUCT_SCROLL_STEP_PX)
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

    screenshot = None
    try:
        shot_path = Path(shot_dir) / "product_validation.png"
        page.screenshot(path=str(shot_path))
        screenshot = str(shot_path)
    except Exception:
        pass

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
    print("Starting replay...")
    result = {
        "status": "FAIL",
        "message": "",
        "qa_url": qa_url,
        "steps": [],
        "final_url": None,
        "final_screenshot": None,
        "final_text": None,
        "product_validation": None,
    }

    shot_dir = Path(screenshot_dir) if screenshot_dir else Path(__file__).resolve().parent / "run_screenshots"
    shot_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=headless)
        except Exception as e:
            # a headed launch can fail on a machine with no display (e.g. a
            # bare server) - headless still lets the replay actually run
            if not headless:
                logger.warning("headed launch failed (%s), falling back to headless", e)
                browser = p.chromium.launch(headless=True)
            else:
                raise
        print("Browser launched.")
        page = browser.new_page()
        page.set_default_timeout(8000)
        # cookie banners/alerts shouldn't be able to hang an unattended run
        page.on("dialog", _dismiss_dialog)

        try:
            page.goto(qa_url, wait_until="domcontentloaded", timeout=30000)
            _settle(page)
        except Exception as e:
            print(f"Replay failed - could not open {qa_url}:\n{e}")
            result["message"] = f"could not open QA URL: {e}"
            browser.close()
            _write_result(result, output_json_path)
            return result

        print("Executing recorded actions...")
        print()

        total_steps = len(STEPS)
        prev_timestamp = None
        # these are the action types that can plausibly trigger real
        # navigation (a link, a submit button, Enter in a form) - after
        # one of these succeeds, give any resulting page load a moment to
        # settle before the screenshot/next action, so both see the
        # RESULTING page rather than a mid-navigation snapshot. A click
        # that didn't navigate is already idle, so this resolves almost
        # immediately and doesn't add a meaningful delay to those.
        NAV_CAUSING_ACTIONS = ("click", "dblclick", "right_click", "submit", "press")

        for i, step in enumerate(STEPS, start=1):
            action_type = step.get("action_type")
            cur_timestamp = step.get("timestamp")

            _print_step_header(i, total_steps, step)

            if i > 1:
                delay = _replay_delay(prev_timestamp, cur_timestamp)
                if delay > 0:
                    print(f"(waiting {delay:.1f}s to match recorded pacing)")
                    page.wait_for_timeout(delay * 1000)

            prev_timestamp = cur_timestamp

            print("Executing...")

            try:
                url_before = page.url
            except Exception:
                url_before = None

            step_start = time.monotonic()

            if action_type == "navigate":
                target = to_qa_url(step.get("page_url"), qa_url)
                try:
                    page.goto(target, wait_until="domcontentloaded", timeout=30000)
                    _settle(page)
                    strategy, found, ok, err = None, True, True, None
                except Exception as e:
                    strategy, found, ok, err = None, True, False, str(e)
            elif action_type == "scroll":
                # no element involved - just replay the same mouse wheel
                # movement that was recorded, on the page as a whole
                try:
                    _replay_scroll(page, step.get("delta_x") or 0, step.get("delta_y") or 0)
                    strategy, found, ok, err = None, True, True, None
                except Exception as e:
                    strategy, found, ok, err = None, True, False, str(e)
            else:
                try:
                    strategy, found, ok, err = resolve_and_act(page, step)
                except Exception as e:
                    # one bad step shouldn't blank out the rest of the run
                    strategy, found, ok, err = None, False, False, str(e)
                    logger.error("step %d raised unexpectedly: %s", i, e)

                if ok and action_type in NAV_CAUSING_ACTIONS:
                    _settle(page)

            duration = time.monotonic() - step_start

            try:
                url_after = page.url
            except Exception:
                url_after = None

            # zero-padded index + action type - traceable to exactly which
            # step produced it, unlike a bare "step3.png"
            shot_path = shot_dir / f"{i:03d}_{action_type}.png"
            try:
                page.screenshot(path=str(shot_path))
                shot_str = str(shot_path)
            except Exception:
                shot_str = None

            logger.debug("step %d (%s): strategy=%s found=%s success=%s", i, action_type, strategy, found, ok)
            if ok:
                print(f"Done ({duration:.2f}s).")
            else:
                # the plain print() is the real user-facing failure message
                # (see AUTOFLOW_DEBUG for the fuller strategy/step trace)
                logger.debug("step %d (%s) failed: %s", i, action_type, err)
                print(f"Replay failed at action {i}:")
                print(err)
            print()

            result["steps"].append({
                "index": i,
                "action_type": action_type,
                "strategy_used": strategy,
                "element_found": found,
                "success": ok,
                "error": err,
                "screenshot": shot_str,
                "url_before": url_before,
                "url_after": url_after,
                "duration": round(duration, 3),
            })

        try:
            result["final_url"] = page.url
            result["final_text"] = page.inner_text("body")
        except Exception as e:
            logger.warning("couldn't read final page state: %s", e)

        final_shot = shot_dir / "final.png"
        try:
            page.screenshot(path=str(final_shot), full_page=True)
            result["final_screenshot"] = str(final_shot)
        except Exception as e:
            logger.warning("couldn't capture final screenshot: %s", e)

        if product_name and product_name.strip():
            pname = product_name.strip()
            print("PRODUCT SEARCH VALIDATION")
            print("")
            print("Requested Product:")
            print(pname)
            print("")
            try:
                pv = _validate_product(page, pname, shot_dir)
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

        # status/message/report are all finalized and written BEFORE the
        # close delay and browser.close() below - nothing about the
        # result depends on the browser still being open past this point
        steps_ok = all(s["success"] for s in result["steps"]) if result["steps"] else True
        result["status"] = "PASS" if steps_ok else "FAIL"
        result["message"] = "all steps resolved" if steps_ok else "one or more steps failed"

        _write_result(result, output_json_path)

        total_actions = len(result["steps"])
        successful_actions = sum(1 for s in result["steps"] if s["success"])
        failed_actions = total_actions - successful_actions

        print("=" * 50)
        print("REPLAY COMPLETED")
        print("=" * 50)
        print()
        print(f"Total Actions: {total_actions}")
        print()
        print(f"Successful Actions: {successful_actions}")
        print(f"Failed Actions: {failed_actions}")
        print()
        print("Final URL:")
        print(result.get("final_url"))
        print()
        print("Screenshots:")
        print(str(shot_dir))
        print()
        print("Generated Script:")
        print(str(Path(__file__).resolve()))
        print()
        print(f"Browser will remain open for {DEFAULT_CLOSE_DELAY} seconds...")

        # everything that needs the page/browser (final_url, final
        # screenshot, product validation, report) is already captured and
        # written above - this is purely a "let it sit on screen for a
        # moment" pause before the ONE close() call below, not a
        # per-action delay
        page.wait_for_timeout(DEFAULT_CLOSE_DELAY * 1000)

        browser.close()
        print("Browser closed successfully.")
        print("=" * 50)

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
