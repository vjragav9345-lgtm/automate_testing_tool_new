"""TEST-ONLY: real-app, real-browser verification of the drag-select
Count Elements fix (S1-S6). Drives the REAL running Flask app
(AUTOFLOW_TEST_HOOKS=1) and the REAL, server-launched Pick Element
browser via the project's own existing test-drive hook, extended in this
task with a "drag_hold_scroll" action for S2's scrolling-during-drag
case.
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


def seed_recording(name, url):
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
        tc = rec.stop(name=name, stop_reason="terminal_enter")
        drafts = (rec._draft_path, rec._draft_jsonl_path)
        b.close()
    for d in drafts:
        if d:
            Path(d).unlink(missing_ok=True)
    tc["name"] = name
    repository.save_recording(tc)
    return f"storage/recordings/{name}.json"


def open_add_action_modal(editor, action_type="count_elements"):
    editor.locator("#addActionBtn").click()
    editor.locator("#addActionModal").wait_for(state="visible")
    editor.locator("#modalActionType").select_option(action_type)
    editor.wait_for_timeout(200)


def do_pick_and_wait(editor, drive_fn):
    editor.locator("#modalPickElementBtn").click()
    editor.wait_for_timeout(2500)
    drive_fn()
    editor.wait_for_function(
        "document.getElementById('modalXpath').value.trim().length > 0",
        timeout=25000,
    )
    editor.wait_for_timeout(800)
    try:
        test_drive("close_browser")
    except Exception:
        pass
    editor.wait_for_timeout(500)


def read_modal_state(editor):
    return {
        "xpath": editor.locator("#modalXpath").input_value(),
        "validate_text": editor.locator("#modalValidateResult").inner_text(),
        "expected_count": editor.locator("#modalField_expected_count").input_value(),
    }


results = {}

with FixtureServer() as srv:
    grid_url = srv.url("zz_drag_grid.html")
    tallgrid_url = srv.url("zz_drag_tallgrid.html")
    virt_url = srv.url("zz_drag_virtualized.html")

    # ================= S1: drag over ~25 cards, no scrolling =================
    print("\n=== S1: drag over 25 cards, no scrolling ===")
    rec_path = seed_recording("zz_drag_s1", grid_url)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        editor = ctx.new_page()
        editor.goto(f"{APP_URL}/recording/edit?path={rec_path}", wait_until="networkidle")
        editor.wait_for_timeout(500)
        open_add_action_modal(editor)
        do_pick_and_wait(
            editor,
            lambda: test_drive("drag_over_xpath", xpath="//div[@class='product-card'][position()<=25]"),
        )
        state = read_modal_state(editor)
        print(state)
        editor.screenshot(path=str(SHOT_DIR / "s1_modal.png"))
        results["S1"] = state
        editor.locator("#modalSaveBtn").click()
        editor.locator("#addActionModal").wait_for(state="hidden", timeout=5000)
        editor.wait_for_timeout(300)
        editor.locator("#saveEditedBtn").click()
        editor.wait_for_selector("#saveStatus:visible", timeout=10000)
        b.close()

    # ================= S3: drag over 2 cards =================
    print("\n=== S3: drag over 2 cards ===")
    rec_path_s3 = seed_recording("zz_drag_s3", grid_url)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        editor = ctx.new_page()
        editor.goto(f"{APP_URL}/recording/edit?path={rec_path_s3}", wait_until="networkidle")
        editor.wait_for_timeout(500)
        open_add_action_modal(editor)
        do_pick_and_wait(
            editor,
            lambda: test_drive("drag_over_xpath", xpath="//div[@class='product-card'][position()<=2]"),
        )
        state = read_modal_state(editor)
        print(state)
        editor.screenshot(path=str(SHOT_DIR / "s3_modal.png"))
        results["S3"] = state
        b.close()

    # ================= S4: Validate after pick shows the same number =================
    print("\n=== S4: Validate after pick shows the same number ===")
    rec_path_s4 = seed_recording("zz_drag_s4", grid_url)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        editor = ctx.new_page()
        editor.goto(f"{APP_URL}/recording/edit?path={rec_path_s4}", wait_until="networkidle")
        editor.wait_for_timeout(500)
        open_add_action_modal(editor)
        do_pick_and_wait(
            editor,
            lambda: test_drive("drag_over_xpath", xpath="//div[@class='product-card'][position()<=10]"),
        )
        after_pick = read_modal_state(editor)
        editor.locator("#modalValidateBtn").click()
        editor.wait_for_timeout(1500)
        after_validate = read_modal_state(editor)
        print("after pick:", after_pick)
        print("after validate:", after_validate)
        editor.screenshot(path=str(SHOT_DIR / "s4_modal_after_validate.png"))
        results["S4"] = {"after_pick": after_pick, "after_validate": after_validate}
        editor.locator("#modalField_count_as").fill("s4_count") if editor.locator("#modalField_count_as").count() else None
        editor.locator("#modalSaveBtn").click()
        editor.locator("#addActionModal").wait_for(state="hidden", timeout=5000)
        editor.wait_for_timeout(300)
        editor.locator("#saveEditedBtn").click()
        editor.wait_for_selector("#saveStatus:visible", timeout=10000)
        b.close()

    # ================= S5: replay the saved step -> PASS with same count =================
    print("\n=== S5: replay S1's saved step ===")
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        dash = ctx.new_page()
        dash.goto(APP_URL, wait_until="networkidle")
        dash.wait_for_timeout(500)
        card = dash.locator(".recording-card", has_text="zz_drag_s1_edited").first
        card.scroll_into_view_if_needed()
        with ctx.expect_page() as log_page_info:
            card.get_by_role("button", name="Replay", exact=True).click()
        log_page = log_page_info.value
        log_page.wait_for_load_state("domcontentloaded")
        log_page.wait_for_selector("text=Replay finished.", timeout=60000)
        log_page.wait_for_timeout(500)
        log_page.screenshot(path=str(SHOT_DIR / "s5_live_log.png"), full_page=True)
        log_text = log_page.inner_text("body")
        log_page.close()
        print(log_text)
        results["S5"] = log_text
        b.close()

    # ================= S2: drag ~25-30 cards while auto-scrolling =================
    # Primary S2 case per the task's own bug report: a REGULAR scrolling
    # page (no virtualization) where items scroll out of the viewport but
    # stay in the DOM - this is what "the count includes the cards that
    # scrolled out of view" describes. Uses a 2-column tall grid so a
    # ~420ms hold at the auto-scroll edge sweeps ~25-30 cards, spanning
    # both columns (width_px=240) so the drag isn't artificially confined
    # to a single column.
    print("\n=== S2: drag while scrolling (regular page, no virtualization) ===")
    rec_path_s2 = seed_recording("zz_drag_s2", tallgrid_url)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        editor = ctx.new_page()
        editor.goto(f"{APP_URL}/recording/edit?path={rec_path_s2}", wait_until="networkidle")
        editor.wait_for_timeout(500)
        open_add_action_modal(editor)
        do_pick_and_wait(
            editor,
            lambda: test_drive(
                "drag_hold_scroll",
                start_xpath="//div[@class='product-card'][1]",
                hold_ms=420,
                width_px=240,
            ),
        )
        state = read_modal_state(editor)
        print(state)
        editor.screenshot(path=str(SHOT_DIR / "s2_modal.png"))
        results["S2"] = state
        editor.locator("#modalField_count_as").fill("s2_count") if editor.locator("#modalField_count_as").count() else None
        editor.locator("#modalSaveBtn").click()
        editor.locator("#addActionModal").wait_for(state="hidden", timeout=5000)
        editor.wait_for_timeout(300)
        editor.locator("#saveEditedBtn").click()
        editor.wait_for_selector("#saveStatus:visible", timeout=10000)
        b.close()

    # ================= S2b (bonus): true virtualized list, items unmounted =================
    # Beyond what S2 requires: a react-window-style list that actually
    # REMOVES off-screen items from the DOM during the drag. Documents the
    # sanctioned fallback path (STEP 3: "if not, fall back... and show a
    # yellow note") for the extreme case where some selected items are no
    # longer live in the DOM by the time the XPath is re-verified.
    print("\n=== S2b (bonus): drag while scrolling a TRUE virtualized list ===")
    rec_path_s2b = seed_recording("zz_drag_s2b", virt_url)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        editor = ctx.new_page()
        editor.goto(f"{APP_URL}/recording/edit?path={rec_path_s2b}", wait_until="networkidle")
        editor.wait_for_timeout(500)
        open_add_action_modal(editor)
        do_pick_and_wait(
            editor,
            lambda: test_drive(
                "drag_hold_scroll",
                start_xpath="//div[@data-item-index='1']",
                hold_ms=800,
            ),
        )
        state = read_modal_state(editor)
        print(state)
        editor.screenshot(path=str(SHOT_DIR / "s2b_modal.png"))
        results["S2b"] = state
        b.close()

with open(SHOT_DIR / "results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, default=str)

print("\n\n=== SUMMARY ===")
print(json.dumps(results, indent=2, default=str))
