"""TEST-ONLY, fully offline unit tests for the resolver fix (items 6b/6c
of the Phase-1-fix verification) - never touches the live Sportzia site,
no network calls, no Send OTP click, costs nothing against that budget.
Launches a blank local page and feeds it fabricated HTML via
page.set_content() to exercise _find_by_text_tag/_find_by_css/
_find_by_xpath directly, imported from a real, unmodified generate_script()
output (same technique every other test script in this directory uses).

    venv/Scripts/python.exe tests/otp_resolver_unit_tests.py
"""
import importlib.util
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import sync_playwright  # noqa: E402

from generator.script_generator import generate_script  # noqa: E402


def _load_module():
    scratch_dir = Path(tempfile.mkdtemp(prefix="otp_resolver_unit_"))
    test_case = {"name": "otp_resolver_unit", "start_url": "about:blank", "actions": []}
    script_path = generate_script(test_case, out_name="otp_resolver_unit_script.py", output_dir=scratch_dir)
    spec = importlib.util.spec_from_file_location("otp_resolver_unit_script", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


NESTED_HTML = """
<html><body>
<div tabindex="0" id="btn" style="width:384px;height:52px;">
  <div id="label">Send OTP</div>
</div>
</body></html>
"""

SEPARATE_HTML = """
<html><body>
<div id="a" style="position:absolute;top:0;left:0;width:200px;height:50px;">Send OTP</div>
<div id="b" style="position:absolute;top:200px;left:0;width:200px;height:50px;">Send OTP</div>
</body></html>
"""

ICON_HTML = """
<html><body>
<div id="icon" style="position:absolute;top:0;left:0;width:36px;height:36px;">&#xF24A;</div>
<div id="button" style="position:absolute;top:100px;left:0;width:384px;height:52px;">
  <div id="label2">Send OTP</div>
</div>
</body></html>
"""


def run_tests():
    module = _load_module()
    results = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        # --- 6a/6b analogue: nested duplicate collapse picks the outer button ---
        page.set_content(NESTED_HTML)
        lp = {"text": "Send OTP", "tag": "div", "css_path": "#nonexistent", "xpath": "//nonexistent"}
        el = module._find_by_text_tag(page, lp)
        if el is None:
            results["nested_collapse"] = "FAIL: _find_by_text_tag returned None (expected the outer #btn div)"
        else:
            tag_id = el.evaluate("e => e.id")
            results["nested_collapse"] = (
                "PASS: resolved to #btn (the outer, hit-testable button)"
                if tag_id == "btn" else f"FAIL: resolved to #{tag_id} instead of #btn"
            )

        # --- 6c: two genuinely separate (non-nested) exact-text matches -> ambiguous -> None ---
        page.set_content(SEPARATE_HTML)
        lp2 = {"text": "Send OTP", "tag": "div", "css_path": "#nonexistent", "xpath": "//nonexistent"}
        el2 = module._find_by_text_tag(page, lp2)
        results["separate_ambiguous"] = (
            "PASS: correctly returned None (genuinely ambiguous, not collapsed)"
            if el2 is None else "FAIL: should have returned None for two separate matches"
        )

        # --- icon-vs-button css_path ambiguity: _find_by_css must reject the
        # icon and pick the text-consistent button when the recorded
        # css_path itself matches both ---
        page.set_content(ICON_HTML)
        lp3 = {"text": "Send OTP", "css_path": "body > div", "href": None}
        el3 = module._find_by_css(page, lp3)
        if el3 is None:
            results["css_path_ambiguous"] = "FAIL: _find_by_css returned None (expected #button)"
        else:
            tag_id3 = el3.evaluate("e => e.id")
            results["css_path_ambiguous"] = (
                "PASS: resolved to #button (rejected the icon match)"
                if tag_id3 == "button" else f"FAIL: resolved to #{tag_id3} instead of #button"
            )

        # --- _verify_resolved_target directly rejects an icon-only element ---
        page.set_content(ICON_HTML)
        icon_el = page.locator("#icon")
        lp4 = {"text": "Send OTP"}
        ok4, reason4 = module._verify_resolved_target(icon_el, lp4)
        results["verify_target_rejects_icon"] = (
            "PASS: icon-only element correctly rejected" if not ok4
            else f"FAIL: icon-only element was accepted (reason={reason4!r})"
        )

        # --- _verify_resolved_target accepts the real, text-consistent button ---
        page.set_content(ICON_HTML)
        button_el = page.locator("#button")
        ok5, reason5 = module._verify_resolved_target(button_el, lp4)
        results["verify_target_accepts_button"] = (
            "PASS: real button correctly accepted" if ok5
            else f"FAIL: real button was rejected (reason={reason5!r})"
        )

        browser.close()

    return results


if __name__ == "__main__":
    results = run_tests()
    print("\n===== OFFLINE RESOLVER UNIT TEST RESULTS =====")
    all_pass = True
    for name, outcome in results.items():
        print(f"{name}: {outcome}")
        if not outcome.startswith("PASS"):
            all_pass = False
    print("\nALL PASS" if all_pass else "\nSOME FAILED")
