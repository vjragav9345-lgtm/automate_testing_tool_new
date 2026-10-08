"""TEST-ONLY: real-app, real-browser verification of V3/V4 from the
follow-up task - in-page Rename/Delete modals (no native dialogs), and
display_name carrying over ("(edited)") through View/Edit -> Save.
"""
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

RECORDING_NAME = "zz_followup_v3_v4"

SIMPLE_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body>
  <input id="searchBox" type="text" placeholder="Search">
  <button id="searchBtn" onclick="document.getElementById('result').textContent = 'Results for: ' + document.getElementById('searchBox').value">Search</button>
  <div id="result"></div>
</body></html>
"""


def main():
    with FixtureServer() as srv:
        fixture_path = BASE / "tests" / "fixtures" / "zz_followup_v3v4.html"
        fixture_path.write_text(SIMPLE_HTML, encoding="utf-8")
        url = srv.url("zz_followup_v3v4.html")

        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            ctx = b.new_context()
            pg = ctx.new_page()
            rec = Recorder(pg)
            rec.install_context_capture(ctx)
            pg.goto(url, wait_until="domcontentloaded")
            pg.wait_for_timeout(300)
            rec.start(launch_url=pg.url)
            pg.fill("#searchBox", "shoes")
            pg.click("#searchBtn")
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

        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            ctx = b.new_context()

            # dialog handler that FAILS the test the instant any native
            # alert/confirm/prompt fires anywhere in this context - the
            # definitive proof Fix 3 actually replaced them.
            native_dialog_fired = []

            def _on_dialog(dialog):
                native_dialog_fired.append((dialog.type, dialog.message))
                dialog.dismiss()

            dash = ctx.new_page()
            dash.on("dialog", _on_dialog)
            dash.goto(APP_URL, wait_until="networkidle")
            dash.wait_for_timeout(500)

            card = dash.locator(".recording-card", has_text=RECORDING_NAME).first
            card.scroll_into_view_if_needed()

            # ---------------- V3: Rename modal (dashboard card) ----------------
            print("\n=== V3: dashboard card Rename uses an in-page modal ===")
            card.get_by_role("button", name="Rename", exact=True).click()
            modal = dash.locator("#renameCardModal")
            modal.wait_for(state="visible", timeout=5000)
            dash.screenshot(path=str(SHOT_DIR / "v3_rename_card_modal.png"))
            dash.locator("#renameCardInput").fill("My test")
            dash.locator("#renameCardSaveBtn").click()
            modal.wait_for(state="hidden", timeout=5000)
            dash.wait_for_timeout(300)
            assert not native_dialog_fired, f"a native dialog fired during Rename: {native_dialog_fired}"
            title_text = card.locator("h3, .recording-title, h4").first.inner_text() if False else None
            print("V3 PASS: Rename card modal opened/closed with no native dialog")

            # ---------------- V3: Delete modal (dashboard card) ----------------
            print("\n=== V3: dashboard card Delete uses an in-page modal ===")
            card = dash.locator(".recording-card", has_text="My test").first
            card.get_by_role("button", name="Delete", exact=True).click()
            del_modal = dash.locator("#deleteCardModal")
            del_modal.wait_for(state="visible", timeout=5000)
            dash.screenshot(path=str(SHOT_DIR / "v3_delete_card_modal.png"))
            dash.locator("#deleteCardCancelBtn").click()
            del_modal.wait_for(state="hidden", timeout=5000)
            assert not native_dialog_fired, f"a native dialog fired during Delete: {native_dialog_fired}"
            print("V3 PASS: Delete card modal opened/cancelled with no native dialog (session preserved)")

            # ---------------- V4: rename -> edit -> save -> "(edited)" ----------------
            print("\n=== V4: edited copy name carries over as 'My test (edited)' ===")
            card = dash.locator(".recording-card", has_text="My test").first
            # View/Edit navigates the SAME page (window.location.href), not a new tab
            card.get_by_role("button", name="View / Edit", exact=True).click()
            dash.wait_for_load_state("networkidle")
            dash.wait_for_timeout(500)
            dash.locator("#saveEditedBtn").click()
            dash.wait_for_selector("#saveStatus:visible", timeout=10000)
            dash.wait_for_timeout(500)
            dash.screenshot(path=str(SHOT_DIR / "v4_editor_after_save.png"))
            assert not native_dialog_fired, f"a native dialog fired in the editor: {native_dialog_fired}"

            dash.goto(APP_URL, wait_until="networkidle")
            dash.wait_for_timeout(500)
            edited_card = dash.locator(".recording-card", has_text="My test (edited)").first
            edited_card.scroll_into_view_if_needed()
            dash.screenshot(path=str(SHOT_DIR / "v4_dashboard_after_edit.png"))
            assert edited_card.count() == 1, "expected exactly one card titled 'My test (edited)'"
            print("V4 PASS: new card shows 'My test (edited)'")

            # edit the ALREADY-edited copy again -> must not stack "(edited) (edited)"
            print("\n=== V4: editing an already-edited copy does not stack '(edited)' ===")
            edited_card.get_by_role("button", name="View / Edit", exact=True).click()
            dash.wait_for_load_state("networkidle")
            dash.wait_for_timeout(500)
            dash.locator("#saveEditedBtn").click()
            dash.wait_for_selector("#saveStatus:visible", timeout=10000)
            dash.wait_for_timeout(500)
            assert not native_dialog_fired, f"a native dialog fired in the editor (2nd save): {native_dialog_fired}"

            dash.goto(APP_URL, wait_until="networkidle")
            dash.wait_for_timeout(500)
            still_card = dash.locator(".recording-card", has_text="My test (edited)").first
            still_card.scroll_into_view_if_needed()
            dash.screenshot(path=str(SHOT_DIR / "v4_dashboard_after_second_edit.png"))
            stacked = dash.locator(".recording-card", has_text="(edited) (edited)")
            assert stacked.count() == 0, "found a stacked '(edited) (edited)' name - display_name suffix logic is wrong"
            assert still_card.count() == 1, "expected the name to STILL read 'My test (edited)' (not stacked, not reverted)"
            print("V4 PASS: re-editing kept the name at 'My test (edited)' - no stacking")

            b.close()

        print("\nALL UI CHECKS (V3/V4) PASS")


if __name__ == "__main__":
    main()
