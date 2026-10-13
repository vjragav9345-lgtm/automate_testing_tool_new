"""
Auto-generated from recording: session_20260812_095857
Generated at: 2026-08-12T09:58:57.354124
Original recorded (production) URL: https://www.amazon.com/s/ref=nb_sb_noss_1?url=search-alias%3Daps&field-keywords=mouse&crid=1HK0D8I787F4D&sprefix=mouse%2Caps%2C378

Resolution order per step: data-testid -> data-test -> data-cy -> id -> name
-> aria-label -> placeholder -> role -> css_path -> xpath -> text+tag ->
bounding box click. Dropdowns use page.select_option(), form submits use
form.requestSubmit(), meaningful keypresses (Enter/Tab/Escape) use el.press().

Run directly with: python session_20260812_095857_script.py <qa_url> [output_json_path] [screenshot_dir]
"""
import sys
import json
import logging
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

STEPS = [   {   'action_type': 'navigate',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.amazon.com/s?k=mouse&crid=1HK0D8I787F4D&sprefix=mouse%2Caps%2C378&ref=nb_sb_noss_1'},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'css_path': 'div#04ca3c1a-2671-4df7-a652-a996a03a7388 > div > div > '
                                           'div > div > span > div > div > div > div > div > '
                                           'div:nth-of-type(2)',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/span[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/span[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]',
                               'text': '',
                               'tag': 'div',
                               'attributes': {'data-cy': 'image-container'}},
        'bounding_box': {   'x': 262.8000183105469,
                            'y': 215.40000915527344,
                            'width': 242.40000915527344,
                            'height': 218},
        'page_url': 'https://www.amazon.com/s?k=mouse&crid=1HK0D8I787F4D&sprefix=mouse%2Caps%2C378&ref=nb_sb_noss_1'},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'css_path': 'div#04ca3c1a-2671-4df7-a652-a996a03a7388 > div > div > '
                                           'div > div > span > div > div > div > div > div > '
                                           'div:nth-of-type(2) > div > span > a > div > img',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/span[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/span[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/span[1]/a[1]/div[1]/img[1]',
                               'text': '',
                               'tag': 'img',
                               'attributes': {}},
        'bounding_box': {   'x': 270.8000183105469,
                            'y': 239.8874969482422,
                            'width': 226.40000915527344,
                            'height': 169.0124969482422},
        'page_url': 'https://www.amazon.com/s?k=mouse&crid=1HK0D8I787F4D&sprefix=mouse%2Caps%2C378&ref=nb_sb_noss_1'},
    {   'action_type': 'navigate',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.amazon.com/YUNZII-C1-Wireless-Tri-Mode-Optical/dp/B0H1M2WJ14/ref=sr_1_1_sspa?crid=1HK0D8I787F4D&dib=eyJ2IjoiMSJ9.UlhdkS_Xw4N4wR9qPv2lOq_F1GEGp2tqEt0bn0voLLDHESMaNNRr8iaR4Zpwi36bZnT1lwh-KLsZqx7XJUQzIe4WZDzgCKigFD77ZDxeQuQtGmbgB6H7KlbyoOC01hciZUf6khxS55O7M0qQJAoVP1TeMpoU7v-bR0w4FrZbewIn0M8sL7nZy7rzOIYQM_kci55Eq3FkOlfV6oSTtMuvHN-6WRXzwbGn51ewK1UB5ZU.N5plZWaMdrz1gb9Ph1BCjE8P8wFi1cTNasAT78RV3nA&dib_tag=se&keywords=mouse&qid=1786508876&sprefix=mouse%2Caps%2C378&sr=8-1-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9hdGY&th=1'},
    {   'action_type': 'navigate',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.amazon.com/s?k=mouse&crid=1HK0D8I787F4D&sprefix=mouse%2Caps%2C378&ref=nb_sb_noss_1'},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'css_path': 'span#a-autoid-10 > span > input',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/span[1]/div[1]/div[12]/div[1]/div[1]/span[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[3]/div[1]/div[1]/div[4]/div[1]/div[1]/div[1]/div[2]/div[1]/form[1]/div[1]/div[1]/span[1]/div[1]/div[1]/span[1]/span[1]/input[1]',
                               'text': '',
                               'tag': 'input',
                               'attributes': {   'name': 'submit.addToCart',
                                                 'aria-label': 'Add to cart',
                                                 'type': 'submit'}},
        'bounding_box': {'x': 518, 'y': 281.9375, 'width': 240.8000030517578, 'height': 30},
        'page_url': 'https://www.amazon.com/s?k=mouse&crid=1HK0D8I787F4D&sprefix=mouse%2Caps%2C378&ref=nb_sb_noss_1'},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': '#nav-cart',
                               'css_path': 'a#nav-cart',
                               'xpath': "//*[@id='nav-cart']",
                               'text': '0\nCart',
                               'tag': 'a',
                               'attributes': {   'href': '/gp/cart/view.html?ref_=nav_cart',
                                                 'aria-label': '0 items in cart'}},
        'bounding_box': {'x': 1168.5999755859375, 'y': 5, 'width': 83.5999984741211, 'height': 50},
        'page_url': 'https://www.amazon.com/cart'}]
PROD_URL = "https://www.amazon.com/s/ref=nb_sb_noss_1?url=search-alias%3Daps&field-keywords=mouse&crid=1HK0D8I787F4D&sprefix=mouse%2Caps%2C378"


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
            logger.warning("resolved via %s but action failed: %s", strategy, e)
            last_err = str(e)
    else:
        last_err = "none of the locator strategies (data-testid/data-test/data-cy/id/name/aria-label/placeholder/role/css_path/xpath/text+tag) matched an element"

    # bounding box is a last resort for plain clicks only - selects/submits/
    # keypresses need a real element to act on, a blind coordinate click
    # would just do the wrong thing
    box = step.get("bounding_box")
    if action_type == "click" and box and box.get("width") and box.get("height"):
        try:
            x = box["x"] + box["width"] / 2
            y = box["y"] + box["height"] / 2
            page.mouse.click(x, y)
            return "bounding_box", element_found, True, None
        except Exception as e:
            return "bounding_box", element_found, False, f"coordinate click failed: {e}"

    return strategy, element_found, False, last_err


def _dismiss_dialog(dialog):
    logger.info("dialog appeared (%s): %s - dismissing", dialog.type, dialog.message)
    dialog.dismiss()


def run(qa_url, output_json_path=None, screenshot_dir=None):
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
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(8000)
        # cookie banners/alerts shouldn't be able to hang an unattended run
        page.on("dialog", _dismiss_dialog)

        try:
            page.goto(qa_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            result["message"] = f"could not open QA URL: {e}"
            browser.close()
            _write_result(result, output_json_path)
            return result

        for i, step in enumerate(STEPS, start=1):
            action_type = step.get("action_type")
            if action_type == "navigate":
                target = to_qa_url(step.get("page_url"), qa_url)
                try:
                    page.goto(target, wait_until="domcontentloaded", timeout=30000)
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

            logger.info("step %d (%s): strategy=%s found=%s success=%s", i, action_type, strategy, found, ok)
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
    run(target, out_json, out_shots)
