"""TEST-ONLY: real-app, real-browser verification of BUG 3 (URL
wildcard matching for dynamic ids). T3 in the task's own VERIFY section:
replay a recording whose "press Enter -> navigate to a fresh per-request
id" step 3 times, expecting PASS every time with the id note.
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
SHOT_DIR = Path("tests/_probe_out/ui_verify_bug3")
SHOT_DIR.mkdir(parents=True, exist_ok=True)

results = {}

with FixtureServer() as srv:
    chat_url = srv.url("zz_bug3_chat.html")

    stale = BASE / "storage" / "recordings" / "edited" / "zz_bug3_chat_edited.json"
    stale.unlink(missing_ok=True)

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        pg = ctx.new_page()
        rec = Recorder(pg)
        rec.install_context_capture(ctx)
        pg.goto(chat_url, wait_until="domcontentloaded")
        pg.wait_for_timeout(300)
        rec.start(launch_url=pg.url)
        pg.wait_for_timeout(300)
        pg.locator("#msgBox").fill("hello there")
        pg.wait_for_timeout(200)
        pg.locator("#msgBox").press("Enter")
        pg.wait_for_timeout(500)
        print("recorded URL after Enter:", pg.url)
        tc = rec.stop(name="zz_bug3_chat", stop_reason="terminal_enter")
        drafts = (rec._draft_path, rec._draft_jsonl_path)
        b.close()
    for d in drafts:
        if d:
            Path(d).unlink(missing_ok=True)
    tc["name"] = "zz_bug3_chat"
    repository.save_recording(tc)
    print("recorded steps:", json.dumps(tc.get("actions"), indent=2, default=str))

    # replay 3 times - each time, the live fixture mints a DIFFERENT
    # random id than the one baked into the recording
    for attempt in range(1, 4):
        print(f"\n=== T3 replay attempt {attempt} ===")
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            ctx = b.new_context()
            dash = ctx.new_page()
            dash.goto(APP_URL, wait_until="networkidle")
            dash.wait_for_timeout(500)
            card = dash.locator(".recording-card", has_text="zz_bug3_chat").first
            card.scroll_into_view_if_needed()
            with ctx.expect_page() as log_page_info:
                card.get_by_role("button", name="Replay", exact=True).click()
            log_page = log_page_info.value
            log_page.wait_for_load_state("domcontentloaded")
            log_page.wait_for_selector("text=Replay finished.", timeout=60000)
            log_page.wait_for_timeout(500)
            log_page.screenshot(path=str(SHOT_DIR / f"t3_attempt{attempt}.png"), full_page=True)
            log_text = log_page.inner_text("body")
            log_page.close()
            print(log_text)
            results[f"attempt_{attempt}"] = log_text
            b.close()

with open(SHOT_DIR / "results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, default=str)

print("\n\n=== SUMMARY ===")
for k, v in results.items():
    passed = "PASS" in v and "FAIL" not in v.split("PASS")[0]
    print(f"{k}: {'contains PASS line' if 'PASS' in v else 'NO PASS FOUND'}")
