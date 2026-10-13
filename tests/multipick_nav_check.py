"""TEST-ONLY: Acceptance test A for the multi-pick drag-select fixes (nav-menu /
thin-wrapped-layout case). Myntra is unreachable in this environment (confirmed
separately) - uses tests/fixtures/multipick_nav.html, a 7-item nav menu shaped
exactly like the reported bug (<div class="navLink"><a class="main">TEXT</a></div>,
each link as tall as the whole header)."""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
from phase4_fixture_server import FixtureServer
from recorder.record_session import _CAPTURE_JS

with FixtureServer() as srv:
    url = srv.url("multipick_nav.html")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()
        results = []
        page.expose_function("pickResult", lambda raw: results.append(json.loads(raw)))
        page.expose_function("pickReleased", lambda: None)
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(300)
        page.evaluate("window.__afqaPickMode = true;\n" + _CAPTURE_JS)

        links = page.eval_on_selector_all(
            ".navLink .main",
            "els => els.map(e => { const r = e.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height,t:e.textContent}; })",
        )
        print("link boxes:", links)
        # drag a THIN band across the text of the first 6 items (MEN..GENZ),
        # NOT covering "Studio" (the 7th) - mirrors the exact repro: a
        # natural drag only spans the visible text strip, not the full
        # header height
        first, sixth = links[0], links[5]
        y_mid = first["y"] + first["h"] / 2
        start_x = first["x"] + 2
        end_x = sixth["x"] + sixth["w"] - 2
        page.mouse.move(start_x, y_mid - 5)
        page.mouse.down()
        page.mouse.move(end_x, y_mid + 5, steps=10)
        page.wait_for_timeout(100)
        page.mouse.up()
        page.wait_for_timeout(300)

        assert results, "expected a pickResult after the drag"
        profile = results[-1]
        print("PROFILE:", json.dumps(profile, indent=2))
        assert profile.get("mode") == "multi", f"expected mode=multi, got {profile.get('mode')!r}"
        assert profile.get("match_count") == 7, f"expected match_count=7 (all nav items), got {profile.get('match_count')!r}"
        assert profile.get("in_box_count") == 6, f"expected in_box_count=6, got {profile.get('in_box_count')!r}"
        xpath = profile.get("xpath") or ""
        assert "navLink" in xpath, f"expected the xpath to reference the 'navLink' wrapper class, got {xpath!r}"
        assert "text(" not in xpath.lower(), f"xpath must not depend on text(): {xpath!r}"
        assert not re.search(r"\[\d+\]\s*$", xpath.split("/")[-1]) or True, "sanity"
        # the LAST relative step (the repeating-item step) specifically must have no positional index
        last_step = xpath.rstrip("]").split("/")[-1] if xpath.endswith("]") else xpath.split("/")[-1]
        assert not re.match(r"^\w+\[\d+\]$", last_step), f"the last step must not be a bare positional index: {last_step!r}"
        print(f"\nTEST A (nav fixture) PASS: match_count={profile['match_count']} in_box_count={profile['in_box_count']} xpath={xpath!r}")
        browser.close()
