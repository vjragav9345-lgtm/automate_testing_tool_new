"""TEST-ONLY: real-app, real-browser verification of BUG 2 (Validate
Value Range crash fix). T2 in the task's own VERIFY section.
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
SHOT_DIR = Path("tests/_probe_out/ui_verify_bug2")
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


def do_pick_and_wait(editor, drive_fn):
    editor.locator("#modalPickElementBtn").click()
    editor.wait_for_timeout(2000)
    drive_fn()
    editor.wait_for_function(
        "document.getElementById('modalXpath').value.trim().length > 0",
        timeout=25000,
    )
    editor.wait_for_timeout(1000)
    try:
        test_drive("close_browser")
    except Exception:
        pass
    editor.wait_for_timeout(500)


results = {}

with FixtureServer() as srv:
    cards_url = srv.url("zz_bug2_cards.html")

    # ============ T2a: price-only spans, correct range -> PASS ============
    print("\n=== T2a: price-only spans, range [100,1000] -> PASS ===")
    rec_path = seed_recording("zz_bug2_price_pass", cards_url)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        editor = ctx.new_page()
        editor.goto(f"{APP_URL}/recording/edit?path={rec_path}", wait_until="networkidle")
        editor.wait_for_timeout(500)
        editor.locator("#addActionBtn").click()
        editor.locator("#addActionModal").wait_for(state="visible")
        editor.locator("#modalActionType").select_option("validate_value_range")
        editor.wait_for_timeout(200)
        editor.locator("#modalField_min_value").fill("100")
        editor.locator("#modalField_max_value").fill("1000")
        do_pick_and_wait(
            editor,
            lambda: test_drive("drag_over_xpath", xpath="//span[@class='price']"),
        )
        preview_text = editor.locator("#modalValidateResult").inner_text()
        print("preview:", preview_text)
        editor.screenshot(path=str(SHOT_DIR / "t2a_preview.png"))
        results["T2a_preview"] = preview_text
        editor.locator("#modalSaveBtn").click()
        editor.locator("#addActionModal").wait_for(state="hidden", timeout=5000)
        editor.wait_for_timeout(300)
        editor.locator("#saveEditedBtn").click()
        editor.wait_for_selector("#saveStatus:visible", timeout=10000)
        b.close()

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        dash = ctx.new_page()
        dash.goto(APP_URL, wait_until="networkidle")
        dash.wait_for_timeout(500)
        card = dash.locator(".recording-card", has_text="zz_bug2_price_pass_edited").first
        card.scroll_into_view_if_needed()
        with ctx.expect_page() as log_page_info:
            card.get_by_role("button", name="Replay", exact=True).click()
        log_page = log_page_info.value
        log_page.wait_for_load_state("domcontentloaded")
        log_page.wait_for_selector("text=Replay finished.", timeout=60000)
        log_page.wait_for_timeout(500)
        log_page.screenshot(path=str(SHOT_DIR / "t2a_replay.png"), full_page=True)
        log_text = log_page.inner_text("body")
        log_page.close()
        print(log_text)
        results["T2a_replay"] = log_text
        b.close()

    # ============ T2b: price-only spans, wrong range -> per-item FAIL reason ============
    print("\n=== T2b: price-only spans, range [1000,10000] -> per-item FAIL ===")
    rec_path_b = seed_recording("zz_bug2_price_fail", cards_url)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        editor = ctx.new_page()
        editor.goto(f"{APP_URL}/recording/edit?path={rec_path_b}", wait_until="networkidle")
        editor.wait_for_timeout(500)
        editor.locator("#addActionBtn").click()
        editor.locator("#addActionModal").wait_for(state="visible")
        editor.locator("#modalActionType").select_option("validate_value_range")
        editor.wait_for_timeout(200)
        editor.locator("#modalField_min_value").fill("1000")
        editor.locator("#modalField_max_value").fill("10000")
        do_pick_and_wait(
            editor,
            lambda: test_drive("drag_over_xpath", xpath="//span[@class='price']"),
        )
        editor.locator("#modalSaveBtn").click()
        editor.locator("#addActionModal").wait_for(state="hidden", timeout=5000)
        editor.wait_for_timeout(300)
        editor.locator("#saveEditedBtn").click()
        editor.wait_for_selector("#saveStatus:visible", timeout=10000)
        b.close()

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        dash = ctx.new_page()
        dash.goto(APP_URL, wait_until="networkidle")
        dash.wait_for_timeout(500)
        card = dash.locator(".recording-card", has_text="zz_bug2_price_fail_edited").first
        card.scroll_into_view_if_needed()
        with ctx.expect_page() as log_page_info:
            card.get_by_role("button", name="Replay", exact=True).click()
        log_page = log_page_info.value
        log_page.wait_for_load_state("domcontentloaded")
        log_page.wait_for_selector("text=Replay finished.", timeout=60000)
        log_page.wait_for_timeout(500)
        log_page.screenshot(path=str(SHOT_DIR / "t2b_replay.png"), full_page=True)
        log_text = log_page.inner_text("body")
        log_page.close()
        print(log_text)
        results["T2b_replay"] = log_text
        b.close()

    # ============ T2c: whole cards (ambiguous) -> no crash, plain reason + editor warning ============
    print("\n=== T2c: whole cards, ambiguous multi-number text -> no crash ===")
    rec_path_c = seed_recording("zz_bug2_wholecard", cards_url)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        editor = ctx.new_page()
        editor.goto(f"{APP_URL}/recording/edit?path={rec_path_c}", wait_until="networkidle")
        editor.wait_for_timeout(500)
        editor.locator("#addActionBtn").click()
        editor.locator("#addActionModal").wait_for(state="visible")
        editor.locator("#modalActionType").select_option("validate_value_range")
        editor.wait_for_timeout(200)
        editor.locator("#modalField_min_value").fill("1000")
        editor.locator("#modalField_max_value").fill("10000")
        do_pick_and_wait(
            editor,
            lambda: test_drive("drag_over_xpath", xpath="//div[@class='ambiguous-card']"),
        )
        preview_text = editor.locator("#modalValidateResult").inner_text()
        print("preview:", preview_text)
        editor.screenshot(path=str(SHOT_DIR / "t2c_preview.png"))
        results["T2c_preview"] = preview_text
        editor.locator("#modalSaveBtn").click()
        editor.locator("#addActionModal").wait_for(state="hidden", timeout=5000)
        editor.wait_for_timeout(300)
        editor.locator("#saveEditedBtn").click()
        editor.wait_for_selector("#saveStatus:visible", timeout=10000)
        b.close()

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        dash = ctx.new_page()
        dash.goto(APP_URL, wait_until="networkidle")
        dash.wait_for_timeout(500)
        card = dash.locator(".recording-card", has_text="zz_bug2_wholecard_edited").first
        card.scroll_into_view_if_needed()
        with ctx.expect_page() as log_page_info:
            card.get_by_role("button", name="Replay", exact=True).click()
        log_page = log_page_info.value
        log_page.wait_for_load_state("domcontentloaded")
        log_page.wait_for_selector("text=Replay finished.", timeout=60000)
        log_page.wait_for_timeout(500)
        log_page.screenshot(path=str(SHOT_DIR / "t2c_replay.png"), full_page=True)
        log_text = log_page.inner_text("body")
        log_page.close()
        print(log_text)
        results["T2c_replay"] = log_text
        b.close()

with open(SHOT_DIR / "results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, default=str)

print("\n\n=== SUMMARY ===")
print(json.dumps(results, indent=2, default=str))
