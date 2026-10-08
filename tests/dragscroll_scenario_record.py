"""TEST-ONLY scenario recorder for the drag/scroll investigation.

Drives the REAL Recorder + action_capture.js in a headed browser with human-
paced input (many small wheel events, multi-point mouse drags with ~40ms
between moves) on real websites, saves the resulting recording, and writes a
"manual log": the page scroll position after every scroll gesture and the
settled slider value after every drag (what a person would have SEEN).

    venv/Scripts/python.exe tests/dragscroll_scenario_record.py <scenario> [--target N]
scenarios: amazon | myntra | nouislider
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import sync_playwright  # noqa: E402

from recorder.record_session import Recorder  # noqa: E402
from storage import repository  # noqa: E402

# same logic as action_capture.js's _captureDragValueSnapshot (what a person SEES next to a slider)
_DRAG_VALUE_SNAPSHOT_JS = r"""
(sourceEl) => {
    function closestSliderLike(el) {
        var node = el;
        for (var i = 0; i < 4 && node; i++) {
            if (node.tagName === 'INPUT' && (node.type || '').toLowerCase() === 'range') return node;
            if (node.getAttribute && (node.getAttribute('role') === 'slider' || node.hasAttribute('aria-valuenow'))) return node;
            node = node.parentElement;
        }
        return null;
    }
    var slider = closestSliderLike(sourceEl);
    if (slider) {
        if (slider.tagName === 'INPUT') return { kind: 'range_value', value: slider.value };
        return { kind: 'aria_value', value: slider.getAttribute('aria-valuenow'), text: slider.getAttribute('aria-valuetext') };
    }
    var container = (sourceEl.closest && sourceEl.closest('[class]')) || sourceEl.parentElement;
    for (var j = 0; j < 3 && container; j++) {
        var txt = (container.innerText || '').trim();
        if (txt && txt.length < 200 && /\d/.test(txt)) return { kind: 'nearby_text', value: txt };
        container = container.parentElement;
    }
    return null;
}
""".replace("/\d/", "/\d/")

OUT_DIR = BASE_DIR / "tests" / "_probe_out"
MANUAL = []
random.seed(12345)


def log(*a):
    print("[scenario]", *a, flush=True)


class Human:
    def __init__(self, page, recorder):
        self.page = page
        self.rec = recorder
        self.vh = page.viewport_size["height"]
        self.vw = page.viewport_size["width"]

    def n_actions(self):
        return len(self.rec.actions)

    def scroll_y(self):
        return self.page.evaluate("() => window.scrollY")

    def wheel(self, total, chunk=90, delay=30, tag="scroll"):
        p = self.page
        p.mouse.move(self.vw * 0.55, self.vh * 0.5, steps=4)
        sign = 1 if total > 0 else -1
        remaining = abs(total)
        while remaining > 0:
            d = min(chunk, remaining)
            p.mouse.wheel(0, sign * d)
            p.wait_for_timeout(delay)
            remaining -= d
        p.wait_for_timeout(700)  # > recorder's 250ms settle, lets it emit ONE scroll action
        y = self.scroll_y()
        MANUAL.append({"n": self.n_actions(), "kind": "scroll", "tag": tag, "scrollY": y})
        log(f"scroll {total:+d} -> scrollY={y:.1f} (actions={self.n_actions()})")

    def bring_into_view(self, locator, margin=140):
        for _ in range(12):
            box = locator.bounding_box()
            if not box:
                return None
            if margin <= box["y"] <= self.vh - margin - box["height"]:
                return box
            delta = int(box["y"] - self.vh * 0.45)
            delta = max(-900, min(900, delta))
            self.wheel(delta, tag="reach-target")
        return locator.bounding_box()

    def click_at(self, x, y):
        p = self.page
        p.mouse.move(x, y, steps=8)
        p.wait_for_timeout(120)
        p.mouse.down()
        p.wait_for_timeout(70)
        p.mouse.up()
        p.wait_for_timeout(500)

    def click(self, locator, tag="click"):
        box = self.bring_into_view(locator)
        if not box:
            log("click skipped (no box)", tag)
            return False
        self.click_at(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        MANUAL.append({"n": self.n_actions(), "kind": "click", "tag": tag, "scrollY": self.scroll_y()})
        log(f"click {tag} (actions={self.n_actions()})")
        return True

    def drag(self, locator, dx, dy=0, tag="drag", n=14, gap=40, settle_ms=1600):
        p = self.page
        box = self.bring_into_view(locator)
        if not box:
            log("drag skipped (no box)", tag)
            return False
        x0, y0 = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        p.mouse.move(x0, y0, steps=8)
        p.wait_for_timeout(150)
        p.mouse.down()
        p.wait_for_timeout(180)
        for i in range(1, n + 1):
            frac = i / n
            p.mouse.move(x0 + dx * frac, y0 + dy * frac + random.uniform(-1.5, 1.5))
            p.wait_for_timeout(gap)
        p.mouse.up()
        p.wait_for_timeout(settle_ms)
        try:
            settled = locator.evaluate(_DRAG_VALUE_SNAPSHOT_JS)
        except Exception:
            settled = None
        MANUAL.append({"n": self.n_actions(), "kind": "drag", "tag": tag, "settled_value": settled,
                       "scrollY": self.scroll_y()})
        log(f"drag {tag} dx={dx} -> settled={settled} (actions={self.n_actions()})")
        return True


def scenario_amazon(h, page, target):
    page.wait_for_timeout(3000)
    h.wheel(500)
    h.wheel(400)
    ranges = page.locator("input[type=range]")
    log("range inputs:", ranges.count())
    if ranges.count() >= 2:
        # native range inputs: aim at each thumb's REAL position (value -> x), not the input's centre
        def thumb_center(loc):
            info = loc.evaluate("e => ({min: +e.min, max: +e.max, value: +e.value})")
            box = h.bring_into_view(loc)
            frac = (info["value"] - info["min"]) / max(1, (info["max"] - info["min"]))
            return box, box["x"] + 10 + frac * (box["width"] - 20), box["y"] + box["height"] / 2
        for idx, dx, tag in ((0, 55, "amazon-min-thumb"), (1, -70, "amazon-max-thumb")):
            loc = ranges.nth(idx)
            box, cx, cy = thumb_center(loc)
            p2 = page
            p2.mouse.move(cx, cy, steps=8); p2.wait_for_timeout(150); p2.mouse.down(); p2.wait_for_timeout(180)
            for i in range(1, 15):
                p2.mouse.move(cx + dx * i / 14, cy + random.uniform(-1, 1)); p2.wait_for_timeout(40)
            p2.mouse.up(); p2.wait_for_timeout(1600)
            settled = loc.evaluate(_DRAG_VALUE_SNAPSHOT_JS)
            MANUAL.append({"n": h.n_actions(), "kind": "drag", "tag": tag, "settled_value": settled, "scrollY": h.scroll_y()})
            log(f"drag {tag} dx={dx} -> settled={settled} (actions={h.n_actions()})")
    go = page.locator("input[type=submit][aria-label='Go']").first
    try:
        if go.count():
            h.click(go, tag="price-go")
            page.wait_for_timeout(3500)
    except Exception as e:
        log("go button skipped", e)
    h.wheel(700)
    h.wheel(-350)
    boxes = page.locator("#s-refinements li input[type=checkbox]")
    try:
        if boxes.count():
            lab = page.locator("#s-refinements li .a-checkbox label, #s-refinements li a").first
            h.click(lab, tag="refinement")
            page.wait_for_timeout(3000)
    except Exception as e:
        log("refinement skipped", e)
    h.wheel(600)
    h.wheel(500)
    h.wheel(-800)
    h.wheel(900)
    h.wheel(-1200)


def scenario_myntra(h, page, target):
    page.wait_for_timeout(4000)
    h.wheel(600)
    h.wheel(-300)
    for round_no in range(20):
        if h.n_actions() >= target:
            break
        # price slider drags (rail thumbs) whenever present
        try:
            left = page.locator("#rootRailThumbLeft")
            right = page.locator("#rootRailThumbRight")
            if round_no % 3 == 0 and right.count():
                h.wheel(-2000, tag="to-top")
                h.drag(right, -random.randint(40, 110), tag=f"price-right-{round_no}")
                page.wait_for_timeout(1500)
            elif round_no % 3 == 1 and left.count():
                h.wheel(-2000, tag="to-top")
                h.drag(left, random.randint(15, 60), tag=f"price-left-{round_no}")
                page.wait_for_timeout(1500)
        except Exception as e:
            log("price drag skipped", e)
        # a couple of natural scrolls
        h.wheel(random.randint(500, 1100))
        h.wheel(random.randint(-400, -150))
        # tick a filter checkbox label (brand/colour lists)
        try:
            labels = page.locator("section ul li label.common-customCheckbox, section ul li label")
            cnt = labels.count()
            if cnt:
                pick = labels.nth(random.randint(0, min(cnt, 14) - 1))
                h.click(pick, tag=f"filter-{round_no}")
                page.wait_for_timeout(3500)
        except Exception as e:
            log("filter skipped", e)
        h.wheel(random.randint(300, 900))
        h.wheel(random.randint(-700, -200))


def scenario_nouislider(h, page, target):
    page.wait_for_timeout(2500)
    targets = page.locator(".noUi-target")
    total = targets.count()
    log("noUiSlider targets:", total)
    idx = 0
    passes = 0
    while h.n_actions() < target and passes < 4:
        slider = targets.nth(idx % total)
        handles = slider.locator(".noUi-handle")
        try:
            hc = handles.count()
            if hc:
                h.wheel(random.choice([-260, -120, 140, 300]), tag="wander")
                which = random.randrange(hc)
                box = slider.bounding_box()
                width = box["width"] if box else 300
                lo, hi = max(25, int(width * 0.08)), max(40, int(width * 0.3))
                h.drag(handles.nth(which), random.choice([-1, 1]) * random.randint(lo, hi),
                       tag=f"noui-{idx % total}-h{which}")
                if hc > 1 and h.n_actions() < target:
                    h.drag(handles.nth(hc - 1 - which), random.choice([-1, 1]) * random.randint(lo, hi),
                           tag=f"noui-{idx % total}-h{hc-1-which}")
        except Exception as e:
            log("slider", idx % total, "skipped:", str(e)[:100])
        idx += 1
        if idx % total == 0:
            passes += 1
        if idx % 6 == 0:
            h.wheel(-random.randint(400, 900), tag="review-up")


SCENARIOS = {
    "amazon": ("https://www.amazon.in/s?k=laptop", scenario_amazon, "dragscroll_amazon_small"),
    "myntra": ("https://www.myntra.com/men-jeans", scenario_myntra, "dragscroll_myntra_medium"),
    "nouislider": ("https://refreshless.com/nouislider/examples/", scenario_nouislider, "dragscroll_nouislider_large"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario")
    ap.add_argument("--target", type=int, default=20)
    ap.add_argument("--name", default=None)
    ap.add_argument("--headless", action="store_true",
                    help="immune to physical-mouse interference (real OS pointer events reach a visible window)")
    args = ap.parse_args()
    url, fn, name = SCENARIOS[args.scenario]
    name = args.name or name

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        recorder = Recorder(page)
        recorder.install_context_capture(context)
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        recorder.start(launch_url=url)
        h = Human(page, recorder)
        try:
            fn(h, page, args.target)
        finally:
            page.wait_for_timeout(1500)
            test_case = recorder.stop(name=name, stop_reason="terminal_enter")
            draft_paths = (recorder._draft_path, recorder._draft_jsonl_path)
            browser.close()
    path = repository.save_recording(test_case)
    for d in draft_paths:
        if d:
            Path(d).unlink(missing_ok=True)
    (OUT_DIR / f"manual_{name}.json").write_text(json.dumps(MANUAL, indent=1, default=str), encoding="utf-8")
    kinds = {}
    for a in test_case["actions"]:
        kinds[a["action_type"]] = kinds.get(a["action_type"], 0) + 1
    log("SAVED", path, "actions:", len(test_case["actions"]), kinds)


if __name__ == "__main__":
    main()
