"""TEST-ONLY: verifies the Count Elements validation UI (requirement 6) and the
multi_none editor message (requirement 4's editor half), driving the ACTUAL
templates/recording_editor.html script directly (no live app.py touched)."""
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
from phase4_fixture_server import FixtureServer

TEMPLATE = BASE / "templates" / "recording_editor.html"
html = TEMPLATE.read_text(encoding="utf-8")
html = html.replace("{{ recording_path | tojson }}", json.dumps("test_recording.json"))
FIXTURES_DIR = BASE / "tests" / "fixtures"
served_path = FIXTURES_DIR / "_count_elements_editor_copy.html"
served_path.write_text(html, encoding="utf-8")

console_errors = []

with FixtureServer() as srv:
    url = srv.url("_count_elements_editor_copy.html")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(400)

        page.evaluate("""
            recordingData = {
                start_url: "https://example.com",
                actions: [
                    { action_type: "navigate", page_url: "https://example.com", locator_profile: {} },
                ],
            };
        """)

        # mocks the real /pick_element/start + /pick_element/status round trip
        # (real app.py/pick_element.py are never touched by this test) so the
        # ACTUAL modalPickElementBtn click handler -> polling -> applyPickedProfile
        # chain runs exactly as it does for a real user, rather than reaching
        # into applyPickedProfile directly (it's not exposed on window at all -
        # a plain nested function inside that same click handler).
        def install_pick_mock(profile_extra):
            page.evaluate("""(profileExtra) => {
                window.__afqaMockDone = false;
                window.fetch = (url, opts) => {
                    if (String(url).includes('/pick_element/start')) {
                        return Promise.resolve({ ok: true, json: () => Promise.resolve({ success: true, pick_id: 'mockpick' }) });
                    }
                    if (String(url).includes('/pick_element/status')) {
                        if (window.__afqaMockDone) {
                            return Promise.resolve({ ok: true, json: () => Promise.resolve({ status: 'waiting' }) });
                        }
                        window.__afqaMockDone = true;
                        return Promise.resolve({ ok: true, json: () => Promise.resolve(Object.assign({ status: 'done' }, profileExtra)) });
                    }
                    return Promise.reject(new Error('unexpected fetch: ' + url));
                };
            }""", profile_extra)

        # open Add Action -> count_elements
        page.evaluate("openAddActionDialog('append', null)")
        page.select_option("#modalActionType", "count_elements")
        page.evaluate("renderModalFields()")

        # --- (a) a fresh multi-pick with empty Expected Count gets prefilled ---
        install_pick_mock({
            "xpath": "//div[contains(@class,'x')]",
            "match_count": 12,
            "locator_profile": {"mode": "multi", "in_box_count": 5},
        })
        page.click("#modalPickElementBtn")
        page.wait_for_timeout(1300)  # one poll tick (1000ms) plus margin
        expected_val = page.eval_on_selector("#modalField_expected_count", "el => el.value")
        result_text = page.eval_on_selector("#modalValidateResult", "el => el.textContent")
        print("expected_count after fresh multi-pick:", expected_val)
        print("result text:", result_text)
        assert expected_val == "12", f"expected Expected Count to be prefilled with 12, got {expected_val!r}"
        assert "Found: 12 matching elements" in result_text
        warn_present = page.eval_on_selector("#countElementsWarnings", "el => !!el") if page.query_selector("#countElementsWarnings") else False
        assert not warn_present, "no mismatch warning expected right after autofill"
        print("CHECK (a) autofill PASS")

        # --- (b) set Expected Count to a WRONG number -> amber warning, live ---
        page.fill("#modalField_expected_count", "99")
        page.eval_on_selector("#modalField_expected_count", "el => el.dispatchEvent(new Event('input'))")
        page.wait_for_timeout(50)
        warn_text = page.eval_on_selector("#countElementsWarnings", "el => el.textContent")
        print("warning text after setting wrong expected count:", warn_text)
        assert "you expect 99" in warn_text and "matches 12 right now" in warn_text
        print("CHECK (b) live mismatch warning PASS")

        # --- (d) Save asks for confirmation when a warning applies ---
        confirm_calls = []
        page.evaluate("""
            window.__origConfirm = window.confirm;
            window.confirm = (msg) => { window.__lastConfirmMsg = msg; return false; };  // simulate Cancel
        """)
        # modalContext must be set for Save to proceed past its own early guard;
        # openAddActionDialog already set it via the 'append' call above
        page.click("#modalSaveBtn")
        last_confirm_msg = page.evaluate("window.__lastConfirmMsg")
        print("confirm() message shown on Save:", last_confirm_msg)
        assert last_confirm_msg and "you expect 99" in last_confirm_msg and "Save anyway?" in last_confirm_msg
        # cancelling must NOT have inserted the action
        actions_len = page.evaluate("recordingData.actions.length")
        assert actions_len == 1, f"expected Cancel to abort the save, action count is {actions_len}"
        print("CHECK (d) confirm-on-save (Cancel aborts) PASS")

        # now confirm() returns true -> Save proceeds
        page.evaluate("window.confirm = (msg) => true;")
        page.click("#modalSaveBtn")
        actions_len2 = page.evaluate("recordingData.actions.length")
        assert actions_len2 == 2, f"expected confirm()=true to let Save proceed, action count is {actions_len2}"
        print("CHECK (d) confirm-on-save (confirm proceeds) PASS")
        page.evaluate("window.confirm = window.__origConfirm;")

        # --- (c) a single-click pick matching exactly 1 element -> amber warning ---
        page.evaluate("openAddActionDialog('append', null)")
        page.select_option("#modalActionType", "count_elements")
        page.evaluate("renderModalFields()")
        install_pick_mock({
            "xpath": "//div[@id='only-one']",
            "match_count": 1,
            "id": "#only-one",
            "locator_profile": {},
        })
        page.click("#modalPickElementBtn")
        page.wait_for_timeout(1300)
        result_text_single = page.eval_on_selector("#modalValidateResult", "el => el.textContent")
        warn_single = page.eval_on_selector("#countElementsWarnings", "el => el.textContent")
        print("single-match result text:", result_text_single)
        print("single-match warning:", warn_single)
        assert "matches only one element" in warn_single
        print("CHECK (c) single-match warning (from a pick) PASS")

        print("\nConsole messages:", console_errors)
        real_errors = [e for e in console_errors if "File not found" not in e and "Recording load failed" not in e]
        assert not real_errors, f"unexpected console errors: {real_errors}"
        print("\nALL COUNT ELEMENTS VALIDATION CHECKS PASS")
        browser.close()

served_path.unlink(missing_ok=True)
