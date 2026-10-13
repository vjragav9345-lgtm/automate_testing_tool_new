"""TEST-ONLY: real-app, real-browser verification of BUG 4's generic
safety net (STEP B) - T4 in the task's own VERIFY section, using a
fixture that mimics a lightbox since the specific 134-action Myntra
recording described in the bug report could not be located anywhere in
the project (see the investigation report).
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
SHOT_DIR = Path("tests/_probe_out/ui_verify_bug4")
SHOT_DIR.mkdir(parents=True, exist_ok=True)

results = {}

with FixtureServer() as srv:
    lb_url = srv.url("zz_bug4_lightbox.html")

    # Seed a navigate-only recording, then manually append the two real
    # steps: click the product image (opens the lightbox), then click
    # Continue Shopping WITHOUT a close-lightbox step in between -
    # simulating "the close wasn't captured" (or failed to resolve on
    # replay), leaving the lightbox open and covering the next target -
    # exactly BUG 4's own reported symptom.
    stale = BASE / "storage" / "recordings" / "edited" / "zz_bug4_lightbox_edited.json"
    stale.unlink(missing_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        pg = ctx.new_page()
        rec = Recorder(pg)
        rec.install_context_capture(ctx)
        pg.goto(lb_url, wait_until="domcontentloaded")
        pg.wait_for_timeout(300)
        rec.start(launch_url=pg.url)
        pg.wait_for_timeout(300)
        tc = rec.stop(name="zz_bug4_lightbox", stop_reason="terminal_enter")
        drafts = (rec._draft_path, rec._draft_jsonl_path)
        b.close()
    for d in drafts:
        if d:
            Path(d).unlink(missing_ok=True)

    tc["name"] = "zz_bug4_lightbox"
    tc["start_url"] = lb_url
    tc["actions"].append({
        "action_type": "click",
        "page_url": lb_url,
        "page_id": 0,
        "locator_profile": {"css_path": None, "xpath": "//*[@id='productImg']", "text": "Product Image"},
        "bounding_box": None,
        "name": "Click product image",
        "origin": "added",
    })
    tc["actions"].append({
        "action_type": "click",
        "page_url": lb_url,
        "page_id": 0,
        "locator_profile": {"css_path": None, "xpath": "//*[@id='continueBtn']", "text": "Continue Shopping"},
        "bounding_box": None,
        "name": "Click continue (lightbox left open)",
        "origin": "added",
    })
    repository.save_recording(tc)
    print("recorded actions:", json.dumps(tc["actions"], indent=2, default=str))

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        dash = ctx.new_page()
        dash.goto(APP_URL, wait_until="networkidle")
        dash.wait_for_timeout(500)
        card = dash.locator(".recording-card", has_text="zz_bug4_lightbox").first
        card.scroll_into_view_if_needed()
        with ctx.expect_page() as log_page_info:
            card.get_by_role("button", name="Replay", exact=True).click()
        log_page = log_page_info.value
        log_page.wait_for_load_state("domcontentloaded")
        log_page.wait_for_selector("text=Replay finished.", timeout=60000)
        log_page.wait_for_timeout(500)
        log_page.screenshot(path=str(SHOT_DIR / "t4_replay.png"), full_page=True)
        log_text = log_page.inner_text("body")
        log_page.close()
        print(log_text)
        results["T4_replay"] = log_text
        b.close()

with open(SHOT_DIR / "results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, default=str)

print("\n\n=== SUMMARY ===")
print(json.dumps(results, indent=2, default=str))
