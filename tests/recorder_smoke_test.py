"""TEST-ONLY smoke test for the FIX 1/2/6 recorder changes - verifies the
new install_context_capture()/start(launch_url=...)/_on_action_binding
plumbing works end-to-end without touching the live Sportzia site or any
real recording session infrastructure (no Flask, no app.py thread).

    venv/Scripts/python.exe tests/recorder_smoke_test.py
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import sync_playwright  # noqa: E402

from recorder.record_session import Recorder  # noqa: E402


MAIN_HTML = """
<html><body>
<button id="btn1">Click Me</button>
<input type="checkbox" id="cb1"> a real checkbox
<div id="stylediv" role="checkbox">a styled checkbox-role div</div>
<div id="radiorow" role="button" style="padding:8px;">
  <input type="radio" id="radio1" name="g1"> pick this option
</div>
<iframe id="child" src="about:blank" style="width:300px;height:200px;"></iframe>
</body></html>
"""


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        recorder = Recorder(page)
        recorder.install_context_capture(context)
        assert recorder._context_capture_installed is True
        print("[smoke] install_context_capture: OK")

        # simulate the "launch URL" flow via set_content (no real
        # navigation needed to exercise the binding/init-script plumbing)
        page.set_content(MAIN_HTML)

        recorder.start(launch_url="https://example.com/launch")
        assert recorder.start_url == "https://example.com/launch", recorder.start_url
        print(f"[smoke] start(launch_url=...): start_url={recorder.start_url!r} OK")

        # attach_page must NOT try to re-register recordAction (would
        # raise) now that context-level capture is installed
        # (page is already attached via start() -> attach_page(is_initial=True);
        # calling attach_page again on the SAME page must stay a no-op)
        page_id_again = recorder.attach_page(page, is_initial=True)
        print(f"[smoke] re-calling attach_page on same page: OK (page_id={page_id_again})")

        # real click on the button - should arrive via the binding, get
        # recorded as a real action (not dropped, not double-registered)
        page.click("#btn1")
        page.wait_for_timeout(800)

        actions = recorder.actions
        print(f"[smoke] captured {len(actions)} action(s) so far")
        assert len(actions) >= 2, "expected at least [navigate, click]"
        assert actions[0]["action_type"] == "navigate"
        assert actions[0]["page_url"] == "https://example.com/launch", (
            f"Step 1 must be the literal launch URL, got {actions[0]['page_url']!r}"
        )
        print("[smoke] Step 1 navigate uses literal launch_url: OK")

        click_actions = [a for a in actions if a.get("action_type") in ("click", "check")]
        assert click_actions, f"no click/check action captured: {actions}"
        print(f"[smoke] button click captured as action_type={click_actions[-1]['action_type']!r}: OK")

        # FIX 2 refinement: a radio INSIDE a role="button" row must still
        # record as "check", not get excluded just because its ancestor
        # row carries role="button" for click-target convenience
        page.click("#radio1")
        page.wait_for_timeout(500)
        radio_action = next((a for a in recorder.actions if (a.get("locator_profile") or {}).get("id") == "#radio1"), None)
        assert radio_action is not None, "radio click was never captured at all"
        assert radio_action["action_type"] == "check", (
            f"radio inside role=button row must record as 'check', got {radio_action['action_type']!r}"
        )
        print("[smoke] radio inside role=button row still records as 'check': OK")

        # FIX 1 item 3: incremental draft flush - the draft file must
        # exist on disk and already contain everything captured so far,
        # without waiting for stop()/save_recording()
        assert recorder._draft_path is not None
        assert recorder._draft_path.exists(), f"draft file was never written: {recorder._draft_path}"
        import json as _json
        draft_data = _json.loads(recorder._draft_path.read_text(encoding="utf-8"))
        assert len(draft_data["actions"]) == len(recorder.actions), (
            f"draft has {len(draft_data['actions'])} actions, memory has {len(recorder.actions)}"
        )
        print(f"[smoke] incremental draft flush: OK ({recorder._draft_path.name}, {len(draft_data['actions'])} actions on disk)")
        recorder._draft_path.unlink()  # clean up this test's own draft file

        # a NEW tab should still attach cleanly (context-level capture
        # already covers it, attach_page's per-page registration must be
        # skipped without raising)
        new_page = context.new_page()
        new_page_id = recorder.attach_page(new_page, is_initial=False)
        print(f"[smoke] new tab attach_page: OK (page_id={new_page_id})")

        browser.close()

    print("\nALL SMOKE CHECKS PASSED")


if __name__ == "__main__":
    main()
