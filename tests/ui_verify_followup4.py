"""TEST-ONLY: real-app, real-browser verification of V1-V10 for the
4-part follow-up task (navigate-readiness false warning, warning count
consistency, count-summary missing-label warning + label suggestions,
meaningful auto step names). Drives the REAL running Flask app
(http://127.0.0.1:5099, started with AUTOFLOW_TEST_HOOKS=1) via
Playwright, including the REAL Pick Element flow: the picker itself runs
in a server-launched browser this test cannot control directly, so real
clicks/drags inside it are injected via the project's own existing
test-drive hook (app.py's /api/recordings/pick_element/_test_drive,
recorder/pick_element.py's _TEST_DRIVE_QUEUE) - the SAME mechanism a
prior task built specifically for this purpose. Every element actually
picked is a REAL DOM element in a REAL browser; only the "a human moves
the mouse" step is replaced with this queued callable.
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
SHOT_DIR = Path("tests/_probe_out/ui_verify4")
SHOT_DIR.mkdir(parents=True, exist_ok=True)

RECORDING_NAME = "zz_followup4_main"

native_dialog_fired = []


def _on_dialog(dialog):
    native_dialog_fired.append((dialog.type, dialog.message))
    dialog.dismiss()


def test_drive(action, **kw):
    import urllib.request
    body = json.dumps({"action": action, **kw}).encode("utf-8")
    req = urllib.request.Request(
        APP_URL + "/api/recordings/pick_element/_test_drive",
        data=body, headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def add_action_via_pick(editor, action_type, pick_xpath, drag=False, extra_fields=None, shot_name=None):
    """Drives the REAL Add Action modal: opens it, selects the action
    type, clicks Pick Element (launching the REAL server-side picker
    browser), test-drives a real click/drag inside THAT browser via the
    existing test-drive hook, waits for the editor's own real polling to
    receive the result, fills any extra fields, validates (if a locator
    field exists) and saves."""
    editor.locator("#addActionBtn").click()
    editor.locator("#addActionModal").wait_for(state="visible")
    editor.locator("#modalActionType").select_option(action_type)
    editor.wait_for_timeout(200)

    editor.locator("#modalPickElementBtn").click()
    # give the picker browser a moment to actually launch before driving it
    editor.wait_for_timeout(2500)
    if drag:
        test_drive("drag_over_xpath", xpath=pick_xpath)
    else:
        test_drive("click_xpath", xpath=pick_xpath)

    # the editor's own JS polls /api/recordings/pick_element/status on an
    # interval and fills modalXpath once "done" arrives - wait for that
    editor.wait_for_function(
        "document.getElementById('modalXpath').value.trim().length > 0",
        timeout=20000,
    )
    editor.wait_for_timeout(500)

    # CONFIRMED REAL BUG in this test harness (not the app): a picker
    # browser stays open after a pick completes (a real user closes it
    # manually once happy - see the "locked" status message) - leaving it
    # open let its OWN still-running wait loop keep polling the SAME
    # global _TEST_DRIVE_QUEUE, stealing a LATER pick's own test-drive
    # click meant for a different, newer session. Closing it immediately
    # after each pick keeps only one session's wait loop alive at a time.
    try:
        test_drive("close_browser")
    except Exception:
        pass
    editor.wait_for_timeout(500)

    if extra_fields:
        for key, value in extra_fields.items():
            editor.locator(f"#modalField_{key}").fill(str(value))

    if editor.locator("#modalValidateBtn").is_visible():
        editor.locator("#modalValidateBtn").click()
        editor.wait_for_timeout(1500)

    if shot_name:
        editor.screenshot(path=str(SHOT_DIR / shot_name))

    editor.locator("#modalSaveBtn").click()
    editor.locator("#addActionModal").wait_for(state="hidden", timeout=5000)
    editor.wait_for_timeout(300)


def main():
    results = {}
    with FixtureServer() as srv:
        url = srv.url("zz_followup4_listing.html")

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

        stale_edited = BASE / "storage" / "recordings" / "edited" / f"{RECORDING_NAME}_edited.json"
        stale_edited.unlink(missing_ok=True)
        tc["name"] = RECORDING_NAME
        repository.save_recording(tc)
        recording_rel_path = f"storage/recordings/{RECORDING_NAME}.json"
        print("Seeded recording, 1 navigate action.")

        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            ctx = b.new_context()
            editor = ctx.new_page()
            editor.on("dialog", _on_dialog)
            editor.on("pageerror", lambda exc: print("[browser-pageerror]", exc))
            editor.goto(f"{APP_URL}/recording/edit?path={recording_rel_path}", wait_until="networkidle")
            editor.wait_for_timeout(500)

            # ============= V1/V8: Count Elements via DRAG pick =============
            print("\n=== V1/V8: Count Elements via real drag-pick ===")
            add_action_via_pick(
                editor, "count_elements",
                "//div[@class='product-card']",
                drag=True,
                extra_fields={"count_as": "product_counts"},
                shot_name="v1_v8_drag_pick_modal.png",
            )

            # ============= V5: radio in parent <label> =============
            print("=== V5: radio option text in a parent <label> ===")
            add_action_via_pick(
                editor, "click",
                "//label[contains(., 'Girls')]/div",
                shot_name="v5_radio_pick_modal.png",
            )

            # ============= V6: checkbox with a volatile count =============
            print("=== V6: checkbox with a count in its label ===")
            add_action_via_pick(
                editor, "check",
                "//input[@id='brandCheckbox']",
                shot_name="v6_checkbox_pick_modal.png",
            )

            # ============= V7a: link =============
            print("=== V7a: a link ===")
            add_action_via_pick(
                editor, "click",
                "//a[@id='viewAllLink']",
                shot_name="v7a_link_pick_modal.png",
            )

            # ============= V7b: button =============
            print("=== V7b: a button ===")
            add_action_via_pick(
                editor, "click",
                "//button[@id='applyBtn']",
                shot_name="v7b_button_pick_modal.png",
            )

            # ============= V7c: fill with placeholder =============
            print("=== V7c: fill with a placeholder ===")
            add_action_via_pick(
                editor, "fill",
                "//input[@id='searchInput']",
                extra_fields={"value": "shoes"},
                shot_name="v7c_fill_pick_modal.png",
            )

            # ============= V8b: manually typed XPath with a text predicate =============
            print("=== V8b: manually-typed XPath with a text() predicate (no pick) ===")
            editor.locator("#addActionBtn").click()
            editor.locator("#addActionModal").wait_for(state="visible")
            editor.locator("#modalActionType").select_option("click")
            editor.locator("#modalXpath").fill("//button[normalize-space(text())='Apply']")
            editor.locator("#modalXpath").dispatch_event("input")
            editor.locator("#modalValidateBtn").click()
            editor.wait_for_timeout(1500)
            editor.screenshot(path=str(SHOT_DIR / "v8b_manual_xpath_modal.png"))
            editor.locator("#modalSaveBtn").click()
            editor.locator("#addActionModal").wait_for(state="hidden", timeout=5000)
            editor.wait_for_timeout(300)

            # ============= V3: two Count Elements + Count Summary (blank labels) =============
            print("\n=== V3: two Count Elements + Count Summary (blank labels) ===")
            add_action_via_pick(
                editor, "count_elements",
                "//div[@class='product-card']",
                drag=True,
                extra_fields={"count_as": "before_filter"},
            )
            add_action_via_pick(
                editor, "count_elements",
                "//div[@class='product-card']",
                drag=True,
                extra_fields={"count_as": "after_filter"},
            )
            editor.locator("#addActionBtn").click()
            editor.locator("#addActionModal").wait_for(state="visible")
            editor.locator("#modalActionType").select_option("count_summary")
            editor.wait_for_timeout(200)
            editor.screenshot(path=str(SHOT_DIR / "v3_count_summary_modal_blank.png"))
            editor.locator("#modalSaveBtn").click()
            editor.locator("#addActionModal").wait_for(state="hidden", timeout=5000)
            editor.wait_for_timeout(300)

            # ============= V4: Count Summary with a WRONG label + suggestions =============
            print("=== V4: Count Summary with a wrong label; suggestions shown ===")
            editor.locator("#addActionBtn").click()
            editor.locator("#addActionModal").wait_for(state="visible")
            editor.locator("#modalActionType").select_option("count_summary")
            editor.wait_for_timeout(200)
            suggestions_text = editor.locator("#countSummaryLabelSuggestions").inner_text()
            print("Label suggestions shown:", suggestions_text)
            editor.screenshot(path=str(SHOT_DIR / "v4_label_suggestions.png"))
            editor.locator("#modalField_labels").fill("summary_count")
            editor.locator("#modalSaveBtn").click()
            editor.locator("#addActionModal").wait_for(state="hidden", timeout=5000)
            editor.wait_for_timeout(300)

            # ============= V9: names in the editor (screenshot + text) =============
            print("\n=== V9: names as shown in the editor ===")
            editor.screenshot(path=str(SHOT_DIR / "v9_editor_actions_list.png"), full_page=True)
            actions_list_text = editor.locator("#actionsList").inner_text()
            print(actions_list_text)

            editor.locator("#saveEditedBtn").click()
            editor.wait_for_selector("#saveStatus:visible", timeout=10000)
            editor.wait_for_timeout(300)
            assert not native_dialog_fired, f"a native dialog fired while adding steps: {native_dialog_fired}"
            editor.close()

            # ============= Replay via the real dashboard, check live log/dashboard/report =============
            print("\n=== Replay via real dashboard - checking live log/dashboard/report ===")
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
            log_page.wait_for_selector("text=Replay finished.", timeout=60000)
            log_page.wait_for_timeout(500)
            log_page.screenshot(path=str(SHOT_DIR / "replay_live_log_full.png"), full_page=True)
            log_text = log_page.inner_text("body")
            log_page.close()
            print("\n--- LIVE LOG TEXT ---")
            print(log_text)

            edited_card.locator(".validation-badge").wait_for(timeout=15000)
            dash.wait_for_timeout(500)
            edited_card.locator(".validation-toggle").click()
            dash.wait_for_timeout(300)
            edited_card.scroll_into_view_if_needed()
            dash.screenshot(path=str(SHOT_DIR / "replay_dashboard_card_full.png"), full_page=True)
            dash_card_text = edited_card.inner_text()
            print("\n--- DASHBOARD CARD TEXT ---")
            print(dash_card_text)

            report_link = edited_card.locator("a", has_text="View Screenshots by Stage")
            b.close()

        with open(SHOT_DIR / "actions_list.txt", "w", encoding="utf-8") as f:
            f.write(actions_list_text)
        with open(SHOT_DIR / "live_log.txt", "w", encoding="utf-8") as f:
            f.write(log_text)
        with open(SHOT_DIR / "dashboard_card.txt", "w", encoding="utf-8") as f:
            f.write(dash_card_text)

        print("\n=== RAW OUTPUTS SAVED to tests/_probe_out/ui_verify4/ ===")


if __name__ == "__main__":
    main()
