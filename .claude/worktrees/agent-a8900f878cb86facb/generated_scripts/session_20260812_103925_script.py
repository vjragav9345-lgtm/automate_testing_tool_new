"""
Auto-generated from recording: session_20260812_103925
Generated at: 2026-08-12T10:56:07.183318
Original recorded (production) URL: https://www.amazon.com/s?k=mouse&crid=PRMGGG3Q3MX0&sprefix=mouse%2Caps%2C329&ref=nb_sb_noss_1

Resolution order per step: data-testid -> data-test -> data-cy -> id -> name
-> aria-label -> placeholder -> role -> css_path -> xpath -> text+tag ->
bounding box click. Dropdowns use page.select_option(), form submits use
form.requestSubmit(), meaningful keypresses (Enter/Tab/Escape) use el.press(),
double/right clicks use el.dblclick()/el.click(button="right"), scrolling
uses page.mouse.wheel().

Prints simple progress/result messages only - no internal strategy/step
logs. Set AUTOFLOW_DEBUG=1 to also see which locator strategy was used for
every step.

Run directly with: python session_20260812_103925_script.py [qa_url] [output_json_path] [screenshot_dir] [headless]
qa_url defaults to the recorded starting URL if omitted. Running the file
directly launches a VISIBLE (headed) browser so you can watch the replay;
pass "1" as the 4th argument to run headless instead.
"""
import os
import sys
import json
import logging
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from playwright.sync_api import sync_playwright

# quiet unless AUTOFLOW_DEBUG=1 - this is a replay script, not a report, so
# by default it should just perform the recorded actions and stay silent
# unless something actually fails
_DEBUG = os.environ.get("AUTOFLOW_DEBUG") == "1"
logging.basicConfig(level=logging.DEBUG if _DEBUG else logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

STEPS = [   {   'action_type': 'scroll',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.amazon.com/s?k=mouse&crid=PRMGGG3Q3MX0&sprefix=mouse%2Caps%2C329&ref=nb_sb_noss_1',
        'delta_x': 0,
        'delta_y': 350},
    {   'action_type': 'scroll',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.amazon.com/s?k=mouse&crid=PRMGGG3Q3MX0&sprefix=mouse%2Caps%2C329&ref=nb_sb_noss_1',
        'delta_x': 0,
        'delta_y': 297},
    {   'action_type': 'scroll',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.amazon.com/s?k=mouse&crid=PRMGGG3Q3MX0&sprefix=mouse%2Caps%2C329&ref=nb_sb_noss_1',
        'delta_x': 0,
        'delta_y': 1969},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'css_path': 'span#a-autoid-9 > span > input',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/span[1]/div[1]/div[11]/div[1]/div[1]/span[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[3]/div[1]/div[1]/div[3]/div[1]/div[1]/div[1]/div[2]/div[1]/form[1]/div[1]/div[1]/span[1]/div[1]/div[1]/span[1]/span[1]/input[1]',
                               'text': '',
                               'tag': 'input',
                               'attributes': {   'name': 'submit.addToCart',
                                                 'aria-label': 'Add to cart',
                                                 'type': 'submit'}},
        'bounding_box': {   'x': 518,
                            'y': 361.13751220703125,
                            'width': 240.8000030517578,
                            'height': 30},
        'page_url': 'https://www.amazon.com/s?k=mouse&crid=PRMGGG3Q3MX0&sprefix=mouse%2Caps%2C329&ref=nb_sb_noss_1',
        'delta_x': None,
        'delta_y': None},
    {   'action_type': 'scroll',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.amazon.com/s?k=mouse&crid=PRMGGG3Q3MX0&sprefix=mouse%2Caps%2C329&ref=nb_sb_noss_1',
        'delta_x': 0,
        'delta_y': -1535},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'css_path': 'div#nav-cart-text-container > span:nth-of-type(2)',
                               'xpath': '/html[1]/body[1]/div[1]/header[1]/div[1]/div[1]/div[3]/div[1]/a[2]/div[2]/span[2]',
                               'text': 'Cart',
                               'tag': 'span',
                               'attributes': {}},
        'bounding_box': {'x': 1085, 'y': 28.61250114440918, 'width': 28, 'height': 15},
        'page_url': 'https://www.amazon.com/s?k=mouse&crid=PRMGGG3Q3MX0&sprefix=mouse%2Caps%2C329&ref=nb_sb_noss_1',
        'delta_x': None,
        'delta_y': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'css_path': 'div#sc-active-a630bd39-fa77-4fa8-aac0-b5dc5d4f9ef0 > '
                                           'div:nth-of-type(4) > div > div:nth-of-type(2) > div > '
                                           'span > span > fieldset > div:nth-of-type(2) > div > '
                                           'button > span',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[3]/div[4]/div[1]/div[2]/div[1]/div[1]/form[1]/ul[1]/div[3]/div[4]/div[1]/div[2]/div[1]/span[1]/span[1]/fieldset[1]/div[2]/div[1]/button[1]/span[1]',
                               'text': '',
                               'tag': 'span',
                               'attributes': {}},
        'bounding_box': {'x': 258.3999938964844, 'y': 349.6000061035156, 'width': 16, 'height': 16},
        'page_url': 'https://www.amazon.com/gp/cart/view.html?ref_=nav_cart',
        'delta_x': None,
        'delta_y': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'css_path': 'a#nav-hamburger-menu > span',
                               'xpath': '/html[1]/body[1]/div[1]/header[1]/div[1]/div[5]/div[1]/a[1]/span[1]',
                               'text': 'All',
                               'tag': 'span',
                               'attributes': {}},
        'bounding_box': {   'x': 36.79999923706055,
                            'y': 73.5,
                            'width': 23.412500381469727,
                            'height': 12},
        'page_url': 'https://www.amazon.com/gp/cart/view.html?ref_=nav_cart',
        'delta_x': None,
        'delta_y': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': '#hmenu-close-icon',
                               'css_path': 'div#hmenu-close-icon',
                               'xpath': "//*[@id='hmenu-close-icon']",
                               'text': '',
                               'tag': 'div',
                               'attributes': {'role': 'button', 'aria-label': 'Close menu'}},
        'bounding_box': {'x': 380, 'y': 20, 'width': 20, 'height': 20},
        'page_url': 'https://www.amazon.com/gp/cart/view.html?ref_=nav_cart',
        'delta_x': None,
        'delta_y': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': '#hmenu-canvas-background',
                               'css_path': 'div#hmenu-canvas-background',
                               'xpath': "//*[@id='hmenu-canvas-background']",
                               'text': '',
                               'tag': 'div',
                               'attributes': {}},
        'bounding_box': {'x': 0, 'y': 0, 'width': 1263.2000732421875, 'height': 720},
        'page_url': 'https://www.amazon.com/gp/cart/view.html?ref_=nav_cart',
        'delta_x': None,
        'delta_y': None},
    {   'action_type': 'navigate',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.amazon.com/s?k=mouse&crid=PRMGGG3Q3MX0&sprefix=mouse%2Caps%2C329&ref=nb_sb_noss_1',
        'delta_x': None,
        'delta_y': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'css_path': 'li#p_n_feature_twelve_browse-bin/23680031011 > span > '
                                           'a > div > label',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[3]/span[1]/div[1]/span[1]/div[1]/div[2]/div[7]/ul[1]/span[1]/span[1]/li[1]/span[1]/a[1]/div[1]/label[1]',
                               'text': '',
                               'tag': 'label',
                               'attributes': {}},
        'bounding_box': {'x': 11.600000381469727, 'y': 131.25, 'width': 21, 'height': 24},
        'page_url': 'https://www.amazon.com/s?k=mouse&crid=PRMGGG3Q3MX0&sprefix=mouse%2Caps%2C329&ref=nb_sb_noss_1',
        'delta_x': None,
        'delta_y': None},
    {   'action_type': 'navigate',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.amazon.com/s?k=mouse&rh=p_n_feature_twelve_browse-bin%3A23680031011&dc&crid=PRMGGG3Q3MX0&qid=1786511355&rnid=23680026011&sprefix=mouse%2Caps%2C329&ref=sr_nr_p_n_feature_twelve_browse-bin_1&ds=v1%3AYJ12iDc02a6NfeOE5%2BkSPdcy8lYfrsdx5MxZUTp%2FlE0',
        'delta_x': None,
        'delta_y': None}]
PROD_URL = "https://www.amazon.com/s?k=mouse&crid=PRMGGG3Q3MX0&sprefix=mouse%2Caps%2C329&ref=nb_sb_noss_1"


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


def run(qa_url, output_json_path=None, screenshot_dir=None, headless=True):
    print("Starting replay...")
    result = {
        "status": "FAIL",
        "message": "",
        "qa_url": qa_url,
        "steps": [],
        "final_url": None,
        "final_screenshot": None,
        "final_text": None,
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
        except Exception as e:
            print(f"Replay failed - could not open {qa_url}:\n{e}")
            result["message"] = f"could not open QA URL: {e}"
            browser.close()
            _write_result(result, output_json_path)
            return result

        print("Executing recorded actions...")

        for i, step in enumerate(STEPS, start=1):
            action_type = step.get("action_type")
            if action_type == "navigate":
                target = to_qa_url(step.get("page_url"), qa_url)
                try:
                    page.goto(target, wait_until="domcontentloaded", timeout=30000)
                    strategy, found, ok, err = None, True, True, None
                except Exception as e:
                    strategy, found, ok, err = None, True, False, str(e)
            elif action_type == "scroll":
                # no element involved - just replay the same mouse wheel
                # movement that was recorded, on the page as a whole
                try:
                    page.mouse.wheel(step.get("delta_x") or 0, step.get("delta_y") or 0)
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

            shot_path = shot_dir / f"step{i}.png"
            try:
                page.screenshot(path=str(shot_path))
                shot_str = str(shot_path)
            except Exception:
                shot_str = None

            logger.debug("step %d (%s): strategy=%s found=%s success=%s", i, action_type, strategy, found, ok)
            if not ok:
                # the plain print() is the real user-facing failure message
                # (see AUTOFLOW_DEBUG for the fuller strategy/step trace)
                logger.debug("step %d (%s) failed: %s", i, action_type, err)
                print(f"Replay failed at action {i}:\n{err}")
            result["steps"].append({
                "index": i,
                "action_type": action_type,
                "strategy_used": strategy,
                "element_found": found,
                "success": ok,
                "error": err,
                "screenshot": shot_str,
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

        browser.close()

    steps_ok = all(s["success"] for s in result["steps"]) if result["steps"] else True
    result["status"] = "PASS" if steps_ok else "FAIL"
    result["message"] = "all steps resolved" if steps_ok else "one or more steps failed"

    if steps_ok:
        print("Replay completed successfully.")
    else:
        failed = [s["index"] for s in result["steps"] if not s["success"]]
        print(f"Replay finished with {len(failed)} failed action(s): {failed}")

    _write_result(result, output_json_path)
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
    run(target, out_json, out_shots, headless=(headless_arg == "1"))
