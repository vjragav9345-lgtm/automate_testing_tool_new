"""TEST-ONLY: real-app, real-browser V7 regression check - replays a
plain click+fill recording (R8) and the user's own existing
session_20260930_013237_edited recording through the REAL running app's
dashboard UI, via its real Replay button and live log popup. Never
renames, edits or deletes the user's recording - Replay only.
"""
import sys
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

R8_NAME = "zz_followup_v7_r8"


def replay_via_ui(ctx, dash, recording_name_substring, shot_prefix):
    dash.goto(APP_URL, wait_until="networkidle")
    dash.wait_for_timeout(500)
    card = dash.locator(".recording-card", has_text=recording_name_substring).first
    card.scroll_into_view_if_needed()
    with ctx.expect_page() as log_page_info:
        card.get_by_role("button", name="Replay", exact=True).click()
    log_page = log_page_info.value
    log_page.wait_for_load_state("domcontentloaded")
    log_page.wait_for_selector("text=Replay finished.", timeout=300000)
    log_page.wait_for_timeout(500)
    log_page.screenshot(path=str(SHOT_DIR / f"{shot_prefix}_live_log.png"), full_page=True)
    log_text = log_page.inner_text("body")
    log_page.close()
    return log_text


def main():
    with FixtureServer() as srv:
        fixture_path = BASE / "tests" / "fixtures" / "r8_regression_local.html"
        url = srv.url("r8_regression_local.html")

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
            tc = rec.stop(name=R8_NAME, stop_reason="terminal_enter")
            drafts = (rec._draft_path, rec._draft_jsonl_path)
            b.close()
        for d in drafts:
            if d:
                Path(d).unlink(missing_ok=True)

        tc["name"] = R8_NAME
        repository.save_recording(tc)
        print("Seeded R8 recording.")

        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            ctx = b.new_context()
            dash = ctx.new_page()

            print("\n=== V7: R8 (plain fill+click) regression, via real app ===")
            log_text_r8 = replay_via_ui(ctx, dash, R8_NAME, "v7_r8")
            print(log_text_r8)
            assert "Replay matched the recording: all 3 steps passed." in log_text_r8, (
                f"R8 regression: expected a clean pass with no warnings, got: {log_text_r8!r}"
            )
            assert "WARNING" not in log_text_r8, f"R8 regression: unexpected WARNING: {log_text_r8!r}"
            print("V7 PASS: R8 still passes cleanly with no warnings")

            print("\n=== V7: user's real session_20260930_013237_edited, via real app ===")
            log_text_user = replay_via_ui(ctx, dash, "session_20260930_013237_edited", "v7_user_edited")
            print(log_text_user)
            # No prior baseline captured for this exact code state - the
            # regression bar here is "runs to completion without crashing,
            # status line present" (never renamed/edited/deleted this
            # recording). Any pass/fail counts are reported, not asserted,
            # since Myntra reachability from this environment is the
            # dominant factor in this recording's outcome, unrelated to
            # any change in this task.
            assert "Replay finished." in log_text_user, f"user recording: replay did not finish cleanly: {log_text_user[:400]!r}"

            b.close()

        print("\nALL UI CHECKS (V7) DONE")


if __name__ == "__main__":
    main()
