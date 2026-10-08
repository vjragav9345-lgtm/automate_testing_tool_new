"""TEST-ONLY: S6 regression checks for the drag-select Count Elements fix.
Verifies: (1) a single-click pick behaves exactly as before (untouched
isMultiPick branch never triggers), (2) an OLD Count Elements step saved
BEFORE this change (a plain tag/class-identity xpath, no position()
predicate) still replays with the correct count, (3) a plain click+fill
recording is unaffected.
"""
import json
import sys
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from playwright.sync_api import sync_playwright
from phase4_fixture_server import FixtureServer
from recorder.record_session import Recorder
from storage import repository

APP_URL = "http://127.0.0.1:5099"
SHOT_DIR = Path("tests/_probe_out/ui_verify_dragfix")
SHOT_DIR.mkdir(parents=True, exist_ok=True)


def test_drive(action, **kw):
    body = json.dumps({"action": action, **kw}).encode("utf-8")
    req = urllib.request.Request(
        APP_URL + "/api/recordings/pick_element/_test_drive",
        data=body, headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def seed_recording(name, url, extra_steps=None):
    stale = BASE / "storage" / "recordings" / "edited" / f"{name}_edited.json"
    stale.unlink(missing_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        pg = ctx.new_page()
        rec = Recorder(pg)
        rec.install_context_capture(ctx)
        pg.goto(url, wait_until="domcontentloaded")
        pg.wait_for_timeout(300)
        rec.start(launch_url=pg.url)
        pg.wait_for_timeout(300)
        if extra_steps:
            extra_steps(pg)
        tc = rec.stop(name=name, stop_reason="terminal_enter")
        drafts = (rec._draft_path, rec._draft_jsonl_path)
        b.close()
    for d in drafts:
        if d:
            Path(d).unlink(missing_ok=True)
    tc["name"] = name
    repository.save_recording(tc)
    return f"storage/recordings/{name}.json"


results = {}

with FixtureServer() as srv:
    grid_url = srv.url("zz_drag_grid.html")

    # ============ S6a: single-click pick still behaves exactly as before ============
    print("\n=== S6a: single-click pick (unchanged behaviour) ===")
    rec_path = seed_recording("zz_s6a_singleclick", grid_url)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        editor = ctx.new_page()
        editor.goto(f"{APP_URL}/recording/edit?path={rec_path}", wait_until="networkidle")
        editor.wait_for_timeout(500)
        editor.locator("#addActionBtn").click()
        editor.locator("#addActionModal").wait_for(state="visible")
        editor.locator("#modalActionType").select_option("click")
        editor.wait_for_timeout(200)
        editor.locator("#modalPickElementBtn").click()
        editor.wait_for_timeout(2500)
        test_drive("click_xpath", xpath="//div[@class='product-card'][1]")
        editor.wait_for_function(
            "document.getElementById('modalXpath').value.trim().length > 0", timeout=25000,
        )
        editor.wait_for_timeout(800)
        try:
            test_drive("close_browser")
        except Exception:
            pass
        editor.wait_for_timeout(500)
        state = {
            "xpath": editor.locator("#modalXpath").input_value(),
            "validate_text": editor.locator("#modalValidateResult").inner_text(),
        }
        print(state)
        editor.screenshot(path=str(SHOT_DIR / "s6a_singleclick_modal.png"))
        results["S6a_singleclick"] = state
        b.close()

    # ============ S6b: OLD-style Count Elements step (pre-fix xpath) still replays ============
    print("\n=== S6b: old-style saved Count Elements step still replays correctly ===")

    def add_old_style_step(pg):
        pass  # navigate-only seed; we inject the step directly below

    rec_path_b = seed_recording("zz_s6b_oldstyle", grid_url)
    # Manually append a pre-fix-style Count Elements step: a plain
    # tag/class-identity xpath with NO position() predicate - exactly what
    # the OLD drag-select code used to produce, matching every card.
    rec_file = BASE / "storage" / "recordings" / "zz_s6b_oldstyle.json"
    tc = json.loads(rec_file.read_text(encoding="utf-8"))
    tc["actions"].append({
        "action_type": "count_elements",
        "page_url": grid_url,
        "page_id": 0,
        "locator_profile": {
            "css_path": None,
            "xpath": "//div[@class='product-card']",
            "element_label": "cards",
            "element_kind": "element",
            "element_section": "",
        },
        "bounding_box": None,
        "count_as": None,
        "expected_count": 50,
        "name": "Count all cards (old-style)",
        "origin": "added",
    })
    rec_file.write_text(json.dumps(tc, indent=2), encoding="utf-8")

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        dash = ctx.new_page()
        dash.goto(APP_URL, wait_until="networkidle")
        dash.wait_for_timeout(500)
        card = dash.locator(".recording-card", has_text="zz_s6b_oldstyle").first
        card.scroll_into_view_if_needed()
        with ctx.expect_page() as log_page_info:
            card.get_by_role("button", name="Replay", exact=True).click()
        log_page = log_page_info.value
        log_page.wait_for_load_state("domcontentloaded")
        log_page.wait_for_selector("text=Replay finished.", timeout=60000)
        log_page.wait_for_timeout(500)
        log_page.screenshot(path=str(SHOT_DIR / "s6b_oldstyle_replay.png"), full_page=True)
        log_text = log_page.inner_text("body")
        log_page.close()
        print(log_text)
        results["S6b_oldstyle_replay"] = log_text
        b.close()

    # ============ S6c: plain click + fill recording, unaffected ============
    print("\n=== S6c: plain click+fill recording, replay unaffected ===")
    rec_path_c = seed_recording("zz_s6c_clickfill", grid_url)
    rec_file_c = BASE / "storage" / "recordings" / "zz_s6c_clickfill.json"
    tc_c = json.loads(rec_file_c.read_text(encoding="utf-8"))
    tc_c["actions"].append({
        "action_type": "click",
        "page_url": grid_url,
        "page_id": 0,
        "locator_profile": {
            "css_path": None,
            "xpath": "//div[@class='product-card'][1]",
            "element_label": "card",
            "element_kind": "element",
            "element_section": "",
        },
        "bounding_box": None,
        "value": None,
        "name": "Click first card",
        "origin": "added",
    })
    rec_file_c.write_text(json.dumps(tc_c, indent=2), encoding="utf-8")

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        dash = ctx.new_page()
        dash.goto(APP_URL, wait_until="networkidle")
        dash.wait_for_timeout(500)
        card = dash.locator(".recording-card", has_text="zz_s6c_clickfill").first
        card.scroll_into_view_if_needed()
        with ctx.expect_page() as log_page_info:
            card.get_by_role("button", name="Replay", exact=True).click()
        log_page = log_page_info.value
        log_page.wait_for_load_state("domcontentloaded")
        log_page.wait_for_selector("text=Replay finished.", timeout=60000)
        log_page.wait_for_timeout(500)
        log_page.screenshot(path=str(SHOT_DIR / "s6c_clickfill_replay.png"), full_page=True)
        log_text = log_page.inner_text("body")
        log_page.close()
        print(log_text)
        results["S6c_clickfill_replay"] = log_text
        b.close()

with open(SHOT_DIR / "results_s6.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, default=str)

print("\n\n=== S6 SUMMARY ===")
print(json.dumps(results, indent=2, default=str))
