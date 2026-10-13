"""TEST-ONLY: real-app, real-browser verification of FIX 2 (page
mismatch detection + settled screenshot + recovery), using local static
fixtures (tests/fixtures/zz_fix2_mismatch.html + product.html/search.html/
slowproduct.html) - no live sites.
"""
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from playwright.sync_api import sync_playwright
from phase4_fixture_server import FixtureServer
from recorder.record_session import Recorder
from storage import repository

APP_URL = "http://127.0.0.1:5099"
SHOT_DIR = Path("tests/_probe_out/ui_verify_fix2")
SHOT_DIR.mkdir(parents=True, exist_ok=True)

results = {}


def seed_navigate_only(name, url):
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
    return tc


def replay_and_capture(name, shot_name):
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        dash = ctx.new_page()
        dash.goto(APP_URL, wait_until="networkidle")
        dash.wait_for_timeout(500)
        card = dash.locator(".recording-card", has_text=name).first
        card.scroll_into_view_if_needed()
        with ctx.expect_page() as log_page_info:
            card.get_by_role("button", name="Replay", exact=True).click()
        log_page = log_page_info.value
        log_page.wait_for_load_state("domcontentloaded")
        log_page.wait_for_selector("text=Replay finished.", timeout=60000)
        log_page.wait_for_timeout(500)
        log_page.screenshot(path=str(SHOT_DIR / shot_name), full_page=True)
        log_text = log_page.inner_text("body")
        log_page.close()
        b.close()
    return log_text


with FixtureServer() as srv:
    home_url = srv.url("zz_fix2_mismatch.html")
    product_url = srv.url("product.html?id=B0HF7WTGSR")
    search_url = srv.url("search.html?k=computers")
    slowproduct_url = srv.url("slowproduct.html?id=B0HF7WTGSR")

    # ============ T1: correct destination, tracking params differ -> PASS ============
    print("\n=== T1: correct destination (tracking params differ) -> PASS ===")
    tc1 = seed_navigate_only("zz_fix2_t1_correct", home_url)
    tc1["actions"].append({
        "action_type": "click", "page_url": home_url, "page_id": 0,
        "locator_profile": {"xpath": "//*[@id='correctLink']", "css_path": None, "text": "Product (correct)"},
        "bounding_box": None, "name": "Click product link", "origin": "added",
    })
    tc1["actions"].append({
        "action_type": "navigate",
        "page_url": product_url + "&utm_source=DIFFERENT&ref_=other",  # recorded WITH different tracking params
        "page_id": 0, "value": None, "locator_profile": None, "bounding_box": None,
        "caused_by_timestamp": "2026-01-01T00:00:00.000Z", "name": "Navigate", "origin": "added",
    })
    (BASE / "storage" / "recordings" / "zz_fix2_t1_correct.json").write_text(
        json.dumps(tc1, indent=2, default=str), encoding="utf-8"
    )
    log1 = replay_and_capture("zz_fix2_t1_correct", "t1_replay.png")
    print(log1)
    results["T1_correct_destination"] = log1

    # ============ T2: wrong destination -> PAGE_MISMATCH, recovers via navigate ============
    print("\n=== T2: wrong destination -> PAGE_MISMATCH, recovers via navigate ===")
    tc2 = seed_navigate_only("zz_fix2_t2_mismatch", home_url)
    tc2["actions"].append({
        "action_type": "click", "page_url": home_url, "page_id": 0,
        "locator_profile": {"xpath": "//*[@id='wrongLink']", "css_path": None, "text": "Search results (wrong destination)"},
        "bounding_box": None, "name": "Click product link (actually wrong)", "origin": "added",
    })
    tc2["actions"].append({
        "action_type": "navigate", "page_url": product_url, "page_id": 0,
        "value": None, "locator_profile": None, "bounding_box": None,
        "caused_by_timestamp": "2026-01-01T00:00:00.000Z", "name": "Navigate", "origin": "added",
    })
    # a follow-up navigate step AFTER the mismatched one - tests recovery
    tc2["actions"].append({
        "action_type": "navigate", "page_url": search_url, "page_id": 0,
        "value": None, "locator_profile": None, "bounding_box": None,
        "name": "Navigate onward", "origin": "added",
    })
    (BASE / "storage" / "recordings" / "zz_fix2_t2_mismatch.json").write_text(
        json.dumps(tc2, indent=2, default=str), encoding="utf-8"
    )
    log2 = replay_and_capture("zz_fix2_t2_mismatch", "t2_replay.png")
    print(log2)
    results["T2_wrong_destination_recovery"] = log2

    # ============ T3: slow/spinner target -> screenshot only after settle ============
    print("\n=== T3: spinner-delayed wrong destination -> settled screenshot ===")
    tc3 = seed_navigate_only("zz_fix2_t3_spinner", home_url)
    tc3["actions"].append({
        "action_type": "click", "page_url": home_url, "page_id": 0,
        "locator_profile": {"xpath": "//*[@id='wrongLink']", "css_path": None, "text": "Search results (wrong destination)"},
        "bounding_box": None, "name": "Click product link (actually wrong, slow)", "origin": "added",
    })
    tc3["actions"].append({
        "action_type": "navigate", "page_url": slowproduct_url, "page_id": 0,
        "value": None, "locator_profile": None, "bounding_box": None,
        "caused_by_timestamp": "2026-01-01T00:00:00.000Z", "name": "Navigate", "origin": "added",
    })
    (BASE / "storage" / "recordings" / "zz_fix2_t3_spinner.json").write_text(
        json.dumps(tc3, indent=2, default=str), encoding="utf-8"
    )
    log3 = replay_and_capture("zz_fix2_t3_spinner", "t3_replay.png")
    print(log3)
    results["T3_spinner_settled_screenshot"] = log3


with open(SHOT_DIR / "results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, default=str)

print("\n\n=== SUMMARY ===")
print(json.dumps(results, indent=2, default=str))
