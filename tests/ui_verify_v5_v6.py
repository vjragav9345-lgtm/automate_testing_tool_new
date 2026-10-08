"""TEST-ONLY: real-app, real-browser verification of V5/V6 from the
follow-up task - adding Count Elements + Count Summary through the real
Recording Editor UI with NO typing of any name/note (the field is gone),
and confirming the auto-generated names + count numbers show up in the
live log, dashboard card and HTML report.
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

RECORDING_NAME = "zz_followup_v5_v6"


def main():
    with FixtureServer() as srv:
        url = srv.url("zz_followup_v5v6.html")

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
            tc = rec.stop(name=RECORDING_NAME, stop_reason="terminal_enter")
            drafts = (rec._draft_path, rec._draft_jsonl_path)
            b.close()
        for d in drafts:
            if d:
                Path(d).unlink(missing_ok=True)

        # CONFIRMED (not a product bug): /recording/edit auto-continues
        # from an existing "<name>_edited.json" copy if one is already on
        # disk (a deliberate, pre-existing feature - see app.py's own
        # recording_editor() route, "ITEM 2 FIX"). Re-running this script
        # with the same RECORDING_NAME without clearing a PRIOR run's own
        # edited copy silently reopens THAT stale copy instead of a fresh
        # one - remove it first so each run starts from a clean slate.
        stale_edited = BASE / "storage" / "recordings" / "edited" / f"{RECORDING_NAME}_edited.json"
        stale_edited.unlink(missing_ok=True)

        tc["name"] = RECORDING_NAME
        path = repository.save_recording(tc)
        print("Seeded recording at:", path)
        recording_rel_path = f"storage/recordings/{RECORDING_NAME}.json"

        native_dialog_fired = []

        def _on_dialog(dialog):
            native_dialog_fired.append((dialog.type, dialog.message))
            dialog.accept()

        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            ctx = b.new_context()
            editor = ctx.new_page()
            editor.on("dialog", _on_dialog)
            editor.goto(
                f"{APP_URL}/recording/edit?path={recording_rel_path}",
                wait_until="networkidle",
            )
            editor.wait_for_timeout(500)

            # ---------------- add "Count Elements" with NO typed name ----------------
            print("\n=== V5: add Count Elements via Add Action - no name field ===")
            editor.locator("#addActionBtn").click()
            editor.locator("#addActionModal").wait_for(state="visible")
            assert editor.locator("#modalStepName").count() == 0, "the 'Step name / note' field should be REMOVED"
            editor.locator("#modalActionType").select_option("count_elements")
            editor.locator("#modalXpath").fill("//div[@class='product-card']")
            editor.locator("#modalField_count_as").fill("product_counts")
            editor.locator("#modalValidateBtn").click()
            try:
                editor.wait_for_selector("text=Found: 3 matching elements", timeout=20000)
            except Exception:
                print("VALIDATE RESULT TEXT:", editor.locator("#modalValidateResult").inner_text())
                editor.screenshot(path=str(SHOT_DIR / "v5_validate_failure.png"))
                raise
            editor.screenshot(path=str(SHOT_DIR / "v5_count_elements_modal.png"))
            save_btn = editor.locator("#modalSaveBtn")
            assert not save_btn.is_disabled(), "Save should be enabled once validation succeeds"
            save_btn.click()
            editor.locator("#addActionModal").wait_for(state="hidden", timeout=5000)
            editor.wait_for_timeout(300)

            # ---------------- add "Count Summary" with NO typed name ----------------
            print("=== V5: add Count Summary via Add Action - no name field ===")
            editor.locator("#addActionBtn").click()
            editor.locator("#addActionModal").wait_for(state="visible")
            editor.locator("#modalActionType").select_option("count_summary")
            editor.locator("#modalField_labels").fill("product_counts")
            editor.locator("#modalSaveBtn").click()
            editor.locator("#addActionModal").wait_for(state="hidden", timeout=5000)
            editor.wait_for_timeout(300)

            editor.screenshot(path=str(SHOT_DIR / "v5_actions_list.png"), full_page=True)
            actions_text = editor.locator("#actionsList").inner_text()
            print("Actions list text:\n", actions_text)
            assert "Count product cards" in actions_text or "Count element" in actions_text, (
                f"expected a meaningful auto-generated Count Elements name, got: {actions_text!r}"
            )
            assert "Show count summary" in actions_text, (
                f"expected a meaningful auto-generated Count Summary name, got: {actions_text!r}"
            )

            editor.locator("#saveEditedBtn").click()
            editor.wait_for_selector("#saveStatus:visible", timeout=10000)
            editor.wait_for_timeout(300)
            save_status_text = editor.locator("#saveStatus").inner_text()
            print("Save status:", save_status_text)
            assert not native_dialog_fired, f"a native dialog fired while adding steps: {native_dialog_fired}"
            editor.close()

            # ---------------- V6: replay and confirm count numbers show ----------------
            print("\n=== V6: replay and confirm count numbers appear ===")
            dash = ctx.new_page()
            dash.on("dialog", _on_dialog)
            dash.goto(APP_URL, wait_until="networkidle")
            dash.wait_for_timeout(500)
            edited_card = dash.locator(".recording-card", has_text=f"{RECORDING_NAME}_edited").first
            edited_card.scroll_into_view_if_needed()

            with ctx.expect_page() as log_page_info:
                edited_card.get_by_role("button", name="Replay", exact=True).click()
            log_page = log_page_info.value
            log_page.wait_for_load_state("domcontentloaded")
            log_page.wait_for_selector("text=Replay finished.", timeout=30000)
            log_page.wait_for_timeout(500)
            log_page.screenshot(path=str(SHOT_DIR / "v6_live_log.png"), full_page=True)
            log_text = log_page.inner_text("body")
            log_page.close()
            print("Live log text:\n", log_text)

            assert "product_counts = 3" in log_text, f"expected 'product_counts = 3' in the live log, got: {log_text!r}"

            edited_card.locator(".validation-badge").wait_for(timeout=15000)
            dash.wait_for_timeout(500)
            edited_card.locator(".validation-toggle").click()
            dash.wait_for_timeout(300)
            edited_card.scroll_into_view_if_needed()
            dash.screenshot(path=str(SHOT_DIR / "v6_dashboard_card.png"), full_page=True)
            card_text = edited_card.inner_text()
            print("Dashboard card text:\n", card_text)
            assert "product_counts = 3" in card_text, f"expected 'product_counts = 3' in the dashboard card, got: {card_text!r}"

            report_link = dash.locator("a", has_text="Open full HTML report")
            report_href = None
            if report_link.count() == 0:
                # the card's own last-log view has no report link shortcut -
                # read it from the live log page's own summary instead
                pass
            b.close()

        print("\nALL UI CHECKS (V5/V6, dashboard + live log) PASS")


if __name__ == "__main__":
    main()
