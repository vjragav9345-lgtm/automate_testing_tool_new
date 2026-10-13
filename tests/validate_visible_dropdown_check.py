"""TEST-ONLY: verifies the Validate Visible "Expect element to be" dropdown change
without touching the live app.py instance already running on :5000 (which won't
have picked up the template edit anyway, since Flask is running with debug=False -
no auto-reload). Serves the ACTUAL, edited templates/recording_editor.html directly
(Jinja's {{ recording_path | tojson }} substituted with a literal), then drives the
real Add/Edit Action modal exactly as a person would, watching for console errors."""
import json
import re
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
served_path = FIXTURES_DIR / "_validate_visible_editor_copy.html"
served_path.write_text(html, encoding="utf-8")

console_errors = []

with FixtureServer() as srv:
    url = srv.url("_validate_visible_editor_copy.html")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(500)  # let the (failing, offline) initial fetch settle harmlessly

        # inject a fake recordingData with one visible and one (synthetic - none
        # exist in real storage, confirmed separately) hidden validate_visible step
        page.evaluate("""
            recordingData = {
                start_url: "https://example.com",
                actions: [
                    { action_type: "navigate", page_url: "https://example.com", locator_profile: {} },
                    { action_type: "validate_visible", page_url: "https://example.com", expected_state: "visible",
                      locator_profile: { xpath: "//div[@id='a']", tag: "div" } },
                    { action_type: "validate_visible", page_url: "https://example.com", expected_state: "hidden",
                      locator_profile: { xpath: "//div[@id='b']", tag: "div" } },
                ],
            };
        """)

        # ---- 1. Adding a NEW Validate Visible step shows only "Visible" ----
        page.evaluate("openAddActionDialog('append', null)")
        page.select_option("#modalActionType", "validate_visible")
        page.evaluate("renderModalFields()")
        options = page.eval_on_selector_all(
            "#modalField_expected_state option",
            "els => els.map(e => ({value: e.value, text: e.textContent}))",
        )
        print("New-step dropdown options:", options)
        assert options == [{"value": "visible", "text": "Visible"}], f"expected only Visible, got {options}"
        default_value = page.eval_on_selector("#modalField_expected_state", "el => el.value")
        assert default_value == "visible"
        print("CHECK 1 (new step, options) PASS")

        # ---- 2. Editing an EXISTING "visible" step still works ----
        page.evaluate("openAddActionDialog('edit', 1)")
        options2 = page.eval_on_selector_all(
            "#modalField_expected_state option",
            "els => els.map(e => ({value: e.value, text: e.textContent}))",
        )
        value2 = page.eval_on_selector("#modalField_expected_state", "el => el.value")
        print("Edit-existing-visible dropdown options:", options2, "value:", value2)
        assert options2 == [{"value": "visible", "text": "Visible"}]
        assert value2 == "visible"
        print("CHECK 2 (edit existing 'visible' step) PASS")

        # ---- 3. Opening an existing step saved with "hidden" ----
        page.evaluate("openAddActionDialog('edit', 2)")
        options3 = page.eval_on_selector_all(
            "#modalField_expected_state option",
            "els => els.map(e => ({value: e.value, text: e.textContent}))",
        )
        value3 = page.eval_on_selector("#modalField_expected_state", "el => el.value")
        print("Edit-existing-hidden dropdown options:", options3, "value:", value3)
        assert value3 == "hidden", f"the saved 'hidden' value must still be shown/preserved, got {value3!r}"
        assert any(o["value"] == "hidden" for o in options3), "a 'hidden' option must be added back for this edit"
        print("CHECK 3 (edit existing 'hidden' step opens without error, value preserved) PASS")

        # confirm NOT silently rewriting to visible: close without touching the
        # field, and check the dropdown's own reported value is still "hidden"
        # (i.e. what Save would actually read for this field)
        still_hidden = page.eval_on_selector("#modalField_expected_state", "el => el.value")
        assert still_hidden == "hidden", "must not silently fall back to 'visible' without the user changing it"
        print("CHECK 3b (no silent conversion to visible) PASS")

        # the harness itself has no real Flask backend behind it (no
        # /api/recordings/view, no /static/* assets) - those 404s/load
        # failures are expected artifacts of THIS test setup, not of the
        # dropdown change; a real error would name one of the functions
        # this test actually exercises (openAddActionDialog,
        # renderModalFields, modalField_expected_state, ...)
        real_errors = [
            e for e in console_errors
            if "File not found" not in e and "Recording load failed" not in e
        ]
        print("\nAll console messages (expected harness-only 404s included):", console_errors)
        assert not real_errors, f"expected no console errors from the actual dropdown code, got: {real_errors}"
        print("\nALL CHECKS PASS - no console errors from the dropdown change itself")
        browser.close()

served_path.unlink(missing_ok=True)
