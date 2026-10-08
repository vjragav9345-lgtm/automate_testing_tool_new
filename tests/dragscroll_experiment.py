"""TEST-ONLY experiment (drag root-cause investigation): loads the exact page
state the evidence recording's drag step ran on and performs the SAME
recorded drag path under different pacing variants, logging the slider label
after each one.  No production code is imported or modified.

    venv/Scripts/python.exe tests/dragscroll_experiment.py <recording.json> <drag_step_index>
"""
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

rec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
idx = int(sys.argv[2])
act = rec["actions"][idx - 1]
url = act["page_url"]
lp_id = act["source_target"]["id"]  # '#rootRailThumbRight'
so = act["start_offset"]
path = act["path"]
delta = act["end_delta"]
print("URL", url)
print("recorded path points", len(path), "t range", path[0]["t"], "..", path[-1]["t"])


def label(page):
    return page.evaluate("""(sel) => { const t = document.querySelector(sel); let n = t; for (let i=0;i<6&&n;i++){ const s=(n.innerText||'').trim(); if (s && /\\d/.test(s) && s.length<120) return s; n=n.parentElement;} return null; }""", lp_id)


def thumb(page):
    return page.evaluate("(sel) => { const r = document.querySelector(sel).getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }", lp_id)


def run_variant(name, mover):
    with sync_playwright() as p:
        b = p.chromium.launch(headless=False)
        ctx = b.new_context(viewport={"width": 1280, "height": 720})
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_selector(lp_id, timeout=30000)
        page.wait_for_timeout(2500)
        box = page.locator(lp_id).bounding_box()
        sx, sy = box["x"] + so["x"], box["y"] + so["y"]
        lab0 = label(page)
        samples = []
        page.mouse.move(sx, sy)
        page.mouse.down()
        mover(page, box, sx, sy, samples)
        page.mouse.up()
        page.wait_for_timeout(1500)
        print(f"{name:34s} start={lab0!r:22} during_last={samples[-1] if samples else None!r:22} FINAL={label(page)!r:22} thumb={[round(v,1) for v in thumb(page)]}")
        b.close()


def m_replay_like(page, box, sx, sy, samples):
    # what production replay does today: each recorded point, 1 step, no delay, final move at end_delta
    for pt in path:
        page.mouse.move(box["x"] + pt["dx"], box["y"] + pt["dy"], steps=1)
    page.mouse.move(sx + delta["dx"], sy + delta["dy"], steps=1)


def m_timed(page, box, sx, sy, samples):
    # honour the recorded inter-point timing
    prev_t = 0
    for pt in path:
        page.wait_for_timeout(max(0, pt["t"] - prev_t))
        prev_t = pt["t"]
        page.mouse.move(box["x"] + pt["dx"], box["y"] + pt["dy"], steps=1)
        samples.append(label(page))
    page.mouse.move(sx + delta["dx"], sy + delta["dy"], steps=1)
    page.wait_for_timeout(100)
    samples.append(label(page))


def m_fixed_delay(ms):
    def f(page, box, sx, sy, samples):
        for pt in path:
            page.mouse.move(box["x"] + pt["dx"], box["y"] + pt["dy"], steps=1)
            page.wait_for_timeout(ms)
            samples.append(label(page))
        page.mouse.move(sx + delta["dx"], sy + delta["dy"], steps=1)
        page.wait_for_timeout(ms)
        samples.append(label(page))
    return f


def m_jump(page, box, sx, sy, samples):
    page.mouse.move(sx + delta["dx"], sy + delta["dy"], steps=1)
    samples.append(label(page))


def m_interp(n):
    def f(page, box, sx, sy, samples):
        page.mouse.move(sx + delta["dx"], sy + delta["dy"], steps=n)
        samples.append(label(page))
    return f


def m_replay_like_settle(page, box, sx, sy, samples):
    m_replay_like(page, box, sx, sy, samples)
    page.wait_for_timeout(300)  # settle before mouseup
    samples.append(label(page))


variants = [
    ("A replay-like (no delay)", m_replay_like),
    ("B recorded timing", m_timed),
    ("C 50ms between points", m_fixed_delay(50)),
    ("D single jump to end", m_jump),
    ("E interpolated 20 steps", m_interp(20)),
    ("F replay-like + 300ms settle pre-up", m_replay_like_settle),
    ("A2 replay-like again (repeat)", m_replay_like),
]
for n, f in variants:
    run_variant(n, f)
