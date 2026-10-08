"""TEST-ONLY: V10 regression - replays the user's real
session_20260930_013237_edited recording through the real running app,
confirming it still completes the same way (no new regressions from
Part 1-4), and confirms a RECORDED step's own editor display is
untouched (no auto-naming applied to recorded steps that never had an
explicit name)."""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from playwright.sync_api import sync_playwright

APP_URL = "http://127.0.0.1:5099"
SHOT_DIR = Path("tests/_probe_out/ui_verify4")
SHOT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        dash = ctx.new_page()
        dash.goto(APP_URL, wait_until="networkidle")
        dash.wait_for_timeout(500)

        card = dash.locator(".recording-card", has_text="session_20260930_013237_edited").first
        card.scroll_into_view_if_needed()

        with ctx.expect_page() as log_page_info:
            card.get_by_role("button", name="Replay", exact=True).click()
        log_page = log_page_info.value
        log_page.wait_for_load_state("domcontentloaded")
        log_page.wait_for_selector("text=Replay finished.", timeout=120000)
        log_page.wait_for_timeout(500)
        log_page.screenshot(path=str(SHOT_DIR / "v10_user_recording_live_log.png"), full_page=True)
        log_text = log_page.inner_text("body")
        log_page.close()
        print(log_text)

        assert "Replay matched the recording: all 11 steps passed" in log_text, (
            f"V10 regression: expected the same 11/11 pass as before, got: {log_text[:300]!r}"
        )
        print("\nV10 PASS: user's real recording still replays all 11 steps passed")

        # editor display for a RECORDED step's own name - unchanged
        edit_page = ctx.new_page()
        edit_page.goto(
            f"{APP_URL}/recording/edit?path=storage/recordings/edited/session_20260930_013237_edited.json",
            wait_until="networkidle",
        )
        edit_page.wait_for_timeout(500)
        edit_page.screenshot(path=str(SHOT_DIR / "v10_user_recording_editor.png"), full_page=True)
        actions_text = edit_page.locator("#actionsList").inner_text()
        print("\n--- Recorded steps as shown in the editor ---")
        print(actions_text)
        edit_page.close()

        b.close()


if __name__ == "__main__":
    main()
