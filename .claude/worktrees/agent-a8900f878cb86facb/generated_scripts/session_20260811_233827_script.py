"""
Auto-generated from recording: session_20260811_233827
Generated at: 2026-08-11T23:38:41.329895
Original start URL: https://books.toscrape.com/

Resolution order per step: id -> css_path -> xpath -> text+tag -> bounding box click.
Run directly with: python session_20260811_233827_script.py <qa_url>
"""
import sys
import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

STEPS = [
    {
        "action_type": "click",
        "value": null,
        "locator_profile": {
            "id": null,
            "css_path": "body#default > div > div > div > aside > div:nth-of-type(2) > ul > li > ul > li:nth-of-type(2) > a",
            "xpath": "/html[1]/body[1]/div[1]/div[1]/div[1]/aside[1]/div[2]/ul[1]/li[1]/ul[1]/li[2]/a[1]",
            "text": "Mystery",
            "tag": "a",
            "attributes": {}
        },
        "bounding_box": {
            "x": 89.80000305175781,
            "y": 296.5249938964844,
            "width": 49,
            "height": 16
        }
    },
    {
        "action_type": "click",
        "value": null,
        "locator_profile": {
            "id": null,
            "css_path": "body#default > div > div > div > div > section > div:nth-of-type(2) > ol > li > article > h3 > a",
            "xpath": "/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/section[1]/div[2]/ol[1]/li[1]/article[1]/h3[1]/a[1]",
            "text": "Sharp Objects",
            "tag": "a",
            "attributes": {}
        },
        "bounding_box": {
            "x": 412.3625183105469,
            "y": 643.125,
            "width": 88.7125015258789,
            "height": 16
        }
    }
]


def resolve_and_act(page, step):
    """Try each locator strategy in order until one works, then perform the action."""
    lp = step["locator_profile"]
    action = step["action_type"]
    value = step.get("value")
    strategy_used = None
    el = None

    # 1. id
    if lp.get("id"):
        try:
            candidate = page.locator(lp["id"])
            if candidate.count() > 0:
                el, strategy_used = candidate.first, "id"
        except Exception:
            pass

    # 2. css_path
    if el is None and lp.get("css_path"):
        try:
            candidate = page.locator(lp["css_path"])
            if candidate.count() > 0:
                el, strategy_used = candidate.first, "css_path"
        except Exception:
            pass

    # 3. xpath
    if el is None and lp.get("xpath"):
        try:
            candidate = page.locator("xpath=" + lp["xpath"])
            if candidate.count() > 0:
                el, strategy_used = candidate.first, "xpath"
        except Exception:
            pass

    # 4. text + tag
    if el is None and lp.get("text"):
        try:
            candidate = page.locator(lp["tag"], has_text=lp["text"])
            if candidate.count() > 0:
                el, strategy_used = candidate.first, "text+tag"
        except Exception:
            pass

    if el is not None:
        try:
            el.scroll_into_view_if_needed(timeout=3000)
            if action == "click":
                el.click(timeout=5000)
            elif action == "fill" and value is not None:
                el.fill(value, timeout=5000)
            return strategy_used
        except Exception as e:
            logger.warning("resolved via %s but action failed: %s", strategy_used, e)

    # 5. last resort - click raw coordinates from when this was recorded
    box = step.get("bounding_box")
    if box and box.get("width") and box.get("height"):
        try:
            x = box["x"] + box["width"] / 2
            y = box["y"] + box["height"] / 2
            page.mouse.click(x, y)
            return "bounding_box"
        except Exception as e:
            logger.error("bounding box fallback failed too: %s", e)

    return None


def run(qa_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(10000)
        page.goto(qa_url, wait_until="domcontentloaded", timeout=30000)

        for i, step in enumerate(STEPS, start=1):
            strategy = resolve_and_act(page, step)
            if strategy:
                logger.info("step %d (%s): resolved via %s", i, step["action_type"], strategy)
            else:
                logger.error("step %d (%s): could not resolve element, skipping", i, step["action_type"])

        browser.close()


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://books.toscrape.com/"
    run(target)
