"""TEST-ONLY: real-app, real-browser verification of FIX 1 (Validate
Value Range rewrite: dropped-price regression, role tagging, value_hint,
per-item replay reporting, editor bounds validation).
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
SHOT_DIR = Path("tests/_probe_out/ui_verify_fix1")
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
        "document.getElementById('modalXpath').value.trim().length > 0", timeout=25000,
    )
    editor.wait_for_timeout(1000)
    try:
        test_drive("close_browser")
    except Exception:
        pass
    editor.wait_for_timeout(500)


results = {}

with FixtureServer() as srv:
    fixture_url = srv.url("zz_fix1_cards.html")

    # ============ Editor: bounds validation (Save-blocking) ============
    print("\n=== Editor bounds validation ===")
    rec_path = seed_recording("zz_fix1_bounds", fixture_url)
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

        # both empty -> Save disabled
        both_empty_disabled = editor.locator("#modalSaveBtn").is_disabled()
        # min > max -> error shown
        editor.locator("#modalField_min_value").fill("100")
        editor.locator("#modalField_max_value").fill("10")
        editor.wait_for_timeout(100)
        min_gt_max_error = editor.locator("#modalValueRangeError").text_content()
        min_gt_max_disabled = editor.locator("#modalSaveBtn").is_disabled()
        # fix it -> only the locator gate should block Save now
        editor.locator("#modalField_max_value").fill("1000")
        editor.wait_for_timeout(100)
        fixed_error = editor.locator("#modalValueRangeError").is_visible()
        editor.screenshot(path=str(SHOT_DIR / "bounds_validation.png"))
        results["bounds_validation"] = {
            "both_empty_disabled": both_empty_disabled,
            "min_gt_max_error": min_gt_max_error,
            "min_gt_max_disabled": min_gt_max_disabled,
            "fixed_error_still_visible": fixed_error,
        }
        b.close()

    # ============ Multi-card: auto_price + per-item PASS/FAIL (direct) ============
    # Bypasses the drag-select test-drive helper (a row-wrapping artifact
    # of that HELPER's own bounding-box math only covered 2 of the 4
    # cards - unrelated to this fix) and constructs the step directly,
    # same pattern as this session's own S6b/S6c regression checks. The
    # pick-time preview path (value_range_preview) is already covered by
    # the mrp_preview/bounds_validation checks elsewhere in this file.
    print("\n=== Multi-card auto_price + per-item reporting ===")
    rec_path2 = seed_recording("zz_fix1_multi", fixture_url)
    rec_file2 = BASE / "storage" / "recordings" / "zz_fix1_multi.json"
    tc2 = json.loads(rec_file2.read_text(encoding="utf-8"))
    tc2["actions"].append({
        "action_type": "validate_value_range",
        "page_url": fixture_url,
        "page_id": 0,
        "locator_profile": {"css_path": None, "xpath": "//div[@id='grid']/div[@class='product-card']", "text": None},
        "bounding_box": None,
        "min_value": 1000,
        "max_value": 10000,
        "name": "Validate cards is between 1000 and 10000",
        "origin": "added",
    })
    rec_file2.write_text(json.dumps(tc2, indent=2), encoding="utf-8")

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        dash = ctx.new_page()
        dash.goto(APP_URL, wait_until="networkidle")
        dash.wait_for_timeout(500)
        card = dash.locator(".recording-card", has_text="zz_fix1_multi").first
        card.scroll_into_view_if_needed()
        with ctx.expect_page() as log_page_info:
            card.get_by_role("button", name="Replay", exact=True).click()
        log_page = log_page_info.value
        log_page.wait_for_load_state("domcontentloaded")
        log_page.wait_for_selector("text=Replay finished.", timeout=60000)
        log_page.wait_for_timeout(500)
        log_page.screenshot(path=str(SHOT_DIR / "multi_replay.png"), full_page=True)
        log_text = log_page.inner_text("body")
        log_page.close()
        print(log_text)
        results["multi_replay"] = log_text
        b.close()

    # ============ value_hint=mrp on the same multi-card pick ============
    print("\n=== value_hint=mrp ===")
    rec_path3 = seed_recording("zz_fix1_mrp", fixture_url)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        editor = ctx.new_page()
        editor.goto(f"{APP_URL}/recording/edit?path={rec_path3}", wait_until="networkidle")
        editor.wait_for_timeout(500)
        editor.locator("#addActionBtn").click()
        editor.locator("#addActionModal").wait_for(state="visible")
        editor.locator("#modalActionType").select_option("validate_value_range")
        editor.wait_for_timeout(200)
        editor.locator("#modalField_min_value").fill("1000")
        editor.locator("#modalField_max_value").fill("3000")
        do_pick_and_wait(
            editor,
            lambda: test_drive("drag_over_xpath", xpath="//div[@id='grid']/div[@class='product-card']"),
        )
        # set the hint AFTER picking - triggers the auto-re-validate wired
        # to the value_hint select's own "change" listener
        editor.locator("#modalField_value_hint").select_option("mrp")
        editor.wait_for_timeout(1500)
        preview_text = editor.locator("#modalValidateResult").inner_text()
        print("preview (mrp hint):", preview_text)
        editor.screenshot(path=str(SHOT_DIR / "mrp_preview.png"))
        results["mrp_preview"] = preview_text
        b.close()

with open(SHOT_DIR / "results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, default=str)

print("\n\n=== SUMMARY ===")
print(json.dumps(results, indent=2, default=str))
