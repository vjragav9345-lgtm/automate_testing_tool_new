"""TEST-ONLY: real-app, real-browser verification of V1/V2 from the
follow-up task. Seeds a recording via the same Recorder/repository the
real app uses (storage/recordings/), then drives the ACTUAL running
Flask app (http://127.0.0.1:5099) and its real dashboard UI via
Playwright: click Run, watch the real live-log popup (real SSE stream)
and the real dashboard card polling. Screenshots saved under
tests/_probe_out/ui_verify/.
"""
import json
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
from phase4_fixture_server import FixtureServer
from recorder.record_session import Recorder
from storage import repository

APP_URL = "http://127.0.0.1:5099"
SHOT_DIR = Path("tests/_probe_out/ui_verify")
SHOT_DIR.mkdir(parents=True, exist_ok=True)

# Hardcoded (not read from the fixture files on disk) so a prior partial
# run that left the fixture file mutated can never corrupt this run's own
# idea of "original" vs "changed" - CONFIRMED REAL bug in an earlier
# version of this script: reading ORIGINAL_HTML from the file at import
# time picked up a previous run's own "changed" overwrite, silently
# recording a page whose "original" and "changed" content were identical.
ORIGINAL_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body>
  <input type="checkbox" id="filterCheckbox" name="filterCheckbox" aria-label="In Stock (418534)">
  <label id="filterLabel" for="filterCheckbox">In Stock (418534)</label>
</body></html>
"""
CHANGED_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body>
  <input type="checkbox" id="filterCheckbox" name="filterCheckbox" aria-label="In Stock (418542)">
  <label id="filterLabel" for="filterCheckbox">In Stock (418542)</label>
</body></html>
"""

RECORDING_NAME = "zz_followup_v1_v2_checkbox"


def main():
    with FixtureServer() as srv:
        fixture_path = BASE / "tests" / "fixtures" / "checkbox_volatile_number.html"
        # ensure ORIGINAL content while recording
        fixture_path.write_text(ORIGINAL_HTML, encoding="utf-8")
        url = srv.url("checkbox_volatile_number.html")

        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            ctx = b.new_context()
            pg = ctx.new_page()
            rec = Recorder(pg)
            rec.install_context_capture(ctx)
            pg.goto(url, wait_until="domcontentloaded")
            pg.wait_for_timeout(300)
            rec.start(launch_url=pg.url)
            pg.check("#filterCheckbox")
            pg.wait_for_timeout(300)
            tc = rec.stop(name=RECORDING_NAME, stop_reason="terminal_enter")
            drafts = (rec._draft_path, rec._draft_jsonl_path)
            b.close()
        for d in drafts:
            if d:
                Path(d).unlink(missing_ok=True)

        tc["name"] = RECORDING_NAME
        path = repository.save_recording(tc)
        print("Seeded recording at:", path)

        # ---- Drive the REAL running app's dashboard UI ----
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            ctx = b.new_context()
            dash = ctx.new_page()
            dash.goto(APP_URL, wait_until="networkidle")
            dash.wait_for_timeout(500)

            card = dash.locator(".recording-card", has_text=RECORDING_NAME).first
            card.scroll_into_view_if_needed()
            dash.screenshot(path=str(SHOT_DIR / "v0_dashboard_before.png"), full_page=True)

            # ---------- V2: unchanged page, replay, expect no warning ----------
            print("\n=== V2: replay against UNCHANGED page ===")
            with ctx.expect_page() as new_page_info:
                card.get_by_role("button", name="Replay", exact=True).click()
            log_page = new_page_info.value
            log_page.wait_for_load_state("domcontentloaded")

            log_page.wait_for_selector("text=Replay finished.", timeout=30000)
            log_page.wait_for_timeout(500)
            log_page.screenshot(path=str(SHOT_DIR / "v2_live_log.png"), full_page=True)
            log_text_v2 = log_page.inner_text("body")
            log_page.close()

            # dash-side polling (runRecording's own /api/test/run/progress
            # loop, separate from the live-log popup's own SSE stream)
            # settles a moment after the live log reports done - wait for
            # its own "TEST PASSED"/"TEST FAILED" badge to appear rather
            # than a fixed sleep.
            card.locator(".validation-badge").wait_for(timeout=15000)
            dash.wait_for_timeout(300)
            card.scroll_into_view_if_needed()
            dash.screenshot(path=str(SHOT_DIR / "v2_dashboard_card.png"), full_page=True)

            assert "WARNING" not in log_text_v2, f"V2: unexpected WARNING in live log: {log_text_v2[:500]!r}"
            print("V2 PASS: no WARNING in live log for the unchanged page")

            # ---------- V1: changed page, replay, expect yellow WARNING ----------
            print("\n=== V1: replay against CHANGED page (non-text strategy) ===")
            fixture_path.write_text(CHANGED_HTML, encoding="utf-8")

            with ctx.expect_page() as new_page_info2:
                card.get_by_role("button", name="Replay", exact=True).click()
            log_page2 = new_page_info2.value
            log_page2.wait_for_load_state("domcontentloaded")
            log_page2.wait_for_selector("text=Replay finished.", timeout=30000)
            log_page2.wait_for_timeout(500)
            log_page2.screenshot(path=str(SHOT_DIR / "v1_live_log.png"), full_page=True)
            log_text_v1 = log_page2.inner_text("body")
            log_html_v1 = log_page2.content()
            log_page2.close()

            card.locator(".validation-badge").wait_for(timeout=15000)
            dash.wait_for_timeout(300)
            card.scroll_into_view_if_needed()
            dash.screenshot(path=str(SHOT_DIR / "v1_dashboard_card.png"), full_page=True)
            dash_card_text = card.inner_text()

            b.close()

        assert "WARNING" in log_text_v1, f"V1: expected WARNING in live log, got: {log_text_v1[:800]!r}"
        assert "Warning:" in log_text_v1 and "recording:" in log_text_v1, f"V1: expected value-changed note, got: {log_text_v1[:800]!r}"
        assert 'class="status-warning"' in log_html_v1, "V1: expected the status-warning CSS class to be applied"
        assert "1 warning" in dash_card_text, f"V1: expected dashboard card to show a warning count - card text: {dash_card_text!r}"
        print("V1 PASS: live log shows yellow WARNING with the value-changed note; dashboard card shows the warning count")
        print("\nALL UI CHECKS (V1/V2) PASS")


if __name__ == "__main__":
    main()
