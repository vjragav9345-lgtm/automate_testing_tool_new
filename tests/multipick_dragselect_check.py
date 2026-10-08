"""TEST-ONLY: Pick Element multi-select (drag-rectangle) feature verification.

Exercises the injected picker script (recorder/action_capture.js) directly against a
local fixture page (myntra.com is unreachable in this environment - confirmed
separately, unrelated to this change), bypassing recorder/pick_element.py's own
thread/session/Flask plumbing entirely so results are unambiguously about the
injected script's own logic, not test-harness scaffolding. Covers acceptance
tests A, C, D, E directly against the fixture; B (count_elements replay) reuses
test A's own resulting xpath; F is a plain, non-pick-mode Recorder/replay
regression check on the same fixture.
"""
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
from phase4_fixture_server import FixtureServer
from recorder.record_session import _CAPTURE_JS, Recorder
from generator.script_generator import generate_script

REPORT = {}


def make_pick_page(pw, url):
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    results = []
    releases = []
    page.expose_function("pickResult", lambda raw: results.append(json.loads(raw)))
    page.expose_function("pickReleased", lambda: releases.append(True))
    # injected only AFTER the page has fully loaded (not via add_init_script,
    # which fires on document-creation - before <body> exists - and hits a
    # PRE-EXISTING, unrelated race confirmed to reproduce identically on the
    # unmodified pre-this-task script too; this fixture never navigates
    # again after load, so a single post-load evaluate() is sufficient and
    # matches how pick_element.py's own _inject_pick_mode ALSO explicitly
    # evaluates the script into the already-loaded page, not just relying
    # on add_init_script alone)
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(300)
    pick_script = "window.__afqaPickMode = true;\n" + _CAPTURE_JS
    page.evaluate(pick_script)
    return browser, ctx, page, results, releases


with FixtureServer() as srv:
    url = srv.url("multipick_grid.html")

    # ---------------- TEST A: drag over several rows ----------------
    with sync_playwright() as p:
        browser, ctx, page, results, releases = make_pick_page(p, url)
        try:
            page.mouse.move(30, 55)
            page.mouse.down()
            page.mouse.move(600, 355, steps=10)
            page.wait_for_timeout(100)
            page.mouse.up()
            page.wait_for_timeout(300)
            assert results, "expected a pickResult call after the drag"
            profile = results[-1]
            print("TEST A profile:", json.dumps(profile)[:500])
            assert profile.get("mode") == "multi", f"expected mode=multi, got {profile.get('mode')!r}"
            assert profile.get("match_count") == 40, f"expected match_count=40 (every card on the page), got {profile.get('match_count')!r}"
            in_box = profile.get("in_box_count")
            assert isinstance(in_box, int) and 2 <= in_box < 40, f"expected a PARTIAL in_box_count (2..39), got {in_box!r}"
            xpath = profile.get("xpath") or ""
            assert not re.search(r"\[\d+\]\s*$", xpath), f"xpath's last step must have no positional [index]: {xpath!r}"
            REPORT["A"] = {"pass": True, "xpath": xpath, "match_count": profile["match_count"], "in_box_count": in_box}
            print(f"TEST A PASS: match_count={profile['match_count']} in_box_count={in_box} xpath={xpath!r}")
        finally:
            browser.close()

    # ---------------- TEST B: Count Elements with that xpath, replay ----------------
    xpath = REPORT["A"]["xpath"]
    tc = {
        "name": "multipick_test_b", "start_url": url,
        "actions": [
            {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": url},
            {"action_type": "count_elements", "value": None, "page_url": url, "expected_count": 40,
             "count_as": "product_count",
             "locator_profile": {"id": None, "css_path": None, "xpath": xpath, "text": None, "role": None,
                                  "tag": "div", "attributes": {}}},
        ],
    }
    d = Path("tests/_probe_out/multipick_test_b")
    d.mkdir(parents=True, exist_ok=True)
    sp = generate_script(tc, out_name="multipick_test_b_script.py", output_dir=d)
    spec = importlib.util.spec_from_file_location("multipick_test_b_mod", sp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    res = mod.run(url, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    for s in res["steps"]:
        print("TEST B step:", s["index"], s["action_type"], "success=" + str(s["success"]), repr(s.get("error"))[:150])
    ok_b = res["status"] == "PASS" and all(s["success"] for s in res["steps"])
    REPORT["B"] = {"pass": ok_b}
    print(f"TEST B {'PASS' if ok_b else 'FAIL'}: status={res['status']}")

    # ---------------- TEST C: single-click Pick Element still works ----------------
    with sync_playwright() as p:
        browser, ctx, page, results, releases = make_pick_page(p, url)
        try:
            box = page.eval_on_selector("#searchBox", "el => { const r = el.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2}; }")
            page.mouse.click(box["x"], box["y"])
            page.wait_for_timeout(200)
            assert results, "expected a pickResult call after the single click"
            profile = results[-1]
            print("TEST C profile:", json.dumps(profile)[:400])
            assert profile.get("mode") is None, f"a single click must NOT be tagged mode=multi, got {profile.get('mode')!r}"
            assert profile.get("match_count") == 1, f"expected a unique match for #searchBox, got {profile.get('match_count')!r}"
            assert profile.get("id") == "#searchBox", f"expected id=#searchBox, got {profile.get('id')!r}"
            # double-click re-pick still works: release, then click a different element
            page.mouse.dblclick(box["x"], box["y"])
            page.wait_for_timeout(200)
            assert releases, "expected a pickReleased call after the double-click"
            REPORT["C"] = {"pass": True}
            print("TEST C PASS: single-click pick + double-click release both work unchanged")
        finally:
            browser.close()

    # ---------------- TEST D: a 1-3px move is a click, not a drag ----------------
    with sync_playwright() as p:
        browser, ctx, page, results, releases = make_pick_page(p, url)
        try:
            box = page.eval_on_selector("#searchBox", "el => { const r = el.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2}; }")
            page.mouse.move(box["x"], box["y"])
            page.mouse.down()
            page.mouse.move(box["x"] + 2, box["y"] + 1, steps=1)  # 1-3px - below DRAG_THRESHOLD_PX
            page.mouse.up()
            page.wait_for_timeout(200)
            assert results, "expected a pickResult call for a sub-threshold movement"
            profile = results[-1]
            print("TEST D profile:", json.dumps(profile)[:400])
            assert profile.get("mode") is None, f"a <=3px move must be treated as a CLICK, not a drag - got mode={profile.get('mode')!r}"
            assert profile.get("id") == "#searchBox"
            REPORT["D"] = {"pass": True}
            print("TEST D PASS: a 1-3px move is correctly treated as a click, not a drag")
        finally:
            browser.close()

    # ---------------- TEST E: drag over a single non-repeating element ----------------
    with sync_playwright() as p:
        browser, ctx, page, results, releases = make_pick_page(p, url)
        try:
            box = page.eval_on_selector("#searchBox", "el => { const r = el.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height}; }")
            page.mouse.move(box["x"] + 5, box["y"] + 5)
            page.mouse.down()
            page.mouse.move(box["x"] + box["w"] - 5, box["y"] + box["h"] - 5, steps=8)
            page.wait_for_timeout(80)
            page.mouse.up()
            page.wait_for_timeout(300)
            assert results, "expected a pickResult call after the drag"
            profile = results[-1]
            print("TEST E profile:", json.dumps(profile)[:400])
            # UPDATED (follow-up task, requirement 4): no more silent
            # single-element fallback for a drag with no repeating group -
            # sends mode="multi_none" instead, with no xpath at all.
            assert profile.get("mode") == "multi_none", f"expected mode=multi_none (no silent fallback), got {profile.get('mode')!r}"
            assert profile.get("xpath") is None
            REPORT["E"] = {"pass": True}
            print("TEST E PASS: no silent single-element fallback - correctly sent multi_none")
        finally:
            browser.close()

    # ---------------- TEST F: normal (non-pick-mode) recording/replay unaffected ----------------
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()
        rec = Recorder(page)
        rec.install_context_capture(ctx)
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(300)
        rec.start(launch_url=page.url)
        page.click("#searchBox")
        page.fill("#searchBox", "hello")
        page.wait_for_timeout(200)
        tc_f = rec.stop(name="multipick_test_f", stop_reason="terminal_enter")
        drafts = (rec._draft_path, rec._draft_jsonl_path)
        browser.close()
    for dft in drafts:
        if dft:
            Path(dft).unlink(missing_ok=True)
    d = Path("tests/_probe_out/multipick_test_f")
    d.mkdir(parents=True, exist_ok=True)
    sp = generate_script(tc_f, out_name="multipick_test_f_script.py", output_dir=d)
    spec = importlib.util.spec_from_file_location("multipick_test_f_mod", sp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    res_f = mod.run(url, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    for s in res_f["steps"]:
        print("TEST F step:", s["index"], s["action_type"], "success=" + str(s["success"]), repr(s.get("error"))[:150])
    ok_f = res_f["status"] == "PASS" and all(s["success"] for s in res_f["steps"])
    REPORT["F"] = {"pass": ok_f}
    print(f"TEST F {'PASS' if ok_f else 'FAIL'}: status={res_f['status']}")

print("\n=== SUMMARY ===")
for k in ["A", "B", "C", "D", "E", "F"]:
    print(k, REPORT.get(k))
assert all(v.get("pass") for v in REPORT.values()), "one or more tests FAILED"
print("\nALL TESTS PASS")
